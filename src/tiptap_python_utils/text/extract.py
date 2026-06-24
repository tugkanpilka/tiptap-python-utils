"""Visible text extraction for TipTap content."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, List, Optional, Tuple

from ..content import Content
from ..contract import kind
from ..model import CodeBlock, Heading, ListItem, Node, Paragraph, TaskItem


@dataclass(frozen=True)
class NodeText:
    node_id: str
    text: str
    html_tag: str = "p"
    context: Optional[str] = None
    node_type: Optional[str] = None


def visible_text(content: Content) -> str:
    return content.text


def word_count(content: Content) -> int:
    return content.word_count()


def text_slices(content: Content, *, context: bool = False) -> List[NodeText]:
    nodes = _content_nodes(content)
    if context:
        return list(_apply_heading_context(nodes))
    return list(nodes)


def _content_nodes(content: Content) -> Iterator[NodeText]:
    if content.root is None:
        return
    for ref in content.refs(parseable=True):
        node = ref.node
        node_id = _node_id(node)
        if not node_id or not isinstance(
            node, (Paragraph, Heading, TaskItem, ListItem, CodeBlock)
        ):
            continue
        yield NodeText(
            node_id=node_id,
            text=node.text,
            html_tag=_tag(node),
            node_type=node.kind,
        )


def _node_id(node: Node) -> str:
    if isinstance(node, TaskItem):
        return node.task_item_id
    return node.id  # ListItem included


def _tag(node: Node) -> str:
    if isinstance(node, Heading):
        return f"h{node.level}"
    if node.kind in (kind.TASK_ITEM, kind.LIST_ITEM):
        return "li"
    if node.kind == kind.CODE_BLOCK:
        return "code"
    return "p"


def _apply_heading_context(nodes: Iterable[NodeText]) -> Iterator[NodeText]:
    context_stack: List[Tuple[int, str]] = []

    for node in nodes:
        if not node.text.strip():
            context_stack.clear()
            yield node
            continue

        if _is_heading(node.html_tag):
            level = int(node.html_tag[1])
            parent_context = _context_string(context_stack)
            _push_heading(context_stack, level, node.text)
            yield NodeText(
                node_id=node.node_id,
                text=node.text,
                html_tag=node.html_tag,
                context=parent_context,
                node_type=node.node_type,
            )
            continue

        yield NodeText(
            node_id=node.node_id,
            text=node.text,
            html_tag=node.html_tag,
            context=_context_string(context_stack),
            node_type=node.node_type,
        )


def _is_heading(html_tag: str) -> bool:
    return len(html_tag) == 2 and html_tag[0] == "h" and html_tag[1].isdigit()


def _push_heading(stack: List[Tuple[int, str]], level: int, text: str) -> None:
    while stack and stack[-1][0] >= level:
        stack.pop()
    stack.append((level, text))


def _context_string(stack: List[Tuple[int, str]]) -> Optional[str]:
    if not stack:
        return None
    return " > ".join(text for _, text in stack)
