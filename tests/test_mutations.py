"""Unit tests for TipTap mutation operations."""

from __future__ import annotations

import json

import pytest

from tiptap_python_utils import (
    Content,
    TiptapValidationError,
    has_shared,
    new_shared_id,
    shared_families,
    shared_id,
    stamp_shared,
    sync_shared,
)

pytestmark = [pytest.mark.unit]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _paragraph(node_id: str, text: str) -> dict:
    return {
        "type": "paragraph",
        "attrs": {"id": node_id},
        "content": [{"type": "text", "text": text}],
    }


def _doc(*nodes: dict) -> str:
    return json.dumps({"type": "doc", "content": list(nodes)})


# ---------------------------------------------------------------------------
# shared_families
# ---------------------------------------------------------------------------


def test_shared_families_should_reject_conflicts():
    content = json.dumps(
        {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"id": "n1", "sharedId": "shared-1"},
                    "content": [{"type": "text", "text": "one"}],
                },
                {
                    "type": "paragraph",
                    "attrs": {"id": "n2", "sharedId": "shared-1"},
                    "content": [{"type": "text", "text": "two"}],
                },
            ],
        }
    )

    with pytest.raises(TiptapValidationError, match="Conflicting node bodies detected"):
        shared_families(content)


# ---------------------------------------------------------------------------
# sync_shared
# ---------------------------------------------------------------------------


def test_sync_shared_should_preserve_local_ids():
    source = json.dumps(
        {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"id": "source-id", "sharedId": "shared-1"},
                    "content": [{"type": "text", "text": "new"}],
                }
            ],
        }
    )
    target = json.dumps(
        {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"id": "target-id", "sharedId": "shared-1"},
                    "content": [{"type": "text", "text": "old"}],
                }
            ],
        }
    )

    rewritten, changed = sync_shared(target, shared_families(source))
    payload = json.loads(rewritten)
    rewritten_node = payload["content"][0]

    assert changed is True
    assert rewritten_node["attrs"]["id"] == "target-id"
    assert rewritten_node["attrs"]["sharedId"] == "shared-1"
    assert rewritten_node["content"][0]["text"] == "new"


# ---------------------------------------------------------------------------
# stamp_shared
# ---------------------------------------------------------------------------


def test_stamp_shared_stamps_shared_id():
    node = {"type": "paragraph", "attrs": {"id": "n1"}, "content": []}

    result = stamp_shared(node, shared_id="shared-99")

    assert result["attrs"]["sharedId"] == "shared-99"
    assert result["attrs"]["id"] == "n1"


def test_stamp_shared_overrides_local_id():
    node = {"type": "heading", "attrs": {"id": "old-id"}, "content": []}

    result = stamp_shared(node, shared_id="shared-1", local_id="new-id")

    assert result["attrs"]["id"] == "new-id"
    assert result["attrs"]["sharedId"] == "shared-1"


def test_stamp_shared_preserves_existing_attrs():
    node = {
        "type": "paragraph",
        "attrs": {"id": "n1", "level": 2, "color": "red"},
        "content": [],
    }

    result = stamp_shared(node, shared_id="shared-5")

    assert result["attrs"]["level"] == 2
    assert result["attrs"]["color"] == "red"
    assert result["attrs"]["sharedId"] == "shared-5"
    assert node["attrs"].get("sharedId") is None


# ---------------------------------------------------------------------------
# append_node
# ---------------------------------------------------------------------------


def test_append_node_appends_to_root_content():
    document = json.dumps(
        {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"id": "p1"},
                    "content": [{"type": "text", "text": "existing"}],
                }
            ],
        }
    )
    new_node = {
        "type": "heading",
        "attrs": {"id": "h1"},
        "content": [{"type": "text", "text": "appended"}],
    }

    result = json.loads(Content.require(document).append_root(new_node).dump())

    assert len(result["content"]) == 2
    assert result["content"][0]["attrs"]["id"] == "p1"
    assert result["content"][1]["attrs"]["id"] == "h1"
    assert result["content"][1]["content"][0]["text"] == "appended"


