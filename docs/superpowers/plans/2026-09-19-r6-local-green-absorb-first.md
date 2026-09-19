# R6 Local Green Absorb First Implementation Plan

> **For agentic workers:** Execute the tasks in dependency order. Each task must record its own evidence before the next task is promoted.

**Goal:** Converge ArcheAxis onto the R6 Local Green Development Line while preserving the Rust canonical writer, the fixed external resource paths, and the no-release boundary.

**Architecture:** R6 adds authority and capability registries around the existing Rust SQLite kernel, isolated Python workers, and Avalonia shell. Mature upstream projects remain adapters, workers, projections, or donors; none becomes a second canonical store. Local Green validation stays an exact-SHA staging and rollback gate.

**Tech Stack:** Rust workspace, C#/.NET 10 Avalonia, Python isolated workers, SQLite, JSON/YAML contracts, PowerShell 7, project-local `.project-local/` evidence.

**Spec:** `docs/authority/taskpack-0919-r6/TASKPACK.md`

## Global Constraints

- `main` is the Local Green development line; do not create tags, releases, or product versions.
- Canonical truth is the Rust SQLite writer; UI, workers, sidecars, indexes, and models cannot write canonical truth.
- Shared paths remain those in `docs/SHARED_RESOURCE_PATH_INDEX.md`; do not scan E:, real Green data, or shared model/tool contents beyond an exact authorized probe.
- Runtime and evidence outputs go through `scripts/runtime/dev.py` into `.project-local/`.
- Unknown and untracked history/private state remains excluded until individually classified.
- Every result is labelled `IMPLEMENTED_LOCAL`, `TESTED_LOCAL`, `CI_VERIFIED_EXACT_SHA`, `INSTALLED_RUNTIME_VERIFIED`, or `BLOCKED` with the actual evidence level.

---

### Task 1: A00 authority reset and R6 registration

**Files:**
- Create: `docs/authority/taskpack-0919-r6/EXECUTOR-START.md`
- Create: `docs/authority/taskpack-0919-r6/TASKS.json`
- Create: `docs/authority/taskpack-0919-r6/MANIFEST.json`
- Modify: `docs/CONFIGURATION_AUTHORITY_INDEX.md`
- Modify: `docs/current/R6-EXECUTION.md`
- Modify: `docs/current/R6-STATE.json`

**Interfaces:**
- Consumes the pasted R6 taskpack and current R5 state.
- Produces one current R6 execution ledger and a machine-readable task list; R5 remains historical evidence.

- [ ] Copy the exact R6 taskpack into the authority directory and record its SHA-256.
- [ ] Register R6 as the active plan and explicitly mark R5 as historical source material.
- [ ] Add an R6 status file whose initial statuses are derived from current evidence, not inferred from the taskpack.
- [ ] Validate JSON and run the documentation authority tests.

### Task 2: A01 version and release freeze

**Files:**
- Modify: `PROJECT_CONTRACT.yaml`
- Modify: `docs/truth/CURRENT_STATE_TRUTH.md`
- Modify: `.github/workflows/release.yml` only if a normal push can publish automatically
- Create/modify: release identity contract tests

**Interfaces:**
- Consumes current release workflow and version truth tests.
- Produces a development-line identity with `published=false` and an explicit Owner-only release gate.

- [ ] Inventory every active product-version and automatic-release path.
- [ ] Add failing assertions for development-line identity and no-release-on-push.
- [ ] Implement the smallest contract/config change.
- [ ] Run targeted release contract tests; do not create a tag or release.

### Task 3: A02 resource and environment authority

**Files:**
- Modify: `config/environment/capability-requirements.yaml` only after schema decision
- Modify: `scripts/workflow/environment_registry.py`
- Create/modify: resolver and path-boundary tests
- Modify: `docs/environment/EXTERNAL_DEPENDENCIES.md` only for project-owned truth

**Interfaces:**
- Consumes `docs/SHARED_RESOURCE_PATH_INDEX.md` and the existing capability schema.
- Produces deterministic exact-path resolution with no PATH guessing or duplicate downloads.

- [ ] Reproduce the three manifest/schema mismatches with the existing validator.
- [ ] Separate schema defect from resource absence; do not silently rewrite either.
- [ ] Add a resolver test for valid application directories and invalid shims.
- [ ] Record external-owner actions as BLOCKED instead of editing shared libraries.

### Task 4: A03 capability absorption registry

**Files:**
- Create: `docs/truth/CAPABILITY_ABSORPTION_REGISTRY.yaml`
- Create: `config/schemas/capability-absorption-registry.schema.json`
- Create: `tests/test_capability_absorption_registry.py`
- Modify: `docs/CONFIGURATION_AUTHORITY_INDEX.md`

**Interfaces:**
- Consumes existing supply-chain ledger and R6 donor pool.
- Produces one registry with allowed absorption modes, authority boundaries, license fields, fallbacks, and status.

- [ ] Define the registry schema and reject missing identity, license, authority, or fallback fields.
- [ ] Seed entries for DeepTutor, OpenTutor, LearningMAP, OpenMAIC, RAG-Anything, LightRAG, Graphiti, MemOS, WeKnora, Cognee, and current internal implementations.
- [ ] Mark each entry as candidate/reference/adapter/provider rather than claiming integration without evidence.
- [ ] Run the new registry tests and compare it to `docs/truth/SUPPLY_CHAIN_LEDGER.json`.

### Task 5: A04 Knowledge/Source V3 contract

