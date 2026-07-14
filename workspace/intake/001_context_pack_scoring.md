# Intake Card 001: Context Pack Scoring

> Created: 2026-06-29
> Status: active
> Target phase: Phase 1 runtime quality improvement
> Scope: local deterministic scoring only; no external vector DB, no network, no LLM dependency.

---

## 1. Source

| Source | Path |
|---|---|
| IR outcome blueprint | `workspace/imports/inspiration-research/docs/14_AB_SYSTEM_FINAL_OUTCOME_BLUEPRINT.md` |
| IR A/B matrix | `workspace/imports/inspiration-research/docs/13_AB_SYSTEM_TECH_SKILL_PLUGIN_MATRIX.md` |
| KB B-line context reference | `workspace/imports/knowledge-base/code-reference/b_line/context_engine.py` |
| Current runtime | `app/rag/retriever.py`, `app/schemas.py`, `app/main.py` |

---

## 2. Problem

The current runtime can produce a `ContextPack`, but the score is too coarse:

```text
items exist -> score = 1.0
no items -> score = 0.0
```

This does not explain why the context is useful, how strong the match is, or whether `/run` is using meaningful memory.

---

## 3. Goal

Add a simple, local, explainable `ContextPack` scoring method.

The first version should score context using deterministic signals only:

```text
item_count
query_term_overlap
source_presence
```

No external network, vector database, LLM, or heavy dependency is allowed in this Intake Card.

---

## 4. Target Runtime Contract

### Schema

Extend `ContextPack` with:

```python
score_reasons: list[str]
```

### Retrieval

`retrieve(query)` should return:

```text
ContextPack.query
ContextPack.items
ContextPack.summary
ContextPack.score
ContextPack.score_reasons
```

### API Impact

`POST /run` already returns `context`, so no new endpoint is required.

---

## 5. Risk

| Risk | Control |
|---|---|
| Overstating context quality | Score remains heuristic and reasons are explicit |
| Adding heavy dependency | Use pure Python only |
| Breaking existing response shape | Only add optional-compatible field |
| Confusing imported reference with runtime code | Implement in root `app/`, keep imports as reference only |

---

## 6. Acceptance

A local test must show:

```text
/health returns 200
/run returns context.score > 0 for matched memory
/run returns context.score_reasons
high-risk delete/registry request returns REVIEW high
trace still writes successfully
```

---

## 7. Rollback

Revert only these files if needed:

```text
app/schemas.py
app/rag/retriever.py
workspace/intake/001_context_pack_scoring.md
```

No database migration is required.
