# FSRS参考项目 — 集成方案

> Generated 2026-06-23 | Agent-5 (Lorentz)
> Sources: reference/fsrs_python_system/ + reference/rs-fsrs-python/

---

## 1. 参考项目概述

### 1.1 rs-fsrs-python (Rust PyO3 Binding)

- **定位**: 将 Rust [rs-fsrs](https://github.com/open-spaced-repetition/rs-fsrs) 通过 PyO3 编译为 Python 原生扩展模块
- **性能**: 纯 Rust 实现，比纯Python快 10-50x
- **构建**: maturin (pyproject.toml + Cargo.toml)
- **依赖**: pyo3 0.22.4, fsrs (git), chrono 0.4.38
- **暴露类**: FSRS, Card, Rating, ReviewLog, RecordLog, SchedulingInfo, Parameters

### 1.2 fsrs_python_system (FastAPI Microservice)

- **定位**: 完整 Flash Card 后端服务
- **技术栈**: FastAPI + SQLModel + py-fsrs + PostgreSQL/SQLite + Uvicorn
- **功能**: 用户隔离/UUID安全模型、Deck CRUD、Card CRUD、间隔重复端点
- **API**: /repetition, /next/{deck_id}, /getDecks, /addCard, /editCard, /deleteCard 等

---

## 2. 可直接集成的代码

### 2.1 PyO3接口适配层 (难度: 低)

从 `rs-fsrs-python/src/lib.rs` 提取接口定义，创建适配层：

```python
# pk_radar/core/fsrs5_native.py (新建)
# 如果安装了 rs-fsrs-python 则使用原生Rust，否则fallback到纯Python

try:
    from rs_fsrs_python import FSRS as NativeFSRS, Card, Rating, Parameters
    NATIVE_AVAILABLE = True
except ImportError:
    NATIVE_AVAILABLE = False

class FSRS5Native:
    """FSRS-5 wrapper with optional Rust acceleration"""
    def __init__(self, w=DEFAULT_W):
        if NATIVE_AVAILABLE:
            params = Parameters(
                request_retention=0.9, maximum_interval=36500,
                w=list(w), decay=-0.5, factor=19/81, enable_short_term=True
            )
            self._native = NativeFSRS(params)
        else:
            self._native = None
```

### 2.2 RecordLog批处理模式 (难度: 低)

从Rust接口学习 `RecordLog.get(Rating) → SchedulingInfo` 模式：

```python
# pk_radar/core/fsrs5.py 添加方法
def review_all_ratings(self, card, now=None):
    """一次调用返回所有4个评级的调度结果"""
    results = {}
    for score_label, score in [("again", 0.0), ("hard", 0.4), ("good", 0.7), ("easy", 1.0)]:
        results[score_label] = self.review(card.copy(), score, now)
    return results
```

### 2.3 SQLModel ORM架构 (难度: 中)

从 `fsrs_python_system/main.py` 提取 SQLModel 表定义：

```python
# pk_radar/core/models.py (新建)
from sqlmodel import Field, Session, SQLModel, Column, DateTime, UniqueConstraint, Relationship

class Deck(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("deck_name", "user_uuid"),)
    deck_id: int | None = Field(default=None, primary_key=True)
    user_uuid: str
    deck_name: str
    last_update: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    cards: list["CardModel"] = Relationship(back_populates="deck", cascade_delete=True)

class CardModel(SQLModel, table=True):
    card_id: int | None = Field(default=None, primary_key=True)
    state: int
    stability: float | None
    difficulty: float | None
    due: datetime
    last_review: datetime
    front_content: str
    back_content: str
    deck_id: int = Field(foreign_key="deck.deck_id", ondelete="CASCADE")
    deck: Deck | None = Relationship(back_populates="cards")
```

### 2.4 DTO+安全模式 (难度: 低)

从参考项目学习 UUID安全模型 + Pydantic DTO 模式：

```python
# 每端点统一安全检查
role = request.headers.get("role")
if role not in ("ADMIN", "USER"):
    raise HTTPException(401)
user_uuid = UUID(request.headers.get("uuid"))
# 每个操作都验证所有权
if entity.user_uuid != user_uuid:
    raise HTTPException(403)
```

### 2.5 Auto-Create Default Deck (难度: 低)

```python
# 在 /getDecks 端点中添加
if len(deck_list) == 0:
    createDeck(session, "default", user_uuid)
    deck_list = session.exec(statement).all()
```

### 2.6 Reversed Card Support (难度: 低)

```python
# 创建卡片时支持反向卡片
if request_body.with_reversed:
    dbCardReversed = convertFsrsEntityToDbEntity(card, request_body, reversed=True)
    session.add(dbCardReversed)
```

---

## 3. 集成优先级矩阵

| 优先级 | 功能 | 来源 | 工期 | 风险 | 价值 |
|--------|------|------|------|------|------|
| P0 | Rust性能层 | rs-fsrs-python | 2h | 中(需Rust) | 10-50x |
| P1 | review_all_ratings | rs-fsrs-python | 30min | 低 | 批处理 |
| P1 | Auto-create default deck | fsrs_python_system | 30min | 低 | UX |
| P1 | Reversed card | fsrs_python_system | 30min | 低 | 功能 |
| P2 | SQLModel ORM | fsrs_python_system | 4h | 中 | 类型安全 |
| P2 | UUID安全模式增强 | fsrs_python_system | 1h | 低 | 安全 |
| P3 | SchedulingInfo返回类型 | rs-fsrs-python | 1h | 低 | 代码质量 |
| P4 | 前端to_study计数 | fsrs_python_system | 30min | 低 | UX |

---

## 4. Rust性能层集成步骤

### 前置条件
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh  # 安装Rust
uv pip install maturin
```

### 步骤
```bash
# 1. 将 rs-fsrs-python 加入依赖
cd reference/rs-fsrs-python
maturin develop --release

# 2. 验证
python -c "from rs_fsrs_python import FSRS, Card; print('OK')"

# 3. 运行测试
pytest tests/test_fsrs5.py -v
```

### 回退方案
如果Rust编译失败，保持纯Python实现不变。`fsrs5_native.py` 已设计为自动fallback。

---

## 5. SQLModel ORM迁移步骤

```text
Phase 1: 定义模型 (models.py) - 1h
Phase 2: 替换 store.py 查询 - 2h
Phase 3: 替换 MigrationRunner - 30min
Phase 4: 添加 SessionDep 依赖注入 - 30min
Phase 5: 全量测试 - 30min
```

### 迁移前后对比

| 维度 | 当前(raw sqlite3) | 目标(SQLModel) |
|------|------------------|----------------|
| 查询语法 | 手写SQL字符串 | select().where() |
| 类型安全 | 无 | Pydantic自动验证 |
| 迁移 | 自定义MigrationRunner | SQLModel.metadata.create_all() |
| 关系 | 手动JOIN | Relationship自动加载 |
| IDE支持 | 无 | 完整自动补全 |

---

## 6. 不推荐直接集成的

| 功能 | 原因 |
|------|------|
| PostgreSQL | 当前SQLite够用；换数据库不划算 |
| AutoGen完整框架 | 太重；只吸收Agent分配算法思想 |
| LangGraph完整引入 | 许可证风险+复杂度；自建轻量状态机 |
| Dify/RAGFlow大平台 | 与Knowledge-Base轻量定位冲突 |
