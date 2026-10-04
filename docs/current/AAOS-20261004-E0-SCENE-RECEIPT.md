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

## 7. W02 能力与 IA 对账（批准集合 vs 当前菜单）

**批准集合**：`docs/truth/CAPABILITY_ATLAS_V2.yaml`（schema 2.0，updated 2026-08-12；状态规则 `docs/truth/AUTHORITY_AND_STATUS_RULES_V1.md`；tombstone 规则要求删除/降级/改名/合并须 Owner Decision）。共 **16 项**：CAP-0010…CAP-0160。

**当前桌面入口**：`MainWindow.axaml` 实测 **17 个 rail 按钮**：Workspace、Capture、Evidence、Originals、Learning、Machine、WorkspaceTree、MemoryMap、Search、Review、Knowledge、Reader、Research、Jobs、Plugins、Models、System（另有等量 Mobile 镜像）。

| capability | 名称 | 当前入口 | 判定 |
| --- | --- | --- | --- |
| CAP-0010 | 原件资产与来源接入 | Workspace / Capture / Originals | 有入口 |
| CAP-0020 | 多格式转换 | Capture / Jobs | 有入口 |
| CAP-0030 | 证据锚定与交叉核验 | Evidence | 有入口（交叉核验未在菜单体现） |
| CAP-0040 | 人类深度学习系统 | Learning / Review | 有入口 |
| CAP-0050 | AI 学习资产与受控调用 | Machine | 部分 |
| CAP-0060 | LER 视觉教学与课件 | 仅学习页内「课件候选」 | **部分（无独立入口）** |
| CAP-0070 | 动态解释与仿真 | — | **MISSING（无入口）** |
| CAP-0080 | 空间记忆与沉浸学习 | MemoryMap（静态示意图） | **部分（仅为示意图）** |
| CAP-0090 | 研究、课程与项目工作空间 | Research / WorkspaceTree | 有入口 |
| CAP-0100 | 开放互操作与生态适配器 | Plugins（未对应）；有策略文档 | **部分（无对应入口）** |
| CAP-0110 | 搜索、图谱与索引 | Search / MemoryMap | 有入口 |
| CAP-0120 | 桌面、平台与可选协作 | System | 有入口 |
| CAP-0130 | 受限受控执行探索 | — | **MISSING（无入口）** |
| CAP-0140 | 备份、同步与发布 | System / Recovery | 部分 |
| CAP-0150 | 模型、Provider 与数据出境治理 | Models | 有入口 |
| CAP-0160 | 可视化与空间学习表征 | MemoryMap / 图谱 | 部分 |

**W02 结论**：

1. **有 2 项批准能力在界面上完全没有入口**：CAP-0070 动态解释与仿真、CAP-0130 受限受控执行探索。按 U09「现有及未来能力都要可发现」，这两项必须在 W12 有正式入口与详情页（**可折叠、不得灰色死按钮**）。
2. **另有 5 项只有部分体现**（CAP-0060/0080/0100/0140/0160）。
3. **不以 seed 充全史**：本次只做 atlas↔菜单映射，**未新增、未删除、未改名任何能力**；任何变更须走 tombstone 规则的 Owner Decision。

## 8. W03 K0 供体与知识库既有实现盘点（复用优先）

**已有代码（先复用，不要重建）**：

| 类别 | 已存在 |
| --- | --- |
| Rust 领域 | `crates/archeaxis-domain/src/vault.rs`、`vault_members.rs` |
| Rust 迁移 | `crates/archeaxis-migration/`（含 `legacy_dryrun` 示例、`migration_dry_run`、`legacy_nonempty_migration`、`stage_demo` 测试） |
| Rust 契约测试 | `crates/archeaxis-api/tests/contract_vault_links.rs`、`contract_vault_members.rs`、`import_origins.rs` |
| **Obsidian 往返** | **`crates/archeaxis-archive/tests/obsidian_vault_roundtrip.rs` + 固定装置 `tests/fixtures/obsidian-vault/`**（`notes/atomic.md`、`notes/index.md`、`vault.canvas`、`attachments/diagram.png`、`PROVENANCE.txt`） |
| Python（legacy `app/`） | `app/exchange/export.py`、`exchange/backup.py`、`ingestion/import_job.py`、`evidence/hl01_import.py`、`knowledge/vault_projection.py`、`workspace/vault.py`、`workspace/migrate.py` |
| 策略文档 | `docs/architecture/OPEN_INTEROP_AND_ADAPTER_POLICY_V1.md`、`docs/MIGRATION_OPERATOR.md`、`docs/ABSORPTION_OBSIDIAN_ASSISTANCE_2026-07-13.md` |

