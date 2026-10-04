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

## 15. W21/Q30 核对（迁移幂等恢复）（2026-10-04）

任务包的验收是「**重复 / 取消 / 断电**后不重复造对象、**不覆盖用户编辑**」。核对结果如下。

### 15.1 已覆盖的三项

| 验收项 | 证据 |
| --- | --- |
| **重复不重复造对象** | `tests/runtime_jobs.rs:81` `http_runs_real_worker_and_replays_without_a_second_transform` —— **重放不会再跑一次转换** |
| **取消** | `tests/runtime_jobs.rs:181` `durable_ack_cancel_retry_and_parallel_budget_are_not_client_lifetime`；`:416` `waiting_admission_does_not_block_cancellation_of_an_owned_worker` |
| **断电/中断的等价场景** | `tests/runtime_jobs.rs:323` `disconnected_submitter_does_not_abandon_claimed_http_operation` —— 提交方断开**不会**让已认领的操作被抛弃 |
| 失败终写的诚实处理 | `:360` `unrecoverable_terminal_write_is_reported_unavailable_not_reaccepted_running` —— 终写不可恢复时报 `unavailable`，**不会**被悄悄重新接受为 running |
| 并发同键冲突 | `tests/contract_conflict_rules.rs:199` `an_execution_that_is_already_running_conflicts_with_a_second_key` |

### 15.2 **未核实**的一项：「不覆盖用户编辑」

「重复导入不得覆盖人类已编辑/已接受的对象」与 15.1 是**不同的性质**：15.1 证明的是**同一份工作不被重做**，而这一条要求的是**新的导入不得盖掉人对旧对象做出的修改**。

本轮我**没有**找到钉住这一条的测试，但我也**没有**穷尽检索（迁移面涉及 `app/`、`crates/archeaxis-migration`、vault 往返多处）。因此记为 **NOT_VERIFIED**：

- 不说它「已覆盖」—— 我没有证据；
- 也不说它「缺失」—— 我没有穷尽查。

下一轮把它作为**具体待办**：先穷尽检索迁移/导入路径上的「已接受对象 + 人类编辑」组合，再决定是补测试还是登记缺口。

### 15.3 本节结论

Q30 四项中**三项已覆盖且证据具体**（含重放不二次转换、断连不弃权、终写失败如实报 unavailable），**一项未核实**。「重复/取消/断电」这一组不是空白。

### 15.4 15.2 的「未核实」现在有答案了：**知识轴上结构性成立**

按 15.2 留下的待办去找「重新导入会不会盖掉人类编辑」，找到的是**决定性的结构事实**，而不是又一个测试。

**生产代码里对 `knowledge` 的唯一一条 UPDATE 是：**

```
crates/archeaxis-domain/src/knowledge.rs:453
UPDATE knowledge SET status=?1, receipt_hash=?2 WHERE knowledge_id=?3
```

**它只改 `status` 与 `receipt_hash`，从不改 `body`。** 新版本走 `:208` 的 `INSERT INTO knowledge(...)`，并以 `knowledge_supersedes` 记录取代关系（`contract_machine_answer.rs:154`、`contract_machine_retest.rs:337`，以及 W15 已钉住的 `supersedes`/`superseded_by` 投影）。

**所以「不覆盖用户编辑」在知识轴上是结构性成立的**：不是靠"导入时小心跳过已编辑项"这种容易漏的实现纪律，而是**根本不存在改写正文的语句**。重新导入只可能新增一行、由 `knowledge_supersedes` 指向旧行，**旧行与其正文原样保留**。

其余检索命中的 `UPDATE knowledge` **全部在测试里**（`SET status='deprecated'` 等），那是测试在构造前置状态，不是产品写入路径。

**仍不声称的部分**：本条覆盖的是**知识对象轴**。vault/导出往返、用户磁盘文件、导出再导入这条路径上的编辑保全**不在本条 SQL 的射程内**，我没有验证。

**15.2 的记账方式本身也要更正**：当时写"没找到测试、也没穷尽检索"是对的；现在正确的做法**不是补一个测试**，而是指出这条性质由**写入面结构**保证。补一个测试只能证明一个用例，而"**不存在任何能改写正文的语句**"是更强的证据 —— 强到不该被一条用例替代。

## 16. W20 分页核实（补上第 13 节留下的那一格）+ 发现一个真实缺陷（2026-10-04）

上一轮（§13.2）我把「分页」记为 **NOT_VERIFIED**，并写明「既不说已覆盖，也不说缺失」。本轮核实完毕。

### 16.1 事实

Core 内**唯一**与列表上界有关的读取，是语义检索的候选语料：

`crates/archeaxis-api/src/runtime/semantic.rs:38-49`
```sql
SELECT k.knowledge_id, k.body, ... FROM knowledge k
  LEFT JOIN anchors a ON k.anchor_id = a.anchor_id
  LEFT JOIN sources s ON a.source_id = s.source_id
WHERE k.status = 'accepted'
  AND NOT EXISTS(SELECT 1 FROM knowledge_supersedes x WHERE x.old_knowledge_id = k.knowledge_id)
ORDER BY k.knowledge_id LIMIT 129
```
返回的是一个**纯数组**，**没有任何字段说明语料被截断**。

其余全部 `LIMIT` 命中都是 `LIMIT 1`（取最新一行），与分页无关。

### 16.2 为什么这是缺陷，而不是"一个够用的上限"

当工作区有**超过 129 条**已接受且未被取代的知识项时，语义检索**只在前 129 条里检索**（且是按 `knowledge_id` 排序取前 129，不是任意 129），却把结果当作"检索了全部"返回。

这同时违反两条本项目已经确立的原则：

1. 任务包 Q27 明列的「分页」；
2. 本项目反复确立的「**不把截断渲染成全部**」—— 与「没有回执时 `coverage` 必须是 `null` 而不是 `0`」（`tests/job_quality.rs:88`）同源。

它比一个普通遗漏更糟：**用户无法从响应里知道自己这次检索是不完整的**。按本项目自己的标准，这与"把未保存伪装成已保存"属于同一类失真。

### 16.3 本轮只登记、不改代码 —— 并说明为什么

修法本身很清楚：**多取一行（130）判断是否触顶，并在响应里显式声明语料被截断与上限**。但它**改动响应形状**，需要先看清该路由的响应用例（`tests/contract_semantic_search.rs`）与 Desktop 端如何消费，才能一次改对。

在本轮预算内我没有把握一次做对，因此**只登记、不动代码**：宁可留下一个**有证据的缺陷条目**，也不要留下一个**半成品改动**。任务包的要求是未完成项显式登记，不是"看起来动过"。

**下一轮**：读 `semantic.rs` 的处理函数与 `contract_semantic_search.rs` 的响应断言 → 实现「多取一行判断触顶 + 显式声明」→ 补含 **>129 条语料**的契约用例 → 门禁与 CI。

## 17. 撤回 §16：那个「缺陷」不存在，是我读错了（2026-10-04）

**§16 登记的「语义语料 129 上限未声明」是错的。本节撤回它。**

我当时只读了 `snapshot()` 里的一行 `LIMIT 129` 就推断「静默截断」，**没有读它下面十行**。实际逻辑是：

```rust
// crates/archeaxis-api/src/runtime/semantic.rs:244-253
let candidates = match current(&runtime).await { Ok(v) => v, Err(r) => return r };
if candidates.len() > 128 {
    return error(
        StatusCode::CONFLICT,
        "semantic search capacity exceeded: more than 128 eligible knowledge items; \
         no partial corpus was ranked",
    );
}
```

`LIMIT 129` 的用途**恰恰是多取一行**：取到 129 就说明「超过 128 上限存在」，于是**拒绝服务并明说"没有对任何部分语料做排序"**。响应里还有 `complete` 与 `status`（`AVAILABLE` / `PARTIAL` / `UNAVAILABLE`），`candidates` 只在全部通过时才返回。

**这正是 §16 声称缺失的那种诚实行为。** 而我在 §16 里写成「用户无法从响应里知道自己这次检索是不完整的」—— **那是对一段正确代码的错误指控。**

**教训**：**读 SQL 不等于读行为。** 我从一行 `LIMIT` 推断出截断语义，却没有读它周围的判断。这和我第 7 轮批评过的「拿端口和自己比」是同类错误：**看到形状就下结论，没有验证语义**。

**§16 作废。** 分页这一格更正为：**语义检索对超限语料是显式拒绝（409 + 说明），不是静默截断 —— 属于已覆盖的诚实行为。** 我仍未核实的只剩「是否存在别的列表路由会静默截断」，而这一轮我没有穷尽检索，不声称。

