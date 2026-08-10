# ArcheAxis OS：全面兼容吸收最小面闭环——云端全量审计与主任务包

> 审计日期：2026-08-06
> 审计对象：`DTALEX66/Cognitive-Loop-OS` 云端公开仓库
> 审计基线：`main` @ `f06c840d0abac3ae9e46bc1bf8f745cf474f3da2`
> 文档性质：只读审计、路线重排、HERMES 执行任务包
> 写入约束：Codex 只读审计；HERMES 是仓库唯一 writer
> 当前决策：把原“阶段 6：全面研究、兼容并吸收同类软件”前移为新的最小面闭环；其他重型蓝图延期
> 实施总原则：合法复用、调用、适配同类开源项目源码优先；自研仅为最后手段

---

## 0. 一页结论

### 0.1 项目正确定位

ArcheAxis OS 当前不是“认知闭环系统”，也不是通用 Agent OS。仓库当前正式定位文件已经写明：

> **ArcheAxis OS is a local-first, evidence-driven, bidirectional learning and knowledge system for individuals and AI.**

中文产品定位应统一为：

> **面向个人与 AI 的、本地优先、证据驱动的双向重型学习与知识系统。**

产品副定位：

> **重型资料摄入、知识演进与 AI 使用工作台。**

Agent 只是 AI 使用层，不是产品中心。历史名词、内部 canonical ID 和兼容接口可以保留，但不得继续主导用户界面、发布说明、评分模型和路线排序。

### 0.2 新的最小面闭环

新的最小面闭环不是“全面复刻 Obsidian”，而是：

> **完成一个可安装、可持续使用的 Human–AI Learning Workspace；以 Obsidian/Markdown/JSON Canvas 为第一条高保真兼容纵切，再逐步吸收 Logseq、Joplin、SiYuan、AppFlowy、AFFiNE、Anytype、Zotero、Readwise、Anki 等同类产品的核心能力与数据。**

最低闭环必须覆盖：

```text
真实资料/现有知识库
  → 导入与保真解析
  → 文件树/编辑/属性/链接/搜索/画布
  → PDF/Web/Office 阅读与证据回链
  → 有引用的 AI 问答/总结
  → 轻量卡片/复习
  → 原格式或开放格式导出
  → 重启后读回
  → 往返验证、冲突报告与可回滚
```

### 0.3 当前仓库离该闭环还有多远

仓库已有扎实但偏后端的基础：FastAPI、SQLite、Tauri、资料摄入、治理对象、迁移、Job/Outbox/Receipt、安全边界、OCR/媒体基础、NetworkX/sqlite-vec、LiteLLM、发布门禁等。它们应被保留并成为兼容工作台的底层能力。

但新的最小面闭环尚未形成：

- 没有成熟的主编辑器、真实文件树、属性面板、标签、反向链接和完整数据视图。
- 没有 Obsidian Vault、Markdown 方言或 JSON Canvas 的真实导入/导出/往返兼容实现。
- `shared/canvas.py` 是内部 SQLite 画布模型，不是 JSON Canvas 兼容层。
- 现有 UI 是页面壳、管理页和局部 task cockpit，并不是日常可用的知识工作台。
- 101 项 registry/ledger 是项目研究账本，不等于 101 个软件已被兼容；当前明确为 implemented 的只有 8 项基础依赖/适配。
- 主分支当前 `0.4.4` 源码清单仍为 `unreleased / public=false`，而 README/状态页仍写 `0.4.2`；当前 main 不能再次发布成 `v0.4.4`。
- PR 头 SHA 的 CI 已有成功证据，但当前 merge SHA `f06c840...` 没有通过现有 GitHub wrapper 取得 exact-SHA workflow run，因此不能宣称当前 main 的精确 SHA 已完成发布级验证。

### 0.4 总体审计判断

目前不是“推倒重来”，而是“底盘已经有了，产品表面和兼容内核尚未建立”。正确策略是冻结重型蓝图，先把现有底盘转换成一个能真实使用、能迁移数据、能导回原生态的开放兼容工作台。

---

## 1. 本次审计范围与证据优先级

### 1.1 审计范围

本次只审计：

- GitHub 仓库 `DTALEX66/Cognitive-Loop-OS`。
- 仓库自有代码、文档、工作流、Release 配置与 `.hermes` 范围。
- 用户此前确认的项目定位、阶段 6 决策和开源研究池。

本次不访问、不扫描、不迁移：

- 个人 E 盘或个人 Obsidian Vault。
- 其他项目目录。
- 外部私有仓库或未明确授权的目录。
- Obsidian、NotebookLM、Readwise 等闭源产品的私有源码。

### 1.2 事实源优先级

今后所有审计与执行必须按以下优先级读取事实：

1. 用户最新明确决策。
2. `docs/PRODUCT_POSITIONING.md`。
3. 当前 `main` 的代码、机器清单和 CI/Release 读回。
4. `docs/PROJECT_STATUS.md` 与验证策略。
5. 当前路线图、执行矩阵和任务包。
6. 历史文档、旧命名、旧评分与旧对话。

低优先级内容与高优先级冲突时，必须标记“历史/待迁移”，不得反向覆盖最新定位。

---

## 2. 云端仓库审计结果

### 2.1 仓库与权限

| 项目 | 审计结果 |
| --- | --- |
| 仓库 | `DTALEX66/Cognitive-Loop-OS` |
| 可见性 | Public |
| 默认分支 | `main` |
| 审计基线 | `f06c840d0abac3ae9e46bc1bf8f745cf474f3da2` |
| Codex 权限 | pull/read；无 push |
| writer 规则 | HERMES 单 writer |

### 2.2 最近完成的真实工程工作

最近合并工作证明项目在 A0 底盘方向有持续推进：

