# 可直接交给 MiniMax Design 的任务提示词：AAOS 宇宙星环正式 UI

你负责 **ArcheAxis Knowledge / 星环知识平台** 正式桌面 UI 的设计、资产及在能力允许时的代码落地。目标是好看、好用、可维护、接真实后端的产品，不交付只有静态效果的网页原型。**人类学习、机器学习、两者相互学习成长是同等重要的长期产品主体**；不得把任何一个压缩成按钮、设置项或装饰图。M0 仅是近期实施顺序，不改变三主体蓝图。**母版是逐页对照基线，不锁死你的创造力**：如果你自己的布局、元素、图标、光效动画、交互或功能组织更优，可以采用；每处变化给出母版/现状/提案三列对照、用户任务与视觉收益、无障碍和真实能力边界，不能静默删掉必要工作流。

## 当前项目与权威

仓库 `D:/All projects/ArcheAxis-Knowledge-OS`；原绿色版 `D:/All projects/ArcheAxis.Knowledge.Green-x64`；所有 UI 隔离树放在原 Green 的 `.ui-task-tree/`。先动态读取 Git status、当前/远端精确 SHA、已有分支和工作树，保护未知 dirty。读取 `AGENTS.md`、根 [`AUTHORITY.md`](../../../AUTHORITY.md)、`docs/DOCUMENTATION_AUTHORITY_INDEX.md`、`docs/CONFIGURATION_AUTHORITY_INDEX.md`、R6 `docs/authority/taskpack-0919-r6/` 的 `EXECUTOR-START.md`/`TASKS.json`/`TASKPACK.md`、`docs/current/R6-STATE.json`、`R6-EXECUTION.md` 与 `M0-DIRECTION-OVERRIDE-20260920.md`；本提示词 2026-10-01 成文时根 `AUTHORITY.md` 确实缺失，"缺失就写 `AUTHORITY_REFERENCE_MISSING`" 保留为历史口径；2026-10-08 复核根 `AUTHORITY.md` 已存在并是导航入口，当前执行者直接读它，按 §5 权威顺序解析，不要从旧包重建权威。再读 `docs/current/AAOS-EXECUTION-PACKET-20261001.md`、`AAOS-UNFINISHED-TASKS-20261001.md`、`AAOS-ALL-TASKS-DISPOSITION-20261001.csv` 的 **`UI_FRONTEND` 52 行**；按 key 查 `AAOS-ALL-TASKS-LEDGER-20261001.json` 原要求。还要读 `AAOS-UI-COVERAGE-MATRIX-20261001.md`、`AAOS-UI-MASTER-ASSET-AUDIT-20261001.md`、`AAOS-UI-ASSET-MANIFEST-20261001.json`、`AAOS-NAVIGATION-STRUCTURE-REVIEW-20261001.md`、`AAOS-UI-NAVIGATION-IA-20261001.md`、`AAOS-UI-BACKEND-MAP-20261001.md`、`AAOS-ERRORS-BLOCKERS-20261001.md` 和 `AAOS-MINIMAX-DESIGN-CAPABILITY-AUDIT-20261001.md`。历史任务包副本在 `docs/history/external-taskpacks/2026-10-01/`；它们不是当前 Authority。

用户的 **12 张产品母版**位于 `D:/All projects/UI套件/01_01_产品信息架构_Information_Architecture.png` 至 `12_12_搜索与复习_Search_Review_FSRS.png`；同目录 **11 张品牌视觉**从 `01_01_品牌主视觉_Brand_Hero.png` 至 `11_11_品牌应用_Applications_Left.png`。必须读 `D:/All projects/UI套件/11_CODEX_UI开发提示词/02_ArcheAxis_AAOS_UI开发提示词_CODEX.md`。B10 只是旧交互参考；没有 AAOS Figma 文件，不因此停工。产品身份是宇宙、星环、星球与知识轨道，品牌色深空蓝 `#081020`、石墨黑 `#1A2233`、Aurora Teal `#2EC4B6`、星际金 `#F4D08B`、Ivory `#F8F6EB`；逐页还要核字体、标志、安全空间、图标笔触和对比度，不仅照搬色值。

## 复制 UI 分支并继续设计

先读 `docs/current/AAOS-GREEN-REPOSITORY-BOUNDARY-AUDIT-20261001.md`：原 Green 目前混有运行包、一套独立 Git 克隆和多棵源码工作树；源码树不是安装态。若后续已裁定新的隔离开发位置，以当前项目规则和该裁定更新工作树路径、资产引用、交接索引及启动脚本；在裁定前遵循现有 `.ui-task-tree` 指令且不删除/迁移旧树。最终部署只能是经同一 SHA 验证的运行包。

**责任边界**：你只负责正式桌面界面的信息架构、视觉、资产、动效、交互、前端状态与真实后端合同的客户端接入。不得自行改写 Rust Core、数据库 schema 或后端领域逻辑；发现缺口给 DSH 版本化接口需求。历史前端开源池和 9/30 UI01–UI14 先按任务 key 核源码、版本、许可证、维护状况、Avalonia 可复用性与替代成本，可用者吸收进前端方案并保留来源/引用路径，不把候选清单当已安装。

先从远端 `codex/aaos-ui-phase2-20261001` 回读精确 SHA，再**复制为独立设计分支**，建议 `codex/minimax-aaos-cosmic-ui-20261001`（已存在则用唯一后缀），在原 Green `.ui-task-tree/` 下建立隔离工作树。保留旧 route/API/对象身份，不覆盖原 UI 分支和正式根未知修改；同一文件只允许一个 writer。MiniMax Design 若没有 Git 或 C#/Avalonia 文件编辑能力，先验证真实可用工具：设计工作继续，在独立本地资产目录输出源文件、导出图和交接清单，由具 Git 能力的执行者按同一精确基线建枝/接入；不要声称分支或代码已创建。使用 MiniMax Design **当前自己的模型、provider、认证与模型选择机制**，不硬编码模型名、不改全局设置；付费调用先核权限和费用，不上传私人数据库、凭据、会话或用户工作区。

