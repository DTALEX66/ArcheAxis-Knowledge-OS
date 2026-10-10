# 可直接复制给 AAOS 本地 Agent / 新会话的执行交接

你接手 ArcheAxis Knowledge（星环知识平台）“UI优先的后续实施”。请先接手并实际完成首批切片，随后给出证据和交接。本交接只在被用户复制给你并用于开启执行任务后授权其本地代码切片；上一个整理会话没有实施任何新 UI，也没有授权远程发布。

当前产品决定：本地优先、人类学习主体验、独立使用。正式栈 Tauri2 + React/TypeScript/Vite，Rust Core是SQLite/CAS唯一writer，Python workers隔离。普通笔记/草稿/Document/Block 无需依据、网络、额度、云复核或人审前置即可保存。识别忠实度与专业依据分开；身份、来源、忠实度、依据、采用、掌握、AI资格、执行是独立状态。不得造第二DB/编辑器/通用Agent OS，不强制AAOS依赖WORK-LAB或DESIGN-LAB。

## 现场与保护

主目录 `D:\All projects\ArcheAxis-Knowledge-OS` 是资料归档和本规划持久入口；本次读回 `codex/Audit` / `1a981a4482b01f31989074e79c82a63400aa07a7`。其AGENTS §6仍旧R6/Avalonia，不能据此恢复正式Avalonia实施。已有未知未跟踪 `crates/archeaxis-api/tests/contract_capability_registry.rs` 不属于本规划，保留。

代码接手优先检查 `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\gov-ui-20261008`。本次读回 `codex/aaos-gov-ui-20261008` / `fc5d4adc7acc28e38c2e6046ef06c0be2eed721d`，有大量未提交UI/前后端/CI与治理修改。该目录AGENTS/Authority指向10/04 AAOS01 Q规范、SUP-022 Tauri正式栈；有独立live ledger。下一会话必须重新读HEAD/status/Authority/合同，不把本提示旧快照当当前。SOURCE-REGISTER.json登记所读文件SHA与dirty摘要。Qoder/Codex正在写哪些文件UNKNOWN，先确认唯一writer；无冲突则继续，冲突就隔离且完整保全dirty，不从HEAD新建worktree后假定包含全部修改。不reset/clean/批量restore/stash/覆盖，不blind cherry-pick独立OSS/UI分支，不终止共享进程。

先读选定目录的AGENTS.md、AUTHORITY.md、LESSONS_LEARNED.md、PROJECT_CONTRACT.yaml、两个Authority索引、`docs/authority/taskpack-1004-aaos01/01_完整执行任务书.md`与当前Q00–Q15台账有效条款，再读 `D:\All projects\ArcheAxis-Knowledge-OS\docs\taskpacks\aaos-ui-first-20261009\TASKPACK.md`、TASKS.json、PAGE-PLAN.csv、COMPARISON.md。这里的UF/CB等只是拆解ID，不新造CAP/Q/F/SUP，也不把新ZIP自动升为Authority。最小纠正当前入口后马上做UI，不先做整仓元治理。

## 首批范围与完成标准

执行顺序：先完成首批 `UF00, UF01, UF02, UF03, CB01, UF04, UF06` 并提交首批证据；随后推进本提示明确纳入的 `S01.A、S01.B、S01.C` 三项清理闭环。按本地可逆操作范围继续，不自动执行未授权的大量删除、工作树退役或迁移；不可逆动作先准备精确可审清单。其他全包实现另分批，V01仍暂停，FT未来重型任务不自动启动。

1. UF00：保护现场、确定唯一writer，把22语义页面与现有route/对象/Core合同对上。22参考路由不是必须新建22生产路由。只纠正影响本批的当前入口，冻结旧执行顺序不删原文。
2. UF01：以新22页原型/截图/token/资产为视觉输入，做真实React Shell、分组导航、公共搜索、窄窗、键盘、主题与状态。保持现有black/white/cosmic三主题与业主emblem；星环知识平台名称由NAMING_CONTRACT锁定，不把旧“系统”字形引回。截图仅用于对照，不能作为整页背景伪装控件。演示KPI/笔记不能冒充真实数据。
3. UF02：SpaceView当前桌面canonical、browser legacy有分裂，统一同一业务页面+有限transport。复用已经修好的Tauri production frontendDist/custom protocol/Core bridge，不能重建第二router或localStorage业务库。历史route/deep-link行为保留。
4. UF03：先交付01工作台、02知识库、03阅读编辑。复用CanonicalLibrary/Knowledge与Tiptap；真实新建/中文编辑/离线保存/搜索/来源引用/版本/退出重启。原始字节、CAS和未知payload保留。没有依据照常保存，专业采用仍独立。空/错/权限/离线/冲突/取消/草稿恢复必须诚实。
5. CB01→UF04：19系统可靠性和20版本来源提前。BackupPanel现有create/list，没有UI workspace restore；document_restore是另一动作。复用已有Core/恢复底座，校准backup ID/filename/schema/显示名；补有限预检/恢复/回读合同，版本化、权限受控，不给WebView任意filesystem路径。UI走list→选择→预检→明确确认→恢复→重启回读。独立fixture验证坏包、schema不兼容、取消、DB/CAS/引用和原库保全。脚本历史21步恢复通过不是当前UI已接好。
6. UF06：17全部能力与18详情提前，16父CAP全可发现，子项/别名/依赖/供体/未来意图可读。来自现有registry/atlas/证据投影，不建第二进度库。186设计文本、97资产来源表、96包内追踪不自证明全能力实现；缺独立细项证据标UNKNOWN，同时继续已知UI。

