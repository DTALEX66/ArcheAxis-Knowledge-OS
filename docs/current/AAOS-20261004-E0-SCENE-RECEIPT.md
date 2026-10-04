# AAOS 2026-10-04 任务包 · E0 现场回执（W00/W01）

执行器 DSH。本回执只读采集，**未修改任何项目源码、未启动产品、未写入资料库**。
采集时间：2026-10-04。来源类别：E（本轮实测）+ 既有 Authority 文件。

## 1. W00 现场身份（只读实测）

| 项 | 实测值 |
| --- | --- |
| 实际项目根 | `D:/All projects/ArcheAxis-Knowledge-OS` |
| 根 HEAD | `1a981a4482b01f31989074e79c82a63400aa07a7`（`docs: audit Green repository boundary and staged cleanup`） |
| 根分支 | **`codex/Audit`**（不是 `main`） |
| 根工作树状态 | **22 项，全部为 `??` 未跟踪**；**无已跟踪文件被修改** |
| 未跟踪内容 | `crates/archeaxis-api/tests/contract_capability_registry.rs` + `docs/history/**`（closure-tasks、desktop-attachments、evidence、handoffs、kanban、migrated-windows-state、plans、skill-call-index.json、sleep-mode、sleep-tasks、storage-cleanup、task-artifacts、task-runtime-scattered，以及 8 个 `worktree-preserved-diffs/hermes__task-runtime__*.patch`） |
| 远端 | `git@github.com:DTALEX66/ArcheAxis-Knowledge-OS.git`（凭据已脱敏） |
| 锁文件 | `Cargo.lock` 22,968 B；`uv.lock` 1,065,721 B |
| 运行中的写者 | **无**（无 `archeaxis-api` / `ArcheAxis.Desktop` 进程） |
| 产品资料库 | `D:\All projects\资料库\workspace.sqlite` 存在（**本轮只登记元数据，未读取内容**） |
| Authority 在位 | `AGENTS.md`、`LESSONS_LEARNED.md`、`docs/CONFIGURATION_AUTHORITY_INDEX.md`、`docs/current/M0-DIRECTION-OVERRIDE-20260920.md`、`docs/authority/taskpack-0919-r6/EXECUTOR-START.md` 全部存在 |

### 1.1 工作树清单（8 个，跨 2 个根）

| # | 路径 | 分支 / HEAD |
| --- | --- | --- |
| 1 | `ArcheAxis-Knowledge-OS` | `codex/Audit` @ `1a981a44` |
| 2 | `…/.project-local/worktrees/dsh-backend-loop-20261001` | `codex/dsh-aaos-real-multiformat-loop-20261001` @ `0134c433`（本执行器） |
| 3 | `…/.project-local/worktrees/v3-era` | 无分支 / `968c4795` |
| 4 | `…/.project-local/worktrees/worker-quality-0906` | 无分支 / `4ca46eaf` |
| 5 | `ArcheAxis.Knowledge.Green-x64/.ui-task-tree/AAOS-integration-verification-413ad3a0` | 无分支 / `62f23189` |
| 6 | `…/.ui-task-tree/aaos-ui-phase2-integrate` | `codex/aaos-ui-phase2-20261001` @ `1a981a44` |
| 7 | `…/.ui-task-tree/ArcheAxis-Knowledge-OS` | 无分支 / `7282e5a9` |
| 8 | `…/.ui-task-tree/minimax-aaos-cosmic-ui-20261001` | `codex/minimax-aaos-cosmic-ui-20261001` @ `627e74ff` |

**写者判定**：本执行器只写 #2。**#1 属于 `codex/Audit` 现场**（22 项未跟踪是他人在途产出，按任务包「保护现场」不动）。#5–#8 **位于 Green 安装目录内**，说明 Green 根同时承载 worktree；这正是 Authority 记录要求「不启动 Green 做测试、不替换、不清理」的原因。

## 2. 现场风险（本轮实测发现，需登记）

1. **根不在 main**：根在 `codex/Audit`，而任务包记录 PR #157 的 base 也是 `codex/Audit`；PR 仍是 open/Draft/未合并。任何「已合并/已交付」说法都缺证据。
2. **根有他人在途未跟踪产出**：22 项。不得 `clean`、不得覆盖、不得当成本执行器成果。
3. **ACL 拒绝范围远比先前记录的 33 个大**：直接在根下执行按路径匹配会**大量报 `os error 5 拒绝访问`**，命中 `.project-local\runs\**\pytest-cache`、`pytest-tmp`、`tmp`，以及 **`.project-local\tools\uv-0.12.18\**`** 与 `.project-local\ui-audit\pytest-cache` 等。这些目录属主不是当前用户。**后果**：glob/ripgrep 类工具在项目根直接搜索会失败或淹没输出，必须限定路径或排除 `.project-local`。
4. **`uv` 工具目录也在拒绝清单内**（`.project-local\tools\uv-0.12.18`）—— Authority 记录提到过「既有失效 uv trampoline 环境」，与此一致。

