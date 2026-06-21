# ActionCoach Turkey Dashboard

## Dosya yapısı
```
actioncoach_dashboard/
├── app.py
├── hubspot_client.py
├── requirements.txt
├── .streamlit/
│   └── secrets.toml   ← token buraya (GitHub'a yükleme!)
└── pages/
    ├── overview.py
    ├── contacts.py
    └── forms.py
```

## Deploy adımları

### 1. GitHub repo aç
- github.com → New repository → "actioncoach-dashboard" → Public → Create

### 2. Dosyaları yükle
- Add file → Upload files
- Şu dosyaları sürükle bırak:
  - app.py
  - hubspot_client.py
  - requirements.txt
  - pages/ klasörü (overview.py, contacts.py, forms.py)
- secrets.toml'u yükleme! (token güvenliği)

### 3. Streamlit Cloud
- share.streamlit.io → Sign in with GitHub
- New app → repo seç → Main file: app.py → Deploy

### 4. Token ekle (Streamlit Cloud'da)
- App Settings → Secrets → şunu yapıştır:
  HUBSPOT_TOKEN = "pat-eu1-..."

### 5. Reboot app → hazır!
