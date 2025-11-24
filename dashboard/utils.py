from django.core.exceptions import ValidationError
import math
from random import randint

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