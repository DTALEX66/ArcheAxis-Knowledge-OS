# CC Task 系统 — A 线规划 + B 线编排参考

## 文件位置：src/utils/tasks.ts（779 行）

## 核心概念

```
Task ─┬─ id: string（唯一标识）
      ├─ status: pending | in_progress | completed（状态机）
      ├─ owner: string | null（Agent 持有者）
      ├─ blockedBy: string[]（依赖阻塞列表）
      └─ createdBy: string | null（创建者）
```

## 三大机制

### 1. 文件锁（proper-lockfile）

```typescript
// 每个 task 对应一个文件，文件锁保证了原子操作
release = await lockfile.lock(taskPath, LOCK_OPTIONS)
// 读取 → 检查 → 修改 → 释放
await release()
```

应用场景：
- 多 Agent 同时操作同一 task 时防止竞态
- taskList 级别锁用于跨 task 原子操作
- LOCK_OPTIONS 含超时和重试配置

### 2. 原子 Claim（claimTask）

```typescript
claimTask(taskListId, taskId, claimantAgentId):
  1. 检查 task 是否存在（提前返回 task_not_found）
  2. 获取文件锁（防止 TOCTOU 竞态）
  3. 读取当前状态
  4. 检查是否已被其他 Agent 持有（already_claimed）
  5. 检查是否已完成（already_resolved）
  6. 检查依赖性阻塞（blockedBy 列表）
  7. 写入 owner → 完成 Claim

失败原因: task_not_found | already_claimed | already_resolved | blocked
```

### 3. 阻塞依赖（blockedBy）

```typescript
// Task A 依赖 Task B 完成
taskA.blockedBy = ["taskB_id"]

// claimTask 时自动检查：
const unresolvedTaskIds = allTasks
  .filter(t => t.status !== "completed")
  .map(t => t.id)
const blockedByTasks = task.blockedBy
  .filter(id => unresolvedTaskIds.has(id))

// 如果有未解决的阻塞，返回 blocked 状态
if (blockedByTasks.length > 0) {
  return { success: false, reason: "blocked", blockedByTasks }
}
```

## 辅助函数

| 函数 | 功能 |
|------|------|
| createTask() | 创建 task，写入文件 |
| getTask() | 读取单个 task |
| updateTask() | 更新（含锁） |
| updateTaskUnsafe() | 无锁更新（仅在持有锁时使用） |
| deleteTask() | 删除 task 文件 |
| listTasks() | 列出所有 task（读取目录） |
| blockTask() | 设置阻塞关系 |
| claimTask() | 原子抢占（核心） |
| claimTaskWithBusyCheck() | 带 Agent 繁忙检测的原子抢占 |

## → A 线迁移映射（学习路径规划）

```text
知识点 = Task
知识点状态: 未学(pending) → 学习中(in_progress) → 已掌握(completed)
前置依赖 = blockedBy

学习流程：
  创建知识路径 → 锁定当前知识点 → 学习完成 → 解锁 → 触发下一个
  复习规划：
    按优先级排序 → 逐个 claim → 复习 → 完成
```

## → B 线迁移映射（DEEP 任务编排）

```text
DEEP 任务 = Task
任务依赖 = blockedBy
Agent 持有 = owner
CODEX = 任务分配器
DEEP Worker = claimTask 的 Agent

并行执行流程：
  CODEX 创建 DEEP-01~99 任务
  ↓
  多个 DEEP Worker 并行 claimTask
  ↓
  锁机制确保每个任务只被一个 Worker 执行
  ↓
  blockedBy 确保依赖任务按顺序执行
  ↓
  所有任务完成 → 合并结果
```
