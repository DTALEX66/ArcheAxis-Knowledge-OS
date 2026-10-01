# AAOS backend P0–P6 real multiformat loop — verification evidence (2026-10-01)

Evidence class legend: `REAL` > `INTEGRATED` > `SYNTHETIC` > `SIMULATED` > `NO_EVIDENCE`.
A claim is only `REAL` when real input bytes reached the real production process and the
result was read back. Test-suite presence alone is never `REAL`.

## 0. Subject identity

| Item | Value |
| --- | --- |
| Branch | `codex/dsh-aaos-real-multiformat-loop-20261001` |
| Base | `origin/codex/Audit` = `1a981a4482b01f31989074e79c82a63400aa07a7` |
| Worktree | `.project-local/worktrees/dsh-backend-loop-20261001` |
| Core binary SHA-256 | `a2d2746edb752fd7034940f129e874093fd71c35eea5aa65ac718eeeefeb8e29` |
| Rust toolchain used | `stable-x86_64-pc-windows-gnu` rustc 1.97.1 + MinGW gcc 16.2.0 |
| Worker interpreter | `.venv\Scripts\python.exe` (Python 3.13.14) |
| Storage schema version | `6` |
| Release state | `FROZEN` (unchanged) |

### Why the base is not the root checkout's HEAD

The prompt named `D:/All projects/ArcheAxis-Knowledge-OS` as the working directory, but
that checkout's `codex/Audit` HEAD (`6621aab7`) **is an ancestor of** `1a981a44` and does
not contain the authority documents the same prompt requires reading:
`AAOS-EXECUTION-PACKET-20261001.md`, `AAOS-UNFINISHED-TASKS-20261001.md`,
`AAOS-ALL-TASKS-DISPOSITION-20261001.csv`, `AAOS-ALL-TASKS-LEDGER-20261001.json`,
`AAOS-ERRORS-BLOCKERS-20261001.md` and `AAOS-GREEN-REPOSITORY-BOUNDARY-AUDIT-20261001.md`
are absent at `6621aab7` and present at `1a981a44`. `origin/codex/Audit` also points at
`1a981a44`, while the **local** `codex/Audit` ref was stale. The Owner chose the
`1a981a44` base; nothing was lost, because `6621aab7` is its ancestor.

Root-level facts observed before any change:

* `AUTHORITY.md` is absent → `AUTHORITY_REFERENCE_MISSING` (consistent with the audit).
* Root checkout has 1 modified tracked file and 22 untracked paths; all were left
  untouched. This work happened in an isolated worktree.
* Local `main` (`d8f99a63`) differs from `origin/main` (`59498723`); `main` is not an
  ancestor of `1a981a44`. Not resolved by this branch.

## 1. Toolchain finding (blocks nothing, but was not obvious)

The default `stable-x86_64-pc-windows-msvc` rustup toolchain is **broken on this
machine**: its `bin` contains `cargo.exe` but **no `rustc.exe`**, and no MSVC `link.exe`
or `cl.exe` is resolvable. `cargo test` therefore dies with
`could not execute process 'rustc -vV' (never executed)`.

A working combination exists and was used:

* rustc/cargo from `~\.rustup\toolchains\stable-x86_64-pc-windows-gnu\bin` (rustc 1.97.1)
* linker `gcc.exe` 16.2.0 from
  `D:\All projects\OS External Configuration\toolchains\mingw\mingw64\bin`
* `CARGO_TARGET_DIR` pointed inside the worktree's git-ignored `.project-local\build`

Recorded as an environment condition, not a product defect.

## 2. Baseline and post-change test signal

Both runs used the same interpreter and `ARCHEAXIS_PYTHON` contract.

| Run | Command | Result |
| --- | --- | --- |
| Baseline, `ARCHEAXIS_PYTHON` unset | `cargo test -p archeaxis-api --no-fail-fast` | **35 passed, 7 targets failed** |
| Same, `ARCHEAXIS_PYTHON` set | `cargo test -p archeaxis-api --no-fail-fast` | **all 28 targets pass, EXIT=0** |
| Per-format suites | `cargo test -p archeaxis-application --no-fail-fast` | **all targets pass, EXIT=0** |
| Launcher suite after this branch's fix | `python -m pytest tests/test_backend_runtime_safety.py` | **33 passed** |
| Launcher consumers | `pytest tests/test_core_launch.py tests/test_desktop_launch.py tests/test_r6_version_release_freeze.py` | **28 passed** |

The 7 baseline failures were **environmental, not product defects**. The dominant cause is
the project's own Python-selection contract: worker-backed tests
`expect("run cargo via scripts/runtime/dev.py to select the exact Python")` and panic with
`NotPresent` when `ARCHEAXIS_PYTHON` is unset. Setting it to an installed interpreter
resolves all of them. **This is why a reviewer must not read a bare `cargo test` failure
as a regression.** Conversely, `ARCHEAXIS_PYTHON` being unset in a real launch is a
genuine product-relevant condition: the Core then reports
`schedule_authority:"unavailable"` and stores an unscheduled event rather than inventing a
schedule.

## 3. P0–P6 status — measured, not inferred

### P0 Authority / Plugin Kernel — `PARTIAL`

* Real process start/stop, health handshake and identity binding: **REAL**. A Core was
  started with the production argv and a v2 launch document and answered
  `GET /api/v1/system/version` with the launched `session_id` and `workspace_db`.
* Single-writer boundary: `Store::open` takes an exclusive OS lock on
  `<db>.writer.lock`, owns the only connection on a dedicated thread, and rejects `e:`,
  UNC, `:memory:`, `..`, reparse points and link-count≠1. Verified by source read; not
  independently re-executed here.
* Not closed: the "plugin kernel" as a general capability registry. The authoritative
  enabled-capability set is two **hard-coded** route tables
  (`crates/archeaxis-application/src/attempts.rs` and
  `services/python-workers/transport/text_ndjson.py`), not a registry.

### P1 Source / Format / Knowledge — `ADVANCED`

This section opens with the branch's **original** measurement and then records what
replaced it. The original result was a real finding and is kept; it is not the current
state of the branch.

#### Original measurement — **superseded**, kept for audit

At the first measurement the headline result of this branch was that a production Core
launch made **every non-text format unreachable**. That is no longer true: the
route-enablement work recorded later in this document closed it, and real course material
now converts 9 of 9 with readiness 9 of 9. The original finding follows, unedited.

* Import → job → execute → transform → anchored candidate → V3 readback ran end to end on
  the real Core for **text**, with a real `source_id`, `transform_id`, `knowledge_id` and
  `anchor_id`, and a real raw `sha256`.
