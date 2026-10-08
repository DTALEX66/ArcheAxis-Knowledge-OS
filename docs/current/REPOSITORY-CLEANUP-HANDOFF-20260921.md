# ArcheAxis 仓库整理、瘦身与交接报告（2026-09-21）

> **HISTORICAL HANDOFF / NOT CURRENT GIT OR RUNTIME TRUTH.** This document is
> preserved for the 2026-09-21 cleanup evidence. Its branch, HEAD, remote and
> working-tree values are dated snapshots. Use
> `REPOSITORY-DRIFT-CURRENT-RECEIPT-20260923.md` for current readback. The
> exact cleanup receipt and deleted-path evidence remain valid within their
> recorded scope.

## 当前结论

本轮完成了一次只读边界审计、项目内输出溢出追踪，以及一组有明确归属且可再生的构建/候选产物清理。未读取、修改或删除 `E:\`、`F:\`、`.codex`、`.zcode`、`.hermes`、凭据、外置共享库、真实资料库、测试资料库或现有 Green 运行目录。

清理收据为 `.project-local/audits/cleanup-receipt-20260921.json`。收据记录 28 个精确路径、全部删除成功、删除前 8,361,939,708 bytes、删除后剩余 0 bytes、错误 0、残留路径 0。删除对象只属于项目内的旧 Green 候选重复包和不再被当前证据引用的中间构建输出。

## Git 与上传状态

| 项目 | 当前值 |
| --- | --- |
| 分支 | `main` |
| `HEAD` | `42d5660c1b5f36b6f13445ea5fe631662cd75047` |
| 本地 `origin/main` | `42d5660c1b5f36b6f13445ea5fe631662cd75047` |
| `HEAD...origin/main` | `0 0` |
| 跟踪文件修改 | 本轮报告提交前为 0 |
| 未跟踪项 | `docs/history/` 迁移资产及 `SESSION-RESTART-2026-09-12.md`，全部保留、未纳入本轮提交 |

本轮先遇到 SSH `known_hosts` 读取权限问题，随后在授权的推送环境中完成上传。最终 `git ls-remote origin refs/heads/main` 返回 `42d5660c1b5f36b6f13445ea5fe631662cd75047`，与本地 `HEAD` 和 `origin/main` 完全一致；`HEAD...origin/main` 为 `0 0`。远端仍提示 required status check `a0-gates` expected，这是分支保护提示，不是本次提交内容的测试通过证明。

## 瘦身范围

### 已删除的旧 Green 候选重复包

以下路径均位于 `.project-local/build/green-candidates/`：

- `ArcheAxis.Knowledge.Green-vclean-archive70226a42-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vclean-core59f6419b-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vlocal-dirty-20260918-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vclean-52fb1d41-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vclean-59f6419b-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vclean-8e2c59be-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vclean-d88c06b4-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vlocal-20260918-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vheadb8bbd16b-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vhead736d20a7-x64.zip`

这是与既有候选存储审计中“保留 `vheadd1bb2b99` 与 `vclean-fc05b0ad`、删除九组旧副本”一致的精确执行。保留项为：

- `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vheadd1bb2b99-x64` 及 `.zip`
- `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vclean-fc05b0ad-x64` 及 `.zip`
- `.project-local/build/green-candidates-r6/` 下的三组 R6 候选及其 ZIP

### 已删除的中间构建输出

- `.project-local/build/cargo-a04-20260921`
- `.project-local/build/cargo-r6-p5-audit`
- `.project-local/build/cargo-r6-domain-fix`
- `.project-local/build/cargo-r6-domain`
- `.project-local/build/cargo-r6-api-direct2`
- `.project-local/build/cargo-r6-api-direct`
- `.project-local/build/cargo-r6-api-check-direct`
- `.project-local/build/cargo-check-dsh`
- `.project-local/build/asr-sherpa-venv`

这些目录没有被当前受跟踪代码或当前 R6 证据索引作为继续运行所需的唯一输入引用，均可由项目入口重新生成。保留 `.project-local/build/cargo` 主目标、`cargo-r6-p4`、`cargo-r6-api-sdk2`、`cargo-r6-api-fix`、`rust-msvc`、`cargo-r6-a12`、`cargo-current-452b5d0c`、`desktop-publish` 和 R6 候选，因为它们仍出现在当前运行收据或历史证据路径中。

## 体积与外溢审计

只读盘点 `inventory_project.py` 的结果是 `status=partial`：全项目观测 47,725,293,678 bytes、295,772 文件、229 个读取错误、26 个 reparse 跳过、883 个排除项；`.project-local` 观测 44,251,819,839 bytes、261,525 文件。该工具明确把私有/opaque 目录作为不可归因项，不能把它们计入“已清理”。

本轮清理后的 PowerShell 快照显示 `.project-local` 约 31,705,314,672 bytes；这与前一工具的排除规则和时间点不同，不能直接相减归因。唯一可归因的回收量以精确清理收据为准：8,361,939,708 bytes。

`trace_output_producers.py` 产出 1,178 条静态输出路径/变量候选，报告模式为 `read_only_structural_candidates`。它只证明源码和脚本中存在输出意图，不证明运行时已经写入外部目录；进程命令行、日志和私有运行态没有读取。`check_resource_boundaries.py` 退出 0，并确认索引中的五个固定资源路径：Model library、OS External Configuration、ArcheAxis.Knowledge.Green-x64、资料库、ceshi。该检查只读取路径元数据，没有扫描这些库内容。

## 已完成验证与已知限制

- A04 当前提交的 Rust 定向测试：8 passed，退出码 0；包含 `knowledge_v3_projection`、`v01_journey`、`api_closed_loop`。
- `git diff --check` 在生成本报告前无输出。
- 权威 SHA 与 R6 authority 检查在 `9ca805b6` 提交时已通过；本轮尝试重跑时，项目 `.venv\Scripts\python.exe` 是 uv trampoline，进程被权限策略拒绝（`permission denied (os error 5)`），因此本轮重跑状态为 `NOT_EXECUTED`，没有把旧 PASS 冒充成新 PASS。
- 当前 PowerShell 会话的 `python` 不在 PATH；没有安装新解释器，也没有改全局环境。后续应使用已登记的项目解释器或修复执行权限后再跑门禁。
- 推送已完成，远端精确 SHA 回读通过；远端返回的 `a0-gates` expected 规则提示仍需按云端流程补齐检查，不能把推送当成 CI PASS。

## 未完成任务与阻塞

- R6/M0 的 owner-gated 协议与宿主决策仍未闭合；A02/A16 不能由执行者自签。
- A05–A15 仍是部分完成，M0 P3 的真实 Core/桌面 journey 仍受当前二进制与源码契约不一致阻塞。
- R13 的安装器、代码签名、卸载器和干净机器验收仍未完成；候选包不等于正式 Green 发布。
- R14/R16 独立审计仍必须由独立 GPT 按证据逐项裁决，不能使用执行者收据自签通过。
- 未跟踪的 `docs/history/` 迁移资产和私有会话提示未获得逐项入库授权，故本轮保留且不上传。

## 交接与精确提交范围

本报告是唯一计划提交的跟踪文件：

`docs/current/REPOSITORY-CLEANUP-HANDOFF-20260921.md`

`.project-local/audits/` 下的原始盘点、外溢候选、资源边界、低额度监控和清理收据是项目内忽略的运行证据，不随提交上传；报告已记录其精确文件名、统计和限制，供本机复核。

下一位执行者应按以下顺序继续：

1. 先修复项目 Python 入口的权限/解释器发现，再重跑 authority SHA、R6 authority 和必要的定向门禁。
2. 重新尝试 `git ls-remote` 或使用已批准的 HTTPS 远端完成精确 SHA 回读；成功后才报告双端一致。
3. 处理 R6/M0 owner-gated 决策和独立审计，不扩大清理范围。
4. 若再次瘦身，只能引用新的精确路径清单和对应回读收据；不得删除 `.project-local/runs`、未知历史、私有状态、外置库或现有 Green。

状态语义：本报告记录的是 `IMPLEMENTED_LOCAL` 的清理动作、`TESTED_LOCAL` 的既有 A04 收据、`REMOTE_READBACK_BLOCKED` 的当前 SSH 限制，以及仍为 `BLOCKED/UNVERIFIED` 的未完任务；没有把本地删除、提交或候选包宣称成发布、安装或独立审计通过。

## 2026-10-08 批次：分类实测、收敛落地与可审核回收清单

本轮**未使用任何删除授权**：没有递归删除、hard reset、`git clean`、历史改写、远程 ref 操作或覆盖未知内容。全部动作是非破坏性的索引、引用修复、目录收敛（`git mv`）与验证。口径：`du -sk`（Git Bash GNU du，1K 块，`.git` 除外）、`git count-objects -v`、`git ls-tree -r -l` 的 blob 字节和、`stat -c%s`、`sha256sum` 逐字节。以下数字均为本任务内实测，不引用上一轮报告的汇总。

### 1. 体积分类（不能只给一个总数）

| 类别 | 实测 | 可否重建 | 本轮变化 |
| --- | --- | --- | --- |
| Git 对象与历史 | `in-pack` 36,361 对象 / `size-pack` 498,483 KB / 3 个 pack；loose 24 对象 56 KB | 否 | **未减少，也不会减少**：只能靠历史改写或远程 ref 删除，二者不在默认授权内，明列于此不作隐藏 |
| 跟踪工作树（blob 合计） | 基线 `a8d2e0bb` 3,121 文件 / 77,460,200 bytes → 本轮 HEAD 3,123 文件 / 77,866,780 bytes | 否 | **+406,580 bytes（变大了）**：新增硬化门禁、共享扫描器、live-region 测试与合同字段。文档收敛没有在 Git 上省字节，见下 |
| `docs/current/` | 405 → 342 跟踪文件；6,023,823 → 5,689,506 bytes | 否 | 分散度收敛；字节进入 `docs/history/`（167 → 230 文件，19,998,278 → 20,482,048 bytes），**Git 总量不降**，这是收敛而非瘦身 |
| 可重建构建输出 | `.project-local/build` 41,888,601 KB | 是 | 未动。主检出 `build/cargo` 是共享暖缓存（1.1 GB registry），删它等于把重建成本转给下一轮 |
| 运行证据 | `.project-local/runs` 10,145,977 KB / 2,196 个 run 目录 | **否** | 未动，列为保护类 |
| 恢复件 | `.project-local/recovery` 8,337,113 KB（含 cargo-msvc-pdb、cargo-gnu-binaries、green-maintenance-wal） | 否 | 未动，恢复路径引用中 |
| 迁移归档 | `.project-local/mig` 4,509,062 KB | 否 | 未动 |
| 依赖缓存 | `.project-local/cache` 3,459,607 KB（nuget/uv/cargo/npm） | 是 | 未动（暖缓存，删除即重建） |
| 工件 | `.project-local/artifacts` 2,505,796 KB | 部分 | 未动；含本轮被更正引用的证据目录，见诚实性批次 |
| 工作树合计 | `.project-local/worktrees` 81,086,691 KB / 42 条目；最大 dsh-backend-loop 38,373,469 KB、aaos-p04-doc-loop 26,268,792 KB、ui02-nav3 8,487,689 KB | 混合 | **本轮自己新增了 5 个 writer 工作树**（见第 4 节），这是并行写作的必要成本，不是瘦身成果 |
| `.venv` / `.hermes` | 1,044,942 KB / 526,955 KB（`.hermes/rt/runtime` 525,499 KB） | 是 / 否 | 未动；`.hermes` 按 AGENTS.md 既不新增写入也不整删 |

### 2. 重复占用实测（junction 机制此前从未规模化）

`frontend/node_modules` 现状：**10 份真实副本 vs 7 个 junction**（PowerShell `Attributes -match ReparsePoint` 实测计数）。单份约 203,917 KB，即约 **2.07 GB 属同一锁文件的重复安装**。本轮新增的 4 个工作树全部改用 junction 复用 `f15-folder-ingest-20261007/frontend/node_modules`（`package-lock.json` 与基线 SHA-256 逐字节相同：`bad160497be687b5…`），新工作树**未复制大型共用资源**。规则已写入 `docs/VERIFICATION_POLICY.md`「任务运行不得膨胀」。

未注册的遗留目录（不是工作树，`git worktree list` 无记录）：`pycache-full` 82,158 KB、`pycache-f06ui` 37,836 KB、`pycache-172` 34,033 KB、`pycache-f09` 32,844 KB（合计 186,871 KB，`__pycache__` 派生物，可重建、无引用）；外壳残留 `aaos-p02-readback-20261007` 28 KB、`aaos-p03-folder-batch-20261007` 28 KB、`dp-f01-20260925` 20 KB、`worker-outside-test` 0 KB。

### 3. 主检出的未跟踪历史资产：唯一性已实测，归属待定

主检出（`codex/Audit`，实测为 `origin/main` 的祖先、落后 750 提交）工作树内有一批 **既未跟踪、.gitignore 也未覆盖** 的 `docs/history/` 内容，且我逐目录核对其在真实基线 `a8d2e0bb` 的跟踪状态为 **0 文件**——即这些字节目前只存在于该工作树，删掉不可从 Git 恢复：

| 路径 | 文件 | `du -sk` | 基线是否跟踪 |
| --- | --- | --- | --- |
| `docs/history/task-artifacts` | 817 | 344,955 KB | 否 |
| `docs/history/desktop-attachments` | 17 | 124,520 KB | 否 |
| `docs/history/evidence` | 68 | 1,028 KB | 否 |
| `docs/history/closure-tasks` | 12 | 68 KB | 否 |
| `docs/history/skill-call-index.json` | 1 | 4 KB | 否 |
| `docs/history/worktree-preserved-diffs` | 9 | 44 KB | 部分（3 个补丁在基线已跟踪） |

处置：本轮**不动一个字节**。需要业主二选一：作为历史证据纳入提交，或显式纳入忽略并保留清单与哈希。风险是它现在处于最坏状态——`git add .` 会把 468 MB 一次性带入提交，而任何清理命令又会使其不可恢复。

### 4. 可审核回收清单（仅清单，未执行）

| exact path | 归属依据 | 用途 | 可重建 | 仍被谁引用 | 目标位置 | 建议操作 | 回退方法 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `.project-local/worktrees/{a-gates,b-surfaces,c-resources,d-docs,e-honesty,f-oss,g-coredemo}-20261008` ＋ `gov-ui-20261008` | 本任务创建，分支已提交，`git worktree list` 注册 | 一 checkout 一 writer 的并行写作位 | 是（分支保留即可重开） | 本轮各分支提交 | 整合完成后 `git worktree remove` | **由我在整合确认后执行**（唯一我认领的删除） | `git worktree add` 回同一 SHA |
| `.project-local/worktrees/pycache-*`（4 个） | 未注册、非工作树、名字与内容均为 `__pycache__` 派生 | 无 | 是 | 实测无引用（不在 `git worktree list`，不在任何收据路径） | — | 待授权回收 186,871 KB | 重跑测试即再生 |
| 10 份重复 `frontend/node_modules` | 同 `package-lock.json` 哈希 | 依赖安装 | 是 | 各工作树自身 | 改为 junction | 待授权：逐树替换为 junction，约回收 1.87 GB | `npm ci` 或重建副本 |
| `.project-local/inputs/diarization-candidates-20261007` 中 `speaker-embedding.onnx` 26,530,550 bytes | 与共享根 `Model library/sherpa-onnx/speaker-diarization/speaker-embedding.onnx` **逐字节同哈希** | F10 分离的暂存输入 | 是（共享根为源） | F10 供给切片 | 只留共享根引用 | 待 F10 结论后回收；`.PATCHED.onnx` 为**已修改件，不得按同名处理** | 重新暂存 |
| `.project-local/build/*` 按身份哈希目录 | 构建输出 | 编译产物 | 是 | 部分证据引用具体二进制身份 | — | 不在本轮提议：暖缓存重建代价高，需按证据引用逐目录判定 | 重新构建 |

### 5. 明确不属于本轮授权 / 未执行的不可逆项

1. Git 历史清理、历史改写、远程 ref 删除、强推——未执行，需单独授权。
2. `.project-local/runs`（10,145,977 KB）、`recovery`、`mig`、`artifacts`、`docs/**` 历史与 `worktree-preserved-diffs` 补丁——被验收或恢复引用，不得自动清除。
3. 主检出未跟踪的 468 MB `docs/history/` 资产——归属待业主判定（见第 3 节），本轮只登记。
4. `.ui-task-tree/ArcheAxis-Knowledge-OS-mainline` 5,783,275 KB——属 `CodexSandboxOnline`，git 以 dubious ownership 拒绝，非本项目 writer 所有，不动。
5. 外置工具根与 `Model library`（29,826,359 KB / 107,665,128 KB）——只读解析，未复制、未重组、未修改全局环境。
6. 任何 ACL 修改、进程终止、全局环境变量变更、Green 日用安装件覆盖或用户 sqlite/CAS 迁移——一律未执行。

状态语义：本节全部为 `IMPLEMENTED_LOCAL`（索引、`git mv` 收敛、引用修复、规则落地）与 `PROPOSED_AWAITING_AUTHORIZATION`（回收清单），没有任何一项被宣称成远端 CI、安装资格、发布或人工验收通过。
