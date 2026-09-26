# Backend takeover: real embedding provider and wheel-smoke gate repair (2026-09-26)

## Decision

Two bounded backend decisions were taken, both recorded with measured evidence in
`docs/current/R6-EXECUTION.md` (entries at 2026-09-26).

1. **The configured embedding provider is now real.** `rag.embedding.provider`
   previously had no effect on retrieval: `app/rag/index.py` called the built-in
   character n-gram embedder directly at index and query time, and
   `configured_embed_many` - the only reader of the setting - had no caller in
   `app/`, `shared/` or `knowledge_base/`. The built-in n-gram embedder remains the
   **default and the unconditional fallback**, so no provider failure becomes a hard
   dependency. `provider: ollama` routes to the registered local runtime through the
   same `POST /api/embed` shape `scripts/pipeline/eval_retrieval.py` already used;
   `provider: llm` keeps the LiteLLM path. Vector width is now a property of the
   resolved provider instead of a fixed 384, resolved from the vectors actually
   obtained, with an explicit `dim` still honoured.

2. **The `wheel-smoke` gate did not test the installed wheel.** The job's first step
   publishes `PYTHONPATH=<checkout root>` through `GITHUB_ENV`, and `GITHUB_ENV`
   persists into later steps, so the step named "Smoke-test installed runtime outside
   repository" imported repository sources. Its guard compared a `sys.path` entry's
   basename against the string `knowledge_base`, which cannot detect a checkout root.
   The step now clears the inherited path, asserts no `sys.path` entry equals
   `GITHUB_WORKSPACE`, requires exactly one installed distribution, and keeps the
   version assertion while printing both observed values on failure. No assertion was
   removed or relaxed.

Consequences that must not be overstated. `wheel-smoke`'s original failure is now **root-caused from the CI
job log**: the wheel was never installed. The build step's setuptools `egg_info` writes
`archeaxis_workspace.egg-info` into the checkout, and the job's first step leaks
`PYTHONPATH=<checkout root>` through `GITHUB_ENV`, so pip reported the just-built wheel as "already installed
with the same version" and skipped it. The smoke step therefore resolved `app`, `shared` and `knowledge_base`
from the checkout, and its version assertion compared the checkout's egg-info against the checkout's own
manifest - which is also why the original log records a bare `AssertionError` with no values: that assertion
carried no message. Both leaks are now closed, the install is `--force-reinstall`, and the assertion prints
both observed values on failure.

What is still unproven: whether the *installed* wheel actually satisfies the smoke step. That is only now
being tested for the first time, because before this change the checkout answered every import. Separately,
the reranker half of the M0 embedding requirement stays **open**: `qwen3-reranker:latest` declares `embedding`
but returns zero-norm vectors, so it is degenerate here and is not claimed as usable.

## Authority basis

- `docs/authority/taskpack-0919-r6/TASKPACK.md` and `docs/current/R6-STATE.json`
  (A06, A11 remain `TESTED_LOCAL_PARTIAL`; A15/A16 unsiged).
- `docs/current/M0-DIRECTION-OVERRIDE-20260920.md`: the embedding/reranker requirement
  is met by "a real usable implementation", local blocking must not stop other
  capability work, and external calls take timeouts and bounded retries.
- `D:\All projects\Model library\README.md` as the registered shared-resource
  inventory; `config/models.yaml` and `config/defaults.yaml` as the product-side
  adapter configuration.
- `AGENTS.md` sections 6 and 7.

## Scope and evidence boundary

- Registered shared resources were used **read-only**. Nothing was downloaded,
  installed, moved, cleaned or re-downloaded; no original material was uploaded; no
  licence was accepted. Only the paths the library README names were inspected.
- Measured, not inferred: both version values inside a same-condition wheel;
  the CI assertion under a clean interpreter; the real 1024-wide embedding, its
  semantic ordering, its end-to-end write/read through `sqlite-vec`, and its
  **non-reproducibility** (max |delta| ~1.4e-03, cosine ~0.9999); the reranker's zero
  norms; declared capabilities from `/api/show` including `vision` on `qwen2.5vl:7b`.
- Not claimed: a working reranker, a vision call, a benchmark, graph or research
  wiring, M0 completion, `main` integration, Local Green qualification, or any Owner
  gate. `local_green_updated=false`; release stays FROZEN.
