# UI 优先首批执行与存储交接 · 2026-10-09

> **2026-10-11 最新 Owner 决定**：恢复完整框架、常见常用格式及最短闭环产品实施，RUNNING_BY_OWNER / PARTIAL；范围见[恢复决定](AAOS-CLOSED-LOOP-OWNER-RESUME-20261011.json)。下文暂停/停止/旧 CI 缺资格均保留原时点，最新 CI 读[收口记录](AAOS-AUTHORITY-CLOSEOUT-20261010.md)。当前优先：创建幂等、独立草稿与现场、冲突恢复、常用格式定位重验、资源启停及新 UI 同对象旅程。

> **2026-10-10 最新仓库同步：BRANCH_PUBLISHED**。公开源码、任务包和文档已推送；源码快照 `3c1265be1017f565a64701b513bac3e51d724584`、Git树 `982dafceddc85b8e023f3d028b86805b9592f041` 经GitHub原生API及远程refs读回匹配，main与两个任务分支一致，本地主检出和代码检出已收敛。当前交付元数据的最新SHA以实际Git HEAD/远程ref为准。旧段落“源码不同/未commit/push/云端缺文件”仅为旧时点；不再表示当前仓库状态。安装/产品任务仍暂停，整体PARTIAL与FAIL保留。**CI_VERIFIED_EXACT_SHA未获得**：推送响应显示required a0-gates仍expected，服务器接收提交不等于CI通过。


本轮状态 **PARTIAL**：首批本地实现与自动检查 PASS；桌面安装版/物理 IME/Owner 验收未执行，S01 清理完成盘点及恢复核验、未执行删除。本文是执行回执，不替换 Authority，不把 TaskPack 或历史 PASS 当本轮完成证据。

当前最新收尾：**UF13 已启动切片完成验证后，按用户要求停止**；整体 TaskPack / UF13 均 **PARTIAL**。读[当前切片回执](receipts/AAOS-UI-FINAL-SLICE-20261010.json)和[原107条及18主题审计](AAOS-UF13-ACCEPTANCE-AUDIT-20261010.json)。审计为实施前快照，后续变化由切片回执分账，不将历史源码证据重标为当前 PASS。**不自动开启后续任务**；V01暂停、FT01–04冻结。

## 最新治理修订：G01 当前路由与索引

2026-10-09 用户要求先对齐权威、规则、索引和本地/云端描述；已更新统一活动路由及消费者。当前入口为 [AAOS-ACTIVE-EXECUTION](AAOS-ACTIVE-EXECUTION.json) 与 [当前 Agent 交接](AAOS-AGENT-HANDOFF-CURRENT.md)，验证及云端边界见 [G01 对齐记录](AAOS-GOVERNANCE-ALIGNMENT-20261009.md)。主根 Authority 缺失与 R6/Avalonia 陈旧入口已在 G01 修复；下文记录首批实施时的现场，不能重新作为当前入口。G01 优先收尾完成，70 项治理回归 PASS；GitHub About 更新 PASS，远程文件尚未提交/推送。

## 配色修订：同一主题内的颜色统一

用户补充要求“统一配色主题下，颜色要统一”。已将工作台横幅写死的深蓝遮罩/浅色文字改为当前主题的面板色、正文色、辅助文字及强调色；侧栏、内部导航与能力目录标题共用侧栏色；卡片、错误边框/背景、信息徽标、命令弹层和对话框改用对应语义主题变量。原始新配色token值与五个theme ID未变，布局和业务逻辑未变。

最新预览为 `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\f714401b40\ui-theme-uniform-20261009\index.html`，按一个主题展示01/02/03，15张真实React截图。浏览器逐主题核对横幅、侧栏和7种组件样式，5主题、35合成样式探针、0pageerror，PASS；host/Core数据仍SIMULATED。原视觉对照保留为配色修订前的布局证据，不能用于声称最新颜色。

最终前端回归 `ui-theme-uniform-front2`：66文件/542测试PASS、source_consistent=true；定向浏览器 `ui-theme-uniform-browser3` PASS、source_consistent=true；生产构建 `51d65f81dba1` PASS、source_consistent=true。新增CSS三文件的before备份、脚本、计算样式和截图在 `runs\f714401b40\ui-theme-uniform-20261009`。此前13窗口全流程属于语义布局阶段，本次配色变更后执行上述定向检查，未重复全流程；不将旧截图标成最新。未安装、未提交/推送。

## 当前用户决定与执行现场

用户授权“按照交接并行执行任务”，确认 `gov-ui-20261008` 没有其他 writer，并明确：**新布局、新架构和其他行为按新任务；新配色不覆盖，旧配色转为可切换主题**。这覆盖交接中关于默认配色的旧安排。新 UI ZIP 是设计输入，原始历史文档不是额外执行授权。

资料/交付入口 `D:\All projects\ArcheAxis-Knowledge-OS`，本轮核实 branch `codex/Audit`、HEAD `1a981a4482b01f31989074e79c82a63400aa07a7`。首批实施开始时主根 `AUTHORITY.md` 为 AUTHORITY_REFERENCE_MISSING（G01 已修复），AGENTS 中旧 R6/Avalonia 不作为新实施基线。

代码 writer 为 `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\gov-ui-20261008`，branch `codex/aaos-gov-ui-20261008`、HEAD `fc5d4adc7acc28e38c2e6046ef06c0be2eed721d`。本轮读回其 AGENTS、Authority、合同与两个 Authority 索引：正式栈仍为 SUP-022 的 Tauri 2 + React/TypeScript/Vite，Rust Core 为 SQLite/CAS 唯一 writer，Python workers 隔离。

保留两个检出的已有 dirty 状态与未知文件。并行 Agent 只读或在独立 ignored scratch 产出候选；统一 writer 按基线 SHA 串行合入。首批 UI/存储阶段没有 reset/clean/stash、覆盖未知修改、提交、推送、PR、云 CI、发布、安装切换或配置修改；后续 G01 仅已更新 GitHub About，见最新治理回执。V01 继续暂停；E/F、私人会话、凭据未进入。

本轮证据根：`D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\f714401b40\ui-first-20261009-a\artifacts`。其他检查使用同一 `runs\f714401b40` 下独立 run。原始失败日志也保留。

## 首批实现

| 切片 | 已实现与证据边界 |
|---|---|
| UF00 | 22 语义页面投影到现有 route/对象；保持旧 `#space`、`#capability` 兼容，不新建第二 router。 |
| UF01 | 五域导航、218px 侧栏、公共搜索、真实 React 工作台、窄窗抽屉及键盘焦点。默认 `blueprint`，新增 `blueprint-light`；原 `black/white/cosmic` 及业主 emblem 保留，既有持久化 theme ID 仍有效。新 token 数值按输入保留。 |
| UF02 | desktop/browser 使用同一 canonical 业务视图。浏览器没有本地 host 时诚实显示离线；未新增 localStorage 业务库、DB 或编辑器。 |
| UF03 | 01 工作台读取 Core 文档/学习投影；02 文档表格、检索、原件/关联身份筛选与分页；03 正文编辑区和来源/版本辅助区，复用 Tiptap 和同一文档状态。20 使用只读历史模式。普通中文笔记无需依据即可保存。分页失败保留已有内容并重试，重复 cursor 拒绝。 |
| CB01 / UF04 | 有限 v2 预检/确认恢复合同；UI list→选择→预检→明确确认→恢复→重启读回。稳定 backup ID/filename/SHA 校验，不接收 WebView 路径。19 可靠性与20版本来源接入已有底座。 |
| UF06 | 16 父 CAP 可发现；186 原始设计细项按原顺序保留、可搜索。每项独立证据 UNKNOWN，父声明/健康握手不提升子项资格。复用 Atlas/registry 与模板联接，无第二进度库。 |

