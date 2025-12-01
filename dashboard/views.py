from django.shortcuts import render
from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from datetime import datetime
from django.utils import timezone
from datetime import timedelta

from factory.models import DeliveryMethod
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
    UserSerializer,
)
from .drafts import JobReferenceDraft
from .models import Cart, Order, JobReference
from .sanpshots import (
    StoredFlashingSnapshot,
    MaterialSnapshot,
    SpecificationSnapshot,
    JobReferenceSnapshot,
    PaymentSnapshot,
    DeliveryInfoSnapshot,
    PickupInfoSnapshot,
)
from .utils import create_stripe_session, get_stripe_session_payment_intent


class UserProfileView(generics.RetrieveUpdateAPIView):
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

    http_method_names = ["get", "post", "delete", "patch", "options"]

    def get_queryset(self):
        return self.request.user.flashings.all()

    def perform_create(self, serializer):
        serializer.save(client_id=self.request.user.id)


class JobReferenceView(viewsets.ModelViewSet):
    serializer_class = JobReferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ["get", "patch", "post", "delete", "options"]

    def get_queryset(self):
        return self.request.user.job_references.all()

    def perform_create(self, serializer):
        serializer.save(client_id=self.request.user.id)

    @action(detail=False, methods=["post"], url_path="check-code")
    def check_code(self, request):
        code = request.data.get("code")
        user = request.user

        exists = user.job_references.filter(code=code).exists()

        return Response({"exists": exists})


class NewJobReferenceView(viewsets.ModelViewSet):
    serializer_class = NewJobReferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ["patch", "options"]

    def get_queryset(self):
        return self.request.user.draf_job_reference


