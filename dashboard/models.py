from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid

from factory.models import MaterialVariant
from .utils import validate_nodes, calculate_total_girth, validate_material_snapshot, generate_six_digit_id

import math

User = get_user_model()

class Specification(models.Model):
    flashing = models.ForeignKey('StoredFlashing', on_delete=models.CASCADE, related_name='specifications')

    quantity = models.IntegerField()
    length = models.FloatField()
    
    @property
    def cost(self):
        c = 0

        total_girth = self.flashing.total_girth

        print("\n\ntotal girth ceil\n", math.ceil(total_girth))
        
        mat_group = self.flashing.original_material.group
        base_price = mat_group.base_price
        price_per_fold = mat_group.price_per_fold
        price_per_100girth = mat_group.price_per_100girth
        price_per_crush_fold = mat_group.price_per_crush_fold
        
        
        return c
    
    

    def __str__(self):
        return f"Spec {self.id} for Flashing {self.flashing.flashing_id}"


class StoredFlashing(models.Model):
    #TODO: The flashing id will be generated on frontend and will be indexed using it,
    #      so I think we need it here to temporary
    # flashing_id = models.CharField(max_length=10, unique=True, primary_key=True)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='flashings', null=True)
    client = models.ForeignKey(User, on_delete=models.PROTECT, related_name='flashings')

    original_material = models.ForeignKey(
        MaterialVariant,
        on_delete=models.PROTECT,
        related_name="ordered_flashings"
    )

    material_details = models.JSONField(
        validators=[validate_material_snapshot],
        null=True,
        blank=True
    )

    # Flashing data/nodes properties here    
    start_crush_fold = models.BooleanField(default=False)
    end_crush_fold = models.BooleanField(default=False)
    color_side_dir = models.BooleanField(default=False)
    tapered = models.BooleanField(default=False)

    # Nodes or data
    nodes = models.JSONField(validators=[validate_nodes], blank=True, null=True)
    total_girth_cached = models.FloatField(default=0)

    @property
    def total_girth(self):
        return self.total_girth_cached
    
    @property
    def material_details(self):
        pass

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):

        print("\nStored flashing saved or updated...\n")
        
        # if self.pk is None:
        #     print("\nrefereshing Stored flashing material_details snapshot...\n")
        #     self.material_details = self.make_snapshot()
        # else:
        #     # The snapshot updates here (if the material_details have changed)
        #     pass

        if self.pk is None and self.nodes:
            self.total_girth_cached = calculate_total_girth(self.nodes)
        else:
            old = type(self).objects.filter(pk=self.pk).values("nodes").first()
            if old and old["nodes"] != self.nodes:
                self.total_girth_cached = calculate_total_girth(self.nodes)

        super().save(*args, **kwargs)
        
    def make_snapshot(self):
        m = self.original_material
        g = m.group

        return {
            "variant_type": g.material.variant_type,
            "name": g.material.name,
            "variant_label": m.label,
            "variant_value": m.value,
            "base_price": float(g.base_price),
            "price_per_fold": float(g.price_per_fold),
            "price_per_100girth": float(g.price_per_100girth),
            "price_per_crush_fold": float(g.price_per_crush_fold),
            "sample_weight": float(g.sample_weight),
            "sample_weight_sq_meter": float(g.sample_weight_sq_meter),
        }

    def refresh_material_snapshot(self):
        new_snapshot = self.make_snapshot()

        if self.material_snapshot != new_snapshot:
            self.material_snapshot = new_snapshot
            self.save(update_fields=["material_snapshot", "updated_at"])
            return True

        return False

    def __str__(self):
        return f"Flashing {self.id} for Order {self.order}"


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
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment_history')

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