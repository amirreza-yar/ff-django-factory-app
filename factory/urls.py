# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from rest_framework_nested import routers
# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
# from drf_spectacular.views import (
#     SpectacularRedocView,
# )
# from auth_kit.views import AuthKitUIView

# from . import views
# from .api import APIRootView

# router = routers.SimpleRouter()

# router.register("factory", views.FactoryViewSet, basename="factory")
# factory_router = routers.NestedDefaultRouter(router, "factory", lookup="factory")

# factory_router.register("staff", views.StaffViewSet, basename="staffs")
# factory_router.register("material", views.MaterialViewSet, basename="materials")
# factory_router.register("delivery-method", views.DeliveryMethodView, basename="delivery-methods")

urlpatterns = (
    # [
    #     path('', APIRootView.as_view(), name='api-root'),
    # ]
    # + factory_router.urls
    # + router.urls
)
