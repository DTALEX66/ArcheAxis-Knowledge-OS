> Historical snapshot: 2026-09-27 至 2026-09-29 的过程记录，非当前状态或执行权威。
> 当前清理、交付、验证与阻塞请读 [2026-10-01 交接](STORAGE-CLEANUP-HANDOFF-20261001.md)。

## 现行解释（2026-10-01）

- B10 最终可部署母版是最高视觉依据；Aurora/黑白共用布局、状态及缩放规则。正文中此前 B03 最高或 B10 仅作风格参考的判断已被取代。
- r97/r38/r30、旧截图数、PID、HEAD、测试/构建及上传结果仅证明对应历史快照；不能推断今天界面、完整原生交互/DPI/动画或安装态已经验收。
- “49 项失败全为旧标题”是当时判断，后续发现并修复真实交互行为问题，不能沿用为全部豁免理由。
- 旧76项保留/未授权、原位展开仍在、未上传及换连接器建议都是早期阶段记录，今天以最新交接和删除回读为准；不再要求沿用旧认证建议。
- SHM PARTIAL、wheel UNVERIFIED、未知归属与历史拒绝如实保留；当前整体仍 PARTIAL，静态/编译通过不等于用户数据库或完整产品健康。

原快照源 SHA-256：`c664c5ef0569bb24fa107db05c01b432d62fe92f6c53292c18531dbcf9f7d7be`。以下保留历史正文，只统一文本格式，不将旧叙述重新认定为当前真值。

---

# AAOS UI 母版资产索引（2026-09-28）

目标工作树：`D:\All projects\ArcheAxis.Knowledge.Green-x64\.ui-task-tree\ArcheAxis-Knowledge-OS-mainline`。按用户确认的 ArcheAxis 成品母版及开发提示词：B03/B05 定产品页面结构与内容，B10 定最终视觉表现、图标、交互和动效，B04/B06/B07/B09 补组件与响应式规范；各自按职责落地，冲突不能偏离 ArcheAxis 项目母版。双主题共用同构界面，不把整页设计板嵌成产品背景。

## 当前发布回读（2026-09-28 r97）

- Green mainline 当前候选：`.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-r97/`；验收入口 `D:\All projects\ArcheAxis.Knowledge.Green-x64\AAOS-Frontend-Acceptance-v4\Start-AAOS-Frontend-Acceptance-v4.cmd`。DLL SHA-256：`C8F40B3C905A918BAFA915FCC11531419C5DC1E738EA9FC4E2B8E318B954D51E`。
- Home 主内容已优先呈现今日学习和快速捕获，统计 KPI 占位隐藏，最近证据保留 Core-backed 真实请求/空态。Reader 三栏改为宽度比例布局，Evidence 稠密表在可用宽度 <1120 DIP 时切紧凑行。
- 16 路由 × 2 主题 × 2 视口 + Home 900×900 双主题，共 66 张；另有 Reader/Evidence 各两种中等宽度，共 70 张，manifest 70 pass / 0 fail。验收目录 DLL 和代表截图 SHA 与 r97 候选一致。
- 当前 UI 仍为 `PARTIAL`：没有 B03/B05 母版逐页像素差分、实时 Core 闭环、完整交互/状态/动画/DPI/UIA/IME/无障碍证据。截图可生成不等于完整 UI 验收完成。
- B10 包只有 HTML/CSS/内联 SVG 等，不含可直接安装的独立图片/icon 包。当前导航 glyph 是源代码内原生 Path geometry，不是从图片裁切；应用 ICO 的资产来源仍 `UNKNOWN`，不得伪称来自 UI 套件。

## 资产速查：文件能不能直接放进产品

| 套件内容 | 能否原样部署 | 当前产品应落路径 | 依据 / 当前状态 |
|---|---:|---|---|
| B10 `index.html`（含 CSS、Inline SVG、图标、图表） | 否，网页包不是 Avalonia 资源 | 页面重建到 `apps/ArcheAxis.Desktop/MainWindow.axaml`、`Views/*.axaml`、`AaosIcon.axaml.cs`、`AaosBrandMark.axaml` | B10 ZIP 仅 README、HTML、BAT；已按控件绘制，但全页复刻仍 PARTIAL |
| VI Logo / 图标系统设计板 PNG | 否，整张板图不能当单个 Logo/Icon | `AaosBrandMark.axaml(.cs)`、`AaosIcon.axaml(.cs)` | 重绘件；产品中被引用 |
| B05 12 张页面 PNG | 否，整页参考图不是可部署配图 | 各页面 `Views/*.axaml` 和 `MainWindow.axaml` | 对照布局重建；不将整页图当背景 |
| B03 配色母版 PNG | 否，参考图不是主题资源 | `Themes/AaosTheme.axaml`、`ThemePalette.cs` | Aurora/Monochrome Token；母版对照仍需逐页视觉差分 |
| 独立 Logo SVG/PNG、ICO、插画包、字体文件 | 套件里没有 | 无 | ZIP 条目审计未发现；`aaos-app-icon.ico` 来源 UNKNOWN，不能标成套件资产 |
| 知识星图旧 PNG | 不建议直接部署 | 无（当前未引用） | 已确认是未部署的旧产品资产；不表示 Core 关系图。保留文件，不挂 UI |
| Evidence 空态旧 PNG | 不直接使用 | Home / Evidence 使用原生 64px 圆形边框 + Evidence 矢量图标 | 本轮替换为 B10 式原生控件；避免套件没有的插画 |

