# R6 执行台账

- plan_id: `AAK-LOCAL-GREEN-ABSORB-FIRST-20260919-R6`
- taskpack_revision: `R6`
- taskpack_sha256: `dcc51e922a35d30ca361e9014e040674b62cee644a3ea57aae12ffa6c2949529`
- baseline_head_at_registration: `61c482967ed1de44e0fcc0f92f99e2672862c0f1`
- delivery line: `main = Local Green Development Line`
- release status: `FROZEN`; no tag/release/product-version promotion

## 当前切片

### A00 — Authority Reset

状态：`TESTED_LOCAL`

已完成：

- 将用户提供的 R6 任务包保存到 `docs/authority/taskpack-0919-r6/TASKPACK.md`。
- 生成 `EXECUTOR-START.md`、`TASKS.json`、`MANIFEST.json`，并绑定任务包 SHA-256。
- 将 `AGENTS.md` 与 `docs/CONFIGURATION_AUTHORITY_INDEX.md` 的当前计划指针切换到 R6。
- 保留 R5、R3.1 及更早任务包和收据，不删除历史。

证据：

- subject_sha: `48a83e07a13d3c2bf09f8d9b46ffffd73482c104`
- tests: `tests/test_documentation_authority_index.py tests/test_path_conventions.py` — 30 passed, exit 0
- evidence_level: `TESTED_LOCAL`

### A01–A16

除已登记切片外，状态为 `PLANNED` 或 `BLOCKED_BY_PRECONDITION`；不从 R5 的 `PARTIAL` 或 `DEFERRED` 自动提升。每个切片须先登记真实代码、输入边界、测试命令和证据等级。

## 证据规则

文档、计划、静态检查和构建结果不能替代运行时、独立审计或 Owner Gate。未测项目标记 `NOT_EXECUTED`；缺外部资源、Owner 决策、证书、干净机或真实 Green 资格时标记 `BLOCKED`。

## A03 — Capability Absorption Registry

状态：`TESTED_LOCAL`

- subject_sha: `9c66fbce27c47d63ca8d6cffd75edba114d548bb`
- changed_paths: `config/schemas/capability-absorption-registry.schema.json`, `docs/truth/CAPABILITY_ABSORPTION_REGISTRY.yaml`, `tests/test_capability_absorption_registry.py`
- upstream_absorbed: none; donor entries are candidates/reference/algorithm or sidecar roles only
- upstream_version_or_sha: `UNPINNED_REVIEW_REQUIRED` for unverified upstreams
- license: every unverified upstream is explicitly marked pending readback; internal core is first-party MIT
- tests: `tests/test_documentation_authority_index.py tests/test_capability_absorption_registry.py` — 12 passed, exit 0
- actual_runtime_result: registry/schema validation only; no external provider was started
- data_touched: repository registry and schema only
- external_paths_touched: none
- limitations: exact upstream revisions, licenses, model licenses, benchmarks and runtime probes remain open
- rollback: revert commit `9c66fbce27c47d63ca8d6cffd75edba114d548bb`; canonical existing supply-chain ledger remains preserved
- remaining_gap: A02 resource schema decision and A04 Knowledge/Source V3 contract

## A01 — Version & Release Freeze

状态：`TESTED_LOCAL`

- subject_sha: `e065b0363896966e4b343c6ecc945e838809861d`
- changed_paths: `docs/current/R6-VERSION-RELEASE-FREEZE.md`, `tests/test_r6_version_release_freeze.py`
- upstream_absorbed: none
- upstream_version_or_sha: not applicable
- license: not applicable
- tests: `tests/test_r6_version_release_freeze.py tests/test_product_version_truth_contract.py tests/test_release_architecture.py` — 7 passed, exit 0
- actual_runtime_result: structural workflow/manifest contract only; no tag, release, installer or Green replacement executed
- data_touched: release contract documentation and tests only
- external_paths_touched: none
- limitations: exact-SHA CI and installed runtime remain separate gates
- rollback: revert commit `e065b0363896966e4b343c6ecc945e838809861d`
- remaining_gap: owner-controlled release reopening after A16 only

## A02 — Resource / Path / Environment Authority

状态：`BLOCKED_BY_OWNER_DECISION`

- current evidence: `config/environment/capability-requirements.yaml` has three intentionally recorded schema deviations (empty plugins category, shared Model library path outside the external root, and shared-model-library install method).
- reason: resolving these requires choosing schema semantics for the separately registered `shared_models` root; silently relaxing containment or inventing a plugin would change governance.
- safe next step: decide whether to extend the manifest with a resource-root identifier and a corresponding schema/resolver contract; do not modify shared libraries or copy model assets.

## A04 — Knowledge / Source Model V3 contract

状态：`TESTED_LOCAL_PARTIAL`

