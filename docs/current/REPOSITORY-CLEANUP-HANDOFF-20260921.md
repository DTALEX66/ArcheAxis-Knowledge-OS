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

## 2026-10-08 批次 B：并行写作工作树处置执行 + 体积按类重测（本会话实测）

本节执行的是上一节第 4 条回收清单里由本写作线认领的那一项删除。口径全部来自本会话运行的命令，
不引用任何历史汇总。`du` 在 GB 精度上不可复现，所以全部字节都出自同一枚举脚本 `enumerate_tree.py`：
它用 `st_file_attributes & 0x400` 识别 Windows 重解析点，**绝不进入链接内部**，
因此 junction 指向的共享安装只被计一次，体积数字也不会把同一份内容重复说出来。
证据目录：`.project-local/task-runtime/worktree-disposition-20261008/`
（`disposition-manifest-20261008.json` 先写、`disposition-receipt-20261008.json` 后落，另含各枚举 JSON）。

### B-0 命令 → 数字的可追溯对应

| 数字 | 产生它的命令（本会话内执行） |
| --- | --- |
| 逐工作树字节/文件/链接 | `enumerate_tree.py --root <每个工作树> --measure-target <WT>/f15-folder-ingest-20261007/frontend/node_modules`（pass X，开始于 2026-10-08T16:50:39+08:00，每树 0.0–0.1s） |
| 逐工作树 `.project-local` 内部构成 | 同脚本 pass Y，开始于 2026-10-08T16:53:37+08:00 |
| `worktrees` 根整体前后 | 同脚本 `--root .project-local/worktrees`：pass W 2026-10-08T16:49:13+08:00（5.7s）/ pass W2 2026-10-08T17:01:56+08:00（5.0s） |
| 主检出整体前后 | 同脚本 `--root D:/All projects/ArcheAxis-Knowledge-OS`：pass R 2026-10-08T16:49:34+08:00（14.2s）/ pass R2 2026-10-08T17:02:01+08:00（13.2s） |
| Git 对象与历史 | `git -C "D:/All projects/ArcheAxis-Knowledge-OS" count-objects -v` |
| 跟踪工作树字节 | `git -C "D:/All projects/ArcheAxis-Knowledge-OS" ls-tree -r -l 29c3cb98` 第 4 列求和 |
| 布局契约判定 | `scripts/runtime/storage_report.py --json …`（本工作树）与 `main_layout_audit.py`（把同一模块指向主检出） |
| 逐项证明 | `git status --short`、`git diff --quiet HEAD`、`git log --oneline 29c3cb98..<branch>`、`git merge-base --is-ancestor <branch> 29c3cb98` —— 在 `build_manifest.py` 与 `execute_disposition.py` 各跑一次 |
| 重解析点分类 | `fsutil reparsepoint query <link>` + `cmd /c dir /al <父目录>`（逐项，输出落进 manifest）与枚举脚本的属性位判定 |
| 共享安装完整性 | `target_watch.py` 三个时间点 + 执行器内每个链接的卸载前/后各一次 |
| 谁依赖这些路径 | `check_dependents.py`（扫三次枚举共 384 个重解析点的目标）与 `git grep` 的路径引用检查 |

### B-1 前后表（不是一个总数，按根分列）

| 根（root） | 处置前 bytes | 处置后 bytes | Δ bytes | 文件数 前→后 | 重解析点 前→后 | 单次通过耗时 |
| --- | --- | --- | --- | --- | --- | --- |
| `.project-local/worktrees` | 87,319,674,501 | 76,430,903,771 | -10,888,770,730 | 869,720 → 816,015 | 18 → 14 | 5.7s / 5.0s |
| 主检出根 `D:/All projects/ArcheAxis-Knowledge-OS` | 170,598,341,251 | 159,706,645,517 | -10,891,695,734 | 1,469,267 → 1,415,810 | 183 → 179 | 14.2s / 13.2s |

- 9 个工作树逐项字节之和（pass X）= **10,908,188,080 bytes**。
- `worktrees` 根实测净减 10,888,770,730 bytes，与逐项之和相差 19,417,350 bytes：差额是同一时间窗内
  **新增在同一根内**的字节——保全收据 18,807,969 bytes（放在本工作树的
  `.project-local/task-runtime/worktree-disposition-20261008/preserved-residue/`）加本会话的证据文件。
  两个根互为包含关系，故不并列相减，只各报各的。
