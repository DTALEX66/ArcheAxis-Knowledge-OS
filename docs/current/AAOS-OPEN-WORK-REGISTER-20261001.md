# AAOS 未闭合任务总账（2026-10-01）

状态：`PARTIAL / AUDITED`。本表把当前项目状态、用户新要求和共享任务资料对照后归档；不是新 Authority，不把任务包条目当作已证实缺陷或已完成证据。优先级为正式 UI → 轻量治理 → 真实后端及前端闭环。用户新允许将分支与仓库目录规范清理作为单独审计任务 GC-01..05；实际删除须在逐项审计、归档、引用更新和回退核实后进行。缓存、历史文档、数据库、恢复包的清理仍暂停；不访问 E/F 盘。

**逐项总账**：`AAOS-ALL-TASKS-LEDGER-20261001.json`。共 270 个来源键、17 组来源，键唯一；每项保留来源 ID、标题、原状态、当下审计分类、要求/验收原文（9/28 包）、证据入口与 R6 映射。它是任务来源与验收差距索引，不覆盖 `R6-STATE.json`。其中 `OPEN_OR_PARTIAL` 表示尚无覆盖整项的当前精确源码与运行证据，不能等同“完全没开发”；`HISTORICAL_TRACE_ONLY` 不恢复旧计划的执行权限。来源级清点已完成；需要真实 GUI/Core/用户数据的逐项完成核验仍在进行。

**逐项执行处置**：`AAOS-ALL-TASKS-DISPOSITION-20261001.csv` 与 `AAOS-UNFINISHED-TASKS-20261001.md` 已对 270 键全部给出队列或非当前执行原因；52 UI、9 轻量治理、54 后端前端闭环，4 个 Owner 关卡，其余候选/延期/历史/暂停/未采纳。来源整理已完成，产品任务未完成。

| 来源族 | 已拆出的条目 | 处理 |
| --- | ---: | --- |
| 9/28 完整包 | 43 | AA-00/01、AA-UI-01..14、AA-BE-01..10、AA-CLEAN-01..04、GJ-01..13；清理四项暂停。 |
| 9/30 UI 包 | 17 + UI01–UI14 | 11 个实施主题、6 个独立交付物、14 个开源候选；候选不是必须全部安装。 |
| UI 开发提示词、9/29 需求与吸收候选、科研增强 | 10 + 17 + 11 + 5 | 与用户最新 PNG 和 R6/M0 裁决对照；长期蓝图不冒充当前功能。 |
| 当前 R6/M0 | 17 + 7 | 复制当前账本状态及历史 M0 差额，验收仍回写现有权威账本。 |
| 0906/0907/0908/0910/0912 历史任务包 | 107 | 仅保留 ID、标题及 supersession 追踪，按当前能力和证据去重，不重启旧执行路线。 |
| 9/24 前端计划、9/25 DP 分工、10/1 生态切片 | 8 + 5 + 9 | 历史/提案与当前缺口分开。 |

9/29 的 97 个来源资产、47 个供应链项目、369 个 OSS 研究条目、16 个能力映射，以及 9/27 的 26 个合成验证阶段，作为**目录/证据**列在 JSON `source_catalogs_not_tasks`；它们不是 555 个新执行任务。对 9/28 包、9/30 包、UI 提示词和四份生态文件均未凭原文直接改变 Authority 或标记 `PASS`。

## 权威与来源

