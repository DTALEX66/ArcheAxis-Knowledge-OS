# AAOS / ArcheAxis Knowledge
# 前端 UI / UX / 视觉系统交接审计提示词

你现在接手 AAOS / ArcheAxis Knowledge（星环知识平台）Windows 桌面前端 UI 项目。

本轮审计只关注：前端界面是否好看、清晰、可用、统一、具有长期桌面软件品质。

不要因为后端 Core、API、数据库、模型、插件注册表或真实数据未接入而阻塞视觉审计。所有未接入能力必须保留为诚实的空状态或不可用状态，但不要求本轮补做后端。

## 1. 项目位置

- 当前隔离工作树：`minimax-aaos-cosmic-ui-20261001`
- 当前分支：`codex/minimax-aaos-cosmic-ui-20261001`
- 正式前端技术：C# / Avalonia UI 12.1.2 / Windows Desktop
- 当前前端入口：`apps/ArcheAxis.Desktop/MainWindow.axaml`、`MainWindow.axaml.cs`、
  `Themes/AaosTheme.axaml`、`ThemePalette.cs`、`AaosBackdrop.cs`、`Views/SourceReaderView.axaml`

## 2. 当前产品视觉方向

AAOS 不是普通 AI Chat，也不是 SaaS Dashboard。目标视觉是：星空 / 宇宙 / 星环作为空间环境，
液态玻璃作为界面材质，编辑器 / 研究工具作为产品气质。整体要接近专业桌面研究工具、长期知识
工作台、高级阅读器、IDE / 文献管理软件、安静可靠有深度的个人认知系统。

避免变成：AI Dashboard、数据大屏、霓虹科技模板、大量渐变卡片、纯营销型 SaaS、
Notion / Obsidian 仿制品、"左菜单 + 右卡片墙"。

## 3. 三套主题必须保留

- **深空主题**：深蓝黑、星空、Aurora Teal、星环、低饱和青绿、星际金作为少量强调、深层空间感。
- **白色主题**：温和白、象牙白、纸张 / 研究档案、低饱和墨绿、柔和灰褐边框、适合长时间阅读。
- **黑色主题**：纯黑 / 石墨黑、极简、低对比度但必须满足可读性、更接近专业编辑器 / IDE、不要霓虹。

## 4. 当前玻璃材质标准

审计重点检查玻璃是否真的可见，而不是只在代码里声明 Acrylic。

必须具备：窗口级 Acrylic / Transparency；Shell 透明；背景星空、网格、星环可以透过玻璃层；
卡片不是纯色实心矩形；玻璃边缘存在轻微高光；有低强度阴影或空间层次；背景透出不能影响文字
可读性；不允许所有元素都强发光；不允许所有卡片都使用同样透明度；紧凑表格和高密度内容可以
适当使用更实的背景。

相关文件：`Themes/AaosTheme.axaml`、`ThemePalette.cs`、`AaosBackdrop.cs`、`MainWindow.axaml`。

关键资源：`AaosGlassBrush`、`AaosGlassRimBrush`、`AaosAcrylicMaterial`、
`AaosAmbientPrimaryBrush`、`AaosAmbientSecondaryBrush`、`AaosAmbientTertiaryBrush`、
`AaosGridBrush`、`AaosGraphGlowColor`。

玻璃审计问题（逐项回答）：

1. 背景网格是否能在主要玻璃卡片内部透出？
2. 大卡片和小卡片是否都有合适的材质层级？
3. 白色主题中玻璃是否变成普通白色卡片？
4. 黑色主题中玻璃是否变成普通黑色面板？
5. 深空主题是否过度霓虹？
6. 玻璃边缘是否像高光，而不是普通描边？
7. 透明度是否造成文本对比度不足？
8. Acrylic 不支持时，fallback 是否仍然好看？
9. Windows 原生窗口是否有真正的 Acrylic 背景？

## 5. 当前布局架构

```text
┌─────────────────────────────────────────────────────────────┐
│ Top Command Bar / Workspace Tabs / Global Search            │
├──────┬──────────────┬───────────────────────────┬───────────┤
│      │              │                           │           │
│ Rail │ Context      │ Main Workspace            │ Inspector │
│      │ Sidebar      │ Reader / Course / Review  │           │
│      │              │ Research / Knowledge      │           │
├──────┴──────────────┴───────────────────────────┴───────────┤
│ Bottom Task Drawer / Core Status / Activity Receipts        │
└─────────────────────────────────────────────────────────────┘
```

