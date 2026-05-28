"""Identity-stripped fingerprint of a raw node, used to detect divergent bodies."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..contract import key


def fingerprint_shared(node: dict[str, Any]) -> str:
    normalized = deepcopy(node)
    attrs = dict(normalized.get(key.ATTRS, {}))
    attrs.pop(key.ID, None)
    attrs.pop(key.SHARED_ID, None)
    if attrs:
        normalized[key.ATTRS] = attrs
    else:
        normalized.pop(key.ATTRS, None)
    return json.dumps(normalized, sort_keys=True)
