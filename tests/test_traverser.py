import pytest

from tiptap_python_utils import Content, Heading, Paragraph, TaskItem, Text, Walker

pytestmark = [pytest.mark.unit]


def test_walker_returns_typed_nodes_in_document_order():
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
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Done"}],
                        }
                    ],
                },
            ],
        }
    )

    walker = Walker(content)

    assert walker.of_type(Heading) == [
        Heading(id="h1", level=2, attrs={"id": "h1", "level": 2}, content=(Text(value="Project"),))
    ]
    assert [node.id for node in walker.of_type(Paragraph)] == ["p1", ""]
    assert [node.task_item_id for node in walker.of_type(TaskItem)] == ["t1"]
    assert [node.value for node in walker.of_type(Text)] == ["Project", "Body", "Done"]


def test_parseable_refs_skip_paragraphs_inside_task_items():
    content = Content.parse(
        {
            "type": "doc",
            "content": [
                {
                    "type": "taskItem",
                    "attrs": {"id": "t1", "checked": False},
                    "content": [
                        {"type": "paragraph", "attrs": {"id": "p1"}, "content": []}
                    ],
                }
            ],
        }
    )

    assert [ref.node.kind for ref in content.refs(parseable=True)] == ["doc", "taskItem"]
