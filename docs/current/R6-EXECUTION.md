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

## Continuation receipt — 2026-09-20 P4 Core process correction/retest/restart

- `subject_sha`: `fec6f1fdeaaa299f421b8d2fe12661e3b6168dd2`
- `probe`: `.project-local/runs/p4_real_correction_restart.py`; its synthetic launch token was corrected to hexadecimal because the Core launch contract rejects non-hex identities.
- `verification`: exit `0`; `human_seed_accepted` `201`, `machine_failed_task` `201`, `machine_candidate` `201`, `human_modified_review` `200`, `human_accept_successor` `200`, `human_deprecate_candidate` `200`, `machine_successful_retest` `201`, and `restart_retest_readback` `200`.
- `result`: the same Core process family persisted the accepted Knowledge, machine failure, human successor correction and retest binding; a cold restart read back the successful retest with the successor `knowledge_version` and original `retest_of`.
- `boundary`: synthetic content and project-local SQLite only; this is process-level evidence, not evidence of a real model or user-observed error.
- `remaining_gap`: owner-approved real model execution, real user error, correction evidence and non-synthetic retest remain open.

## Continuation receipt — 2026-09-20 A15 independent audit

- `subject_sha`: `ffd8ff202cfcbd4e34f40dc3dd7f5d0cde2b9f33`
- `report`: `.project-local/audits/a15-independent-ffd8ff202cfcbd4e34f40dc3dd7f5d0cde2b9f33/report.md`; receipts are in the same ignored project-local directory.
- `independence`: a fresh reviewer with no implementation-turn context reran authority, contract/evidence-index/unseen checks and MCP surface probes; it explicitly states that executor receipts were not self-signed as A15 PASS.
- `result`: `A15_PASS / PRODUCT_NOT_READY`; P0-P6 are all `BLOCKED` under the M0 real-closure bar, A16 is `BLOCKED`.
- `evidence`: authority `PASS`; Python gate `31 passed, 1 warning`; unseen and MCP probes exit `0`; repository clean gate remains `FAIL` because 22 preserved untracked history/private paths remain.
- `remaining_gap`: real P3 UI/full-state restart, real model/user P4 correction/retest, P5 workspace identity and real Legacy semantic diff, and Owner-gated Green backup/replace/readback/rollback remain open.

- execution_status: `NOT_EXECUTED`
- blocker: Owner Gate requires the independent audit and the unresolved A02 resource-root decision, desktop runtime evidence, real Green migration/restart/rollback evidence and full closed-loop journey
- release_rule: R6 remains `IN_PROGRESS` with release `FROZEN`; no tag, release or Local Green replacement was performed

## Continuation receipt — 2026-09-21 P3 headless learning journey driver

- `subject_sha`: `b5dd4361bfac07140f9f77173fa42c39441df008`
- `changed_paths`: `apps/ArcheAxis.Desktop/Program.cs`, `tests/test_desktop_learning_review_contract.py`
- `behavior`: explicit `--learning-smoke <dbPath>` runs a project-local synthetic Knowledge → Assessment → learner answer/review → FSRS schedule and open mastery projection → Core stop/start readback. Run suffixes prevent repeated execution on the same SQLite from colliding on deterministic Knowledge/Assessment/event identifiers.
- `verification`: RED source-contract test failed before the flag existed; GREEN source contract `1 passed, 11 deselected`, desktop/P3 gate `39 passed, 3 warnings`, .NET build `0 warnings, 0 errors`, all exit `0`.
- `runtime_readback`: `NOT_EXECUTED/BLOCKED` against available project-local Core artifacts: the older default Core returned `404` for Assessment, while `cargo-r6-p4` reached the route but its review response did not match the current source contract. No stale binary was treated as current-source evidence and no external toolchain was rebuilt.
- `scope`: only project source/tests and `.project-local` smoke paths; no external library, Green runtime, real data, E/F, credentials or private agent state was accessed.

## Continuation receipt — 2026-09-21 P2 General lesson renderer

- `subject_sha`: `7944c5f011be2f963cef97af32518e1e54a0b46d`
- `changed_paths`: `app/adapters/courseware_lesson.py`, `tests/test_general_courseware_renderer.py`
- `behavior`: a deterministic local adapter accepts only a `general` lesson artifact bound to the supplied `CourseManifestV1`; it produces an Obsidian-compatible `Projection` with manifest/artifact/source/knowledge/renderer metadata and fail-closed binding checks.
- `verification`: static file/contract inspection passed; the focused pytest command was `NOT_EXECUTED` (project `.venv` uv trampoline failed with permission denied), so this is `STRUCTURAL` evidence only. No H5P/OpenMAIC/provider/model or real curriculum was introduced.
- `remaining_gap`: interactive renderer execution, Core courseware receipt, reviewed curriculum and domain acceptance remain open; P2 stays `TESTED_LOCAL_PARTIAL`.

## Continuation receipt — 2026-09-21 restored Python verification gates

- `subject_sha`: `cbffa9c6bc12ec8b306b678ce1507ad86b257bb8`
- `environment`: project `.venv\Scripts\python.exe` started successfully under the approved local execution boundary; no dependency installation was performed.
- `P2`: `tests/test_general_courseware_renderer.py` — `5 passed, 1 warning`, exit `0`.
- `P3`: `tests/test_desktop_learning_review_contract.py` — `12 passed, 1 warning`, exit `0`.
- `P0`: `tests/test_axw_cap503_activator.py tests/test_axw_cap503_builtin.py tests/test_worker_reachability.py` — `32 passed, 1 warning`, exit `0`; `scripts/ci/check_vnext_workers.py` printed `workers-vnext check passed`, exit `0`.
- `authority`: `scripts/maintenance/check_authority_sha_consistency.py` printed `PASS`, exit `0`.
- `boundary`: these are project-local contract/compile/reachability gates; they do not prove real Python worker lifecycle, interactive Avalonia use, real model execution or Green installation.

## Continuation receipt — 2026-09-21 P3 existing-Core candidate matrix

- `subject_sha`: `d7ea1e36ca1c5360106e97fee78dea8b410ed8a7`
- `candidates`: `.project-local/build/cargo-r6-p4/debug/archeaxis-api.exe`, `cargo-r6-api-sdk2/debug`, `cargo-r6-api-fix/debug`, and `rust-msvc/debug`.
- `verification`: the first three reached review but returned a body that did not satisfy the current answer/FSRS projection contract; `rust-msvc` returned `404` for the Assessment route. Each run used a separate `.project-local` SQLite and bounded output directory; hung smoke processes were stopped only after their executable path was verified.
- `result`: `BLOCKED/NOT_EXECUTED` for current-source runtime. No candidate was relabeled as a current build, and no external toolchain rebuild or external-library write was attempted.

