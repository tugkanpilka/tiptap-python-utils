"""Unit tests for the public TipTap content API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import ClassVar, Mapping

import pytest

from tiptap_python_utils import TiptapValidationError
from tiptap_python_utils import (
    CodeBlock,
    Content,
    Doc,
    ListItem,
    Node,
    Paragraph,
    Text,
    Unknown,
    key,
    kind,
    registry,
)
from tiptap_python_utils.model import ContentTuple

pytestmark = [pytest.mark.unit]


def test_parse_empty_doc_returns_typed_root_and_round_trips():
    payload = {"type": "doc", "content": []}

    content = Content.parse(json.dumps(payload))

    assert content.root == Doc(present=frozenset({"type", "content"}))
    assert content.to_dict() == payload


def test_parse_invalid_content_is_lenient_but_require_raises():
    assert Content.parse("{invalid").root is None
    assert Content.parse("{invalid").text == ""

    with pytest.raises(TiptapValidationError, match="Document content is not valid JSON"):
        Content.require("{invalid")


def test_wrap_single_node_as_document():
    content = Content.wrap(
        {
            "type": "paragraph",
            "attrs": {"id": "p1"},
            "content": [{"type": "text", "text": "Body"}],
        }
    )

    assert content.root == Doc(
        content=(
            Paragraph(
                id="p1",
                attrs={"id": "p1"},
                content=(Text(value="Body", present=frozenset({"type", "text"})),),
                present=frozenset({"type", "attrs", "content"}),
            ),
        ),
        present=frozenset({"type", "content"}),
    )
    assert content.text == "Body"


def test_known_nodes_preserve_attrs_content_extra_and_text_marks():
    payload = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "attrs": {"id": "p1", "color": "red"},
                "content": [
                    {
                        "type": "text",
                        "text": "Body",
                        "marks": [{"type": "bold"}],
                        "custom": True,
                    }
                ],
                "customNodeKey": 7,
            }
        ],
    }

    content = Content.require(payload)

    assert content.paragraphs == [
        Paragraph(
            id="p1",
            attrs={"id": "p1", "color": "red"},
            extra={"customNodeKey": 7},
            content=(
                Text(
                    value="Body",
                    marks=({"type": "bold"},),
                    extra={"custom": True},
                    present=frozenset({"type", "text", "marks", "custom"}),
                ),
            ),
            present=frozenset({"type", "attrs", "content", "customNodeKey"}),
        )
    ]
    assert content.to_dict() == payload


def test_unknown_node_round_trips_losslessly():
    payload = {
        "type": "doc",
        "content": [
            {
                "type": "customPanel",
                "attrs": {"id": "panel-1"},
                "content": [{"type": "text", "text": "Inside"}],
                "custom": {"x": 1},
            }
        ],
    }

    content = Content.require(payload)

    assert isinstance(content.root.content[0], Unknown)
    assert content.to_dict() == payload


def test_registry_accepts_new_node_without_codec_changes():
    @dataclass(frozen=True)
    class Callout(Node):
        kind: ClassVar[str] = "callout"

        @classmethod
        def read(cls, raw: Mapping[str, object], children: ContentTuple) -> "Callout":
            return cls(
                id=str(raw.get("attrs", {}).get("id", "")),
                attrs=dict(raw.get("attrs", {})),
                content=children,
                present=frozenset(str(name) for name in raw.keys()),
            )

    registry.register(Callout)
    payload = {"type": "doc", "content": [{"type": "callout", "attrs": {"id": "c1"}}]}

    assert isinstance(Content.require(payload).root.content[0], Callout)


def test_query_properties_return_nodes_in_document_order():
    content = Content.parse(
        {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"id": "h1", "level": 2},
                    "content": [{"type": "text", "text": "Project"}],
                },
                {
                    "type": "paragraph",
                    "attrs": {"id": "p1"},
                    "content": [{"type": "text", "text": "Body"}],
                },
                {
                    "type": "taskItem",
                    "attrs": {"id": "t1", "checked": False},
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Task"}]}],
                },
                {
                    "type": "listItem",
                    "attrs": {"id": "li1"},
                    "content": [{"type": "text", "text": "Note"}],
                },
                {
                    "type": "codeBlock",
                    "attrs": {"id": "cb1"},
                    "content": [{"type": "text", "text": "print('hi')"}],
                },
            ],
        }
    )

    assert [node.id for node in content.headings] == ["h1"]
    assert [node.id for node in content.paragraphs] == ["p1", ""]
    assert [node.task_item_id for node in content.tasks] == ["t1"]
    assert [node.value for node in content.texts] == ["Project", "Body", "Task", "Note", "print('hi')"]
    assert content.walker().of_type(ListItem)[0].id == "li1"
    assert content.walker().of_type(CodeBlock)[0].id == "cb1"


def test_word_count_counts_parseable_id_backed_content_nodes():
    content = Content.parse(
        {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"id": "p1"},
                    "content": [{"type": "text", "text": "hello world"}],
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "ignored"}],
                },
            ],
        }
    )

    assert content.word_count() == 2


def test_selection_text_attr_replace_append_and_dump_do_not_mutate_inputs():
    original = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "attrs": {"id": "p1"},
                "content": [{"type": "text", "text": "Old"}],
            }
        ],
    }
    replacement = {
        "type": "paragraph",
        "attrs": {"id": "p1"},
        "content": [{"type": "text", "text": "Replacement"}],
    }

    updated = Content.require(original).where_id("p1").leaf().text("New")
    with_attr = updated.where_id("p1").attr("color", "blue")
    attr_payload = with_attr.to_dict()
    replaced = with_attr.where_id("p1").replace(replacement)
    appended = replaced.of(kind.DOC).append(
        {"type": "paragraph", "attrs": {"id": "p2"}, "content": []}
    )

    payload = json.loads(appended.dump())
    assert attr_payload["content"][0]["attrs"]["color"] == "blue"
    assert payload["content"][0]["content"][0]["text"] == "Replacement"
    assert payload["content"][1]["attrs"]["id"] == "p2"
    assert original["content"][0]["content"][0]["text"] == "Old"
    assert replacement["content"][0]["text"] == "Replacement"


def test_where_id_rejects_missing_and_duplicate_ids():
    with pytest.raises(TiptapValidationError, match="not found"):
        Content.require({"type": "doc", "content": []}).where_id("missing")

    with pytest.raises(TiptapValidationError, match="appears multiple times"):
        Content.require(
            {
                "type": "doc",
                "content": [
                    {"type": "paragraph", "attrs": {"id": "p1"}},
                    {"type": "paragraph", "attrs": {"id": "p1"}},
                ],
            }
        ).where_id("p1")


def test_selection_set_can_update_text_key():
    payload = json.loads(
        Content.require(
            {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "attrs": {"id": "p1"},
                        "content": [{"type": "text", "text": "Old"}],
                    }
                ],
            }
        )
        .where_id("p1")
        .leaf()
        .set(key.TEXT, "New")
        .dump()
    )

    assert payload["content"][0]["content"][0]["text"] == "New"


def _doc_with_paragraph(text: str = "Hello") -> Content:
    return Content.require(
        {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"id": "p1"},
                    "content": [{"type": "text", "text": text}],
                }
            ],
        }
    )


def test_selection_text_without_leaf_rejects_non_text_ref():
    with pytest.raises(TiptapValidationError, match=".leaf"):
        _doc_with_paragraph().where_id("p1").text("New")


def test_selection_marks_without_leaf_rejects_non_text_ref():
    with pytest.raises(TiptapValidationError, match=".leaf"):
        _doc_with_paragraph().where_id("p1").marks([{"type": "bold"}])


def test_selection_marks_requires_list():
    with pytest.raises(TiptapValidationError, match="marks must be a list"):
        _doc_with_paragraph().where_id("p1").leaf().marks("bold")


def test_selection_leaf_descends_to_nested_text():
    nested = Content.require(
        {
            "type": "doc",
            "content": [
                {
                    "type": "blockquote",
                    "attrs": {"id": "bq1"},
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Deep"}],
                        }
                    ],
                }
            ],
        }
    )

    updated = nested.where_id("bq1").leaf().text("Replaced").to_dict()
    assert updated["content"][0]["content"][0]["content"][0]["text"] == "Replaced"


def test_selection_leaf_skips_refs_without_text_descendants():
    empty = Content.require(
        {
            "type": "doc",
            "content": [{"type": "paragraph", "attrs": {"id": "p1"}, "content": []}],
        }
    )
    selection = empty.where_id("p1").leaf()
    assert len(selection) == 0


def test_selection_marks_writes_marks_on_text():
    updated = _doc_with_paragraph().where_id("p1").leaf().marks([{"type": "bold"}]).to_dict()
    assert updated["content"][0]["content"][0]["marks"] == [{"type": "bold"}]


def test_content_append_root_appends_node():
    updated = (
        _doc_with_paragraph()
        .append_root({"type": "paragraph", "attrs": {"id": "p2"}, "content": []})
        .to_dict()
    )
    assert [child["attrs"]["id"] for child in updated["content"]] == ["p1", "p2"]


def test_content_replace_by_id_replaces_target():
    updated = (
        _doc_with_paragraph()
        .replace_by_id(
            "p1",
            {
                "type": "paragraph",
                "attrs": {"id": "p1"},
                "content": [{"type": "text", "text": "Replaced"}],
            },
        )
        .to_dict()
    )
    assert updated["content"][0]["content"][0]["text"] == "Replaced"


def test_content_replace_by_id_rejects_missing_attrs_id():
    with pytest.raises(TiptapValidationError, match="must include attrs.id"):
        _doc_with_paragraph().replace_by_id(
            "p1", {"type": "paragraph", "attrs": {}, "content": []}
        )


def test_heading_level_tracks_attrs_after_attr_write():
    doc = Content.require(
        {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"id": "h1", "level": 1},
                    "content": [{"type": "text", "text": "Title"}],
                }
            ],
        }
    )

    updated = doc.where_id("h1").attr("level", 4)
    heading = updated.headings[0]
    assert heading.level == 4
    assert json.loads(updated.dump())["content"][0]["attrs"]["level"] == 4


def test_task_item_is_completed_tracks_attrs_after_attr_write():
    doc = Content.require(
        {
            "type": "doc",
            "content": [
                {
                    "type": "taskList",
                    "content": [
                        {
                            "type": "taskItem",
                            "attrs": {"id": "t1", "checked": False},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Buy milk"}],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )

    updated = doc.where_id("t1").attr("checked", True)
    assert updated.tasks[0].is_completed is True


def test_heading_level_falls_back_to_one_when_attrs_invalid():
    doc = Content.require(
        {
            "type": "doc",
            "content": [
                {"type": "heading", "attrs": {"level": 99}, "content": []},
            ],
        }
    )
    assert doc.headings[0].level == 1
