# Intake Card 002: Trace to MachineLesson

> Created: 2026-06-29
> Status: active
> Target phase: Phase 1 feedback loop
> Scope: deterministic lesson generation from local trace/eval only.

---

## 1. Source

| Source | Path |
|---|---|
| Cognitive OS start instruction | `workspace/imports/inspiration-research/docs/14_AB_SYSTEM_FINAL_OUTCOME_BLUEPRINT.md` |
| KB B-line feedback reference | `workspace/imports/knowledge-base/code-reference/b_line/feedback_loop.py` |
| KB machine lesson reference | `workspace/imports/knowledge-base/code-reference/b_line/machine_lesson.py` |
| Current runtime | `app/evaluation/feedback.py`, `app/evaluation/evaluator.py`, `app/core/trace.py`, `app/memory/store.py`, `app/main.py` |

---

## 2. Problem

The current `/run` pipeline writes an `ExecutionTrace` and returns an `EvalResult`, but it does not persist the learning from that run.

Without `MachineLesson`, the system can execute but cannot yet learn from execution.

---

## 3. Goal

After every completed non-REVIEW `/run`, generate and save a `MachineLesson`.

The first version should be deterministic:

```text
trace.success = true  -> success lesson
trace.success = false -> failure lesson
future_constraint     -> evaluator improvement text
```

---

## 4. Runtime Contract

### API

`POST /run` should return:

```text
lesson: MachineLesson
```

Add:

```text
GET /memory/lessons
```

### Persistence

Write lessons to:

```text
data/memory/lessons.jsonl
```

This path is runtime data and stays ignored by git.

---

## 5. Risk

| Risk | Control |
|---|---|
| Lesson quality is too generic | Mark as v1 deterministic lesson and keep evidence trace id |
| Runtime data accidentally committed | `data/memory/` is ignored |
| REVIEW path creates misleading lesson | Only completed runs generate lessons |
| Future AI-generated lessons hallucinate | Current version uses only trace/eval fields |

---

## 6. Acceptance

Local verification must show:

```text
/health returns 200
/run returns lesson
lesson.evidence_trace_id matches trace.id
GET /memory/lessons returns at least one lesson
high-risk delete/registry request still returns REVIEW high
```

---

## 7. Rollback

Revert only these files if needed:

```text
app/main.py
app/memory/store.py
app/evaluation/feedback.py
workspace/intake/002_trace_to_machine_lesson.md
```

No schema migration is required because `MachineLesson` already exists.
