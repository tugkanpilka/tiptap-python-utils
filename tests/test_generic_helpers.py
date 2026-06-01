"""Unit tests for the generic node helpers.

Covers the cross-cutting construction/query layer:
``codec.build_node``, ``Content.append``, ``Content.where``,
``Selection.filter`` / ``Selection.any``, and ``new_node_id``.
"""

from __future__ import annotations

import pytest

from tiptap_python_utils import (
    Content,
    Heading,
    TaskItem,
    Text,
    TiptapValidationError,
    key,
    kind,
    new_node_id,
)
from tiptap_python_utils.codec import build_node

pytestmark = [pytest.mark.unit]


# ---------------------------------------------------------------------------
# new_node_id
# ---------------------------------------------------------------------------


def test_new_node_id_is_unique_and_unprefixed() -> None:
    a, b = new_node_id(), new_node_id()
    assert a != b
    assert not a.startswith("shared-")  # distinct from new_shared_id()


# ---------------------------------------------------------------------------
# build_node — typed-field hydration
# ---------------------------------------------------------------------------


def test_build_node_hydrates_heading_level_from_attrs() -> None:
    node = build_node(kind.HEADING, "Title", attrs={key.LEVEL: 3})
    assert isinstance(node, Heading)
    assert node.level == 3
    assert node.text == "Title"


def test_build_node_default_has_no_content_when_text_empty() -> None:
    node = build_node(kind.PARAGRAPH)
    assert node.content == ()
    assert key.CONTENT not in node.present


def test_build_node_with_text_creates_single_text_child() -> None:
    node = build_node(kind.PARAGRAPH, "hello")
    assert len(node.content) == 1
    child = node.content[0]
    assert isinstance(child, Text)
    assert child.text == "hello"


def test_build_node_text_kind_sets_value_not_child() -> None:
    node = build_node(kind.TEXT, "raw")
    assert isinstance(node, Text)
    assert node.text == "raw"
    assert node.content == ()


def test_build_node_task_item_derives_identity_from_attrs() -> None:
    node = build_node(kind.TASK_ITEM, attrs={key.ID: "t1"})
    assert isinstance(node, TaskItem)
    assert node.local_task_item_id == "t1"


# ---------------------------------------------------------------------------
# build_node — identity stamping
# ---------------------------------------------------------------------------


def test_build_node_stamps_node_id_when_attrs_have_no_identity() -> None:
    node = build_node(kind.PARAGRAPH, node_id="p1")
    assert node.attrs.get(key.ID) == "p1"


def test_build_node_keeps_existing_identity_over_node_id() -> None:
    node = build_node(kind.PARAGRAPH, attrs={key.ID: "kept"}, node_id="ignored")
    assert node.attrs.get(key.ID) == "kept"


def test_build_node_pure_when_no_node_id_given() -> None:
    node = build_node(kind.PARAGRAPH, attrs={key.LEVEL: 1})
    assert key.ID not in node.attrs


# ---------------------------------------------------------------------------
# build_node — container rejects inline text
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "container", [kind.BULLET_LIST, kind.ORDERED_LIST, kind.TASK_LIST, kind.DOC]
)
def test_build_node_rejects_text_on_containers(container: str) -> None:
    with pytest.raises(TiptapValidationError):
        build_node(container, "nope")


def test_build_node_round_trips_extra_fields() -> None:
    node = build_node(kind.PARAGRAPH, "x")
    raw = node.raw()
    assert raw[key.TYPE] == kind.PARAGRAPH
    assert raw[key.CONTENT][0][key.TEXT] == "x"


# ---------------------------------------------------------------------------
# Content.append
# ---------------------------------------------------------------------------


def _empty() -> Content:
    return Content.require({"type": "doc", "content": []})


def test_append_stamps_fresh_id_when_omitted() -> None:
    content = _empty().append(kind.HEADING, "H", attrs={key.LEVEL: 2})
    [heading] = content.headings
    assert heading.attrs.get(key.ID)  # non-empty
    assert heading.level == 2


def test_append_keeps_given_node_id() -> None:
    content = _empty().append(kind.PARAGRAPH, "p", node_id="given")
    [para] = content.paragraphs
    assert para.attrs.get(key.ID) == "given"


def test_append_adds_node_to_root() -> None:
    content = _empty().append(kind.HEADING, "Visible")
    assert any(h.text == "Visible" for h in content.headings)


# ---------------------------------------------------------------------------
# Content.where / Selection.filter / Selection.any
# ---------------------------------------------------------------------------


def _two_headings() -> Content:
    return (
        _empty()
        .append(kind.HEADING, "Intro", attrs={key.LEVEL: 1})
        .append(kind.HEADING, "Body", attrs={key.LEVEL: 2})
    )


def test_where_filters_by_predicate() -> None:
    content = _two_headings()
    selected = content.where(
        lambda n: n.kind == kind.HEADING and getattr(n, "text", "") == "Body"
    )
    assert len(selected) == 1
    assert selected.nodes[0].text == "Body"


def test_where_visits_all_refs_including_descendants() -> None:
    content = _two_headings()
    # Generic where() is not kind-scoped: a Heading and its Text child both
    # expose .text == "Body".
    selected = content.where(lambda n: getattr(n, "text", "") == "Body")
    assert len(selected) == 2


def test_selection_any_short_circuits_true() -> None:
    content = _two_headings()
    assert content.of(kind.HEADING).any(lambda n: n.text == "Intro") is True


def test_selection_any_false_on_no_match() -> None:
    content = _two_headings()
    assert content.of(kind.HEADING).any(lambda n: n.text == "Missing") is False


def test_selection_any_false_on_empty_selection() -> None:
    content = _empty()
    assert content.of(kind.HEADING).any() is False


def test_has_heading_text_via_generic_query() -> None:
    content = _two_headings()
    # The replacement for the old heading-specific has_heading_text:
    assert content.of(kind.HEADING).any(lambda n: n.text.strip() == "Body")
