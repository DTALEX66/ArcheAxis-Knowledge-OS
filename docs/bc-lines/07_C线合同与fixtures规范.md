# 07｜C线合同与 fixtures 规范

## 合同原则

```text
A线不直接读取 B线数据库
B线不直接写 Obsidian Vault
双方只交换标准 JSON / Markdown Projection
```

## 必备合同

```text
course_pack.schema.json
context_pack.schema.json
taskpack.schema.json
execution_trace.schema.json
machine_lesson.schema.json
intake_card.schema.json
engineering_contract.schema.json
obsidian_projection.schema.json
```

## fixtures 命名

```text
sample_course_pack.json
sample_context_pack.json
sample_taskpack.json
sample_execution_trace.json
sample_machine_lesson.json
sample_intake_card.json
sample_engineering_contract.json
sample_obsidian_projection.json
```

## ID 规则

```text
course_id: course_xxx
context_id: ctx_xxx
task_id: task_xxx
trace_id: trace_xxx
lesson_id: lesson_xxx
intake_id: intake_xxx
contract_id: contract_xxx
projection_id: proj_xxx
```

## 状态字段

推荐状态：

```text
draft
candidate
approved
active
blocked
archived
```

## 风险字段

```text
low
medium
high
critical
```