- 工作树条目数：`git worktree list` 处置前 38 条 → 处置后 29 条（`git worktree list | wc -l` 实测 29）。

### B-2 处置清单与逐项证明

证明口径（每项全绿才动）：`git status --short` 为空 **且** `git diff --quiet HEAD` 返回 0 **且**
`git log --oneline 29c3cb98..<branch>` 为空 **且** `git merge-base --is-ancestor <branch> 29c3cb98` 退出 0 **且**
HEAD 附着在分支上（detached 时 `git worktree add <path> <branch>` 的回滚不成立，直接跳过）。
`refs/stash` 是仓库全局的：`git -C "D:/All projects/ArcheAxis-Knowledge-OS" stash list` 返回 2 条，
逐工作树查询也都是同样这 2 条，且都属于无关旧分支（`codex/local-pre-api-updates-20260918`、`feat/portable-data-root`），
对本清单 9 项**不构成未提交工作的证据**——只登记，不 apply、不 drop、不作为拒绝理由：

```
stash@{0}: On codex/local-pre-api-updates-20260918: local copies already uploaded to origin/main 2026-09-18
stash@{1}: On feat/portable-data-root: recovery-20260805-before-taskpack-completion
```

同时更正上一节的写入时记录：`BRANCH-DISPOSITION-CURRENT-20260923.md` 写入时把 `<WT>/d-docs-20261008`
记为 `DIRTY-UNCOMMITTED-PROTECTED`（脏项 2、tip `fb63001542`）。本会话执行时实测该项干净、tip 为 `cd83a4ff`（下表）。
这就是不能继承旧审计、必须临执行重跑证明的原因——两边都不算错，只是状态在并行中漂移了。

| worktree | branch | tip | status 行数 | `29c3cb98..<branch>` | `--is-ancestor` 退出 | 链接数 | 工作树 bytes | 保全 bytes | 随树删除的 `build/` bytes | 结果 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `a-gates-20261008` | `codex/aaos-branch-disposition-20261008` | `7652836e55` | 0 | 空 | 0 | 1 | 79,282,395 | 710,003 | 4,988 | REMOVED |
| `b-surfaces-20261008` | `codex/aaos-ui-templates-20261008` | `d73c50d7c0` | 0 | 空 | 0 | 1 | 89,560,325 | 11,361,584 | 5,107 | REMOVED |
| `c-resources-20261008` | `codex/aaos-gov-resindex-20261008` | `9f3fd470a5` | 0 | 空 | 0 | 0 | 78,366,623 | 116,743 | 0 | REMOVED |
| `d-docs-20261008` | `codex/aaos-gov-volume-20261008` | `cd83a4ffac` | 0 | 空 | 0 | 0 | 79,132,551 | 417,774 | 0 | REMOVED |
| `e-honesty-20261008` | `codex/aaos-gov-honesty-20261008` | `15f0e6de93` | 0 | 空 | 0 | 0 | 78,703,432 | 208,533 | 0 | REMOVED |
| `f-oss-20261008` | `codex/aaos-gov-oss-20261008` | `ea1e170024` | 0 | 空 | 0 | 1 | 1,379,343,754 | 4,007,548 | 1,281,672,941 | REMOVED |
| `g-coredemo-20261008` | `codex/aaos-gov-coredemo-20261008` | `c94c725900` | 0 | 空 | 0 | 0 | 78,593,306 | 714,062 | 0 | REMOVED |
| `oss-reuse-20261008` | `codex/oss-reuse-templates-20261008` | `15f79cf7fc` | 0 | 空 | 0 | 0 | 271,541,615 | 0 | 2,684,749 | REMOVED |
| `ui02-nav3-20261008` | `codex/aaos-ui02-nav3-20261008` | `a8d2e0bb2e` | 0 | 空 | 0 | 1 | 8,773,664,079 | 1,271,722 | 8,693,407,471 | REMOVED |
| **合计** |  |  |  |  |  | 4 | 10,908,188,080 | 18,807,969 | 9,977,775,256 | 9 REMOVED / 0 SKIPPED |

