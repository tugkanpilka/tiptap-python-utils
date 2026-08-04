"""Visible text extraction for TipTap content."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..content import Content
from .tracked import tracked_blocks


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
    return sum(block.word_count for block in tracked_blocks(content))


def text_slices(content: Content, *, context: bool = False) -> List[NodeText]:
    return [
        NodeText(
            node_id=block.local_id,
            text=block.text,
            html_tag=block.html_tag,
            context=block.context,
            node_type=block.node_type,
        )
        for block in tracked_blocks(content, context=context)
    ]