- PR #38：桌面端确定性 `WM_CLOSE` 生命周期修复；先销毁 native window，再退出进程。
- PR #37：项目命名对齐矩阵，但主要是文档，未完成全仓用户可见命名迁移。
- PR #36：Task Cockpit 与 Cognitive Canvas 页面接入。
- 更早工作：portable data root、Workspace BFF、导航壳、Release 与 Windows lifecycle 修复。

这些工作改善了桌面可靠性和管理入口，但不构成“全面兼容同类软件”的产品闭环。

### 2.3 CI 状态

已确认 PR #38 头提交 `9ffd72a...` 的 CI run 成功，9 个 job 全绿，包括：

- browser smoke
- lint
- Windows runtime smoke
- wheel smoke
- Python 3.11 / 3.12 / 3.13 tests
- desktop shell
- A0 gates

风险：当前 `main` merge SHA `f06c840...` 的 workflow runs 通过当前 connector 返回空集合。现有 wrapper 只返回 PR 触发的首屏 run，因此这里不能将“PR 头绿”偷换为“当前 main 精确 SHA 已绿”。Release 前必须从 GitHub Actions 原始 API/页面或 `gh` 取得 exact-SHA 证据。

### 2.4 版本与 Release 真相

| 项目 | 当前事实 | 问题 |
| --- | --- | --- |
| `app/release-manifest.json` | `0.4.4` | `unreleased / public=false` |
| `pyproject.toml` | `0.4.4` | 与状态页不一致 |
| `PROJECT_STATUS.md` | 写 `0.4.2` | 明显过期 |
| README | 仍混有 `0.4.2` 与旧定位 | 对外真相漂移 |
| tag `v0.4.4` | 指向早于当前 main 的旧提交 | 当前 main 不能重用此 tag/version |
| Release workflow | 多处硬编码 `0.4.4` | 下一版必须升级 |
| public installer | manifest 标记 `not_implemented` | 不能宣称公开可安装发布完成 |

必须执行：

- 修复当前开发线时使用 `0.4.5`，不得移动或覆盖既有 `v0.4.4`。
- 新最小面闭环对外 alpha 完成后再进入 `0.5.0`。
- Release identity 要区分 `verification_ci_run` 与 `release_run`；不能把 Release workflow 自己的 run ID 当作前置验证 CI。
- 发布声明只能建立在 exact tag SHA、全绿 CI、下载资产、SHA-256 复算、manifest readback 和 Windows lifecycle 证据上。

### 2.5 定位一致性审计

`docs/PRODUCT_POSITIONING.md` 已正确写出：

- 本地优先、证据驱动、个人与 AI 双向学习和知识系统。
- Agent 不是产品中心。
- 对外用 `Learning & Knowledge System`、`Human–AI Learning Workspace`。

但以下仍漂移：

- 仓库名仍为 `Cognitive-Loop-OS`。
- `pyproject.toml` description/keywords/console script 仍有 cognitive OS / agent 语义。
- manifest 仍写 `ArcheAxis Cognitive Workspace`。
- README 和状态页仍出现“认知闭环”。
- PR #37 的命名矩阵仍以 Cognitive Runtime/Workspace 为主。
- UI 中 task/cognitive/canvas 的表达仍偏旧蓝图。

处理原则：

- 不做危险的全仓 bulk rename。
- 内部 ID、包名、数据库名和 CLI 先保留兼容。
- 先统一所有用户可见标题、描述、帮助文本、manifest display name、README 首页和发布说明。
- 对历史文档加 `historical` 标识，不删除证据。

### 2.6 Registry 与开源吸收状态

当前仓库 registry/ledger：

- 共 101 项。
- `implemented = 8`。
- `adapter_contract_pending = 27`。
- `deferred_review = 38`。
- `reference_only = 28`。

当前 implemented 的 8 项是：LiteLLM、Crawl4AI、Trafilatura、MarkItDown、Langfuse、NetworkX、sqlite-vec、Loguru。

必须避免三种错误等同：

```text
进入研究池 ≠ 进入 registry
进入 registry ≠ 已集成
已集成一个依赖 ≠ 已兼容该软件产品
```

用户此前的研究主表有 369 个去重候选，而仓库测试仍硬编码精确 101 项和末项 ID。这会阻挡研究池扩展，应改成 schema、唯一性、排序、证据和状态约束测试，而不是固定数量测试。

### 2.7 当前架构可保留资产

以下能力应原样保留，并通过新 Compatibility Kernel 暴露，不应重写：

- FastAPI + SQLite + Tauri 本地桌面底盘。
- URL、GitHub、approved-root 本地文件 intake。
- Job / Outbox / Delivery Receipt 和事务读回。
- Candidate / Claim / Evidence / Knowledge 等治理合同。
- MigrationOperator 与多 owner 迁移。
- Safe HTTP、loopback 写入、approved roots、symlink/junction containment。
- MarkItDown、Trafilatura、OCR、FFmpeg/media 基础。
- NetworkX、sqlite-vec、FTS 和 LiteLLM。
- release manifest、wheel smoke、Windows runtime/lifecycle 门禁。
- BFF 的 `public_ref` 与内部 ID 隐藏设计。

### 2.8 当前 UI 审计

现有导航分为：首页、资料与知识、学习、AI、系统。实际状态大致如下：

- Available：overview、research、evidence、knowledge、canvas、diagnostics。
- Partial：runtime、delivery、learning、evolution、machine knowledge。
- Planned：projects、agents、skills、models、workflow builder、runs、integrations、MCP、audit、settings。

主要问题：

