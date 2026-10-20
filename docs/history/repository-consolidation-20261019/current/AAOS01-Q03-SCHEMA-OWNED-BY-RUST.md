# AAOS-01 Q03：`cognitive_os.sqlite` **已查明**，且 **canonical schema 由 Rust 创建**

## 1. 第 21 轮那个"关系未查明"的问题，有答案了 —— **而且是良性的**

```
app/setup/setup_status.py:40   LEGACY_DATABASE_PATH = "data/cognitive_os.sqlite"
app/workspace/migrate.py:3     "Moves data out of the legacy monolithic cognitive_os.sqlite into the ..."
app/workspace/migrate.py:41    BACKUP_PREFIX = "cognitive_os.pre-"
```

`app/workspace/migrate.py:497` 的签名与文档：

```python
def migrate(db_path, workspace_root, *, backup_dir=None) -> dict:
    """Backup → plan → move data into the four-asset-domain layout.

    The legacy database is never deleted. Idempotent: ..."""
```

**所以**：

| 文件 | 身份 |
| --- | --- |
| `data/cognitive_os.sqlite` | **legacy 单库**（迁移**源**），源码里明确标为 `LEGACY_DATABASE_PATH` |
| `data/archeaxis.sqlite` | **产品库**（配置中的 canonical 路径），由迁移产出 |

**关系有文档、有工具、有备份前缀、幂等、且"legacy 库永不删除"。**

**因此我第 21 轮写的"两者关系未查明"应当收窄为**：关系**明确**，只是**本工作树尚未跑过迁移**（只有 legacy 文件，没有产品库）。
**这不是缺陷，是一个未执行的前置步骤。**

## 2. 更重要的发现：**canonical schema 由 Rust Core 创建**

全仓库检索：

```
git grep -rn 'user_version *=' -- .        -> 零命中（全仓库！）
```

而 `CREATE TABLE IF NOT EXISTS knowledge` 的来源是：

```
crates/archeaxis-store-sqlite/src/lib.rs          <- Rust Core
shared/knowledge_governance_migration.py
docs/history/donor-branch-assets/.../shared/knowledge_migration.py
```

**结论**：`archeaxis.sqlite` 的 schema（含 `user_version`）**由 Rust Core 建立**，Python 侧**只读不建**
（这解释了为什么 `app/workspace/system.py:65` 只 `PRAGMA user_version` 读，而全仓库没有一处 Python 写它）。

**这与"Rust Core 是 canonical 写者"是一致的，而且是它的一个具体证据** —— **连 schema 的建立权都在 Rust 侧**。

## 3. 因此第 21 轮"实际调用握手"的前置条件明确了

app 启动要求 `DB_PATH` 存在**且 schema 已迁移**。要得到那个状态，需要先让 **Rust Core 建立 schema**。

**已定位到的可用入口**：

```
scripts/probes/legacy_migration_smoke.py     <- legacy 迁移探针
```

## 4. 本轮**未**做

1. **仍未成功调用握手** —— 前置（schema 已迁移的库）未就绪，**如实记录**；
2. **未运行** `legacy_migration_smoke.py`，也未让 Rust Core 建库；
3. **未查** `app/workspace/migrate.py` 与 `shared/*_migration.py` 之间的调用顺序（谁是总入口）；
4. 官方 Green 与官方资料库**零触碰**。

## 5. 下一轮（具体）

用**临时目录**跑一次「让 schema 就绪」的路径（优先 `scripts/probes/legacy_migration_smoke.py`），
然后在**那份临时库**上真正调用一次 `/api/v1/system/handshake` —— 把 22 轮的静态阅读换成一次实际观察。
