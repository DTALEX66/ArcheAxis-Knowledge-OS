# Runtime Facade Tracer Bullet

## 目标

为现有 Core Runtime 建立一个可运行的公共边界，不复制 Planner、Router、Permission、Executor 或 Trace 实现，也不切断旧 `/run` 入口。

## 交付

- `app/facades/runtime.py` 提供 `execute_runtime()`。
- `RuntimeExecution` 统一返回 route、permission 和可选 trace。
- 安全任务通过现有注册工具执行并写入现有 trace 存储边界。
- 需要人工审核的任务停在 permission，不执行、不写 trace。
- 旧 `/run` 复用 Facade，并继续保留原有状态、document、context、task、eval 和 lesson 字段；安全执行结果新增标准 permission 字段。

## 依赖方向

```text
app.main
  → app.facades.runtime
    → app.core.router
    → app.core.permissions
    → app.agent.executor
    → app.core.trace
```

Facade 只编排现有实现。业务模块不得反向导入 `app.main`，现有底层实现也不得依赖 Facade。

## 验证合同

- route → permission → execute → trace 使用真实低风险 `echo` 工具。
- 高风险 `code_exec` 停在 permission。
- Facade 与旧 `/run` 对相同输入返回可比较的 route、permission 和 trace 合同。

## 回滚

回滚本切片时恢复 `app.main.run()` 的原编排，并删除 `app/facades/runtime.py`、`app/facades/__init__.py` 和对应合同测试；不需要数据库迁移或恢复。
