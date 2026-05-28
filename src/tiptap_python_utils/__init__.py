"""Public API for TipTap JSON utilities."""

from .contract import key, kind
from .content import Content
from .exceptions import TiptapValidationError
from .model import (
    Blockquote,
    BulletList,
    CodeBlock,
    Doc,
    Heading,
    ListItem,
    Node,
    OrderedList,
    Paragraph,
    TableCell,
    TaskItem,
    TaskList,
    Text,
    Unknown,
    registry,
)
from .contract.policy import content_id, is_parseable, node_id, tiptap_id
from .select import Selection
from .shared import (
    fingerprint_shared,
    has_shared,
    new_shared_id,
    shared_id,
    shared_families,
    stamp_shared,
    sync_shared,
)
from .tasks import has_open_tasks, open_tasks, syncable_tasks
from .text import NodeText, text_slices, visible_text, word_count
from .walk import Ref, Walker

EMPTY_DOCUMENT_CONTENT = '{"type":"doc","content":[]}'

__all__ = [
    "Blockquote",
    "BulletList",
    "CodeBlock",
    "Content",
    "Doc",
    "EMPTY_DOCUMENT_CONTENT",
    "Heading",
    "ListItem",
    "Node",
    "NodeText",
    "OrderedList",
    "Paragraph",
    "Ref",
    "Selection",
    "TableCell",
    "TaskItem",
    "TaskList",
    "Text",
    "TiptapValidationError",
    "Unknown",
    "Walker",
    "content_id",
    "fingerprint_shared",
    "has_open_tasks",
    "has_shared",
    "is_parseable",
    "key",
    "kind",
    "new_shared_id",
    "node_id",
    "open_tasks",
    "registry",
    "shared_families",
    "shared_id",
    "stamp_shared",
    "sync_shared",
    "syncable_tasks",
    "text_slices",
    "tiptap_id",
    "visible_text",
    "word_count",
]
