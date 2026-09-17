# ArcheAxis R3｜执行入口

R3.1补强：必须同时读取GOVERNANCE-MIGRATION.md及JSON，完成5项仓库规范化、7项语言迁移切片；TASKS已绑定到原父任务。不能把语言分工说明当迁移已完成，不能把核心调用链迁移整体后置到X13。

计划：AAK-FOLLOWUP-20260908-R3。项目：ArcheAxis Knowledge／星环知识平台。
这是一份续修包，不是新项目，不是 DSH 产品方案，不授权重新选语言或重造平台。

## 安装与校验

将 ZIP 内的 archeaxis-followup-r3-20260908 整个目录放入实际 ArcheAxis 仓库：
`docs/authority/taskpack-0908-r3/`。最终 TASKS.json、TASKPACK.md、verify_package.py 应在该目录同一层，不要再多套一层目录。
不要放到 DSH 安装目录；不要根据 Markdown 猜写缺失 JSON。目录已存在且有改动时先比较、保全，不覆盖。

在真实仓库根运行：
```powershell
python .\docs\authority\taskpack-0908-r3\verify_package.py
```
校验通过只证明任务包文件/映射一致，不证明产品通过审计。

## 按这个顺序开始

1. 读取仓库 AGENTS.md、实际授权入口和工作树。核对 branch/HEAD；基线为 codex/full-loop-0906 的 cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed。若已有更新，逐项核对差异后承接，不回退到本包基线，不冲掉用户改动。
2. 读取 TASKPACK.md、AUDIT-DELTA.md、TASKS.json、ACCEPTANCE.md；frozen-r2 中的旧材料是历史来源，不是第二活动计划。
3. X00 在现有权威/决策机制中登记 R3 增量并把当前指针统一指向此包；继承 R2 全部 work/acceptance 和覆盖要求，只扩充而不悄悄降门。不得覆盖旧0907证据或伪造授权签名。
4. 依照任务内 r3_work、r3_acceptance 和验收场景继续。同一选定执行器可连续完成获授权的就绪切片，不必等另一个品牌模型批准日常实现。独立 GPT 留在 Q00/Q01。
5. 优先修 X04/X05 的身份、版本/归档/事件契约；X07/X08 的核查与事件实现可先做对应修复切片，但整项完成仍必须满足原依赖。X14 在 X01/X02 的保全与止增条件满足后提前做。
6. 交付 X11 可运行 Windows 候选并走 Q00。不要等待 F01—F06 才给用户软件；不要因为有可运行候选就越过尚未通过的必需门禁。

## 每个切片的动作

在现有执行台账登记：父任务ID、具体缺陷/功能ID、精确路径、输入基线、实现、测试命令、环境、结果、输出hash、限制、回滚。
先复用旧代码与已装组件，修改最小范围，完成针对性回归，再跑受影响集成测试。命令从当前仓库及真实环境确认，不编造未存在的测试入口。
状态可用 IN_PROGRESS / BLOCKED_RESOURCE / IMPLEMENTED_PENDING_AUDIT / VERIFIED；VERIFIED 必须附独立适用证据。包内 baseline_state 是审计起点，不是今天又重跑了全部测试。
遇真实权限、保护规则、付费、真实库切换或路径越界要求时停该动作并报告；继续其他合法就绪任务。

## 必须保持

Rust Core 唯一主库权威；Python workers 不直连主库；C#/Avalonia 负责宿主；Web/TS 复用成熟体验。主入口继续验证 DeepTutor。
保留完整人机双侧、个人定义、16能力域、16格式组、11增强、29功能、3D/动画/大型知识宫殿。重型自研保持冻结。
不碰 E 盘，不上传私密内容和真实库，不新增 .hermes 开发产物，不大范围删除。清理只能针对逐项确认、授权的可重建缓存。
本包没有发布授权、没有调用付费 API 授权，也不是绕过仓库守卫的 grant。

交接时使用 EXECUTION-TEMPLATE.md 所列字段更新既有台账，列出仍失败的门禁与用户如何启动实际软件。
