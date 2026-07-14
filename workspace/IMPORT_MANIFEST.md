# Cognitive-OS Import Manifest

> Created: 2026-06-29
> Repository: `D:\Project\Cognitive-OS`
> Purpose: Track reusable assets imported from `Knowledge-Base` and `Inspiration-Research` without mixing reference material directly into runtime code.

---

## 1. Import Principle

`Cognitive-OS` is now the clean working repository for the cognitive operating system runtime.

The two earlier projects remain source projects:

| Source Project | Role | Import Policy |
|---|---|---|
| `Inspiration-Research` | Research, framework, A/B system design, bridge docs, intake logic | Import as design/reference first. Promote only through Intake Card. |
| `Knowledge-Base` | Current runnable engineering system and implementation reference | Import as code/doc reference first. Reuse only after adaptation. |

Obsidian remains only a partial upstream input source. It is not imported here and is not the main system.

---

## 2. Current Import Summary

| Import Root | Source | Files | Status |
|---|---|---:|---|
| `workspace/imports/inspiration-research/` | `D:\Project\Inspiration-Research` | 141 | Reference imported |
| `workspace/imports/knowledge-base/` | `D:\Project\Knowledge-Base` | 121 | Reference imported |

No nested `.git` directories were intentionally imported. Runtime data, databases, caches, build outputs, and dependency folders are excluded.

---

## 3. Inspiration-Research Imports

| Destination | Source | Contents | Use In Cognitive-OS | Promotion Rule |
|---|---|---|---|---|
| `workspace/imports/inspiration-research/root/` | IR root docs | README, project declaration, iron rules, lessons, bridge docs | Project boundary and governance reference | Can influence root docs and AGENTS rules after review |
| `workspace/imports/inspiration-research/docs/` | IR `docs/` | Current framework docs, A/B matrices, roadmap, production readiness, standards | Primary strategic design source | Convert into Cognitive-OS docs through summary, not raw copy |
| `workspace/imports/inspiration-research/maps/` | IR `maps/` | A/B mapping and migration priorities | Planning reference | Use in roadmap and task ordering |
| `workspace/imports/inspiration-research/reference-key-docs/` | IR `reference/*.md` | Integration plan, FSRS plan, extraction reports, GitHub references | Feature source and technical inspiration | Each feature needs an Intake Card |
| `workspace/imports/inspiration-research/dual-system-integration/` | IR dual-system docs | A/B integration and absorption analysis | Architecture reference | Use to define runtime boundaries |
| `workspace/imports/inspiration-research/a-line-design/` | IR A-Line selected design folders | Human Learning OS subsystem docs | A-system product and data model design | Promote per subsystem into implementation tasks |
| `workspace/imports/inspiration-research/b-line-design/` | IR B-Line folders | Machine/Agent OS design docs | B-system Agent/runtime design | Promote per subsystem into implementation tasks |

### Do Not Promote Directly

- Unverified paper claims.
- Historical archive material.
- Broad future roadmap promises.
- Any document that lacks a runtime target, acceptance criteria, and rollback path.

---

## 4. Knowledge-Base Imports

| Destination | Source | Contents | Use In Cognitive-OS | Promotion Rule |
|---|---|---|---|---|
| `workspace/imports/knowledge-base/root/` | KB root docs | README, INSTALL, AGENTS | Operating context and safety reference | Can inform Cognitive-OS README and AGENTS |
| `workspace/imports/knowledge-base/project-docs/` | KB project docs | KB README, manifest, status, MVP docs, API docs | Product baseline and compatibility reference | Summarize into Cognitive-OS docs; avoid direct promise copying |
| `workspace/imports/knowledge-base/code-reference/core/` | KB backend core | store, FSRS, quality, policy, migrations | Candidate implementation source for document/card/review/storage | Reuse by adaptation, not blind copy |
| `workspace/imports/knowledge-base/code-reference/learning_final/` | KB A-line implementation | diagnostics, encoding, teach, profile, metacognition, consolidation, palace | Candidate A-system services | Promote only after matching Cognitive-OS schemas |
| `workspace/imports/knowledge-base/code-reference/b_line/` | KB B-line implementation | context, routes, agent roles, sandbox, eval, trace, feedback | Candidate B-system services | Promote only after matching TaskPack/Trace/Memory contracts |
| `workspace/imports/knowledge-base/code-reference/mcp/` | KB MCP implementation | tool registry, permissions, audit, server | Candidate tool governance layer | Promote after risk model and dry-run policy are defined |
| `workspace/imports/knowledge-base/frontend-reference/` | KB frontend config | package, tsconfig, next config | Future frontend reference | Do not introduce frontend in Phase 1 |

