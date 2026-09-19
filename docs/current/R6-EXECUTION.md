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

### A05 回归收口 — workspace converter seam

- status: `TESTED_LOCAL`
- subject_sha: `029fb76f200acd1b58d95d2a310bb61980835c7c`
- changed_paths: `app/workspace/service.py`, `tests/test_workspace_api.py`
- problem: a workspace upload regression bypassed the legacy `service.convert_file` injection seam and sent an invalid test WAV into the real ASR/FFmpeg path
- fix: default intake keeps `convert_file_with_trace`; an explicitly replaced `service.convert_file` remains supported and receives a synthesized single-engine `ConversionTrace`
- tests: RED original regression exit `1`; focused workspace/format/multiformat suite `44 passed, 3 warnings`, exit `0`; `git diff --check` exit `0`
- evidence: conversion receipt `attempted_engines` is asserted for both retained raw assets; no external paths or user data touched
- remaining_gap: semantic conversion quality, external engines, real fixtures and complete-format promotion remain open
- rollback: revert commit `029fb76f200acd1b58d95d2a310bb61980835c7c`

### A05 回归收口 — fallback readback

- status: `TESTED_LOCAL`
- subject_sha: `97300cc6c8e6389edc33f5dc32adaec8761e6c58`
- changed_paths: `tests/test_workspace_pipeline_multiformat.py`
- behavior: a synthetic `primary → passthrough` fallback now travels through `intake_upload`, SQLite `loss_report_json`, and the public `conversion-run` receipt with attempted engines, selected engine, and fallback reason intact
- tests: `tests/test_workspace_pipeline_multiformat.py tests/test_format_execution_v1.py tests/test_conversion_run.py` — `19 passed, 3 warnings`, exit `0`; `git diff --check` exit `0`
- limitations: synthetic receipt evidence only; real external engines, semantic quality and real fixtures remain unverified
- rollback: revert commit `97300cc6c8e6389edc33f5dc32adaec8761e6c58`

### A09/A10 contract increment — General prerequisite graph

- status: `TESTED_LOCAL`
- subject_sha: `d581be95`
- changed_paths: `app/contracts/general_learning_v1.py`, `tests/test_general_learning_contract.py`
- behavior: General CourseManifest now requires prerequisite IDs to resolve within the manifest and rejects self-reference and multi-node cycles while retaining valid prerequisite chains
- tests: `tests/test_general_learning_contract.py tests/test_domain_pack_v1.py tests/test_courseware_v1.py tests/test_rag_pipeline.py tests/test_derived_projection_v1.py` — `22 passed, 1 warning`, exit `0`; Ruff on both changed files exit `0`
- limitations: this is a contract gate; it does not prove real curriculum content, renderer execution, embedding/reranker quality or runtime learning
- rollback: revert commit `d581be95`

### 合并受影响 Python 门禁回读

- subject_sha: `d46f8932f6dc5ba520535bc6f4c26e0f366bb104`
- tests: `tests/test_general_learning_contract.py tests/test_domain_pack_v1.py tests/test_courseware_v1.py tests/test_rag_pipeline.py tests/test_derived_projection_v1.py tests/test_workspace_pipeline_multiformat.py tests/test_format_execution_v1.py tests/test_conversion_run.py tests/test_workspace_api.py`
- result: `72 passed, 3 warnings`, exit `0`
- limits: Python contract/workspace evidence only; cargo/.NET, real external engines/models, Green and full M0 loop remain unverified or blocked

### A07/P4.1 contract increment — human review coupling

- status: `TESTED_LOCAL`
- subject_sha: `b20d87af26b120161bed1dab3ae21da3c64f24f6`
- changed_paths: `packages/contracts/v1/machine-feedback.schema.json`, `tests/contract/test_deepseek_contract_cases.py`
- behavior: `correction_applied` and `correction_reverted` now require `feedback.reviewed_by_human=true`; unreviewed correction events are rejected
- tests: specified machine-loop Python regression — `45 passed, 5 warnings`, exit `0`; RED had exit `1` against the old schema; `git diff --check` exit `0`
- limitations: JSON Schema/contract evidence only; real model execution, correction/retest runtime and Rust integration remain open
- rollback: revert commit `b20d87af26b120161bed1dab3ae21da3c64f24f6`

