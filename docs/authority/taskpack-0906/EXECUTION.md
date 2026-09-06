# 2026-09-06 Full Loop execution

User authorized execution of `ARCHEAXIS-UPDATED-FULL-LOOP-TASKPACK-2026-09-06.zip`.
Package: 2026-09-06-r1; all 25 manifest file hashes verified. Baseline:
`4ca46eaf94c486dadcf200aac6b41cd968b1ce6e`; remote main read back at start.
The package supersedes r2/r3 plans, not historical test receipts.
The original 21-task DAG is preserved byte-for-byte as [TASKS.json](TASKS.json),
SHA-256 `1aa5c17c94f8c279987b5f4c70777e25d3614b6419fda65fd351abf71ff6bc94`.
It remains a frozen plan (`plan_only`), not an issued remote authorization or
implementation claim. Early repairs below do not satisfy unmet task dependencies.

## Accepted scope and ownership

- Formal desktop: `apps/ArcheAxis.Desktop`, C#/Avalonia; Rust owns a separate
  vNext database; Python workers provide computation only. Existing Green
  v0.6.14 and its user data stay recoverable. No release/version churn.
- E drive remains prohibited. Shared tools/models stay in existing libraries.
- Development root: project-owned `.project-local`; `.hermes` is preserved legacy
  material. Product workspaces and agent-private configuration are separate.
- One writer owns `codex/full-loop-0906`; the quality worker used its own
  `codex/worker-quality-0906` worktree. Its three-file patch was reviewed and
  integrated serially; its dirty worktree is retained. Storage/CI review is read-only.
- T20 is inventory/preservation planning; no blanket deletion or claimed GB savings.

## Progress ledger

| Tasks | State | Next acceptance |
| --- | --- | --- |
| T00 | PARTIAL | Approved decisions loaded; actual shared toolchain/local Python verified; baseline intake still to finish |
| T19 | TESTED_LOCAL / PARTIAL | Shared launcher and normal/linked/concurrent/failure path tests pass; remaining legacy fixed-path entrypoints need adoption |
| T01/T02 | TESTED_LOCAL / PARTIAL | Actual loss receipt/replay and generated three-language vocabulary verified; full DTO/roles/anchors/protocol and CI deduplication still open |
| T17 | PARTIAL | Eleven concrete legacy reuse gaps checked against source; nonempty migration and behavior qualification still open |
| T03/T04 | TESTED_LOCAL / PARTIAL | CAS originals, transaction/replay/migration and verified backup/archive implemented; writer actor, process lock, executor and Supervisor still open |
| T05/T06/T07 | TESTED_LOCAL / PARTIAL | Byte-faithful CER/WER and loss/coverage regressions pass; real corpus, all format chains and worker/Core integration still open |
| T08/T09/T10/T11 | PLANNED | Research, knowledge and both usage/feedback loops |
| T18/T12 | PLANNED | Interactive Avalonia workbench with real Core integration |
| T13/T14 | PLANNED | Nonempty migration, old capability absorption, index closure |
| T15/T16 | PLANNED | Same-candidate Windows qualification and reversible delivery |
| T20 | TESTED_LOCAL / PARTIAL | Metadata-only dry-run measured permitted scope; private/mixed roots unknown, 4 path errors; no deletion |

Current order: finish T19 entrypoint exceptions and T00/T17 baseline inventory,
then T01/T02 real contracts, T03 writer ownership, T04 executor, format workers
and the actual desktop/learning loops. T20 read-only inventory tooling was
integrated from the separate worker worktree; no cleanup is authorized merely
by a size result.

## Saved checkpoint and follow-up

### T00 field refresh and T17 reuse intake (2026-09-06)

Read-only field audit at local HEAD `6b3cd4d7ad0d607594b6f8452d117a1368722f31`:
live `refs/heads/main` readback was `4ca46eaf94c486dadcf200aac6b41cd968b1ce6e`.
These refs differ; this audit is neither publication nor exact-SHA CI evidence.
No models, tools or services were installed or started by this audit.

- Executable/metadata probes: PowerShell 7.6.5, project Python 3.13.14,
  external Rust/cargo 1.97.1, .NET SDK 10.0.400, Node 22.23.1, ffmpeg 8.1.2,
  Tesseract 5.5.0.20241111. NVIDIA query: RTX 5060, 8151 MiB, driver 595.97.
- OCR default language path is stale: `TESSDATA_PREFIX` refers to the former
  `OS External Configuration/toolchains/...` tree. An explicit language directory
  `D:/All projects/OS External Configuration/10-toolchains/scoop/apps/tesseract-languages/current`
  made `--list-langs` return 163 entries including simplified/traditional Chinese,
  English, Japanese and Korean. This is discovery, not an OCR accuracy test.
  Do not repair the global environment; bind the explicit path in the project worker profile.
