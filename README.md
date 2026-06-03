# tiptap_python_utils

[![PyPI](https://img.shields.io/pypi/v/tiptap_python_utils.svg)](https://pypi.org/project/tiptap_python_utils/)
[![Python](https://img.shields.io/pypi/pyversions/tiptap_python_utils.svg)](https://pypi.org/project/tiptap_python_utils/)
[![CI](https://github.com/tugkanpilka/tiptap-python-utils/actions/workflows/ci.yml/badge.svg)](https://github.com/tugkanpilka/tiptap-python-utils/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

TipTap is a JavaScript editor. If your backend is Python and you need to
process TipTap JSON — extract text, query tasks, sync shared nodes — this
library does it in pure Python with zero dependencies. No JS bridge, no
Node.js subprocess.

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

## Features

- **Zero runtime dependencies.** Standard library only.
- **Python 3.9+.** Tested on 3.9, 3.10, 3.11, 3.12, 3.13.
- **Lossless round trip.** Unknown node kinds and any extra fields are preserved.
- **Immutable AST.** All mutations return new instances via a fluent selection API.

## Install

```bash
pip install tiptap_python_utils
```

## Three Ways to Load a Document

Pick a constructor by how much you trust the input — lenient, strict, or
auto-wrapping a bare node into a `doc`.

| Constructor | When to use | On invalid input |
|---|---|---|
| `Content.parse(raw)` | Lenient — `raw` may be `None`, a string, or a dict | Returns a `Content` with `root=None` |
| `Content.require(raw)` | Strict — input must be a valid TipTap `doc` | Raises `TiptapValidationError` |
| `Content.wrap(node)` | Auto-wraps a non-doc node into a `doc` root | Raises if the node is not parseable |

## Lossless Round Trip

Parsing never silently drops fields — custom nodes and unknown keys survive a
parse-then-serialize cycle byte-for-byte. Two mechanisms preserve information:

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

Build typed nodes directly in Python and serialize them back to
TipTap-compatible JSON.

```python
from tiptap_python_utils import Content, Paragraph, Text

node = Paragraph(id="p1", content=(Text(value="Hello"),))
doc = Content.wrap(node.raw())
```

## Selection and Editing

The fluent selection API is the single home for mutation: every method returns
a new `Content`, so the original is never mutated.

### Select by id or kind

```python
from tiptap_python_utils import Content, kind

# By id (uses TipTap's id resolution rules under the hood).
content.where_id("p1")

# By TipTap kind.
content.of(kind.PARAGRAPH)

# By an arbitrary predicate over every node (and its descendants).
content.where(lambda node: getattr(node, "level", None) == 1)
```

### Generic queries

`Selection` carries two predicate primitives that work for any kind, so you
don't need a bespoke `has_heading_text`-style helper per node type:

```python
# Narrow a selection further.
content.of(kind.HEADING).filter(lambda n: n.level == 2)

# Existence check (short-circuits).
content.of(kind.HEADING).any(lambda n: n.text.strip() == "Introduction")
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

# Build-and-append in one call — works for any kind, stamps a fresh id when
# none is given. Typed fields (e.g. Heading.level) hydrate correctly.
content.append(kind.HEADING, "New section", attrs={"level": 2})
content.append(kind.PARAGRAPH, "Body text", node_id="p3")

# Replace a node by id (the replacement's attrs.id must match).
content.replace_by_id("p1", {
    "type": "paragraph",
    "attrs": {"id": "p1"},
    "content": [{"type": "text", "text": "Replaced"}],
})
```

## Text Extraction

Pull the visible plain text out of a document — useful for search indexing,
word counts, or previews.

```python
from tiptap_python_utils import Content, text_slices, visible_text, word_count

content = Content.require(raw)

plain_text = visible_text(content)
count = word_count(content)
slices = text_slices(content, context=True)
```

## Tasks

Query task lists in a document — find every task item or check whether any are
still open.

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

Keep copies of the same logical node (linked by `sharedId`) in sync — collect
canonical bodies, then rewrite every matching node from them.

`Content.shared_families()` collects canonical bodies grouped by `sharedId` into
a `SharedFamilies` value object. `Content.sync_shared(families)` rewrites every
matching node in the document from those canonical bodies, preserving
per-instance identity (`id`, `sharedId`). Both return immutable values — the
original `Content` is never mutated.

```python
from tiptap_python_utils import Content

# Canonical doc: the source of truth for every shared body.
canonical = Content.require({"type": "doc", "content": [
    {
        "type": "paragraph",
        "attrs": {"id": "p1", "sharedId": "intro"},
        "content": [{"type": "text", "text": "Authoritative intro"}],
    }
]})

# Doc that mirrors the same sharedId but with a stale body.
target = Content.require({"type": "doc", "content": [
    {
        "type": "paragraph",
        "attrs": {"id": "p1-copy", "sharedId": "intro"},
        "content": [{"type": "text", "text": "Stale copy"}],
    }
]})

synced = target.sync_shared(canonical.shared_families())
assert synced.has_shared("intro")
```

Related helpers on `Content`:

- `content.where_shared_id(sid)` — `Selection` over every node with that sharedId.
- `content.has_shared(sid)` — quick presence check.
- `node.with_shared_id(sid)` — stamp a sharedId onto a node (returns a new node).
- `new_shared_id()` — mint a fresh `shared-…` identifier.

## Public API

Common imports are available from the package root:

```python
from tiptap_python_utils import (
    Content,
    Paragraph,
    SharedFamilies,
    TaskItem,
    Text,
    has_open_tasks,
    kind,
    new_node_id,
    new_shared_id,
    open_tasks,
    text_slices,
    visible_text,
    word_count,
)
```

## Contributing

Issues and pull requests are welcome. Please read
[CONTRIBUTING.md](CONTRIBUTING.md) for the local setup, architecture overview,
and release checklist, and open an issue at
[github.com/tugkanpilka/tiptap-python-utils/issues](https://github.com/tugkanpilka/tiptap-python-utils/issues)
before opening a pull request so we can align on the approach.

## License

MIT — see [LICENSE](LICENSE).

## Stability

The project is pre-1.0; minor versions may include breaking changes. See
[CHANGELOG.md](CHANGELOG.md) for what changed and when.
</content>
</invoke>
