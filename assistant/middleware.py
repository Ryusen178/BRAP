"""Middleware untuk melacak kunjungan halaman"""
from .models import PageVisit


def get_client_ip(request):
    """Dapatkan IP address dari request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class PageVisitTrackingMiddleware:
    """Middleware untuk melacak setiap kunjungan halaman (page view asli, bukan API/AJAX)"""

    def __init__(self, get_response):
        self.get_response = get_response
        # Halaman/prefix yang tidak perlu dilacak sebagai "kunjungan"
        self.ignored_paths = [
            '/admin/',
            '/accounts/',
            '/static/',
            '/media/',
            '/__debug__/',
            '/api/',         # endpoint AJAX/background, bukan halaman yang dibuka user
            '/dashboard/',   # supaya admin buka/refresh dashboard tidak ikut tercatat
        ]

    def __call__(self, request):
        # Hanya hitung request GET (load halaman), bukan POST/AJAX/background call,
        # dan path-nya tidak termasuk yang di-ignore
        should_track = (
            request.method == 'GET'
            and all(not request.path.startswith(path) for path in self.ignored_paths)
        )

        if should_track:
            try:
                PageVisit.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    page=request.path,
                    visitor_ip=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
                )
            except Exception:
                # Jangan biarkan tracking error mengganggu aplikasi
                pass

        response = self.get_response(request)
        return response