- Existing Ollama metadata endpoint reports 0.33.2 and zero loaded models.
  Registered models: qwen3:8b, qwen2.5vl:7b, qwen3-embedding:0.6b,
  qwen3-reranker:latest, qwen3-coder:30b-a3b-q4_K_M. No inference qualification.
- Shared model metadata confirms Whisper model.bin (1,617,884,929 bytes),
  SenseVoice and streaming Zipformer ONNX files, and ComfyUI image weights.
  File presence is not evidence that this project can load/run them.
- Project distribution metadata: onnxruntime 1.20.1, faster-whisper 1.2.1,
  Pillow 12.3.0, pytesseract 0.3.13, PyMuPDF 1.28.2, python-pptx 1.0.2,
  openpyxl 3.1.5. No metadata found for torch/onnxruntime-gpu/sherpa-onnx/transformers.
  These probes did not import or infer with those packages.

T17 code-level gap map below is a reuse intake, not complete semantic review.
Preserve capabilities, not legacy bugs; every row needs nonempty behavior tests.

| Owner | Existing source/behavior to absorb | Required vNext acceptance |
| --- | --- | --- |
| T05 | `app/ingestion/multi_format.py`: resumable directory conversion | Restart retries failures; changed output hash invalidates success; unknown formats require review |
| T05/T06 | `app/ingestion/structured_conversion.py`: PDF tables/page/bbox | Mixed text/scanned/table pages retain per-page coverage and explicit failed pages |
| T05 | `app/ingestion/pptx_adapter.py`, `xlsx_adapter.py`: tables/notes/empty slides/cell cap | Nonempty Office fixtures retain structure and declared truncation; old XLSX cache-value comment is not implemented behavior |
| T02/T05 | `app/ingestion/conversion_run.py`, new document workers: structure and loss receipts | Worker -> Core -> restart retains cumulative losses, coverage and structure; current slice fixes receipt only, not structure |
| T05 | `app/ingestion/web.py`: raw response before extraction | Redirect chain, raw SHA, parser failure and byte-limit failure stay auditable |
| T05/T12 | `app/ingestion/web_screenshot.py`: actual nonempty browser screenshot | Dynamic long-page DOM/screenshot coverage; do not inherit legacy `--no-sandbox` or mistake fixed window for full coverage |
| T06/T09 | `shared/evidence_verification.py`: actual semantic matches only | Wrong frames never substitute for missing evidence; OCR/transcript/interpretation remain separate |
| T10 | `shared/learning_scheduler.py`, `app/knowledge/learning_artifact.py`: FSRS/source binding | Durable correct/incorrect scheduling; approval replay is idempotent and conflicting commands fail |
| T10/T11 | `app/knowledge/co_learning_loop.py`, `app/learning/quiz.py`: feedback/review | Stale evidence triggers review; repair answer leakage/duplicate distractors before absorption |
| T09/T11 | `app/knowledge/machine_knowledge.py`, `app/learning/distillation.py`: approval/scope/revocation | Unapproved/cross-scope/revoked material excluded from default context, historical receipts retained |
| T12/T13 | `OSUI/archeaxis-knowledge-ui-v2/app-v3.js`, `frontend/src/spaces/LearningSpace.tsx` | Preserve useful interactions without promoting UNBOUND fixtures; import nonempty legacy relationships/attachments/learning/revocation and navigate them in desktop |

Avalonia still has starter content, and the migration crate currently inventories
and exports JSONL rather than performing qualified semantic imports. No row above
is accepted merely because an old asset is listed in LEGACY_MANIFEST.

### T02 receipt and shared-vocabulary slice (2026-09-06)

Base commit `6b3cd4d7ad0d607594b6f8452d117a1368722f31`; local runs below used
the changed worktree. No push, cloud CI, new version, GUI launch or Green update.

- Rust now consumes generated vocabulary from the two canonical schema `$defs`;
  the same generator produces C# and Python bindings. Thirteen categories have
  strict parsers; 29 identical JSON positive/negative cases run in all three
  languages. Drift checks detect missing, edited and stale generated output.
  This qualifies the vocabulary library, not every existing endpoint: legacy
  lowercase knowledge/review states and complete DTO generation remain open.
- Actual `worker_text.py` runs on a BOM-prefixed 5001-line Chinese/emoji/CRLF
  sample. Its loss receipt passes the HTTP handler, persists, survives close/reopen
  and identical replay with both losses and 5000/5001 coverage unchanged.
  This test explicitly projects text/receipt, not structure, and is not the
  production executor. Unknown output/receipt fields now fail rather than vanish.