## 3. W01 本轮需求 delta（U01–U12 → 现有 Authority 对账）

| 需求 | 相对 R6/M0 的 delta | 登记去向（拟） |
| --- | --- | --- |
| U01 独立思考 | 执行姿态，不需新增台账 | — |
| U02 AAOS 如何成为 Agent | 产品叙事；不新建运行时 | 06 能力合同章 |
| U03 开源池吸收须对账 | 已有「参考/代码/可用/往返」四态区分 | W03/W19 |
| U04 调研可用/高人气/获奖 UI | **新增调研项** | W10 |
| U05 学习/科研/研发 API 优先 | **新增来源优先级** | E4a/E4c |
| U06 插件/技能菜单说明已接能力 | **新增可发现性要求** | W12/W13 |
| U07 API 许可/额度/兼容变化入雷达 | **新增雷达条目** | W19/W35 |
| U08 可落地方案而非规划 | 执行姿态 | 全部 |
| U09 现有+未来能力均可发现 | **新增：不得用死按钮/灰色隐藏替代** | W02/W12/W14 |
| U10 界面必须好看（独立交付条件） | **新增：视觉为独立 Gate，未经认可样板不得扩散** | W10/W11/W17 |
| U11 交付完整任务包 | 已由用户完成 | — |
| U12 知识库全能力兼容 + 双向无缝转换 | **最大新增**：新增 K0–K5 兼容流，不得以「支持导入导出」充当 | W03/W21–W24/W27–W29 |

**结论**：R6/M0 阶段门禁**不收窄、不覆盖**；U04/U05/U06/U07/U09/U10/U12 作为**本轮新增 delta** 登记，其中 **U12 是唯一新增的长期目标流**，U10 是本轮唯一新增的**独立验收 Gate**。

## 4. 工具可用性（按权威路径记录核对，**无需下载**）

依据 `docs/SHARED_RESOURCE_PATH_INDEX.md`（项目内权威路径登记）与 `D:\All projects\OS External Configuration\00-registry\project-tool-index.yaml`（跨项目共用工具索引），逐项实测存在：

| 资源 ID | 路径 | 存在 |
| --- | --- | --- |
| `shared_tools` | `D:\All projects\OS External Configuration` | 是 |
| `shared_cargo` (MSVC) | `10-toolchains\cargo\bin\cargo.exe` | 是 |
| `shared_rustc` (MSVC) | `10-toolchains\cargo\bin\rustc.exe` | 是 |
| `shared_rustfmt_home` | `toolchains\rust\rustup` | 是 |
| `shared_dotnet_sdk_10_0_401` | `10-toolchains\dotnet-sdk-10.0.401\dotnet.exe` | 是 |
| `shared_aaos_ui_python` | `10-toolchains\python\venv-aaos-ui-312\Scripts\python.exe` | 是 |
| `shared_nuget_cache` | `60-cache\nuget` | 是 |
| `shared_msvc_environment` | `10-toolchains\msvc\VC\Auxiliary\Build\vcvars64.bat` | 是 |
| `shared_models` | `D:\All projects\Model library` | 是 |

**按用户指令「缺少工具先查权威路径记录，确认共用外置工具库与本地仓库都没有才下载」的结论：本轮 W04–W09 所需工具全部已在共用外置工具库中就位，因此不下载任何工具。**

**待解决的工具链分歧（登记，不在本轮擅改）**：Authority 记录登记的是 **MSVC** 工具链（`10-toolchains\cargo`）与 rustfmt（MSVC stable），而本执行器此前在 worktree 中实际使用的是 **GNU** 工具链（`toolchains\mingw` + `stable-x86_64-pc-windows-gnu`）。W00/W05/W07 需要确定唯一口径；在确定前，**不擅自改动环境或 PATH**。

## 5. NOT_RUN / 阻塞

| 项 | 状态 | 原因 |
| --- | --- | --- |
| 本轮未复跑 DSH 先前测试数 | **NOT_RUN** | 任务包明确要求重新采集，不沿用书面回报 |
| 未读取资料库内容 | **NOT_RUN（按边界）** | Authority 要求只登记元数据 |
| 未启动 Green / 未替换 / 未发布 | **NOT_RUN（按边界）** | Authority 与任务包双重禁止 |
| 未读历史 ZIP（47 个素材包等） | **NOT_RUN（按边界）** | 任务包要求按需读取，不做无限全历史搜索 |
| E4b K0–K5 兼容流 | **PENDING** | 依赖 W03 既有实现盘点 |

## 6. 下一步（按任务包顺序）

1. W01 收尾：把上表 delta 落到现有 `docs/current/` 可变台账（不新建第二 authority）。
2. W02/W03：能力与 IA 对账 + 供体/知识库既有实现盘点（K0）。
3. W04–W09：工程可靠性（单源 runtime manifest、启动输入、学习事件、真实 bind 0、进程捕获、缺失状态合同）。