- 没有日常知识工作台的核心布局：文件树 + 编辑器 + 右侧属性/链接/引用 + 全局搜索。
- task cockpit 仍读 legacy jobs/global lifecycle，未使用 BFF 的稳定 `public_ref`。
- 任务选择依赖 `activity` 字符串，不是稳定实体身份。
- lifecycle 是全局聚合，不与选定任务绑定。
- task cockpit 和 canvas 的测试主要是字符串存在测试，不是行为或 E2E。
- canvas 页面虽然标为 available，但主要是创建空画布和读回，不等于成熟画布编辑器。
- 已规划的大量 Agent 页面会稀释当前最小面，需统一后移或降级为“实验室”。

### 2.9 当前兼容能力审计

Obsidian/PKM 方面目前只有：

- 外部路径必须显式传入，不能默认访问个人磁盘。
- 文档中规划了 `ObsidianVaultSourceV1`、`VaultFileV1` 等未来合同。
- `shared/canvas.py` 借鉴 Heptabase/Obsidian Canvas 的内部数据模型。
- Markdown/Wikilink 有局部质量检查。

尚未发现真实实现：

- Vault 扫描与增量游标。
- Frontmatter 类型保真。
- Wikilink、embed、heading/block reference、alias 的可逆解析。
- callout、task、tag、attachment 的兼容。
- `.canvas` JSON Canvas import/export。
- Obsidian → ArcheAxis → Obsidian 的 C3 往返测试。
- 冲突报告、未识别语法报告和原文件不破坏保证。

因此目前不能宣称“兼容 Obsidian”，更不能宣称“全面复刻 Obsidian”。

---

## 3. 新最小面闭环阶段与当前完成度

以下百分比是本次审计判断值，不是机器测试结果。每一项只有通过本文件的验收门禁才可改为完成。

| 阶段 | 内容 | 当前估算 | 判断 |
| --- | --- | ---: | --- |
| S0 | 真相、桌面、版本与发布底线 | 70% | 底盘较强；版本、exact-SHA、installer、命名仍未收口 |
| S1 | 市场能力地图、源码复用与许可证账本 | 25% | 有 101 项账本和 369 项研究池，但未统一；仅 8 项 implemented |
| S2 | 通用工作区对象模型、格式层、Adapter SDK | 20% | 有治理合同和适配器雏形，无统一兼容内核 |
| S3 | PKM 核心工作台：树、编辑、属性、标签、链接、搜索、画布 | 20% | 有导航壳和局部页面，无成熟主工作区 |
| S4 | Obsidian/Markdown/Canvas 及其他 PKM 导入导出 | 5% | 以边界和设计文档为主，真实兼容近乎未开始 |
| S5 | PDF/Web/Office/媒体阅读、标注与来源追踪 | 35% | 摄入和转换基础存在；reader/annotation 产品面缺失 |
| S6 | 有引用的 AI 阅读、问答与摘要 | 15% | LiteLLM/检索底座存在；产品化 sourced Q&A 不完整 |
| S7 | 轻量学习：卡片、完形、复习、掌握 | 20% | 后端对象存在；真实学习体验和 Anki 往返未形成 |
| S8 | 跨软件往返、重启、冲突、安全和性能验证 | 10% | 有通用测试基础；没有兼容 fixture 矩阵 |
| S9 | Windows 可安装公开 Alpha 与迁移文档 | 35% | workflow 存在；当前 public installer 未实现、版本真相未闭环 |

### 3.1 完成阶段的重新表述

旧 Phase 0–9 不能直接映射为新产品完成度。更准确的说法是：

- 基础工程、合同、安全、迁移、研究候选治理已形成较强底座。
- Workspace 摄入/Job/Outbox/Receipt 已形成一条后台纵切。
- 桌面壳、portable data root 和 Windows 生命周期正在接近可靠。
- 面向用户的知识工作区、格式兼容、阅读、AI 问答、轻学习和往返迁移尚未闭环。

旧评分表和“最后三个维度上 8 分”的讨论必须以新定位重算。今后分数只认下面三类证据：

1. 用户可操作的真实产品路径。
2. 跨应用真实 fixture 的导入/导出/往返结果。
3. exact-SHA CI、可安装 artifact、重启读回和回滚证据。

计划、自评、文件数量和字符串测试不得把任何维度推到 8 分以上。

---

## 4. 对本轮错误的完整复盘

### E1：没有先锁定最高优先级定位文件

我在回答前没有先把 `docs/PRODUCT_POSITIONING.md` 作为产品语义的最高仓库事实源，导致旧路线、旧命名和仓库名影响了判断。

纠正：任何审计的第一步必须输出“定位校验头”：正式定位、非定位、当前最小闭环、延期内容、基线 SHA。

### E2：被仓库名和旧术语锚定

`Cognitive-Loop-OS`、Cognitive Workspace、认知闭环、Agent 相关页面仍散布仓库。我错误地让这些遗留词覆盖了新定位。

纠正：将遗留术语视为兼容债务，而不是路线依据；用户可见命名与内部 canonical ID 分开治理。

### E3：把“全面兼容吸收同类软件”缩成“复刻 Obsidian”

Obsidian 应是第一条高价值兼容纵切，不是整个阶段的边界。用户原始决定包含 Anytype、NotebookLM、Readwise、AppFlowy、Obsidian/Logseq、Anki、Langfuse/Phoenix、Home Assistant、VS Code 等成熟结构。

纠正：阶段目标用“能力面 + 兼容层级 + 产品波次”描述，不再用单一竞品代替完整阶段。

### E4：混淆“全面兼容”“全面复刻”“复制源码”

三者不是一回事：

- 全面兼容：数据、格式、工作流和迁移体验可互通。
- 能力吸收：复用开源组件或借鉴成熟交互结构。
- 全面复刻：几乎复制目标产品完整表面，成本和法律风险都更高。

纠正：以开放格式和可逆迁移为核心；对闭源产品只用公开格式/API/SDK/行为测试。

### E5：延续了 Agent/重型蓝图导向的评分

旧评分把 Agent Runtime、复杂演化和重型闭环作为高权重，和当前“先做全面兼容吸收最小面”的决定冲突。

