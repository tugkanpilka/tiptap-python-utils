import pytest

from tiptap_python_utils import Content, has_open_tasks, text_slices

pytestmark = [pytest.mark.unit]


def test_has_open_tasks_handles_pending_and_invalid_content():
    pending = Content.parse(
        {
            "type": "doc",
            "content": [{"type": "taskItem", "attrs": {"id": "t1", "checked": False}}],
        }
    )

    assert has_open_tasks(pending) is True
    assert has_open_tasks(Content.parse("{invalid")) is False


def test_text_slices_build_heading_context_and_use_tiptap_id():
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
                    "attrs": {"tiptapId": "p1"},
                    "content": [{"type": "text", "text": "Body"}],
                },
            ],
        }
    )

    result = text_slices(content, context=True)

    assert [(item.node_id, item.text, item.context) for item in result] == [
        ("h1", "Project", None),
        ("p1", "Body", "Project"),
    ]
