> R4继承说明：以下原规范/历史记录完整保留。出现R3、旧日期、旧入口或“最新”表述均按原记录时间解释；当前活动入口见EXECUTOR-START.md，当前增量见HUMAN-LEARNING.md。R4未重查远端或复跑原产品测试。

# 审计增量与续修优先级

## 证据口径

2026-09-08 重新读取分支集合确认：
- codex/full-loop-0906 = cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed。
- main = 4ca46eaf94c486dadcf200aac6b41cd968b1ce6e。
- 本包依据对话中的9月8日独立复审及针对性仓库读取。没有新增全量审计、没有重跑 Windows/Rust/.NET 或操作用户真实资料。
- 继承审计结论：Q00不通过，Q01尚未具备通过条件。当前CI通过的100 Rust测试、C#构建、29词表案例和Python调用只证明其覆盖范围，并非完整产品通过。
- 仓内 C-FIX-STATUS v7 存在旧HEAD/偏早DONE。本包不删除已有修复，不采信与当前独立证据冲突的完成声明。

## 四个优先 P1 修复

|问题|承接|必须实现|回归|
|---|---|---|---|
|review new_body直接覆盖旧正文|X04/X05/X07，C03|审校不得改正文；修改新建修订及supersedes，旧字节/ID含义稳定|REVISION-01，IMPACT-01|
|归档11表→13表但仍v3|X05/X10，C03/C04|明确升级并兼容真实历史布局；未知布局不猜补|ARCHIVE-01|
|6371/无error冒充支持|X07，C07|运行、判定、来源独立性、对象/单位/条件分别记录|VERIFY-01|
|学习同key异内容静默去重|X04/X08，C05|事件身份绑定对象和规范payload；相同重试回原结果，冲突拒绝|EVENT-01|

修复优先不是要求重开所有历史实现。先写能重现缺陷的测试，再修生产入口及领域/持久层，确认不是只改探针。

## 原 C01—C10 完整承接

|审计项|已有进展保留|继续修什么|原任务|
|---|---|---|---|
|C01|当前入口已有更新|语言索引、乱码、任务状态/执行记录对齐；单一有效计划|X00/X13|
|C02|中间件已覆盖客户端actor|未知启动角色拒绝、真实宿主凭据隔离、机器越权负例|X04/X09|
|C03|审校事务、关系与反查已有实现|不可变修订、双向导航、同步资格检查与影响传播|X04/X05/X07|
|C04|类型、hash/行数、事务计数已改|一致快照、独立staging、非空全关系迁移、历史归档恢复|X05/X10|
|C05|历史与到期时间、去重基础|事件冲突/缺key、FSRS、实际学习事件与重启|X04/X08|
|C06|资格函数已进入查询和测试|真实MCP任务、方法/独立评测、反馈再调用|X09|
|C07|真实公开抓取探针已有进展|统一多格式executor、可信核查结果与真实云端门禁|X05/X06/X07|
|C08|DeepTutor已有中文/聊天/路线演示|Core接线、真实资料回流、Windows可用入口|X03/X08/X11|
|C09|当前Windows CI绿|同源候选包、GUI/人机全链/恢复和独立门禁|X11/Q00/Q01|
|C10|已有两轮删除与本机摘要|同范围全仓盘点、止增、唯一数据保护和实际空间差分|X01/X14/X13|

清理：19.146 GiB 明确有排除项；另列 .hermes 42.853 GiB，根 target 再长到5.603 GiB。不能把19.146当全仓总量，也不能把两数相加声称精确实测。逻辑文件大小、分配字节和卷可用空间分别记录。

## 固定来源

- [代码与审校](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed/crates/archeaxis-domain/src/knowledge.rs)
- [归档实现](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed/crates/archeaxis-archive/src/lib.rs)
- [学习事件](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed/crates/archeaxis-domain/src/learning.rs)
- [核查探针](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed/scripts/probes/x07_public_check_probe.py)
- [基线Windows CI](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/34172047879)
- [冻结任务](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed/docs/authority/taskpack-0907/TASKS.json)

旧冻结材料保留在 frozen-r2；其中日期、原始TODO、路径和自报DONE均是历史记录，不覆盖R3。