## Continuation receipt — 2026-09-21 P2 combined contract gate

- `subject_sha`: `f1fd5085ed342409e02cd279a34e9b252b4a54c5`
- `command`: `.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider --basetemp=.project-local\runs\p2-renderer-gates-20260921 tests/test_general_courseware_renderer.py tests/test_general_learning_contract.py tests/test_courseware_v1.py tests/test_domain_pack_v1.py tests/test_truth_reset_contract.py -q`
- `verification`: `18 passed, 1 warning`, exit `0`; warning is the existing unknown `cache_dir` pytest option.
- `boundary`: contract/Projection evidence only; no interactive renderer, Core courseware receipt, external Provider, model runtime or real curriculum was claimed.

## Continuation receipt — 2026-09-21 P0 worker evidence boundary

- `subject_sha`: `45f42ab1d6d3a4da1e5ef397b0f8674b502cda1e`
- `verification`: static worker reachability and lifecycle source review completed. Existing lifecycle tests use a monkeypatched `FileConverter`; the reachability manifest records routes/exemptions but does not bind real Python worker manifest, runner, health, enable/disable or provider replacement behavior.
- `result`: `STRUCTURAL / NOT_EXECUTED`; no complete P0 worker gate is available without the Python runtime and a real worker binding. The two un-routed capability workers remain explicitly exempt for missing model/route contracts.
- `scope`: no source change, no external library/Green/real data/E/F/private-state access, no commit-level product claim beyond this evidence boundary.

## Continuation receipt — 2026-09-20 repository normalization and contract boundary repair

- `subject_sha`: `5864a4adfe3fe8028ea09ed64b29efb1874a7121`
- `changed_paths`: the 29 tracked text files reported by the worktree convention gate; `scripts/check_language_boundaries.py`, `tests/test_language_boundaries.py`, and nine `packages/contracts/v1/*.schema.json` metadata repairs.
- `normalization`: only tracked text bytes were normalized from CRLF to LF; preserved untracked `docs/history/**` and `SESSION-RESTART-2026-09-12.md` were not read, staged or changed.
- `contract_repair`: worker protocol version is now derived only from `v*` directories containing `worker-protocol.schema.json`; the independent Knowledge V3 schema directory no longer creates a false protocol-version collision. Nine v1 schemas now carry explicit draft-2020-12 `$schema` and filename-matching `$id` metadata; no business fields were changed.
- `verification`: `check_repository_conventions.py --source worktree --format json` returned `issue_count=0`; `check_language_boundaries.py --json` returned `passed=true`, protocol major `1`; `check_vnext_contracts.py` returned exit `0`; the affected contract regression command returned `50 passed, 1 warning`, exit `0`; authority SHA consistency returned `PASS`.
- `scope`: project source/contracts/tests/docs only; no external library, Green runtime, real data, E/F, credentials or private agent state was accessed. This receipt does not claim CI, installer, GUI or full M0 closure.

## Continuation receipt — 2026-09-20 A04 V3 governance write path

- `subject_sha`: `566ef4716ac161b1627cd10ced13331323f48eaf`
- `changed_paths`: `crates/archeaxis-store-sqlite/src/lib.rs`, `crates/archeaxis-domain/src/knowledge.rs`, `crates/archeaxis-api/src/lib.rs`, `crates/archeaxis-api/tests/knowledge_v3_projection.rs`, and archive schema-version assertions.
- `behavior`: the Rust Core remains the single writer; V3 governance fields are stored in an additive `knowledge_v3_metadata` sidecar, validated at the canonical write path, projected on `/api/v1/knowledge-items/:id/v3`, and inherited across modified review revisions. Legacy rows keep explicit unknown values when no metadata exists.
- `verification`: focused Python gates were not applicable to Rust behavior; `git diff --check` passed. Rust `cargo fmt/test` were `NOT_EXECUTED` because no usable cargo executable is available in the bounded environment and rebuilding through the external shared toolchain was not authorized by the execution boundary. This is `TESTED_LOCAL_PARTIAL`, not a Rust runtime PASS.
- `scope`: no external library, Green runtime, real data, E/F, credentials or private agent state was accessed; no dual-write was introduced.
- `remaining_gap`: exact Rust compile/test, cold restart/readback, Avalonia UI wiring and real first-use V3 journey remain open.

## Continuation receipt — 2026-09-20 A05 HTML static execution receipt

- `subject_sha`: `566ef4716ac161b1627cd10ced13331323f48eaf`
- `changed_paths`: `services/python-workers/web/worker_html.py`, `tests/workers/test_bulk_html.py`, `tests/test_unified_job_contract.py`.
- `behavior`: HTML snapshot execution now emits `archeaxis.format-execution-receipt/v1` bound to source SHA-256, engine/version, derived document id, measured blocks/anchors/links and explicit static-snapshot limitations; the existing transport preserves it inside the loss report without changing the three-output protocol.
- `verification`: focused worker and unified-job command returned `18 passed, 1 warning`, exit `0`; `git diff --check` passed.
- `scope`: static local HTML only; dynamic browser rendering, remote fetching, semantic quality, external engines and complete format promotion remain open. Evidence level is `TESTED_LOCAL`, not `complete`.

## Continuation receipt — 2026-09-20 A06 path-free retrieval projection

- `subject_sha`: `75ae3d5828d2a5b0dcb0e93960359c61523e2c88`
- `changed_paths`: `app/workspace/vault.py`, `tests/test_vault_search_api.py`.
- `behavior`: read-only Vault substring search now derives an opaque, stable `source_id` from the relative source identity; `canonical_source_ids` and projection items carry that id with the content hash as `source_revision`, so absolute Vault roots never enter the derived receipt.
- `verification`: `tests/test_derived_projection_v1.py tests/test_vault_search_api.py` returned `10 passed, 1 warning`, exit `0`; `git diff --check` passed.
- `scope`: local synthetic Vault fixtures only; no Vault, canonical knowledge, external provider, model or shared library was written. Vector/reranker/graph/research quality and provider benchmarks remain open.