恢复沿用 Core 离线 maintenance：预检 human-only、拒绝机器/路径/损坏 CAS/不兼容 schema；host 限 main window，保持恢复操作锁，保全原 DB/CAS，失败按原 maintenance 回滚；snapshot/manifest/CAS 使用拒绝写入/删除的持有句柄封存，并重新校验 SHA。恢复期间屏蔽快捷键、导航和 portal 操作；确认尝试结束时，无论成功还是读回失败，都失效旧视图及缓存。失败不发成功事件，保留未确认 alert。未保存草稿阻止确认。

版本页显示真实 Core/合同/schema/SQLite，安装包来源与构建 SHA 仍 UNKNOWN。未接通的其他新页面明确显示“此页面尚未接通”及所属切片；不能把22入口、186细项、97资产来源或96追踪条目等同22完整页面或全能力实现。

装饰 hero 是业主输入 ZIP 的单独素材，不是整页截图。来源 ZIP SHA `ede6626a0fa572351e534bc202c8d5d69817fec99e570b301bdfd17a02b78dc1`，member `AAOS_UI_Frontend_20261009/assets/images/deep-space-hero-original.png`，素材 SHA `9595b1a8badc979b6d8f9b10c3afff2a9ac2eec249f400d79d33e7d1e793685c`。上游素材许可未独立核验；本轮仅本地使用，完整来源回执为 `artifacts\ui-asset-source.json`。

## 本轮验证

| 检查 | 当前结果 | 证据 |
|---|---|---|
| 前端全回归 | PASS，66 文件 / 542 测试，0 skip | `runs\f714401b40\ui-theme-uniform-front2\artifacts\result.json`及`logs\check.log`；SIMULATED/SYNTHETIC bridge fixtures |
| 类型与生产前端构建 | PASS，source_consistent=true | `runs\f714401b40\51d65f81dba1\artifacts\frontend-build.json`；非已安装运行 |
| Windows Tauri 单元回归 | PASS，78 测试 | `runs\f714401b40\ui-first-tauri-final5\artifacts\result.json`；INTEGRATED Windows fixture，非桌面交互验收 |
| Core 文档/分页/maintenance | PASS，9+3+1 测试 | `runs\f714401b40\ui-first-core-final5\artifacts\result.json`；真实 SQLite/CAS，隔离内容 |
| vNext 合同结构/语言边界 | PASS | `runs\f714401b40\ui-first-contract-final3\artifacts\result.json` |
| 新 v2 schema 与真实预检 DTO | PASS，拒绝额外路径/非法 ID/SHA | `runs\f714401b40\ui-first-contract-v2\artifacts\result.json` |
| Chromium UI 门禁 | PASS，13 窗口/缩放组合、5主题；抽屉/focus/对比度/布局/模板与故障注入；新增新02→实际Doc ID→新03的双主题/双窗口四组验证 | `runs\f714401b40\ui-first-browser-semantic-final2\artifacts\browser-smoke\canonical-browser-smoke.json`及外层`artifacts\result.json`；真实浏览器+模拟 host |
| 独立 Core 进程闭环 | PASS，7步 | `artifacts\core-probe\attempt-05\receipt.json`，REAL Core + SYNTHETIC authored content |

最后一项包括：中文 v2 与未知 payload/CAS 原字节保存；仅停止自己启动的 Core 后重启并逐 DTO 回读；v2 预检与取消不改变 DB/WAL/SHM 哈希；坏 CAS/manifest schema 拒绝；变更到 v3 后 maintenance 恢复；保全库仍可真实读回 v3，恢复库真实读回 v2 及全部 DTO/CAS。所有 probe owned processes 已停止。不是 Tauri UI 原生确认命令端到端、物理中文输入法、安装版或人类学习资格证据。

maintenance 回执返回的 Windows `\\?\D:` 扩展路径不能直接传给现有 runtime CLI；probe 按同一文件的普通本地路径表示后回读。此限制保留在 probe README，未改任意路径权限。

最终语义布局前，Windows Tauri/Core 两组回归已通过；最终源码指纹另外逐文件确认其 Rust/Core/合同输入未变化。这两组不代表新前端在原生桌面的交互验收。

新布局新增8个有行为断言的回归：02→03传递真实Doc ID，未知payload保存与未保存离开保护，来源/文档初始化两个返回顺序，原件CAS核验，读取/分页失败不覆盖内容，新建与兼容入口。初始化先等来源和列表启动完成，再打开对象，避免关联原件漏核验和读取失败提示被启动消息覆盖。当前Doc ID保存在App状态；刷新阅读页需重新选取文档。集合/标签/其他视图仍明确未接通。

首批01/02/03/17/18/19/20的最终原型/React视觉对照见 `artifacts\ui-visual-review-final\index.html`，28张当前截图，数据标 SIMULATED。保留早期 `ui-visual-review` 和中间 `ui-visual-review-semantic`，不能将它们当最终布局证据。原始PNG2560×1440，旧render-audit标称CSS1600×900；最终使用CSS1600×900、倍率1.6导出同尺寸，标记 INFERRED_EXPORT_RATIO，不声称物理DPI验证；另保留CSS1440×1000、倍率1。02表格、03正文/辅助区与平面导航已实际渲染。既有Inspector可手动切换，开启时1440宽度下正文约570px，仍有信息密度及视觉细化空间；不声称像素完全相同或已安装验收。

## S01.A–C

详细报告见本目录 `AAOS-STORAGE-READBACK-20261009.md`，逐路径文件在 `artifacts\storage-inventory`。

同脚本/同过滤口径：初始616,850文件 /54,336,649,956 B；复测640,466文件 /58,000,205,953 B。增加23,616文件 /3,663,555,997 B，主要为本轮构建与证据，**不是清理节省**。533权限错误、私有目录/reparse跳过使统计只代表可读逻辑下限；物理分配、硬链接共享及实际可回收字节 UNKNOWN。

已有13 ZIP 在项目内分段对象上流式重构，15,042,293,812 B，13/13 SHA与长度匹配；pack/catalog SHA匹配，未再次写出15GB原件。65既有迁移目的端 SHA/长度65/65匹配，16 exact source 当前不存在；没有新增迁移。`D:\tmp`三个未知文件仅保留已授权元数据，未读正文/迁移/删除。

history 分别盘点两个检出的 tracked/untracked/ignored，逐文件长期保留/跟踪策略是提案。本地1007条精确 exclude 不是可共享长期政策；没有 blanket ignore、stage或删除原历史证据。S01仍PARTIAL，实际处置 NOT_EXECUTED；0 B释放表示未处置，不表示无可回收空间。

## 待办与回退

1. 在明确授权的独立测试工作区做 Tauri 原生恢复/重启读回，以及物理 IME/Owner 首批验收；不能使用正式知识库替代隔离 fixture，不能默认切 Green 安装。
2. S01先核实候选的消费者/生成方式/当前使用，再取得交接要求的 exact-path 大量删除或退役批准。未知、权限缺口、历史原件及恢复材料继续保留。
3. 下一批再按任务包 UF05、UF07 等逐批实施；V01、FT重型能力、远程发布不因本轮自动恢复。

