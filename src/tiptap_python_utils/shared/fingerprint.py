"""Identity-stripped fingerprint of a node, used to detect divergent bodies."""

from __future__ import annotations

import json

from ..contract import key
from ..model import Node


def fingerprint(node: Node) -> str:
    raw = node.raw()
    attrs = dict(raw.get(key.ATTRS, {}))
    attrs.pop(key.ID, None)
    attrs.pop(key.SHARED_ID, None)
    attrs.pop(key.SHARED, None)
    attrs.pop(key.PLACE, None)
    attrs.pop(key.TASK_CANONICAL_ID, None)
    if attrs:
        raw[key.ATTRS] = attrs
    else:
        raw.pop(key.ATTRS, None)
    return json.dumps(raw, sort_keys=True)
