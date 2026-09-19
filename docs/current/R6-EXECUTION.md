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

- subject_sha: `766a281db2c2f1c71d57360e89b4263bf4c46a70`
- changed_paths: `app/contracts/knowledge_v3.py`, `app/contracts/__init__.py`, `packages/contracts/v3/knowledge-source.schema.json`, `packages/contracts/v3/__init__.py`, `tests/test_knowledge_source_v3_contract.py`, `crates/archeaxis-api/src/lib.rs`, `crates/archeaxis-api/tests/knowledge_v3_projection.rs`, `crates/archeaxis-domain/src/knowledge.rs`
- upstream_absorbed: none; this is a first-party contract layer
- upstream_version_or_sha: contract `3.0.0`
- license: first-party MIT
- tests: `tests/test_knowledge_source_v3_contract.py tests/test_documentation_authority_index.py` — 15 passed, exit 0; `cargo test -p archeaxis-api --test knowledge_v3_projection --test v01_journey --test api_closed_loop` — 6 passed, exit 0
- actual_runtime_result: Rust Core now exposes a read-only `/api/v1/knowledge-items/:id/v3` projection with supersession and anchor-source readback; machine revision keeps its original machine provenance; legacy confidence remains explicit `null` when unmeasured
- data_touched: contract code and tests only
- external_paths_touched: none
- limitations: V3 write-side metadata is still derived from the legacy row, temporal/risk/confidence measurements are not persisted by the legacy create route, Avalonia routes and real first-use evidence remain open; no claim of full V3 runtime completion
- rollback: revert commit `b1df307c353112928df410780ea3f0695f2a82a3`; existing V1 contracts and storage remain intact
- remaining_gap: add an owner-approved canonical write path for V3 governance metadata, then wire UI and run a real restart/readback journey without dual-writing

## A05 — Multiformat Pipeline

状态：`TESTED_LOCAL_PARTIAL`

- subject_sha: `95bc3fcc1a19de6b2d681920508571512ff16629`
- changed_paths: `app/contracts/format_execution_v1.py`, `app/workspace/service.py`, `tests/test_format_execution_v1.py`, `tests/test_workspace_pipeline_multiformat.py`
- contract: every receipt carries original retention, transform engine/version, loss status/notes, structure counts/kinds, block anchors, quality facts and explicit fallback state
- adapter: existing `ConversionRun` is now projected by `GET /api/library/{raw_sha256}/conversion-run` through `FormatExecutionReceiptV1.from_conversion_run`; SQLite writer and storage schema remain unchanged
- tests: `tests/test_format_execution_v1.py tests/test_workspace_pipeline_multiformat.py` — 12 passed, exit 0
- actual_runtime_result: local workspace API returns a path-free, structural receipt with measured block/anchor counts and explicit unmeasured semantic-fidelity/fallback facts; receipt status remains `partial`
- data_touched: repository contract, service projection and tests only; no external assets or user data
- external_paths_touched: none
- limitations: receipt is not a proof of semantic quality, fallback attempts are not persisted by the legacy run, external Docling/OCR/ASR/Office engines and real first-use fixtures remain unverified; no format is promoted to `complete`
- rollback: revert commit `95bc3fcc1a19de6b2d681920508571512ff16629`; prior conversion-run summary and storage remain intact
- remaining_gap: wire receipt emission into canonical Core/API if required by the final architecture, then execute representative real fixtures before any format becomes `complete`

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

## A08 — Human Learning Kernel

状态：`TESTED_LOCAL_PARTIAL`

- subject_sha: `235a89c7`
- changed_paths: `app/contracts/learning_kernel_v1.py`, `packages/contracts/learning/v1/learning-kernel.schema.json`, `tests/test_learning_kernel_v1.py`, `app/contracts/__init__.py`
- contract: each exposure binds question/knowledge versions, source anchors, stable exposure and retry IDs, correctness/rating, FSRS state transition and due schedule
- tests: `tests/test_learning_kernel_v1.py tests/test_axw051b_due_queue.py tests/test_desktop_learning_review_contract.py` — 15 passed, exit 0
- actual_runtime_result: local FSRS/due-queue and source-level Avalonia retry contract tests; no .NET runtime or real first-use journey started
- data_touched: repository contract, generated schema and tests only
- external_paths_touched: none
- limitations: the new receipt is not yet emitted by the Core review route; adaptive content selection and restart readback remain unverified
- rollback: revert commit `235a89c7`; existing review v2 and FSRS paths remain intact
- remaining_gap: wire receipt emission to the single Rust writer and prove one real human review through restart

