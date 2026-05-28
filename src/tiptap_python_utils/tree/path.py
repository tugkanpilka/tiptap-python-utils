"""Immutable tree path operations for typed TipTap nodes."""

from __future__ import annotations

from dataclasses import replace
from typing import Tuple

from ..exceptions import TiptapValidationError

from ..contract import key
from ..model import Node


def node_at_path(node: Node, path: Tuple[int, ...]) -> Node:
    current = node
    for index in path:
        try:
            current = current.content[index]
        except IndexError as exc:
            raise TiptapValidationError(
                "TipTap selection path is no longer valid"
            ) from exc
    return current


def replace_at_path(node: Node, path: Tuple[int, ...], replacement_node: Node) -> Node:
    if not path:
        return replacement_node

    index = path[0]
    content = list(node.content)
    if index >= len(content):
        raise TiptapValidationError("TipTap selection path is no longer valid")

    content[index] = replace_at_path(content[index], path[1:], replacement_node)
    return replace(node, content=tuple(content), present=node.present | {key.CONTENT})
