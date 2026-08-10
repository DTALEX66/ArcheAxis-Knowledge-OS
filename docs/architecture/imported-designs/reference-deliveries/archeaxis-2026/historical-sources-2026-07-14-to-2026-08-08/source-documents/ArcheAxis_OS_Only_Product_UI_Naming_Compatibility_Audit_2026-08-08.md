# ArcheAxis OS：定位、产品、UI、命名与兼容路线总审计

> 审计日期：2026-08-08
> 云端基线：`DTALEX66/Cognitive-Loop-OS` / `main@4512377314a9d95e2482023568365f268eb808d2`
> 范围：仅 ArcheAxis OS（本仓库）。不把外部工作流、验证控制项目或历史协作基础设施当作 OS 产品的一部分。

## 0. 结论先行

本项目现在的正确定位不是“认知闭环系统”、不是通用 Agent OS，也不是以任务/Runtime 仪表盘为中心的产品。它应被统一为：

> **ArcheAxis Workspace（元枢工作台）是一个本地优先、证据驱动、面向人和 AI 的学习与知识工作台。**
> **当前阶段以开放格式互操作与成熟能力吸收为最小面；Obsidian Vault、Markdown 与 JSON Canvas 是第一条高保真垂直闭环。AI 是可引用的使用层，不是产品中心。**

这里的“全面兼容/吸收”应理解为：以明确、可测试、可回滚的兼容矩阵逐项实现用户可感知的互操作能力；不是复制任何产品的全部源码、品牌或私有插件生态。第一闭环的完成条件是可以真实打开一个隔离 Vault，阅读、编辑、保存、重启回读、处理链接/附件/Canvas，并在冲突或失败时报告和恢复；现状尚未达到。

当前仓库的工程底座、桌面壳、受治理的资料/知识/学习构件和新建的兼容内核都有价值；但用户界面仍主要服务于旧的 Research → Knowledge → Runtime 治理仪表盘，和新的“本地互操作知识工作台”之间存在结构性错位。最高优先级不是重写前端，也不是继续扩张 Agent/Runtime，而是完成 **兼容内核真相修正 + Vault 工作台第一垂直面**。

## 1. 本次采用的上下文：哪些是当前决策，哪些不是

### 1.1 当前绑定决策

以下内容相互一致，作为后续实现的产品契约：

1. 产品是本地优先、证据驱动的 Human–AI Learning & Knowledge Workspace；稳定知识、证据、学习和用户资料优先于任一模型或 Agent。
2. 当前最小面提前为“开放本地知识工作台的全面能力吸收阶段”；Obsidian/Markdown/JSON Canvas 是首个高保真兼容纵切，而非旧路线中很晚的一个导入任务。
3. 第一条真实用户路径必须覆盖：

   ```text
   选择/导入 Vault
   → 文件树、阅读和编辑 Markdown
   → 属性、链接/反链、标签、搜索、附件、Canvas
   → 可引用的 AI 使用与轻量学习/复习
   → 开放格式导出
   → 重启回读、增量变化、冲突、回滚和损失报告
   ```

4. 重型 Runtime、通用多 Agent、市场、3D/VR、企业协作、远程同步等后置；既有代码可保留为内部能力，但不能再主导首页、导航或当前里程碑。
5. 源码复用优先级：合法依赖/SDK/API/CLI → 有许可的 fork/vendor → Adapter/sidecar → 自研。研究、登记、参考不等于已集成。

### 1.2 已纳入但不应覆盖当前决策的材料

| 材料 | 本次用途 | 处理结果 |
| --- | --- | --- |
| 2026-08-06 最小面主任务包 | 提供兼容内核、首个垂直面、验收标准 | 保留为高优先级设计依据 |
| 2026-08-07 云端全量审计 | 提供历史债务、分支、发布与文档漂移证据 | 与最新 main 再交叉核验 |
| 上传的 OS 集成建议文档 | 仅保留其关于边界、Obsidian P0、复用优先和重型能力后置的结论 | 本工作区副本已被系统清理，且原指令禁止通过 Library 重读；如需逐行复核请重新上传 |
| 仓库当前 `PRODUCT_POSITIONING.md` 与更新后的 `AGENTS.md` | 提供新定位和“Obsidian 首个高保真切片”的已写入事实 | 保留，但需补当前阶段和术语一致性 |
| 旧任务包、旧 handoff、旧蓝图、旧 registry | 只用于识别污染和迁移边界 | 不再作为产品排序或能力宣称依据 |

### 1.3 必须排除的污染项

