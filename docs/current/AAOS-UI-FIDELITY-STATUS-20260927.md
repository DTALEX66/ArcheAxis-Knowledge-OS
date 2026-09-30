> Historical snapshot: 2026-09-27 至 2026-09-29 的过程记录，非当前状态或执行权威。
> 当前清理、交付、验证与阻塞请读 [2026-10-01 交接](STORAGE-CLEANUP-HANDOFF-20261001.md)。

## 现行解释（2026-10-01）

- B10 最终可部署母版是最高视觉依据；Aurora/黑白共用布局、状态及缩放规则。正文中此前 B03 最高或 B10 仅作风格参考的判断已被取代。
- r97/r38/r30、旧截图数、PID、HEAD、测试/构建及上传结果仅证明对应历史快照；不能推断今天界面、完整原生交互/DPI/动画或安装态已经验收。
- “49 项失败全为旧标题”是当时判断，后续发现并修复真实交互行为问题，不能沿用为全部豁免理由。
- 旧76项保留/未授权、原位展开仍在、未上传及换连接器建议都是早期阶段记录，今天以最新交接和删除回读为准；不再要求沿用旧认证建议。
- SHM PARTIAL、wheel UNVERIFIED、未知归属与历史拒绝如实保留；当前整体仍 PARTIAL，静态/编译通过不等于用户数据库或完整产品健康。

原快照源 SHA-256：`b88275b2b9c7355b7fdd13482f1c97e42e86b6ad9f495d21876cb8679786bcd5`。以下保留历史正文，只统一文本格式，不将旧叙述重新认定为当前真值。

---

# AAOS UI 套件复刻状态

日期：2026-09-28
目标：在 Green 目录生成可单独打开的 Avalonia 前端候选
视觉依据：B03 ArcheAxis 项目母版是最终成品界面与页面结构最高标准；B05 补页面内容；B10 补充其覆盖的视觉细节、图标、交互和动效；B04/B06/B07/B09 补充组件、响应式规范。双主题共用同构页面。

## 当前判定（2026-09-28 r97 双端源码与绿色版验收候选）