纠正：当前评分只围绕可用工作台、兼容广度、往返保真、复用效率、可靠发布。

### E6：没有先做仓库内部矛盾检查

如果先比较 positioning、manifest、README、status、naming matrix，就会立即发现：新定位已经存在，但传播未完成。

纠正：增加 `truth-drift` 机器门禁，扫描版本、display name、定位句和 capability 状态的冲突。

### E7：混淆研究数量、注册数量和实现数量

369 个研究候选、101 个 registry 项和 8 个 implemented 项代表三个阶段。我在早期表述里没有始终分开。

纠正：所有报告固定输出 `researched / registered / evaluated / selected / integrated / verified` 六列。

### E8：验证证据层级表述不够严格

PR 头 CI 绿色不能自动证明 merge SHA 或 Release artifact 已验证。

纠正：验证报告固定记录 source SHA、tree SHA、CI run、artifact digest、下载复算、安装生命周期和 readback；任何一项缺失即为未完成。

### E9：没有在任务一开始复述用户的阶段决策

这是记忆使用失败，也是协作流程失败。即使历史内容已被整理，我也没有先做范围 checksum。

纠正：后续每次长审计先复述五行 scope checksum，并要求 HERMES 写进每个 PR 描述：

```text
定位：Human–AI Learning & Knowledge System
当前闭环：全面兼容吸收最小面
第一纵切：Obsidian/Markdown/JSON Canvas
实现原则：合法源码复用/调用优先
延期：重型 Agent、深层双向学习、3D/VR/企业化等
```

---

## 5. 源码复用优先政策

### 5.1 强制复用阶梯

每个功能在进入开发前必须依次证明前一层不可用：

1. **直接依赖**：使用成熟、维护活跃、许可证兼容的包。
2. **官方 SDK/API/CLI 调用**：不复制实现，只集成稳定接口。
3. **受控 fork/vendor/组件嵌入**：固定 upstream commit，保留 LICENSE、NOTICE、修改记录和升级路径。
4. **Adapter/Sidecar**：对许可证、语言或进程边界不适合直接合并的项目，以独立进程或插件隔离。
5. **Clean-room 自研**：仅当不存在可复用实现、许可证不允许、组件不满足安全/性能或兼容要求时使用。

每个任务包必须包含 `Reuse Decision Record`，若直接进入第 5 层，PR 不得合并。

### 5.2 许可证门禁

| 类型 | 默认策略 |
| --- | --- |
| MIT/BSD/Apache-2.0 等宽松许可 | 可直接依赖、fork 或 vendor；保留许可与 NOTICE |
| LGPL/MPL 等弱 copyleft | 优先动态链接、独立包或边界隔离；逐项法律审查 |
| GPL/AGPL 等强 copyleft | 默认 sidecar/独立分发或 clean-room；确认衍生作品和网络分发义务前不得合入核心 |
| Source-available | 按具体条款审查，不将“可看源码”误写为开源 |
| 闭源/专有 | 仅用公开 API、SDK、导出格式和黑盒行为兼容 |
| 未知/无 LICENSE | 阻断，不复制、不 vendor、不发布 |

本政策不是法律意见；任何分发前都要由项目负责人确认许可证义务。

### 5.3 对 Obsidian 等闭源产品的边界

- 不复制 Obsidian 私有源码。
- 可使用其公开文档、公开文件格式、官方 API 和官方 sample plugin。
- 可实现 Markdown、YAML frontmatter、wikilink、embed、JSON Canvas 等公开/事实格式兼容。
- 插件兼容只能基于官方公开 API；不得宣称未实际运行验证的“100% 插件兼容”。
- NotebookLM/Readwise/Notion 等优先走官方导出/API；没有公开接口时只做用户持有数据的导入。

### 5.4 供应链必备字段

每个复用项目至少记录：

- upstream URL、owner、版本/tag、精确 commit。
- SPDX license、LICENSE 文件 hash、NOTICE 要求。
- 引入方式：dependency/fork/vendor/sidecar/API/reference。
- 使用范围、修改文件、暴露接口、数据访问边界。
- CVE/维护状态、最后提交、替代方案、升级负责人。
- SBOM 条目、第三方声明、回滚步骤。
- 验收 fixture、性能基线、兼容级别和证据链接。

---

## 6. 兼容级别定义

以后禁止使用无级别的“已兼容”。统一使用：

| 级别 | 定义 |
| --- | --- |
| C0 | 已登记：格式/接口/许可证/能力已研究，尚无运行实现 |
| C1 | 可导入：能读入真实 fixture，并生成保真报告 |
| C2 | 可导出：能导出目标或约定开放格式，并被目标工具读取 |
| C3 | 可往返：A → ArcheAxis → A，语义与资源在容差内保真 |
| C4 | 可增量同步：有 cursor、冲突检测、双写保护和恢复机制 |
| C5 | 运行时/插件兼容：可运行目标扩展或 API，必须有真实运行矩阵 |

### 最小面 Alpha 的承诺边界

- 所有研究对象达到 C0，并完成能力/许可证归档。
- 每类软件至少一个代表产品达到 C1。
- Markdown/JSON Canvas 等开放格式达到 C2。
- Obsidian Vault 基础、Markdown、JSON Canvas、Anki 基础交换达到 C3。
- C4 仅做受控本地文件增量同步试点。
- 不在本阶段承诺通用 C5 插件运行时兼容。

---

## 7. 新架构：Compatibility Kernel

### 7.1 核心对象

建立独立、版本化、与单一竞品解耦的对象模型：

- `WorkspaceObjectV1`
- `DocumentV1`
- `BlockV1`
- `PropertyV1`
- `TagV1`
- `LinkV1`
- `AttachmentV1`
- `CanvasV1`
- `CanvasNodeV1`
- `CanvasEdgeV1`
- `AnnotationV1`
- `CardDeckV1`
- `CardV1`
- `ImportSessionV1`
- `ExportSessionV1`
- `SyncCursorV1`
- `ConflictV1`
- `CompatibilityReportV1`

