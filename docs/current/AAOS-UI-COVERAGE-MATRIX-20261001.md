# AAOS 正式前端覆盖矩阵（2026-10-01，执行中）

## 证据边界

- 当前执行权威：`AGENTS.md`、`docs/CONFIGURATION_AUTHORITY_INDEX.md`、R6 TaskPack、`docs/current/R6-STATE.json` 与 M0 overlay。R6 状态仍为 `IN_PROGRESS`，release 为 `FROZEN`。
- 最终视觉母版：用户 2026-10-01 明确指定 `D:/All projects/UI套件/01_01_产品信息架构_Information_Architecture.png` 至 `12_12_搜索与复习_Search_Review_FSRS.png` 的产品 UI 图；同目录品牌视觉 `01_01_品牌主视觉_Brand_Hero.png` 至 `11_11_品牌应用_Applications_Left.png` 用于色彩、标志、字形、图形语言。B10 仅作交互结构参考，不再作为最终视觉验收标准。2026-09-28/29 UI 文档和 Master Atlas 是历史或阶段记录。
- 2026-09-28 完整任务包 `D:/All projects/Record/AAOS_ArcheAxis_今日完整整合最终任务包_2026-09-28.zip` SHA-256 `E989877203FD47B9A027B2ABD0D9521DEB9A97E5D5E6905697E0FCA451E5A753`；9 月 29 日规划和截图是日期绑定的历史记录。2026-09-30 ZIP SHA-256 `A51AE04407A807C647739F787ABDB91ACCD1021AB515BC989069CB2D25197170`，仅含两份 Markdown，无源码/图片。其 Current/Future、路由兼容、素材来源与许可证要求纳入对照；包内跨 WORK-LAB/DESIGN-LAB 实施不扩入本任务。
- 2026-10-01 四份外部材料的 AAOS 切片与四份源 SHA-256 见 `../history/external-inputs/2026-10-01/AAOS-ECOSYSTEM-AUDIT.md` 和 `AAOS-ECOSYSTEM-EXTRACT.json`。其中知识 owner、人审/version/provenance、精确 SHA 交付是待核对输入；缓存/目录/数据库清理迁移已被用户当前指令暂停。
- 根目录 `AUTHORITY.md` 缺失（`AUTHORITY_REFERENCE_MISSING`）；使用项目声明的 `PROJECT_CONTRACT.yaml`、决策账本和 Authority 索引。
- 本表为当前源码映射和待验收事项；“页面存在”不等于母版逐像素、实际交互、真实后端或绿色版安装验收通过。
- 逐页母版与资产详情见 `AAOS-UI-MASTER-ASSET-AUDIT-20261001.md`，逐资产路径/SHA/部署状态见 `AAOS-UI-ASSET-MANIFEST-20261001.json`，生产路由与真实身份映射见 `AAOS-UI-BACKEND-MAP-20261001.md`。

## 9 月 30 日 ZIP 对比结论

| ZIP 要求 | 本轮/当前权威对照 | 处理 |
| --- | --- | --- |
| 现有正式前端升级、保留 route/API/identity | 与用户本轮要求及 R6 C#/Avalonia + Rust Core 一致 | 纳入实施及兼容回归，不另起 React 前端 |
| Current Core + Future Capability、只读蓝图 | 与 M0 延后高级能力一致；蓝图不等于已实现 | 以现有 Capability Atlas/登记表为单源，逐页区分可用/未知 |
| 静态数据图替换动态数据视图 | 与“母版复刻”和真实后端状态同时适用；装饰图仍可保留 | 逐资产标识装饰/数据，数据图必须接真实来源并提供列表降级 |
| 开源 UI01–UI14 候选 | 当前正式栈为 Avalonia；多数示例是 React/CSS | 仅在具体组件缺口且许可、版本、源码适配已核实时选用，不整体引入第二设计系统 |
| WORK-LAB 与 DESIGN-LAB 同 Shell 实施 | 超出当前 AAOS 三个明确工作目录与本仓边界；R6 明确 WORK-LAB 非运行前提 | 记录为跨项目提案，不写入这两个项目或假装已接通 |
| `AUTHORITY.md` | 本仓根目录当前不存在 | `AUTHORITY_REFERENCE_MISSING`；按现有 Authority 索引执行 |
| 不自行 merge/release | R6 release 仍 `FROZEN`；用户 2026-10-01 明确要求“该合并的合并” | 已验证公共分支经 PR #155 合并；该历史 ZIP 的合并限制不覆盖当前用户授权，release 仍未授权 |
| 商业级 `RC_READY` | 当前 R6 `IN_PROGRESS`，桌面完整验收未完成 | 只在所有 DoD 真实通过时标记；否则保持 `PARTIAL` |

