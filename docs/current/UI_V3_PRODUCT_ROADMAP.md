# 当前 UI 设计与历史路线图

> **2026-10-10 路由修正**：产品PAUSED_BY_OWNER；本轮仅治理维护，六项增量冻结。旧路线和下一队列不是恢复指令。先查 [路径身份路由](AAOS-AUTHORITY-ROUTES.json) 与活动指针；当前事实使用最新分域回执。

> **2026-10-09 当前执行覆盖**：用户已选择新 UI 优先任务及 G01；规范活动指针为 [AAOS-ACTIVE-EXECUTION](AAOS-ACTIVE-EXECUTION.json)，当前任务来源为 [UI 优先 TaskPack](../taskpacks/aaos-ui-first-20261009/TASKPACK.md)，实际进度只读 [UI 执行记录](AAOS-UI-FIRST-EXECUTION-20261009.md)。规划原文的 PLANNING_READY / NOT_EXECUTED 是规划时状态，激活与实际结果由当前覆盖记录，不改写不可变原包。AAOS-01 Q00–Q15 台账仅记录该继承工作流，不代表新 UI 全队列；旧 R6/M0 整包顺序冻结，有效合同、单一 Rust Core writer、内容先保存及历史证据保留。V01 继续暂停。
> 当前新布局、架构和其余产品界面按新任务执行；默认 `blueprint`，配套 `blueprint-light`，旧 `black` / `white` / `cosmic` 仅为额外配色主题。五主题共用新布局、组件状态及统一语义颜色；一个主题内部的按钮、菜单、侧栏与正文保持一致。主题不更改 Core 配置或知识数据。
> 平台指令优先；平台范围内用户当前明确决定优先于项目旧描述。此文档同步不授予 commit、push、merge、发布、私人账户/会话访问或恢复暂停的云端任务权限；本机资源索引不是云端权限。

## 当前设计来源

- 新22页参考、tokens与资产来源通过 [UI任务包](../taskpacks/aaos-ui-first-20261009/README.md) 和来源登记核对，页面职责以 [PAGE-PLAN](../taskpacks/aaos-ui-first-20261009/PAGE-PLAN.csv) 承接。
- 五域布局和语义页面按新任务实施；普通文档、Tiptap与Core逻辑复用，历史hash兼容不作为新默认布局。
- `blueprint` 是新设计默认，`blueprint-light` 是配套浅色，旧 `black` / `white` / `cosmic` 只作额外主题；五主题共用新布局、组件状态、页面密度和缩放规则，按钮、菜单、侧栏及正文用统一语义颜色。主题切换只更新前端宿主资源，不更改 Core 配置或知识数据。
- B10/Aurora/Archive Desk/Liquid Glass 是历史参考，不是默认主题或当前新布局权威。当前任务尚未接通的页面明示不可用；不把22页意图、原型演示内容或截图当产品完成度。

## 历史视觉与路线说明（原日期与证据范围保留）

以下整段保留此前路线描述；其中“当前”“最高视觉依据”“两套主题”与正式Avalonia回读等措辞仅对原历史阶段有效，不覆盖上面的当前设计。旧阶段计划不自动执行。

- 当前正式轨道（2026-10-08 更正）：Tauri 2 + React/TypeScript/Vite 宿主（`frontend/`、`src-tauri/`）＋ Rust Core 唯一 SQLite/CAS 写者；依据 `DECISION_SUPERSESSION_LEDGER.yaml` SUP-021 → SUP-022（2026-10-04 业主裁决）与根 `AGENTS.md` §6。本文件此前写"当前正式轨道：C#/Avalonia 桌面壳；React/Tauri 只作 legacy"，那是 SUP-021 时代的读法，保留于此作为更正记录，不再作为当前结论。
- 正式桌面入口：`src-tauri/tauri.conf.json`；`apps/ArcheAxis.Desktop/`（C#/Avalonia）为冻结行为/组件供体；`desktop/` 是独立恢复入口（标识 `com.archeaxis.workspace.recovery`）；legacy `/workspace` 产品页返回 410，仅保留兼容 API
- 设计底座：用户采用的 B10 最终可部署母版；Aurora 与黑白深色两套配色共用布局及状态
- 语言：中文优先

