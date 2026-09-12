# R5增量验收

原38场景完整保留；下列18切片验收挂回原父任务与Q00/Q01，不另设最终审计权威。全部NOT_RUN。

## CLEAN01

父任务：X00, X02。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：核对真实项目路径、卷、工作树与既有授权；D:\All projects 只是历史安装根，不当整盘扫描许可；DSH安装目录不当项目路径。只列项目根、已知项目缓存及明确获授权外部根。

通过条件：范围表含canonical_path、授权依据、排除项、卷ID、工具版本、时间；E盘及未授权根不访问。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## CLEAN02

父任务：X02, X14。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：统计tracked/ignored/untracked、构建、模型、原件、数据库、备份、日志、媒体、依赖；同范围报告bytes/GiB、文件数、逻辑大小、可获取分配大小和卷空闲。硬链接去重规则明确；junction/symlink不跟随。

通过条件：总量可由互斥分类复算；不得排除历史目录制造缩小；权限失败、云占位、压缩/稀疏文件和无法测量项单列，不读占位文件触发下载。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## CLEAN03

父任务：X01, X02, X14。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：在授权范围查询启动脚本、配置、进程命令行和日志中的输出位置；覆盖Cargo、Python、pip/uv、npm/pnpm、浏览器、OCR/媒体临时文件、模型下载、打包、Agent会话。记录写入进程、入口、配置来源与所有权证据；不输出凭据。

通过条件：每条候选外溢路径有producer/config/evidence/owner；共享缓存与归属未知项保留；不能按目录名或修改时间认定属于项目。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## CLEAN04

父任务：X01。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：沿项目现有启动/开发/CI入口明确允许输出根；修工具级配置和进程环境，不改HOME/CODEX_HOME等全局变量；不将缓存全部塞到另一个未管理目录。覆盖异常、取消和并发。

通过条件：启动、解析、测试、打包后按同范围比较新增路径；新构建/临时产物不写历史会话目录；外部组件真实遵守，配置文档不算完成。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## CLEAN05

父任务：X02, X10, X14。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：保全会话、补丁、审计收据、未提交源码、原件、学习记录、机器方法、配置和密钥引用；活动数据库走一致备份/导出。模型和内容包单列，不当一般缓存删。

通过条件：保全目录有hash与恢复抽查；复制文件存在不等于可恢复；真实数据库恢复在隔离staging，不能覆盖当前库。密钥不进入公开报告。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## CLEAN06

父任务：X14。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：先按大小筛候选，再对非占位且许可读取的候选算hash；相同字节仍核引用、版本、许可、运行依赖和跨项目共享。盘点嵌套虚拟环境、旧构建、重复下载、重复ZIP。

通过条件：输出保留项与每个候选删除项、引用重定向/重建路径；不因同名/同hash直接删原件或不同来源记录；避免重复计硬链接。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## CLEAN07

父任务：X14。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：先生成逐路径操作清单、预计释放与回滚方式；清理已确认归属、可重建且无占用项。隔离保留期限按磁盘和用户策略配置；不做整盘递归删除、不默认清空共享缓存。已有授权内连续执行，越界只阻塞该项。

通过条件：清单记录canonical_path、类型、大小、依据、使用者、backup/hash、动作、状态；执行前复核路径和重解析点，变更/占用则跳过；隔离同卷不计释放空间。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## CLEAN08

父任务：X14, X11。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：同工具同范围复测逻辑大小、分配大小、卷空闲；记录并发写入和回收站影响；启动、导入、复习、机器调用及受影响构建实测。

通过条件：报告清理前后、实际删除、隔离、失败/跳过、净释放；保留模型与资料可读，Git和未提交工作未丢；不能用预计值冒充释放值。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## CLEAN09

父任务：X01, X13, X14。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：按缓存/日志/归档/索引/模型/原件分别设可配置预算、轮转和诊断；唯一数据不自动过期。增量日志避免重复记录全量内容，失败任务的临时产物可追踪回收。

通过条件：预算超限先止增/提示具体生产者；验证重复运行后的增量与峰值，阈值来自实测及用户预算，禁硬凑固定GB；共享缓存独立管理。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## CLEAN10

父任务：X13, X14。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：检查当前跟踪产物、LFS、对象库、重复release、安装包依赖和开发资产误打包；先修ignore和发布白名单，再处理已跟踪生成物。保留有用历史。

通过条件：交付运行所需数据完整；删除当前文件不宣称清掉Git历史。默认不改写历史、不force-push、不强制LFS迁移、不删旧tag；必要历史重写另列影响与授权。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## REPO01

父任务：X00, X13。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：统一AGENTS、项目契约、决策覆盖表、语言索引、任务板、执行器入口；原历史原样保存。当前任务状态附tested SHA/收据，不继承旧DONE。

通过条件：只存在一个活动TASKS入口；差异有supersession映射，失效规则不能从旧入口复活。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## REPO02

父任务：X02, X13。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：覆盖tracked/ignored/untracked源码、供体、旧UI、冻结功能和唯一资料；每项指定保留/适配/迁移/退役候选以及当前调用者。

通过条件：跟踪文件全部归类；忽略大目录按目录及例外清单盘点；未知项保留，不以批量搬目录代替复用。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## REPO03

父任务：X01, X11, X13。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：锁版本、维护实际使用依赖及许可/SBOM；复用现有CI，检查变更触发、Windows打包、更新回滚与诊断。

通过条件：干净环境可重建同源码候选；打包不夹带真实数据库、密钥、会话；依赖删减必须证明调用不需要。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## REPO04

父任务：X03, X11, X13。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：真实Avalonia宿主管进程、端口、退出、恢复和诊断；Web/TS接现有学习界面；中文/空格路径及模型不可用时可保存资料。

通过条件：从用户默认入口完成闭环并重启继续；不要求手工启动多个终端，不用截图或build通过替代GUI操作。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## MIG01

父任务：X02, X04, X13。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：建立旧入口/调用者/数据写入/语言/目标/fixture/退役条件清单；Rust、Python、C#、TS按职责选择，不追求全仓单语言。

通过条件：关键链模块100%有唯一目标归属，剩余模块明确M1或保留计算能力；不用Rust行数占比验收。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## MIG02

父任务：X04, X05, X07。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：迁正文修订、审校、权限、事务、入库、作业、知识资格到Core；Python成熟OCR/模型/媒体计算走worker，不能直写新主库。

通过条件：真实请求在Rust决策且拒绝绕过；知识修改保留原修订；兼容、失败事务和worker返回契约通过；不只写接口空壳。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## MIG03

父任务：X03, X04, X06, X08, X09。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：契约包含身份、版本、取消、错误、重试；C#管理生命周期，Web/TS回收人类事件，Python执行计算，真实机器客户端使用Core方法。

通过条件：沿真实入口走跨进程往返；同键异payload冲突；模型/插件不能自报verified或人已掌握；允许停用组件保留资产。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

## MIG04

父任务：X05, X10, X11, X13。

输入：真实源码/当前入口与获授权样本或文件范围。

操作：旧非空库独占只读导出或停机一致快照，经staging迁到新库；旧legacy写者与新Core各自独占各自活动库，禁止双写同步。验证旧备份格式。

通过条件：旧默认入口退出且不得隐式回退Python业务写者；数据差分可解释；回滚按匹配版本快照，不能用旧程序直开不兼容新库；备份恢复实测。

结果：NOT_RUN。证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

