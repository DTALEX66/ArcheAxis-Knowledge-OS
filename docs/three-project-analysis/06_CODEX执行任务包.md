# CODEX 执行任务包

## 总目标

将 `Knowledge-Base + Inspiration-Research + Cognitive-OS` 聚合为一个可开发、可测试、可扩展的 Cognitive Loop OS。

---

## Task 1：建立总项目文档

目标文件：

```text
SYSTEM_MANIFEST.md
PROJECT_BOUNDARY.md
ASSET_REGISTRY.md
DATA_CONTRACT.md
ROADMAP.md
DECISIONS.md
```

验收：

```text
三项目职责清楚
active / experimental / roadmap 分层清楚
每个资产类型有唯一解释
```

---

## Task 2：Cognitive-OS SQLite 化

当前：

```text
memory.jsonl
lessons.jsonl
trace.jsonl
```

目标：

```text
data/cognitive_os.sqlite
```

表：

```text
core_objects
routes
memory_records
taskpacks
execution_traces
eval_results
machine_lessons
tool_calls
permission_decisions
```

验收：

```text
/run 仍能跑通
/memory/search 可用
/traces 可用
/memory/lessons 可用
```

---

## Task 3：RoutePolicy 独立化

目标：

```text
app/core/route_policy.py
app/core/risk_policy.py
```

把 router.py 中的关键词、风险词、低价值词、route priority 拆成可配置策略。

验收：

```text
空输入 DROP
低价值输入 DROP
高风险输入 REVIEW
学习输入 KB
研究输入 IR
执行输入 TASK
```

---

## Task 4：PermissionDecision

新增：

```text
PermissionDecision
risk_level
allowed_tools
blocked_tools
requires_human_review
reason
```

所有 TaskPack 执行前必须过 permission check。

验收：

```text
code_exec 默认 blocked
safe_write 默认 dry-run
高风险任务不能执行
```

---

## Task 5：KB ContextPack / TaskPack 合同

目标：

```text
shared/schemas/context_pack.schema.json
shared/schemas/taskpack.schema.json
```

Cognitive-OS 接收 KB 生成的标准 TaskPack。

验收：

```text
TaskPack 有 goal / steps / constraints / tools / risk / success_criteria
Trace 能记录每一步
```

---

## Task 6：IR Intake Card 合同

目标：

```text
shared/schemas/intake_card.schema.json
shared/schemas/engineering_contract.schema.json
```

验收：

```text
Research Note 能转 Intake Card
Intake Card 能转 Engineering Contract
Engineering Contract 能进入 KB experimental
```

---

## Task 7：Adapter 骨架

目录：

```text
shared/adapters/
  converters/
  crawlers/
  vector/
  llm/
  observability/
  memory/
  graph/
  security/
```

先实现：

```text
markitdown_adapter.py
native_text_adapter.py
local_trace_adapter.py
```

验收：

```text
Adapter 不直接写核心库
Adapter 输出标准对象
失败可降级
```

---

## Task 8：测试体系

新增测试：

```text
tests/test_router.py
tests/test_ingestion_file.py
tests/test_tools_registry.py
tests/test_run_loop.py
tests/test_permission.py
tests/test_sqlite_memory.py
```

验收：

```text
所有核心路径有测试
危险路径有测试
路径穿越有测试
```
