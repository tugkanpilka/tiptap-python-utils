"""Raw TipTap JSON → typed AST hydration."""

from __future__ import annotations

from typing import Any, Mapping

from ..contract import key, kind
from ..exceptions import TiptapValidationError
from ..model import ContentTuple, Doc, Node, registry
from .raw import require_object


def read_doc(raw: Mapping[str, Any]) -> Doc | None:
    """Read a raw TipTap document root."""
    if raw.get(key.TYPE) != kind.DOC:
        return None
    parsed = read_node(raw)
    return parsed if isinstance(parsed, Doc) else None


def read_node(raw: Mapping[str, Any]) -> Node:
    """Read a raw TipTap node by delegating to the registry."""
    children = read_children(raw.get(key.CONTENT, []))
    return registry.read(raw, children)


def read_children(raw_children: Any) -> ContentTuple:
    if not isinstance(raw_children, list):
        return ()
    return tuple(read_node(child) for child in raw_children if isinstance(child, dict))


def read_node_input(node_or_raw: Any, *, label: str) -> Node:
    """Read either a typed node or a raw node payload."""
    if isinstance(node_or_raw, Node):
        return node_or_raw

    parsed = require_object(node_or_raw, label=label)
    node = read_doc(parsed) if parsed.get(key.TYPE) == kind.DOC else read_node(parsed)
    if node is None:
        raise TiptapValidationError(f"{label} must be a valid TipTap node")
    return node
