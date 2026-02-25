"""
Debug test — sidebar'da çalıştır, API yanıtını tam göster
"""
import streamlit as st
import requests
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="AgroSense Debug", layout="wide")
st.title("🔍 AgroSense API Debug")

SH_CLIENT_ID     = "sh-645dcab9-79b1-42a2-9d89-edee62b45fe1"
SH_CLIENT_SECRET = "S2xXnoyA9RkciUtMv4DVntkV2hFQZbMd"

# Test koordinatları — Kırıkkale civarı küçük parsel
TEST_GEOM = {
    "type": "Polygon",
    "coordinates": [[[33.50, 39.84],[33.51, 39.84],[33.51, 39.85],[33.50, 39.85],[33.50, 39.84]]]
}
TEST_DATE = "2024-06-15"

# ── 1. Token ──────────────────────────────────────────────────
st.markdown("## 1. Token Testi")
if st.button("Token Al"):
    try:
        r = requests.post(
            "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
            data={"grant_type":"client_credentials",
                  "client_id":SH_CLIENT_ID,"client_secret":SH_CLIENT_SECRET},
            timeout=15)
        st.write(f"Status: {r.status_code}")
        if r.ok:
            d = r.json()
            st.success(f"✓ Token alındı! expires_in={d.get('expires_in')}s")
            st.session_state["token"] = d["access_token"]
        else:
            st.error(f"Token hatası: {r.text[:300]}")
    except Exception as e:
        st.error(f"Bağlantı hatası: {e}")

# ── 2. STAC ───────────────────────────────────────────────────
st.markdown("## 2. STAC Catalog Testi")
test_date = st.text_input("Test tarihi", value=TEST_DATE)
if st.button("STAC Ara") and "token" in st.session_state:
    d = datetime.strptime(test_date, "%Y-%m-%d")
    start = (d - timedelta(days=15)).strftime("%Y-%m-%dT00:00:00Z")
    end   = (d + timedelta(days=15)).strftime("%Y-%m-%dT23:59:59Z")

    # Versiyon A: filter ile
    body = {
        "collections": ["SENTINEL-2"],
        "bbox": [33.50, 39.84, 33.51, 39.85],
        "datetime": f"{start}/{end}",
        "limit": 5,
    }
    st.write("STAC isteği:", body)
    r = requests.post(
        "https://catalogue.dataspace.copernicus.eu/stac/search",
        json=body,
        headers={"Authorization": f"Bearer {st.session_state['token']}",
                 "Content-Type":"application/json"},
        timeout=20)
    st.write(f"Status: {r.status_code}")
    if r.ok:
        feats = r.json().get("features",[])
        st.success(f"✓ {len(feats)} sahne bulundu")
        for f in feats[:3]:
            st.write(f"- {f['properties']['datetime'][:10]} | bulut: {f['properties'].get('eo:cloud_cover','?')}%")
        if feats:
            st.session_state["best_date"] = feats[0]["properties"]["datetime"][:10]
            st.info(f"En yakın: {st.session_state['best_date']}")
    else:
        st.error(f"STAC hatası: {r.text[:500]}")

# ── 3. OpenEO bağlantı ────────────────────────────────────────
st.markdown("## 3. OpenEO Bağlantı Testi")
if st.button("OpenEO Bağlan"):
    try:
        import openeo
        conn = openeo.connect("https://openeo.dataspace.copernicus.eu")
        conn.authenticate_oidc_client_credentials(
            client_id=SH_CLIENT_ID, client_secret=SH_CLIENT_SECRET)
        caps = conn.describe_account()
        st.success(f"✓ Bağlandı! Hesap: {caps}")
        st.session_state["conn_ok"] = True
    except Exception as e:
        st.error(f"OpenEO bağlantı hatası: {e}")

# ── 4. OpenEO NDVI execute ────────────────────────────────────
st.markdown("## 4. OpenEO NDVI Execute Testi")
best = st.session_state.get("best_date", TEST_DATE)
st.write(f"Kullanılacak tarih: **{best}**")
if st.button("NDVI Çek (OpenEO)") and st.session_state.get("conn_ok"):
    try:
        import openeo
        from datetime import timedelta
        conn = openeo.connect("https://openeo.dataspace.copernicus.eu")
        conn.authenticate_oidc_client_credentials(
            client_id=SH_CLIENT_ID, client_secret=SH_CLIENT_SECRET)

        d_end = (datetime.strptime(best,"%Y-%m-%d")+timedelta(days=1)).strftime("%Y-%m-%d")

        with st.spinner(f"OpenEO çalışıyor ({best} → {d_end})..."):
            cube = conn.load_collection(
                "SENTINEL2_L2A",
                spatial_extent={"west":33.50,"south":39.84,"east":33.51,"north":39.85},
                temporal_extent=[best, d_end],
                bands=["B04","B08"],
                max_cloud_cover=90,
            )
            b08 = cube.band("B08"); b04 = cube.band("B04")
            ndvi = (b08-b04)/(b08+b04)
            ndvi_t = ndvi.reduce_dimension(dimension="t", reducer="mean")

            fc = {"type":"FeatureCollection","features":[
                {"type":"Feature","id":"test",
                 "geometry":TEST_GEOM,"properties":{}}]}

            result = ndvi_t.aggregate_spatial(geometries=fc, reducer="mean")
            raw = result.execute()

        st.success("✓ Execute tamamlandı!")
        st.write("**Ham yanıt tipi:**", type(raw).__name__)
        st.write("**Ham yanıt:**", raw)
        st.json(raw if isinstance(raw,(dict,list)) else {"value":str(raw)})

    except Exception as e:
        st.error(f"OpenEO execute hatası: {type(e).__name__}: {e}")
        import traceback
        st.code(traceback.format_exc())

# ── 5. Koleksiyon listesi ─────────────────────────────────────
st.markdown("## 5. Mevcut Koleksiyonlar")
if st.button("Koleksiyonları Listele"):
    try:
        import openeo
        conn = openeo.connect("https://openeo.dataspace.copernicus.eu")
        conn.authenticate_oidc_client_credentials(
            client_id=SH_CLIENT_ID, client_secret=SH_CLIENT_SECRET)
        colls = conn.list_collections()
        s2_colls = [c for c in colls if "SENTINEL" in c.get("id","").upper() and "2" in c.get("id","")]
        st.write("Sentinel-2 koleksiyonları:")
        for c in s2_colls:
            st.write(f"- `{c['id']}` — {c.get('title','')}")
    except Exception as e:
        st.error(f"Hata: {e}")