- “Cognitive Loop / Cognitive OS / 认知运行时”作为对外产品中心的叙事。
- 旧的 `Research → Knowledge → Learning → Runtime` 重型闭环作为当前 UI 的默认路径。
- 将 Agent、模型、技能、MCP、工作流构建器放在产品一级导航。
- 将“已研究/已登记的 101 个开源项目”表述为“已经吸收/兼容”。
- 将个人 Vault、旧外部项目或任意外部目录当作可自动扫描或写回的目标。
- 不相关协作或验证基础设施的产品概念、命名和页面进入 OS 的定位、导航或发布文案。

## 2. 云端现状审计

### 2.1 产品真实度评分（审计判断，不是测试结果）

| 维度 | 当前 | 原因 | 下一阶段目标 |
| --- | ---:| --- | --- |
| 工程/桌面壳与基础可访问性 | 7/10 | Tauri、响应式壳、键盘/焦点/移动抽屉、浏览器 smoke 已存在 | 保留并换成工作台内容 |
| 现有治理资料链 | 6/10 | 本地导入、候选、知识、学习、回读已有真实路径 | 收为“来源/证据”辅助层 |
| 产品信息架构 | 3.5/10 | 首屏和导航仍围绕旧运行时与规划入口 | 以 Vault 工作台重排 |
| Obsidian 第一条用户路径 | 2.5/10 | 有旧导入器和新语义分析，但没有 Vault 打开、编辑、写回、回读 UI | 先完成 UI-1/2 |
| 高保真格式兼容 | 2/10 | 有 Markdown/Canvas 起步契约，缺附件、稳定身份、增量、冲突、完整 loss report | 以声明矩阵逐项验收 |
| 命名一致性 | 3/10 | 同时暴露 5–7 套产品名称和旧术语 | 先立 Naming Contract v2 |

### 2.2 近期更新：有进展，但没有改变最小闭环结论

当前 main 最新合并为 #53。K2/K3 相关提交新增了 `shared/compat/`：Vault 文件模型、导入会话、修订回滚，以及 Markdown/JSON Canvas 的语义分析；#53 还修复了部分受治理工作区路径中的延迟导入 500。相关 PR 的定向 CI 已成功。

这些是值得保留的底座，但它们不是完整兼容闭环，原因如下：

1. `VaultFile` 的 frontmatter 解析是手写子集。它会重排/合并评论，忽略空行、引号、复杂对象、锚点、流式结构等未识别 YAML；`unknown_fields` 从未填充，`loss_report()` 实际永远为空。它不能称为“无损 YAML round-trip”。
2. `ImportSession.scan()` 遍历所有文件后直接按 UTF-8 文本读取。图片、PDF、音视频等附件会触发解码错误；兼容账本也没有附件对象、MIME、原始字节哈希、mtime、大小策略或复制/引用策略。
3. 写回 `RevisionLog.record()` 未校验 approved root 或 `expected_hash`，无法拒绝并发改动；`rollback()` 又退回直接 `write_text`，没有原子写、冲突检查或恢复结果记录。
4. 旧 `shared/obsidian_importer.py` 仍是硬编码中文目录、随机 ID、正文 5k/10k 截断、非幂等地写入核心表的旧导入器；它还会直接把 machine knowledge 标为 active。`/obsidian/import/apply` 仍可到达这条路径，不能作为新产品入口。
5. 旧投影 `shared/obsidian_projection.py` 明确是一向 Markdown 投影，并继续直接 `write_text`。部分投影 API 已改为 `501` fail-closed，这比运行时报错正确，但也说明投影不是可用能力。
6. K3 的 `analyze_markdown` 与 `analyze_canvas` 仅是纯分析器和小型 fixture 测试；没有 Vault identity、链接索引回写、真实附件、交互 UI、Windows/Tauri 重启回读或跨版本兼容验证。

**结论：** 兼容内核状态应标为 `foundation / not user-closed`，不能标“Obsidian bidirectional”或“全面兼容”。

### 2.3 文档和代码的主要错位

