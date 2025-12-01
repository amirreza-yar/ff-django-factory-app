from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
import uuid

from .utils import validate_nodes, generate_six_digit_id, AustraliaStateChoices
from .models import Order


class SpecificationSnapshot(models.Model):
    flashing = models.ForeignKey(
        "StoredFlashingSnapshot",
        on_delete=models.CASCADE,
        related_name="specifications",
        editable=False,
    )

    quantity = models.IntegerField(editable=False)
    length = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=10, decimal_places=2)

    weight = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError(
                "SpecificationSnapshot is immutable and cannot be updated once created."
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Spec snapshot {self.id} for Flashing snapshot {self.flashing.id}"


class MaterialSnapshot(models.Model):
    flashing = models.OneToOneField(
        "StoredFlashingSnapshot", on_delete=models.CASCADE, related_name="material"
    )

    class VariantType(models.TextChoices):
        COLOR = "color", "Color"
        THICKNESS = "thickness", "Thickness"

    variant_type = models.CharField(
        max_length=10, choices=VariantType.choices, default=VariantType.COLOR
    )

    name = models.CharField(max_length=50)
    variant_label = models.CharField(max_length=50)
    variant_value = models.CharField(max_length=50)
    base_price = models.FloatField()
    price_per_fold = models.FloatField()
    price_per_100girth = models.FloatField()
    price_per_crush_fold = models.FloatField()
    sample_weight = models.DecimalField(max_digits=10, decimal_places=2)
    sample_weight_sq_meter = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.0
    )

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError(
                "MaterialSnapshot is immutable and cannot be updated once created."
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Material snapshot {self.id} for Flashing snapshot {self.flashing.id}"


class StoredFlashingSnapshot(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="flashings")
    
    code = models.CharField(max_length=50, editable=False)
    position = models.CharField(max_length=50, editable=False, null=True)

    start_crush_fold = models.BooleanField()
    end_crush_fold = models.BooleanField()
    color_side_dir = models.BooleanField()
    tapered = models.BooleanField()

    nodes = models.JSONField(validators=[validate_nodes])

    total_girth = models.FloatField()

    @cached_property
    def total_cost(self):
        return round(sum(spec.cost for spec in self.specifications.all()), 2)

    @cached_property
    def total_weight(self):
        return round(sum(spec.weight for spec in self.specifications.all()), 2)

    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError(
                "StoredFlashingSnapshot is immutable and cannot be updated once created."
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Flashing snapshot {self.id} for order {self.order}"


class JobReferenceSnapshot(models.Model):
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="job_reference"
    )

    code = models.PositiveIntegerField()
    project_name = models.CharField(max_length=50)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError(
                "JobReferenceSnapshot is immutable and cannot be updated once created."
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Job reference snapshot {self.id} for order {self.order}"


class PaymentSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="payment_history"
    )

    transaction_id = models.CharField(max_length=100, unique=True)
    stripe_session_id = models.CharField(max_length=100, unique=True)

    class PaymentMethod(models.TextChoices):
        VISA = "visa", "Visa"
        PAYPAL = "paypal", "PayPal"
        STRIPE = "stripe", "Stripe"

    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    date = models.DateTimeField(default=timezone.now, editable=False)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    gst_ratio = models.DecimalField(max_digits=3, decimal_places=2)

    @cached_property
    def flashings_cost(self):
        return round(sum(flash.total_cost for flash in self.order.flashings.all()), 2)

    @cached_property
    def delivery_cost(self):
        fulfill = self.order.fulfillment
        if fulfill.type == "delivery":
            return fulfill.cost
        else:
            return None

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = uuid.uuid4()

        if self.pk and self._state.adding is False:
            raise ValueError(
                "PaymentSnapshot is immutable and cannot be updated once created."
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment {self.id} for Order {self.order.id}"


class DeliveryInfoSnapshot(models.Model):
    id = models.CharField(primary_key=True, max_length=6, editable=False, unique=True)
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="delivery"
    )

    @cached_property
    def type(self):
        return "delivery"

    cost = models.DecimalField(
        max_digits=8, decimal_places=2, editable=False
    )

    date = models.DateField(editable=False, null=True)

    #! Address Info
    title = models.CharField(max_length=100)
    street_address = models.CharField(max_length=200)
    suburb = models.CharField(max_length=100)
    state = models.CharField(max_length=3, choices=AustraliaStateChoices.choices)
    postcode = models.PositiveIntegerField()

    distance_to_factory = models.PositiveIntegerField()

    recipient_name = models.CharField(max_length=50)
    recipient_phone = models.CharField(max_length=50)

    @cached_property
    def full_address(self):
        return f"{self.street_address}, {self.suburb}, {self.state} {self.postcode}, Australia"


    #! Delivery method Info
    _dm_type = models.CharField(max_length=20, editable=False)

    _dm_name = models.CharField(max_length=100)
    _dm_description = models.TextField(blank=True, null=True, editable=False)

    _dm_base_cost = models.DecimalField(max_digits=8, decimal_places=2, editable=False)
    _dm_cost_per_kg = models.DecimalField(max_digits=6, decimal_places=2, editable=False)
    _dm_cost_per_km = models.DecimalField(max_digits=6, decimal_places=2, editable=False)

    # max_weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    # max_distance_km = models.PositiveIntegerField()

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_six_digit_id()
            while Order.objects.filter(id=self.id).exists():
                self.id = generate_six_digit_id()

        else:
            raise ValueError(
                "DeliveryInfoSnapshot is immutable and cannot be updated once created."
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Delivery info snapshot {self.id} for order {self.order}"


class DriverInfoSnapshot(models.Model):
    id = models.CharField(primary_key=True, max_length=6, editable=False, unique=True)
    delivery_info = models.OneToOneField(
        DeliveryInfoSnapshot, on_delete=models.CASCADE, related_name="driver"
    )

    name = models.CharField(max_length=50)
    phone = models.PositiveIntegerField()

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_six_digit_id()
            while Order.objects.filter(id=self.id).exists():
                self.id = generate_six_digit_id()

        if self.id:
            raise ValueError(
                "DriverInfoSnapshot is immutable and cannot be updated once created."
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Delivery info snapshot {self.id} for delivery {self.delivery_info}"


class PickupInfoSnapshot(models.Model):
    id = models.CharField(primary_key=True, max_length=6, editable=False, unique=True)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="pickup")

    @cached_property
    def type(self):
        return "pickup"

    date = models.DateField(editable=False, null=True)

    # TODO: What should the pickup address be?
    @cached_property
    def factory_address(self):
        return self.order.user.factory.full_address

    # TODO: What should the pickup delivery time be? For example from 9:00 to 18:00 maybe?
    @cached_property
    def factory_work_desc(self):
        start = self.order.user.factory.working_hours_start
        end = self.order.user.factory.working_hours_end

        start_str = start.strftime("%-I:%M %p")
        end_str = end.strftime("%-I:%M %p")

        return f"Open: {start_str} – {end_str}"

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_six_digit_id()
            while Order.objects.filter(id=self.id).exists():
                self.id = generate_six_digit_id()

        super().save(*args, **kwargs)
