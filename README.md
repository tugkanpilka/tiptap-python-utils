# tiptap_python_utils

[![PyPI](https://img.shields.io/pypi/v/tiptap_python_utils.svg)](https://pypi.org/project/tiptap_python_utils/)
[![Python](https://img.shields.io/pypi/pyversions/tiptap_python_utils.svg)](https://pypi.org/project/tiptap_python_utils/)
[![CI](https://github.com/tugkanpilka/tiptap-python-utils/actions/workflows/ci.yml/badge.svg)](https://github.com/tugkanpilka/tiptap-python-utils/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Python utilities for [TipTap](https://tiptap.dev) JSON content.

`tiptap_python_utils` parses TipTap documents into typed, immutable Python
nodes, preserves unknown/custom nodes for lossless round trips, and provides
small helpers for traversal, immutable edits, visible text extraction, task
queries, and shared-node synchronization.

- **Zero runtime dependencies.** Standard library only.
- **Python 3.9+.** Tested on 3.9, 3.10, 3.11, 3.12, 3.13.
- **Lossless round trip.** Unknown node kinds and any extra fields are preserved.
- **Immutable AST.** All mutations return new instances via a fluent selection API.

## Install

```bash
pip install tiptap_python_utils
```

## Quick Start

```python
from tiptap_python_utils import Content

raw = {
    "type": "doc",
    "content": [
        {
            "type": "paragraph",
            "attrs": {"id": "p1"},
            "content": [{"type": "text", "text": "Old"}],
        }
    ],
}

# Strict-load → descend to the text leaf → write a new value → serialize.
updated = Content.require(raw).where_id("p1").leaf().text("New").dump()
```

## Three Ways to Load a Document

| Constructor | When to use | On invalid input |
|---|---|---|
| `Content.parse(raw)` | Lenient — `raw` may be `None`, a string, or a dict | Returns a `Content` with `root=None` |
| `Content.require(raw)` | Strict — input must be a valid TipTap `doc` | Raises `TiptapValidationError` |
| `Content.wrap(node)` | Auto-wraps a non-doc node into a `doc` root | Raises if the node is not parseable |

## Lossless Round Trip

Parsing never silently drops fields. Two mechanisms preserve information:

- `Node.extra` stores top-level keys that aren't part of the known schema
  (e.g. custom node attributes, vendor-specific keys).
- `Node.present` records which structural keys (`attrs`, `content`, …) appeared
  in the raw input, so `raw()` emits empty `attrs: {}` or `content: []` only
  when they were originally present.
- Unknown node kinds become `Unknown(raw_kind="…")` rather than being rejected.

```python
from tiptap_python_utils import Content

raw = {"type": "doc", "content": [
    {"type": "customPanel", "attrs": {"id": "p1"}, "content": [], "custom": {"x": 1}}
]}

assert Content.require(raw).to_dict() == raw  # byte-for-byte
```

## Typed Nodes

Build typed nodes directly and serialize them back to TipTap-compatible JSON:

```python
from tiptap_python_utils import Content, Paragraph, Text

node = Paragraph(id="p1", content=(Text(value="Hello"),))
doc = Content.wrap(node.raw())
```

## Selection and Editing

The fluent selection API is the single home for mutation. Selection methods
return a new `Content`; the original is never mutated.

### Select by id or kind

```python
from tiptap_python_utils import Content, kind

# By id (uses TipTap's id resolution rules under the hood).
content.where_id("p1")

# By TipTap kind.
content.of(kind.PARAGRAPH)
```

### Atomic mutations

```python
# Write an attribute on the selected node.
content.where_id("p1").attr("color", "blue")

# Descend to the first text descendant, then write text or marks.
content.where_id("p1").leaf().text("Updated")
content.where_id("p1").leaf().marks([{"type": "bold"}])

# Replace the whole selected node, or append a child to it.
content.where_id("p1").replace({"type": "paragraph", "attrs": {"id": "p1"}, "content": []})
content.where_id("ul1").append({"type": "listItem", "attrs": {"id": "li-new"}, "content": []})
```

`.text()` and `.marks()` are strict — they only operate on `Text` refs. Chain
`.leaf()` first to descend from a container.

### Document-level commands

```python
# Append a node to the document root.
content.append_root({"type": "paragraph", "attrs": {"id": "p2"}, "content": []})

# Replace a node by id (the replacement's attrs.id must match).
content.replace_by_id("p1", {
    "type": "paragraph",
    "attrs": {"id": "p1"},
    "content": [{"type": "text", "text": "Replaced"}],
})
```

## Text Extraction

```python
from tiptap_python_utils import Content, text_slices, visible_text, word_count

content = Content.require(raw)

plain_text = visible_text(content)
count = word_count(content)
slices = text_slices(content, context=True)
```

## Tasks

```python
from tiptap_python_utils import Content, has_open_tasks, open_tasks

content = Content.require(raw)

pending = has_open_tasks(content)
items = open_tasks(content)
```

Each `TaskItem` exposes derived state as properties:

```python
task = open_tasks(content)[0]

task.task_item_id       # canonical id (falls back to local id)
task.is_completed       # status / checked interpretation
task.is_linked_copy     # True when local id differs from canonical id
task.shared_id          # sharedId attr, if any
```

## Shared-Node Synchronization

`shared_families` collects canonical bodies grouped by `sharedId`;
`sync_shared` rewrites every matching node in a document using those canonical
bodies while preserving per-instance identity (`id`, `sharedId`).

```python
from tiptap_python_utils import shared_families, sync_shared

# Canonical doc: the source of truth for every shared body.
canonical = {"type": "doc", "content": [
    {
        "type": "paragraph",
        "attrs": {"id": "p1", "sharedId": "intro"},
        "content": [{"type": "text", "text": "Authoritative intro"}],
    }
]}

# Doc that mirrors the same sharedId but with a stale body.
target = {"type": "doc", "content": [
    {
        "type": "paragraph",
        "attrs": {"id": "p1-copy", "sharedId": "intro"},
        "content": [{"type": "text", "text": "Stale copy"}],
    }
]}

families = shared_families(canonical)
synced_json, changed = sync_shared(target, families)
assert changed is True
```

## Architecture (one paragraph)

The package is layered: `contract` (key/kind/policy primitives) → `model`
(immutable AST with a registry of node classes; unknown kinds round-trip via
`Unknown`) → `codec` (raw I/O in `raw.py`, hydration in `reader.py`, dump in
`writer.py`) → `walk` & `tree` (traversal + path-based replacement on the
immutable tree) → `select` (fluent `Selection` — the single home for mutation)
→ `content` (public facade) → `text` / `tasks` / `shared` (user-facing
workflows built on `Content`). All nodes are `@dataclass(frozen=True)`;
mutations return new instances.

## Public API

Common imports are available from the package root:

```python
from tiptap_python_utils import (
    Content,
    Paragraph,
    TaskItem,
    Text,
    has_open_tasks,
    kind,
    open_tasks,
    shared_families,
    sync_shared,
    text_slices,
    visible_text,
    word_count,
)
```

## Stability

The project is pre-1.0; minor versions may include breaking changes. See
[CHANGELOG.md](CHANGELOG.md) for what changed and when.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
```

Build and validate a release artifact:

```bash
python -m build
python -m twine check dist/*
```

## Contributing

Issues and pull requests are welcome. Please read
[CONTRIBUTING.md](CONTRIBUTING.md) for the local setup and release checklist,
and open an issue at
[github.com/tugkanpilka/tiptap-python-utils/issues](https://github.com/tugkanpilka/tiptap-python-utils/issues)
before larger changes so we can align on the approach.

## License

MIT — see [LICENSE](LICENSE).
