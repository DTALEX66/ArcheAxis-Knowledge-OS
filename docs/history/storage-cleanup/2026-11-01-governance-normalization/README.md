# 治理优先：生产者增长约束、临时落点与历史文件归位

Owner本轮要求“优先执行各类治理和规范任务，静默执行不要在问我了”。沿既有S01/G01执行，不新建业务队列，不恢复UI实施或监控。前轮PR204合并主分支`da9fca0de9c617a0e8c100c32d9fcecf00f45ee7`，本批在独立本地治理分支实施；前轮云端资格不移绑本批修改。

## 实际改变

- `local_pinned_packaging.bundle()`复用便携producer的固定checkpoint、≥1GiB用途/共享/保留声明、pre及载荷投影审查和finally-post。按payload与NSIS工具合计实际字节触发；成员最多写入已登记字节，额外1字节只检测，拒绝增长、短读和hash不符。post越线使包装结果FAIL，保留复制主异常、原NSIS退出码和部分候选。没有新增force、跳过或自动抬升基线。
- capability/search探针每次通过`dev.artifact_directory`分配独立工作目录，合成vault与数据库同属该目录；启动不再递归清空固定共享run。完成后仅清自己的临时载荷，迁移失败的证据保留。原搜索、握手和候选/学习只读断言保持。
- 资源索引builder默认分配规范run内唯一目录；显式override只作经校验的parent，每次排他创建新子目录。BAT落显式workdir，OCR通过独占随机PNG文件句柄写入，保留原固定样本及其硬链接目标。registry直接CLI也分配规范workdir；API不提供workdir时，需写文件的两种probe明确NOT_RUN。只读解析与`--no-probe`不因此分配目录。

投影仍是复制输入下界，不计生成installer、日志和元数据，不是磁盘硬配额或跨producer原子锁。其他runtime stager/build和linked-worktree计量/owner映射仍未全面覆盖。现有便携producer与固定基线保持，不通过扩大allowlist隐藏债务。

## 已执行的48项无损归位

14份公开合成模型历史结果/日志、15份历史公开PR草稿、19份一次性项目修码/核验脚本，经归属、消费者、逐成员SHA/CRC及独立恢复演练后，原散落48叶已精确退役。164,241原字节单份压缩保全为3ZIP共62,949B；101,292B仅为原件与ZIP差，不计新治理证据开销，不是物理磁盘回收。没有执行旧修码脚本或发布草稿；原失败状态保留。

恢复入口均在ignored `.project-local/runs/be268a2d33/gov-layout-20261101/`：`restore.py`恢复14项，`restore-drafts.py`恢复15项，`restore-scripts19.py`恢复19项。默认只验证；`--restore`按完整manifest恢复原路径，拒绝覆盖。19项中的组内脚本依赖整组保全。恢复前用[MANIFEST](MANIFEST.json)核ZIP、映射及工具SHA；历史消费者先恢复完整组，不执行过时脚本改当前源码。归档原件与载荷不进Git。

root再次独立验证48路径全缺失、3ZIP成员原尺寸/SHA及原FINAL和后继FINAL身份；恢复演练新增副本另行精确退役，不混入旧收益。浅层布局与正式post计量均581→533，无新增布局；旧49目录仍36非空/13空，不能把本次48叶整理说成旧49目录全部清理。

## 测量与验证边界

普通令牌前计量28,460,851,496可读B/343,900文件，后计量28,464,394,459B/350,905文件；均674读取错误、243私有排除、PARTIAL，原/wrapper退出1，源码前后一致。差3,542,963B包含本轮测试fixture、收据和代码变化，不是净空间回收。旧管理员0错误快照与本次普通令牌覆盖不同；不重新要求ACL修复，不改变权限，也不将不可读解释为不存在。固定登记checkpoint保持原字节，不逐包滚动；本批对固定基线为NO_NEW_GROWTH_TRIGGER，不能据此宣称全仓预算PASS。

冻结后的`gov-code-final3`为196 passed/1既有skip/3真实资源用例deselected，child/wrapper0、源码一致；`gov-lint-final`按实际CI Ruff规则通过。架构、路径和文档权威检查通过；仓库规范首次发现两测试文件CRLF，统一LF后`gov-conv-final2`通过，原FAIL保留。后计量是其记录时点，早于这次换行修复重测和文档封存，没有因后续少量证据重新滚动基线。没有运行真实MSVC/Tesseract、Ubuntu宿主、NSIS或≥1GiB装包；Windows分支用模块级平台代理，PNG/BAT与旧硬链接为真实小文件，reparse拒绝为模拟属性测试。前轮全产品CI不代替本批本地资格。

独立复核曾发现override复用覆盖样本及registry CLI丢失workdir两项P2，已修复并静态复核闭合；原RED保留。早期`gov-probe-red/green`因其他writer并行变更而wrapper3/INVALIDATED，child分别1/0，不作为最终资格。root另读取原Git blob，在隔离合成目录用失败迁移stub复现旧固定run删除历史证据，再验证修复版保留；不启动服务器或读真实库。最终有效收据与完整SHA见MANIFEST。

三处Green历史mig的后继载荷绑定仍UNVERIFIED：历史缺失/曾在Formal存在不能证明现在已迁移或永久丢失；不扫描外部隐藏工作区正文或Agent状态。剩余533布局项、其他producer增长覆盖和该来源缺口继续沿[唯一执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)接续，整体PARTIAL。
