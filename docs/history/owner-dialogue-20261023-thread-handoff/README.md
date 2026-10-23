# AAOS 本线程完整交接提示词与证据导航（2026-10-23）

可将本文件全文交给新对话，或粘贴下文提示词并要求完整读取本文件。本文件是换会话时的固定快照与导航，不是第二份持续更新的执行记录。实际进度唯一写入 `docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md`。

覆盖本线程可见用户请求、项目内已登记决定、已落地修改与实测回执；没有读取、复制或上传私人 Codex native sessions，也不将摘要伪称逐字原始对话。更早聊天“接手AAOS全链路执行”的完整原始内容未在本次交接重新逐字核验，沿已登记索引追溯，未知项须保留 UNKNOWN。

## 一、直接交给新对话的完整提示词

你现在接手 ArcheAxis-Knowledge-OS（AAOS / 星环知识系统 ArcheAxis Knowledge）。工作区固定为 `D:\All projects\ArcheAxis-Knowledge-OS`。请完整读取本交接及所指权威和证据，在真实源码与工作树基础上接续，不重新立项，不把历史报告、旧 COMPLETE、旧权限拒绝或模拟通过当作当前事实。

### 1. Owner 最新决定：人类与 AI 双侧闭环，不能只做一侧

Owner 在交接整理时先纠正：**“人类侧不冻结，还是按照闭环执行”**，随后进一步明确：**“最新讨论的都是人类侧 闭环应该还要包括AI侧啊”**。

这是最新执行范围：继续完整框架、常用多格式、人类知识与学习闭环、AI 知识与学习闭环，以及两侧有证据、按权限的知识复用。不是只恢复人类侧，也不是只停留在 AI 适配合同。

- **人类侧**：抓取／上传及批量资料 → 原件保全 → 解析／OCR／转写与位置 → 阅读编辑 → 百科／社区／科研检索与对比分析 → 候选与人工知识接纳 → 特色展示、课程／练习／学习／复习 → 重启续用、导出、备份恢复。
- **AI 侧**：外部或既有业务的脱敏经验候选及证据 → 有限授权接收 → 验证、身份去重、相似与冲突审查、适用性及必要审批 → 已批准 AI 知识／经验资产 → 按任务权限检索、引用并使用 → 发现错误、纠正、复测、修订与撤回 → 重启后保持知识、证据及版本关系。
- **双侧连接**：同一知识、来源与版本可以在授权范围服务人的学习和 AI 使用；人的纠正可进入 AI 候选审查，AI 的输出也只是有来源、有状态、可审查的候选，不能自动当成人已掌握或权威事实。不整库灌入、不绕过人工晋升、不另建业务真值。

双侧闭环是 Owner 对既有 Human–AI Co-Learning 的明确验收要求，映射原 CL-01—07/J1—6 和原任务 ID，不另建 Runtime、任务包、业务数据库或并行进度账本。现有学习／纠正／复测的 API 测试通过不等于上述完整业务链已真实跑通。

原任务书 `D:\All projects\Record\AAOS_AI_Context_Separation_Codex_Task_20261023.md` 中“只改 AI、人类侧冻结”，约束的是已经实施的那次 AI 上下文专项单元：该单元确实未修改人类侧，应保留这一历史事实。**它不再是后续项目开发的全面禁令。** 最新 Owner 决定覆盖该禁止后续推进人类侧的解释；AI 原始上下文外置的职责决定继续有效。不得改写原任务书或旧回执来伪造历史。

### 2. 产品定位与本期边界

AAOS 是本地优先、证据驱动、Human–AI 双向知识与学习产品，不是所有项目／软件的总控系统。尽快交付可以实际使用的有限首版，同时保留持续迭代能力。

本期抓住：完整共享核心 + 常规常用 PDF／Office／文档／图片／音视频等多格式 + 既有研究比较 + 已选个人知识库特色展示和学习 + 本地／用户自行绑定的云端模型路径 + 人类与 AI 双侧闭环 + 同候选重启／导出／恢复。常用格式与特色按现行清单逐项核真实支持、方向、损失和延期，不能默默删除原承诺。

