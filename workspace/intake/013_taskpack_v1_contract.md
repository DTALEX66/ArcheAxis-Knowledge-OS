# TaskPackV1 Contract Tracer

## 目的

Phase 1 的 Contracts Facade 只 identity re-export `app.schemas`。Phase 2 第一枪以现有 KB TaskPack 为信息最完整的 legacy 输入，建立 `TaskPackV1`，但不宣称其他合同或 SQLite 已完成版本化。

## 数据流

```text
knowledge_base.taskpack.TaskPack
→ from_knowledge_taskpack
→ app.contracts.v1.TaskPackV1
→ to_knowledge_taskpack (无损)

TaskPackV1
→ project_to_runtime
→ RuntimeTaskProjection(task, unmapped_fields)
```

## 边界

- `schema_version` 固定为 `1.0.0`，生成 JSON Schema 带稳定 `$id`。
- Pydantic `extra="forbid"`，未知字段不能静默忽略。
- KB 往返保留 context、allowed/blocked tools、constraints、criteria、risk 和 review；canonical 将步骤实际工具记为 `requested_tools`，把策略字段分别记为 `declared_allowed_tools`、`explicitly_blocked_tools`。
- Runtime 没有 `context_id`、`blocked_tools`、`requires_review`，所以只提供显式窄投影。
- Runtime 只接收 `requested_tools`，不得把 declared allowed 列表当作请求执行列表。
- `requires_review=true`、critical risk、步骤工具与 requested 不一致、请求 blocked/undeclared 工具或 allowed/blocked 交集都会抛出 `ContractMappingError`。
- `app/contracts` 由 Architecture Guard 约束为纯合同层；legacy 依赖只能位于 `app/adapters`。

## SQLite 阻塞

`kb_taskpacks` 当前没有 `context_id` 和 `requires_review`。本 tracer 不改 DDL，也不把缺失值伪装成默认值。SQLite row adapter 留给带 migration/rollback 的独立任务。

## 回滚

删除 `app/contracts`、`app/adapters`、Facade 新导出和对应测试即可；不涉及数据库或外部资源。
