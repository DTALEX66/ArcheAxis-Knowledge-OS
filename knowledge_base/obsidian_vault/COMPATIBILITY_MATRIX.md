# Obsidian Compatibility Matrix

Status of Obsidian vault features supported by archeaxis-workspace's
Obsidian projection layer (`shared/obsidian_projection.py`) and the
synthetic test vault (`knowledge_base/obsidian_vault/`).

## Feature Coverage

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| Plain Markdown (.md) reading | ✅ Fully compatible | `adapter_contract:plaintext:md:passthrough` always installed; `convert_file()` returns content verbatim | No transformation — passes through verbatim |
| YAML frontmatter | ✅ Read preserved | `Projection.frontmatter` extracts tags, aliases, dates; rendered by `_render_frontmatter()` | No deep schema validation — values passed as-is |
| `[[Wikilinks]]` to other notes | ✅ Parsed and emitted | `_extract_wikilinks()` extracts targets; render functions emit `[[target]]` in body | One-way projection: wikilinks point to vault pages but no auto-resolve |
| `[[Wikilink\|display text]]` | ✅ Parsed and emitted | `_extract_wikilinks()` strips display text; projection emits `[[target\|display]]` | Display text preserved in output |
| `#Tags` inline | ✅ Parsed and emitted | `_extract_tags()` finds `#tag` and `#tag/subtag` patterns | Must not collide with `##` headings or code blocks |
| Frontmatter `tags: [a, b]` | ✅ Extracted | `_extract_tags()` reads from `frontmatter.tags` | Merged with inline tags in `Projection.tags` |
| `> [!note]` callouts | ✅ Passthrough preserved | Plain Markdown — no transformation needed | Rendered verbatim; only standard callout types tested |
| `> [!tip]`, `> [!warning]`, `> [!error]`, `> [!info]`, `> [!important]` | ✅ Passthrough preserved | Obsidian-specific qualifiers preserved | Rendered verbatim |
| `![[Embedded note]]` | ✅ Passthrough preserved | Obsidian embed syntax passes through as plain text | Not rendered as transclusion — markdown passthrough only |
| `[link](attachments/file.png)` | ✅ Relative link preserved | Passthrough keeps relative paths | Link validation not currently implemented |
| Code blocks ` ```python ` | ✅ Fully compatible | Standard Markdown — no transformation | Syntax highlighting preserved |
| Tables (`\| ... \|`) | ✅ Fully compatible | Standard Markdown | Alignment markers preserved |
| Lists (ordered/unordered) | ✅ Fully compatible | Standard Markdown | Nested lists preserved |
| **Bold**, *italic*, ~~strikethrough~~ | ✅ Fully compatible | Standard Markdown | All inline formatting preserved |
| `.obsidian/` directory | ✅ Structure preserved | JSON config files kept as-is | Not interpreted — structure only |
| Multi-level directory hierarchy | ✅ Read/write supported | `Projection.path` supports subdirectories; vault has `Daily/`, `Lessons/`, `TaskPacks/`, `Traces/`, `attachments/` | Directory structure preserved |
| Heading anchors (`[[page#Section]]`) | ⚠️ Partially supported | Wikilink parser extracts target including `#Section` | Anchor portion passed through; no cross-reference validation |

## Not Supported / Future

| Feature | Status | Reason |
|---------|--------|--------|
| Canvas / Excalidraw | ❌ Not supported | No JSON/.canvas parsing; not a Markdown format |
| Live preview plugins | ❌ Not supported | Only static Markdown is processed |
| Graph view data export | ❌ Not supported | Graph is Obsidian-native; no export format exists |
| Bidirectional sync | ❌ Not supported | One-way projection only (KB → Obsidian) |
| Incremental sync / diff | ❌ Not supported | Full rewrite on each projection |
| Conflict detection | ❌ Not supported | No write-back path to detect conflicts |
| Plugin syntax (Dataview, Templater, etc.) | ❌ Not supported | Plugin-specific syntax is opaque Markdown |
| Tags view / tag graph | ❌ Not supported | Tags extracted but not linked to Obsidian's tag pane |
| Vault search indexing | ❌ Not supported | No FTS index of vault content |
| Any E:/ vault data | ❌ Blocked | Project boundary: no external vault access allowed |
| Automatic attachment copying | ❌ Not supported | Attachments are copied only as relative path references |
| `#heading` in `[[page#heading]]` | ⚠️ Partial | Wikilink anchor parsed but not validated against heading list |

## Test Vault Structure

The synthetic test vault at `knowledge_base/obsidian_vault/` contains:

```text
obsidian_vault/
├── .obsidian/
│   ├── app.json              — Obsidian app settings
│   ├── core-plugins.json     — Enabled plugin list
│   └── appearance.json       — Theme / font settings
├── index.md                  — Vault home / Map of Content
├── card-system.md            — Knowledge card lifecycle (wikilinks, tags, frontmatter, callouts, code)
├── task-management.md        — Context pack tracking (wikilinks, callouts, JSON example)
├── review-workflow.md        — SM-2 review pipeline (table, math, callouts, wikilinks)
├── daily-brief-format.md     — Brief format reference (wikilinks, code, callouts)
└── attachments/
    └── index.md              — Attachment placeholder directory
```

## Verification

Each feature in the ✅ and ⚠️ rows above has a corresponding test in
`tests/test_obsidian_projection.py` and `tests/test_obsidian_vault.py`.
