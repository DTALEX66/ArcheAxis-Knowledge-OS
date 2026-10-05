historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# AAOS-01 Q02 改接范围：**宿主运行时模型里根本没有 Core 可执行体**（2026-10-04）

## 1. 根因再收窄一层

`desktop/src-tauri/src/runtime.rs:5-11`：

```rust
pub struct RuntimeSpec {
    pub python: PathBuf,
    pub cwd: PathBuf,
    pub data_dir: PathBuf,
    pub isolated: bool,
    pub external_dev: bool,
    pub profile: &'static str,
}
```

**没有 Core 可执行体字段。** 宿主的运行时模型**只有 Python 解释器**：

- dev：`root/.project-local/build/venv/Scripts/python.exe`（`:102`）
- 安装态：`resource_dir/runtime/python/python.exe`（`:119`）

所以上一轮"宿主把旧 Python 后端当 core 起"**不是一处笔误，而是整个运行时模型就是按 Python 后端设计的**。改接**不是改一行**。

## 2. 改接要动的五处（逐处带依据）

| # | 位置 | 现状 | 依据 |
| --- | --- | --- | --- |
| 1 | `RuntimeSpec` | **没有 Core 路径** | `runtime.rs:5-11` |
| 2 | `runtime_command` | `Command::new(&runtime.python)` | `backend.rs:282` |
| 3 | 启动参数/环境 | `-m app.runtime_entrypoint core` + `ARCHEAXIS_DESKTOP_CONTROL=stdio-v1` + `COGNITIVE_*` 镜像 | `backend.rs:76-88` |
| 4 | 就绪判据 | `wait_for_readiness` / `probe_readiness(port, token)` + `protocol::readiness_payload_valid` —— 针对**旧后端**的载荷 | `backend.rs:360, 390` |
| 5 | 前端契约 | `EXPECTED_API_CONTRACT = "1.x"`、`EXPECTED_PRODUCT_ID = "archeaxis-workspace"` | `frontend/src/api/client.ts` |

**要保留的既有优点**（不该在改接中丢掉）：`choose_loopback_port`（bind 0）、launch token、`Job` 归属、`Drop`/`shutdown_job_owned_child` 清理、`read_bounded_output` 有界读取、`wait_for_exit`。

## 3. 一个**已经对齐**的好消息

宿主在安装态期望 `resource_dir/runtime/python/python.exe`（**嵌套一层 `python`**）。

| | 路径 | 状态 |
| --- | --- | --- |
| 宿主期望 | `<resource>/runtime/python/python.exe` | 源码 `runtime.rs:119` |
| **官方 Green 安装** | `D:\All projects\ArcheAxis.Knowledge.Green-x64\runtime\python\python.exe` | **存在**（此前只读核实过） |
| 我上一包自组的候选 | `<candidate>/runtime/python.exe` | **顶层，少一层** |

**结论**：宿主的期望**与官方 Green 布局一致**；**是我上一包的候选组装少了一层 `python` 目录**。这条属**我先前工作的偏差**，记在此，供 Q13（Windows 安装态）修正 —— 而且它再次说明"我在上一包里的自组候选"不能当作安装态的判据。

## 4. 本轮顺带核实的工具

- `frontend/node_modules` **不存在**；`frontend/package-lock.json` **已跟踪** ✓；
- **`node.exe` 在共用外置工具库中可用**：`10-toolchains\scoop\apps\nodejs-lts\24.18.0\node.exe`。

**所以 frontend 的 16 个 vitest 基线是可跑的**，但需要先按 lockfile 安装依赖（网络 + 时间）。**本轮未执行。**

## 5. 本轮**未**做（不得当成已知）

1. **未安装 frontend 依赖、未跑 vitest** —— 改接前基线**仍缺**；
2. **未读** `job.rs`、`protocol.rs`；`readiness_payload_valid` 具体校验什么**未确定**；
3. **未构建、未运行**；
4. **未改任何实现文件** —— 本提交只新增本文件。

## 6. 下一项（两件事，按序）

1. **取基线**：用工具库的 node 按 `package-lock.json` 装依赖 → 跑 `frontend` 的 16 个 vitest → 记录改接前结果；
2. **改接**：给 `RuntimeSpec` 加 Core 可执行体路径（dev 用构建产物、安装态用 `<resource>/core/archeaxis-api.exe` —— 与我在上一包候选里核实过的 `core\archeaxis-api.exe` 一致），把 `runtime_command` 换成 Core，切换到 **HTTP v2 + 启动声明**，并让就绪判据匹配 Rust Core 的就绪行。**保留 §2 列出的既有优点。**