总体为 `PARTIAL`，母版逐页视觉差分、原生 UIA、DPI/IME/无障碍全矩阵和真实 Core 闭环仍未闭合。r97 使用索引 .NET SDK 10.0.400 经 Green mainline 工作树的 `scripts/runtime/dev.py` 从当前 dirty source Release 发布至 `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-r97/`；构建成功，保留 NU1900 网络审计警告；`ArcheAxis.Desktop.dll` SHA-256 为 `C8F40B3C905A918BAFA915FCC11531419C5DC1E738EA9FC4E2B8E318B954D51E`。Green 独立验收目录 `D:\All projects\ArcheAxis.Knowledge.Green-x64\AAOS-Frontend-Acceptance-v4\` 已逐文件部署并运行该候选。截图覆盖 16 路由 × Aurora/Monochrome 的 1920×1080 DIP、720×900 DIP，Home 900×900 双主题，以及 Reader/Evidence 在 1280×900、1024×768；共 70 张，manifest 70/70。首页现将今日学习、快速捕获和最近证据置于主内容，隐藏未提供真实数据的 KPI 占位；Reader 三栏依可用宽度变化，Evidence 表格在 1120 DIP 以下切换紧凑行。双端 6 个相关 XAML/C# 文件 SHA 一致。B03/B05 逐页精确差分与 B10 细节对照仍 `UNVERIFIED/PARTIAL`；预览窗口 Core offline，不证明后端联调。稳定版 `ArcheAxis.exe`、主数据库、VBS 启动入口未覆盖。

已知运行风险调查：用户截图中的 `0xe0434352` 与空地址读取错误不足以确认根因。静态检查未发现自写 P/Invoke/unsafe interop，也未发现未处理异常诊断钩子；`AaosBackdrop` 在正常模式每 40ms 重绘全屏并创建渐变画刷，是需通过正常/reduced-motion 运行对照验证的压力疑点，不是已证实根因。真实崩溃进程路径、Windows/.NET 事件/转储仍缺失。Core offline，不能证明真实后端交互闭环。

当前构建与状态以本节 r97 为准；下方旧候选号、资产名、测试数字、断点和 PID 属对应日期的历史记录，不代表当前状态。首页结构表仍存在历史母版说明；具体当前排布以 r97 首页项及当前源码为准。B03 决定页面母版/结构，B05 补充内容，B10 补其覆盖的视觉/图标/交互/动效，B04/B06/B07/B09 补组件/响应式规范。
## 页面覆盖

当前验收覆盖 16 个路由：Home、Capture、Library、Search、Reader、Knowledge、Editor、Memory、Learning、Review、Evidence、Machine、Workspace、Settings、Jobs、Recovery；其中产品页与系统工具路由按套件母版分类。

| B03 / B05 目标页面 | 当前 Avalonia 状态 | 复刻差异 / 限制 |
| --- | --- | --- |
| 首页 | B03 Hero→今日学习/快速捕获并列→最近证据；统计辅助；双主题插画 | 今日学习、快速捕获和最近证据优先；未提供真实数据的 KPI 占位隐藏，不填 B05 示例数。Evidence、Memory Graph 保留独立路由。 |
| 捕获收件箱 | 居中单列捕获页面；六类入口按可用宽度 6/3/2 列排列 | 最近项来自当前会话真实 Core 回执；未接入写入契约的入口不伪称可用。跨重启历史未暴露时显示真实空态。当前页面视觉仍需逐主题、视口截图比对。 |
| 证据库 | B05 四 KPI + 六列稠密表 | 锚点总数与来源数从 Core 返回的 anchors 真实计数；验证、主题、引用字段未暴露，明确空态。选中 anchor 切到独立详情页。 |
| 证据详情 | 独立全页布局，左右分栏呈现正文区域与来源链 | 页面结构、共享标题/说明、细线阅读纹理和来源链图已复刻；正文/引用/验证信息仍因 Core 未暴露而明确 unavailable。 |
| 原创编辑器 | 只读占位与来源引用区 | Core 当前没有 Original 保存、版本提交和冲突接口，不能复刻为可写编辑器而不引入第二写入真相。 |
| 人类学习 | B05 四指标 + 左计划/队列 + 右增长图 + 真实学习/FSRS | KPI、进度及趋势保持 Core 未暴露空态；真实学习队列、Assessment、四档 FSRS 保留。 |
| 机器学习 | B05 指标 + 五项 Knowledge Supply / 趋势双栏 | Core 缺指标/readiness/趋势历史，五项能力明确标记未暴露；单 task_id 收据仍可读。 |
| 工作区 | B05 空间树 + 文件表骨架 | 两栏布局已实现并随窄宽堆叠；真实空间/文件读模型与创建能力仍未接通，保持空态/禁用。 |
| 记忆地图 | B10 风格节点示意 + Core Knowledge lineage | 示意拓扑不冒充实时图谱；Core 仍未公开真实节点、边或关系投影。 |
| 搜索 | B05 大搜索入口 + 五列 Core 结果表 | 搜索投影真实；来源/主题/时间筛选在 Core 未暴露前禁用。 |
| 复习 / FSRS | B05 四 KPI、待复习队列与排程图；仅在 Core 返回真实 Assessment 时显示问题卡 | Core 未就绪或没有真实 Assessment 时不渲染占位问题卡。无标准答案字段故不伪造。排程/趋势统计读模型仍缺。 |
| 设置 | B05 2×4 八卡 + 双主题选择 | 八项设置依赖未暴露；除本地主题选择外均不可写、明确 disabled。 |
| Research | 独立专页卡片 | 页面不再复用通用 unavailable surface；Core 研究会话/候选真实读写契约与闭环仍未验证。 |
| Plugins | 独立专页卡片 | 页面不再复用通用 unavailable surface；插件 registry/readiness 投影与动作仍受 Core/插件契约限制。 |
| Models | 独立专页卡片 | 页面不再复用通用 unavailable surface；模型 registry/provider health 的真实投影及配置闭环仍未验证。 |

## 为什么不能直接宣称一模一样

1. B10 确定最终视觉与交互；B03 决定页面母版与 AAOS 配色；B05/L5 补充逐页内容。静态视觉与 HTML 原型不包含 Avalonia 控件树、真实数据契约或本地 Core 状态，因此需要在保留视觉层级的同时映射真实可用数据。
2. 套件的 L8 React/TypeScript 工程把多个页面路由到 `GenericAAOS`，页面中含示例数值和静态示例记录；L9 HTML 原型将交互状态保存在浏览器 `localStorage`。两者不能直接替代正式桌面数据流。
3. 当前项目 Authority 将 `apps/ArcheAxis.Desktop/` 的 C#/Avalonia 定为正式桌面端。切换到 L8 React 工程会改变正式 UI 技术栈；本轮未擅自作此架构替换。
4. 部分母版/B05 页面依赖 Core 目前未公开的读写契约。若强填示例计数、示例证据或图谱关系，界面会与真实产品状态不符。
5. 两个主题必须复用同一 ArcheAxis 母版布局并切换配色 Token；双主题下的像素一致仍需对每页、每个窗口尺寸分别截图并比对。已知旧版截图只能作为历史记录；当前 r38 未提供覆盖全页面的截图差分证据。

## 缩放适配

- 设计画布：1920×1080 logical px。
- 默认候选窗口：1440×900 logical px；最小：720×560。
- 当前桌面主 rail 为 128 DIP，11 项语义矢量 glyph 带悬停提示与可访问标签；窄屏使用移动 rail。当前几何及像素级 B03 对照未完成，视觉差分仍为 `PARTIAL`。
- 主内容：保留 1600 logical px 最大宽度；页面卡片按窗口宽度折行。
- 捕获页面保持居中单列；六类入口按可用宽度切换为 6/3/2 列，下方显示最近回执。该布局状态来自当前源码；跨窗口/DPI 的截图验收尚未闭合。
- 首页指标：宽屏 4 列、760 以下 1 列、760–1279 为 2 列；首页捕获/今日专注在 1024 以下改为纵向。
- 搜索工具、工作区和复习面板也有代码级断点。当前已知系统缩放环境下的全路由截图矩阵、150% DPI、多显示器运行时变化和窄视口视觉回读仍为 `UNVERIFIED`；Release 编译成功不等于缩放视觉验收通过。

## 当前验证

- 当前 r38：Release build `PASS`，0 warnings / 0 errors；候选运行实例 PID 24712，Core offline。该证据只支持编译成功和进程/离线状态，不证明 Core 联通或逐页视觉验收。
- 当前 r38 全路由双主题截图、窄视口及 DPI 矩阵差分：`UNVERIFIED`；没有用旧版本截图替代当前版本的视觉证据。
- 原始 Green 版：未覆盖；隔离工作树：`D:\All projects\ArcheAxis.Knowledge.Green-x64\.ui-task-tree\ArcheAxis-Knowledge-OS-mainline`。

## 候选与旧验收路径

历史 Debug 候选截图：`.project-local/acceptance/AAOS-UI-CANDIDATE-20260927-r8/AAOS-UI-CANDIDATE-20260927-r8.png`（宽屏）及 `AAOS-UI-CANDIDATE-20260927-r8-compact.png`（紧凑窗口）；启动入口：`.project-local/acceptance/AAOS-UI-CANDIDATE-20260927-r8/Start-AAOS-UI-CANDIDATE-20260927-r8.cmd`。这些属于旧 r8 证据，不是当前 r30 验收入口。当前 r30 的 Release build 和 PID/Core 状态已在“当前验证”记录；没有将旧 r8 截图冒充 r30 的 UI 验收，也没有据此声称 Green 正式版已更新。

## 执行历史日志（保留审计记录）

本节及其后带日期/候选编号的增量均为当时状态的历史记录。状态、测试数、路径、限制或结论可能已被本文件开头的 r30 校准更新；保留原文用于审计演进，不应当作当前真值。

## 2026-09-27 前端任务包审计增量

### UI 套件提示词与母版层级更正

- 已读取用户给出的 `D:\All projects\UI套件\11_CODEX_UI开发提示词\02_ArcheAxis_AAOS_UI开发提示词_CODEX.md`。其中包含 AAOS 产品定义、12 个正式页面、证据来源链/学习/工作区/记忆/搜索/复习、双主题视觉约束、响应式与验收要求；这些用于本次前端范围审计。
- 当前 authority：用户明确确认 ArcheAxis B03 页面母版是最终落地成品界面；按 B03 复刻页面布局、导航语义和区域构图。B05 补内容，B10 补它覆盖的视觉细节和动效；它们不推翻 B03 页面布局。
- 附件提议缺模块时使用 Adapter + Mock fallback；当前项目 Authority 与用户“严格按真实产品”要求不允许将示例数据或 Mock 冒充真值。因此只采纳 Adapter/明确 unavailable、empty、error states 的结构性建议，不采纳把 Mock 显示成已实现数据的做法。
- 历史错误说明：此前报告误把 B10 写成页面布局最高权威。该表述违反用户指定的 B03 母版优先规则，现已更正；旧实现/旧验收记录只作历史状态，不作为当前视觉 authority。

### 本轮完成的前端修复

- 修复复习页在 840 logical px 以下的指标栅格：原实现把“已完成”和“学习进度”放在同一格；现在四张指标卡按两列两行排列。
- 记忆地图从当前 Knowledge 详情或资料库中已选择的 Knowledge 自动带入 `knowledge_id`，并沿用现有 Core Knowledge V3/lineage 请求；单独打开页面时仍可使用输入框。没有把 lineage 标成 Memory Graph。
- 为记忆地图、捕获入口、搜索提交与复习队列入口补齐可访问名称。
- 回归证明：窄屏栅格和导航对象接线测试先失败后通过。前端/UI 合同范围 282 passed；Avalonia Debug build 为 0 warnings / 0 errors。

### 资产和产物身份

- 用户指定资产目录：`D:\All projects\UI套件`；正式前端工作树中的提取副本：`.project-local/inputs/AAOS/extracted/`。已读取 B05 的 12 张 1920×1080 图，其中首页、原创编辑器、复习页已实际查看；读取了 B10 `index.html` 和 B07 theme tokens。B05 ZIP SHA-256 为 `E61F4DA03F192695B6FA710025DF6F9B3A15E557F09316362F93DD160A7DFECB`；B10 ZIP SHA-256 为 `AE26EA0B6D0C333C0858F1AB6B906E4F1BF92E2337142BA96BC6594C00ED4B94`。指定目录下没有总包 `ArcheAxis_AAOS_UI开发资料总包_按批次.zip`，但本项目中的 AAOS 分批资产已可读取。
- 隔离验收目录已有候选：`D:\All projects\ArcheAxis.Knowledge.Green-x64\AAOS-Frontend-Acceptance-v2\`。当前候选 EXE SHA-256 为 `CD63343DEB06A5CC3739BD8407AEC4FFB52422D33BE7B0BCC7BF0EB86C258BE6`，早于本轮最新 Debug DLL SHA-256 `32386840AF09BFE746564B68631C5EB68CE16BC4567DDCCF97B4A2D95ED17808`，因此候选尚未包含本轮修复；不得用旧 EXE 声称本轮 UI 已验收。
- 2026-09-27 r7 在隔离 task tree 中重新构建并启动；截图和 launcher 在 `.project-local/acceptance/AAOS-UI-CANDIDATE-20260927-r7/`。原始 Green 程序未覆盖。逐页原生视觉、交互、2560×1440、窄窗和 DPI 回读仍为 `NOT_EXECUTED`。
- 单独运行桌面启动准备回归时，6 项因 `scripts/runtime/dev.py` 将该 worktree 的 development root 解析到 Git common-dir 所属的 `D:\All projects\ArcheAxis-Knowledge-OS\.project-local`，而测试候选在 Green 内独立 task tree，最终触发 `development executable must be inside project .project-local`。为保持用户指定的隔离边界，本轮没有把可执行文件或测试产物写回该共享根，也没有改动桌面进程生命周期代码；这使当前源码的候选启动及原生视觉验收继续受阻。

### 全页面和合同阻塞清单

| 页面/功能 | 当前真实界面与已用契约 | 前端完成度 / 所需后端依赖 |
| --- | --- | --- |
| 首页 | 首页工作流、首次使用、继续工作；`GET /api/v1/workspaces/info`、学习队列及当前会话回执 | `PARTIAL`。缺少单一可信首页投影：今日资料/笔记、活跃任务、复习统计、学习趋势、近期 Evidence 明细和 Memory Graph 汇总；必须返回来源与时间范围，缺值表示 unavailable，不可由 UI 拼造。 |
| 捕获收件箱 | 本地文件选择与 `/api/v1/imports`；呈现 Core source/job 回执 | `PARTIAL`。网页/URL/快速笔记的持久化入口缺少锁定合同；每种写入需返回持久 source identity、job/receipt、状态与可重试错误。 |
| 证据库 / 详情 | `GET /api/v1/evidence/anchors` 与资料搜索；证据选择后进入独立详情页并显示真实 source/revision/hash/locator | `PARTIAL`。缺 Evidence bundle、完整详情/原文块、锚点引用和状态变更投影；详情页结构已对齐 B05，数据仍受 Core contract 限制。 |
| 原创编辑器 | 已有单独视图、标题/正文/引用/版本区域 | `FRONTEND_IMPLEMENTED_BACKEND_BLOCKED`。当前只读；需 Original 文档读取、内容保存/自动保存、版本提交和并发冲突合同。至少需稳定 original id、body、base revision、引用来源、保存后 revision/receipt 和明确 conflict response；未定义前不开放伪保存。 |
| 人类学习 / FSRS | `/api/v1/learning/items`、Assessment、events、reviews、state | `PARTIAL`。真实队列/作答/复习流已接线；全量 Mastery projection、排程趋势/历史统计和 M0 真实首用/重启闭环尚未全部闭合。Mastery 与 Truth 必须区分。 |
| 机器学习 | 按用户提供 task id 读取 `/api/v1/machine/tasks/{taskId}` | `PARTIAL`。仅单任务回执；缺任务列表、索引/Embedding/自动标签/实体关系以及模型 readiness 投影。普通流程仍要求手输 task id。 |
| 工作区 | 尚无独立空间树/内容工作台 | `NOT_IMPLEMENTED`。`/api/v1/workspaces/info` 仅提供聚合状态，不是目录树；需要有身份、父子关系、对象类型、可读摘要、权限和空/错误状态的树/内容读模型。 |
| 记忆地图 | 本轮已支持从已选 Knowledge 自动带入；`GET /api/v1/knowledge-items/{id}/v3` 读 lineage | 页面仍为 `FRONTEND_IMPLEMENTED_BACKEND_BLOCKED`。需要 Core 返回有类型节点、边、引用对象、版本与边界/分页信息的 Memory Graph 投影；Knowledge supersedes lineage 不能代替图。 |
| 搜索 | `GET /api/v1/search?q=...`，资料类型/active 筛选、选择摘要、Enter/双击打开来源或知识 | `PARTIAL`。查询来自真实 Core；结果详情区和表格密度未对齐 B05，embedding/reranker/过滤字段与真实搜索范围仍由 Core 能力决定。 |
| 设置 / 工作区系统 | `/api/v1/system/version`、`/api/v1/workspaces/info`、两套主题 token | `PARTIAL`。主题切换已存在；设置布局、持久化偏好及完整运行时状态仍未逐项达到 B05/B06 验收。 |
| 研究 | 当前为路由级 unavailable 面 | `NOT_IMPLEMENTED`。需要研究 session/candidate 的列表、来源/版本绑定详情、创建/复核动作及已提交回执合同。 |
| 插件 / 模型 | 当前为路由级 unavailable 面；产品 UI Contract 明确凭据由 Owner 持有且 AAOS 不得读取或记录 | `NOT_IMPLEMENTED`。需要插件 registry/readiness、模型 registry/provider health 的脱敏投影；配置动作的权限、验证、错误及回读合同。不得展示凭据。 |
| 恢复 / 任务 | 任务可按已知 job id 读回；恢复只读当前边界，未执行恢复 | `PARTIAL`。任务列表/当前筛选有边界；恢复点、备份清单、可执行恢复和回滚合同均未暴露，不能伪造可恢复状态。 |

以上清单只登记前端页面缺口及其接口依赖，不改变后端任务状态或要求后端重排。建议按“母版页面、用户动作、当前接口、缺字段/能力、回执/错误/持久化、双主题/缩放验收”逐项锁定合同后再接线。

### 当前验收结论

`PARTIAL / BLOCKED_FOR_FINAL_ACCEPTANCE`。本轮修复的是两个可由前端独立完成的交互/响应式问题；12 页严格复刻、B06 18 状态全矩阵、专属 Research/Workspace/Plugin/Model 页面、多个 Core 页面合同、当前源码 Green 候选重建、原生逐页截图/键鼠与多尺寸/DPI 验收均未完成。UI 任务包不能标记全部完成。恢复方式：保留工作树改动；若只需撤回本轮，可按 `git diff` 中 `MainWindow.axaml.cs` 的响应式及 `OnMemoryMapClick` 两处、对应测试和本节记录逐项反向修改，不回滚工作树其他既有 UI 改动。


### 2026-09-27 Master Layout Follow-up (superseded)

- Historical note only: this checkpoint incorrectly treated B03 as obsolete. It recorded a 64px icon rail; later work temporarily drifted to a 280px text sidebar. Current authority is B03, and the 128 DIP semantic icon rail below restores the mother layout direction.

### 2026-09-27 Evidence Library Follow-up

- Following B03 Evidence Library, the page now uses a readable persisted-anchor list and a right-side anchor detail/bundle projection; compact layouts stack details below the list.
- Rows use fields returned by Core GET /api/v1/evidence/anchors: anchor_id, source_id, source_revision, created_at. Details retain raw_sha256 and locator/position. The DTO has no title, author, format, cover, or verification label, so the UI does not invent those values or expose unsupported type filters.
- Source changes: apps/ArcheAxis.Desktop/Views/EvidenceCenterView.axaml, apps/ArcheAxis.Desktop/Views/EvidenceCenterView.axaml.cs, apps/ArcheAxis.Desktop/MainWindow.axaml.cs; title/master assertion updated in tests/test_desktop_navigation_contract.py.
- Verification at that point: three targeted UI contract files, 235 passed and 1 pytest configuration warning; MainWindow, theme, and EvidenceCenter XAML XML parse passed; git diff --check passed. Superseded by the 2026-09-27 runtime recovery entry below.


### 2026-09-27 Original Editor Responsive Follow-up

- The Original editor keeps a broad read-only authoring surface with Evidence references and version history at the side on desktop; below the 1024 logical px tablet breakpoint, the reference/history column moves below the editor.
- Save and citation insertion remain disabled because the Core Original write/version contract is not available. No local shadow write path was added.
- At that point: 235 targeted UI contract tests passed with 1 pytest configuration warning. Build/runtime status is superseded by the 2026-09-27 runtime recovery entry below.


### 2026-09-27 Search Results Layout Follow-up

- Search results now use a compact table-like list aligned to the B05 Search page: result title, kind, source, and status. All four fields come from the existing Core-backed LibraryResultRow; unsupported topic and update-time columns are omitted.
- At that point: 235 targeted UI contract tests passed with 1 pytest configuration warning. Build/runtime status is superseded by the 2026-09-27 runtime recovery entry below.

### 2026-09-27 Runtime Recovery and Acceptance Candidate

- The user reported repeated Windows `0xe0434352` dialogs. Runtime reproduction identified three independent startup defects in the current candidate: duplicate `HomeFocusText` NameScope registration from an obsolete hidden panel; an early `SelectionChanged` handler dereferencing a named field before XAML initialization completed; and responsive Home grids with invalid row/column placements (the four-stat grid was overwritten to three columns, and lifecycle cards retained narrow-layout rows at desktop width). All three were corrected in `apps/ArcheAxis.Desktop/MainWindow.axaml` and `apps/ArcheAxis.Desktop/MainWindow.axaml.cs`.
- The acceptance launcher also explicitly set worker-profile variables to empty strings. `WorkerProfile.Load` treats an empty explicit path as an invalid configuration; the launcher now unsets these variables and invokes the available .NET host against the published DLL.
- Verification: `dotnet publish` succeeded with 0 warnings and 0 errors; actual Avalonia window remained running and `PrintWindow` captured the rendered Home at 1818x1172. The observed runtime state is Core offline because this candidate intentionally has no Core binary. Candidate screenshot: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260927/AAOS-UI-CANDIDATE-20260927.png`; launcher: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260927/Start-AAOS-UI-CANDIDATE-20260927.cmd`.
- Current verification limitations: the bundled Python interpreter has no `pytest` module and the `uv` managed-Python directory is inaccessible, so the three targeted test files were not rerun after these last changes (`NOT_EXECUTED`). The prior 235-pass result is historical, not evidence for the latest source. Full page-by-page master matching, dark/light visual captures, and multi-size/DPI runtime acceptance remain incomplete. Current status remains `PARTIAL / BLOCKED_FOR_FINAL_ACCEPTANCE`.

### 2026-09-27 B10 Icon and Illustration Follow-up

- Added a shared `AaosIcon` vector control and redrew the eight VI icon-system concepts (Knowledge, Evidence, Search, Memory, Growth, Human-AI, Connection, Thinking) with consistent 1.7px rounded strokes and theme-dynamic Aurora Teal. Extended matching line icons cover Capture, Originals, Workspace, Review, Settings and Notifications.
- Replaced the primary/compatibility navigation and mobile navigation path fragments, and added matching icons to command search, Notifications and Workspace actions. The current MainWindow has 24 uses of the shared control; no page-navigation icon remains as an inline geometry. The standalone Evidence empty-state artwork and generated Knowledge empty-state remain product illustrations; reference-page screenshots are not embedded as live data.
- Replaced the Home planet/orbit decoration with a small connected-node illustration in the B10 graph language. Its accessibility description explicitly marks it as schematic, not a real Memory Graph projection.
- Historical r7 evidence is superseded by the r8 follow-up below.

### 2026-09-27 B10 Home Composition Follow-up (historical, superseded by B03 authority)

- Rebuilt Home's main hierarchy to match B10 `renderHome()` ordering: heading/actions, four KPI cards, Recent Evidence and Today Progress, then Memory Graph with node details and Knowledge Evolution. Kept the B10 node-network illustration as native vectors. Existing Capture and workflow surfaces remain below the master composition.
- Recreated B10's graphSvg composition more closely: a central Knowledge node, six named surrounding nodes (Evidence, Originals, Learning, Memory, Workspace, Review), connecting spokes, and selectable nodes. Selection updates the detail panel but clearly reports that Core graph details are unavailable. Knowledge Evolution now uses the B10 sparkline visual language as an explicitly labelled schematic, nested under Node Details as in the master.
- Home recent evidence now reads `GET /api/v1/evidence/anchors`, displays up to four actual Core anchors, and reports explicit loading/empty/error/offline states. Workspace anchor aggregate populates the Evidence KPI. Other unavailable KPIs and graph/trend projections remain unavailable; no sample data is presented as product truth.
- Responsive layout stacks the master two-column card rows under the tablet breakpoint, retains the graph illustration at compact widths, and stacks Home actions on mobile. Native window capture read back `GetDpiForWindow=120` (125%); the requested 780px physical width was constrained by the 720 logical px minimum to 918px physical, still below the 840 logical px mobile breakpoint. Restored the ambient glow behind the graph card without hiding or moving the illustration.
- Verification: the three targeted UI contract files report `241 passed` with `--noconftest`. The repository's standard `conftest.py` path is incompatible with this nested Green task worktree: its dev launcher resolves runtime storage to the shared Git common-dir and rejects that path under the isolation boundary, so no common-dir runtime artifacts were created. Avalonia Debug build: `PASS`, 0 warnings / 0 errors. Native Home process remains responsive with Core offline.
- Screenshot and launcher: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260927-r8/`. Home top captured at 1500x980; B10 graph composition captured after scrolling; tablet at 960x760; mobile/minimum-width at 918x760. 125% native DPI was observed; 150% DPI remains `NOT_EXECUTED`. Core offline is not a connected-data acceptance result.
- Overall remains `PARTIAL / BLOCKED_FOR_FINAL_ACCEPTANCE`: other routes, two-theme route coverage, comparison to the full B10 appearance, all route-specific illustrations/icons, and 125%/150% DPI screenshot verification are still incomplete.

