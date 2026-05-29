"""Unit tests for TipTap mutation operations."""

from __future__ import annotations

import json

import pytest

from tiptap_python_utils import (
    Content,
    TiptapValidationError,
    new_shared_id,
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
# Content.shared_families
# ---------------------------------------------------------------------------


def test_shared_families_should_reject_conflicts():
    content = Content.require(
        json.dumps(
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
    )

    with pytest.raises(TiptapValidationError, match="Conflicting node bodies detected"):
        content.shared_families()


# ---------------------------------------------------------------------------
# Content.sync_shared
# ---------------------------------------------------------------------------


def test_sync_shared_should_preserve_local_ids():
    source = Content.require(
        json.dumps(
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
    )
    target = Content.require(
        json.dumps(
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
    )

    rewritten = target.sync_shared(source.shared_families())
    rewritten_node = json.loads(rewritten.dump())["content"][0]

    assert rewritten_node["attrs"]["id"] == "target-id"
    assert rewritten_node["attrs"]["sharedId"] == "shared-1"
    assert rewritten_node["content"][0]["text"] == "new"


def test_sync_shared_no_op_when_no_matching_shared_id():
    target = Content.require(
        json.dumps(
            {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "attrs": {"id": "p1", "sharedId": "shared-x"},
                        "content": [{"type": "text", "text": "keep"}],
                    }
                ],
            }
        )
    )
    source = Content.require(
        json.dumps(
            {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "attrs": {"id": "s1", "sharedId": "shared-y"},
                        "content": [{"type": "text", "text": "other"}],
                    }
                ],
            }
        )
    )

    rewritten = target.sync_shared(source.shared_families())

    assert rewritten.dump() == target.dump()


# ---------------------------------------------------------------------------
# Self-describing shared core: `shared` (family-identical) + `place` (per-copy)
# ---------------------------------------------------------------------------


def test_shared_families_ignores_shared_and_place_when_fingerprinting():
    # Two members of one family, identical body text, but differing per-copy
    # `place` and differing `shared` core. These keys are provenance, not body,
    # so the fingerprint must ignore them and NOT flag a conflict.
    content = Content.require(
        json.dumps(
            {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "attrs": {
                            "id": "n1",
                            "sharedId": "shared-1",
                            "shared": {"id": "shared-1", "topics": ["a"]},
                            "place": {"context": "dated_note", "topicId": None},
                        },
                        "content": [{"type": "text", "text": "same body"}],
                    },
                    {
                        "type": "paragraph",
                        "attrs": {
                            "id": "n2",
                            "sharedId": "shared-1",
                            "shared": {"id": "shared-1", "topics": ["b"]},
                            "place": {"context": "undated_note", "topicId": "t-1"},
                        },
                        "content": [{"type": "text", "text": "same body"}],
                    },
                ],
            }
        )
    )

    families = content.shared_families()

    assert "shared-1" in families


def test_shared_families_still_rejects_real_body_divergence_despite_place():
    # Differing `place` must not mask a genuine body difference: the text still
    # differs, so this remains a conflict (guards against over-stripping).
    content = Content.require(
        json.dumps(
            {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "attrs": {
                            "id": "n1",
                            "sharedId": "shared-1",
                            "place": {"context": "dated_note", "topicId": None},
                        },
                        "content": [{"type": "text", "text": "one"}],
                    },
                    {
                        "type": "paragraph",
                        "attrs": {
                            "id": "n2",
                            "sharedId": "shared-1",
                            "place": {"context": "undated_note", "topicId": "t-1"},
                        },
                        "content": [{"type": "text", "text": "two"}],
                    },
                ],
            }
        )
    )

    with pytest.raises(TiptapValidationError, match="Conflicting node bodies detected"):
        content.shared_families()


