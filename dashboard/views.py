from django.shortcuts import render
from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from datetime import datetime

from .serializers import (
    FactorySerializer,
    MaterialSerializer,
    StoredFlashingSerializer,
    AddressSerializer,
    JobReferenceSerializer,
    OrderSerializer,
    CartSerializer,
    StoredFlashing,
    Address,
    TemplateSerializer,
    NewJobReferenceSerializer,
    UserSerializer
)
from .drafts import JobReferenceDraft
from .models import Cart, Order
from .sanpshots import (
    StoredFlashingSnapshot,
    MaterialSnapshot,
    SpecificationSnapshot,
    JobReferenceSnapshot,
    PaymentSnapshot,
)
from .utils import create_stripe_session, get_stripe_session_payment_intent


class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserFactoryView(generics.RetrieveAPIView):
    serializer_class = FactorySerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ["get", "options"]

    def get_object(self):
        return self.request.user.factory


class MaterialsView(generics.ListAPIView):
    serializer_class = MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ["get", "options"]

    def get_queryset(self):
        return self.request.user.factory.materials.all()


class StoredFlashingView(viewsets.ModelViewSet):
    serializer_class = StoredFlashingSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ["get", "post", "patch", "options"]

    def get_queryset(self):
        return self.request.user.flashings.all()

    def perform_create(self, serializer):
        serializer.save(client_id=self.request.user.id)


class JobReferenceView(viewsets.ModelViewSet):
    serializer_class = JobReferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ["get", "patch", "delete", "options"]

    def get_queryset(self):
        return self.request.user.job_references.all()

    def perform_create(self, serializer):
        serializer.save(client_id=self.request.user.id)

    @action(detail=False, methods=["patch", "get"], url_path="new")
    def new(self, request):
        user = request.user

        draft, _ = JobReferenceDraft.objects.get_or_create(client=user)

        serializer = NewJobReferenceSerializer(
            draft, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)


class NewJobReferenceView(viewsets.ModelViewSet):
    serializer_class = NewJobReferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names=["patch", "options"]

    def get_queryset(self):
        return self.request.user.draf_job_reference


