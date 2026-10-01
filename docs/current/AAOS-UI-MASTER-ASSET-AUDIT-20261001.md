# AAOS 母版与资产覆盖审计（2026-10-01）

状态：`PARTIAL / SOURCE_AUDIT`。本文是本轮只读源码、母版压缩包和历史材料的覆盖索引；没有逐页像素差分或桌面运行验收。当前视觉标准按用户指令和 `docs/current/AAOS-UI-REVIEW-20260929.md` 的 2026-10-01 现行解释，以 B10 为最终母版；B01–B09 仅补充细节。R6/M0 执行权威仍由 `docs/CONFIGURATION_AUTHORITY_INDEX.md` 索引。`docs/current/R6-STATE.json` 的 `updated_at` 是 2026-09-26，不能据此判定今日 UI 完成。

## 母版及资产索引

| ID | 实际路径 | 本轮读回 | 可用性 |
|---|---|---|---|
| B10 | `D:\All projects\UI套件\10_B10_最终版高保真可部署UI\archeaxis_最终版_高保真可部署UI.zip` | 仅 `README.md`、42,376 B 的 `index.html`、Windows 打开批处理。11 个主导航路由。HTML 含内嵌 SVG、CSS 光效、`floatGlow`/`dashMove`/`pulse`/`scanSweep` 动画、Modal/Drawer/Toast/Palette；没有独立 PNG/JPG/Icon 字体资产。 | 可直接复用配色数值、构图、交互语义、SVG 路径思想；Avalonia 中须转为控件/矢量资源。HTML 的 `localStorage` 示例状态不能作为真实 Core 集成。 |
| UI 提示词 | `D:\All projects\UI套件\11_CODEX_UI开发提示词\02_ArcheAxis_AAOS_UI开发提示词_CODEX.md` | 明确 B10 第一优先，核心闭环、双主题、证据来源、FSRS、键盘和动效降级要求。 | 设计与验收约束；其中允许 Mock fallback 与本轮用户“真实后端、不得虚构数据”冲突，按本轮指令用 unavailable/empty/error。 |
| 现有正式资产 | `apps/ArcheAxis.Desktop/Assets/` | 12 项：ICO、SVG 品牌标及 10 张 PNG；`ArcheAxis.Desktop.csproj` 仅嵌入 `aaos-app-icon.ico`。`MainWindow.axaml` 未引用这些 PNG/SVG；Home 和 Memory 使用 `AaosMemoryGraphView`。 | ICO 已用于窗口；品牌 SVG、PNG 是可复核候选，不得声称已部署。使用前须核对母版与数据语义、授权来源、深浅主题。 |
| 绿色版任务树 | `D:\All projects\ArcheAxis.Knowledge.Green-x64\.ui-task-tree\ArcheAxis-Knowledge-OS-mainline` | 存在。 | 属于并行实施树；本审计不修改。不能由其存在推断绿色版根目录已安装。 |
| 9 月 30 日材料 | `D:\All projects\Record\AAOS_UI_FRONTEND_TASKPACK_20260930.zip` | 两份 Markdown。要求静态数据配图改为可交互 SVG/Canvas，并保留真实用户图片。 | 与本轮用户“复刻母版”一致：复刻视觉形态，同时让数据图形使用真实后端状态；不得把历史材料升格为 R6/M0 Authority。 |

## 页面—现有实现—资产—交互—后端—验收矩阵

下表是追踪入口，不表示功能完成。B10 的 11 个导航项对应正式 Avalonia 页面；正式端还存在 Source Reader、Jobs 等扩展路由。代码入口主要为 `apps/ArcheAxis.Desktop/MainWindow.axaml`、`MainWindow.axaml.cs`、`Views/EvidenceCenterView.axaml`、`Views/SourceReaderView.axaml`、`Themes/AaosTheme.axaml` 和 `ThemePalette.cs`。

