# Phase 2 TaskPack：版本化 Contracts 与 Legacy Adapter

> 输入基线：`d0e833c997e8fa114bfa55b2e5ea54577dfaca73`。Phase 2 逐个建立 canonical v1 合同和显式 adapter；不直接执行目标 SQL，不修改活动数据库。

## 状态

- TP2.0 已完成：Runtime、KB dataclass、JSON Schema 与 SQLite 字段差异审计。
- TP2.1 已完成：`TaskPackV1`、KB 无损 adapter、Runtime fail-closed 窄投影与 wheel tracer。
- 后续合同不得在未完成实现与 round-trip 证据前进入公共 Facade。

## 已确认差异

| 表面 | 关键字段 | 当前限制 |
| --- | --- | --- |
| Runtime `app.schemas.TaskPack` | `id`、`tools`；risk 最高 `high` | 无 `context_id`、`blocked_tools`、`requires_review` |
| KB `knowledge_base.taskpack.TaskPack` | `task_id`、allowed/blocked、context、review | 当前最完整的 legacy TaskPack 结构 |
| `shared-contracts/taskpack.schema.json` | 与 KB 接近 | 只是候选 Schema，无版本字段且未作为运行时 SSOT |
| SQLite `kb_taskpacks` | JSON 列保存 steps/tools/constraints | 缺 `context_id` 和 `requires_review`，当前写入路径会丢字段 |

因此本轮只证明 KB ↔ canonical 无损往返；canonical 将步骤工具表示为 `requested_tools`，将 KB 策略拆为 `declared_allowed_tools` / `explicitly_blocked_tools`。canonical → Runtime 只投影 requested tools，并报告不可表示字段。`critical`、`requires_review=true`、步骤/请求不一致、blocked/undeclared 请求和策略冲突一律 fail closed。

## Ownership

### 允许

- `app/contracts/`：无业务依赖的版本化 Pydantic 合同。
- `app/adapters/`：canonical 与现有 Runtime/KB 对象之间的纯映射。
- `app/facades/contracts.py`：仅导出已经完成并验证的 Phase 2 表面。
- 对应合同、Guard、集成、wheel smoke 和文档测试。

### 禁止

- 修改 SQLite DDL、迁移或活动数据。
- 让 `app/contracts` 依赖 Runtime、KB、Research、Facade 或 storage。
- 用空值、默认值、risk 降级或字段过滤冒充无损转换。
- 一次性声明 ContextPack、Trace、Evaluation、Lesson 等未实现合同已完成。
- 重写 Planner、Permission、Executor、Evaluator 或 Lesson 语义。

## 垂直任务

### TP2.1 TaskPackV1（首轮）

1. RED：KB TaskPack 经 canonical 往返后每个字段完全一致。
2. RED：Runtime 窄投影显式返回所有不可表示字段。
3. RED：critical risk、requires-review、allowed/blocked 冲突 fail closed。
4. RED：生成 JSON Schema 固定 `schema_version=1.0.0`、稳定 `$id`、拒绝 extra。
5. 旧 IR→KB→OS 集成测试改用 adapter，不再手工复制字段。
6. wheel smoke 从源码目录外导入 canonical 和 adapter。

### TP2.2 SQLite row adapter（后续独立高风险批次）

1. 先为现有缺列写失败 round-trip 测试。
2. 决定显式 sidecar 或正式 migration；不得偷偷推断 `requires_review`。
3. 迁移必须具备 backup、重复运行、回滚和独立 reviewer 证据。

### TP2.3–TP2.6 后续合同

按真实调用链逐个推进 ContextPack、ExecutionTrace/Evaluation/Lesson、Research/Knowledge、Learning/Mastery/MachineKnowledge。每个合同独立 RED→GREEN，不做水平批量占位。

## 验收

- canonical 模型有固定版本、严格 extra policy 和稳定生成 Schema。
- adapter 对可逆路径逐字段往返；窄模型投影公开 loss report。
- 安全语义无法表示时 fail closed。
- Architecture Guard 阻止 `app/contracts` 反向业务依赖。
- 旧入口和 Runtime 类继续可用，不要求数据库恢复。
- 完整门禁、外部 wheel、冻结复核、普通 push 和对应 CI 成功。

## 回滚

TP2.1 只新增 Python 合同/adapter、公共导出和测试，可整提交回滚；没有 SQLite 或用户数据回滚步骤。
