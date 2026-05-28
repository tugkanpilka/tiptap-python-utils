"""Node-kind to typed class dispatch."""

from __future__ import annotations

from typing import Any, Mapping

from ..contract import key
from .base import ContentTuple, Node
from .nodes import (
    Blockquote,
    BulletList,
    CodeBlock,
    Doc,
    Heading,
    ListItem,
    OrderedList,
    Paragraph,
    TableCell,
    TaskItem,
    TaskList,
    Unknown,
)
from .base import Text


class Registry:
    """Map raw TipTap kinds to typed node classes."""

    def __init__(self) -> None:
        self._classes: dict[str, type[Node]] = {}

    def register(self, node_class: type[Node]) -> type[Node]:
        self._classes[node_class.kind] = node_class
        return node_class

    def read(self, raw: Mapping[str, Any], children: ContentTuple) -> Node:
        node_kind = str(raw.get(key.TYPE, ""))
        node_class = self._classes.get(node_kind, Unknown)
        return node_class.read(raw, children)


registry = Registry()
for _node_class in (
    Doc,
    Text,
    Paragraph,
    Heading,
    TaskItem,
    ListItem,
    CodeBlock,
    TaskList,
    BulletList,
    OrderedList,
    Blockquote,
    TableCell,
):
    registry.register(_node_class)
