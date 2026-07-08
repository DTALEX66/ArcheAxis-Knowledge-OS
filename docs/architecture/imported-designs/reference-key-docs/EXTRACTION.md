# Reference Project Extraction Report

> Generated 2026-06-23 | Agent-5 (Lorentz) — FSRS Optimizer + Reference Integration

---

## 1. rs-fsrs-python (Rust PyO3 Binding)

### Source Files Examined

| File | Purpose |
|------|---------|
| `src/lib.rs` | PyO3 Rust bindings: wraps `fsrs::FSRS`, `Card`, `Rating`, `ReviewLog`, `RecordLog`, `SchedulingInfo` |
| `Cargo.toml` | Deps: pyo3 0.22.4, fsrs (git rs-fsrs), chrono 0.4.38 |
| `pyproject.toml` | Build system: maturin >=1.7; package name `rs-fsrs-python` |
| `README.md` | Usage example, test instructions (`maturin develop && python tests/test.py`) |

### Extracted Components

#### A. PyO3 Class Definitions (src/lib.rs)

```rust
#[pyclass] struct FSRS(fsrs::FSRS);          // Scheduler wrapper
#[pyclass] struct Parameters { ... }          // 19-param weight config + decay/factor
#[pyclass] struct Card(fsrs::Card);           // Card state (difficulty, stability, due, reps)
#[pyclass] enum Rating { Again, Hard, Good, Easy }
#[pyclass] struct RecordLog(fsrs::RecordLog); // Review result for all 4 ratings
#[pyclass] struct SchedulingInfo(...);        // (Card, ReviewLog) pair per rating
```

**Key API:**
- `FSRS(parameters).repeat(card, now) -> RecordLog` — batch review for all 4 ratings
- `RecordLog.get(Rating) -> SchedulingInfo` — retrieve scheduling result per rating
- `Card` getters: `difficulty`, `stability`, `elapsed_days`, `due`, `scheduled_days`, `reps`, `last_review`

#### B. Parameters Structure

```rust
pub struct Parameters {
    pub request_retention: f64,   // default 0.9
    pub maximum_interval: i32,    // default 36500
    pub w: [f64; 19],             // FSRS-5 weights
    pub decay: f64,               // default -0.5
    pub factor: f64,              // default 19/81
    pub enable_short_term: bool,  // default true
}
```

#### C. Build Integration Pattern

```toml
# pyproject.toml
[build-system]
requires = ["maturin>=1.7,<2.0"]
build-backend = "maturin"

# Cargo.toml
[dependencies]
pyo3 = { version = "0.22.4", features = ["chrono"] }
fsrs = { git = "https://github.com/open-spaced-repetition/rs-fsrs", rev = "5e6d336" }
```

### Integration Status

| Component | Status | Notes |
|-----------|--------|-------|
| FSRS-5 algorithm | ✅ Integrated | Pure Python port in `pk_radar/core/fsrs5.py` |
| 19-parameter weights | ✅ Integrated | `DEFAULT_W` tuple, optimized via `fsrs_optimizer.py` |
| Rust native performance | ❌ Pending | 10-50x speedup; requires maturin build chain |
| `RecordLog` batch API | ❌ Pending | All-4-ratings-at-once pattern not in our code |
| `SchedulingInfo` struct | ❌ Pending | Would simplify card+log return types |

---

## 2. fsrs_python_system (FastAPI Microservice)

### Source Files Examined

| File | Purpose |
|------|---------|
| `main.py` | Full FastAPI app with SQLModel ORM, CRUD endpoints, FSRS integration |
| `README.md` | Architecture overview, API flow description |

### Extracted Components

#### A. SQLModel Database Schema

```python
# Deck entity — user-scoped card collections
class Deck(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("deck_name", "user_uuid", name="deck_name_uuid"),)
    deck_id: int | None = Field(default=None, primary_key=True)
    user_uuid: UUID
    deck_name: str
    last_update: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    cards: list["DatabaseCard"] = Relationship(back_populates="deck", cascade_delete=True)

# Card entity — FSRS state + content
class DatabaseCard(SQLModel, table=True):
    card_id: int | None = Field(default=None, primary_key=True)
    state: int                 # FSRS state enum (0=new, 1=learning, 2=review, 3=relearning)
    step: int | None
    stability: float | None
    difficulty: float | None
    due: datetime              # Next review deadline
    last_review: datetime      # Last review timestamp
    front_content: str
    back_content: str
    deck_id: int = Field(foreign_key="deck.deck_id", ondelete="CASCADE")
    deck: Deck | None = Relationship(back_populates="cards")
```

#### B. DTO Pattern (Pydantic Models)

```python
class RatedCard(BaseModel):       # POST /repetition request
    card_id: int
    rating: str                    # "Again"|"Hard"|"Good"

class BackendAnswerCard(BaseModel): # GET /next/{deck_id} response
    card_id: int | None
    front_content: str | None
    back_content: str | None
    deck_id: int | None

class NewCard(BaseModel):          # POST /addCard request
    front_content: str
    back_content: str
    with_reversed: bool
    deck_id: int

class DeckDTO(BaseModel):          # GET /getDecks response
    deck_id: int
    deck_name: str
    to_study: int | None           # Cards due for review
    cards_amount: int | None       # Total cards in deck
```