完整定位表仍在下方；`zip!/内部条目` 是压缩包路径，不是磁盘目录。

## 可部署源资产审计

已检查任务树内 `.project-local/inputs/AAOS/` 的批次镜像与提取结果。套件压缩包中**没有独立的 ArcheAxis Logo SVG/PNG、应用 ICO、图标文件包、插画文件包或字体文件**。B10 发布包包含 `README.md`、`index.html` 和 Windows 启动 BAT；标志、图形、图表片段内嵌在 HTML/CSS/SVG 中。VI、L2、L5、配色包提供的是整张设计板/页面 PNG/JPG，只作参考，不应直接裁成产品资产。

| 可用内容 | 原始套件位置（ZIP 内条目） | 任务树内已迁移镜像 | 当前产品部署/引用 | 判定 |
|---|---|---|---|---|
| B10 最终 UI、CSS、内联 SVG/图形与交互 | `D:\All projects\UI套件\10_B10_最终版高保真可部署UI\archeaxis_最终版_高保真可部署UI.zip!/index.html`；同包 `README.md` | `.project-local/inputs/AAOS/extracted/archeaxis_最终版_高保真可部署UI/index.html`、`README.md` | Avalonia XAML/C# 重建；不将网页整页塞入应用 | 提供光效、质感和交互细节；页面布局服从 B03。B10 单包只有 HTML、README、BAT，无独立图片包。 |
| VI 主标志、变体、图标与图形语言 | `D:\All projects\UI套件\01_B01_基础视觉拆图_L1\ArcheAxis_VI_12张独立图.zip!/04_04_主标志_Primary_Logo.png`、`!/05_05_标志变体_Logo_Variations.png`、`!/10_10_图标系统_Icon_System.png`、`!/09_09_图形语言_Graphic_Language.png` | `.project-local/inputs/AAOS/extracted/ArcheAxis_VI_12张独立图/` 下同名 PNG | `AaosBrandMark.axaml`、`AaosIcon.axaml(.cs)` | 参考板用原生矢量重绘；B03 页面导航 glyph 映射到主 rail，不生成位图图标。 |
| B05 12 页高保真内容 | `D:\All projects\UI套件\05_B05_高保真产品页面_L5\ArcheAxis_L5_12张高保真产品页面.zip!/01_首页_Home_1920x1080.png` 至 `!/12_设置_Settings_1920x1080.png` | `.project-local/inputs/AAOS/extracted/ArcheAxis_L5_12张高保真产品页面/` 下同名 PNG | `apps/ArcheAxis.Desktop/MainWindow.axaml`、`Views/*.axaml` | 补充 B03 内容；布局冲突服从 B03。 |
| L2 细节板（含 VI / UI、字体视觉参考） | `D:\All projects\UI套件\02_B02_深度细节_L2\ArcheAxis_L2_VI+UI_36张细节图.zip!/VI/14_14_英文字体_Display.png`、`!/VI/15_15_中文与UI字体.png`、`!/UI/...` | `.project-local/inputs/AAOS/extracted/ArcheAxis_L2_VI+UI_36张细节图/VI/` 与 `/UI/` | Avalonia 控件与 `Themes/AaosTheme.axaml` | 参考板，不是可安装字体或图标文件。Inter 由项目 `Avalonia.Fonts.Inter` 依赖提供。 |
| AAOS 颜色纠正母版 | `D:\All projects\UI套件\03_B03_页面级UI与AAOS配色纠正_L3\AAOS_配色纠正母版_v2.zip!/AAOS_UI_母版_深空黑蓝_极光青_少量星辉金_v2.png` | `.project-local/inputs/AAOS/extracted/AAOS_配色纠正母版_v2/AAOS_UI_母版_深空黑蓝_极光青_少量星辉金_v2.png` | `apps/ArcheAxis.Desktop/Themes/AaosTheme.axaml`、`ThemePalette.cs` | 两主题均由产品资源映射；参考图不作为背景贴图。 |
| B09 交互闭环参考 | `D:\All projects\UI套件\09_B09_交互式真实Demo\archeaxis_L9_交互式真实Demo.zip!/` | `.project-local/inputs/AAOS/extracted/archeaxis_L9_交互式真实Demo/` | Capture → Evidence → Original → Memory → Review 的交互/状态实现 | 交互参照；不覆盖 B10 视觉优先级。 |
| 统一开发与验收说明 | `D:\All projects\UI套件\11_CODEX_UI开发提示词\02_ArcheAxis_AAOS_UI开发提示词_CODEX.md`、`04_CODEX_UI统一验收清单.md` | `.project-local/inputs/AAOS/02_ArcheAxis_AAOS_UI开发提示词_CODEX.md`、`04_CODEX_UI统一验收清单.md` | 本任务实施与逐项验收依据 | 原文件已读；本索引与页面实施按其执行。 |

## 当前应用资产状态（实查）

