# 开源项目参考代码集成计划

> Generated 2026-06-25 | Agent Knowledge-Base 参考代码提取
> 基于 reference/GITHUB_REFERENCE_PROJECTS.md + EXTRACTION.md + A/B线分析报告
> 涵盖 20+ 开源项目、28 个可集成特性

---

## 1. 项目现状总览

### 代码实现成熟度

| 子系统 | 模块 | 状态 | 详细说明 |
|--------|------|------|---------|
| **A线核心** | fsrs5.py (FSRS-5) | ✅ 已实现+优化 | 19参数权重，RMSE 0.3748→0.3628 |
| | store.py (卡片/复习存储) | ✅ 已实现 | 原生 sqlite3，手动 SQL |
| | learning_system.py | ✅ 已实现 | 学习诊断系统 |
| | evolution.py | ✅ 已实现 | 长期巩固系统 |
| | fsrs_optimizer.py | ✅ 已实现 | 随机爬山法优化器 |
| **A线增强** | cognitive_load.py | ✅ 已实现 | `backend/pk_radar/learning_final/cognitive_load.py` |
| | encoding.py | ✅ 已实现 | 记忆编码模块 |
| | rubrics.py | ✅ 已实现 | Rubric评分引擎 |
| | teach_back.py | ✅ 已实现 | 费曼输出 |
| | metacognition.py | ✅ 已实现 | 元认知系统 |
| | profile.py | ✅ 已实现 | 学习画像 |
| | diagnostics.py | ✅ 已实现 | 学习诊断 |
| | consolidation.py | ✅ 已实现 | 长期巩固 |
| | palace/ | ✅ 已实现 | 知识宫殿 |
| **B线核心** | machine_knowledge.py | ✅ 已实现 | 机器知识单元 |
| | agent_orchestrator.py | ✅ 已实现 | 状态机路由+Agent编排 |
| | context_engine.py | ✅ 已实现 | 上下文包构建 |
| | route_engine.py | ✅ 已实现 | 路线规划 |
| | eval_engine.py | ✅ 已实现 | 评估引擎 |
| | feedback_loop.py | ⚠️ 基础功能 | 仅反模式记录+B→A回流 |
| | trace_audit.py | ✅ 已实现 | 执行追踪 |
| | sandbox_executor.py | ✅ 已实现 | 沙箱执行 |
| | model_router.py | ✅ 已实现 | 模型路由+限流 |
| | agent_role.py | ✅ 已实现 | Agent角色定义 |
| | a_to_b.py | ✅ 已实现 | A转B翻译 |
| **MCP层** | tool_registry.py | ✅ 已实现 | 工具注册表 |
| | permissions.py | ✅ 已实现 | MCP权限系统 |
| | server.py | ✅ 已实现 | MCP服务器 |
| | audit.py | ✅ 已实现 | MCP审计 |
| **缺失模块** | agents/ | ❌ 完全缺失 | Agent角色矩阵独立目录 |
| | taskpacks/ | ❌ 完全缺失 | CODEX/DEEP任务包 |
| | execution/ | ❌ 完全缺失 | 正式执行沙箱目录 |
| | SQLModel ORM | ❌ 完全缺失 | 仍用raw sqlite3 |

### 状态标记说明

| 标记 | 含义 |
|------|------|
| ✅ **已实现** | 代码已存在且功能完整 |
| ⚠️ **基础功能** | 实现存在但缺少关键特性 |
| 🔶 **部分实现** | 框架存在，核心算法/模式待补充 |
| ❌ **完全缺失** | 尚未实现 |

---

## 2. 高优先级集成 (Priority=High)

### H1: py-fsrs Rust原生性能层

**来源**: `rs-fsrs-python` (Rust PyO3, MIT)
**状态**: 🔶 部分实现 — fsrs5.py纯Python已有，Rust加速层缺失
**价值**: 批处理场景 10-50x 吞吐提升

#### 实现路径

