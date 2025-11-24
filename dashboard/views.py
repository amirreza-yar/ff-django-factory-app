from django.shortcuts import render
from .serializers import FactorySerializer, MaterialSerializer, Material, StoredFlashing, StoredFlashingSerializer

from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action

class UserFactoryView(generics.RetrieveAPIView):
    serializer_class = FactorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.factory


class MaterialsView(generics.ListAPIView):
    serializer_class = MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        factory = self.request.user.factory
        materials = Material.objects.filter(factory=factory)
        print(factory, materials)
        return materials


class StoredFlashingView(viewsets.ModelViewSet):
    # queryset = StoredFlashing.objects.all()
    serializer_class = StoredFlashingSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ['get', 'post', 'patch']

    def get_queryset(self):
        flashings = StoredFlashing.objects.filter(client=self.request.user)
        return flashings