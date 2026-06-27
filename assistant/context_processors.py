from django.urls import NoReverseMatch, reverse


def oauth(request):
    """Expose Google OAuth login URL only when provider routes are registered."""
    try:
        return {'google_login_url': reverse('google_login')}
    except NoReverseMatch:
        return {'google_login_url': None}