* Against the **verified** golden corpus (all 10 fixture SHA-256 values re-checked against
  `tests/fixtures/golden/manifest.json` — all `MATCH`), a production launch converted
  **1 of 10**:
  `{REACHABLE: 1, FAILED_AT_ROUTE: 9}`. Every non-text format failed with
  `Core execution ended without a terminal receipt`.
* Root cause (verified by direct source read and independently reproduced): the Core
  registers no route for the capability. `crates/archeaxis-application/src/executor.rs`
  returns `no worker registered for capability {capability}` for an unregistered
  capability — **after** the claim has already inserted the `running` attempt row and
  acknowledged it — so no worker process is ever spawned and the attempt is never
  terminated. `crates/archeaxis-api/src/main.rs` calls `Executor::open(...)`, and
  `Executor::open` delegates to `open_routes` with an **empty** extra-route slice; the
  only seeded route is `("text.extract", default_worker, false)`. All eleven
  `open_routes` call sites are test code. The launch document cannot carry extra routes
  even in principle: `TextWorker` is `deny_unknown_fields` and holds only
  `python`/`script`/`staging`. The configured worker script advertises only
  `["text.extract"]` (`services/python-workers/transport/text_ndjson.py`).
* **The operator-visible error is uninformative.** The specific
  `no worker registered for capability pdf.extract` string is never persisted; the
  post-await safety net in `crates/archeaxis-api/src/runtime/mod.rs` sees the attempt
  still `running` and overwrites it with `Core execution ended without a terminal
  receipt`. The job is first accepted with `202 running`, then settles `failed`. For the
  UI this must be surfaced as `unavailable` for the format, not as a conversion error.
* The repository already codifies the single-route production shape as intended
  behaviour: `crates/archeaxis-application/tests/pdf_job_end_to_end.rs` asserts
  `no worker registered for capability pdf.extract` using `Executor::open`, and passes.
* Secondary cause (real, but provably unreached in production): the transport refuses a
  capability it did not advertise with `AAK-VAL-001 "unsupported capability"`. Driving the
  transport directly with `pdf.extract` / `image.ocr` / `office.structure` / `html.structure`
  / `canvas.structure` / `media.probe` returns `rejected`, while `text.extract` returns
  `succeeded`. In a production launch the Core errors out before spawning any worker, so
  this path is not what the operator sees.

Consequence to state plainly: the per-format Rust suites passing does **not** mean the
product can convert a PDF. It means the executor *can* when a test registers the route.

Formats that additionally lack a reachable engine, named separately from the route gap:

| Format | Status | Why |
| --- | --- | --- |
| audio → ASR transcription | **RESOLVED on this branch** | `media/worker_transcribe.py` had a real engine, a real model and verified output while no route named its capability. It now has a sidecar mode and the `media.transcribe` route, verified end to end through the real Core — see §3b. It is the one format the pack requires before final closure. |
| video decode | still `NO_ROUTE`, path **fixed** | `media/worker_video.py` likewise has no sidecar mode or declared capability; its ffmpeg path now resolves through the declaration as well as `PATH`. |
| webpage fetch | `NO_ROUTE` | `web/worker_webpage.py` same; a fetch is deliberately not part of the HTML route. |
| image caption / VL | `BLOCKED` | needs an Ollama endpoint at `127.0.0.1:11434` with `qwen2.5vl:7b`; no `ollama` binary and nothing listening. LM Studio is installed but has no models loaded and is not integrated — see §3b. |
| image OCR | **RESOLVED on this branch** | The route is now declared and registered, the engine and language data resolve from the declared registry, and the language being read selects the data. Real OCR of a real Chinese image converts through the Core (§3b). |

> **False test signal.** `crates/archeaxis-application/tests/ocr_job_end_to_end.rs` guards
> on tessdata being available and **returns early when it is not**, reporting
> `1 passed ... finished in 0.00s` while asserting nothing. On this machine it is a silent
> skip, not evidence that OCR works. A reader must not count that suite as OCR coverage.

`media.probe` is **not** transcription — it reads the container header only and says so.

### ASR now reaches the Core — a real recording, transcribed

`media/worker_transcribe.py` had a real engine, a real model and verified output, and no Core
job could reach it: no sidecar mode and no declared capability. The repository's own
reachability record held the reason it was left unrouted — *"no model is configured in this
repository or on this machine's defaults. Routing it now would create a capability that always
fails for want of a model."* That reason is resolved rather than argued with: the model
resolves through the declared capability registry, with `ARCHEAXIS_ASR_MODEL_DIR` and a
declared-path fallback, and the audio media types now name the containers a reader exists for.

| Layer | Result |
| --- | --- |
| declared routes | `[..., 'media.transcribe', ...]` — the staged profile publishes it |
| Core job | import `202` → enqueue `202` → execute `202 running` → **`succeeded`** |
| transcript | `星环知识平台正在验证真实音频转写能力` / `这是一个用于测试的中文语音样本` |
| structure | `line-1` (0–19), `line-2` (19–34) — canonical anchors over the projected text |
| sidecar detail | language `zh` at `0.9983`, 2 segments over 8,940 ms, engine `python-worker-transcribe` 0.1.0, model `faster-whisper-large-v3-turbo`, `covered 2 / total 2` |
| timing | preserved as `cues` under `params.worker_output`: `0–4240 ms`, `4240–8119 ms` |

Two deliberate non-changes are worth recording. A `media` job is **not** silently redirected to
ASR: routing `.wav` to the transcribe engine was tried and reverted, because it changed the
meaning of the existing `media` kind — the container probe — whose own test depends on a
garbage file named `.wav` reaching the probe. Transcription therefore has its own kind and
capability. And `mp3`/`m4a`/`flac`/`ogg`/`opus` were previously unnamed in the media-type
table *because no reader could read them*; they are named now that one can, while staying out
of `media.probe`'s accepted types so the two readers remain disjoint.

A probe that cannot read the declaration reports `capability: false` with the reason rather
than crashing — which is what the runner's interpreter, with no PyYAML, requires. An explicit
`--profile` that is bad still fails closed, because a silent fallback answers a different
question than the one asked.

#### What replaced the original measurement

Everything above about routes being unreachable was fixed on this branch, and the detailed
evidence is in *Packaging-time capability readiness* and *Real learning material through
the staged runtime* below. In short:

* a launch now **declares** its capability routes, and the staged runtime publishes the
  ones whose workers are present, so the Core registers exactly what the runtime has;
* the nine standalone workers locate the shared transport from their own file, so the
  source tree and a staged runtime both work, where a fixed directory depth worked only
  for the source tree;
* the resolver reads the declared capability manifest, and a manifest it cannot read is a
  named failure instead of a silent "engine not found";
