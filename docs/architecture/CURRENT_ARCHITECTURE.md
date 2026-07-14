# 当前运行时架构

> 本文描述当前代码，不描述远期蓝图。实时路由数由 `/health` 递归计算，不在文档里写死。

## 运行拓扑

```text
Client / Agent / Cron
        │
        ▼
app.main :8000
├── Core Runtime
│   ├── facades/runtime.py (public route → permission → execute → trace boundary)
│   ├── ingest / route / run
│   ├── retrieval / tools / evaluation
│   ├── memory / trace / lesson
│   └── sleep-loop
└── /kb mounted sub-application
    ├── routers/composite.py
    ├── routers/quality.py
    ├── routers/projection.py
    ├── legacy domain routes in api.py
    └── dashboard / search / cards / reviews / graph
        │
        ▼
SQLite + FTS5 + sqlite-vec + NetworkX + local artifacts
```

## 主闭环

```text
input
→ attention route
→ retrieve
→ compile fixed echo-based steps
→ permission
→ execute registered tool (often echo in the current planner path)
→ trace
→ binary success evaluation
→ candidate lesson
→ memory
```

## 知识质量闭环

```text
source inventory
→ multi-format extraction
→ per-file processing manifest
→ content/fact extraction
→ content-matched evidence
→ caller-supplied source-independence summary (candidate only)
→ human-truth accuracy benchmark
→ KB index
```

## 模块规则

1. `app/` 负责认知运行时，不直接承载所有知识领域实现；`app/facades/` 是跨模块调用的公共边界。
2. `knowledge_base/routers/` 是稳定 API 表面；`api.py` 中的旧路由是待收敛兼容层。
3. `shared/` 保存可跨 Core、KB、IR 复用的无 UI 能力。
4. `shared-contracts/` 保存合同和适配器；适配器不得返回伪成功。
5. `workspace/` 和 `docs/architecture/imported-designs/` 是方向记录与参考，不进入运行时导入。
6. 运行时数据、日志、数据库、模型和用户知识不进入 Git。

## Facade 所有权

| Facade | 状态 | 当前委托实现 | 兼容入口 |
| --- | --- | --- | --- |
| Runtime | tracer bullet 已接入 | `app.core.router`、`app.core.permissions`、`app.agent.executor`、`app.core.trace` | `POST /run` |
| Knowledge | 待实现 | `knowledge_base` 稳定入口 | `/kb/*` |
| Research | 待实现 | `Inspiration-Research` 兼容实现 | IR API |
| Enhancement | 待实现 | 现有摘要、卡片与质量模块 | 现有 KB API |
| Contracts | 待实现 | `app.schemas`、`shared-contracts` | 当前对象导入 |

Runtime Facade 只编排现有实现：允许 `app.main → app.facades → app.core/app.agent`，禁止底层业务模块反向依赖 Facade 或主应用。旧 `/run` 仍保留，回滚不需要数据库迁移。

## Architecture Guard

`scripts/check_architecture.py` 使用 AST 扫描生产 Python 树。CI 会拒绝新增 `sys.path` 变异、Contracts/Platform 反向业务依赖、底层运行时反向 Facade 依赖，以及个人目录或外部盘符硬编码。历史兼容点按文件、行号和 AST 表达式精确 grandfather，不允许目录级宽泛豁免。

## 当前债务

- `knowledge_base/api.py` 已将复合、质量和投影路由拆出，但仍有遗留领域路由；后续按 search/learning/obsidian/admin 继续迁移。
- Knowledge Base 已迁为正规可安装包；2026-07-14 本地隔离 wheel smoke 已验证模板、运行入口和 runtime root，远端 CI 仍以提交后的实际结果为准。
- 旧细粒度 API 尚未全部隐藏或废弃，因此实时路由数仍较高。