四个空间层级：

1. **Global Rail** 稳定入口：首页、捕获、证据库、原创、人类学习、机器学习、工作区、记忆、
   搜索、复习、设置 / 恢复。
2. **Context Sidebar** 按空间显示二级功能。首页：继续工作、快速捕获、最近证据、今日学习与
   复习。Reader：Outline、原始、阅读、对照、来源链。Learning：当前课程、学习目标、课程结构、
   活动、Teach-back。Review：今日复习、待审核、冲突、变更预览。Memory：知识关联、记忆地图、
   谱系。
3. **Main Workspace** 按任务切换：Today / Home、Library、Reader、Knowledge、Review、
   Learning、Course Workspace、Research、Machine Growth、Workspace、Capability Center。
4. **Inspector** 显示：当前对象、来源、版本、状态、关系、来源 Anchor、Knowledge 关联、
   课程使用情况、AI Receipt、历史版本。

## 6. 已完成的核心 UI

Shell（全局 Rail、Context Sidebar、Main Workspace、Inspector、Bottom Task Drawer、
Top Command Bar、Ctrl+K 命令入口）；Home（继续工作、最近证据、今日进度、今日学习、最近任务、
环境状态）；Reader（三栏结构、来源目录、原始 / 阅读 / 对照、Source Chain、Anchor 概念、
由此产生的 Knowledge、返回关联 Knowledge）；Review（复习队列、Review Diff、原知识、修改后、
Assessment、FSRS Again / Hard / Good / Easy、调度图表）；Learning（学习路径、今日学习、
Course Workspace、学习目标、Knowledge Components、Prerequisites、
Unit → Lesson → Activity → Assessment、Renderer Host、Teach-back）；Machine Growth
（知识供给、模型、标签、Topic Graph、Machine Receipt、Core 边界状态）；
Workspace / Research / Capability（已有只读入口；Core 未提供时使用明确的待投影状态；
不生成虚假目录、虚假插件状态或虚假模型数据）。

## 7. 当前重要截图

`aaos-deep-space-glass-final.png`、`aaos-deep-space-stars-glass.png`、
`aaos-deep-space-ui-final.png`、`aaos-reader-deep-space-shell.png`、
`aaos-window-acrylic-deep-space.png`。重点查看后三张。

## 8. 视觉审计重点

**A. 是否仍然像 Dashboard**：是否存在大量同等权重卡片？是否每个内容都被包装成卡片？首页是否像
KPI 仪表盘？是否能看出"下一步应该做什么"？Reader 是否像真正的阅读器，而不是卡片容器？
Learning 是否像学习工作台，而不是数据统计页？

**B. 是否仍有 AI 味**。需要减少：霓虹蓝 / 紫、过度发光、"AI"字样过度强调、模型名占据主视觉、
魔法棒 / 闪光 / 机器人等泛 AI 图标、大号渐变按钮、生成式产品常见的玻璃糖果风。应增强：来源、
版本、锚点、文档结构、学习目标、人的判断、Review、History、证据链、可恢复性。

**C. 是否具有宇宙方向**：宇宙风格必须来自空间结构，而不是贴图。星点应该稀疏；星环应该成为导航
与关系隐喻；轨道可以表达来源 / Knowledge / 学习路径；环境光应该低频；背景不能抢阅读内容；
不要使用过多科幻 HUD 线条；不要出现飞船、星球、爆炸等具体科幻插画干扰工作。

**D. 是否具有长期使用品质**：阅读 2 小时是否疲劳？白色主题是否适合长文？黑色主题是否有足够
对比度？深空主题是否适合专注？空状态是否说明下一步？禁用按钮是否解释原因？Inspector 是否信息
过载？Context Sidebar 是否会挤压主内容？窄窗是否仍能找到主要动作？键盘操作是否明确？

## 9. 交互动效审计

动效原则：120ms 快速反馈；180ms 标准切换；280ms 重点展开；420ms 大区域出现；
6000ms 环境光缓慢变化。

应该保留：Inspector 抽屉滑入；Context Sidebar 内容淡入；工作区页面切换；Task Drawer 展开 /
收起；星环低频呼吸；卡片边缘轻微高光变化；Graph Node 选择反馈。

不应该出现：页面整体飞入；卡片逐个弹跳；高频闪烁；无限循环渐变；过度粒子；打字机式 AI 动效；
影响阅读的环境动画。

