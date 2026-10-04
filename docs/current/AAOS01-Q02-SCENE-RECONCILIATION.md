# AAOS-01 Q02 现场核对与 **Q01 结论更正**（2026-10-04）

## 0. 更正：Q01 里「`desktop/` 是分离的 Recovery Shell，不合并」**说错了一半**

Q01 我据两个 `tauri.conf.json` 的 `productName`/`identifier` 不同，判定 `desktop/` 是**刻意分离**的恢复壳、**不合并**。本轮读 `src-tauri/src/main.rs` 发现：

```rust
// src-tauri/src/main.rs:248-258
#[path = "../../desktop/src-tauri/src/backend.rs"] mod backend;
#[path = "../../desktop/src-tauri/src/job.rs"]     mod job;
#[path = "../../desktop/src-tauri/src/protocol.rs"] mod protocol;
#[path = "../../desktop/src-tauri/src/runtime.rs"] mod runtime;
```

**正式宿主 `src-tauri` 直接用 `#[path]` 引用 `desktop/src-tauri/src/` 的源码。** 也就是说：

- **两个 manifest 是两份**（product / recovery）—— 这一点我 Q01 说对了；
- **但 Rust 实现是共享的**，`desktop/src-tauri/src/` 是**正式宿主的承重源码**，不是可自由冻结/删除的旁支。

**所以「该冻结的冻结」必须排除它**：冻结或清理 `desktop/src-tauri/src/` 会**直接打断 `src-tauri` 的编译**。同时「该合并的合并」在这里的答案是：**已经通过 `#[path]` 事实上合并了，没有可合并的重复品**。

**我 Q01 的措辞会让执行者去"保留两个独立实现"，那是错的。** 记录在此，并保留 Q01 文件不改（可追溯我在何时基于什么更正）。

## 1. Q02 核对到的既有实现（**不是空的**）

| 组件 | 事实 |
| --- | --- |
| 前端 | `frontend/src/` **45 个追踪文件**：`app/App.tsx`、`main.tsx`、**9 个 space**（Workspace/Vault/Library/Intake/Evidence/Learning/Exchange/AiAssets/Settings）、`api/{client,learning,workspace}.ts`、10 个 components、`runtime/recovery.ts`、**16 个测试文件** |
| Tauri 宿主 | `src-tauri/`：`Cargo.toml`（package `archeaxis-desktop`，bin **`ArcheAxis`**，`tauri =2.11.5`，`windows` Win32 **JobObjects**/Security/Threading）；`main.rs` 871 行 |
| 命令面 | **7 个 `#[tauri::command]`**：`backend_info`、`recovery_status`、`recovery_log_tail`、`enter_safe_mode`、`retry_backend`、`restore_backup`、`exit_application` |
| Core 生命周期 | 宿主持有 `process: Arc<Mutex<Option<BackendProcess>>>`（`desktop/src-tauri/src/backend.rs`），退出路径有 `cleanup_backend_on_exit` / `exit_application` |
| 前端↔Core | **前端不调用那 7 个命令**；`api/client.ts` 是"**唯一带凭据的 HTTP 客户端**"，直接对 Core HTTP 说话，含 `Handshake`、`RuntimeProjection`（offline/backend_starting/migrating/incompatible/unauthorized/unavailable）、`WRITE_SCOPE` |
| CSP | `connect-src 'self' http://127.0.0.1:*` —— 与"前端直连 Core HTTP"一致 |

**结论**：Q02 的"Tauri 启动与只读桥接"**已有大量实现**（宿主 + 后端进程管理 + 前端 HTTP 客户端 + 9 个 space）。按包内"已存在且合格的实现直接复用，只修缺口"，**Q02 不是从零搭**。

## 2. 本轮**发现但未解决**的疑点（写下来，不当作已解决）

1. **契约版本不一致**：`frontend/src/api/client.ts` 里 `EXPECTED_API_CONTRACT = "1.x"`、`EXPECTED_PRODUCT_ID = "archeaxis-workspace"`，而本仓库现行 Core 是 **HTTP contract v2**。**是否是真错配、还是 v1 客户端对 v2 Core 的兼容约定，我没有核**，因此只登记为疑点。这条直接落在 **Q03（类型合同与权限）**。
2. **没有构建、没有运行**：本轮**未执行** `cargo` 或 `npm`，所以"它能编、能起"**未验证**。`src-tauri` 依赖 `#[path]` 的四个 `desktop` 文件，路径是否正确、能否编译，**本轮没有验证**。
3. **未读** `desktop/src-tauri/src/{backend,runtime,job,protocol}.rs` 的内容，因此"**Core 生命周期到底怎么起的**"（谁、什么参数、什么就绪判据）**仍未确定**。
4. `frontend/src/__tests__` 有 16 个测试文件，**本轮未运行**（`vitest` 未执行）。

## 3. 下一项（Q02 的实际工作）

按依赖 Q02 依赖 Q01 ✓（且已更正），下一步是**验证而非新建**：

1. 读 `desktop/src-tauri/src/backend.rs` 确定 Core 启动契约（命令、参数、就绪判据、退出清理）；
2. 跑 `frontend` 的 `vitest`（已有 16 个测试）；
3. 尝试 `cargo check` `src-tauri`（验证 `#[path]` 四个文件与编译）；
4. 只有以上三项有结果后，才谈"实际 Core 生命周期和资料列表"是否达标 —— **表格初始 NOT_RUN，不预填 PASS**。