### A13/P5 Python backup hardening

- status: `TESTED_LOCAL`
- subject_sha: `fc0df3a182abed4feded8eeb0ab25b88bb4bcadb`
- changed_paths: `app/exchange/backup.py`, `tests/test_axw094b_backup.py`
- behavior: backup verify/restore rejects absolute, dot, parent and symlink-escaping manifest paths; verify also rejects ordinary files not declared by the manifest while excluding the manifest and known transient lease suffixes
- tests: first hardening regression `15 passed, 1 warning`; export/backup/migration/loss suite `50 passed, 1 warning`; backup/migration suite `45 passed, 1 warning`; second backup/export/API suite `46 passed, 3 warnings`; all exit `0`
- limitations: Python directory-backup evidence only; Rust SQLite schema/FK/source-object hash, workspace identity, real data migration and Green activation remain open
- rollback: revert commits `67dc2356` and `fc0df3a182abed4feded8eeb0ab25b88bb4bcadb`

### A14 contract guard — correction/retest evidence refs

- status: `TESTED_LOCAL`
- subject_sha: `274de700c4dc4c02ede5d15fb3938fef5498677f`
- changed_paths: `app/contracts/closed_loop_v1.py`, `tests/test_closed_loop_v1.py`
- behavior: a `complete` closed-loop receipt now requires non-empty evidence refs on both `correction` and `retest` stages
- tests: focused RED against the old implementation exited `1`; Python closed-loop/feedback/machine regression `74 passed, 5 warnings`, exit `0`; `git diff --check` exit `0`
- limitations: this is a false-completion guard only; it does not add successor/task/restart IDs or prove a real runtime journey
- rollback: revert commit `274de700c4dc4c02ede5d15fb3938fef5498677f`

### 任务包级完成审计回读

- audit_subject_sha: `477bfd3532ae5c1fbd0e7c8af7f1d0c7311ef72b`
- result: R6 remains `IN_PROGRESS`, release remains `FROZEN`; no additional safe Python/contract card remains without inventing Owner/canonical/runtime semantics.
- next_ready_when_preconditions_exist: P3 real first-use path — Core Assessment → answer → Mastery/FSRS → full restart/readback — requires `cargo`, `.NET SDK` and permitted project-local fixtures.
- independent_gates: A15 remains `PLANNED / NO_EVIDENCE`; A16 remains Owner Gate. No local contract test is promoted to runtime, independent audit, Green or release evidence.

### 工具链恢复运行回读

- subject_sha: `d5776f6b3efb0d804396b1d4258aed43e032ffcd`
- Rust domain: exact shared cargo/rustc path and isolated project target; `cargo check --offline -p archeaxis-domain` exit `0`; `assessment`, `learning_state_persistence`, `machine_tasks` — `16 passed`; `cargo fmt` `NOT_EXECUTED` because rustfmt component is absent.
- .NET desktop: exact declared external SDK `10.0.400`; `ArcheAxis.Desktop.csproj` build `0 warnings, 0 errors`; CoreSupervisor apphost exit `0` with `stop-race` skipped; Vocabulary apphost exit `0`, `29 shared wire cases parsed`.
- API Rust: exact cargo/MSVC invocation reaches linker but fails `LNK1181: kernel32.lib`; API learning/machine tests remain `NOT_EXECUTED / BLOCKED` until the shared Windows SDK LIB is available.
- boundaries: no external toolchain files were modified; generated outputs stayed under project `.project-local` or project test output roots; no E/F, Green or real material library was accessed.

## A06 — Retrieval / Graph / Research

状态：`TESTED_LOCAL_PARTIAL`