### 2026-09-27 统一页面标题与当前原生回读

- 所有路由内部重复的 `page-title` 已移除，页面名由 B10 共用顶栏唯一显示；页面描述、内容区、操作控件均保留。Source Reader 与 Evidence 页面同样复用该顶栏。
- UI 图标与插画状态仍为 `PARTIAL`：已有统一 14 个主题色矢量符号和 B10 首页/记忆图谱示意组件；未完成全部页面与 B05 页面级插画/图形的逐项复刻和母版差分验收。B10 压缩包本身只含 HTML、README 与启动脚本，没有可直接复用的页面图片资产；独立 VI 图标墙可作为绘制参考。
- 验证：三项 UI 合同测试 `242 passed`；Avalonia Debug build `0 warnings / 0 errors`；新进程原生窗口运行，标题为 Core offline；`GetDpiForWindow=120`。新截图位于 `.project-local/acceptance/AAOS-UI-CANDIDATE-20260927-r8/AAOS-UI-CANDIDATE-20260927-r8-title-fix.png`。
- 此项截图裁切结论已被后续 DPI-aware 原生截图证据 supersede：先前 1454×938 由 DPI-unaware 截图脚本引起虚拟化，导致窗口边缘被采集裁掉；不是应用实际客户区尺寸。
- 当前启动入口 `.project-local/acceptance/AAOS-UI-CANDIDATE-20260927-r8/Start-AAOS-UI-CANDIDATE-20260927-r8.cmd` 已指向隔离任务树当前 Debug DLL。此窗口仅用于本地视觉检查，Core 未连接；原 Green 根目录运行文件未覆盖。

### 2026-09-27 DPI-aware native viewport correction

