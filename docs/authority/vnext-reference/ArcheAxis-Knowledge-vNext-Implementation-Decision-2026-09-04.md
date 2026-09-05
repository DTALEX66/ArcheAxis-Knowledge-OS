# ArcheAxis Knowledge vNext 明确实施方案

副标题：从最新云端仓库到第一个可用全链路——终局语言、仓库规范、多 Agent 并行、旧代码吸收与交付门

版本：2.1（深化落仓版）  
决策日期：2026-09-04  
云端审计基线：**main@ce3c2de551bcaac52c8a26d012e6482c1a73a540**  
最新公开发行：**v0.6.14**（2026-08-29）  
项目范围：只处理 ArcheAxis Knowledge；WORK-LAB、DESIGN-LAB 暂不作为运行依赖或合同前提  
用途：个人研究、非商业使用；第一方 MIT 与第三方许可仍分别管理  
权威说明：本报告确认并收敛 Owner 的最新决定，取代此前审计中“C# 作为唯一领域写者”的语言结论；此前其他事实审计不因此作废

> **执行协议已被后续总包替代：** 本文保留语言、产品、证据和迁移的
> 论证价值；其中 `authority lease`、A00/A01/C02/R03 等任务编号、旧 task
> path、签发顺序和 receipt 字段不得执行。唯一执行入口是包根
> `MASTER-TASKPACK.md`、`TASK-GRAPH.yaml` 与 `repo-seed/.project/`。

## 执行结论

**明确答案：停止继续做广泛架构调研，直接开工。** 终局语言不再并列候选：**C#/Avalonia 管桌面体验与 Supervisor；Rust 管权威领域核心、本地 BFF、迁移、恢复与主 SQLite 唯一业务写入；Python 只做可替换的解析、OCR、ASR、检索、模型与评测 worker。** 新的 vNext 数据库从第一天就只允许 Rust 写。

最合适的推进形态是：**同一个云端 monorepo 内新建最终目录，以绿地垂直切片重做主链；现有 v0.6.14 保持可用和不可变；旧代码只按“行为、语料、纯函数、适配器、契约”逐项吸收，不复制旧权威结构，不原地抢写旧数据库。**

当前不做系统级平台，也不先建设通用 Agent OS、插件市场、跨设备同步、图数据库或完整全网研究平台。第一目标是让用户在 Windows 上真实完成：

1. 导入自己的原件；
2. 阅读并精确选中原文；
3. 保存个人知识，或让模型提出候选；
4. 人工编辑、接受、拒绝或标为未验证；
5. 搜索并跳回原件锚点；
6. 生成一个学习项目并记录一次学习结果；
7. 关闭全部进程后重启回读；
8. 导出、恢复并核对哈希。

这条闭环通过后再接自动全网交叉验证。个人定义、观点、观察、问题、假设、传闻记录都可无外部证据入库；“能保存”与“可宣称为外部事实”是两件事。

### 最终判断卡

| 决策项 | 唯一方案 | 立即排除 |
|---|---|---|
| 项目阶段 | vNext 产品化垂直切片 | 系统级平台、通用 Agent OS |
| 组织方式 | 1 名 Owner/Integrator + 多 Agent 并行，天然可扩为多人 | 多个 Agent 直接共同维护 main |
| 仓库 | 原仓库内单 monorepo，短分支、独立 worktree | 新建多仓、长期 vNext 分支 |
| 桌面 | C# 14 / .NET 10 LTS / Avalonia 12.1.x | 新增 React/Tauri 产品功能 |
| 权威核心 | Rust stable / Edition 2024，本地独立服务 | C# 与 Rust 双核心、Python 领域核心 |
| AI 与文档 | 隔离 Python capability workers | Python 获得主库句柄 |
| 数据 | Rust WriterActor + SQLite WAL + 原件 CAS | 多进程写库、完整事件溯源起步 |
| IPC | UI→Core 为 loopback HTTP/JSON；Core→Python 为 stdio NDJSON | 首版 FFI、PyO3、多个本地端口 |
| 检索 | 首版 SQLite FTS5；向量为后续可重建投影 | 首版先上向量库或图数据库 |
| 旧代码 | 逐项 reuse / wrap / port / retire | 整树复制或原地大爆炸迁移 |

## 1. 审计边界、最新事实与历史裁决

### 1.1 这次核对的是最新云端 main

2026-09-04 对 GitHub API 的重新读取确认，默认分支仍为 **ce3c2de551bcaac52c8a26d012e6482c1a73a540**，提交时间为 2026-09-03 17:51:49 UTC，主题为 “docs: record exact CI repair evidence”。不存在比该 SHA 更新的 main 提交。[R01]

递归树包含 1,246 个文件：约 642 个 Python、317 个 Markdown、93 个 JSON、33 个 TSX、12 个 TypeScript、12 个 Rust；没有 C# 源文件或 csproj。现状因此非常清楚：Python 仍是大部分领域/API/SQLite 实现，Rust 主要是 Tauri/恢复宿主，Avalonia 目标尚未落地。[R02][R03]

最新公开发行仍为 v0.6.14，包含 Setup、Green、Portable、wheel、SBOM、SHA256SUMS 和第三方声明等 9 个资产。它应继续作为可恢复旧产品，不在 vNext 施工中改写。[R04]

### 1.2 当前仓库自己的阻塞事实

同一 SHA 的最新 push CI run 33787077225 显示 overall success，但真正执行的只有 gateplan、lint 与 a0-gates，其余 11 个 job（包括 test、browser、Windows、desktop、installer 与 wheel）全部 skipped。因此它只能证明轻量门通过，不能证明全仓或产品路径绿色。[R09]

更晚的 scheduled nightly run 33851057281 于 2026-09-04 07:56 UTC 失败：full-suite 失败，Python 3.11/3.13 compatibility 成功，browser-smoke 与 windows-runtime 因依赖关系跳过。报告以这个更新的运行事实为准；当前状态必须表述为“门禁通过、完整资格化失败”，而不是“全部绿色”。[R10]

仓库的 G0 登记明确写有：58 个直接 SQLite 连接位置仍存在；Source、Anchor、Evidence、Claim、Human Learning Event 与 Machine Competence 的运行时唯一写者/消费者/拒绝证据没有闭合；完整 Windows、浏览器、wheel、installer 与全格式资格化仍未完成。[R05]

CURRENT_REALITY 文件仍把 canonical branch 写为其父提交 af216e3，而真实 main 已是 ce3c2de。这再次证明“当前 SHA”不能靠人工写入同一个会继续变化的文档。vNext 改为由 CI 产生不可变 receipt，并让 Current 页面只读取回执，不再自我引用。[R06]

### 1.3 历史完整性与冲突处理

历史权威登记已经覆盖当前可访问的 97 个去重来源资产，其中 64 个具有决策意义，并显式补齐 2026-08-26 至 2026-09-04 的接缝。其最新 Owner 裁决是：**C#/Avalonia UI + Rust authoritative Core/BFF/sole writer + Python replaceable sidecars**。

此前“C# 唯一写者”报告把个人长期维护成本放在过高权重；用户随后明确“不考虑个人维护”，并再次确认核心记忆是 Rust。因此本报告做的不是再次摇摆，而是恢复同一约束下的正确权威：

- 如果只求最短原型日历，C# sole writer 会更快；
- 如果既要尽快可用，又不想在可用后再迁一次核心与数据，vNext 从第一天使用 Rust 唯一写者更合适；
- Rust 不会让 OCR、LLM 或事实判断自动更准确，它负责权威状态、故障边界、资源控制和不返工的终局结构；
- C#/.NET 同样具备成熟的类型与内存安全能力，选择 Rust 不是贬低 C#，而是边界和迁移成本决策。[S01][S02]