## 视觉权威与历史参考

- 当前用户采用提示词指定的 **B10 最终高保真可部署母版是最高视觉依据**，决定其覆盖的页面布局、导航、区域关系、整体构图与交互；不能由旧测试、原型或较早 B03 参考反向覆盖。此前 B03 优先解释属于历史阶段，已被本次明确方向取代。
- 母版上的深空黑蓝、Ivory、Aurora Teal 与少量星辉金为 AAOS 品牌皮肤。用户同时要求保留黑白深色方案并提供配套主题化：两套主题共用 ArcheAxis 母版布局、组件状态、页面密度和缩放规则；只切换已定义的色彩资源。主题切换只更新前端宿主资源，不更改 Core 配置或知识数据。
- B03/B05 页面参考、B04 组件与 tokens、B06/B07 响应式和工程合同、B09 交互补充仅在不冲突 B10 和当前用户指令时吸收。B10 中的示例计数、证据与图谱不能充当 Core 真值；保留真实数据、未知/不可用状态、键盘可达和减少动画边界。双主题采用同构页面，只切换已定义配色资源。
- Archive Desk / Liquid Glass 是历史参考，不是默认主题。其他主题方向仍须有独立设计决策、
  可访问性/性能验收和用户明确确认；不得借“路线图”或旧截图直接替换生产界面。
- `frontend/src/design-system/tokens.css` 与 legacy Tauri 的可见运行时回读只用于行为/视觉对照，正式
  Avalonia 运行时的回读优先于旧 UI 方案、历史
  handoff 或原型文档；视觉证据必须区分源码浏览器、Tauri/Green WebView 和已安装产品路径。

## 历史 Web/Tauri 集成能力快照（不代表 Avalonia 页面接线）

> 下表是旧 UI/sidecar 的历史集成记录。当前组件资格和桌面页面接线须分别按 R6 A03、Core/API 与正式 Avalonia 运行时证据核实。

| 底座/能力 | 生产状态 | 边界 |
| --- | --- | --- |
| DeepTutor v1.5.17 | 可选学习 sidecar | authority projection；不拥有产品导航，不写核心真值 |
| Docling / MarkItDown / Office adapters | 已接入 | 通过窄转换适配器 |
| OCR / ffmpeg / ASR | 部分到已接入 | 缺依赖时显式失败 |
| sqlite-vec | 已接入 | 可重建索引 |
| FSRS / BKT | 已接入 | 只影响人类学习证据 |
| PDF 阅读 | 已接入 | 后端魔数/大小校验；sandboxed Blob frame；不再分发 PDF.js |
| Tauri / NSIS / Green / Portable | 已发布（legacy 发布线） | 非当前正式壳；项目数据边界独立，保留为恢复与行为参考 |

## 2026-08 React/Tauri 页面快照（非当前 Avalonia 页面状态）

> 下表来自旧 Web/Tauri 产品面的页面清单，不能证明这些页面已迁移到当前 Avalonia 正式桌面。

| 页面 | 状态 | 真实来源 |
| --- | --- | --- |
| 工作台总览 | 已接入 | Workspace status |
| 本地资料库 | 已接入 | Vault inspect/search/write/backups |
| 任务与回执 | 已接入 | Job/Outbox/Receipt/lifecycle |
| 研究复核 | 已接入 | Research candidate projection |
| 候选知识 | 已接入 | Knowledge projection |
| 知识画布 | 已接入 | Canvas API |
| 学习路线 | 部分接入 | Learning projection |
| 掌握与反馈 | 部分接入 | Human/Machine split projection |
| 机器知识 | 部分接入 | Approved/candidate governance |
| 证据中心 | 已接入 | Lifecycle/PDF/Anchor/Exchange/Backup |
| 视觉课件 | 文档规划 | 不进入普通用户导航 |
| 空间记忆 | 文档规划 | 不进入普通用户导航 |
| 路线图与设计史 | 已接入 | 受版本控制的产品真值 |

## 历史阶段计划（冻结；由 R6/M0 取代）

> 以下 P0.5/P1/P2 计划属于旧 React/Tauri 阶段。当前执行顺序只由 R6 TaskPack、M0 overlay 与当前执行台账决定。

