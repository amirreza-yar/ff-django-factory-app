# factory/management/commands/create_demo_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from factory.models import Factory, Staff, Material, MaterialGroup, MaterialVariant, DeliveryMethod
from django.utils import timezone
import decimal

class Command(BaseCommand):
    help = "Create demo factory, staff, materials, and delivery methods"

    def handle(self, *args, **options):
        # -----------------------------
        # 1. Create Factory
        # -----------------------------
        factory, created = Factory.objects.get_or_create(
            name="Demo Factory",
            defaults={
                'email': 'demo@example.com',
                'phone': '1234567890',
                'address': '123 Demo Street',
                'description': 'This is a demo factory',
                'working_hours_start': '08:00',
                'working_hours_end': '17:00',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created Factory: {factory.name}"))
        else:
            self.stdout.write(self.style.WARNING(f"Factory already exists: {factory.name}"))

        # -----------------------------
        # 2. Create Staff
        # -----------------------------
        staff_users = [
            {'username': 'alice', 'email': 'alice@example.com', 'fullname': 'Alice Smith'},
            {'username': 'bob', 'email': 'bob@example.com', 'fullname': 'Bob Johnson'},
            {'username': 'charlie', 'email': 'charlie@example.com', 'fullname': 'Charlie Brown'},
        ]
        for idx, udata in enumerate(staff_users, start=1):
            user, _ = User.objects.get_or_create(username=udata['username'], defaults={
                'email': udata['email'],
                'first_name': udata['fullname'].split()[0],
                'last_name': udata['fullname'].split()[1]
            })
            Staff.objects.get_or_create(factory=factory, user=user, employee_id=f"EMP{idx:03}")

        self.stdout.write(self.style.SUCCESS("Staff created."))

        # -----------------------------
        # 3. Create Materials, Groups, Variants
        # -----------------------------
        materials_data = ['Steel', 'Aluminium', 'Copper', 'Galvanized Steel']
        for material_name in materials_data:
            material, _ = Material.objects.get_or_create(factory=factory, name=material_name, variant_type='thickness')
            group, _ = MaterialGroup.objects.get_or_create(
                material=material,
                defaults={
                    'base_price': decimal.Decimal('100.00'),
                    'price_per_fold': decimal.Decimal('5.00'),
                    'price_per_100girth': decimal.Decimal('2.00'),
                    'price_per_crush_fold': decimal.Decimal('1.50'),
                    'sample_weight': decimal.Decimal('10.0')
                }
            )
            for i in range(1, 6):
                MaterialVariant.objects.get_or_create(
                    group=group,
                    label=f"{material_name} Variant {i}",
                    value=f"V{i}"
                )

        self.stdout.write(self.style.SUCCESS("Materials, groups, and variants created."))

        # -----------------------------
        # 4. Create Delivery Methods
        # -----------------------------
        # PickupMethod.objects.get_or_create(factory=factory, name="Factory Pickup")

        DeliveryMethod.objects.get_or_create(
            factory=factory,
            method_type='freight',
            name="Rail Freight",
            max_weight_kg=50000,
            max_distance_km=10000
        )

        DeliveryMethod.objects.get_or_create(
            factory=factory,
            method_type='factory',
            name="UTE",
            max_weight_kg=500,
            max_distance_km=200,
            base_cost=decimal.Decimal('50.00'),
            cost_per_kg=decimal.Decimal('2.00'),
            cost_per_km=decimal.Decimal('1.50')
        )

        DeliveryMethod.objects.get_or_create(
            factory=factory,
            method_type='factory',
            name="Rigid Truck",
            max_weight_kg=2000,
            max_distance_km=500,
            base_cost=decimal.Decimal('100.00'),
            cost_per_kg=decimal.Decimal('1.50'),
            cost_per_km=decimal.Decimal('1.00')
        )

        DeliveryMethod.objects.get_or_create(
            factory=factory,
            method_type='factory',
            name="Van",
            max_weight_kg=1000,
            max_distance_km=300,
            base_cost=decimal.Decimal('70.00'),
            cost_per_kg=decimal.Decimal('2.00'),
            cost_per_km=decimal.Decimal('1.25')
        )

        self.stdout.write(self.style.SUCCESS("Delivery methods created."))
        self.stdout.write(self.style.SUCCESS("Demo data creation complete!"))
