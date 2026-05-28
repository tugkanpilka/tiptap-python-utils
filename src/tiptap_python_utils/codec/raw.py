"""Raw TipTap JSON I/O and dict-shaped helpers.

This module is intentionally free of any ``..model`` import so that raw
validation can be exercised without hydrating the typed AST.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, Iterator, Mapping, Optional

from ..contract import key, kind, policy
from ..exceptions import TiptapValidationError
from ..types import DocumentContent


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


def raw_node_id(node: Mapping[str, Any]) -> str:
    return policy.content_id(node.get(key.ATTRS, {}))


def raw_text(node: Mapping[str, Any]) -> str:
    return " ".join(_iter_text(node))


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def _iter_text(node: Mapping[str, Any]) -> Iterator[str]:
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
