historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# AAOS-01 Q02 核心发现：**Tauri 宿主把旧 Python 后端当 `core` 启动**（2026-10-04）

## 1. 证据（代码，非推断）

`desktop/src-tauri/src/backend.rs:64-105`（正式宿主经 `#[path]` 直接引用此文件）：

```rust
pub fn launch(runtime: &RuntimeSpec) -> Result<Self, String> {
    ...
    run_migration(runtime, &job, Arc::clone(&migration_logs))?;
    let port = choose_loopback_port()?;              // bind 127.0.0.1:0
    let token = launch_token()?;
    let mut command = runtime_command(runtime);      // Command::new(&runtime.python)
    command
        .args(["-m", "app.runtime_entrypoint", "core"])   // <-- 旧 Python 后端
        .env("ARCHEAXIS_HOST", "127.0.0.1")
        .env("ARCHEAXIS_PORT", port.to_string())
        .env("ARCHEAXIS_DESKTOP_CONTROL", "stdio-v1")
        .env("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN", &token)
        .env("ARCHEAXIS_DESKTOP_WRITE_SCOPES", "workspace:write")
        .env("COGNITIVE_HOST", "127.0.0.1")          // legacy mirrors
        ...
    let mut child = command.spawn()...;
    job.assign(&child)...;                            // JobObject 归属
    drain_child_output(&mut child, logs, "core");
    wait_for_readiness(&mut child, port, &token, &logs)...;
```

**它启动的是 `python -m app.runtime_entrypoint core` —— 旧 Python 后端 —— 而不是 Rust `archeaxis-api`。**

## 2. 这与新包**明文冲突**

| 包内原文 | 冲突点 |
| --- | --- |
| 启动提示词：「保留有效 Rust/worker 和历史行为/恢复参考，**不把旧 Python 后端重新接成权威**」 | 宿主正把旧 Python 后端当权威 core 拉起 |
| `00_两包共同架构与交接规则.md`：「**正式业务写入由 Rust Core 执行**」「宿主、前端…不直写 canonical DB」「**Core HTTP v2 与 NDJSON 优先复用**」 | 当前启动的是 stdio-v1 的 Python 后端 |

## 3. 这**同时解释**了上一轮的两个疑点 —— 它们是**同一个根因**

| 上轮疑点 | 本轮的根因 |
| --- | --- |
| `frontend/src/api/client.ts` 期望 `EXPECTED_API_CONTRACT = "1.x"`、`product_id = "archeaxis-workspace"`，而 Rust Core 是 **v2** | 前端是**对着旧 Python 后端的 v1 契约**写的 |
| 「Core 生命周期怎么起的未确定」 | 它起的是 `python -m app.runtime_entrypoint core`，**不是** Rust Core |

**结论**：Tauri 产品壳（前端 + 宿主）**是照旧 Python 后端搭的**。重构要做的"该迁移的"核心内容，正是**把它重新对准 Rust Core**。

## 4. 因此 Q02 / Q03 的真实工作（不是新建，是改接）

1. **Q02**：把 `BackendProcess::launch` 的启动目标从 `python -m app.runtime_entrypoint core` 改为 **Rust `archeaxis-api`**（HTTP v2 + 就绪契约），保留既有优点：`choose_loopback_port`、launch token、JobObject 归属、Drop 清理、**有界输出读取**（`read_bounded_output`）。
2. **Q03**：前端契约由 `1.x`/`archeaxis-workspace` 迁到现行 **Core HTTP v2**，并对齐权限（`WRITE_SCOPE` 与 v2 的 scope 语义）。

**这两项都要先完成包内"共享合同先定归属"** —— 即 v2 契约的 DTO 归属，属于 Q03 的产出。

## 5. 本轮**未**做的（不得当成已知）

1. **没有构建、没有运行**：`cargo` 与 `npm` 本轮都未执行。**"能编、能起"仍未验证。**
2. **没有改任何实现文件**：本提交只新增本文件。**该改接尚未动手。**
3. **未读** `desktop/src-tauri/src/runtime.rs`、`job.rs`、`protocol.rs` 与 `frontend` 的 16 个测试；`RuntimeSpec` 从何而来（决定"启动什么"）**仍未确定**。
4. **未运行** `frontend` 的 `vitest`（16 个测试文件）。

## 6. 下一项

**按依赖顺序，先做 Q02 改接的前置验证**（不是直接改代码）：

1. 读 `desktop/src-tauri/src/runtime.rs` 弄清 `RuntimeSpec` 如何解析（决定 Core 可执行体从哪来）；
2. 跑 `frontend` 的 `vitest`，取得**改接前的基线**；
3. 再谈改接 —— 并保留回退点。
