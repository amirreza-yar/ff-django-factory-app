from rest_framework import serializers

from .models import StoredFlashing

class StoredFlashingSerializer(serializers.Serializer):
    
    class Meta:
        model = StoredFlashing
        fields = ['']