| B10 页面 | 当前实现入口 | 母版资产/视觉要求 | 关键交互与真实后端要求 | 当前证据与缺口 |
|---|---|---|---|---|
| Home | `HomeSurface`、`AaosMemoryGraphView` | 深空黑蓝、Teal/Ivory、四卡、Hero/记忆图、轻微轨道 | 快速 Capture、最近证据、学习队列、节点详情；数值只读 Core | 源码存在；图/趋势无 Core 投影时标记不可用；未逐组件视觉验收。 |
| Capture | `CaptureSurface`、`AaosCaptureScanSweep` | 扫描动效、类型按钮、最近列表 | 文件导入与真实回执；文本/链接写入缺口必须禁用或标明 | 源码明确文本保存 Core 未接入；动画播放未验。 |
| Evidence Library / Detail | `EvidenceCenterView` | 列表/详情、可信星、来源链 | Core anchors、筛选、详情与来源跳转 | 已有视图；母版图标几何、完整筛选及真实数据链需逐项验。 |
| Originals | `OriginalEditorSurface` | 阅读/编辑主区与引用抽屉 | 引用 ID、保存、版本历史，均需 Core 契约 | 源码有只读/未载入状态；不可把示例文本当用户原创。 |
| Human Learning | `LearningSurface` | 进度、学习卡、柔和图表 | 真实计划、学习记录与复习入口 | 页面存在；数据绑定和空态需端到端回读。 |
| Machine Learning | `MachineKnowledgeSurface` | 能力/管线状态而非静态装饰图 | 真实索引、模型/任务状态与机器生成标识 | 页面存在；静态图需按 9 月 30 日材料审计。 |
| Workspace | `WorkspaceSurface` | 树/列表、分组、选中层级 | 真实项目/来源导航 | 页面存在；未有本轮视觉/交互实测。 |
| Memory Map | `MemoryMapSurface`、`AaosMemoryGraphView` | B10 内嵌 SVG 构图、低速脉冲、节点焦点 | Core 节点/边、筛选、详情、缩放/键盘降级 | 控件存在；无投影时应明确 empty，不用示意边冒充真实关系。 |
| Search | `SearchSurface` | 结果层级、筛选和清晰空态 | Core keyword/semantic、可用筛选、来源跳转 | 页面存在；未接入的筛选需标为 unavailable。 |
| Review / FSRS | `ReviewSurface` | 卡片翻转、Again/Hard/Good/Easy | Core FSRS 队列、评分写入、下一次 due | 页面存在；翻转与 reduced motion 的实际播放未验。 |
| Settings | `SettingsSurface` | 双主题令牌、表单/状态 | 偏好持久化与离线/错误状态 | 页面存在；B10 原包只给深色基线，黑白主题需同布局完整适配。 |

## 资产部署与冲突判定

- B10 色值：`#061118` 背景、`#0C1C26`/`#102630` surface、`#1FC8C5` 主交互、`#F3EFE6` 文字、`#E6BE73` 稀少可信强调。字体栈以 Inter、Segoe UI、中文系统字体为主。须与 `AaosTheme.axaml`、`ThemePalette.cs` 按令牌逐项核验，而非只比首页。
- 当前唯一由项目文件确认打包的图像是 `Assets/aaos-app-icon.ico`。`aaos-brand-mark.svg` 和 10 张 PNG 仅是源码候选资产；所有候选保留原位，待逐图确认用途/许可和双主题后再打包。不要因“未引用”删除。
- B10 不提供可单独部署的页面配图，因此其数据图形应按内嵌 SVG 复刻为 Avalonia 矢量/Canvas，绑定真实节点、边和状态。9 月 30 日任务包要求替换静态数据配图，与本轮用户目标一致；真实用户图片、资料预览和纯装饰品牌图片应保留并单独标记来源。
- 对确实缺失的纯装饰配图，可依据 B10 构图调用图片生成，但目前未见 B10 指定可复刻的独立光栅图。本轮不为数据图、图标或状态图生成位图。图标采用现有 `AaosIcon`/Avalonia 矢量，需逐图与 B10/B01 对齐线宽、几何、大小和焦点态。
- 历史报告曾称 Home 使用 Aurora/Monochrome PNG，后续源码审计纠正其未引用；本轮源码仍显示 `HomeHeroVisual` 绑定 `AaosMemoryGraphView`。故上述 PNG 当前标记为 `CANDIDATE_UNUSED`，绝不宣称已部署。其原始作者/许可元数据未在 B10 包内出现，状态 `UNVERIFIED`。

## 下一步验收口径

逐路由保留母版截图和同尺寸原生截图，核查布局、字体、间距、色彩、图标、双主题、720/1440 DIP 及 100/125/150/200% DPI；另录制窗口缩放、鼠标/键盘、空/加载/错误/离线与 reduced motion。每个数据图形需给出实际 Core 响应或 unavailable 证据。当前阶段仅有源码与压缩包静态审计，以上均为 `NOT_EXECUTED`。