## 18. 供体工具核实（W22 前置）（2026-10-04）

按 Owner 原话「缺少工具，先查权威路径记录，确定共用外置工具库和本地仓库里没有，再下载到共用外置工具库」，本轮完成**前置条件核对**：

| 核对项 | 结果 |
| --- | --- |
| 权威路径记录 | `docs/SHARED_RESOURCE_PATH_INDEX.md:11` `shared_tools = D:\All projects\OS External Configuration`；`:18` 说明 `10-toolchains` 是它的子目录，不是第六个工具库 |
| 共用外置工具库内 Anki / Notion / Obsidian / Zotero | **均不存在** |
| 本地仓库内供体程序 | 无 |

**所以「下载到共用外置工具库」的前提条件已满足 —— 但本轮未下载**（体积与时间超出本轮预算），如实登记为**未执行**，不写成"已准备"。

### 18.1 仓库已有先例，且它不是「装 GUI 应用」

`crates/archeaxis-archive/tests/obsidian_vault_roundtrip.rs`（R15）走的是**格式忠实的手工固定装置 + `PROVENANCE.txt` + 明确列出未覆盖项**，而不是调用 Obsidian 本体：

- `vault_root()` = `CARGO_MANIFEST_DIR/tests/fixtures/obsidian-vault`，**真实存在且已跟踪**：`PROVENANCE.txt`、`notes/index.md`、`notes/atomic.md`、`attachments/diagram.png`、`vault.canvas`；
- 文档字符串**主动列出四项未覆盖**（链接图未被吸收、无表存储关系、`.canvas` 语义图未存）。

### 18.2 需要 Owner 裁决的一个取舍

- **(A) 下载四个 GUI 应用**到 `shared_tools`：可支撑「真实应用打开我们的导出」这类断言；代价是数百 MB 与较长下载。
- **(B) 沿用仓库先例**：格式忠实的固定装置 + PROVENANCE + 明确缺口声明；无需下载，且与 Obsidian 既有做法一致。

**建议：先用 (B) 做格式级往返**（那是测试真正能断言的），把 (A) 留给「真实应用打开导出」这一条单独的人面向检查。

### 18.3 本轮第三次差点误报

我一度以为 `tests/fixtures/obsidian-vault` **既未跟踪也不在磁盘上**，并准备登记为缺陷。核对 `vault_root()` 后发现：该路径是**相对 crate 清单目录**解析的，真实位置在 `crates/archeaxis-archive/tests/fixtures/obsidian-vault`，**固定装置完整存在**。

**又是我看错路径。** 与上一轮的「假缺陷指控」同类：**没有读解析逻辑就下结论**。记录在此 —— 它说明核对的价值不在于我判断多准，而在于**我每次都去查了**。

## 19. 补上我自己验证口径里的一个缺口（2026-10-04）

**发现**：我一直写的「套件全绿」，用的是 `scripts/ci/cargo_test.bat -p archeaxis-api` —— **只测 api 这一个 crate**。而 CI 的 `cargo-test` 作业跑的是 `cargo test (workspace)`。也就是说：**`archeaxis-archive`、`archeaxis-domain`、`archeaxis-migration` 三个 crate 我从未跑过**，却一直把 CI 的绿当作自己的验证结果引用。

**本轮补跑（本地，GNU 工具链）**：

```
cargo test -p archeaxis-archive -p archeaxis-domain -p archeaxis-migration
```

结果：**全部通过**（含 `obsidian_vault_roundtrip`、domain 的 25 条、migration 的若干）。所以**没有隐藏的失败** —— 但**这是一个真实的验证口径缺口**：我引用的是别人的检查，不是我自己跑的。

**更正**：以后凡是我说"套件绿"，要么是 `-p archeaxis-api` **明说范围**，要么就是 workspace 级；**不再把 CI 的结果当成我本地跑过的**。

## 20. W22 方向分析（Obsidian 供体）（2026-10-04）

按仓库既有先例（**格式忠实固定装置 + PROVENANCE + 明确缺口**，已于 §18.1 记录），核对现有 Obsidian 往返到底证明了哪个方向：

`crates/archeaxis-archive/tests/obsidian_vault_roundtrip.rs` 的文档字符串自陈证明三件事、拒绝暗示第四件：

1. 字节与文件名在**导出/恢复进全新工作区**后存活 → 即 **Obsidian → AAOS → 导回** 两个方向都有覆盖；
2. 固定装置是**真 vault**（每条内部链接、标题锚点、块引用都在夹具内解析，不是假设）；
3. 链接在笔记抽取文本里**以文本形式**存活；
4. **明确不覆盖**：导入不写锚点、无表存链接/嵌入关系、`.canvas` 语义图未存。

**结论**：Obsidian 这一个供体**已经有真实的双向往返 + 显式缺口声明**，是 W22 的模板；**Anki / Notion / Zotero 目前一个都没有**。

W22 下一个切片的形状因此是明确的：**再做一个供体的格式忠实夹具 + 往返 + 缺口自陈**。按 §18.2，先走 (B)，GUI 应用那一步留给「真实应用打开导出」的单独人面向检查。

## 21. W22 供体方向矩阵（2026-10-04）

Q31/Q32 要求 **A-AAOS-A 与 AAOS-A-AAOS 两个方向**。本轮把四个供体的**实际方向覆盖**核清 —— 这是任何"往返已完成"声明的前提。

| 供体 | AAOS → A | A → AAOS | 证据 |
| --- | --- | --- | --- |
| **Obsidian** | ✅ 导出/恢复进全新工作区 | ✅ 导入 vault | `crates/archeaxis-archive/tests/obsidian_vault_roundtrip.rs`（含四项显式缺口） |
| **Anki** | ✅ `to_anki_csv`（Anki 可导入的 CSV） | ❌ **不存在** | 导出实现 `app/adapters/anki_zotero.py:25`；测试 `tests/test_adapters_longterm.py`、`tests/workers/test_bulk_legacy_adapters.py` |
| **Zotero** | ❌ 未见 | ✅ `parse_zotero_json`（库导出 → 知识单元） | 同两个测试文件 |
| **Notion** | ❌ | ❌ | 全仓无命中 |

**Anki → AAOS 方向**：`.apkg` 在 `crates/`、`services/`、`app/` 内**除夹具外零命中**；一个 `.apkg` 只会被 `archive.inventory` 当作**容器**清点（那是诚实的，但**不是**读取牌组）。

**本轮新增的事实**：`tests/fixtures/anki-apkg/review.apkg` 提供了该缺失方向**需要的地基**（一个真包），但**读取路径仍不存在**，所以**不声称往返** —— 与 `PROVENANCE.txt` 第 2 条一致。

### 两条必须同时说清的边界

1. `to_anki_csv` 产出的是 **CSV**，不是 `.apkg`。Anki 能导入它，但这条路径**未经 Anki 本体打开验证**（§18.2 的 (A) 项）。
2. Anki 的**笔记类型 / 选项组 / 排程语义在这一层完全没有被读写**。把 CSV 导入 Anki，会由 Anki 用**它自己的默认值**建卡 —— 与 `review.apkg` 里那组真实排程数字**无关**。这正是 **Q36 / W27「不伪造外来评分与调度」** 要单独处理的事，**不能**因为"有 CSV 导出"就当成已经覆盖。

## 22. 关于 59 个 SQLite 属主：审计脚本自己已经回答了该怎么办（2026-10-04）

上一轮我越界（在 `app/adapters/anki_zotero.py` 里 `sqlite3.connect`），`audit_first_wave_owners` 把属主数从 59 顶到 60，`CI` 失败，我选择**回滚而不是把数字改成 60**。本轮读了这个脚本本身，它**自己把这条判断说清楚了**：

```
scripts/ci/audit_first_wave_owners.py:1-6
"""Produce the source-only G0 inventory of direct SQLite connection owners.

This script deliberately does not import product modules or open a database.
It is an input to the language-boundary audit, not evidence of a runtime
writer and not authorization to change one.
"""
```

**所以：**

1. 这份清单是**只读盘点**，它**不导入产品模块、不打开数据库**；
2. 它**不是"运行时写入者"的证据**，也**不是"可以改一个"的授权** —— 这两句是脚本作者写的，不是我推断的；
3. 测试把 59 冻结住，是为了让**任何**新增属主都**先发出响声**。