* PDF anchors are numbered globally and OCR language data is chosen for the language being
  read, which were the two defects the real-material run exposed.

Re-measured on real course material through a staged runtime: **readiness 9 of 9, cases
converted 9 of 9**. The formats named as lacking a route in the table above — ASR
transcription, video decode, webpage fetch, image caption — remain outside the matrix for
the reasons given there; ASR and video decode before this branch also needed the path
fixes described in §3b, and image caption is still `BLOCKED` on a vision endpoint.

### P2 Search / Learning Plan / Course — `PARTIAL`

* Lexical search: **REAL**. `GET /api/v1/search` found the imported source and its
  transform with `source_found: true`.
* Semantic/embedding/reranker: **ABSENT in the Core**. `crates/archeaxis-domain/src/search.rs`
  is FTS5 only, and there is no embedding/vector/rerank code anywhere under `crates/`.
  The only vector code lives behind the legacy Python `/kb` sub-app, whose default
  "embedding" is a character n-gram hash, not a model.
* UI contract obligation: when no provider exists the UI must receive an explicit
  `unavailable`, which the contract document now specifies.

### P3 Human Learning — `PARTIAL (SYNTHETIC protocol evidence)`

* Real FSRS: **REAL dependency**. `fsrs>=5.0` is declared, and the scheduler runs as a
  bounded Python subprocess (`crates/archeaxis-application/src/scheduler.rs`). In the M0
  run the review path reported `schedule_authority:"fsrs"` with a real `due`,
  `stability`, `difficulty` and `step`.
* Idempotency: **REAL**. A replayed `client_event_id` returned `duplicate: true` with the
  original receipt.
* Cold restart readback: **REAL**. After stopping and restarting the Core on the same
  database, `answer`, `next_review` and the schedule were identical.
* Mastery: `mastery_projection.closed == false` is a deliberate open sentinel, not a
  defect. `correct_streak` is re-derived per read.
* **Not closed by real human first use.** The M0 receipt self-declares
  `evidence_level: "SYNTHETIC"` and `real_m0_verified: false` because the answer, the
  source and the human review action are fixtures. A synthetic pass is not a human first
  use, and this branch does not claim one.
* Reachable stub: `POST /api/v1/learning/events` without `schedule_state` still reports
  `placeholder_ladder` with a `null` next review — the 1/2/4/7/14 ladder. The UI must
  distinguish `fsrs` from `placeholder_ladder` from `unavailable`.

### P4 Machine Loop — `PARTIAL`, `STUB`-bound

* Machine task receipt write and readback, including `retest_of` binding to the original
  failure and binding to the corrected successor knowledge version: **REAL** (receipts are
  written by a machine principal and are immutable).
* Human correction: **REAL**, and it is the **only** correction path
  (`POST /knowledge-items/{id}/review-decisions` with `action:"modified"` creating a
  successor revision). A machine principal is refused.
* **No real model inference happened.** The M0 run posted `model_version:"stub/local-stub"`
  and `failure:"declared stub model, no real inference performed"`. The machine leg is
  therefore protocol evidence, not model evidence.
* **Gaps:** there is no HTTP writer for the machine competence ledger, and no endpoint
  that *starts* a retest — `retest_of` is only a field the machine fills in when it
  self-reports. `GET /learning/items/{item_key}/state` returns the fixed
  `machine: {"status":"not_recorded"}` even when receipts exist.

### P5 / P6 Persistence / Local Green — `PARTIAL`

* Online backup, a deliberate mutation, and a verified restore: **REAL**.
  `--maintenance-backup` exited `0` (`schema_version 6`); after deleting all
  `learning_events` rows and restoring, `counts_after == counts_before` exactly, with
  `verified: true` and a distinct `counts_mutated` proving the restore did work. An
  independent verifier repeated this for `machine_tasks`, `learning_assessments`,
  `card_references` and `knowledge_v3_metadata` and every table survived — this path uses
  the SQLite Online Backup API, not the archive table list.
* Cold restart with full state readback: **REAL** (see P3).
* **Not closed:** the real Legacy copy migration. The M0 probe reported
  `legacy_migration: {"skipped": "legacy database not present"}` and the run's sole
  validation error is `legacy migration not verified`. That leg is **paused by the Owner**
  and is reported `NOT_EXECUTED`, never `PASS`. In-place Green replacement and
  release/tagging remain `FROZEN` / Owner-gated.
* Verdict for this branch: **`NOT_READY`**, and now for a **narrower** reason than when this
  section was first written. The route and format reachability gap that made P1
  `NOT_REACHABLE` is closed (readiness 9 of 9, real material 9 of 9), so the remaining
  reasons are: the Legacy copy migration leg is paused by the Owner, P4 has no real model,
  and P2/P3 have not been exercised with real content or a real human first use. It is still
  not `LOCAL_GREEN_READY_FOR_OWNER_REVIEW`.

## 3b. Real material and the declared external resource library

The section above measures reachability with the repository's own synthetic golden
corpus. This one repeats the measurement with **real user learning material** and then
separates two causes that the golden corpus cannot distinguish: a route that is not
registered, and an engine path that does not resolve.

Material root (supplied by the Owner): `D:\All projects\ceshi` — a real Obsidian knowledge
base plus course archives. After excluding vault tool-state folders and machine-generated
`*ASR*` transcripts, it holds **3,095 real `.md` notes**, 1,203 `.png`, 66 `.pdf`, 64 `.mp4`,
24 `.docx`, 22 `.canvas`.

### Real material through the production launch — `scripts/probes/real_material_conversion_smoke.py`

`{CONVERTED: 1, FAILED_AT_ROUTE: 5}`. The one success is a real, human-authored Chinese
course note, converted by `python-worker-text` with `covered 47 / total 47`:

| Kind | Real file | Result |
| --- | --- | --- |
| `text` | `10_课程库\...\C0205_...\04_关键图表与课件索引.md` (2,048 B) | **CONVERTED** — 982 chars out, preserves the YAML frontmatter and the Mermaid block |
| `canvas` | `...\C0413_潜意识巨人\02_课程地图.canvas` (2,617 B) | failed — route gap |
| `html` | `...\TALOS-frontend-design\...\renderer\index.html` (13,060 B) | failed — route gap |
| `pdf` | `...\06.颠覆认知，圆梦清华.pdf` (100,776 B) | failed — route gap |
| `office` | `...\07.九大人生法则看考研成败（大字体）.docx` (63,409 B) | failed — route gap |
| `image` | `...\三命通会_p1.png` (11,958 B) | failed — route gap |

