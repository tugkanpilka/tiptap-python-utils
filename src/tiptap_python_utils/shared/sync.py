"""Rewrite shared nodes from canonical bodies while preserving local identity."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from .. import codec
from ..content import Content
from ..contract import key
from ..tree import node_at_path, replace_at_path
from .identity import normalize_shared_id


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
