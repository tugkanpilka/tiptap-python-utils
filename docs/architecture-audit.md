# Architecture Audit

Date: 2026-05-28

This audit looks at organization, responsibility boundaries, and dependency direction. The lens is Clean Code / Clean Architecture: a module should have one clear reason to change, dependencies should point toward stable concepts, and package entrypoints should not hide real behavior.

## Scope

Reviewed:

- `src/tiptap_python_utils/**/*.py`
- public exports in `__init__.py` files
- module size and responsibility concentration
- internal import direction and local imports
- tests as evidence of the public API surface

Not reviewed:

- runtime performance
- API design from a user research perspective
- external downstream usage outside this repository

## Executive Summary

The codebase is small and behaviorally healthy, but organization is starting to blur. The main issue is not widespread dead code. The main issue is that several modules mix abstraction levels, and one package initializer is doing real domain work.

Highest priority finding:

- `src/tiptap_python_utils/model/__init__.py` is a real implementation module, not a package initializer. It defines all node types, serialization behavior, registry behavior, registry bootstrap side effects, and parsing helpers in one 345-line file.

Second-order findings:

- `edit/commands.py` mixes typed node transforms with document-level string/dict commands.
- `content.py` is a facade, query API, serializer, selector factory, and word-count implementation.
- `codec/json.py` mixes raw JSON parsing, validation, AST hydration, dumping, and raw-node helpers.
- There is a conceptual dependency cycle around `content -> select -> edit -> content`, currently hidden by function-local imports in `edit.commands`.

## `__init__.py` Audit

| File | Current role | Assessment |
| --- | --- | --- |
| `src/tiptap_python_utils/__init__.py` | Root public API barrel plus `EMPTY_DOCUMENT_CONTENT` | Mostly acceptable, but the constant belongs in a defaults/contract module if it remains public. |
| `src/tiptap_python_utils/codec/__init__.py` | Re-exports codec helpers | Acceptable. |
| `src/tiptap_python_utils/contract/__init__.py` | Re-exports contract modules | Acceptable. |
| `src/tiptap_python_utils/edit/__init__.py` | Re-exports edit commands | Acceptable, though exported commands are mixed-level. |
| `src/tiptap_python_utils/model/__init__.py` | Defines domain model, registry, helpers, and import-time registry setup | Problematic. This should become a re-export-only initializer. |
| `src/tiptap_python_utils/select/__init__.py` | Re-exports `Selection` | Acceptable. |
| `src/tiptap_python_utils/shared/__init__.py` | Re-exports shared-node service helpers | Acceptable, but package internals need clearer names. |
| `src/tiptap_python_utils/tasks/__init__.py` | Re-exports task query helpers | Acceptable. |
| `src/tiptap_python_utils/text/__init__.py` | Re-exports text helpers | Acceptable. |
| `src/tiptap_python_utils/tree/__init__.py` | Re-exports tree path helpers | Acceptable. |
| `src/tiptap_python_utils/walk/__init__.py` | Re-exports traversal helpers | Acceptable. |

Rule to adopt:

`__init__.py` files should only define package docs, imports, `__all__`, and compatibility aliases. They should not define domain classes, registries, algorithms, or import-time mutation.

## Findings

### 1. `model/__init__.py` Is Doing Too Much

Evidence:

- 345 lines, largest source file.
- Defines base types and aliases: `ContentTuple`, `MarksTuple`, `NodeT`.
- Defines all node classes: `Node`, `Text`, `Doc`, `Paragraph`, `Heading`, `TaskItem`, list/container nodes, `Unknown`.
- Defines registry infrastructure: `Registry`, `registry`.
- Registers built-in node classes at import time.
- Defines parsing/normalization helpers: `_payload`, `_heading_level`, `_task_canonical_id`, `_task_completion`, `_has_any_identity`.

Clean Code concern:

This file has multiple reasons to change:

- a new TipTap node type
- a change to raw serialization
- a change to task identity policy
- a change to registry behavior
- a change to package exports

Recommended shape:

- `model/base.py`: `Node`, common type aliases
- `model/nodes.py`: concrete node classes
- `model/task.py` or `model/task_item.py`: task-specific parsing and identity behavior if it keeps growing
- `model/registry.py`: `Registry`, `registry`, built-in registration
- `model/payload.py` or `model/readers.py`: raw payload extraction helpers
- `model/__init__.py`: re-export compatibility only

Compatibility requirement:

Keep existing imports working, especially:

- `from tiptap_python_utils import Paragraph`
- `from tiptap_python_utils.model import ContentTuple`
- `from tiptap_python_utils.model import registry`

### 2. `edit/commands.py` Mixes Two Abstraction Levels

Evidence:

- Low-level typed node transforms: `set_text`, `set_key`, `set_attr`, `append_child`.
- High-level document commands: `append_node`, `replace_node`.
- `append_node` and `replace_node` import `Content` inside function bodies to avoid import pressure.

Clean Code concern:

The file says "pure immutable TipTap edit commands", but some functions operate on typed `Node` objects while others parse `str | dict`, validate document content, select nodes, and return serialized JSON strings.

Recommended shape:

- `edit/node.py`: typed node transforms such as `set_text`, `set_key`, `set_attr`, `append_child`.
- `edit/document.py`: public document-level commands such as `append_node`, `replace_node`.
- `edit/__init__.py`: compatibility re-exports.

Target outcome:

No function-local import should be needed to avoid a conceptual cycle.

### 3. `content.py` Is a Useful Facade, but It Owns Too Many Policies

Evidence:

- Parses and requires content through `codec`.
- Provides root access and serialization.
- Provides query properties: `tasks`, `headings`, `paragraphs`, `texts`.
- Creates selections: `where_id`, `of`.
- Implements word-count traversal and identity filtering.
- Has private mutation hooks used by shared sync: `_require_root`, `_with_root`.

Clean Code concern:

The facade is valuable, but word-count policy and type-specific query shortcuts may pull domain rules into the facade. Private methods used by another package also suggest an internal boundary that is not explicit.

Recommended shape:

- Keep `Content` as a public facade.
- Move word-count implementation to `text` or a query module.
- Decide whether `_require_root` and `_with_root` are internal facade methods or should become explicit internal helpers.
- Keep selector creation here only if `Content` is intentionally the primary user entrypoint.

### 4. `codec/json.py` Mixes Raw JSON Concerns With AST Hydration

Evidence:

- Raw parsing: `parse_raw`, `require_object`.
- AST reading: `read_doc`, `read_node`, `read_children`, `read_node_input`.
- Serialization: `dump`, `dumps`.
- Raw helpers: `raw_node_id`, `raw_text`, `normalize_text`.

Clean Code concern:

JSON parsing, AST construction, and raw helper utilities are separate reasons to change. `codec/json.py` is still small, but it is the kind of file that becomes a junk drawer.

Recommended shape:

- `codec/raw.py`: JSON object parsing and strict/lenient validation.
- `codec/reader.py`: raw TipTap node to typed model.
- `codec/writer.py`: typed model to raw/dumped JSON.
- Keep `codec/__init__.py` as the compatibility export surface.

### 5. `shared/service.py` Is Named Too Broadly

Evidence:

- Extracts shared families.
- Stamps shared IDs.
- Checks shared presence.
- Generates shared IDs.
- Calculates fingerprints.
- Applies shared sync with tree replacement.
- Normalizes shared IDs.

Clean Code concern:

`service.py` does not communicate intent. The functions are related, but not all at the same abstraction level.

Recommended shape:

- `shared/identity.py`: `normalize_shared_id`, `new_shared_id`, `shared_id`, `stamp_shared`
- `shared/fingerprint.py`: `fingerprint_shared`
- `shared/families.py`: `shared_families`, conflict policy
- `shared/sync.py`: `sync_shared`, merge behavior
- `shared/__init__.py`: compatibility re-exports

### 6. Public API Surface Is Broad

Evidence:

The root package exports nodes, facade classes, constants, edit commands, shared helpers, task helpers, text helpers, policy helpers, and contract modules.

Clean Code concern:

Broad public surfaces make refactoring risky. Some exports are clearly user-facing (`Content`, `Paragraph`, `Text`), while others may be internal implementation details exposed accidentally (`content_id`, `is_parseable`, `node_id`, `tiptap_id`).

Recommended action:

Create a public API decision table before removing or renaming anything:

- Public and stable
- Public but provisional
- Internal but currently exported for compatibility
- Internal and safe to move

Then add API snapshot tests so refactors can move implementation without breaking imports.

### 7. Conceptual Dependency Direction Needs Tightening

Observed direction:

- `content` depends on `codec`, `model`, `select`, and `walk`.
- `select` depends on `edit`, `tree`, `walk`, `model`, and `codec`.
- `edit.commands` depends on `model`, `codec`, and function-local `Content`.
- `shared.service`, `tasks.query`, and `text.extract` depend on `Content`.

Concern:

`Content` is both a facade used by higher-level workflows and a dependency of lower-level package helpers. The function-local imports in `edit.commands` are the clearest symptom.

Recommended target direction:

- `contract`, `types`, `exceptions`: base layer
- `model`: domain AST layer
- `codec`: raw I/O to model boundary
- `walk`, `tree`: AST utilities
- `edit/node`: AST transforms
- `content`: public facade
- `text`, `tasks`, `shared`, `edit/document`: user-facing workflows that may depend on `Content`
- root `__init__.py`: public exports only

## Refactor Plan

### Phase 0: Safety Rails

Before moving files:

- Add public import tests for all names exported from `tiptap_python_utils.__all__`.
- Add package-level import tests for compatibility imports such as `tiptap_python_utils.model.ContentTuple`.
- Keep current behavior tests green.

### Phase 1: Make `model/__init__.py` Re-export Only

Move implementation into real modules while preserving old import paths.

Proposed files:

- `model/base.py`
- `model/nodes.py`
- `model/registry.py`
- `model/payload.py`

Acceptance criteria:

- `model/__init__.py` contains only docstring, imports, and `__all__`.
- Existing tests pass unchanged.
- No public imports break.

### Phase 2: Split Edit Layers

Separate typed node transforms from document-level commands.

Proposed files:

- `edit/node.py`
- `edit/document.py`

Acceptance criteria:

- No function-local `from ..content import Content` in low-level node edit code.
- `edit/__init__.py` preserves current exports.

### Phase 3: Clarify Codec Boundaries

Split raw parsing from model reading/writing if `codec/json.py` keeps growing.

Acceptance criteria:

- raw JSON validation can be tested independently from AST hydration.
- AST reading depends on `model`, but model does not depend on codec.

### Phase 4: Rename and Split Shared Internals

Replace generic `service.py` with intent-revealing modules.

Acceptance criteria:

- public shared helpers still import from `tiptap_python_utils`.
- implementation files communicate purpose by filename.

### Phase 5: Revisit Public API

Decide which helpers should remain stable public API.

Candidates to classify:

- `content_id`
- `node_id`
- `tiptap_id`
- `is_parseable`
- `EMPTY_DOCUMENT_CONTENT`
- `codec` helpers
- `tree` helpers
- `selection_id`

## Recommended First Change

Start with `model/__init__.py`. It is the clearest violation and the highest leverage cleanup. The refactor can be done without changing behavior by moving code into dedicated modules and keeping `model/__init__.py` as a compatibility export file.

Do not start by deleting exports. First make the internal organization honest, then decide whether the public API should shrink.
