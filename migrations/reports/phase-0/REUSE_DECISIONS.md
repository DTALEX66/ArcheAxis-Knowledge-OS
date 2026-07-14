# Phase 0 复用决策

> Git 基线：`82b9df3f719d9212111536b454654f2243150f16`。原则：Existing Assets First；先包装与验证，再切换。只评估当前仓库已吸收版本，不访问外部项目。

| 资产 | 决策 | 优先级 | 事实与 Phase 1 动作 |
|---|---|---:|---|
| `shared/config.py` + `shared/auth.py` | 适配后复用，作为 Gateway 基础 | P0 | 三个应用已有共享认证，但中间件接线重复；生产使用必须经过 `validate_runtime_config`，并补 RBAC。 |
| `shared-contracts/schemas/*.json` | 作为 canonical contract 候选，不宣称当前 SSOT | P0 | Fixture validator 只证明 fixture；运行时 `app/schemas.py`、`shared/schemas.py` 有字段漂移，先建 legacy adapter。 |
| KB ContextPack/TaskPack builders | 适配后复用 | P0 | 实现位于 `__init__.py`，`builder.py` 近似占位；输出不等于 Runtime DTO。 |
| `shared/storage.py` + `shared/migration.py` | 保留并包 Repository Facade，禁止复制第二套 | P0 | 与 Runtime、Sleep Loop DDL 并存；Phase 1 不移动表、不改 schema。 |
| `shared/safe_writer.py` | 直接复用为安全写原语 | P0 | 默认 dry-run、路径 containment、覆盖备份和审计报告已有测试；用于替代散落写入。 |
| `shared/processing_manifest.py` | 直接复用 | P0 | Append-only JSONL、latest-state、源/输出哈希和 resume 语义完整。 |
| 质量纯函数模块 | 直接复用，保留 candidate/human-review 语义 | P0 | `content_quality`、`accuracy_benchmark`、`evidence_verification`、`oer_crosswalk` 已聚合；不能把 caller evidence 当 server verified。 |
| `app/core/router.py` + `route_policy.yaml` | 直接保留，经 Runtime Facade 暴露 | P1 | 规则已抽 YAML；Permission 仍反向导入私有匹配函数，应提公共 policy API。 |
| `app/tools/registry.py` | 适配后复用，不复制注册表 | P1 | 工具与风险集中，但与 `tools.yaml` 漂移且直接导入 KB；拆 Catalog 与 handler adapters。 |
| IR IntakeCard/EngineeringContract generators | 复用纯生成逻辑 | P1 | 无存储副作用，但字段必须映射版本化 Contracts。 |
| LiteLLM adapter | 适配后复用 | P1 | 会传播 provider 错误而不伪造成功；只有 mock 证据，不得声称真实 provider E2E。 |
| Crawl4AI adapter | 适配后复用为 crawl 聚合 Facade | P1 | Adapter 委托 `app.ingestion.multi_format.convert_url()`，后者真实优先调用 Crawl4AI 再 fallback；需补直接合同测试并让名称反映聚合行为。 |
| MarkItDown adapter | **禁止作为多格式完成能力复用** | P0 | 当前只真实读取文本，二进制返回占位；真实多格式路径在 `app/ingestion/multi_format.py`，应包装现有实现。 |
| vector/security/memory/observability/graph adapters | 不复用，只是空壳命名空间 | P1 | `__init__.py` 仅有 placeholder docstring，不得作为 Facade 已完成证据。 |
| `shared/obsidian_projection.py` | 仅复用纯 render，禁止直接复用 writer | P0 | `write_projection()` 缺少 vault containment；必须接 SafeWriter 和 approved root。 |
| `local_trace_adapter.py` | 禁止服务层直接复用 | P0 | 接受任意 `output_dir` 并直接 mkdir/write，无 containment、备份或原子写；改为 Trace Repository。 |
| `app/memory/vector_db.py` | 只复用 sqlite-vec 技术路线 | P0 | 不复用 Python `hash()` ID/embedding；先建 VectorStore 接口、稳定哈希和 rebuild。 |
| `shared/sleep_loop_engine.py` | 复用行为和数据，通过 Facade 收口 | P1 | 不复制引擎；后续复用统一 Planner/Permission/Executor/Evidence 语义。 |
| `knowledge_base/api.py` | 复用端点行为，不作为新架构边界 | P1 | 兼容保留旧 URL，Facade 调领域 service/repository，不直接依赖整个 FastAPI app。 |
| 外部来源声明 | 只承认当前仓库已吸收代码 | P0 | 禁止再次扫描、验证或同步仓库外项目；任何外部路径只能由显式 adapter/config 提供。 |

## 禁止事项

- 不复制整棵业务目录、注册表、DDL 或 Sleep Loop 到新壳层。
- 不直接执行目标设计 SQL，不在 Phase 1 搭便车迁移数据库。
- 不把 placeholder、preview、dry-run、stub、mock provider 或 candidate 当作完成。
- 不把未实际调用 Crawl4AI/MarkItDown 的兼容层按品牌名宣称为真实集成。
- 不在运行时代码新增 `sys.path.insert`、仓库外绝对路径或无 containment 写入。