| 位置 | 当前真实情况 | 风险 | 要求 |
| --- | --- | --- | --- |
| `docs/PRODUCT_POSITIONING.md` | 新定位正确：本地优先、证据驱动、学习知识系统，Agent 非中心 | 未写当前“开放互操作工作台/Obsidian first”阶段 | 补产品阶段与验收边界 |
| `AGENTS.md` | 已写 broad compatibility 与首个 Obsidian/MD/Canvas 切片 | 表中仍称 `Cognitive-OS` 前台层；禁止语句过宽 | 保留个人数据禁令，允许许可审查后的指定上游研究/复用 |
| `README.md` | 标题已改，但主体仍是 Phase 0–9、Runtime、Job/Outbox、旧闭环 | 新用户和后续代理会被旧叙事带偏 | 重写首页；旧技术史移至 legacy |
| `docs/PROJECT_STATUS.md` | 日期仍为 2026-08-01，描述 A0/Runtime/旧外部吸收 | 漏 K2/K3/K4，且将旧路径当当前阶段 | 拆为“当前产品真相”和“历史能力” |
| `docs/ABSORPTION_EXECUTION_MATRIX.md` | J 兼容层仍排在 H/I/Runtime 之后；J-001 只是一向 fixture | 与已前置的最小面直接冲突 | 重写排序与状态，不删除保留历史 |
| `docs/FUTURE_EXECUTION_BLUEPRINT.md` | 仍以长期 World→Runtime 叙事及旧 Track 序列为主 | 继续污染任务选择 | 标为 legacy strategic reference，移出默认入口 |
| `knowledge_base/api.py` | OpenAPI 仍称已吸收 Obsidian/Tana/Notion/Logseq/Roam 等 | 明显过度陈述 | 改为 `planned/reference`，以矩阵为准 |
| 开源 registry/ledger | 101 项含 B 线、旧项目名和过时目标；生成日期 7/22 | 不可作当前路线账本 | 建新 OS-only upstream ledger，旧账本归档 |

## 3. 产品最小闭环：应如何定义“全面兼容”

### 3.1 不采用“全量复刻 Obsidian”的表述

不能将对方的产品源码、私有插件市场、品牌或全部行为作为复制目标。更可靠的定义是：**开源格式和用户日常核心工作流的高保真互操作**。这既符合本项目 MIT 边界，也能真正验证用户数据所有权。

第一阶段的兼容矩阵应至少有以下状态：

`not_scoped → researched → license_approved → adapter_ready → fixture_verified → desktop_verified → released`

每一项必须同时拥有：来源 revision、许可证、兼容方向、保真级别、已知损失、fixture、回滚点和真实证据。不能再用“支持/已吸收”一个词覆盖全部状态。

### 3.2 第一高保真垂直面的 P0 能力矩阵

| 能力 | 目标 | 现状 | P0 验收 |
| --- | --- | --- | --- |
| Vault 选择/授权 | 明确目录、approved root、隐藏目录策略 | 无用户工作台入口 | 选择→预览→确认；逃逸/symlink fail closed |
| 文件树/打开 | 真实层级、最近项、标签、搜索结果 | 无 | 浏览器/Tauri 打开 fixture Vault |
| Markdown 阅读/编辑 | 原文保真、保存、撤销、预览 | 无 | 修改后重启逐字回读 |
| YAML properties | 复杂 YAML 不静默丢失 | 手写子集，不足 | 使用 round-trip parser 或 raw-preserving patch；无法表达即 blocking loss |
| Links/backlinks | wikilink、Markdown link、aliases、anchors、block refs | 只分析，未入索引/UI | 点击跳转、反链、缺失目标报告 |
| Search/tags | 本地全文、过滤、证据定位 | 后端旧搜索未接入工作台 | 查询、结果、打开、重启一致 |
| Attachments | 图片/PDF/音频/视频引用与缺失报告 | 不支持 | 不读二进制为文本；路径、hash、MIME、预览/外部打开 |
| JSON Canvas | `.canvas` 读取、编辑、保存、语义 diff | 只做校验 | 打开/编辑/保存/重启/节点边保真 |
| 增量/冲突/回滚 | rename/delete/diff/expected-hash/revision | 不足 | 两次变化、并发冲突、回滚、可读 loss report |
| 学习与 AI | 有出处的问答/卡片/复习 | 旧治理链可借用，未接内容页 | 引文指向原文；复习独立聚焦模式 |

### 3.3 最小闭环的最终证据

同一套受控 fixture Vault（中文、英文、emoji、空格路径、长文、复杂 YAML、alias、链接、图片/PDF、缺失附件、`.canvas`、rename/delete、冲突）必须在 Chromium 和 Tauri/Windows 中完成：

```text
Open → inspect semantic/loss report → edit → atomic save → restart/reopen
→ verify content and relations → simulate external change → conflict resolution
→ rollback → export/reopen using the format
```

其中一项产生 silent loss、错误覆盖、未报告缺失附件或不能读回，即该纵切不通过。

## 4. 现有 UI 审计与目标布局

### 4.1 当前壳可复用，信息架构不可沿用

当前 UI 的 rail / subnav / main / inspector / activity dock 框架、响应式抽屉、焦点管理和 reduced-motion 处理是可复用资产。但它的内容结构不适合目标产品：