首批交付必须有真实Core的内容/版本持久化与重启回读、新Shell/首批页面同尺寸视觉对照、可靠性恢复实链、16父能力可发现及已有无障碍修复回归。先让首批真实可用，未实现的其他页明确未接通；不得做截图壳并报完成。

## 已有实现与旧任务去向

Qoder原无障碍审查只读T1–T5；随后Codex已有T0–T5修复、三主题焦点/状态栏/Inspector/A0回归。保留而非重做。生产Tauri资源路径修复、错误分类、模板cursor分页、KnowledgeCoursePanel与courses接口、Core机器纠正/复测也已有源码或本地记录。旧GUI39窗口/主题、模板/21步journey与AQ27自动部分记录不能被当成新22页/新工作区当前通过。AQ26真人待验，AQ27不全部都是待人审。

后续S1b UF05学习路径/课程；S2 CB02+UF07教学需求→方案审阅→交付版本→练习Teach-back→反馈修订→再交付，先人工交换，UF12基础画布；S3 UF08双链研究、UF09 AI记忆纠正复测/受限任务、O01+UF10开源模板资源、CB03集合关系视图公式、CB04+UF11多格式互通，最后UF13统一收口和M01资格。模板28学科登记、对象坐标/引用、Tiptap属性和已有分页要复用。691是来源行不是集成数；68surface的115冲突/59记录按所选供体语义处理，不全装369池。开源优先SDK/API/CLI/vendor/adapter，可重用成熟能力后再补实际缺口。

A–E是交换语义：A知识版本读取，B观察候选，C教学需求与表达方案，D交付登记，E学习反馈/修订；映射既有对象，不造五个服务。新字段不塞strict v1，actor不能自称human，哈希/幂等/重试/用途/授权/撤回必须可验。保留旧知识版本、课程binding和旧event rubric，表达修订不改知识。外部内容非特权；三项目不合库、不互相必需。动画、参数仿真、空间3D/VR/AR/XR、训练、移动同步和高级Agent/Marketplace保留发现入口，但FT01–04延期不自动实施。

整仓体积、外溢清理和 `docs/history/` 长期保留/跟踪已作为 S01.A–C 明确加入交接，详见下一节。Record去重及本地exclude不构成三项整体闭环。用户先前停止的本地/云端CI线V01仍暂停；dirty已有local_verify及节流workflow不能丢，不因本次补充恢复CI改造、云重跑或远程操作。

## S01.A–S01.C · 三项清理闭环（明确纳入后续交接）

这三项都是未完成的后续任务，不能因资料归档、精确 exclude 或 UI 首批完成而写成 COMPLETE。UI 保持优先，首批交付后继续本节；也可由用户把 HANDOFF-STORAGE-CLEANUP.md 单独交给一个 Agent。三个子项先共享一份当前计量与归属清单，再串行处置，避免同一 checkout 多 writer。当前整理会话仅补交接，不实施清理。

### S01.A：整仓“50多GB”的全面保全清理