- subject_sha: `4acfe197a39be5166788abfee71f49cda7d2b8f6`
- changed_paths: `app/workspace/vault.py`, `tests/test_vault_search_api.py`
- contract: FTS/embedding/reranker/graph/research outputs are explicitly derived, rebuildable and read-only; each item references an allowed canonical source and source revision
- tests: `tests/test_derived_projection_v1.py tests/test_vault_search_api.py tests/test_graph_rag.py tests/test_knowledge_graph_contract.py tests/test_temporal_graph.py` — 24 passed, exit 0
- actual_runtime_result: the read-only Vault substring search now emits a deterministic `archeaxis.derived-projection/v1` FTS receipt with path-free canonical source IDs, content-hash revisions, measured match predicates and explicit empty-result handling
- data_touched: repository Vault projection and tests only; no Vault or canonical knowledge rows are written
- external_paths_touched: none
- limitations: this is a deterministic lexical projection, not an embedding/reranker/graph/research quality benchmark; runtime adapters still return legacy shapes in other paths, provider version readback and exact-source restart/readback evidence remain open
- rollback: revert commit `4acfe197a39be5166788abfee71f49cda7d2b8f6`; existing Vault search behavior and derived-projection contract remain intact
- remaining_gap: adapt additional real retrieval/research endpoints to this receipt and run exact-source restart/readback evidence before claiming broad A06 closure

## A07 — Machine Memory / Growth

状态：`TESTED_LOCAL_PARTIAL`

- subject_sha: `a5c1b79f8e36eb3207a8e9c0c4688bf863b634b9`
- changed_paths: `app/agent/experience_harvest.py`, `app/agent/feedback.py`, `tests/test_agent_feedback.py`
- contract: Experience → Lesson → Skill Candidate → Review → Reuse is explicit; reuse requires approved human review and machine_verified is permanently false
- tests: `tests/test_agent_feedback.py tests/test_experience_harvest.py tests/test_machine_growth_v1.py tests/test_distillation_review.py tests/test_axw053_transform.py` — 21 passed, exit 0
- actual_runtime_result: execution feedback now emits a machine-growth receipt from the real local harvest path; it records experience and lesson evidence while leaving candidate, human review and reuse explicitly `skipped`
- data_touched: repository feedback/receipt code and tests only; receipt is returned in the caller response and does not auto-promote machine knowledge
- external_paths_touched: none
- limitations: receipt emission is wired to execution feedback but not every experience/distillation writer; candidate persistence, human review, reuse and retest restart evidence remain open; machine_verified stays false
- rollback: revert commit `a5c1b79f8e36eb3207a8e9c0c4688bf863b634b9`; existing experience and distillation behavior remains intact
- remaining_gap: connect the receipt to the remaining canonical distillation paths and prove review→reuse→retest on a real local journey

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

- subject_sha: `47246eea813bb2d2d012ca531057dd80be0813c2`
- changed_paths: `docs/current/R6-MODEL-LIBRARY-INVENTORY-20260919.json`
- contract: role → model → quantization → runtime → memory → fallback is explicit, with measured/unmeasured status and evidence references
- source: repository `config/model-profiles/local-2026-09-05.yaml` historical profile plus a fresh shallow read-only inventory of the registered shared model root
- tests: `tests/test_model_pool_v1.py tests/test_asr_model_resolution.py tests/test_axw096a_benchmark.py` — 12 passed, exit 0
- actual_runtime_result: `D:\\All projects\\Model library` exists as a non-reparse directory; shallow metadata found `ComfyUI`, `ollama`, `runtimes-tmp`, `sherpa-onnx`, `whisper` and one README; no weights or model file contents were read
- data_touched: one path-free metadata receipt in the repository; no model weights or shared files were copied
- external_paths_touched: `D:\\All projects\\Model library` read-only metadata only
- limitations: executable availability, model integrity, VRAM/RAM/latency measurements, licensing, current runtime health and role benchmarks remain unverified; entries are not a release selection
- rollback: revert commit `47246eea813bb2d2d012ca531057dd80be0813c2`; existing model profile and resolver remain intact
- remaining_gap: run bounded role benchmarks with exact receipts using only the registered shared models and project-local outputs