不要以全面兼容长期蓝图或库存清零为首版前提。可选开源池、更多具名软件特色、第三方 API 追加接入、插件／技能／模板／MCP 扩展留后期内置市场。当前只沿已有合同保留专业、可替换接口，不开发通用市场、支付、第二 Runtime 或所有扩展包。已验证且属于本期的能力保留，未知和未来图标不冒充可用。

六项冻结增量、V01、FT01—04及其他未选长期能力，不因“人类侧不冻结”或“双侧闭环”自动解冻。企业管理、多租户、企业部署不进入本期。PSD／Illustrator AI／CDR／CAD／3D 专业源格式直接编辑与往返不属于常用格式承诺，可经导出图片／PDF使用；长期空间能力仍保留。

### 3. AI 原始上下文与 AAOS 知识的边界

跨任意项目、Agent、软件、会话的原始聊天、运行状态、日志、工具轨迹、代码演进与接续记忆，归独立 `EXTERNAL_CONTEXT_PROVIDER`。范围不限现有三个项目。AAOS 不采集、同步或保存整份私人会话，不成为中央长期运行记忆。

AAOS 接收的只是最小、脱敏、可追溯、待治理的知识候选：错误模式、根因、无效尝试、有效修复、正确方向、技术规范、适用与禁用条件、验证证据。保留有限当前文档问答上下文、RAG、模型请求状态、AI 知识检索、人机双向学习、纠正与复测；不能借“外置上下文”删除业务必需状态。

尚未授权选择或部署 OpenViking、Hy-Memory／MemHub 等供应商，也没有真实外部系统连接。当前必须写 **NOT_CONNECTED**。离线候选接收和隔离测试不是跨软件同步。外部部署、私人会话读取、跨仓连接、全局配置、付费调用均不由双侧闭环目标自动授权。

### 4. 前端唯一方向：现有 Stitch + 能力启动台

Owner 多次明确不要再维护旧版界面，全面接入 Stitch。正式前端仍是现有 React/Tauri，不重做系统桌面、不接管 Windows 任务栏、不引入第二套 UI。22 页已沿收到的设计语言改排源码；原设计只有 5 个专用页面，其余沿设计语言承接原业务，不能声称未见稿逐像素还原。

在现有 Stitch 中增加可搜索、分类的能力启动台菜单窗：点击图标进入既有能力视图，保护草稿和对象身份，重复打开复用已有状态。Dock 收敛为工作台／知识／学习／研究／全部能力／小栖六入口。待配置、缺依赖、未接入、冻结／规划中分别显示；未来图标不能触发未授权安装或假执行。

Owner 否定生成图的大号彩色发光图标。当前锁定 `lucide-react@1.61.0`，沿统一 SVG 与许可登记；保留现有 Radix 控件。要求真正背景透出和 backdrop blur，不能用纯色卡片或 CSS 中出现 blur 就宣称视觉达标。已有 cosmic 外窗／卡片／标题栏 62%／28%／20%，主窗20px、启动台24px backdrop blur；这些只是当前实现参数，最终以实际原生渲染和 Owner 验收为准。其他主题、减少透明、高对比和性能仍需对应证据。

小栖／贾维斯材料是设计与能力规划来源，不等于自动恢复语音／唤醒／系统控制等冻结项。必要时可沿已授权范围只读参考 Stitch，未生成、未覆盖原稿就不能写已生成。

### 5. 必须先读的当前权威

所有下列相对路径均相对于 `D:\All projects\ArcheAxis-Knowledge-OS`：

