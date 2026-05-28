"""Typed TipTap AST model.

This package initializer is intentionally re-export-only. Implementation
lives in:

- ``base``      — ``Node``, ``Text``, ``ContentTuple``, ``MarksTuple``, ``NodeT``
- ``nodes``     — concrete node classes (``Doc``, ``Paragraph``, ``Heading``, …)
- ``registry``  — ``Registry`` plus the bootstrapped ``registry`` instance
- ``payload``   — raw-payload extraction helpers used by node readers
"""

from .base import ContentTuple, MarksTuple, Node, NodeT, Text
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
from .registry import Registry, registry

__all__ = [
    "Blockquote",
    "BulletList",
    "CodeBlock",
    "ContentTuple",
    "Doc",
    "Heading",
    "ListItem",
    "MarksTuple",
    "Node",
    "NodeT",
    "OrderedList",
    "Paragraph",
    "Registry",
    "TableCell",
    "TaskItem",
    "TaskList",
    "Text",
    "Unknown",
    "registry",
]