## A12 — Avalonia Product Shell

状态：`TESTED_LOCAL_PARTIAL`

- subject_sha: `e6b02afeb6b8611cf4973dafd3b261a1eeebec26`
- changed_paths: `docs/current/R6-DESKTOP-BUILD-20260919.json`, `docs/current/R6-DESKTOP-SMOKE-20260919.json`
- contract: required shell surfaces map to explicit Core endpoints and canonical writer `archeaxis-core-rust-sqlite`; source reader path is verified as `/api/v1/imports`
- tests: `tests/test_desktop_routes_v1.py tests/test_desktop_learning_review_contract.py tests/test_desktop_runtime.py` — 12 passed, exit 0; external .NET restore/build also passed with 0 warnings and 0 errors
- actual_runtime_result: registered .NET 10.0.400 built a Release `win-x64` self-contained candidate; the same candidate completed its built-in headless supervisor/Core smoke with exit 0 using a current-source Rust Core, and the workspace DB was created under `.project-local`
- data_touched: two project-local build/smoke receipts; build output, package cache and smoke DB remain under ignored `.project-local`
- external_paths_touched: none
- limitations: Avalonia navigation and real first-use, clean-machine startup, no-terminal behavior, signing and installer/uninstaller remain unverified; smoke is headless only, build bypassed the required `a0-gates` status on push, and nothing is installed in Green
- rollback: revert commit `e6b02afeb6b8611cf4973dafd3b261a1eeebec26`; existing shell source and Core supervisor remain intact
- remaining_gap: launch the candidate in an isolated project-local run, prove Core/readback and no-terminal behavior, then perform owner-gated staging/installation checks

## A13 — Legacy Migration + Local Green

状态：`TESTED_LOCAL_PARTIAL`

- subject_sha: `e6b02afeb6b8611cf4973dafd3b261a1eeebec26`
- changed_paths: `docs/current/R6-DESKTOP-BUILD-20260919.json`, `docs/current/R6-DESKTOP-SMOKE-20260919.json`
- contract: Local Green identity fixes `distribution=local-green`, historic public base `v0.6.14`, exact source/tree/runtime digests and `published=false`
- tests: `tests/test_local_green_v1.py tests/test_green_candidate_assembly.py tests/test_green_candidate_verifier.py tests/test_migration_runner.py` — 48 passed, 1 skipped, exit 0
- actual_runtime_result: project-local candidate assembler/verifier and isolated migration runner tests only; no real Green runtime was touched
- data_touched: repository contract, generated schema and tests only
- external_paths_touched: none; `D:\All projects\ArcheAxis.Knowledge.Green-x64` and real material library were not modified
- limitations: no nonempty legacy copy migration, staging first-use, restart readback, in-place replacement or rollback has been executed; the candidate has only been built, hashed and headlessly smoke-tested
- rollback: revert commit `e6b02afeb6b8611cf4973dafd3b261a1eeebec26`; existing candidate and migration utilities remain intact
- remaining_gap: stage the exact hashed candidate under `.project-local`, run migration diff/restart evidence, then owner-gated Green replacement with hash backup and rollback evidence

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

## M0 internal audit receipt — 2026-09-20