必须检查 `AAOS_REDUCED_MOTION=1`。在 reduced motion 下：停止环境星点动画；停止星环呼吸；
禁用大部分过渡；保留必要的焦点变化和状态反馈。

## 10. 重点审计页面顺序

1. **Home / Today**：是否像"今天继续什么"，而不是 Dashboard？主要动作是否清晰？星空背景是否
   压过内容？今日进度是否过于 KPI 化？玻璃卡片是否过多？
2. **Reader**：是否真的像阅读器？目录、正文、Inspector 是否比例合理？原始 / 阅读 / 对照是否
   清晰？Source ↔ Knowledge 是否可理解？原文 Anchor 是否明显但不打扰？
3. **Knowledge**：是否能分辨我的经验、资料知识、研究结果、机器候选？是否存在正确的来源标签？
   是否有"个人经验不需要外部 Evidence"的表达？是否过度数据库化？
4. **Review**：Diff 是否比普通卡片更像成熟审核工具？原知识 / 修改后是否并排清晰？接受、修改、
   拒绝、保留候选、替代旧知识是否分层？是否能看到影响范围？
5. **Learning**：Course Workspace 是否是主工作台？是否存在真正的课程结构？Teach-back 是否像
   学习活动，而不是 Chat？Mastery 是否易懂？不同领域 Renderer 是否有扩展空间？
6. **Machine Growth**：是否避免开发者 Trace 风格？普通用户是否先看到结论？Receipt 是否应该
   默认收起？"AI 成长"是否比"机器学习"更自然？是否明确 Knowledge Truth 与 Mastery 的区别？
7. **Capability Center**：插件卡片是否按普通用户语言表达？是否明确本地 / 云端？是否明确联网和
   API Key？是否说明数据去向？是否明确不可用影响？是否避免技术类别淹没用户？

## 11. 审计禁止事项

不要接入 Rust Core；不要改变 API；不要改变数据库；不要创建虚假知识、课程、插件或模型数据；
不要因为页面没有真实数据而填入随机样例；不要把后端缺失伪装成完成状态；不要改变产品信息架构的
核心原则；不要重新设计成普通 SaaS Dashboard；不要把所有能力都变成一级菜单；不要新增与品牌
无关的插画；不要使用强烈霓虹渐变；不要把每个区域都做成卡片；不要为了玻璃效果牺牲文字可读性。

## 12. 审计输出格式

`AAOS-FRONTEND-UI-HANDOFF-AUDIT-YYYYMMDD.md`，必须包含：

1. 当前结论：是否达到可交接状态；视觉成熟度 1–5；布局成熟度 1–5；玻璃材质成熟度 1–5；
   长期使用成熟度 1–5。
2. 页面审计表：页面 / 布局 / 视觉 / 玻璃 / 交互 / 响应式 / 问题等级 / 建议。
   等级：P0 阻止使用；P1 明显影响产品质量；P2 视觉或体验缺陷；P3 可选优化。
3. 三套主题对比：每套记录主背景、内容表面、玻璃表面、玻璃边缘、主色、强调色、次要文字、
   错误 / 警告 / 成功、对比度风险、是否有 AI / 霓虹残留。
4. 布局问题：Rail 宽度、Context Sidebar 宽度、Main Workspace 可用宽度、Inspector 宽度、
   Task Drawer 高度、1280 宽度、1024 宽度、840 宽度、720 宽度、窄窗是否能完成主要任务。
5. 玻璃材质问题：玻璃是否真正透出背景？Acrylic 是否真实生效？Fallback 是否好看？边缘高光是否
   过强？透明度是否影响文字？玻璃是否到处泛滥？哪些区域应该保留实色？
6. 去 AI 化问题：列出仍然存在的 AI Dashboard 视觉、霓虹发光、生成器语言、过度模型化内容、
   过度卡片化、过度数据化，并给出具体修改建议。
7. 交接后的下一轮任务：只列前 10 项，按优先级排序。每一项必须包含任务、涉及文件、视觉目标、
   交互目标、是否只需前端、验收截图。

## 13. 交接目标

最终目标不是"功能看起来很多"，而是：用户打开 AAOS 后，感觉自己进入了一个安静、深邃、可信、
可长期工作的个人知识宇宙。

最终 UI 应同时具备：宇宙空间感、星环结构感、液态玻璃材质感、编辑器效率感、阅读器专注感、
研究工具可信度、学习系统连续性、人工判断优先、AI 作为辅助而不是主角。

审计结论必须基于实际界面截图和真实代码，不要只根据设计意图判断。
