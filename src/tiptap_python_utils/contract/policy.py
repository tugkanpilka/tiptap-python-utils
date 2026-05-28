"""TipTap identity and parseability policy."""

from __future__ import annotations

from typing import Any, Optional

from . import key, kind

_CONTAINER_KINDS = frozenset(
    {
        kind.TASK_ITEM,
        kind.LIST_ITEM,
        kind.TABLE_CELL,
        kind.BLOCKQUOTE,
    }
)


def is_parseable(node_kind: str, parent_kind: str) -> bool:
    """Return whether a node is tracked as an addressable document node."""
    if node_kind == kind.PARAGRAPH and parent_kind in _CONTAINER_KINDS:
        return False
    return True


def node_id(attrs: Any) -> Optional[str]:
    return _string_attr(attrs, key.ID)


def tiptap_id(attrs: Any) -> Optional[str]:
    return _string_attr(attrs, key.TIPTAP_ID)


def content_id(attrs: Any) -> str:
    return node_id(attrs) or tiptap_id(attrs) or ""


def shared_id(attrs: Any) -> Optional[str]:
    return _string_attr(attrs, key.SHARED_ID)


def _string_attr(attrs: Any, name: str) -> Optional[str]:
    if not isinstance(attrs, dict):
        return None

    value = attrs.get(name)
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)
