# Project naming alignment matrix

> 这份矩阵只记录影响范围和迁移边界，不执行跨文件批量替换。机器身份以
> `config/naming-registry.yaml` 和 `docs/NAMING_ENCODING_CONVENTIONS.md` 为唯一规范。

## Canonical identity

| Surface | Canonical value | User-facing value | Status |
| --- | --- | --- | --- |
| Core service ID | `core` | Cognitive Runtime / 认知运行时 | canonical |
| Core Python package | `app` | 不直接展示 | canonical |
| Knowledge service ID | `knowledge-base` | Knowledge Base / 知识库 | canonical |
| Knowledge Python package | `knowledge_base` | 不直接展示 | canonical |
| Research service ID | `inspiration-research` | Inspiration Research / 灵感研究 | canonical |
| Research Python package | `inspiration_research` | 不直接展示 | canonical |
| Product identity | — | ArcheAxis OS / 元枢系统 | product display |
| Workspace identity | — | ArcheAxis Cognitive Workspace / 元枢·观心 | product display |

## Reference classes

### Safe to preserve

- `Cognitive-Loop-OS`: repository name, remote URL, project root, historical handoff and audit references.
- `Cognitive-OS`: deprecated core alias and historical architecture references.
- `Knowledge-Base`: deprecated service alias, compatibility prose and historical task-pack references.
- `Inspiration-Research`: physical compatibility directory and deprecated launcher path.
- `ArcheAxis OS`: installer, desktop protocol, release and user-facing product identity.

These values must not be globally replaced: each belongs to a different identity surface.

### Canonicalize at new boundaries

New code, database fields, API contracts and machine-readable configuration must use:

- service IDs from the naming registry;
- Python package names for imports;
- product display labels only at the UI boundary;
- repository paths only where a filesystem or Git boundary requires them.

### Deferred migration candidates

The following are candidates for separate, reviewable migrations; they are not changed by this matrix:

1. `.codex.example/config.example.toml` remote project alias `Cognitive-OS`.
2. Older `docs/` architecture, audit and task-pack documents using project-era names.
3. `knowledge_base/README.md`, `inspiration_research/api.py` and facade defaults that expose deprecated aliases as target labels.
4. Release/CI strings that intentionally refer to `ArcheAxis OS` installer identity.
5. `Inspiration-Research/` compatibility launcher and its ignored data boundary.

Each candidate requires a contract/test update and a remote exact-SHA review before changing.

## Verification performed

- `config/naming-registry.yaml` defines the three canonical service IDs and explicit deprecated aliases.
- `docs/NAMING_ENCODING_CONVENTIONS.md` requires canonical IDs internally and aliases only at compatibility boundaries.
- Root layout contains both canonical Python packages and the intentionally retained
  `Inspiration-Research/` compatibility path.
- User-facing desktop code consistently uses `ArcheAxis OS` / `元枢系统`; repository and historical
  documents retain `Cognitive-Loop-OS` where that is the repository identity.
- No bulk rename is authorized by this matrix, and no runtime, credential, external-drive or user-WIP
  path is changed.

## Exit criteria for a future rename

A future naming migration is ready only when it has:

1. an explicit source-to-target mapping;
2. compatibility aliases and deprecation behavior;
3. persisted-value migration and rollback evidence;
4. import/API/CI/document reference scans;
5. exact-SHA CI and main readback;
6. no change to installer identity or user-facing product naming unless separately approved.
