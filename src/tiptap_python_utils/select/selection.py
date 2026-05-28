"""Fluent TipTap selection API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterator, Tuple

from ..exceptions import TiptapValidationError

from .. import codec
from ..edit import append_child, set_attr, set_key, set_text
from ..model import Doc, Node
from ..tree import node_at_path, replace_at_path
from ..walk import Ref

if TYPE_CHECKING:
    from ..content import Content


class Selection:
    """A selected set of TipTap nodes that can be edited immutably."""

    def __init__(self, content: "Content", refs: Tuple[Ref, ...]) -> None:
        self._content = content
        self._refs = refs

    def __iter__(self) -> Iterator[Ref]:
        return iter(self._refs)

    def __len__(self) -> int:
        return len(self._refs)

    @property
    def refs(self) -> Tuple[Ref, ...]:
        return self._refs

    @property
    def nodes(self) -> Tuple[Node, ...]:
        return tuple(ref.node for ref in self._refs)

    def text(self, value: str) -> "Content":
        return self._apply(lambda node: set_text(node, value))

    def set(self, name: str, value: Any) -> "Content":
        return self._apply(lambda node: set_key(node, name, value))

    def attr(self, name: str, value: Any) -> "Content":
        return self._apply(lambda node: set_attr(node, name, value))

    def replace(self, node_or_raw: Any) -> "Content":
        replacement = codec.read_node_input(node_or_raw, label="Node content")
        return self._apply(lambda _node: replacement)

    def append(self, node_or_raw: Any) -> "Content":
        child = codec.read_node_input(node_or_raw, label="Node content")
        if isinstance(child, Doc):
            raise TiptapValidationError("Child node content must not be a document root")
        return self._apply(lambda node: append_child(node, child))

    def dump(self) -> str:
        return self._content.dump()

    def _apply(self, transform: Any) -> "Content":
        root = self._content._require_root()
        updated: Node = root

        for ref in sorted(self._refs, key=lambda item: len(item.path), reverse=True):
            current = node_at_path(updated, ref.path)
            updated = replace_at_path(updated, ref.path, transform(current))

        if not isinstance(updated, Doc):
            raise TiptapValidationError("Document root must remain a TipTap doc")
        return self._content._with_root(updated)
