from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid
import math


User = get_user_model()

class StateChoices(models.TextChoices):
        NSW = "NSW", "New South Wales"
        VIC = "VIC", "Victoria"
        QLD = "QLD", "Queensland"
        WA = "WA", "Western Australia"
        SA = "SA", "South Australia"
        TAS = "TAS", "Tasmania"
        ACT = "ACT", "Australian Capital Territory"
        NT = "NT", "Northern Territory"

class Factory(models.Model):
    # General
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    # Contact information
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    description = models.TextField()

    street_address = models.CharField(max_length=200)
    suburb = models.CharField(max_length=100)
    state = models.CharField(max_length=3, choices=StateChoices.choices)
    postcode = models.PositiveIntegerField()

    @property
    def full_address(self):
        return f"{self.street_address}, {self.suburb}, {self.state} {self.postcode}, Australia"

    # Working hours
    working_hours_start = models.TimeField(blank=False, null=False)
    working_hours_end = models.TimeField(blank=False, null=False)
    
    gst_ratio = models.FloatField(default=0.1)

    # Status
    is_active = models.BooleanField(default=True)

    # TODO: NEED THE FOLLOWING FIELDS? REASON?
    # working_timezone = models.CharField(max_length=50, blank=True, null=True)

    # auto_assign_orders = models.BooleanField(default=True, help_text="Auto-assign orders to operators")
    # require_qa_approval = models.BooleanField(default=True, help_text="Require QA approval before dispatch")

    # class Priority(models.TextChoices):
    #     LOW = 'low', 'Low'
    #     MEDIUM = 'medium', 'Medium'
    #     HIGH = 'high', 'High'
    #     URGENT = 'urgent', 'Urgent'

    # default_priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)

    # notify_order_assigned = models.BooleanField(default=True)
    # notify_status_changes = models.BooleanField(default=True)
    # notify_qa_failures = models.BooleanField(default=True)
    # notify_deadlines = models.BooleanField(default=True)

    # Capacity settings
    max_concurrent_orders = models.PositiveIntegerField(default=50)
    daily_order_limit = models.PositiveIntegerField(default=100)

    # weekly off days: 0=Monday ... 6=Sunday
    weekly_off_days = models.JSONField(default=list, blank=True, null=True)

    # specific dates the factory is closed
    specific_off_days = models.JSONField(default=list, blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["is_active"]),
        ]


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
    

    variant_type = models.CharField(max_length=10, choices=VariantType.choices, default=VariantType.COLOR)

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


    def __str__(self):
        return f"{self.material.name} - Group #{self.id}"


class MaterialVariant(models.Model):
    group = models.ForeignKey(
        MaterialGroup, on_delete=models.CASCADE, related_name="variants", editable=False
    )

    label = models.CharField(max_length=100)
    value = models.CharField(max_length=100)

    def calculate_weight(self, girth, length):
        sample = float(self.group.sample_weight) / float(self.group.sample_weight_sq_meter)

        return sample * girth * length / 1000000

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

            result = (D_d / float(self.max_distance_km)) * (1 + k * (W_d / float(self.max_weight_kg))) * D_ref
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






# TODO: WHAT IS THIS??
# class ProductionLine(models.Model):
#     """Production line model"""

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     factory = models.ForeignKey(Factory, on_delete=models.CASCADE, related_name='production_lines')

#     line_id = models.CharField(max_length=50)
#     name = models.CharField(max_length=255)
#     description = models.TextField(blank=True, null=True)

#     # Capacity and capabilities
#     max_concurrent_orders = models.PositiveIntegerField(default=1)
#     supported_materials = models.JSONField(default=list, help_text="List of supported material types")

#     # Status
#     is_active = models.BooleanField(default=True)

#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.name} ({self.line_id})"

#     class Meta:
#         ordering = ['name']
#         unique_together = ['factory', 'line_id']


# class OrderAssignment(models.Model):
#     """Order assignment to factory/production line"""

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

#     # Import Order from dashboard app
#     order_id = models.UUIDField()  # Reference to dashboard.Order

#     factory = models.ForeignKey(Factory, on_delete=models.CASCADE, related_name='order_assignments')
#     production_line = models.ForeignKey(ProductionLine, on_delete=models.SET_NULL, blank=True, null=True, related_name='order_assignments')
#     assigned_staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, blank=True, null=True, related_name='order_assignments')

#     # Assignment details
#     assigned_at = models.DateTimeField(default=timezone.now)
#     assigned_by_id = models.UUIDField()  # Reference to tempBackend.User

#     # Priority
#     class Priority(models.TextChoices):
#         LOW = 'low', 'Low'
#         MEDIUM = 'medium', 'Medium'
#         HIGH = 'high', 'High'
#         URGENT = 'urgent', 'Urgent'

#     priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)

