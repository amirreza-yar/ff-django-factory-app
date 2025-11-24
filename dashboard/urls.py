from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import UserFactoryView, MaterialsView, StoredFlashingView


router = DefaultRouter()
router.register('flashing', StoredFlashingView, basename='user-flashing')
# flashing_router = routers.NestedDefaultRouter(router, 'flashing', lookup='flashing')

# router.register("materials", MaterialsView, basename='user-materials')

urlpatterns = [
    path("factory/", UserFactoryView.as_view(), name='user-factory'),
    path("materials/", MaterialsView.as_view(), name='user-material'),
] + router.urls
