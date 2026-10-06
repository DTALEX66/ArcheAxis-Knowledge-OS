# 发给 DSH 的执行提示词 · 2026-10-03

你是本项目剩余整改执行方。任务是把当前正式Desktop/Core推进到真实M0闭环，并整理项目本体及Green工作区，安全同步可公开项目内容。**不要相信“全部完成”“历史都已上传”等结论；从当前Git、Authority、源码、运行时和远端证据核实。不要重做已有实现或另开架构。**

## 1. 边界、当前入口和权限

- 主仓库 `D:\All projects\ArcheAxis-Knowledge-OS`；当前实现worktree `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\dsh-backend-loop-20261001`；分支 `codex/dsh-aaos-real-multiformat-loop-20261001`。进入前动态读取branch/HEAD/status，若与交接不同先解释，不reset或覆盖。
- Green `D:\All projects\ArcheAxis.Knowledge.Green-x64`，根目录不是Gitrepo，里面有真实库、运行包和主repo管理的嵌套worktrees。共享工具和模型只按现有索引消费，不迁移、不删、不上传权重。
- 依次读最近AGENTS、LESSONS_LEARNED、`docs/CONFIGURATION_AUTHORITY_INDEX.md`、R6 `EXECUTOR-START.md/TASKS.json/TASKPACK.md`、M0 overlay、R6 live state/execution、`docs/current/AAOS-CLOSURE-GAP-AUDIT-20261003.md`及`AAOS-INDEPENDENT-AUDIT-20261003.md`。R7标签不自动成为新Authority；不存在的权威报AUTHORITY_REFERENCE_MISSING。
- 既定架构：C#/Avalonia正式UI，Rust Core唯一canonical SQLite写者，隔离Python workers；禁止UI/worker直写主库、legacy/vNext双写。
- 用户选定 **MINIMAX视觉＋DSH功能**。保留已移植cosmic/theme/glass、诊断折叠、点击反馈、reduced-motion、多轮纠正。不得整体切回某分支覆盖当前融合结果。
- 用户要求项目同步：可提交和正常推送经过核验的任务所属源码、项目合同、脱敏审计文档/证据；禁止force push、history rewrite、直接破坏保护分支。merge/main和Release不得从“上传”推导授权；Release保持FROZEN。
- “所有内容上传”不覆盖凭据、私人native session/memory、数据库、用户原始资料、运行缓存、模型权重。不能把它们强制add，不能读取凭据正文。遇权限拒绝保留UNKNOWN，按项目正常auth路径核实远端，不改ACL或绕边界。
- 用户要求清理是范围目标；递归删除仍执行AGENTS的精确清单审批。未确认清单不删；不清空Green data，不删未知/不可读文件。E盘禁止访问。
- one writer per write-set；可并行只读审计及隔离写集。不得自行切换用户provider/auth/config；模型难度分配遵从当前配置和明确授权。控制TOKEN，必要输出保留证据，避免全仓重复扫描。

## 2. 必须继承的已完成差量

正式Desktop语义搜索与FTS共存；真实PARTIAL/UNAVAILABLE保留。课程正常路径已是“选择知识→from-knowledge→持久化GET→实际render正文/来源核验→真人显式开始学习→Core Assessment”。课程worker错误修改正文/ID/标题已被Core502拒绝；禁用期间排队任务不能执行；artifact冲突409。不要再把这些列为未实现或重复重构。

schema9课程存储、schema8旧archive兼容、真实旧库副本迁移、新课程backup/restore、真人事件5保留已有分段证据。真实reranker采用 `/v1/responses` exact yes/no首token概率；缺一项仍PARTIAL，不补概率，不用聊天自评分或实验bias当生产概率。

最新Desktop目录 `.project-local/build/minimax-dsh-course-search-20261003/desktop-selfcontained`，DLL SHA256 `23D9B3BB83425CC6A716017FBC05778BFCE89CC72515D4F08B2037E3221A0767`。它是当时集成源码的本地publish，不是自动合格的清洁最终候选。

用户已真实提交过学习事件5，但源知识为fixture。用户认为先前模型回答可接受；不得将其改为错误或伪造纠正。`mastery_projection.closed=false`目前是代码固定值，不是已完成掌握。当前结果NOT_READY。

## 3. 执行任务与验收

### F01 普通界面文案及真实状态

实看最新attached-window图和实际窗口，清理首页Core/evidence anchors、侧栏Assessment/Review协议说明及其他默认后台术语。自然文案必须说明用户可做什么；诊断可展开但默认收起。不可用/失败不隐藏，不把UNKNOWN显示0或成功。核实三主题、窄窗、键鼠焦点、忙碌/禁用/错误/成功及减弱动效；扩展矩阵按Authority要求执行，不用静态字符串测试冒充交互。

### B01 权威缺口的必要差量

先给Owner一个具体可审阅的Mastery规则提案和影响，得到裁决再实现；不能自创连对/Good即掌握。核查resource-root语义Owner缺口。from-knowledge目前只支持有anchor的active accepted；若选定旅程要求无anchor Personal Knowledge，补必要路径和来源语义，否则请Owner明确范围并记录限制。不要通过缩小目标偷偷判PASS。

