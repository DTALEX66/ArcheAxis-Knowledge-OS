# AAOS 未闭合任务总账（2026-10-01）

状态：`PARTIAL / AUDITED`。本表把当前项目状态、用户新要求和共享任务资料对照后归档；不是新 Authority，不把任务包条目当作已证实缺陷或已完成证据。优先级为正式 UI → 轻量治理 → 真实后端及前端闭环。清理任务暂停，缓存、历史文档、数据库、恢复包均保持原样；不访问 E/F 盘。

## 权威与来源

- 当前权威入口：`AGENTS.md`、`docs/CONFIGURATION_AUTHORITY_INDEX.md`、`PROJECT_CONTRACT.yaml`、决策账本、`docs/authority/taskpack-0919-r6/`、`docs/current/R6-STATE.json`、`docs/current/R6-EXECUTION.md`、`docs/current/M0-DIRECTION-OVERRIDE-20260920.md`。根 `AUTHORITY.md` 缺失：`AUTHORITY_REFERENCE_MISSING`。R6 状态账本标记 `IN_PROGRESS`、release `FROZEN`，账本更新时间为 2026-09-26；须以本轮源码、远端与原生运行回读补充，不应视为 10 月 1 日实时验收。
- 用户最终产品视觉：`D:/All projects/UI套件/01_01_产品信息架构_Information_Architecture.png` 至 `12_12_搜索与复习_Search_Review_FSRS.png`；品牌图 `01_01_品牌主视觉_Brand_Hero.png` 至 `11_11_品牌应用_Applications_Left.png`。B10 只作交互原型参考。逐页映射见 `AAOS-UI-COVERAGE-MATRIX-20261001.md`、`AAOS-UI-MASTER-ASSET-AUDIT-20261001.md`、`AAOS-UI-NAVIGATION-IA-20261001.md`、`AAOS-UI-ASSET-MANIFEST-20261001.json`。
- 共享任务资料：`D:/All projects/Record/AAOS_ArcheAxis_今日完整整合最终任务包_2026-09-28.zip` 的 `00_先读我.md` 说明它是交接资料，`03_完整任务与验收要求.md` 的 AA/UI/BE/CLEAN/GJ 条目尚未逐条评定；`D:/All projects/Record/AAOS_UI_FRONTEND_TASKPACK_20260930.zip` 是后续前端提案，须先对照 live Authority；`D:/All projects/Record/AAOS_UI深度优化调研与Codex执行方案_2026-09-28.md` 为研究建议。9 月 29 日规划属历史记录。10 月 1 日四份外部生态材料的 AAOS 摘录及来源见 `docs/history/external-inputs/2026-10-01/AAOS-ECOSYSTEM-AUDIT.md` 和 `AAOS-ECOSYSTEM-EXTRACT.json`，三项目实施清单标记 `PROPOSAL_NOT_NEW_AUTHORITY`。上述资料中的跨项目、清理或迁移建议没有自动授权本项目执行。

## 第一阶段：正式 UI 前端（当前优先）

| ID | 尚待完成的可验收工作 | 当前证据与边界 |
| --- | --- | --- |
| UI-01 | 12 张产品母版逐页同尺寸对照，补齐布局、配图、矢量图标、字体、间距和视觉层级；品牌五色及两套基础主题全页复核。 | 现有 Home 双主题星球 Hero、主题令牌和菜单图标是局部实施；64 张原生页面/主题/720、1280 渲染截屏仅证明可渲染，未完成母版一致性比对。见覆盖矩阵和资产清单。 |
| UI-02 | 一级/二级/三级导航全部落到可用真实对象或清楚的待开发状态；窄窗、键盘、历史 route 和系统区保持一致。 | 当前 10 个日常一级入口、独立系统区、宽屏二级栏/窄屏折叠已实施；三级多为路径说明，尚缺真实对象 ID 导航全覆盖。见导航 IA。 |
| UI-03 | 逐页实现真实交互和加载、空、错误、权限、离线、冲突状态；不能用示例数据伪装 Core。 | 首页和证据空态有原生 Core 回读；其他页面/状态矩阵仍未逐项运行。原创正式持久化、图谱节点边、语义搜索等接口不足时应明确不可用。见后端映射。 |
| UI-04 | 动效及光效对照母版做适度原生实现，并验证 reduced motion、失焦停帧、低性能回退；完成 100/125/150/200% DPI、IME、屏幕阅读器与窗口缩放。 | 原生低频星环背景已实施且失焦/减弱动效停计时；未完成多页面动态视觉、DPI、IME 与 UIA 验收。Web/React 动效库仅作来源参考，不直接嵌入第二运行时。 |
| UI-05 | 定向核对 9/28 任务包 AA-UI-01..14 与 9/30 包可用 UI/Icon 库的具体版本、许可证、素材映射；把确可用资产直接部署并维护索引。 | Lucide 0.468.0 三类 Reader 文件矢量已映射；余下候选仍需逐项选择和核许可。见 `AAOS-UI-THIRD-PARTY-ICON-SOURCES-20261001.md`。 |
| UI-06 | 对当前精确源码执行全合同、Release、原生全页视觉及真实操作验收，并在原绿色版提供同一 SHA 的启动路径。 | 阶段版本 `18a000758e7ffe9e731d070f1c46e67a07c4de6d` 已以独立目录安装在原 Green 根下、启动 Desktop 与 Core，严格候选/安装验证 20,081 文件、0 问题；后续变更必须重建同 SHA 安装。64 截屏不是交互或真实用户数据验收。 |