#### C. API Endpoint Patterns

| Endpoint | Method | Pattern |
|----------|--------|---------|
| `/getDecks` | GET | User-scoped deck list with `to_study` count; auto-creates default deck |
| `/addDeck` | POST | Validates uniqueness per user, creates with `createDeck()` |
| `/deleteDeck` | POST | Ownership check via `user_uuid`, cascade deletes cards |
| `/addCard` | POST | Creates card via FSRS scheduler, supports reversed cards |
| `/editCard` | POST | Content-only edit after ownership check |
| `/getCard` | GET | Single card fetch by ID with ownership gate |
| `/deleteCard` | POST | Ownership check via `card.deck.user_uuid` chain |
| `/next/{deck_id}` | GET | Iterates deck cards, returns first with `due < now` |
| `/repetition` | POST | Core: FSRS review + state persistence |

#### D. Security Pattern

```python
# Role check on every endpoint
role = request.headers.get("role")
if role != "ADMIN" and role != "USER":
    raise HTTPException(status_code=401)

# User isolation via UUID header
user_uuid = UUID(request.headers.get("uuid"))
# Ownership verified on every mutation
if entity.user_uuid != user_uuid:
    raise HTTPException(status_code=403)
```

#### E. FSRS Integration Pattern

```python
def convertDbEntityToFsrsCardAndMakeReview(dbCard, rating):
    scheduler = Scheduler()
    card = Card()
    card.state = State(dbCard.state)
    card.stability = dbCard.stability
    card.difficulty = dbCard.difficulty
    card.last_review = dbCard.last_review
    # Map string rating to enum
    ratingEnum = {"Again": Rating.Again, "Hard": Rating.Hard, "Good": Rating.Good}.get(rating, Rating.Easy)
    card, review_log = scheduler.review_card(card, ratingEnum)
    # Write back to DB entity
    dbCard.state = card.state.value
    dbCard.stability = card.stability
    dbCard.difficulty = card.difficulty
    dbCard.due = card.due
    dbCard.last_review = card.last_review
    return dbCard
```

### Integration Status

| Component | Status | Notes |
|-----------|--------|-------|
| REST API CRUD | ✅ Integrated | Our FastAPI app has equivalent review/card/deck endpoints |
| SQLModel ORM | ❌ Pending | We use raw sqlite3; SQLModel would give type safety + auto-migration |
| Deck ownership | ✅ Integrated | UUID-based isolation pattern already in our API |
| DTO pattern | ✅ Integrated | Pydantic BaseModel used for request/response |
| Auto-create default deck | ❌ Pending | Nice UX touch when first deck list is empty |
| Reversed card support | ❌ Pending | Creates front/back-flipped duplicate card |
| `to_study` count | ❌ Pending | Real-time count of due cards per deck |

---

## 3. Integration Priority & Difficulty Matrix

| # | Feature | Source | Difficulty | Rationale |
|---|---------|--------|------------|-----------|
| 1 | Rust py-fsrs binding | rs-fsrs-python | **Hard** | Requires Rust toolchain + maturin build in CI; 50-line shim in Python |
| 2 | SQLModel ORM migration | fsrs_python_system | **Medium** | Mechanical refactor of `store.py`; ~15 tables; preserves existing API |
| 3 | RecordLog batch API | rs-fsrs-python | **Easy** | Add `review_all_ratings()` wrapper returning dict of 4 results |
| 4 | `to_study` deck count | fsrs_python_system | **Easy** | Single SQL query per deck; add to `DeckDTO` |
| 5 | Auto-create default deck | fsrs_python_system | **Easy** | 5-line check in `getDecks` endpoint |
| 6 | Reversed card creation | fsrs_python_system | **Easy** | Clone card with swapped front/back |
| 7 | SchedulingInfo return type | rs-fsrs-python | **Easy** | Dataclass wrapping (Card, ReviewLog) tuple |
| 8 | Database migration runner | fsrs_python_system | **Easy** | Replace `migrations.py` with SQLModel `create_all` |

---

## 4. Quick-Start Integration Paths

### Path A: Drop-in Rust Performance (1-2 hours)

```
1. Install Rust toolchain: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
2. Add rs-fsrs-python as git dependency in pyproject.toml
3. Create pk_radar/core/fsrs5_native.py shim:
   from rs_fsrs_python import FSRS, Card, Rating, Parameters
   class FSRS5Native:
       def review(self, card, score): ...
4. Run: uv pip install maturin && maturin develop --manifest-path reference/rs-fsrs-python/Cargo.toml
```

### Path B: SQLModel ORM (3-4 hours)

```
1. Add sqlmodel to pyproject.toml dependencies
2. Define SQLModel classes in pk_radar/core/models.py
3. Migrate store.py queries from raw SQL to SQLModel select()
4. Replace MigrationRunner with SQLModel.metadata.create_all()
5. Add SessionDep dependency injection pattern
```

### Path C: Quick Wins (30 min each)

- Add `to_study` field to deck list response
- Auto-create "default" deck on first access
- Support `with_reversed` flag in card creation
- Add `review_all_ratings()` returning dict of 4 scheduling results