因此正确做法**既不是"永远不许加"，也不是"把数字改掉"**，而是：**新能力必须落在既有的受 sanction 属主背后** —— 让"能开 SQLite 的模块集合"**不增长**。

**这使上一轮的回滚从"我的判断"升级为"脚本作者的明文规定"**：我当初没有授权去改那个数字，回滚是对的。

### 22.1 下一步的确切形状

Anki 读取器（`parse_apkg`，语义已在 §29 轮验证）应改为：

- **不在适配器里 `connect`**；
- 落在**某个已列入 59 的模块**背后，由它提供"读取一个**外来**只读 SQLite 字节串"的窄接口；
- 该接口必须显式标明**外来只读**（`:memory:` 反序列化，**不可能**写工作区库）；
- 保持上一版已验证的诚实语义：排程标 `imported_from_source`、未答过的卡**无间隔而非 0**、缺 collection **响亮拒绝**、单元内**不出现** `reviewed_by`/`graded_by`/`correct`/`mastery`/`score`。

**属主数保持 59。**

## 23. W29/Q38 核对（冲突 / 删除）（2026-10-04）

**先说检索可信度**：我先用两个**确知存在**的串校准（`superseded_by`、`knowledge_supersedes` 均有命中），确认检索有效，**再**下结论 —— 这是第 20/23/25 轮三次「grep 静默返回空」之后固定的做法。

### 23.1 「未见对象不是自动删除」—— **结构性成立**

| 检索 | 结果 |
| --- | --- |
| `DELETE FROM knowledge`（知识表本身） | **无命中** |
| `deleted_at` | **无命中** |
| `UPDATE knowledge` | **唯一一条**：`crates/archeaxis-domain/src/knowledge.rs:453` `SET status=?1, receipt_hash=?2`（**从不改 body**，见 §15.4） |
| 命中的 `DELETE` | 只有 `crates/archeaxis-domain/src/search.rs:51` `DELETE FROM knowledge_fts;` —— 那是 **FTS 索引重建**，删的是索引行，**不是知识** |

**结论**：知识在 Core 里**没有删除路径**。所以「没看到某个对象」**在结构上不可能**导致它被删除 —— 与 §15.4（不存在能改写正文的语句）同源，**比任何单条测试都更强**。

### 23.2 「三方差异与 tombstone」—— **未实现，且此处的 tombstone 是另一个意思**

`tombstone` 在本仓库中的含义与「对象删除标记」**无关**：

```
docs/truth/CAPABILITY_ATLAS_V2.yaml:6
tombstone_rule: "任何 capability 的删除、降级、改名、合并均需 Owner Decision 和可追溯映射…"
```

那是**能力图谱的治理规则**（消歧见 `docs/current/AAOS-20261004-E0-SCENE-RECEIPT.md:100`），**不是**同步用的 tombstone；其余命中为导入的设计文档。

**所以 Q38 的第二半（多源三方差异 + 对象 tombstone）不存在** —— 它属于多源同步能力，而该能力**尚未开始**。记为**未实现**，不记为缺陷。

### 23.3 一条不可互相冒充的边界

`supersedes` / `superseded_by`（W15 已钉）解决的是**同一工作区内的版本取代**，**不是跨源冲突消解**。两者**不可互相冒充** —— 前者是"我把旧的换成了新的"，后者是"两个来源对同一件事说了不同的话"。

## 24. W30/Q39 核对（Agent 边界）（2026-10-04）

### 24.0 先说校准本身的一次失败

我先用 `git grep -c 'approval' -- crates` 校准，**返回空** —— 差点据此判定「没有审批」。`git grep` 默认**区分大小写**，改用 `-i` 后审批**大量存在**。

**教训：校准失败时必须先修校准，不能用一次失败的校准去支持任何结论。** 这正是 §23 起我把"先校准"写进流程的原因 —— 而它这一轮**当场救了我一次**。

### 24.1 有实现、有证据的三项

| 项 | 证据 |
| --- | --- |
| **预算** | `crates/archeaxis-application/src/executor.rs:360` 与 `crates/archeaxis-sidecar-protocol/src/worker.rs:161` 校验 "invalid task identity, capability or budget"；`crates/archeaxis-api/tests/runtime_jobs.rs:181` 覆盖 parallel budget |
| **取消** | `runtime_jobs.rs:181`；`:416` 等待准入不阻塞取消 |
| **审批** | `app/evaluation/governance.py:27` `EvaluationApproval`；`app/knowledge/closed_loop.py:11,35` `KnowledgeLearningArtifactApproval` —— 审批记录携带 `reviewer_id` / `rationale` / `reviewed_at` |

### 24.2 「提示注入不得升级为系统指令」—— 要求在文档里，词表在实现里没有

```
docs/taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md:177
- prompt injection、网页命令、文档宏和模型输出永远不能升级为系统指令；
```

**但 `crates/`、`app/`、`shared/` 内没有 prompt injection 的实现词表。**

**结构上成立的部分**：模型输出进入知识层时**只能是 `candidate`**，且 `machine` actor **不能自我接受、不能复核**（W15 已钉，含生产 launch-token 路径）。所以「模型输出不能升级为系统指令」在**知识层是由写入面结构保证的** —— 与 §15.4、§23.1 同源：不是"我加了检查"，而是"**没有那条能让它升级的语句**"。

**仍未覆盖的部分**：该要求还涵盖**网页命令与文档宏**，那属于不可信摄入面。我**未核实**那条路径上的同等约束，因此**不声称** —— 用知识层的结论去覆盖摄入面，会是一次越界的推断。

### 24.3 步数上限 —— 不存在

`max_steps` / `step_limit` / `agent_run` 在 `crates`、`app`、`shared` 内**无命中**。记为**未实现**（不是缺陷：Agent Runtime 属被推迟的能力）。

## 25. W28/Q37 核对（权限不扩大）（2026-10-04）

**校准有效**（先用 `mime_type` 确认检索可用，再下结论）。

**两个词表陷阱必须先说清，否则结论会错**：

| 查的串 | 命中实际是什么 |
| --- | --- |
| `acl` | 来自 **`dataclass`** 的子串，**不是**访问控制 |
| `comments` | `shared/compat/models.py` 里的 **YAML frontmatter `# 注释` 保真**，**不是**源软件的评论 |

**两处都是"形状像、语义不同"**，与 §23.2 的 `tombstone` 同类 —— 这正是每轮先查语义而不是先信形状的原因。

### 25.1 源侧暴露边界：**未记录**

`shared/compat/import_session.py` 的 `compat_files` 表记录的是：

`relative_path` · `source_hash` · `file_size` · `frontmatter_json` · `body_hash` · `is_canvas` · `is_binary` · `mime_type` · `imported_at`

**没有任何字段**记录源的可⻅性/ACL、源评论、源修订历史是否被暴露或吸收。所以「**源 ACL / 评论 / 历史暴露边界**」这一项**未实现**。

### 25.2 「权限不扩大」的**结构现状** —— 一个必须精确的区分

兼容层只是把文件读进来并记入 `compat_files`，**它不分配任何目标侧权限**。

因此「不扩大权限」目前**不是被保证的，而是因为还没有权限概念**。这两者**不同**：

- 前者是**设计上的保证**（有人写下了规则并让它可验证）；
- 后者是**空白**（没有规则，因为没有被规则约束的东西）。

**不能把空白说成保证。** 我说的是后者。

### 25.3 目标权策略：**NOT_VERIFIED**

我**没有穷尽检索** `docs/` 里的目标权策略文档，所以**既不声称有、也不声称无** —— 记为未核实。

## 26. 一个验证完整性隐患：脚本方式运行会加载**根仓库**的代码（2026-10-04）

**发现经过**：为 Q37 加上 `source_context` 列之后，我用**脚本文件**验证，却报 `no such column: source_context`。诊断结果：

```
module file: D:\All projects\ArcheAxis-Knowledge-OS\shared\compat\import_session.py
```

**加载的是根仓库，不是本工作树。**

**机制**：`python <script.py>` 会把**脚本所在目录**放到 `sys.path[0]`。我把脚本写在 `.project-local/runs/`，于是**工作树根不在解析路径上**，而共用 CI venv 已把**根仓库**配了进去 —— 根仓库的 `shared` 因此胜出。

| 调用方式 | 实际解析到 |
| --- | --- |
| `python .project-local/runs/x.py` | **根仓库**（错） |
| `Set-Location <worktree>` + `python -c "..."` | **工作树** ✅ |
| `pytest`（rootdir = 工作树） | **工作树** ✅ |