#     # Status tracking
#     class AssignmentStatus(models.TextChoices):
#         ASSIGNED = 'assigned', 'Assigned'
#         IN_PROGRESS = 'in_progress', 'In Progress'
#         QA = 'qa', 'Quality Assurance'
#         READY = 'ready', 'Ready for Dispatch'
#         COMPLETED = 'completed', 'Completed'

#     status = models.CharField(
#         max_length=20,
#         choices=AssignmentStatus.choices,
#         default=AssignmentStatus.ASSIGNED
#     )

#     # Progress tracking
#     progress_percentage = models.PositiveIntegerField(default=0)
#     estimated_completion = models.DateTimeField(blank=True, null=True)
#     actual_completion = models.DateTimeField(blank=True, null=True)

#     # Quality control
#     qa_passed = models.BooleanField(default=False)
#     qa_notes = models.TextField(blank=True, null=True)
#     qa_staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, blank=True, null=True, related_name='qa_assignments')

#     # Additional data stored as JSON
#     assignment_data = models.JSONField(default=dict, blank=True)

#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"Assignment for Order {self.order_id}"

#     class Meta:
#         ordering = ['-assigned_at']
#         indexes = [
#             models.Index(fields=['order_id']),
#             models.Index(fields=['factory']),
#             models.Index(fields=['status']),
#             models.Index(fields=['priority']),
#         ]


# class FactoryAnalytics(models.Model):
#     """Factory performance analytics"""

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     factory = models.ForeignKey(Factory, on_delete=models.CASCADE, related_name='analytics')

#     # Date range
#     date = models.DateField()
#     period = models.CharField(max_length=20, help_text="'daily', 'weekly', 'monthly'")

#     # Performance metrics
#     orders_received = models.PositiveIntegerField(default=0)
#     orders_completed = models.PositiveIntegerField(default=0)
#     orders_on_time = models.PositiveIntegerField(default=0)

#     # Quality metrics
#     qa_pass_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage
#     defect_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)   # Percentage

#     # Financial metrics
#     revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
#     costs = models.DecimalField(max_digits=12, decimal_places=2, default=0)

#     # Utilization metrics
#     production_line_utilization = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage
#     staff_utilization = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage

#     # Additional metrics stored as JSON
#     custom_metrics = models.JSONField(default=dict, blank=True)

#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.factory.name} - {self.date} ({self.period})"

#     class Meta:
#         ordering = ['-date']
#         unique_together = ['factory', 'date', 'period']
#         indexes = [
#             models.Index(fields=['factory', 'date']),
#             models.Index(fields=['period']),
#         ]


# class AdjustmentRequest(models.Model):
#     """Order adjustment request model"""

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     request_id = models.CharField(max_length=50, unique=True)

#     # Relationships
#     order_id = models.UUIDField()  # Reference to dashboard.Order
#     factory = models.ForeignKey(Factory, on_delete=models.CASCADE, related_name='adjustment_requests')

#     # Request details
#     requested_by_id = models.UUIDField()  # Reference to tempBackend.User
#     reason = models.TextField()
#     requested_changes = models.JSONField()  # Products/items being replaced

#     # Status and priority
#     class RequestStatus(models.TextChoices):
#         PENDING = 'pending', 'Pending'
#         APPROVED = 'approved', 'Approved'
#         REJECTED = 'rejected', 'Rejected'
#         COMPLETED = 'completed', 'Completed'

#     status = models.CharField(
#         max_length=20,
#         choices=RequestStatus.choices,
#         default=RequestStatus.PENDING
#     )

#     class Priority(models.TextChoices):
#         LOW = 'low', 'Low'
#         MEDIUM = 'medium', 'Medium'
#         HIGH = 'high', 'High'
#         URGENT = 'urgent', 'Urgent'

#     priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)

#     # Response
#     response = models.TextField(blank=True, null=True)
#     responded_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, blank=True, null=True, related_name='adjustment_responses')
#     responded_at = models.DateTimeField(blank=True, null=True)

#     # Attachments (file URLs/paths stored as JSON)
#     attachments = models.JSONField(default=list, blank=True)

#     # Additional notes
#     notes = models.TextField(blank=True, null=True)

#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"Replacement Request {self.request_id}"

#     class Meta:
#         ordering = ['-created_at']
#         indexes = [
#             models.Index(fields=['order_id']),
#             models.Index(fields=['factory']),
#             models.Index(fields=['status']),
#             models.Index(fields=['priority']),
#             models.Index(fields=['created_at']),
#         ]


# class Material(models.Model):
#     """Material definition model"""

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     factory = models.ForeignKey(Factory, on_delete=models.CASCADE, related_name='factory_materials')

#     # Basic material info
#     name = models.CharField(max_length=100)
#     material_id = models.CharField(max_length=50, unique=True)

#     # Material type
#     class MaterialType(models.TextChoices):
#         PLASTIC = 'plastic', 'Plastic'
#         METAL = 'metal', 'Metal'
#         WOOD = 'wood', 'Wood'
#         COMPOSITE = 'composite', 'Composite'
#         OTHER = 'other', 'Other'