- `subject_sha`: `dc5aa97fc1d95f81a3c480901de7807dffd963f2`
- `scope`: P0 boundary/security, P2 Model library/Domain Pack, and P3/A13 migration/Green read-only audits; this receipt does not self-sign A15 or A16.
- `P0`: targeted boundary/security suites reported `54 passed, 1 skipped` and `104 passed, 1 skipped`, exit `0`; Rust/.NET security gates and full project gate remain `NOT_RUN` because `cargo`, `rustfmt`, and `dotnet` are unavailable.
- `P2`: Model library and Domain Pack are `PARTIAL`; the inventory is shallow metadata only, with no weights/content, executable health, benchmark, or runtime readback. General and the existing domain manifests remain `contract_only`; courseware contracts do not prove an interactive renderer.
- `P3/A13`: synthetic legacy-copy migration and historical project-local Green candidate/headless smoke receipts are valid within their bounded scopes; current exact-HEAD nonempty migration, GUI first-use, installer/signing, clean-machine, in-place Green replacement, and rollback remain `BLOCKED` or `NOT_RUN`.
- `boundary`: no E/F, credentials, private agent directories, external shared libraries, real material library, test source corpus, or existing Green runtime was read or modified.
- `next_card`: verify the P3 human-learning first-use path with an available Rust/.NET toolchain, including Assessment → answer → Mastery/FSRS → full restart readback; keep A15/A16 and Green replacement owner-gated.

## Continuation receipt — 2026-09-20 M0 P0/P3 closure slice

- `subject_sha`: `6b0896ea1d8be4e9b9a94ec0db9b7376ad2b7aa6`
- `P0`: added `scripts/maintenance/check_authority_sha_consistency.py`; it requires `HEAD == origin/main`, the authority record's latest commit to be `HEAD`, permits the current-main claim to name the record commit's first parent, and keeps `R6-STATE.subject_sha` as independently resolvable evidence identity. This prevents self-referential SHA false failures while catching stale pointers.
- `P3`: stateful Assessment reviews now persist an explicit open `mastery_projection` (`closed=false`) beside the learner answer and FSRS schedule; the projection does not claim Knowledge truth or completed mastery. A restart readback test covers Assessment, answer, FSRS state and the open projection.
- `tests`: `.venv\\Scripts\\python.exe -m pytest -p no:cacheprovider tests/test_authority_sha_consistency.py tests/test_model_pool_v1.py tests/test_domain_pack_v1.py tests/test_courseware_v1.py tests/test_general_learning_contract.py -q` — `17 passed, 1 warning`, exit `0`.
- `rust_tests`: `NOT_EXECUTED`; `cargo` and `rustfmt` remain unavailable. The new Rust projection behavior is `IMPLEMENTED_LOCAL / UNVERIFIED` until the named Cargo tests run.
- `scope`: no E/F, credentials, private agent directories, external shared libraries, real material library, test source corpus, or existing Green runtime was read or modified.

## Continuation receipt — 2026-09-20 P3 review API readback

- `subject_sha`: `5b5c10982f76eb3be3a20864b0167dbe75110294`
- `changed_paths`: `crates/archeaxis-api/src/lib.rs`, `crates/archeaxis-api/tests/learning_state_api.rs`
- `behavior`: stateful review responses now return the persisted learner `answer` and the explicit open `mastery_projection`; schedule-only legacy reviews continue to return JSON nulls for those fields.
- `tests`: Rust API test adds first-submit and idempotent replay assertions for answer/projection equality.
- `verification`: `cargo test -p archeaxis-api --test learning_state_api` is `NOT_EXECUTED` because `cargo` is unavailable; source diff check passed. This remains `IMPLEMENTED_LOCAL / UNVERIFIED`.
- `boundary`: no external library, Green runtime, real data, E/F, credentials, or private agent state was accessed.

## Continuation receipt — 2026-09-20 Python contract gate and P4.1 read-only audit