**含义**：**用脚本文件方式验证，可能在一棵"不是我正在改的树"上得到绿色。** 这与 §19（把 CI 的验证当成我自己的）属于**同一类验证完整性缺陷** —— 只不过这次是"**跑对了命令，跑错了目标**"。

**纪律（即刻生效）**：在本工作树内验证，只用 `pytest`，或 `python -c`（cwd = 工作树根）；**脚本文件必须放在工作树根内**。若确有脚本，必须显式打印并断言 `module.__file__` 指向工作树。

**本次改动经复核未受影响**：

- `git diff --stat` 显示编辑确实落在工作树文件（11 insertions / 1 deletion）；
- cwd = 工作树时，`shared.compat.import_session.__file__` **指向工作树**，且 `"source_context" in _SCHEMA` 为 **True**；
- `pytest tests/test_compat_kernel.py` → **9 passed / 1 skipped**。

### 26.1 顺带落地的 Q37 改动

`compat_files` 新增一列（含迁移，沿用既有 `ALTER TABLE` 模式）：

```sql
source_context TEXT NOT NULL DEFAULT 'acl,comments,history:not_recorded'
```

含义：兼容层读取源文件时**没有**采集"谁能看、带了什么评论、有什么修订历史"，这一边界现在**被写下来是"声明为未记录"**，而不是留白。列默认值承担它，所以**没有插入语句需要记得说这件事** —— 让"忘记声明"在结构上不可能。

## 27. W23/Q33 核对（复杂数据库）+ 一处「未承载」的显式声明（2026-10-04）

校准有效。**五个方面里的三个已有实现**：

| 方面 | 状态 | 证据 |
| --- | --- | --- |
| **视图** | ✅ | `shared/collection_views.py` —— table / board / calendar / gallery / list |
| **公式** | ✅ | `app/ingestion/xlsx_adapter.py:35-39` —— 公式单元格**保留公式文本**并标 `is_formula`、带稳定锚点（**不假装求出了值**） |
| **汇总 rollup** | ✅ | `shared/collection_views.py:180` `aggregate()` |

| 方面 | 状态 |
| --- | --- |
| **属性类型** | ❌ **未建模** —— `_render_table(items, columns)` 里的 column 是 dict 的键，**不是有类型的属性** |
| **关系 relation** | ❌ **未建模** —— `shared/compat` 内无 relation 词表；视图只按字段分组/过滤 |

### 27.1 改动：把「未承载」写出来

`render_view` 的返回新增 `not_carried`，显式声明**没有承载**的东西：

```python
data["not_carried"] = [
    "property_types: a column is a dict key, not a typed property",
    "relations: links between items are neither modelled nor stored",
]
```

理由与 §26.1（Q37）同：**未言明的缺席会被读成「源本来就没有这些东西」** —— 而一个空视图**最不该**暗示这个。

### 27.2 验证纪律（第 36 轮新规首次执行）

本轮**打印了 `module.__file__`** 并确认解析到**工作树**：

```
module: D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\dsh-backend-loop-20261001\shared\collection_views.py
```

`pytest tests -k "collection or view"` → **189 passed / 4 skipped**。

## 28. W25/Q35 核对：本轮**真机端到端跑了一次**（2026-10-04）

**执行**（本轮、本分支，含我这些轮的全部改动）：

```
python scripts/probes/r10_core_journey_smoke.py     -> exit 0
```

它 **spawn 真实 Core 进程**（`archeaxis-api <db> 0` + stdin launch JSON），全程走**真实 HTTP**：

| 步骤 | 方法 | 路径 | 状态 |
| --- | --- | --- | --- |
| reachability | GET | `/api/v1/system/version` | 200 |
| import | POST | `/api/v1/imports` | 202 |
| enqueue | POST | `/api/v1/jobs` | 202 |
| execute | POST | `/api/v1/jobs/{id}/executions` | 202 |
| job_status | GET | `/api/v1/jobs/{id}` | 200 ×2 |
| output | GET | `/api/v1/jobs/{id}/outputs/text` | 200（`readable`） |
| search | GET | `/api/v1/search?q=6371` | 200 |

`transform_count: 1` · `knowledge_count: 0` · `core_port: 54432`

**收据**：`.project-local/runs/2611ed9ca1/1e82a3abc6f6/artifacts/r10-smoke/6082014ae21f41e4a14338d3c33d93c9/r10-core-conversion.json`

### 28.1 但它**自己声明没有验证闭环** —— 我不改这个结论

```json
{"ok": true, "scope": "real_conversion_probe", "closed_loop_verified": false, ...}
```

**本次跑通的是「来源 → 转换 → 输出回读 → 检索」，不是闭环。** 依据：`knowledge_count: 0`（未产生已接受知识），且**没有任何学习步骤**。

**Q35 要求的是**：来源 → 讲解/练习 → **作答** → **反馈** → **学习记录回读**。**本次未覆盖。**

把这次说成「学习链已跑通」会是**最容易犯、也最严重的一次失真** —— 连探针自己都写了 `closed_loop_verified: false`。**我不越界。**

### 28.2 本轮的实际价值

- **新鲜的实跑证据**：本轮、本分支，包含 W06 mastery、首页进展卡片、复习状态行、归档回执、compat `source_context`、`collection_views` 的全部改动；
- **真实进程 + 真实 HTTP + 真实 worker 转换**；
- 输出**可读回**（`output_status: readable`）且**可检索**；
- 并**明确划出它没有证明的那一段**。

**学习链需单独做**：在同一收据上继续走 知识接受 → 复习调度 → 作答 → 学习事件 → item state 回读（那正是 W06 已覆盖的接口）。

## 29. W25/Q35 续：**历史学习链收据已因设计而失效**（2026-10-04）

§28 我说「学习链要单独做」。本轮查清了**为什么不只是"没做"，而是"曾经做过又被明确收回"**。

### 29.1 历史收据（taskpack-0910-r3）确实记过一次真实学习链

`docs/authority/taskpack-0910-r3/EXECUTION.md:52`（R10d）记载的真实 Core 冒烟收据是：

```
reachability 200 -> import 202 -> search 200 (count 1)
  -> learning_event POST /learning/events   -> 201
  -> reference     POST /learning/items/card-smoke/references -> 201
```

即**当时那次实跑是走过学习事件与引用的**。

### 29.2 但今天的 `run_journey` 已经**明确不再是学习旅程**

`shared/core_client.py:132-148` 的文档字符串自己写着：

```
"""Probe reachability, source storage and existing search results only.

Kept under its historical name for callers. This is not a cold-start learning
journey: it neither parses the imported source nor proves that search hits
derive from it. Never invent an answer or write learner progress. The legacy
item/event arguments remain accepted for compatibility, but are unused.
"""
```

**所以那条历史收据是"因设计而失效"的**：函数被有意收窄，参数保留只为兼容，**已经不再使用**。

**全仓检索 `run_journey` 的调用者**：只有 `docs/` 与 `STATE.json` 里的记载，**没有任何现存代码调用它**。今天真实在跑的是 `run_conversion_journey`（§28 的收据）。

这又是本项目那个反复出现的动作：**把一句过度的声明收回**，并在文档字符串里写清它现在到底做什么。

### 29.3 Q35 的准确状态

| 项 | 状态 |
| --- | --- |
| **转换链**（来源→转换→输出回读→检索） | ✅ **本轮真机跑通**（§28，exit 0） |
| **学习链**（来源→讲解/练习→作答→反馈→学习记录回读） | ❌ **没有任何 live 端到端证据** |
| 学习链的**接口** | ✅ 存在：`/learning/events`、`/learning/items/{id}/state`、`/learning/reviews`（W06 已钉幂等与投影） |
| 驱动这些接口的**编排器** | ❌ 不存在。`core_client` 只有**请求构造器**（`learning_event_request` / `reference_request` / `review_request`），**没有把它们串起来的旅程** |

**所以「有接口」不等于「有旅程」** —— 这两件事必须分开说，否则会把"接口齐备"读成"链路已验证"。

**下一步（形状已定）**：写一个真正驱动学习链的探针 —— 起真实 Core → 造一条 accepted 知识 → `learning/events` → `learning/items/{id}/references` → 复习 → 读 `item state` 回执；**并明确它不做人类审校**（审校永远是人做的事，`run_journey` 的历史文档字符串早已把这条写成原则）。

## 30. W25/Q35 学习链：**本轮真机跑通**（2026-10-04）

