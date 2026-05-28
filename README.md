# tiptap_python_utils

Python utilities for TipTap JSON content.

`tiptap_python_utils` parses TipTap documents into typed Python nodes, preserves
unknown/custom nodes for lossless round trips, and provides small helpers for
traversal, immutable edits, visible text extraction, task queries, and shared
node synchronization.

The package has no runtime dependencies.

## Install

```bash
pip install tiptap_python_utils
```

## Quick Start

```python
from tiptap_python_utils import Content, Paragraph, Text, kind

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

updated = Content.require(raw).where_id("p1").text("New").dump()
```

## Typed Nodes

Build typed nodes directly and serialize them back to TipTap-compatible JSON:

```python
node = Paragraph(id="p1", content=(Text(value="Hello"),))
doc = Content.wrap(node.raw())
```

Unknown/custom node types are preserved as `Unknown` nodes and round-trip without
dropping extra fields.

## Selection And Editing

Select nodes by id or TipTap kind:

```python
updated = Content.require(raw).of(kind.PARAGRAPH).attr("color", "blue").dump()
```

Selection methods return updated immutable content:

```python
updated = (
    Content.require(raw)
    .where_id("p1")
    .text("Updated")
    .attr("data-state", "reviewed")
    .dump()
)
```

## Text Extraction

Extract visible text or contextual slices:

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

## Public API

Common imports are available from the package root:

```python
from tiptap_python_utils import (
    Content,
    Paragraph,
    TaskItem,
    Text,
    append_node,
    has_open_tasks,
    kind,
    replace_node,
    shared_families,
    sync_shared,
    text_slices,
)
```

## Development

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Build and check a release artifact:

```bash
python -m build
python -m twine check dist/*
```
