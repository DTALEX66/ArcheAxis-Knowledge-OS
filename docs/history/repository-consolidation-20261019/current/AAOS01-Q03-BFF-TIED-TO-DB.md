# AAOS-01 Q03 **结论**：BFF **直接绑库、不是代理** → C 不能"换源"，且当前接线有**单写者冲突**

## 1. 决定性证据

`app/workspace/router.py` 的导入把答案写在第一屏：

```python
from app.evidence.anchor import (EvidenceAnchor, build_evidence_anchor,
    list_evidence_anchor_page, resolve_evidence_anchor, store_evidence_anchor)
from app.evidence.ledger import (EvidenceBundleError, get_bundle_inspection, list_bundle_summaries)
from app.workspace import bff, service, vault
from shared.storage import DB_PATH          # <-- 数据库路径
```

我第 15 轮在 `router.py` 里搜不到 `sqlite3.connect`，**因为连接在它导入的模块里**。查那些模块：

```
app/evidence/anchor.py:87    with sqlite3.connect(Path(db)) as connection:
app/evidence/anchor.py:117       "INSERT INTO evidence_anchors "
app/evidence/anchor.py:238       "INSERT OR REPLACE INTO index_revisions "
app/evidence/anchor.py:267       "UPDATE index_revisions SET source_revision=?...");
app/evidence/ledger.py:169       "INSERT INTO evidence_bundles_v1 (...) "
app/evidence/ledger.py:175       "INSERT INTO evidence_bundle_entries_v1 "
app/evidence/ledger.py:329       "INSERT INTO evidence_bundle_reviews_v1 "
app/workspace/service.py:402    with sqlite3.connect(database, timeout=30.0) as connection:
shared/storage.py:22            DB_PATH = _resolve_database_path()
```

## 2. 因此三件事确定

### (a) BFF **不是**对 Core 的代理，而是**直接绑 SQLite**

它的**契约文档**（`WORKSPACE_BFF_V1.md`）可复用 ✓；它的**实现**不可复用 ❌ —— 要成为兼容层，**必须新写成对着 Core HTTP 的投影**，不能"换源"。

**这否掉了我第 15 轮"工作主要是把它对准 Rust Core"的乐观表述。**

### (b) 当前接线存在**单写者冲突**

`router.py` 的导入面里**有会写的模块**（`store_evidence_anchor`、evidence bundles 的 INSERT）。所以：

- 契约说 v1 面 **GET only**，**但路由所在的整套面会写**；
- 若 Tauri 宿主同时跑 **Rust Core（唯一写者）**，就出现 **两个写者对同一个 `DB_PATH`**。

这正是包内禁止的："**同文件一个 writer**"、"宿主、前端、worker…**不直写 canonical DB**"、"**不改…双写旧新库**"。

**这才是"改接"必须做的真正理由 —— 不是风格问题，是写者冲突。**

### (c) 一个**已标记但未查**的schema 疑点

| 栈 | 表名 |
| --- | --- |
| Python 写 | **`evidence_anchors`** |
| Rust Core 读 | **`anchors`**（`FROM anchors a JOIN sources s`） |

**表名不同** → 可能同一 schema 里两张表，**也可能两套栈用了不同 schema/库**。**我没有查，所以只标记，不下结论。**

## 3. 我的估算第五次修正（并说明为什么老在改）

| 轮次 | 估计 | 依据 |
| --- | --- | --- |
| 11 | ~75 条映射 | 只数路径 |
| 12 | 61 条都要覆盖 | 零重叠 |
| 13 | 部分可能是别名 | 按名字 |
| 14 | 上调 | 核 1 条载荷 |
| 15 | 下调（BFF 已存在） | 契约 + 零写者（**当时搜错文件**） |
| **16** | **C = 新写一个对着 Core HTTP 的投影层；契约文档可复用、实现不可复用** | **查出连接在导入模块里** |

**五次修正，根因是同一个**：我在调研做深之前就先估了。**这条纪律要写成教训**：
> **没有查明数据来源归属之前，不要给"迁移成本"下数字。**

## 4. 下一轮

**先查 §2(c) 的表名疑点**（`evidence_anchors` vs `anchors`）—— 它决定 C 是"投影到 Core HTTP"还是"连 schema 都要统一"。

## 5. 本轮**未**做

1. **未改任何实现文件**；未建 schema；未写适配层；未构建未运行；
2. **未查** `evidence_anchors` vs `anchors` 的表名差异（§2c）；
3. **未查**`app/workspace/service.py` 是否也写（只看到 `sqlite3.connect`，**未逐条看它是否 INSERT/UPDATE**）；
4. **仍未读完** `RuntimeClient.test.ts`（**连续第四轮欠账**）。