删除前后 `git worktree list` 的差集正好是这 9 条；9 个分支在删除后逐个 `git rev-parse --short` 回读仍指向原 tip。
9 次 `git worktree remove` **全部在无 `--force` 的情况下退出 0**（收据 `items[].actions[]` 记录了命令原文与退出码），
即没有任何一项需要强制丢弃内容。
跳过项：**无**（0 项证明失败）。清单没有扩大：候选就是任务给的 9 个，`gov-ui-20261008`（本写作线自身）与
`f15-folder-ingest-20261007`（共享安装源）写进了执行器的硬性拒绝集 `DENY`，即使被误列也不动。
删除前另跑了一次“路径引用面”检查：`git grep -l -e "worktrees/<name>/" 29c3cb98` 与 `git grep -l -e "<name>/.project-local" …`
对 9 项全部为 0 命中，即**没有任何被跟踪文件把证据指向这些工作树内部**；
被引用的回执实际住在主检出 `.project-local/artifacts/evidence/…`（`find` 实测三例：`ui02-three-level-nav-20261008`、
`ui-branch-frontend-all-gates-20261008`、`ui03-failure-states-20261008`），不在被删目录里。

执行中的一次真实故障（如实记录，不粉饰）：第一次运行 `execute_disposition.py` 在**第一项 `a-gates-20261008`
完成 junction 卸载之后、保全复制刚开始时**崩溃——`\\?\` 扩展长度路径与 `Path.relative_to()` 不可比，抛 `ValueError`。
此时该工作树**尚未删除**，收据也未落盘。修正入队路径后重跑：`a-gates` 的链接数在第二次运行为 0（已被摘掉），
其前后对照改用同一工具的两个采样点——pass X 卸载前 `8,078 文件 / 190,195,893 bytes`（2026-10-08T16:50:39+08:00）
与崩溃后复查（2026-10-08T17:00:27+08:00）逐项一致；其余 3 项在 `cmd /c rmdir` 前后各测一次，见 B-3。

### B-3 junction（Windows 重解析点）处置与共享安装完整性

危险机制按事实处理，不靠命名规律推断：递归删除会跟着 junction 走进唯一真副本。
固定顺序为 *枚举重解析点 → `cmd /c rmdir "<link>"`（只摘链接，不碰目标）→ 复核目标文件数与字节 → 才 `git worktree remove`*。
`Remove-Item` 在这些路径上抛 NRE、`rm -rf` 跟随链接，二者均不可用，故未使用。
删除动作之前还做了一次**整树新扫描**（不是复用 manifest 的结论）：任何残留重解析点都会中止该项，
收据字段 `links_remaining_after_unmount` 9 项全为空列表。

共享目标：`D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/f15-folder-ingest-20261007/frontend/node_modules`

| 已卸载链接 | 目标 | 卸载前 files / bytes | 卸载后 files / bytes | 一致 | 链接已消失 | `cmd /c rmdir` 退出 |
| --- | --- | --- | --- | --- | --- | --- |
| `D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/b-surfaces-20261008/frontend/node_modules` | `D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/f15-folder-ingest-20261007/frontend/node_modules` | 8,078 / 190,195,893 | 8,078 / 190,195,893 | True | True | 0 |
| `D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/f-oss-20261008/frontend/node_modules` | `D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/f15-folder-ingest-20261007/frontend/node_modules` | 8,078 / 190,195,893 | 8,078 / 190,195,893 | True | True | 0 |
| `D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/ui02-nav3-20261008/frontend/node_modules` | `D:/All projects/ArcheAxis-Knowledge-OS/.project-local/worktrees/f15-folder-ingest-20261007/frontend/node_modules` | 8,078 / 190,195,893 | 8,078 / 190,195,893 | True | True | 0 |

独立复查（`target_watch.py`，四个时间点，同一属性位规则）：

```
2026-10-08T17:00:27+08:00  exists=True  files=8,078  bytes=190,195,893  nested_links=0   <- measure of shared target AFTER the aborted first run unmounted a-gates junction (its before-state is pass X at 16:50:39)
2026-10-08T17:00:36+08:00  exists=True  files=8,078  bytes=190,195,893  nested_links=0   <- before re-run of executor
2026-10-08T17:00:50+08:00  exists=True  files=8,078  bytes=190,195,893  nested_links=0   <- after executor run: all candidate junctions unmounted and worktrees removed
2026-10-08T17:15:22+08:00  exists=True  files=8,078  bytes=190,195,893  nested_links=0   <- final: shared install re-measured at the end of the session, after all 9 removals
```

功能面复查：幸存 junction 仍能解析出完整安装——
`ls -A <WT>/gov-ui-20261008/frontend/node_modules/ | wc -l` = 166 项，
`ls -A <WT>/f15-folder-ingest-20261007/frontend/node_modules/ | wc -l` = 166 项，
`sha256sum` 两侧 `.package-lock.json` 同为 `f67718ea26117a0adf70e953a0aaebb495ad63d1e954bb617ce78b687d0fed19`。

**留给下一位的新风险（本会话实测，勿凭旧文档行事）**：`node_modules → f15` 的 junction 原有 9 个，
本会话摘掉 4 个，仍存 5 个（`aaos-member-chain-20261007`、`canonical-browser-host-20261007`、
`f04-detect-ui-20261007`、`f06-pages-ui-20261007`、`gov-ui-20261008`）。
**删除 `f15-folder-ingest-20261007` 会一次打断这 5 个检出**，必须先摘链接或改为独立安装。
反向依赖也已实测：`check_dependents.py` 扫过三个枚举通过里的 384 个重解析点，
**目标位于被删 9 个工作树之内的链接 = 0**，故本轮删除没有孤立任何外部 junction。

### B-4 分类体积（按类分列，禁止合并成一个数）

| 类别 | bytes（本会话实测） | 可否重建 / 回收 | 依据命令 |
| --- | --- | --- | --- |
| Git 对象与历史（包内） | `size-pack` 498,483 KiB = 510,446,592 bytes；`in-pack` 36,361 对象 / 3 packs | **不可**：只有历史改写或删远程 ref 才降，二者不在授权内——明列于此，不隐藏 | `git count-objects -v` |
| Git 对象（散对象） | count 274 / size 1,522 KiB = 1,558,528 bytes；garbage 0 | 会自动打包，不是回收目标 | `git count-objects -v` |
| `.git/` 实际占用（主检出，含 refs/logs/工作树管理条目） | 前 527,904,985 → 后 524,708,819 bytes | 差值来源就是 9 条工作树管理目录 | pass R / R2 |
| 跟踪工作树字节（blob 合计 @ `29c3cb98`） | 78,221,061 bytes / 3,146 blobs | **不可回收**：这是代码本体 | `git ls-tree -r -l 29c3cb98` |
| ├ `docs/`（跟踪） | 34,172,216 bytes：非 ASCII 目录名被 ls-tree 加引号，分两桶 17,788,846 + 16,383,370；子项 `docs/current` 5,822,177 bytes / 349 文件，`docs/history` 3,566,628 bytes / 164 文件 | 收敛 ≠ 瘦身 | 同上 |
| ├ `apps/`（跟踪，最大非 docs 目录） | 14,198,754 bytes / 58 文件 | — | 同上 |
| 被忽略的开发根 `.project-local`（主检出） | 前 167,769,964,299 → 后 156,881,464,731 bytes | 见下面各类 | pass R / R2 |
| ├ 构建输出 `build_output` | 88,635,920,407 bytes / 236,191 文件 | 可重建，但属暖缓存 | pass R2 by_class |
| ├ ├ 其中随 9 个工作树一起销毁的**各树私有 `build/`** | 9,977,775,256 bytes | 可重建：`scripts/runtime/dev.py` 重新构建。dev.py 的规则是“主检出共享 bare Cargo target，**linked worktree 保留各自独立输出**”，故这是该工作树的私有输出，不是共享缓存；共享 `build/cargo` 与 `cache/cargo`(`CARGO_HOME`) 均未动 | pass Y 逐树 `build` 子项 |
| ├ 运行证据 `run_evidence` | 13,229,867,953 bytes / 165,641 文件 | **不可**：被验收与恢复引用 | pass R2 |
| ├ 任务运行态 `task_runtime` | 11,253,488,992 bytes / 171,547 文件 | 混合：含本会话证据 | pass R2 |
| ├ 恢复件 `recovery` | 8,537,075,003 bytes / 70 文件 | **不可** | pass R2 |
| ├ 依赖与工具缓存 `cache` + `dependency_cache` | 8,675,989,710 bytes | 可重建；删=把重建成本转给下一轮 | pass R2 |
| ├ 迁移归档 `migration_archive` | 4,621,926,307 bytes | **不可** | pass R2 |
| ├ 候选产物 `candidate_output` | 2,370,124,740 bytes | 部分 | pass R2 |
| ├ 虚拟环境 `venv` | 类合计 2,125,406,272 bytes / 45,800 文件；主检出 `.venv/` 单目录 1,013,827,188 bytes / 24,129 文件 | 可重建 | pass R2 |
| ├ 前端依赖安装 `dependency_install` | 1,020,192,570 bytes / 42,163 文件 | 可重建 | pass R2 |
| ├ 字节码与测试缓存 `bytecode_cache` + `test_cache` | 383,729,727 bytes | 可重建，派生物 | pass R2 |
| ├ .NET / 前端 / Rust 构建产物 `dotnet_build_output` + `frontend_build_output` + `rust_build_output` | 2,210,939,284 bytes | 可重建 | pass R2 |
| ├ `git_admin`（各处 `.git`） | 546,478,483 bytes | 否 | pass R2 |
| ├ `.hermes`（遗留保留） | 497,066,790 bytes / 19,049 文件 | 否：AGENTS.md 既不新增写入也不整删 | pass R2 |
| ├ `data/`（被忽略的本地运行副本） | 101,390,408 bytes / 73 文件 | 否：唯一副本 | pass R2 |
| ├ 主检出源码面 `docs/` 磁盘占用 | 509,981,876 bytes / 1,832 文件（对比跟踪合计 78,221,061 bytes 全仓） | 含上一节登记的未跟踪 `docs/history/` 资产，归属仍待业主判定，本轮未动 | pass R2 |
| 逐工作树占用（处置后最大 5 项，pass W2） | `dsh-backend-loop-20261001` 41,088,219,419；`aaos-p04-doc-loop-20261007` 28,134,624,123；`aaos-ui-newui-20261007` 2,379,851,265；`f06-pages-ui-20261007` 2,271,461,369；`f10-supply-20261007` 491,061,329 | 混合 | pass W2 by_top_level |
| 跨工作树重复占用 | 真实 `frontend/node_modules` 副本 **5 份，合计 967,284,557 bytes**：`aaos-p04-doc-loop-20261007` 190,195,893 / `aaos-ui-core-integration-20261007` 190,195,893 / `aaos-ui-newui-20261007` 190,204,400 / `dsh-backend-loop-20261001` 206,492,478 / `f15-folder-ingest-20261007` 190,195,893。其中与共享目标逐字节等量（190,195,893 bytes / 8,078 文件）的**另** 2 份可折叠为 junction，理论回收 570,587,679 bytes；`aaos-ui-newui-20261007`（190,204,400）与 `dsh-backend-loop-20261001`（206,492,478）字节数不同，须先比锁文件再论折叠；另 5 个 junction 已把同类副本折叠到目标（只计一次） |
| ├ 未注册的遗留目录 | `worktrees` 根下已无未注册目录名混入（pass W2 的 26 个顶层条目与 `git worktree list` 的 29 条一致，其中 `dp-f01-*`、`pycache-*` 等上一节遗留项在主检出快照之前即已消失） | — | pass W2 vs `git worktree list` |
| 项目自有归档（`.project-local`，不含 `worktrees` 子树） | zip 14,444,936,740 bytes / 1,145 文件；git bundle 47,251,223 / 3 文件；gz 134,944,998 / 2,010；tar 83,200,380 / 333 | 逐项判定，绝不按扩展名批量删 | `report_tables.py` 扩展扫描 |
| 二进制 / 数据库 / 模型权重（同一扫描范围） | binary_artifact 11,719,894,782 bytes / 16,980 文件；database 5,349,175,055 / 18,667 文件；model_weight 268,873,861 / 360 文件 | 部分是证据、部分是缓存，未归因即不动 | 同上 |
| 跨项目 / 私有 / 共享（**不在本轮枚举范围**） | 只读核对声明根：`D:\All projects\Model library`、`D:\All projects\OS External Configuration`、`D:\All projects\ArcheAxis.Knowledge.Green-x64`、`D:\All projects\资料库`、`D:\All projects\ceshi`（`reparse=false`）。本轮**未测**其体积，也不沿用上一节的 `du -sk` 数字 | 不属本项目 writer 所有，不动 | `scripts/maintenance/check_resource_boundaries.py` 退出 0 |
| └ Green 部署树内的 `.ui-task-tree/` 检出 | `git -C "…/.ui-task-tree/ArcheAxis-Knowledge-OS-mainline" status --short` → `fatal: detected dubious ownership`，属主 `DESKTOP-L26E3AC/CodexSandboxOnline`（同树内另有 4 个目录，其一 `minimax-aaos-cosmic-ui-20261001` 是本仓库注册工作树） | **不动**：非本项目 writer 所有，且不在候选清单 | 本会话执行 |

测量口径的两条硬警告（否则数字会被误读）：

1. **不可读路径 = 真实下界，不是零**。主检出的 `.project-local/runs/*`、`tools/uv-0.12.18` 等被 ACL 拒绝：
   pass R 有 610 条不可读（分布：`.project-local` 533 条、`.hermes` 77 条），pass R2 同样 610 条；
   归档扫描另计 663 条。`worktrees` 根两次通过均为 0 条，故 B-1/B-2 的处置数字不受此影响。
   另需 `\\?\` 扩展长度前缀：第一次 pass W 未加前缀时静默漏读 940 条深路径（低估 153,264,853 bytes），
   加前缀后为 0 条——这也是 `.project-local`/主检出总字节必须读作下界的原因。
2. **`scripts/runtime/storage_report.py` 的 `directory_size()` 会跟随 junction**：它按 `entry.is_dir(follow_symlinks=False)`
   判断目录，而 Windows junction 在该调用下仍返回目录语义，于是同一份共享安装被重复计入预算。证据：本工作树该脚本报
   `frontend/` 0.18 GB，而同树 `frontend` 的真实字节只有 1,205,210 bytes，
   差额恰等于共享目标 `f15/frontend/node_modules` 的 190,195,893 bytes。
   故该脚本用于**布局判定与预算报警**，不用于本节的体积归因；本节数字一律出自 `enumerate_tree.py`。
   这是工具的既有语义，本轮未改（见 B-8），只如实报告。

### B-5 精确回滚（每个动作都能单独还原）

工作树（先重挂检出目录；分支从未删除，故内容级回滚是零成本的）：

```bat
git -C "D:\All projects\ArcheAxis-Knowledge-OS" worktree add "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\a-gates-20261008" codex/aaos-branch-disposition-20261008
git -C "D:\All projects\ArcheAxis-Knowledge-OS" worktree add "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\b-surfaces-20261008" codex/aaos-ui-templates-20261008
git -C "D:\All projects\ArcheAxis-Knowledge-OS" worktree add "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\c-resources-20261008" codex/aaos-gov-resindex-20261008
git -C "D:\All projects\ArcheAxis-Knowledge-OS" worktree add "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\d-docs-20261008" codex/aaos-gov-volume-20261008
git -C "D:\All projects\ArcheAxis-Knowledge-OS" worktree add "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\e-honesty-20261008" codex/aaos-gov-honesty-20261008
git -C "D:\All projects\ArcheAxis-Knowledge-OS" worktree add "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\f-oss-20261008" codex/aaos-gov-oss-20261008
git -C "D:\All projects\ArcheAxis-Knowledge-OS" worktree add "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\g-coredemo-20261008" codex/aaos-gov-coredemo-20261008
git -C "D:\All projects\ArcheAxis-Knowledge-OS" worktree add "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\oss-reuse-20261008" codex/oss-reuse-templates-20261008
git -C "D:\All projects\ArcheAxis-Knowledge-OS" worktree add "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\ui02-nav3-20261008" codex/aaos-ui02-nav3-20261008
```

被摘掉的 junction（在对应工作树重新 add 之后执行；目标为本会话记录的原值，非记忆值）：

```bat
cmd /c mklink /J "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\a-gates-20261008\frontend\node_modules" "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\f15-folder-ingest-20261007\frontend\node_modules"
cmd /c mklink /J "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\b-surfaces-20261008\frontend\node_modules" "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\f15-folder-ingest-20261007\frontend\node_modules"
cmd /c mklink /J "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\f-oss-20261008\frontend\node_modules" "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\f15-folder-ingest-20261007\frontend\node_modules"
cmd /c mklink /J "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\ui02-nav3-20261008\frontend\node_modules" "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\f15-folder-ingest-20261007\frontend\node_modules"
```

保全件回滚：把 `preserved-residue/<worktree>/` 原样复制回 `<worktree>/.project-local/`（实测 341 文件 / 18,807,969 bytes，与收据里逐树 `copied_bytes` 之和相等，复检 bytes 一致：`numbers.json.preserved.bytes_match_receipt=True）。

不可逆、且回滚命令不覆盖的部分（必须说清）：删除工作树同时销毁了各树私有 `build/` 共 9,977,775,256 bytes 暖缓存——重挂工作树**不会**带回它，只能由 `scripts/runtime/dev.py` 重新构建；
主检出共享 `build/cargo`、`.project-local/cache`（`CARGO_HOME`/nuget/npm/uv 路由目标）与 `f15` 的共享安装均未动。

### B-6 未授权 / 未执行项（与处置项分开列）

1. **删除分支或 ref**：未执行。9 个分支删除后逐个回读仍指向原 tip：`codex/aaos-branch-disposition-20261008` `7652836e`、`codex/aaos-ui-templates-20261008` `d73c50d7`、`codex/aaos-gov-resindex-20261008` `9f3fd470`、`codex/aaos-gov-volume-20261008` `cd83a4ff`、`codex/aaos-gov-honesty-20261008` `15f0e6de`、`codex/aaos-gov-oss-20261008` `ea1e1700`、`codex/aaos-gov-coredemo-20261008` `c94c7259`、`codex/oss-reuse-templates-20261008` `15f79cf7`、`codex/aaos-ui02-nav3-20261008` `a8d2e0bb`。
   `BRANCH-DISPOSITION-CURRENT-20260923.md` 第 236 行把 `git worktree remove … ; git branch -d …` 写成一条组合命令，
   本轮**只执行前半段**：删 ref 不在授权内。
2. **提交 / 推送 / 建 PR / 改远程**：未执行（任务边界）。
3. **历史改写、`git gc --prune=now`、`repack`、远程 ref 删除**：未执行；包内 510,446,592 bytes 属不可约历史，明列不隐藏。
4. **`refs/stash` 的 2 条全局 stash**：只登记，未 apply、未 drop。
5. **主检出未跟踪的 `docs/history/` 资产**：本轮未改其归属，维持上一节的业主二选一（纳管或显式忽略+保留清单）。
6. **主检出 `.project-local` 的 174 条 OUT-OF-LAYOUT**：只登记不处置——
   `main_layout_audit.py` 用仓库自带的 `storage_report.py` 规则指向主检出实测 `out_of_layout_count=174`
   （`.project-local` 游离项 170；根级 4 项：.zcode/, archeaxis_workspace.egg-info/, p-w7n3ehdf/, tools/）。
   其中含 `artifacts/`、`audits/`、`inputs/`、`tools/`、`wi/`、两个 `.bundle` 归档与大批 `api-upload-*.json`：
   它们有主、被引用或归属待定，**不是本轮删除清单**，也不借机给它们补一个合法名分。
7. **未列入 9 项的其他 26 个工作树**（最大 `dsh-backend-loop-20261001` 41,088,219,419 bytes、
   `aaos-p04-doc-loop-20261007` 28,134,624,123 bytes）：未动。
   幸存 `worktrees` 根内仍有 14 个重解析点（含 `dsh-backend-loop` 自身 8 个、`dp-f01-20260925` 1 个），
   任何后续回收都必须先摘链接。**不自作主张扩列。**
8. **`frontend/`、`scripts/a0_browser_smoke.py`、`scripts/audit/build_oss_reuse_inventory.py`、`docs/current/OSS-REUSE-*`、
   `AAOS-GOVERNANCE-UI-HANDOFF-20261008.md`、`AAOS-UI-ASSET-MANIFEST-20261007.json`、`AAOS-UI-MASTER-ASSET-AUDIT-20261001.md`**：
   属其他写作线，本轮一个字节未改；本工作树 `git status --short` 里它们的未提交改动仍归其主。
9. **本工作树分支在会话期间前移**：任务给的基线是具名提交 `29c3cb98`，所有祖先证明都锚定该 SHA；
   会话中 `codex/aaos-gov-ui-20261008` 被并行提交推进到 `27da2816`（`git log --oneline 29c3cb98..HEAD` = 2 条），
   且 `git merge-base --is-ancestor 29c3cb98 HEAD` 退出 0，故处置结论不受影响。
10. **外置共享根 / Green 部署树 / `.ui-task-tree`**：只读元数据核对，未扫描、未复制、未修改全局环境。
11. **`scripts/runtime/storage_report.py`**：见 B-8，未改。

### B-7 验证（本会话实际运行，非引用）

```
"D:/All projects/ArcheAxis-Knowledge-OS/.venv/Scripts/python.exe" -m pytest tests/workflow/test_workspace_layout_contract.py tests/runtime-paths/test_dev_paths.py -q
..............s...............                                  [100%]
29 passed, 1 skipped, 9 subtests passed in 8.27s
# PYTEST_EXIT=0（工作树根目录执行；未加 --basetemp，未跑整个 tests/）
```

任务提示的 `tests/test_dev_root_layout.py` / `tests/test_storage_report.py` **不存在**
（`ls tests/ | wc -l` = 439，无同名文件；`find . -iname '*dev_root*'` 与 `grep -r storage_report tests/` 定位到真实名字）。
真正守着这套契约的是上面两个文件：前者断言入口与 `.project-local` 允许类（`test_the_development_root_holds_only_sanctioned_classes`），
后者含 `test_identity_rejects_junction_ancestor` 等 junction 防护。
另跑：`scripts/runtime/storage_report.py --json …` 在本工作树 → `layout: every entry is inside the documented set`、退出 0；
`scripts/maintenance/check_resource_boundaries.py` 退出 0；
`git worktree prune --dry-run -v` 输出**为空**——9 条被删工作树的管理条目已由 `git worktree remove` 自行清除，
没有陈旧条目可清，故**未执行真实 prune**（“只 prune 我删过的路径”在无陈旧条目时等价于不 prune）。

### B-8 `storage_report.py` 许可类清单：本轮无需新增（附证据）

本会话在 `.project-local` 下新建的只有**已许可类内部的子目录**：
`task-runtime/worktree-disposition-20261008/`（枚举脚本、manifest、receipt、target watch、`preserved-residue/` 保全件、日志）。
`task-runtime` 已在 `DEV_ALLOWED` 内，故 `main_layout_audit.py` 对本工作树实测 `out_of_layout_count=0`、
`dev_strays=0`，`storage_report.py` 退出 0。
因此**未修改** `scripts/runtime/storage_report.py`：既没有“本轮新建却缺名分的类”需要补，也不借机放宽任何既有规则；
B-4 警告 2 指出的 junction 跟随属该工具既有语义，只报告不改（改了会让预算口径与历史收据不可比）。

状态语义：本节为 `IMPLEMENTED_LOCAL` + `TESTED_LOCAL`（定向测试见 B-7）。
删除对象仅限“干净且已并入基线的并行写作检出目录 + 其私有可重建输出 + 已复制副本的未跟踪收据”；
没有把它说成历史瘦身（包内字节一分未降）、没有说成远端 CI、没有说成发布或人工验收通过；
共享安装的完整性由前后两次文件数/字节与 SHA-256 双向证明，不由“应该没事”推断。