所有对象必须保留：

- `source_ref` 和原始路径。
- 原格式/方言和解析版本。
- stable external ID（如存在）。
- 原始片段或可验证 hash。
- 未识别语法/属性的 passthrough 区域。
- 导入、变更、导出和冲突 provenance。

### 7.2 Adapter 接口

每个同类软件通过统一接口接入：

```text
probe(source) -> CapabilityProbe
scan(source, cursor?) -> SourceInventory
plan_import(inventory) -> ImportPlan
import_batch(plan, batch) -> ImportReceipt
plan_export(target) -> ExportPlan
export_batch(plan, batch) -> ExportReceipt
validate_roundtrip(fixture) -> CompatibilityReport
resume(cursor) -> next batch
rollback(session_id) -> RollbackReceipt
```

强制边界：

- Adapter 不直接写核心表，必须经过 Compatibility Kernel service。
- 导入先进入 staging/quarantine，再通过 schema 校验和事务提升。
- 原始资产只读保存；默认不原地修改用户 Vault。
- 导出默认写入新目录；覆盖必须显式授权并有 backup manifest。
- 每批都有 hash、数量、失败项、重试和幂等键。

### 7.3 数据分层

```text
Raw Assets（原始文件，只读/内容寻址）
  → Staging（解析结果、未知字段、错误）
  → Canonical Compatibility Model
  → Governed Knowledge / Learning / Evidence
  → UI Projections / Search / Graph
  → Exporters / Sync Adapters
```

这能同时保留原始数据、支持多软件迁移，又不让竞品格式污染核心治理模型。

---

## 8. 产品波次与同类项目吸收矩阵

### Wave A：最小面必须完成

1. Obsidian Vault / CommonMark+扩展 Markdown / JSON Canvas。
2. 主工作区：文件树、编辑器、属性、标签、链接、反链、搜索、附件、画布。
3. PDF/Web/Office 阅读与标注。
4. 有引用的 AI 问答/摘要。
5. Anki/FSRS 基础卡片与复习。
6. Windows 安装、迁移向导、回滚和 fixture 往返。

### Wave B：同类 PKM 广度

- Logseq
- Joplin
- SiYuan
- AppFlowy
- AFFiNE
- Anytype
- Notesnook
- Trilium
- SilverBullet/Foam
- Zotero

目标：每项至少 C0；代表性公开格式至少 C1；可合法复用的开源组件优先直接集成或 adapter。

### Wave C：研究与学习生态

- Readwise/Reader：官方 API/导出兼容。
- NotebookLM：吸收“来源集合 + 引用回答 + 学习产物”工作流，不复制闭源实现。
- Anki/FSRS：牌组交换、调度算法和复习体验。
- Moodle/Open edX/Kolibri/H5P：课程/活动格式研究，先 C0/C1。
- Langfuse/Phoenix：保留为 AI 使用观测能力，不上升为产品中心。

### Wave D：结构吸收而非当前闭环

- VS Code：扩展宿主、命令面板、工作区结构。
- Home Assistant：integration manifest、配置流、设备/实体式能力注册思想。
- n8n/Airflow：工作流与耐久执行。

这些只用于架构吸收或后续插件系统，不在最小面内建设通用 Agent 平台。

---

## 9. 完整执行任务包

## TP-MS00：产品真相与 Release 基线收口

**目标**：消除新定位、版本、manifest、README、状态页和 Release workflow 的矛盾，为后续兼容开发建立可信基线。

**范围**：

- 用户可见名称统一为 Learning & Knowledge System / Human–AI Learning Workspace。
- 内部 ID/包名/CLI 暂保留，建立 alias/兼容说明。
- 开发版本升级到 `0.4.5`；不移动任何历史 tag。
- README、PROJECT_STATUS、CHANGELOG、manifest、pyproject、Tauri 显示版本一致。
- `verification_ci_run` 与 `release_run` 分离。
- 新增 truth-drift 测试。

**RED 测试**：人为制造一个版本/定位冲突，测试必须失败；Release identity 将两个 run 混用时必须失败。

**GREEN 验收**：

- 全仓用户可见产品名一致。
- 机器检查仅允许白名单内历史/internal 术语。
- `0.4.5` exact-SHA CI 通过。
- 不宣称 public installer；如发布 remediation 包，必须有下载/readback/lifecycle 证据。

**回滚**：只回滚新增 commit；不 reset、不 force push、不改历史 tag。

---

## TP-MS01：369 项研究池、101 项账本和复用决策统一

**目标**：建立唯一市场/开源能力台账，作为全面兼容吸收的控制面。

**范围**：

- 将 369 项研究池归并进 versioned registry，不要求一次全部进入实现队列。
- 去除 `tests/test_registry_v2.py` 对精确 101 条和末项 ID 的硬编码。
- 新 schema 增加 `compatibility_level`、`reuse_mode`、`license_spdx`、`license_hash`、`upstream_commit`、`capability_domains`、`selected_components`、`evidence`。
- 状态统一为 researched/registered/evaluated/selected/integrated/verified/deferred/rejected。
- 每个项目建立 license/provenance gate。

**优先复用**：延续现有 registry/ledger 和 R0 provenance contract，不另建第二套账本。

**RED 测试**：重复 URL、未知许可证却 selected、无精确 commit 的 vendor、implemented 无证据、统计不一致必须失败。

**GREEN 验收**：

- 369 项都可被唯一追踪或有明确去重映射。
- 101 项旧 ID 和证据不丢失。
- 能生成按能力、许可、复用方式、兼容等级的机器报告。

---