1. `AGENTS.md`、`AUTHORITY.md`、`PROJECT_CONTRACT.yaml`。
2. `docs/current/AAOS-ACTIVE-EXECUTION.json`，优先最新 `owner_scope_current`、`execution_control` 和 `ai_context_separation`；旧 dated state 不是最新授权。
3. `docs/truth/CLOSED_LOOP_DEFINITION.md`，唯一闭环定义 `AAOS-SHORTEST-COMPLETE-LOOP-V2`，含本期收敛与双侧要求。
4. `docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md` 第十八至二十二节及 `DECISION_SUPERSESSION_LEDGER.yaml`。
5. `docs/current/AAOS-AI-CONTEXT-BOUNDARY-20261023.md`：AI 专项的实际影响面、合同、限制与回滚。
6. `docs/current/AAOS-AUTHORITY-ROUTES.json`、`docs/DOCUMENTATION_AUTHORITY_INDEX.md`。
7. `docs/current/AAOS-AGENT-HANDOFF-CURRENT.md` 顶部最新接续和本文件；下方同日旧阻塞／暂停只按历史理解。
8. `docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md`，唯一实施记录，读末段及所指原始回执。
9. 当前冻结规划包 `docs/taskpacks/aaos-ui-first-20261009/` 的 TASKPACK／TASKS／PAGE-PLAN／FREEZE-REGISTER，以及现行 UI-P／BE-P 分片覆盖。冻结包的 NOT_EXECUTED 是规划快照，不回填。
10. 查原材料先查 `AAOS-资料索引.md`、`docs/history/record-archive-20261009/INDEX.md` 及 MANIFEST，再按登记 exact path 找来源，不能盲扫磁盘／Home。

正式宿主 `frontend/` + `src-tauri/`，Rust Core 是唯一 SQLite/CAS 业务 writer，Python workers 隔离。`desktop/` 有被正式宿主复用的生命周期代码，不能一概当无用旧代码删除；Avalonia 旧宿主与历史 `app/` 路线按权威识别供体身份。

### 6. 现场快照与保护要求

本次交接开始实测：branch `codex/sync-20261019`，HEAD `95b463c12dbd40744b43039add69c48ceaeba94e`，origin fetch/push `git@github.com:DTALEX66/ArcheAxis-Knowledge-OS.git`。交接前 `git status --short` 共54条，暂存区为空。交接本身又修改当前导航／权威并新增本文件，最终清单以同目录 MANIFEST 和本地收尾状态为准。

这批是 dirty 工作树成果，不能仅用 HEAD 认定测试源码。交接本轮未 commit／push／触发 CI／merge／release／安装／替换 Green，远端 exact SHA **UNVERIFIED**，不能宣称双端一致。历史曾推送的 `d388801b...` 是另一时点，不能覆盖当前状态。

之前 Python uv 子进程 os error5、Git 只读曾真实阻塞三个目标回合；Owner 切换完全访问后已恢复：canonical Python3.13.14及其子进程 PASS，正式 Git 临时引用 create/read/delete PASS，HEAD／branch／staging 保持。直接 `.git` 文件探针曾在执行前被策略拒绝，保留该失败，但不能继续说当前 Git 只读。之后 Rust/API/前端本地测试确实执行。新对话仍须核当前权限，不通过改 ACL、换账户／解释器或全局配置绕过。

写入前核 `git status --short`，保护全部既有修改；一个 checkout 同时单 writer，独立 writer 才用隔离 worktree。并行需遵循当时平台规则，不把历史“并行”当无限 Agent 启动授权。不得 reset --hard／clean／批量 restore／force push／混入无关文件。

### 7. 已落地内容与证据边界

**Stitch 与启动台**：新增启动台组件／样式／回归，收敛 Dock、导航与图标，复用业务和草稿保护；修复业务窗因 inline containment 与 auto margin 导致零宽。实际前端浏览器见到窗口与图标、无横向溢出、菜单／搜索／Esc焦点有效，但当时未接 Core；浏览器截图不是原生／安装／Owner视觉通过。证据索引见第二节表。

