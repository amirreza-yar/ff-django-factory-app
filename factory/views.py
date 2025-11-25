# from rest_framework import permissions, viewsets
# from django.contrib.auth import authenticate, login, logout
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from rest_framework import status

# from .models import Factory, Staff, Material, DeliveryMethod
# from .serializers import FactorySerializer, MaterialSerializer, StaffSerializer, DeliveryMethodSerializer
# from .permissions import DjangoModelPermissionsForAll


# class FactoryViewSet(viewsets.ModelViewSet):
#     queryset = Factory.objects.all()
#     serializer_class = FactorySerializer
#     # permission_classes = [DjangoModelPermissionsForAll]
#     permission_classes = [permissions.AllowAny]


# class StaffViewSet(viewsets.ModelViewSet):
#     queryset = Staff.objects.all()
#     serializer_class = StaffSerializer
#     # permission_classes = [DjangoModelPermissionsForAll]
#     permission_classes = [permissions.AllowAny]

#     def get_queryset(self):
#         factory_id = self.kwargs.get('factory_pk')
#         if factory_id:
#             return Staff.objects.filter(factory_id=factory_id)
#         return Staff.objects.none()
    
#     def perform_create(self, serializer):
#         serializer.save(factory_id=self.kwargs["factory_pk"])


# class MaterialViewSet(viewsets.ModelViewSet):
#     queryset = Material.objects.all()
#     serializer_class = MaterialSerializer
#     # permission_classes = [DjangoModelPermissionsForAll]
#     permission_classes = [permissions.AllowAny]

#     def get_queryset(self):
#         factory_id = self.kwargs.get('factory_pk')
#         if factory_id:
#             return Material.objects.filter(factory_id=factory_id)
#         return Material.objects.none()

#     def perform_create(self, serializer):
#         serializer.save(factory_id=self.kwargs["factory_pk"])


# class DeliveryMethodView(viewsets.ModelViewSet):
#     queryset = DeliveryMethod.objects.all()
#     serializer_class = DeliveryMethodSerializer
#     permission_classes = [permissions.AllowAny]
    
#     def get_queryset(self):
#         factory_id = self.kwargs.get('factory_pk')
#         if factory_id:
#             return DeliveryMethod.objects.filter(factory_id=factory_id)
#         return DeliveryMethod.objects.none()

#     def perform_create(self, serializer):
#         serializer.save(factory_id=self.kwargs["factory_pk"])
