"""Unified trackability traversal for TipTap content."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, replace
from typing import List, Optional, Tuple

from ..content import Content
from ..contract import kind
from ..model import Heading, Node, TaskItem
from ..walk.traversal import TRACKABLE_NODE_CLASSES, selection_id


@dataclass(frozen=True)
class TrackedBlock:
    """One backend-addressable block and its visible text."""

    local_id: str
    node_type: str
    text: str
    word_count: int
    html_tag: str
    context: Optional[str] = None
    is_open_task: bool = False
    shared_id: Optional[str] = None

    def with_context(self, context: str | None) -> TrackedBlock:
        return replace(self, context=context)


def tracked_blocks(content: Content, *, context: bool = False) -> List[TrackedBlock]:
    """Return every addressable block using one traversal."""
    if content.root is None:
        return []

    blocks = [_to_block(node) for node in _tracked_nodes(content)]
    if not context:
        return blocks
    return list(_apply_heading_context(blocks))


def _tracked_nodes(content: Content) -> Iterator[Node]:
    for ref in content.refs(parseable=True):
        node = ref.node
        if not isinstance(node, TRACKABLE_NODE_CLASSES):
            continue
        if not selection_id(node):
            continue
        yield node


def _to_block(node: Node) -> TrackedBlock:
    local_id = selection_id(node)
    if local_id is None:
        raise ValueError(f"trackable node {node.kind!r} has no resolvable id")
    text = node.text
    return TrackedBlock(
        local_id=local_id,
        node_type=node.kind,
        text=text,
        word_count=_word_count(text),
        html_tag=_html_tag(node),
        is_open_task=_is_open_task(node),
        shared_id=node.shared_id,
    )


def _word_count(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0
    return len(stripped.split())


def _html_tag(node: Node) -> str:
    if isinstance(node, Heading):
        return f"h{node.level}"
    if node.kind in (kind.TASK_ITEM, kind.LIST_ITEM):
        return "li"
    if node.kind == kind.CODE_BLOCK:
        return "code"
    if node.kind == kind.BLOCKQUOTE:
        return "blockquote"
    if node.kind == kind.TABLE_CELL:
        return "td"
    return "p"


def _is_open_task(node: Node) -> bool:
    return isinstance(node, TaskItem) and not node.is_completed


def _apply_heading_context(blocks: List[TrackedBlock]) -> Iterator[TrackedBlock]:
    context_stack: List[Tuple[int, str]] = []

    for block in blocks:
        if not block.text.strip():
            context_stack.clear()
            yield block
            continue

        if _is_heading_tag(block.html_tag):
            level = int(block.html_tag[1])
            parent_context = _context_string(context_stack)
            _push_heading(context_stack, level, block.text)
            yield block.with_context(parent_context)
            continue

        yield block.with_context(_context_string(context_stack))


def _is_heading_tag(html_tag: str) -> bool:
    return len(html_tag) == 2 and html_tag[0] == "h" and html_tag[1].isdigit()


def _push_heading(stack: List[Tuple[int, str]], level: int, text: str) -> None:
    while stack and stack[-1][0] >= level:
        stack.pop()
    stack.append((level, text))


def _context_string(stack: List[Tuple[int, str]]) -> Optional[str]:
    if not stack:
        return None
    return " > ".join(text for _, text in stack)
