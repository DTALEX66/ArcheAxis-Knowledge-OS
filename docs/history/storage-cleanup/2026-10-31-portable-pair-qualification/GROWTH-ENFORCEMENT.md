# 便携候选复制前的持续体积约束

正式`tauri_portable_candidate.assemble()`现在在任何目标mkdir/copy前核对每项真实常规文件尺寸、合法相对路径与计划总数；达到1GiB时，直接API与CLI均须提供用途、共享方式、保留理由和本仓canonical run。唯一固定基线登记在活动指针`execution_control.owner_priority_20261030.operator_storage_checkpoint`，绑定实际六源清理后报告的原始字节/SHA。登记来自既有Owner治理授权下的Codex执行，不冒称新增Owner决定；不会每生成一包就自动推进基线。

大包同步调用既有`storage_report.measure()`，以同一固定基线分别检查当前体积及计划载荷投影。新增规范外路径、类别首次越线、总量或当前超预算类别累计增长超过既有2GiB复核线，均在复制前停止；不添加force/skip开关。已有旧债持平/下降不因此触发，PARTIAL仍保留访问/私有/布局局限，不能变成存储PASS。形成有效pre状态后，成功、复制失败或预检拒绝均在finally尝试post并封存独立收据；复制主异常优先保留，post/收据失败另附，部分候选不自动删除。

独立静态审查曾发现：仅在prestat核尺寸仍可被随后增长的源文件突破。现每成员至多复制计划bytes，额外1字节只检测、不落盘；短读、超长或最终hash不符保留源及部分候选并失败。正式旧源码反例确认21B计划实际写入85B；修复后相同微小样本目标不超过21B。小包不进行百万文件扫描。本轮没有真实1GiB组包、UI/Host重建或部署；合成门槛只在测试中缩小，没有改变正式常量。

旧源首轮3FAIL收据保留；将异常文案断言改成实际目标大小后，行为RED为2FAIL/1PASS，分别复现缺声明仍复制与stat后增长越界，短读本已拒绝。最终完整受影响文件57PASS，Ruff0，直接CLI导入/帮助及真实checkpoint原字节读取0，均绑定`d7f17757206625a0012021d6bd61e2c639a209bd`加相应dirty patch，源码前后一致。中途57PASS但Ruff19项失败的原收据也保留；修正新增import/异常名/多语句及同文件两处旧SIM102后，最终三run共用patch `68ca79873c9aea3654d340c072b9db8fb619694c46718199f4cc888380893601`。pytest禁用cacheprovider导致的既有cache_dir warning未隐藏。精确身份及分层见[GROWTH-ENFORCEMENT.json](GROWTH-ENFORCEMENT.json)。后续仅增文档不重跑产品测试，以文档门禁另行绑定。

本切片仅支持当前REPO内canonical artifacts；linked worktree的common-owner根路由尚未适配，即使初始化checkpoint也不能解除拒绝。其他机器/CI缺同仓可核基线时同样拒绝大包；未宣称这些环境已资格化。快照不是全仓原子锁，载荷投影不计少量新manifest/receipt字节，post保留实际已知结果；其他producer并发增长、不可读内容及物理分配仍未知。

`local_pinned_packaging`、其他runtime stager/build producer尚未接入同等门禁，应沿现有规范化任务继续治理；本实现不构成所有目录或全仓增长问题已解决。后端日常继续复用已验证的in-place runtime及pinned Core，避免为单项验证复制整包。回退为获授权本地提交的这组producer/tests/目录说明/指针变更；先保留实际报告、失败证据与现有候选，不伴随载荷删除。清理、完整恢复、产品/安装/Owner验收的边界仍见[六源清理记录](BATCH-DEPLOYMENT.md)，实际接续只读[唯一执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。