Every failure is the same `Core execution ended without a terminal receipt` after a `202`
acceptance, and every receipt records the origin path and the sha256 of the bytes sent. So
the route gap is not an artefact of synthetic fixtures: on real material the shipped binary
still converts only plain text.

### Engines themselves are present and working — the *paths* are the defect

The Owner's point is correct: the external libraries are not missing, and they are already
declared in `OS External Configuration/00-registry/project-tool-index.yaml` and
`config/environment/capability-requirements.yaml` with explicit paths and versions. I
verified those declared paths exist, then drove each engine through its own worker:

| Engine | Declared path | Default resolution (as shipped) | With the declared path |
| --- | --- | --- | --- |
| faster-whisper large-v3-turbo | `Model library\whisper\faster-whisper-large-v3-turbo` beside the declared external root (model.bin 1,617,884,929 B) | `worker_transcribe.py` derived `PROJECT_ROOT.parent/"Model library"` → in a worktree that resolves to `.project-local\worktrees\Model library\...` → `ASR model directory not found` | **fixed on this branch** — the probe now resolves the real model library with no override |
| tesseract 5.5.0 + tesseract-languages | `10-toolchains\scoop\apps\tesseract\current` and `...\tesseract-languages\current` | `worker_ocr.py` used `shutil.which("tesseract")` (not on `PATH`) and derived the binary from `TESSDATA_PREFIX`, which the session sets to a path **missing the `10-` prefix** → `tesseract binary not found on PATH` | **fixed on this branch** — see below |
| ffmpeg 8.1.2 | `10-toolchains\scoop\apps\ffmpeg\current\bin` | `worker_video.py` used **only** `shutil.which("ffmpeg")` and accepted no override at all | **fixed on this branch** — real 12.9 s MP4 produced a 16 kHz mono WAV, one sampled keyframe and a loss receipt naming the declared binary |

### Fixed on this branch: a declared-path resolver, wired into OCR

`services/python-workers/tool_paths.py` resolves a declared tool or model to an existing
path: an explicit per-tool override wins, then the manifest's `external_paths` resolved
against the declared external root. A declared path may not be absolute and may not escape
the root. A miss names the tool and what was consulted, and **never substitutes a binary
found on `PATH`** — `guess_on_path` only *reports* what PATH would have offered.

`vision/worker_ocr.py` now resolves both the binary and the language data through it.
Language data needed the same treatment: tesseract reads `TESSDATA_PREFIX` when no
`--tessdata-dir` is passed, so a stale ambient value silently overrode a correctly
resolved binary.

Real verification, with the ambient `TESSDATA_PREFIX` **deliberately left stale** and no
`TESSERACT_CMD` set:

* before: `{"error": "tesseract binary not found on PATH (OCR engine unavailable)"}`
* after: `tessdata_dir = ...\10-toolchains\scoop\apps\tesseract-languages\current`,
  text `三命通会` / `(明) 万明英_著`, `covered 3/3`

`tests/workflow/test_worker_tool_paths.py` (7 tests) pins override precedence, declared
resolution, the escape guard, and that the default path never consults `PATH` at all.

Two registry gaps surfaced while doing this, both for the Owner's registry rather than for
code: `faster-whisper-large-v3-turbo` — the model actually present on disk — is **not
declared** in `capability-requirements.yaml` (only `faster-whisper-base` is, as an
auto-download), while `sherpa-onnx` is declared as `../Model library/sherpa-onnx`, a
relative path that escapes the external root and is therefore refused by the resolver's
escape guard.

### All three engine paths now resolve from the declaration

`tool_paths.resolve(name)` is the single call a worker makes; `vision/worker_ocr.py`,
`media/worker_video.py` and `media/worker_transcribe.py` all use it. Verified against the
real registry, with no override of any kind set:

| Worker | Before | After |
| --- | --- | --- |
| OCR | `tesseract binary not found on PATH` | binary and language data resolved; real Chinese text read |
| video | `ffmpeg not found` | `ffmpeg version 8.1.2`; real 12.9 s MP4 → WAV + keyframe |
| transcribe | `ASR model directory not found` (worktree-derived path) | real model library resolved; a real 5.8 MB Chinese MP3 returned 3,362 chars across 295 segments |

What remains on this axis is **not** path resolution: see the route-enablement section below.

### Route enablement: the launch now declares its capability routes

This is the P1 blocker itself. `main.rs` called `Executor::open`, which seeds exactly one
route (`text.extract`), so every format engine was implemented, tested and unreachable.

The launch document's `text_worker` now carries an optional `routes` list of
`{capability, script}`. `main.rs` registers **exactly what is declared and nothing more**:
the Core still never assumes a checkout layout, and an absent list keeps the previous
single-route behaviour byte for byte. Validation refuses, rather than silently shadowing:
an empty capability, a script that is not an existing absolute local path, a
parent-directory escape, a redeclaration of `text.extract`, and a duplicate capability.

Two process-level tests launch the real binary:

| Test | Result |
| --- | --- |
| a declared `canvas.structure` route reaches its worker | canvas job settles **succeeded** |
| nothing declared, same canvas job | still fails closed |

`packages/contracts/bootstrap/v2/launch.schema.json` documents the field.

### The staged runtime publishes routes, and a staged run now converts non-text

Two further halves had to land before a staged candidate could use this, and a staged
run is what exposed the second one:

* `backend_launcher.load_profile` validated the profile field set **exactly**, so a
  profile carrying `routes` was rejected outright and `start()` never forwarded any. It
  now accepts an optional `routes` list, resolves each script relative to the profile,
  requires it to exist, and refuses a malformed entry by name instead of dropping it — a
  dropped route would resurface later as an unexplained failed job.
  `stage_backend_runtime` derives the routes it declares from the workers actually
  present, so a candidate never advertises an absent script (which the Core refuses) or a
  capability with no worker (which would fail at job time).
* **Every one of the nine sidecar-capable workers could not start in a staged tree.**
  They located the shared transport via a fixed `parents[3]` plus a
  `services/python-workers/` suffix, which is correct only for the source layout. The
  staged layout puts workers at `<root>/workers/<category>/` with the transport at
  `<root>/workers/transport/`, so the worker died with `FileNotFoundError` before serving
  anything. Each worker now tries both known layouts from its own file.

Verified end to end with `scripts/probes/staged_runtime_routes_smoke.py`, which builds a
runtime root, writes a profile whose routes come from the stager's own `present_routes`,
starts the Core through the launcher's own `load_profile` + `start`, and runs a canvas
job:

| Run | Result |
| --- | --- |
| before the worker fix | `FileNotFoundError: ...\staged-routes\services\python-workers\transport\text_ndjson.py` |
| after | **`job_state: succeeded`** on the golden canvas fixture |

