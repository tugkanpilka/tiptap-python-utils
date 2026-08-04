"""Trackability matrix for TipTap node shapes.

Pins how each editor block shape is seen by node sync (``selection_id``),
extraction (``text_slices`` / ``tracked_blocks``), and metadata (``word_count``,
``has_open_tasks``).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tiptap_python_utils import (
    Content,
    has_open_tasks,
    text_slices,
    tracked_blocks,
    word_count,
)
from tiptap_python_utils.walk.traversal import (
    SELECTION_ID_LEAF_CLASSES,
    TRACKABLE_NODE_CLASSES,
    selection_id,
)

pytestmark = [pytest.mark.unit]


@dataclass(frozen=True)
class BlockExpectation:
    local_id: str
    node_type: str
    html_tag: str
    text: str
    word_count: int
    is_open_task: bool = False


@dataclass(frozen=True)
class Expectation:
    selection_ids: tuple[str, ...]
    blocks: tuple[BlockExpectation, ...]
    total_word_count: int
    open_tasks: bool


@dataclass(frozen=True)
class Case:
    id: str
    doc: dict
    expected: Expectation


def _doc(*blocks) -> dict:
    return {"type": "doc", "content": list(blocks)}


def _paragraph(node_id: str, text: str = "") -> dict:
    node: dict = {"type": "paragraph", "attrs": {"id": node_id}}
    if text:
        node["content"] = [{"type": "text", "text": text}]
    return node


def _task_item(
    task_id: str | None,
    text: str = "",
    *,
    paragraph_id: str | None = None,
    status: str = "pending",
) -> dict:
    item: dict = {"type": "taskItem", "attrs": {"status": status}}
    if task_id is not None:
        item["attrs"]["id"] = task_id
    para: dict = {"type": "paragraph"}
    if paragraph_id is not None:
        para["attrs"] = {"id": paragraph_id}
    if text:
        para["content"] = [{"type": "text", "text": text}]
    item["content"] = [para]
    return {"type": "taskList", "content": [item]}


def _list_item(
    list_kind: str,
    item_id: str | None,
    text: str = "",
    *,
    paragraph_id: str | None = None,
) -> dict:
    item: dict = {"type": "listItem"}
    if item_id is not None:
        item["attrs"] = {"id": item_id}
    para: dict = {"type": "paragraph"}
    if paragraph_id is not None:
        para["attrs"] = {"id": paragraph_id}
    if text:
        para["content"] = [{"type": "text", "text": text}]
    item["content"] = [para]
    return {"type": list_kind, "content": [item]}


def _blockquote(
    block_id: str | None,
    text: str = "",
    *,
    paragraph_id: str | None = None,
) -> dict:
    quote: dict = {"type": "blockquote"}
    if block_id is not None:
        quote["attrs"] = {"id": block_id}
    para: dict = {"type": "paragraph"}
    if paragraph_id is not None:
        para["attrs"] = {"id": paragraph_id}
    if text:
        para["content"] = [{"type": "text", "text": text}]
    quote["content"] = [para]
    return quote


def _table_cell(
    cell_id: str | None,
    text: str = "",
    *,
    paragraph_id: str | None = None,
) -> dict:
    cell: dict = {"type": "tableCell"}
    if cell_id is not None:
        cell["attrs"] = {"id": cell_id}
    para: dict = {"type": "paragraph"}
    if paragraph_id is not None:
        para["attrs"] = {"id": paragraph_id}
    if text:
        para["content"] = [{"type": "text", "text": text}]
    cell["content"] = [para]
    return {
        "type": "table",
        "content": [{"type": "tableRow", "content": [cell]}],
    }


def _assert_blocks(actual, expected: tuple[BlockExpectation, ...]) -> None:
    assert len(actual) == len(expected)
    for block, want in zip(actual, expected):
        assert block.local_id == want.local_id
        assert block.node_type == want.node_type
        assert block.html_tag == want.html_tag
        assert block.text == want.text
        assert block.word_count == want.word_count
        assert block.is_open_task is want.is_open_task


CASES: tuple[Case, ...] = (
    Case(
        "paragraph_empty",
        _doc(_paragraph("p1")),
        Expectation(
            ("p1",),
            (BlockExpectation("p1", "paragraph", "p", "", 0),),
            0,
            False,
        ),
    ),
    Case(
        "paragraph_with_text",
        _doc(_paragraph("p1", "hello")),
        Expectation(
            ("p1",),
            (BlockExpectation("p1", "paragraph", "p", "hello", 1),),
            1,
            False,
        ),
    ),
    Case(
        "task_empty_id_on_task_item",
        _doc(_task_item("t1")),
        Expectation(
            ("t1",),
            (BlockExpectation("t1", "taskItem", "li", "", 0, True),),
            0,
            True,
        ),
    ),
    Case(
        "task_id_lifted_from_paragraph",
        _doc(_task_item(None, paragraph_id="p1")),
        Expectation(
            ("p1",),
            (BlockExpectation("p1", "taskItem", "li", "", 0, True),),
            0,
            True,
        ),
    ),
    Case(
        "task_completed_id_on_task_item",
        _doc(_task_item("t1", status="done")),
        Expectation(
            ("t1",),
            (BlockExpectation("t1", "taskItem", "li", "", 0, False),),
            0,
            False,
        ),
    ),
    Case(
        "task_lifted_completed",
        _doc(_task_item(None, paragraph_id="p1", status="done")),
        Expectation(
            ("p1",),
            (BlockExpectation("p1", "taskItem", "li", "", 0, False),),
            0,
            False,
        ),
    ),
    Case(
        "bullet_id_on_list_item",
        _doc(_list_item("bulletList", "li1", "item")),
        Expectation(
            ("li1",),
            (BlockExpectation("li1", "listItem", "li", "item", 1),),
            1,
            False,
        ),
    ),
    Case(
        "bullet_id_lifted_from_paragraph",
        _doc(_list_item("bulletList", None, "item", paragraph_id="p1")),
        Expectation(
            ("p1",),
            (BlockExpectation("p1", "listItem", "li", "item", 1),),
            1,
            False,
        ),
    ),
    Case(
        "blockquote_id_on_block",
        _doc(_blockquote("bq1", "quoted")),
        Expectation(
            ("bq1",),
            (BlockExpectation("bq1", "blockquote", "blockquote", "quoted", 1),),
            1,
            False,
        ),
    ),
    Case(
        "blockquote_id_lifted_from_paragraph",
        _doc(_blockquote(None, "quoted", paragraph_id="p1")),
        Expectation(
            ("p1",),
            (BlockExpectation("p1", "blockquote", "blockquote", "quoted", 1),),
            1,
            False,
        ),
    ),
    Case(
        "blockquote_no_id",
        _doc(_blockquote(None, "quoted")),
        Expectation((), (), 0, False),
    ),
    Case(
        "table_cell_id_on_cell",
        _doc(_table_cell("c1", "cell text")),
        Expectation(
            ("c1",),
            (BlockExpectation("c1", "tableCell", "td", "cell text", 2),),
            2,
            False,
        ),
    ),
    Case(
        "table_cell_id_lifted_from_paragraph",
        _doc(_table_cell(None, "cell text", paragraph_id="p1")),
        Expectation(
            ("p1",),
            (BlockExpectation("p1", "tableCell", "td", "cell text", 2),),
            2,
            False,
        ),
    ),
    Case(
        "table_cell_no_id",
        _doc(_table_cell(None, "cell text")),
        Expectation((), (), 0, False),
    ),
    Case(
        "multi_block_order",
        _doc(_paragraph("p1", "hello"), _paragraph("p2", "world")),
        Expectation(
            ("p1", "p2"),
            (
                BlockExpectation("p1", "paragraph", "p", "hello", 1),
                BlockExpectation("p2", "paragraph", "p", "world", 1),
            ),
            2,
            False,
        ),
    ),
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_trackability_matrix(case: Case):
    content = Content.require(case.doc)

    selection_ids = tuple(
        selection_id(ref.node)
        for ref in content.refs(parseable=True)
        if selection_id(ref.node)
    )
    blocks = tracked_blocks(content)

    assert selection_ids == case.expected.selection_ids
    _assert_blocks(blocks, case.expected.blocks)
    assert word_count(content) == case.expected.total_word_count
    assert content.word_count() == case.expected.total_word_count
    assert has_open_tasks(content) is case.expected.open_tasks
    assert tuple(slice.node_id for slice in text_slices(content)) == tuple(
        block.local_id for block in case.expected.blocks
    )


def test_has_open_tasks_is_false_when_task_has_no_resolvable_id():
    content = Content.require(
        _doc(
            {
                "type": "taskList",
                "content": [
                    {
                        "type": "taskItem",
                        "attrs": {"status": "pending"},
                        "content": [{"type": "paragraph"}],
                    }
                ],
            }
        )
    )

    assert has_open_tasks(content) is False


def test_trackable_node_classes_stay_aligned_with_selection_id():
    """Guard against drift between tracked_blocks filter and selection_id leaves."""
    leaf_kinds = {cls.kind for cls in SELECTION_ID_LEAF_CLASSES}
    trackable_kinds = {cls.kind for cls in TRACKABLE_NODE_CLASSES}
    assert leaf_kinds <= trackable_kinds
    assert trackable_kinds - leaf_kinds == {"taskItem"}