- 一级导航为“首页、资料与知识、学习、AI、系统”，二级还暴露 7 个未接入的 AI/Agent 页面。
- 顶栏同时放置品牌、静态工作区 tab、未接入的只读搜索、规划中命令入口、主题、诊断、用户，信息密度高而主操作不清。
- 右侧检查器固定展示 SQLite、receipt、Lifecycle、A1 Shell 等开发/治理信息，未展示当前文档的属性、反链、证据或附件。
- 固定底部活动坞占约 156px，重复 Job/Delivery/Review/“Truth Boundary”；在 1280px 宽度下中间实际工作区约 700px，无法承担编辑器。
- Canvas 目前是内部 SQLite “受治理画布”回放，不是 `.canvas` 内容模式。
- `global-search` 是只读占位；命令按钮只提示“规划中”。不应在正式产品表层暴露不可执行主操作。

### 4.2 目标工作台布局

```text
┌──────────────────────────────────────────────────────────────────────┐
│ ArcheAxis Workspace | Vault breadcrumb | 真正的搜索 | 新建 | 保存状态 │
├──────┬──────────────────────┬──────────────────────────┬─────────────┤
│ Rail │ Context side pane    │ 内容工作区               │ Inspector   │
│      │ Files / Search /     │ tabs + Markdown reader/  │ 可选：      │
│ Vault│ Tags / Outline       │ editor / Canvas / PDF    │ Properties  │
│Canvas│                      │                          │ Outline     │
│ Learn│                      │                          │ Backlinks   │
│ Ask* │                      │                          │ Evidence    │
│Setup │                      │                          │ Attachments │
├──────┴──────────────────────┴──────────────────────────┴─────────────┤
│ 可折叠 Activity：import / index / save / conflict / export            │
└──────────────────────────────────────────────────────────────────────┘
* Ask 只有在可展示引用和本地隐私边界时出现，不是 Agent 一级模块。
```

布局原则：

1. 默认入口是 **Vault / 最近打开的内容**，不是统计 dashboard。
2. 左轨只保留用户对象：`Workspace`、`Canvas`、`Learn`、`Ask`、`Settings`；诊断放开发设置，不面向普通用户。
3. 左侧第二栏是随上下文变化的工作面：文件树、搜索结果、标签或大纲。不要把“研究/证据/知识”拆成三个互相隔离的一级产品。
4. 中央编辑区永远是最大空间。右栏默认可关，只在选中文档后展示属性、反链、引用、附件和修订。
5. 活动面板默认折叠为 32–40px，仅报告可恢复的后台事项；不再常驻占用阅读/写作空间。
6. 顶栏只保留真实搜索、导入/新建、保存/同步/冲突状态与必要设置。命令面板在有真实命令前不出现。

### 4.3 当前路由到目标路由的处置

| 当前页面群 | 处置 | 新归属 |
| --- | --- | --- |
| 总览、项目、Runtime、Delivery | 从默认界面撤下；保留为内部诊断/活动详情 | Activity / Dev tools |
| Research、Evidence、Knowledge | 合为文档/来源上下文，不再作为三条孤立主路径 | Inspector / Sources tab |
| Canvas | 替换为真实 JSON Canvas 内容模式；旧 SQLite 回放迁为内部/导入工具 | Canvas |
| Learning、Evolution、Machine | 合为“Learn”：Cards、Review、Progress | Learn |
| Agents、Skills、Models、Builder、Runs、Integrations、MCP | 从用户一级导航删除 | Ask 的受控能力或开发设置 |
| Diagnostics、Audit、Settings | 保留，但压缩为 Settings；诊断只对开发/支持可见 | Settings / Dev |

### 4.4 UI 实施顺序

- **UI-0：真相与导航收口。** 新标题、默认 Vault 空状态、移除可见的规划中 AI 群和假的搜索/命令入口；不做视觉重写。
- **UI-1：只读 Vault 工作台。** 文件树、打开、阅读、属性/大纲/反链、链接/附件错误、搜索结果；只接兼容 API 和 fixture。
- **UI-2：编辑与索引。** Markdown 编辑、原子保存、revision、expected-hash 冲突、标签/反链/全文搜索、附件预览/外部打开。
- **UI-3：内容 Canvas 与学习/引用 AI。** JSON Canvas 编辑，证据引用问答，FSRS 复习页面。
- **UI-4：高保真闭环。** 多轮导入、rename/delete、外部修改、冲突、rollback、导出和 Windows/Tauri 回读。

