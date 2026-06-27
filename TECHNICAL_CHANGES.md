# BRAP — Technical Changes Documentation

## Overview
Implementasi AI Fallback Chain (DeepSeek → Gemini → Groq) dan Google OAuth Login ke BRAP Shopping Assistant.

---

## 1. AI Fallback Chain Implementation

### Location: `assistant/services.py`

#### Key Changes:
- **Fallback Flow:**
  ```
  DeepSeek (Primary)
       ↓ (if fails)
  Gemini (Fallback 1)
       ↓ (if fails)
  Groq (Fallback 2)
       ↓ (if fails)
  Basic Parsing (Last Resort)
  ```

#### New Functions:
- `_parse_query_deepseek()` - Try DeepSeek API
- `_parse_query_gemini()` - Try Google Gemini API
- `_parse_query_groq()` - Try Groq API (Mixtral model)
- `parse_query_with_fallback()` - Main orchestrator function
- `parse_query_with_deepseek()` - Backward compatibility wrapper

#### Updated Functions with Fallback:
- `generate_brap_insight()` - Generate product insights with fallback
- `generate_product_description()` - Generate descriptions with fallback

#### Error Handling:
- Each failed AI provider logs as `WARNING` (not `ERROR`)
- Gracefully fallback to next provider
- Final fallback to basic parsing if all AI providers fail
- System always returns valid response (never fails completely)

### Environment Variables Required:
```env
DEEPSEEK_API_KEY=sk-xxxx              # Optional
GEMINI_API_KEY=AIzaSyxxx             # Optional
GROQ_API_KEY=gsk_xxxx                # Optional
```

**Note:** At least one API key should be configured. If none available, system falls back to basic parsing.

---

## 2. Google OAuth Login Implementation

### Location: `brap/settings.py`, `brap/urls.py`, `templates/account/`

#### Changes in settings.py:

**Added to INSTALLED_APPS:**
```python
'django.contrib.sites',
'allauth',
'allauth.account',
'allauth.socialaccount',
'allauth.socialaccount.providers.google',
```

**Added Configuration:**
```python
SITE_ID = 1

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'}
    }
}

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Allauth Settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'optional'
SOCIALACCOUNT_AUTO_SIGNUP = True
LOGIN_REDIRECT_URL = '/'
```

#### Changes in brap/urls.py:
```python
path('accounts/', include('allauth.urls')),  # Added for OAuth handling
```

#### New Templates:

1. **templates/account/login.html**
   - Custom login page with Google OAuth button
   - Email/password login option
   - Link ke signup page
   - Styled dengan BRAP design system

2. **templates/account/signup.html**
   - Custom signup page
   - Google OAuth option
   - Email registration form
   - Password requirements display

#### Updated base.html:
```html
<!-- User authentication UI in navbar -->
{% if user.is_authenticated %}
  <!-- Show user avatar + dropdown menu -->
{% else %}
  <!-- Show login button -->
{% endif %}
```

### Required Setup:
1. Generate Google OAuth 2.0 credentials from Google Cloud Console
2. Configure in Django admin panel under "Social Applications"
3. Add redirect URIs to Google Cloud Console

---

## 3. Dependencies Added

### requirements.txt:
```
google-generativeai==0.5.0    # Google Gemini API client
groq==0.4.2                    # Groq API client
django-allauth==0.57.0         # OAuth & authentication
```

### Installation:
```bash
pip install -r requirements.txt
python manage.py migrate      # Create allauth tables
```

---

## 4. Database Changes

### New Tables (from django-allauth):
- `socialaccount_socialapp` - OAuth app configurations
- `socialaccount_socialaccount` - User social accounts
- `socialaccount_sociallogin` - Social login history
- `account_emailaddress` - Email verification data

### Migration:
```bash
python manage.py migrate
```

---

## 5. Settings Configuration

### Location: `brap/settings.py`

#### New API Key Settings:
```python
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
```

#### OAuth Configuration:
```python
SOCIALACCOUNT_PROVIDERS = { ... }
AUTHENTICATION_BACKENDS = [ ... ]
```

---

## 6. File Structure