## TP-MS02：核心组件复用 Spike 与选型

**目标**：不从零写编辑器、画布、文件树和数据视图，先验证可嵌入的成熟开源组件。

**候选能力，不预先锁死具体项目**：

- 编辑内核：ProseMirror/TipTap/BlockNote/CodeMirror 类。
- 画布：JSON Canvas 兼容库、tldraw/XYFlow 类。
- 文件树/虚拟列表/命令面板：成熟 UI 组件。
- Markdown AST：成熟 parser + 方言扩展。
- 搜索：保留 SQLite FTS/sqlite-vec，补 UI 层。

**约束**：候选必须重新核验当前许可证、维护状态、包大小、Tauri 离线运行、CSP、安全和可访问性；本文件不替代实际选型调查。

**Spike 输出**：

- 至少两个候选的运行 demo。
- License/size/performance/extension/serialization 对比。
- ADR：选择、拒绝原因、升级路径、最小 fork 面。
- 可删除的实验分支，不把 demo 当产品完成。

**GREEN 验收**：在 Tauri 离线环境加载 1000 文档目录、打开 1 MB Markdown、编辑/保存/重启读回，并通过基础内存/响应时间预算。

---

## TP-MS03：Compatibility Kernel 与 Adapter SDK

**目标**：完成第 7 节对象、服务和 Adapter 合同，所有外部软件接入都走统一通道。

**范围**：

- versioned contracts、JSON schema、迁移 owner。
- staging、session、receipt、cursor、conflict、report。
- 原始文件 content hash 和 passthrough。
- import/export dry-run、resume、rollback。
- BFF 投影使用 `public_ref`，UI 不暴露内部 ID。

**优先复用**：现有 contracts、MigrationOperator、Job/Outbox/Receipt、processing manifest、approved roots、安全 HTTP。

**RED 测试**：路径越界、symlink escape、重复 batch、崩溃恢复、未知字段丢失、Adapter 直写核心表必须失败。

**GREEN 验收**：fixture 导入中途终止后可 resume；rollback 后数据库、导出目录和 receipt 一致；重启读回完全相同。

---

## TP-MS04：Obsidian / Markdown / JSON Canvas C3 纵切

**目标**：建立首条端到端高保真兼容路径，而不是复制 Obsidian UI 或私有源码。

**导入范围**：

- 文件夹/Vault、Markdown、YAML frontmatter。
- 标题、段落、列表、task、表格、代码块、公式保留。
- wikilink、alias、embed、heading/block reference。
- tag、callout、附件与相对路径。
- `.canvas` JSON Canvas 节点、边、分组、颜色和未知字段 passthrough。

**导出范围**：

- 导出到新目录，默认不修改源 Vault。
- 保留文件名、相对链接和附件结构。
- 未能表示的内容生成机器可读 loss report。

**真实 fixture 矩阵**：

- 中英文、Unicode、空格、长路径、重复文件名。
- 大小写冲突、broken link、循环 embed。
- frontmatter 多类型、alias、日期、数组。
- 画布 file/text/link/group 节点。
- 100/1,000/10,000 文件规模档。

**C3 验收**：

```text
Fixture Vault A
 → import
 → UI edit one note / one property / one canvas position
 → restart
 → export Vault B
 → target parser/readback
 → semantic diff within documented tolerance
```

任何数据丢失必须进入 loss report；silent loss 为阻断错误。

---

## TP-MS05：日常可用的核心知识工作台

**目标**：把现有管理页壳升级为真正可持续使用的主工作区。

**布局**：

```text
左：Workspace/Vault、文件树、标签、收藏
中：编辑器 / 阅读器 / 画布
右：属性、反向链接、出链、引用、AI 上下文
顶：全局搜索、命令面板、创建/导入
底：后台任务、同步/导入状态、错误与冲突
```

**优先复用**：TP-MS02 选定组件；保留现有 BFF、安全边界和搜索底座。

**范围**：文件创建/重命名/移动/删除到回收站、编辑自动保存、属性、标签、链接提示、反链、全文/语义搜索、附件预览、画布编辑。

**非目标**：通用 Agent builder、复杂 workflow、多人协作、移动端、3D。

**GREEN 验收**：从启动应用到导入 Vault、搜索、编辑、建链、画布修改、关闭、重启读回，全程无需命令行；真实 Playwright/Tauri 点击测试覆盖主路径。

---

## TP-MS06：第二波 PKM Adapter

**目标**：证明 Compatibility Kernel 不是 Obsidian 专用。

**优先顺序**：

1. Logseq、Joplin、SiYuan。
2. AppFlowy、AFFiNE、Anytype。
3. Notesnook、Trilium、SilverBullet/Foam。

**执行方式**：

- 开源且许可兼容：优先直接依赖其 parser/exporter 或受控 fork。
- 有稳定 API/CLI：优先调用。
- 数据库私有且易变：只通过官方导出，不反向破解。
- 每个 Adapter 独立 taskpack、独立 fixture、独立兼容等级。

**最小验收**：每组至少一个 C1；不能导出的产品明确标记 C1，不虚报 C2/C3。

---

## TP-MS07：重型资料阅读、标注与研究工作台

**目标**：把现有摄入底座变成真实阅读体验。

**范围**：

- PDF、网页、Office、图片、音视频的 source asset 页面。
- 页码/时间戳/DOM 片段级 annotation anchor。
- 高亮、批注、摘录、Claim/Evidence 回链。
- Zotero 导入；Readwise/Reader 走官方 API/导出。
- 原文与转换文本并排，任何 OCR/ASR 不确定性可见。

**优先复用**：MarkItDown、Trafilatura、现有 OCR/FFmpeg、成熟 PDF.js/annotation 组件；先做许可证和 Tauri 验证。

**非目标**：本阶段不自研浏览器内核、不抓取受保护内容、不绕过 DRM/登录。