```text
Phase 1: 适配层 (1h)
  └─ 创建 backend/pk_radar/core/fsrs5_native.py
  └─ 提供 try/except 降级: 有Rust绑定用NativeFSRS，无则fallback到纯Python
  └─ 暴露 FSRS5Native 类，接口与 fsrs5.FSRS5 一致

Phase 2: 构建集成 (30min)
  └─ 在 pyproject.toml 中添加可选依赖组 (optional-dependencies)
  └─ maturin 构建脚本 + CI缓存策略
  └─ Rust toolchain 检查脚本 (backend/scripts/check_rust.ps1)

Phase 3: 验证 (30min)
  └─ 新增测试 test_fsrs5_native.py
  └─ 性能基准: 原生vs纯Python吞吐对比
```

#### 依赖
- Rust toolchain (rustup) — 可选运行时依赖
- maturin >=1.7 — 构建时依赖
- 当前 fsrs5.py — 零破坏，100%向后兼容

#### 参考代码
- `reference/archive/rs-fsrs-python/` — PyO3类定义、Parameters结构
- `reference/EXTRACTION.md §1` — 接口定义提取

---

### H2: RecordLog批处理调度 (review_all_ratings)  [已实现]

**来源**: `rs-fsrs-python` (Rust PyO3, MIT)
**状态**: 🔶 部分实现 — `FSRS5.review()` 单卡片单评级已有
**价值**: 一次调用计算4个评级结果，消除循环开销

#### 实现路径

```text
Phase 1: 方法添加 (30min)
  └─ 在 fsrs5.py 中添加 FSRS5.review_all_ratings(card, now=None)
  └─ 返回 dict[Literal["again","hard","good","easy"], SchedulingInfo]

Phase 2: API集成 (30min)
  └─ 在 api.py 的 /repetition 端点添加 preview 模式
  └─ 返回所有4个评级的结果供前端预览

Phase 3: Deck级批量调度 (1h)
  └─ 添加 /\{deck_id\}/review-all 端点
  └─ 一次加载deck所有due卡片，批量计算
```

#### 依赖
- 无外部依赖 — 纯Python实现
- 依赖 fsrs5.py 现有核心逻辑

---

### H3: LiteLLM模型网关适配层 [已实现]

