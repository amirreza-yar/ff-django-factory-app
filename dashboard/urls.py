from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers as nested_routers

from .views import (
    UserFactoryView,
    MaterialsView,
    StoredFlashingView,
    JobReferenceView,
    AddressView,
    OrderView,
    CartView,
    TemplateView,
    NewJobReferenceView,
    UserProfileView,
)


# router = DefaultRouter()
# router.register('flashing', StoredFlashingView, basename='user-flashing')
# router.register('order', OrderView, basename="user-order")

nested_router = nested_routers.SimpleRouter()
nested_router.register("flashing", StoredFlashingView, basename="user-flashing")
nested_router.register("order", OrderView, basename="user-order")
nested_router.register("cart", CartView, basename="user-cart")
nested_router.register("template", TemplateView, basename="user-template")

nested_router.register("job-ref", JobReferenceView, basename="user-job-reference")
nested_router.register("job-ref-new", NewJobReferenceView, basename="user-new-job-reference")
job_reference_router = nested_routers.NestedDefaultRouter(
    nested_router, "job-ref", lookup="job_ref"
)
job_reference_router.register("address", AddressView, basename="user-address")

# flashing_router = routers.NestedDefaultRouter(router, 'flashing', lookup='flashing')

# router.register("materials", MaterialsView, basename='user-materials')

urlpatterns = (
    [
        path("factory/", UserFactoryView.as_view(), name="user-factory"),
        path("materials/", MaterialsView.as_view(), name="user-material"),
        path("profile/", UserProfileView.as_view(), name="user-profile"),
        # path("cart/", CartView.as_view({'get': 'retrieve'}), name="user-cart"),
        # path("job-reference/", JobReferenceView.as_view(), name='user-job-reference'),
    ]
    + nested_router.urls
    + job_reference_router.urls
)