**GREEN 验收**：PDF 高亮在重启后定位稳定；网页快照可追溯；引用能回到具体页/时间/片段；导出保留引用信息。

---

## TP-MS08：有来源的 AI 阅读与问答

**目标**：吸收 NotebookLM 类“来源集合 + 引用回答 + 学习产物”体验，但不复制闭源实现。

**范围**：

- 用户选择来源集合形成 context pack。
- 问答、摘要、对比、时间线、FAQ。
- 每个关键结论绑定可点击 citation。
- 无证据时明确回答不足，不生成 verified truth。
- 模型/提示/来源/输出/反馈 trace 可读回。

**优先复用**：现有 LiteLLM、FTS/sqlite-vec、Evidence/Claim/Candidate 合同；必要时调用成熟 RAG/observability 组件。

**非目标**：通用 autonomous Agent、长时自主执行、自动知识晋升。

**GREEN 验收**：固定 fixture 问题集上，引用命中率、无依据拒答、重启读回和模型不可用降级均有测试。

---

## TP-MS09：Anki/FSRS 轻量学习闭环

**目标**：将阅读/笔记转为可复习材料，完成最小个人学习闭环。

**范围**：

- basic、cloze、正反面卡片。
- 从高亮/笔记生成 Candidate Card，用户确认后入组。
- 使用成熟 FSRS 实现，不自研调度算法。
- Anki 包/字段/牌组的基础导入导出和 C3 fixture。
- 复习记录与 MasterySignal 连接，但不扩展为重型学习科学平台。

**GREEN 验收**：导入牌组、复习、关闭重启、导出并由目标工具读取；调度状态不静默丢失。

---

## TP-MS10：兼容性、冲突、安全、性能和恢复总门禁

**目标**：把“能演示”提升为“可迁移真实个人知识库”。

**测试矩阵**：

- import/export/roundtrip。
- restart/crash/resume/rollback。
- 路径穿越、symlink/junction、恶意压缩包、超大文件、编码炸弹。
- 同名、大小写、非法 Windows 字符、长路径。
- 同步冲突和并发编辑。
- 1k/10k/50k 文档规模基线。
- 离线启动、模型不可用、外部服务不可用。
- 从旧 `0.4.x` 数据目录迁移。

**完成标准**：所有 Wave A fixture 的兼容报告可复现；silent loss=0；阻断级安全问题=0；失败可回滚。

---

## TP-MS11：0.5.0 Minimum-Surface Public Alpha

**目标**：发布第一个代表新定位的 Windows 公开 Alpha。

**前置条件**：MS00–MS10 全部达到各自 gate；不是只合并代码。

**发布内容**：

- Windows installer。
- 精确 source/tag/tree/CI identity。
- SBOM、THIRD_PARTY_NOTICES、dependency/license report。
- SHA-256 checksums 与 provider digest。
- 下载后复算、安装、启动、导入 demo Vault、重启、卸载生命周期证据。
- Obsidian/Markdown/Canvas/Anki 兼容级别表。
- 已知数据损失边界、备份和回滚说明。
- 从 `0.4.x` 的迁移说明。

**禁止**：在 installer、exact-SHA CI、资产 readback 或兼容 fixture 缺任一项时宣布 Alpha 完成。

---

## 10. 任务排序与并行边界

唯一允许的主路径：

```text
MS00 → MS01 → MS02 → MS03 → MS04 → MS05
                         ├→ MS07 → MS08
                         ├→ MS09
                         └→ MS06
MS04/MS05/MS06/MS07/MS08/MS09 → MS10 → MS11
```

规则：

- MS00、MS01、MS03 是串行门禁，不能跳过。
- MS02 可以做多个候选 spike，但只有一个 writer 合并。
- MS06/07/09 可在 MS03 稳定后分支研究；不允许多 writer 同改核心合同。
- MS08 必须建立在 MS07 的真实 source/citation anchor 上。
- MS11 不接受“功能 PR 都绿”替代完整集成与 installer 证据。

---

## 11. 明确延期的重型蓝图

在 0.5.0 Minimum-Surface Alpha 前冻结：

- 通用 Agent OS、完整 Agent Runtime、Agent Marketplace。
- 通用 workflow builder、复杂 durable orchestration。
- 深层 Human Learning 科学模型与完整课程平台。
- Machine Knowledge 自主演化、自动 Lesson 提升。
- 全面 Evaluation/Evolution/Sleep Loop。
- 2.5D/3D、VR/AR、空间工作台。
- 企业多租户、组织权限、实时多人协作。
- 社区、社交、插件市场和商业化体系。
- 完整移动端与多端实时同步。
- 所有同类软件的 C4/C5。

这些内容保留在 deferred backlog，不删除、不抢占最小面资源。

---

## 12. HERMES 主执行指令

以下内容可直接作为 HERMES 的总任务指令：