### 1.4 对旧 G0 冻结的精确修订

原 G0 规则继续保护旧产品和旧数据库：Rust 不得直接接管旧库，不得与 Python 双写，不得把新编译成功冒充迁移完成。[R03][R05]

但绿地 vNext 需要一条新的 Owner ADR，明确限定：

1. vNext workspace/database 与旧数据库完全隔离；
2. Rust 从第一天只写 vNext 新库；
3. 旧产品继续独占旧库，或只读取旧库副本；
4. 迁移通过“旧库副本→带哈希导出包→Rust 校验→新库导入”，不共享数据库、不实时同步；
5. 在导入、差分、回滚、Windows 产品路径通过前，vNext 不替代 v0.6.14 的发布权威。

这不是绕过单写原则，而是把“旧库迁移”和“新产品孵化”拆开。原规则中禁止额外数据库的部分，应由 PR-00 的 supersession row 显式缩窄，不得静默忽略。

## 2. 为什么这是最合适的语言架构

### 2.1 候选反证矩阵

| 方案 | 首个可用闭环 | 终局返工 | 故障/写入边界 | 当前判断 |
|---|---|---|---|---|
| Avalonia + Rust Core + Python workers | 需先打通三角，但可并行 | 无第二次核心迁移 | 最清楚 | **采用** |
| Avalonia + C# sole writer + Python | 最快 | 若 Rust 仍是终局，必再迁一次 | 清楚 | 仅在 Owner 正式撤销 Rust 时采用 |
| React/Tauri + Rust Core + Python | 可复用 UI | 仍需迁 Avalonia 产品面 | 清楚 | 只作行为 oracle |
| Python/Qt 或 Python Web 全栈 | 原型快 | 权威、打包、隔离均重做 | 较弱 | 不采用 |

### 2.2 每种语言只回答一种问题

| 触发条件 | 必须使用 | 禁止 |
|---|---|---|
| 改变 Source、Anchor、Claim、Review、Learning、Job、权限、迁移或恢复状态 | Rust | UI 或 worker 直接写 SQL |
| 桌面窗口、导航、可访问性、Reader、Review、Supervisor、恢复界面 | C#/Avalonia | 在 UI 重复领域状态机 |
| 依赖 Python 成熟生态的解析、OCR、ASR、embedding、rerank、网页获取、模型推理、评测 | Python worker | 返回 verified/mastery/approval 等权威结论 |
| 跨语言 DTO、错误、事件、版本与兼容规则 | OpenAPI 3.1 + JSON Schema 2020-12 | 每种语言自定义一套字段 |
| Windows 安装、签名、进程与诊断脚本 | PowerShell | 把脚本变成长期业务核心 |
| 当前 React/Tauri/TypeScript | legacy、对比测试、设计提炼 | 新增 vNext 产品功能 |

新桌面固定 .NET 10 LTS；截至审计日 Avalonia 最新稳定版本为 12.1.2。Rust 使用仓库固定的 stable 工具链与 Edition 2024。Python 协议不绑定解释器；新 capability pack 默认资格化 3.14，旧适配器可暂留已经验证的 3.12/3.13 环境，彼此独立锁定，不再共享一个巨型 venv。[S03][S04][S05]

### 2.3 运行时拓扑

```text
Avalonia Desktop / Supervisor
        │  OpenAPI HTTP/JSON
        │  127.0.0.1 随机端口 + 每次启动令牌
        ▼
Rust archeaxis-local-service
  ├─ Domain / Commands / Policy
  ├─ WriterActor ── SQLite WAL
  ├─ Raw object CAS
  ├─ Backup / Restore
  └─ Job Orchestrator
         │  stdin/stdout NDJSON + schema + hash
         ▼
   Python capability workers
```

首版拒绝 Rust/C# FFI 与 PyO3 嵌入。进程协议更容易独立测试、升级、超时、崩溃恢复和替换 worker；Rust ABI 不是本项目可依赖的稳定跨语言契约。UI 到 Core 使用本机 HTTP 是为了最快打通生成客户端和调试，绑定 127.0.0.1、随机端口、一次性启动令牌、scope、request-id 与 idempotency-key；以后若威胁模型要求，可替换为 Windows named pipe，但 DTO 与领域语义不变。[S06][S07][S08]

## 3. 先交付什么：最小但完整的产品闭环

### 3.1 v0.1 只保留四个界面

- **Library / Import**：TXT、Markdown、原生文本 PDF；保存原件与转换回执。
- **Reader / Anchor**：阅读、选择、精确引用、版本漂移提示、跳回原文。
- **Knowledge / Review**：个人知识、机器候选、人工编辑/接受/拒绝、证据状态。
- **Learning / Recovery**：一个学习项目、一次答题/复习、重启回读、导出与恢复。

首版不做插件市场、通用多 Agent 产品功能、复杂 Canvas、3D/VR、跨设备同步、完整 RDF、图数据库、在线协作、自动更新或多平台正式支持。

### 3.2 个人知识无需伪造证据

最小知识对象允许以下来源类型：PERSONAL_DEFINITION、NOTE、OBSERVATION、OPINION、QUESTION、HYPOTHESIS、RUMOR_REPORT、FORECAST、FACTUAL_CLAIM。所有类型都能保存和检索。

独立的评估字段回答不同问题：

- source provenance：来自用户、文件、网页还是模型；
- transformation quality：模型是否读对、转对；
- evidence status：未评估、本次未找到、单源支持、交叉支持、冲突、反驳；
- test status：不可测试、未测试、部分测试、复现、复现失败；
- rumor status：非传闻、传播中未证实、已解决；
- forecast status：非预测、开放、命中、未命中、结算不明确；
- human decision：未复核、接受、修改、拒绝、撤销。

因此软件可以保存“这是我的定义”，同时诚实显示“无外部证据”；也可以保存“网上有人这样传”，同时不把传闻内容升级为事实。

### 3.3 锚点和来源

RawAsset 保存不可变字节、SHA-256、MIME、采集时间、rights 与 locator。Anchor 同时保存 source version、页码/时间码/结构位置、start/end、exact、prefix、suffix 和 context hash。W3C Web Annotation 的 TextQuoteSelector 与 TextPositionSelector 正好提供了可互操作的最小模型；PROV-O 可作为来源关系映射，但首版不需要完整 RDF 存储。[S09][S10]

### 3.4 “准确率”不能由模型自报

用户看到的每个百分比必须同时显示任务、样本量、版本和时间。至少分开：

| 环节 | v0.1/v0.2 指标 | 不能冒充 |
|---|---|---|
| OCR/ASR/解析 | CER/WER、字段准确率、结构 F1、失败率 | 事实正确率 |
| 锚点 | 重定位成功率、context-hash 命中率 | 来源可信度 |
| 检索 | Precision@K、Recall@K、MRR、原始资料覆盖率 | “搜遍全网” |
| 主张抽取 | precision、recall、F1、人工修改率 | 模型 confidence |
| 证据关系 | supports/refutes/qualifies 分类指标 | 主张永久为真 |
| 预测 | Brier score、校准与结算覆盖 | 当下事实状态 |

Precision 与 recall 必须基于带标签黄金集；NIST 也要求把适用情境、准确性、有效性、可靠性和未能测量的风险写清，不能把一个模型分数当作整体可信度。[S11][S12]

### 3.5 v0.1 验收剧本

