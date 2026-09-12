# CLEANUP-AND-SPILL｜R5执行要求

所有项均待依据实际环境执行；任务包不直接操作你的磁盘。原GOV/LANG及父任务全部要求仍有效。跨任务切片按归属贡献执行，不形成第二任务队列。

## CLEAN01 确认范围与磁盘基线

父任务：X00, X02；阶段：M0立即。

执行：核对真实项目路径、卷、工作树与既有授权；D:\All projects 只是历史安装根，不当整盘扫描许可；DSH安装目录不当项目路径。只列项目根、已知项目缓存及明确获授权外部根。

验收：范围表含canonical_path、授权依据、排除项、卷ID、工具版本、时间；E盘及未授权根不访问。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。

## CLEAN02 完整体积与大文件盘点

父任务：X02, X14；阶段：M0提前。

执行：统计tracked/ignored/untracked、构建、模型、原件、数据库、备份、日志、媒体、依赖；同范围报告bytes/GiB、文件数、逻辑大小、可获取分配大小和卷空闲。硬链接去重规则明确；junction/symlink不跟随。

验收：总量可由互斥分类复算；不得排除历史目录制造缩小；权限失败、云占位、压缩/稀疏文件和无法测量项单列，不读占位文件触发下载。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。

## CLEAN03 外溢数据追踪到生产者

父任务：X01, X02, X14；阶段：M0提前。

执行：在授权范围查询启动脚本、配置、进程命令行和日志中的输出位置；覆盖Cargo、Python、pip/uv、npm/pnpm、浏览器、OCR/媒体临时文件、模型下载、打包、Agent会话。记录写入进程、入口、配置来源与所有权证据；不输出凭据。

验收：每条候选外溢路径有producer/config/evidence/owner；共享缓存与归属未知项保留；不能按目录名或修改时间认定属于项目。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。

## CLEAN04 先修写入路径与持续增长

父任务：X01；阶段：M0立即。

执行：沿项目现有启动/开发/CI入口明确允许输出根；修工具级配置和进程环境，不改HOME/CODEX_HOME等全局变量；不将缓存全部塞到另一个未管理目录。覆盖异常、取消和并发。

验收：启动、解析、测试、打包后按同范围比较新增路径；新构建/临时产物不写历史会话目录；外部组件真实遵守，配置文档不算完成。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。

## CLEAN05 唯一资产保全与恢复抽查

父任务：X02, X10, X14；阶段：M0提前。

执行：保全会话、补丁、审计收据、未提交源码、原件、学习记录、机器方法、配置和密钥引用；活动数据库走一致备份/导出。模型和内容包单列，不当一般缓存删。

验收：保全目录有hash与恢复抽查；复制文件存在不等于可恢复；真实数据库恢复在隔离staging，不能覆盖当前库。密钥不进入公开报告。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。

## CLEAN06 重复文件与多份缓存辨别

父任务：X14；阶段：M0提前。

执行：先按大小筛候选，再对非占位且许可读取的候选算hash；相同字节仍核引用、版本、许可、运行依赖和跨项目共享。盘点嵌套虚拟环境、旧构建、重复下载、重复ZIP。

验收：输出保留项与每个候选删除项、引用重定向/重建路径；不因同名/同hash直接删原件或不同来源记录；避免重复计硬链接。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。

## CLEAN07 清理预演、隔离与精确执行

父任务：X14；阶段：M0提前。

执行：先生成逐路径操作清单、预计释放与回滚方式；清理已确认归属、可重建且无占用项。隔离保留期限按磁盘和用户策略配置；不做整盘递归删除、不默认清空共享缓存。已有授权内连续执行，越界只阻塞该项。

验收：清单记录canonical_path、类型、大小、依据、使用者、backup/hash、动作、状态；执行前复核路径和重解析点，变更/占用则跳过；隔离同卷不计释放空间。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。

## CLEAN08 释放空间与功能回归

父任务：X14, X11；阶段：M0提前并复测。

执行：同工具同范围复测逻辑大小、分配大小、卷空闲；记录并发写入和回收站影响；启动、导入、复习、机器调用及受影响构建实测。

验收：报告清理前后、实际删除、隔离、失败/跳过、净释放；保留模型与资料可读，Git和未提交工作未丢；不能用预计值冒充释放值。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。

## CLEAN09 容量预算与保留策略

父任务：X01, X13, X14；阶段：M0机制/M1收口。

执行：按缓存/日志/归档/索引/模型/原件分别设可配置预算、轮转和诊断；唯一数据不自动过期。增量日志避免重复记录全量内容，失败任务的临时产物可追踪回收。

验收：预算超限先止增/提示具体生产者；验证重复运行后的增量与峰值，阈值来自实测及用户预算，禁硬凑固定GB；共享缓存独立管理。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。

## CLEAN10 Git与交付包瘦身

父任务：X13, X14；阶段：M1。

执行：检查当前跟踪产物、LFS、对象库、重复release、安装包依赖和开发资产误打包；先修ignore和发布白名单，再处理已跟踪生成物。保留有用历史。

验收：交付运行所需数据完整；删除当前文件不宣称清掉Git历史。默认不改写历史、不force-push、不强制LFS迁移、不删旧tag；必要历史重写另列影响与授权。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。
