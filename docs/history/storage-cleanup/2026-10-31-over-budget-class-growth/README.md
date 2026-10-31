# 旧超预算类别增长：抵消漏报修复

现有baseline会承认旧预算债，但其他类别减少不应掩盖旧超预算类别继续大量增长。`growth_review`现对当前仍over_budget且与baseline可比较的类别单列增量，严格大于既有2GiB阈值时要求审查；总净增长、新越线类别及新布局项原语义保留，不新增阈值、注册器或自动清理。`nrm-grow3`以spr-size5内存副本构造runs+3GiB/build−4GiB：总量−1GiB且无新越线类别，原NO_NEW变为REVIEW_REQUIRED；原JSON字节和PARTIAL身份保持，不是磁盘实际新增/减少GiB的观察。

候选回归为既有28项加7个边界：增长3GiB、平、下降、小于2GiB、恰2GiB、2GiB+1及underbudget抵消；35通过，但candidate替换资格与正式运行分列。root部署后 `nrm-grow4` 对正式仓库模块与原测试路径实际35通过、actual/wrapper0、source_consistent=true，没有候选overlay。源码两文件、提案/实际补丁身份及收据/日志见MANIFEST；未重测全仓、复制载荷、删除或执行API/模型。本修复不代表旧债消失或规范化通过，当前进度仍沿[唯一执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。

后继风格检查 `nrm-lint2` 退出1：既有unused import、zip strict参数和嵌套if三项。最小修正后 `nrm-lint3` 全部通过，`nrm-grow5` 正式35项再次通过；四个收据均源码一致。原失败及首次正式验证身份保留，后继源码SHA见MANIFEST，不混写成同一次运行。