This is the first time the loop runs from a **staged** tree rather than a source checkout:
staged profile → launcher → Core → declared route → real worker → converted output.

### Staged per-format matrix — 11 of 12 real inputs convert

One runtime root, routes from the stager's own `present_routes`, workers under the
runtime's own interpreter, one real input per capability
(`scripts/probes/staged_format_matrix_smoke.py`):

| Case | Engine the Core reported | Verdict |
| --- | --- | --- |
| text/txt | `python-worker-text` | CONVERTED |
| pdf | `pymupdf-native-pdf` | CONVERTED |
| office/docx | `python-worker-office` | CONVERTED |
| office/xlsx | `python-worker-office` | CONVERTED |
| office/pptx | `python-worker-office` | CONVERTED |
| html | `python-worker-html` | CONVERTED |
| canvas | `python-worker-canvas` | CONVERTED |
| subtitles | `python-worker-subtitles` | CONVERTED |
| archive | `python-worker-archive` | CONVERTED |
| media/wav | `python-worker-media` | CONVERTED |
| media/mp4 | `python-worker-media` | CONVERTED |
| image/ocr | — | FAILED_AT_ROUTE |

**One condition must be stated with this result, because without it the same matrix
reports only 8 of 12.** The runtime's interpreter has to carry the engine distributions:
with a standard-library-only interpreter, pdf/xlsx/pptx fail with
`no native PDF engine available`, `xlsx engine missing` and `pptx engine missing`. I
confirmed that is a packaging condition and not a product defect by provisioning the
engines into the registered standalone runtime, after which those three converted — and
then restoring that runtime to exactly its previous contents (`pip`, `README.txt`), since
it is an Owner-registered shared resource and not mine to leave modified.

**The OCR case is explained, and it was not the engine.** The staged OCR job failed with
`Failed loading language 'eng' ... Tesseract couldn't load any languages!`, which reads
like a language-data problem. The actual cause was the resolver's reader:

`tool_paths` read `capability-requirements.yaml` with a bare `import yaml` inside
`try/except ImportError: return []`, and treated a read or parse failure the same way. On a
runtime interpreter **without PyYAML** every declared path therefore resolved to nothing
and the worker reported

```
tesseract binary not found on PATH (OCR engine unavailable)
```

for an engine that is installed and declared. A missing YAML parser was reported as a
missing engine — the silent downgrade the project's rules forbid, and the reason this took
two rounds to place: the message pointed at tesseract while the fault was the reader.

Fixed on this branch. `ManifestUnreadable` now names the manifest, the reason, and the
remedy, and is distinct from `ToolNotFound`; the workers delegate to `tool_paths.declared`
instead of keeping their own `except Exception: return None` wrappers, which was the
mechanism that turned the fault into a quiet miss. Verified on the same interpreter that
lacks PyYAML:

| | Message |
| --- | --- |
| before | `tesseract binary not found on PATH (OCR engine unavailable)` |
| after | `<manifest>: no YAML parser available (No module named 'yaml'); install PyYAML so declared capabilities can be read` |

and on an interpreter that has it, the same worker reads
`OCR GOLDEN ANCHOR / Synthetic screenshot fixture - no personal data`.

**So the runtimes differ in a way that is worth stating plainly:** the format workers need
their engine distributions **and** the resolver needs PyYAML. The interpreter must carry
both. This is a packaging condition and it is why the matrix reports 11 of 12 on a
provisioned runtime and 8 of 12 on a bare one — the three extra failures are
`pdf`/`xlsx`/`pptx` engine imports, and the OCR case was this parser.

Also not covered by the matrix: `image.caption`, which needs a vision model at an Ollama
endpoint this host does not serve. It is absent on purpose rather than reported as a pass.

### Packaging-time capability readiness — the two runtime failures as a check

Both staged failures above were packaging conditions that only appeared at first use, as
engine-shaped errors from a job. `scripts/release/verify_backend_capabilities.py` answers
them at packaging time instead. For every route the profile declares it checks, against the
interpreter the profile names:

* **launch** — the worker starts under that interpreter and emits a protocol hello
  advertising exactly the capability being declared. That proves the interpreter runs the
  worker, the shared transport loads, and the declared capability is the one the worker
  actually serves. (Verified as a usable signal: all nine sidecar workers emit a valid
  hello naming their own capability.)
* **engine** — the engine's Python modules are importable by that interpreter, and each
  external executable resolves **through the declared capability manifest, not PATH**,
  which is the distinction that made a working tesseract look absent.

A failing route is named and the run fails closed; nothing is installed. A capability that
needs a served model is reported `unverifiable` rather than passed.

Run against one staged tree with two interpreters:

| Interpreter | Result |
| --- | --- |
| standard-library only | fails closed, naming the missing import per route (`ModuleNotFoundError: No module named 'fitz'`) |
| with the engines and PyYAML | `total 9 / ready 9 / not_ready 0`, exit 0 |

The requirements table follows the imports the workers **actually make**, and a test
enforces it both ways — a capability with no entry, or a module the worker never imports,
fails the suite. Writing that table from memory produced two wrong entries (`html` listed
`bs4` and `image.ocr` listed `PIL`, neither of which those workers import); the check is
what caught them, and the test now prevents the drift.

**This is the mechanism behind the earlier verdicts.** "A staged runtime can convert 11 of
12" is a statement about a *provisioned* runtime, and this checker is what decides whether
a given runtime is provisioned, per route, without running a job.

### Real learning material through the staged runtime — 9 of 9 convert

The matrix above uses the repository's synthetic golden corpus. Setting
`ARCHEAXIS_REAL_MATERIAL_ROOT` makes the same probe pick one real file per route from a real
library and record each file's origin and size, so the conversion is of real content. The
same run now also reports the acceptance verdict — every declared route ready **and** every
selected case converted, exiting non-zero otherwise — so "the probe finished" can never read
as a pass.

| Case | Engine the Core reported | Result |
| --- | --- | --- |
| text/md · text/csv · text/json | `python-worker-text` | CONVERTED ×3 |
| pdf | `pymupdf-native-pdf` | CONVERTED |
| image/ocr | `python-worker-ocr` | CONVERTED |
| office/docx | `python-worker-office` | CONVERTED |
| html | `python-worker-html` | CONVERTED |
| canvas | `python-worker-canvas` | CONVERTED |
| media/mp4 | `python-worker-media` | CONVERTED |

```
accepted: true   verdict_reason: "ready and every case converted"
readiness: total 9 / ready 9 / not_ready 0
verdicts:  CONVERTED 9
```