**阅读工具消费者修复**：原生分组探针查旧 `.ui-reader-page`，遗漏新版“整理关联来源”折叠区而点击隐藏按钮。已按当前语义 region／summary 展开，并保留真实滚轮及命中检查；菜单、Dock 和浏览器矩阵同步 Stitch。组件21项、tsc及所选 Ruff 语法规则通过。完整 Python、新候选原生分组链未重验，原 REAL FAIL 保留。

**材料问答预算与诊断**：原 REAL 4B 调用已获得响应但 `finish_reason=length`，仅 reasoning，无最终答案；input491/output2048/total2539，75.61秒。原保存配置也是2048，不能把此失败归因于后来发现的 UI 裁剪。另修复前端将已保存较大预算压到2048的问题，预览／确认冻结相同请求，执行／状态／历史提供受限诊断，不把 reasoning 当答案、不改用户配置、不自动重试。最终47项及tsc通过，未重跑真实模型，不能声称原失败消失或提高预算必定解决。

**云生产缺口**：源码 `model_configuration::validate` 只接受数值 loopback HTTP；`material_cloud.py` 生产 preflight／execute 仍 NOT_ACTIVATED。产品 Windows Credential Manager/Vault 有有限适配，不代表 Vault→Core→worker→真实云调用已打通。此为生产实现缺口，不能只写“等用户给key”。最终产品由用户自行绑定订阅/API，不能借本线程 Codex 凭据或要求聊天贴密钥。历史“必要时用GPT订阅节省token”不是隐式凭据借用或付费调用授权。

**AI 外部候选边界**：新增 Domain/API 的 `external_context.rs` 和两份集成测试；两个 `lib.rs` 只追加模块／路由。严格 DTO、显式 Admission、任意合法项目 namespace、限长、同身份幂等／冲突拒绝、受限读回，复用现有 Document/AiAsset candidate；没有建表、SQL迁移、第二 writer 或 transport。GET `/api/v1/machine/external-context/status` 是 NOT_CONNECTED，不是远端探测。POST `/api/v1/machine/external-context/candidates` 仅既有认证 human actor，显式材料授权＋脱敏确认，machine403；不是远端 provider 自助授予权限的入口。

候选外部 PASS 不自动可信，统一 `UNVERIFIED_EXTERNAL`／candidate；无新增自动证据核验器或语义去重引擎。状态 offline／timeout／revoked／missing／deleted／unknown 由可信调用方提供观察，不代表当前已真实出网或远程撤权订阅。脱敏确认不是全自动DLP。AI专项前后640个受保护现有源码哈希相同，是该专项未改人类侧的证据，不等于本线程从未改过前端，也不冻结下一轮双侧实现。

### 8. 最新 AI 专项测试，必须按原始证据解释

最终不重叠批次：Domain31、AI及共用API45、人类业务API23、前端67，均 exit0。本地真实 Rust Router/Store/SQLite 与组件运行，输入为 SYNTHETIC，**不是外部 provider REAL 接通，也不是当前提交 exact-SHA CI**。初次 API 编译 E0308（Store::open 参数少借用）exit101 已修复并重验，失败日志保留。更早30项 Domain 是重叠批次，不重复累加。

原始命令、日志SHA、源码文件SHA、patchSHA、退出码见 `docs/history/project-drift-audit-20261021/ai-context-separation-20261023.json`。canonical wrapper 为 `.venv/Scripts/python.exe scripts/runtime/dev.py --run-id <run> -- <command>`，下列为真实子命令的换行展示；如重跑必须用新 run-id，不覆盖原证据：

