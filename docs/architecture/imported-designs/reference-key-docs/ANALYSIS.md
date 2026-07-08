# Reference Project Analysis

## 1. Reference Project Summaries

### rs-fsrs-python (Rust + PyO3 binding)
A native Python binding for the [rs-fsrs](https://github.com/open-spaced-repetition/rs-fsrs) Rust crate via PyO3/maturin. Exposes the full FSRS scheduler (Card, ReviewLog, Rating, Scheduler) as a compiled Rust extension module, delivering ~10-50x speedup over pure-Python FSRS implementations. Uses maturin as the build system with pyproject.toml, supports CPython 3.8+ and PyPy. The project follows the open-spaced-repetition spec with parameter optimization and Wozniak-style forgetting curves.

### fsrs_python_system (FastAPI Microservice)
A standalone FastAPI web service wrapping the py-fsrs library with SQLModel ORM for persistence. Implements full CRUD for decks and cards, spaced-repetition review endpoints (/repetition, /cards/next/{deck_id}), and per-user isolation via UUID-based security headers. Uses SQLite as the database with automatic migration via SQLModel.create_all. The architecture follows a clean DTO/service pattern with Pydantic models for request/response validation.

---

## 2. What We Have Already Integrated

- **FSRS-5 Algorithm**: Our `backend/pk_radar/core/fsrs5.py` implements the full FSRS-5 scheduler including the 19-parameter weight vector, retrievability decay (`R = exp(-t/S)`), stability/difficulty dual-state tracking, short-term vs long-term memory branches, and SM-2 score-to-grade mapping.
- **FastAPI Endpoints**: We have a complete FastAPI application with review, card, and deck management endpoints that mirror the microservice pattern from fsrs_python_system.
- **Card/Review System**: Our `cards` and `reviews` SQLite tables track memory_strength, interval_seconds, review_count, and per-review score with before/after strength snapshots.
- **FSRS Optimizer**: `backend/pk_radar/core/fsrs_optimizer.py` performs gradient-free weight optimization against real review data, outputting tuned weights to `backend/optimized_fsrs_weights.json`.

---

## 3. What We Could Still Integrate

### py-fsrs Native Rust Performance
Replace our pure-Python FSRS-5 with the `rs-fsrs-python` Rust binding. The compiled extension offers 10-50x throughput improvement for batch scheduling scenarios (generating schedules for hundreds of cards simultaneously). Integration would require adding `rs-fsrs-python` as a dependency (built via maturin) and wrapping the Rust Scheduler class behind our existing Python API.

### SQLModel ORM
The fsrs_python_system uses SQLModel (SQLAlchemy + Pydantic) for declarative table definitions with type-safe queries, automatic migration, and relationship management. Our current codebase uses raw sqlite3 with manual SQL strings. Migrating to SQLModel would give us: IDE autocompletion for queries, automatic schema migration via `SQLModel.metadata.create_all`, relationship cascading (deck -> cards), and cleaner DTO/schema separation.

### Batch Scheduling
The py-fsrs library supports batch card review and schedule computation in a single pass -- useful for "review all due cards" operations. We currently process cards one at a time. Adding batch support would reduce latency for decks with many due cards.

### Retention Graphs
The reference projects include retention analysis (predicted vs actual recall over time). We could add a `/stats/retention` endpoint that plots the forgetting curve for a user's cards, showing where actual recall deviates from the model's prediction -- valuable feedback for parameter tuning.

---

## 4. Integration Priority Matrix

| Priority | Feature | Reasoning |
|----------|---------|-----------|
| **High** | py-fsrs native perf | Direct drop-in for fsrs5.py; 10-50x speedup with no API change. Most impactful single upgrade. |
| **High** | Batch scheduling | Eliminates per-card overhead in review sessions. Required for deck-level "review all" UX. |
| **Medium** | SQLModel ORM | Cleaner codebase, type safety, auto-migration. Refactor touches many files but is mechanical. |
| **Medium** | Retention graphs | Valuable for user trust and parameter validation. Requires frontend chart component too. |
| **Low** | Parameter optimization UI | Our optimizer runs offline; a UI for live tuning is nice-to-have but premature with only 50 reviews. |
| **Low** | Same-day review bonus | Already present in FSRS-5 weights (w[18]) but not yet surfaced in UX flow. Needs scheduling logic update. |
