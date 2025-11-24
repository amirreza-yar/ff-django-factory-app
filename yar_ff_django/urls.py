from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularRedocView, SpectacularAPIView
)
from auth_kit.views import AuthKitUIView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('factory.urls'), name='factory-api'),
    path('', include('base.urls'), name='base-api'),
    path('api/d/', include('dashboard.urls'), name='dashboard-api'),
]