- subject_sha: `b1df307c353112928df410780ea3f0695f2a82a3`
- changed_paths: `app/contracts/knowledge_v3.py`, `app/contracts/__init__.py`, `packages/contracts/v3/knowledge-source.schema.json`, `packages/contracts/v3/__init__.py`, `tests/test_knowledge_source_v3_contract.py`
- upstream_absorbed: none; this is a first-party contract layer
- upstream_version_or_sha: contract `3.0.0`
- license: first-party MIT
- tests: A04 contract + existing machine/graph governance set — 19 passed; standalone V3/schema set — 6 passed; exit 0
- actual_runtime_result: Pydantic and JSON-schema validation only; no database migration or UI journey run
- data_touched: contract code and tests only
- external_paths_touched: none
- limitations: Rust SQLite schema/migration, API serialization, Avalonia routes, and real first-use evidence still not wired to V3
- rollback: revert commit `b1df307c353112928df410780ea3f0695f2a82a3`; existing V1 contracts and storage remain intact
- remaining_gap: implement and test Core persistence/API adapter without weakening single-writer rules

## A05 — Multiformat Pipeline

状态：`TESTED_LOCAL_PARTIAL`

- subject_sha: `47b476d7`
- changed_paths: `app/contracts/format_execution_v1.py`, `packages/contracts/v1/format-execution-receipt.schema.json`, `tests/test_format_execution_v1.py`, `app/contracts/__init__.py`
- contract: every receipt carries original retention, transform engine/version, loss status/notes, structure counts/kinds, block anchors, quality facts and explicit fallback state
- adapter: existing `ConversionRun` can be adapted through `FormatExecutionReceiptV1.from_conversion_run` without changing the SQLite writer or storage schema
- tests: `tests/test_format_execution_v1.py tests/test_conversion_run.py tests/test_workspace_pipeline_multiformat.py` — 16 passed, exit 0; after schema alias cleanup A05 standalone — 4 passed, exit 0
- actual_runtime_result: local contract and existing workspace pipeline tests only; no claim that external Docling/OCR/ASR/Office engines are installed or complete
- data_touched: repository contract, generated schema and tests only
- external_paths_touched: none
- limitations: Rust/Core persistence wiring, per-format quality measurement, external engine version readback and R6 real first-use promotion remain open
- rollback: revert commit `47b476d7`; existing conversion-run storage and adapters remain intact
- remaining_gap: wire receipts into the canonical Core/API path and execute representative real fixtures before any format becomes `complete`

## A06 — Retrieval / Graph / Research

状态：`TESTED_LOCAL_PARTIAL`

- subject_sha: `2fd448a6`
- changed_paths: `app/contracts/derived_projection_v1.py`, `packages/contracts/v1/derived-projection.schema.json`, `tests/test_derived_projection_v1.py`, `app/contracts/__init__.py`
- contract: FTS/embedding/reranker/graph/research outputs are explicitly derived, rebuildable and read-only; each item references an allowed canonical source and source revision
- tests: `tests/test_derived_projection_v1.py tests/test_graph_rag.py tests/test_knowledge_graph_contract.py tests/test_temporal_graph.py` — 19 passed, exit 0
- actual_runtime_result: contract and existing deterministic graph/retrieval tests only; no LightRAG/Graphiti external provider or benchmark was started
- data_touched: repository contract, generated schema and tests only
- external_paths_touched: none
- limitations: runtime adapters still return legacy shapes in some paths; canonical Core projection wiring, provider version readback and retrieval quality benchmark remain open
- rollback: revert commit `2fd448a6`; existing graph and retrieval implementations remain intact
- remaining_gap: adapt real retrieval/research endpoints to this receipt and run exact-source restart/readback evidence

## A07 — Machine Memory / Growth

状态：`TESTED_LOCAL_PARTIAL`

- subject_sha: `d8211b2e`
- changed_paths: `app/contracts/machine_growth_v1.py`, `packages/contracts/v1/machine-growth.schema.json`, `tests/test_machine_growth_v1.py`, `app/contracts/__init__.py`
- contract: Experience → Lesson → Skill Candidate → Review → Reuse is explicit; reuse requires approved human review and machine_verified is permanently false
- tests: `tests/test_machine_growth_v1.py tests/test_experience_harvest.py tests/test_distillation_review.py` — 12 passed, exit 0
- actual_runtime_result: existing harvest/distillation local SQLite tests and contract validation; no model provider or long-running reuse benchmark started
- data_touched: repository contract, generated schema and tests only
- external_paths_touched: none
- limitations: receipt emission is not yet wired into all experience and distillation writes; candidate/retest restart evidence remains open
- rollback: revert commit `d8211b2e`; existing experience and distillation behavior remains intact
- remaining_gap: emit the receipt from the canonical writer and prove review→reuse→retest on a real local journey