def test_append_node_to_empty_document():
    document = json.dumps({"type": "doc", "content": []})
    new_node = {
        "type": "paragraph",
        "attrs": {"id": "p1"},
        "content": [{"type": "text", "text": "first"}],
    }

    result = json.loads(Content.require(document).append_root(new_node).dump())

    assert len(result["content"]) == 1
    assert result["content"][0]["attrs"]["id"] == "p1"


# ---------------------------------------------------------------------------
# has_shared
# ---------------------------------------------------------------------------


def test_has_shared_true_when_present():
    content = json.dumps(
        {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"id": "n1", "sharedId": "shared-abc"},
                    "content": [],
                }
            ],
        }
    )

    assert has_shared(content, shared_id="shared-abc") is True


def test_has_shared_false_when_absent():
    content = json.dumps(
        {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"id": "n1", "sharedId": "shared-other"},
                    "content": [],
                }
            ],
        }
    )

    assert has_shared(content, shared_id="shared-abc") is False


def test_has_shared_finds_nested_nodes():
    content = json.dumps(
        {
            "type": "doc",
            "content": [
                {
                    "type": "blockquote",
                    "content": [
                        {
                            "type": "heading",
                            "attrs": {"id": "h1", "sharedId": "shared-nested"},
                            "content": [{"type": "text", "text": "deep"}],
                        }
                    ],
                }
            ],
        }
    )

    assert has_shared(content, shared_id="shared-nested") is True


# ---------------------------------------------------------------------------
# shared_id
# ---------------------------------------------------------------------------


def test_shared_id_returns_existing():
    node = json.dumps(
        {"type": "paragraph", "attrs": {"id": "n1", "sharedId": "shared-42"}, "content": []}
    )
    assert shared_id(node) == "shared-42"


def test_shared_id_returns_none_when_absent():
    node = json.dumps({"type": "paragraph", "attrs": {"id": "n1"}, "content": []})
    assert shared_id(node) is None


# ---------------------------------------------------------------------------
# new_shared_id
# ---------------------------------------------------------------------------


def test_new_shared_id_returns_prefixed_unique_id():
    result = new_shared_id()

    assert result.startswith("shared-")
    assert len(result) > len("shared-")


def test_new_shared_id_returns_unique_values():
    assert new_shared_id() != new_shared_id()


# ---------------------------------------------------------------------------
# replace_node
# ---------------------------------------------------------------------------


def test_replace_node_replaces_target_node():
    updated = (
        Content.require(_doc(_paragraph("node-1", "old")))
        .replace_by_id("node-1", json.dumps(_paragraph("node-1", "new")))
        .dump()
    )

    payload = json.loads(updated)
    assert payload["content"][0]["attrs"]["id"] == "node-1"
    assert payload["content"][0]["content"][0]["text"] == "new"


def test_replace_node_rejects_mismatched_ids():
    with pytest.raises(
        TiptapValidationError,
        match="Node content attrs.id must match path node_id",
    ):
        Content.require(_doc(_paragraph("node-1", "old"))).replace_by_id(
            "node-1", json.dumps(_paragraph("node-2", "new"))
        )


def test_replace_node_rejects_duplicate_target_occurrences():
    with pytest.raises(
        TiptapValidationError,
        match="appears multiple times in document content",
    ):
        Content.require(
            _doc(_paragraph("node-1", "old"), _paragraph("node-1", "other"))
        ).replace_by_id("node-1", json.dumps(_paragraph("node-1", "new")))


def test_replace_node_rejects_missing_target():
    with pytest.raises(
        TiptapValidationError,
        match="Node with ID node-1 not found in document content",
    ):
        Content.require(_doc(_paragraph("node-2", "old"))).replace_by_id(
            "node-1", json.dumps(_paragraph("node-1", "new"))
        )
