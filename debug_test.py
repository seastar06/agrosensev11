"""Debug v2 - doğru collection adları ile test"""
import streamlit as st, requests, json
from datetime import datetime, timedelta

st.set_page_config(page_title="Debug v2", layout="wide")
st.title("🔍 Debug v2")

SH_CLIENT_ID     = "sh-645dcab9-79b1-42a2-9d89-edee62b45fe1"
SH_CLIENT_SECRET = "S2xXnoyA9RkciUtMv4DVntkV2hFQZbMd"

@st.cache_data(ttl=1700)
def get_token():
    r = requests.post(
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        data={"grant_type":"client_credentials","client_id":SH_CLIENT_ID,"client_secret":SH_CLIENT_SECRET},
        timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]

token = get_token()
st.success("✓ Token OK")

test_date = st.text_input("Test tarihi", "2024-06-15")
st.markdown("---")

# STAC - farklı collection adlarını dene
st.markdown("## STAC Collection Denemeleri")
STAC_URL = "https://catalogue.dataspace.copernicus.eu/stac/search"
collections_to_try = ["SENTINEL-2-L2A", "sentinel-2-l2a", "S2MSI2A", "SENTINEL-2"]

if st.button("Tüm Collection'ları Dene"):
    d = datetime.strptime(test_date, "%Y-%m-%d")
    s = (d - timedelta(days=15)).strftime("%Y-%m-%dT00:00:00Z")
    e = (d + timedelta(days=15)).strftime("%Y-%m-%dT23:59:59Z")
    bbox = [33.50, 39.84, 33.51, 39.85]

    for coll in collections_to_try:
        body = {"collections":[coll], "bbox":bbox, "datetime":f"{s}/{e}", "limit":3}
        r = requests.post(STAC_URL, json=body,
            headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"}, timeout=15)
        feats = r.json().get("features",[]) if r.ok else []
        if feats:
            st.success(f"✅ `{coll}` → {len(feats)} sahne! İlk: {feats[0]['properties']['datetime'][:10]}")
            st.session_state["working_collection"] = coll
            st.session_state["stac_features"] = feats
        else:
            st.warning(f"❌ `{coll}` → 0 sonuç (status:{r.status_code})")

# STAC root - hangi collections var?
st.markdown("---")
if st.button("STAC Root Collections Listele"):
    r = requests.get("https://catalogue.dataspace.copernicus.eu/stac/collections",
        headers={"Authorization":f"Bearer {token}"}, timeout=15)
    if r.ok:
        data = r.json()
        colls = data.get("collections", [])
        s2 = [c for c in colls if "2" in c.get("id","") and "SENTINEL" in c.get("id","").upper()]
        st.write(f"Toplam {len(colls)} collection, S2 olanlar:")
        for c in s2:
            st.write(f"- `{c['id']}` — {c.get('title','')}")
    else:
        st.error(f"{r.status_code}: {r.text[:200]}")

# OpenEO - doğru collection adı ile dene
st.markdown("---")
st.markdown("## OpenEO SENTINEL2_L2A Test")
if st.button("OpenEO NDVI Çek (SENTINEL2_L2A)"):
    import openeo
    conn = openeo.connect("https://openeo.dataspace.copernicus.eu")
    conn.authenticate_oidc_client_credentials(client_id=SH_CLIENT_ID, client_secret=SH_CLIENT_SECRET)

    # SENTINEL2_L2A — koleksiyon listesinde bu vardı!
    d = datetime.strptime(test_date, "%Y-%m-%d")
    start = (d - timedelta(days=15)).strftime("%Y-%m-%d")
    end   = (d + timedelta(days=15)).strftime("%Y-%m-%d")

    with st.spinner(f"OpenEO: {start} → {end}..."):
        try:
            cube = conn.load_collection(
                "SENTINEL2_L2A",
                spatial_extent={"west":33.50,"south":39.84,"east":33.51,"north":39.85},
                temporal_extent=[start, end],
                bands=["B04","B08"],
                max_cloud_cover=90,
            )
            b08 = cube.band("B08"); b04 = cube.band("B04")
            ndvi = (b08-b04)/(b08+b04)
            ndvi_t = ndvi.reduce_dimension(dimension="t", reducer="mean")

            fc = {"type":"FeatureCollection","features":[
                {"type":"Feature","id":"test",
                 "geometry":{"type":"Polygon","coordinates":[[[33.50,39.84],[33.51,39.84],
                   [33.51,39.85],[33.50,39.85],[33.50,39.84]]]},"properties":{}}]}

            result = ndvi_t.aggregate_spatial(geometries=fc, reducer="mean")
            raw = result.execute()
            st.success("✓ Veri geldi!")
            st.write("Tip:", type(raw).__name__)
            st.write("Değer:", raw)
            st.json(raw if isinstance(raw,(dict,list)) else {"val":str(raw)})
        except Exception as e:
            st.error(f"Hata: {e}")

# OpenEO - geniş aralık, reduce olmadan timestamp bak
st.markdown("---")
if st.button("OpenEO: Mevcut Tarihleri Göster"):
    import openeo
    conn = openeo.connect("https://openeo.dataspace.copernicus.eu")
    conn.authenticate_oidc_client_credentials(client_id=SH_CLIENT_ID, client_secret=SH_CLIENT_SECRET)
    d = datetime.strptime(test_date, "%Y-%m-%d")
    start = (d - timedelta(days=30)).strftime("%Y-%m-%d")
    end   = (d + timedelta(days=30)).strftime("%Y-%m-%d")
    with st.spinner("Zaman bilgisi alınıyor..."):
        try:
            cube = conn.load_collection(
                "SENTINEL2_L2A",
                spatial_extent={"west":33.50,"south":39.84,"east":33.51,"north":39.85},
                temporal_extent=[start, end],
                bands=["B04"],
                max_cloud_cover=90,
            )
            # sadece timestamps'i al — veri indirme
            ts = cube.dimension_labels("t").execute()
            st.success(f"✓ {len(ts)} görüntü tarihi:")
            st.write(ts)
            st.session_state["available_dates"] = ts
        except Exception as e:
            st.error(f"Hata: {e}")