| 项目路径 | 当前是否被 UI 引用 | 来源/处理结论 |
|---|---|---|
| `apps/ArcheAxis.Desktop/Assets/aaos-app-icon.ico` | `ArcheAxis.Desktop.csproj` 图标属性引用 | 本轮重绘为 B10 mark 的多分辨率 ICO；套件 ZIP 无独立 ICO，因此是依据母版生成的产品资产，不宣称源自套件。 |
| `apps/ArcheAxis.Desktop/AaosBrandMark.axaml`、`.cs` | `MainWindow.axaml` 侧栏引用 | 实际产品 Logo 是从 B10 CSS/VI 结构重绘的 Avalonia 控件。 |
| `apps/ArcheAxis.Desktop/Assets/aaos-brand-mark.svg` | **无代码引用**（仅作为 AvaloniaResource 被资源 glob 收录） | 保留为矢量母版复刻稿；实际界面使用 `AaosBrandMark.axaml(.cs)`。 |
| `apps/ArcheAxis.Desktop/AaosIcon.axaml`、`.cs` | 多个产品控件引用 | 主导航与扩展路由使用 B03/VI 语义线性 glyph，并保留 tooltip 与 AutomationProperties。 |
| `apps/ArcheAxis.Desktop/Assets/aaos-evidence-anchor-empty-state.png` | **当前无代码引用** | 仍保留在 Assets；Home 与 Evidence 空态已改用原生控件/矢量图标。本轮不删除旧文件，不把它列为套件可用资产。 |
| `apps/ArcheAxis.Desktop/Assets/aaos-knowledge-constellation-empty-state.png` | **无代码引用** | 旧产品资产，不在套件 ZIP 内；保留但不部署，不代表 Core 关系图。 |
| `Avalonia.Fonts.Inter` + `WithInterFont()` | `Program.cs` / `AaosTheme.axaml` 配置使用 | 项目依赖提供字体，不是套件迁移的字体文件。 |

## 使用规则

- ZIP 源路径用 `zip 路径!/内部条目` 表示；镜像均在任务树 `.project-local/inputs/AAOS/`，不是原 UI 套件里的扁平目录。此索引已修正此前写错的源路径。
- 直接可部署资产仅能以**ZIP 内独立文件**和实际产品代码引用为准。B10 HTML 内的 CSS/SVG、整页 UI/VI 板必须重绘为 Avalonia 控件或按项目规则生成单独资源。
- 页面布局、导航语义图标与区域构图以 B03 ArcheAxis 页面母版为准；B05 补充内容；B10 补充其覆盖的风格、交互和动效。发生冲突时不得反向覆盖用户确认的 B03 成品界面。
- 当前验收矩阵为 16 路由 × 双主题 × 1440/720 DIP，共 64 张，实际像素受 Windows 125% 缩放影响；另有 4 张路线总览。100%/150%/200% DPI、多显示器与实际点击/焦点路径尚未逐项验证。

## 2026-10-07 前端 UI 增量资产补记

本次正式入口为 Tauri 2/React 前端。三套主题品牌资源已放在 `frontend/src/assets/aaos-brand-mark-{black,white,cosmic}.svg`，均从项目现有星环结构重新绘制为冷色版本，并由 `StatusBar.tsx` 根据活动主题实际引用。逐文件 SHA-256、字节数、引用和排除原因见本轮增量清单 [`AAOS-UI-ASSET-MANIFEST-20261007.json`](AAOS-UI-ASSET-MANIFEST-20261007.json)。

继续复用 `frontend/src/components/AaosIcon.tsx` 现有 AAOS 几何，不将源设计板或整页截图裁成产品素材。`apps/ArcheAxis.Desktop/Assets/aaos-brand-mark.svg` 原件含暖金与温白，此轮未拷贝；Avalonia Home/empty-state PNG 有页面语义且旧索引记录为未引用/仅特定首页装饰，因此不作为通用三主题图，不借用其旧资产清单来声称已接入。Galaxy loader 仅以局部 CSS 适配，真实加载控件引用见 `GalaxyStates.tsx`；上游 MIT 与固定提交列于 `THIRD_PARTY_NOTICES.md`。

Vite 在当前 Windows sandbox 下因 Node `realpath()` EPERM 无法完成 bundle，故资产“由 TS 源引用”已确认，但生产 bundle 收录和画面渲染仍 UNVERIFIED。此补记不修改旧候选、Green 或既有 PNG 收据。

## 当前预览与证据

历史验收截图位于 `.project-local/acceptance/`，对应早期候选，不代表当前源码。Evidence Detail 需要真实 Core anchor；不能注入演示记录。

历史候选 r97 与 Green `AAOS-Frontend-Acceptance-v4/` 仅代表 2026-09-28 的版本，不代表当前源码。当前源码 Release 构建位于各自 `.project-local/build/dotnet/ArcheAxis.Desktop/bin/Release/net10.0/win-x64/`；Green 原生界面矩阵见 `.project-local/acceptance/AAOS-UI-VERIFY-20260929/`。Core offline 状态不等于 UI 截图验收，也不能据此声称 Core 闭环通过。

## 配图、图标、图表与动效覆盖盘点（2026-09-29；B03 母版优先，B05 补充产品内容，B10 补充风格/交互/动效）

范围：12 个正式页面、桌面共享壳、`Assets/` 下全部独立资源，以及 B10 HTML 内嵌 SVG/CSS 动效。页面 PNG 是视觉参照，不作为产品整页背景；装饰图不冒充 Core 数据。