不建议此时迁 React 或重写整个静态前端。先以模块化拆分现有 `app.js`（vault、editor、inspector、activity、settings）承接 UI-1；等真实编辑交互稳定后再评估框架迁移。

## 5. 名称审计与 Naming Contract v2

### 5.1 现有问题

当前用户可见和机器可见层同时使用：`Cognitive-Loop-OS`、`Cognitive OS`、`Cognitive Runtime`、`ArcheAxis OS`、`元枢系统`、`元枢桌面`、`元枢·观心`、`Human–AI Learning Workspace`。这不是多语言，而是多套互相竞争的产品身份。

尤其不合适的部分：

- **Cognitive-Loop-OS / Cognitive OS / 认知运行时**：旧定位，暗示通用认知/Agent 操作系统。
- **ArcheAxis OS / 元枢系统**：`OS/系统`过泛，继续把产品理解为平台或运行时。
- **元枢·观心**：诗性二级名无法说明用户要打开、编辑、互操作知识资料的工作台；不适合作为默认产品名。
- 旧 README、API title、Registry target 中的命名还会持续将后续实现拉回旧路线。

### 5.2 建议命名层级

| 层级 | 建议值 | 说明 |
| --- | --- | --- |
| 品牌 | **ArcheAxis / 元枢** | 可保留，待商标/域名检查后最终确认 |
| 对外产品 | **ArcheAxis Workspace / 元枢工作台** | 唯一用户主名称 |
| 当前版本/频道 | `ArcheAxis Workspace Alpha` | 未公开 stable 前使用，不夸大完成度 |
| 对外描述 | `本地优先、证据驱动的 Human–AI 学习与知识工作台` | 描述，不是第二品牌 |
| 当前里程碑 | `Obsidian-compatible Workspace` | 阶段名，不单独造新产品名 |
| 仓库技术 ID（暂保留） | `Cognitive-Loop-OS` | GitHub/历史引用兼容用，不进用户界面 |
| Python 分发/CLI（暂保留） | `cognitive-loop-os` / `cognitive-os` | 0.4/0.5 兼容；后续新增 `archeaxis` 别名 |
| Rust crate | `archeaxis-desktop-shell` | 名称健康，可保留 |
| Tauri identifier | `com.archeaxis.cognitive-workspace` | 暂勿改；关联安装/数据迁移，必须单独迁移 |
| 内部模块 | `vault`、`compat`、`source`、`evidence`、`revision`、`conflict`、`loss_report` | 新边界统一使用领域名 |

建议把“元枢·观心”降为可选 workspace/profile 模板名称或完全停止使用；不要让它和产品名并列。

### 5.3 迁移规则

1. 先创建 `docs/NAMING_CONTRACT_V2.md` 和机器可读 registry，定义 display / legacy / alias / forbidden 四类词。
2. UI、安装器显示名、README、release manifest、OpenAPI 先切换为 `ArcheAxis Workspace / 元枢工作台`；同时写明仓库技术 ID 仍为 legacy compatibility ID。
3. 在一次正式兼容发布前，新增 CLI 别名与稳定迁移说明；不要破坏 `cognitive-os`。
4. GitHub 仓库改名应单独决策：先完成 public display/installer 切换与链接清单，再利用 GitHub redirect 一次性迁移。没有用户授权不改远端名。
5. bundle identifier 与数据目录只有在有迁移、回滚、升级/卸载回读证据时才变更。

## 6. 开源项目、格式与界面布局：OS-only 选择表

### 6.1 总原则

旧 registry 的 101 项并非当前 OS 的可执行清单：它混入了旧项目目标、Agent/编码工具和已后置能力。应冻结它为历史候选库，另建 `upstreams/os-compat-ledger.json`。新账本以格式/能力/UI 模式为中心，每项强制写入 exact revision、license、组件范围、数据边界、集成方式、fixture 与退出条件。

| 类别 | 当前应取用的价值 | 处理方式 |
| --- | --- | --- |
| Obsidian | Vault 的用户工作流、链接语义、可配置 pane 语法 | 不复制品牌/私有产品；以开放 Markdown 和 JSON Canvas 为契约 |
| JSON Canvas | `.canvas` 的开放互操作格式 | 可直接作为 import/export/storage 格式；MIT 规范 |
| Markdown/YAML | 用户数据与 properties 的基础 | 选择可 round-trip 的受许可解析器；不能手写声称无损 |
| 编辑器 | 编辑、语法、撤销、搜索、可访问性 | 优先许可清晰的组件，例如 CodeMirror 类组件；逐包审计 |
| Canvas renderer | 可视编辑、缩放、拖拽、撤销 | JSON Canvas 先行；Excalidraw 仅作为未来 `.excalidraw` 适配器候选 |
| 研究/文献 | collection → item list → reader、注释→证据 | 取 Zotero 交互范式；模型与数据边界独立 |
| 学习/复习 | 专注 review、可解释间隔算法 | FSRS/py-fsrs 可作为受许可算法候选，不复制完整 Anki 产品 |
| 其他 PKM | 不同工作流的互操作需求 | 分别建 adapter，不污染 Vault canonical model |
| Agent/RAG/工作流 | 只在后续真正需要时调用 | 当前仅 reference/deferred；不进导航 |

