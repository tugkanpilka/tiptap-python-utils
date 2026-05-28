"""Task-specific TipTap behavior."""

from __future__ import annotations

from ..content import Content
from ..model import TaskItem


def syncable_tasks(items: list[TaskItem]) -> list[TaskItem]:
    return [item for item in items if item.task_item_id]


def open_tasks(items: list[TaskItem]) -> list[TaskItem]:
    return [item for item in items if not item.is_completed]


def has_open_tasks(content: Content) -> bool:
    return bool(open_tasks(content.tasks))
