# DSH 后端审计定位索引 — 2026-09-27

> 用途：让独立审计（A15）**不需要猜**就能定位本轮后端工作的分支、身份、产物与证据。
> 本文件只做定位与状态登记，不是审计结论，也不签发任何资格。
>
> 本文件位于 `docs/current/`，不修改任何 authority index（`DIRECTORY_AUTHORITY_INDEX.md`、
> `RUNTIME_DELIVERY_AUTHORITY_INDEX.md` 等）——那些文件由另一个会话的治理对齐任务在改，
> 本任务不进入。

---

## 1. 分支

| 分支 | 远端 | 作用 |
| --- | --- | --- |
| `dsh/backend-20260927` | 已推送（`7503195b`） | 后端第三轮交付，**已冻结，不再改动** |
| `dsh/backend-r5` | 见 §5 | 独立续接分支；本轮审计定位索引所在分支 |

两者**都是独立分支**，均未合入 `main`。`origin/main` 在本文件撰写时为 `43c2cafa`，
而后端线自 `69a3baed` 分出，**尚未合入主线**。

## 2. 源码身份（必须分开读）

| 身份 | 值 | 说明 |
| --- | --- | --- |
| 授权/任务基线 | `69a3baed13be061f2f8283c6efd4b0e5e80c4d23` | 后端线起点 |
| **runtime_source_commit** | `4017259e` | Core 与 workers 的源码；此后未改运行语义 |
| **packager_source_commit** | `7503195b` | `stage_backend_runtime.py` + `backend_launcher.py` |
| 第三轮 HEAD / tree | `7503195b105b441e53062cc81036fa3916c9c217` / `1a5b2051c66cbb7f68e1da5e5f235143e5c4d9ff` | |
| 文档-only 提交 | `ad89858c`、`b646ab0e` 等 | `ee015075 → b646ab0e` 机械比对：仅 3 个 `docs/current/` 文件，运行相关 diff = 无 |

**不要把 runtime_source 与 packager_source 混成一个 SHA**：前者决定 Core/worker 行为，
后者决定"产物里有哪些组件、依赖复制了哪些、manifest 长什么样"。

## 3. 运行时产物

| 项 | 值 |
| --- | --- |
| 最终 runtime root | `D:\All projects\AAOS-DSH-BACKEND-RUNTIME\7503195b` |
| manifest | `backend-runtime-manifest.json`，sha256 `dc7a240f…`，2786 文件 |
| Core | `core/archeaxis-api.exe`，sha256 `e9a53907…` |
| Python | `runtime/python.exe` 3.13.14（登记的可搬运解释器） |
| workers | `workers/**` + `shared/learning_scheduler.py` |
| 依赖闭包 | `fsrs`、`typing_extensions`、`sqlite_vec`（从已批准本地环境复制，零下载） |
| 正式 launcher | `start-backend.cmd` → `start-backend.py` |

> **可审计性限制**：该 root 在**仓库之外**且未提交。审计者需要本索引给出路径与 hash 才能核对；
> 若需要可交付快照，应由 Owner 决定是否另行打包（当前未做）。

## 4. 证据位置

| 内容 | 位置 |
| --- | --- |
| 差额表（A–H + M0 26 阶段逐项） | `docs/current/DSH-BACKEND-GAP-MAP-20260927.md` |
| 第一轮证据索引 | `docs/current/DSH-BACKEND-EVIDENCE-20260927.json` |
| 第二轮证据索引（含身份不一致实测更正） | `docs/current/DSH-BACKEND-EVIDENCE-R2-20260927.json` |
| 面向 Codex 的合同 | `docs/current/DSH-BACKEND-CONTRACT-20260927.md` |
| 原始运行回执 | `.project-local/dsh-evidence/`（**git-ignored**，仅本机可读） |
| 第三/四轮审计提示词 | `docs/current/DSH-BACKEND-AUDIT-PROMPT-20260927.md`（主检出中为**未跟踪**，本任务未认领、未提交） |

## 5. 本轮新增（`dsh/backend-r5`）

在该分支上新增：

- `scripts/release/backend_launcher.py`：正式 launcher（自解析 runtime root、读 worker-profile、
  生成 launch JSON、启动 Core、等待 ready、具名失败、`--smoke` 首次交换与 shutdown）。
- `scripts/release/stage_backend_runtime.py`：后端运行时暂存 + manifest（runtime/packager 身份分离）。
- `scripts/release/check_runtime_isolation.py`：源码遮蔽/editable 守卫。
- 本文件。

首次推送后，远端引用即为审计入口：
`git ls-remote origin refs/heads/dsh/backend-r5`。

## 6. 可直接复核的结论（附来源）

| 结论 | 证据 |
| --- | --- |
| 正式 launcher 在仓库外、干净环境、含空格数据根、无 `ARCHEAXIS_PYTHON` 下启动成功 | launcher `--smoke` 输出 `ok: true`，`/system/version` 与 `/workspaces/info` 均 200 |
| 失败全部具名，无静默 fallback | profile 缺失/JSON 损坏/schema 不支持/Core 缺失/解释器缺失 → `{"ok": false, "failure": …}` exit 2 |
| Core 从 `worker-profile.json` 解析调度解释器 | `SchedulerClient::from_env` + 3 个 Rust 单元测试；M0 `answer_recorded -> fsrs` |
| 26 阶段 M0 在暂存运行时上通过 | `m0-loop-receipt.json`：`ok/chain/fsrs` 均 true |
| Rust 全 workspace | 243 passed / 0 failed |
| runtime-path + launcher + candidate 测试 | 64 passed / 1 skipped / 0 failed |

## 7. 未完成（审计时请勿误判为已完成）

`IMPLEMENT_NOW` **未清零**：A03 插件运行时内部面、A04 负例集、A05 多格式后端、
A06 Search/vector/rerank/graph 边界与实现、A08–A10 学习/领域/课件生产链、A07 undo/revert、
A11 本地模型池登记读回、migration 业务语义深度、最终候选冻结、最终资格门、
Codex 合同的本轮增量更新、Green 后端集成计划。

`placeholder_ladder → fsrs` 的合同澄清（第四轮 item 四）未做，因此**未改动任何行为**。

这些是普通后端工程任务，**不属于** Owner Decision，也不是资源或授权限制。

## 8. 保持不变的边界

Owner 原库未写；Green 未读写；`apps/**` 零改动；未 push 到 `main`；未删除 stash；
未清理未知文件；四项 Owner Gate（A02 / P0-H01 / DP-F01 / DP-A11-Research）未被扩大。