**Files:**
- Modify: Rust domain knowledge schema and migrations
- Modify: `packages/contracts/`
- Modify: Python/C# adapters only where contract requires it
- Create targeted cross-language tests

**Interfaces:**
- Consumes current knowledge governance and candidate contracts.
- Produces explicit personal, external, machine-candidate, temporal, confidence, risk, and supersession fields without an evidence admission gate.

- [ ] Add RED cases for accepted personal knowledge without external evidence and candidate machine knowledge.
- [ ] Implement cross-field validation and Rust writer enforcement.
- [ ] Verify UI/workers remain non-writers.

### Task 6: A05 multimodal format pipeline

**Files:**
- Modify existing worker adapters and format matrix
- Create targeted fixtures under `.project-local/`
- Modify format contract tests

**Interfaces:**
- Consumes registered Docling/MinerU/PaddleOCR/Tesseract/FFmpeg/faster-whisper capabilities.
- Produces original/transform/loss/structure/anchor/engine/version/quality/fallback receipts.

- [ ] Promote only formats with real execution evidence; keep partial formats partial.
- [ ] Run F01/F04/F05/F06/F07/F08/F09/F12 targeted paths using project test corpus copies.
- [ ] Record missing engines as BLOCKED.

### Task 7: A06 retrieval/graph/research projections

**Files:**
- Modify existing FTS5, graph, research facades
- Add projection contract tests and bounded research receipt tests

**Interfaces:**
- Consumes canonical knowledge and source contracts.
- Produces rebuildable projections only; no external graph/vector system writes canonical truth.

### Task 8: A07 machine experience and growth

**Files:**
- Modify machine candidate/receipt contracts and experience modules
- Add failure/correction/retest tests

**Interfaces:**
- Consumes machine task receipts and evaluation contracts.
- Produces Lesson and Skill Candidate records that require review before acceptance.

### Task 9: A08 human learning kernel

**Files:**
- Modify learning contracts, FSRS scheduler, and UI route adapters
- Add restart and mastery/truth separation tests

**Interfaces:**
- Consumes Knowledge Components and accepted knowledge.
- Produces learner state, activities, assessment, mastery, FSRS review, and cross-session reflection without changing truth status.

### Task 10: A09 domain learning packs

**Files:**
- Create `packages/contracts/domain-learning-pack/v1/`
- Create packs for General, Math/Physics, Programming, and Design
- Add schema and behavior tests

**Interfaces:**
- Produces domain-specific activity and assessment behavior while sharing the learning kernel.

### Task 11: A10 courseware and learning artifacts

**Files:**
- Modify learning artifact contracts and renderer adapters
- Add artifact provenance tests

**Interfaces:**
- Consumes Knowledge, Domain Pack, renderer, model/tool version, generation config, learner context.
- Produces traceable lesson, slide, quiz, simulation, coding lab, and teach-back artifacts.

### Task 12: A11 local model capability pool

**Files:**
- Modify local model resolver and environment registry
- Create model-role manifest and benchmark receipt schema
- Create tests using metadata only unless an exact model probe is authorized

**Interfaces:**
- Produces role-to-model mappings, resource measurements, fallbacks, and compatibility status.

### Task 13: A12 Avalonia product shell

**Files:**
- Modify `apps/ArcheAxis.Desktop/`
- Modify route/state contracts and desktop tests

**Interfaces:**
- Produces real routes for Home, Knowledge, Source, Learning, Jobs, Machine/AI Assets, Settings, Recovery.
- Reads through Core only; does not write canonical SQLite directly.

### Task 14: A13 legacy migration and Local Green candidate

**Files:**
- Modify migration verifier and candidate manifest tooling
- Add isolated staging fixtures and rollback evidence

**Interfaces:**
- Consumes read-only legacy snapshot copies.
- Produces exact-SHA candidate, semantic diff, loss ledger, restart readback, and rollback evidence.

### Task 15: A14 full human-machine closed loop

**Files:**
- Modify journey harness and receipt schemas
- Add real first-use regression tests

**Interfaces:**
- Requires source import, transform, knowledge acceptance, artifact, real answer, mastery, restart, machine use, failure, correction, retest.
- Synthetic or preloaded PASS data is invalid.

### Task 16: A15 independent audit

**Files:**
- Create `docs/authority/taskpack-0919-r6/INDEPENDENT-AUDIT.md`
- Create audit evidence index

**Interfaces:**
- Consumes exact-SHA evidence from A00-A14.
- Produces PASS/FAIL/BLOCKED per gate; executor cannot self-sign readiness.

### Task 17: A16 Owner Gate

**Files:**
- Modify `docs/current/R6-STATE.json` only after independent audit
- Create owner review receipt

**Interfaces:**
- Produces only `LOCAL_GREEN_READY_FOR_OWNER_REVIEW` or `NOT_READY`; never release readiness.

- [ ] Verify all preceding gates and evidence levels.
- [ ] Record unresolved gaps and rollback paths.
- [ ] Stop and wait for Owner release authorization.

---

## Self-review

The R6 spec requires local Green identity, canonical ownership, capability registry, Knowledge V3, multimodal formats, retrieval/graph, machine growth, domain packs, courseware, model pool, Avalonia routes, migration, first-use, restart, independent audit, and Owner Gate. Tasks 1–17 map one-to-one to A00–A16. No task claims that a plan or build is runtime proof; external resource writes, Green replacement, signing, release, and Owner approval remain explicit gates.