**来源**: [LiteLLM](https://github.com/BerriAI/litellm) (MIT)
**状态**: 🔶 部分实现 — `b_line/model_router.py` 已有本地路由+限流
**价值**: 统一OpenAI/Anthropic/Ollama API，成本追踪+自动fallback

#### 实现路径

```text
Phase 1: Adapter封装 (1h)
  └─ 创建 backend/pk_radar/b_line/litellm_adapter.py
  └─ LiteLLMRouter 类封装 litellm.router.Router
  └─ 注册本地模型信息到 LiteLLM 路由表
  └─ 保留 model_router.py 作为本地fallback层

Phase 2: 成本+限流增强 (1h)
  └─ 将 model_router.py 的 TokenBucket 集成到 LiteLLM 部署配置
  └─ 添加 cost_tracker 记录每会话token消耗
  └─ 对接 trace_audit 记录每次模型调用

Phase 3: 验证 (30min)
  └─ 多provider fallback测试
  └─ 成本限制触发测试
```

#### 依赖
- `litellm` pip包 — MIT许可证，可直接依赖
- 支持 OpenAI / Anthropic / Ollama / vLLM

---

### H4: Multi-Agent角色分配算法

**来源**: AutoGen (MIT) + CrewAI (MIT) + CAMEL (Apache-2.0)
**状态**: ⚠️ 基础功能 — `agent_orchestrator.py` 有状态机路由，`agent_role.py` 有角色定义
**价值**: 从固定角色表升级为智能分配——依据任务类型、风险等级、记忆匹配

#### 实现路径

```text
Phase 1: Agent分配评分器 (1.5h)
  └─ 创建 backend/pk_radar/b_line/agent_assignment.py
  └─ 实现 agent_fit_score() 加权算法:
      - role_task_match (0.30)
      - tool_permission_match (0.20)
      - domain_memory_match (0.15)
      - risk_level_fit (0.15)
      - validation_need (0.10)
      - cost_fit (0.10)
  └─ 参考: B线分析提取报告 §5.2

Phase 2: 动态角色池 (1h)
  └─ 扩展 agent_orchestrator.py 支持运行时注册/注销角色
  └─ 添加角色能力自述 (capabilities_json)
  └─ 添加角色性能历史 (success_rate, avg_cost, avg_latency)

Phase 3: 多Agent编排模式 (1h)
  └─ 实现顺序/并行/条件三种执行模式 (agent_orchestrator.py 已定义枚举)
  └─ 添加 AgentNode 依赖图解析器
  └─ 参考: AutoGen的对话模式 + CrewAI的层级/顺序流程
```

#### 依赖
- 无外部依赖 — 吸收算法思想，不引入AutoGen/CrewAI框架
- License: MIT → 安全参考，无需顾虑

---

### H5: DSPy风格反馈优化循环

**来源**: [DSPy](https://github.com/stanfordnlp/dspy) (MIT) + [Langfuse](https://github.com/langfuse/langfuse) (MIT)
**状态**: ⚠️ 基础功能 — `feedback_loop.py` 仅反模式记录
**价值**: 从"记录失败"升级为"自动优化"——Prompt优化+权重调整

#### 实现路径

```text
Phase 1: 评估指标采集 (1h)
  └─ 增强 eval_engine.py 添加 metric_collector
  └─ 采集: 任务成功率、token消耗、延迟、用户反馈评分
  └─ 存储到 execution_traces 表的 evidence_json

Phase 2: Prompt优化器 (1.5h)
  └─ 创建 backend/pk_radar/b_line/prompt_optimizer.py
  └─ 实现 compile_examples() — 从成功/失败trace提取示例
  └─ 实现 optimize_prompt() — 基于few-shot示例重写prompt
  └─ 参考: DSPy的teleprompt优化器模式 (不依赖框架)

Phase 3: 自动调参管道 (1.5h)
  └─ 创建 backend/scripts/optimization_pipeline.ps1
  └─ 管道: collect metrics → identify regressions → optimize → validate → deploy
  └─ 添加 observability.py 对接 metrics 可视化

Phase 4: Langfuse可观测性 (1h)
  └─ 创建 b_line/langfuse_adapter.py 封装 Langfuse SDK
  └─ 自动追踪: trace_id → span → event, 模型调用, 工具调用
  └─ 与 trace_audit.py 共享 trace_id
```

#### 依赖
- `dspy-ai` pip包 (可选) — MIT许可证
- `langfuse` pip包 (可选) — MIT许可证
- 与 `trace_audit.py` 和 `eval_engine.py` 集成

---

### H6: OpenHands风格沙箱执行

**来源**: [OpenHands](https://github.com/All-Hands-AI/OpenHands) (MIT) + [E2B](https://github.com/e2b-dev/e2b) (Apache-2.0)
**状态**: ✅ `b_line/sandbox_executor.py` 已有基本沙箱
**价值**: 安全执行CDE/DEEP任务包，ACI设计模式，Dry-run审批

#### 实现路径

```text
Phase 1: ACI接口设计 (1h)
  └─ 定义 Agent-Computer Interface (ACI) 抽象层
  └─ 操作原语: read_file, write_file, run_command, list_files, search_code
  └─ 参考: SWE-agent的ACI设计 (不复制代码，吸收接口思想)

Phase 2: 沙箱适配器 (1h)
  └─ 创建 backend/pk_radar/execution/sandbox_adapter.py
  └─ DockerSandbox — Docker SDK封装
  └─ E2BSandbox — E2B云端沙箱封装
  └─ LocalSandbox — 受限本地执行 (仅只读/无网络模式)
  └─ 统一 ISandbox 接口

Phase 3: Dry-run执行门 (1h)
  └─ 在 sandbox_executor.py 中添加 dry_run + approval 模式
  └─ 高风险操作 → dry_run → 人类审批 三步门控
  └─ 参考: B线分析提取报告 §5.4 (Autonomous Execution Gate)

Phase 4: 执行追踪 (30min)
  └─ 每次沙箱操作写入 execution_traces
  └─ 操作回放支持
```

#### 依赖
- `docker` pip包 — Apache-2.0许可证
- `e2b` pip包 (可选) — Apache-2.0许可证
- 目标目录: `backend/pk_radar/execution/` — 当前缺失

---

### H7: RAG评估框架 (忠实度+相关性)

**来源**: [Ragas](https://github.com/explodinggradients/ragas) (Apache-2.0) + [Phoenix](https://github.com/Arize-AI/phoenix) (Apache-2.0)
**状态**: ⚠️ 基础功能 — `b_line/eval_engine.py` 有评估引擎但无RAG指标
**价值**: 量化RAG质量 (faithfulness, relevancy, precision, recall)

#### 实现路径

```text
Phase 1: RAG指标实现 (1h)
  └─ 在 eval_engine.py 或新建 eval_rag.py 中添加指标计算
  └─ Faithfulness: 检查生成内容是否忠实于检索上下文
  └─ Relevancy: 检查检索结果是否相关于用户查询
  └─ Context Precision/Recall: 检索质量的精确度和召回率
  └─ 参考: Ragas论文 (不依赖框架，自行实现指标)

Phase 2: Phoenix可观测性 (1h)
  └─ 创建 b_line/phoenix_adapter.py 封装 Phoenix SDK
  └─ LLM trace可视化: embedding查询 → 检索 → 生成
  └─ 添加 RAG trace span 到 trace_audit

Phase 3: 自动化评估管道 (30min)
  └─ eval_engine.py 中集成 RAG 评估到现有评估框架
  └─ 添加 /eval/rag 端点
```

#### 依赖
- `arize-phoenix` pip包 (可选) — Apache-2.0许可证
- `ragas` pip包 (可选) — Apache-2.0许可证

---

## 3. 中优先级集成 (Priority=Medium)

### M1: SQLModel ORM迁移

**来源**: `fsrs_python_system` (FastAPI + SQLModel)
**状态**: ❌ 完全缺失 — 当前使用 raw sqlite3

| 维度 | 当前(raw sqlite3) | 目标(SQLModel) |
|------|------------------|----------------|
| 查询语法 | 手写SQL字符串 | `select().where()` |
| 类型安全 | 无 | Pydantic自动验证 |
| 迁移 | 自定义MigrationRunner | `SQLModel.metadata.create_all()` |
| 关系 | 手动JOIN | Relationship自动加载 |
| IDE支持 | 无 | 完整自动补全 |

#### 实现路径

```text
Phase 1: 模型定义 (1h)
  └─ 创建 backend/pk_radar/core/models.py
  └─ Deck, CardModel, ReviewLog, KnowledgeBlock 等表
  └─ 参考: EXTRACTION.md §2A + FSRS集成方案.md §2.3

Phase 2: store.py迁移 (2h)
  └─ 逐个替换 store.py 的 raw SQL 为 SQLModel select()
  └─ CRUD: create_card, get_due_cards, record_review, get_decks...

Phase 3: 迁移系统替换 (30min)
  └─ 移除自定义 MigrationRunner
  └─ 使用 SQLModel.metadata.create_all() + Alembic (可选)

Phase 4: 依赖注入 (30min)
  └─ 添加 SessionDep 模式 (FastAPI Depends)
  └─ 参考: fsrs_python_system/main.py
```

---

### M2: Mem0/Zep机器记忆系统

**来源**: [Mem0](https://github.com/mem0ai/mem0) (Apache-2.0) + [Zep](https://github.com/getzep/zep) (Apache-2.0)
**状态**: ❌ 完全缺失 — 无跨会话持久Agent记忆
**价值**: Agent能记住过去任务，建立领域经验

#### 实现路径

```text
Phase 1: Mem0适配器 (1h)
  └─ 创建 backend/pk_radar/b_line/machine_memory.py
  └─ Mem0Memory 封装 mem0 的 Memory 类
  └─ 添加 add(task_result, user_id) + search(query, user_id)

Phase 2: 记忆自动提取 (1h)
  └─ 每次任务完成后自动调用 memory.add()
  └─ 从 execution_traces 提取关键信息
  └─ 从 feedback_loop.anti_patterns 提取失败模式

Phase 3: Agent记忆检索 (1h)
  └─ 在 context_engine.py 中添加记忆检索步骤
  └─ Agent分配时查询领域相关经验
  └─ 参考: Mem0的memory-to-prompt模式
```

---

### M3: Context Pack正式评分

**来源**: B线分析提取报告 §5.3
**状态**: ⚠️ 基础功能 — `context_engine.py` 可组装但无质量评分
**价值**: 量化上下文质量，避免token浪费

#### 实现路径

```text
Phase 1: 评分器实现 (1h)
  └─ 在 context_engine.py 中添加 ContextPackScorer
  └─ 实现 context_pack_score = weighted_sum(
      relevance=0.25, trust=0.20, recency=0.15,
      task_fit=0.15, brevity=0.10, evidence=0.10,
      token_cost_inverse=0.05)

Phase 2: 智能截断 (30min)
  └─ 根据评分裁剪低质量片段
  └─ token预算控制: 超出阈值自动压缩
```

---

### M4: Agent角色矩阵形式化

**来源**: B线分析提取报告 §10 + AutoGen/CrewAI模式
**状态**: ⚠️ 基础功能 — `agent_role.py` 有定义，`agents/` 目录缺失
**价值**: 正式的角色定义、权限映射、风险评估

#### 实现路径

```text
Phase 1: Agent角色目录 (1h)
  └─ 创建 backend/pk_radar/agents/roles.py
  └─ 定义8个角色: Planner, Researcher, Coder, Tester, Reviewer, Security, License, MemoryCurator
  └─ 每个角色包含: 职责描述、典型工具、风险等级、capabilities

Phase 2: 权限矩阵 (30min)
  └─ 角色→工具→权限 三向映射表
  └─ 在 permissions.py 中引用
```

---

## 4. 低优先级集成 (Priority=Low)

### L1: Retention保留率图表

**来源**: fsrs_python_system + py-fsrs
**状态**: ❌ 完全缺失
**实现**: `/stats/retention` 端点 + 前端图表组件

### L2: to_study 待复习计数

**来源**: fsrs_python_system
**状态**: ❌ 完全缺失
**实现**: deck列表中显示待复习卡片数

### L3: Auto-create默认牌组

**来源**: fsrs_python_system
**状态**: ❌ 完全缺失
**实现**: 用户首次访问时自动创建"default"牌组

### L4: Reversed Card反向卡片

**来源**: fsrs_python_system
**状态**: ❌ 完全缺失
**实现**: 创建卡片时 `with_reversed=True` 生成前后翻转的副本

### L5: SchedulingInfo返回值

**来源**: rs-fsrs-python
**状态**: ❌ 完全缺失
**实现**: Dataclass包装 (Card, ReviewLog) 返回类型

---

## 5. 集成依赖关系图

```text
H3: LiteLLM  ─────────────────────→  model_router.py (增强)
               │
H4: AutoGen/CrewAI ──────────────→  agent_role.py (增强)
               │                       │
               ├──→  agent_orchestrator.py (增强)
               │
H5: DSPy ─────────────────────────→  feedback_loop.py (升级)
               │                       │
               ├──→  eval_engine.py (增强)
               │
H6: OpenHands/E2B ────────────────→  创建 execution/sandbox_adapter.py
               │
H7: Ragas/Phoenix ───────────────→  eval_engine.py (增强)
               │
H1: rs-fsrs-python ──────────────→  创建 fsrs5_native.py (+fsrs5.py)
               │
H2: RecordLog ────────────────────→  fsrs5.py (+review_all_ratings)
               │
M1: SQLModel ─────────────────────→  创建 models.py + store.py (重构)
               │
M2: Mem0 ─────────────────────────→  创建 machine_memory.py
               │
M3: Context Pack ─────────────────→  context_engine.py (增强)
               │
M4: Agent Roles ──────────────────→  创建 agents/roles.py
```

---

## 6. 技术栈要求

### 必须安装
| 工具 | 用途 |
|------|------|
| Python 3.10+ | 当前运行时 |
| FastAPI + Uvicorn | Web服务 |
| sqlite3 | 当前存储 |
| pytest | 测试框架 |

### 可选安装 (按优先级)
| 工具 | 用途 | 许可证 | 对应集成项 |
|------|------|--------|-----------|
| `litellm` | 模型网关 | MIT | H3 |
| `dspy-ai` | Prompt优化 | MIT | H5 |
| `langfuse` | LLM可观测性 | MIT | H5 |
| `docker` | 沙箱执行 | Apache-2.0 | H6 |
| `e2b` | 云端沙箱 | Apache-2.0 | H6 |
| `arize-phoenix` | LLM trace可视化 | Apache-2.0 | H7 |
| `ragas` | RAG评估 | Apache-2.0 | H7 |
| `sqlmodel` | ORM | MIT | M1 |
| `mem0` | Agent记忆 | Apache-2.0 | M2 |
| Rust + maturin | FSRS原生性能 | MIT | H1 |

### 不推荐引入
| 项目 | 原因 |
|------|------|
| AutoGen | 太重，只吸收算法思想 |
| CrewAI | 同上，只吸收角色分配模式 |
| LangGraph | 许可证风险+复杂度，自建状态机 |
| Dify | 与轻量定位矛盾 |
| RAGFlow | 同上 |
| PostgreSQL | SQLite当前足够 |
| Selenium | 已有crawl4ai替代 |

---

## 7. MVP实现路线图

### Sprint 1 (Quick Wins — 每个30min)
- [ ] H2: review_all_ratings() 批处理 (fsrs5.py)
- [ ] L2: to_study 待复习计数
- [ ] L3: Auto-create默认牌组
- [ ] L4: Reversed Card支持
- [ ] L5: SchedulingInfo返回类型

### Sprint 2 (核心性能 — 1-2天)
- [ ] H1: Rust原生性能层 (fsrs5_native.py)
- [ ] M1: SQLModel ORM迁移 Phase 1-2

### Sprint 3 (Agent系统 — 2-3天)
- [ ] H4: Agent分配评分器
- [ ] H6: ACI接口+沙箱适配器
- [ ] M4: Agent角色矩阵

### Sprint 4 (反馈优化 — 2-3天)
- [ ] H5: DSPy风格Prompt优化器
- [ ] H3: LiteLLM网关适配层
- [ ] M2: Mem0机器记忆系统

### Sprint 5 (评估可观测 — 1-2天)
- [ ] H7: RAG评估框架
- [ ] M3: Context Pack评分器
- [ ] L1: 保留率图表

---

## 8. 已完成项目复核

以下GITHUB_REFERENCE_PROJECTS.md中的项目已在本地实现，无需集成：

| 项目 | 对应实现 |
|------|---------|
| Khan Academy Exercises | learning_final/diagnostics.py (自适应诊断) |
| py-fsrs | core/fsrs5.py (FSRS-5算法) |
| fsrs4anki optimizer | core/fsrs_optimizer.py (权重优化器) |
| LangGraph 状态机 | b_line/agent_orchestrator.py (状态机路由) |
| SWE-agent ACI | b_line/sandbox_executor.py (沙箱+门控) |
| ChromaDB/Qdrant | search/vector_search.py + search/hybrid.py |
| MetaGPT SOP | b_line/agent_orchestrator.py (顺序/并行Agent) |
| Haystack NLP Pipeline | b_line/context_engine.py (上下文组装) |
| promptfoo 评估 | b_line/eval_engine.py (评估框架) |
| Ollama 本地LLM | b_line/model_router.py (本地模型路由) |

---

## 9. 风险 & 依赖管理

| 风险 | 缓解策略 |
|------|---------|
| Rust编译失败 | fsrs5_native.py 自动fallback到纯Python |
| LiteLLM API key缺失 | model_router.py 保留本地模型路由 |
| Docker不可用 | SandboxAdapter 提供 LocalSandbox fallback |
| SQLModel迁移破坏现有数据 | 保留迁移脚本和backup功能 |
| Mem0/Zep版本冲突 | 使用Adapter模式，版本锁在requirements中 |