- Runtime evidence identified the layout defect: at `RenderScaling=1.25`, `MainFrameGrid` was 1440 DIP wide, `WorkspaceScrollViewer` 1160 DIP, and the actual content inside it 1096 DIP; the old responsive rules selected four KPI columns from the outer 1440 DIP width. The UI therefore exceeded the usable page width on this layout.
- Main-window startup now clamps requested width/height to the selected screen working area divided by that screen's scaling factor, with a 32 DIP margin, and starts centered. Responsive breakpoints now use workspace content width after desktop navigation rail/inspector allocation; extracted Evidence layout receives the same width. At the current 125% display, Home KPI uses a two-column/two-row layout.
- The previous 1454×938 screenshot was produced by a DPI-unaware capture process. Re-capture set the capture thread to Per-Monitor-V2 and read back the full HWND at 1818×1172 physical pixels; all window controls and the complete Home right column are visible. Screenshot: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260927-r8/AAOS-UI-CANDIDATE-20260927-r8-title-fix.png`.
- Verification after the responsive change: `tests/test_desktop_navigation_contract.py`, `tests/test_avalonia_visual_authority.py`, and `tests/test_desktop_routes_v1.py` report `243 passed`; Debug build `0 warnings / 0 errors`; the rebuilt native candidate is responsive and Core offline. The acceptance launcher points to this worktree's current Debug DLL.
- 125% Home viewport is now visually verified. 150% DPI, a full route-by-route dual-theme/size matrix, and remaining B10/B05 per-page illustrations and icons remain incomplete; overall fidelity stays `PARTIAL`.

### 2026-09-27 B10 母版图标壳层对齐

- 历史实现依据 B10 ZIP 内 `index.html` 曾将桌面 11 个一级导航统一改为 10×10 圆点；此导航策略已因 B03 母版权威更正而被替换。顶栏命令入口与 B10 细节仍保留，逐页截图验收未完成。
- 定向验收：`test_avalonia_visual_authority.py`、`test_desktop_navigation_contract.py`、`test_desktop_routes_v1.py` 共 244 项通过。Avalonia Debug 编译成功，0 warnings / 0 errors；编译输出在 `.project-local/acceptance/AAOS-UI-CANDIDATE-20260927-r9/`，因 r8 候选正运行而使用隔离输出目录。
- 仅壳层一级图标已按 B10 复刻；12 个页面所有配图/图标、B05 截图细节、双主题逐页截图差分仍未全部完成，本次不可据此宣称整套资产验收完毕。

### 2026-09-27 B10 Memory Graph 节点图形复刻

- 依据母版 `graphSvg()` 的六节点拓扑和 `.graph-stage circle.node-dot` 状态样式，统一节点圆直径至 38 DIP（对应 380 DIP 画布上的 10% 直径），外圈改为 Surface2 填充与 Gold 描边，名称置于节点圆心；连线使用 Border 色。悬停/选择改为 Gold 3px 描边，选中态不再整圆填成主色。
- 该矢量组件同时用于首页示意和记忆地图插画；不伪装为后端实时图数据。定向验收 245 项通过，Debug 构建 0 warnings / 0 errors；产物 `.project-local/acceptance/AAOS-UI-CANDIDATE-20260927-r12/`。
- 仍待：与 B10 原生 HTML 渲染逐页截图差分、中心节点慢速 pulse 的 reduced-motion 安全实现、其余页面/空态/流程插画及双主题缩放验收。

### 2026-09-27 并行页面差异审计与本轮落地

- 两个只读审计切片完成：Home/Capture/Evidence/Original/Learning；Machine/Workspace/Memory/Search/Review/Settings。关键差距已具体化：Workspace 原先被通用 Unavailable 面板代替；Home 额外堆叠非母版工作流/快速捕获卡；图谱中心动效缺失；Aurora Sidebar Token `#081821` 与 B10 `#091821` 不一致。
- Workspace 增加 B05 所示左右分栏页面骨架（空间树、名称/类型/更新时间/成员表头、新建文档与列表视图动作位置），窄宽切为上下布局。Core 未暴露数据时保留空树与文件空态，不使用截图示例目录/文件/日期，写操作按钮明确禁用。
- Home 默认可见内容收束到 B10 的 KPI、最近证据/今日进度、Memory Graph/节点详情与趋势；原快速捕获和工作流/首次使用大卡不再附加在母版内容后，快速文件导入仍从 Capture 路由使用。
- Memory Graph 中心节点按 B10 3秒周期做低幅透明度呼吸；减弱动画环境变量 `AAOS_REDUCED_MOTION=1/true` 会停止动效，且只在 Home/Memory Map 路由启用。Aurora Sidebar Token 已改为母版精确色 `#091821`。
- 验证：`test_avalonia_visual_authority.py`、`test_desktop_navigation_contract.py`、`test_desktop_routes_v1.py` 共 `248 passed`；Debug build `0 warnings / 0 errors`；`git diff --check` 通过。候选位于 `.project-local/acceptance/AAOS-UI-CANDIDATE-20260927-r16/`。没有新增运行窗口；当前多份同标题离线实例无法无歧义归属，本轮运行时截图回读 `NOT_EXECUTED`。
- 全部 12 页 B05/B10 对照与双主题/DPI验收仍未完成；特别是 Capture/Evidence/Detail/Learning/Workspace剩余数据布局、Search/Review母版构图、机器学习与FSRS图标/插画仍是后续工作。总体保持 `PARTIAL`。

### 2026-09-27 Search / Review / Machine Learning 复刻增量（r17 source）

- Search 按 B05 Search 主卡与五列结果表重排：结果、类型、主题、来源、更新时间。Core 当前未暴露 topic/updated 字段，表格显示“Core 未暴露”；保留真实搜索/筛选与结果选择行为。
- Review 采用 B10 大卡问题面 + 展开作答/FSRS 区，队列移至卡片下方。Assessment 当前只返回 question/content，不存在标准答案字段，因此界面明确为自主回想作答，不伪造答案；保留回答正确性选择、四档 FSRS 与 Core 提交回执。
- 修复 Review 重排对应的响应式代码：移除旧 ReviewPageGrid/ReviewMetricGrid 尺寸访问，增加机器学习双栏窄屏堆叠、指标卡 WrapPanel 自适应宽度、Review FSRS 按钮窄屏两列；加载队列时保持 Review 路由。
- Machine Learning 对齐 B05 四指标行 + Knowledge Supply / 趋势双栏；无历史指标时明确显示空态，不生成示例折线。原 task_id 收据查询保留。
- 定向验证：`test_avalonia_visual_authority.py`、`test_desktop_navigation_contract.py`、`test_desktop_routes_v1.py` 共 `249 passed`，含 Avalonia XAML XML 解析、布局合约和可访问名称检查。`dotnet`/`msbuild` 当前不在执行环境中，桌面编译与原生截图均 `NOT_EXECUTED`；不能将现有 r16 build 作为 r17 实现的编译证据。整体仍为 `PARTIAL`。
- 该次审计只验证了当时 10×10 NavigationDot 与 B10 CSS/几何相符；它未验证 B03 导航复刻。品牌光效、页面插画、双主题逐页截图、150% DPI 和 crash WER/dump 栈仍未闭合。

### 2026-09-27 并行页面母版对齐与缩放修复（历史记录，当时最新）

- 按用户指示并行处理 Original/Learning、Machine/Settings、Memory/Search/Review 三个独立页面写集；主线统一处理 Capture、Evidence、窗口缩放与主题断点。所有实现仍在 Green 隔离任务树。
- Capture 已重排为 B05 左侧 2 列×3 行入口和右侧最近捕获表；表格只读当前会话收到的真实 source/job 回执，可直接打开对应来源，未暴露的网页/链接/快速笔记入口保持禁用。跨重启捕获历史未暴露，因此显示会话级空态。
- Evidence 已重排成四 KPI 和六列紧凑表；anchor/source 总量按 Core anchor 投影真实计数，验证率/主题/引用字段缺失时保留 Core 未暴露标记。详情作为表后来源链卡片，不伪造成已验证结论。
- Original、Human Learning、Machine Learning、Settings、Memory Map、Search、Review 已按各自 B05 页面构图重新布局；学习/复习、Knowledge Supply、图谱关系、设置字段缺失时明确未暴露，不填套件中的示例数值或开启无后端写入的开关。
- 修复响应式断点：主题选择器窄屏显式增加第二行；Inspector 重新读取 1440 DIP 主题资源断点；Capture 保留 B05 双列比率；Evidence 表在窄宽切换紧凑三列模板；Learning/Review/Machine/Settings 面板在窄宽堆叠。
- 双主题静态色 fallback 对齐运行时 Aurora Info/Disabled Token；搜索路由恢复 desktop rail active 状态。
- 验证：三项定向 UI 合同回归最新 `255 passed`；XAML 使用 XML/结构合同校验，`git diff --check` 通过。最新源码编译与原生视觉回读 `NOT_EXECUTED`：当前执行环境无 `dotnet`/`msbuild`，旧候选不能代替当前编译证据。
- 整体仍为 `PARTIAL`；12 页逐页原生截图、Aurora/Monochrome 双主题、窗口尺寸及 125%/150% DPI 的视觉差分没有完成。资产包中的 L5 图是整页参考图，不直接嵌入产品界面；B10 本身无可复用页面图片，图标与图谱以代码绘制重建。

### 2026-09-27 Evidence Detail 母版构图补齐

- 证据 anchor 选择后进入独立 Evidence Detail 全页视图；共享页面标题切换为“证据详情”，返回列表后还原。保留 B05 左侧阅读区与右侧来源链/引用区的层级。
- 正文未由当前 Core anchor 契约暴露，因此显示明确边界说明，并用 11 条低对比 Aurora 阅读线复刻母版的正文行纹理；不展示套件示例论文标题、作者、引用数或验证值。
- 来源链网络保留中心 Evidence 与六个节点，source、revision、hash、created_at、locator 仅取已选择的真实 anchor；Core 未暴露的引用和验证状态继续明确标记。
- 详情面板在 1024 logical px 以下切为纵向布局。新增契约先得到预期失败，接入实现后通过；三个 UI 回归文件 `255 passed`，两个 XAML XML 解析通过，`git diff --check` 通过。
- 当前命令环境的 `dotnet`/`msbuild` 不可用，最新变更的 Avalonia 编译和原生页面截图为 `NOT_EXECUTED`；该增量属于 `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC`，整体仍 `PARTIAL`。

### 2026-09-27 Original / Human Learning 母版空态补齐

