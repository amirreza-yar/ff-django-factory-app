from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q, F
import uuid
from datetime import timedelta

from factory.models import MaterialVariant
from .utils import (
    validate_nodes,
    calculate_total_girth,
    validate_material_snapshot,
    generate_six_digit_id,
    two_days_from_now,
)
from .tasks import trigger_async_geocode_distance

import math

User = get_user_model()


class Specification(models.Model):
    flashing = models.OneToOneField(
        "StoredFlashing", on_delete=models.CASCADE, related_name="specifications"
    )

    quantity = models.IntegerField()
    length = models.FloatField()

    @property
    def cost(self):
        try:
            mat_group = self.flashing.material.group
            total_girth = math.ceil(self.flashing.total_girth / 100.0)
            crush_num = int(self.flashing.start_crush_fold) + int(
                self.flashing.end_crush_fold
            )
            fold_num = len(self.flashing.nodes) - 2

            base_price = mat_group.base_price
            price_fold = mat_group.price_per_fold * fold_num
            price_girth = mat_group.price_per_100girth * total_girth
            price_crush = mat_group.price_per_crush_fold * crush_num

            c = base_price + price_fold + price_girth + price_crush

            print(
                "calculated prices: ",
                (base_price, mat_group.base_price, 1),
                (price_fold, mat_group.price_per_fold, fold_num),
                (price_girth, mat_group.price_per_100girth, total_girth),
                (price_crush, mat_group.price_per_crush_fold, crush_num),
                (c),
                sep="\n"
            )

            return float(c) * float(self.length / 1000) * float(self.quantity)
        except:
            return 0

    def __str__(self):
        return f"Spec {self.id} for Flashing {self.flashing.id}"


class StoredFlashing(models.Model):
    # TODO: The flashing id will be generated on frontend and will be indexed using it,
    #      so I think we need it here to temporary
    # flashing_id = models.CharField(max_length=10, unique=True, primary_key=True)
    client = models.ForeignKey(User, on_delete=models.PROTECT, related_name="flashings")

    material = models.ForeignKey(
        MaterialVariant, on_delete=models.PROTECT, related_name="ordered_flashings"
    )

    # Flashing data/nodes properties here
    start_crush_fold = models.BooleanField(default=False)
    end_crush_fold = models.BooleanField(default=False)
    color_side_dir = models.BooleanField(default=False)
    tapered = models.BooleanField(default=False)

    # Nodes or data
    nodes = models.JSONField(validators=[validate_nodes])

    @property
    def total_girth(self):
        if self.nodes:
            return calculate_total_girth(self.nodes)
        else:
            return None

    @property
    def total_cost(self):
        return sum(spec.cost for spec in self.specifications.all())

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_complete(self):
        required_fields = [
            "material",
            "nodes",
            "total_girth",
            "specifications",
        ]

        for field in required_fields:
            if getattr(self, field) in [None, "", []]:
                return False

        if not self.specifications.exists():
            return False

        try:
            validate_nodes(self.nodes)
        except Exception:
            return False

        return True

    def __str__(self):
        return f"Flashing {self.id} for client {self.client.email}"


class Cart(models.Model):
    client = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    flashings = models.ManyToManyField(StoredFlashing)

    class DeliveryTypeChoices(models.TextChoices):
        DELIVERY = "delivery", "Delivery"
        PICKUP = "pickup", "Pickup"

    delivery_type = models.CharField(
        max_length=20,
        choices=DeliveryTypeChoices.choices,
        default=DeliveryTypeChoices.DELIVERY,
        editable=False,
    )
    delivery_cost = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, editable=False
    )
    delivery_date = models.DateField(null=True)

    stripe_session_id = models.CharField(max_length=100, unique=True, null=True)

    @property
    def estimated_delivery_date(self):
        return two_days_from_now()

    address = models.ForeignKey("Address", on_delete=models.SET_NULL, null=True)

    @property
    def job_reference(self):
        if not self.address:
            return None
        return self.address.job_reference

    @property
    def flashings_cost(self):
        return sum(flash.total_cost for flash in self.flashings.all())

    @property
    def gst_ratio(self):
        return self.client.factory.gst_ratio

    @property
    def total_amount(self):
        return round((self.flashings_cost + float(self.delivery_cost)) * (self.gst_ratio + 1), 2)

    @property
    def is_complete(self):
        if not self.flashings.exists():
            return False

        if not self.address:
            return False

        if not self.delivery_date:
            return False

        if not self.job_reference:
            return False

        if self.flashings_cost <= 0:
            return False

        if not (0 <= self.gst_ratio <= 1):
            return False

        return True

    def clean(self):
        super().clean()
        incomplete = self.flashings.filter(is_complete=False)
        if incomplete.exists():
            self.flashings.remove(*incomplete)

    def __str__(self):
        return f"Cart for client {self.client_id}"


class Order(models.Model):
    id = models.CharField(primary_key=True, max_length=6, editable=False, unique=True)

    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="orders", editable=False
    )

    class OrderStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETE = "complete", "Complete"

    status = models.CharField(
        max_length=50,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        editable=False,
    )

    class DeliveryTypeChoices(models.TextChoices):
        DELIVERY = "delivery", "Delivery"
        PICKUP = "pickup", "Pickup"

    delivery_type = models.CharField(
        max_length=20,
        choices=DeliveryTypeChoices.choices,
        default=DeliveryTypeChoices.DELIVERY,
        editable=False,
    )
    delivery_cost = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, editable=False
    )
    delivery_date = models.DateField(editable=False)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_six_digit_id()
            while Order.objects.filter(id=self.id).exists():
                self.id = generate_six_digit_id()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.id} for client {self.client.email}"


class JobReference(models.Model):
    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="job_references"
    )

    code = models.PositiveIntegerField()
    project_name = models.CharField(max_length=50)

    class Meta:
        unique_together = ("client", "code")


class Address(models.Model):
    job_reference = models.ForeignKey(
        JobReference, on_delete=models.CASCADE, related_name="addresses"
    )

    class StateChoices(models.TextChoices):
        NSW = "NSW", "New South Wales"
        VIC = "VIC", "Victoria"
        QLD = "QLD", "Queensland"
        WA = "WA", "Western Australia"
        SA = "SA", "South Australia"
        TAS = "TAS", "Tasmania"
        ACT = "ACT", "Australian Capital Territory"
        NT = "NT", "Northern Territory"

    title = models.CharField(max_length=100)
    street_address = models.CharField(max_length=200)
    suburb = models.CharField(max_length=100)
    state = models.CharField(max_length=3, choices=StateChoices.choices)
    postcode = models.PositiveIntegerField()

    distance_to_factory = models.PositiveIntegerField(default=0)

    recipient_name = models.CharField(max_length=50)
    recipient_phone = models.CharField(max_length=50)

    @property
    def full_address(self):
        return f"{self.street_address}, {self.suburb}, {self.state} {self.postcode}, Australia"

    def save(self, *args, **kwargs):
        if self.pk is None:
            trigger_async_geocode_distance(self)

        super().save(*args, **kwargs)


class Template(models.Model):
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='templates')
    name = models.CharField(max_length=30)

    start_crush_fold = models.BooleanField(default=False)
    end_crush_fold = models.BooleanField(default=False)
    color_side_dir = models.BooleanField(default=False)
    tapered = models.BooleanField(default=False)

    nodes = models.JSONField(validators=[validate_nodes])

    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return f"Template {self.name} for client {self.client}"