**四态分类（任务包要求「参考/代码/可用/往返」分开）**：

| 态 | 结论 |
| --- | --- |
| 参考 | 有（interop 策略、迁移操作手册、吸收记录） |
| 代码 | **有**（上表全部为已跟踪文件） |
| 可用 | **NOT_RUN** —— 本轮未执行，不声称可用 |
| 往返 | **代码与固定装置存在，但本轮 NOT_RUN** —— 不得据此声称已验收 |

**W03 结论**：**W22（Markdown/Obsidian 首个双向 profile）已有可观既有基础**，必须**先复用 vault/roundtrip/迁移三处**再谈新增；K1 的交换合同应**扩展现有 `packages/contracts/v1/`**，不另起一套。

## 9. G0 状态（E0 退出条件）

| 工作项 | 状态 | 证据 |
| --- | --- | --- |
| W00 真实根/HEAD/工作树/唯一写者 | **完成** | 本回执 §1、§1.1 |
| W01 有效 Authority 与本轮 delta | **完成** | 本回执 §3 |
| W02 能力与 IA 对账 | **完成（发现 2 项无入口 + 5 项部分）** | 本回执 §7 |
| W03 供体/知识库既有实现盘点 K0 | **完成（四态已分；可用与往返为 NOT_RUN）** | 本回执 §8 |
| W35 雷达专项状态与范围确认 | **PENDING** | 未开始 |

G0 尚未闭合的部分：W35 未做；且 atlas 与 Authority 的一致性建议由 Hermes 侧独立复核（任务包建议分工），本回执行器不自签。



## 10. W15 机器可测部分对账（2026-10-04）

任务包 W15 的实物验收是「人完成逐条处置，**机器 actor 拒绝**，**历史可纠正**」。前两项里的后两项**不需要真人**即可核对，结论如下：

**机器 actor 拒绝 —— 已完整覆盖，本轮未新增测试（不盲目重做）**：

| 场景 | 证据 |
| --- | --- |
| 机器复核自己的候选 → **403** | `crates/archeaxis-api/tests/knowledge_actor_guard.rs:130-139` |
| 机器创建「accepted」→ **400 cannot self-accept** | 同上 `:61-71` |
| body 里伪造 `actor=human` + 头部 machine → **400（不升级）** | 同上 `:73-83` |
| 未知 actor → **400** | 同上 `:85-94` |
| 机器记录人类学习结果 → **403** | 同上 `:141-` |
| **生产路径**（v2 launch 的 machine_token，而非开发头部）人/机令牌对照，机器对 review-decisions → 拒绝 | `tests/launch_auth.rs:494,538,547`；另有 `:419 machine_launch_cannot_self_accept_even_with_forged_headers` 与 `:621` 重启后同一约束 |

**历史可纠正 —— 已覆盖**：`tests/knowledge_v3_projection.rs:92` 新版本 `supersedes == [旧 id]`；`:103` **旧版本仍可读**且 `superseded_by` 指向新版本（不是删除，是可审计地取代）；`:177` 再次修订仍记录其取代对象。

**仍未做（只能由人）**：真实库 19 条候选的**逐条处置**本身。`review-decisions` 需要 human actor，执行方不得代做，故本项保持 NOT_RUN。

**本轮无代码改动**：这是一次"先检查现有成果"的对账，结论是既有覆盖已经满足机器侧验收；新增重复测试只会制造第二份真值。

## 11. W16/B2 原创草稿持久化 · 处置（2026-10-04）

**结论：BLOCKED_ON_OWNER（范围授权），本轮不实现。**

依据（本轮**重新核对**，不是引用旧结论）：

| 核对项 | 结果 |
| --- | --- |
| 两处「保存草稿」按钮 | 仍 `IsEnabled="False"`，提示「保存到 Core 的功能尚未提供」，无障碍名「保存草稿暂不可用…」 |
| Core 草稿路由或表 | **不存在**（`crates/archeaxis-api/src` 内检索 `drafts` 无命中） |
| `M0-DIRECTION-OVERRIDE-20260920.md` | **完全没有提到**原创编辑器或草稿 → 无授权 |

所以这不是缺陷：界面没有把「未保存」伪装成「已保存」，并说清了原因与所需动作。而实现它等于把一个**闭环外的新能力**塞进 M0 —— 正是方向覆盖明文禁止的；它还会新增**第二个写入面**，牵连备份/恢复/迁移，以及「草稿不得进入检索、证据、知识、学习任何一张表」的边界。