- Shared `loss-receipt.schema.json` and Rust boundary reject null/missing/type,
  count/ratio, engine/version, unknown-property and contradictory terminal payloads.
  JSON integer decimal/exponent notation is handled consistently. The exact old
  four-field completion-digest bytes replay without creating another transform.
- Quality reports cannot emit a measured null, a non-measured value/interval,
  non-finite number or reversed interval. Error rates above one remain legitimate.
  The schema resolver now registers each actual schema ID and resolves existing
  cross-file assessment references offline.
- The launcher pins `ARCHEAXIS_PYTHON` to its actual interpreter for Rust child
  worker tests. CI adds bounded parser/drift checks in existing lanes; duplicate
  main/vnext workflow triggers are not yet consolidated.

Final affected-scope verification (run IDs below share `be268a2d33/`):

| Check | Result | Run |
| --- | --- | --- |
| Contract/quality/classifier/runtime-path pytest | 93 passed, 52 subtests passed, 4 existing RefResolver deprecation warnings; 21.06 s | `a6c267fd2227` |
| Rust workspace `--locked --offline` | PASS, including actual Python receipt and archive/backup regressions; existing unused-symbol warnings remain | `0cdfc9cb2adc` |
| C# shared JSON parser harness | 29 cases PASS, no GUI | `023f1aff6108` |
| Actual Avalonia application build `--no-restore` | PASS, zero warnings/errors; not UI acceptance | `9873833d17c4` |
| Generated vocabulary exact drift check | PASS | `6fa8267c0ae2` |
| Changed-file Ruff / architecture / schema structural gate | PASS | `e73bbea64ce7` / `90be3b1949a8` / `97ed856aaaba` |

Representative RED evidence: receipt loss/incoherence `317bb68ca475`, contradictory
HTTP output `0166628a3cfb`, explicit null `df4fb84d7a07`, integer syntax `09dbf64b1355`,
missing Rust binding `a6342d5b35c3`, classifier shadowing `6a95b1588dda`.
No full Python qualification was repeated for this bounded slice.

Next implementation: finish T02 actual worker envelope/coordinate/role checks,
T03 sole writer/workspace lock and T04 executor, retaining worker structure.
The identified OCR path/probe defect can proceed independently in an isolated
worker: the existing public local model profile should supply `tessdata_dir` to
all three Tesseract invocations; failed language/TSV probes must not report full
capability. No global environment edit or duplicate runtime-default truth.

Foundation checkpoint: `09482433e5743ebc2e4956dc2667ff7b97ec521d`, tree
`7671405bac6be57a0568dc918a132f9d89fecadc`, local branch `codex/full-loop-0906`.
It has not been pushed. No exact-SHA CI, main merge or new release is claimed.

After freezing that clean commit, `scripts/ci/run_tests.ps1 --full -q --tb=short`
passed: **2147 passed, 7 skipped, 5 warnings, 10 subtests passed**, 142.13 seconds.
Run `be268a2d33/41d434c4c732` records the above commit/tree and `dirty=false`.
The source-head conventions check also passed (`be268a2d33/90ce5b07fc58`).
The 7 skips are not passed qualifications. Subsequent T20 additions were verified
separately; the full-suite result is not relabeled as a test of a later commit.

T20 follow-up: `scripts/maintenance/inventory_project.py` plus 9 stdlib tests
passed (`be268a2d33/998c4bbcc6fe`). Permission denial was a controlled injected
error; links, metadata counts, excluded boundaries and CLI were real filesystem
tests. No ACL was changed. Main-project read-only scan:

- Command: `python -B scripts/runtime/dev.py -- python -B
  scripts/maintenance/inventory_project.py .` using the project `.venv` interpreter.
- Run: `be268a2d33/a75da5dd5b03`; raw local report:
  `.project-local/runs/be268a2d33/a75da5dd5b03/artifacts/inventory.json`.
- Successfully observed: **19,676,885,323 logical bytes**, 113,646 regular-file
  paths; 30 exclusions, 2 reparse points and 4 errors. Group sums match the total.
  Hard-linked paths count independently; this is not allocated disk space.
- Exit 1 / PARTIAL: 4 WinError 3 observations on long-path test residue under
  two prior run roots. These were recorded, not silently treated as absent.
- `.hermes`, Git/agent-private boundaries and excluded subtrees remain unmeasured
  (`null`), not zero. Therefore there is **no repository-wide total** and no claimed
  correction of the historical full-size figure. No files were deleted or moved;
  no allocated-space savings, complete preservation or rebuild proof is claimed.
