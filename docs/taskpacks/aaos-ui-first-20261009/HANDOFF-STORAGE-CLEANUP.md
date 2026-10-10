# 可单独复制：AAOS 整仓、外溢与历史归档清理交接

用户已要求把以下三项未闭环工作纳入后续交接。你只有在用户把本提示交给你启动执行后，才在本提示的具体本地范围内推进；生成本提示的会话没有实施清理。先完成盘点/归属/保全/精确处置方案，做已经授权的可逆整理；不为审批前置而停止所有可审工作。批量删除等高风险步骤再依据 exact path 授权决定。

项目主根：`D:\All projects\ArcheAxis-Knowledge-OS`。现有实现writer候选：其 `.project-local\worktrees\gov-ui-20261008`，该目录有未提交UI/后端/CI/治理修改；不能从HEAD新建worktree就认为保留了dirty。先重新读AGENTS.md、AUTHORITY.md、LESSONS_LEARNED.md、PROJECT_CONTRACT.yaml、两个Authority索引、Git branch/HEAD/status和worktree状态，确定唯一writer。主检出与writer的文档基线不同，不能依据历史COMPLETE或旧R6/Avalonia入口判断当前；栈/模型不由清理任务改变。

已知的历史成果是：Record180文件盘点中121项本项目/共享资料归档、59项有排除依据；逻辑原始约15.35GB，13历史ZIP经过项目内分段去重压缩约1.91GB，整套Record档案约2.206GB，完整字节恢复及SHA已验证。这个成果不代表整仓“50多GB”清理或所有外溢结束，也不表示外部Record原件已经删除。当前体积必须重新计量。

归档入口是根 `AAOS-资料索引.md`，详细索引和SHA在 `docs/history/record-archive-20261009/INDEX.md`、MANIFEST.json、CONSOLIDATION.json、VALIDATION-COMPACTED.json；原件/压缩对象在本项目 `.project-local/archives/record-20261009`。复用 `scripts/maintenance/archive_record_materials.py` 与 `compact_record_archives.py` 的现有查找/恢复/验证入口，先读代码和帮助，不重建第二套档案，不再次复制15GB。已有来源本地恢复即可，禁止迁外库或上传。

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

默认PowerShell7，先读实际版本；Windows exact path/-LiteralPath，不跟随越界reparse。写入前git status，保护未知修改，不reset/clean/批量restore/forcepush，不终止共享进程、不绕过ACL。E/F不进入，凭据/.env/privateAgent memory/session不读取；未知他项目或软件归属不迁移、不删除。安装器、恢复材料、来源原件与旧失败证据保留或无损压缩，不靠删除它们省空间。

复用项目规定的输出根 `.project-local/` 与现有脚本。每次计量/压缩/恢复/处置记录开始结束时间、当前HEAD、工作区摘要、工具版本、完整命令、退出码、路径/哈希、日志与readback。缺权限/锁保持BLOCKED/UNRESOLVED，缺物理占用UNKNOWN不记0。相同计量口径核对前后，区分目标体积、实际释放和共享去重；全部有效资料必须在本项目可查且可还原原字节。

本任务不实施UI/前后端、不恢复停止的V01 CI工作，不跑正式知识库测试、不切换Green安装、不触发云端重跑、不commit/push/发布、不写其他项目。清理风险不通过关闭未知文件检查或忽略整个history解决。完成交付本节三项的实际动作与证据、明确未决清单及下一份自包含提示词；若仅完成盘点方案或等待exact-path裁决，报告PARTIAL，不假装已经清理完。
