from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularRedocView, SpectacularAPIView
)
from auth_kit.views import AuthKitUIView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('factory.urls'), name='factory-api'),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path('api/auth/', include('auth_kit.urls')),
    path('api/auth/ui/', AuthKitUIView.as_view(), name='auth_kit_ui'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
