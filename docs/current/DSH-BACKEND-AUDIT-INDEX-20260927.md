# DSH 后端审计定位索引 — 2026-09-27

> 合并校正：下文交付状态和运行路径为原分支的历史记录，不能证明当前整合
> candidate 已完成真实 M0。`ad89858c` 实际修改了打包器，不是文档-only；
> `DSH-BACKEND-AUDIT-PROMPT-20260927.md` 在主线已 tracked；launcher 由
> backend-20260927 继承，r5 没有首次引入。当前验证与分支处置另见
> `SEPTEMBER-BACKEND-INTEGRATION-20260927.md`。

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
| 打包修复 / 文档提交 | `ad89858c` / `b646ab0e` | 前者修改 stage_backend_runtime.py；后者为文档。不得把整个区间归为文档-only |

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
| 差额表（A–H + M0 26 阶段逐项） | `docs/current/DSH-BACKEND-GAP-MAP-20260927.md`（**在分支上**） |
| 第一轮证据索引 | `docs/current/DSH-BACKEND-EVIDENCE-20260927.json`（在分支上） |
| 第二轮证据索引（含身份不一致实测更正） | `docs/current/DSH-BACKEND-EVIDENCE-R2-20260927.json`（在分支上） |
| 面向 Codex 的合同 | `docs/current/DSH-BACKEND-CONTRACT-20260927.md`（在分支上） |
| 原始运行回执（日志、m0 回执、run env、wheel/安装资质） | `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\dsh-backend-20260927\.project-local\dsh-evidence\` |
| 第三/四轮审计提示词 | `docs/current/DSH-BACKEND-AUDIT-PROMPT-20260927.md`（主线 tracked；并非本整合任务创建） |

> **路径精度说明（此前写得不够准，已更正）**：原始回执位于 **r4 worktree 自己的**
> `.project-local/dsh-evidence/`，而 `.project-local/` 是 **git-ignored**，不在任何分支上；
> 写成相对路径会让检出 r5 的审计者去错目录。因此这里给出绝对路径。
> 审计者若只拿到分支，可复核的是分支内的索引与文档；原始回执需要 Owner 提供副本
> 或在本机核对——这一点是本轮可审计性的真实边界，不是遗漏。

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

---

## 9. 本分支对已冻结分支的更正（审计时必须知道）

`dsh/backend-20260927` 冻结于 `7503195b`，而该提交上 **`scripts/check_language_boundaries.py` 失败（exit 1）**：

```
PROTOCOL_VERSION=1 but the envelope literals are [1, 2]
crates/archeaxis-application/src/scheduler.rs->profile/v2
```

根因是我第三轮新增的 Rust 测试字面量 `"archeaxis.worker-profile/v2"`：该门禁扫描源码中的
`<name>/v<digit>` 协议版本字面量，它被读成同一语言内的第二个 envelope 版本。第三轮加完
scheduler 测试后我只跑了 ruff 与 repository conventions，**没有重跑语言边界门禁**，因此漏掉。
这也意味着第三、四轮报告中"language boundaries 通过"的说法对当时的工作树**不成立**——它来自
更早一次运行。

本分支（`dsh/backend-r5`）把该字面量改为非版本形态的 `"archeaxis.worker-profile/unsupported"`，
保持同一测试意图（错误 schema 必须具名拒绝）。修复后在本分支上实测：

| 门禁 | 结果 |
| --- | --- |
| `scripts/check_language_boundaries.py` | `language boundary check passed …` exit 0 |
| `scripts/check_architecture.py` | `architecture guard passed` |
| `scripts/check_repository_conventions.py --source worktree` | `passed (worktree)` |
| `ruff --select E9,F63,F7,F82` | `All checks passed!` |
| `cargo fmt --all -- --check` | exit 0 |
| `cargo test -p archeaxis-application --lib` | 6 passed / 0 failed（含该用例） |
| `tests/runtime-paths/` | 47 passed / 9 subtests |

冻结分支 `dsh/backend-20260927` **未回改**（保持"已交付即不再改动"），因此它上面的该门禁仍为
失败。是否把这一行修复回植到冻结分支，请 Owner 决定。