候选合入回执、基线 SHA 与各阶段 before 备份保存在本 run，完整源码指纹/实际变更范围见 `artifacts\FINAL-DELIVERY.json`。回退须按本轮具体 hunks 与 before 校验，保护原有 dirty；不要从 HEAD 整文件 restore、reset、clean或回写旧主题作为新默认。不同版本的原始失败回执和 source-inconsistent运行不用于最终PASS。

## 治理与学习旅程阶段 · H01 / UF05

当前以今天任务包为主，继承旧合同与有效实现；当前用户优先治理与 UI 的决定已进入活动指针、Agent 交接及 G01 对齐记录。原任务包的规划状态和历史证据不改写。

H01 来源结构与去向验收 PASS / INTEGRATED；426 来源定位键、原270行、新96项、22页、186设计原文、六来源字节与97身份核验见 AAOS-H01-SOURCE-TRACE-20261009.md/json。独立语义覆盖仍 UNVERIFIED / PARTIAL，97原件正文未全读、产品资格 UNKNOWN。当前可见对话稳定决定已提炼，不读取私人会话。

UF05 已在代码 writer 接通新06/07同一学习旅程：Core已有课程目录分页 → 保存候选回读 → 绑定版本阅读 → 实际学习对象与作答/复习。目录是既有 SQLite 候选的只读投影，不增加数据库。搜索知识在选择时重新核验接受状态；普通笔记仍可先保存，生成条件独立检查。保存课程打开时先读原manifest，仅当前绑定可render；陈旧课程保留原正文和身份且禁止进入新的学习写入，不偷偷升级旧课与旧事件。

模型尚未支持的诊断、先修、负荷、Teach-back、元认知与画像都留在详情并对应后续任务；未显示虚构进度。当前仅 native-lesson，不能称八个真实渲染引擎。前端异步结果按对象/请求代次隔离，避免快速切换把上一对象结果写入当前课程。

| 验证 | 当前结果与实际范围 | 本地证据定位 |
|---|---|---|
| 治理/来源/索引回归 | 51 PASS | ui-learning-governance-final1/artifacts/execution.json |
| 前端完整回归 | 67文件 / 554 PASS；之后仅窄屏CSS调整，定向24 PASS | ui-learning-front-full2 与 ui-learning-responsive-front1 |
| 最终类型/生产前端构建 | PASS，source_consistent=true；非安装态 | ui-learning-stage-20261009/frontend-final-build2.json |
| Windows有限Native bridge | 16 PASS；包含课程只读列表路由/非法cursor拒绝，非桌面交互 | ui-learning-native4/artifacts/execution.json |
| Core课程与学习事件合同 | 6 PASS，实际 Python course/FSRS workers + SQLite | ui-learning-course-events1/artifacts/result.json |

上述路径以项目 owning root 的 .project-local/runs/f714401b40 为基准，均本地 ignored 证据，未核实云端可用。

新增事件回归从真实 course worker 生成/读/render 到真实 item key、assessment、错误作答、FSRS安排；重开同一 SQLite 后逐值回读课程、题目、事件和状态，事件重试不重复。同知识修订后旧课程变为 stale，原manifest/assessment/事件保留，再次重开继续一致；数据库实际1事件/1幂等键。测试内容和答案为 SYNTHETIC；Core/worker/SQLite 跨层证据为 INTEGRATED。不是 OS 独立进程重启、真人掌握或原生安装资格。当前 assessment DTO 没有独立 question/rubric 版本字段，不声称这些字段已验。

首轮浏览器60场景0pageerror，五主题内06/07颜色一致，current/stale/failure呈现通过；390px顶部控件横向溢出，已调整换行布局，最终复测单独记录。首轮 PARTIAL 保留，不改写为 PASS。

最终浏览器 `visual-assessment/final3`：60场景 PASS / SIMULATED，0pageerror、0横向溢出，五主题一致；当前/陈旧/失败边界及步序间距60/60通过。宽屏两列、窄屏一列，原配色文件SHA保持。此阶段于2026-10-10本地收尾，仍引用原20261009任务包和run身份，不重命名原包。

UF05 本地代码、合同与浏览器布局验收 PASS / INTEGRATED + SIMULATED；M01人工/安装资格、云端文件同步、V01仍 NOT_EXECUTED。后续继续按活动指针优先 UF07 及其他 UI 层任务，不把此阶段等同全部任务完成。回退按本阶段 before 备份/候选manifest具体hunks，保护原有 dirty，禁止整文件从HEAD restore。

## 新UI深化材料分析与归档阶段 · 2026-10-10

用户指定两个TXT已原字节归档到 docs/history/ui-design-increment-20261009/sources/，共15917 B，2/2 SHA与外部原件一致；正文15662 B符合附清单。原件未删除/改写；此归档是本地Git可审阅文件，未commit/push/云端发布。清单声明ZIP的exact同目录未找到，成员与01–08附表UNVERIFIED，不搜索其他目录或假造原文。

[设计增量](AAOS-UI-DESIGN-INCREMENT-20261010.md)及配套JSON登记18类有用要求并映射到原切片；22页新入口派生表保留原ID/CAP/深链接。活动pointer design_overlays、资料入口、文档索引、truth导航和当前Agent交接已同步。原TaskPack与配色值保留；五日常入口、现场恢复、迟到回执、普通不完整教学草稿与完整学习生命周期补验收，不称新增导航已实现。

档案/增量只读门禁PASS；canonical run ui-design-increment-gates1 的新增篡改负例、文档权威及索引共54 PASS；主检出16个新增来源回归PASS。来源保全及任务映射是 INTEGRATED 文档证据，产品实现不由该门禁批准。

CB02/UF07仍在实施：本轮发现并修复review v2元数据只参与幂等hash而未随事件保存的问题；6项现有真实worker/API/SQLite学习回归通过（ui-teaching-review-evidence1），重开历史可回读原题目/知识/辅助/评分/修订声明版本；这些是提交观察，不批准rubric/掌握。该句是材料吸收时点记录；正式教学记录/人工交换和六页UI现已合入并完成下述本地阶段验收；普通未完整准备草稿需复用Document保存，不放松正式登记权限冒充支持。新材料不恢复V01/FT，不扩大远程、跨仓、安装或破坏权限。

### 2026-10-10 ZIP补交更新

先前同目录缺件为当时观察；用户补交后ZIP SHA/23726 B与声明一致，CRC与内部9/9校验PASS，10成员按字节归档。五CSV共107规格记录映射到原任务；原18主题及派生22页映射保留。资料吸收PASS不代表新增产品验收PASS，当前CB02/UF07仍进行中。源07提示词不替代当前授权。详见设计增量/来源Manifest/ZIP-SPEC-CROSSWALK.json。未commit/push。

### 2026-10-10 CB02 / UF07 本地阶段验收

LOCAL PASS / INTEGRATED + SIMULATED。08需求、09方案审阅、10交付版本、11练习/Teach-back、12反馈修订、16人工交换复用同一Rust Core与React组件；16同时保留既有原件导入/文档导出入口。机器回执：[阶段源码与证据](receipts/AAOS-TEACHING-STAGE-20261010.json)。产品代码在gov-ui-20261008，主根只镜像治理资料；未commit/push，云端不得用旧main推导这批代码已上线。

