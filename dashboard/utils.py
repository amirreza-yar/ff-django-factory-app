from django.core.exceptions import ValidationError
import math
from random import randint
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import requests
import stripe

ORS_API_KEY = settings.ORS_API_KEY

GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
ROUTE_URL = "https://api.openrouteservice.org/v2/directions/driving-car"

stripe.api_key = settings.STRIPE_KEY

def create_stripe_session(amount, name="Test Order Pay"):
    DOMAIN = "http://localhost:8000"

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "aud",
                    "product_data": {"name": name},
                    "unit_amount": int(amount * 100),  # $10.00
                },
                "quantity": 1,
            }
        ],
        success_url=f"{DOMAIN}/api/d/cart/success-pay?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{DOMAIN}/payment/cancel",
    )

    return session

def get_stripe_session_payment_intent(session_id):
    session = stripe.checkout.Session.retrieve(session_id)
    payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
    
    return session, payment_intent

def geocode_text(query):
    """Return (lon, lat) from a postcode or partial address."""
    params = {
        "api_key": ORS_API_KEY,
        "text": query,
        "size": 1
    }

    resp = requests.get(GEOCODE_URL, params=params)
    resp.raise_for_status()
    data = resp.json()

    features = data.get("features")
    if not features:
        raise ValueError(f"Could not geocode: {query}")

    coords = features[0]["geometry"]["coordinates"]
    return coords[0], coords[1]  # (lon, lat)

def driving_distance_km(from_address, to_address):
    """Return driving distance in kilometers between two postcodes or addresses."""
    start = geocode_text(from_address)
    end = geocode_text(to_address)

    body = {
        "coordinates": [
            [start[0], start[1]],
            [end[0], end[1]]
        ]
    }

    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }

    resp = requests.post(ROUTE_URL, json=body, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    summary = data["routes"][0]["summary"]
    distance_meters = summary["distance"]

    return math.ceil(distance_meters / 1000)

def generate_six_digit_id():
    return str(randint(100000, 999999))

def validate_nodes(nodes):
    if not nodes:
        return

    if not isinstance(nodes, list):
        raise ValidationError("nodes must be a list")

    # required fields
    required_fields = {"node_id", "left", "top"}

    node_ids = set()
    next_refs = set()
    prev_refs = set()

    for node in nodes:
        if not isinstance(node, dict):
            raise ValidationError("each node must be an object")

        if not required_fields.issubset(node.keys()):
            raise ValidationError("each node must contain node_id, left, top")

        node_id = node["node_id"]

        if node_id in node_ids:
            raise ValidationError(f"duplicate node_id '{node_id}' found")
        node_ids.add(node_id)

        # optional numeric field
        if "next_line_bside_length" in node:
            value = node["next_line_bside_length"]
            if value is not None and not isinstance(value, (int, float)):
                raise ValidationError(
                    f"next_line_bside_length for node '{node_id}' must be a number"
                )

        # collect references
        if "next_node_id" in node and node["next_node_id"]:
            next_refs.add(node["next_node_id"])

        if "prev_node_id" in node and node["prev_node_id"]:
            prev_refs.add(node["prev_node_id"])

    # references must exist
    for ref in next_refs.union(prev_refs):
        if ref not in node_ids:
            raise ValidationError(f"reference to unknown node_id '{ref}'")

    # build maps
    prev_map = {n.get("node_id"): n.get("prev_node_id") for n in nodes}
    next_map = {n.get("node_id"): n.get("next_node_id") for n in nodes}

    # head and tail checks
    heads = [nid for nid, prev in prev_map.items() if not prev]
    tails = [nid for nid, nxt in next_map.items() if not nxt]

    if len(heads) != 1:
        raise ValidationError("there must be exactly one head (prev_node_id=None)")

    if len(tails) != 1:
        raise ValidationError("there must be exactly one tail (next_node_id=None)")

    # walk through the chain, detect cycles
    visited = set()
    current = heads[0]

    while current:
        if current in visited:
            raise ValidationError("node chain contains a cycle")
        visited.add(current)
        current = next_map.get(current)

    if len(visited) != len(nodes):
        raise ValidationError("node chain is broken or incomplete")

def calculate_total_girth(nodes):
        """
        Walks through the linked nodes in order and returns the sum
        of distances between each pair.
        """
        if not nodes:
            return 0

        # Build quick lookup by node_id
        node_map = {n["node_id"]: n for n in nodes}

        # Find the head node
        head = None
        for n in nodes:
            if not n.get("prev_node_id"):
                head = n
                break

        if not head:
            return 0  # invalid or empty chain

        total = 0.0
        current = head

        while current.get("next_node_id"):
            nxt = node_map[current["next_node_id"]]

            dx = nxt["left"] - current["left"]
            dy = nxt["top"] - current["top"]

            total += math.hypot(dx, dy)

            current = nxt

        return total

def validate_material_snapshot(data):
    """
    Validates that the snapshot contains the expected keys and value types.
    Ensures consistency so corrupted or incomplete snapshots don't get saved.
    """
    required_fields = {
        "variant_type": str,
        "name": str,
        "variant_label": str,
        "variant_value": str,
        "base_price": (int, float, str),
        "price_per_fold": (int, float, str),
        "price_per_100girth": (int, float, str),
        "price_per_crush_fold": (int, float, str),
        "sample_weight": (int, float, str),
        "sample_weight_sq_meter": (int, float, str),
    }

    if not isinstance(data, dict):
        raise ValidationError("Material snapshot must be a JSON object.")

    missing = [k for k in required_fields.keys() if k not in data]
    if missing:
        raise ValidationError(f"Missing snapshot fields: {', '.join(missing)}")

    for key, expected_types in required_fields.items():
        if not isinstance(data[key], expected_types):
            raise ValidationError(
                f"Invalid type for '{key}'. Expected {expected_types}, got {type(data[key])}."
            )
            
def two_days_from_now():
    return (timezone.now() + timedelta(days=2)).date()