"""Phase 3 acceptance: raw codec layer must be testable without the typed AST.

These tests import only from ``tiptap_python_utils.codec.raw`` so a regression
that pulls a ``..model`` dependency into the raw layer would surface as an
ImportError at collection time, not a behavioural failure.
"""

from __future__ import annotations

import sys

import pytest

from tiptap_python_utils.codec.raw import (
    normalize_text,
    parse_raw,
    raw_node_id,
    raw_text,
    require_object,
)
from tiptap_python_utils.exceptions import TiptapValidationError

pytestmark = [pytest.mark.unit]


def test_raw_module_does_not_import_model() -> None:
    raw_module = sys.modules["tiptap_python_utils.codec.raw"]
    assert "tiptap_python_utils.model" not in (
        getattr(raw_module, "__dict__", {}).get("__annotations__", {})
    )
    for attr in vars(raw_module).values():
        module_name = getattr(attr, "__module__", "")
        assert not module_name.startswith("tiptap_python_utils.model"), attr


def test_parse_raw_returns_none_for_invalid_json() -> None:
    assert parse_raw("{invalid") is None
    assert parse_raw(None) is None
    assert parse_raw("[]") is None


def test_parse_raw_deep_copies_dict_input() -> None:
    payload = {"type": "doc", "content": []}
    parsed = parse_raw(payload)
    assert parsed == payload
    assert parsed is not payload
    parsed["content"].append({"type": "paragraph"})
    assert payload["content"] == []


def test_require_object_rejects_invalid_json_with_label() -> None:
    with pytest.raises(TiptapValidationError, match="Document is not valid JSON"):
        require_object("{invalid", label="Document")


def test_require_object_rejects_non_object_payload() -> None:
    with pytest.raises(TiptapValidationError, match="Node must be a JSON object"):
        require_object("[]", label="Node")


def test_require_object_returns_independent_copy() -> None:
    payload = {"type": "paragraph", "attrs": {"id": "p1"}}
    parsed = require_object(payload, label="Node")
    parsed["attrs"]["id"] = "mutated"
    assert payload["attrs"]["id"] == "p1"


def test_raw_node_id_reads_attrs_id() -> None:
    assert raw_node_id({"type": "paragraph", "attrs": {"id": "p1"}}) == "p1"
    assert raw_node_id({"type": "paragraph"}) == ""


def test_raw_text_joins_descendant_text_nodes() -> None:
    payload = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Hello"}]},
            {"type": "paragraph", "content": [{"type": "text", "text": " world "}]},
        ],
    }
    assert raw_text(payload) == "Hello world"


def test_raw_text_ignores_non_dict_children() -> None:
    payload = {"type": "doc", "content": [None, {"type": "text", "text": "ok"}]}
    assert raw_text(payload) == "ok"


def test_normalize_text_collapses_whitespace() -> None:
    assert normalize_text("  hello\tworld\n") == "hello world"
