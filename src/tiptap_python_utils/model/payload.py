"""Raw TipTap payload extraction helpers shared by node readers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Mapping, TYPE_CHECKING

from ..contract import key, policy

if TYPE_CHECKING:
    from .base import ContentTuple


def payload(
    raw: Mapping[str, Any],
    children: "ContentTuple",
    *,
    extra_keys: set[str] | None = None,
) -> dict[str, Any]:
    present = frozenset(str(name) for name in raw.keys())
    known = {key.TYPE, key.ATTRS, key.CONTENT} | (extra_keys or set())
    attrs = raw.get(key.ATTRS, {})
    return {
        "id": policy.content_id(attrs),
        "content": children,
        "attrs": deepcopy(attrs) if isinstance(attrs, dict) else {},
        "extra": {name: deepcopy(value) for name, value in raw.items() if name not in known},
        "present": present,
    }


def heading_level(attrs: Mapping[str, Any]) -> int:
    level = attrs.get(key.LEVEL, 1) if isinstance(attrs, dict) else 1
    return level if isinstance(level, int) and 1 <= level <= 6 else 1


def task_canonical_id(attrs: Mapping[str, Any], fallback: str) -> str:
    if not isinstance(attrs, dict):
        return fallback

    canonical_id = attrs.get(key.TASK_CANONICAL_ID)
    if isinstance(canonical_id, str):
        stripped = canonical_id.strip()
        if stripped:
            return stripped
    if canonical_id is not None:
        return str(canonical_id)
    return fallback


def task_completion(attrs: Mapping[str, Any], extra: Mapping[str, Any]) -> bool | None:
    completion = _interpret_status(extra.get(key.STATUS))
    if completion is not None:
        return completion

    if not isinstance(attrs, dict):
        attrs = {}

    completion = _interpret_status(attrs.get(key.STATUS))
    if completion is not None:
        return completion

    return _interpret_checked(attrs.get(key.CHECKED))


def _interpret_status(value: Any) -> bool | None:
    if isinstance(value, str) and value.lower() in {"done", "pending"}:
        return value.lower() == "done"
    return None


def _interpret_checked(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
        return value.strip().lower() == "true"
    return None


def has_any_identity(attrs: Dict[str, Any]) -> bool:
    return key.ID in attrs or key.TIPTAP_ID in attrs
