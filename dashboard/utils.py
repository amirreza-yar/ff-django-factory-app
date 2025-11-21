from django.core.exceptions import ValidationError
import math

def validate_nodes(nodes):
    if not isinstance(nodes, list):
        raise ValidationError("nodes must be a list")

    # basic field validation
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

        if "next_node_id" in node and node["next_node_id"]:
            next_refs.add(node["next_node_id"])

        if "prev_node_id" in node and node["prev_node_id"]:
            prev_refs.add(node["prev_node_id"])

    # references must exist
    for ref in next_refs.union(prev_refs):
        if ref not in node_ids:
            raise ValidationError(f"reference to unknown node_id '{ref}'")

    # find head and tail
    prev_map = {n.get("node_id"): n.get("prev_node_id") for n in nodes}
    next_map = {n.get("node_id"): n.get("next_node_id") for n in nodes}

    heads = [nid for nid, prev in prev_map.items() if not prev]
    tails = [nid for nid, nxt in next_map.items() if not nxt]

    if len(heads) != 1:
        raise ValidationError("there must be exactly one head (prev_node_id=None)")

    if len(tails) != 1:
        raise ValidationError("there must be exactly one tail (next_node_id=None)")

    # check linked-list correctness (no cycles, consistent count)
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