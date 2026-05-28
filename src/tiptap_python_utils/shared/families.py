"""Group canonical bodies by sharedId and answer presence queries."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from ..content import Content
from ..contract import key
from ..exceptions import TiptapValidationError
from .fingerprint import fingerprint_shared
from .identity import normalize_shared_id


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


def has_shared(content: str | Dict[str, Any], shared_id: str) -> bool:
    tiptap = Content.require(content)
    for ref in tiptap.refs(parseable=True):
        if normalize_shared_id(ref.node.attrs.get(key.SHARED_ID)) == shared_id:
            return True
    return False