## 先审架构，再做页面

完整覆盖首页、捕获、证据库、原创、人类学习、机器学习、工作区、记忆、搜索、复习/FSRS，另有系统设置/恢复与可发现的只读未来蓝图。按 `AAOS-NAVIGATION-STRUCTURE-REVIEW-20261001.md` 重新设计：一级工作流清楚可辨；二级是当前工作流的对象/任务；三级是真实 source/knowledge/job/learning item/task 等对象 ID、版本和动作。当前代码的 10 个一级标签全隐藏、二级首页/工作区/记忆缺项、复习二级归属错误、三级只是文字说明；你可以提出更优的整体方案，但需解决这些问题，并保持旧命令、快捷键和深链接兼容。Agent、MCP、模型与插件治理不混入日常一级菜单；长期 3D/VR/AR、仿真、协作等在蓝图中清楚标 `待开发`。

审查**整窗布局架构**，并先读 `docs/current/AAOS-LAYOUT-ARCHITECTURE-REVIEW-20261001.md`：品牌/全局导航、顶栏搜索与状态、主内容、上下文侧栏、Inspector/活动抽屉、空/错/离线面板之间的区域关系；针对宽窗、中窗、720 窄窗以及 100/125/150/200% DPI 分别说明哪些区域常显、折叠、转抽屉或主内容内嵌。首页需有星球 Hero、真实概览、快速捕获、今日专注/最近证据，以及独立的人类学习、机器学习、双向成长区域；Capture 的多格式输入与近期来源、Evidence 的筛选/来源详情、Originals 编辑、人类学习工作台、机器学习工作台、双向纠错与复测流转、Workspace 文件树、Memory 图谱、Search/Review 均需逐页分区。不能因窄屏或新视觉方案把功能静默藏掉；数据图由真实 Core 驱动，装饰星图不得冒充知识图谱。

## 视觉、资产和动效

两套基础主题均完整适配：深空黑蓝 Aurora 与 Ivory/明亮主题，并统一 Aurora Teal/星际金及黑白配套令牌；覆盖所有页面和空、加载、错误、离线、权限、冲突状态。优先部署现有可合法使用的资产，逐项维护原路径、部署路径、引用点、SHA、版本、许可证、浅/深色变体。缺图时参照母版重制星球、星环、山脊、星尘与情绪插画；图标用可维护 SVG/Avalonia Path，不用整页位图代替控件。动效按场景用低频光晕、轨道、状态转场、适量视频或矢量动画，验证 reduced motion、失焦暂停、低性能回退和文字可读性；不能用持续视频替代数据或交互。

先现场核 MiniMax Design 的 Agent Mode、Canvas Flow、资产中心、Image Generator/Photo Editor/Image to Video/Video Editor、Skill Plaza 的 `image-remix` 和 `character-scene-storyboard`，逐项核安装版能否调用、版本、许可证、费用、导出格式。官方 [Design 网站](https://design.minimax.io/)和[工具目录](https://design.minimax.io/tools)只是公开候选；[MiniMax-AI/skills](https://github.com/MiniMax-AI/skills/blob/main/README_zh.md)是面向编程工具的另一套 Beta 技能库，不能假定已在 Design 内安装。`vision-analysis`、`shader-dev`、`minimax-multimodal-toolkit` 可按适配性评估；React/Next.js、Framer Motion/GSAP 等 Web 方法只作视觉/运动参考，正式运行时是 C#/Avalonia。对 9/30 包 UI01–UI14 同样核版本与许可，不必全装。官方未给热度排名时把“最火”写 `UNVERIFIED`，按 AAOS 适用性选，不为流行度调用无关插件。

## 真实后端、验收和交付

沿 `AAOS-UI-BACKEND-MAP-20261001.md` 将页面/状态接到已合并的真实 Rust Core；没有 Original 持久化、完整 graph、语义搜索、workspace 编辑、机器纠错等生产路由时给出真实空态或 `待开发`，不要用虚构 KPI、图、文件、模型健康或演示卡片冒充集成。与 DSH 后端分支交换版本化 API/状态合同；保持 Rust 单写入边界。Desktop/dotnet 启动异常必须读日志/堆栈，不凭 `0xe0434352` 推断原因。网页/画布预览只能作阶段展示，最终以原生 Avalonia 和原 Green 安装态验收。

每页交付：母版—现状—新方案三列对照、布局尺寸与断点、主题令牌、资产及引用索引、交互/动画规范、真实接口与七类状态、原生双主题/宽窄窗截图、差异与未闭合项。按 52 个 UI key 记录 `PLANNED / IMPLEMENTED_LOCAL / TESTED_LOCAL / CI_VERIFIED_EXACT_SHA / INSTALLED_RUNTIME_VERIFIED`，不能跨级推断。完成后仅提交任务所属公共修改，推送独立设计分支并回读远端精确 SHA 与同 SHA CI；原 Green 给出**实际验证过**的启动路径，未安装则写 `NOT_EXECUTED`。保留 PR Draft 与 R6 release `FROZEN`，未满足全产品门禁不宣称完成或发布。

节省云端 token：先读索引和 52 个 UI key，每次只加载一个页面及有关母版/源码；用路径、SHA 和裁剪图引用已有资产，不反复传 23 张整图、270 行账本或 ZIP；先复用已审主题/组件/图标，确有缺口再调用生成和视频能力。即使软件缺 Git/代码能力也继续产出可接入的设计源和资产，不把能力缺口当作设计停工理由。