## Continuation receipt — 2026-09-20 parallel A07 experience boundary hardening

- `subject_sha`: `f8a124a2f0ed71bc413c4b5386325ccbb46cb8f8`
- `changed_paths`: `app/agent/experience_harvest.py`, `tests/test_experience_harvest.py`.
- `behavior`: `events_to_trajectory()` now rejects lifecycle kinds outside the declared task-start/task-end/tool-call/observation set instead of silently dropping them; Experience→Lesson receipts therefore cannot be built from an implicitly truncated event stream.
- `verification`: the new regression was RED on the prior implementation (exit `1`), then the focused A07 suite returned `17 passed, 1 warning`, exit `0`; the combined parallel gate returned `32 passed, 1 warning`, exit `0`; `git diff --check` passed.
- `boundary`: synthetic local lifecycle events only; no external model or runtime evidence was claimed. Review, reuse, user-observed error and real retest remain open.

## Continuation receipt — 2026-09-20 parallel A09/A10 provenance binding hardening

- `subject_sha`: `f8a124a2f0ed71bc413c4b5386325ccbb46cb8f8`
- `changed_paths`: `app/contracts/courseware_v1.py`, `packages/contracts/v1/courseware-artifact.schema.json`, `tests/test_courseware_v1.py`.
- `behavior`: course artifacts now reject blank or duplicate `source_ids` and `knowledge_ids` in both the Pydantic contract and the JSON Schema, keeping source/knowledge provenance deterministic.
- `verification`: focused A09/A10 suite returned `20 passed, 1 warning`, exit `0`; the combined parallel gate returned `32 passed, 1 warning`, exit `0`; `git diff --check` passed. A broader schema coverage check still exposes its pre-existing hardcoded inventory drift and was not relabeled as a regression.
- `boundary`: contract-level evidence only; real domain courseware, interactive execution, provider/model learning and human acceptance remain open.

## Continuation receipt — 2026-09-20 parallel A08 quiz fail-closed boundary

- `subject_sha`: `4a0058f247d2e7d1dc1df8848019b7d4d367a65f`
- `changed_paths`: `app/learning/quiz.py`, `tests/test_quiz_learning_path.py`.
- `behavior`: quiz generation now rejects unknown kinds and an explicit empty kind selection instead of silently returning an empty Assessment.
- `verification`: focused A08 tests returned `36 passed, 1 warning`, exit `0`; the combined second-round gate returned `33 passed, 1 warning`, exit `0`; `git diff --check` passed.
- `boundary`: contract-only local evidence; Core/Desktop runtime, real models and human learning remain open.

## Continuation receipt — 2026-09-20 parallel A12 Green manifest integrity

- `subject_sha`: `a0b93bd8363747f65be40aa5c97bd6479dc08400`
- `changed_paths`: `scripts/release/verify_green_candidate.py`, `tests/test_green_candidate_manifest.py`.
- `behavior`: candidate verification now fails closed for malformed file maps, unsafe relative paths, missing or symlinked files, byte-count mismatches and invalid or mismatched SHA-256 values; explicit source commit/tree checks remain opt-in to preserve existing candidate compatibility.
- `verification`: new manifest tests returned `4 passed, 1 warning`, exit `0`; both existing project-local candidates passed their structural `--require-runtime --require-workers` checks, but neither is current-HEAD provenance.
- `boundary`: this hardens project-local candidate verification only; it does not build a new exact-HEAD candidate or authorize Green replacement/rollback.

## Continuation receipt — 2026-09-20 parallel A14 closed-loop evidence completeness

- `subject_sha`: `a0b93bd8363747f65be40aa5c97bd6479dc08400`
- `changed_paths`: `app/contracts/closed_loop_v1.py`, `tests/test_closed_loop_v1.py`.
- `behavior`: a `complete` closed-loop receipt now requires every one of the eight ordered stages to contain non-empty, non-blank evidence references in addition to real evidence levels and pass statuses.
- `verification`: focused A14 tests returned `19 passed, 3 warnings`, exit `0`; the combined second-round gate returned `33 passed, 1 warning`, exit `0`; `git diff --check` passed.
- `boundary`: contract-level evidence only; a real model/user correction journey, restart, Green activation and rollback remain open.

## Continuation receipt — 2026-09-20 parallel A03 provider identity hardening

- `subject_sha`: `25355f1dd31be5a9dc4703506a771455878de595`
- `changed_paths`: `shared/provider_contract.py`, `tests/test_provider_contract.py`.
- `behavior`: Provider, capability and dry-run route identities now fail closed on blank values, wrong enum types, empty minimum-model/base URL fields and duplicate capability names, preventing ambiguous local routing declarations.
- `verification`: focused A03 tests returned `8 passed, 1 warning`, exit `0`; the combined third-round gate returned `47 passed, 1 warning`, exit `0`; `git diff --check` passed.
- `boundary`: local contract evidence only; upstream/license/runtime readback, network/provider availability and real model benchmarks remain open.

## Continuation receipt — 2026-09-20 parallel A05 failed HTML execution receipt

- `subject_sha`: `25355f1dd31be5a9dc4703506a771455878de595`
- `changed_paths`: `services/python-workers/web/worker_html.py`, `tests/workers/test_bulk_html.py`.
- `behavior`: a present HTML source that cannot be projected now returns a path-free `archeaxis.format-execution-receipt/v1` with `status=failed`, source digest/name, engine identity, failure type and empty structure counts; missing or unreadable inputs keep the existing structured error path.
- `verification`: the focused worker/format command returned `18 passed`, exit `0`; the combined third-round gate returned `47 passed, 1 warning`, exit `0`; `git diff --check` passed.
- `boundary`: local static failure receipt only; dynamic rendering, external engines, semantic quality and complete format promotion remain open.

## Continuation receipt — 2026-09-20 parallel A06 deterministic retrieval projection

- `subject_sha`: `dbb744f5e73986677d5b3e7b5044ed43ed40fd09`
- `changed_paths`: `app/workspace/vault.py`, `tests/test_vault_search_api.py`.
- `behavior`: Vault scan results are sorted by normalized relative path before search results, canonical source IDs and projection IDs are derived, making identical content stable across filesystem enumeration orders while keeping absolute roots out of receipts.
- `verification`: focused A06 command returned `12 passed, 2 warnings`, exit `0`; the combined fourth-round gate returned `49 passed, 3 warnings`, exit `0`; `git diff --check` passed.
- `boundary`: synthetic/project-local Vault fixtures only; vector/reranker/graph/research wiring, real Vault and provider benchmarks remain open.