- `subject_sha`: `2d813c64bd8d8ab40a1dbf8eb01466d23a7b60c1`
- `python_gate`: `.venv\\Scripts\\python.exe -B -m pytest -p no:cacheprovider -q --tb=short tests/test_capability_absorption_registry.py tests/test_knowledge_source_v3_contract.py tests/test_format_execution_v1.py tests/test_vault_search_api.py tests/test_machine_growth_v1.py tests/test_learning_kernel_v1.py tests/test_general_learning_contract.py tests/test_domain_pack_v1.py tests/test_courseware_v1.py tests/test_model_pool_v1.py` — `42 passed, 1 warning`, exit `0`; `TESTED_LOCAL` contract/fixture scope only.
- `P4.1_audit`: `IMPLEMENTED_LOCAL` for machine receipt, active accepted/personal Knowledge binding, failed `retest_of`, machine API and human correction successor constraints; `BLOCKED` for real model execution/error/correction/retest journey; Cargo tests `NOT_EXECUTED`.
- `A15_readonly_audit`: independent read-only result remains `NOT_RUN / BLOCKED`; contracts are structural, security exact-SHA/full gate is `NOT_RUN`, migration/learning/machine/models/domain/first-use/restart/Green remain blocked or partial. It does not self-sign A15 PASS.
- `boundary`: no external model content, Green runtime, real data, E/F, credentials or private agent state was accessed.

## Continuation receipt — 2026-09-20 P3 desktop assessment gate

- `subject_sha`: `e019721b9c9da77e0bb7990b5d862c91d22d557d`
- `changed_paths`: `apps/ArcheAxis.Desktop/MainWindow.axaml.cs`, `tests/test_desktop_learning_review_contract.py`
- `behavior`: Assessment binding now checks `knowledge_id` against the active Knowledge and rebinds on mismatch; answer/rating/submit controls remain disabled until a valid Assessment is bound; successful review responses surface saved-answer and open-projection status without claiming mastery.
- `tests`: `.venv\\Scripts\\python.exe -B -m pytest -p no:cacheprovider tests/test_desktop_learning_review_contract.py -q` — `9 passed, 1 warning`, exit `0`.
- `runtime`: Avalonia/.NET build and real first-use remain `NOT_EXECUTED` because `dotnet` is unavailable; this is source-contract evidence only.
- `boundary`: no Green runtime, external libraries, real data, E/F, credentials or private agent state was accessed.

## Continuation receipt — 2026-09-20 P0.1/P2.1 ready-now gates

- `subject_sha`: `5e00582186791dbdee58feb44020c2792035f5d7`
- `P0.1`: `.venv\\Scripts\\python.exe -B -m pytest -p no:cacheprovider tests/test_axw_cap503_activator.py tests/test_axw_cap503_builtin.py tests/test_worker_reachability.py -q` — `32 passed, 1 warning`, exit `0`; `TESTED_LOCAL` only.
- `P2.1`: `.venv\\Scripts\\python.exe -B -m pytest -p no:cacheprovider tests/test_courseware_v1.py tests/test_machine_knowledge_contract.py -q` — `10 passed, 1 warning`, exit `0`; `TESTED_LOCAL / STRUCTURAL` only.
- `limitations`: these gates do not prove Rust/.NET runtime, real external workers, real models, interactive renderer, Green, or external data journeys.

## Continuation receipt — 2026-09-20 P3 desktop learning history readback

- `subject_sha`: `30ff2658de4a210d74131493265771f2884e5d45`
- `changed_paths`: `apps/ArcheAxis.Desktop/MainWindow.axaml.cs`, `tests/test_desktop_learning_review_contract.py`
- `behavior`: opening a learning item now calls the existing learning-events route, reads the latest persisted outcome, and shows saved-answer/open-projection status conservatively; malformed or failed history remains `学习记录：未读回` and never becomes a mastery claim.
- `tests`: `.venv\\Scripts\\python.exe -B -m pytest -p no:cacheprovider tests/test_desktop_learning_review_contract.py -q` — `10 passed, 1 warning`, exit `0`.
- `runtime`: Avalonia/.NET build and real restart/readback remain `NOT_EXECUTED` because `dotnet` is unavailable; this is source-contract evidence only.

## Continuation receipt — 2026-09-19 current-SHA Green candidate and portable worker smoke

