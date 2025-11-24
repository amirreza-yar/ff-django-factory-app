from django.shortcuts import render
from .serializers import FactorySerializer, MaterialSerializer, Material, StoredFlashing, StoredFlashingSerializer, AddressSerializer, JobReferenceSerializer, JobReference, Address

from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action

class UserFactoryView(generics.RetrieveAPIView):
    serializer_class = FactorySerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ['get', 'options']

    def get_object(self):
        return self.request.user.factory


class MaterialsView(generics.ListAPIView):
    serializer_class = MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ['get', 'options']

    def get_queryset(self):
        return self.request.user.factory.materials.all()


class StoredFlashingView(viewsets.ModelViewSet):
    serializer_class = StoredFlashingSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ['get', 'post', 'patch', 'options']

    def get_queryset(self):
        return self.request.user.flashings.all()


class JobReferenceView(viewsets.ModelViewSet):
    serializer_class = JobReferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ['get', 'post', 'patch', 'delete', 'options']

    def get_queryset(self):
        return self.request.user.job_references.all()


class AddressView(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ['get', 'post', 'patch', 'options']

    def get_queryset(self):
        job_ref_id = self.kwargs.get('job_ref_pk')
        return self.request.user.job_references.get(id=job_ref_id).addresses.all()
    
    def perform_create(self, serializer):
        serializer.save(job_reference_id=self.kwargs["job_ref_pk"])