在干净 Windows 11 x64 环境中，使用项目自有、许可已记录的 PDF 与 Markdown：

1. 无终端窗口启动 Green 包；Supervisor 启动 Rust Core，Core 完成版本握手；
2. 导入两个原件，原字节 SHA-256 可回读，重复导入幂等；
3. Python worker 转换并返回 loss report；worker 无数据库权限；
4. 用户在 Reader 选中一句话，保存后能点击回到同一版本同一位置；
5. 用户保存一条无来源个人定义；模型提出至少一条 MachineCandidate；
6. 接受、修改、拒绝分别产生不可变 receipt，不把候选直接标为 verified；
7. FTS5 搜索同时返回原文、个人知识和已接受候选，并可跳回 Anchor；
8. 创建一个学习卡，提交一次答案，Rust 写入学习事件与下一次复习状态；
9. 强杀 Python worker，权威数据不损坏，Job 留下失败 receipt，重试幂等；
10. 关闭所有进程再启动，Source、Anchor、Knowledge、Review、Learning 全部回读；
11. 使用 SQLite Online Backup API 生成快照与 workspace export；
12. 在全新 workspace 恢复，schema、对象数、随机记录和全部哈希一致。

任何一项 skipped 都不算 PASS。

## 4. 数据、存储与一致性

### 4.1 不做完整事件溯源

首版采用正常化关系表作为当前权威状态，配套 append-only audit_event、command_receipt、job_receipt 与 outbox。只有审计回执不可变；FTS、embedding、缩略图、统计和 UI projection 全部可删除重建。这样保留可追溯和恢复能力，又避免先建设一个昂贵的通用事件平台。

v0.1 只有五个事务聚合根：Workspace、Source、KnowledgeItem、LearningItem、Job。RawAsset、Anchor、AtomicClaim、ReviewDecision、LearningEvent、CommandReceipt、ExportManifest 和 RestoreReceipt 是不可变实体、值对象或回执；FTS、缩略图、统计等是可重建投影。这个收缩避免把事务边界做成“全域大锁”。

### 4.2 SQLite 规则

- 仅 Rust Core 打开 read-write 连接；Avalonia、Python、Agent 全部没有主库路径和句柄。
- WriterActor 持有一个 read-write connection，以 typed command 串行写入。
- 每个 command 在一个事务中写 aggregate revision、audit/outbox、idempotency 与 receipt。
- 只在本机磁盘启用 WAL；SQLite 官方说明 WAL 可让读写并行，但同一 WAL 仍只能同时有一个 writer，而且不适合网络文件系统。[S13]
- 启用 foreign_keys，设置 busy timeout；长任务不持有事务。
- 在线备份必须走 SQLite Online Backup API 或经过验证的 VACUUM INTO，不复制活动中的 sqlite/wal/shm 文件。[S14]
- 首版检索使用 FTS5；它是 SQLite 官方全文检索模块，支持 rank、snippet、prefix 与布尔查询。向量只在黄金检索集证明增益后加入，并保持可重建。[S15]

### 4.3 原件 CAS 与导出

原件存放在 workspace objects/sha256/ 前缀目录；数据库只保存 identity、rights、MIME、size、capture 与引用。导出包包含：SQLite 一致快照、对象文件、contracts/version、component manifest、每个文件哈希、导出 receipt。恢复先验证 manifest 和 hash，再创建新 workspace；禁止覆盖现有 workspace。

## 5. 仓库最终目录规范

```text
/
├─ AGENTS.md
├─ PROJECT_CONTRACT.yaml
├─ DIRECTORY_AUTHORITY.yaml
├─ LEGACY_MANIFEST.yaml
├─ Cargo.toml / Cargo.lock / rust-toolchain.toml
├─ global.json / Directory.Packages.props
├─ pyproject.toml / uv.lock
├─ apps/
│  └─ desktop/                         # C# / Avalonia / Supervisor
├─ crates/
│  ├─ archeaxis-contracts/
│  ├─ archeaxis-domain/
│  ├─ archeaxis-application/
│  ├─ archeaxis-store-sqlite/
│  ├─ archeaxis-archive/
│  ├─ archeaxis-api/
│  └─ archeaxis-sidecar-protocol/
├─ services/
│  ├─ local-service/                   # Rust binary
│  └─ python-workers/                  # capability packs, no DB
├─ packages/
│  └─ contracts/                       # OpenAPI, JSON Schema, compatibility
├─ integrations/                       # import/export and external adapters
├─ fixtures/                           # rights manifest + golden inputs/expected
├─ tests/
│  ├─ contract/
│  ├─ integration/
│  ├─ journey/
│  └─ migration/
├─ config/
├─ packaging/
├─ docs/
│  ├─ authority/
│  ├─ architecture/
│  ├─ decisions/
│  ├─ operations/
│  ├─ taskpacks/
│  └─ history/
├─ scripts/
│  ├─ agent/
│  ├─ ci/
│  └─ dev/
├─ tools/
│  └─ agent-adapters/{generic,codex,dsh,hermes}/
├─ .github/
└─ .project-local/                     # 全部 gitignore
   ├─ worktrees/ agents/ leases/ runs/
   └─ cache/ tmp/ logs/ artifacts/
```

根目录只允许入口、跨语言锁定、治理与一级代码空间；新增顶层目录必须先改 DIRECTORY_AUTHORITY.yaml。模型、用户数据、数据库、运行日志、Agent 会话、下载、venv、target、bin/obj 和临时报告都不得提交。

当前根目录在过渡期仍有 app、shared、knowledge_base、frontend、src-tauri、desktop 等旧路径。第一批不进行 1,000 文件大搬家；由 LEGACY_MANIFEST.yaml 标成 active-legacy/read-only/fixture-source/retire-after 等类别。vNext 达到两个稳定里程碑后，从 active main 删除未吸收旧代码，历史由 tag 和 Git 保留，不建立永久 legacy 垃圾场。

## 6. Codex、DSH、Hermes 与任意 Agent 的并行写入协议

### 6.1 组织模型

当前采用 **一个 Owner/Integrator，多 Agent 贡献**。以后增加人类开发者时，只升级 CODEOWNERS 与审批人数，不改变目录、任务协议或数据边界。

开发时可以多写，运行时必须单写：多个 Agent 可以在不同 worktree/branch 写代码；契约、迁移、锁文件、CI、版本和发布清单必须串行租约；main 只由合并流程写；业务 SQLite 只由 Rust Core 写。

Git 官方 worktree 支持同一仓库同时检出多个分支，HEAD 与 index 独立，适合 Agent 隔离。Codex 官方也建议以 AGENTS.md 保存仓库布局、构建、测试、约束和 done 定义，并用 worktree 隔离并行任务。[S16][S17]

### 6.2 工具无关的权威层

- 根 AGENTS.md：短、准确、工具无关；写项目使命、目录、命令、边界与 done。
- 目录内 AGENTS.md：只写局部差异，例如 Rust、Avalonia、Python、contracts；不得复制全局架构。
- PROJECT_CONTRACT.yaml：机器可读的语言与依赖方向。
- task envelope：谁从哪个 base SHA、在哪个 worktree、允许改哪些路径、如何验收。
- CI scope-gate：从 PR base 或受保护来源读取 envelope，拒绝越权路径。
- tools/agent-adapters：只有 Codex/DSH/Hermes 的薄启动适配，不复制政策。
- .codex、.hermes、.dsh 及其他软件的真实运行状态、凭据、缓存、日志统一映射到 .project-local/agents/ 并忽略。

