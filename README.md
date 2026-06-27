# 🛍️ BRAP — AI Shopping Assistant
**Django + DeepSeek AI + Google Shopping (SerpApi)**

---

## 📁 Struktur Project

```
brap_project/
├── brap/                    ← Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── assistant/               ← App utama
│   ├── templates/assistant/
│   │   ├── base.html
│   │   ├── home.html        ← Halaman pencarian
│   │   └── results.html     ← Halaman hasil
│   ├── static/
│   │   ├── css/main.css
│   │   └── js/main.js
│   ├── services.py          ← DeepSeek + Google Shopping logic
│   ├── views.py
│   └── urls.py
├── requirements.txt
├── .env.example
├── Procfile                 ← Untuk Railway/Heroku
└── runtime.txt
```

---

## ⚙️ CARA INSTALL & MENJALANKAN LOKAL

### 1. Clone / Download project

```bash
git clone <repo-url>
cd brap_project
```

### 2. Buat Virtual Environment

```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables

```bash
# Copy file contoh
cp .env.example .env

# Edit .env dengan editor favoritmu (VS Code, Notepad, dll)
```

Isi `.env` dengan:

```env
SECRET_KEY=buat-secret-key-panjang-minimal-50-karakter-acak
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DEEPSEEK_API_KEY=sk-xxxxxxxx        # Dari platform.deepseek.com
SERPAPI_KEY=xxxxxxxxxxxxxxxx         # Dari serpapi.com
```

### 5. Jalankan Migrasi Database

```bash
python manage.py migrate
```

### 6. Jalankan Server

```bash
python manage.py runserver
```

Buka browser: **http://127.0.0.1:8000**

---

## 🔑 CARA DAPAT API KEY

### A. DeepSeek API Key
1. Buka https://platform.deepseek.com/
2. Daftar / Login
3. Klik **API Keys** → **Create new API key**
4. Copy key → paste ke `.env` sebagai `DEEPSEEK_API_KEY`
5. **Biaya**: Sangat murah (~$0.0001/request)

### B. SerpApi Key (Google Shopping)
1. Buka https://serpapi.com/
2. Daftar akun gratis
3. **Free plan**: 100 pencarian/bulan (cukup untuk testing!)
4. Klik **Dashboard** → copy API Key
5. Paste ke `.env` sebagai `SERPAPI_KEY`
6. **Untuk production**: Plan berbayar mulai $50/bulan (5.000 pencarian)

> **Catatan**: Jika `SERPAPI_KEY` kosong, app otomatis pakai **mode demo** 
> dengan data placeholder. Berguna untuk testing tampilan!

---

## 🚀 DEPLOY KE ONLINE (Railway — GRATIS)

Railway adalah platform deploy paling mudah untuk tugas akhir.

### Langkah Deploy:

#### 1. Push ke GitHub dulu
```bash
git init
git add .
git commit -m "Initial commit BRAP"
git branch -M main
git remote add origin https://github.com/username/brap.git
git push -u origin main
```

#### 2. Buat akun Railway
1. Buka https://railway.app/
2. Login dengan GitHub

#### 3. Deploy dari GitHub
1. Klik **New Project** → **Deploy from GitHub repo**
2. Pilih repo BRAP kamu
3. Railway otomatis detect Django dan deploy!

#### 4. Set Environment Variables di Railway
Di dashboard Railway → project kamu → **Variables**:

```
SECRET_KEY          = (buat key panjang baru untuk production)
DEBUG               = False
ALLOWED_HOSTS       = nama-app.up.railway.app
DEEPSEEK_API_KEY    = sk-xxxxxxxx
SERPAPI_KEY         = xxxxxxxxxxxxxxxx
```

#### 5. Generate Secret Key Baru
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### 6. Jalankan Static Files
Di Railway dashboard → **Settings** → **Deploy** → tambahkan:
```
python manage.py collectstatic --noinput
```

Atau tambahkan ke `Procfile`:
```
release: python manage.py migrate && python manage.py collectstatic --noinput
```

---

## 🔧 CARA KERJA SISTEM

```
User input query
      ↓
[DeepSeek AI] → Parse query → extract:
  - keywords, budget, kategori, sort_by
      ↓
[SerpApi Google Shopping] → Cari produk real
      ↓
[DeepSeek AI] → Generate "BRAP Insight" per produk
      ↓
[Django Template] → Tampilkan hasil ke user
```

---

## 📝 TROUBLESHOOTING

| Error | Solusi |
|-------|--------|
| `ModuleNotFoundError: dotenv` | `pip install python-dotenv` |
| `DisallowedHost` | Tambahkan domain ke `ALLOWED_HOSTS` di `.env` |
| `Produk tidak ditemukan` | Cek `SERPAPI_KEY` di `.env` |
| Static files tidak muncul di production | Jalankan `collectstatic` |
| DeepSeek error | Cek saldo/kuota di platform.deepseek.com |

---

## 💡 PENGEMBANGAN LANJUTAN (Opsional)

- **Login/Register**: Django built-in auth
- **History pencarian**: Simpan ke database (buat model `SearchHistory`)
- **Wishlist**: User bisa save produk favorit
- **Notifikasi harga**: Cek harga berkala dengan Celery
- **Image search**: Upload foto, cari produk serupa
- **Perbandingan produk**: Tambahkan fitur compare side-by-side

---

## 🛠️ Tech Stack

- **Backend**: Django 5.0
- **AI**: DeepSeek (parse query + generate insight)  
- **Shopping Data**: SerpApi Google Shopping
- **Frontend**: HTML/CSS vanilla (dark theme)
- **Deploy**: Railway / Heroku / VPS
- **Static**: WhiteNoise