Teaching v2稳定身份、规范hash、purpose/scope/privacy、父链、显式知识/课程修订、撤回传播和幂等导入已接通。实际launch主体权限与来源声明分开；专业依据/识别质量/表达适配/操作故障/掌握/AI资格独立分类，旧evidence_fidelity仍兼容。不计分记录不改变知识正文、FSRS或AI资格。普通不完整准备草稿复用无来源Document；首次创建带稳定请求ID，同ID异内容拒绝，丢回执重试不重复创建。初次请求与随后编辑分别保留。两确认窗口复用AaosDialog，Escape/Tab/取消回焦有回归；未知/坏交换JSON可下载原始File，不自动登记。

SQLite11→12加法迁移与append-only记录/撤回表；archive12保留document_checks、新教学表及CAS，历史10/11各按真实旧导出布局回归，历史fixture为SYNTHETIC。SQL/JSON父链与withdraw重复回执不一致会拒绝；旧v1四库交换验证保留，不借此写canonical。

最终验证：49项选定Rust回归、579项前端（69文件）、17项native有限桥接测试、33项旧v1/课程回归PASS，production build/typecheck PASS。真实Core build3探针7/7：两个fresh工作区、8节点教学链、人工JSON交换、预检主DB/WAL不写、坏hash/缺引用/主体伪冒/重复冲突拒绝、撤回重启与不复活；5个自有进程均结束。前置个人定义为SYNTHETIC，不是真人效果。

浏览器最终180场景（6页×5主题×1440/390×有数据/空/失败）PASS / SIMULATED，0页面错误/横向溢出，60失败提示首屏可见，12源码SHA前后不变；原主题值未改。Core探针课程/题目/rubric为空且learning events为0；旧课程绑定与知识修订、旧问题/评分/辅助/rubric声明历史分别由domain/learning_state_api回归证明，不能称一条端到端路径验了全部。原生已安装UI、物理IME、M01真人试学与长期效果NOT_EXECUTED；全平台格式保真留UF11。V01/FT边界不变。

证据根：.project-local/runs/f714401b40/ui-teaching-stage-20261010/；final3视觉、build3实际Core与各canonical run回执保留；初轮SOURCE_DRIFT视觉、5秒并发长链超时、错误Python缺pytest及探针-shm观察面误设均保留，不计最终PASS。回退按本阶段hunks/before基线，不回滚整份已有dirty文件，不把schema12新数据覆盖回旧库。下一优先UF12及剩余治理/UI任务，整个任务包仍未完成。

最终字节收口：本阶段32个源码文件约定检查PASS；6文件仅LF/空白修正后重跑49 Rust、579前端、17 bridge、production build、build3 Core probe及final3视觉180，结果均PASS。原immutable包21成员字节/hash与writer镜像保持一致。源码回执已绑定最终LF文件；阶段回执不赋予发布/安装/真人资格。

## 画布与视觉表达阶段 · UF12 · 2026-10-10

新21已接真实表达工作区：图文节点、节点关系及文字、负坐标与尺寸、键盘/拖动、CAS 图像/音视频引用；以既有 Document 的 attrs、immutable versions、create_request_id、expected_version 保存。Core 同事务验证图结构与知识／课程／方案关联、CAS 字节 SHA 与媒体头类型；陈旧课程/历史知识可显式引用，预课程方案可关联后来同知识课程，不推断或回写旧记录。未知旧表达只读保全，普通文档不被转换或覆盖。

普通缺完整上下文的表达草稿可先保存。对象切换、迟到保存、首建重试、冲突、只读历史、未提交坐标/连线输入与取消保持分账；新表达没有伪正文块，完整 envelope 读回核对。文本、媒体说明和关系标签进入确定性文本投影，布局和所有原有 attrs 仍保留。导出当前已保存修订的 snapshot／SHA／媒体引用，不写知识正文；媒体未打包，明确 reference_only，不称独立完整媒体包。

动画产物、参数仿真、空间／XR 说明及原惰性 metadata 原样保留，详情使用既有 CAP-0070/0080/0160；高级引擎继续 NOT_EXECUTED / FT冻结。原五主题 ID、palette 文件 SHA、legacy CanvasBoard 保持；关系标签遮挡修正只使用主题语义变量。

验证：61 Rust / 630 frontend（71文件）/ 17有限native bridge PASS，最终 production build PASS；21源码文本约定 PASS。实际独立 Core 进程4步骤 PASS / INTEGRATED（SYNTHETIC内容），覆盖真实PNG CAS、知识/方案、首次创建重试、引用/冲突/actor负例、导出、退出重启、历史修订、原CAS字节和知识不变；真实课程绑定另由domain SQLite回归证明，不能声称该进程使用了课程或真人。

最终浏览器首屏30 + 画布细节10 PASS / SIMULATED：5主题×1440/390×loaded/empty/failure，0pageerror/整页横溢，状态30/30、CAS图10/10、关系标签10/10可见；画布内部滚动仍属设计行为。native bridge编译对应最终dist，不是安装版/WebView2现场或物理IME。M01、真人效果、V01、发布及完整任务包验收仍 NOT_EXECUTED/PARTIAL。

[UF12源码及证据回执](receipts/AAOS-CANVAS-STAGE-20261010.json)绑定最终字节及本地run。证据根 .project-local/runs/f714401b40/ui-canvas-stage-20261010/；初轮Windows canonical CAS失败、探针端点假设错误、CSS缺规则、CRLF检查和标签遮挡截图均保留，未改写为PASS。专用bounded Core CAS reader保留本地长路径前缀，external staging权限未扩大。回退仅本阶段before/owned hunk及新增文件，保护既有dirty，不reset/clean/批量restore。下一优先 CB03 / UF08，整体目标继续。


## 集合、关系与研究阶段 · CB03 / UF08 · 2026-10-10

本地交付子项验收 PASS / INTEGRATED + SIMULATED；未实施细项保持显式未执行。当前04/05接版本化Document关系／研究和Collection组件；集合、类型属性、固定成员／关系、过滤排序分页、五种本地视图与有界公式由Rust Core读写或只读投影，不建立第二知识库或第二writer。F02身份是FUTURE-1004:F02，不混同旧Space/Format编号。

研究问题、材料、假设、方法、实验、反证、结论、未决可非线性编辑并保存；结论来源与推导依据分账，不自动采用为知识或评分。固定Document/version/Block、source/SHA和immutable knowledge详情在同页打开，草稿保留。集合关系以record.reference为from，Collection修订及content SHA为source_snapshot；图与列表读取同一快照。20来源分页与1000边截断均显示范围，历史缺目标与不支持metadata分别显示，删除关系不改旧修订。

保存确认、冻结重试与随后编辑分账；Core写入明确400拒绝可修正后新请求，丢ACK/读回失败不解除冻结。未提交JSON、迟到历史／核对回执和对象切换有双组件回归。未知attrs/body/source_payload保全覆盖本地选定夹具，不推导全部来源平台／数值编码无损。导出原定义与引用，不导出伪计算结果或完整媒体包。

