# AAOS backend acceptance runbook — 2026-10-01

How to reproduce, on this branch, the two results the loop claims:

1. **Capability readiness** — whether each capability route a runtime declares is actually
   usable on the interpreter it names, per route, without running a job.
2. **Format reachability** — whether real material of each format reaches the Core,
   converts, and stores its text, with the Core reporting the engine it used.

Both are executable, fail closed, and install nothing. Every number below is a command's
own output, not a summary.

## Branch and base

| | |
| --- | --- |
| branch | `codex/dsh-aaos-real-multiformat-loop-20261001` |
| base | `codex/Audit` @ `1a981a4482b01f31989074e79c82a63400aa07a7` |
| pull request | [#157](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/157) (Draft) |

## Preconditions

Nothing below needs network access. The stage that needs a runtime is the only one with a
non-trivial precondition.

| Need | Why | How to check |
| --- | --- | --- |
| a built Core binary | the probe launches it as the Core | `cargo build -p archeaxis-api` (see *Toolchain* below) |
| a Python interpreter for the workers | the Core spawns workers with it | any 3.11+ interpreter |
| engine distributions **in that interpreter** | `pdf`, `office` and `ocr` import their engines inside the worker | `verify_backend_capabilities.py --requirements` lists them; a ready run lists none |
| the declared external root | engines are found through the declaration, not `PATH` | `ARCHEAXIS_EXTERNAL_ROOT`; the manifest is `config/environment/capability-requirements.yaml` |

**The single most useful precondition check** — it enumerates what the capabilities need
without starting a worker or touching the runtime:

```bash
python scripts/release/verify_backend_capabilities.py --requirements
```

Schema `archeaxis.capability-requirements/v1`: per capability, the `python_modules`, the
declared `declared_executables`, and any `unverifiable_models`. If a runtime lacks one of
these, the readiness check below names it per route rather than reporting a generic
"engine missing".

## Stage 1 — capability readiness

```bash
ARCHEAXIS_EXTERNAL_ROOT="<external root>" \
python scripts/release/verify_backend_capabilities.py <staged root> \
    --interpreter <runtime python> --json-out readiness.json
```

For every route the staged profile declares, two checks run against that interpreter:

* **launch** — the worker starts and emits a protocol hello advertising exactly the
  capability being declared;
* **engine** — the engine's modules are importable, and each external executable resolves
  **through the declared manifest, not `PATH`**.

Exit `0` when every route is ready, `1` when not (each failing route is named), `2` on a
usage or precondition error. Schema `archeaxis.capability-readiness/v1`; the report also
carries `requirements` and `missing`, so a failing run states what to install.

Observed on a provisioned runtime: `total 9 / ready 9 / not_ready 0`, exit `0`.
Observed on a standard-library-only interpreter: exit `1`, with the missing import named
per route (e.g. `ModuleNotFoundError: No module named 'fitz'`).

## Stage 2 — format reachability on real material

```bash
ARCHEAXIS_EXTERNAL_ROOT="<external root>" \
ARCHEAXIS_REAL_MATERIAL_ROOT="<a library of real material>" \
ARCHEAXIS_OCR_LANG=chi_sim \
python scripts/probes/staged_format_matrix_smoke.py <core binary> <runtime python>
```

The probe stages a complete runtime (Core, workers, declared manifest, profile), launches
it, then drives one real file per route through import → enqueue → execute → outputs. With
`ARCHEAXIS_REAL_MATERIAL_ROOT` set it selects the smallest usable real file per route
(skipping tool state such as `.obsidian` and, via `ARCHEAXIS_REAL_EXCLUDE`, machine
transcripts) and records each file's origin; without it the repository's synthetic golden
corpus is used.

It runs stage 1 first and reports both. `ok` is the **acceptance verdict**, not "the probe
finished": every declared route ready **and** every selected case converted. Exit `0` only
then, `1` otherwise, `2` on a missing argument.

`ARCHEAXIS_OCR_LANG` selects the OCR language — it defaults to `eng` and is a property of
the material, not of the route. Material in another script needs it set, or OCR reads the
wrong model. `ARCHEAXIS_OCR_TESSDATA` can pin the language-data directory; the directory is
used only if it holds the requested language.

Observed on real course material, provisioned runtime:

```
accepted: true   verdict_reason: "ready and every case converted"
readiness: total 9 / ready 9 / not_ready 0
verdicts:  CONVERTED 9
```

including `pdf` → `pymupdf-native-pdf`, `office/docx` → `python-worker-office`,
`image/ocr` → `python-worker-ocr`, `media/mp4` → `python-worker-media`.

## Stage 3 — the published contract's own claims

`docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md` tells the UI branch what it may rely
on. Every section of it is checked, and the whole set runs from one command per side:

```bash
# §1 process model and handshake, §2 authentication, §4 constant fields,
# §5 conflicts and error shapes, §6 launch shape, §3 output and schedule-authority
# boundaries, §8 the route families that deliberately do not exist
cargo test -p archeaxis-api --test contract_process_model \
                            --test contract_auth_boundaries \
                            --test contract_constant_fields \
                            --test contract_conflict_rules \
                            --test contract_launch_shape \
                            --test contract_job_outputs \
                            --test contract_schedule_authority \
                            --test contract_absent_surfaces
```

```bash
# §3 route inventory, the index that keeps this list honest, and the numbers the documents state
python -m pytest tests/maintenance/test_contract_route_inventory.py \
                 tests/maintenance/test_contract_verification_map.py \
                 tests/maintenance/test_contract_number_consistency.py -q
```

`tests/maintenance/test_contract_verification_map.py` is the index: it maps each contract
section to the artifact that checks it and fails if one is renamed, deleted, or emptied, or if
the contract grows a section nothing covers. It does not re-check the claims — it keeps the
links real, because a missing test does not fail, it simply does not run.

`tests/maintenance/test_contract_number_consistency.py` compares every count the contract, this
runbook and the ledger state with the thing it describes — the matrix case counts, the route
counts, the readiness total, and the disposition's 58 keys with their evidence levels. It also
checks that the ledger agrees with the disposition it points at, that the disposition's stated
counts match its own entries, and that it covers exactly the keys in the two lanes this task
owns.

§7's evidence is the probes in this runbook plus `scripts/release/verify_backend_capabilities.py`;
§9's items each name the artifact that closed them, or are marked as Owner decisions.

Requires `ARCHEAXIS_PYTHON` set to an interpreter (see the toolchain note), and nothing else:
these drive the real binary or the real routers, so they need no provisioned runtime.

## What is not covered, on purpose

* **`image.caption`** needs a vision model at an Ollama endpoint this host does not serve.
  It is reported `unverifiable` rather than passed, and is absent from the matrix.
* **Supported formats this matrix does not exercise**: the golden corpus covers 12 cases
  and real-material mode 9, so six are golden-only here — `office/xlsx`, `office/pptx`,
  `subtitles`, `archive`, `media/wav` and `text/txt`. They are reachable and their
  golden-corpus results are recorded in
  `docs/current/AAOS-BACKEND-LOOP-EVIDENCE-20261001.md`; the real-material run selects one
  file per route and the library used here holds none for them.
* **Legacy data migration, in-place replacement, and release** are out of scope by the
  frozen boundary and are reported `NOT_EXECUTED`. `A02`/`A16` remain `BLOCKED`.

Readiness is not a quality claim: it says a route can run, not that its output is accurate.

## Toolchain note (Windows, this host)

`cargo build` here needs a working `rustc` and linker. The MSVC toolchain bin on this host
has `cargo.exe` but no `rustc.exe`, so use the GNU toolchain with MinGW on `PATH` and an
in-tree `CARGO_TARGET_DIR`:

```powershell
$env:PATH = "<mingw>\bin;$env:USERPROFILE\.rustup\toolchains\stable-x86_64-pc-windows-gnu\bin;$env:PATH"
$env:CARGO_TARGET_DIR = "<worktree>\.project-local\build\cargo-gnu"
```

Rust tests that drive Python workers require `ARCHEAXIS_PYTHON` set to the interpreter.

## Rollback

The branch is additive relative to its base: no schema migration and no data change. Every
commit is independently revertable; the two behavioural ones are the PDF anchor numbering
and the OCR language selection. Reverting either restores the previous behaviour and
re-fails exactly the regression test added with it.