## 第二阶段：轻量治理

| ID | 尚待完成的可验收工作 | 当前证据与边界 |
| --- | --- | --- |
| GOV-01 | 保持项目 Authority 索引、R6/M0 ledger、UI 覆盖矩阵与真实代码/证据同步；修复过期的 B10/旧候选断言和交接陈述。 | 旧账本不能替代 10 月 1 日现场；本轮 236 项定向测试通过，精确远端 CI 仍须在修复提交后重跑。 |
| GOV-02 | 把 9/28 AA/UI/BE/GJ 和 9/30 项逐条映射为已实现、局部、待核、阻塞，保持来源与完成证据分离；仅登记 AAOS 范围。 | 共享包自述未对照本机事实，故未把全部包条目直接标 `TODO`。本表记录当前已确认缺口，详细任务文字仍在原 ZIP。 |
| GOV-03 | 分支仅合并通过验收且适合公开的公共修改，回读远端精确 SHA 与 CI；不把 Draft PR、push、候选组包称为发布。 | 阶段 PR #155 已合并；当前 PR #156 为 Draft，尚未达到完整 UI/后端闭环门。R6 release 仍冻结。 |

## 第三阶段：真实后端及前端闭环

| R6 / M0 对应 | 尚待完成的可验收工作 | 状态来源 |
| --- | --- | --- |
| A02、A16 | 资源根语义及最终 Local Green/发布由 Owner 决策；A16 还要求 P0–P6、真实迁移、备份替换回滚。 | `BLOCKED_BY_OWNER_DECISION`，`R6-STATE.json`；不自行改变资源边界或发布。 |
| A03–A06 | 上游 SHA/许可/runtime/基准；Desktop/Core 经 UI 重启与真实首用；代表性多格式质量/动态渲染；向量、reranker、graph/research/provider 与基准。 | A03 `TESTED_LOCAL` 仍有缺口，A04–A06 `TESTED_LOCAL_PARTIAL`。 |
| A07–A11 | 真实模型错误→人审→复用重测；Mastery/自适应学习、真实领域内容与互动 renderer；共享模型运行和有界基准。 | A07–A11 `TESTED_LOCAL_PARTIAL`；合成 FSRS/UIA 不能替代真实模型/领域运行。 |
| A12–A14 | 当前源码的全路由 UIA/键盘/DPI/IME/无障碍、真实首用；workspace identity/Legacy 语义迁移与 P3、Green 替换/重启/回滚；真实 Source→Knowledge→Human Learning→Machine correction/retest 全链路及重启回读。 | A12–A14 `TESTED_LOCAL_PARTIAL`。旧候选证据不能继承给新 EXE。用户暂停清理，不因此启动 Legacy 数据迁移。 |
| A15 | 独立 G01–G14 Local Green 资格，包含真实格式、模型、GUI、干净机器、runtime 目录及发布证据。 | `TESTED_LOCAL_PARTIAL`；完整资格仍阻塞，产品不得标 READY。 |

执行时按 `UI-01..06 → GOV-01..03 → R6/M0` 前进，但允许 UI 所需的真实 Core 绑定同步完成。每项关闭须写明精确源码/二进制、测试或原生证据、真实/合成数据等级与未闭合项。不得把清理任务恢复到队列。
