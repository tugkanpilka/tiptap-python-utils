"""Public TipTap content facade."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional

from .exceptions import TiptapValidationError
from .types import DocumentContent

from . import codec
from .contract import key, kind, policy
from .model import (
    Blockquote,
    BulletList,
    CodeBlock,
    Doc,
    Heading,
    ListItem,
    Node,
    OrderedList,
    Paragraph,
    TableCell,
    TaskItem,
    TaskList,
    Text,
)
from .select import Selection
from .shared import SharedFamilies
from .walk import Ref, Walker


@dataclass(frozen=True)
class Content:
    """Parsed TipTap content aggregate."""

    _tree: Optional[Dict[str, Any]]
    _root: Optional[Doc]

    @classmethod
    def parse(cls, raw: Optional[DocumentContent]) -> "Content":
        raw_object = codec.parse_raw(raw)
        if raw_object is None:
            return cls(None, None)

        root = codec.read_doc(raw_object)
        return cls(raw_object, root)

    @classmethod
    def require(cls, raw: DocumentContent) -> "Content":
        raw_object = codec.require_object(raw, label="Document content")
        if raw_object.get(key.TYPE) != kind.DOC:
            raise TiptapValidationError("Document content must be a TipTap doc")

        root = codec.read_doc(raw_object)
        if root is None:
            raise TiptapValidationError("Document content must be a TipTap doc")
        return cls(raw_object, root)

    @classmethod
    def wrap(cls, raw_node: Optional[DocumentContent]) -> "Content":
        raw_object = codec.parse_raw(raw_node)
        if raw_object is None:
            return cls(None, None)
        if raw_object.get(key.TYPE) == kind.DOC:
            return cls.parse(raw_object)
        return cls.parse({key.TYPE: kind.DOC, key.CONTENT: [raw_object]})

    @property
    def root(self) -> Optional[Doc]:
        return self._root

    @property
    def text(self) -> str:
        if self.root is None:
            return ""
        return codec.normalize_text(self.root.text)

    @property
    def tasks(self) -> list[TaskItem]:
        return self.walker().of_type(TaskItem)

    @property
    def headings(self) -> list[Heading]:
        return self.walker().of_type(Heading)

    @property
    def paragraphs(self) -> list[Paragraph]:
        return self.walker().of_type(Paragraph)

    @property
    def texts(self) -> list[Text]:
        return self.walker().of_type(Text)

    def walker(self) -> Walker:
        return Walker(self._root)

    def refs(self, *, parseable: bool = False) -> Iterator[Ref]:
        return self.walker().refs(parseable=parseable)

    def where_id(self, node_id: str) -> Selection:
        matches = [ref for ref in self.refs(parseable=True) if ref.node_id == node_id]
        if not matches:
            raise TiptapValidationError(
                f"Node with ID {node_id} not found in document content"
            )
        if len(matches) > 1:
            raise TiptapValidationError(
                f"Node with ID {node_id} appears multiple times in document content"
            )
        return Selection(self, tuple(matches))

    def of(self, node_kind: str) -> Selection:
        return Selection(
            self,
            tuple(ref for ref in self.refs() if ref.node.kind == node_kind),
        )

    def where_shared_id(self, shared_id: str) -> Selection:
        return Selection(
            self,
            tuple(
                ref
                for ref in self.refs(parseable=True)
                if ref.node.shared_id == shared_id
            ),
        )

    def has_shared(self, shared_id: str) -> bool:
        return any(
            ref.node.shared_id == shared_id for ref in self.refs(parseable=True)
        )

    def shared_families(self) -> SharedFamilies:
        return SharedFamilies.from_content(self)

    def sync_shared(self, families: SharedFamilies) -> "Content":
        if self._root is None:
            return self
        refs = tuple(
            ref
            for ref in self.refs(parseable=True)
            if ref.node.shared_id and ref.node.shared_id in families
        )
        if not refs:
            return self
        return Selection(self, refs).transform(families.merge)

    def append_root(self, node_or_raw: Any) -> "Content":
        return self.of(kind.DOC).append(node_or_raw)

    def replace_by_id(self, node_id: str, node_or_raw: Any) -> "Content":
        replacement = codec.read_node_input(node_or_raw, label="Node content")
        replacement_id = replacement.attrs.get(key.ID, "")
        if not replacement_id:
            raise TiptapValidationError("Node content must include attrs.id")
        if replacement_id != node_id:
            raise TiptapValidationError("Node content attrs.id must match path node_id")
        return self.where_id(node_id).replace(replacement)

    def dump(self) -> str:
        return json.dumps(self.to_dict())

    def to_dict(self) -> Dict[str, Any]:
        if self._root is not None:
            return self._root.raw()
        if self._tree is not None:
            return deepcopy(self._tree)
        raise TiptapValidationError("Document content is not valid")

    def word_count(self) -> int:
        return sum(len(node.text.split()) for node in _word_count_nodes(self.root))

    def _require_root(self) -> Doc:
        if self._root is None:
            raise TiptapValidationError("Document content is not valid")
        return self._root

    def _with_root(self, root: Doc) -> "Content":
        return Content(root.raw(), root)


def _word_count_nodes(root: Optional[Doc]) -> Iterator[Node]:
    if root is None:
        return
    for child in root.content:
        yield from _iter_word_count_nodes(child)


def _iter_word_count_nodes(node: Node) -> Iterator[Node]:
    if _is_countable(node):
        if _identity(node):
            yield node
        return

    if _is_container(node):
        for child in node.content:
            yield from _iter_word_count_nodes(child)


def _is_countable(node: Node) -> bool:
    return isinstance(node, (Paragraph, Heading, TaskItem, ListItem, CodeBlock))


def _is_container(node: Node) -> bool:
    return isinstance(
        node,
        (Doc, TaskList, BulletList, OrderedList, Blockquote, TableCell),
    )


def _identity(node: Node) -> str:
    if isinstance(node, TaskItem):
        return node.task_item_id
    return node.id or policy.node_id(node.attrs) or ""