The first run of this matrix reported **7 of 9**. Both failures were defects, and both are
now fixed with tests that fail if the defect returns:

* **PDF** used a page-local line counter in the anchor's final path segment, which the Core
  treats as the line's global position. Single-page PDFs hide this because page-local equals
  global; a real multi-page PDF does not. See the anchor section above.
* **OCR** hardcoded `eng` for the route and consulted the declaration for language data
  never — only the repository's bundled copy. A Chinese page was therefore handed the
  English model. `ARCHEAXIS_OCR_LANG` now selects the language (default `eng`),
  `ARCHEAXIS_OCR_TESSDATA` can pin the directory, the chosen directory must actually hold
  the requested language, and the declared `tesseract-languages` entry is a candidate
  resolved through the same resolver the workers use.

**Image captioning remains out of scope**: `image.caption` needs a vision model at an Ollama
endpoint this host does not serve. It is absent from the matrix on purpose rather than
reported as a pass.

### Reproducing this

`docs/current/AAOS-BACKEND-ACCEPTANCE-RUNBOOK-20261001.md` records the branch and base, the
preconditions and how to check each, the two commands with their exit semantics (`0` pass,
`1` fail closed, `2` usage), the observed output, what is deliberately not covered, the
Windows toolchain note, and the rollback. The readiness check states its own preconditions:
`verify_backend_capabilities.py --requirements` enumerates, per capability, the Python
modules and declared executables a runtime needs, and a failing check carries `missing` —
the distinct modules and executables that are absent — so the gap between a runtime and a
passing run is enumerable rather than guessed at. A route that could not be **checked**
(for instance because the manifest cannot be read) is reported as not checked rather than as
an absent engine.

### PDF anchors are numbered globally — the multi-page receipt

The Core addresses an anchor by its span and by the **final** path segment, treating any
leading segment as a qualifier. The PDF worker put a *page-local* line counter in that
final position, so page 2 began at `["page-2","line-1"]` while the Core expected
`["line-26"]`. Every `char_start`/`char_end` was correct; only the label differed. On a
single-page document page-local equals global, so the golden single-page fixture never
showed it and the first real multi-page PDF did.

Located by reproducing the rejection outside the Core and applying the Core's own rules to
the worker's response: five anchors differed, with identical spans.

| | Result |
| --- | --- |
| reproducer, before | 5 differing anchors, `structure or coverage does not match projected text` |
| reproducer, after | **0 differences** |
| new regression test | a two-page PDF with different line counts per page; asserts the job **succeeds** and every anchor names its global line with the page as a leading qualifier |
| reverting only the worker line | that test **fails at `execute`**, so it detects the defect rather than describing it |
| `receipt_spans` guard | still refuses a genuinely wrong final segment, so the fix does not weaken it |

The OCR failure was this branch's fault and is now fixed: an ambient `TESSDATA_PREFIX`
holding unrelated languages was accepted as "usable" because the check required only *some*
`*.traineddata`. The worker kept it, passed no `--tessdata-dir`, and tesseract reported
`Failed loading language`. The check now requires **the language being read**, so an ambient
directory is kept only when it can serve it. Real verification with an ambient directory
that exists and holds only `deu`, asking for `chi_sim`: the declared language data is used
and the worker reads `三命通会` / `(明) 万明英_著`, `covered 3/3`. With both fixes, every case
in the real-material matrix has a route, an anchor scheme and an engine path that hold.

Note on the packaging path: the full `stage_backend_runtime.py` refuses linked donor
trees (`ValueError: protected staging path`). That is deliberate fail-closed behaviour and
it rejected both `.venv` and the uv-managed interpreter directories on this host, so the
probe builds a minimal root (Core + workers + profile) instead. The stager's route
derivation is nonetheless covered by unit tests, and `CI`'s `green-candidate-vnext` job
passes.

So the corrected classification is:

* **Route gap** — the Core registers only `text.extract`; this is why every binary format
  fails in production. Unchanged by anything above.
* **Path-resolution defect** — where a route exists or a worker is invoked directly, the
  worker still guesses (`which()`) or derives a relative path instead of reading the
  declared resource registry. `worker_transcribe` at least accepts `--model-dir` /
  `ARCHEAXIS_ASR_MODEL_DIR`; `worker_ocr` accepts `TESSERACT_CMD`; `worker_video` accepts
  nothing.
* **Language selection** — OCR defaulted to `eng` over a Chinese image and produced
  garbage. That is a caller-side choice, not an engine fault.

This is precisely the A02 deliverable that is still missing: *model resolver*, *tool
resolver*, *external capability registry*, *exact paths*, **no PATH guessing**. A02 is
recorded as `BLOCKED_BY_OWNER_DECISION` because the resource-root schema needs an Owner
decision — but "stop guessing and read the declared paths" is not a schema decision, and
it is what unblocks the engines.

### On LM Studio

The Owner also notes LM Studio is installed. Verified: `C:\Users\ALEX\.lmstudio` exists, an
`LMS` process is running, and `~/.lmstudio/bin/lms.exe` is present. However `~/.lmstudio/models`
is **empty**, nothing is listening on port 1234, and **no file under `config/` mentions
LM Studio** — the only model server the code knows is Ollama at `127.0.0.1:11434`
(`config/defaults.yaml`, `config/model-profiles/*`), and the vision caption worker speaks
Ollama's native `/api/generate` rather than the OpenAI-compatible `/v1` surface LM Studio
serves. So LM Studio is a real local runtime that is **not integrated and currently has no
models loaded**, and it does not change the caption/VL `BLOCKED` verdict. It is a candidate
for the A02/A03 registry, not an available engine today.

## 4. Per-key disposition against the disposition ledger
Lane `BACKEND_FRONTEND_LOOP` (54 keys). Evidence level is the highest actually reached.

