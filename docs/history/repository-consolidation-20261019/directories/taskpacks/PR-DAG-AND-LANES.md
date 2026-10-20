# vNext PR DAG and lanes

Before PR-03, `TASK-GRAPH.yaml` in the complete execution package is the
reviewed bootstrap source. PR-03 installs its byte-identical canonical copy at
`.project/TASK-GRAPH.yaml`; after that protected copy merges, it is the
machine-readable authority. This document is only a compact projection and
must not introduce another task ID system.

## Non-negotiable sequence

`PR-00 → PR-01 → PR-02 → PR-03 → PR-04`.

Only after PR-04 merges may Rust, Avalonia, Python and journey worktrees run in
parallel. Integration, migrations, lockfiles, root CI and release promotion stay
serial at their authority boundaries.

## Pull-request waves

| IDs | Delivery | Dependency edge | Exit |
|---|---|---|---|
| PR-00 | Owner decision, legacy freeze, G0 narrowing | none | authority fixed |
| PR-01 | Hermetic full-suite | PR-00 | two offline full runs |
| PR-02 | Exact-SHA qualification receipt and fail-closed release | PR-01 | hostile promotion fixtures |
| PR-03 | Directories, AGENTS, task/grant/GatePlan/receipt schemas and scope gate | PR-02 | governance hostile tests |
| PR-04 | OpenAPI/JSON Schema, DTO, errors and handshake | PR-03 | three-language fixtures |
| PR-05…PR-08 → PR-09 | Rust / Avalonia / Python / journey → Hello Triangle | PR-04 | Day-5 architecture proof |
| PR-10…PR-13 → PR-14 | content base / converter / reader / oracle → import integration | PR-09 | import, anchor, restart |
| PR-15 → (PR-16 / PR-17) → PR-18 | knowledge domain → UI / semantics → Alpha | PR-14 | review and FTS Alpha |
| PR-19 + PR-21 / PR-22; PR-19 → PR-20; all → PR-23 | learning + model pack / faults; then recovery UI → safety loop | PR-18 | feature freeze |
| PR-24 → PR-25 | exact-byte Green → clean-machine Owner Preview | PR-23 | 12 steps pass |
| PR-26 → PR-27 | legacy exporter → Rust migration | PR-25 | zero-loss migration gates |
| PR-28 → PR-29 | bounded web evidence → model competence | PR-25 / PR-21 | v0.2 receipts |
| PR-30 → PR-31 | Setup/Portable/Green → migration RC | PR-25 / PR-27 | Week-6 RC decision |
| PR-32 | legacy writer retirement | PR-31 plus owner preconditions | reversible small deletions |
| PR-33A…PR-33F | optional OCR, Office, media, web, vision, vector packs | individual entry conditions | measured capability receipts |

## Parallel ownership

- Owner/Integrator: decisions, protected shared paths, merge, release authorization.
- Rust Core: `crates/**` and `services/local-service/**`.
- Avalonia UI: `apps/desktop/**`.
- Python Capability: `services/python-workers/**`.
- Journey/Packaging: `fixtures/**`, `tests/**` and `packaging/**`.

Owner must not become a primary feature lane. With only three Agents, Python may
assist Journey/Packaging after PR-14; journey work is never removed.

These rows are 39 stable Program nodes, not pre-authorized PRs. Actual branches
use JIT child slices from `.project/EXECUTION-SLICE-BLUEPRINTS.yaml`; downstream
Programs unlock only through a Program completion receipt whose atom coverage is
complete.

## Scope cuts

Day 20 includes TXT, Markdown, native-text PDF, one real capability path and
Windows 11 Green only. Scanned PDF/OCR, Office, audio/video, automatic web
capture, vector retrieval, legacy migration, installers and other operating
systems may be deferred without weakening the v0.1 12-step acceptance gate.