## A09 — Domain Learning Packs

状态：`TESTED_LOCAL_PARTIAL`

- subject_sha: `4e0d6b5a`
- changed_paths: `app/contracts/domain_pack_v1.py`, `config/domain-packs/general.json`, `config/domain-packs/math-physics.json`, `config/domain-packs/programming.json`, `config/domain-packs/design.json`, `packages/contracts/v1/domain-pack.schema.json`, `tests/test_domain_pack_v1.py`
- contract: four domain manifests share one versioned structure, canonical-only source policy, explicit learning modes, assessment types and canonical object types
- tests: `tests/test_domain_pack_v1.py tests/test_lesson_contract.py tests/test_axw051b_due_queue.py` — 14 passed, exit 0
- actual_runtime_result: manifest/schema and existing lesson/learning queue tests only; manifests are explicitly `contract_only`
- data_touched: repository contract, four manifests, generated schema and tests only
- external_paths_touched: none
- limitations: no domain curriculum or real domain-specific first-use behavior has been claimed; no external content was imported
- rollback: revert commit `4e0d6b5a`; existing lesson and queue behavior remains intact
- remaining_gap: populate reviewed domain content, connect pack selection to Core and run distinct math/programming/design journeys

## A10 — Courseware / Interactive Learning

状态：`TESTED_LOCAL_PARTIAL`

- subject_sha: `2064dc4d`
- changed_paths: `app/contracts/courseware_v1.py`, `packages/contracts/v1/courseware-artifact.schema.json`, `tests/test_courseware_v1.py`, `app/contracts/__init__.py`
- contract: lesson/slide/quiz/visual/simulation/PBL/coding/audio-video artifacts share source IDs, knowledge IDs, domain pack, renderer version and human-review flags
- tests: `tests/test_courseware_v1.py tests/test_lesson_contract.py tests/test_canvas_projection.py` — 9 passed, exit 0
- actual_runtime_result: contract, Lesson adapter and Canvas projection tests only; no Avalonia renderer or real interactive activity executed
- data_touched: repository contract, generated schema and tests only
- external_paths_touched: none
- limitations: artifact contract is not yet connected to a courseware renderer or Core job receipt; no video/audio or simulation quality claim
- rollback: revert commit `2064dc4d`; existing lesson and Canvas behavior remains intact
- remaining_gap: wire renderer outputs to canonical source/knowledge references and run one real reviewed interactive lesson

## A11 — Local Model Pool

状态：`TESTED_LOCAL_PARTIAL`

- subject_sha: `8ee33bc6`
- changed_paths: `app/contracts/model_pool_v1.py`, `config/model-profiles/r6-capability-pool.json`, `packages/contracts/v1/model-capability-pool.schema.json`, `tests/test_model_pool_v1.py`
- contract: role → model → quantization → runtime → memory → fallback is explicit, with measured/unmeasured status and evidence references
- source: repository `config/model-profiles/local-2026-09-05.yaml` historical profile only; no shared Model library files were copied or modified
- tests: `tests/test_model_pool_v1.py tests/test_asr_model_resolution.py tests/test_axw096a_benchmark.py` — 12 passed, exit 0
- actual_runtime_result: manifest validation and existing model-resolution/benchmark utility tests; no fresh model benchmark was run
- data_touched: repository contract, manifest, generated schema and tests only
- external_paths_touched: none
- limitations: current shared model inventory, VRAM/RAM/latency measurements, and current runtime health remain unverified; entries are not a release selection
- rollback: revert commit `8ee33bc6`; existing model profile and resolver remain intact
- remaining_gap: perform owner-approved read-only inventory of the fixed Model library path, then run bounded role benchmarks with exact receipts

## A12 — Avalonia Product Shell

状态：`TESTED_LOCAL_PARTIAL`

