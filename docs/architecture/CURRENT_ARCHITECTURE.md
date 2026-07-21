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
│   ├── research.py (GitHub quarantine → provenance graph → persisted candidate ResearchPackage)
│   ├── enhancement.py (in-memory summary/card/quality candidate)
│   └── contracts.py (Phase 2 首批 V1 contracts + verified adapters; legacy runtime objects remain identity exports)
├── Core Runtime
│   ├── ingest / route / run
│   ├── retrieval / tools / evaluation
│   ├── memory / trace / lesson
│   └── sleep-loop
├── /workspace local product shell
│   ├── URL / GitHub / file intake
│   ├── aggregate status / diagnostics
│   └── synchronous Job / Outbox / Receipt persistence
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

数据库和索引变更由 `shared.migration_runner.MigrationOperator` 统一编排。确定性 registry 注册九个 owner：Core、TaskPack、Phase 4 Research、Knowledge Governance、Workspace SQLite，以及 Vector/FTS documents/cards；SQLite owner 复用 `shared/migration.py` 的 ledger、verified backup/manifest、幂等、碰撞检测与 offline rollback，并在同一 schema transaction 内写入 operator provenance。当前 schema 的 fresh TaskPack 表在 ledger-only apply 前仍创建 verified backup；缺失目标表的空数据库 fail closed。TaskPack whole-file rollback 先核对排除 operator 元数据的 post-apply 逻辑 fingerprint，数据/架构漂移时拒绝恢复，并在临时 replacement 中保全当前 operator provenance 后才原子替换。FTS owner 使用无 import-time storage 初始化的显式目标模块；Vector candidate 同时校验 ID、embedding-byte fingerprint 与 canonical source snapshot；Vector/FTS active switch、rollback handle 与 applied provenance 同 transaction 提交，Vector rollback 也在同一 transaction 内恢复 active rows 并清理 candidate/backup。跨进程 owner lease 位于目标数据库相邻的隐藏 SQLite sidecar（`.<database-name>.<path-digest>.migration_operator_locks.lockdb`，digest 为 resolved database path 经 case-fold 后 SHA-256 的前 16 位十六进制字符），目标数据库替换不会释放 lease，且 token-scoped release 不会删除其他进程的 lease；显式 backup 目录仅保存 verified backup 与 manifest。CLI 仅接受显式数据库与 backup 目录，并输出 pending/applied/failed/rolled_back provenance。

## 主闭环

```text
input
→ attention route
→ retrieve
→ plan supported explicit intent (`read file:` currently verified)
→ permission
→ execute registered tool
→ validate attributable non-dry-run evidence
→ trace
→ multidimensional execution/status/evidence evaluation
→ candidate lesson
→ memory
```

不支持的 Goal 不得 fallback 为 echo 成功；echo、no-op、preview 和 dry-run 不是成功证据。当前只把 `read file:` 作为已验证纵向切片，尚未宣称通用 Dynamic Planner 完成。

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

## 主网关安全边界

- 生产与开发 runtime 不内置管理员凭据；凭据必须由 operator 或隔离测试 fixture 显式提供。
- Token 签发重新认证调用者，普通调用者不能通过请求字段选择管理员角色。
- 主网关按普通读、敏感写和 `/auth/token` 使用独立限流策略；认证 API Key/JWT subject 与匿名 peer 分桶不保存原始凭据。
- 所有仓库拥有的 Uvicorn 启动入口禁用隐式 proxy-header rewriting。只有直接 peer 命中显式 `trusted_proxies` 时才解析 XFF；未受信代理头与双凭据早期拒绝同样消耗 pre-auth 预算。
- 当前 Rate Limiter 为单进程内存实现；文档不把它描述为多进程或分布式一致限流器。

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
| Runtime | `file_read` 真实证据 tracer 已接入 | `app.agent.planner`、`app.core.permissions`、`app.agent.executor`、`shared.tool_evidence`、多维 evaluator | `POST /run` |
| Knowledge | tracer bullet 已接入 | `knowledge_base.search.keyword_search` | standalone `/search`、mounted `/kb/search` |
| Research | GitHub candidate-only 持久化闭环已接入 | `app.research.github`、`shared.research_store`、`MigrationOperator` owner `research.sqlite` | `POST /research/github-repository`、`GET /research/packages/{package_id}`；旧 external trending/auto 路径 fail closed |
| Enhancement | tracer bullet 已接入 | `progressive_summarize`、`generate_from_markdown`、`audit_markdown_quality` | 现有细粒度能力保持不变 |
| Contracts | Phase 2 首批 tracers 已完成 | Runtime、Research、Knowledge/Relation、Learning/Mastery 与 Machine Knowledge V1 contracts + 现有真实对象 adapters；legacy runtime objects 仍 identity re-export | 当前对象导入 |

