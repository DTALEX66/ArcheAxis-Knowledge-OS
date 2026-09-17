# ArcheAxis R4｜唯一活动执行入口

计划ID沿用AAK-FOLLOWUP-20260908-R3；包修订R4；日期2026-09-09。

## 放置与校验

先在交付外层运行`python verify_delivery.py`。外层的private-history、reference-archives是用户保留来源，不复制或提交到公开代码仓库。用用户已选永久workspace或已授权的项目内忽略目录保管；不擅自选择DSH安装目录或其他盘。

仅将active内全部内容放到实际ArcheAxis仓库的`docs/authority/taskpack-0909-r4/`，不要多套active目录。目标存在先比对/保全已有改动，不覆盖。

在真实仓库根运行：
```powershell
python .\docs\authority\taskpack-0909-r4\verify_package.py
```

校验只读，证明任务包结构/继承与文件完整性，不执行安装、授权或产品测试。

## 开始顺序

1. 先读仓库AGENTS和真实授权入口、CONTEXT-HANDOFF.md、CONTEXT-DECISIONS.json、TASKPACK.md、TASKS.json。检查当前branch/HEAD、工作树、已有台账；cbe253b只为9月8日继承起点，绝不强制回退新代码。
2. X00在现有决策机制登记R4增量，唯一入口转到taskpack-0909-r4；保留旧0907、R3.1的原文与tested SHA。plan_only不是权限凭证；不得伪造签名。已有会话授权允许的日常实现连续执行，不按模型品牌重复要许可。
3. 同时读取GOVERNANCE-MIGRATION.md/JSON、HUMAN-LEARNING.md/JSON、LEARNING-CONTRACT.json、ACCEPTANCE.md/JSON。每任务的原work/acceptance、r3与r4增量均须满足；不得只读r4。
4. 先X00/X01/X02止增与保全；X04/X05处理版本/身份/归档/事件；X06/X07接管线和核查；X03/X08/X09完成真实两侧。X14在原依赖满足后提前清理。原任务DAG不变，切片前置还须遵守HUMAN-LEARNING.json。
5. M0只需代表主题与已有互动真实闭环，HL09的三主题/36领域扩展归M1。X10/X11交Windows同源候选，独立Q00；X12/X13/X14收口后Q01。F01—F06仍冻结保留。
6. 用EXECUTION-TEMPLATE.md及R4追加字段更新仓库现有台账；任何新增任务先挂原父任务，不能复制第二活动TASKS。旧包校验PASS不能当产品门PASS。

完整历史只在外层本地查阅。遇到真正缺资源/权限的动作只阻塞该项，继续其他合法就绪任务；不得削减原真实云端核查、迁移、机器执行和Windows门。

## 跨任务切片执行规则

切片是跨任务功能索引，不是额外串行队列。depends_on_slices为整体行为验收前置，不阻塞契约/fixture先行。父任务按原DAG及本表归属贡献验收，不以尚未就绪下游贡献阻塞上游；整条切片闭环在各贡献汇合后验收。HL09/HL12按M0/M1分别检查。具体归属见CONTRIBUTION-MATRIX.md。
