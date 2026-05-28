"""Concrete TipTap node classes built on top of ``Node``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Dict, Mapping

from ..contract import key, kind, policy
from .base import ContentTuple, Node
from .payload import (
    heading_level,
    payload,
    task_canonical_id,
    task_completion,
)


@dataclass(frozen=True)
class Doc(Node):
    kind: ClassVar[str] = kind.DOC


@dataclass(frozen=True)
class Paragraph(Node):
    kind: ClassVar[str] = kind.PARAGRAPH


@dataclass(frozen=True)
class Heading(Node):
    kind: ClassVar[str] = kind.HEADING

    @property
    def level(self) -> int:
        return heading_level(self.attrs)

    def raw_attrs(self) -> Dict[str, Any]:
        attrs = super().raw_attrs()
        if key.LEVEL in attrs or key.ATTRS not in self.present:
            attrs.setdefault(key.LEVEL, self.level)
        return attrs


@dataclass(frozen=True)
class TaskItem(Node):
    kind: ClassVar[str] = kind.TASK_ITEM

    @property
    def local_task_item_id(self) -> str:
        return policy.content_id(self.attrs)

    @property
    def canonical_task_item_id(self) -> str:
        return task_canonical_id(self.attrs, self.local_task_item_id)

    @property
    def task_item_id(self) -> str:
        return self.canonical_task_item_id

    @property
    def is_linked_copy(self) -> bool:
        local = self.local_task_item_id
        canonical = self.canonical_task_item_id
        return bool(local and canonical and local != canonical)

    @property
    def is_completed(self) -> bool:
        return bool(task_completion(self.attrs, self.extra))

    def raw_attrs(self) -> Dict[str, Any]:
        attrs = super().raw_attrs()
        if key.CHECKED in attrs or (
            key.ATTRS not in self.present and key.STATUS not in self.extra
        ):
            attrs.setdefault(key.CHECKED, self.is_completed)
        return attrs


@dataclass(frozen=True)
class ListItem(Node):
    kind: ClassVar[str] = kind.LIST_ITEM


@dataclass(frozen=True)
class CodeBlock(Node):
    kind: ClassVar[str] = kind.CODE_BLOCK


@dataclass(frozen=True)
class TaskList(Node):
    kind: ClassVar[str] = kind.TASK_LIST


@dataclass(frozen=True)
class BulletList(Node):
    kind: ClassVar[str] = kind.BULLET_LIST


@dataclass(frozen=True)
class OrderedList(Node):
    kind: ClassVar[str] = kind.ORDERED_LIST


@dataclass(frozen=True)
class Blockquote(Node):
    kind: ClassVar[str] = kind.BLOCKQUOTE


@dataclass(frozen=True)
class TableCell(Node):
    kind: ClassVar[str] = kind.TABLE_CELL


@dataclass(frozen=True)
class Unknown(Node):
    raw_kind: str = ""

    @classmethod
    def read(cls, raw: Mapping[str, Any], children: ContentTuple) -> "Unknown":
        return cls(raw_kind=str(raw.get(key.TYPE, "")), **payload(raw, children))

    @property
    def kind(self) -> str:
        return self.raw_kind