### R01 同一真实输入的P0–P5

在项目内隔离运行目录，用用户允许的真实资料和原件hash，完成Source→Transform→Anchor/Loss/Quality→知识审核→语义/FTS查询→General课件候选→真人审阅→开始学习。真人提供答案/自评；机器执行同一知识任务；真实错误由真人判断、纠正、显式接受，再Retest。没有真实错误时如实保留未验收，不能让模型故意犯错后叫真实闭环。

每个节点记录同一workspace/source/knowledge版本/课程/Assessment/item/task/correction/retest身份及实际API/UI读回。做到退出Desktop/Core、冷重启、恢复答案/课程/FSRS/队列，再维护CLI备份恢复全状态和对象hash/FK检查。不重跑或修改原Legacy数据库，复用已核验旧库副本证据。

P0需记录新候选的启用成功、真实失败、禁用、人工profile替换、重启、恢复及worker身份；不擅自增加自动provider切换或自动JIT。共享模型如果未加载要给真实不可用状态及现有加载入口。

### Q01 最新集成候选及门禁

聚合改动停止后冻结真实source snapshot，构建全新候选并核manifest路径/数量/摘要/worker注册/运行Python及依赖。不能把b421ddee旧候选或dirty构建当新SHA候选。按项目canonical gate及风险图执行一次阶段完整验证；失败只复跑修复相关门禁。

已知未通过：全量Python收集缺onnxruntime/fsrs/jiwer/pymupdf；worktree convention有60个CRLF问题，architecture通过。先区分依赖环境、index/HEAD实际问题和baseline，不批量重写immutableTaskPack，不把skip算PASS。发现依赖缺失先查已有锁定环境，必要安装限定项目作用域/版本/来源并保留回退，禁止全局安装。

### S01 可公开项目内容双端同步

读取实时remote/main/feature SHA、ahead/behind及开放PR。当前feature PR #157 base为codex/Audit，MINIMAX PR #158也未合；main与feature不是同一HEAD。保护别人新提交，正常fast-forward或有证据的集成，不force。按明确路径stage本任务，diff/secret/path/合同检查后commit/push，回读服务器最新SHA和exact-SHA CI状态。

至少分别报告：feature是否本地/云端同SHA，main是否合入，CI是否实际success，候选是否含新SHA，安装是否完成。不可用“已上传”替代这些状态。

主root1007未跟踪history及1测试目前未证明全部已上传/归档。逐项metadata分类、确认属于项目可公开文档才读取核查；私人session/memory/混合档案正文禁止。可公开内容须比对现有远端文件或归档manifest/member hashes后再复制进单一writer提交；已归档不重复上传。含用户资料/密钥/未知恢复内容的一律保留本地并列清单，不上传。

### C01 项目本体与Green精确清理

先分SOURCE、当前RUNTIME、用户DATA、必要RECOVERY、任务已结束CACHE、历史DOCUMENT、UNKNOWN。云端同HEAD仅覆盖tracked；ignored/untracked没随push保存；删tracked后再push会删云端当前树。禁止`git clean -fdx`、`reset --hard`及整树覆盖。

优先核查 Green `.ui-task-tree/AAOS-integration-verification-413ad3a0`：已知tracked/untracked均0，仅ignored `.ruff_cache`，tip62f23189已可从远端main历史到达。确认无消费者/私有载荷，保存必要证据，列完整绝对路径审批后规范移除worktree。

其他dirty worktrees、phase2/minimax ignored证据、Green三个AAOS-v*及启动器/data、主repob421ddee候选Python、现役Desktop/Core/run保留。两个早期候选的计划在主repo `.project-local/audit-cleanup-20261003.json`；重新核路径/进程/数据库/链接/恢复依赖和审批，不能因旧计划存在就删除。

每个可删路径需要owner、producer/消费者、当前是否使用、源与恢复摘要/恢复试验、精确授权、删除后readback与净节省。不可枚举项不算空目录；`p-w7n3ehdf`保持UNKNOWN。恢复包私有不上传，Git仓库“干净”不等于用户数据被清空。

## 4. 最终交付与禁止漂移

交付：真实P0–P6验收矩阵、前/后端剩余清单、新源码SHA/tree及候选manifest、真实UI/重启/备份恢复收据、双端SHA/CI读回、精确清理执行与保留清单、Owner未决项和回退步骤。更新mutableR6 live记录，不修改immutable包；历史收据保留原SHA。

安装Green备份/原位替换/重启/回滚必须得到Owner具体路径和操作授权后才执行；不给用户安装步骤前先准备好可审阅候选和回退。独立审计方复核后只能判LOCAL_GREEN_READY_FOR_OWNER_REVIEW或NOT_READY，不自动RELEASE_READY。

第二Provider、更多Domain/renderer、Graphiti/LightRAG、Marketplace、扩展Research、3D/VR/AR等按M0/长期Authority排期，不突然塞进当前闭环，也不说它们已经完成。不得写新的大蓝图代替执行，不重复审计已修问题，不制造真人答案/错误/授权，不把编译、fixture、push、CI、merge、安装混为一谈。
