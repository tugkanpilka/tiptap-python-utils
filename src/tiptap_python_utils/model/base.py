"""Foundational typed-AST primitives: type aliases, ``Node`` and ``Text``.

``Text`` lives here (and not in ``nodes``) because ``Node.with_text``
references it; co-locating them keeps the base layer free of lazy imports.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import Any, ClassVar, Dict, Iterator, Mapping, Tuple, TypeVar

from ..contract import key, kind, policy
from ..exceptions import TiptapValidationError
from .payload import has_any_identity, payload

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
        return cls(**payload(raw, children))

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
        if self.id and not has_any_identity(attrs):
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

    def with_content(self, content: ContentTuple) -> "Node":
        return replace(self, content=content, present=self.present | {key.CONTENT})

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
            **payload(raw, children, extra_keys={key.TEXT, key.MARKS}),
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

    def with_marks(self, marks: MarksTuple) -> "Text":
        return replace(
            self,
            marks=tuple(deepcopy(mark) for mark in marks),
            present=self.present | {key.MARKS},
        )

    def append(self, child: "Node") -> "Node":
        raise TiptapValidationError("Text nodes cannot contain child nodes")

    def with_content(self, content: ContentTuple) -> "Node":
        raise TiptapValidationError("Text nodes cannot contain child nodes")
