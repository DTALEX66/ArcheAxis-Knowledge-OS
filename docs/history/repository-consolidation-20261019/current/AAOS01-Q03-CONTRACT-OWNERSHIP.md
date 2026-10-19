# AAOS-01 Q03 第一步：**合同归属已查明 —— 两套握手，谁都不满足对方**（2026-10-04）

## 1. 合同归属的现状（事实）

`packages/contracts/` **已经是合同单源**，schema-first：

| 目录 | schema 数 |
| --- | --- |
| `v1/` | **18** |
| `v2/` | **0（目录不存在）** |
| `bootstrap/v2/` | 1（`launch.schema.json`） |
| `learning/v1/` | 2 |
| `learning/v2/` | 1（`review.schema.json`） |

另有 `compatibility-policy.md`、`protocol-mapping.md`、`errors.catalog.yaml`，以及 **正/负例**（`examples/positive`、`examples/negative`）与生成脚本 `scripts/contracts/generate_vocabulary.py`。

## 2. **关键**：`/api/v1` 不是合同大版本

`packages/contracts/v1/compatibility-policy.md` 原文：

> "`/api/v1` and schema names ending in `/v1` identify the major version only. API, worker protocol, database schema and export format version **independently**."

**所以我此前把前端的 `EXPECTED_API_CONTRACT = "1.x"` 直接说成"与 Core v2 错配"是不准确的** —— 路径 major 与 schema 版本本就各自独立。**这一点我在此更正措辞。**

## 3. 但错配**确实存在**，而且原因比我先前说的更硬

```
frontend/src/api/client.ts
  24: const EXPECTED_PRODUCT_ID   = "archeaxis-workspace";
  25: const EXPECTED_API_CONTRACT = "1.x";
  79:  if (handshake.product_id   !== EXPECTED_PRODUCT_ID)   incompatible("product mismatch…");
  81:  if (handshake.api_contract !== EXPECTED_API_CONTRACT) incompatible("API contract mismatch…");
  90:  if (!Number.isInteger(handshake.schema_version) …)
  93:  if (!Array.isArray(handshake.capabilities) …)
  99:  if (handshake.migration_state !== "ready") …
```

**而 `product_id` / `api_contract` / `migration_state` 这些字段名在整个 `crates/archeaxis-api/src` 里零命中。**

（校准：同一检索方式下 `system/version` 在 Core 里有命中，说明检索有效，不是"搜不到任何东西"。）

## 4. 决定性的一句：**Core 自己说它的握手对象是 Avalonia**

```rust
// crates/archeaxis-api/src/main.rs:7-9
//! Serves the vNext local HTTP API on 127.0.0.1 — the handshake target for the
//! Avalonia Supervisor (sidecar-protocol versioned envelope is the message
//! contract; /api/v1/system/version is the first exchange).
```

**所以现状是两套握手，谁都不满足对方：**

| 一方 | 期望 | 现实 |
| --- | --- | --- |
| **Rust Core** | 由 **Avalonia Supervisor** 驱动，`/api/v1/system/version` 首次交换 | Avalonia 正是**要被替换**的宿主 |
| **Tauri 前端** | `product_id="archeaxis-workspace"`、`api_contract="1.x"`、`migration_state="ready"`… | 这些字段**由旧 Python 后端提供**，Rust Core 不产出 |

**这就是"该迁移的"最核心的内容**：让 Tauri 前端与 Rust Core **说同一套话**。

## 5. 因此包内"共享合同先定归属"的顺序是对的

Q03 **必须**先于 Q02 的改接：改接（把启动目标换成 Rust Core）会让 Tauri 前端在握手处直接判定 `incompatible` 并拒绝 —— **除非合同先统一**。

**Q03 的产出因此明确为**：

1. 决定 **v2 合同面**的归属与生成方式（`packages/contracts/v2/` 目前**不存在**，需建面或明确 v1 面继续有效）；
2. 决定握手字段（`product_id` / `api_contract` / `migration_state` / `capabilities` …）**由谁产出**：Core 增补，还是 Tauri 前端改判据；
3. 把结果登记进 Authority delta，**保留正/负例与 `errors.catalog.yaml` 的既有做法**。

## 6. 本轮**未**做（不得当成已知）

1. **没有读** `system_version` 的实现体 —— 我核到的是"**这些字段名在 Core 源码里零命中**"，**不是**"我已逐字段读过响应"；
2. **未构建、未运行**（未实际握手一次）；
3. **未改任何实现文件** —— 本提交只新增本文件；
4. 前端 16/119 基线与本轮的合同结论**无关**，未重跑（本轮无代码改动）。