- 当前权威入口：`AGENTS.md`、`docs/CONFIGURATION_AUTHORITY_INDEX.md`、`PROJECT_CONTRACT.yaml`、决策账本、`docs/authority/taskpack-0919-r6/`、`docs/current/R6-STATE.json`、`docs/current/R6-EXECUTION.md`、`docs/current/M0-DIRECTION-OVERRIDE-20260920.md`。根 `AUTHORITY.md` 缺失：`AUTHORITY_REFERENCE_MISSING`。R6 状态账本标记 `IN_PROGRESS`、release `FROZEN`，账本更新时间为 2026-09-26；须以本轮源码、远端与原生运行回读补充，不应视为 10 月 1 日实时验收。
- 用户最终产品视觉：`D:/All projects/UI套件/01_01_产品信息架构_Information_Architecture.png` 至 `12_12_搜索与复习_Search_Review_FSRS.png`；品牌图 `01_01_品牌主视觉_Brand_Hero.png` 至 `11_11_品牌应用_Applications_Left.png`。B10 只作交互原型参考。逐页映射见 `AAOS-UI-COVERAGE-MATRIX-20261001.md`、`AAOS-UI-MASTER-ASSET-AUDIT-20261001.md`、`AAOS-UI-NAVIGATION-IA-20261001.md`、`AAOS-UI-ASSET-MANIFEST-20261001.json`。
- 共享任务资料：`D:/All projects/Record/AAOS_ArcheAxis_今日完整整合最终任务包_2026-09-28.zip` 的 `00_先读我.md` 说明它是交接资料，`03_完整任务与验收要求.md` 的 AA/UI/BE/CLEAN/GJ 条目尚未逐条评定；`D:/All projects/Record/AAOS_UI_FRONTEND_TASKPACK_20260930.zip` 是后续前端提案，须先对照 live Authority；`D:/All projects/Record/AAOS_UI深度优化调研与Codex执行方案_2026-09-28.md` 为研究建议。9 月 29 日规划属历史记录。10 月 1 日四份外部生态材料的 AAOS 摘录及来源见 `docs/history/external-inputs/2026-10-01/AAOS-ECOSYSTEM-AUDIT.md` 和 `AAOS-ECOSYSTEM-EXTRACT.json`，三项目实施清单标记 `PROPOSAL_NOT_NEW_AUTHORITY`。上述资料中的跨项目、清理或迁移建议没有自动授权本项目执行。

## 第一阶段：正式 UI 前端（当前优先）

