"""project_kos_wisma URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, include

# TAMBAHAN UNTUK MEDIA (UPLOAD FOTO)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('kos.urls')),
]

# AGAR FOTO KTP BISA DITAMPILKAN
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