## Continuation receipt — 2026-09-20 parallel A07 distillation evidence binding

- `subject_sha`: `dbb744f5e73986677d5b3e7b5044ed43ed40fd09`
- `changed_paths`: `app/learning/distillation.py`, `tests/test_distillation_review.py`.
- `behavior`: a verified evidence bundle can promote only the candidate whose `claim_id` it names; cross-candidate evidence is rejected before approval is recorded.
- `verification`: A07 review/reuse regression returned `18 passed, 1 warning`, exit `0`; the combined fourth-round gate returned `49 passed, 3 warnings`, exit `0`; `git diff --check` passed.
- `boundary`: local SQLite contract only; real model/user review, reuse and retest journey remain open.

## Continuation receipt — 2026-09-20 parallel A10 renderer path identity

- `subject_sha`: `dbb744f5e73986677d5b3e7b5044ed43ed40fd09`
- `changed_paths`: `app/adapters/courseware_lesson.py`, `tests/test_general_courseware_renderer.py`.
- `behavior`: lossy or unsafe lesson IDs now receive a stable hash suffix, Windows reserved names are disambiguated, and every rendered path segment is bounded to 120 characters so distinct course artifacts cannot silently collide.
- `verification`: renderer tests returned `6 passed, 1 warning`, the A10 contract gate returned `21 passed, 1 warning`, and the combined fourth-round gate returned `49 passed, 3 warnings`, all exit `0`; `git diff --check` passed.
- `boundary`: deterministic local projection only; interactive renderer execution, real curriculum and domain acceptance remain open.

## Continuation receipt — 2026-09-20 independent A15 exact-SHA audit

- `subject_sha`: `bf06c7114ceb500b2d8813df14982eb418fbc463`
- `independence`: a fresh Luna high reviewer ran without implementation-turn context and did not modify source, state or audit files; its result is recorded here by the primary writer and is not an executor self-signature.
- `identity`: `main`, local `HEAD`, local `origin/main` and a fresh `git ls-remote origin refs/heads/main` readback all returned `bf06c7114ceb500b2d8813df14982eb418fbc463`; `HEAD...origin/main` is `0 0`.
- `mechanical_gates`: authority SHA exit `0`; historical R3.1 evidence index exit `0` with 17 slices, 81 tracked pointers and 3 receipts; current contract/unseen gate `31 passed, 1 warning`; security/permission/path/MCP gate `41 passed, 1 skipped, 3 warnings`; R11 unseen and MCP probes exit `0`.
- `result`: `A15_PASS / PRODUCT_NOT_READY`. G01 is locally PASS; G02-G11, G13 and G14 remain BLOCKED or insufficient for PASS; G12 is FAIL because 22 preserved untracked history/private paths remain. P0-P6 remain BLOCKED and A16 remains BLOCKED.
- `boundary`: this audit does not prove real representative format quality, human Avalonia first-use, real model/user correction-retest, complete Rust backup/recovery, Legacy semantic migration, clean-machine Windows qualification, Green replacement/rollback or release readiness.

## Continuation receipt — 2026-09-20 release architecture and performance boundary

- `subject_sha`: `f73d370e2043a9135e7a836099a8c1faec7f87b4`
- `architecture`: `scripts/release/verify_release_architecture.py --root .` returned exit `0`; the formal Avalonia → Rust Core → Python workers release chain is identified. This is structural evidence only.
- `performance_probe`: `scripts/run_performance_benchmark.py --corpus tests/fixtures/corpus --report .project-local/runs/r6-perf-20260920/artifacts/performance.json` wrote a project-local report and returned `overall: passed`, but all required `small`, `medium` and `large` layers were skipped because the fixture does not contain those directories; only cold-start data and a 7-file/2428-byte corpus summary were measured.
- `result`: performance evidence is `NOT_EXECUTED/INCOMPLETE` for the AXW-096A layered gate; no A11 model benchmark or full A05 conversion-quality claim is made. A12 architecture remains `TESTED_LOCAL_PARTIAL`.
- `boundary`: no public download, external model, shared library, Green runtime, real data, E/F or private agent state was accessed.

## Continuation receipt — 2026-09-20 benchmark and dev-environment fail-closed repair

- `subject_sha`: `b8fbb41a40913af660a354a2b422a1d887f5b50b`
- `changed_paths`: `shared/performance_benchmark.py`, `scripts/run_performance_benchmark.py`, `scripts/runtime/dev.py`, `tests/test_axw096a_benchmark.py`, `tests/runtime-paths/test_dev_paths.py`.
- `benchmark_behavior`: required `small/medium/large` layers now produce explicit `NOT_EXECUTED` or `INCOMPLETE` completeness records; a missing or partial required layer forces `overall: incomplete` and a non-zero process result even when cold-start thresholds pass.
- `dev_behavior`: `dev.py` now replaces inherited `PYTHONPATH` with the current checkout root, so absolute project scripts import current `app`, `scripts` and `shared` modules without stale or foreign checkout masking.
- `verification`: tooling gate returned `35 passed, 1 warning, 9 subtests passed`; the actual missing-layer benchmark now prints `completion: NOT_EXECUTED` and `overall: incomplete` through `dev.py`. The benchmark result is intentionally incomplete until a real layered corpus exists.
- `boundary`: no model weights, external corpus download, shared library, Green runtime, E/F or private state was accessed; A11 executable model benchmark and A02 resource-root decision remain open.

## Continuation receipt — 2026-09-20 A12/A13 fail-closed recovery and provenance

- `subject_sha`: `5cf49da1aaf3e3dab0536fd25d29d199d37fca2c`
- `changed_paths`: `app/workspace/migrate.py`, `tests/test_axw_data403_migrate.py`, `scripts/release/verify_green_candidate.py`, `tests/test_green_candidate_verifier.py`.
- `A13`: rollback readback now exposes `integrity_ok` and `rollback_eligible`; a source-hash or SQLite-integrity mismatch returns `status=error`, clears `restore_candidate`, and explains the block instead of offering an unsafe restore path.
- `A12/A13`: Green candidate verification has an explicit `--require-provenance` gate requiring non-blank `source_commit` and `source_tree`, while default compatibility and explicit expected-commit/tree checks remain unchanged.
- `verification`: `tests/test_axw_data403_migrate.py tests/test_axw_long_path.py tests/test_green_candidate_verifier.py tests/test_green_candidate_manifest.py` returned `20 passed, 1 warning`, exit `0`; `git diff --check` passed.
- `boundary`: no Green build, external Green replacement, real Legacy migration, installer/signing, clean-machine or rollback action was performed. The prior independent A15 audit is bound to `bf06c711`; it must be rerun after this code change before being treated as current-SHA evidence.