- `task_id`: A13 Green candidate composition and portable worker route closure
- `source_sha`: `0e934f33ee9a5f6082c04abda454c67df1055097`
- `source_tree`: `5d34d98c3d80e31a9174b83d78fd1707496ba279`
- `implementation`: `services/python-workers/transport/text_ndjson.py` now resolves route workers from either the source checkout or the relocated `workers/` candidate root; the regression is covered by `tests/workers/test_text_ndjson.py`.
- `candidate`: `.project-local/build/green-candidates-r6/ArcheAxis.Knowledge.Green-vr6-0e934f33-x64`
- `candidate_verification`: `verify_green_candidate.py --require-runtime --require-workers` returned `ok=true`, scope `desktop-core-runtime-workers`, 2514 manifest files, no problems.
- `zip_sha256`: `6AB6C5ECAEAFABFCF4A91131A9F20D2510BDCF5EE0CABD31D4D844344BD2A087`
- `worker_runtime`: candidate `runtime/python.exe -B -S workers/transport/text_ndjson.py` returned exit 0, a valid hello, a succeeded `text.extract` response and three content-addressed outputs.
- `desktop_runtime`: candidate `ArcheAxis.Desktop.exe --smoke` returned exit 0 with `SMOKE OK: owned core handshake ok: archeaxis-api 0.1.0-outline`; an isolated candidate data root created a 4096-byte SQLite file and was removed after the run.
- `tests`: portable worker fix suite `52 passed, 1 skipped, 47 subtests passed`; no external paths were touched.
- `limitations`: this advances A13 to current-SHA candidate and headless runtime evidence; nonempty legacy migration, restart/readback, clean-machine GUI, signing, installer/uninstaller, Green replacement and rollback remain open and owner-gated where applicable.
- `rollback`: revert commit `0e934f33ee9a5f6082c04abda454c67df1055097`; project-local candidate and smoke artifacts are ignored outputs.

## Continuation receipt — 2026-09-19 A13 non-empty staging migration and restart identity

- `task_id`: A13 staging migration and restart/readback evidence
- `subject_sha`: `75b32145338f21eaf8aa28ddd0119631cdfc04f4`
- `migration_test`: `cargo test -p archeaxis-migration --test legacy_nonempty_migration` — exit 0; 1 passed, 0 failed. The test covers a non-empty isolated legacy fixture, read-only export, hash/count verification, Rust staging import, explicit loss rows, schedule preservation, idempotent replay and byte-identical legacy bytes afterward.
- `restart_test`: the current Green candidate was run twice against `.project-local/runs/r6-a13-restart-readback-0e934f33/workspace.sqlite`; both runs returned exit 0 and `SMOKE OK`, both created/read the same 4096-byte DB, and the DB SHA-256 stayed `1FE8F6113488865C546D2FAA55B21482662CE4BE19D4F505EEEFA09BC3131489`.
- `scope`: project-local staging and headless identity evidence only; no real Green DB, user material library, external model library or Green installation was touched.
- `limitations`: the fixture is synthetic, and owner activation, GUI first-use, signed installer lifecycle, in-place replacement, failure recovery and rollback remain open.

## Continuation receipt — 2026-09-20 P3 API FSRS and Assessment readback

- `subject_sha`: `8bbdd491066b78d2474db0d03edce3ba0c38e295`
- `changed_paths`: `crates/archeaxis-api/tests/learning_state_api.rs`
- `behavior`: the submitted-answer restart fixture now creates accepted Knowledge, binds a learning item reference, creates a Core-owned Assessment, and submits `assessment_id` plus `knowledge_version`; this matches the API contract that answers must be bound to an Assessment.
- `verification`: with the declared shared Rust/MSVC/Windows SDK environment and the existing project `.venv` FSRS interpreter, `learning_state_api` `5 passed`, `machine_correction_loop` `1 passed`, and `machine_task_api` `4 passed`; exit code `0`. The run covered real FSRS scheduling, due-date projection, answer persistence/readback, idempotent replay, and restart.
- `prior_failure`: the first direct run used the managed Python without the installed `fsrs` package and reported `schedule_authority=unavailable`; after switching to the existing project `.venv`, the same tests passed. This was an environment-selection failure, not a product fallback result.
- `warnings`: existing Rust warnings for unused `stable_id` and `Executor.worker`; no rustfmt run because the shared toolchain does not provide `cargo-fmt/rustfmt`.
- `scope`: no external library, Green runtime, real data, E/F, credentials or private agent state was accessed; build outputs stayed under `.project-local`.
- `remaining_gap`: Avalonia first-use UI, authoritative mastery semantics, full restart/readback across Course/Artifact/Mastery/FSRS, P4 real machine correction/retest, P5 full backup/restore, A15 independent audit and A16 Owner Gate remain open.

