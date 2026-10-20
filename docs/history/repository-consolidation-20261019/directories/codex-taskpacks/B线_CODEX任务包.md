# B线 CODEX 任务包

## 目标

让 `Inspiration-Research + Knowledge-Base + Cognitive-OS` 在不依赖 Obsidian 的情况下，独立跑通最小核心闭环。

## 禁止事项

```text
禁止修改正式 Obsidian Vault
禁止执行 shell/code_exec
禁止读取密钥
禁止跨盘扫描
禁止删除文件
```

## 第一批任务

### Task B1：建立 shared schema 引用

输入：

```text
shared-contracts/schemas/*.json
```

输出：

```text
三个项目都能读取并校验 schema
```

验收：

```text
fixtures 全部通过 schema validation
```

### Task B2：IR 生成 IntakeCard

输入：

```text
research_note.md 或 raw research text
```

输出：

```text
intake_card.json
```

验收：

```text
字段完整：why / what_to_absorb / what_not_to_absorb / risk_level
```

### Task B3：IR 生成 EngineeringContract

输入：

```text
intake_card.json
```

输出：

```text
engineering_contract.json
```

验收：

```text
包含 goal / deliverables / acceptance_criteria / blocked_actions
```

### Task B4：KB 生成 ContextPack

输入：

```text
engineering_contract.json
source evidence
```

输出：

```text
context_pack.json
```

验收：

```text
包含 goal / sources / evidence / constraints
```

### Task B5：KB 生成 TaskPack

输入：

```text
context_pack.json
```

输出：

```text
taskpack.json
```

验收：

```text
包含 steps / allowed_tools / blocked_tools / success_criteria / risk_level
```

### Task B6：Cognitive-OS 执行 mock TaskPack

输入：

```text
taskpack.json
```

输出：

```text
execution_trace.json
machine_lesson.json
```

验收：

```text
低风险任务 success
高风险任务 blocked
所有步骤有 trace
```
