from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from .models import Factory

class APIRootView(APIView):
    """
    API Root that lists all factory-related routes.
    """
    def get(self, request, *args, **kwargs):
        first_factory = Factory.objects.first()
        factory_id = first_factory.pk if first_factory else "<factory_id>"

        return Response({
            "factories": reverse("factory-list", request=request),
            "materials": reverse(
                "materials-list", kwargs={"factory_pk": factory_id}, request=request
            ),
            "delivery methods": reverse(
                "delivery-methods-list", kwargs={"factory_pk": factory_id}, request=request
            ),
            "staffsy": reverse(
                "staffs-list", kwargs={"factory_pk": factory_id}, request=request
            ),
            "auth ui": reverse("auth_kit_ui", request=request),
            "doc": reverse('redoc', request=request)
            
        })
        
# class APIAuthView(APIView):
#     def get(self, request, *args, **kwargs):
#         return Response({
#             "drf-kit-login": reverse("login", request=request),
#         })