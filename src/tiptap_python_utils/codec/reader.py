"""Raw TipTap JSON → typed AST hydration."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from ..contract import key, kind
from ..exceptions import TiptapValidationError
from ..model import ContentTuple, Doc, Node, registry
from ..model.payload import has_any_identity
from .raw import require_object


# Kinds that hold block/container children, never inline text directly.
_TEXT_REJECTING_KINDS = frozenset(
    {
        kind.DOC,
        kind.BULLET_LIST,
        kind.ORDERED_LIST,
        kind.TASK_LIST,
        kind.LIST_ITEM,
        kind.TASK_ITEM,
        kind.BLOCKQUOTE,
        kind.TABLE_CELL,
    }
)


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


def build_node(
    node_kind: str,
    text: str = "",
    *,
    attrs: Optional[Dict[str, Any]] = None,
    node_id: Optional[str] = None,
) -> Node:
    """Build any typed node from (kind, text, attrs) via the registry.

    Constructs a minimal raw payload and hydrates it through ``read_node`` so
    subclass-typed fields (e.g. ``Heading.level``) and ``present`` semantics
    are derived the same way as when parsing real JSON. Pure: ``node_id`` is
    only stamped when ``attrs`` carries no identity of its own.
    """
    merged = dict(attrs or {})
    if node_id is not None and not has_any_identity(merged):
        merged[key.ID] = node_id

    raw: Dict[str, Any] = {key.TYPE: node_kind}
    if merged:
        raw[key.ATTRS] = merged
    if text:
        _attach_text(raw, node_kind, text)
    return read_node(raw)


def _attach_text(raw: Dict[str, Any], node_kind: str, text: str) -> None:
    if node_kind == kind.TEXT:
        raw[key.TEXT] = text
    elif node_kind in _TEXT_REJECTING_KINDS:
        raise TiptapValidationError(
            f"Node kind '{node_kind}' cannot hold inline text content"
        )
    else:
        raw[key.CONTENT] = [{key.TYPE: kind.TEXT, key.TEXT: text}]


def read_node_input(node_or_raw: Any, *, label: str) -> Node:
    """Read either a typed node or a raw node payload."""
    if isinstance(node_or_raw, Node):
        return node_or_raw

    parsed = require_object(node_or_raw, label=label)
    node = read_doc(parsed) if parsed.get(key.TYPE) == kind.DOC else read_node(parsed)
    if node is None:
        raise TiptapValidationError(f"{label} must be a valid TipTap node")
    return node
