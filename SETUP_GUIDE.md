# BRAP — Setup Guide

Panduan lengkap untuk setup AI Fallback dan Google OAuth Login di BRAP Shopping Assistant.

## Prerequisites
- Python 3.8+
- Django 5.0.6
- Virtual Environment

## 1. Install Dependencies

```bash
# Activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

## 2. Setup Database & Migrations

```bash
# Create migrations for django-allauth
python manage.py migrate

# Create superuser untuk admin panel
python manage.py createsuperuser

# Collect static files (untuk production)
python manage.py collectstatic
```

## 3. Configure Google OAuth

### Step 1: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable "Google+ API"

### Step 2: Create OAuth 2.0 Credentials
1. Go to Credentials page
2. Click "Create Credentials" → "OAuth 2.0 Client ID"
3. Choose "Web Application"
4. Add authorized redirect URIs:
   - `http://localhost:8000/accounts/google/login/callback/`
   - `http://yourdomain.com/accounts/google/login/callback/` (for production)
5. Copy Client ID dan Client Secret

### Step 3: Configure in Django Admin
1. Run: `python manage.py runserver`
2. Go to http://localhost:8000/admin
3. Login dengan superuser credentials
4. Go to "Sites" dan pastikan domain sesuai (localhost:8000 untuk development)
5. Go to "Social Applications"
6. Tambah provider "Google":
   - Name: Google
   - Client id: <paste your Client ID>
   - Secret key: <paste your Client Secret>
   - Sites: pilih site yang sesuai

### Step 4: Setup .env file
```bash
# Copy .env.example ke .env
cp .env.example .env

# Edit .env dan isi API keys:
# DEEPSEEK_API_KEY=sk-xxxx
# GEMINI_API_KEY=AIzaSyxxx
# GROQ_API_KEY=gsk_xxxx
# SERPAPI_KEY=xxxx
```

## 4. Setup AI APIs

### Option A: DeepSeek (Primary AI)
1. Go to [api.deepseek.com](https://api.deepseek.com)
2. Sign up dan create API key
3. Add ke .env: `DEEPSEEK_API_KEY=sk-xxxx`

### Option B: Google Gemini (Fallback 1)
1. Go to [makersuite.google.com](https://makersuite.google.com/app/apikey)
2. Click "Get API Key"
3. Add ke .env: `GEMINI_API_KEY=AIzaSyxxx`

### Option C: Groq (Fallback 2)
1. Go to [console.groq.com](https://console.groq.com)
2. Create account dan get API key
3. Add ke .env: `GROQ_API_KEY=gsk_xxxx`

### Google Shopping API (SerpApi)
1. Go to [serpapi.com](https://serpapi.com)
2. Get API key
3. Add ke .env: `SERPAPI_KEY=xxxx`

## 5. Run Development Server

```bash
python manage.py runserver
```

Visit: http://localhost:8000

## 6. Features Overview

### Google OAuth Login
- Click "Login" button di navbar
- Pilih "Lanjutkan dengan Google"
- User akan redirect ke Google login
- Setelah login, user akan redirect ke home page

### AI Fallback Chain
Query parsing menggunakan fallback chain otomatis:
1. **DeepSeek** (Primary)
2. **Gemini** (Fallback if DeepSeek fails)
3. **Groq** (Fallback if both fail)
4. **Basic parsing** (Last resort)

Jika salah satu AI provider down atau rate limit, sistem akan otomatis gunakan provider berikutnya.

### User Menu
- Logged-in users akan melihat avatar di navbar
- Click avatar untuk buka dropdown menu
- Logout dari sini

## 7. Troubleshooting

### "Social Account Provider not found"
```bash
# Make sure django-allauth is properly installed
pip install django-allauth --upgrade
python manage.py migrate
```

### Google Login not working
- Check .env file for correct Client ID & Secret
- Verify redirect URIs di Google Cloud Console
- Make sure "Site" domain matches di Django admin

### AI APIs not responding
- Check API keys di .env
- Verify internet connection
- Check rate limits dari provider

## 8. Production Deployment

### Update settings for production:
```bash
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECRET_KEY=generate-strong-secret-key

# For Heroku:
- Add environment variables di Heroku Config Vars
- Run: git push heroku main
```

### Use environment-specific settings:
```python
# settings.py
if not DEBUG:
    # Production settings
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
```

## Additional Resources

- [Django Allauth Docs](https://django-allauth.readthedocs.io/)
- [DeepSeek API Docs](https://api-docs.deepseek.com/)
- [Google Gemini API Docs](https://ai.google.dev/)
- [Groq API Docs](https://console.groq.com/docs)
- [SerpApi Docs](https://serpapi.com/docs)

---

**Last Updated:** 2026-06-24
**Version:** 1.0