验证：108 Rust、711 frontend（77文件）、18有限native bridge、typecheck、生成合同回读、changed-file Ruff与47源码字节／约定PASS。最终Core build2独立进程10步PASS，真实PNG/text CAS、研究与集合、版本/权限/错误/过滤分页、1000截断、退出重启；材料为SYNTHETIC。五主题×1440/390×21场景，聚合覆盖210场景PASS / SIMULATED（原轮209有效场景＋同源码夹具脚本下唯一失败场景独立复验三次均通过；原轮保留PARTIAL，空白DOM超时根因UNVERIFIED）；关系标签已移出节点区域，窄屏回焦以有界等待验证。日期视图为日期分组，图库为记录卡片；不是月历网格或完整媒体图库资格。

Rollup、外部公式方言等价、单位／时区／往返语义、学术搜索／GraphRAG／消歧及大型图引擎仍NOT_EXECUTED，UF06详情可见；原设计意图和Atlas不提升为完成。原palette字节保持。安装/WebView现场/物理IME/M01真人、云CI/发布未执行；V01/FT状态保持。

[源码与证据回执](receipts/AAOS-RESEARCH-STAGE-20261010.json)归本执行记录；证据根 .project-local/runs/f714401b40/ui-research-stage-20261010/。初轮CRLF/lint/style/native词汇/test-selector/图标签/即时回焦检查失败均保留，不能当最终PASS。主根只同步治理入口，产品仍gov-ui-20261008未合并；回退只处理本阶段hunks。下一优先UF09和剩余治理/UI任务，整体任务包继续PARTIAL。


## UF09 · 当前进行中（2026-10-10）

IN_PROGRESS / PARTIAL；不是阶段完成。13页上下文候选/用途/操作/时效/版本/明确授权与撤回、14页独立原知识/纠正知识授权选择、22页有限回执读取已接入实际Core对象。固定rubric与评测的Core合同已接入；评测界面尚待完成。

当前定向证据：上下文/旅程/原机器面板21项前端、类型检查、多owner草稿保护2项、Core授权与推理中撤回脱敏审计7项、rubric历史身份防伪1项PASS。失败尝试原样保留。推理中撤回返回EXECUTED_BUT_WITHHELD，失败审计不宣称未执行；稳定回答请求并发/重启重试不重复已持久化推理。模型仅当前端点可发现，真实调用NOT_RUN；预算/清理扩展、复测竞态、视觉与最终门禁仍待验证。

本阶段证据根 `.project-local/runs/f714401b40/ui-ai-stage-20261010/`，产品唯一writer仍gov-ui-20261008。先前阶段回执保留其当时源码快照，不证明UF09修改后的当前树最终合格。整体TaskPack PARTIAL，V01 PAUSED，FT冻结，未提交/推送/安装/发布。


### UF09 增量验证 · 恢复授权与有限任务（2026-10-10）

状态仍 `PARTIAL / IN_PROGRESS`。仅 gov-ui-20261008 为产品 writer。归档 restore 的 Core-owned fence 每次恢复隔离所有历史授权对象，文档/版本与归档原字节保留，新明确人工授权需新对象身份。store/archive 38 项 PASS，含实际恢复回归；此前失败日志保留，旧 schema10 模拟夹具修复了残留 schema12 教学表，原数据/外键断言保留并增强 trigger 核验。生产整库 Online Backup 维护入口是另一条路径，其保护候选待整合验证，不据归档 PASS 推导生产恢复权限安全。

页22已接实际有限 job 运行、冻结 request_id 重试、状态与取消。新增 Native job_execution_status/job_execution_cancel，jobs_get 保持原接口；取消202仅请求，终态须同request读回。前端15项、Native14项、owned-worker runtime6项、类型检查PASS，各自绑定run源码；真实步骤/提交记录/检查点/可继续条件待补，当前6字段状态不算全部实现。

早前 qwen3.5-4b 本机路由闭环已验证，6个自有进程退出；worker模型名为请求路由，权重摘要UNKNOWN，真人掌握/专业真值UNMEASURED。基础5类AI资产、有限客户端上下文包、生产恢复fence、最终当前模型及5主题视觉验证仍待整合。阶段证据：本地 .project-local/runs/f714401b40/ui-ai-stage-20261010/restore-and-task-progress.json；不作为最终UF09 PASS，不提交私有运行目录，未commit/push/install/release。


同日后续验证：生产maintenance恢复fence7项、恢复后省略授权拒绝API5项、Native完整82项、持久任务步骤/预算/committed检查点9项、基础资产领域6项、资产/任务/恢复前端39项及类型检查均本地PASS。Native恢复回执严格要求 authorization_requires_new_grants=true；失败恢复exact回滚，恢复早于首次授权的备份也不能省略grant消费。任务窗口缓存未读，标NOT_OBSERVED。严格资产parser与页13真实入口已接线，类型检查PASS；API生产身份、资产进入模型回答/复测adapter及最终5主题矩阵仍待验证，UF09整体PARTIAL。阶段记录restore-and-task-progress.json保留各run源码与失败证据。


## 2026-10-10 最新阶段：UF09 本地工程收口

当前状态 **LOCAL_ENGINEERING_CLOSED_WITH_EXPLICIT_QUALIFICATION_GAPS**；整体TaskPack仍 **PARTIAL**。最新事实以[UF09源码与证据回执](receipts/AAOS-AI-STAGE-20261010.json)为准，前文UF09待API/adapter/visual等段落为当时时点记录。

13页五类版本化AI资产、不完整候选保存、固定版本与rubric人工审核、独立授权/撤回及有限上下文包已接通；14页知识与资产双授权进入实际回答和独立复测，保存原答案、纠正、评测及撤回历史，冻结重试并验证ACK/UNKNOWN历史读回。22页接已有有限Core任务、预算/实际步骤/已提交检查点和取消请求，父级重渲染保留pending及冻结参数。恢复路径在生产Online Backup/归档及maintenance写入新授权fence，拒绝旧grant和无grant兼容绕过；原历史留存，新授权须明确创建。

最终前端全回归836测试/93文件通过，随后3项阅读布局调整由49测试/6文件、最终前端dist04和Native构建、最终视觉覆盖验证。Rust domain/store/archive217、两迁移fixture19、Python worker/治理70及Native83通过；前序五包Rust命令两次FAIL完整保留，陈旧合成v1/v8 fixture已最小修正并定向复验，不将旧命令重标PASS。最终范围82个引用文件检查通过，App仅上下文旧问题。全仓conventions8项、architecture13项旧问题仍FAIL，不能声称全仓门禁全绿。

五原主题×宽窄×24场景聚合覆盖240项PASS（SIMULATED）：原轮239有效加唯一空白载入场景独立3次复验，原PARTIAL与根因UNVERIFIED保留。40阅读裁剪检查、10张代表截图实际复看通过，32源码hash一致；原theme/token字节保留。自动化React浏览器证据不代表安装态桌面交互。

实际现有本地请求路由qwen3.5-4b完成2次推理：资产进入回答与独立复测，冻结重试、授权/成员撤回阻断、同Core持久化与正常重启读回通过。内容和人工审核fixture为SYNTHETIC；后端实际model/weights UNKNOWN，专业真值/语义质量UNMEASURED、人掌握及M01 NOT_RUN。普通重启不证明restore fence，后者使用独立回归。外部客户端仅PREPARED_NOT_SENT_TO_PEER；通用Agent/参数训练仍延期。

本次补交ZIP已完整归档，10成员/CRC/内部9项hash通过，107条原规格逐记录映射。安装态/物理IME/Owner验收、cloud CI及发布未执行。源绑定模型与最终UI分别记账；3个schema后来仅CRLF→LF，保留逐字节备份及等价证明，不冒称模型探针绑定最终全部源码。所有自有探针/视觉进程已结束。