Runtime Facade 只编排现有实现：允许 `app.main → app.facades → app.core/app.agent`，禁止底层业务模块反向依赖 Facade 或主应用。旧 `/run` 仍保留，回滚不需要数据库迁移。

Knowledge Facade 当前只承诺 keyword 模式，不把 vector/hybrid 实现细节提升为稳定合同。Research 的 GitHub source path 返回并持久化完整 candidate graph：quarantined `SourceRecordV1`、source provenance、`ClaimV1`、`EvidenceV1`、governance findings、`ResearchPackageV1` 和受内容约束的 IntakeCard relation；写前与 strict read 都重算身份和 provenance，不提供自动 promotion。Enhancement 只返回内存 candidate，不写数据库、不调用网络或 LLM。Contracts 已完成路线图首批 V1 对象，但不声明与旧 JSON Schema 全量等价；未列入首批清单的 `ContextPackV1` 与通用 validator 仍 deferred。

`app/contracts/` 是纯 canonical 层，由 Architecture Guard 禁止反向依赖业务模块；`app/adapters/` 承担 KB/Runtime/SQLite row 映射。KB TaskPack 可逐字段无损往返；Runtime 窄投影公开不可表示字段并 fail closed。Research contracts 保持来源、claim、evidence、冲突、未知与风险边界。Knowledge graph rows 保留属性与有向关系；Mastery Signal 由 review/mistake 快照推导。Learning Artifact 对当前 Enhancement candidate 深隔离往返，caller-supplied 数据只能保持 candidate 且必须人工复核。Machine Knowledge 对 decoded legacy row 深隔离往返，旧 active 只映射为 `legacy_active_unverified`，inactive 映射为 `deprecated`，任何 approved 状态向旧行投影都会 fail closed。

## Architecture Guard

`scripts/check_architecture.py` 使用 AST 扫描生产 Python 树。CI 会拒绝新增 `sys.path` 变异、Contracts/Platform 反向业务依赖、底层运行时反向 Facade 依赖，以及个人目录或外部盘符硬编码。历史兼容点按文件、行号和 AST 表达式精确 grandfather，不允许目录级宽泛豁免。

## 当前债务

- `knowledge_base/api.py` 已将复合、质量和投影路由拆出，但仍有遗留领域路由；后续按 search/learning/obsidian/admin 继续迁移。
- Knowledge Base 已迁为正规可安装包；2026-07-14 本地隔离 wheel smoke 已验证模板、运行入口和 runtime root，远端 CI 仍以提交后的实际结果为准。
- 旧细粒度 API 尚未全部隐藏或废弃，因此实时路由数仍较高。
- Safe HTTP、approved roots、versioned stable hash、Vector/FTS shadow rebuild/switch/rollback 与通用 migration registry/operator 已建立；当前 registry 同时拥有 Core、TaskPack、Research、Knowledge Governance 与 Workspace SQLite schema。
- Runtime 只验证了 `file_read` 显式意图；通用 Planner、Reviewed Feedback 与 Sleep Loop 统一执行 port 仍待完成。
