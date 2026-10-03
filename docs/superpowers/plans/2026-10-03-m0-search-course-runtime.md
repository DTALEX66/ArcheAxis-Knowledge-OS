# M0 Search and Course Runtime Implementation Plan

> For agentic workers: use superpowers:subagent-driven-development or superpowers:executing-plans task by task. Maintain one writer per write set.

**Goal:** Connect the existing M0 semantic-search and General course contracts to the canonical Core and desktop journey.

**Architecture:** Rust Core remains the only SQLite writer. Isolated Python adapters use the existing loopback model service and existing General course/lesson contracts; their outputs remain derived candidates. The desktop uses Core APIs and explicit human actions.

**Tech Stack:** Existing Rust/Axum/SQLite, Python standard-library HTTP plus installed donor dependencies, Avalonia; no new global installation.

**Spec:** `docs/current/M0-DIRECTION-OVERRIDE-20260920.md`, R6 A06/A09/A10, `app/contracts/general_learning_v1.py`, `app/contracts/courseware_v1.py`, `app/adapters/courseware_lesson.py`.

## Constraints

- Release stays FROZEN. Green replacement remains Owner-gated after P0–P5 evidence.
- No E drive, credential/session access, shared-weight reads or external-resource writes.
- Use one verified loopback embedding provider and one verified reranker. Unsupported endpoints fail explicitly; hash embeddings are not real semantic evidence.
- Preserve FTS5 and provenance. Semantic scores are ranking signals, not factual confidence.
- Reuse General component/objective/prerequisite/artifact contracts; native-lesson is the existing first renderer. No additional domain or renderer.
- Preserve human review and `Mastery != Truth`; do not invent mastery closure semantics.

## Tasks

- [ ] Preflight the existing local embedding/reranker endpoints with synthetic input; record exact model, response shape and failures without loading new shared assets.
- [ ] Add an isolated semantic-ranking adapter with bounded requests, finite/dimension-checked embeddings, provenance and explicit failure receipts. Test invalid responses and real endpoint execution.
- [ ] Connect semantic ranking to the existing Core search route while preserving lexical results and source/knowledge identity. Cover active status, errors and bounded execution.
- [ ] Add canonical General manifest/artifact persistence using the existing contracts, atomic Rust writes and source/version binding; include schema migration and archive/backup coverage.
- [ ] Reuse the existing lesson renderer via the worker boundary and expose its derived result through Core. Never auto-promote rendered content.
- [ ] Connect the General lesson to the existing desktop learning journey; keep internal diagnostics collapsed and make human acceptance/learning actions explicit.
- [ ] Verify same-source search→course→lesson→Assessment→human review→cold restart→backup/restore, then independent review and final candidate assembly.

## Write sets and verification

G4/UI worker owns desktop changes. Plugin worker owns executor/capability changes. Search/course worker owns new Python adapters and associated tests. Core integration is serialized by the root agent after those interfaces are verified. Run targeted RED→GREEN tests and affected module gates; only rerun the full final gate after integration stabilizes.

Endpoint availability, dependency availability and mastery authority remain facts to verify, not assumed success. Record partial/blocked conditions explicitly.