### 6.2 外部产品与界面模式审计

| 参考对象 | 应吸收的交互/格式价值 | 许可证与复用结论 | 现在的动作 |
| --- | --- | --- | --- |
| Obsidian + JSON Canvas | 左侧文件/搜索，中间文档 tab，右侧属性/反链/大纲；可收起的 pane；Markdown/`.canvas` 数据所有权 | JSON Canvas 规范及资源 MIT，可被任意工具实现 [JSON Canvas](https://github.com/obsidianmd/jsoncanvas) | 第一 vertical；不要声称复制 Obsidian 应用 |
| Joplin | notebooks → note list → editor 的三栏信息取向，笔记 Markdown 与本地搜索 | 主仓库默认 AGPL-3.0-or-later，名称/logo 亦有限制 [Joplin license](https://github.com/laurent22/joplin/blob/dev/LICENSE) | 行为研究；不直接拷贝进 MIT 核心 |
| Logseq | block 引用、页面关系、journal/outline 与 PDF 注释思路 | 主仓库 AGPL-3.0 [Logseq](https://github.com/logseq/logseq) | 只做行为与格式研究，Markdown 兼容稳定后再考虑 block adapter |
| AFFiNE | 文档、Canvas、表格作为同一工作区的内容模式；Canvas 不应只是 dashboard | CE 声称 MIT，但 monorepo/组件需逐组件核验 [AFFiNE](https://github.com/toeverything/AFFiNE) | UI 模式参考；若复用组件须独立 SBOM/license decision |
| AppFlowy | local-first workspace、数据控制和结构化内容的产品经验 | AGPLv3 [AppFlowy](https://github.com/appflowy-io/appflowy) | 不直接嵌入；参考交互与数据边界 |
| SiYuan | 文档级 properties、块引用、分屏、PDF 资料处理 | AGPL 代码 | 行为研究；不进本仓库代码 |
| Zotero | collection → items → reader 三栏；注释与出处绑定 | 产品是资料收集、组织、注释、引用工具 [Zotero](https://github.com/zotero/zotero)；组件许可需单独核验 | 用于 Evidence/Reader 层，不是第一 Vault 编辑器 |
| Anki / py-fsrs | 专注复习而非 dashboard；间隔重复状态机 | `py-fsrs` 标为 MIT [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs) | Learn UI-3 后接算法；先固定 card/review contract |
| Excalidraw | 独立无限画布的拖拽、缩放、undo、导出交互 | 编辑器 MIT [Excalidraw](https://github.com/excalidraw/excalidraw) | 未来 `.excalidraw` adapter；不替代 JSON Canvas 首要兼容 |
| Notion/Roam/Capacities/Anytype 等 | 产品行为、功能缺口与迁移样本 | 商业/源可用/许可不明时一律 reference-only | 不复制代码、不写“已吸收” |

### 6.3 推荐的布局借鉴，不推荐的克隆

- 取 **Obsidian/VS Code** 的可调 pane 语法：activity rail → context pane → editor → optional inspector。
- 取 **Joplin/Zotero** 的“集合/列表/阅读”降级布局：当用户不是从文件树进入时，结果列表仍可高效打开笔记或资料。
- 取 **Logseq** 的关系可见性，但不要在 Markdown 兼容未稳定前改成 block-first 主模型。
- 取 **AFFiNE** 的文档/画布同工作区思路，但拒绝其“所有能力常驻在一张大表面”的复杂度。
- 取 **Anki** 的单任务复习模式；不要继续把复习埋在统计 dashboard。

## 7. OS-only 实施任务包

### P0 — Product Truth Reset（阻断后续漂移）

**目标：** 让所有默认入口只表达当前最小面。

- 新增 `PRODUCT_STAGE_COMPATIBILITY.md`：定位、第一 vertical、兼容状态定义、非目标。
- 重写 README 首屏、PRODUCT_STATUS 和 OpenAPI 描述；把 Phase 0–9、Runtime-heavy、旧蓝图和旧 taskpack 移至 `docs/legacy/`，加历史页眉和链接。
- 修正 AGENTS 的 legacy `Cognitive-OS` 表与过宽禁止语句；保留不扫描个人数据的安全边界。
- 把 `ABSORPTION_EXECUTION_MATRIX` 改为“兼容优先”：K0/K1 选择 → K2 kernel → K3 semantics → K4 Vault UI → K5 editing/readback；其他能力标 deferred。
- 建立 Naming Contract v2；更新测试，使它验证当前定位而非锁死旧词。

**验收：** 新 clone 的 README、AGENTS、产品状态、UI 标题、release manifest、OpenAPI 任取一处都不会把 OS 描述成 Cognitive/Agent OS，且都能指向同一当前最小面。

### P1 — Compatibility Kernel Hardening（先修真实数据安全）

**目标：** 将当前 skeleton 变为可作为 UI 依赖的可靠核心。

- 采用 K1 选定的可 round-trip YAML 方案，或保留 raw bytes 并在无法结构化修改时明确阻断；不再把手写子集称无损。
- 建模 `VaultRoot`、`VaultFile`、`AttachmentRef`、`LinkRef`、`Revision`、`Conflict`、`ImportSession`、`LossReport`、`SyncCursor`。
- Markdown、`.canvas` 和二进制附件分流；文件均有 stable relative identity、hash、mtime/size、mime、审计来源。
- 所有读取与写入均经过 approved root / realpath containment；写入支持 expected-hash、原子临时文件、revision、回滚也原子化。
- 识别 rename/delete、外部变更和重复导入；无法表达的语义必须进入 loss report 并阻断声称无损的操作。
- 将旧 `obsidian_importer` 的 real apply 路径迁为 legacy/blocked，绝不再写入 Knowledge/MKU 核心表作为兼容实现。

**验收：** 复杂 YAML、二进制附件、symlink、并发外部改动、rename/delete、rollback 都有 RED/GREEN fixture；无 silent loss。

### P2 — Vault Workbench Read-only（第一可用界面）

**目标：** 用户第一次可以在桌面中真正“打开自己的知识空间”。

- 新的 typed Vault API：选择/批准根目录、扫描、文件树、打开、搜索、语义/loss report、属性、链接/反链、附件清单。
- 按目标布局改 UI：真实 Vault 默认页，文件树、阅读器、可选 inspector；移除显眼的规划入口。
- 现有 Research/Evidence 仅作为来源和证据 inspector，不做新用户流程的第一屏。

**验收：** Chromium 与 Tauri 使用同一 fixture，选择 → 浏览 → 搜索 → 打开链接 → 查看属性/反链/附件缺失 → 重启回读均通过。

### P3 — Editor, Search and Revision（可写的本地工作台）

**目标：** Markdown/属性可安全编辑，所有改变可恢复。

- 以许可已批准的编辑器组件接入 Markdown source/preview、undo/redo、快捷键、accessibility。
- properties editor、tag/alias、搜索索引、backlink index、附件引用更新。
- 保存前 expected-hash；冲突 UI 展示 base/local/external 与选择策略；revision/recovery 可见。

**验收：** 编辑、保存、重启、外部修改冲突、撤销、回滚、搜索与反链重建在 browser/Tauri/Windows fixture 均可验证。

### P4 — Canvas, Evidence, Learn, Ask（内容能力，不是新平台）

**目标：** 把空间组织、来源阅读、轻量学习和 AI 接入同一份资料。

- JSON Canvas 原生打开/编辑/保存和 semantic diff；Excalidraw 只作独立后续适配器。
- PDF/网页来源以 Zotero 式阅读/注释/出处关联进入 inspector。
- Cards/Review 采用专注页面；调度算法与内容来源分离。
- Ask 仅允许引用当前 Vault/选中文档的可见出处；无出处答案必须标为候选或拒绝。

**验收：** Canvas、引用问答、卡片复习均可跳回原始内容；没有 AI 自动把内容提升为事实。

### P5 — C3 Interoperability / Release Proof（第一 vertical 的完成）

**目标：** 证明该 vertical 不是 demo。

- 建版本化公开 compatibility matrix 和 fixtures；覆盖跨语言文件名、复杂内容、插件常用文本语义、附件、Canvas、缺失项、外部修改。
- 导入、编辑、导出、重开、rename/delete、conflict/rollback 全链压力测试。
- Tauri/Windows 安装器、升级/卸载/数据保留与 exact release artifact/readback。

**验收：** 一次发布可引用 exact SHA、兼容矩阵、已知限制、fixture 结果与恢复说明；未支持项目清晰可见。

### P6 — 后续兼容适配器（只在 P5 后）

按“格式优先、用户数据优先”建立 Joplin、Logseq、SiYuan、AFFiNE、Zotero、Readwise、Anki 等独立 adapter TaskPack。每次只纳入一个格式/能力，不能为了“全面”把多个生态并行塞进核心。

## 8. 立即可执行的清单

1. 冻结任何扩大 Runtime/Agent/UI 占位页的工作。
2. 开 P0 PR：产品真相、命名契约、文档入口、UI 可见导航收口；不改安装标识或 GitHub 仓库名。
3. 开 P1 PR：先补 current compatibility kernel 的红测（附件、YAML 复杂结构、conflict、rollback）；确认底座真实后再加依赖或替换实现。
4. P2 只做 read-only Vault 工作台，并以隔离 fixture Vault 做第一次 browser/Tauri 端到端证据。
5. P3 后才开放写入与旧 importer apply 的替代迁移；写入以前不得宣传双向兼容。
6. 将开源 ledger 从“项目罗列”改成“可执行兼容选择表”；每次复用前固定 revision/license/SBOM。

## 9. 本次明确不做

- 不改云端仓库、不删除分支、不重命名 GitHub repo、不改 bundle identifier。
- 不把外部协作、审计或验证系统纳入 OS 产品设计。
- 不接入通用 Agent、MCP 市场、多 Agent、远程服务、3D/VR 或企业协作。
- 不把旧 Obsidian apply importer 扩展成新兼容方案。
- 不因“全面兼容”绕开版权、许可证、个人数据授权、fixture 和回滚门槛。

## 10. 需要产品负责人确认的两项命名决定

本任务包的默认建议是 `ArcheAxis Workspace / 元枢工作台`。请只在启动 P0 前确认：

1. **品牌是否继续使用“ArcheAxis / 元枢”？** 若保留，先做商标/域名与发行渠道检索后锁定。
2. **“元枢·观心”是完全废止，还是降为可选工作区模板名？** 建议废止为产品显示名。

其余事项无需再等命名决定：兼容内核硬化、Vault 工作台和文档真相收口可以立即开始。

## 11. 审计证据入口

- 最新界面：[index.html](https://github.com/DTALEX66/Cognitive-Loop-OS/blob/4512377314a9d95e2482023568365f268eb808d2/app/workspace/ui/index.html)、[app.js](https://github.com/DTALEX66/Cognitive-Loop-OS/blob/4512377314a9d95e2482023568365f268eb808d2/app/workspace/ui/assets/app.js)、[styles.css](https://github.com/DTALEX66/Cognitive-Loop-OS/blob/4512377314a9d95e2482023568365f268eb808d2/app/workspace/ui/assets/styles.css)
- 定位与命名：[PRODUCT_POSITIONING.md](https://github.com/DTALEX66/Cognitive-Loop-OS/blob/4512377314a9d95e2482023568365f268eb808d2/docs/PRODUCT_POSITIONING.md)、[AGENTS.md](https://github.com/DTALEX66/Cognitive-Loop-OS/blob/4512377314a9d95e2482023568365f268eb808d2/AGENTS.md)、[命名矩阵](https://github.com/DTALEX66/Cognitive-Loop-OS/blob/4512377314a9d95e2482023568365f268eb808d2/docs/NAMING_ALIGNMENT_MATRIX.md)
- 兼容内核：[models.py](https://github.com/DTALEX66/Cognitive-Loop-OS/blob/4512377314a9d95e2482023568365f268eb808d2/shared/compat/models.py)、[import_session.py](https://github.com/DTALEX66/Cognitive-Loop-OS/blob/4512377314a9d95e2482023568365f268eb808d2/shared/compat/import_session.py)、[revision.py](https://github.com/DTALEX66/Cognitive-Loop-OS/blob/4512377314a9d95e2482023568365f268eb808d2/shared/compat/revision.py)、[c3.py](https://github.com/DTALEX66/Cognitive-Loop-OS/blob/4512377314a9d95e2482023568365f268eb808d2/shared/compat/c3.py)
- 待退役旧桥接：[obsidian_importer.py](https://github.com/DTALEX66/Cognitive-Loop-OS/blob/4512377314a9d95e2482023568365f268eb808d2/shared/obsidian_importer.py)、[Obsidian API routes](https://github.com/DTALEX66/Cognitive-Loop-OS/blob/4512377314a9d95e2482023568365f268eb808d2/knowledge_base/api.py)
