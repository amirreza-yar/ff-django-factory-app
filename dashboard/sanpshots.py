from django.db import models
from django.utils import timezone
import uuid

from .utils import validate_nodes
from .models import Order

class SpecificationSnapshot(models.Model):
    flashing = models.ForeignKey(
        "StoredFlashingSnapshot", on_delete=models.CASCADE, related_name="specifications", editable=False
    )

    quantity = models.IntegerField(editable=False)
    length = models.FloatField()

    cost = models.FloatField()

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("SpecificationSnapshot is immutable and cannot be updated once created.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Spec snapshot {self.id} for Flashing snapshot {self.flashing.id}"

class MaterialSnapshot(models.Model):
    flashing = models.OneToOneField('StoredFlashingSnapshot', on_delete=models.CASCADE, related_name='material')

    class VariantType(models.TextChoices):
        COLOR = "color", "Color"
        THICKNESS = "thickness", "Thickness"
    variant_type = models.CharField(max_length=10, choices=VariantType.choices, default=VariantType.COLOR)

    name = models.CharField(max_length=50)
    variant_label = models.CharField(max_length=50)
    variant_value = models.CharField(max_length=50)
    base_price = models.FloatField()
    price_per_fold = models.FloatField()
    price_per_100girth = models.FloatField()
    price_per_crush_fold = models.FloatField()

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("MaterialSnapshot is immutable and cannot be updated once created.")
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Material snapshot {self.id} for Flashing snapshot {self.flashing.id}"

class StoredFlashingSnapshot(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="flashings")

    start_crush_fold = models.BooleanField(default=False)
    end_crush_fold = models.BooleanField(default=False)
    color_side_dir = models.BooleanField(default=False)
    tapered = models.BooleanField(default=False)

    nodes = models.JSONField(validators=[validate_nodes])

    total_girth = models.FloatField()

    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("StoredFlashingSnapshot is immutable and cannot be updated once created.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Flashing snapshot {self.id} for order {self.order}"

class JobReferenceSnapshot(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="job_reference")
    
    code = models.PositiveIntegerField()
    project_name = models.CharField(max_length=50)

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
    
    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("JobReferenceSnapshot is immutable and cannot be updated once created.")
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Job reference snapshot {self.id} for order {self.order}"

class PaymentSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="payment_history"
    )

    transaction_id = models.CharField(max_length=100, unique=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_session_id = models.CharField(max_length=100, unique=True)

    class PaymentMethod(models.TextChoices):
        VISA = "visa", "Visa"
        PAYPAL = "paypal", "PayPal"
        STRIPE = "stripe", "Stripe"

    method = models.CharField(max_length=20, choices=PaymentMethod.choices)

    date = models.DateTimeField(default=timezone.now, editable=False)
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = uuid.uuid4()

        if self.pk and self._state.adding is False:
            raise ValueError("PaymentSnapshot is immutable and cannot be updated once created.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment {self.id} for Order {self.order.id}"