## Continuation receipt — 2026-09-20 independent A15 current-SHA re-audit after A12/A13

- `subject_sha`: `4b8c720ce8a3b058900ce58befd56da6fad7fce1`; first parent `5cf49da1aaf3e3dab0536fd25d29d199d37fca2c`; local `origin/main` and `HEAD...origin/main` both read back as `4b8c720c` and `0 0`.
- `independence`: a fresh GPT-5.6 Luna high reviewer ran without implementation-turn context, did not modify source, state or audit files, and returned its result to the primary writer; this is not an executor self-signature.
- `mechanical_gates`: authority SHA PASS; R3.1 evidence index PASS with 17 slices, 81 tracked pointers and 3 receipts; R3.1 evidence-command parser exit `0`; contract/unseen/authority pytest `31 passed, 1 warning`; security/permission/path/MCP pytest `71 passed, 1 skipped, 3 warnings`; vNext contracts PASS; path conventions PASS with 2146/2146 tracked paths owned.
- `remote_readback`: `git ls-remote origin refs/heads/main` was NOT_EXECUTED successfully and returned exit `1` because local SSH `known_hosts` permission/host-key verification failed; an HTTPS fallback also failed in the local TLS credential environment. Local ref equality is not remote proof.
- `result`: `A15_PASS / PRODUCT_NOT_READY`. G01 is BLOCKED; G02-G11, G13 and G14 remain BLOCKED or insufficient for PASS; G12 is FAIL because 22 preserved untracked history/private paths remain. P0-P6 remain BLOCKED/PARTIAL and A16 remains BLOCKED_BY_OWNER_DECISION.
- `boundary`: this current-SHA audit still does not prove real representative format quality, human Avalonia first-use, real model/user correction-retest, complete Rust backup/recovery, Legacy semantic migration, clean-machine Windows qualification, Green replacement/rollback or release readiness. No E/F, `.codex`, `.zcode`, `.hermes`, external shared library, real data or Green runtime was accessed.

## Continuation receipt — 2026-09-20 parallel Luna readback gates

- `subject_sha`: `4b8c720ce8a3b058900ce58befd56da6fad7fce1` (working tree code unchanged after the current-SHA A15 audit).
- `verification`: A05 readback returned `50 passed, 3 warnings`; A06 returned `26 passed, 1 warning`; A07 returned `36 passed, 3 warnings`; A08 returned `33 passed, 1 warning`; A09/A10 returned `23 passed, 1 warning`; A12/A13 returned `60 passed, 1 skipped, 1 warning`. Every command exited `0` and used the project `.venv` with project-local basetemp roots.
- `boundary`: these are local contract/readback gates over synthetic or repository fixtures. They do not promote any slice to real runtime, model, external-engine, Green, clean-machine or release PASS; warnings and the one intentional skip remain recorded.

## Continuation receipt — 2026-09-20 automatic model allocation: bounded P1/P3/P5 cards

- `subject_sha`: `964fb8e20d5c97e513c716127e42e22406768ce4`; parent `b4e170a3c89fe327c3348276a44058f38ea68866`.
- `P1`: `app/workspace/service.py` now prefers an activated builtin `ConversionDispatcher` for the existing DOCX/HTML/image/media/PPTX/XLSX/CSV intake formats and falls back to the prior conversion chain with a path-free plugin failure receipt. The focused plugin-dispatch and intake regression returned `31 passed, 3 warnings`; ruff and Python syntax checks passed.
- `P3`: `/api/v1/learning/items/:item_key/state` now reads back the existing Assessment and latest persisted review answer, assessment binding, schedule fields, mastery projection and next-review value after SQLite reopen. No writer, schema or authoritative Mastery semantics changed. Rust test `cargo test -p archeaxis-api --test item_state_api` is `NOT_EXECUTED` because `cargo` and `rustfmt` are unavailable.
- `P5`: backup validation and restore preflight now fail closed when SQLite `PRAGMA integrity_check` is not `ok`; a same-count catalog-corruption regression was added. Rust `cargo test -p archeaxis-domain --test backup_safety verify_counts_rejects_sqlite_integrity_failure_even_when_counts_match` is `NOT_EXECUTED` because `cargo`/`rustc` are unavailable; `git diff --check` passed.
- `allocation`: Luna handled bounded Python and API-contract work in parallel; Terra handled the SQLite backup hardening. No agent accessed E/F, `.codex`, `.zcode`, `.hermes`, Green, external libraries, model weights or real user data. The changes improve local evidence only; P1/P3/P5 remain partial and M0 remains `NOT_READY`.

## Continuation receipt — 2026-09-20 A12 unmanifested-file fail-closed gate

- `subject_sha`: `de80584cf5282f78c7a910a4487cbc04c3bd6602`; pushed to `origin/main`.
- `changed_paths`: `scripts/release/verify_green_candidate.py`, `tests/test_green_candidate_manifest.py`.
- `behavior`: Green candidate verification now rejects every candidate-tree file absent from `candidate-manifest.json`, while allowing the manifest itself. This closes the unrecorded-payload gap without treating the candidate as an installed Green release.
- `verification`: `tests/test_green_candidate_manifest.py tests/test_green_candidate_verifier.py tests/test_green_candidate_assembly.py tests/test_release_architecture.py tests/test_r6_version_release_freeze.py tests/test_product_version_truth_contract.py` — `22 passed, 1 skipped, 1 warning`, exit `0`; Ruff on both changed files exit `0`; `git diff --check` exit `0`.
- `boundary`: local candidate-verifier evidence only. No clean-machine run, signing, installer, Green replacement, rollback, external library, model library, real data, E/F drive or private agent state was accessed. A12, A13 and M0 remain `TESTED_LOCAL_PARTIAL` / `NOT_READY`.

## Continuation receipt — 2026-09-20 A09/A10 objective coverage and renderer boundary