新增 `scripts/probes/r10_learning_chain_smoke.py`，起**真实 Core 进程**（launch JSON 走 stdin、读就绪行取端口），全程**真实 HTTP**：

| 步骤 | 方法 | 路径 | 状态 |
| --- | --- | --- | --- |
| reachability | GET | `/api/v1/system/version` | **200** |
| **accepted_fact** | POST | `/api/v1/knowledge-items` | **201** |
| **learning_event** | POST | `/api/v1/learning/events` | **201** |
| **reference** | POST | `/api/v1/learning/items/card-learning-smoke/references` | **201** |
| **item_state** | GET | `/api/v1/learning/items/card-learning-smoke/state` | **200** |

`knowledge_id: k_689b9ae35192afc9e58b73b2` · `state_keys: ["item_key","learner","machine"]` · `core_port: 49244` · **exit 0**

**收据**：`.project-local/runs/2611ed9ca1/36d0ee9737d6/artifacts/r10-learning/8e9f46e6412748d1a232819e0b0b8df5/r10-learning-chain.json`

**解析确认**（第 36 轮纪律）：`module: ...worktrees\dsh-backend-loop-20261001\shared\core_client.py` —— 用的是**本工作树**。

### 30.1 探针**自己声明**它没覆盖什么

```json
"scope": "real_learning_chain_probe",
"not_covered": ["human knowledge review", "answer and feedback pair"]
```

- **不做人类审校**：`core_client.review_request` 覆盖 accepted/rejected/deprecated/modified，那是**人的动作**；一个旅程自己去做它，等于**给自己判分**。
- **不做作答/反馈对**：那需要 assessment 路径，本切片未覆盖。

**所以这次跑通的是**：来源（已接受事实）→ 学习事件 → 依据修订的引用 → 物品状态回读。
**仍未跑通的是**：讲解/练习的呈现、作答、反馈。两者**分开陈述**。

### 30.2 一次自我纠正：猜形状产生的两个 null

第一次运行时我**猜**了 state 的 JSON 形状，抽出 `known_reference` 与 `state_status`，两者都是 `null`。

**危险之处**：`known_reference: null` 会被读成「**该物品没有已知引用**」—— 而事实是**我的抽取写错了**，不是数据没有。

已改为记录 `state_keys`（**读到的真实键名**，`["item_key","learner","machine"]`），并在代码注释里写明原因。**猜出来的字段比没有字段更危险**，因为它长得像证据。

## 31. W25/Q35 学习链**全段真机跑通**（2026-10-04）

在 §30 的探针上补齐 **assessment** 与 **answer** 两步，真实 Core 全程 HTTP，**exit 0**：

| 步骤 | 方法 | 路径 | 状态 |
| --- | --- | --- | --- |
| reachability | GET | `/api/v1/system/version` | 200 |
| accepted_fact | POST | `/api/v1/knowledge-items` | 201 |
| learning_event | POST | `/api/v1/learning/events` | 201 |
| reference | POST | `/api/v1/learning/items/card-learning-smoke/references` | 201 |
| **assessment** | POST | `/api/v1/learning/items/card-learning-smoke/assessment` | **201** |
| **answer** | POST | `/api/v1/learning/reviews` | **201** |
| **item_state** | GET | `/api/v1/learning/items/card-learning-smoke/state` | **200** |

### 31.1 反馈是**真实读到的**，不是我猜的

作答的 201 回执就是这个链的**反馈**。我记录它**实际携带的键名**：

```
answer_keys:      ["answer","duplicate","event_id","mastery_projection","next_review",
                   "next_review_days","schedule_authority","schedule_state","streak_after"]
assessment_keys:  ["anchor_id","assessment_id","content","created_at","item_key","knowledge_id",
                   "knowledge_version","question","source_id"]
state_keys:       ["item_key","learner","machine"]
```

即：**排程**（`next_review` / `next_review_days`）、**投影**（`mastery_projection`，W06 的派生字段）、**连续答对**（`streak_after`）、**幂等标记**（`duplicate` / `event_id`）；题面（`question`）并挂到 `knowledge_version` / `anchor_id` / `source_id`。

### 31.2 仍然只排除一件事，且理由不变

```json
"not_covered": ["human knowledge review"]
```

**人类审校**仍然不在旅程里 —— `review_request` 覆盖 accepted/rejected/deprecated/modified，**一个旅程自己去做它，等于给自己判分**。这一条从 R10 起就是原则，我不动它。

### 31.3 与 §28 的对照

| 链 | 状态 |
| --- | --- |
| 转换链（来源→转换→输出回读→检索） | ✅ §28 真机，exit 0 |
| **学习链（来源→题面/依据→作答→反馈→状态回读）** | ✅ **本节真机，exit 0** |
| 人类审校 | ❌ **不在任何旅程内，且不应在** |

## 32. 把两条实跑探针纳入门禁（2026-10-04）

§28 与 §31 的两条链是**手工驱动**的。手工证据有个隐患：**Core 一旦回归，探针会静默失效，而收据仍写着通过** —— 与我在 §19 承认过的「把 CI 的验证当成我自己的」是同一类问题，只是方向相反。

新增 `tests/test_live_chain_probes.py`（2 条），把两条探针**按原样跑起来**并断言它们**实际输出的收据**：

| 断言 | 意义 |
| --- | --- |
| `ok is True` 且 `failed_step is None` | 每一步都真的成功 |
| 转换探针 `scope == "real_conversion_probe"` 且 **`closed_loop_verified is False`** | **它必须继续拒绝认领闭环** —— 若哪天变了，收据必须被重读 |
| 学习探针 7 步齐全且状态均 2xx | reachability / accepted_fact / learning_event / reference / assessment / answer / item_state |
| `next_review`、`mastery_projection` 在 `answer_keys`；`question` 在 `assessment_keys` | 反馈与题面是**读到的**，不是猜的 |
| **`not_covered == ["human knowledge review"]`** | 人类审校**永远不得**进入旅程 |

**没有内建 Core 的检出会 skip**（并写明理由）—— **跳过的探针是诚实的，编造的通过不是**。

本轮**未对这条门禁本身做反例验证**（即未故意破坏探针确认它会失败）。如实记录，不声称做过。它的断言取自真实输出中已观察到的具体值（步骤名、状态码、键名、`not_covered`），不是我构造的常量。

## 33. 补上 §32 承认的缺口：门禁**已被证明会失败**（2026-10-04）

§32 我写明「本轮未对这条门禁做反例验证」。本轮做了。

### 33.1 反例：让探针**少报它没做的事**

把学习探针的声明从

```json
"not_covered": ["human knowledge review"]
```

改成 `"not_covered": []`，然后跑门禁：

```
FAILED tests/test_live_chain_probes.py
       ::test_the_learning_chain_still_runs_and_still_excludes_human_review
1 failed, 1 passed
```

**失败精确落在应守的那一条上**（人类审校不得进入旅程），另一条（转换探针）**不受影响** —— 说明断言是**针对性的**，不是一起塌。

### 33.2 复原后

```
tree restored, CLEAN
2 passed
```

**所以这条门禁不再只是「看起来在守」：它被观察到会失败，且失败在正确的位置。**

反例只在工作区临时施加，随后 `git checkout` 复原 —— **仓库中没有任何残留改动**。

这与 §32 那条缺口的区别很关键：**"我认为它会失败"和"我看见它失败"是两回事**，而我上一轮只做到了前者。

## 34. W26/Q36 补：Anki 读取器**声明它没承载什么**（2026-10-04）

§31 的读取器已带出笔记类型、字段、排程与依据来源，但**没有带出牌组与选项组**（学习步长、间隔、难度系数），而且**没有说**。

一个被导入的单元因此会被读成「源知道的就这些」。已补：

```python
"not_carried": [
    "deck_options: the learning steps, intervals and ease the collection scheduled with",
    "deck_names: the deck an item belonged to",
]
```

与 §26.1（Q37 源侧上下文）、§27.1（Q33 未承载的数据库特性）**同一手法**：**把空白变成声明为空白**。

实测（含第 36 轮纪律）：

```
module: ...worktrees\dsh-backend-loop-20261001\shared\compat\import_session.py
not_carried: ["deck_options: ...", "deck_names: ..."]
20 passed, 1 skipped
```

## 35. W31/Q40：把真机收据**绑定到 SHA 并放进仓库**（2026-10-04）

### 35.1 我自己证据里的一个真实缺口

§28 与 §31 的探针把收据写进 `.project-local/runs/<run>/...` —— 那是**被忽略且不保留**的目录。

