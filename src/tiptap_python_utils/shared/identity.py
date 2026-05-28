"""Shared-node identity primitives.

Pure value-level helpers: normalize a sharedId, mint a new one, read a node's
sharedId, and stamp identity onto a raw node payload. No document traversal,
no families, no sync — those live in their sibling modules.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from .. import codec
from ..contract import key


def normalize_shared_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def new_shared_id() -> str:
    return f"shared-{uuid4().hex}"


def shared_id(node: str | Dict[str, Any]) -> Optional[str]:
    parsed = codec.read_node_input(node, label="Node content")
    return normalize_shared_id(parsed.attrs.get(key.SHARED_ID))


def stamp_shared(
    node: str | Dict[str, Any],
    shared_id: str,
    local_id: Optional[str] = None,
) -> dict[str, Any]:
    """Return a deep-copied node with sharedId and optional local id stamped."""
    parsed = codec.read_node_input(node, label="Node content").raw()
    attrs = dict(parsed.get(key.ATTRS, {}))

    if local_id is not None:
        attrs[key.ID] = local_id
    attrs[key.SHARED_ID] = shared_id
    parsed[key.ATTRS] = attrs
    return parsed
