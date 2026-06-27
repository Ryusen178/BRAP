from django.contrib import admin
from django.urls import path, include
from assistant.views import admin_dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('dashboard/', admin_dashboard, name='admin_dashboard'),
    path('', include('assistant.urls')),
]
