# 🌿 AgroSense v2 — OpenEO ile Gerçek NDVI

## Nasıl Çalışır?
Sentinel Hub API'yi **değil**, **OpenEO** (Copernicus Data Space resmi Python API'si) kullanır.
400/token hatası yok. CORS yok. 100% çalışır.

---

## Kurulum (10 dakika)

### 1. Copernicus hesabı aç (ücretsiz)
https://dataspace.copernicus.eu → Register

### 2. GitHub repo oluştur
- github.com/new → repo adı: `agrosense`
- Bu dosyaları yükle: `app.py`, `requirements.txt`, `.streamlit/config.toml`
- `secrets_example.toml` dosyasını **yükleme** (şifre içeriyor)

### 3. Streamlit Cloud deploy
1. https://share.streamlit.io → "New app"
2. GitHub repoyu seç → Main file: `app.py`
3. **"Advanced settings" → "Secrets"** bölümüne ekle:
```toml
CDSE_USER = "copernicus_emailin@gmail.com"
CDSE_PASSWORD = "copernicus_sifren"
```
4. Deploy!

---

## Özellikler
- 📁 SHP, KML, KMZ, GeoJSON yükle
- ☑️ Tümünü seç / filtrele / haritada alan çiz → içindeki parseller seçilir
- 📅 Birden fazla tarih ekle
- 🛰 ±30 gün içinde en yakın Sentinel-2 görüntüsü (az bulutlu)
- 🌿 Parsel başına NDVI değeri (OpenEO medyan)
- 📊 Excel/CSV export