下一队列 **O01 / UF10**（资源/开源吸收/模板），先读当前活动指针及原任务合同；模板cursor分页已存在，不重复实现。V01暂停、FT01–04冻结、五日常导航UF13仍待实施。主根只镜像资料与治理入口，gov-ui-20261008仍唯一产品writer；未commit/push/merge/安装。

## 2026-10-10 最新阶段：O01 / UF10 本地工程收口

状态 **LOCAL_ENGINEERING_CLOSED_WITH_EXPLICIT_QUALIFICATION_GAPS**；原19条合同及整体TaskPack仍 **PARTIAL**。当前事实读[资源与模板源码回执](receipts/AAOS-RESOURCES-STAGE-20261010.json)，前文UF09及下一O01/UF10属于原时点记录。

15页接通完整68供体/115原冲突、所选9项的版本/许可/权限/运行/实测与冻结条件，宿主握手独立读回；不造CAP或安装资格。学科模板复用28学科T1/T2/T3、完整cursor和同一Document版本库；固定创建请求、UNKNOWN冻结重试/历史确认、晚编辑与卸载保护、实际学习项/版本/块引用及位置保全。Core在同事务校验已知metadata；未知历史属性只允许原样携带，无损JS数值表示变化恢复旧Value再编码，真实改写/删除/精度损失拒绝。原主题token不改，引用卡使用当前主题panel/border。

最终前端96文件/866测试、Rust五包串行656、Native83、Python22和数值Document回归15通过；当前前端dist、Core与Native构建通过。真实Core六case含0/101/500/501/1001及501分页中并发新增/编辑，固定成员、版本hash、重启读回通过；12自有进程生命周期、11distinct PID（Windows复用一次）全退出。结构七检查与范围源码通过；历史失败及全仓conventions8/architecture13问题保留，不能声称全仓绿。

五主题宽窄视觉120场景为分时点聚合（旧90+最终相关30）；最新单轮全120未执行，fixture为SIMULATED。最终10图实际审阅，引用卡主题计算样式和来源指纹阅读通过；千级22.2–110.3ms只为前端fixture筛选/选择，不代表Core完整加载性能。当前锁生成SBOM/NOTICE1106条，不当成发布/installed或exact locked许可快照资格。

共有ZIP06record23混合导入/取消仍PARTIAL，CB04/UF11下一步修真实body/request_id、重试身份、取消终态和成功资料定位，再逐格式隔离验收。全池ignored payload、正式旧库、外部/安装态/Owner/M01、退出与云端发布资格各自保持缺口。UF13五日常导航仍待实施，V01暂停、FT01–04冻结。未commit/push/merge/install/release；主根只镜像资料/入口，产品writer仍gov-ui-20261008。


## 2026-10-10 执行中：CB04 / UF11 导入与互通基础修复

状态 **IN_PROGRESS / PARTIAL**，本阶段尚未收口；当前基础源码与定向回归见[基础回执](receipts/AAOS-EXCHANGE-FOUNDATION-20261010.json)。批次执行补全实际Core所需body/deadline_ms和冻结request_id，稳定行身份、同步单飞、UNKNOWN同请求恢复、Core允许后失败/取消新尝试、取消202与终态分开。表格以真实控件和稳定行key渲染；原件与转换独立，成功项按真实source/job回调。JobContent按指定任务读取，不以最近50任务替代，校验来源/原件hash/attempt/request并拒绝晚回执覆盖。旧Office三格式纠正现有Core路由声明，运行/许可/引擎资格没有据此升级。

定向前端78、Python目录驱动21、Core混合原件/重试/取消/重开1、Native真实HTTP传输2及TypeScript检查通过，当前Core新构建与seal通过。Core/native的控制失败与取消夹具明确SYNTHETIC；不冒称实际生产格式全覆盖或安装态。原始失败证据保留，13个当前源码文件逐hash登记。新16页、选定实际格式过程与逐格式定位/损失、四类互通独立验收、完整原15行合同和UF13仍待完成；正式非空旧库NOT_RUN。无commit/push/merge/install/release。主根只镜像记录，产品变更仍在唯一gov-ui-20261008 writer。


## 2026-10-10 最新进展：CB04 / UF11 集成与验证进行中

当前状态 **IN_PROGRESS**，整体 TaskPack **PARTIAL**。最新时点读 [交换集成回执](receipts/AAOS-EXCHANGE-INTEGRATION-20261010.json)；原基础回执、资源阶段及其下一队列文字保留原时点含义。不可把本次集成视为 UF11/CB04 全格式、全部平台或正式旧库收口。

16 页已经接入独立原件与转换、已保存文档两文件导出、人工教学交换和四类互通状态；五主题原 token 保留，新布局共享。手动与批量执行冻结 job/request/body，UNKNOWN 只允许同身份重试或读回，取消必须读回终态。成功派生输出校验 kind、SHA256 与 UTF8 字节长度，下载绑定实际 source/job/request/attempt。PPTX 新转换产物以真实 shape ID、chart relationship/part 保证位置唯一，旧歧义产物及拒绝证据保留。

定向前端 133 项、TypeScript、PPTX Python 6 项及实际 Rust 文档闭环 9 项通过；全前端首次 953 PASS / 8 FAIL，旧媒体/EPUB fixture 缺合同字段正在最小修正，通用持久化读取额外审阅尚未完成。新前端已构建，但此时点不是最终源码资格。五主题视觉与最终 Native/集成验证仍待读回。

隔离实际格式探针完成 11 个成功格式、损坏 PDF 失败及失败项新请求、原件 CAS 和重启验证；独立定位探针证明 13 个 located anchor、12 个实际派生选区及 49 个负检查。材料为 SYNTHETIC、证据 INTEGRATED：派生选区 marker 仍 unverified，知识 Candidate 尚需人工审核。PDF、容器与媒体头信息的格式定位、独立重解析、浏览器/原软件定位及专业正确性没有据此通过。自有 Core/worker PID 均退出。正式非空用户旧库未获 exact 来源许可，保持 NOT_RUN；全平台往返、增量同步、installed/Owner/cloud CI/release 仍未执行。

用户补交 ZIP 的 10 成员、CRC 与内部 9/9 SHA 已通过归档门禁，之前容器缺失的观察已更新。原 ZIP 与 CSV 字段是来源，不是当前权威或完成证明。继续本阶段最终验证，之后才推进 UF13 五日常路径；V01 暂停、FT01–04 冻结。主根仅镜像资料和治理，gov-ui-20261008 为唯一产品 writer；未 commit/push/merge/install。


## 2026-10-10 最新阶段：CB04 / UF11 本地工程收口

状态 **LOCAL_ENGINEERING_CLOSED_WITH_EXPLICIT_QUALIFICATION_GAPS**；原15条合同与整体TaskPack仍 **PARTIAL**。当前事实读[交换源码回执](receipts/AAOS-EXCHANGE-STAGE-20261010.json)、[原合同逐条验收](AAOS-EXCHANGE-ACCEPTANCE-20261010.json)及[72格式登记与所选实际证据](AAOS-FORMAT-QUALIFICATION-20261010.json)。先前 IN_PROGRESS、基础回执及旧队列保留时点含义。

