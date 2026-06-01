"""Fluent TipTap selection API."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import TYPE_CHECKING, Any, Callable, Iterator, Tuple

from .. import codec
from ..contract import key
from ..exceptions import TiptapValidationError
from ..model import Doc, Node, Text
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

    def leaf(self) -> "Selection":
        """Descend each ref to its first Text descendant."""
        leaves = tuple(leaf for ref in self._refs for leaf in _first_text_descendant(ref))
        return Selection(self._content, leaves)

    def filter(self, pred: Callable[[Node], bool]) -> "Selection":
        """Narrow the selection to refs whose node matches ``pred``."""
        return Selection(self._content, tuple(r for r in self._refs if pred(r.node)))

    def any(self, pred: Callable[[Node], bool] = lambda _node: True) -> bool:
        """True if any selected node matches ``pred`` (short-circuits)."""
        return any(pred(r.node) for r in self._refs)

    def text(self, value: str) -> "Content":
        self._require_text_only("text")
        return self._apply(lambda node: node.with_text(value))

    def marks(self, marks: Any) -> "Content":
        if not isinstance(marks, list):
            raise TiptapValidationError("TipTap marks must be a list")
        self._require_text_only("marks")
        return self._apply(lambda node: node.with_marks(tuple(marks)))

    def attr(self, name: str, value: Any) -> "Content":
        return self._apply(lambda node: node.with_attr(name, value))

    def set(self, name: str, value: Any) -> "Content":
        return self._apply(lambda node: _set_raw_key(node, name, value))

    def replace(self, node_or_raw: Any) -> "Content":
        replacement = codec.read_node_input(node_or_raw, label="Node content")
        return self._apply(lambda _node: replacement)

    def append(self, node_or_raw: Any) -> "Content":
        child = codec.read_node_input(node_or_raw, label="Node content")
        if isinstance(child, Doc):
            raise TiptapValidationError("Child node content must not be a document root")
        return self._apply(lambda node: node.append(child))

    def transform(self, fn: Callable[[Node], Node]) -> "Content":
        return self._apply(fn)

    def dump(self) -> str:
        return self._content.dump()

    def _require_text_only(self, op: str) -> None:
        for ref in self._refs:
            if not isinstance(ref.node, Text):
                raise TiptapValidationError(
                    f"Selection.{op}() requires Text refs; chain .leaf() first"
                )

    def _apply(self, transform: Any) -> "Content":
        root = self._content._require_root()
        updated: Node = root

        for ref in sorted(self._refs, key=lambda item: len(item.path), reverse=True):
            current = node_at_path(updated, ref.path)
            updated = replace_at_path(updated, ref.path, transform(current))

        if not isinstance(updated, Doc):
            raise TiptapValidationError("Document root must remain a TipTap doc")
        return self._content._with_root(updated)


def _first_text_descendant(ref: Ref) -> Tuple[Ref, ...]:
    if isinstance(ref.node, Text):
        return (ref,)
    for index, child in enumerate(ref.node.content):
        descended = _first_text_descendant(
            Ref(node=child, path=ref.path + (index,), parent_kind=ref.node.kind)
        )
        if descended:
            return descended
    return ()


def _set_raw_key(node: Node, name: str, value: Any) -> Node:
    if name == key.TYPE:
        raise TiptapValidationError("TipTap node type cannot be updated")
    if name == key.ATTRS and not isinstance(value, dict):
        raise TiptapValidationError("TipTap attrs must be a JSON object")
    if name == key.CONTENT and not isinstance(value, list):
        raise TiptapValidationError("TipTap content must be a list")
    if name == key.TEXT and not isinstance(node, Text):
        raise TiptapValidationError(
            "Selection.set('text', ...) requires Text refs; chain .leaf() first"
        )
    if name == key.MARKS:
        if not isinstance(node, Text):
            raise TiptapValidationError("TipTap marks apply only to Text nodes")
        if not isinstance(value, list):
            raise TiptapValidationError("TipTap marks must be a list")
        return replace(
            node,
            marks=tuple(deepcopy(mark) for mark in value),
            present=node.present | {key.MARKS},
        )

    # Round-trip through codec so subclass-typed fields (e.g. Heading.level)
    # are re-hydrated from the new raw payload. Polymorphic over all node types.
    raw = node.raw()
    raw[name] = deepcopy(value)
    return codec.read_node(raw)
