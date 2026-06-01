"""Generic node identity primitives."""

from __future__ import annotations

from uuid import uuid4


def new_node_id() -> str:
    return uuid4().hex
