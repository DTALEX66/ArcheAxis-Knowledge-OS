# LANGUAGE-MIGRATION-EXECUTION｜R5执行要求

所有项均待依据实际环境执行；任务包不直接操作你的磁盘。原GOV/LANG及父任务全部要求仍有效。跨任务切片按归属贡献执行，不形成第二任务队列。

## MIG01 逐模块迁移台账

父任务：X02, X04, X13；阶段：M0关键链/M1其余。

执行：建立旧入口/调用者/数据写入/语言/目标/fixture/退役条件清单；Rust、Python、C#、TS按职责选择，不追求全仓单语言。

验收：关键链模块100%有唯一目标归属，剩余模块明确M1或保留计算能力；不用Rust行数占比验收。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。

## MIG02 Rust领域权威真正接管

父任务：X04, X05, X07；阶段：M0。

执行：迁正文修订、审校、权限、事务、入库、作业、知识资格到Core；Python成熟OCR/模型/媒体计算走worker，不能直写新主库。

验收：真实请求在Rust决策且拒绝绕过；知识修改保留原修订；兼容、失败事务和worker返回契约通过；不只写接口空壳。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。

## MIG03 跨语言实际接线

父任务：X03, X04, X06, X08, X09；阶段：M0。

执行：契约包含身份、版本、取消、错误、重试；C#管理生命周期，Web/TS回收人类事件，Python执行计算，真实机器客户端使用Core方法。

验收：沿真实入口走跨进程往返；同键异payload冲突；模型/插件不能自报verified或人已掌握；允许停用组件保留资产。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。

## MIG04 数据迁移、旧权威退出与回滚

父任务：X05, X10, X11, X13；阶段：M0关键链/M1旧入口收口。

执行：旧非空库独占只读导出或停机一致快照，经staging迁到新库；旧legacy写者与新Core各自独占各自活动库，禁止双写同步。验证旧备份格式。

验收：旧默认入口退出且不得隐式回退Python业务写者；数据差分可解释；回滚按匹配版本快照，不能用旧程序直开不兼容新库；备份恢复实测。

证据：tested_source_sha, run_id, scope_and_environment, input_output_or_inventory, actual_result, limitations, rollback。

回滚：保留旧源码/配置和原始收据；使用经验证备份或重建流程恢复；不删除未知资产，不回写不兼容活动库。