范围说明与最小切片建议见 `docs/current/AAOS-ORIGINAL-DRAFT-SCOPE-NOTE-20261003.md`。**需 Owner 回答该文第 5 节的四个问题**（是否排期、是否接受最小切片、草稿能否显式提升为来源、保留多久）。在得到答复前，本项保持未实现，界面保持如实禁用。

## 12. W19 私有数据授权（Q26）· 本轮核对与一处自我纠正（2026-10-04）

**结论：本轮不实现权限模型，记为 BLOCKED_BY_AUTHORITY_DECISION，并纠正我上一轮自己写错的一处台账。**

### 12.1 核对结果

| 核对项 | 结果 |
| --- | --- |
| Core 内权限/ACL 面（`permission` / `Principal` / `acl`） | **检索 `crates/archeaxis-api/src` 全部无命中** —— 不存在 |
| `ask.rs` 的 240 字摘要 | 是**展示上限**，不是授权：它约束"回答里放多少正文"，不区分谁有权读什么 |
| `M0-DIRECTION-OVERRIDE-20260920.md:120` | provider routing 宿主生命周期明确标为 **`BLOCKED_BY_AUTHORITY_DECISION`**，并写明「不得把 test-only worker 生命周期升格为 M0 完成」 |
| 同文 `:142` | Fallback Provider 在 M0 范围内，但只支持 Enable/Disable/Default/Fallback/Health |

所以 Q26 的「查询/片段/全文权限分开」与「备用目的地不越权」**需要一个尚不存在的授权模型**；而它所要挂靠的 provider 宿主生命周期本身**已被权威决策阻塞**。按包内规则（不得把闭环外能力塞进 M0、BLOCKED 项不得自行解封），本轮**不做实现**。

**已经钉住的部分（不是空白）**：`ask.rs` 的摘要上限由单测固定（`excerpt` 的边界用例），回答必须带可核查引用，且 `contract_ask.rs` 有「回答是材料本身而非转述」「无命中是不作答而非空回答」「无锚点就说明无锚点，不编造来源」等断言。**但"谁能读全文"这一层没有断言，因为这一层不存在。**

### 12.2 自我纠正：CAP-0150 的状态写错了

上一轮（W13）我在 `config/capability-map.v1.json` 里把 **CAP-0150「模型、Provider 与数据出境治理」标为 `core_native`**。本轮核对证明 **Core 里没有这个面**：`core_native` 意味着「由 Core 自身路由实现」，而这里连一条相关路由或模型都不存在。provider routing 目前是 Python 侧 sidecar 设计且宿主生命周期被阻塞。

因此改为 **`not_implemented`**。这是一次**我自己制造的台账不准确**，由本轮核对发现并修掉 —— 台账说"已实现"而代码里没有，正是任务包最要防的那种失真。

## 13. W20 核对（Q27 / Q28）（2026-10-04）

### 13.1 Q28「元数据/摘要/全文分别记录，不伪称全文导入」—— **转换轴已覆盖**

| 已钉住的诚实性质 | 证据 |
| --- | --- |
| **没有回执时 `coverage` 是 `null`，不是 0** | `tests/job_quality.rs:88` `value["coverage"].is_null()`，注释写明「no receipt yet means no coverage claim」；`lib.rs:1730` 用 `unwrap_or(Value::Null)` |
| **被截断的转换不得声称全覆盖** | `tests/f01_quality_roundtrip.rs:539` `f01_capped_fixture_reports_anchor_loss_and_never_claims_full_coverage`，断言 `coverage < 1.0` |
| 质量面只报 coverage / loss / region，**从不报准确率** | `tests/job_quality.rs:2` 文件头声明 |

**未实现的部分**：书目轴（元数据 / 摘要 / 全文三者的分别记录）**在 Core 里没有对应概念** —— `crates/` 内检索 `abstract` 与 `full_text` **零命中**。它属于外部书目来源（Crossref/OpenAlex 那一类）的切片，而那个切片**尚未开始**。因此这是**未实现的能力，不是缺陷**，也不得被说成已覆盖。

### 13.2 Q27「401/403/429/5xx/超时/分页/预算耗尽」—— 部分覆盖，部分**不存在**