def test_sync_shared_preserves_per_copy_place_and_carries_shared_core():
    source = Content.require(
        json.dumps(
            {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "attrs": {
                            "id": "source-id",
                            "sharedId": "shared-1",
                            "shared": {"id": "shared-1", "primaryTopic": "t-react"},
                            "place": {"context": "dated_note", "topicId": None},
                        },
                        "content": [{"type": "text", "text": "new"}],
                    }
                ],
            }
        )
    )
    target = Content.require(
        json.dumps(
            {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "attrs": {
                            "id": "target-id",
                            "sharedId": "shared-1",
                            "shared": {"id": "shared-1", "primaryTopic": "STALE"},
                            "place": {"context": "undated_note", "topicId": "t-react"},
                        },
                        "content": [{"type": "text", "text": "old"}],
                    }
                ],
            }
        )
    )

    rewritten = target.sync_shared(source.shared_families())
    node = json.loads(rewritten.dump())["content"][0]

    # Body + family-identical `shared` core come from the canonical (source).
    assert node["content"][0]["text"] == "new"
    assert node["attrs"]["shared"]["primaryTopic"] == "t-react"
    # Per-copy identity and `place` stay the target's own.
    assert node["attrs"]["id"] == "target-id"
    assert node["attrs"]["place"] == {"context": "undated_note", "topicId": "t-react"}


# ---------------------------------------------------------------------------
# Node.with_shared_id
# ---------------------------------------------------------------------------


def test_with_shared_id_stamps_shared_id():
    paragraph = Content.wrap(
        {"type": "paragraph", "attrs": {"id": "n1"}, "content": []}
    ).root.content[0]

    stamped = paragraph.with_shared_id("shared-99")

    assert stamped.shared_id == "shared-99"
    assert stamped.id == "n1"


def test_with_shared_id_preserves_existing_attrs():
    paragraph = Content.wrap(
        {
            "type": "paragraph",
            "attrs": {"id": "n1", "level": 2, "color": "red"},
            "content": [],
        }
    ).root.content[0]

    stamped = paragraph.with_shared_id("shared-5")

    assert stamped.attrs["level"] == 2
    assert stamped.attrs["color"] == "red"
    assert stamped.shared_id == "shared-5"
    assert paragraph.shared_id is None


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
# Content.has_shared
# ---------------------------------------------------------------------------


def test_has_shared_true_when_present():
    content = Content.require(
        json.dumps(
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
    )

    assert content.has_shared("shared-abc") is True


def test_has_shared_false_when_absent():
    content = Content.require(
        json.dumps(
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
    )

    assert content.has_shared("shared-abc") is False


def test_has_shared_finds_nested_nodes():
    content = Content.require(
        json.dumps(
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
    )

    assert content.has_shared("shared-nested") is True


# ---------------------------------------------------------------------------
# Node.shared_id
# ---------------------------------------------------------------------------


def test_node_shared_id_returns_existing():
    node = Content.wrap(
        {"type": "paragraph", "attrs": {"id": "n1", "sharedId": "shared-42"}, "content": []}
    ).root.content[0]
    assert node.shared_id == "shared-42"


def test_node_shared_id_returns_none_when_absent():
    node = Content.wrap(
        {"type": "paragraph", "attrs": {"id": "n1"}, "content": []}
    ).root.content[0]
    assert node.shared_id is None


# ---------------------------------------------------------------------------
# Content.where_shared_id
# ---------------------------------------------------------------------------


def test_where_shared_id_selects_matching_nodes():
    content = Content.require(
        json.dumps(
            {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "attrs": {"id": "p1", "sharedId": "shared-1"},
                        "content": [{"type": "text", "text": "one"}],
                    },
                    {
                        "type": "paragraph",
                        "attrs": {"id": "p2"},
                        "content": [{"type": "text", "text": "two"}],
                    },
                    {
                        "type": "paragraph",
                        "attrs": {"id": "p3", "sharedId": "shared-1"},
                        "content": [{"type": "text", "text": "one"}],
                    },
                ],
            }
        )
    )

    selection = content.where_shared_id("shared-1")

    assert len(selection) == 2
    assert {ref.node.id for ref in selection} == {"p1", "p3"}


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