```text
# ai-context-separation-domain-final，31 PASS，exit0
scripts/ci/cargo_test.bat test -p archeaxis-domain --offline --locked --test external_context_candidates --test ai_assets --test context_grants --test machine_loop_restart --test learning_schedule_authority --test learning_state_persistence

# ai-context-separation-api-02，45 PASS，exit0
scripts/ci/cargo_test.bat test -p archeaxis-api --offline --locked --test external_context_api --test ai_assets_api --test context_grant_api --test learning_schedule_api --test learning_state_api --test contract_machine_correction --test contract_machine_retest --test source_bound_knowledge_api

# ai-context-separation-human-api，23 PASS，exit0
scripts/ci/cargo_test.bat test -p archeaxis-api --offline --locked --test document_draft_loop --test contract_general_course --test format_location_anchor_api --test research_state_api

# ai-context-separation-frontend，67 PASS，exit0
node frontend/node_modules/vitest/vitest.mjs run --root frontend src/__tests__/MaterialQuestionPanel.test.tsx src/__tests__/DocumentEditor.test.tsx src/__tests__/KnowledgeCoursePanel.test.tsx src/__tests__/CanonicalResearchPublic.test.tsx
```

原始 stdout/stderr 由 canonical dev.py 合并保存，不能冒称两条独立流。日志在 `.project-local/runs/be268a2d33/<run>/logs/execution.log`，执行回执在同 run 的 `artifacts/execution.json`。本地 ignored 证据未上传，跨机器接手须明确其可用性，不能伪称云端也有。

### 9. 必须保留的失败和资格缺口

1. 原生阅读工具不可达 REAL FAIL：探针已修但当前原生链尚未重验。
2. 本地模型 `material_no_final_answer` REAL FAIL：预算恢复修复仅定向测试，没有真实新答案。
3. 云端材料生产路径未实现、真实调用未验，不是仅缺账户设置。
4. 外部上下文 provider NOT_CONNECTED：未部署、未跨软件同步。AI完整“候选→治理→使用→纠正复测→重启”未由接收测试证明。
5. 当前 dirty 源码正式全套构建／同候选Core业务／原生／安装／J1—6与CL01—07／Owner视觉及使用验收尚未全通过。旧构建不能资格化后继改动。
6. PDF/Office等有历史局部 Core 证据，但常用格式完整往返、扫描OCR、中文ASR、视频内容转写／时间定位仍须当前样本资格。媒体头信息不是内容识别完成。
7. 旧167场景浏览器子报告PASS，但外层 run 因另一探针文件变化为INVALIDATED，不能把全run写PASS。
8. 当前批次未提交上传、远端 exactSHA与CI未核。测试、push、merge、release、已安装运行、Owner接受各自独立。

### 10. 下一步：按双侧主线补缺口，避免重新发散

接手先完成现场核对与小结，再在已授权有限首版内继续；当前这次交接只整理文件，没有启动后继产品任务。不要反复让 Owner 为普通实现细节确认，也不凭“继续闭环”擅自外发材料或付费调用。

建议依赖顺序：

1. 核权威最新覆盖、Git dirty清单和源码hash、canonical工具与必要服务；识别既有自有／共享进程，不盲杀。把已选本期人类与AI能力、共用对象和阻断点对到原任务ID与CL/J，补具名延期；不重盘所有库存、不写新大规划。
2. 对当前变化运行必要canonical build与定向回归，资格化同一候选。不要原封重复先前已通过的无变化大套件。
3. 修复并真实复验人类资料→阅读定位→研究比较→知识→学习→重启导出恢复，以及原生来源工具消费者；保留草稿、错误、离线、失败与对象版本。
4. 同时纳入AI业务闭环：在现有知识体系验证候选审查／冲突／批准或拒绝／权限检索使用／纠正复测／新旧版本与反例／重启恢复；所需现行合同和实际消费端先核源码，缺失处做最小实现，不凭测试名宣称已通。双侧交互核同来源、同版本、授权范围和知识状态，不强迫普通笔记先审批。
5. 本地最终答案与产品自有云端路径分别处理。先完成无模型成本的生产接线与取消／失败保护；真实云端仍需适当材料／渠道／费用授权，缺授权准确报缺口，不用模拟顶替。不能无限重试失败模型，也不能自行改provider／模型／endpoint／全局配置。
6. 在同候选完成有限格式与特色、原生／隔离安装、备份恢复、可靠性和Owner验收；尚未完成的分别报PARTIAL／NOT_EXECUTED。Green精确路径虽有历史条件授权，必须先读当前 `green_update_authorization` 和资格条件，本次交接及双侧决定不自动触发覆盖。
7. 公共成果交付沿已有 Task Grant、明确白名单和实际权限处理：保护未知修改、显式stage、禁止force，提交推送后才核双端精确SHA；merge／release独立。当前交接未做这些动作，不能代填成功。