- 主对象是 `D:\All projects\ArcheAxis-Knowledge-OS`，含项目内 `.project-local/`、活跃 worktree、Git 对象、归档、开发输出与历史遗留。重新实测；“50多GB”是用户历史观察，不能写成今天已测值。Record 归档约2.206GB只是子项，不能代表整仓。
- 先读 Git/worktree 状态与本项目目录边界，不跟随 junction/symlink 逃出授权根。不读 `.env`、凭据、私人 Agent memory/session；对私有目录只作不进入的未知归属登记。`.hermes/` 原位保留，不新增输出、不 blanket 删除。
- 按 Git对象、活跃/退役候选工作树、可重建缓存/构建输出、安装器、恢复材料、业务数据、来源原件、历史证据分组；记录绝对路径、归属依据、文件数、逻辑字节、可获得的物理占用及重复/共享计数口径。无法计量 UNKNOWN；不能把硬链接或共享载荷重复计算成实际可回收空间。
- 有用材料都留本项目，复用现有 Record 索引、分段压缩恢复工具与档案，不再复制15GB、不迁外库。允许无损压缩/合并、提取关键信息；摘要不能替代原始字节、来源和恢复配方。可重建副本只有确认归属、生成方式、引用、当前使用与授权后才处置。
- 先形成逐路径 `KEEP / COMPRESS / DEDUP / REGENERABLE_DELETE_CANDIDATE / UNRESOLVED` 清单。大量删除、活跃工作树退役、跨盘迁移或终止共享进程不在默认许可内：先把精确路径、影响、备份/恢复与预期节省做成可审结果，再按实际用户授权判断；不 reset/clean/批量restore，不绕过ACL或文件锁，不运行激进 Git prune/gc 清掉未交付历史。
- 验收：同口径清理前/后全仓计量、实际释放字节、保留字节和未处理字节可核对；每项处置有日志及 readback；压缩去重后从项目内材料恢复并验证原始 SHA-256。安装器、原始素材、恢复材料和历史失败证据不通过删除来省空间；未知仍开放。

### S01.B：外溢数据的归属、迁移合并与清理

- 已明确的来源候选：`D:\tmp`、`D:\All projects\dsh-acl-reports-20261003`、`D:\All projects\.aaos-stray-archive-20261001`、`D:\All projects\.aaos-root-backup-20261001`。另有截图中的 D 根12个临时文件，只按既有迁移清单列出的 exact path 回查，不扫描整个 D盘或 Home。检查来源是否仍存在、已迁走、被其他 Agent 使用或重新生成；历史目录名和旧65文件迁移回执都不是当前归属证据。
- 回查项目内已有外溢迁移清单、哈希、日志和引用；核对创建命令、Git worktree与实际用途，避免把工作流基础设施、他项目文件或未知材料当 AAOS垃圾。既有65项有历史迁移记录，`D:\tmp`仍有未决对象；不要以“目录名像 AAOS”直接决定删除。
- 有用且归属已证实的材料迁到项目规定的档案位置，并与已归档副本比哈希去重、合并索引；先目的端落地及完整恢复验证，再判断来源删除授权。原件不用格式化、改编码或截断。没用且明确可重建的材料列精确处置依据；未知标 UNRESOLVED 保留。
- 只处理上述明示来源和清单中的 exact 文件。不进入其他项目、软件私有目录或 E/F；绿色安装目录/其他外部工作树不因为与 AAOS有关而自动获得清理授权。
- 验收：来源→目的地→SHA/字节数→引用更新→保留/删除授权→现场readback逐项登记；已迁项目内容可检索和恢复。剩余项列绝对路径、归属缺口与下一动作，不能无证据把残留数量记0或整条标 COMPLETE。

### S01.C：`docs/history/` 长期保留与 Git 跟踪裁决

- 对主检出与实际 writer 分别重新盘点 `docs/history/` 的 tracked / untracked / ignored及字节、引用和原件位置；识别分支差异及私有本地 exclude。Qoder提到1114文件/475.3MiB、后续1007条精确exclude均是日期快照，重新核对后再报告当前值。
- `.git/info/exclude` 只是防误stage的本地措施，不是长期保留决定，也不会自动传递给新 checkout。禁止 `git add .`，不能用整体忽略 `docs/history/` 或删除旧失败/权威原文来关闭问题。
- 逐类明确：可公开且应版本化的权威导航/处置登记/哈希/恢复工具/关键文本回执；本项目保留、可无损压缩但不直接进入Git的大原件/历史证据；项目运行缓存和可重建生成物；未知/敏感材料。原件保存在项目目录与已Git跟踪是两种状态，登记必须分别说明。
- 每类写明 `TRACK_EXPLICIT_PATHS / ARCHIVE_PROJECT_LOCAL / IGNORE_PRECISE_GENERATED_PATHS / PENDING_OWNER_DECISION`、理由、原始和压缩哈希、恢复方法、持久入口与消费者影响。默认策略是小索引/恢复配方可审后版本化、原始重料仍完整保存在本项目；不可暗示该策略已经获准 staging/commit/push，更不能配置外部库/LFS上传。若仍有互斥长期选择，提交具体逐路径候选给用户裁决，保留开放状态。
- 原始权威/历史PASS/FAIL和来源日期不改写，摘要带原始引用；压缩合并不改变权威等级。仅在方案获准后修改必要的可共享规则/索引，精确处理tracked文件变动，保持未知文件检查与历史恢复能力。
- 验收：有可查的长期保留/跟踪决策表，每条可回到项目内原件或字节恢复路径；换到不继承本地exclude的合法隔离工作树时，规则与查找仍有效。统计本地防误stage、方案审批、规则落地和Git交付各自状态；未批准/未执行不算已关闭。