| 母版页面/工作面 | 当前实现入口 | 资产 | 关键交互 | 真实后端接口/状态 | 当前验收证据与缺口 |
| --- | --- | --- | --- | --- | --- |
| Home | `MainWindow.axaml.cs` route `home` | 双主题 Hero；B10 对照待逐项复核 | 快速捕获、最近证据 | Core 最近知识/状态投影；离线不可假造 KPI | 历史 native capture；当前正常启动/逐项视觉待验 |
| Capture Inbox | route `capture` | 原生矢量、扫描动效 | 导入、任务读回 | `/api/v1/imports`、jobs；保存不可用须明示 | 真实写入/恢复待验 |
| Evidence Library/Detail | route `evidence` | 原生矢量与来源 glyph | 筛选、详情、来源链 | anchors、knowledge V3、review decisions | 空/错/权限/冲突及 B10 视觉待验 |
| Originals/Editor | route `original-editor` | B10/B05 对照待核 | 编辑、引用、版本 | 无正式原创持久化接口时标记不可用 | 不得把本地草稿冒充 Core 写入 |
| Human Learning/Review | routes `learning`、`review` | 卡片翻转/矢量 | assessment、答案、FSRS 等级 | learning items/assessment/events/reviews/state | 历史 synthetic 闭环；本轮冷启动与负例待验 |
| Machine Learning | route `machine-growth` | 原生组件 | 任务、纠错、复测 | machine tasks；未接通模型能力显示 UNKNOWN | 真实模型运行仍未证实 |
| Workspace/Jobs | routes `workspace`、`jobs` | 原生空间树/状态边 | 任务执行、取消、结果回读 | workspaces/info、jobs/executions/outputs | 受 worker 配置约束，实际读回待验 |
| Memory Map | route `memory-map` | 原生矢量图谱；不可用时列表 | 节点选择、来源 Inspector | 无完整 graph API；不能显示示例为真实图 | 动效、键盘和数据边界待验 |
| Search | route `search` | 矢量筛选与结果 | 关键词、来源跳转 | `/api/v1/search` 当前词法 | 语义/向量筛选须标不可用 |
| Settings/Recovery | routes `settings`、`recovery` | 统一主题令牌 | Aurora/Monochrome、恢复 | system/version、workspace identity | DPI、IME、reduced motion 与恢复待验 |
| Reader/Knowledge/Library | routes `source-reader`、`knowledge`、`library` | B10/B05 对照待核 | 原件、锚点、知识详情 | sources、knowledge-items、search | 页面仍须覆盖成功/空/错/离线 |

## 横向验收

| 事项 | 状态 | 待完成证据 |
| --- | --- | --- |
| 逐页 UI 套件产品 PNG 布局/配图/图标/字体/间距 | `PARTIAL` | 用户指定的 12 张母版与原生截屏同尺寸逐页对照及差异记录；B10 仅核交互结构 |
| Aurora/Monochrome 和深空黑蓝/Ivory/Teal 令牌 | `PARTIAL` | 两主题所有页面与状态的视觉回读 |
| 交互、动画、缩放、IME/a11y | `PARTIAL` | 正常桌面启动、键鼠与 100/125/150/200% DPI 实测 |
| Desktop/Core 稳定启动 | `UNVERIFIED` | 实际日志定位、修复和重启回读；0xe0434352 本身不是根因 |
| 原绿色版集成 | `UNVERIFIED` | 原根准确启动路径、二进制/配置身份和同一 workspace 读回 |
| 远端交付 | `CI_VERIFIED_EXACT_SHA / MERGED_MAIN`，仅针对 2026-10-01 阶段性公共增量 | PR #155 head `6621aab7b7e2067f0ffe0fcaad1f479f7fd691d6` 与 merge/main `59498723a8d4e94c6314e490473ba6d60847c247` 的各自 CI success；后续 Green dirty UI 尚未交付 |
