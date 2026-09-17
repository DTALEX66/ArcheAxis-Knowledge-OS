# ArcheAxis全部未完成任务整合包 R5

日期：2026-09-12。完整承接R4，不以本次整理代替当前远端/Windows实测。本次用户追加重点：仓库规范化、语言迁移、最快闭环、大体积瘦身和外溢数据追踪清理。

保留原23任务、29功能、66需求、16能力域、16格式组、11增强、5 GOV+7 LANG、12 HL及38验收场景和完整历史/研究来源。新增18项任务内强制切片：10清理与外溢、4规范化强化、4迁移强化。所有条款映射回原TASKS；F01—F06冻结保留。

当前完成状态：继承9月8日历史基线与R4规划；本次未查询最新HEAD或访问本机盘，所有新增项为待实现。X00先按真实收据更新现有台账，保留已完成成果；未确认项纳入续修清单，不能凭旧标题认为已做完。

## 三个重点专项

- CLEANUP-AND-SPILL.md：范围与体积基线、外溢生产者溯源、写入止增、唯一数据保全、重复辨别、清单预演/隔离、精确清理、实际释放及回归、预算轮转、Git/安装包瘦身。
- REPOSITORY-NORMALIZATION.md：唯一规则入口、全仓归属、依赖/构建/发布一致、默认启动及安装可用。
- LANGUAGE-MIGRATION-EXECUTION.md：模块迁移台账、Rust真实权威、Python worker化、Avalonia/Web实际接线、旧库兼容及旧入口退役。M0关键链迁移不能后置到M1。

## 快速执行

先X00核状态，X01/X02止增和保全；X14在原依赖满足后立即推进，不等首版全部结束。X04/X05修权威底座，X03/X06/X07接界面/管线/核查，X08/X09完成真实人机双侧，X10/X11交Windows候选与恢复，Q00独立审计。X12/X13/X14完成全格式、学科、全仓剩余迁移和容量收口，再Q01。具体交付见FASTEST-LOOP.md。

## 数据保全与测量

历史50多GB不是当前实测。只测批准范围，明确逻辑大小/实际分配/卷空闲；不跟随junction，不重算父子目录或硬链接，不按同名直接删除。共享模型、跨项目缓存、真实库、未提交代码和唯一会话/补丁/审计记录保留。隔离同卷不算释放；删除后用相同范围复测并运行受影响功能。

外溢项必须追到生产者、配置与所有权；先修写入源再清旧数据。不是整盘扫描/清空许可，不访问E或未授权位置，不改全局HOME/CODEX_HOME。Git历史重写、force-push、删除旧tag不在默认清理动作内。

## 交付结构

active是唯一新活动任务包；history-r4保留上一版完整交付及原始历史，不能作为当前规则入口，也不要提交到公开仓库。从active/EXECUTOR-START.md执行。表格模板只提供字段，没有伪造本机测量值。verify_package.py及外层校验只验证任务包完整性，不证明产品质量或实际释放空间。

## 全部任务索引

|任务|继承状态（待X00复核）|新增切片|
|---|---|---|
|X00 基线、冲突裁决与唯一任务入口|REOPENED|CLEAN01, REPO01|
|X01 运行路径止增、浏览器失败与关键 CI|PARTIAL|CLEAN03, CLEAN04, CLEAN09, REPO03|
|X02 旧资产保全与当前能力的语义复用|PARTIAL|CLEAN01, CLEAN02, CLEAN03, CLEAN05, REPO02, MIG01|
|X03 现成学习工作台资格与默认入口|PARTIAL|REPO04, MIG03|
|X04 跨语言真实契约及身份语义|REOPENED|MIG01, MIG02, MIG03|
|X05 Rust原件、事务、作业与恢复底座|REOPENED|MIG02, MIG04|
|X06 复用workers贯通首批真实格式|PARTIAL|MIG03|
|X07 质量、公开核查、知识修订和搜索|REOPENED|MIG02|
|X08 人类学习侧复用与事件回收|PARTIAL|MIG03|
|X09 机器知识、真实调用、评测与反馈|PARTIAL|MIG03|
|X10 旧库非空迁移与无损差分|PARTIAL|CLEAN05, MIG04|
|X11 Windows人机闭环候选与可用包|PARTIAL|CLEAN08, REPO03, REPO04, MIG04|
|Q00 独立GPT审计M0|FAILED_AT_BASELINE|保留原要求|
|X12 多格式完整覆盖与学科活动|PARTIAL|保留原要求|
|X13 全仓规范化与必要交付体验收口|PARTIAL|CLEAN09, CLEAN10, REPO01, REPO02, REPO03, REPO04, MIG01, MIG04|
|X14 本地50多GB保全清理与容量止增|PARTIAL|CLEAN02, CLEAN03, CLEAN05, CLEAN06, CLEAN07, CLEAN08, CLEAN09, CLEAN10|
|Q01 独立GPT审计M1及清理结果|NOT_READY|保留原要求|
|F01 视觉教学、动画与交互仿真|DEFERRED_RETAINED|保留原要求|
|F02 大型知识宫殿与2D/2.5D/3D/VR/AR|DEFERRED_RETAINED|保留原要求|
|F03 完整人机学习、经验迁移和可选微调|DEFERRED_RETAINED|保留原要求|
|F04 多端同步、SDK、扩展和可选协作|DEFERRED_RETAINED|保留原要求|
|F05 研究课程项目工作空间与图谱纵深|DEFERRED_RETAINED|保留原要求|
|F06 吸收失败后的必要独立实现|DEFERRED_RETAINED|保留原要求|