| 页面 / 区域 | 母版视觉资产 | 当前产品实现与接线路径 | 审计结论 / 动效 |
|---|---|---|---|
| 全局品牌与导航 | B01 VI 图形语言；B10 `AA` 渐变方块标记、ArcheAxis / AAOS 品牌字与 hollow-dot 主导航 | `MainWindow.axaml` 的原生 48px 品牌标块与 `AaosBrandMarkBrush`、`AaosIcon.axaml(.cs)` 的 `NavigationDot` | B10 正式主导航 11 项统一 hollow-dot；品牌尺寸/文案与桌面 rail 280 DIP 对齐。移动端使用可操作底部导航以保证缩放可用。扩展工具路由使用有语义 glyph 的 icon-only rail，并保留 hover/automation 标签。 |
| 首页主视觉 | B03/B05 星球与轨道、标题区 | `Assets/aaos-home-hero-aurora-b03-v1.png`、`aaos-home-hero-monochrome-b03-v1.png`；`ThemePalette.GetHeroArtwork` → `MainWindow.axaml` 的 `HomeHeroPlanetImage` | 新生成 RGBA 透明主题图、同一构图适配双主题；替换原椭圆占位。环境辉光缓慢呼吸；支持 reduced-motion。图不代表真实 Memory Graph 数据。 |
| 捕获收件箱 | B05 捕获入口、文件/媒体动作图标、状态 | `AaosIcon` + `MainWindow.axaml` 的 `CapturePageGrid`、`CaptureTypeGrid` 和 `CaptureScanSweep` | 入口横排响应式折行；单列居中捕获面板与最近记录。三类可用入口采用文档/图片/音频文件过滤器，真实导入时使用扫描扫光，不使用循环 GIF。外部链接/笔记不可用时展示为不可操作状态。 |
| 证据库 | B05 稠密表格、来源/类型图标、空态 | `AaosIcon` + `Views/EvidenceCenterView.axaml` | 图标矢量；空结果用语义文案与图标。旧 `aaos-evidence-anchor-empty-state.png` 为金色/青色高拟物插画、无代码引用，保留但不部署。 |
| 证据详情 | B05 来源链关系图 | `Views/EvidenceCenterView.axaml(.cs)` 原生节点/连线 | 可读边仅来自真实 anchor；Core 未暴露字段保持空态。无需生成静态关系图，避免伪造连边。正文/面板有轻量淡入。 |
| 原创编辑器 | B05 编辑器、证据引用卡 | `MainWindow.axaml` 原生编辑布局 + `AaosIcon` | 不需要生成空白编辑器插画；Core 保存/引用接口缺失时保持空态和禁用。 |
| 人类学习 | B05 计划/队列/成长图表 | `MainWindow.axaml` + `AaosReviewScheduleChart.axaml(.cs)`、`AaosIcon` | 以数据控件绘制；Core 未提供历史值时不画伪曲线或伪进度。 |
| 机器学习 | B05 Knowledge Supply、趋势图 | `MainWindow.axaml` + 原生图表/图标 | 等待真实 Core 投影；不生成静态假图。状态变化沿用轻量淡入。 |
| 工作区 | B05 空间树、文件表 | `MainWindow.axaml` + `AaosIcon` | 树和文件类型符号为矢量；空间读模型未暴露时显示空态，不放无意义装饰图。 |
| 记忆地图 | B03/B05 星图/拓扑 | `AaosMemoryMapConstellation.axaml(.cs)`、`AaosMemoryGraphView.axaml(.cs)` | 原生绘制并按 Viewbox 缩放；真实拓扑缺失时明确标记示意。中心脉冲、虚线流动支持关闭。旧 `aaos-knowledge-constellation-empty-state.png` 为无代码引用的高拟物装饰图，保留但不部署。 |
| 搜索 | B05 搜索入口、过滤器、结果类型 | `MainWindow.axaml` + `AaosIcon` | 搜索和过滤图标为矢量，无需位图/GIF。缺失筛选字段明确显示 Core 未暴露。 |
| 复习 / FSRS | B05 记忆卡、熟悉度/排程图表 | `MainWindow.axaml` 的 `ReviewCardSurface` + `AaosReviewScheduleChart`、`AaosIcon` | 问题卡仅在 Core 返回真实 Assessment 后出现；未就绪时首屏为队列与排程图。卡片翻转采用原生动画；只绘制真实队列/排程数据。 |
| 设置 | B05 设置卡、主题入口 | `MainWindow.axaml` + `AaosIcon` | 原生矢量图标；主题切换同步更换首页插画配色，保持构图一致。 |

### B03/B05 页面母版逐页回读索引

所有下列 PNG 都是设计参照，不直接作为产品整页背景。B03 文件位于 `.project-local/inputs/AAOS/extracted/ArcheAxis_10张页面级UI_统一体系/`，B05 文件位于 `.project-local/inputs/AAOS/extracted/ArcheAxis_L5_12张高保真产品页面/`。