三项交付：存储基线、逐路径处置清单、外溢迁移/剩余清单、history长期决策表、压缩恢复与哈希回执、前后体积对比、实际修改范围、待裁决事项和下一份交接。文档留本项目规定的当前/历史目录，明细和原始计量日志留 `.project-local/runs/<unique>/`，统一索引登记。资料可找、字节可恢复、归属/授权可追溯、未知不冒充已清，是闭环标准。

## 已完整保全的输入与查找

原件在本项目 `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\archives\record-20261009\originals\Record`，不要再向用户索取已补交材料，不搬外库、不再复制15GB。根 `AAOS-资料索引.md` / docs/history/record-archive-20261009/MANIFEST.json 可查文件成员，旧压缩ZIP可按本项目recipes恢复原字节。

有效新ZIP：AAOS_最后任务包_20261009.zip（12成员）；AAOS_UI_补交_01_核心文档原型与素材_20261009.zip；AAOS_UI_补交_02_4K界面效果图_20261009.zip；AAOS_UI_补交_03_1440p界面效果图_20261009.zip；AAOS_UI_补交_04_全页响应式与总览_20261009.zip；AAOS_补齐材料与分析增量_20261009.zip。大小SHA声明同目录；全SHA见SOURCE-REGISTER。旧AAOS_UI_前端更新任务包_20261009.zip是历史截断源，不作完整输入。

小文本预解包位置 `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\task-runtime\aaos-task-planning-20261009\sources` 已登记原ZIP/member/hash；若缓存不存在直接从上述ZIP恢复。UI core包内docs/01–04、reference/tokens.css/style.css/pages.json、manifests/page-map/asset-manifest是实施参考；别执行prototype/scripts替代正式代码。只提取当页必要资产与图，按源hash登记。

新计划96来源映射、22页职责、旧270来源键+Q/F等合并和逻辑冻结均已登记。OLD-TASK-DISPOSITION.json保留旧要求/验收原文，不依据历史COMPLETE推断当前完成。来源未知不写0，未读历史不补造。不得读取私人Agent会话、凭据或正式知识库来整理对话。

## 验证、输出与授权边界

Shell先读实际版本，上轮PowerShell7.6.5。文件用exact path/-LiteralPath。默认本地：只选定AAOS代码与.project-local输出，不进入E/F，不跨项目写入、不上传/远程写入/安装付费资源。不改agent/provider/model/全局配置。不重启被用户停止的旧工作。

复用scripts/runtime/dev.py、scripts/ci/run_tests.ps1、frontend.py/.mjs及现有定向tests。统一quick/full草案在writer scripts/ci/local_verify.py，先读实际内容/--help/工具路径再使用。可参考 `& 'D:\All projects\ArcheAxis-Knowledge-OS\.venv\Scripts\python.exe' -B scripts/ci/local_verify.py --profile quick --run-id ui-first-s1-<unique>`；full同入口`--profile full`，按受影响范围与现有合同决定，不另建平行测试体系。已有Node/Cargo位置通过--node/--cargo，不全局安装。

测试的临时根、DB、CAS、WebView、端口和日志按项目runtime入口隔离，不用正式库、原始恢复材料。先非交互，真实安装/卸载/反复启动桌面前说明影响并确认。每次开始/结束时间、HEAD/dirty、源码哈希、工具版本、完整命令、退出码、日志、缺环境/skip记录；源码变化INVALIDATED。输出LOCAL_PASS/FAIL/NOT_RUN/CLOUD_BLOCKED/人工待验收，SYNTHETIC、INTEGRATED、REAL分别标注。本地不等于云端、安装或真人试学。物理IME/DPI/读屏和长期效果留M01，不用网页模拟缩放假装物理DPI。

默认本次执行不commit/push/PR/merge/release，不触发云重跑，不切换Green安装目录，不清理未知worktree或历史原件。遇到未授权不可逆动作，先把可复核候选和exact影响清单准备完，再请求该动作许可；普通本地已授权实现和回归不用反复确认。

首批结束交付：实际文件与功能变化、当前代码快照、页面/旧任务承接更新、准确验证命令/状态/日志、截图对照与差异、当前剩余问题，以及可独立复制给下一Agent的下一切片提示词。未完成明确PARTIAL，不说整个项目全部完成。把当前代码切片完成与用户可用/安装/真实学习验收分开。

清理阶段结束另交 S01.A–C 的前后计量、逐路径动作/授权/readback、哈希恢复证明、长期跟踪决策状态和未决归属；首批UI完成不关闭清理，清理完成也不等于安装/真人学习资格通过。