- Top-level `src-tauri`, `desktop`, `apps` contain mixed sources and outputs;
  their measured size does not authorize deleting those directories. T20 exact
  candidates, references, file identities, rebuild proof and preservation remain open.

## Foundation slice evidence and known limits

Except for the clean checkpoint explicitly recorded above, evidence below is
local execution on a dirty worktree based on the baseline SHA,
not exact-SHA CI or installed delivery. Run artifacts are ignored development
data, not uploaded source; this ledger retains the compact result.

- Rust workspace: `python -B scripts/runtime/dev.py -- cargo test --workspace --locked --offline -q`,
  PASS, run `be268a2d33/82aa87283335`. Includes 8 job atomicity/migration tests,
  API rejection/readback, 6 archive tests and 2 online-backup original/protection tests.
  The current-run 12-step in-process journey receipt passed strict identity/step validation;
  its worker receipt is simulated, not real worker qualification.
- Python full suite: `scripts/ci/run_tests.ps1 --full -q --tb=short`, run
  `be268a2d33/82bf1c1f0ccf`: 2144 passed, 7 skipped, 1 failed (removed historical
  normalization link). That link is restored as historical, not current authority.
  Follow-up targeted verification PASS: 81 tests and 10 subtests, run
  `be268a2d33/266cbe5d9306`, covers authority links, CI/classifier, runtime paths
  and byte-faithful worker regressions. This is not a second full-suite result
  and not a claim that all 21 taskpack tasks passed.
- Windows Avalonia shell build: shared .NET 10.0.400, `dotnet build
  apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj -v minimal -p:NuGetAudit=false`,
  PASS with zero warnings/errors, run `be268a2d33/50fe8d007849`.
  Build outputs are under `.project-local/build/be268a2d33/dotnet/`.
  This is compilation only; the UI still displays the starter content.
- Supervisor regression harness: `dotnet run --project
  tests/runtime-paths/CoreSupervisor.Tests`, PASS, run `be268a2d33/04e9c814e017`.
  Exercises a real unrelated loopback service, an owned stderr-flooding child
  cancelled before readiness, and real Rust Core using a spaced database path,
  an OS-assigned port, HTTP handshake and shutdown. Old wrong-workspace attach
  and Core reporting port zero were reproduced before their fixes.
- Repository conventions PASS, run `be268a2d33/901bebc82b93`.
- No new Release/tag/version, Green replacement, user-data migration or E-drive
  access was performed. No remote CI is qualified by these local runs.

Remaining safety/qualification gaps (do not conceal):

1. Store still exposes SQLite connections; the formal single writer actor and
   cross-process workspace lock remain T03. Backup source validation is pinned
   to one read transaction; destructive restore still needs full fault injection.
2. CAS and archive restore preserve original bytes and reject bad hashes, FK,
   future/unrelated databases and existing destinations. Publication uses
   same-filesystem no-clobber hard links; NTFS tested, other filesystems unqualified.
   Crash between object publication and DB publication can leave `<target>.objects`
   with no DB. Preserve this directory, inspect it, and use a different fresh
   destination for retry. Never delete it blindly. Automatic interrupted-publication
   recovery and power-loss durability remain unqualified. Ordinary cleanup
   failures can also leave owned staging objects; errors must not mean “cleaned”.
3. Legacy metadata-only archive formats are rejected by the new v2 path; they
   cannot reconstruct absent originals. Nonempty legacy migration remains T13.
4. Full Rust/C#/Python DTO roundtrips remain T02; the receipt/vocabulary slice above
   is now verified. Document structure, actual-source anchor bounds, launch/role
   authority and worker attempts are still not qualified. Local engine probes are
   not full multi-format accuracy or full-chain evidence.
5. Supervisor fixed-port attach, readiness cancellation/drain and silent-child
   startup are fixed in the tested slice. Launch authentication, process-level
   workspace lock, crash-restart policy and the actual interactive UI remain open.
   Do not launch the new GUI as the user's usable product.
6. Initial .NET first-run output reported development-certificate installation;
   trust/credential stores were not inspected or modified by commands. The launcher
   now disables ASP.NET certificate generation for subsequent runs. No certificate
   cleanup was attempted because ownership has not been established.

## Execution rulings

- Current user authorization adopts `.project-local` over older guidance naming
  `.hermes`. No global software configuration is changed.
- Routing is not an OS sandbox. External-root overrides are rejected until
  an explicit ownership configuration is implemented.
- Historical receipts retain their original test SHA; current handoff instructions
  point to the replacement launcher.
- A source compile or Green install is not vNext completion. Full tasks remain
  open until their acceptance, including negative paths, is measured.
