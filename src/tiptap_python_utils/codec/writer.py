"""Typed AST → raw TipTap JSON serialization."""

from __future__ import annotations

import json
from typing import Any, Dict

from ..model import Node


def dump(node: Node) -> Dict[str, Any]:
    return node.raw()


def dumps(node: Node) -> str:
    return json.dumps(dump(node))