### P0 — 本地生产迁移（历史完成，已被 P0R 单壳收敛取代）

- [x] 所有 active 页面切换到 OSUI 壳层 token 和中文优先文案。
- [x] 生产 Adapter 覆盖 OSUI 主要方法；不可用方法返回明确失败，不回退 Mock。
- [x] 工作台、导入、任务、证据、学习和设置走真实 API。
- [x] 加入设计图对比、窄屏几何、活动坞折叠、Inspector 可访问性门。
- [x] 真实原生 Tauri WebView 启动、后端握手和“工作台→资料库”点击回读。

### P0.5 — 云端与安装候选（待完成）

- GitHub exact-SHA CI。
- Windows NSIS/Green/Portable candidate lifecycle。
- 后续版本 tag、公开资产 identity/checksum/readback；不得改写 v0.6.11。

### P0R — 单壳收敛与前端真值（HISTORICAL SNAPSHOT：当时为 React/Tauri 单壳）

> 下方 `[x]` 记录的是当时（React/Tauri 阶段）的收敛结果。**2026-10-08 更正**：SUP-022（2026-10-04 业主裁决）之后 `frontend/` 与 `src-tauri/` 重新成为正式产品宿主，所以本节标题里的"当时为 React/Tauri 单壳"读法如今与主线一致，但它仍是历史快照，不代表当时的验收；本文件旧版本在此写"当前正式轨道是 C#/Avalonia，React/Tauri 只作 legacy 行为参考，见 `config/product/UI_CONTRACT_V2.json` 的 `productShell.webCompatibilityRole`"，该字段已随合同收敛删除，现行字段是 `productShell.productionEntrypoint`、`productShell.donorShell` 与 `productShell.recoveryEntry`。

- [x] （历史）canonical shell 当时锁定为 `frontend/src/app/App.tsx` + `src-tauri/`；该“canonical”称谓已作废，现为 legacy behavior reference。
- [x] 全局命令、当前空间二级导航、可折叠 Inspector/Activity Dock。
- [x] 390×844 / 360×640 横向导航与布局流内底栏。
- [x] 退役 `/kb` Dashboard 与根 legacy HERMES 面板。
- [x] React Library 接入原件阅读与页级 EvidenceAnchor 投影。
- [x] API 2xx DTO 运行时校验、Setup preflight 门禁、Intake 错误脱敏。
- [x] Tauri Recovery WebView 先启动、Core 异步启动。
- [x] 离线黑白深色 token：不加载网络字体、不保留紫色主强调色；命令面板仅在显式打开时成为模态遮罩，含 reduced-motion 降级。
- [ ] 当前分支 Windows Rust/原生 WebView/NSIS/exact-SHA/人工视觉复审。

实施与对标来源：[`FRONTEND_CONSOLIDATION_V1_2026-08-28.md`](FRONTEND_CONSOLIDATION_V1_2026-08-28.md)。

### P1 — 原件与证据工作台

- 将多格式阅读器升级为页码轨 + 实色纸面 + 派生版本面板。
- 把 Claim/Evidence/Bundle 关系从列表提升为工作台，同时保留列表等价访问。
- Anchor CURRENT/STALE/ORPHANED 状态进入检查器。

### P2 — 学习产品底座融合

- DeepTutor 学习会话通过 authority bridge 投影进入统一学习空间。
- 学习响应只写 LearningEvent，不直接写机器 K。
- Teach Back、复习与错误恢复使用真实对象和回执。

### P3 — 视觉课件与空间记忆

只有以下条件全部满足时开放执行：

- 真实学习对象；
- EvidenceBundle 和锚点；
- 场景/时间线或 Locus/Route 合同；
- 失败和撤销；
- 静态/文字/低动效替代；
- 性能和设备探针；
- 学习效果证据。

## 明确不做

- 不把界面改成普通 AI 聊天首页。
- 不把 Runtime、Agent、MCP 或内部 ID 放入一级导航。
- 不用紫色营销渐变替代设计语言。
- 不用 Mock 数量、伪进度或未绑定按钮填满页面。
- 不因 release 通过就跳过视觉验收。
