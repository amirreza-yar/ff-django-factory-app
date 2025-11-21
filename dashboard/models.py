from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

from random import randint
import uuid

from factory.models import MaterialVariant
from .utils import validate_nodes, calculate_total_girth

User = get_user_model()

def generate_six_digit_id():
    return str(randint(100000, 999999))

class Specification(models.Model):
    id = models.CharField(max_length=10, primary_key=True)
    flashing = models.ForeignKey('StoredFlashing', on_delete=models.CASCADE, related_name='specifications')

    quantity = models.IntegerField()
    length = models.FloatField()
    cost = models.FloatField()

    def __str__(self):
        return f"Spec {self.id} for Flashing {self.flashing.flashing_id}"


class MaterialSnapshot(models.Model):
    original_material = models.ForeignKey(MaterialVariant, on_delete=models.PROTECT, related_name="ordered_flashings")
    # Snapshot of material on creation time
    # Something like Stainless Steel, type = thickness,
    # code/variant_label = SS304-08, thickness/variant_value = 0.8 [mm]
    class MaterialType(models.TextChoices):
        COLOR = "color", "Color"
        THICKNESS = "thickness", "Thickness"
    variant_type = models.CharField(max_length=20, choices=MaterialType.choices)
    name = models.CharField(max_length=50)
    variant_label = models.CharField(max_length=50)
    variant_value = models.CharField(max_length=50)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_fold = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_100girth = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_crush_fold = models.DecimalField(max_digits=10, decimal_places=2)
    sample_weight = models.DecimalField(max_digits=10, decimal_places=2)
    sample_weight_sq_meter = models.DecimalField(max_digits=5, decimal_places=2)

    def save(self, *args, **kwargs):
        # Create the material snapshot
        if self.pk is None:
            self.variant_type = self.original_material.group.material.variant_type
            self.name = self.original_material.group.material.name
            self.variant_label = self.original_material.label
            self.variant_value = self.original_material.value
            self.base_price = self.original_material.group.base_price
            self.price_per_fold = self.original_material.group.price_per_fold
            self.price_per_100girth = self.original_material.group.price_per_100girth
            self.price_per_crush_fold = self.original_material.group.price_per_crush_fold
            self.sample_weight = self.original_material.group.sample_weight
            self.sample_weight_sq_meter = self.original_material.group.sample_weight_sq_meter

        super().save(*args, **kwargs)

class StoredFlashing(models.Model):
    #TODO: The flashing id will be generated on frontend and will be indexed using it,
    #      so I think we need it here to temporary
    flashing_id = models.CharField(max_length=10, unique=True, primary_key=True)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='flashings')

    material = models.OneToOneField(MaterialSnapshot, on_delete=models.PROTECT, related_name='flashing')

    # Flashing data/nodes properties here    
    start_crush_fold = models.BooleanField(default=False)
    end_crush_fold = models.BooleanField(default=False)
    color_side_dir = models.BooleanField(default=False)
    tapered = models.BooleanField(default=False)

    # Nodes or data
    nodes = models.JSONField(validators=[validate_nodes], editable=False)
    total_girth_cached = models.FloatField(default=0)
    @property
    def total_girth(self):
        return self.total_girth_cached

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Calculate the total girth and save it
        if self.pk is None:
            self.total_girth_cached = calculate_total_girth(self.nodes)
        else:
            old = type(self).objects.filter(pk=self.pk).values("nodes").first()
            if old and old["nodes"] != self.nodes:
                self.total_girth_cached = calculate_total_girth(self.nodes)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Flashing {self.flashing_id} for Order {self.order.id}"


class Order(models.Model):
    id = models.CharField(
        primary_key=True,
        max_length=6,
        editable=False,
        unique=True
    )

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders", editable=False)

    class OrderStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    status = models.CharField(max_length=50, choices=OrderStatus.choices, default=OrderStatus.PENDING)

    class DeliveryTypeChoices(models.TextChoices):
        DELIVERY = 'delivery', 'Delivery'
        PICKUP = 'pickup', 'Pickup'
    delivery_type = models.CharField(max_length=20, choices=DeliveryTypeChoices.choices, default=DeliveryTypeChoices.DELIVERY)
    delivery_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    estimated_delivery_date = models.DateTimeField(editable=False)

    job_reference_code = models.PositiveIntegerField()
    job_reference_project_name = models.CharField(max_length=100)

    original_address = models.ForeignKey('JobReference', on_delete=models.PROTECT)
    address_title = models.CharField(max_length=100)
    address_streetAddress = models.CharField(max_length=200)
    address_suburb = models.CharField(max_length=100)
    address_state = models.CharField(max_length=100)
    address_postcode = models.PositiveIntegerField()

    recipient_name = models.CharField(max_length=50)
    recipient_phone = models.CharField(max_length=50)

    # For now lets use the 'flashing' which is foreign keyed to this order model
    # flashings_data = models.JSONField(editable=False)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    is_complete = models.BooleanField(default=False)


    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_six_digit_id()
            while Order.objects.filter(id=self.id).exists():
                self.id = generate_six_digit_id()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order num: {self.id}"


class PaymentHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payment_history')
    
    transaction_id = models.CharField(max_length=255, unique=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class PaymentMethod(models.TextChoices):
        CARD = 'card', 'Card'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        PAYPAL = 'paypal', 'PayPal'

    method = models.CharField(max_length=20, choices=PaymentMethod.choices)

    date = models.DateTimeField(default=timezone.now, editable=False)
    
    def __str__(self):
        return f"Payment {self.transaction_id} for Order {self.order.id}"


class JobReference(models.Model):
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_references')
    
    code = models.PositiveIntegerField(max_length=10)
    project_name = models.CharField(max_length=50)


class Address(models.Model):
    job_reference = models.ForeignKey(JobReference, on_delete=models.CASCADE, related_name='addresses')

    title = models.CharField(max_length=100)
    streetAddress = models.CharField(max_length=200)
    suburb = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postcode = models.PositiveIntegerField()

    recipient_name = models.CharField(max_length=50)
    recipient_phone = models.CharField(max_length=50)