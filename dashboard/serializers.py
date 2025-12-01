from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator, ValidationError
from django.contrib.auth import get_user_model

from .models import (
    StoredFlashing,
    Specification,
    JobReference,
    Address,
    Order,
    Cart,
    Template,
)
from .drafts import JobReferenceDraft
from .sanpshots import StoredFlashingSnapshot
from factory.models import (
    Factory,
    Staff,
    Material,
    MaterialVariant,
    MaterialGroup,
    DeliveryMethod,
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):

    mobile = serializers.CharField(default="+671231231231")

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "mobile"]


class DynamicFieldsMixin(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


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
    class Meta:
        model = Specification
        fields = ["quantity", "length", "cost", "weight"]


class StoredFlashingSerializer(serializers.ModelSerializer):
    material_data = serializers.SerializerMethodField()
    specifications = SpecificationSerializer(many=True, required=True)

    class Meta:
        model = StoredFlashing
        fields = [
            "code", "position", 
            "id",
            "material",
            "material_data",
            "start_crush_fold",
            "end_crush_fold",
            "color_side_dir",
            "tapered",
            "nodes",
            "specifications",
            "total_girth",
            "total_weight",
            "total_cost",
            "is_complete",
        ]
        read_only_fields = ["id"]

    def get_material_data(self, obj):
        m = obj.material
        g = m.group

        return {
            "name": g.material.name,
            "type": g.material.variant_type,
            "label": m.label,
            "value": m.value,
        }

    def _add_to_cart_if_complete(self, flashing):
        if flashing.is_complete:
            user = self.context["request"].user
            if user != flashing.client:
                raise ValidationError("WHAT??")
            cart, _ = Cart.objects.get_or_create(client=flashing.client)
            if not cart.flashings.filter(id=flashing.id).exists():
                cart.flashings.add(flashing)

    def create(self, validated_data):
        specs_data = validated_data.pop("specifications", None)

        stored_flashing = super().create(validated_data)

        if specs_data is not None:
            for spec in specs_data:
                Specification.objects.create(flashing=stored_flashing, **spec)

        self._add_to_cart_if_complete(stored_flashing)

        return stored_flashing

    def update(self, instance, validated_data):
        specs_data = validated_data.pop("specifications", None)

        instance = super().update(instance, validated_data)

        if specs_data is not None:
            instance.specifications.all().delete()

            for spec in specs_data:
                Specification.objects.create(flashing=instance, **spec)

        return instance


class StoredFlashingSnapshotSerializer(serializers.ModelSerializer):
    material = serializers.SerializerMethodField()
    specifications = serializers.SerializerMethodField()

    def get_material(self, obj):
        return {
            "type": obj.material.variant_type,
            "name": obj.material.name,
            "label": obj.material.variant_label,
            "value": obj.material.variant_value,
        }

    def get_specifications(self, obj):
        specs = obj.specifications.all()
        return [
            {
                "quantity": s.quantity,
                "length": s.length,
                "cost": s.cost,
            }
            for s in specs
        ]

    class Meta:
        model = StoredFlashingSnapshot
        fields = [
            "code", "position", 
            "start_crush_fold",
            "end_crush_fold",
            "color_side_dir",
            "tapered",
            "nodes",
            "total_girth",
            "material",
            "specifications",
        ]


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
            "full_address"
        ]


class JobReferenceSerializer(DynamicFieldsMixin):

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