| 项 | 状态 | 证据 |
| --- | --- | --- |
| 401 | ✅ 覆盖 | `launch_auth`（本轮实跑 9 passed）；冷启动测试里旧 token → 401 |
| 403 | ✅ 覆盖 | `knowledge_actor_guard` 机器复核 → 403（3 passed） |
| 5xx | ✅ 覆盖 | `contract_semantic_search` 502（worker 失败）、`runtime/mod.rs` 503 `AAK-WORKER-001` |
| 超时 | ✅ 覆盖 | 调度超时释放事务、worker 超时后拒绝 |
| **429 / 预算耗尽** | ❌ **不存在** | `crates/archeaxis-api/src` 内检索 `429` / `rate.limit` / `budget` **零命中** |
| **分页** | ⚠️ **本轮未核实** | 我**不声称**已覆盖，也**不声称**缺失；需下一轮专门核对 |

**说明**：429/预算属于 external-provider 治理，与 W19 的 Q26 同源，当前既无实现也无授权；分页需要单独核对后才下结论。

## 14. W21/Q29 核对（安全解包）（2026-10-04）

### 14.1 路径穿越 —— **结构性不可达，且有测试**

`services/python-workers/document/worker_archive.py`：

- `:45` `UNSAFE_NAME = ("..", "/", "\\", ":")`
- `:51-53` 文档字符串写明：成员自己的名字可能含分隔符、可能是绝对路径、可能试图逃逸，**所以名字走在声明里，永远不走进路径**（"travels in the declaration, never in the path"）

也就是说这个 worker **列举/声明**归档成员，**不把成员名当路径写到磁盘**。zip-slip 因此在结构上不可达，而不是靠过滤侥幸挡住 —— 这比"检查后写入"更强。交付测试为 `tests/test_worker_archive_route.py`。

### 14.2 reparse point —— Core 侧有拒绝，但**不在归档面上**

`crates/archeaxis-application/src/scheduler.rs:114-138`：worker profile 路径**逐级祖先**检查，Windows 上按 `FILE_ATTRIBUTE_REPARSE_POINT (0x400)` 判定，任一祖先为链接即 `Unavailable("linked worker profile path")`。这是真实的重解析点防护，**但服务的是 profile 路径，不是归档解包**。

归档侧因为 14.1（不落盘）而不经过这条路径。**我没有验证归档面存在独立的 reparse 防护**，也不声称有。

### 14.3 压缩炸弹 —— **本轮未证实有防护**

在 `worker_archive.py` 内检索 ratio / expansion / 上限相关守卫，**没有找到压缩比或展开上限**。因为成员不落盘、只作声明，炸弹的经典危害（写满磁盘）面变小，但**"小体积声明出超大条目"是否被拒，我没有验证** —— 因此这一格记为 **NOT_VERIFIED**，不写成"已覆盖"。

### 14.4 原件保留 —— **本轮未核验**

未核验解包路径下原件是否保留（14.1 表明不落盘，但这与"原件是否被改动/删除"是两个问题）。记为 **NOT_VERIFIED**。

### 14.5 本节结论

Q29 的三项里：**路径穿越结构性达标且有测试**；**reparse 防护存在于相邻面而非归档面**；**炸弹与原件保留未验证**。按包内规则（未核实即 NOT_RUN，不写主观结论），本节只登记核实到的事实。

### 14.6 自我更正：14.3 说轻了

写完 14.3（"炸弹未证实有防护"）之后我取到了 `tests/test_worker_archive_route.py` 的完整用例名，证据**比我写的更强**：

| 测试 | 它固定的性质 |
| --- | --- |
| `test_a_nested_container_is_listed_but_not_opened` | **嵌套容器只被列出、不被打开** —— 递归展开（压缩炸弹的主要放大路径）在行为上被固定 |
| `test_the_receipt_says_it_is_an_inventory_not_the_contents` | **回执自己声明"这是清单，不是内容"** —— 正是 Q28/Q29 要的"不伪称全文导入" |
| `test_an_empty_container_is_refused_rather_than_reported_as_empty_success` | 空容器被**拒绝**，而不是报成"空成功" |
| `test_a_corrupt_container_fails_loudly` | 损坏容器**响亮失败**，不静默 |
| `test_the_inventory_is_one_line_per_member_with_line_anchors` | 清单逐成员一行并带行锚点 |

**更正后的准确表述**：Q29 在归档面上是「**不落盘**（穿越结构性不可达）+ **不递归展开**（炸弹放大路径被固定）+ **回执自陈是清单**」，三者都有测试。

14.3 里"未证实"的写法是在**证据不全时的保守**；准确的差别是：**没有"压缩比阈值"这一具体机制**，而不是"没有防护"。**"没有阈值"与"没有防护"不是一回事。**

我既不夸大也不缩小 —— **说轻了同样是失真**，所以这一节更正我自己上一节。仍保持 NOT_VERIFIED 的只剩 14.4 原件保留，以及 14.2 归档面是否有独立 reparse 防护。
