# AAOS-01：Core 打不开旧 Python 库 —— 迁移缺口的完整规格（2026-10-05）

## 1. 现象
```
旧数据根副本     → Core 退出: "failed to open workspace"
全新空目录       → Core 就绪并存活 ✓
```
**真实产品数据根全程只读**（只复制到临时目录观察）。

## 2. 两条错误来自两个函数（`crates/archeaxis-api/src/main.rs:213-246`）
```rust
if let Some(profile) = &launch.text_worker {
    Executor::open_routes(db, &profile.staging, &profile.python, &profile.script, &extra)
        .map_err(|| "failed to initialize execution workspace")   // 应用走的这条（declares text_worker）
} else {
    Store::open(db).map_err(|| "failed to open workspace")        // 直跑走的这条（无 text_worker）
}
```

## 3. 确切原因：旧库没有 Core 要的元数据表
**Core 读**（`crates/archeaxis-store-sqlite/src/lib.rs:249/281/393`）：
```sql
SELECT value FROM workspace_meta WHERE key='schema_version'
```
**旧库实际**：
```
user_version   = 0
application_id = 0
journal_mode   = delete
tables (98)    = a_to_b_candidates, anchors_v2, …, evidence_anchors, episodic_memory,
                 episodic_memory_fts*, execution_traces, …   ← 无 workspace_meta
```

## 4. 因此 adapter / 迁移的最小规格

| | 旧（Python 产品） | 新（Core） |
| --- | --- | --- |
| 元数据 | 无 `workspace_meta` | `workspace_meta(key,value)` 含 `schema_version` |
| journal | `delete` | WAL |
| 规模 | 98 表（`evidence_anchors`、FTS 表等） | Core schema |

**两条可选路径（待产品选择，本清单不选定）**：
1. **迁移**：把 98 表旧库升到 Core schema（**需定义 `evidence_anchors` → Core 对象的映射语义**，即 §四B 的 adapter）；
2. **只读接入**：Core 用新库；旧库作为 legacy 输入**只读**接入（**不动旧数据，风险低，但需新库指针与来源标记**）。

## 5. 本轮不声称
- **未选定路径**（涉及数据语义，属产品决定）；
- **未写任何迁移代码**；
- **未改动真实数据根**。