- Original Editor 对齐 B10 的“原创”共享页标题、在证据支持下沉淀原创内容的副标题、顶部保存草稿/插入引用操作和 1.35:0.95 双栏；因 Core 写合同未提供，两个写操作保持禁用并说明原因。
- 原创编辑区按 B05 留出标题与正文区域，正文用 11 条低对比空态线复刻母版纹理；右侧明确无关联 Evidence，不使用 B05 截图里的示例原创标题或引用卡片。
- Human Learning 路由标题统一为“人类学习”。计划主卡保留 B05 的五条进度轨道构图，但主题和进度等待 Core 投影；真实学习队列移到辅助区，避免把空态填成伪造百分比。
- 更新旧导航合同标题断言后，`test_avalonia_visual_authority.py`、`test_desktop_navigation_contract.py`、`test_desktop_routes_v1.py` 共 `257 passed`；Original、Learning、Evidence 新增/定向断言均通过，MainWindow 与 Evidence XAML XML 解析通过。
- 最新 Avalonia 编译和运行时截图仍为 `NOT_EXECUTED`（当前 shell 无 `dotnet`/`msbuild`）；当前增量属于 `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC`，完整视觉验收继续为 `PARTIAL`。

### 2026-09-27 Memory Map B05 径向母版复刻

- 逐像素参照 L5 `09_记忆地图_Memory_Map_1920x1080.png`：记忆地图专用图形改为中心“知识”节点、14 个无标签空心节点与辐射连线；首页继续使用独立 B10 品牌图形，避免复用错误的 6 个标签节点。
- 14 个外围点仅作为页面构图纹理，提供“示意节点”无障碍名称和选择反馈，不赋予虚构的知识实体含义；Core 未提供真实 Memory Graph 的边界文案保留。
- 图形外加均匀缩放 Viewbox，宽度跟随内容区收缩；顶部原有知识谱系读取仍保持真实 Core lineage，与示意图明确区分。
- 记忆地图与 B10 品牌图形定向契约 `4 passed`。最新 Avalonia 编译及运行时图像回读仍未执行；整体保持 `PARTIAL`。

### 2026-09-27 Settings 母版主卡与双主题入口合并

- 移除独占垂直空间的主题说明卡，将 Aurora Teal / 黑白深色选择器并入设置主卡标题行；八项设置卡片仍按母版 2×4 排列，主题配对能力保留。
- 设置页副标题改为 L5 页面原文，减少非母版说明文字对首屏位置的挤占；Core 系统状态读数继续置于设置主内容之后。
- 新增 XML 结构回归：保证主题选择器与八卡网格同属设置主卡。定向测试先对旧布局失败，修改后通过；三项 UI 测试文件最新 `258 passed`，四个 XAML XML 解析通过，`git diff --check` 通过。
- Green 根下当前可检查的 `runtime` 只有 Python，两个已发布验收目录有 self-contained CLR runtime 但无 SDK/MSBuild 编译器；因此当前源码 Avalonia rebuild 与新运行时截图仍 `NOT_EXECUTED`，完整视觉验收保持 `PARTIAL`。

### 2026-09-27 Capture B05 文案与表格列复刻

- Capture 副标题和六类入口卡片说明对齐 B05 原文；功能状态继续遵守 Core 边界，可用的本地文件入口保持交互，未接入的网页/链接/笔记保持禁用。
- 最近捕获表恢复“内容 / 类型 / 时间”母版列序；真实来源打开按钮嵌入内容列，Core 未提供的导入时间明确显示 `Core 未提供`，不会把来源 ID 或任务状态伪作时间。
- Capture 定向契约 `13 passed`；随后更新过期的“来源列”布局断言，三项 UI 测试文件最新 `259 passed`。四个关联 XAML XML 解析通过，`git diff --check` 通过。

### 2026-09-27 Human Learning B05 首屏节奏收敛

- 将“载入学习路径”操作移入“学习计划”卡标题行，移除 KPI 前额外操作行；保留同一个 Core 学习读取 handler。
- 五条空进度轨道保留 B05 构图；去掉重复五次的“Core 未暴露学习主题”，只保留一处计划项/进度投影说明，缺数据时不伪造主题或百分比。
- 新增独立结构回归：验证四指标先于计划卡、载入操作在计划卡内、五条 track 保持空白。Human Learning 定向 `3 passed`。

### 2026-09-27 Workspace B05 分栏比例与 Capture 时间列

- Workspace 桌面双栏从固定 300 DIP 树栏调整为树/文件区 `0.29*:0.71*`，对应 B05 约 29% / 71% 内容比例；已有 900 DIP 紧凑断点下继续上下堆叠。
- 新增独立 workspace 结构回归，验证默认比例和紧凑堆叠行为；workspace 定向 11 项通过。
- Capture 最新表头按母版“内容 / 类型 / 时间”；来源动作留在内容列，第三列如实标出 Core 未提供的时间。完整 UI 回归待 Home/Evidence/Machine 并行写集合并后统一运行。

### 2026-09-27 并行页面母版对齐增量（Home / Evidence / Machine / Search）

- Home 按 B05 收敛为 KPI、最近证据/记忆图谱/今日关注三列和全宽学习趋势；窄屏断点改为单列或双列，不再显示额外工作流/首次使用大卡。
- Evidence 列表恢复母版紧凑工具栏、四项指标和全宽 anchor 表；空态只覆盖表格内容区，详情继续走独立详情页。
- Machine Learning 统一“机器学习”标题；趋势卡恢复 B05 图表高度与横向网格线，无历史数据时保持空图并说明 Core 等待状态。
- Search 将查询输入、过滤器/状态和五列结果表拆入母版对应区域；移除重复选中结果横幅，Inspector 仍由真实选择投影驱动。
- 同轮完成 Capture、Human Learning、Workspace 的剩余构图收敛。新增/更新页面结构合同测试，并与现有导航、主题、路由合同一并执行：8 个 UI 测试文件共 `268 passed`（1.33 秒）。四个关键 XAML 文件 XML well-formed；`git diff --check` 通过。
- 最新源码的 Avalonia 编译及原生双主题/多 DPI 截图仍 `NOT_EXECUTED`：当前可用环境没有 .NET SDK/MSBuild。既有旧候选不代表本轮源码已编译。总体状态继续为 `PARTIAL`，不能据静态结构合同宣称 12 页视觉验收完成。

### 2026-09-27 绿色版目录候选部署与真实窗口审计

- 在 `D:\All projects\OS External Configuration\10-toolchains\dotnet\dotnet.exe` 找到 .NET SDK 10.0.400。Avalonia `Release / win-x64 / SelfContained` 发布到绿色版内隔离任务树的 `.project-local/acceptance/AAOS-UI-LIVE-20260927-r10/`，可不依赖系统预装 .NET Desktop Runtime。
- 实机启动首次复现 `AaosBrandMark.axaml` 变换语法异常（Avalonia 12 不接受无单位数值 `translate(0, 10)`）；修为 `translate(0px, 10px)` 后 r10 实例正常创建 vNext 窗口。实机标题回读 `ArcheAxis Learning Workspace (vNext) — core offline (core binary not found (set ARCHAXIS_CORE_BIN))`，说明这是 UI/core 离线状态，未伪称后端联通。
- 将可运行候选整套 225 个发布文件安装到 Green 根下的 `AAOS-Frontend-Acceptance-v3/`，额外加入候选专用启动器、说明和窗口截图；发布 exe 与源产物 SHA-256 完全一致：`202299740EE48EABAD9D8D92038CAD75B5A898E5203D5B29DA09FA31C0C54B39`。原 `ArcheAxis.exe`、Green v0.6.14 launcher 与 `archeaxis.sqlite` 均保持原样；v3 明确使用候选数据目录，不接 Green 原版数据库。
- 从 Green 根内 v3 启动器实机启动成功，Accessibility/UIA 路由打开 Home、Capture、Evidence、Originals、Human Learning、Machine Learning、Workspace、Memory Map、Search、Review、Settings 11 个可见路由并保存逐页截图。当前显示器截图实测视窗 1818×1172（窗口 DPI 120）。
- 这轮启动验收截图同时发现仍需修复的视觉缺陷：Home KPI 在当前缩放下折为 2×2；Human Learning 队列标题重叠；Machine Learning / Review KPI 主值和说明挤压；Originals 右侧空 WebView 出现灰块；Capture 卡片有母版未出现的内部按钮；Evidence 未知 KPI 字号过大；Settings / Memory Map 在首屏展示多余 Core 诊断信息。已将对应独立页面/文件写集并行分派，不把这批候选报告为完整 UI 验收完成。
- 本节前一版定向 UI 测试为 `276 passed`，发生在本轮响应式和逐页显示缺陷修复前；最新 unified gate 将在并行修复合并后重跑。当前整体仍为 `PARTIAL`，正式 Green 主启动器暂未切换到 vNext 候选。

### 2026-09-27 UI candidate r13 — historical source readback

- This is a fresh self-contained win-x64 Release publish from the Green-contained isolated worktree codex/aaos-ui-mainline-20260927 at source HEAD d8f99a6357405054f1f9ee66eb2f88d36f7f5143; the published executable SHA-256 is $hash. It does not replace files in the Green root.
- Targeted UI regression: 265 passed (--noconftest; four UI contract files). Release publish succeeded using .NET SDK 10.0.400 with 0 warnings / 0 errors. One startup instance stayed responsive and reported Core offline because no Core binary was staged.
- Native PrintWindow readback of the current Release window: 1818×1172 physical px at the current 125% display. Screenshot $png (SHA-256 $pngHash). The visible Home shows B10 order and the clipped brand tagline fixed. It is an actual Avalonia render, but only Home/dark Aurora theme has been visually read back.
- Launcher: $launcher. Double-click opens the isolated preview. Preview data/backend are offline; this is not the integrated Green executable.
- DSH delivery and audit files are under docs/current/DSH-BACKEND-HANDOFF-20260927.md, DSH-BACKEND-AUDIT-INDEX-20260927.md, and DSH-BACKEND-EXECUTION-PROMPT-20260927.md; parallel reports additionally found by API gap map, asset audit, B10 page audits, workspace-settings audit, and memory-search-review audit are independent audit artifacts, not all DSH implementation output.
- Overall UI completion remains PARTIAL: all 12 routes, both themes per route, real Core connection, image/icon fidelity beyond the current shared vector subset, and the full viewport/DPI matrix are not complete. Do not treat this preview as final acceptance.

### 2026-09-27 B10 asset reuse and native graphic correction (historical)