### 11. 监控、权限和数据边界

`aaos`额度heartbeat最新已登记状态PAUSED，曾每30分钟检查。历史规则：正式订阅任一可读窗口剩余≤20%时，完成已启动可验证单元、收回自有进程，停止后继开发，整理交接并按授权上传公开文件、核SHA，然后暂停；null/missing为UNKNOWN，credits不代替订阅百分比。**本次不恢复监控、不查询额度，不能因额度重置自动恢复。** 人类侧继续与双侧闭环不等于恢复monitor。

默认只在本项目写入；日志、缓存、运行库、临时产物用已忽略 `.project-local/`。不读写无关项目、不扫描私人sessions、.env、密钥、Cookie、native memory、浏览器认证、不借Codex凭据、不改全局模型配置/ACL/PATH/注册表。E:/F:没有当前exact path+operation授权不得进入。WORK-LAB／DESIGN-LAB不属本次开发，不合仓、不共享DB。安装、部署、后台监听和大模型下载不能由接口规划自动授权。

### 12. 精确回滚与汇报

AI专项：`.project-local/artifacts/ai-context-separation-20261023/` 保存before、task-only.patch、rollback-manifest.json和rollback.py。原只读检查曾 `ROLLBACK_CHECK_OK 16`，只影响专项16文件，保留其他脏改动与候选数据。**本次交接后来又改了其中的权威／导航文件，旧脚本哈希保护预期会拒绝直接apply。** 不更新旧manifest掩盖后继修改，不盲跑--apply；应人工合并AI反向增量并保留最新双侧决定和交接。新建四份Rust文件可按实际依赖移除，两个lib.rs只撤专项新增模块／路由；不删库、不reset／clean。

本次纯交接修改前副本及前后hash在 `.project-local/artifacts/thread-handoff-20261023/`，仅用于回退本次文档增量，不覆盖后继更新。该目录ignored，未随Git上传。

每个回报须列：实际改动和目的、精确文件、真实命令/退出码/日志、源码身份、证据级别、未执行及缺口、下一步、回滚。分别报告人类链、AI链、双侧连接和全产品资格；不得用测试总数、菜单图标、文档归档代替业务闭环。

## 二、证据与修改文件的完整导航

### A. 本线程阶段与替代关系

| 阶段／用户关注 | 现行解释与来源 |
| --- | --- |
| 接手“接手AAOS全链路执行”、审计漂移、前后端并行 | 当前权威、分片和唯一执行记录；私人旧会话未在交接阶段重新扫描。 |
| 一再要求全面Stitch，质感不符与难看图标 | 唯一新UI；启动台与业务复用；概念图只作布局、图标明确被否定。 |
| 新增功能不断、开源池/API/兼容为何扩张 | 决定十八、十九，SUP-026：有限首版与后期市场；库存不等于执行队列。 |
| 配额监控、≤20%收尾上传双端一致 | 历史规则保留；最新monitor暂停，不把旧ACTIVE heartbeat当当前自动授权。 |
| “完成本次后暂停”与后继“继续／解决／闭环” | 暂停是历史时点；权限已恢复，最新有限双侧主线可接续，monitor仍暂停。 |
| 桌面系统感、Dock＋中间能力菜单窗 | 在现有Stitch加启动台，不接管Windows、不重做所有页面，不先造插件Runtime。 |
| 核心也能收敛、特色展示／学习、多格式快交付 | 共享核心不拆真值；专用引擎视图逐步模块化，保留既有有限特色并具名延期。 |
| 贾维斯／小栖三文档、两张图、历史两蓝图 | 已有owner-dialogue-20261022-desktop-launcher归档，5文档＋2图本地保全；建议与用户决定分开。 |
| Python/Git连续阻塞及用户切换完全访问 | 权限恢复检查点覆盖旧阻塞结论，失败原件保留，不把权限PASS当产品PASS。 |
| 云端由最终用户自行绑定，必要可GPT订阅省token | 产品要求保留；当前云生产实现缺口，不能借Codex凭据、隐式付费或伪造云验收。 |
| AI外部上下文任务书 | 已完成最小候选边界及本地回归，外部仍未连接；旧专项禁止人类改动是该单元边界。 |
| 最后纠正“人类不冻结”“闭环也包括AI” | 当前最高范围为人类＋AI＋双侧连接；SUP-028、决定二十二、活动指针owner_scope_current。 |
| 当前“整理全部、完整交接” | 只整理权威导航／快照，不在整理回合顺带开发、模型、安装或上传。 |