- `subject_sha`: `4e5394e39d81476591a3bd0fd892976f4213c331`; pushed to `origin/main`.
- `changed_paths`: `app/contracts/general_learning_v1.py`, `tests/test_general_learning_contract.py`, `app/adapters/courseware_lesson.py`, `tests/test_general_courseware_renderer.py`.
- `A09/A10`: every knowledge component referenced by a General course artifact must be covered by at least one Learning Objective; otherwise manifest validation fails closed. This prevents artifacts from carrying unteachable or unscoped components.
- `P2 renderer`: native Markdown lesson rendering now has explicit regression coverage for `interactive=true` and non-`native-lesson` renderers; both are rejected rather than silently projected as static lessons. H5P remains a separate future adapter.
- `verification`: combined General contract/courseware/renderer/domain/truth suite — `26 passed, 1 warning`, exit `0`; Ruff on all four changed files passed; `git diff --check` exit `0`.
- `boundary`: local contract and projection evidence only; no real curriculum, interactive renderer, provider, model, Green, external library, E/F drive or private state was accessed. A09/A10 remain partial for real runtime learning, and M0 remains `NOT_READY`.

## Continuation receipt — 2026-09-20 A07 event identity and R6 authority digest repair

- `A07 subject_sha`: `5005172114d329057e08829bf780a343b9c1d76f`; A07 receipt fix was tested locally and committed before this authority record update.
- `changed_paths`: `app/agent/experience_harvest.py`, `tests/test_experience_harvest.py`, `scripts/maintenance/check_r6_taskpack_authority.py`, `docs/authority/taskpack-0919-r6/MANIFEST.json`, `docs/authority/taskpack-0919-r6/TASKS.json`, `docs/authority/taskpack-0919-r6/EXECUTOR-START.md`, `docs/current/R6-STATE.json`, `docs/current/M0-DIRECTION-OVERRIDE-20260920.md`.
- `A07`: repeated event timestamps now receive deterministic occurrence suffixes (`now`, `now-1`, `now-2`) so machine-growth evidence references remain unique and stable; `19 passed, 1 warning`, exit `0`. Existing unrelated Ruff `UP037` findings were not changed.
- `A00`: immutable `TASKPACK.md` remains unchanged. The source-provided CRLF provenance SHA `dcc51e922a35d30ca361e9014e040674b62cee644a3ea57aae12ffa6c2949529` and canonical repository LF SHA `788c5d50b5953d21eb9f67587d5406d37ad2e5457c2ca3b991399d9988e5951b` are now explicit in all R6 authority records; `EXECUTOR-START.md` no longer contains `$sha`. `check_r6_taskpack_authority.py` verifies both digests and the CRLF→LF normalization relation.
- `boundary`: no external library, model pool, Green runtime, real data, E/F drive or private agent state was accessed. A15 found the prior digest ambiguity; this repair addresses that authority defect but does not promote A15/M0 to ready.

## Continuation receipt — 2026-09-20 A07 global event-ID collision repair

- `subject_sha`: `facd30eacc2ce217825132988af9ab546cec6881`; pushed to `origin/main`.
- `changed_paths`: `app/agent/experience_harvest.py`, `tests/test_experience_harvest.py`.
- `behavior`: receipt generation now tracks a global used-ID set and advances deterministic suffixes until each event reference is unique, covering repeated timestamps, timestamp/suffix collisions and `event-<index>` fallback collisions.
- `verification`: RED reproduced `['now', 'now-1', 'now-1']` before the fix; GREEN A07 suite returned `20 passed, 1 warning`, exit `0`; `git diff --check` exit `0`. Existing unrelated Ruff `UP037` findings at the pre-existing forward annotations remain unchanged.
- `boundary`: local receipt evidence only; real model execution, human error, review/reuse/retest, CI and runtime evidence remain open. No E/F drive, external library, model pool, Green or private state was accessed.

## Continuation receipt — 2026-09-20 P0 Python worker route contract

- `subject_sha`: `80398b1e4fd550301b5f7949a6fa3d0c53602960`; pushed to `origin/main`.
- `changed_paths`: `tests/test_worker_route_contract.py`.
- `behavior`: every `text_ndjson.ROUTES` entry is checked against an in-repository worker file, top-level `ENGINE` and `extract()` declarations, non-empty version/media metadata and supported call shape. Path escape and missing-worker drift fail closed.
- `verification`: P0 suite `27 passed, 1 warning, 47 subtests`, exit `0`; `scripts/ci/check_vnext_workers.py` reported `workers-vnext check passed`; Ruff passed.
- `boundary`: static route evidence only. It does not bind PluginManifest/CapabilityStore to the real subprocess, health, enable/disable, fallback or provider replacement lifecycle; P0 remains `PARTIAL`.

## Continuation receipt — 2026-09-20 P0 worker lifecycle contract

- `subject_sha`: `092c71a64c313a31701df5b1dfb41228cb896da6`; code commit pushed to `origin/main`.
- `changed_paths`: `tests/test_p0_python_worker_lifecycle.py`.
- `behavior`: test-only composition of the existing `PluginManifest`/`CapabilityStore` gate with the real `services/python-workers/transport/text_ndjson.py` subprocess. It covers hello, successful text extraction with output hashes and candidate-only authority effect, invalid-input failure with no outputs, disable blocking without launch, enable recovery, staging-root boundaries, and no SQLite creation.
- `verification`: actual configured CPython ran the focused card plus adjacent manifest/activator/NDJSON regression: `47 passed, 1 warning, 47 subtests passed`, exit `0`; `scripts/ci/check_vnext_workers.py` reported `workers-vnext check passed`; Ruff passed; `git diff --check` passed before commit.
- `evidence_boundary`: `TESTED_LOCAL_CONTRACT` only. No production launcher, schema, desktop host, external library, model pool, Green runtime, real user data, E/F drive or private agent state was accessed. P0 remains `PARTIAL`; M0 remains `NOT_READY`.

## Continuation receipt — 2026-09-20 P0-H01 host lifecycle and toolchain boundary

