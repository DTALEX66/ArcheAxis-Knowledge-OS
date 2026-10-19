# AAOS-01 Q03 裁决提案：**握手字段的逐项差集与归属建议**（2026-10-04）

## 1. Core 实际返回什么（已读实现体，不再是推断）

```rust
// crates/archeaxis-api/src/lib.rs:121-127
async fn system_version() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "runtime": "archeaxis-api",
        "contract": "0.1.0-outline",
        "schema_version": archeaxis_store_sqlite::SCHEMA_VERSION,
    }))
}
```

**只有三个字段。** 注意 `"contract": "0.1.0-outline"` —— **Core 自己把它的合同标为 outline（大纲阶段）**，这是重要的诚实信号：**它还不是稳定契约**。

## 2. 逐项差集（前端 `Handshake` = 10 项）

| 前端要求 | Core 是否提供 |
| --- | --- |
| `schema_version` | ✅ **有** |
| `product_id` | ❌ 无 |
| `product_name` | ❌ 无 |
| `api_contract` | ❌ 无（Core 叫 `contract`，值 `0.1.0-outline`） |
| `backend_version` | ❌ 无 |
| `source_commit` | ❌ 无 |
| `runtime_mode` | ❌ 无 |
| `workspace_id` | ❌ 无 |
| `capabilities` | ❌ 无 |
| `migration_state` | ❌ 无 |

**10 项只对上 1 项**，且命名也不同（`api_contract` vs `contract`）。

## 3. 两个选项与取舍

### 选项 A：**宿主（Tauri）拥有监督者握手**，Core 基本不动 —— **我建议这个**

理由：前端要的多是**宿主/运行时事实**，不是数据库事实：

| 字段 | 本质 |
| --- | --- |
| `product_id` / `product_name` | 产品身份（`docs/truth/NAMING_CONTRACT_V2.md` 锁定） |
| `runtime_mode` / `migration_state` | 宿主进程状态 |
| `workspace_id` | 工作区选择 |
| `source_commit` | 构建身份 |
| `backend_version` | 可由 Core 的 `runtime` + 宿主拼出 |
| `capabilities` | 能力目录（Core **已有** `capabilities.rs` 与 `CAP-*`） |
| `schema_version` | **唯一真正来自 Core 的** |

**做法**：宿主取回 Core 的 `system_version` 后**合成**完整握手交给前端；Core **保持**现有三个字段。

**优点**：① 不为一个 outline 契约**过早冻结 v2 schema**；② 不把宿主状态塞进 canonical 写者；③ 前端判据**一行不用改**；④ 可逆（只加合成层）。

**代价**：握手不再能"只问 Core 一句就拿到"，需要宿主在场。

### 选项 B：**Core 增补全部十项**

**优点**：前端一个请求拿全。

**代价**：① 把 `runtime_mode`/`migration_state`/`workspace_id` 这类**宿主事实**写进 canonical 写者；② Core 自述仍是 `0.1.0-outline`，**增补等于提前冻结**；③ 与"Core 只做业务写入"的分层冲突。

## 4. `packages/contracts/v2/` 的建面时机

**建议：现在不建。** 依据：① Core 自述 `0.1.0-outline`；② 选 A 后要固定的只是**宿主合成的握手形状**，属宿主合同，可在 Q13（安装态）稳定后再上提为跨端 schema；③ 包内要求"最短必要完整架构""不为目录漂亮"，**建一个空 v2 面不是进展**。

## 5. 本轮做与未做

**做了**：读到 `system_version` 的**实现体**（上一轮只是"字段名零命中"），据此给出**逐项差集**与两选项取舍。

**未做**：
1. **未提交任何 schema 文件** —— 所有权未定，**先建 schema 就是先冻结一个未定的决定**；给出的是**提案**；
2. **未改任何实现文件**；
3. **未构建、未运行**（未实际握手一次）；
4. 未读 `frontend/src/__tests__/RuntimeClient.test.ts` —— 若采纳 A，下一步应先读它。

## 6. 需要的一句话

**采纳 A 还是 B？** 若不回答，我将**按 A 推进**（合成层在宿主侧，Core 不动），因为它在"最短必要架构""Core 只做业务写入""不提前冻结 outline 契约"三条上都更稳，且**完全可逆**。
