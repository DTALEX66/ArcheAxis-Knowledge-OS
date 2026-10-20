# AAOS-01 Q03 **结论落定**：同一个数据库文件里，**两套并行数据模型**

## 1. 决定性证据（两处同值）

```yaml
# config/defaults.yaml:10-13
database:
  path: "data/archeaxis.sqlite"
  journal_mode: "WAL"
  backup_dir: "data/backups"
```

```rust
// desktop/src-tauri/src/backend.rs:303
.env("ARCHEAXIS_DB_PATH", "data/archeaxis.sqlite")
```

而 Python 侧（`shared/storage.py:18-22`）：

```python
def _resolve_database_path() -> Path:
    return resolve_runtime_path(str(config.get("database.path", "data/archeaxis.sqlite")))
DB_PATH = _resolve_database_path()
```

**三处指向同一个 `data/archeaxis.sqlite`。**

## 2. 所以第 17 轮那个分叉有答案了

> 我上一轮写："若**同一文件** → 两套模型共库，**必须先统一**；若不同文件 → 问题是"哪一套 canonical"。"

**答案是：同一个文件。** 因此：

| 事实 | 含义 |
| --- | --- |
| 同一个 SQLite 文件 | 不是"两套独立数据"，而是**一个库里两套 schema** |
| 里面同时有 `anchors`(Rust) · `anchors_v2`(shared) · `evidence_anchors`(Python) · `ir_research_notes` · `ir_intake_cards` … | **一个 canonical 库里并存多套模型** |
| Python 面**会写**这个文件（`INSERT INTO evidence_anchors` / `evidence_bundles_v1` / `index_revisions`） | **写者冲突是真实的，不是假设** |

## 3. Q03 的完整结论（一句话）

> **当前树上，Tauri 前端所依赖的 Python 面与 Rust Core 共用同一个 canonical 数据库文件，

**这正是"该迁移的迁移"必须做的原因 —— 是写者与数据模型的冲突，不是代码风格。**

## 4. 我没有核实的（写清楚，别被当成已知）

1. **Avalonia `CoreSupervisor.cs` 传给 Core 的库路径没查到** —— 我对该文件检索 `sqlite`/`database`/`Arguments` **零命中**，
2. **未实际打开那个库看表** —— 表名来自源码里的 `CREATE TABLE`，**不是从真实库导出的 schema**；
3. **未核** `anchors_v2` 的用途与归属；
4. **未核** `app/workspace/service.py` 是否写（第三轮未做）。

## 5. 下一轮：从"诊断"转向"交付"

Q03 的诊断到此**足够完整**了。继续只读的边际收益已经很低 —— **下一轮起转交付**：

**产出 Q03 的裁决材料（一页）**：
1. **canonical 数据模型的选择**：以 Core 的 `anchors` 为准，还是保留 `evidence_anchors` 形状？（含各自代价）
2. **兼容层的首条可跑切片**：`/api/v1/system/handshake` + `evidence/anchors` 两条**端到端**，作为可回退样板；
3. **明确不做的事**：不动 Rust Core 的 outline 契约、不动前端 119 个绿色用例、不写第二个 canonical。

**这样比第 19 份对比表有用。**