- Added `AAOS-UI-ASSET-INDEX-20260927.md` with source-suite and task-tree mirror paths, separating deployable resources from reference boards and B10-native redraws.
- The B10 package contains HTML/CSS and no standalone icon/image pack. Existing app assets `aaos-app-icon.ico`, two empty-state PNGs, and the B10-derived SVG/vector brand mark are individually indexed. The app ICO is now redrawn from the B10 mark; both empty-state PNGs remain in Assets but have no current code references. The rendered UI uses native vector empty-state controls and the `AaosBrandMark` control.
- Memory Map radial visualization now uses the B10 six named concepts and the mother layout's placement pattern; the previous 14 anonymous ring points were replaced. Clicks remain clearly labeled as illustrative because Core has no verified graph projection yet.
- Removed seven fabricated-looking outline bars from the Review schedule chart. Empty state now uses native vector composition and states that Core schedule data will appear after an actual review; no synthetic counts are shown.
- Current verification: Debug build PASS (0 warnings, 0 errors); Memory Map contract checks PASS (3); Evidence illustration contract PASS (1). Native screenshot readback for these latest changes remains NOT_EXECUTED; the prior r16 screenshots predate them. Overall remains PARTIAL.

### 2026-09-27 r20 native preview correction and asset delivery index

- Corrected the B10 radial nodes to use legible labels beside the gold node markers; node hit targets no longer clip six concept names. DPI-aware screenshot readback confirms all six labels in the running Avalonia window.
- Learning and Evidence KPI empty values now use `—` with “暂无数据” labels rather than oversized “Core 未暴露” values. Learning KPI cards use four columns on a wide content area and two columns in narrow layouts.
- Release publish PASS to `.project-local/build/aaos-ui-preview/AAOS-UI-CANDIDATE-20260927-r20/` using .NET SDK 10.0.400. NU1900 remains because NuGet vulnerability metadata endpoint was unreachable; publish succeeded. Candidate is standalone preview with Core offline.
- Actual 1818×1172, current 125% DPI window screenshots: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260927-r20/home-aurora-125dpi.png` and `memory-map-aurora-125dpi.png`. Home and Memory Map were visually read back; this verifies these two screens only.
- `AAOS-UI-ASSET-INDEX-20260927.md` now identifies deployable reused assets, B10 redraws, exact suite and mirror paths, and current candidate locations. Overall remains PARTIAL: remaining routes/themes, full responsive matrix, Core-connected behavior, and Green-root integration need completion.


### 2026-09-27 r23 native preview evidence

- Published Release candidate `.project-local/build/aaos-ui-preview/AAOS-UI-CANDIDATE-20260927-r23/` launched successfully as PID 34856 in the Green-contained task tree. Window title truthfully reports `core offline (core binary not found (set ARCHAXIS_CORE_BIN))`; no Core facts were fabricated.
- UI Automation enumerated the formal B10 navigation routes. The r23 window was captured with `PrintWindow` after making the capture process DPI-aware; each image is 1818×1172 physical px at the current 125% display scaling.
- Fresh screenshot pairs exist for Capture, Evidence Library, Originals, Human Learning, Machine Learning, Workspace, Memory Map, Search, Review, Settings and Home under `.project-local/acceptance/AAOS-UI-CANDIDATE-20260927-r23/`. The 22 PNGs are each 1818×1172; sampled surface pixels differ between Aurora and Monochrome, confirming theme switching changes rendered resources. Evidence Detail cannot be opened without an actual persisted Core anchor; that state remains blocked by runtime data availability.
- This proves the latest candidate launches and the listed routes render in both themes at one DPI. It does not prove one-to-one pixel parity, 150% DPI, narrow viewport behavior, Core-connected rendering, or completion of every suite illustration. Overall status remains `PARTIAL`.

### 2026-09-27 B03/B05 Memory Map composition correction

- B03/B05 page authority uses an unlabeled radial constellation graph with a Knowledge center; it is distinct from the B10 Home Hero's six semantic labels. `AaosMemoryMapConstellation` now generates all 14 hollow selectable nodes (the prior code declared `MasterNodeCount = 14` but rendered only six named nodes), with radial and faint deterministic illustrative links. No link is represented as a Core relationship; Core lineage remains separately read from its existing endpoint.
- Added a source contract that failed against the previous six-node implementation and now passes. Targeted chart/graph contracts: 2 passed; Release build: 0 errors (NU1900 advisory endpoint warning). Candidate r26 published and launched Core offline. Native screenshot readback is `NOT_EXECUTED`: Windows HWND inspection from this execution session returned invalid-handle 1400 for the candidate; no screenshot is claimed.

### 2026-09-27 complete image/icon/motion audit and Home hero replacement

- Audited all twelve page compositions, shared brand/navigation graphics, all desktop `Assets/` image files, and B10 inline SVG/CSS motion. Per-route audit and file mappings are recorded in `AAOS-UI-ASSET-INDEX-20260927.md`.
- Generated two true-alpha Home planet/orbit illustrations matching the B03 motif, one Aurora Teal and one monochrome. Replaced the ellipse placeholder in `HomeWelcomeHero`, connected both resources to `ThemePalette`, and scaled the artwork/tagline to the available visual-container width.
- Existing per-page icons/charts/graphs are code-native vectors/data visualizations; AI raster art is not appropriate for evidence relationships, search results, workspace trees, or Core metrics. The two legacy empty-state PNGs were visually reviewed and remain unreferenced; they do not match the B03/B10 style closely enough to deploy.
- Home visual contract + brand/icon contracts: 8 passed. Six-file visual/navigation regression after correcting the pulse-duration assertion: 268 passed, 4 failed (three stale/incomplete layout/text contracts and one B10-vs-B03 Home composition conflict). Release rebuild: 0 errors, 2 NuGet vulnerability-feed warnings.

### 2026-09-27 B03 icon and image audit follow-up

- Corrected the earlier authority mistake: B03 is the final layout/navigation composition authority; B05 supplies page content; B10 supplies its applicable detail, visual finish and motion. The prior B10 text that promoted its round-dot navigation to a prohibition on B03 icons was incorrect.
- Main desktop rail glyphs now map Home, Capture, Evidence, Originals, Human Learning, Machine Learning, Workspace, Memory Map, Search, Review, Settings to distinct vector icons in `AaosIcon`; icon geometry inherits both theme foregrounds and scales at 20 DIP. Full B03 rail width/icon-only geometry still needs screenshot comparison.
- The 12-page audit index now links each page to its exact B03/B05 mother PNG and records the product-side control/art asset, responsive/theme behavior, Core-data truth rule, and remaining verification state.
- ImageGen artwork is used for the non-data Home planet/orbit hero only, with matching Aurora and monochrome transparent assets. Other chart/graph/source-chain/file visuals remain code-native because generated bitmap art would misrepresent changing Core data. B10 hover/focus easing, drawer slide, node hover scale/filter and orbit-only motion remain unimplemented; reduced-motion runtime coverage remains incomplete.
- Current visual status stays `PARTIAL / VISUAL_RUNTIME_UNVERIFIED`; previous framework-level image/icon audit did not close per-page DPI/theme screenshot acceptance.

### 2026-09-27 B03 compact navigation correction

- The r27 125%-DPI screenshot showed a 280-DIP text rail consuming roughly one fifth of the viewport, unlike the B03 narrow icon rail. The desktop rail is now 128 DIP, with eleven centered 22-DIP semantic glyphs, B03-style active pill sizing, compact brand mark and preserved accessible names/tooltips. Mobile navigation remains separate.
- Responsive content-width calculations already subtract `MasterSidebarWidth`, so Home and page breakpoints now gain the recovered viewport width without hard-coded per-page offsets.
- Verification in progress: rebuild the current Release candidate, inspect live window responsiveness and rerun the shell/icon contracts. Existing r27 screenshot remains historical evidence and does not show this correction.
- Candidate `.project-local/build/aaos-ui-preview/AAOS-UI-CANDIDATE-20260927-hero-assets/` starts and remains responsive under UI Automation; Core correctly reports offline. Screen capture in this execution session returned black frames, so new image pixel placement and DPI visual QA are `UNVERIFIED`. Overall fidelity remains `PARTIAL`.






### 2026-09-28 r38 Search / Evidence / Review follow-up

- Search results now show only truthful Core fields (title, kind, source, status); topic and update-time placeholder columns were removed. Unsupported source/topic/time filters remain visible but disabled.
- Evidence Library refresh/detail layout and Review schedule no-data chart were integrated. No fake schedule bars or sample evidence were added.
- Release build PASS: 0 warnings, 0 errors. Candidate: .project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r38/ArcheAxis.Desktop.exe; launcher: Start-AAOS-UI-CANDIDATE-20260928-mother-ui-r38.cmd; SHA-256 E7BFF68B6892067F319A54F5F6C131FCC18DA480928F31C40EC273AA68E0B0DE. Runtime PID 24712 responds and reports Core offline.
- git diff --check PASS. UI contract suite `303 passed`. Native screenshot/readback NOT_EXECUTED because this session cannot read the app window handle. Dual-theme and multi-size/DPI visual acceptance remains UNVERIFIED.



最新候选 r38：.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r38/ArcheAxis.Desktop.exe；启动器 Start-AAOS-UI-CANDIDATE-20260928-mother-ui-r38.cmd；PID 24712，Core offline；SHA-256 E7BFF68B6892067F319A54F5F6C131FCC18DA480928F31C40EC273AA68E0B0DE。定向 UI 合同 303 passed，Release build 0 warnings/0 errors。视觉验收仍 PARTIAL：未完成所有页面的双主题、多个尺寸和 DPI 截图回读。

### 2026-09-28 r39 B10 graph interaction follow-up

- B10 mother CSS audit confirms graph node hover/active uses 1.06 scale, 14px secondary-color glow and a 0.2s transition; the center node pulses over 3s and flow dashes move over 3.6s. No orbit rotation keyframes were found.
- `AaosTheme.axaml` now provides the node hover/selected soft glow and 0.2s transform transition. Reduced-motion removes that transition. This is a code-native runtime visual effect and follows the active theme primary resource; no generated bitmap is used for data visualization.
- Release build PASS: 0 warnings, 0 errors. Candidate: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r39/`; launcher: `Start-AAOS-UI-CANDIDATE-20260928-mother-ui-r39.cmd`; app DLL SHA-256 `CADEE5D3A751B3063040DD9FCAD69F1B0F1EEE62FD5959D9BF8E50CAB8A57B5D`. Running PID 30832 responds and reports Core offline.
- Focused shell, mother constellation, brand mark and icon contracts: 13 passed (one pytest config warning). `git diff --check` passed for the modified theme.
- This only covers the graph-node motion gap. Whole-app visual acceptance remains PARTIAL; all-page/two-theme/viewport/DPI image readback has not been completed in this turn.