| ID | 尚待完成的可验收工作 | 当前证据与边界 |
| --- | --- | --- |
| UI-01 | 12 张产品母版逐页同尺寸对照，补齐布局、配图、矢量图标、字体、间距和视觉层级；品牌五色及两套基础主题全页复核。 | 现有 Home 双主题星球 Hero、主题令牌和菜单图标是局部实施；64 张原生页面/主题/720、1280 渲染截屏仅证明可渲染，未完成母版一致性比对。见覆盖矩阵和资产清单。 |
| UI-02 | 一级/二级/三级导航全部落到可用真实对象或清楚的待开发状态；窄窗、键盘、历史 route 和系统区保持一致。 | 重审见 `AAOS-NAVIGATION-STRUCTURE-REVIEW-20261001.md`：10 个一级标签均被隐藏，二级首页/工作区/记忆缺项，复习被归入学习二级，三级只是路径文字。结构审计完成，实施与原生验收仍 `OPEN`。<br>2026-10-08 React 主线已实施（`IMPLEMENTED_LOCAL / TESTED_LOCAL`，分支 `codex/aaos-ui02-nav3-20261008`，基线 `4b9828c4`，提交 `5dc551e7`）：`frontend/src/presentation/spaceSections.ts` 给 9 个空间各自二级对象分组，ready 项必须绑定当前渲染表面真实挂载的 `data-section` 区域，否则降级为待开发并写出缺失的 Core 操作（如 URL 抓取、掌握度聚合、跨文档核验台账、投递队列）；`frontend/src/components/NavTrail.tsx` 三级对象路径显示 Core 返回的 `source_id@revision / document_id v版本 / item_key / knowledge_id`；复习成为学习空间独立二级分组。旧重审的"标签被隐藏"属冻结 Avalonia 供体，React 主线标签本就常显。回执 `…/evidence/ui02-three-level-nav-20261008/summary.json`：vitest 362/362（53 文件）+ tsc exit 0 + `scripts/a0_browser_smoke.py` 本地 Chromium 10 视口×3 主题 `status=PASS`、无横向溢出、`errors=[]`。**未**主张安装宿主 WebView2 原生截图、物理 IME/DPI/P95 与九步人工旅程。 |
| UI-03 | 逐页实现真实交互和加载、空、错误、权限、离线、冲突状态；不能用示例数据伪装 Core。 | 首页和证据空态有原生 Core 回读；其他页面/状态矩阵仍未逐项运行。原创正式持久化、图谱节点边、语义搜索等接口不足时应明确不可用。见后端映射。<br>2026-10-08 `PARTIAL`（分支 `codex/aaos-ui02-nav3-20261008`，提交 `871c123c`，基线 `4b9828c4`）：实测 13 个页面中离线态只有 1 处、冲突态 3 处有表达，且知识库页把 Core 已区分的 409/403/404/429/502/离线 全压成同一句话。已落 `coreFailureReason()` 分类器并接入知识库页（未知错误不显示原因，不编造），分类原因作为补充文本且**故意不带 role**——第一版给它加了 `role="status"`，第二个 live region 打断 3 条用 `findByRole("status")` 单匹配等待消息的已提交真值测试（知识库、复习守卫、资料库脏文保持），全量套件确定性失败，已 `git revert`（`1cdaf97a`）后按无 role 方案重做。同一轮 `FolderIngest.test.tsx` 的失败是 5 秒超时（单独跑恒绿），与本页无关——上一轮我把它误记成同一原因，此处更正。2026-10-08 续：分类已再接入资料库/学习/全能力目录三页（提交 `137ad858`，干净树采集），全量 vitest **373/373（54 文件）**+ tsc exit 0 + 本地 Chromium A0 门 `PASS`（10 视口、0 溢出、0 页面错误、0 宿主问题）。回执 `…/evidence/ui03-failure-states-20261008/summary.json`：全量 vitest 两次独立运行均 371/371（54 文件）+ tsc exit 0 + 本地 Chromium A0 门 `PASS`（10 视口、0 溢出、0 页面错误，干净树 `871c123c` 采集）。**仍未做**：示例数据伪装逐页检查、原生 WebView2 宿主内回读。2026-10-08 续二：分类再接入 8 个 Web 模式旧页（导入、交换、证据、机器知识、知识库、资料库、工作台、学习，共 31 处错误处理，按脚本逐页计数 5/3/6/3/4/4/1/5）。这些页原先拿到带 `offline`/`unauthorized`/`migrating`/`backend_starting` 的 ApiError 却只显示“本地数据暂时不可用”，即宿主缺失与写入被拒读起来一模一样；`failureMessage()` 现分类这四种，未分类的 5xx 保持原句不变，`ClosedLoopSpaces` 的既有断言全部照旧通过。提交 `82ef65d9`：全量 vitest **374/374（54 文件）**+ tsc exit 0 + A0 门 `PASS`（干净树 `82ef65d9` 采集，10 视口、0 横向溢出、0 页面错误、0 宿主问题）。`SettingsSpace` 因错误写法不同被本轮脚本跳过，仍属未接页。 |
| UI-04 | 动效及光效对照母版做适度原生实现，并验证 reduced motion、失焦停帧、低性能回退；完成 100/125/150/200% DPI、IME、屏幕阅读器与窗口缩放。 | 原生低频星环背景已实施且失焦/减弱动效停计时；未完成多页面动态视觉、DPI、IME 与 UIA 验收。Web/React 动效库仅作来源参考，不直接嵌入第二运行时。 |
| UI-05 | 定向核对 9/28 任务包 AA-UI-01..14 与 9/30 包可用 UI/Icon 库的具体版本、许可证、素材映射；把确可用资产直接部署并维护索引。 | Lucide 0.468.0 三类 Reader 文件矢量已映射；余下候选仍需逐项选择和核许可。见 `AAOS-UI-THIRD-PARTY-ICON-SOURCES-20261001.md`。 |
| UI-06 | 对当前精确源码执行全合同、Release、原生全页视觉及真实操作验收，并在原绿色版提供同一 SHA 的启动路径。 | 阶段版本 `18a000758e7ffe9e731d070f1c46e67a07c4de6d` 已以独立目录安装在原 Green 根下、启动 Desktop 与 Core，严格候选/安装验证 20,081 文件、0 问题；后续变更必须重建同 SHA 安装。64 截屏不是交互或真实用户数据验收。 |

