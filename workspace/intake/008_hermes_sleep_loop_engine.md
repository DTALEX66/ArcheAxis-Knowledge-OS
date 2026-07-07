# 008 HERMES 就寝无人值守循环引擎

> Status: implemented-v0.1
> Date: 2026-07-07
> Scope: night-time unattended task splitting, durable queue ledger, loop worker, FastAPI control surface, and local dashboard.

## 背景

用户定义夜间就寝场景：用户休息后不再交互，HERMES 需要在后台持续运行，自动拆解任务、执行队列、捕获衍生任务、完成一轮后进入下一轮，直到用户手动终止。

## 本轮决策

当前 Cognitive-Loop-OS 的实际运行时是 Python/FastAPI + SQLite，仓库内没有 Node 主服务、Redis/MySQL 部署基线。因此 v0.1 采用本地优先方案：

- SQLite 作为无人值守任务账本，表结构保留未来 MySQL 迁移边界。
- 数据库状态队列替代 Redis 队列，字段保留待执行/执行中/完成/失败/阻断状态。
- FastAPI 暴露复合端点 `/sleep-loop?action=...`，避免继续增加大量单用途 API。
- `scripts/sleep_loop_worker.py` 作为常驻 tick worker，`ecosystem.config.cjs` 提供 PM2 守护配置。
- `index.html` 作为本地控制面板，轮询状态、任务与日志。

## 已固化边界

- 单次拆解默认 20，锁死 50。
- 全局队列上限 200。
- 单任务衍生任务最多 8。
- 单任务失败最多重试 3 次，耗尽归档。
- 就寝并发配置锁死 4。
- 单任务超时 120s。
- CPU 超阈进入冷却；内存超阈先 GC，仍超则熔断。
- 高危任务进入队列会被硬边界拦截并记录日志。
- 就寝模式不弹窗、不语音、不外发第三方通知。

## 产物

- `shared/sleep_loop_engine.py`
- `app/main.py` `/sleep-loop` 复合 API
- `scripts/sleep_loop_worker.py`
- `ecosystem.config.cjs`
- `index.html`
- `docs/HERMES_SLEEP_LOOP_ENGINE.md`
- `tests/test_sleep_loop_engine.py`

## 验证

- `python -m pytest tests/test_sleep_loop_engine.py -q --tb=short` → 4 passed
- `python -m pytest tests -q --tb=short` → 82 passed
- `cd Knowledge-Base && python -m pytest tests -q --tb=short` → 28 passed
- `python -m ruff check shared/sleep_loop_engine.py scripts/sleep_loop_worker.py tests/test_sleep_loop_engine.py --select E,F,B --statistics` → 0 errors

## 后续

- 可将 SQLite 队列迁移到 Redis/MySQL 双层架构。
- 可将 CPU 超阈升级为持续 60s 窗口，异常终止升级为 10min 窗口。
- 可补 `/sleep-loop` 到正式鉴权/角色体系，而不是当前复用本地 API key。