```
brap_project/
├── assistant/
│   ├── services.py (UPDATED - AI fallback chain)
│   ├── templates/assistant/
│   │   └── base.html (UPDATED - user auth UI)
│   └── static/css/
│       └── main.css (UPDATED - user menu styles)
├── brap/
│   ├── settings.py (UPDATED - OAuth config)
│   └── urls.py (UPDATED - allauth urls)
├── templates/account/ (NEW)
│   ├── login.html (NEW)
│   └── signup.html (NEW)
├── requirements.txt (UPDATED)
├── .env.example (NEW)
├── SETUP_GUIDE.md (NEW)
└── TECHNICAL_CHANGES.md (NEW)
```

---

## 7. Usage Examples

### 1. AI Query Parsing (Automatic Fallback):
```python
from assistant.services import parse_query_with_fallback

# Will try DeepSeek → Gemini → Groq → Basic parsing
result = parse_query_with_fallback("Cari laptop gaming murah")
# Returns: {
#   "keywords": "laptop gaming",
#   "max_price": None,
#   "category": "laptop",
#   ...
# }
```

### 2. Product Insight Generation (With Fallback):
```python
from assistant.services import generate_brap_insight

insight = generate_brap_insight(
    product_name="Dell XPS 13",
    price=12000000,
    user_query="laptop gaming murah"
)
# Returns: "Best Value: Performa tinggi & Ringkas"
```

### 3. Google OAuth Login Flow:
1. User clicks "Login" button
2. Redirected to `/accounts/login/`
3. User clicks "Lanjutkan dengan Google"
4. Redirected to Google consent screen
5. After consent, creates/updates user account
6. Redirected to home page with authenticated session

---

## 8. Security Considerations

### API Keys:
- Store in `.env` file (not committed to git)
- Add `.env` to `.gitignore`
- Never expose in logs or error messages

### OAuth:
- Use HTTPS in production
- Set `SECURE_SSL_REDIRECT = True` in production
- Enable `SESSION_COOKIE_SECURE = True`
- Enable `CSRF_COOKIE_SECURE = True`

### Rate Limiting:
- Implement rate limiting for API calls
- Add caching for common queries
- Monitor API quotas

---

## 9. Testing

### Unit Tests for AI Fallback:
```python
def test_parse_query_fallback_chain():
    # Mock DeepSeek to fail
    # Verify Gemini is tried
    # Verify Groq is tried if Gemini fails
    pass

def test_generate_insight_with_fallback():
    # Test that each provider can generate insights
    pass
```

### Integration Tests:
```python
def test_google_oauth_login():
    # Test OAuth callback flow
    # Verify user is created/updated
    # Verify session is set
    pass
```

---

## 10. Monitoring & Logs

### AI Provider Status:
```python
# Check logs for provider fallback events
logger.info("Query parsed successfully with DeepSeek")
logger.info("Query parsed successfully with Gemini")
logger.info("Query parsed successfully with Groq")
logger.warning("All AI providers failed, using fallback parsing")
```

### Performance Metrics:
- Track which AI provider is used most frequently
- Monitor API response times
- Track fallback usage rate

---

## 11. Future Enhancements

1. **Caching Layer:**
   - Cache parsed queries for common searches
   - Reduce API calls and costs

2. **Load Balancing:**
   - Distribute requests across providers
   - Improve response time

3. **Provider-Specific Optimizations:**
   - Tune prompts per provider
   - Optimize token usage

4. **User Preferences:**
   - Allow users to choose preferred AI provider
   - User-specific OAuth scopes (calendar, etc.)

5. **Analytics:**
   - Track which AI provider works best for different query types
   - Analyze user search patterns

---

## 12. Troubleshooting Guide

### Issue: "social account provider not found"
**Solution:** Run `python manage.py migrate`

### Issue: Google OAuth redirect not working
**Solution:** 
- Verify redirect URI in Google Cloud Console
- Check Django Site domain in admin
- Ensure ALLOWED_HOSTS includes domain

### Issue: AI queries failing with 401 Unauthorized
**Solution:**
- Verify API keys in .env
- Check API quotas
- Verify API keys are not expired

### Issue: User avatar not showing
**Solution:**
- Verify user has Google social account linked
- Check social account `extra_data` contains `picture` field

---

**Created:** 2026-06-24
**Last Modified:** 2026-06-24
**Version:** 1.0