没有找到能可靠确认是用户所指 DSH/Hermes 的稳定公开写入规范，所以方案不猜它们的专有文件名或参数。它们只需能接受：仓库路径、base SHA、任务 envelope、allowed_paths、验收命令，并返回 patch/commit/receipt，就能接入。

### 6.3 每任务信封

```yaml
schema: archeaxis.task/v1
id: AX-VN-CORE-003
base_sha: <40-hex>
lane: rust-core
objective: import raw asset and persist receipt
allowed_paths:
  - crates/archeaxis-application/**
  - crates/archeaxis-store-sqlite/src/import/**
  - tests/integration/import/**
forbidden_paths:
  - packages/contracts/**
  - crates/archeaxis-store-sqlite/migrations/**
  - .github/**
depends_on: [AX-VN-CONTRACT-001]
required_checks: [scope-gate, rust-check, import-integration]
lease:
  holder: agent-run-id
  expires_at: <RFC3339>
```

规则：一个任务、一个 branch、一个 worktree、一个 Agent owner；两份活动租约不得覆盖同一路径；Agent 可读全仓但只写 allowed_paths；信封不能由本 PR 给自己扩权；任务完成返回 base/head SHA、文件列表、命令、结果、契约/迁移影响、风险和回滚 receipt。

### 6.4 串行保护路径