**含义：我在收据里引用的那些路径是短暂的。** 运行目录一旦被清理，引用就指向不存在的东西。这正是 Q40 说的「**回归要对应真正集成 SHA/构建，不借旧成绩**」的反面 —— 证据没有绑在任何可持久的东西上。

### 35.2 已补：`scripts/probes/refresh_live_chain_receipts.py`

它跑两条探针，把结果写进**被跟踪**的 `docs/current/receipts/LIVE-CHAIN-RECEIPTS.json`，其中包含：

| 字段 | 值 |
| --- | --- |
| `schema` | `archeaxis.live-chain-receipts/v1` |
| `commit` / `tree` | 运行时的 `HEAD` 与 tree 哈希 |
| `worktree_state` | 运行时工作区状态（**不干净就如实写**） |
| `chains.conversion` | `ok=True steps=8 scope=real_conversion_probe` |
| `chains.learning` | `ok=True steps=7 scope=real_learning_chain_probe` |

**绝对路径被剥离**（`receipt_path` 移除）—— **检出放在哪里不是证据**。

### 35.3 一个必须说清的关系

这次运行时 `worktree_state` 是 `?? scripts/probes/refresh_live_chain_receipts.py` —— 因为**脚本本身当时还没提交**。所以：

- 收据里记录的 `commit` 是**运行时的 HEAD**，也就是本提交的**父提交**；
- 收据文件本身由**紧随其后的提交**（本提交）携带；
- **我没有把 `worktree_state` 洗成 "clean"** —— 它当时确实不干净，如实写下来。

**这是一个结构性事实，不是隐瞒**：收据不可能在自己被提交前知道自己所在的提交哈希。

## 36. W32/Q41：回执与**真实提交**一一对应（2026-10-04）

新增 `tests/test_live_chain_receipt_matches_a_real_commit.py`（6 条），把 45 轮的持久收据**钉到真实历史上**：

| 断言 | 意义 |
| --- | --- |
| `schema` / `commit` / `tree` 长度、`worktree_state` 存在 | 收据必须自陈它是哪一次运行 |
| `commit` **确实存在于本仓库**，且记录的 `tree` **就是该提交的 tree** | 名字对不上树 = 证据没有到达状态 |
| `commit` 必须是 `HEAD` 的**祖先** | **来自没人能到达的分支的证据，不是这条工作线的证据** |
| 两条链 `ok`、`failed_step` 为空、`scope` 不变、**每步均 2xx** | 状态与步骤逐条对应 |
| 转换链仍 `closed_loop_verified is False`；学习链仍 `not_covered == ["human knowledge review"]` | 两条"不认领"的声明必须保持 |

### 36.1 反例：第一次**没有真正跑起来** —— 这比没有反例更糟

第一次反例我用**相对路径**改写收据，PowerShell 把它解析到了**根仓库**，于是：

```
[System.IO.File]::ReadAllText($p)  ->  未能找到路径 ...\ArcheAxis-Knowledge-OS\docs\...
```

**文件从未被改动**，而那一次门禁报的是 `6 passed` —— 也就是**未改动文件的通过**。

**如果我就此写"门禁已被证明会失败"，那会是一次纯粹的编造。** 我看到了 stderr 才没这么写。

> **一个没有真正运行的反例，比没有反例更糟 —— 它会制造信心。**

### 36.2 用绝对路径重做（真正跑起来了）

```
content changed by patch: True
FAILED ...::test_the_receipt_declares_its_schema_and_the_commit_it_ran_against
FAILED ...::test_the_named_commit_exists_and_its_tree_is_the_recorded_tree
2 failed, 4 passed
==== RESTORE ====
tree restored, CLEAN    ->    6 passed
```

失败**精确落在应守的两条上**（schema/tree 长度、tree 与提交不符），其余四条不受影响。

## 37. 按任务包**权威行表**重核：发现两行我漏了（2026-10-04）

§46 我写下「任务包中不需要 Owner 决定、不需要下载供体、不属于现场 UI owner 的条目已全部核对或落地」。

**本轮我回去读了任务包自己的行表（Q01–Q42），发现那句话太宽了 —— 有两行我从未核对过。**

| 行 | 验收主题 | 我此前的状态 |
| --- | --- | --- |
| **Q18 / W15** | `expected_version` 不符**拒绝**并保留历史 | **未核对** |
| **Q20 / W16** | 进入页读取**不写事件、不消耗卡片** | **未核对** |

**教训**：**"我已经把能做的都做了"是最容易说出口、也最该去查证的一句话。** 我用了 46 轮才想到去读那张权威表本身。

### 37.1 Q18：**机制不存在**

校准有效（用两个已确知存在的串 `knowledge_supersedes` / `learning_events` 确认检索可用）后：

```
git grep -in "expected_version|version_conflict|stale_version|precondition" -- crates
->  NO version-competition guard vocabulary anywhere in crates
```

**`expected_version`、`version_conflict`、`stale_version`、`precondition` 在 `crates` 内全部零命中。**

所以验收「`expected_version` 不符拒绝并保留历史」**目前没有任何机制**。记为**未实现**。

（⚠️ 一处诚实的自我提醒：我第一次"校准"用的串是 `expected_version` 本身 —— **那是我假设存在的，不是确知存在的**，所以那次校准什么都没校准。改用确知串后结论才成立。）

### 37.2 Q20：**结构性成立**

三个学习读取处理器 `learning_history`（`lib.rs:202`）、`learning_items`（`:250`）、`item_state`（`:305`），在各自行范围内检索：

```
INSERT | UPDATE | DELETE | submit_wait | execute   ->  (no write keywords)
```

**三个处理器里没有任何写入语句。** 所以「进入页读取不写事件、不消耗卡片」**在结构上成立** —— 与 §15.4（没有语句能改 body）、§23.1（没有语句能删知识）、§24.2（没有语句能让模型输出升级）**同源**：不是"我加了检查所以不会写"，而是"**没有那条能写的语句**"。

**边界（不声称的部分）**：我核对的是**这三个处理器自身**；**没有排除**写入藏在他们调用的某个 helper 里。这一点我没有查，因此不说"不可能"。

## 38. Q04 复核：**未验证**，并拦住一次假缺陷（2026-10-04）

Q04 的验收是「每个 required 能力在候选位置**真正可调用**」。本轮尝试真实组装候选后核对，**没有完成**，原因具体：

```
python scripts/release/assemble_green_candidate.py --desktop <build> --core <exe> \
    --workers services/python-workers --out <dir> --version 0.0.0-q04candidate
->  ValueError: workers require a staged runtime
```

`--workers` 必须配 `--runtime`（由 `scripts/release/stage_backend_runtime.py` 先产出的**已暂存运行时**）。**本轮没有产出该运行时，所以组装失败。**

### 38.1 必须拦住的那一步

组装失败后，我的解析检查跑在**一个空目录**上，输出：

```
worker files resolved: 0
missing or empty: 13
   MISSING archive.inventory workers\document\worker_archive.py
   ...
```

**这 13 行是组装失败的产物，不是"13 个能力缺失"。** 如果我把它们抄进收据当作发现，那就是**又一次对正确代码的错误指控** —— 与第 20 轮我撤回的那次同类。

**所以 Q04 记为 NOT_VERIFIED**，并记下确切阻塞：**需要先暂存后端运行时**。

### 38.2 已经知道的部分（不等于 Q04）

- W04 已证明**清单单源**且**清单里每个脚本在源码树中存在**（`tests/test_worker_route_lists_agree.py` 断言 "scripts exist"）；
- W13 的能力台账把 16 个批准能力与运行时路由联起来；
- **但"在候选位置真正可调用"是另一件事**，它要求在**组装后的布局**里验证 —— 本轮未做到。

**"源码树里存在" ≠ "候选里可调用"**，这两件事同样不能互相冒充。

## 39. Q04 补齐：**13/13 能力在候选内解析成功**（2026-10-04）

§38 的阻塞（`workers require a staged runtime`）已解决：**运行时取自共用外置工具库**，不碰 Green。

```
--runtime "<shared_tools>\10-toolchains\python\python\cpython-3.12.13-windows-x86_64-none"
stage_backend_runtime.py   -> exit 0   (files: 2799)
assemble_green_candidate.py -> exit 0   (root + zip)
```

### 39.1 Q04 的结论

```
candidate root: ArcheAxis.Knowledge.Green-v0.0.0-q04candidate-x64
declared capabilities: 13
workers resolved in the candidate: 13
missing or empty: 0 []
```