## Continuation receipt — 2026-09-20 P3 desktop answer recovery

- `subject_sha`: `428de718a808acebb025ca01f3c1e62c60c30916`
- `changed_paths`: `apps/ArcheAxis.Desktop/MainWindow.axaml.cs`, `tests/test_desktop_learning_review_contract.py`
- `behavior`: when reopening a learning item, the desktop now restores the persisted learner answer into the answer box while retaining the conservative open-projection status; it does not claim mastery.
- `verification`: focused RED then GREEN; desktop learning contract `11 passed, 1 warning`, exit `0`; external .NET Desktop build `0 warnings, 0 errors`, exit `0`.
- `scope`: source-contract and build evidence only; no Green runtime, real user data, external library, E/F, credentials or private agent state was accessed.
- `remaining_gap`: real Avalonia first-use interaction, authoritative mastery/FSRS full-state readback, process-level machine correction/retest, workspace identity decision and Owner-gated Green migration remain open.

## Continuation receipt — 2026-09-20 P3 headless desktop runtime gate

- `subject_sha`: `5e4b95d1abfe7d456b0a5bdaf837e306f63a18dc`
- `verification`: Desktop apphost `--smoke` completed the owned Desktop → CoreSupervisor → Core handshake/shutdown with exit `0`; the combined desktop routes/runtime/output/learning contract gate reported `33 passed, 3 warnings`, exit `0`.
- `evidence_boundary`: the smoke creates no learning event and does not exercise real Avalonia controls; window first-use, click-submit and cold restart UI readback remain `NOT_EXECUTED / BLOCKED`.
- `scope`: all outputs stayed under `.project-local`; no Green runtime, external library, real data, E/F, credentials or private agent state was accessed.

## Continuation receipt — 2026-09-20 P4 machine-loop and P5 persistence gates

- `subject_sha`: `5e4b95d1abfe7d456b0a5bdaf837e306f63a18dc`
- `P4_verification`: exact shared Rust/MSVC/Windows SDK environment ran API `machine_task_api` (`4 passed`), `machine_correction_loop` (`1 passed`) and domain `machine_tasks` (`7 passed`), total `12 passed`, exit `0`; the real Core receipt probe returned HTTP `201` write and `200` readback. A full human → machine failed task → human correction → retest → cold restart runner exited `8` before the first human Core readiness step because stderr was suppressed; this is a blocker, not a pass.
- `P5_verification`: domain backup/restart (`6 passed`), migration (`7 passed`) and store-sqlite (`5 passed`) exact Cargo suites, total `18 passed`, exit `0`; workspace identity generation/restore matching remains an Owner decision.
- `A15_preparation`: independent-gate preparation ran `31 passed, 1 warning`, the R11 unseen probe and MCP client smoke both exited `0`, and authority SHA readback exited `0`; this is preparation evidence only and does not self-sign A15.
- `scope`: no external shared library, Green runtime, real data, E/F, credentials or private agent state was accessed; generated evidence stayed under `.project-local`.

- execution_status: `NOT_EXECUTED`
- blocker: Owner Gate requires the independent audit and the unresolved A02 resource-root decision, desktop runtime evidence, real Green migration/restart/rollback evidence and full closed-loop journey
- release_rule: R6 remains `IN_PROGRESS` with release `FROZEN`; no tag, release or Local Green replacement was performed