#     material_type = models.CharField(max_length=20, choices=MaterialType.choices)

#     # Base pricing (for cost calculations)
#     base_cost = models.DecimalField(max_digits=8, decimal_places=2, help_text="Base cost per unit")
#     cost_per_fold = models.DecimalField(max_digits=8, decimal_places=2, default=0)
#     squash_fold_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
#     cost_per_100mm_girth = models.DecimalField(max_digits=8, decimal_places=2, default=0)
#     cost_per_1m_length = models.DecimalField(max_digits=8, decimal_places=2, default=0)

#     # Variants (colors, thicknesses, etc.)
#     variants = models.JSONField(default=list, help_text="List of material variants")

#     # Status
#     is_active = models.BooleanField(default=True)

#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.name} ({self.material_id})"

#     class Meta:
#         ordering = ['name']
#         unique_together = ['factory', 'material_id']


# class PaymentMethod(models.Model):
#     """Payment method configuration"""

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     factory = models.ForeignKey(Factory, on_delete=models.CASCADE, related_name='payment_methods')

#     class PaymentType(models.TextChoices):
#         CREDIT_CARD = 'credit_card', 'Credit Card'
#         DEBIT_CARD = 'debit_card', 'Debit Card'
#         BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
#         PAYPAL = 'paypal', 'PayPal'
#         STRIPE = 'stripe', 'Stripe'
#         CASH = 'cash', 'Cash'

#     payment_type = models.CharField(max_length=20, choices=PaymentType.choices)
#     name = models.CharField(max_length=100)
#     description = models.TextField(blank=True, null=True)

#     # Configuration (API keys, settings, etc.)
#     config = models.JSONField(default=dict, blank=True)

#     # Processing fees
#     processing_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
#     processing_fee_fixed = models.DecimalField(max_digits=6, decimal_places=2, default=0)

#     # Status
#     is_active = models.BooleanField(default=True)

#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.name} ({self.payment_type})"

#     class Meta:
#         ordering = ['name']
#         unique_together = ['factory', 'payment_type', 'name']


# class DeliveryMethod(models.Model):
#     """Delivery method configuration"""

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     factory = models.ForeignKey(Factory, on_delete=models.CASCADE, related_name='delivery_methods')

#     class DeliveryType(models.TextChoices):
#         PICKUP = 'pickup', 'Pickup'
#         LOCAL_DELIVERY = 'local_delivery', 'Local Delivery'
#         EXPRESS_DELIVERY = 'express_delivery', 'Express Delivery'
#         STANDARD_SHIPPING = 'standard_shipping', 'Standard Shipping'
#         INTERNATIONAL = 'international', 'International'

#     delivery_type = models.CharField(max_length=20, choices=DeliveryType.choices)
#     name = models.CharField(max_length=100)
#     description = models.TextField(blank=True, null=True)

#     # Cost calculation
#     base_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
#     cost_per_kg = models.DecimalField(max_digits=6, decimal_places=2, default=0)
#     cost_per_km = models.DecimalField(max_digits=6, decimal_places=2, default=0)

#     # Delivery constraints
#     max_weight_kg = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
#     max_distance_km = models.PositiveIntegerField(blank=True, null=True)
#     estimated_delivery_days = models.PositiveIntegerField(blank=True, null=True)

#     # Service areas (postal codes, cities, etc.)
#     service_areas = models.JSONField(default=list, blank=True)

#     # Status
#     is_active = models.BooleanField(default=True)

#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.name} ({self.delivery_type})"

#     class Meta:
#         ordering = ['name']
#         unique_together = ['factory', 'delivery_type', 'name']


# class CustomerStats(models.Model):
#     """Customer statistics for factory dashboard"""

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     factory = models.ForeignKey(Factory, on_delete=models.CASCADE, related_name='customer_stats')

#     # Customer reference
#     customer_id = models.UUIDField()  # Reference to tempBackend.User

#     # Statistics
#     total_orders = models.PositiveIntegerField(default=0)
#     total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
#     average_spent_per_order = models.DecimalField(max_digits=10, decimal_places=2, default=0)

#     # Recent activity
#     last_order_date = models.DateTimeField(blank=True, null=True)
#     last_order_id = models.UUIDField(blank=True, null=True)

#     # Customer status
#     class CustomerStatus(models.TextChoices):
#         ACTIVE = 'active', 'Active'
#         INACTIVE = 'inactive', 'Inactive'
#         VIP = 'vip', 'VIP'

#     status = models.CharField(max_length=10, choices=CustomerStatus.choices, default=CustomerStatus.ACTIVE)

#     # Additional data
#     customer_data = models.JSONField(default=dict, blank=True)  # Cached customer info

#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"Customer stats for {self.customer_id}"

#     class Meta:
#         unique_together = ['factory', 'customer_id']
#         indexes = [
#             models.Index(fields=['factory', 'total_spent']),
#             models.Index(fields=['factory', 'last_order_date']),
#             models.Index(fields=['status']),
#         ]