### 2026-09-28 r44 B05 Memory Map / Search alignment

- B05 Memory Map now uses the mother composition: a 2:1 graph/control split at desktop widths, one filled Knowledge center, fourteen hollow unlabeled radial nodes, and no extra stars or cross-mesh. The ID/lineage input is in the graph card header; node details and lineage are secondary collapsed sections. Placeholder filter values were removed while unavailable Core fields remain explicit.
- Search now keeps advanced filters collapsed and matches the B05 five-column table (result, type, topic, source, update time). Topic and update-time cells bind the existing `Core 未暴露` projection labels rather than synthetic values. The query outline follows the active theme primary color.
- Monochrome runtime review found and fixed low contrast in the Memory Map center label; it now uses `AaosPrimaryTextBrush` in both palettes.
- Focused Search/Memory Map contracts: `14 passed` (one existing pytest config warning). Release build: `0 warnings / 0 errors`. Native `PrintWindow` readback confirms Memory Map and Search at 1818×1172 and Memory Map at 1280×900; the Aurora and Monochrome views both render, and the 1280×900 layout stacks and scrolls.
- Candidate: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r44/`; launcher: `Start-AAOS-UI-CANDIDATE-20260928-mother-ui-r44.cmd`; DLL SHA-256 `7281D98AB9CDE3D7D4587D6F56754FF29CFD556A30DB352543C558B2DAA4A211`. Running process reports Core offline.

### 2026-09-28 r45 Human Learning B05 composition

- Human Learning now follows B05's 4-metric row and `1:2` study-plan/growth-panel proportions. Because Core does not currently provide the mother screenshot's mastery/card/due/ability metrics or timestamped history, values and trend lines remain explicit empty states; no sample values are copied.
- Core queue, source chain, capture context, answer/grade controls and receipts remain in the collapsed “队列、来源与复习详情” area. The Review route remains the primary complete FSRS surface.
- Targeted Human Learning and adjacent route contracts: `43 passed, 190 deselected`, one pre-existing pytest `cache_dir` warning. Release build: `PASS`, 0 warnings / 0 errors. Native screenshot: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r45/human-learning-runtime.png`, 1818×1172 at current 125% Windows scaling; route and 4:2 card proportions visually confirmed. Candidate PID 25924 responds, Core offline. Overall status remains `PARTIAL`.
- Candidate launcher: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r45/Start-AAOS-UI-CANDIDATE-20260928-mother-ui-r45.cmd`; desktop DLL SHA-256 `881A0B8BA98EEE5A05009FC6670A7401D167913453A7A64456FD84BE352AFB60`.

### 2026-09-28 r48 responsive metric sizing correction

- Human Learning KPI card heights now contain all three text rows. Responsive item widths account for content padding and per-card margins; at 1280×900 physical resolution and current 125% scaling, all four cards render in two full-width columns without overflow.
- Screenshot: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r48/human-learning-1280x900.png`. Release build `PASS` (0 warnings / 0 errors); targeted UI contracts `43 passed, 190 deselected`, one existing pytest option warning. Candidate PID 26344 responds with Core offline.
- Launcher: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r48/Start-AAOS-UI-CANDIDATE-20260928-mother-ui-r48.cmd`; DLL SHA-256 `6C2F0731B1213DD43BA1174E8E09DE583E1F6D8B43F6989E6E7EB3B8E681F77B`. Current overall fidelity remains `PARTIAL`; all routes, themes, DPI and real Core projections are not yet verified.

### 2026-09-28 r50 Machine Learning B05 composition

- Machine Learning keeps B05's four KPI cards and Knowledge Supply / trend split; KPI widths now account for content insets and card margins, switching to one, two or four columns as the usable width changes. Main panel order stacks on compact windows.
- Matched B05 copy hierarchy by localizing the dashboard headings, expanded the trend plotting area to 420 DIP, and centered the empty trend state. Core has no machine-readiness overview or historical series, so no sample values or line are drawn.
- The live task-id receipt query remains functional inside a collapsed secondary Expander. The page-level Core limitation is a concise status sentence.
- `tests/test_machine_learning_b05_contract.py` and `tests/test_human_learning_b05_contract.py`: `6 passed`, one existing pytest option warning. Release build: `0 warnings / 0 errors`.
- Native readback: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r50/machine-learning-runtime.png` at 1818×1172 and `machine-learning-1280x900.png`; both routes captured after invoking Machine Learning through UI Automation. Current DPI is 125%. Candidate PID 40220 responds, Core offline. DLL SHA-256 `83F2F026DC4F97864A1CF1BEBA7C35D408D456E88D0C2790617E64D393F8A68A`.
- Launcher: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r50/Start-AAOS-UI-CANDIDATE-20260928-mother-ui-r50.cmd`. Visual fidelity remains `PARTIAL`; this route and two sizes do not complete the full product audit.

### 2026-09-28 r51 selected-node theme correction / dual-theme readback

- Updated the selected B10 Memory Graph node outline to `AaosGoldBrush`; Aurora keeps the warm gold accent and Monochrome resolves the same token to grayscale.
- Machine Learning page Core limitation remains concise visibly; its AutomationProperties name retains the stable `FRONTEND_IMPLEMENTED_BACKEND_BLOCKED` classification.
- Current native theme screenshots at 1818×1172: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r51/machine-learning-aurora.png` and `machine-learning-monochrome.png`. Theme changed through the live Settings selector and returned to Machine Learning. Current window PID 29992 responds in Monochrome; Core offline.
- Verification: 261 targeted desktop navigation, visual authority, Human Learning, Machine Learning, Search, and Memory Map contracts passed (one existing pytest config warning); r51 Release build has 0 warnings / 0 errors. DLL SHA-256 `1ECEF0F5F821C0A5B7E2E849F5A4B95590A4B951531C7416219F7A603E51F882`. Overall remains `PARTIAL`.
- This turn materially aligns these two pages but does not complete all-page one-to-one verification. Remaining pages, responsive/theme matrix and Core-connected screens are still open; overall status remains `PARTIAL`.

### 2026-09-28 r52 Capture Inbox B05 composition

- Replaced Capture's single-column, six-across layout with the B05 desktop split: quick capture on the left (0.8 share), recent captures on the right (1.2 share), with the six input cards in a 2×3 grid. Below 760 DIP the two panels stack; below 420 DIP the input grid becomes one column. Recent rows remain Core-session projections and the offline empty state remains truthful.
- `tests/test_avalonia_visual_authority.py` and adjacent route suites: 261 passed. `git diff --check` passed. Release publish succeeded to `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r52/`; Avalonia's user-profile telemetry target was excluded for this invocation because its fixed log path is denied. NuGet vulnerability feed was unreachable (`NU1900`). DLL SHA-256: `A61695DC57535541A3B5DF45961CFEBAC4524CB7DFE5BCD8B602451B8F436288`.
- Launcher: `Start-AAOS-UI-CANDIDATE-20260928-mother-ui-r52.cmd`. Process responds; native screenshot readback is `NOT_EXECUTED` because the newly launched process exposes no main-window handle in this execution context. r51 Capture screenshot is explicitly stale for the new layout and is not claimed as proof.
- Overall fidelity remains `PARTIAL`: Settings geometry/switch visuals, per-page theme and DPI readback, full icon/artwork audit, and real Core-connected flows remain open.

### 2026-09-28 r53 Capture / Settings composition follow-up

- Capture retains the B05 left/right composition and responsive 2×3 entrance cards from r52. The Settings Core diagnostics Expander now lives inside the master settings card and remains collapsed by default, so it no longer adds a separate visible section below the eight B05 settings cards.
- Full adjacent UI contract selection: 261 passed. Release publish succeeded to `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r53/`; the Avalonia telemetry target was excluded for this invocation because its fixed user-profile log path is denied. NuGet vulnerability feed remains unreachable (`NU1900`). DLL SHA-256: `BDE41791D723DD5FCD2232B1B6496D14FE76BC9269B3F2404A67E1AEF691F190`.
- Launcher: `Start-AAOS-UI-CANDIDATE-20260928-mother-ui-r53.cmd`. The process starts and responds, but native pixel readback remains `UNVERIFIED`: the execution context does not expose a stable visible-window capture; the r52 `PrintWindow` attempt returned a blank frame and was discarded. No stale or blank image is used as r53 proof.
- Overall fidelity remains `PARTIAL`; full per-route dual-theme, DPI and interaction readback plus remaining page-level artwork/icon discrepancies are still open.

### 2026-09-28 r54 B01 primary symbol adaptation

- Side-rail brand mark now follows the B01 symbol construction without a rounded-square tile: three concentric orbits, a tilted horizontal orbit, crossing cardinal axes, long-axis eight-ray star, and four axis satellites. Aurora uses teal with a restrained gold focus; Monochrome resolves the same focus to the neutral primary color. The standalone SVG reference was synchronized to the same symbol-only geometry. Windows `.ico` remains a separate application icon surface.
- Settings Core diagnostics remain inside the collapsed master card; Capture retains B05's split composition and responsive type grid.
- Seven focused UI test files: 265 passed. Release publish succeeded to `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r54/`; Avalonia telemetry target was excluded for this invocation because its fixed user-profile log path is denied. NuGet vulnerability feed was unavailable (`NU1900`). DLL SHA-256: `BDE41791D723DD5FCD2232B1B6496D14FE76BC9269B3F2404A67E1AEF691F190`.
- Launcher: `Start-AAOS-UI-CANDIDATE-20260928-mother-ui-r54.cmd`. Full rendered screenshot comparison is still `UNVERIFIED`; process launch and source contracts do not prove pixel-level runtime fidelity. Overall remains `PARTIAL` pending all-route dual-theme/viewport interaction evidence and remaining exact artwork/application lockups.

### 2026-09-28 r55 normal Release runtime correction / Capture UIA readback

