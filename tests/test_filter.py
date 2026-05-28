import pytest

from tiptap_python_utils import Paragraph, TaskItem, Text, open_tasks, syncable_tasks

pytestmark = [pytest.mark.unit]


def item(task_item_id: str, *, done: bool = False) -> TaskItem:
    return TaskItem(
        attrs={"id": task_item_id, "checked": done},
        content=(Paragraph(content=(Text(value="Task"),)),),
    )


def test_syncable_tasks_require_identity():
    assert syncable_tasks([item("task-1"), item("")]) == [item("task-1")]


def test_open_tasks_skip_completed_items():
    assert open_tasks([item("task-1"), item("task-2", done=True)]) == [item("task-1")]