class AddressView(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ["get", "post", "delete", "patch", "options"]

    def get_queryset(self):
        job_ref_id = self.kwargs.get("job_ref_pk")
        return self.request.user.job_references.get(id=job_ref_id).addresses.all()

    def perform_create(self, serializer):
        serializer.save(job_reference_id=self.kwargs["job_ref_pk"])


class OrderView(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ["get"]

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

    @action(detail=False, methods=["post"], url_path="estimate-delivery")
    def estimate_delivery_date(self, request):
        # TODO Should recieve an address_id and should estimate delivery date
        # TODO Should return the estimated delivery date
        cart = request.user.cart
        
        address_id = request.data.get("address_id")
        
        try:
            address = Address.objects.get(
                id=address_id, job_reference__client=request.user
            )
        except Address.DoesNotExist:
            return Response({"error": "Address not found"}, status=404)
        
        distance = float(address.distance_to_factory)
        weight = float(cart.total_delivery_weight)
        
        # print(distance, weight, address.best_delivery_method.estimate_delivery_days(distance, weight))
        best_date = address.best_delivery_method.estimate_delivery_days(distance, weight) + 2
        
        
        return Response({"estimated_delivery_date": (timezone.now() + timedelta(days=best_date)).date()}, status=200)

    @action(detail=False, methods=["post"], url_path="update")
    def update_cart(self, request):
        job_reference_id = request.data.get("job_reference_id")
        address_id = request.data.get("address_id")
        delivery_date_str = request.data.get("delivery_date")
        delivery_type = request.data.get("delivery_type")

        cart = request.user.cart

        if not delivery_date_str:
            return Response({"error": "delivery_date is required"}, status=400)

        if not (address_id or job_reference_id):
            return Response(
                {"error": "address_id or job_reference_id is required"}, status=400
            )

        if not delivery_type:
            return Response({"error": "delivery_type is required"}, status=400)
        elif delivery_type == "delivery" and not address_id:
            return Response(
                {"error": "for delivery the address_id is required"}, status=400
            )
        elif delivery_type == "pickup" and not job_reference_id:
            return Response(
                {"error": "for pickup the job_reference_id is required"}, status=400
            )

        # Setting delivery date
        # TODO Should check the estimated delivery date based on delivery method (.estimate_dalivery_date method in methods model)
        try:
            delivery_date = datetime.strptime(delivery_date_str, "%Y-%m-%d").date()
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

            cart.delivery_date = delivery_date
        except ValueError:
            return Response(
                {"error": "delivery_date must be a valid date in YYYY-MM-DD format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if delivery_type == "pickup":
            try:
                job_ref = JobReference.objects.get(
                    id=job_reference_id, client=request.user
                )
                cart.delivery_type = "pickup"
                cart.job_reference_pickup = job_ref
                cart.address = None
            except Address.DoesNotExist:
                return Response({"error": "JobReference not found"}, status=404)

        elif delivery_type == "delivery":
            try:
                address = Address.objects.get(
                    id=address_id, job_reference__client=request.user
                )
                cart.delivery_type = "delivery"
                cart.address = address
                cart.job_reference_pickup = None
            except Address.DoesNotExist:
                return Response({"error": "Address not found"}, status=404)

        # return Response(
        #     {
        #         "job_reference_id": job_reference_id,
        #         "address_id": address_id,
        #         "delivery_date_str": delivery_date_str,
        #         "delivery_type": delivery_type,
        #     },
        #     status=200,
        # )
        cart.save()

        serializer = CartSerializer(cart, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="pay")
    def pay(self, request):
        cart = request.user.cart
        if not cart.is_complete:
            return Response(
                {"error": "Cart isn't complete"},
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

        # try:
        if True:

            order_snapshot = Order.objects.create(
                client=cart.client,
            )
            PaymentSnapshot.objects.create(
                order=order_snapshot,
                method="stripe",
                transaction_id=payment_intent.id,
                stripe_session_id=session.id,
                total_amount=payment_intent.amount / 100.0,
                gst_ratio=cart.gst_ratio,
            )

            JobReferenceSnapshot.objects.create(
                order=order_snapshot,
                code=cart.job_reference.code,
                project_name=cart.job_reference.project_name,
                # title=cart.address.title,
                # street_address=cart.address.street_address,
                # suburb=cart.address.suburb,
                # state=cart.address.state,
                # postcode=cart.address.postcode,
                # distance_to_factory=cart.address.distance_to_factory,
                # recipient_name=cart.address.recipient_name,
                # recipient_phone=cart.address.recipient_phone,
            )

            for flash in cart.flashings.all():
                flash_snapshot = StoredFlashingSnapshot.objects.create(
                    order=order_snapshot,
                    code=flash.code,
                    position=flash.position,
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
                    sample_weight=original_group.sample_weight,
                    sample_weight_sq_meter=original_group.sample_weight_sq_meter,
                )

                for spec in flash.specifications.all():
                    SpecificationSnapshot.objects.create(
                        flashing=flash_snapshot,
                        quantity=spec.quantity,
                        length=spec.length,
                        weight=spec.weight,
                        cost=spec.cost,
                    )

            # TODO: Here first of all the cart should be empty. Then the stored flashings should be removed

            if cart.delivery_type == "delivery":
                addr = cart.address
                del_m = addr.best_delivery_method
                DeliveryInfoSnapshot.objects.create(
                    order=order_snapshot,
                    cost=cart.delivery_cost,
                    date=cart.delivery_date,
                    title=addr.title,
                    street_address=addr.street_address,
                    suburb=addr.suburb,
                    state=addr.state,
                    postcode=addr.postcode,
                    distance_to_factory=addr.distance_to_factory,
                    recipient_name=addr.recipient_name,
                    recipient_phone=addr.recipient_phone,
                    _dm_type=del_m.method_type,
                    _dm_name=del_m.name,
                    _dm_description=del_m.description,
                    _dm_base_cost=del_m.base_cost,
                    _dm_cost_per_kg=del_m.cost_per_kg,
                    _dm_cost_per_km=del_m.cost_per_km,
                )

            elif cart.delivery_type == "pickup":
                PickupInfoSnapshot.objects.create(
                    order=order_snapshot, date=cart.delivery_date
                )
            else:
                Response(
                    {
                        "error": "Something went wrong, not your fault but you better not pay this order!"
                    }
                )

            # for flash in cart.flashings.all():
            #     flash.delete()

            # cart.delete()

        # except Exception as e:
        #     order_snapshot.delete()
        #     return Response(
        #         {"error": f"Couldn't create snapshots: {str(e)}"}, status=500
        #     )

        serializer = CartSerializer(cart, context={"request": request})
        order_serializer = OrderSerializer(order_snapshot, context={"request": request})
        return Response(
            {
                "cart": serializer.data,
                "session": session,
                "intent": payment_intent,
                "order": order_serializer.data,
            }
        )
