"""Phase 0 safety rail: freeze canonical sub-package import paths.

Refactors that move implementation between files (e.g. splitting
`model/__init__.py` into `model/base.py`, `model/nodes.py`, ...) must
keep these import paths working. The CLAUDE.md compat requirement
("from tiptap_python_utils.model import ContentTuple / registry / Paragraph")
is encoded here alongside every other currently-exported subpackage name.

If a name is intentionally moved out of one of these subpackages,
update the corresponding snapshot in the same commit.
"""

from __future__ import annotations

import importlib

import pytest


SUBPACKAGE_PUBLIC_NAMES: dict[str, frozenset[str]] = {
    "tiptap_python_utils.codec": frozenset(
        {
            "dump",
            "dumps",
            "normalize_text",
            "parse_raw",
            "raw_node_id",
            "raw_text",
            "read_children",
            "read_doc",
            "read_node",
            "read_node_input",
            "require_object",
        }
    ),
    "tiptap_python_utils.contract": frozenset({"key", "kind", "policy"}),
    "tiptap_python_utils.model": frozenset(
        {
            "Blockquote",
            "BulletList",
            "CodeBlock",
            "ContentTuple",
            "Doc",
            "Heading",
            "ListItem",
            "MarksTuple",
            "Node",
            "NodeT",
            "OrderedList",
            "Paragraph",
            "Registry",
            "TableCell",
            "TaskItem",
            "TaskList",
            "Text",
            "Unknown",
            "registry",
        }
    ),
    "tiptap_python_utils.select": frozenset({"Selection"}),
    "tiptap_python_utils.shared": frozenset(
        {
            "SharedFamilies",
            "fingerprint",
            "new_shared_id",
        }
    ),
    "tiptap_python_utils.tasks": frozenset(
        {"has_open_tasks", "open_tasks", "syncable_tasks"}
    ),
    "tiptap_python_utils.text": frozenset(
        {"NodeText", "text_slices", "visible_text", "word_count"}
    ),
    "tiptap_python_utils.tree": frozenset({"node_at_path", "replace_at_path"}),
    "tiptap_python_utils.walk": frozenset({"Ref", "Walker", "selection_id"}),
}


# Names whose canonical home is a nested module, e.g. policy helpers
# live under contract.policy, not directly under contract.
NESTED_PUBLIC_NAMES: dict[str, frozenset[str]] = {
    "tiptap_python_utils.contract.policy": frozenset(
        {"content_id", "is_parseable", "node_id", "tiptap_id"}
    ),
}


@pytest.mark.parametrize(
    "module_name,expected_names",
    sorted({**SUBPACKAGE_PUBLIC_NAMES, **NESTED_PUBLIC_NAMES}.items()),
)
def test_subpackage_public_names_are_importable(
    module_name: str, expected_names: frozenset[str]
) -> None:
    module = importlib.import_module(module_name)
    missing = sorted(name for name in expected_names if not hasattr(module, name))
    assert missing == [], f"{module_name} is missing: {missing}"


@pytest.mark.parametrize(
    "module_name,expected_names", sorted(SUBPACKAGE_PUBLIC_NAMES.items())
)
def test_subpackage_all_covers_expected_snapshot(
    module_name: str, expected_names: frozenset[str]
) -> None:
    """Sub-packages that declare __all__ must include every snapshotted name.

    `model` currently has no __all__; that's fine — the importability test
    above already covers it. When Phase 1 introduces one, this test will
    automatically start enforcing the snapshot.
    """
    module = importlib.import_module(module_name)
    declared = getattr(module, "__all__", None)
    if declared is None:
        pytest.skip(f"{module_name} does not declare __all__")
    missing = sorted(expected_names - set(declared))
    assert missing == [], f"{module_name}.__all__ is missing: {missing}"


def test_claude_md_required_compat_paths():
    """The three compat paths called out explicitly in CLAUDE.md."""
    from tiptap_python_utils import Paragraph  # noqa: F401
    from tiptap_python_utils.model import ContentTuple  # noqa: F401
    from tiptap_python_utils.model import registry  # noqa: F401
