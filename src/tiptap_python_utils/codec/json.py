"""TipTap raw JSON codec."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

from ..exceptions import TiptapValidationError
from ..types import DocumentContent

from ..contract import key, kind, policy
from ..model import ContentTuple, Doc, Node, registry


def parse_raw(raw: Optional[DocumentContent]) -> Optional[Dict[str, Any]]:
    """Leniently parse a raw document payload."""
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
    else:
        parsed = raw

    return deepcopy(parsed) if isinstance(parsed, dict) else None


def require_object(
    content: str | Mapping[str, Any],
    *,
    label: str = "content",
) -> Dict[str, Any]:
    """Strictly parse a JSON object payload."""
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise TiptapValidationError(f"{label} is not valid JSON") from exc
    else:
        parsed = deepcopy(dict(content))

    if not isinstance(parsed, dict):
        raise TiptapValidationError(f"{label} must be a JSON object")
    return parsed


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


def dump(node: Node) -> Dict[str, Any]:
    return node.raw()


def dumps(node: Node) -> str:
    return json.dumps(dump(node))


def raw_node_id(node: Mapping[str, Any]) -> str:
    return policy.content_id(node.get(key.ATTRS, {}))


def raw_text(node: Mapping[str, Any]) -> str:
    return " ".join(_iter_text(node))


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def _iter_text(node: Mapping[str, Any]):
    if not isinstance(node, dict):
        return

    if node.get(key.TYPE) == kind.TEXT:
        text = str(node.get(key.TEXT, "")).strip()
        if text:
            yield text
        return

    content = node.get(key.CONTENT, [])
    if not isinstance(content, list):
        return

    for child in content:
        if isinstance(child, dict):
            yield from _iter_text(child)
