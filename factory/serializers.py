from rest_framework import serializers
from .models import Factory, Staff, Material, MaterialVariant, MaterialGroup, DeliveryMethod


class StaffSerializer(serializers.ModelSerializer):

    role = serializers.CharField(read_only=True)
    employee_id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Staff
        fields = ["first_name", "last_name", "email", "employee_id", "role", "created_at"]


class DeliveryMethodSerializer(serializers.ModelSerializer):

    created_at = serializers.DateTimeField(read_only=True)


    class Meta:
        model = DeliveryMethod
        fields = [
            "id",
            "name",
            "method_type",
            "description",
            "is_active",
            "created_at",
            "updated_at",
            "priority",
            "base_cost",
            "cost_per_kg",
            "cost_per_km",
            "max_weight_kg",
            "max_distance_km",
        ]


class FactorySerializer(serializers.ModelSerializer):
    staff = StaffSerializer(many=True, read_only=True)

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
            "staff",
        ]
        
    # def update(self, instance, validated_data):
    #     print(validated_data, instance)


class MaterialVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialVariant
        fields = ['label', 'value']

class MaterialGroupSerializer(serializers.ModelSerializer):
    label_values = MaterialVariantSerializer(source='variants', many=True)

    class Meta:
        model = MaterialGroup
        fields = [
            'base_price', 
            'price_per_fold', 
            'price_per_100girth', 
            'price_per_crush_fold', 
            'sample_weight',
            'name',
            'label_values',
        ]

class MaterialSerializer(serializers.ModelSerializer):
    variants = serializers.ListField(write_only=True)  # accept nested groups/variants for create
    groups_detail = serializers.SerializerMethodField(read_only=True)  # for reading nested groups

    class Meta:
        model = Material
        fields = ['id', 'name', 'variant_type', 'variants', 'groups_detail']

    def get_groups_detail(self, obj):
        groups = obj.groups.all()
        return [
            {
                "name": g.name or "Default Group",
                "base_price": str(g.base_price),
                "price_per_fold": str(g.price_per_fold),
                "price_per_100girth": str(g.price_per_100girth),
                "price_per_crush_fold": str(g.price_per_crush_fold),
                "sample_weight": str(g.sample_weight),
                "label_values": [{"label": v.label, "value": v.value} for v in g.variants.all()]
            }
            for g in groups
        ]

    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
        factory = self.context.get('factory')
        material = Material.objects.create(factory=factory, **validated_data)

        for group_data in variants_data:
            group = MaterialGroup.objects.create(
                material=material,
                name=group_data.get('name', 'Default Group'),
                base_price=group_data.get('base_price', 0),
                price_per_fold=group_data.get('price_per_fold', 0),
                price_per_100girth=group_data.get('price_per_100girth', 0),
                price_per_crush_fold=group_data.get('price_per_crush_fold', 0),
                sample_weight=group_data.get('sample_weight', 0),
            )
            for variant in group_data.get('label_values', []):
                MaterialVariant.objects.create(
                    group=group,
                    label=variant.get('label', ''),
                    value=variant.get('value', '')
                )

        return material

    def update(self, instance, validated_data):
        variants_data = validated_data.pop('variants', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if variants_data:
            # Delete old groups and variants (or handle smart updating)
            instance.groups.all().delete()

            for group_data in variants_data:
                group = MaterialGroup.objects.create(
                    material=instance,
                    name=group_data.get('name', 'Default Group'),
                    base_price=group_data.get('base_price', 0),
                    price_per_fold=group_data.get('price_per_fold', 0),
                    price_per_100girth=group_data.get('price_per_100girth', 0),
                    price_per_crush_fold=group_data.get('price_per_crush_fold', 0),
                    sample_weight=group_data.get('sample_weight', 0),
                )
                for variant in group_data.get('label_values', []):
                    MaterialVariant.objects.create(
                        group=group,
                        label=variant.get('label', ''),
                        value=variant.get('value', '')
                    )

        return instance
