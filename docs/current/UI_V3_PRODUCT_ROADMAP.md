# UI v3 产品路线图

- 当前轨道：canonical React/Tauri 单壳收敛已实现，当前分支待原生 WebView / installer / exact-SHA 验证
- 生产入口：主 Tauri React WebView；`/workspace` 产品页返回 410，仅保留 `/workspace/api/*`
- 设计底座：黑白深色基线（黑底、白灰结构、低饱和状态色）
- 语言：中文优先

## 视觉权威与历史参考

- 黑白深色基线是当前默认主题；不写入 `data-theme`，不得把白底、深绿、青绿或玻璃覆盖层
  作为默认视觉重新引入。
- Archive Desk / Liquid Glass 是历史参考，不是默认主题。任何未来吸收都必须先有独立设计
  决策、可访问性/性能验收和用户明确确认；不得借“路线图”或旧截图直接替换生产界面。
- `frontend/src/design-system/tokens.css` 与主 Tauri 的可见运行时回读优先于旧 UI 方案、历史
  handoff 或原型文档；视觉证据必须区分源码浏览器、Tauri/Green WebView 和已安装产品路径。

## 已运行底座

| 底座/能力 | 生产状态 | 边界 |
| --- | --- | --- |
| DeepTutor v1.5.17 | 可选学习 sidecar | authority projection；不拥有产品导航，不写核心真值 |
| Docling / MarkItDown / Office adapters | 已接入 | 通过窄转换适配器 |
| OCR / ffmpeg / ASR | 部分到已接入 | 缺依赖时显式失败 |
| sqlite-vec | 已接入 | 可重建索引 |
| FSRS / BKT | 已接入 | 只影响人类学习证据 |
| PDF 阅读 | 已接入 | 后端魔数/大小校验；sandboxed Blob frame；不再分发 PDF.js |
| Tauri / NSIS / Green / Portable | 已发布 | 项目数据边界独立 |

## 当前生产页面

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

## 下一阶段

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

### P0R — 单壳收敛与前端真值（当前实现）

- [x] canonical shell 锁定为 `frontend/src/app/App.tsx` + `src-tauri/`。
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
