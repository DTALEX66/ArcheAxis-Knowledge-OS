# TaskPack AXDESK-A3：认知画布与证真回放

## 风险

高风险：涉及跨 Research、Knowledge、Runtime 的只读统一投影。

## 原则

先只读，再考虑编辑。
Canvas 节点必须来自真实合同，不能成为另一套影子数据模型。

## 三种画布

### Research Canvas

- Source
- Claim
- Evidence
- Conflict
- Unknown
- Research Package

### Knowledge Canvas

- Knowledge Unit
- Relation
- Learning Artifact
- Mastery Signal
- Machine Knowledge

### Execution Canvas

- Goal
- Context Pack
- Plan
- Permission
- Tool
- Evidence
- Evaluation
- Human Decision
- Lesson

## 证真回放

支持：

- 时间线；
- 图模式；
- 输入输出摘要；
- Evidence；
- Retry lineage；
- Human decision；
- Evaluation；
- Lesson；
- 从已存在 checkpoint 回读。

不支持：

- 修改历史；
- 客户端构造 Evidence；
- 从 UI 静默晋升知识；
- 缺少后端合同的“从这里重跑”按钮。

## 验收

- Node/Edge identity 可重算；
- 公共投影不泄露内部 ID；
- Source/Claim/Evidence 绑定可验证；
- Replay 与持久化状态一致；
- 刷新和重启后一致；
- 大画布性能基准；
- 键盘和屏幕阅读器可操作。
