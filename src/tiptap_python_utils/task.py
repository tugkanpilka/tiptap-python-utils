"""Pure, raw-dict helpers for TipTap ``taskList`` / ``taskItem`` shapes.

This module is the raw-dict counterpart to the typed ``tasks`` package:
``tasks`` works on hydrated ``Content``/``TaskItem`` objects, while ``task``
deals only with plain TipTap JSON dicts and never imports the model layer.

Read as a namespace: ``task.create_list(...)``, ``task.is_list(...)``,
``task.is_item(...)``.
"""

from __future__ import annotations

from typing import Any, List

from .contract import key, kind

__all__ = ["create_list", "is_item", "is_list"]


def create_list(items: List[Any]) -> dict:
    """Wrap ``items`` in a ``taskList`` block.

    By design this does **not** copy ``items`` — the same list object is
    stored on the returned block's ``content`` (by reference). Callers may
    keep appending to the original list afterwards and see the change
    reflected here. Do not introduce ``deepcopy``/``list(...)``/``[*items]``
    here: the shared-reference behaviour is part of the contract and is
    pinned by ``tests/test_task_namespace.py``.
    """
    return {key.TYPE: kind.TASK_LIST, key.CONTENT: items}


def is_list(item: Any) -> bool:
    """True iff ``item`` is a valid ``taskList`` dict.

    Safe on missing keys (uses ``.get()``): all three conditions must hold —
    ``item`` is a dict, its ``type`` is ``taskList``, and its ``content`` is a
    list.
    """
    if not isinstance(item, dict):
        return False
    return item.get(key.TYPE) == kind.TASK_LIST and isinstance(
        item.get(key.CONTENT), list
    )


def is_item(node: Any) -> bool:
    """True iff ``node`` is a ``taskItem`` dict.

    Safe on missing keys: ``node`` must be a dict whose ``type`` is
    ``taskItem``.
    """
    if not isinstance(node, dict):
        return False
    return node.get(key.TYPE) == kind.TASK_ITEM
