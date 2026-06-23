"""Unit tests for the pure raw-dict `task` namespace."""

from __future__ import annotations

from tiptap_python_utils import task


# --- create_list -----------------------------------------------------------


def test_create_list_wraps_items_in_task_list_block():
    items = [{"type": "taskItem"}]
    block = task.create_list(items)
    assert block == {"type": "taskList", "content": items}


def test_create_list_accepts_empty_list():
    assert task.create_list([]) == {"type": "taskList", "content": []}


def test_create_list_stores_items_by_reference_not_a_copy():
    items = [{"type": "taskItem", "n": 1}]
    block = task.create_list(items)
    # Same object, not a copy.
    assert block["content"] is items


def test_create_list_reflects_later_mutations_of_original_list():
    items = [{"type": "taskItem", "n": 1}]
    block = task.create_list(items)
    # Caller keeps appending to the original list after wrapping.
    items.append({"type": "taskItem", "n": 2})
    # The change is visible inside the block (by-reference contract).
    assert block["content"] == [
        {"type": "taskItem", "n": 1},
        {"type": "taskItem", "n": 2},
    ]
    assert len(block["content"]) == 2


# --- is_list ---------------------------------------------------------------


def test_is_list_true_for_valid_task_list():
    assert task.is_list({"type": "taskList", "content": []}) is True
    assert task.is_list({"type": "taskList", "content": [{"type": "taskItem"}]}) is True


def test_is_list_false_for_wrong_type():
    assert task.is_list({"type": "bulletList", "content": []}) is False


def test_is_list_false_when_content_not_a_list():
    assert task.is_list({"type": "taskList", "content": {}}) is False
    assert task.is_list({"type": "taskList", "content": "x"}) is False


def test_is_list_false_on_missing_keys_without_raising():
    assert task.is_list({}) is False
    assert task.is_list({"type": "taskList"}) is False  # no content key
    assert task.is_list({"content": []}) is False  # no type key


def test_is_list_false_for_non_dict():
    assert task.is_list(None) is False
    assert task.is_list([]) is False
    assert task.is_list("taskList") is False


# --- is_item ---------------------------------------------------------------


def test_is_item_true_for_task_item():
    assert task.is_item({"type": "taskItem"}) is True
    assert task.is_item({"type": "taskItem", "attrs": {"checked": True}}) is True


def test_is_item_false_for_wrong_type():
    assert task.is_item({"type": "taskList"}) is False
    assert task.is_item({"type": "listItem"}) is False


def test_is_item_false_on_missing_keys_without_raising():
    assert task.is_item({}) is False


def test_is_item_false_for_non_dict():
    assert task.is_item(None) is False
    assert task.is_item([]) is False
    assert task.is_item("taskItem") is False
