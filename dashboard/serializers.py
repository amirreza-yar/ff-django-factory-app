from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator, ValidationError

from .models import StoredFlashing, Specification, JobReference, Address, Order
from factory.models import (
    Factory,
    Staff,
    Material,
    MaterialVariant,
    MaterialGroup,
    DeliveryMethod,
)


class FactorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Factory
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "address",
            "description",
            "working_hours_start",
            "working_hours_end",
            "weekly_off_days",
            "specific_off_days",
        ]


class SpecificationSerializer(serializers.ModelSerializer):
    # cost = serializers.SerializerMethodField()

    # def get_cost(self, obj):
    #     return obj.cost

    class Meta:
        model = Specification
        fields = ["quantity", "length", "cost"]


class StoredFlashingSerializer(serializers.ModelSerializer):
    original_material_id = serializers.PrimaryKeyRelatedField(
        queryset=MaterialVariant.objects.all(), write_only=True
    )

    material = serializers.SerializerMethodField()

    specifications = SpecificationSerializer(many=True, required=False)

    class Meta:
        model = StoredFlashing
        fields = [
            "id",
            "order",
            "material",
            "start_crush_fold",
            "end_crush_fold",
            "color_side_dir",
            "tapered",
            "nodes",
            "original_material_id",
            "specifications",
            "total_girth",
            "is_complete",
        ]
        read_only_fields = ["id"]

    def get_material(self, obj):
        m = obj.original_material
        g = m.group

        return {
            "material": g.material.name,
            "type": g.material.variant_type,
            "variant_label": m.label,
            "variant_value": m.value,
        }

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        original_material = validated_data.pop("original_material_id")

        stored_flashing = StoredFlashing.objects.create(
            client=user, original_material=original_material, **validated_data
        )
        return stored_flashing

    def update(self, instance, validated_data):
        specs_data = validated_data.pop("specifications", None)

        # regular field updates
        instance = super().update(instance, validated_data)

        if specs_data is not None:
            # wipe old ones
            instance.specifications.all().delete()

            # recreate
            for spec in specs_data:
                Specification.objects.create(flashing=instance, **spec)

        return instance


class MaterialVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialVariant
        fields = ["id", "label", "value"]


class MaterialSerializer(serializers.ModelSerializer):
    variants = MaterialVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Material
        fields = ["id", "name", "variant_type", "variants_count", "variants"]


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id",
            "title",
            "street_address",
            "suburb",
            "state",
            "postcode",
            "recipient_name",
            "recipient_phone",
        ]


class JobReferenceSerializer(serializers.ModelSerializer):

    addresses = AddressSerializer(many=True, required=False)

    class Meta:
        model = JobReference
        fields = ["id", "code", "project_name", "addresses"]

    def validate_code(self, value):
        user = self.context["request"].user
        if JobReference.objects.filter(client=user, code=value).exists():
            raise ValidationError("You already have a job reference with this code.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        addr_data = validated_data.pop("addresses", None)

        job_reference = JobReference.objects.create(client=user, **validated_data)

        if addr_data is not None:
            for addr in addr_data:
                Address.objects.create(job_reference=job_reference, **addr)
        return job_reference


class OrderSerializer(serializers.ModelSerializer):
    flashings = serializers.PrimaryKeyRelatedField(many=True, queryset=StoredFlashing.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            self.fields['flashings'].queryset = StoredFlashing.objects.filter(client=request.user.id)

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "delivery_type",
            "delivery_cost",
            "estimated_delivery_date",
            "original_address",
            "flashings",
            "created_at",
            "is_complete",
        ]

    read_only_fields = ['id', 'status', 'delivery_cost', 'created_at', 'is_complete']

    def update(self, instance, validated_data):
        # validated_data.pop("delivery_type", None)
        # instance.delivery_type = 'delivery'
        return super().update(instance, validated_data)