- Corrected candidate publishing: r52-r54 had been built with `DesignTimeBuild=true` to bypass a denied Avalonia telemetry log path; those builds are not valid visual/runtime acceptance artifacts and must not be used as previews. r55 uses the normal Release pipeline and only sets the telemetry-only `UsedAvaloniaProducts` property empty for this invocation. The NuGet vulnerability index still reports `NU1900`.
- r55 starts with title `ArcheAxis Learning Workspace (vNext) — core offline (core binary not found (set ARCHAXIS_CORE_BIN))`, responds, and exposes a real Avalonia UI Automation tree. Invoking `打开捕获` loads `快速捕获`, `最近捕获回执列表`, and document/image/audio import controls. `GetDpiForWindow` reads 120 DPI (125% scaling); window rect is 1818×1172 physical px.
- Native `PrintWindow` and cropped desktop `BitBlt` both return blank/failed pixels in this host; screenshot visual comparison is `UNVERIFIED`. Runtime route/control readback does not prove pixel fidelity. r55 candidate: `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r55/`; launcher `Start-AAOS-UI-CANDIDATE-20260928-mother-ui-r55.cmd`; DLL SHA-256 `D06523129DC80A27BCE6B54917A496E7E2A52E8DCAC9FCC0EE9298FF4D279580`.
- Focused suite currently: 265 passed; `git diff --check` passed. Overall goal remains `PARTIAL`; the requested full mother UI and all-page visual acceptance are unfinished.

### 2026-09-28 r56 B10 Capture scan sweep integration

- Integrated `AaosCaptureScanSweep` into the real Capture header and import lifecycle. The scan runs on a 2.4-second linear -120%→420% loop while import is active, then stops/resets. The component hides and resets for the app's reduced-motion preference and when removed from the visual tree. Color follows `AaosPrimaryBrush`.
- r56 is normally Release-published with `-p:UsedAvaloniaProducts=` to skip only the telemetry-only AvaloniaStats target; the previous r52-r54 DesignTimeBuild candidates are not valid preview artifacts. NuGet vulnerability index warning `NU1900` remains environmental.
- UI Automation readback: process responds, title reports Core offline, and the live window has the real brand symbol; invoking Capture presents `快速捕获` and `最近捕获回执列表`. Window is visible at 120 DPI (125% scaling), 1818×1172 physical pixels. Native screenshot APIs still yield blank/failed pixels, so pixel-level visual comparison is UNVERIFIED.
- Eight focused suites: 269 passed; `git diff --check` passed. Candidate `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r56/`; launcher `Start-AAOS-UI-CANDIDATE-20260928-mother-ui-r56.cmd`; DLL SHA-256 `267DE1A3F68307FD02985AE72F9B3992549ED5E868C9D4C5B99EA64BB214CA79`.
- Overall remains `PARTIAL`; page-by-page Aurora/Monochrome, viewport, motion and visual evidence are still incomplete. This focused work is not a substitute for the planned single holistic audit after all UI pages are implemented.

### 2026-09-28 r57 B03/B05 labeled primary navigation rail

- Restored the full mother navigation rail: 195 DIP wide (13.5% of the 1440 DIP reference canvas), with icon + Chinese label for all 11 primary routes. The full brand tagline is visible on desktop; at the existing mobile breakpoint the desktop rail/tagline collapse and the bottom mobile rail remains.
- Added test-first B03 rail contracts; updated stale icon-only/128-DIP expectations. Runtime UI Automation on r57 confirms all 11 labels and `KNOWLEDGE OS · EVIDENCE · MEMORY`, with a responding visible window and truthful Core-offline title. Physical window dimensions remain 1818×1172 at 120 DPI (125% scaling).
- Candidate `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r57/`; launcher `Start-AAOS-UI-CANDIDATE-20260928-mother-ui-r57.cmd`; normal Release publish, DLL SHA-256 `86F44F4F8D91CE6553CA9B5693DF249CAB2B4956B906608ABAFDA89BDB6753`. Ten focused UI suites: 277 passed; `git diff --check` passed. NuGet vulnerability index reports `NU1900` in this offline environment.
- Window pixel capture is still unavailable (blank PrintWindow / failed cropped BitBlt), so visual pixel comparison is UNVERIFIED. The full mother UI is not done; this fixes shell width/labels only and does not replace the single holistic audit after all routes are implemented.

## 2026-09-28 r83 全路由双主题离屏视觉回读

- Current Release publish: `PASS`; candidate `.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-r83/ArcheAxis.Desktop.exe`. NuGet vulnerability source was unreachable and emitted `NU1900`; package restore reported all packages current. This warning did not fail the build.
- Candidate DLL SHA-256: `D6445865F81677C6BA56770C08C7CADA2A82469F78F82143CBB77D7E79DDCAAB`.
- Native Avalonia UI capture produced 32 route/theme images at 1440×900 DIP for all 16 routes, plus Home at 720×900 and 900×900 DIP. Contact sheets: `contact-aurora-1440x900.png`, `contact-monochrome-1440x900.png`. Screenshot CLI now passes a normalized theme explicitly. Windows argument quoting was fixed for the output path containing spaces; previous r82 Aurora/Mono evidence had identical SHA and is invalid as proof of theme switching.
- Visual readback: both contact sheets show the 16 routes in both palettes; targeted full-size captures confirm distinct Aurora teal and neutral Monochrome surfaces/actions on Machine Learning, Evidence, Human Learning, and Settings. Machine trend empty-state capsule now masks the grid line. Empty and offline states remain honest; no synthetic metrics/evidence/trend values were added.
- Responsive visual evidence: Home 720 and 900 DIP renders exist in the candidate folder. These are Avalonia `RenderTargetBitmap` snapshots at logical capture sizes, not physical-monitor DPI or installed Green runtime acceptance.
- The 1440×900 DIP route captures rasterized to 1800×1125 pixels, confirming the host Avalonia render scale was 1.25 (125%) during capture. 150% DPI remains unverified.
- Tests: `NOT_EXECUTED` this turn. Runtime integration with online Core, 150% DPI, full interaction and animation playback, and pixel-difference scoring against every B05 mother remain `UNVERIFIED`. Overall mother fidelity stays `PARTIAL`; no Green root installation, commit, push, or release was performed.

## 2026-09-28 r85 页面母版增量

- Search、Memory Map、Review 三个页面专项并行完成，写集分别位于 `MainWindow.axaml` Search/Memory 区域、`AaosMemoryMapConstellation.axaml(.cs)`、`AaosReviewScheduleChart.axaml(.cs)`；统一 Release `PASS`，NuGet vulnerability endpoint 的 `NU1900` warning 仍为环境性告警。
- Memory Map 的 `knowledge_id` 与读取按钮现位于右侧控制栏，左侧画布拥有完整母版占比；14 个空心径向点仍是示意图，非 Core 实际知识关系。Search 默认折叠未接入筛选并扩大结果空态表格；Review 图表以传入点为唯一数据源，缺失日用 em dash。
- r85 全 16 路由×Aurora/Monochrome 的 1440×900 DIP 原生视图渲染共 32 张，联系表 `contact-aurora-1440x900.png` / `contact-monochrome-1440x900.png`；另有 Memory 两主题 1920×1080 DIP 对照和 Home/Memory 720 DIP 窄窗图。截图仍是 RenderTargetBitmap，不替代物理 DPI/运行时验收。
- 本轮测试未运行（`NOT_EXECUTED`）。真实 Core 在线投影、150% DPI、全部交互/动画，以及全部 B05 母版像素差异验证仍 `UNVERIFIED`。整体仍为 `PARTIAL`。
## 2026-09-28 r64 候选增量

- 当前可见预览：`.project-local/acceptance/AAOS-UI-CANDIDATE-20260928-mother-ui-r64/`；Release publish 已通过。28 个 UI 合同文件 `330 passed`。NuGet vulnerability index 不可达，产生 `NU1900` warning。
- 延续 r63 首页统计 1160/840 DIP 断点；B10 `.nav button` 的 220ms ease 已映射到 Button Background/BorderBrush/Foreground BrushTransition，reduced-motion 会禁用。Memory Graph keyboard focus 与 hover 同样显示主题高亮。
- 原生 Avalonia UI Automation 逐断点读回四张 KPI 卡的坐标：内容宽度 1161 DIP 时 1 行；1159.4 与 841 DIP 时各 2 行；839.4 DIP 时 4 行。窗口测试后恢复为 1818×1172，PID `5372` 响应正常。
- r64 PID `5372` 可见且响应，Core offline。Windows Desktop Duplication/GDI 捕获权限拒绝，未取得截图；实际像素比对 `UNVERIFIED`。12 页×双主题×多 DPI 矩阵尚未验收。Green 正式运行目录未更新。

## 2026-09-28 r87 源码增量（未构建）

- Library 结果区由两栏改成母版尺度的全宽结果表；搜索命中时隐藏空态卡，零结果、未就绪、错误和中断时显示空态，详情投影卡置于结果表下方。避免左半宽表格和结果与空态同时展示。
- 扩展路由 Reader、Research、Jobs、Plugins、Models 改用独立语义矢量 glyph（Reading、Research、TaskQueue、Plugin、Chip）。套件资产只含整页参考板和内嵌矢量/样式，不存在可直接投放的独立 icon/illustration pack；因此原生矢量重绘，而不是把整页截图裁成产品资产。
- 以上更改尚无 Release build 或渲染证据：当前宿主 `dotnet`/SDK 不可用。r86 既有截图不代表 r87；验收状态 `IMPLEMENTED_LOCAL / NOT_EXECUTED`。Green 根目录未更新。

## Archive note — historical Green acceptance evidence

The old Green checkout acceptance tree `D:\All projects\ArcheAxis.Knowledge.Green-x64\.ui-task-tree\ArcheAxis-Knowledge-OS\.project-local\acceptance` was compacted after full SHA-256 and ZIP CRC verification. Historical r7/r8/r9/r12/r16 and LIVE-r10 paths cited in this report resolve inside `D:\All projects\Record\AAOS-project-archives\2026-09-29\green-old-checkout-acceptance.zip` under `acceptance/`; they are not active preview paths. Archive SHA-256: `18546D400BD280B64611C155EB95AEC7895E24EBD412188BF3AF63E3E82042BE`. Restore/readback instructions: [Green acceptance archive record](../history/storage-cleanup/2026-09-29/green-old-checkout-acceptance-compaction.md).
