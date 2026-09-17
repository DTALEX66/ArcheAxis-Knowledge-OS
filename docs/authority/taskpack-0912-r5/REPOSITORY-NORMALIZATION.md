# REPOSITORY-NORMALIZATION｜R5执行要求

所有项均待依据实际环境执行；任务包不直接操作你的磁盘。原GOV/LANG及父任务全部要求仍有效。跨任务切片按归属贡献执行，不形成第二任务队列。

## REPO01 唯一规范与任务状态

父任务：X00, X13；阶段：M0入口/M1全仓。

执行：统一AGENTS、项目契约、决策覆盖表、语言索引、任务板、执行器入口；原历史原样保存。当前任务状态附tested SHA/收据，不继承旧DONE。

验收：只存在一个活动TASKS入口；差异有supersession映射，失效规则不能从旧入口复活。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。

## REPO02 全仓归属和旧资产复用

父任务：X02, X13；阶段：M0关键链/M1全仓。

执行：覆盖tracked/ignored/untracked源码、供体、旧UI、冻结功能和唯一资料；每项指定保留/适配/迁移/退役候选以及当前调用者。

验收：跟踪文件全部归类；忽略大目录按目录及例外清单盘点；未知项保留，不以批量搬目录代替复用。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。

## REPO03 依赖构建发布一致

父任务：X01, X11, X13；阶段：M0关键链/M1收口。

执行：锁版本、维护实际使用依赖及许可/SBOM；复用现有CI，检查变更触发、Windows打包、更新回滚与诊断。

验收：干净环境可重建同源码候选；打包不夹带真实数据库、密钥、会话；依赖删减必须证明调用不需要。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。

## REPO04 默认启动和安装可用

父任务：X03, X11, X13；阶段：M0可用/M1体验。

执行：真实Avalonia宿主管进程、端口、退出、恢复和诊断；Web/TS接现有学习界面；中文/空格路径及模型不可用时可保存资料。

验收：从用户默认入口完成闭环并重启继续；不要求手工启动多个终端，不用截图或build通过替代GUI操作。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。