### B. 检查点、原失败及截图

检查点统一位于 `docs/history/project-drift-audit-20261021/`：

| 文件 | 证明范围／限制 |
| --- | --- |
| `stitch-ui-local-checkpoint-20261022.json` | 22页源码与局部组件／模拟浏览器；不是同候选全业务原生。 |
| `stitch-visual-pause-20261022.json` | 当时正式构建与局部Core、原生FAIL、暂停；不能资格化后继dirty源码。 |
| `stitch-launchpad-checkpoint-20261022.json` | 启动台／图标／材质、36定向组件、窄屏前端；当时build权限失败。 |
| `stitch-glass-correction-20261022.json` | 零宽修复与透明材质、10组件和桌面前端读数。 |
| `stitch-reader-probe-repair-20261022.json` | 来源折叠工具probe续修、21组件与导航；原生未重验。 |
| `stitch-material-review-20261023.json` | 图标语义、10组件、全新桌面标签截图；无Core、无Owner视觉资格。 |
| `material-budget-recovery-20261023.json` | 原真实模型失败、预算恢复与47定向回归；无真实模型重验。 |
| `cloud-execution-blocker-20261023.json` | 云生产源码缺口与当时权限阻塞，权限部分已由后继覆盖。 |
| `execution-permission-recovery-20261023.json` | Python与正式Git临时ref恢复，非产品资格。 |
| `ai-context-separation-20261023.json` | AI候选边界源码／原始命令日志hash／31+45+23+67回归及限制。 |

关键本地实物：

- 原生FAIL：`.project-local/runs/be268a2d33/webdriver-65b88076c711/tmp/journey/receipt.json`；SHA256 `d294a860a0f946b5b6dff33ba6863cc148d9c1fb7a9e569819abbaf31e708096`。
- 本地模型FAIL：`.project-local/runs/be268a2d33/stitch-j4-local-material-02/artifacts/local-material-model-runtime.json`；SHA256 `001cbd02e5fac88b9f39becb14d72aea3cfbb520c2a2a689e347b725346b909c`；候选 `stitch-closure-portable-02`。
- 当前材质截图：`.project-local/artifacts/stitch-material-review-20261023/workbench-fresh-tab.png`、`launchpad-fresh-tab.png` 与 `readback.json`。旧标签resize模糊截图也保留，不当新截图PASS。
- AI专项代码patch身份、六份源码hash及各日志hash以AI检查点为准；不能只拿HEAD证明未提交源码。
- Stitch只读参考已登记project `10243059433218383839`／screen `206611daf7a948edb97ea60c7a7d8654`，设计接收不等于当前原生实现验收。

### C. 已改代码按工作单元列出

**UI／预算／probe既有修改**：