### Do Not Promote Directly

- Raw database files.
- Generated cache/build output.
- Frontend feature sprawl before runtime pipeline is stable.
- Any KB code that assumes old `pk_radar` package paths without adaptation.

---

## 5. Active Runtime Baseline

The root app currently comes from the Cognitive OS starter code and has been validated locally.

| Runtime Area | Current Status |
|---|---|
| FastAPI app | Present at `app/main.py` |
| Schemas | Present at `app/schemas.py` |
| `/health` | Verified OK |
| `/run` | Verified with Chinese TASK input |
| REVIEW safety path | Verified with high-risk Chinese input |
| Trace JSONL | Writes under ignored `data/logs/` |
| Memory JSONL | Writes under ignored `data/memory/` |

Current minimum loop:

```text
Input -> ingest -> attention route -> retrieve -> compile task -> execute -> trace -> evaluate
```

---

## 6. Promotion Workflow

No imported reference becomes active runtime code until it passes this workflow.

```text
Imported Reference
  -> Intake Card
  -> Contract Mapping
  -> Minimal Runtime Patch
  -> Local Verification
  -> Trace / Memory Check
  -> Stable or Experimental Label
```

### Required Intake Card Fields

```text
Source file(s)
Target runtime module
Target schema(s)
API impact
Data impact
Risk level
Acceptance test
Rollback path
```

---

## 7. First Promotion Candidates

| Priority | Candidate | Source | Target | Reason |
|---:|---|---|---|---|
| 1 | Context Pack scoring | IR A/B final outcome + KB `b_line/context_engine.py` | `app/rag/` + `app/schemas.py` | Directly improves `/run` quality without heavy dependencies |
| 2 | Trace analyzer and MachineLesson | KB `b_line/trace_audit.py`, `machine_lesson.py`, `feedback_loop.py` | `app/evaluation/` + `app/memory/` | Closes feedback loop from execution to memory |
| 3 | Tool risk registry | KB `mcp/permissions.py`, `tool_registry.py`, `mcp_guard.py` | `app/tools/` | Strengthens dry-run and safety gate |
| 4 | FSRS/card model | KB `core/fsrs5.py`, `store.py` | future `app/learning/` | Adds human learning loop after runtime core is stable |
| 5 | Obsidian export contract | IR Obsidian docs | future ingestion spec | Keep Obsidian as input source only |

---

## 8. Phase 1 Boundary

Phase 1 should not import the whole old KB or IR architecture into runtime.

Do now:

```text
/health
/run
schemas
trace
memory
attention router
context pack stub
task pack stub
evaluation stub
risk review path
```

Do later:

```text
full frontend
multi-agent orchestration
real vector DB
real external tools
Obsidian sync
PDF/OCR/Whisper heavy ingestion
large framework dependencies
```

---

## 9. Safety Notes

- Imported files are reference assets until promoted.
- High-risk operations remain REVIEW or dry-run by default.
- No deletion or cleanup should happen without explicit confirmation.
- Do not use imported code to access external systems until permissions are explicit.
- Do not treat IR unverified research material as product truth.

---

## 10. Next Action

Create the first active Intake Card:

```text
workspace/intake/001_context_pack_scoring.md
```

Goal:

```text
Add a simple ContextPack score to the current `/run` pipeline using only local, deterministic signals.
```

Acceptance:

```text
/run returns context.score > 0 for matched memory
score reasons are explainable
no external network or heavy vector dependency
trace still writes successfully
```