- `subject_sha`: `a5ef4f5f4d29203bda4137ecb9cc026658ecb309` (read-only audit basis).
- `card`: `P0-H01 Formal Host Provider Lifecycle`; status `BLOCKED_BY_AUTHORITY_DECISION`.
- `finding`: current formal path is Avalonia → Rust Core; Python `CapabilityStore`/converter dispatch is not the formal runner. The existing lifecycle test is test-only and does not bind the host.
- `proposed_contract`: versioned `provider-routing.json` sidecar, atomically written by CapabilityStore and read-only in Rust Core; it must carry default/fallback order, manifest digest/version, enabled state, replacement generation and health receipt reference. Rust Core remains the sole Canonical writer.
- `toolchain_readback`: current shell lacks `ARCHEAXIS_RUST_TOOLCHAINS`, `ARCHEAXIS_MSVC_VCVARS`, `INCLUDE`, `LIB`, `WindowsSdkDir` and `VCToolsInstallDir`; project doctor reports Rust unavailable. Historical exact blocker is `LNK1181: kernel32.lib`. This is an external Windows SDK environment gap; no project-local substitute exists.
- `next_action`: freeze the sidecar projection contract, then implement P0-H01 in isolated write sets; separately authorize exact Windows SDK/toolchain readback before Rust runtime gates.
- `boundary`: read-only audit plus project intake note only; no production host, external toolchain, Green runtime, real data, E/F drive or private agent state was modified.

## Continuation receipt — 2026-09-20 P0-H01 provider-routing contract slice

- `subject_sha`: `e21713b84b5dafe1b028e86481f119aa1efd4a4f`; code commit pushed to `origin/main`.
- `changed_paths`: `shared/provider_routing.py`, `tests/test_provider_routing.py`.
- `behavior`: fail-closed pure contract parser for `archeaxis.provider-routing/v1`; validates non-negative generation, provider manifest SHA/version, installed/enabled state, safe relative references, health receipt semantics, closed default/fallback routes and duplicate/unknown providers. `eligible_providers()` never promotes unknown health to healthy.
- `verification`: RED observed missing-module collection failure; after implementation, focused contract suite `10 passed, 1 warning`, related provider/CapabilityStore/manifest/activator regression `60 passed, 3 warnings`, Ruff and `py_compile` passed.
- `evidence_boundary`: `TESTED_LOCAL_CONTRACT` only. The formal Rust/Core and Avalonia host do not consume this snapshot yet; no SQLite schema, external toolchain, Green runtime, real data, E/F drive or private agent state was touched. P0-H01 remains blocked for the cross-layer Authority decision.

## Continuation receipt — 2026-09-20 provider-routing identity hardening

- `subject_sha`: `5a53d9a6445935e755df5f3ac263bd7922839aa7`; code commit pushed to `origin/main`.
- `finding`: independent current-SHA review exposed inconsistent handling of surrounding whitespace in capability/provider/fallback identities; a parsed snapshot could later fail lookup.
- `changed_paths`: `shared/provider_routing.py`, `tests/test_provider_routing.py`.
- `fix`: identity fields now reject surrounding whitespace consistently; fallback IDs are normalized through the same validator before duplicate and route-closure checks.
- `verification`: RED reproduced both cases; focused plus related provider/CapabilityStore/manifest/activator regression `62 passed, 3 warnings`, Ruff, `py_compile`, and `git diff --check` passed.
- `evidence_boundary`: contract-only fix, `TESTED_LOCAL_CONTRACT`; formal Rust/Core/Avalonia host integration remains open and no external resource or private state was accessed.

## Continuation receipt — 2026-09-20 P0-H01 CapabilityStore sidecar feasibility audit

- `subject_sha`: `5a53d9a6445935e755df5f3ac263bd7922839aa7` (current provider-routing contract code; no production code changed by this audit).
- `status`: `BLOCKED_BY_AUTHORITY_DECISION`; the proposed `provider-routing.json` publisher was not implemented because the current inputs do not define a safe projection.
- `findings`: `PluginManifest` exposes a healthcheck description but no capability/default/fallback ownership or health receipt; `CapabilityRecord` has no replacement generation or health state. CapabilityStore transitions move pack directories, replace `registry/index.json`, and would need a third sidecar replacement without a single crash-recoverable transaction. Disable/enable route semantics and fallback restoration order are also unspecified.
- `verification`: `scripts/ci/run_tests.ps1 -- -q tests/test_provider_routing.py tests/test_axw_cap501_store.py tests/test_axw_cap502_plugin_manifest.py` returned `36 passed, 2 warnings`, exit `0`. Terra's read-only audit found no file changes.
- `next_authority_inputs`: freeze (1) manifest capability/route source, (2) disabled-provider route semantics and fallback restoration, and (3) directory/index/sidecar recovery or transaction protocol. Only then implement the cross-layer host card.
- `evidence_boundary`: local feasibility and regression evidence only. No Rust/C# host, external toolchain, Green runtime, external library, model pool, real data, E/F drive or private agent state was accessed; P0 and M0 remain `PARTIAL` / `NOT_READY`.

## Continuation receipt — 2026-09-20 P2-R2 renderer provenance regression

- `subject_sha`: `4b035b8983061e5ebcb888c89d862e733e5e15b8`; code commit pushed to `origin/main`.
- `changed_paths`: `tests/test_general_courseware_renderer.py`.
- `behavior`: the General native lesson projection regression now asserts the derived `Projection.source`, empty wikilinks and required tags, preserving provenance fields alongside existing manifest/artifact/source/knowledge bindings.
- `verification`: `tests/test_general_courseware_renderer.py` returned `8 passed`, exit `0`; Ruff for the adapter and test passed; `git diff --check` passed.
- `evidence_boundary`: `TESTED_LOCAL_CONTRACT/PROJECTION` only. Production renderer behavior was unchanged; no real curriculum, model/provider, external library, Green runtime, real data, E/F drive or private state was accessed. A10/P2 and M0 remain partial/not ready.

## Continuation receipt — 2026-09-20 A14 real-model preflight

- `subject_sha`: `004587fde08661239012ac1c70b180eea363c2c0` (read-only preflight basis; no product code changed).
- `readback`: `config/models.yaml` still selects `default_llm.provider=stub` and `default_llm.name=local-stub`; `Get-Command ollama` found no executable; `Test-NetConnection 127.0.0.1:11434` returned `TcpTestSucceeded=false`.
- `status`: `NOT_EXECUTED / BLOCKED`; no synthetic machine receipt was promoted to real-model evidence. A14 still requires an owner-approved runnable model/provider and a human-observed error/correction sequence.
- `boundary`: only project config and localhost availability were checked. No external model library, external tool, real data, E/F drive, private state or provider credentials were accessed; M0 remains `NOT_READY`.

