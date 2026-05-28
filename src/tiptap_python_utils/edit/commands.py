"""Pure immutable TipTap edit commands."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..exceptions import TiptapValidationError

from .. import codec
from ..contract import key
from ..model import Doc, Node, Text


def set_text(node: Node, value: Any) -> Node:
    text_value = value if isinstance(value, str) else str(value)
    if isinstance(node, Text):
        return node.with_text(text_value)
    if isinstance(node, Doc):
        raise TiptapValidationError("Document node does not support text updates")

    direct_texts = [child for child in node.content if isinstance(child, Text)]
    if direct_texts:
        return node.__class__(
            **{
                **_clone_payload(node),
                "content": (direct_texts[0].with_text(text_value),),
                "present": node.present | {key.CONTENT},
            }
        )

    for index, child in enumerate(node.content):
        try:
            updated_child = set_text(child, text_value)
        except TiptapValidationError:
            continue
        content = list(node.content)
        content[index] = updated_child
        return node.__class__(
            **{
                **_clone_payload(node),
                "content": tuple(content),
                "present": node.present | {key.CONTENT},
            }
        )

    return node.__class__(
        **{
            **_clone_payload(node),
            "content": (Text(value=text_value),),
            "present": node.present | {key.CONTENT},
        }
    )


def set_key(node: Node, name: str, value: Any) -> Node:
    if name == key.TEXT:
        return set_text(node, value)
    if name == key.TYPE:
        raise TiptapValidationError("TipTap node type cannot be updated")
    if name == key.ATTRS and not isinstance(value, dict):
        raise TiptapValidationError("TipTap attrs must be a JSON object")
    if name == key.CONTENT and not isinstance(value, list):
        raise TiptapValidationError("TipTap content must be a list")
    if name == key.MARKS and isinstance(node, Text):
        if not isinstance(value, list):
            raise TiptapValidationError("TipTap marks must be a list")
        return Text(
            value=node.value,
            marks=tuple(deepcopy(mark) for mark in value),
            content=node.content,
            attrs=node.attrs,
            extra=node.extra,
            present=node.present | {key.MARKS},
        )

    raw = node.raw()
    raw[name] = deepcopy(value)
    return codec.read_node(raw)


def set_attr(node: Node, name: str, value: Any) -> Node:
    return node.with_attr(name, value)


def append_child(node: Node, child: Node) -> Node:
    if isinstance(node, Text):
        raise TiptapValidationError("Text nodes cannot contain child nodes")
    return node.append(child)


def append_node(content: str | dict[str, Any], node: str | dict[str, Any] | Node) -> str:
    """Append a node to the document root content."""
    from ..content import Content

    document = codec.require_object(content, label="Document content")
    root_content = document.get(key.CONTENT, [])
    if not isinstance(root_content, list):
        raise TiptapValidationError("Document content must contain a content list")
    return Content.require(document).of("doc").append(node).dump()


def replace_node(
    content: str | dict[str, Any],
    node_id: str,
    node: str | dict[str, Any] | Node,
) -> str:
    """Replace one parseable node by local attrs.id."""
    from ..content import Content

    document = codec.require_object(content, label="Document content")
    replacement_raw = (
        node.raw() if isinstance(node, Node) else codec.require_object(node, label="Node content")
    )
    replacement_id = codec.raw_node_id(replacement_raw)
    if not replacement_id:
        raise TiptapValidationError("Node content must include attrs.id")
    if replacement_id != node_id:
        raise TiptapValidationError("Node content attrs.id must match path node_id")

    root_content = document.get(key.CONTENT, [])
    if not isinstance(root_content, list):
        raise TiptapValidationError("Document content must contain a content list")

    tiptap = Content.require(document)
    matches = [
        ref
        for ref in tiptap.refs(parseable=True)
        if ref.node.attrs.get(key.ID) == node_id
    ]
    if not matches:
        raise TiptapValidationError(
            f"Node with ID {node_id} not found in document content"
        )
    if len(matches) > 1:
        raise TiptapValidationError(
            f"Node with ID {node_id} appears multiple times in document content"
        )

    return tiptap.where_id(node_id).replace(replacement_raw).dump()


def _clone_payload(node: Node) -> dict[str, Any]:
    payload = {
        "id": node.id,
        "attrs": deepcopy(node.attrs),
        "extra": deepcopy(node.extra),
    }
    if hasattr(node, "level"):
        payload["level"] = getattr(node, "level")
    if hasattr(node, "task_item_id"):
        payload.update(
            {
                "task_item_id": getattr(node, "task_item_id"),
                "is_completed": getattr(node, "is_completed"),
                "local_task_item_id": getattr(node, "local_task_item_id"),
                "canonical_task_item_id": getattr(node, "canonical_task_item_id"),
                "is_linked_copy": getattr(node, "is_linked_copy"),
            }
        )
    if hasattr(node, "raw_kind"):
        payload["raw_kind"] = getattr(node, "raw_kind")
    return payload
