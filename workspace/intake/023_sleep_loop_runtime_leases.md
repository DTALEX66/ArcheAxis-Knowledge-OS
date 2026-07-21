# 023 Sleep Loop Runtime 与租约账本

## 目标

将就寝无人值守循环从独立工具执行器收敛到统一 Runtime execution port，同时保留可跨进程恢复、可审计、可停止的持久任务账本。

```text
Sleep task request
→ idempotent durable queue
→ atomic lease claim + attempt receipt
→ Sleep TaskPack projection
→ canonical Runtime facade
→ trace-bound terminal receipt
→ typed derived-task replan
```

## 架构边界

- `shared.sleep_loop_engine` 只负责队列、状态机、租约、heartbeat、恢复和 receipt，不反向导入 `app` facade。
- `app.sleep_runtime` 是组合根：把 Sleep ledger task 投影为 Runtime TaskPack，再调用唯一 Runtime facade。
- HTTP API 与独立 worker 都从该组合根执行 tick；未配置 Runtime callable port 时 fail closed。
- 仅 Runtime 返回的结构化 `derived_tasks` 可生成子任务。普通工具文本中的 `TODO:`、`NEXT:` 等内容不是控制指令。

## 持久性与并发语义

- 入队请求在 run 内由 idempotency key 与规范化 fingerprint 去重；同 key 不同请求拒绝。
- claim 使用 SQLite `BEGIN IMMEDIATE`，同时写 task lease 和唯一 attempt receipt。
- worker 必须持有 exact owner/token 才能 heartbeat 或提交终态。
- lease 过期后，只读 executor 可重排；结果未知的写 executor 进入 reconciliation-required，不自动重放。
- pause 阻止新 claim，但不破坏已领取任务；stop 原子关闭 running task、lease 和 attempt receipt。
- dependency 必须引用同一 run 中已经存在的 task。依赖边只从新任务指向既有任务，因此队列 API 不允许构造环。
- 父任务的 typed derived child 保存 `parent_id`、cycle 和独立 fingerprint；非法 child 单独记录拒绝事件，不回滚已完成父任务。

## Schema ownership

`sleep-loop.sqlite` 是 MigrationOperator 的独立 SQLite owner，管理 run、task、attempt、event 表及索引。启动与测试均要求 operator provenance；禁止先旁路建表再伪补 provenance。

Legacy upgrade 对无 lease 的旧 `running` 行分类处理：安全读任务重排，潜在副作用任务进入人工协调状态。rollback 通过受验证备份恢复旧 ledger。

## 验收

- `tests/test_sleep_loop_engine.py`：并发 claim、lease、heartbeat、pause/stop、dependency、幂等、typed replan、attempt receipt 和跨进程 restart/readback。
- `tests/test_sleep_loop_migration.py`：owner apply、legacy upgrade、drift 与 rollback。
- `tests/test_sleep_taskpack_adapter.py`：Sleep ledger 到 Runtime TaskPack 的投影边界。
- `tests/test_architecture_guard.py`：禁止 shared 层反向依赖 Runtime facade。

发布前仍须通过 Root、Knowledge Base、Integration、Ruff、Architecture Guard、冻结 tree 的 Blocker/High 审查与 exact-SHA CI。