## Continuation receipt — 2026-09-20 P5 backup manifest duplicate-path hardening

- `subject_sha`: `e793252cd149c23c868c84921ab13ef3c7f31150`; code commit pushed to `origin/main`.
- `changed_paths`: `app/exchange/backup.py`, `tests/test_axw094b_backup.py`.
- `behavior`: `verify_backup()` normalizes manifest separators and rejects a duplicate relative path before counting or hashing it, closing a manifest-count ambiguity without changing backup layout or restore policy.
- `verification`: `tests/test_axw094b_backup.py` returned `17 passed`, exit `0`; Ruff for `app/exchange/backup.py` passed; `git diff --check` passed. The full test file still reports a pre-existing `SIM105` at its cleanup block, which was not changed.
- `evidence_boundary`: `TESTED_LOCAL` Python backup-manifest contract only. Rust SQLite integrity, workspace identity, real Legacy semantic diff, Green replacement/rollback and clean-machine evidence remain open; no external library, model pool, real data, E/F drive or private state was accessed.

## Continuation receipt — 2026-09-20 A08/P3 learning tick idempotency input boundary

- `subject_sha`: `7793a2c47a010024811994bc4e5bea10c4e19b3a`; code commit pushed to `origin/main`.
- `changed_paths`: `app/api/learning.py`, `tests/test_learning_api_security.py`.
- `behavior`: `/api/v1/learning/tick` now rejects a missing-type, empty or whitespace-only `idempotency_key` with a 400 response before dispatching the co-learning tick. Existing truth-field fail-closed behavior remains unchanged.
- `verification`: security tests `10 passed`, learning-loop E2E `1 passed`, exit `0`; Ruff on both changed files and `git diff --check` passed.
- `evidence_boundary`: local API input-contract evidence only. No authoritative Mastery/FSRS writer, desktop UI, real model/provider, external library, Green runtime, real data, E/F drive or private state was accessed; A08/P3 and M0 remain partial/not ready.

## Continuation receipt — 2026-09-20 A06 derived projection query boundary

- `subject_sha`: `14da2ea80dcc0f3a2f928b6f5e29a758f6b325c4`; code commit pushed to `origin/main`.
- `changed_paths`: `app/contracts/derived_projection_v1.py`, `tests/test_derived_projection_v1.py`.
- `behavior`: `DerivedProjectionReceiptV1.query` now rejects empty or whitespace-only strings, matching the Vault search boundary; the original query text is preserved when valid.
- `verification`: focused projection and Vault search tests `12 passed`, exit `0`; Ruff for both changed files and `git diff --check` passed.
- `evidence_boundary`: `TESTED_LOCAL_CONTRACT` only. Vector/reranker/graph/research provider wiring, real source restart/readback, external libraries, Green runtime, real data and E/F/private state were not accessed; A06 and M0 remain partial/not ready.

## Continuation receipt — 2026-09-20 A11 measured model evidence boundary

- `subject_sha`: `f19fea2027259c8d5e8b4475eadea6f1df5b31f5`; code commit pushed to `origin/main`.
- `changed_paths`: `app/contracts/model_pool_v1.py`, `tests/test_model_pool_v1.py`.
- `behavior`: model entries marked `measured_current` or `measured_historical` now require at least one evidence reference; unmeasured and blocked entries may remain without references.
- `verification`: `tests/test_model_pool_v1.py` returned `5 passed`, exit `0`; Ruff for both changed files and `git diff --check` passed.
- `evidence_boundary`: `TESTED_LOCAL_CONTRACT` only. No model weights, shared model library, runtime probe, external provider, Green runtime, real data, E/F drive or private state was accessed; A11 and M0 remain partial/not ready.

## Continuation receipt — 2026-09-20 A05 fallback receipt consistency

- `subject_sha`: `dd71d77adba53cd4235a93dc1d61af636ecfc6e5`; code commit pushed to `origin/main`.
- `changed_paths`: `app/contracts/format_execution_v1.py`, `tests/test_format_execution_v1.py`.
- `behavior`: `FallbackInfoV1` now rejects a non-empty reason when `used=false`, while allowing the normal no-fallback record of the selected engine in `attempted_engines`.
- `verification`: format receipt and workspace multiformat tests `15 passed`, exit `0`; test Ruff, production Ruff with existing B009/UP037 baseline excluded, and `git diff --check` passed. Full production Ruff still reports pre-existing B009/UP037 findings outside this change.
- `evidence_boundary`: `TESTED_LOCAL_CONTRACT` only. No external conversion engine, model pool, real data, Green runtime, E/F drive or private state was accessed; A05 and M0 remain partial/not ready.

## Continuation receipt — 2026-09-20 A08 learning provenance uniqueness

- `subject_sha`: `8e8d33ea41c152f403e83c35aadd6272ae50c64b`; code commit pushed to `origin/main`.
- `changed_paths`: `app/contracts/learning_kernel_v1.py`, `tests/test_learning_kernel_v1.py`.
- `behavior`: `LearningKernelReceiptV1.source_anchor_ids` now rejects duplicate anchors while preserving caller order for valid receipts.
- `verification`: `tests/test_learning_kernel_v1.py` returned `5 passed`, exit `0`; Ruff for both changed files and `git diff --check` passed.
- `evidence_boundary`: `TESTED_LOCAL_CONTRACT` only. Avalonia UI, authoritative Mastery/FSRS writer, real model/provider, Green runtime, real data, E/F drive and private state were not accessed; A08/P3 and M0 remain partial/not ready.

## Continuation receipt — 2026-09-20 A07 machine growth provenance uniqueness

- `subject_sha`: `8786d069bd88bbf7f31865453806d5f22d458252`; code commit pushed to `origin/main`.
- `changed_paths`: `app/contracts/machine_growth_v1.py`, `tests/test_machine_growth_v1.py`.
- `behavior`: `MachineGrowthReceiptV1.source_event_ids` now rejects duplicate source events while preserving caller order for valid receipts.
- `verification`: `tests/test_machine_growth_v1.py` returned `5 passed`, exit `0`; test Ruff, production Ruff with existing I001/SIM102 baseline excluded, and `git diff --check` passed. Full production Ruff still reports pre-existing findings outside this change.
- `evidence_boundary`: `TESTED_LOCAL_CONTRACT` only. No real model execution, human review, external provider, Green runtime, real data, E/F drive or private state was accessed; A07 and M0 remain partial/not ready.