class NewJobReferenceSerializer(serializers.ModelSerializer):
    finalize = serializers.BooleanField(default=False)

    class Meta:
        model = JobReferenceDraft
        fields = [
            "code",
            "project_name",
            "title",
            "street_address",
            "suburb",
            "state",
            "postcode",
            "recipient_name",
            "recipient_phone",
            "finalize",
        ]
        read_only_fields = ["client"]

    def validate_code(self, value):
        user = self.context["request"].user
        if JobReference.objects.filter(client=user, code=value).exists():
            raise ValidationError({"You already have a job reference with this code."})
        return value

    def update(self, instance, validated_data):
        finalize = validated_data.pop("finalize", False)

        # Normal partial update on draft
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if finalize:
            self._finalize(instance)

        return instance

    def _finalize(self, draft):
        required = [
            "code",
            "project_name",
            "title",
            "street_address",
            "suburb",
            "state",
            "postcode",
            "recipient_name",
            "recipient_phone",
        ]

        missing = [f for f in required if not getattr(draft, f)]
        if missing:
            raise ValidationError({"detail": f"Missing fields: {missing}"})

        # Create real JobReference
        job_ref = JobReference.objects.create(
            client=draft.client,
            code=draft.code,
            project_name=draft.project_name,
        )

        Address.objects.create(
            job_reference=job_ref,
            title=draft.title,
            street_address=draft.street_address,
            suburb=draft.suburb,
            state=draft.state,
            postcode=draft.postcode,
            recipient_name=draft.recipient_name,
            recipient_phone=draft.recipient_phone,
        )

        draft.delete()


class OrderSerializer(serializers.ModelSerializer):

    flashings = StoredFlashingSnapshotSerializer(
        many=True,
        required=True,
    )

    job_reference = serializers.SerializerMethodField()
    fulfillment = serializers.SerializerMethodField()
    payment_history = serializers.SerializerMethodField()

    def get_job_reference(self, obj):
        j = obj.job_reference
        return {
            "code": obj.job_reference.code,
            "project_name": j.project_name,
            # "address_title": j.title,
            # "full_address": j.full_address,
            # "recipient_name": j.recipient_name,
            # "recipient_phone": j.recipient_phone,
        }

    def get_fulfillment(self, obj):
        if obj.fulfillment_type == "delivery":
            delivery = obj.fulfillment
            return {
                "type": delivery.type,
                "cost": delivery.cost,
                "date": delivery.date,
                "address": {
                    "title": delivery.title,
                    "street_address": delivery.street_address,
                    "suburb": delivery.suburb,
                    "state": delivery.state,
                    "postcode": delivery.postcode,
                    "distance_to_factory": delivery.distance_to_factory,
                    "recipient_name": delivery.recipient_name,
                    "recipient_phone": delivery.recipient_phone,
                    "full_address": delivery.full_address,
                },
                "method": {
                    "_dm_type": delivery._dm_type,
                    "_dm_name": delivery._dm_name,
                    "_dm_description": delivery._dm_description,
                    "_dm_base_cost": delivery._dm_base_cost,
                    "_dm_cost_per_kg": delivery._dm_cost_per_kg,
                    "_dm_cost_per_km": delivery._dm_cost_per_km,
                },
                "driver": {
                    "name": delivery.driver.name, 
                    "phone": delivery.driver.phone
                } if getattr(delivery, "driver", None) else None,
            }
        elif obj.fulfillment_type == "pickup":
            return {
                "type": obj.fulfillment_type,
                "date": obj.delivery_date,
            }

    def get_payment_history(self, obj):
        p = obj.payment_history
        return {
            "transaction_id": p.transaction_id,
            "method": p.method,
            "date": p.date,
            "amount": p.total_amount,
            "gst": p.gst_ratio,
            "flashings_cost": p.flashings_cost,
            "delivery_cost": p.delivery_cost,
        }

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "fulfillment_type",
            "job_reference",
            "flashings",
            "created_at",
            "fulfillment",
            "payment_history",
            "created_at",
        ]


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = "__all__"


class CartSerializer(serializers.ModelSerializer):

    flashings = StoredFlashingSerializer(
        many=True,
        required=True,
    )
    address = AddressSerializer(many=False, required=True)
    job_reference = JobReferenceSerializer(
        many=False, required=True, fields=["id", "code", "project_name"]
    )

    class Meta:
        model = Cart
        fields = [
            "client",
            "flashings",
            "delivery_type",
            "delivery_cost",
            "estimated_delivery_date",
            "address",
            "job_reference",
            "delivery_date",
            "total_amount",
        ]