16页为原件/派生、已保存文档两文件导出、人工教学交换与四互通状态，使用原五主题共享新布局。手动/批量冻结job/request/body，同步单飞、UNKNOWN同身份核对与重试、取消202须实际终态；generic及pin持久化结果均核对来源修订、成功尝试、非空请求、safe transform ID和各产物SHA256/kind/UTF8长度。PPTX保留真实shape与图表关系定位，新producer两处成功、旧歧义epoch拒绝不改。浏览器发现并修复StrictMode目录锁、窄屏批次操作列与PRE裁剪。

全前端980/105文件与Native85通过，之后局部UI修复由46/3文件、TypeScript、最终frontend45c60208f97a与Native build03及完整五主题宽窄40场景复验；不是把早期980伪标为最终全树测试。最终40场景/10组交互/80实际Blob下载字节读回通过（SIMULATED Core host），33源码指纹一致，root实际复看10张最终派生正文截图。所有自有视觉/Core/worker进程均退出。

实际isolated Core/worker：11成功格式与损坏PDF、失败项新请求/原件CAS/重复导入/控制取消/重启分别验收；定位13个located anchor、12个派生选区及49负检查通过。Rust文档/版本/导出/备份9项、PPTX Python6项、目录路由Python21项及实际混合Core回归1项通过。材料SYNTHETIC、实际执行INTEGRATED；HTML fallback、PDF版本占位原值、media仅头信息、格式定位及独立重解析缺口保留。派生选区Marker仍unverified，知识Candidate未审定。

全格式/平台保真与重构往返、外部增量同步、正式非空用户旧库迁移（无exact来源授权NOT_RUN）、installed/Owner/M01/专业真值、cloud CI/release资格未获本阶段证明。ZIP10成员/CRC/内部9 SHA及107原记录归档映射已核验，原件源指令不提升权威。所有旧失败/不同源码epoch完整保留；未commit/push/merge/install/release，主根仍仅镜像资料治理，gov-ui为唯一产品writer。下一步UF13五日常旅程；活动goal未完成。


## 2026-10-10 当前停止交接：UF13 已启动切片

用户要求“完成当天跑的任务就停止任务”。本次已启动导航/工作台/门禁切片完成验证后停止；整体 **PARTIAL**，不是 UF13/全任务包完成。依据 [当前切片回执](receipts/AAOS-UI-FINAL-SLICE-20261010.json)，最终前端 **997/108 PASS**、TypeScript PASS、门禁脚本回归47 PASS、frontend build a188f9aecc96 PASS；源码前后及当前指纹一致。前两次前端失败、类型检查失败完整保留，已按新入口合同修正旧平铺断言、限定heading层级与CSV测试读取。新UI只获得SIMULATED自动行为证据；未运行新的浏览器/原生/安装/真实Core旅程。

五日常入口与固定全部能力/设置落地，原22页ID、hash、CAP186细项保留；全局命令明确查页面与能力。工作台接通实际Core本地文档标题/正文检索（20结果上限、真实ID、输入法/晚返回保护）；到期复习接受SQLite UTC及FSRS offset/微秒日期，跳转具体item_key仍走原草稿/恢复守护。日常欢迎横幅可收起，themes.css与theme.ts SHA等于上一阶段，原五配色未覆盖；场景对象仅App生命周期保持，不声称跨重启恢复。

门禁runner修正为dirty worktree检查、隔离compileall缓存及v2 schema扫描。来源/ZIP/教学/表达/研究/AI生成检查6 PASS；合同结构检查 **FAIL**（既有learning-kernel/review schema缺元字段），资源生成检查 **FAIL**（历史资格绑定core-contract.ts漂移）。这些失败及旧全仓conventions/architecture失败不隐藏，不改历史资格SHA；quick/full聚合门禁此切片NOT_EXECUTED。

107原字段与18设计主题审计保留；剩余跨重启草稿/筛选滚动恢复、冲突比较/权限变化恢复、真实最近现场/导入进度、研究收藏及安装/真人/长期资格没有完成。新建幂等候选仅保留在本地candidate-library，NOT_APPLIED，其隔离9测试不算产品通过。已启动子Agent均停止，不创建后续任务或自动后台继续；未commit/push/merge/install/release/删除。保留本阶段本地证据、精确字节备份及所有旧失败；恢复执行须用户新指令。


## 2026-10-10 新授权：仓库双端同步

用户已授权当前项目公开内容commit/push及不改写历史的本地收敛，见 [同步交付范围](AAOS-REPOSITORY-SYNC-20261010.md)。此前“未授予/未执行commit/push”的段落是旧时点记录；本次交付不恢复产品实施，不升级PARTIAL/FAIL或安装资格。云端和本地源码是否一致须读最终交付SHA，不从历史GitHub About回读推断。

## 2026-10-11 Owner 闭环恢复：首批可靠性增量（PARTIAL）

Owner 当前目标为完整核心框架、常见常用格式与最短闭环，恢复决定由活动指针指向 `AAOS-CLOSED-LOOP-OWNER-RESUME-20261011.json`。当前强制旅程改为 `tests/journey/tauri-common-format-owner-loop.yaml`；该文件是验收要求登记，不是完成证据。历史旅程及其结果保留各自身份。

本地已补原创创建固定请求/丢失响应回读、引用独立核验及正式桥接导航限制、能力启停确认与独立回读，并扩展已有 Core 内容政策探针检查创建重放、重启和独立备份恢复不产生重复文档。根工作树定向 UI 55 项通过；HTTP/探针 helper 19 项、合同/路由结构 30 项通过（后两组为 canonical runner `--noconftest` 的明确隔离范围，不是全仓门禁）。根前端 build 在 Vite 写 assets 时 EPERM，未以提权或 ACL 修改绕过。

分项状态及本地收据见 [闭环工程进度](receipts/AAOS-CLOSED-LOOP-ENGINEERING-20261011.json)。当前草稿跨重启、全局对象搜索、常见格式真实内容资格和同对象新 UI 全流程仍未验收；当前新增代码未获得 exact-SHA CI 或安装运行资格。主题不变；六项对话增量、V01、FT01–04 保持既有冻结/暂停状态。

同日继续：真实对象检索已接入命令面板，按搜索时的版本和正文 SHA 打开只读文档，避免卸载当前编辑草稿。根工作树五个 UI 测试文件 73 PASS；HTTP/资源结构 38 PASS。Core-owned typed 工作状态及有限宿主操作已接入源码：使用既有 workspace_meta，通过唯一 writer 保全独立草稿与冻结原创请求，workspace/restore epoch/revision CAS、人工权限、恢复候选显式处理和已保存草稿条件清除；生产 UI 持久化接线仍进行中，Native 测试未执行。

中文复合 DOCX/XLSX/PPTX/PDF 内容、结构、定位、独立新 job 重解析和重启探针已加入 desktop-fast。PDF locator 直接核验实际 pdf.extract 的 canonical page/global-line 和文本/结构输出指纹，不伪造 worker_structure/bbox/OCR。本地 15 项 parser/helper/build-contract 检查 PASS；当前完整框架及实际 Core 资格仍 PARTIAL。生成工作状态 DTO、语言边界、文档权威和当前 TypeScript 检查 PASS。

基线完整 CI `38069114525`（6c5fcc3）最终 FAIL：installer-lifecycle PASS，desktop-fast 84 PASS / 1 FAIL，测试 fixture 的 Windows accepted socket 继承非阻塞模式，read 返回 WouldBlock。已显式切为阻塞读取并保留原有超时；新源码复测待候选。当前本地 rustfmt 对指定项目文件返回 access denied，不提权或调整 ACL，不能宣称格式/Native PASS。