| 产品页 | B03 页面结构参考 | B05 页面内容参考 | 产品侧视觉资产/控件和判定 |
|---|---|---|---|
| Home | `04_04_首页结构_1920x1080.png` | `01_首页_Home_1920x1080.png` | `Assets/aaos-home-hero-{aurora-b03-v1,monochrome-b03-v1}.png` + Hero glow；原生统计与 focus 列表。Hero 响应缩放，统计仅显示真实 Core 值；统计区按 1160/900 contentWidth 自 4 列转 2 列/单列，首页焦点区 contentWidth < 900 时单列堆叠。 |
| Capture Inbox | `05_05_捕获输入_1920x1080.png` | `02_捕获收件箱_Capture_Inbox_1920x1080.png` | 原生矢量 Capture/Import glyph + `CaptureScanSweep`；仅在真实导入进行态显示扫光，不用循环 GIF。 |
| Evidence Library | `06_06_证据库_1920x1080.png` | `03_证据库_Evidence_Library_1920x1080.png` | `Views/EvidenceCenterView.axaml(.cs)` + AaosIcon；无记录显示语义空态，旧 PNG 不引用。 |
| Evidence Detail | 同 `06_06_证据库_1920x1080.png` 中详情/链路区域 | `04_证据详情_Evidence_Detail_1920x1080.png` | 原生 source-chain 节点/连线；只连接真实 anchor，不生成关系插画。 |
| Originals / Editor | `07_07_原创_1920x1080.png` | `05_原创编辑器_Originals_Editor_1920x1080.png` | 原生编辑表面、引用卡与矢量动作图标；没有真实原件时不生成封面图。 |
| Human Learning | `08_08_人机学习_1920x1080.png` | `06_人类学习_Human_Learning_1920x1080.png` | 原生学习卡/排程图控件；无 Core 历史值时不画假进度。 |
| Machine Learning | `08_08_人机学习_1920x1080.png` | `07_机器学习_Machine_Learning_1920x1080.png` | 原生状态、指标、趋势区域；无投影数据不生成装饰 AI 图或假曲线。 |
| Workspace | `09_09_工作区_1920x1080.png` | `08_工作区_Workspace_1920x1080.png` | 原生空间树、表格及类型 glyph；不展示母版示例目录/人员数据。 |
| Memory Map | `10_10_记忆搜索复习_1920x1080.png` | `09_记忆地图_Memory_Map_1920x1080.png` | `AaosMemoryMapConstellation` / `AaosMemoryGraphView`；数据空态区分 synthetic illustration 与真实拓扑。 |
| Search | `10_10_记忆搜索复习_1920x1080.png` | `10_搜索_Search_1920x1080.png` | 原生 Search/filter/result glyph 与真实结果行；不需要静态图片。 |
| Review / FSRS | `10_10_记忆搜索复习_1920x1080.png` | `11_复习_FSRS_1920x1080.png` | 原生卡片翻面与排程图；reduced-motion 时跳过翻转。 |
| Settings | `03_03_导航结构_1920x1080.png`（shell）、配色纠正母版 | `12_设置_Settings_1920x1080.png` | 原生主题和设置组 glyph；两主题仅换资源，布局结构共用。 |

上表记录资产类别、确切参考文件和产品接线。历史 r95 的 66 张 capture 只代表当时指定画面；当前回读结果见本文件 2026-09-29 矩阵更新。桌面母版逐页图像差分、其他 DPI、多屏 DPI、焦点/点击全路径仍为 `UNVERIFIED`，文档映射不等于完整交互验收。旧 rNN 结论只代表历史时点。

### B10 动效清点