## 第二阶段：轻量治理

| ID | 尚待完成的可验收工作 | 当前证据与边界 |
| --- | --- | --- |
| GOV-01 | 保持项目 Authority 索引、R6/M0 ledger、UI 覆盖矩阵与真实代码/证据同步；修复过期的 B10/旧候选断言和交接陈述。 | 旧账本不能替代 10 月 1 日现场；本轮 236 项定向测试通过，精确远端 CI 仍须在修复提交后重跑。 |
| GOV-02 | 逐项维持所有用户资料、历史任务 ID 与当前 R6/M0 的追踪映射；对每项真实完成证据继续复核。 | 270 条来源级拆解已在 JSON 总账，9/28 的完整要求/验收已复制；运行时验收尚未逐项通过，不能把来源级审计称为产品完成。 |
| GOV-03 | 分支仅合并通过验收且适合公开的公共修改，回读远端精确 SHA 与 CI；不把 Draft PR、push、候选组包称为发布。 | 阶段 PR #155 已合并；当前 PR #156 为 Draft，尚未达到完整 UI/后端闭环门。R6 release 仍冻结。 |
| GOV-04 | 审计项目源码与 Green 安装边界、工作树/分支和路径引用；保护未知修改，先归档与验证，再逐项处置确属冗余的分支/目录，并更新索引、脚本、启动路径。 | 见 `AAOS-GREEN-REPOSITORY-BOUNDARY-AUDIT-20261001.md` 的 GC-01..05。目录身份仅初审；未删除/迁移任何文件。缓存、历史文档、数据库和恢复包继续保持。 |

## 第三阶段：真实后端及前端闭环

| R6 / M0 对应 | 尚待完成的可验收工作 | 状态来源 |
| --- | --- | --- |
| A02、A16 | 资源根语义及最终 Local Green/发布由 Owner 决策；A16 还要求 P0–P6、真实迁移、备份替换回滚。 | `BLOCKED_BY_OWNER_DECISION`，`R6-STATE.json`；不自行改变资源边界或发布。 |
| A03–A06 | 上游 SHA/许可/runtime/基准；Desktop/Core 经 UI 重启与真实首用；代表性多格式质量/动态渲染；向量、reranker、graph/research/provider 与基准。 | A03 `TESTED_LOCAL` 仍有缺口，A04–A06 `TESTED_LOCAL_PARTIAL`。 |
| A07–A11 | 真实模型错误→人审→复用重测；Mastery/自适应学习、真实领域内容与互动 renderer；共享模型运行和有界基准。 | A07–A11 `TESTED_LOCAL_PARTIAL`；合成 FSRS/UIA 不能替代真实模型/领域运行。 |
| A12–A14 | 当前源码的全路由 UIA/键盘/DPI/IME/无障碍、真实首用；workspace identity/Legacy 语义迁移与 P3、Green 替换/重启/回滚；真实 Source→Knowledge→Human Learning→Machine correction/retest 全链路及重启回读。 | A12–A14 `TESTED_LOCAL_PARTIAL`。旧候选证据不能继承给新 EXE。用户暂停清理，不因此启动 Legacy 数据迁移。 |
| A15 | 独立 G01–G14 Local Green 资格，包含真实格式、模型、GUI、干净机器、runtime 目录及发布证据。 | `TESTED_LOCAL_PARTIAL`；完整资格仍阻塞，产品不得标 READY。 |

执行时按 `UI-01..06 → GOV-01..04 → R6/M0` 前进，但允许 UI 所需的真实 Core 绑定同步完成。每项关闭须写明精确源码/二进制、测试或原生证据、真实/合成数据等级与未闭合项。GC-01..05 仅适用于分支/仓库目录规范；其他清理与迁移继续暂停。
