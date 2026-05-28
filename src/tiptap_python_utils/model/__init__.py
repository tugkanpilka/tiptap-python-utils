"""Typed TipTap AST model."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import Any, ClassVar, Dict, Iterator, Mapping, Tuple, TypeVar

from ..contract import key, kind, policy

ContentTuple = Tuple["Node", ...]
MarksTuple = Tuple[Any, ...]
NodeT = TypeVar("NodeT", bound="Node")


@dataclass(frozen=True)
class Node:
    """Base typed TipTap node."""

    id: str = ""
    content: ContentTuple = field(default_factory=tuple)
    attrs: Dict[str, Any] = field(default_factory=dict, compare=False, repr=False)
    extra: Dict[str, Any] = field(default_factory=dict, compare=False, repr=False)
    present: frozenset[str] = field(default_factory=frozenset, compare=False, repr=False)

    kind: ClassVar[str]

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", policy.content_id(self.attrs))

    @classmethod
    def read(cls: type[NodeT], raw: Mapping[str, Any], children: ContentTuple) -> NodeT:
        return cls(**_payload(raw, children))

    @property
    def shared_id(self) -> str | None:
        return policy.shared_id(self.attrs)

    @property
    def text(self) -> str:
        return " ".join(part for part in self.iter_text() if part)

    def iter_text(self) -> Iterator[str]:
        for child in self.content:
            yield from child.iter_text()

    def raw(self) -> Dict[str, Any]:
        raw: Dict[str, Any] = {key.TYPE: self.kind}
        raw.update(deepcopy(self.extra))

        attrs = self.raw_attrs()
        if attrs or key.ATTRS in self.present:
            raw[key.ATTRS] = attrs

        if self.content or key.CONTENT in self.present:
            raw[key.CONTENT] = [child.raw() for child in self.content]
        return raw

    def raw_attrs(self) -> Dict[str, Any]:
        attrs = deepcopy(self.attrs)
        if self.id and not _has_any_identity(attrs):
            attrs[key.ID] = self.id
        return attrs

    def with_text(self, value: str) -> "Node":
        if not self.content:
            return self
        return replace(self, content=(Text(value=value),))

    def with_attr(self, name: str, value: Any) -> "Node":
        attrs = deepcopy(self.attrs)
        attrs[name] = deepcopy(value)
        return replace(self, attrs=attrs, present=self.present | {key.ATTRS})

    def append(self, child: "Node") -> "Node":
        return replace(self, content=self.content + (child,), present=self.present | {key.CONTENT})


@dataclass(frozen=True)
class Text(Node):
    value: str = ""
    marks: MarksTuple = ()

    kind: ClassVar[str] = kind.TEXT

    @classmethod
    def read(cls, raw: Mapping[str, Any], children: ContentTuple) -> "Text":
        value = raw.get(key.TEXT, "")
        marks = raw.get(key.MARKS, [])
        return cls(
            value=value if isinstance(value, str) else str(value),
            marks=tuple(deepcopy(marks)) if isinstance(marks, list) else (),
            **_payload(raw, children, extra_keys={key.TEXT, key.MARKS}),
        )

    @property
    def text(self) -> str:
        return self.value.strip()

    def iter_text(self) -> Iterator[str]:
        if self.text:
            yield self.text

    def raw(self) -> Dict[str, Any]:
        raw = super().raw()
        if self.value or key.TEXT in self.present:
            raw[key.TEXT] = self.value
        if self.marks or key.MARKS in self.present:
            raw[key.MARKS] = [deepcopy(mark) for mark in self.marks]
        return raw

    def with_text(self, value: str) -> "Text":
        return replace(self, value=value, present=self.present | {key.TEXT})


@dataclass(frozen=True)
class Doc(Node):
    kind: ClassVar[str] = kind.DOC


@dataclass(frozen=True)
class Paragraph(Node):
    kind: ClassVar[str] = kind.PARAGRAPH


@dataclass(frozen=True)
class Heading(Node):
    level: int = 1

    kind: ClassVar[str] = kind.HEADING

    @classmethod
    def read(cls, raw: Mapping[str, Any], children: ContentTuple) -> "Heading":
        return cls(level=_heading_level(raw), **_payload(raw, children))

    def raw_attrs(self) -> Dict[str, Any]:
        attrs = super().raw_attrs()
        if key.LEVEL in attrs or key.ATTRS not in self.present:
            attrs.setdefault(key.LEVEL, self.level)
        return attrs


@dataclass(frozen=True)
class TaskItem(Node):
    task_item_id: str = ""
    is_completed: bool = False
    local_task_item_id: str = ""
    canonical_task_item_id: str = ""
    is_linked_copy: bool = False

    kind: ClassVar[str] = kind.TASK_ITEM

    @classmethod
    def read(cls, raw: Mapping[str, Any], children: ContentTuple) -> "TaskItem":
        completed = _task_completion(raw)
        local_id = policy.content_id(raw.get(key.ATTRS, {}))
        canonical_id = _task_canonical_id(raw, local_id)
        return cls(
            task_item_id=canonical_id,
            is_completed=bool(completed),
            local_task_item_id=local_id,
            canonical_task_item_id=canonical_id,
            is_linked_copy=bool(local_id and canonical_id and local_id != canonical_id),
            **_payload(raw, children),
        )

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.local_task_item_id and self.task_item_id:
            object.__setattr__(self, "local_task_item_id", self.task_item_id)
        if not self.canonical_task_item_id and self.task_item_id:
            object.__setattr__(self, "canonical_task_item_id", self.task_item_id)
        if (
            not self.is_linked_copy
            and self.local_task_item_id
            and self.canonical_task_item_id
            and self.local_task_item_id != self.canonical_task_item_id
        ):
            object.__setattr__(self, "is_linked_copy", True)

    @property
    def shared_id(self) -> str | None:
        return policy.shared_id(self.attrs)

    def raw_attrs(self) -> Dict[str, Any]:
        attrs = super().raw_attrs()
        if self.local_task_item_id and not _has_any_identity(attrs):
            attrs[key.ID] = self.local_task_item_id
        if self.canonical_task_item_id and (
            key.TASK_CANONICAL_ID in attrs
            or self.canonical_task_item_id != self.local_task_item_id
        ):
            attrs.setdefault(key.TASK_CANONICAL_ID, self.canonical_task_item_id)
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
        return cls(raw_kind=str(raw.get(key.TYPE, "")), **_payload(raw, children))

    @property
    def kind(self) -> str:
        return self.raw_kind


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


def _payload(
    raw: Mapping[str, Any],
    children: ContentTuple,
    *,
    extra_keys: set[str] | None = None,
) -> dict[str, Any]:
    present = frozenset(str(name) for name in raw.keys())
    known = {key.TYPE, key.ATTRS, key.CONTENT} | (extra_keys or set())
    attrs = raw.get(key.ATTRS, {})
    return {
        "id": policy.content_id(attrs),
        "content": children,
        "attrs": deepcopy(attrs) if isinstance(attrs, dict) else {},
        "extra": {name: deepcopy(value) for name, value in raw.items() if name not in known},
        "present": present,
    }


def _heading_level(raw: Mapping[str, Any]) -> int:
    attrs = raw.get(key.ATTRS, {})
    level = attrs.get(key.LEVEL, 1) if isinstance(attrs, dict) else 1
    return level if isinstance(level, int) and 1 <= level <= 6 else 1


def _task_canonical_id(raw: Mapping[str, Any], fallback: str) -> str:
    attrs = raw.get(key.ATTRS, {})
    if not isinstance(attrs, dict):
        return fallback

    canonical_id = attrs.get(key.TASK_CANONICAL_ID)
    if isinstance(canonical_id, str):
        stripped = canonical_id.strip()
        if stripped:
            return stripped
    if canonical_id is not None:
        return str(canonical_id)
    return fallback


def _task_completion(raw: Mapping[str, Any]) -> bool | None:
    status = raw.get(key.STATUS)
    if isinstance(status, str) and status.lower() in {"done", "pending"}:
        return status.lower() == "done"

    attrs = raw.get(key.ATTRS, {})
    if not isinstance(attrs, dict):
        attrs = {}

    status = attrs.get(key.STATUS)
    if isinstance(status, str) and status.lower() in {"done", "pending"}:
        return status.lower() == "done"

    checked = attrs.get(key.CHECKED)
    if isinstance(checked, bool):
        return checked
    if isinstance(checked, str) and checked.strip().lower() in {"true", "false"}:
        return checked.strip().lower() == "true"
    return None


def _has_any_identity(attrs: Dict[str, Any]) -> bool:
    return key.ID in attrs or key.TIPTAP_ID in attrs