同日草稿正式 UI 接线继续：App-owned Core 工作状态 provider、初始读回身份闸、独立文档草稿、冻结原创请求、显式恢复候选、正文 ACK 后条件清理及独立 journal 重试已合入当前工作树。正式桌面宿主使用 Core journal；浏览器呈现夹具不获得 Native 持久化资格。服务读取/写入/清理/恢复先校验生成合同，无效回执不替换现场输入。定向 62 项通过后，全前端首次 1021 PASS / 8 FAIL、4 errors，发现旧恢复 fixture 回传无关 DTO，以及模板未登记工作状态接口。补全明确 fixture 并增加无效读回保护后，工作状态/恢复/模板/阅读 53 项 PASS、TypeScript PASS；首次失败原日志保留，最终全回归待收口。已知正文 ACK、journal 清理失败不回退正文版本，不重复写同正文。

候选 `7458281da0d24d07eb96e348bd16a145331aa78e` 完整 CI `38071837781` 最终 FAIL：rust-vnext 的 root cargo fmt、desktop-fast 的 Native cargo fmt，以及 desktop-build 全前端中的旧原创创建 fixture（1015 PASS / 1 FAIL）。Windows 桌面失败步骤尚未到 Native 测试；installer-lifecycle SKIPPED，不记 PASS。两份 CI 格式补丁按基线 blob/preimage、全部 11 个任务文件范围及 token 等价审查后已应用；UI 创建 fixture 使用实际请求派生 ID、完整 block DTO 及独立版本读回，保留身份校验。尚未提交新的修复候选；真实 Core 草稿重启、当前常用格式探针与同对象全旅程仍 NOT_QUALIFIED。

后续完整前端回归 `be268a2d33/9f6c48743688`：111 文件 / 1034 测试 PASS，采用最多 4 个 worker 保留原断言与超时；此前默认并发的文件批次与懒加载等待超时 FAIL 保留。挂载回归实测复现正文 ACK 后残留 debounce 二次正文写入，现取消计时器并用已确认内容防止重复写；独立草稿、新 Session 同请求创建恢复、仅 journal 重试及晚输入四项挂载回归 PASS（SIMULATED）。全回归之后只给该测试的 undefined narrowing 加明确 guard，定向 4 项再次 PASS；产品源码未因此改变。新测试纳入 TypeScript 检查。

扫描 PDF 的实际 OCR 前置资格原先只看旧 gitignored tools 路径，已对齐 CI/worker 声明的 TESSDATA_PREFIX，并核对 companion 和显式引擎文件。CI 或明确 OCR 声明下缺语言数据、失效引擎或 PDF 输入构造失败硬失败；普通未声明本地环境明确 NOT_EXECUTED。纯选择回归含 9 项断言；该 Rust 测试本地因依赖 build script 的 kernel32.lib 缺失 NOT_EXECUTED，当前实际 OCR 正文与定位资格仍不能升级。未改变主题或激活冻结范围。


## 2026-10-11 多格式及同对象 UI 接线续批（PARTIAL）

当前候选 `282fcf579e8696e5b3e74f19a3e821865e350db5` 的 desktop-fast 实际 Core/worker 回执已下载并核对 clean source：DOCX/XLSX/PPTX/文字 PDF 的选定中文复合样本、原件保全、定位独立复验、新作业重解析及重启通过；内容策略包含原创丢失 ACK 的客户端注入、固定请求重放唯一性、重启和独立备份恢复通过。材料是合成自有样本；未证明安装界面、原格式重建、中文扫描识别或全部媒体内容。完整 CI 仍有 Rust 格式和 browser-smoke 失败，不记全局 PASS。

续批合入 CSV 原生 facts 覆盖稳定单元格路径修复、真实 OCR line 来源/尝试/输出指纹核验、page16→page03→同源候选→手工审核、Tiptap 引用 position 序列化与点击/键盘实际节点定位。整合测试发现两个原件面板共享焦点 ref；按页面用途修复后相关41项 PASS。26项实际本地 parser/helper 回归、TypeScript 与 canonical frontend build PASS。新真实 journal/recovery、common-light/OCR 探针已接 CI，但新增 Core locator 尚未获当前编译和实际执行资格。分项收据见 [续批证据](receipts/AAOS-CLOSED-LOOP-CONTINUATION-20261011.json)。学习/练习切页同对象身份仍在独立工作树修复；完整九步、实际 ASR、安装态及 Owner 验收未完成。所有旧失败及历史源码证据保留；主题、冻结范围和 no-release 边界不变。

同对象学习接线已统一合入：accepted知识→course/lesson→assessment→page11练习→page12复习保留原身份与独立答案，错对象拒绝。最终整合前端113文件/1043项、TypeScript及production build PASS（SIMULATED）。当前282候选完整CI为FAIL，desktop-build及desktop-fast PASS；安装WebDriver失败截图显示恢复确认门禁正确生效，旧probe缺明确选择。现已改为实际UI保留候选，再核对相同workspace/restore_epoch、revision+1、候选精确保全；17项Native helper含5项正反回归通过，实际安装复验仍待新候选。

本地canonical浏览器probe启动Vite后readiness超时；独立owned-loopback实验证实WinError10013套接字权限拒绝，未提权/改ACL/网络配置。曾尝试的局部proxy调整与实验代码已撤回，失败证据保留。已声明本地Whisper模型存在，但offline SAPI生成入口被AuthorizationManager拒绝；缺明确项目内spoken WAV+文字稿，实际ASR NOT_EXECUTED。当前询问Owner素材路径，其他闭环继续推进。

同日受控 AI 同对象接线已合入主树：page13→14 人工纠错/审核→13 独立复测授权→14 复测→22 精确任务回执，原问题、知识和纠正候选身份保留。候选准备仅读取当前已接受知识，不自动授权；每次消费仍由 Core 核对明确的 grant snapshot。AI 页组内保持同一挂载旅程，离开页组或重启仍需按现有 Core 历史显式恢复，不新增业务持久库。最终前端114文件/1050项、TypeScript与production build PASS，源码指纹一致；证据为 SIMULATED，真实推理、当前安装态九步及 Owner 验收保持 NOT_QUALIFIED。详见[受控AI整合回执](receipts/AAOS-CONTROLLED-AI-JOURNEY-INTEGRATION-20261011.json)。首次 bundled Python 缺 PyYAML、随后 GBK 控制台编码失败的尝试保留，最终使用项目已登记环境与 -X utf8 验证，无安装或权限绕过。主题及冻结范围不变，新候选待上传和 exact-SHA CI。

候选 `93baf3934e73949ef6e2627bb01721f928990704` 已正常上传 Audit 并由 GitHub API 独立核对 SHA。完整 CI `38075889002` 已终止 FAIL：lint 发现新语音探针写死 SystemRoot fallback 和 ffmpeg 本机路径，其他必需检查因依赖跳过，不记 PASS。已改为 SystemRoot 环境声明及项目 tool_paths.declared_location('ffmpeg')，保留缺失时拒绝，未放宽架构门禁。当前本地 architecture guard PASS；语音探针 helper 9 PASS、实际 ASR 3 NOT_EXECUTED（回执 be268a2d33/1bd323953127），无 SAPI 重试或新素材读取。修复候选仍需重新完整 CI，整体继续 PARTIAL。
