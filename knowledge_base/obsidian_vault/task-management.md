---
tags: [cognitive-loop, task, context-pack]
aliases: [Task Management, Context Pack System]
---

# Task Management

Tracks context packs and task executions within Cognitive-Loop-OS.

## Context Pack Structure

A context pack groups related tasks into an atomic unit:

- **Context Pack** (top-level unit)
  - **Trace** (execution record)
  - **Lesson** (machine learning outcome)
  - **Task Ticket** (atomic action)

### Example Context Pack

```json
{
  "pack_id": "cp-2026-001",
  "tasks": ["task-1", "task-2"],
  "status": "completed"
}
```

## Related

- [[card-system]] — cards are generated from task completion evidence
- [[daily-brief-format]] — summarizes daily task activity
- #task-management/context-pack

> [!warning] Data Bound
> Task artifacts stay inside `.hermes/task-runtime/`. Do not commit runtime data.