class AddressView(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ["get", "post", "patch", "options"]

    def get_queryset(self):
        job_ref_id = self.kwargs.get("job_ref_pk")
        return self.request.user.job_references.get(id=job_ref_id).addresses.all()

    def perform_create(self, serializer):
        serializer.save(job_reference_id=self.kwargs["job_ref_pk"])


class OrderView(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ["get", "post", "patch", "options"]

    def get_queryset(self):
        return self.request.user.orders.all()

    def perform_create(self, serializer):
        serializer.save(client_id=self.request.user.id)


class TemplateView(viewsets.ModelViewSet):
    serializer_class = TemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ["get", "post", "options", "patch"]
    
    def get_queryset(self):
        return self.request.user.templates.all()

    def perform_create(self, serializer):
        serializer.save(client_id=self.request.user.id)


class CartView(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """
        Retrieve the authenticated user's cart
        """
        cart = request.user.cart
        serializer = CartSerializer(cart, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="remove-flashing")
    def remove_flashing(self, request):

        flashing_id = request.data.get("flashing_id")
        if not flashing_id:
            return Response({"error": "flashing_id is required"}, status=400)

        try:
            flashing = StoredFlashing.objects.get(id=flashing_id, client=request.user)
        except StoredFlashing.DoesNotExist:
            return Response({"error": "Flashing not found"}, status=404)

        cart = request.user.cart
        cart.flashings.remove(flashing)
        cart.save()
        return Response({"success": f"Flashing {flashing_id} removed from cart"})

    @action(detail=False, methods=["post"], url_path="set-address")
    def add_address(self, request):
        address_id = request.data.get("address_id")
        if not address_id:
            return Response({"error": "address_id is required"}, status=400)

        try:
            address = Address.objects.get(
                id=address_id, job_reference__client=request.user
            )
        except Address.DoesNotExist:
            return Response({"error": "Address not found"}, status=404)

        cart = request.user.cart
        cart.address = address
        cart.save()

        serializer = CartSerializer(cart, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="set-delivery-date")
    def set_delivery_date(self, request):
        cart = request.user.cart

        delivery_date_str = request.data.get("delivery_date")
        if not delivery_date_str:
            return Response({"error": "delivery_date is required"}, status=400)

        # Parse the date safely
        try:
            delivery_date = datetime.strptime(delivery_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "delivery_date must be a valid date in YYYY-MM-DD format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Compare with estimated_delivery_date
        if delivery_date < cart.estimated_delivery_date:
            return Response(
                {
                    "error": (
                        f"delivery_date must be greater than or equal to "
                        f"{cart.estimated_delivery_date}"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update the cart
        cart.delivery_date = delivery_date
        cart.save()

        serializer = CartSerializer(cart, context={"request": request})

        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="pay")
    def pay(self, request):
        cart = request.user.cart
        if not cart.is_complete:
            return Response(
                {"error": "Cart cannot isn't complete"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount = cart.total_amount
        try:
            stripe_session = create_stripe_session(amount, f"Payment for client")
            cart.stripe_session_id = stripe_session.id
            cart.save()
            print(cart.stripe_session_id)
        except:
            return Response(
                {"error": "Counldn't create payment session"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"pay_url": stripe_session.url}, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["get"],
        url_path="success-pay",
        permission_classes=[permissions.AllowAny],
    )
    def success_pay(self, request):
        session_id = request.GET.get("session_id")
        if not session_id:
            return Response({"error": "Missing session id"}, status=400)

        try:
            session, payment_intent = get_stripe_session_payment_intent(session_id)
            cart = Cart.objects.get(stripe_session_id=session.id)
        except Cart.DoesNotExist:
            return Response({"error": "Cart or stripe session not found"}, status=404)

        try:
            order_snapshot = Order.objects.create(
                client=cart.client,
                delivery_type=cart.delivery_type,
                delivery_cost=cart.delivery_cost,
                delivery_date=cart.delivery_date,
            )

            PaymentSnapshot.objects.create(
                order=order_snapshot,
                transaction_id=payment_intent.id,
                total_price=payment_intent.amount / 100.0,
                stripe_session_id=session.id,
                method="stripe",
            )


            JobReferenceSnapshot.objects.create(
                order=order_snapshot,
                code=cart.job_reference.code,
                project_name=cart.job_reference.project_name,
                title=cart.address.title,
                street_address=cart.address.street_address,
                suburb=cart.address.suburb,
                state=cart.address.state,
                postcode=cart.address.postcode,
                distance_to_factory=cart.address.distance_to_factory,
                recipient_name=cart.address.recipient_name,
                recipient_phone=cart.address.recipient_phone,
            )


            for flash in cart.flashings.all():
                flash_snapshot = StoredFlashingSnapshot.objects.create(
                    order=order_snapshot,
                    start_crush_fold=flash.start_crush_fold,
                    end_crush_fold=flash.end_crush_fold,
                    color_side_dir=flash.color_side_dir,
                    tapered=flash.tapered,
                    nodes=flash.nodes,
                    total_girth=flash.total_girth,
                )


                original_variant = flash.material
                original_material = flash.material.group.material
                original_group = flash.material.group

                MaterialSnapshot.objects.create(
                    flashing=flash_snapshot,
                    variant_type=original_material.variant_type,
                    name=original_material.name,
                    variant_label=original_variant.label,
                    variant_value=original_variant.value,
                    base_price=original_group.base_price,
                    price_per_fold=original_group.price_per_fold,
                    price_per_100girth=original_group.price_per_100girth,
                    price_per_crush_fold=original_group.price_per_crush_fold,
                )


                for spec in flash.specifications.all():
                    SpecificationSnapshot.objects.create(
                        flashing=flash_snapshot,
                        quantity=spec.quantity,
                        length=spec.length,
                        cost=spec.cost,
                    )

            # TODO: Here first of all the cart should be empty. Then the stored flashings should be removed

        except Exception as e:
            order_snapshot.delete()
            return Response(
                {"error": f"Couldn't create snapshots: {str(e)}"},
                status=500
            )

        serializer = CartSerializer(cart, context={"request": request})
        order_serializer = OrderSerializer(order_snapshot, context={"request": request})
        return Response(
            {"cart": serializer.data, "session": session, "intent": payment_intent, "order": order_serializer.data}
        )