以下路径一次只能有一个 authority lease：AGENTS.md、PROJECT_CONTRACT.yaml、DIRECTORY_AUTHORITY.yaml、LEGACY_MANIFEST.yaml、.github/**、packages/contracts/**、数据库 migrations、Cargo.lock、Directory.Packages.props、uv.lock、config/schemas/**、packaging/**、全部版本号与发布清单。

若要改契约：先单独合并短 contract PR；然后 Rust、C#、Python 消费者从新 main 并行实现；最后合同兼容测试统一验收。禁止三个 Agent 各自发明字段。

### 6.5 GitHub 保护缺口

当前仓库已有 active main-protection 与 tag-protection ruleset，但 main 规则只防非快进、删除并要求 a0-gates；strict required checks 为 false，且没有要求所有变更经 PR。[R07]

个人仓库现阶段建议：

- main 必须经 PR；禁止直接 push、force push、删除和规则绕过；
- required checks 对最新 main 严格重跑；
- 个人维护时不强制第二个人批准，由 Owner 在 CI 绿后合并；
- 一个任务 squash 为一个主干提交；authority PR 串行；
- 普通无重叠 PR 可快速连续合并；GitHub Actions concurrency 串行 integration/release；
- 将来转组织/多人后，再要求非作者 CODEOWNER、撤销旧批准、限制最后推送者自批，并在可用时启用 merge queue。

CODEOWNERS 是审查路由，不是文件锁或操作系统权限。AGENTS.md 也是指令，不是安全边界；真正的拒绝必须由 CI、远端 ruleset、隔离凭据和进程权限执行。[S18][S19]

## 7. 旧代码如何融合吸收

### 7.1 五类裁决

| 类别 | 当前资产 | vNext 动作 |
|---|---|---|
| 直接保留 | golden fixtures、rights/hash、release receipts、有效测试、设计 token | 移入新权威目录并固定预期 |
| 无状态包装 | multi_format、OCR/ASR、网页获取、processing manifest、质量纯函数 | 删除存储副作用，变成 Python capability worker |
| 语义移植 | Source/Anchor/Evidence/Claim、review、learning、backup/export、auth/idempotency | 以旧测试为 oracle，在 Rust 重写状态机与 command |
| 仅作对照 | React/Tauri UI、FastAPI 路由、当前 installed journeys | 截图/fixture/合同对比，不进入新运行时依赖 |
| 退役 | 分散 sqlite3.connect、重复 DDL、placeholder/mock、重复 KB/shared 边界 | vNext 不导入；两个稳定里程碑后删除 active path |

现有 Phase-0 复用记录已经确认 shared/processing_manifest.py、质量纯函数和部分摄取路径值得保留，也明确 MarkItDown 占位、若干 adapter 空壳、任意 output_dir writer 与 Python hash 向量 ID 不应照搬。[R08]

### 7.2 强制 ReuseDecisionRecord

每个被吸收模块必须记录：来源 path/commit、行为用途、许可、输入/输出、网络、数据写入、资源、已知缺陷、资格化 fixture、采用方式、Owner 与删除旧代码的条件。未填写记录的旧模块不进入 vNext。

### 7.3 迁移不是共享数据库

旧库导入器在独立副本上只读，产生版本化 migration package：对象、记录、关系、旧 ID、新 ID 建议、源 schema、hash、loss/rejection。Rust 先 validate/dry-run，再原子写新库，生成 migration receipt。失败只删除新 workspace；旧库不动。通过两轮固定 fixture 差分和一次真实副本演练后才允许用户迁移。

## 8. 四周执行路线与并行任务

### 8.1 时间承诺

- **第 2 个工作日**：仓库治理、契约 v1 与目录落地。
- **第 5 个工作日**：Avalonia→Rust→Python “Hello Triangle” 和 Rust 新库写入/重启/备份 spike。
- **第 10 个工作日**：可用 Alpha，完成导入、阅读、锚点、个人知识、候选复核、FTS 搜索、重启回读。
- **第 15 个工作日**：加入最小学习事件、导出/恢复和失败恢复。
- **第 20 个工作日**：干净 Windows 11 Green 包与完整 12 步旅程，形成 Owner 可日用的 v0.1 Preview。
- **第 5—6 周**：旧库只读导出/导入、真实副本差分、Setup/Portable/Green 加固、失败注入、SBOM 与 exact-SHA receipt；通过后才称为 release-candidate。

这是 Owner/Integrator 加 3—4 个 Agent lane 的工程估算，不是保证日期。若只有一个执行者，保持同一顺序、不降低验收门，诚实日历为 6—8 周；未来即使多人开发，也沿用同一小 PR、合同和权威文件串行规则。

### 8.2 PR 序列

| PR | 交付 | 合并门 |
|---|---|---|
| PR-00 | ADR：终局语言、绿地例外、旧 G0 保护、停止调研 | 历史 supersession 无冲突 |
| PR-01 | 最终目录、AGENTS、task/receipt schema、scope-gate、ruleset 计划 | Agent 越界 fixture 被拒绝 |
| PR-02 | OpenAPI/JSON Schema v1 + Hello Triangle + version handshake | C#/Rust/Python contract tests |
| PR-03 | Rust WriterActor、SQLite migrations、CAS、import、receipt、backup spike | restart + hash + worker-crash PASS |
| PR-04 | Avalonia Library/Reader + PDF/MD basic worker + Anchor | 点击精确回原文 |
| PR-05 | Personal Knowledge + MachineCandidate + Review + FTS5 | 三类 review 和搜索回读 |
| PR-06 | LearningItem/Event + retry/job state + export/restore | 新 workspace 全量一致 |
| PR-07 | Windows Green packaging + clean-machine journey | exact-SHA 12 步全 PASS |
| PR-08 | 旧库只读 exporter / vNext importer | dry-run、两份差分、回滚 |

PR-00 与 PR-01 串行。PR-02 契约合并后，Rust、Avalonia、Python、fixtures/E2E 四条 lane 并行；每天只集成通过 scope gate 的小 PR。迁移、lock、CI aggregate 和版本仍串行。

### 8.3 前 48 小时

1. Owner 合并 PR-00，不写业务代码。
2. 创建 apps、crates、services、packages、fixtures、tests、docs、scripts、tools 目标目录和 LEGACY_MANIFEST，不搬旧树。
3. 加 task.schema.json、receipt.schema.json、new-worktree 与 verify-scope。
4. 修 main ruleset：require PR、strict status checks、禁止 bypass；保留 tag 防更新/删除。
5. 冻结最小 DTO：VersionInfo、Workspace、RawAsset、Source、Anchor、KnowledgeArtifact、MachineCandidate、ReviewDecision、LearningEvent、Job、Error、Receipt。
6. 建四个 worktree：rust-core、avalonia-ui、python-worker、journey-fixtures。

## 9. CI、开发速度与完成定义

### 9.1 三层门

| 层 | 目标时间 | 内容 |
|---|---:|---|
| Scope Gate | 1—2 分钟 | Task-ID、base SHA、allowed paths、租约、format、generated drift、secret/path scan |
| PR Component | 5—10 分钟 | 受影响 Rust/.NET/Python 单测、合同、迁移静态检查 |
| Merge/Nightly | 15—30 分钟 | golden journey、重启/崩溃/恢复、全格式、Windows 打包、依赖与许可 |

scope-gate 永远运行；不要把可能被 paths 过滤跳过的 workflow 直接设成 required。重测试按影响范围并行，依赖缓存按 lockfile hash；authority、migration、packaging 和 release 使用 concurrency 串行。当前 41 KB 的 ci.yml 不继续无限增长，vNext 先建立小而独立的 gate，再逐步收敛旧 CI。[S19][S20]

### 9.2 单一命令面

Windows-first 提供以下稳定入口，Agent 不自行拼接环境：

- scripts/dev/bootstrap.ps1
- scripts/dev/check.ps1 --scope <task-id>
- scripts/dev/run.ps1
- scripts/dev/test-slice.ps1
- scripts/dev/journey.ps1 --case v01
- scripts/dev/package-green.ps1

Linux/macOS 只为 Core/worker 快速开发提供对应 sh；未经真实平台旅程，不宣称产品支持。

### 9.3 Definition of Done

一项功能只有同时满足以下条件才完成：合同版本明确；正常/拒绝/重试路径有测试；没有新增越界 DB 句柄；结果绑定 base/head SHA 与 lock hash；用户能从 UI 操作并重启回读；失败可恢复；receipt 写明 skipped 和未知项；文档只描述同一份机器回执。

## 10. 自动全网交叉验证放在 v0.2

v0.1 已允许用户粘贴/导入本地与网页快照、建立来源和 EvidenceLink，并人工标注支持、反驳、限制或仅提及。v0.2 再自动化：主张原子化、多语言/反向查询、多提供商检索、原始资料优先、快照与锚点、转载簇去重、来源独立性、支持/反驳分类、冲突解释与 CoverageReceipt。

“全网”不得在 UI 中当作绝对覆盖。每次运行必须写：查了哪些 provider、查询、语言、时间区间、页数、命中、失败、登录墙/付费墙/robots、未覆盖范围和原始资料比例。“本次未找到”不能显示成“网络上不存在”。

v0.2 进入条件：v0.1 的原件、锚点、候选、人工复核、检索、重启和恢复全部稳定。否则自动检索只会把更多不可靠输入灌入不稳定权威层。

## 11. 还需不需要调研：明确停止规则

**不再需要广泛调研语言、桌面框架、数据库或 Agent 产品。** 现在只剩四项实现型验证，它们必须写代码和跑旅程，网页调研不能代替：

1. 48 小时 Hello Triangle：Avalonia 启 Core，Core 调 Python，版本/错误/超时可见；
2. Rust persistence spike：import、WriterActor、restart、online backup、restore；
3. Anchor spike：真实 PDF/Markdown 的 exact/prefix/suffix/position 点击回读；
4. Windows Green spike：干净机目录包、无终端、进程树退出、用户数据在安装目录外。

架构至少冻结到 v0.1 和旧库迁移 dry-run 完成。只有以下硬证据才允许重开语言 ADR：一次有界修复后第 10 个工作日仍无法完成最小闭环；跨语言/构建/打包边界连续两个迭代占用超过约 30% 工期；并能证明根因确实是 Rust/C# 运行时边界，而不是领域模型、需求或测试缺失。即使触发，也只能由 Owner 明确切成 C# Core，不能保留双核心或双写者。

DSH/Hermes 的专有启动适配、具体 OCR/ASR/model wheel、Windows 10 支持与真实旧库迁移属于按需资格化，不得重新打开已经收敛的产品和语言方向。

## 12. 风险、禁止项与最终 GO 条件

### 12.1 主要风险

- 三语言会增加构建和合同成本；用极窄合同、进程协议和并行 lane 控制。
- Rust 领域开发初期慢；先写 Source/Anchor/Review/Learning 的最小状态，不移植全部旧功能。
- Python capability 依赖冲突；每个 pack 独立 interpreter/lock，不共用全局环境。
- 当前旧仓库过大、文档多；新 active docs 只保留 authority、architecture、operations、taskpacks 四条入口。
- Agent 指令不是权限；必须由 scope gate 与远端 ruleset拒绝越界。
- 自动全网核验可能产生伪覆盖；必须保存 CoverageReceipt 与原件锚点。

### 12.2 硬禁止

- 不允许 Avalonia、Python 或 Agent 直接打开主 SQLite。
- 不允许 Rust 与旧 Python 对同一数据库或同一聚合双写。
- 不允许在 vNext import 前直接读取用户旧生产库。
- 不允许把模型 confidence 显示为准确率。
- 不允许把 personal/unsourced 知识拒之门外或伪造成 verified。
- 不允许 Agent 直接 push main、修改自己的权限信封、同时抢合同/迁移/lock。
- 不允许从 mock、compile、局部测试、skipped job 或文件存在推导产品完成。
- 不允许先建通用平台再补黄金闭环。

### 12.3 v0.1 GO

只有 exact-SHA 的 v0.1 12 步验收全 PASS；Rust 是 vNext 唯一业务写者；Python/C# 无主库句柄；原件与锚点可回读；个人知识和候选语义分离；worker crash 不损坏状态；export/restore hash 一致；干净 Windows 11 Green 可用，才可以称“用户能用的软件”。

## 13. 研究问题—证据缺口矩阵

| 问题 | 状态 | 证据/处理 |
|---|---|---|
| 云端是否最新 | 已解决 | main API 固定 ce3c2de，[R01] |
| 历史是否遗漏 Rust 裁决 | 已解决 | 97 项总账 + Owner 最新裁决 |
| 当前是否已有 Rust Core/Avalonia | 已解决：没有 | 642 py / 12 rs / 0 cs，[R02][R03] |
| 多 Agent 能否并行写 | 已解决 | worktree + envelope + scope gate + ruleset |
| 数据能否多写 | 已解决：不能 | Rust WriterActor；SQLite WAL 仍一 writer，[S13] |
| DSH/Hermes 专有约定 | 未证实且不阻塞 | vendor-neutral adapter，不猜实现 |
| Rust/Avalonia/Python 在本机能否完整打包 | 需工程验证 | 5 日 Hello Triangle/Green spike |
| 旧真实数据库能否无损导入 | 需工程验证 | 只读副本、dry-run、差分、回滚后再开放 |
| 自动全网覆盖率 | 需产品评测 | v0.2 CoverageReceipt + 黄金主张集 |

这就是停止广泛研究的依据：所有架构问题已经可裁决；剩余问题只能靠实现和测量解决。

## 14. 深化裁决：方案不变，但工程边界更精确

本轮从契约、证据、运行时安全、Agent 治理、旧库迁移和交付容量六个方向反向审计。结果不是换技术栈，而是修正六处容易造成后续返工的模糊表达：

1. 事务聚合根只有 Workspace、Source、KnowledgeItem、LearningItem、Job 五个；Anchor、Claim、ReviewDecision 等不能全部称为聚合。
2. Day 5 是跨语言架构证明；Day 10 是可丢弃 workspace 的 Alpha；Day 20 才允许在 Green 包中使用真实数据；旧库迁移、Setup/Portable、SBOM/NOTICE 和升级恢复在第 5—6 周收口。
3. Python 独立进程是故障隔离，不是对恶意本机原生代码的强沙箱；首发 worker 必须是来源和依赖均已固定的 trusted-but-fallible capability pack。
4. Agent 的声明、AGENTS.md 和 CODEOWNERS 都不是强制授权；真正边界是受保护 base 中的 envelope/lease、scope gate、远端 ruleset 和 Owner 合并。
5. 证据不是知识准入门。个人内容、事实主张、机器转换质量、测试、传闻和预测必须正交表示，不能压成一个“真实性 92%”。
6. 旧产品可恢复不等于产生 vNext 新数据后还能无损退回旧 writer；切换后历史分叉，只能恢复 vNext 备份或 fix-forward。

这些条目是 2.1 的规范性澄清；如与前文简写冲突，以第 14—22 节为准。

## 15. v0.1 领域与跨语言契约

### 15.1 五个聚合根

| 聚合根 | 内部事实 | 必须保持的不变量 |
|---|---|---|
| Workspace | 身份、格式版本、状态 | 首版只归档；恢复创建新 workspace，不覆盖原位置 |
| Source | SourceRevision、RawAssetRef、解析状态 | 原字节先入 CAS；更新产生 revision；失败保留原件和 attempt |
| KnowledgeItem | KnowledgeRevision、EvidenceLink、ReviewDecision | 人工内容可无证据；机器候选未经接受不进入默认搜索/学习 |
| LearningItem | append-only LearningEvent、调度投影 | 事件不可改；Rust 依据 scheduler profile 重建状态 |
| Job | attempt、receipt、输出引用 | worker at-least-once；领域提交用唯一键和事务实现 effectively-once |

KnowledgeItem 是用户可见容器；一份 KnowledgeRevision 可以包含零到多个 AtomicClaim。只有能独立判断的陈述才抽成 ClaimRevision，个人定义和问题不必被伪装成事实主张。

### 15.2 命令、API 与锚点

- API 固定 `/api/v1`。所有 mutation 强制 `Idempotency-Key`；已有聚合 mutation 同时强制 `If-Match`。同 key/同规范请求重放原 receipt；同 key/不同请求返回 `AAK-CON-002`。
- `POST /imports` 使用 multipart 流，不接受 UI 给出的绝对路径。Rust 自行计算文件 SHA-256；幂等摘要由文件哈希和规范 metadata 构成。
- request Schema 严格拒绝未知字段；response consumer 忽略未知可选字段，未知枚举映射 UNKNOWN 并保留原字符串。API、worker、DB schema、export format 各自版本化。
- 锚点文本统一 LF、NFC、Unicode scalar/code-point offset、`[start,end)`。C# 必须用 `System.Text.Rune`，Rust 用 chars，Python 用 code point。PDF 再带 0-based page、归一化 quad 和 rotation。
- Anchor 查询返回 EXACT、RELOCATED、AMBIGUOUS 或 ORPHANED；重定位结果不覆写原 Anchor。
- Python stdio 只传控制 NDJSON；大对象通过 `job://input`、`job://output` 任务目录。输出必须有 URI、SHA-256、byte length、media type 与 schema；不得出现 DB path、workspace path 或权威状态。

PR-02 只有在 OpenAPI/Schema、正反示例、三语言生成、Unicode/emoji offset fixture、major mismatch、unknown field/enum、幂等冲突、timeout/crash/invalid output 全部在 Windows 真运行且零 skipped 后才完成。

## 16. 知识—证据—验证模型

### 16.1 核心不变量

- 用户接受保存不等于证据支持；模型候选不覆盖原文或用户知识；编辑创建新 revision。
- EvidenceLink 必须绑定 ClaimRevision、SourceSnapshot 和 Anchor，而不是只绑定一个会变化的 URL。
- 来源是否“原始”相对于具体主张判断。公司公告能直接证明“公司宣布了什么”，不能自动证明产品效果。
- TransformRun、VerificationRun、CoverageReceipt 和 MetricMeasurement 都不可变，并记录模型、提示词、配置、输入、输出与快照哈希。
- “某账号声称 X”和“X 确实发生”是两个主张。REPORTS_ASSERTION 不能自动升级为 SUPPORTS。

### 16.2 正交状态，不做真相总分

| 维度 | 最小状态示例 | 回答的问题 |
|---|---|---|
| Review | MACHINE_CANDIDATE / USER_ACCEPTED / REJECTED | 用户是否要保留 |
| Evidence | UNASSESSED / UNSOURCED / SUPPORTED / CONFLICTED / REFUTED / STALE | 当前证据关系 |
| Test | NOT_TESTED / PASSED / FAILED / MIXED / NON_REPRODUCIBLE | 是否真实测试过 |
| Rumor | REPORTED_UNVERIFIED / SAME_ORIGIN_REPEATED / CORROBORATED / DEBUNKED | 是否只是传播或有独立生成来源 |
| Forecast | OPEN / DUE / RESOLVED_TRUE / RESOLVED_FALSE / VOIDED | 预测是否已到可结算窗口 |

传闻必须同时去重 DocumentCluster、AssertionOriginGroup 与 EvidenceGenerationGroup。多个搜索 Provider 只是多个发现渠道；几十篇转载同一爆料仍只是一条上游说法。无法证明独立性时标 UNKNOWN，不计作独立确认。

### 16.3 CoverageReceipt 与真实准确率

v0.2 流水线是：主张原子化与限定→Evidence Need→原始资料、独立复核、反证三路检索→合法快照→锚点→URL/内容/出处/证据生成去重→立场与冲突→CoverageReceipt→人工复核。

Receipt 列出 provider/index family、查询族、语言、时间、命中/获取/失败/阻塞、不可访问源、未解决缺口、去重簇、独立证据组、模型/提示词/schema/快照哈希与停止原因。它最多显示 PLANNED_COMPLETE、PARTIAL、INSUFFICIENT；禁止 `coverage_score=87` 和“已搜遍全网”。W3C Web Annotation、PROV-O 与 DQV 分别可作为锚点、来源活动和质量指标的语义依据，首版仍使用 SQLite 关系表。[S09][S10][S21]

CoverageReceipt 的 `receipt_sha256` 计算对象是“移除该字段后的 RFC 8785 canonical JSON”，避免自引用哈希；重新检索产生新 receipt，以 supersedes 连接旧结果，不覆写历史。

模型质量必须按环节测：OCR 的 CER/WER；锚点 exact/fuzzy/orphan；主张抽取与证据立场的分类型 precision/recall/F1；检索 Recall@k/MRR/nDCG；引用正确率；预测到期后的 Brier/calibration；自动化使用 precision-at-coverage 与 abstention。每个数值必须附任务定义、黄金集版本、样本量、语言/格式/领域、模型/配置、日期、95% 区间和错误类别。无人工黄金集就显示 UNMEASURED，不以模型 confidence 代替 accuracy。[S11][S12][S25]

v0.1 只做对象、状态、快照、复合锚点、手工 EvidenceLink、候选复核、TransformRun、FTS、恢复与 CoverageReceipt 预留；v0.2 才实现多 Provider 自动搜索与综合。开工前只需三个有界 spike：真实 PDF/Markdown/动态网页锚点、30—50 个真实主张的出处/独立性去重、第一版人工黄金集。

## 17. 运行时、安全与数据恢复

### 17.1 启动与本机认证

Avalonia Supervisor 创建 Windows Job Object，使用 kill-on-close 管理自己的后代；通过继承控制管道启动 Rust。Rust 绑定 `127.0.0.1:0`，完成 challenge/proof 后派生短期 HTTP credential。秘密不得出现在命令行、普通环境变量、仓库文件或日志。固定端口、Windows Service、管理员权限和防火墙规则都不进入首版。

Rust 以 `-I -u`、环境 allowlist 和任务 staging 目录启动固定版本的 Python。stdout 只允许协议，stderr 为有限诊断；输入/输出 path、schema、hash、size、count、deadline、cancel 和 crash receipt 都由 Rust 校验。

### 17.2 唯一写者的物理实现

WriterActor 在独立线程持有一个 read-write SQLite connection 与有界队列。每个 command 使用 `BEGIN IMMEDIATE`，把业务当前状态、append-only audit、outbox、idempotency record 与 receipt 一次提交；长解析绝不持有事务。只读查询连接也由 Core 管理，UI/worker 不获得路径。

CAS 的正确顺序是任务 staging→流式 SHA-256→关闭/刷新→按哈希原子 rename→数据库引用。恢复使用 Online Backup 与 CAS lease；必须注入进程崩溃、磁盘不足、坏 hash、重复提交、导出中断和重启故障，并至少做 100 次关键 writer crash-loop 才能称 Preview 候选。[S13][S14]

### 17.3 Green、Setup、Portable 不是同义词

Day 20 Green 自带所需 runtime 与一个 capability pack，但用户数据仍位于 `%LOCALAPPDATA%/ArcheAxis/profiles/<id>`，程序目录视为只读。Week 6 的 Setup 处理安装/卸载，绝不删除 workspace；Portable 必须有显式 marker、可写本地 NTFS 和数据路径警告，拒绝在网络共享或云同步目录运行活动 SQLite。

## 18. 多 Agent 写入的可执行治理

### 18.1 角色与控制面

Repository Owner/Integrator 签发任务和租约并合并；Task Agent Owner 只写 envelope 路径；CI 从 base 重新计算，不信任 Agent 自报；Rust Runtime Writer 与 Python Capability Worker 属于运行时角色，不能混为仓库权限。

版本控制内的 `.project/` 保存 schema、issued tasks、leases 和 policy；`.project-local/` 保存 worktree、Agent session、logs、cache、临时产物并全部忽略。`.codex/`、`.dsh/`、`.hermes/` 只可作本机 vendor state；adapter 可以翻译 task，但不能扩权。现有被跟踪的 `.hermes/task-runtime` 要由专门 bootstrap PR 移出并设置提交拒绝。

### 18.2 scope gate 的顺序

1. 从 PR base 读取 PROJECT_CONTRACT、DIRECTORY_AUTHORITY、Schema、已签发 envelope 与 lease；head 中的授权变化对本 PR 无效。
2. 核对唯一 Task-ID、完整 SHA、digest、有效期、依赖和 activation commit。
3. 若 authority/consumed-interface digest 或 write scope 在签发后变化，拒绝；仅完全不相交时自动 refresh。
4. 用 rename detection 计算双端路径，规范化并拒绝绝对路径、`..`、大小写碰撞、symlink escape、submodule、异常 executable bit。
5. 依 deny→exact→longest literal prefix→priority 匹配；歧义 fail closed；核对 lane、operation、文件/行数和二进制上限。
6. 权威文件必须持有唯一有效 lease；检查 secret、vendor state、生成漂移和数据库依赖边界。
7. 验证 Agent execution receipt；CI 自己产生 qualification receipt。最终聚合 job 使用 `if: always()`，任何 required job skipped/cancelled/failed 都失败。

远端 ruleset 只固定两个稳定 context：`vnext-scope-gate`、`vnext-required`，要求 PR、current-base strictness、linear history、squash merge、禁止 direct/force push 和 bypass。个人 Owner 阶段可为 0 个独立审批，但检查不能绕过；未来团队模式再增加一票、CODEOWNER 和 last-push approval。CODEOWNERS 只表达责任，不是写权限。[S18][S27]

### 18.3 并行不靠“大家小心”

一个 task 对应一个 branch、worktree 和 Agent owner；一个任务最多持一个 authority resource lease。合同、DB migration、dependency lock、repo governance、legacy manifest、packaging/release 各自串行，不使用模糊总锁。普通 lane 默认 200—600 行、最多 25 文件；估计超过两个工作日先拆分。每天两次 Owner 集成窗口，减少所有 Agent 因 main 更新持续抖动。

## 19. 可执行 PR DAG 与交付容量

### 19.1 主链

| 波次 | PR | 并行关系 | 退出门 |
|---|---|---|---|
| Authority | A00→A01→C02 | 完全串行 | ADR、治理恶意测试、合同三语言 fixture |
| Triangle | R03 / U03 / P03 / T03→I04 | 四 lane 并行，I04 串行 | Day 5 跨进程成功与失败路径 |
| Import | R05 / P05 / U05 / T05→I06 | 四 lane 并行 | Day 8 import/read/anchor/restart |
| Knowledge | R07 / U07 / T07→I08 | 三 lane 并行 | Day 10 disposable Alpha |
| Safety loop | R09 / U09 / P09 / T09→I10 | 四 lane 并行 | Day 15 feature freeze，完整数据安全环 |
| Preview | K11→T11→I12 | 串行资格化 | Day 20 exact-SHA Windows Green Preview |
| Migration/RC | M13→M14；K14；Q14→I15 | 迁移串行，打包并行 | Week 6 RC 与 retire-ready 判断 |

Day 20 只承诺 Windows 11 x64 Green、TXT/Markdown/native-text PDF、一个真实 capability path 和 12 步闭环；不承诺旧库迁移、扫描 PDF/OCR、Office、音视频、全网自动核验、向量、installer、签名或其他 OS。Week 6 才合入真实旧库副本迁移、Setup/Portable、SBOM/NOTICE、故障矩阵和 upgrade recovery。

4+2 周假定 1 名 Owner/Integrator 加 3—4 条 Agent lane。按 80 lane-day 预算，约 60% 用于功能/基础设施，25% 用于测试/集成/打包/恢复，15% 保留。若只有一个串行执行者，日历按 6—8 周估计，但架构与门不降级。

## 20. 旧代码吸收与迁移深化

### 20.1 58 个旧 SQLite 连接点如何处理

按精确基线的扫描规则，58 处连接分布为 shared 16、app/knowledge 14、app/workspace 7、app/memory 7、app/evidence 4、app/ingestion 2、app/learning 2、其他 6。它们不再阻塞新库开工，但全部登记为冻结 legacy exception，逐项记录表、操作、聚合、运行调用者、Rust command 与移除门；CI 拒绝第 59 个。

### 20.2 reuse / wrap / port / oracle / retire

| 旧能力 | 裁决 | vNext 去向 |
|---|---|---|
| ingestion、OCR/ASR、多格式、质量/评测能力 | wrap/reuse | 独立 Python capability，只有 job scratch |
| evidence、knowledge、learning、memory、workspace | port | Rust Domain/Application/Store |
| storage、migration、backup、OCFL、RAG 状态 | oracle/port | Rust SQLite/CAS/Archive；FTS 先行，向量延期 |
| FastAPI、facade、旧 contracts | oracle→retire/port | 以行为为参照，重建 packages/contracts 与 Rust service |
| frontend、OSUI、Tauri desktop | oracle | 迁移 tokens、labels、journey；不保留运行时 |
| tests | 分级 | fixture reuse；不变量 port；实现耦合 oracle；mock-only retire |
| docs/reports | history/oracle | 选定权威；Current 状态改由 CI receipt 生成 |

根旧 `pyproject.toml/uv.lock` 在过渡期不覆盖；vNext worker 先使用目录内独立 lock。权利不清的资产先标 blocked，不能进入默认包。

### 20.3 单向迁移和真实回滚语义

v0.6.14 一致性副本由旧侧 Online Backup 产生；exporter 使用 `mode=ro`、OS 只读、固定 schema、无网络，把稳定排序的 JCS NDJSON、CAS 字节、ID mapping、rights、loss/rejection 打成 migration package。Rust 先 dry-run，再导入同卷 staging workspace，重建投影、关闭重开、检查 integrity/逻辑 digest/journey，只有 READY receipt 才原子切换 current pointer。[S14][S23][S26]

不得比较两个 SQLite 文件或不同工具产生的 ZIP 字节哈希；比较原件 byte hash、规范记录、映射后语义、引用完整性与逻辑 digest。硬门是 unclassified_loss=0、hash_mismatch=0、dangling_reference=0、重复导入 no-op、同 snapshot 两次导出 manifest digest 一致。

激活前失败只丢 staging；激活后但首个 vNext 写入前可以指回旧产品；首个 vNext 写入后禁止自动回旧 writer，因为两边已分叉。此后只能恢复 vNext backup、修复后再迁或明确接受新数据丢失；绝不做反向同步。

## 21. Day-0 开工包

本报告随附 `ArcheAxis-vNext-Day0-Starter-Pack-2026-09-04.zip`。它不是一个等待整包合并的大提交，而是 PR-00/01/02 的可拆分输入，包含：

- 根 AGENTS、PROJECT_CONTRACT、DIRECTORY_AUTHORITY 与 LEGACY_MANIFEST 示例；
- language authority ADR、五聚合领域合同、运行时安全、证据 v0.2、旧库迁移规范；
- 原项目路径级吸收矩阵与四波 absorption/retire-ready 计划；
- task envelope、execution receipt、authority lease 与 worker protocol Schema；
- OpenAPI outline、稳定 error catalog、compatibility policy；
- 12 步 owner journey、完整 PR DAG、Week-1 gates 与 A00/A01/C02 issuance templates；
- scope-gate fail-closed 算法与首批 hostile fixtures；
- 文件级 SHA256 清单。

模板不是授权。A01/C02 的 placeholder 必须由 Owner 在前置 PR 合并后填入最新完整 base SHA、authority digest、holder 与 expiry，并先提交到受保护 base；Agent 不得在自己的 PR 中激活或扩大它。

## 22. 下一次动作与停止条件

现在不再增加候选语言、数据库、桌面框架或 Agent 产品。唯一正确下一步是：Owner 先审 PR-00 的 ADR/supersession row，再将 A00 作为小 PR 应用到云端仓库；合并后生成 A01 的新 base/lease，建立 scope gate 和两个远端 required checks；A01 合并后才签发 C02。

本次交付未修改云端仓库，也未声称当前 nightly 已修好。出现以下任一情况立即停：任务需要 envelope 外路径；权威 lease 缺失/过期；main 改了重叠路径或 consumed interface；必须弱化/跳过门；任何组件要求成为第二个数据库写者；迁移需要猜 schema 或出现未分类 loss。

到此，产品/语言/治理/证据/迁移层均已有唯一方案。剩余不确定性只能靠 exact-SHA 实现、真实 fixture、干净 Windows journey 和测量解决，不再靠开放式调研解决。

## 附录 A：关键来源

### 仓库与历史事实

[R01] 最新 main commit  
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/commit/ce3c2de551bcaac52c8a26d012e6482c1a73a540

[R02] 固定 SHA 目录树  
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/tree/ce3c2de551bcaac52c8a26d012e6482c1a73a540

[R03] Language Boundary Authority Index  
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/ce3c2de551bcaac52c8a26d012e6482c1a73a540/docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md

[R04] v0.6.14 release  
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.6.14

[R05] G0 Evidence Gap Register  
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/ce3c2de551bcaac52c8a26d012e6482c1a73a540/docs/current/AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md

[R06] Current Reality  
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/ce3c2de551bcaac52c8a26d012e6482c1a73a540/docs/current/CURRENT_REALITY_2026-09-01.md

[R07] 当前 main ruleset API  
https://api.github.com/repos/DTALEX66/ArcheAxis-Knowledge-OS/rulesets/20849492

[R08] Phase-0 Reuse Decisions  
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/ce3c2de551bcaac52c8a26d012e6482c1a73a540/migrations/reports/phase-0/REUSE_DECISIONS.md

[R09] ce3c2de push CI run（轻量门成功、11 jobs skipped）  
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/33787077225

[R10] 2026-09-04 scheduled nightly（full-suite failed）  
https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/33851057281

### 官方技术来源

[S01] .NET introduction  
https://learn.microsoft.com/en-us/dotnet/core/introduction

[S02] Rust ownership  
https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html

[S03] .NET release and support policy  
https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core

[S04] Avalonia supported platforms  
https://docs.avaloniaui.net/docs/supported-platforms

[S05] Avalonia 12.1.2 release  
https://github.com/AvaloniaUI/Avalonia/releases/tag/12.1.2

[S06] OpenAPI authoritative specifications  
https://spec.openapis.org/

[S07] JSON Schema 2020-12  
https://json-schema.org/draft/2020-12

[S08] Rust external/ABI boundary  
https://doc.rust-lang.org/reference/items/external-blocks.html

[S09] W3C Web Annotation Data Model  
https://www.w3.org/TR/annotation-model/

[S10] W3C PROV-O  
https://www.w3.org/TR/prov-o/

[S11] NIST AI RMF  
https://www.nist.gov/itl/ai-risk-management-framework

[S12] scikit-learn precision/recall definitions  
https://scikit-learn.org/stable/modules/model_evaluation.html

[S13] SQLite WAL  
https://sqlite.org/wal.html

[S14] SQLite Online Backup API  
https://sqlite.org/backup.html

[S15] SQLite FTS5  
https://sqlite.org/fts5.html

[S16] Git worktree  
https://git-scm.com/docs/git-worktree

[S17] OpenAI Codex best practices / AGENTS.md  
https://developers.openai.com/codex/learn/best-practices

[S18] GitHub CODEOWNERS  
https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners

[S19] GitHub protected branches  
https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches

[S20] GitHub Actions concurrency  
https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency

[S21] W3C Data Quality Vocabulary  
https://www.w3.org/TR/vocab-dqv/

[S22] RFC 3986 URI Generic Syntax  
https://www.rfc-editor.org/rfc/rfc3986.html

[S23] RFC 8785 JSON Canonicalization Scheme  
https://www.rfc-editor.org/rfc/rfc8785.html

[S24] Library of Congress WARC format description  
https://www.loc.gov/preservation/digital/formats/fdd/fdd000236.shtml

[S25] Stanford IR Book：Evaluation of ranked retrieval results  
https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html

[S26] SQLite URI filenames / read-only mode  
https://www.sqlite.org/uri.html

[S27] GitHub Rulesets  
https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets

—— 完 ——