| 母版动效 | Avalonia 对应实现 | 状态 |
|---|---|---|
| `floatGlow` 环境呼吸光 | 首页 `.aaos-home-ambient-glow` / DispatcherTimer | 已实现；reduced-motion 下固定静止。 |
| `dashMove` 关系虚线流动 | `AaosMemoryGraphView` 边动画 | 已实现；隐藏页面或 reduced-motion 时停止。 |
| `pulse` 知识节点脉冲 | `AaosMemoryGraphView` 中心节点 | 已实现；隐藏页面或 reduced-motion 时停止。 |
| `scanSweep` 捕获扫描 | `CaptureScanSweep` | 控件已接入；需真实导入运行时回读逐态验收。 |
| 复习卡翻转 | `ReviewCardFlipTransform` / `ReviewFlipDurationMs` | 已实现；仍需双主题与 reduced-motion 运行时验收。 |
| Hero 轨道/星球漂浮 | 双主题透明 PNG + Home ambient glow timer | 当前 PNG 轨道不独立运动；只有环境辉光低幅呼吸。母版确实要求轨道运动时需补可关闭的原生 Transform 动画，不转成 GIF。 |
| Toast / 状态出现 | `ToastSurface` + `ToastOpacityAnimation` / `ToastTransformGroup` | 已实现 220ms opacity、translateY 与 scale easing，并有反向隐藏过渡；reduced-motion 即时切换；具体视觉仍需截图对照。 |
| Hover / focus transitions | B10 CSS 120–220ms transitions | 全局 Button 的 Background/BorderBrush/Foreground 使用 220ms ease BrushTransition，reduced-motion 停止；Memory Graph 节点 hover/focus/selection 会强调相邻节点与边。完整控件截图仍需与母版逐项比对。 |
| Inspector drawer | B10
ight .28s cubic-bezier(...)` | 代码驱动 280ms cubic ease-out 滑入；reduced-motion 直接切换。 |
| Memory node hover / focus / select | `AaosMemoryGraphView` | pointer-over、keyboard focus、selection 高亮相邻示意边；主题刷新和 reduced-motion 已接线。交互与状态合同已覆盖，视觉滤镜仍需母版截图比对。 |


### 2026-09-28 B05 Human Learning / Memory Map / Search 更新

- Human Learning 运行态布局对齐 `06_人类学习_Human_Learning_1920x1080.png`：四个指标卡、左侧学习计划、右侧复习与能力增长图区域；响应式宽屏比例 `1:2`，窄屏纵向堆叠。由于 Core 当前未暴露样例截图中的掌握度、卡片数量、队列数、能力数和趋势值，指标和图表位置保留但采用明确空态，不复用母版样例数字或曲线。
- 队列、来源链、Capture 上下文、Review Card 和回执收在“队列、来源与复习详情”折叠区，避免扩展数据压低 B05 首屏主布局；既有 Core 读取、选择和提交行为仍保留在树内。
- Memory Map r44 对齐 B05 14 个无标签径向节点及中心知识节点；过滤、节点详情、Knowledge lineage 收在折叠面板中。Search r44 对齐 B05 五列结果结构，高级筛选默认折叠。
- Human Learning B05 结构合同及相邻导航回归：`40 passed, 190 deselected`；完整运行窗口仍待视觉验收。
- Human Learning 指标卡响应宽度按 rail、content padding、列数和卡片外边距计算；1280×900 当前 125% 缩放回读中四张卡以两列铺满可用宽度，无文字溢出。r48 截图与构建证据见 `AAOS-UI-FIDELITY-STATUS-20260927.md`。
- Machine Learning r50 维持母版四指标与知识供给/趋势双卡构图；真实数据未暴露时不造指标和折线，趋势区留出母版尺度的画布并居中提示。task_id 回执仍可在折叠区读取；125% 缩放下宽视口和 1280×900 紧凑视口均已原生窗口回读，详见 Fidelity Status。

**2026-09-28 r39 更新：** Memory node pointer-over/selected 已补 B10 柔光滤镜（14px blur、主题主色）与 200ms RenderTransform 过渡；reduced-motion 清除过渡。发布候选为 `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r39/`。全页面双主题及多 DPI 原生画面回读仍未完成，整体视觉验收保持 `PARTIAL`。

### 新增二进制资源与来源核验

- 套件无可直接部署的独立页面插画、图标包、品牌 Logo 源文件或 GIF；B10 图形主要内嵌在 HTML/CSS/SVG，产品端以 Avalonia 原生控件重绘。
- 两张首页插画通过 ImageGen 按 B03 轨道星球主视觉生成，并在项目内保存。Aurora 与黑白图保持相同构图，主题切换不改变页面布局。运行时不依赖用户目录的生成缓存。
- 2026-09-28 按 B03 母版重新生成两主题 hero，替换此前带写实行星/山脉、与母版不符的插画；产品文件：`apps/ArcheAxis.Desktop/Assets/aaos-home-hero-aurora-b03-v1.png`、`aaos-home-hero-monochrome-b03-v1.png`。
- 资产回读：两图均为 `1536×1024 RGBA`，Aurora alpha extrema `0..254`、bbox `(65,19)-(1522,1000)`、SHA-256 `5CA2CCC123CC768073F36292CBD30615F032C86FB8FB966A162F4A4B835D89D1`；黑白 alpha extrema `0..254`、bbox `(143,9)-(1524,1000)`、SHA-256 `7B57EC85FA308C6EC6251D9EF5AA42822F46878AE8CCC8B7D19FD95650A94CC4`.
- `aaos-app-icon.ico` 由 `ArcheAxis.Desktop.csproj` 引用；`aaos-brand-mark.svg` 是参考稿，实际运行使用 `AaosBrandMark`。两张旧空态插画没有代码引用，保留但不部署，避免未经确认的大改动。

### 2026-09-28 资产与路由 glyph 复核

- 套件没有独立的 Logo、ICO、图标包、插画包或字体文件；B05 12 张 PNG 是整页设计参考，B10 的图形以 HTML/CSS/SVG 内嵌为主。可用的单独产品位图只包括本项目已按母版生成的 Aurora/Monochrome 首页 Hero；其他数据可视化、关系图、证据链与工作区图标继续用真实数据驱动的 Avalonia 原生绘制，不能以生成图片替代。
- `aaos-home-hero-aurora.png`、`-v2.png`、`-v3.png` 多版并存；当前 `ThemePalette.GetHeroArtwork` 使用 v3。`aaos-brand-mark.svg` 和两张旧空态 PNG 无界面代码引用；保留作为未引用历史/参考资产，不纳入当前运行资产覆盖率。
- 扩展路由的 Reader、Research、Jobs、Plugins、Models 原先分别复用 Evidence、Search、Review、Connection、Memory glyph；源码已改为 Reading、Research、TaskQueue、Plugin、Chip 原生语义路径。r87 尚未构建，运行视觉待验证。
- 首页 Hero 的行星轨道仍为静态位图；如需补 B10 轨道运动，应按 reduced-motion 可关闭的原生 Transform 动效实施，不转换 GIF。B05 全页逐像素对照及 150% DPI 仍 `UNVERIFIED`。

本次把主 rail 导航占位圆点替换为 B03 语义矢量 glyph，并记录剩余动效缺口。首页主视觉此前已生成并完成双主题接线。12 页双主题、不同 DPI/窗口尺寸的原生视觉回读仍未完成，因此整体不得标记为全部验收通过。除首页 Hero 外，审计未发现应以生成位图替代真实图表、证据关系或文件内容的位置；其他视觉采用原生图表、拓扑和矢量 glyph，避免生成资产伪造数据。

### 2026-09-28 r83 全路由视觉候选

- Release 候选：`.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-r83/ArcheAxis.Desktop.exe`。
- 16 个路由（Home、Capture、Library、Search、Reader、Knowledge、Original、Memory、Human Learning、Review、Evidence、Machine Learning、Workspace、Settings、Jobs、Recovery）均以 Aurora / Monochrome 各生成一张 1440×900 DIP Avalonia `RenderTargetBitmap` 原生窗口图，共 32 张。联系表：`contact-aurora-1440x900.png`、`contact-monochrome-1440x900.png`；窄窗首页图：`home-720x900.png`、`home-900x900.png`。
- `Program.cs` 的 UI capture 入口现在把主题别名规范化为正式主题常量；截图参数中的含空格绝对路径必须在 Windows 启动参数中完整引用。该调整消除了此前“文件名不同但截图 SHA 相同”的捕获错误。
- 双主题抽查确认高亮、表面和按钮色随主题变化。Evidence 使用真实 Core anchor 列并保持空态；Machine Learning 趋势空态无伪造曲线，状态胶囊遮挡网格线；Human Learning 指标仍按真实 Core 投影显示 unavailable；Settings 主题选择可见。
- 这批图是 Avalonia 原生离屏渲染的视图证据，不等同于安装目录/DPI/真实物理显示器交互验收。全路由母版像素差异、150% DPI、触摸/键盘交互、动效播放与真正的 Core 在线数据仍需后续回读；母版验收总体继续标为 `PARTIAL`。

### 2026-09-28 r85 Search / Memory / Review 页面推进

- Search 保持 B05 五列表头比例，真实 DTO 未暴露的主题/更新时间明确 unavailable；过滤器默认收起，Core 未读搜索结果在大面积结果表内居中，不复制母版样例行。
- Memory Map 左侧主画布恢复母版的大幅居中图谱；`knowledge_id` 与读取谱系操作移至右侧图谱控制栏。`AaosMemoryMapConstellation` 的 14 个节点按母版空心无标签圆点布置，保持示意属性，不伪装为真实关系。
- Review 排程图采用 Core 实际传入柱点；无数据时展示轻量空态柱形符号与 7 日轴，缺失日不补零；支持 hover/focus 与窄列宽度。
- r85 候选 `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-r85/` 已 Release 发布。完整 16 路由双主题 1440×900 DIP 图及联系表在该目录；Memory Map 另有两主题 1920×1080 DIP 母版尺寸图和窄窗图。全量 B05 逐像素差分、150% DPI 和动画播放证据仍未完成。

### 本次实施回读

- UI 资产合同与品牌/图标合同：`8 passed`；首页新资源均进入 Avalonia `Assets/**` 且通过源码绑定。
- 六文件静态回归：`268 passed, 4 failed`。已把脉冲合同从过期的 `1500ms` 字符串断言改为与当前 3 秒周期一致。余下失败为 `test_b10_topbar_actions_follow_text_only_master_treatment`、`test_settings_and_machine_learning_match_l5_page_structure_without_fake_values`、`test_home_visible_content_stops_at_b10_master_composition`、`test_home_matches_b10_two_row_dashboard_composition`；其中两个首页断言依旧要求 B10 两行布局，与用户确认的 B03 首页页面级母版顺序不同。顶部图标测试也要求隐藏图标，与本轮“所有配图 ICON 都要复刻”的明确要求冲突。设置/机器学习结构断言仍需另行逐项对照 B05，当前不宣称通过。
- Release 桌面重建：`PASS`，0 errors、2 `NU1900` vulnerability-feed warnings（NuGet 服务索引不可达）；候选目录 `.project-local/build/aaos-ui-preview/AAOS-UI-CANDIDATE-20260927-hero-assets/`。
- 本轮 B03 图标/资产索引合同：`11 passed`（3 组定向测试），覆盖 11 项侧栏 glyph、双主题首页 PNG 绑定与 B03 Hero→stats→capture/focus 页面顺序。Release build `PASS`，0 errors、2 `NU1900` warnings；新候选 `AAOS-UI-CANDIDATE-20260927-asset-audit-r26` 已启动且窗口 `Responding=True`。
- 实际像素窗口截图回读：`NOT_EXECUTED`。当前执行进程可读到 Avalonia 窗口标题/UIA，但本地进程的屏幕抓取返回黑帧，不能以此冒充视觉验收；本次实现状态为 `IMPLEMENTED_LOCAL / BUILD_PASS / VISUAL_RUNTIME_UNVERIFIED`。


### 2026-09-27 Research / Plugins / Models 专页结构

- 三个独立入口现有独立标题 glyph、按页面语义编排的三块能力区与状态/边界区；窄内容宽度时能力卡纵向堆叠。
- Core 接口未提供真实 registry/research 投影，页面明确 unavailable，不展示虚构记录或启用按钮。
- 当前 Release r30 启动 PID 20844；单独构建成功。



### 2026-09-27 Research / Plugins / Models 专页结构

- 三个独立入口现在使用独立标题 glyph、按页面语义编排的三块能力区与状态/边界区；窄内容宽度时能力卡纵向堆叠。
- Core 接口未提供真实 registry/research 投影，页面明确 unavailable，不展示虚构记录或启用按钮。
- 当前 Release r38 启动 PID 24712；构建成功（0 warnings/0 errors），定向 UI 合同 303 passed。Core offline；全页面双主题与 DPI/窗口尺寸截图视觉验收仍 UNVERIFIED。






### 2026-09-28 r38 candidate

Preview executable: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r38/ArcheAxis.Desktop.exe`

Launcher: `Start-AAOS-UI-CANDIDATE-20260928-mother-ui-r38.cmd`

SHA-256: `E7BFF68B6892067F319A54F5F6C131FCC18DA480928F31C40EC273AA68E0B0DE`

UI contract: 303 passed. Release build: 0 warnings, 0 errors. Running PID 24712 reports Core offline. Search rows use Core title/kind/source/status. Review chart contains a responsive empty-state grid and no synthetic values. Dual-theme, all-page screenshot, window-size and DPI visual acceptance remain UNVERIFIED.

## 2026-09-28 B01 标志适配更新

- `AaosBrandMark.axaml` 现在是侧栏使用的无底板轨道星符号：三级同心轨道、倾斜横椭圆、贯穿长轴、主轴长射线星和四个端点；Aurora 用青色轨道与金色焦点，Monochrome 将焦点归一为浅灰白。
- `Assets/aaos-brand-mark.svg` 已同步为 symbol-only 可缩放矢量源，不再包含渐变方形 tile。其与实时 XAML 组件几何一致；B01 完整主标志的 ArcheAxis / Knowledge OS / 星环知识平台锁定组合仍需按应用场景另行复刻。
- `Assets/aaos-app-icon.ico` 仍是 Windows 图标容器，当前沿用带背景的应用图标轮廓；其来源仍 UNKNOWN，不能称为直接套件资产。

### 2026-09-28 Asset fidelity correction

- B01 geometry was read directly from `04_04_主标志_Primary_Logo.png` and now drives the XAML rail symbol plus `Assets/aaos-brand-mark.svg`. The current component is symbol-only; it does not yet reproduce the complete B01 wordmark lockup as a separate reusable full-logo variant.
- The r52-r54 binaries used an invalid `DesignTimeBuild=true` workaround and are superseded for preview/acceptance by the normally compiled r55 candidate. r55 runtime route/control readback is available through UI Automation; pixel screenshot comparison remains UNVERIFIED because host capture APIs returned empty pixels.
- B10 Capture `scanSweep` is now implemented as `AaosCaptureScanSweep.axaml(.cs)`: 2.4-second linear loop, primary theme color, capture-import lifecycle and reduced-motion stop/reset. This is a native vector animation, not a GIF asset.
- B03/B05 primary rail now uses the mother proportion (195 DIP on 1440 DIP reference canvas) and eleven labeled vector navigation actions; mobile keeps the responsive bottom rail. Wordmark tagline appears on desktop with the symbol.

### 2026-09-28 r64 运行态增量

- 预览路径与启动入口见上方“当前预览与证据”。r64 当前窗口 PID `5372` 可见且响应；UI Automation 的主题双向切换及返回首页证据来自 r62。
- 28 个 UI 合同文件 `330 passed`；Release publish `PASS`（NuGet vulnerability index 不可达，`NU1900` warning）。新增的 220ms BrushTransition 与 reduced-motion/focus 样式通过独立合同和 XAML 解析。系统屏幕采集被拒绝；12 页双主题/DPI 的像素回读尚未完成，视觉矩阵 `UNVERIFIED`。
- r64 原生 UI Automation 运行读回四个指标卡布局：内容宽度 1161 / 1159.4 / 841 / 839.4 DIP 分别呈 1 / 2 / 2 / 4 行；窗口已恢复到 1818×1172。此证据验证断点流式布局，不代表像素风格验收。

### 2026-09-28 r78 图像/图标回读与窄宽修正

- 当前候选在 `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-r78/`，已发布并生成 Home（Aurora Teal、黑白深色）、Workspace（Aurora Teal）、Original Editor（黑白深色）截图；双主题 Home hero 裁切/色彩及上述页面布局已目视复核。
- Workspace 移除静态演示目录，改为等待 Core 空间投影的空态矢量图标；保留母版文件列表骨架。Original Editor 引用块与 Workspace 列表下拉图标改为共享矢量组件；搜索入口快捷键显示为 `Ctrl+K`。
- Home 内容宽度不超过 900 DIP 时切换单列文案、隐藏装饰插画，统计卡同步单列，避免窄宽重叠。此改动已随候选发布。
- 本地 Release 发布 `PASS`；`NU1900` 只表示 NuGet 漏洞数据服务不可达。r78 覆盖的截图和当前 125% 桌面缩放目视通过，不代表所有页面/主题/缩放组合通过。
- 全量验收仍 `PARTIAL`：其余正式页面的配图、图标、动效和 12 页 × 双主题 × 多尺寸/DPI 的视觉差分尚未全部完成。

## 2026-09-29 原生界面矩阵更新

当前 Green mainline Release 在 125% Windows 显示缩放下完成 16 路由 × Aurora/Monochrome × 1440/720 DIP 的 64 张原生 Avalonia 截图。清单、逐图 SHA-256 和 4 张路线总览见 `.project-local/acceptance/AAOS-UI-VERIFY-20260929/`。此矩阵验证当前显示缩放下的渲染与响应布局；其他 DPI/多屏、键鼠完整路径、逐图标和逐动效母版差分仍为 `UNVERIFIED`。历史 r97 与旧截图只代表历史候选，不代表本次源码。

母版对照复核确认 Capture、Evidence、窄屏 Home、窄屏 Search 和 Learning 仍有布局或首屏差距，须完成修复后重新审视。套件没有可直接部署的独立 GIF 或完整图标包；B03/L5 页面 PNG 是含示例数据的整页参照，图标和动效需以 Avalonia 原生控件复刻，不能把示意数据当作 Core 数据。

### 2026-09-29 final matrix follow-up

上一段记录的是修复前差距；本轮已重排 Capture、Search、Evidence 与 Home 窄屏首屏，并压缩 Learning/Machine 窄屏 KPI 卡。最终 64 张新 Release 截图和 4 张联系表位于 `.project-local/acceptance/AAOS-UI-VERIFY-20260929/final/`，完整清单为 `capture-manifest.json`。Home/Capture/Search/Evidence/Learning/Machine 的当前单图已目视抽查；整体仍 `PARTIAL`，不能把这次宽度矩阵解释为所有 DPI、所有交互、动效或逐组件像素相等的验收。

Icon_System 母版语义校准更新了 Growth、Connection、Thinking 与实心 NavigationDot；其余 glyph 仍为矢量重绘。缺乏独立高分辨率 glyph 源，不能声明线宽/几何像素一比一。动效播放帧和 100%/150%/200% DPI 仍未执行；详情见 `AAOS-UI-REVIEW-20260929.md`。
