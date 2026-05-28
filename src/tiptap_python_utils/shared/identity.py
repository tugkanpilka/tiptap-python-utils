"""Shared-node identity primitives."""

from __future__ import annotations

from uuid import uuid4


def new_shared_id() -> str:
    return f"shared-{uuid4().hex}"
