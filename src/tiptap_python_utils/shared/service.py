"""Shared-node behavior for TipTap documents."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, Optional
from uuid import uuid4

from ..exceptions import TiptapValidationError

from .. import codec
from ..content import Content
from ..contract import key
from ..tree import node_at_path, replace_at_path


def shared_families(content: str | Dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return canonical node bodies grouped by sharedId."""
    tiptap = Content.require(content)
    families: dict[str, dict[str, Any]] = {}
    fingerprints: dict[str, str] = {}

    for ref in tiptap.refs(parseable=True):
        node = ref.node.raw()
        node_shared_id = normalize_shared_id(node.get(key.ATTRS, {}).get(key.SHARED_ID))
        if not node_shared_id:
            continue

        fingerprint = fingerprint_shared(node)
        if (
            node_shared_id in fingerprints
            and fingerprints[node_shared_id] != fingerprint
        ):
            raise TiptapValidationError(
                f"Conflicting node bodies detected for sharedId '{node_shared_id}'"
            )
        if node_shared_id not in families:
            families[node_shared_id] = deepcopy(node)
            fingerprints[node_shared_id] = fingerprint

    return families


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


def has_shared(content: str | Dict[str, Any], shared_id: str) -> bool:
    tiptap = Content.require(content)
    for ref in tiptap.refs(parseable=True):
        if normalize_shared_id(ref.node.attrs.get(key.SHARED_ID)) == shared_id:
            return True
    return False


def shared_id(node: str | Dict[str, Any]) -> Optional[str]:
    parsed = codec.read_node_input(node, label="Node content")
    return normalize_shared_id(parsed.attrs.get(key.SHARED_ID))


def new_shared_id() -> str:
    return f"shared-{uuid4().hex}"


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


def sync_shared(
    content: str | Dict[str, Any],
    families: dict[str, dict[str, Any]],
) -> tuple[str, bool]:
    """Rewrite matching shared nodes using canonical bodies."""
    tiptap = Content.require(content)
    updated_root = tiptap._require_root()
    changed = False

    refs = tuple(tiptap.refs(parseable=True))
    for ref in sorted(refs, key=lambda item: len(item.path), reverse=True):
        current = node_at_path(updated_root, ref.path)
        current_raw = current.raw()
        current_shared_id = normalize_shared_id(
            current_raw.get(key.ATTRS, {}).get(key.SHARED_ID)
        )
        if not current_shared_id or current_shared_id not in families:
            continue

        replacement_raw = _merge_preserving_identity(
            current_raw,
            families[current_shared_id],
        )
        if replacement_raw == current_raw:
            continue

        replacement = codec.read_node_input(replacement_raw, label="Node content")
        updated_root = replace_at_path(updated_root, ref.path, replacement)
        changed = True

    return tiptap._with_root(updated_root).dump(), changed


def normalize_shared_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def _merge_preserving_identity(
    target_node: dict[str, Any],
    canonical_node: dict[str, Any],
) -> dict[str, Any]:
    replacement = deepcopy(canonical_node)
    target_attrs = target_node.get(key.ATTRS, {})
    replacement_attrs = dict(replacement.get(key.ATTRS, {}))

    if isinstance(target_attrs, dict) and target_attrs.get(key.ID):
        replacement_attrs[key.ID] = target_attrs[key.ID]
    target_shared_id = normalize_shared_id(target_attrs.get(key.SHARED_ID))
    if target_shared_id:
        replacement_attrs[key.SHARED_ID] = target_shared_id

    replacement[key.ATTRS] = replacement_attrs
    return replacement