| Key | Maps to | Status | Evidence | Basis |
| --- | --- | --- | --- | --- |
| `AA-BE-01` Provider Consumption Contract | A03/A11 | `PARTIAL` | `NO_EVIDENCE` | No provider was consumed; no embedding/model provider route exists. |
| `AA-BE-02` Multiformat Intake unified contract | A05 | `PARTIAL` | `REAL` (intake) / `FAILED` (convert) | Intake accepts every real fixture with `202`; conversion is text-only. |
| `AA-BE-03` OCR | A05 | `BLOCKED` | `NO_EVIDENCE` | Route not registered in production; tesseract present but off `PATH` and `TESSDATA_PREFIX` stale. |
| `AA-BE-04` ASR | A05 | `BLOCKED` | `NO_EVIDENCE` | No route, no sidecar mode; model path mis-resolves. |
| `AA-BE-05` Retrieval | A06 | `PARTIAL` | `REAL` | Lexical FTS5 only; no vector/reranker route. |
| `AA-BE-06` General Learning | A09/A10 | `PARTIAL` | `SYNTHETIC` | General-only manifest validated locally; no real domain content. |
| `AA-BE-07` Human Learning | A08 | `PARTIAL` | `SYNTHETIC` | Real FSRS + real persistence; synthetic actions; no real human first use. |
| `AA-BE-08` Real Local Machine Loop | A07/A14 | `PARTIAL` | `SYNTHETIC` | Protocol path works; declared stub model, no inference. |
| `AA-BE-09` Backup / Restore | A13 | `PARTIAL` | `REAL` | Verified round trip via the SQLite Online Backup API, independently reproduced for learning and machine tables; the separate JSONL **archive** path omits four tables (§5.3). |
| `AA-BE-10` Legacy Copy Migration | A13 | `NOT_EXECUTED` | `NO_EVIDENCE` | Paused by the Owner. Not attempted, not passed. |
| `GJ-01` real multiformat input | A05 | `PARTIAL` | `REAL` | 10 real verified fixtures imported; 9 formats fail to convert. |
| `GJ-02` Source → Knowledge | A04/A05 | `REAL` | `REAL` | Text source produced anchored candidate + V3 with real hashes. |
| `GJ-03` Search | A06 | `REAL` | `REAL` | Lexical hit bound to `source_id` and `transform_id`. |
| `GJ-04` Human Learning | A08 | `PARTIAL` | `SYNTHETIC` | As `AA-BE-07`. |
| `GJ-05` Human Restart | A08 | `REAL` | `REAL` | Identical state/schedule after same-database restart. |
| `GJ-06` Machine Learning Loop | A07/A14 | `PARTIAL` | `SYNTHETIC` | As `AA-BE-08`. |
| `GJ-07` Machine Restart | A07/A14 | `PARTIAL` | `SYNTHETIC` | Machine receipts survived restart in the M0 run. |
| `GJ-08` Backup / Restore | A13 | `PARTIAL` | `REAL` | As `AA-BE-09`. |
| `GJ-09` Legacy Migration | A13 | `NOT_EXECUTED` | `NO_EVIDENCE` | Owner-paused. |
| `GJ-10` Exact-source Candidate | A13 | `REAL` | `REAL` | Candidate bound to persisted transform + UTF-16 selection + raw hash. |
| `GJ-11` Native Acceptance | A12/A15 | `NOT_EXECUTED` | `NO_EVIDENCE` | Desktop binary not launched on this branch; UI writer owns that surface. |
| `ATLAS-0929:REQ-SOURCE-001` | CAP-0010 | `REAL` | `REAL` | Original bytes preserved, hash verified. |
| `ATLAS-0929:REQ-CONVERT-001` | CAP-0020 | `PARTIAL` | `REAL` | Text only; 9 formats fail. |
| `ATLAS-0929:REQ-EVIDENCE-001` | CAP-0030 | `REAL` | `REAL` | Anchor + UTF-16 range + quote validated by the Core. |
| `ATLAS-0929:REQ-LEARNING-001` | CAP-0040 | `PARTIAL` | `SYNTHETIC` | As `AA-BE-07`. |
| `ATLAS-0929:REQ-INTEROP-001` | CAP-0100 | `PARTIAL` | `REAL` | Backend launcher credential contract fixed (see §5). |
| `ATLAS-0929:REQ-SEARCH-001` | CAP-0110 | `PARTIAL` | `REAL` | Lexical only. |
| `ATLAS-0929:REQ-DESKTOP-001` | CAP-0120 | `NOT_EXECUTED` | `NO_EVIDENCE` | Out of this branch's write set. |
| `ATLAS-0929:REQ-BACKUP-001` | CAP-0140 | `PARTIAL` | `REAL` | As `AA-BE-09`. |
| `ATLAS-0929:REQ-IDENTITY-001` | — | `REAL` | `REAL` | Naming/identity unchanged; no rename performed. |
| `R6-LIVE-LEDGER:A00` | — | `PARTIAL` | `REAL` | Authority re-read live; `AUTHORITY.md` still absent. |
| `R6-LIVE-LEDGER:A01` | — | `REAL` | `REAL` | Release `FROZEN` respected; no tag/release created. |
| `R6-LIVE-LEDGER:A03` | — | `PARTIAL` | `NO_EVIDENCE` | Capability registry still two hard-coded route tables. |
| `R6-LIVE-LEDGER:A04` | — | `REAL` | `REAL` | V3 write/read path exercised with real hashes. |
| `R6-LIVE-LEDGER:A05` | — | `PARTIAL` | `REAL` | One format reachable; nine not. |
| `R6-LIVE-LEDGER:A06` | — | `PARTIAL` | `REAL` | Lexical only. |
| `R6-LIVE-LEDGER:A07` | — | `PARTIAL` | `SYNTHETIC` | No real model. |
| `R6-LIVE-LEDGER:A08` | — | `PARTIAL` | `SYNTHETIC` | No real human first use. |
| `R6-LIVE-LEDGER:A09` | — | `PARTIAL` | `SYNTHETIC` | General-only. |
| `R6-LIVE-LEDGER:A10` | — | `PARTIAL` | `SYNTHETIC` | First renderer only. |
| `R6-LIVE-LEDGER:A11` | — | `NO_EVIDENCE` | `NO_EVIDENCE` | No provider executed. |
| `R6-LIVE-LEDGER:A13` | — | `PARTIAL` | `REAL` | Backup/restore real; migration paused; export set incomplete. |
| `R6-LIVE-LEDGER:A14` | — | `PARTIAL` | `SYNTHETIC` | Full loop proven only with fixtures. |
| `R6-LIVE-LEDGER:A15` | — | `NOT_EXECUTED` | `NO_EVIDENCE` | Independent G01–G14 qualification not run. |
| `M0-OVERLAY:P0` | — | `PARTIAL` | `REAL` | See §3. |
| `M0-OVERLAY:P1` | — | `PARTIAL` | `REAL` | One of ten formats reachable. |
| `M0-OVERLAY:P2` | — | `PARTIAL` | `REAL` | Lexical only. |
| `M0-OVERLAY:P3` | — | `PARTIAL` | `SYNTHETIC` | Real FSRS, synthetic actor. |
| `M0-OVERLAY:P4` | — | `PARTIAL` | `SYNTHETIC` | Stub model. |
| `M0-OVERLAY:P5` | — | `PARTIAL` | `REAL` | No migration. |
| `M0-OVERLAY:P6` | — | `NOT_READY` | `NO_EVIDENCE` | See §3. |
| `DP-GIT-01` branch/commit semantic audit | — | `REAL` | `REAL` | Base divergence documented in §0. |
| `DP-F01` real text quality roundtrip | — | `REAL` | `REAL` | Text round trip through the production shape. |
| `DP-A11` research contract gap analysis | — | `NOT_EXECUTED` | `NO_EVIDENCE` | Not started. |