```text
frontend/package.json
frontend/package-lock.json
frontend/src/app/App.tsx
frontend/src/components/AaosIcon.tsx
frontend/src/components/StitchWorkspaceChrome.tsx
frontend/src/components/StitchWorkspaceChrome.css
frontend/src/components/StitchLaunchpad.tsx                  (新增)
frontend/src/components/StitchLaunchpad.css                  (新增)
frontend/src/components/lucide-NOTICE.txt                    (新增)
frontend/src/components/MaterialQuestionPanel.tsx
frontend/src/api/machineFailure.ts
frontend/src/__tests__/AppDockNavigation.test.tsx
frontend/src/__tests__/AppSceneNavigationGuard.test.tsx
frontend/src/__tests__/MachineFailureDiagnostics.test.ts
frontend/src/__tests__/MaterialQuestionPanel.test.tsx
frontend/src/__tests__/SourceCandidateJourney.test.tsx
frontend/src/__tests__/StitchLaunchpad.test.tsx               (新增)
scripts/probes/aaos01_grouped_owner_loop.py
scripts/probes/stitch_ui_browser.py
tests/test_grouped_native_owner_probe.py
```

**AI专项六份源码／测试**：

```text
crates/archeaxis-domain/src/lib.rs
crates/archeaxis-domain/src/external_context.rs              (新增)
crates/archeaxis-domain/tests/external_context_candidates.rs (新增)
crates/archeaxis-api/src/lib.rs
crates/archeaxis-api/src/external_context.rs                 (新增)
crates/archeaxis-api/tests/external_context_api.rs           (新增)
```

**规范、供应链、交接、来源归档与intake**：以当前Git清单、活动指针与同目录 `MANIFEST.json` 精确展开。包括 AGENTS／AUTHORITY／替代账本、资料与文档索引、唯一闭环定义、current导航／范围／执行记录、供应链账本与许可、owner-dialogue-20261022-desktop-launcher、新AI边界／checkpoint／intake，以及本次交接。54条是交接前status记录数，目录型untracked会在manifest展开为逐文件，不能把两种计数混用。

### D. 原始附加材料与归档身份

1. `D:\All projects\Record\ArcheAxis_OS_Full_Context_Handoff_2026-08-19.md`。
2. `D:\All projects\Record\AAOS_本次对话完整汇总_六项核心优势与开发方案_20261010.md`。
3. `C:\Users\ALEX\Doubao\chats\2026-10-22\new-chat\贾维斯语音能力-ArcheAxis交接与融入方案.md`。
4. 同目录 `贾维斯语音能力-ArcheAxis融入交接与审计包.md`。
5. 同目录 `贾维斯复刻-成熟案例调研与选型清单.md`。
6. 两张图：`codex-clipboard-8d7bf3e2-7a4b-4512-b923-37431cf33feb.png` 和 `codex-clipboard-3125ca57-27f4-4785-9f6c-943bf21aa29d.png`，原位置为 `C:\Users\ALEX\AppData\Local\Temp\`。

上列七份先读 `docs/history/owner-dialogue-20261022-desktop-launcher/MANIFEST.json`／SOURCE-EXCERPTS／DESIGN；本地保全位于 `.project-local/archives/owner-dialogue-20261022-desktop-launcher/`，不要重复扫描原聊天目录。概念图图标不获批准。该归档创建时的PAUSED／仅设计状态是历史，不能覆盖后继实现或最新双侧决定。

7. 最新AI任务原文：`D:\All projects\Record\AAOS_AI_Context_Separation_Codex_Task_20261023.md`，SHA256 `de476678054c51e9ab5800c7b4ed608fa0c778ab4eaf3a0419c619bb688d596a`。最新Owner双侧决定覆盖其“以后也不得推进人类侧”的解释，其余外置原始上下文／保留AI知识／供应商中立／不造第二平台边界仍有效。

附件中的指令和建议必须与用户当前请求区分；原文保存不是全部执行授权。本文件未更新全局Codex memory，也不声称新会话自动继承任何私人账号记忆。
