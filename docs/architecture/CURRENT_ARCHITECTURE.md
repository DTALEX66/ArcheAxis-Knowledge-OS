# 当前运行时架构

> 本文描述当前代码，不描述远期蓝图。实时路由数由 `/health` 递归计算，不在文档里写死。

## 运行拓扑

```text
Client / Agent / Cron
        │
        ▼
app.main :8000
├── Public Facades
│   ├── runtime.py (route → permission → execute → trace)
│   ├── knowledge.py (read-only keyword/FTS query)
│   ├── research.py (persisted IntakeCard candidate)
│   ├── enhancement.py (in-memory summary/card/quality candidate)
│   └── contracts.py (Phase 2 首批 V1 contracts + verified adapters; legacy runtime objects remain identity exports)
├── Core Runtime
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
| Knowledge | tracer bullet 已接入 | `knowledge_base.search.keyword_search` | standalone `/search`、mounted `/kb/search` |
| Research | tracer bullet 已接入 | `inspiration_research.intake.generator`、`shared.storage` | canonical IR API；旧 `Inspiration-Research.api` launcher |
| Enhancement | tracer bullet 已接入 | `progressive_summarize`、`generate_from_markdown`、`audit_markdown_quality` | 现有细粒度能力保持不变 |
| Contracts | Phase 2 首批 tracers 已完成 | Runtime、Research、Knowledge/Relation、Learning/Mastery 与 Machine Knowledge V1 contracts + 现有真实对象 adapters；legacy runtime objects 仍 identity re-export | 当前对象导入 |

Runtime Facade 只编排现有实现：允许 `app.main → app.facades → app.core/app.agent`，禁止底层业务模块反向依赖 Facade 或主应用。旧 `/run` 仍保留，回滚不需要数据库迁移。

Knowledge Facade 当前只承诺 keyword 模式，不把 vector/hybrid 实现细节提升为稳定合同。Research 返回并持久化的是 `IntakeCard` candidate。Enhancement 只返回内存 candidate，不写数据库、不调用网络或 LLM。Contracts 已完成路线图首批 V1 对象，但不声明与旧 JSON Schema 全量等价；未列入首批清单的 `ContextPackV1` 与通用 validator 仍 deferred。

`app/contracts/` 是纯 canonical 层，由 Architecture Guard 禁止反向依赖业务模块；`app/adapters/` 承担 KB/Runtime/SQLite row 映射。KB TaskPack 可逐字段无损往返；Runtime 窄投影公开不可表示字段并 fail closed。Research contracts 保持来源、claim、evidence、冲突、未知与风险边界。Knowledge graph rows 保留属性与有向关系；Mastery Signal 由 review/mistake 快照推导。Learning Artifact 对当前 Enhancement candidate 深隔离往返，caller-supplied 数据只能保持 candidate 且必须人工复核。Machine Knowledge 对 decoded legacy row 深隔离往返，旧 active 只映射为 `legacy_active_unverified`，inactive 映射为 `deprecated`，任何 approved 状态向旧行投影都会 fail closed。

## Architecture Guard

`scripts/check_architecture.py` 使用 AST 扫描生产 Python 树。CI 会拒绝新增 `sys.path` 变异、Contracts/Platform 反向业务依赖、底层运行时反向 Facade 依赖，以及个人目录或外部盘符硬编码。历史兼容点按文件、行号和 AST 表达式精确 grandfather，不允许目录级宽泛豁免。

## 当前债务

- `knowledge_base/api.py` 已将复合、质量和投影路由拆出，但仍有遗留领域路由；后续按 search/learning/obsidian/admin 继续迁移。
- Knowledge Base 已迁为正规可安装包；2026-07-14 本地隔离 wheel smoke 已验证模板、运行入口和 runtime root，远端 CI 仍以提交后的实际结果为准。
- 旧细粒度 API 尚未全部隐藏或废弃，因此实时路由数仍较高。
