# Phase 0 架构缺口

> Git 基线：`82b9df3f719d9212111536b454654f2243150f16`。P0 表示进入 Phase 1 前必须定案或建立 Guard；P1 在 Facade 收口期间处理；P2 按后续路线图实施。

| ID | 优先级 | 事实与影响 | 仓库内证据 | 建议/目标 Phase |
|---|---|---|---|---|
| AG-01 | P0 | 实际依赖为 `app ↔ knowledge_base ↔ shared` 循环；非测试运行时 AST 审计为 app→KB 5、KB→app 3、shared→app 3、shared→KB 8 处。 | `app/main.py:82`; `app/tools/registry.py:203-247`; `knowledge_base/search/vector_search.py:8`; `shared/bridge.py:3-5` | Phase 1 定义单向依赖，Facade 截断反向导入，CI 禁止 Platform/Contracts 导入业务模块。 |
| AG-02 | P0 | **27 个非测试运行时文件**修改 `sys.path`，模块导入依赖源码目录布局。 | `Inspiration-Research/api.py:8-10`; `scripts/run_daily.py:11-13`; `shared/graph_rag.py:18-22`; `shared/web_search.py:20-21` | Phase 1 Guard 禁止新增；Facade 接通后逐步删除。 |
| AG-03 | P0 | 当前不是完整单网关：Core+KB 位于 8000，IR 仍是 8001 独立 FastAPI；三处重复 CORS、鉴权和异常接线。 | `app/main.py:22-103`; `knowledge_base/api.py:31-172`; `Inspiration-Research/api.py:25-136`; `docker-compose.yml:11-60` | Research Facade 先接主网关，独立入口只保留兼容期。 |
| AG-04 | P0 | ContextPack、TaskPack、ExecutionTrace、MachineLesson 在 `app`、`shared` 与 JSON Schema 中存在多个定义面，Schema 不是运行时 SSOT。 | `app/schemas.py`; `shared/schemas.py`; `shared-contracts/schemas/*.schema.json` | Phase 1 明确 legacy adapter；Phase 2 建版本化合同。 |
| AG-05 | P0 | 集成测试手工映射 KB→Runtime TaskPack，并手工保存 Lesson；只证明结构连通，不是完整 `/run → evaluation → reviewed lesson`。 | `integration-tests/test_ir_kb_os_loop.py:69-98` | 提取纯 adapter，增加 Schema/运行时模型合同测试。 |
| AG-06 | P0 | 同一 SQLite 文件由 Runtime、KB/IR、Sleep Loop 多套 DDL/初始化入口管理，部分模块 import 时创建目录或初始化 DB。 | `app/memory/database.py:11-132,431-432`; `shared/storage.py:21-279`; `shared/migration.py:19-232`; `shared/sleep_loop_engine.py:169-229,1087` | Phase 1 统一 composition root/Repository，不改表；正式 Migration Runner 留 Phase 3。 |
| AG-07 | P0 | 持久化 rowid 和文本 embedding 使用 Python `hash()`，跨进程不稳定，重启后可能得到不同 ID/向量。 | `app/memory/vector_db.py:91-109,143-150,300-303`; `docs/EXECUTION_ROADMAP.md:85-90` | Phase 3 换稳定哈希并设计索引重建/回滚；不得作为新 Adapter ID 规则复用。 |
| AG-08 | P1 | `knowledge_base/api.py` 为 1171 行、91 个直接路由的巨型兼容入口，跨 KB/IR/Obsidian 多域。 | `knowledge_base/api.py`; `knowledge_base/routers/composite.py`; `quality.py`; `projection.py` | 冻结新增，按领域拆 router；新 Facade 不直接依赖整个 API app。 |
| AG-09 | P1 | `shared/sleep_loop_engine.py` 为 1087 行、34 个顶层函数，兼有 schema、队列、guard、执行、资源控制和状态查询。 | `shared/sleep_loop_engine.py:34-1087` | 先包 SleepLoop Facade，后拆 repository/service/worker/policy，不复制第二套完成语义。 |
| AG-10 | P1 | 只有 `route_policy.yaml` 被运行时读取；`tools.yaml`、`models.yaml`、agent/codex profile 没有业务消费，工具风险仍硬编码。 | `app/core/router.py:16-29`; `config/*.yaml`; `app/tools/registry.py:20-73` | 明确配置 SSOT，消除 YAML/Python 双写。 |
| AG-11 | P1 | 源码与 wheel 边界不一致：IR 不在 package discovery；Contracts Schema 无明确 package-data/wheel smoke。 | `Dockerfile:17-23`; `pyproject.toml:53-60`; `.github/workflows/ci.yml:57-80` | 从仓库外临时目录验证 IR、Facade 和 Schema 资源。 |
| AG-12 | P0 | CI 缺少架构依赖 Guard 和运行时 Pydantic↔JSON Schema 一致性测试；fixture 自验证不能替代运行时合同。 | `.github/workflows/ci.yml:25-80`; `shared-contracts/validators/validate_fixtures.py` | Phase 1 加 forbidden-import 与 legacy DTO↔canonical 双向合同测试。 |
| AG-13 | P2 / Phase 7 | Planner 仍主要产生固定 echo，Evaluator 主要是二值结果，candidate Lesson 不等于审核闭环。 | `app/agent/planner.py`; `app/core/compiler.py`; `app/evaluation/evaluator.py`; `shared/bridge.py:23-51` | Phase 7 才实施动态规划和证据驱动评价；当前不得宣称完整认知闭环。 |
| AG-14 | P1 | Root 警告审计发现未关闭 SQLite 连接；mypy 正式配置被 NumPy stub/Python 3.10 语法阻断，3.13 诊断仍有项目错误。 | `tests/test_coverage_gap.py::TestLogging`; `TEST_BASELINE.md` | Phase 1/3 关闭连接泄漏；先修类型工具链可复现性，再逐域归零。 |
| AG-15 | P1 | 缺少本地容器、反向代理、TLS 与并发负载实测。 | 当前 Phase 0 执行证据 | Phase 9/10 完成部署与运行时验证；现阶段不得宣称通过。 |

## 迁移顺序

1. **P0-1：**锁定依赖规则、合同边界和禁止新增 `sys.path.insert`。
2. **P0-2：**建立 Research、Knowledge、Enhancement、Runtime、Contracts 五个 Facade，只委托现有实现。
3. **P0-3：**统一 composition root、认证接线和数据库初始化，不改变数据库结构。
4. **P1-1：**以 SafeWriter/Repository 收口散落写入；拆分 KB 巨型入口并包装 Sleep Loop。
5. **P1-2：**补 wheel、合同、权限、安全 HTTP 与路径 containment 门禁。
6. Phase 7 前不得把 echo Planner、二值 Evaluation、preview/candidate Lesson 宣称为完整闭环。
