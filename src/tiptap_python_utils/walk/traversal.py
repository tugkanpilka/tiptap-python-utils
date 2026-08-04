"""Depth-first TipTap traversal."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Optional, Tuple, Type, TypeVar

from ..contract import kind, policy
from ..model import (
    Blockquote,
    CodeBlock,
    Heading,
    ListItem,
    Node,
    Paragraph,
    TableCell,
    TaskItem,
)

NodeT = TypeVar("NodeT", bound=Node)

# Blocks that tracked_blocks() may surface. Keep in sync with selection_id resolution.
TRACKABLE_NODE_CLASSES: tuple[Type[Node], ...] = (
    Paragraph,
    Heading,
    TaskItem,
    ListItem,
    CodeBlock,
    Blockquote,
    TableCell,
)

# Trackable blocks whose id resolves via node.id when attrs lack one.
# TaskItem is excluded — it has dedicated resolution in selection_id().
SELECTION_ID_LEAF_CLASSES: tuple[Type[Node], ...] = (
    Paragraph,
    Heading,
    ListItem,
    CodeBlock,
    Blockquote,
    TableCell,
)


@dataclass(frozen=True)
class Ref:
    node: Node
    path: Tuple[int, ...]
    parent_kind: str

    @property
    def node_id(self) -> Optional[str]:
        return selection_id(self.node)

    @property
    def parseable(self) -> bool:
        return not self.path or policy.is_parseable(self.node.kind, self.parent_kind)


class Walker:
    """Depth-first traversal for typed TipTap content."""

    def __init__(self, root_or_content: Any) -> None:
        self._root = getattr(root_or_content, "root", root_or_content)

    def walk(self) -> Iterator[Node]:
        if self._root is None:
            return
        yield from _walk(self._root)

    def of_type(self, node_class: Type[NodeT]) -> list[NodeT]:
        return [node for node in self.walk() if isinstance(node, node_class)]

    def refs(self, *, parseable: bool = False) -> Iterator[Ref]:
        if self._root is None:
            return
        yield from _refs(
            self._root,
            path=(),
            parent_kind=kind.DOC,
            parseable=parseable,
        )


def selection_id(node: Node) -> Optional[str]:
    attrs_id = policy.node_id(getattr(node, "attrs", {}))
    if attrs_id:
        return attrs_id
    if isinstance(node, TaskItem):
        return (
            node.local_task_item_id
            or node.task_item_id
            or lifted_paragraph_id(node)
            or None
        )
    lifted = lifted_paragraph_id(node)
    if lifted:
        return lifted
    if isinstance(node, SELECTION_ID_LEAF_CLASSES):
        return node.id or None
    return None


def lifted_paragraph_id(node: Node) -> Optional[str]:
    """Read-time id from a direct child paragraph when the container has none."""
    if not isinstance(node, (TaskItem, ListItem, Blockquote, TableCell)):
        return None
    for child in node.content:
        if isinstance(child, Paragraph):
            child_id = policy.content_id(child.attrs) or child.id
            if child_id:
                return child_id
    return None


def _walk(node: Node) -> Iterator[Node]:
    yield node
    for child in node.content:
        yield from _walk(child)


def _refs(
    node: Node,
    *,
    path: tuple[int, ...],
    parent_kind: str,
    parseable: bool,
) -> Iterator[Ref]:
    ref = Ref(node=node, path=path, parent_kind=parent_kind)
    if not parseable or ref.parseable:
        yield ref

    for index, child in enumerate(node.content):
        yield from _refs(
            child,
            path=path + (index,),
            parent_kind=node.kind,
            parseable=parseable,
        )