```text
你是 DTALEX66/Cognitive-Loop-OS 的唯一 writer。

产品定位：ArcheAxis OS 是面向个人与 AI 的、本地优先、证据驱动的双向重型学习与知识系统；不是认知闭环系统，也不是通用 Agent OS。

当前最小面闭环：全面兼容、吸收市面同类软件的成熟能力。第一条高保真纵切是 Obsidian Vault / Markdown / JSON Canvas，但阶段边界不限于 Obsidian。其他重型 Agent、深层学习演化、3D/VR、企业化蓝图延期。

实施原则：优先合法复用同类开源源码、依赖、SDK、API、CLI、fork、vendor 或 sidecar；clean-room 自研是最后选择。闭源产品只做公开格式/API/行为兼容，禁止复制私有源码。许可证未知即阻断。

基线：开始每个 TaskPack 前 fetch origin，报告 main SHA、目标分支 SHA、dirty 状态、相关 PR/CI/Release。不得 reset --hard、force push、移动历史 tag、覆盖他人提交、扫描个人 E 盘/个人 Vault/其他项目。

执行顺序：严格按 MS00 → MS01 → MS02 → MS03 → MS04 → MS05，再并行收口 MS06/MS07/MS08/MS09，最后 MS10 → MS11。一次只执行一个可验收 TaskPack，不把计划、占位文件、字符串测试或模型自评计作完成。

每个 TaskPack 必须：
1. 创建独立分支；先 RED 测试，再最小实现，再 GREEN。
2. 提交 Reuse Decision Record：候选、许可证、精确 upstream commit、选择/拒绝原因、升级和回滚路径。
3. 使用仓库现有安全、迁移、Job/Outbox/Receipt、BFF public_ref、approved roots 和 release gates，不另造旁路。
4. Adapter 不得直写核心表；所有外部输入进入 staging/candidate，不能自动成为 verified truth。
5. 默认只读源数据，导出到新目录；覆盖或同步必须有显式授权、backup manifest 和 rollback。
6. 运行任务包内 unit/integration/browser/Tauri/restart/roundtrip 测试。
7. 推送后取得 PR 头 exact-SHA CI；合并后再取得 main merge exact-SHA CI。二者不可互相替代。
8. 报告真实文件、真实命令、真实测试结果、真实 CI run、真实 artifact/readback；未知即写 UNKNOWN。

完成报告固定输出：
- 定位与 scope checksum
- before/after SHA
- 修改文件
- 复用项目、版本、commit、license、引入方式
- 新增/变更合同与迁移
- RED/GREEN 测试
- 兼容等级 C0-C5
- fixture 与 semantic diff
- 安全/性能/重启/回滚证据
- PR/CI/Release 链接
- 未完成项和下一 TaskPack

任何 taskpack 如果需要扩大授权、访问外部个人数据、修改其他仓库、引入许可证不明源码或改写历史，立即停止并请求用户决定。
```

---

## 13. Definition of Done

新的最小面闭环只有同时满足以下条件才完成：

### 产品

- 用户无需命令行即可导入真实 Vault/资料、阅读、编辑、建链、搜索、画布、AI 问答、复习和导出。
- 主工作区没有以 planned Agent 页面占据产品中心。
- 用户可见定位统一，旧术语只出现在白名单历史/internal 场景。

### 兼容

- Obsidian/Markdown/JSON Canvas 达到承诺的 C3 fixture 门禁。
- Anki 基础交换达到 C3。
- 每类同类软件至少一个代表 Adapter 达到 C1。
- 未支持或有损内容有机器可读报告，silent loss 为零。

### 工程

- 复用组件都有精确 upstream、license、SBOM、NOTICE、升级和回滚记录。
- 所有 schema 由 migration owner 管理。
- 崩溃后可 resume，失败可 rollback，重启可读回。
- source adapter 不越权，不默认修改用户原数据。

### 验证与发布

- unit、integration、browser、真实 Tauri 点击、Windows lifecycle 全绿。
- PR SHA 与 merge SHA 分别有 exact-SHA CI。
- 0.5.0 tag 精确绑定受保护 main。
- installer、checksum、provider digest、下载复算、manifest identity、安装/卸载证据齐全。
- release notes 明确兼容级别和已知限制。

---

## 14. 立即执行的前三个动作

1. **先执行 MS00**：收口定位/版本/Release 真相，开发线升级 `0.4.5`，添加 truth-drift gate。
2. **再执行 MS01**：统一 369/101/8 三层事实，去掉固定 101 测试，建立 license/reuse/compatibility 账本。
3. **随后执行 MS02**：对编辑器、画布、Markdown AST、文件树做开源复用 spike；完成 ADR 后才进入 Compatibility Kernel。

不要直接开始大规模写 Obsidian clone。那会绕过格式内核、许可证账本和组件选型，最终形成高成本的一次性实现。

---

## 15. 审计证据入口

- 仓库：<https://github.com/DTALEX66/Cognitive-Loop-OS>
- 审计基线：<https://github.com/DTALEX66/Cognitive-Loop-OS/commit/f06c840d0abac3ae9e46bc1bf8f745cf474f3da2>
- 正式定位：<https://github.com/DTALEX66/Cognitive-Loop-OS/blob/f06c840d0abac3ae9e46bc1bf8f745cf474f3da2/docs/PRODUCT_POSITIONING.md>
- 当前状态：<https://github.com/DTALEX66/Cognitive-Loop-OS/blob/f06c840d0abac3ae9e46bc1bf8f745cf474f3da2/docs/PROJECT_STATUS.md>
- Release manifest：<https://github.com/DTALEX66/Cognitive-Loop-OS/blob/f06c840d0abac3ae9e46bc1bf8f745cf474f3da2/app/release-manifest.json>
- PR #38：<https://github.com/DTALEX66/Cognitive-Loop-OS/pull/38>
- PR #37：<https://github.com/DTALEX66/Cognitive-Loop-OS/pull/37>
- PR #36：<https://github.com/DTALEX66/Cognitive-Loop-OS/pull/36>

---

## 16. 最终决策记录

本文件确认并冻结以下决策，直到用户再次明确修改：

1. 项目不是认知闭环系统；正式定位是 Human–AI Learning & Knowledge System。
2. 将原阶段 6“全面研究、兼容、吸收同类软件”前移为新的最小面闭环。
3. Obsidian 是第一条高保真纵切，不是全部阶段。
4. 以合法复制/复用/调用同类开源项目源码和组件为首选，降低工作量。
5. 对闭源产品只做公开格式/API/行为兼容。
6. 其他重型蓝图延期，不删除。
7. HERMES 是唯一 writer；Codex 保持只读审计。
8. 完成以真实运行、往返 fixture、exact-SHA CI、可安装 artifact、重启读回和回滚证据为准。
