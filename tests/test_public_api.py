"""Phase 0 safety rail: freeze the root package public API.

This test exists so that refactors moving implementation between files
cannot silently shrink, expand, or break the package's public surface.

If a name is intentionally added/removed/renamed in `tiptap_python_utils`,
update EXPECTED_PUBLIC_API in the same commit so the intent is reviewable.
"""

from __future__ import annotations

import importlib

import tiptap_python_utils as pkg


EXPECTED_PUBLIC_API = frozenset(
    {
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
        "SharedFamilies",
        "TableCell",
        "TaskItem",
        "TaskList",
        "Text",
        "TiptapValidationError",
        "Unknown",
        "Walker",
        "content_id",
        "fingerprint",
        "has_open_tasks",
        "is_parseable",
        "key",
        "kind",
        "new_node_id",
        "new_shared_id",
        "node_id",
        "open_tasks",
        "registry",
        "syncable_tasks",
        "task",
        "text_slices",
        "tiptap_id",
        "visible_text",
        "word_count",
    }
)


def test_all_matches_expected_snapshot():
    assert set(pkg.__all__) == EXPECTED_PUBLIC_API


def test_every_exported_name_is_importable():
    missing = [name for name in EXPECTED_PUBLIC_API if not hasattr(pkg, name)]
    assert missing == [], f"declared in __all__ but not accessible: {missing}"


def test_every_exported_name_imports_via_from_statement():
    module = importlib.import_module("tiptap_python_utils")
    for name in EXPECTED_PUBLIC_API:
        obj = getattr(module, name, None)
        assert obj is not None, f"`from tiptap_python_utils import {name}` would fail"