Lane `OWNER_GATE` (4 keys) — all remain `BLOCKED_BY_OWNER_DECISION`, none attempted:

| Key | Requirement | Status |
| --- | --- | --- |
| `RECORD-0928:GJ-12` (`A15`) | Independent audit / Local Green qualification | `BLOCKED` |
| `RECORD-0928:GJ-13` (`A16`) | Green Owner Gate | `BLOCKED` |
| `R6-LIVE-LEDGER:A02` | Resource-root environment authority | `BLOCKED` |
| `R6-LIVE-LEDGER:A16` | P0–P6 closure + real migration + backup/replace/rollback | `BLOCKED` |

## 5. Defects found and fixed, or found and left open

### Fixed on this branch

1. **Backend launcher machine credential was sent in a header the Core never reads.**
   `scripts/release/backend_launcher.py` published the machine token as
   `x-archeaxis-machine-token`. `crates/archeaxis-api/src/launch.rs::authenticate` reads
   only `x-archeaxis-launch-token` and matches it against either token. Impact was
   **latent** (the launcher only issued human `GET`s), but any future machine call using
   those credentials would have been silently attributed to the **human** actor instead of
   being refused — an identity downgrade with no visible error.
   Fix: a `credential(tokens, role)` helper that selects the token by principal and always
   sends it in `x-archeaxis-launch-token`, plus an opt-in `role=` on `call()`. Covered by a
   new regression test written RED-first (`AttributeError` before the fix, passing after).
   `tests/test_backend_runtime_safety.py`: **33 passed**; launcher consumers: **28 passed**.

### Found and left open (each needs its own decision)

2. **Format routes are not registered in the production binary** (P1 headline). Largest gap
   between "works in tests" and "works in the product". Needs a route-enablement mechanism
   plus a regression test that launches the production shape and converts one real fixture
   per format. Not attempted here because choosing the enablement mechanism is an
   architectural decision and the R6 boundary says to wire only what the current loop
   requires. **Owner decision requested.**
3. **The open-format JSONL archive omits four live data tables.**
   `EXPORT_TABLES` in `crates/archeaxis-archive/src/lib.rs` lists 16 tables and leaves out
   `machine_tasks`, `learning_assessments`, `card_references` and `knowledge_v3_metadata`,
   so an archive export/restore round trip silently drops human-learning assessments,
   learning-item references, machine task receipts and the V3 governance sidecar.
   `crates/archeaxis-domain/src/machine.rs` already documents this limitation in-tree
   ("_because it is created on demand it is not part of EXPORT_TABLES, so archives do not
   carry machine receipts yet_").

   **This is not the online backup path, and it is not a backup data-loss bug.**
   `--maintenance-backup` / `--maintenance-restore` go through
   `crates/archeaxis-domain/src/backup.rs`, which uses the **SQLite Online Backup API**
   (a page-level copy of the whole database) and never consults `EXPORT_TABLES`. An
   independent verifier drove real HTTP routes to create rows in all four tables and then
   ran the real maintenance CLI; every table survived the backup, a deliberate mutation,
   and the restore (`machine_tasks` 1→1→0→1, `learning_assessments` 1→1→0→1,
   `card_references` 1→1→0→1, `knowledge_v3_metadata` 1→1→1→1; `verified: true`).

   Reachability: `--maintenance-export` is not a supported flag (exit 2), no HTTP route
   calls `export_workspace`, and no script calls it, so the archive path is exercised only
   by Rust tests today. A separate stale-comment defect remains: the v3-layout comment in
   the same file still describes its 13-table set as "identical to the current table set",
   which is wrong at schema version 6.
4. **`GET /sources/{id}/jobs/{job_id}/transform` filters `kind='text'`**, so a non-text
   transform is unreadable through the source-scoped route even when the job succeeded.
5. **ASR / video / webpage workers cannot be launched by the Core at all** (no
   `--staging-root` sidecar mode, no declared capability).
6. **Path resolution instead of the declared registry** — partially fixed on this branch.
   `services/python-workers/tool_paths.py` now resolves declared paths and never falls back
   to `PATH`, and `vision/worker_ocr.py` uses it for both the binary and the language data.
   Still to do on the same axis: `worker_video.py` (accepts no engine override at all) and
   `worker_transcribe.py` (still derives its model directory). Also needs the Owner's
   registry updated: `faster-whisper-large-v3-turbo` is present on disk but undeclared, and
   `sherpa-onnx` is declared with a root-escaping relative path.
7. **Contract drift.** `packages/contracts/v1/openapi-outline.yaml` declares five
   unregistered routes and omits several real ones. Superseded for UI work by
   `docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md`.
8. **`docs/current/DSH-BACKEND-CONTRACT-20260927.md`** lists `POST /jobs/{id}/receipts` in
   its 30-route table; that route is test-only and answers `404` in production.

## 6. Delivered artifacts

| Artifact | Kind | Why |
| --- | --- | --- |
| `docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md` | contract | The UI branch's versioned, live-verified route/auth contract. |
| `scripts/probes/production_format_coverage_smoke.py` | probe | Measures per-format production reachability; the evidence for P1. |
| `scripts/release/backend_launcher.py` | fix | Credential/actor misattribution. |
| `tests/test_backend_runtime_safety.py` | test | Regression test for the above. |
| `docs/current/AAOS-BACKEND-LOOP-EVIDENCE-20261001.md` | report | This document. |

## 7. Rollback

Single-commit rollback. On the branch:

```
git revert <commit>          # or: git checkout <base> -- \
  scripts/release/backend_launcher.py \
  tests/test_backend_runtime_safety.py
```

The two added files are additive and can be deleted without affecting behaviour. No
database was migrated, no release or tag was created, no runtime asset was replaced, and
nothing outside this worktree's git-ignored `.project-local\` was written. The root
checkout's modified and untracked paths were never touched.

## 8. What is explicitly `NOT_EXECUTED`

* Real Legacy copy migration, in-place Green replacement, rollback of an installed
  runtime, release/tag/version publication — Owner-paused.
* Desktop (Avalonia) launch and native UI acceptance — the UI writer's surface.
* Independent G01–G14 Local Green qualification (A15) — requires an independent auditor.
* Real model inference, real embeddings/reranking, real human first use.
* Push, PR and exact-SHA CI readback — pending, reported separately once performed.