- subject_sha: `4bfbdbcc`
- changed_paths: `app/contracts/desktop_routes_v1.py`, `config/desktop/routes-v1.json`, `packages/contracts/v1/desktop-routes.schema.json`, `tests/test_desktop_routes_v1.py`
- contract: required shell surfaces map to explicit Core endpoints and canonical writer `archeaxis-core-rust-sqlite`; source reader path is verified as `/api/v1/imports`
- tests: `tests/test_desktop_routes_v1.py tests/test_desktop_learning_review_contract.py tests/test_desktop_runtime.py` — 12 passed, exit 0
- actual_runtime_result: source-level route/provenance/retry checks and Python Core readiness tests; `dotnet` command not found on this host
- data_touched: repository contract, route manifest, generated schema and tests only
- external_paths_touched: none
- limitations: Avalonia compile, self-contained bundle, clean-machine startup and no-terminal behavior remain unverified/blocked by missing .NET SDK/runtime
- rollback: revert commit `4bfbdbcc`; existing shell source and Core supervisor remain intact
- remaining_gap: use the registered external toolchain or CI desktop-vnext gate for exact-SHA build and runtime verification; do not install global runtime here

## A13 — Legacy Migration + Local Green

状态：`TESTED_LOCAL_PARTIAL`

- subject_sha: `ce54472a`
- changed_paths: `app/contracts/local_green_v1.py`, `packages/contracts/v1/local-green-identity.schema.json`, `tests/test_local_green_v1.py`
- contract: Local Green identity fixes `distribution=local-green`, historic public base `v0.6.14`, exact source/tree/runtime digests and `published=false`
- tests: `tests/test_local_green_v1.py tests/test_green_candidate_assembly.py tests/test_green_candidate_verifier.py tests/test_migration_runner.py` — 48 passed, 1 skipped, exit 0
- actual_runtime_result: project-local candidate assembler/verifier and isolated migration runner tests only; no real Green runtime was touched
- data_touched: repository contract, generated schema and tests only
- external_paths_touched: none; `D:\All projects\ArcheAxis.Knowledge.Green-x64` and real material library were not modified
- limitations: no nonempty legacy copy migration, staging first-use, restart readback, in-place replacement or rollback has been executed
- rollback: revert commit `ce54472a`; existing candidate and migration utilities remain intact
- remaining_gap: obtain exact-SHA self-contained desktop/Core candidate, stage it under `.project-local`, then owner-gated Green replacement with hash backup and rollback evidence

## A14 — Full Human–Machine Closed Loop Receipt

状态：`TESTED_LOCAL_PARTIAL`

- subject_sha: `2e56b94e56ad7aeb552e92da0f22604e486baece`
- changed_paths: `app/contracts/closed_loop_v1.py`, `app/contracts/__init__.py`, `packages/contracts/v1/closed-loop.schema.json`, `tests/test_closed_loop_v1.py`
- contract: the receipt fixes the ordered stages source → knowledge → human_learning → machine_use → evaluation → correction → lesson → retest; completion requires real evidence for every stage and forbids synthetic completion
- tests: `tests/test_closed_loop_v1.py tests/test_golden_journey_receipt.py tests/test_core_client.py tests/test_co_learning_loop.py` — 35 passed, exit 0
- actual_runtime_result: contract plus existing local Golden Journey/Core/co-learning tests; no real owner-approved source-to-retest journey, external model, Green runtime or restart readback was executed
- data_touched: repository contract, generated schema and tests only; no external library, model library, real data library, test corpus or Green installation was modified
- limitations: this is an evidence boundary and validation contract, not proof that every runtime stage is wired or complete
- rollback: revert commit `2e56b94e56ad7aeb552e92da0f22604e486baece`; existing source, Core and learning paths remain intact
- remaining_gap: emit this receipt from the canonical Rust/SQLite journey and collect real restart/readback evidence before A14 can be promoted beyond partial

## A15 — Independent Audit

状态：`PLANNED`

- prerequisite: A14 has a tested contract, but its real journey and restart/readback evidence are still open
- execution_status: `NOT_EXECUTED`; no independent reviewer or unseen-example audit was claimed in this run
- boundary: the implementation author cannot self-sign Q00/Q01 or convert local contract tests into an independent audit result
- next_evidence: an independently produced report must bind each PASS/FAIL/BLOCKED finding to an exact subject SHA and the corresponding runtime evidence

## A16 — Owner Gate

状态：`PLANNED`

- execution_status: `NOT_EXECUTED`
- blocker: Owner Gate requires the independent audit and the unresolved A02 resource-root decision, desktop runtime evidence, real Green migration/restart/rollback evidence and full closed-loop journey
- release_rule: R6 remains `IN_PROGRESS` with release `FROZEN`; no tag, release or Local Green replacement was performed
