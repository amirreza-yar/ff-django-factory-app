from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q, F
import uuid
from datetime import timedelta
from django.core.exceptions import ValidationError

from .utils import validate_nodes, calculate_total_girth, validate_material_snapshot, generate_six_digit_id, two_days_from_now
from factory.models import Factory
import math

User = get_user_model()

class Specification(models.Model):
    flashing = models.ForeignKey('StoredFlashing', on_delete=models.CASCADE, related_name='specifications')

    quantity = models.IntegerField()
    length = models.FloatField()

    @property
    def cost(self):
        try:
            mat_group = self.flashing.original_material.group
            total_girth = math.ceil(self.flashing.total_girth / 100.0)
            crush_num = int(self.flashing.start_crush_fold) + int(self.flashing.end_crush_fold)
            fold_num = len(self.flashing.nodes) - 2

            base_price = mat_group.base_price
            price_fold = mat_group.price_per_fold * fold_num
            price_girth = mat_group.price_per_100girth * total_girth
            price_crush = mat_group.price_per_crush_fold * crush_num

            c = base_price + price_fold + price_girth + price_crush

            # print(
            #     "calculated prices: ",
            #     (base_price, mat_group.base_price, 1),
            #     (price_fold, mat_group.price_per_fold, fold_num),
            #     (price_girth, mat_group.price_per_100girth, total_girth),
            #     (price_crush, mat_group.price_per_crush_fold, crush_num),
            #     (c),
            #     sep="\n"
            # )

            return float(c) * float(self.length / 1000) * float(self.quantity)
        except:
            return 0

    def __str__(self):
        return f"Spec {self.id} for Flashing {self.flashing.id}"


class StoredFlashing(models.Model):
    #TODO: The flashing id will be generated on frontend and will be indexed using it,
    #      so I think we need it here to temporary
    # flashing_id = models.CharField(max_length=10, unique=True, primary_key=True)
    order = models.ManyToManyField('Order', related_name='flashings')
    client = models.ForeignKey(User, on_delete=models.PROTECT, related_name='flashings')

    original_material = models.ForeignKey(
        'MaterialVariant',
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
        if self.nodes:
            return calculate_total_girth(self.nodes)
        else:
            return None

    @property
    def material_details(self):
        pass

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_complete(self):
        required_fields = [
            "original_material",
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

    def save(self, *args, **kwargs):
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
        
        # if self.order and not self.is_complete:
        #     self.order = None

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

    status = models.CharField(max_length=50, choices=OrderStatus.choices, default=OrderStatus.PENDING, editable=False)

    class DeliveryTypeChoices(models.TextChoices):
        DELIVERY = 'delivery', 'Delivery'
        PICKUP = 'pickup', 'Pickup'
    delivery_type = models.CharField(max_length=20, choices=DeliveryTypeChoices.choices, default=DeliveryTypeChoices.DELIVERY, editable=False)
    delivery_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0, editable=False)
    estimated_delivery_date = models.DateField(default=two_days_from_now, editable=False)

    original_address = models.ForeignKey('Address', on_delete=models.PROTECT, null=True)

    # For now lets use the 'flashing' which is foreign keyed to this order model
    # flashings_data = models.JSONField(editable=False)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    
    # @property
    # def flashings(self):
    #     return self.flashings
    
    @property
    def is_complete(self):
        return False

    def save(self, *args, **kwargs):
        # Generating 6-digits order id
        if not self.id:
            self.id = generate_six_digit_id()
            while Order.objects.filter(id=self.id).exists():
                self.id = generate_six_digit_id()

        # enforce that all flashings belong to the same client
        invalid_flashings = self.flashings.exclude(client=self.client)
        if invalid_flashings.exists():
            raise ValueError("All flashings must belong to the same client as the order")

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
    
    class Meta:
        unique_together = ('client', 'code')


class Address(models.Model):
    job_reference = models.ForeignKey(JobReference, on_delete=models.CASCADE, related_name='addresses')

    title = models.CharField(max_length=100)
    street_address = models.CharField(max_length=200)
    suburb = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postcode = models.PositiveIntegerField()

    recipient_name = models.CharField(max_length=50)
    recipient_phone = models.CharField(max_length=50)
    

class Staff(models.Model):
    """Factory staff/operators model"""

    # id = models.UUIDField(primary_key=True, default=uuid.uuid5, editable=False)
    factory = models.ForeignKey(Factory, on_delete=models.CASCADE, related_name="staff", editable=False)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="staff_profile", editable=False
    )

    # Personal info
    employee_id = models.CharField(max_length=50, unique=True, editable=False)

    # Employment details
    class StaffRole(models.TextChoices):
        OPERATOR = "operator", "Operator"
        SUPERVISOR = "supervisor", "Supervisor"
        MANAGER = "manager", "Manager"
        QA = "qa", "Quality Assurance"

    role = models.CharField(
        max_length=20, choices=StaffRole.choices, default=StaffRole.OPERATOR
    )

    class EmploymentStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        TERMINATED = "terminated", "Terminated"

    status = models.CharField(
        max_length=20, choices=EmploymentStatus.choices, default=EmploymentStatus.ACTIVE
    )

    @property
    def first_name(self):
        return self.user.first_name

    @property
    def last_name(self):
        return self.user.last_name

    @property
    def fullname(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def email(self):
        return self.user.email

    @property
    def factory_name(self):
        return self.factory.name

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.fullname}"

    class Meta:
        # ordering = ['last_name', 'first_name']
        unique_together = ["factory", "employee_id"]