**清单声明的 13 个能力，其 worker 在候选布局 `<root>/workers/<script>` 下全部存在且非空**（同一份也在 `<root>/runtime/workers/<script>` 下）。

**Q04 的"解析"这一半达标。** 仍未做的是**逐能力真实调用**（那需要为每个能力喂一份真实输入并观察回执）—— 我**不把"文件在"说成"已调用"**。

### 39.2 又一次"看错路径"，以及我没有据此下结论

第一次核对报 `missing or empty: 13` —— 因为我把**候选父目录**当成了候选根；真实根是带版本号的那个子目录。

```
candidate-q04b\                                  <-- 我看的
candidate-q04b\ArcheAxis.Knowledge.Green-v...\   <-- 真实根
    workers\  core\  desktop\  runtime\  shared\
```

**这是本会话第三次因路径看错而险些产生假缺陷。** 我没有把那 13 行写进收据。

### 39.3 一个**未核实**的布局事实（不声称是缺陷）

运行时内部还有一层：

```
<root>\runtime\           <-- 候选内的运行时根
    runtime\python.exe     <-- 解释器实际在这
    workers\  core\  shared\
    start-backend.cmd / start-backend.py / worker-profile.json
```

而生成的启动器里写着 `ARCHEAXIS_PYTHON = root & "\runtime\python.exe"`。**它能否解析正确，取决于该脚本里 `root` 指的是哪个目录** ——

- 若 `root` = 候选根 → 指向 `<root>\runtime\python.exe`，**不存在**（实际在更深一层）；
- 若 `root` = 运行时根 → 指向 `<root>\runtime\runtime\python.exe`，**正确**。

**我没有读该脚本里 `root` 的定义，所以我不说这是缺陷。** 记为**未核实**，并写明判据 —— 这是第 20 轮那次假指控之后我固定下来的做法。

## 40. §39.3 的判据已读：**这是一个真实缺陷**（2026-10-04）

§39.3 我写明「判据是读该脚本里 `root` 的定义，我没读，所以不说是缺陷」。本轮读了：

```vbs
root = files.GetParentFolderName(WScript.ScriptFullName)          <- 候选根
executable                                   = root & "\desktop\ArcheAxis.Desktop.exe"
shell.Environment("PROCESS")("ARCHEAXIS_CORE_BIN") = root & "\core\archeaxis-api.exe"
shell.Environment("PROCESS")("ARCHEAXIS_PYTHON")   = root & "\runtime\python.exe"
```

**`root` 就是候选根**（该 vbs 自己所在的目录）。对照组证实这一解读：

| 启动器设置的路径 | 实际存在？ |
| --- | --- |
| `<root>\core\archeaxis-api.exe` | **True** |
| `<root>\desktop\ArcheAxis.Desktop.exe` | **True** |
| `<root>\runtime\python.exe` | **False** |
| `<root>\runtime\runtime\python.exe` | **True** |

**所以这是真实缺陷**：前两条按候选根解析正确，**唯独解释器那条指向不存在的路径**。

### 40.1 病根与边界

**病根**：组装把**已暂存运行时**整个放进 `<root>\runtime\`，而那份暂存运行时**自身内部还有一层 `runtime\`** 放着解释器 —— 于是解释器落在 `<root>\runtime\runtime\python.exe`，而启动器期望 `<root>\runtime\python.exe`。

**边界（不声称的部分）**：我**没有运行该启动器**。这是**路径解析层面**的判定（`Test-Path` 对同一 `root` 基准下的三条路径给出 2 True / 1 False），**不是运行期观察到的失败**。要说"启动必定失败"还需要实跑一次。

## 41. **撤回 §40**：那不是缺陷，是我传错了参数（2026-10-04）

**§40 登记的「候选启动器 `ARCHEAXIS_PYTHON` 指向不存在的解释器」是错的。本节撤回它。**

### 41.1 我错在哪

暂存器的输出目录长这样：

```
backend-runtime-q04\            <-- 我传给了 --runtime
    runtime\python.exe           <-- 解释器在这（真正的运行时根）
    core\  shared\  workers\  start-backend.cmd  ...
```

**真正的运行时根是 `<staged>\runtime`，而我传的是 `<staged>`。** 组装器把传入目录的**内容**铺到 `<root>\runtime\` 下 —— 传错一层，解释器就落深一层。

### 41.2 决定性实验

改用 `--runtime <staged>\runtime` 重新组装：

```
candidate runtime\python.exe          -> True
candidate runtime\runtime\python.exe  -> False
```

**启动器与组装器都是对的**（`worker-profile.json` 里的 `"python": "runtime/python.exe"` 也是对的）。**错的只有我的调用。**

### 41.3 为什么我的"对照组"没有拦住我

§40 我用对照组证明 `root` = 候选根：`core\archeaxis-api.exe` 与 `desktop\ArcheAxis.Desktop.exe` 都存在、唯独 `runtime\python.exe` 不存在。

**对照组是有效的，但它证明的是"我对这个产物的读法没错"，而不是"我把这个产物造对了"。**

> **我拿一个自己造错的候选，去证明启动器写错了路径。**

这是本会话**第四次**因路径产生错误结论 —— 但前三次我都在写入收据前拦住了，**这一次我已经把它作为"真实缺陷"提交并推送了**。所以必须显式撤回。

### 41.4 有效的部分仍然有效

- **Q04 的解析结论不受影响**：13/13 能力在候选内解析成功（那份候选的 workers 目录是对的，传错的是 runtime）；
- `runtime\python.exe` 这一层判据本身没错，错的是**基准候选**。

### 41.5 新增的纪律

**对照组的有效性，取决于被测产物本身是不是按正确方式产生的。** 以后凡是用一个**我自己组装的产物**去证明"产物有问题"，必须先确认**组装调用本身**符合该工具的参数契约（读它给出的文档字符串/清单，而不是凭目录长相推断）。

## 42. 正确组装的候选：**静态一致**（2026-10-04）

§41 用 `--runtime <staged>\runtime` 组出了正确的候选 `candidate-q04c`。本轮核它的静态一致性：

```
candidate root: ArcheAxis.Knowledge.Green-v0.0.0-q04c-x64
capabilities declared: 13 | workers resolved: 13
profile declares python as: runtime/python.exe
  -> resolves inside the candidate: True | runtime\python.exe
```

**三方互相印证**：清单声明的 13 个能力 → 候选 `workers\` 下 13/13；`worker-profile.json` 声明的 `runtime/python.exe` → 在候选内**确实解析得到**；启动器 `启动绿色候选.vbs` 与 `core\  desktop\` 都在。

### 42.1 一个不是缺陷的不对称（并说明我为什么先查再写）

`start-backend.cmd` / `start-backend.py` 在候选里**找不到**。我先查了再下结论：

- 它们**属于暂存器的输出根**（`<staged>\`），**不属于运行时根**（`<staged>\runtime\`）；
- 正确传参时，组装器只把**运行时根的内容**铺进 `<root>\runtime\`，所以这两个文件**本就不该出现**；
- 候选自己的启动器是 `启动绿色候选.vbs`，**后端启动由它承担**。

它们出现在 §49 的 q04b 里，**恰恰是因为我当时把整个暂存根传了进去** —— 这反过来**再次印证 §41 的撤回是对的**。

**这是本会话第五次"路径看起来不对"。前四次里三次我拦住了、一次我发布后撤回；这一次查完发现根本不是问题。**

### 42.2 仍未做的

**没有启动这个候选。** 静态一致 ≠ 能跑起来。Q04 的第二半（逐能力真实调用）与"启动候选并观察后端就绪"都**仍未做**，如实登记。

## 43. 正确组装的候选：**真的跑起来了**（2026-10-04）

§42 我写明「静态一致 ≠ 能跑起来」「没有启动这个候选」。本轮启动了 —— **用候选自己的核心、自己的解释器、自己的 workers 路径**：

```
candidate root: ArcheAxis.Knowledge.Green-v0.0.0-q04c-x64
core: True | python: True | transport: True
readiness line names port: 50389
GET  /system/version          -> 200
POST /knowledge-items         -> 201
GET  /knowledge-items/{id}/v3 -> 200 | body carries the text: True
RESULT: assembled candidate core reached readiness and answered
EXIT=0
```

**含义**：这是一个**组装产物**（不是源码树）在跑 —— 它启动、绑定端口、用 launch token 认证、走自己的写入路径落一条数据、再读回来，**用的全是候选内部的 `core\`、`runtime\`、`workers\`**。

### 43.1 它同时彻底洗清了 §40 的错误指控

§40 我断言"候选的解释器路径是坏的"。本轮证明**恰恰相反**：候选内的 `runtime\python.exe` 与 `workers\transport\text_ndjson.py` **都真实可用并被真实使用**。

### 43.2 **不声称**的部分

- **没有调用任何 worker 能力** —— 本轮只走了知识路由，`workers\document\*` 等**一次都没执行**；所以 Q04 的"逐能力真实调用"半**仍未做**；
- **没有启动桌面**（`启动绿色候选.vbs` 会拉桌面 + 核心）；本轮只起核心；
- **没有长期运行**：起→就绪→三步请求→杀进程，是短程冒烟，不是稳定性验证。

## 44. Q04 逐能力真实调用：**在候选里跑通了第一个**（2026-10-04）

§43 只走了知识路由，`workers\*` 一次都没执行。本轮**在组装好的候选里真实执行了一个 worker 能力**：

```
module: ...worktrees\dsh-backend-loop-20261001\shared\core_client.py
{"ok": true, "failed_step": null, "scope": "real_conversion_probe",
 "output_status": "readable", "knowledge_count": 0, "transform_count": 1}