class Material(models.Model):
    name = models.CharField(max_length=50, blank=False, null=False)
    factory = models.ForeignKey(
        Factory, on_delete=models.CASCADE, related_name="materials", editable=False
    )

    class VariantType(models.TextChoices):
        COLOR = "color", "Color"
        THICKNESS = "thickness", "Thickness"
    

    variant_type = models.CharField(max_length=20, choices=VariantType.choices, default=VariantType.COLOR)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def variants(self):
        return MaterialVariant.objects.filter(group__material=self)

    @property
    def variants_count(self):
        return self.variants.count()

    def clean(self):
        if self.pk and not self.variant_groups.exists():
            raise ValidationError("Material must have at least one variant group.")

    def __str__(self):
        return f"{self.name}"

    class Meta:
        unique_together = ["name"]


class MaterialGroup(models.Model):
    material = models.ForeignKey(
        Material, on_delete=models.CASCADE, related_name="groups", editable=False
    )

    name = models.CharField(max_length=50, default="Base Group")

    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_fold = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_100girth = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_crush_fold = models.DecimalField(max_digits=10, decimal_places=2)
    sample_weight = models.DecimalField(max_digits=10, decimal_places=2)
    sample_weight_sq_meter = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)

    # def calculate_weight(self, )

    def __str__(self):
        return f"{self.material.name} - Group #{self.id}"


class MaterialVariant(models.Model):
    group = models.ForeignKey(
        MaterialGroup, on_delete=models.CASCADE, related_name="variants", editable=False
    )

    label = models.CharField(max_length=100)
    value = models.CharField(max_length=100)

    def clean(self):
        if not self.pk and not self.group_id:
            raise ValidationError("Variant must belong to a group.")

    def __str__(self):
        return f"{self.group.material.name} - {self.label}"


class DeliveryMethod(models.Model):
    factory = models.ForeignKey(
        Factory,
        on_delete=models.CASCADE,
        related_name="delivery_methods",
        editable=False
    )

    class MethodType(models.TextChoices):
        FACTORY = "factory", "Factory Delivery"
        FREIGHT = "freight", "Freight"

    method_type = models.CharField(
        max_length=20, choices=MethodType.choices, editable=False
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    priority = models.IntegerField(default=1)
    
    base_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    cost_per_kg = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    cost_per_km = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    max_weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    max_distance_km = models.PositiveIntegerField()


    def estimate_delivery_days(self, *args):
        if self.method_type == 'factory':
            try:
                D_d, W_d = args
            except ValueError:
                raise ValueError("Factory delivery requires: D_d, W_d")

            D_ref = 1
            k = 0.1

            result = (D_d / self.max_distance_km) * (1 + k * (W_d / self.max_weight_kg)) * D_ref
            return max(math.ceil(result), 1)

        elif self.method_type == 'freight':
            try:
                (D_d,) = args
            except ValueError:
                raise ValueError("Freight delivery requires: D_d")

            result = D_d / self.max_distance_km * self.D_ref + self.extra_days
            return max(math.ceil(result), 1)

        else:
            raise ValueError(f"Unknown delivery method type: {self.method_type}")

    def save(self, *args, **kwargs):
        if hasattr(self, "METHOD_TYPE"):
            self.method_type = self.METHOD_TYPE

        # This means that the model isn't saved to the database yet
        if self._state.adding:
            # Get the maximum display_id value from the database
            last_priority = self.__class__.objects.all().aggregate(largest=models.Max('priority'))['largest']

            # aggregate can return None! Check it first.
            # If it isn't none, just use the last ID specified (which should be the greatest) and add one to it
            if last_priority is not None:
                self.priority = last_priority + 1

        super().save(*args, **kwargs)

    class Meta:
        ordering = ['name', "priority"]
        constraints = [
            models.UniqueConstraint(fields=['priority'], name='unique_priorities')
        ]

    def __str__(self):
        return self.name