steps: [reachability 200, import 202, enqueue 202, execute 202,
        job_status 200 x3, output 200, search 200]
EXIT=0
```

**关键点**：启动的是候选自己的 `core\archeaxis-api.exe`，用的是候选自己的 `runtime\python.exe` 与 `workers\transport\text_ndjson.py` —— 所以这次**真实的 worker 执行发生在组装产物内部**，不是源码树。

### 44.1 我**不**声称的

- **没有指名道姓说清是哪一个 capability id**：该旅程喂的是 `.md` 样本，走的是文本路线，但"它具体对应 `routes.json` 里的哪个 id"**我没有去核实**，所以不写具体名字；
- `knowledge_count: 0` 且旅程自报 `scope: real_conversion_probe` —— **它不声称闭环**，我也不；
- `search 200` 只说明路由可达，**不代表有命中**（未断言 count）；
- **13 个能力里只跑了 1 个**，且是哪一类还需逐项确认。**Q04 的"逐能力"半只完成了第一例。**

## 45. 多能力扫描：**六项全失败，但不归因于能力**（2026-10-04）

本轮想一次推进 Q04 的逐能力半，用真实夹具跑了六种 kind：

```
note.md      kind=text     ok=false  failed_step=search_results  output_status=readable
page.html    kind=html     ok=false  failed_step=job_status      output_status=null
document.pdf kind=pdf      ok=false  failed_step=job_status      output_status=null
picture.png  kind=image    ok=false  failed_step=job_status      output_status=null
board.canvas kind=canvas   ok=false  failed_step=job_status      output_status=null
package.zip  kind=archive  ok=false  failed_step=job_status      output_status=null
```

### 45.1 为什么**不能**把它写成"六个能力失败"

我的启动声明里**只注册了一个文本 worker**：

```python
{"launch_token": ..., "session_id": ..., "text_worker": {...}}
```

而**候选自己带着 `worker-profile.json`，里面列着各能力的 worker**。我只交了 `text_worker`，**非文本 kind 根本没有 worker 可跑** —— `job_status` 卡住是**必然**，不是能力坏了。

**这与 §49 是同一类错误：我的调用不符合产物的用法，然后产物看起来坏了。** 上一轮我刚刚因为同类问题撤回了一个已发布的"缺陷"。

### 45.2 顺带一处**未解释**的异常

`note.md` 在**单独跑**（§44）时成功，这次却停在 `search_results`。我**不解释**它 —— 最可能是同一次进程里连跑六单带来的状态差异，但我没有验证，所以不写结论。

### 45.3 结论

**Q04 的逐能力半仍然是 1/13**（只有 §44 那一次文本路线成功，而且我连它的 capability id 都没核实）。**本轮没有增加任何能力证据。**

**下一步的确切形状**：启动声明必须**取自候选自己的 `worker-profile.json`**，让每个能力都有 worker，再逐 kind 跑。在此之前跑出来的失败**都不能算能力的账**。

## 46. Q04 逐能力：**候选内 4 个能力产出可读输出**（2026-10-04）

§45 的诊断（"启动声明只注册了一个 worker"）是对的。`TextWorker` 的契约本身就写着这件事：

```rust
crates/archeaxis-api/src/launch.rs:31-53
pub struct TextWorker {
    pub python, script, staging,          // script 服务 text.extract
    pub routes: Vec<WorkerRoute>,          // 其余能力：一个 capability 一个 script
    pub root: Option<PathBuf>,             // 一个根 + 相对路径（正是 W05 那项工作）
}
```

按 `services/python-workers/routes.json`（W04 的单源清单）把 **13 条路由**填进启动声明、`root` 指向候选根、脚本用相对路径：

```
routes registered in the launch: 13
note.md      kind=text     ok=false  failed_step=search_results  output_status=readable
page.html    kind=html     ok=true   failed_step=null            output_status=readable
document.pdf kind=pdf      ok=false  failed_step=job_status      output_status=null
picture.png  kind=image    ok=false  failed_step=job_status      output_status=null
board.canvas kind=canvas   ok=false  failed_step=search_results  output_status=readable
package.zip  kind=archive  ok=false  failed_step=search_results  output_status=readable
```

### 46.1 必须分开读的两类失败

**A 类：能力跑了、输出可读，只是卡在检索步骤。** `text` / `canvas` / `archive` 三者 `output_status: readable` —— **转换确实成功**。它们倒在我传的查询串 `6371` 上：那三份材料里**本来就没有 `6371`**，所以**检索没有命中是正确行为**，旅程把它当失败是**旅程的严格**，**不是能力的问题**。

**B 类：`pdf` / `image` 倒在 `job_status`。原因未确定。** 可能是候选里缺对应引擎（OCR/PDF），也可能是真实失败 —— **我没有查，所以不归因**。

### 46.2 本轮的实际增量

**在组装好的候选里，已有 4 个能力产出可读输出**：

| 能力 | 证据 |
| --- | --- |
| `text.extract` | `output_status: readable` |
| **`html.structure`** | **`ok: true`**（整条旅程通过） |
| `canvas.structure` | `output_status: readable` |
| `archive.inventory` | `output_status: readable` |

**Q04 的逐能力半：4 / 13 已在候选内产出可读输出**（此前是 1）。其余 9 个未做，其中 `pdf`/`image` 有**未定的失败**需要单独查。

## 47. §46 的 B 类失败查清了：**不是能力缺陷，是候选缺依赖**（2026-10-04）

§46 我把 `pdf`/`image` 的失败记为"原因未确定，不归因"。本轮把它查到底 —— **打的是任务单本身，不是我的封装**：

```
import  -> 202 | source_id: src_f4eee107088575eabd4e19a7
enqueue -> 202 {"job_id": "pdf-why-1", "state": "queued"}
execute -> 202
terminal state: failed (2 polls)
error: {"code":"AAK-WORKER-003",
        "message":"no native PDF engine available (pymupdf/pdfminer)",
        "retryable":false}
```

### 47.1 这说明的是**worker 做得对**

PDF worker **跑了**，并且**响亮地、带错误码地、明确不可重试地**说明：**候选里没有原生 PDF 引擎**。

**这是正确行为，不是缺陷。** 一个静默给空结果或假装成功的 worker 才叫缺陷 —— 而它给了 `AAK-WORKER-003` + 明确原因 + `retryable:false`。

### 47.2 真正的原因在我这边

我暂存运行时用的是共用工具库里的**裸 CPython**（`cpython-3.12.13-windows-x86_64-none`），**它没有项目依赖的 site-packages**；而暂存器的参数表里本来就有 `--dep-source` / `--dep`（`action="append"`）——**那正是用来把依赖装进候选的**，我**没有用**。

所以：

- **不是 `pdf.extract` 坏了**；
- **不是候选布局坏了**；
- 是**我这个候选的运行时不含 worker 依赖**。

**这是本会话第三次"我的调用/搭建方式不对，产物看起来坏了"**（§45 少注册 worker、§49 传错 runtime、本节缺依赖）。前两次一次拦下、一次已发布后撤回 —— **这次我在写下结论之前就查到了原因**。

### 47.3 未完成

**没有**用 `--dep-source` 重做一个带依赖的候选并重跑 `pdf`/`image`。所以 `pdf.extract` / `image.ocr` 在候选内的**真实可调用性仍然未验证** —— 只验证了它们**会被正确地拒绝**。
