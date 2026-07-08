# B线线路最终合集 — 深度分析提取报告

> Generated 2026-06-23 | Agent-5 (Lorentz)
> Source: reference/B线线路最终合集包/ (14 files, ~91KB total)

---

## 1. 系统定位

B线从"给AI查资料的MCP层"升级为 **Machine Knowledge & Agent Execution OS**（机器知识与Agent执行操作系统）。

```text
让机器不是"会聊天"，而是能基于可靠知识安全执行任务。
```

---

## 2. B线核心闭环

```text
目标输入
→ Context Pack 上下文组装
→ Machine Knowledge 机器知识检索
→ Machine Route 机器路线规划
→ MCP Tool 工具选择
→ Agent Role 多线Agent分配
→ TaskPack CODEX/DEEP任务拆解
→ Sandbox Dry-run/执行隔离
→ Eval 测试验证
→ Audit 审计证据链
→ Feedback 经验回流(A线/B线)
```

---

## 3. B线11层架构

| 层 | 系统 | 作用 |
|---|------|------|
| 知识层 | Machine Knowledge | 机器可读的规则、流程、约束、模式 |
| 上下文层 | Context Pack | 给Agent组装刚好够用的可信上下文 |
| 路线层 | Machine Route | 规划机器查、想、调工具、验证的路径 |
| 工具层 | MCP Tools | 暴露文档、机器知识、任务、审计工具 |
| Agent层 | Multi-Agent Roles | 多角色协同，分工执行 |
| 任务层 | TaskPack | 生成CODEX/DEEP可执行任务包 |
| 执行层 | Sandbox / Approval | dry-run、权限、审批、执行隔离 |
| 评估层 | Eval / Test | 测试、红队、RAG/Agent评估 |
| 审计层 | Trace / Evidence | 工具、模型、执行全链路追踪 |
| 记忆层 | Machine Memory | 成功经验、失败模式、项目记忆 |
| 回流层 | B→A / B→B Feedback | 失败回流为人学习卡片或机器反模式 |

---

## 4. 六大核心对象

```text
MachineKnowledgeUnit  — 机器知识单元（规则/流程/约束/模式）
MachineRoute          — 机器执行路线（步骤/状态/工具/验证）
ToolSpec              — 工具规格（MCP/API/CLI + 权限/风险）
AgentRole             — Agent角色（Planner/Researcher/Coder/Tester/Reviewer）
TaskPack              — 任务包（CODEX补丁包/DEEP并行包/验收测试/回滚计划）
ExecutionTrace        — 执行追踪（全链路证据/状态/错误/回放）
```

---

## 5. 关键算法提取

### 5.1 Machine Route Planner（路线规划评分）

```python
route_score = weighted_sum(
    goal_match=0.25,          # 目标匹配度
    knowledge_coverage=0.20,  # 知识覆盖率
    tool_availability=0.15,   # 工具可用性
    risk_fit=0.15,            # 风险适配度
    agent_fit=0.10,           # Agent适配度
    validation_strength=0.10, # 验证强度
    cost_fit=0.05,            # 成本适配度
)
```

### 5.2 Multi-Agent Assignment（Agent分配评分）

```python
agent_fit_score = weighted_sum(
    role_task_match=0.30,        # 角色任务匹配
    tool_permission_match=0.20,  # 工具权限匹配
    domain_memory_match=0.15,    # 领域记忆匹配
    risk_level_fit=0.15,         # 风险等级适配
    validation_need=0.10,        # 验证需求
    cost_fit=0.10,               # 成本适配
)
```

### 5.3 Context Pack Builder（上下文包构建）

```python
context_pack_score = weighted_sum(
    relevance=0.25,          # 相关性
    trust=0.20,              # 可信度
    recency=0.15,            # 时效性
    task_fit=0.15,           # 任务适配
    brevity=0.10,            # 简洁度
    evidence=0.10,           # 证据强度
    token_cost_inverse=0.05, # token成本（逆）
)
```

### 5.4 Autonomous Execution Gate（自主执行门控）

```python
execution_permission = composite_decision(
    risk_score,        # 风险评分
    reversibility,     # 可逆性
    test_coverage,     # 测试覆盖
    permission_level,  # 权限等级
    human_approval,    # 人类审批
)
# 高风险操作强制 dry-run → human approval → execute
```

### 5.5 Feedback Learning（反馈学习优先级）

```python
feedback_priority = weighted_sum(
    failure_frequency=0.25,  # 失败频率
    impact=0.20,             # 影响程度
    repeatability=0.20,      # 可复现性
    fixability=0.15,         # 可修复性
    cost_saved=0.10,         # 节省成本
    risk_reduction=0.10,     # 风险降低
)
```

### 5.6 Self-Learning Loop（自主学习闭环）

```text
run → trace → evaluate → detect failure pattern
→ write machine_lesson candidate → human/auto review
→ update prompt/tool/route/memory
```

---

## 6. 开源项目对标矩阵

| B线模块 | 主对标 | 次对标 | 吸收策略 |
|---------|--------|--------|---------|
| MachineRoute | LangGraph | Conductor/Haystack | 只吸收状态机思想 |
| MultiAgent | AutoGen/CrewAI | MetaGPT/CAMEL | 不复制复杂框架进核心 |
| SoftwareAgent | OpenHands | SWE-agent/Aider | 先做适配器，不重造 |
| PromptOptimize | DSPy | promptfoo | 先接评估，再接优化 |
| EvalAudit | Langfuse/promptfoo | Phoenix/Ragas | 强制 trace/eval |
| Memory | Mem0/Zep | projectmem | 区分项目记忆和通用记忆 |
| ModelGateway | LiteLLM | vLLM/Ollama | 先LiteLLM统一API |
| Sandbox | E2B/OpenHands | Docker local | 默认 dry-run |
| RAG | LlamaIndex/Haystack | RAGFlow/Dify | 只参考，不套大平台 |
| IDE | Continue/Aider | OpenHands | 后期对接 |

---

## 7. B线硬规则

```text
1. 机器知识必须有来源
2. 机器执行必须有权限
3. 机器结论必须有证据
4. 机器任务必须可验收
5. 机器错误必须回流
6. 机器指令不能直接污染A线长期记忆
```

---

## 8. B线数据模型 (SQL)

```sql
CREATE TABLE machine_knowledge_units (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  source_type TEXT NOT NULL,    -- A_line / external / project / feedback
  source_entity_id INTEGER,
  confidence REAL NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending',  -- pending/approved/active/archived
  approved_by TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);

CREATE TABLE machine_routes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  goal TEXT NOT NULL,
  steps_json TEXT NOT NULL DEFAULT '[]',
  tools_json TEXT NOT NULL DEFAULT '[]',
  risk_level TEXT NOT NULL DEFAULT 'low',
  score REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE agent_roles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  role_name TEXT NOT NULL,       -- Planner/Researcher/Coder/Tester/Reviewer
  capabilities_json TEXT NOT NULL DEFAULT '[]',
  tool_permissions_json TEXT NOT NULL DEFAULT '[]',
  risk_level TEXT NOT NULL DEFAULT 'low'
);

CREATE TABLE task_packs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  pack_type TEXT NOT NULL,       -- codex / deep
  content TEXT NOT NULL,
  acceptance_criteria_json TEXT NOT NULL DEFAULT '[]',
  rollback_plan TEXT,
  risk_level TEXT NOT NULL DEFAULT 'low',
  created_at TEXT NOT NULL
);

CREATE TABLE execution_traces (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  trace_id TEXT NOT NULL,
  route_id INTEGER,
  task_pack_id INTEGER,
  tool_name TEXT,
  model TEXT,
  status TEXT NOT NULL,
  evidence_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);

CREATE TABLE context_packs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  task_goal TEXT NOT NULL,
  content TEXT NOT NULL,
  source_units_json TEXT NOT NULL DEFAULT '[]',
  score REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
```

---

## 9. B线API & MCP工具

### REST API

| 端点 | 用途 |
|------|------|
| GET /machine/knowledge | 机器知识检索 |
| POST /machine/knowledge | 创建机器知识 |
| POST /machine/knowledge/{id}/approve | 审批机器知识 |
| POST /machine/routes/plan | 路线规划 |
| POST /context-packs/build | 构建上下文包 |
| GET /mcp/tools | 工具列表 |
| POST /mcp/tools/{name}/call | 调用MCP工具 |
| POST /agents/assign | 分配Agent |
| POST /taskpacks/generate-codex | 生成CODEX任务包 |
| POST /taskpacks/generate-deep | 生成DEEP任务包 |
| POST /execution/dry-run | 干运行 |
| POST /execution/approve | 审批执行 |
| GET /execution/traces | 查看追踪 |

### MCP工具

```text
machine_knowledge.search / .get
machine_route.plan
context_pack.build
agent.assign
taskpack.generate_codex / .generate_deep
project.analyze
license.audit
execution.dry_run
audit.trace
feedback.record
```

---

## 10. Agent角色矩阵

| 角色 | 职责 | 典型工具 | 风险等级 |
|------|------|---------|---------|
| Planner | 任务分解、路线规划 | machine_route.plan | low |
| Researcher | 知识检索、上下文组装 | machine_knowledge.search, context_pack.build | low |
| Coder | 代码生成、Patch | taskpack.generate_codex | medium |
| Tester | 测试编写、验证 | execution.dry_run | medium |
| Reviewer | 代码审查、安全审计 | license.audit, audit.trace | medium |
| Security | 权限检查、风险门控 | execution.approve | high |
| License | 许可证合规检查 | license.audit | high |
| Memory Curator | 经验提取、反模式记录 | feedback.record | low |

---

## 11. MVP收敛路线 (6步)

```text
MVP-1: 机器知识 + 上下文包         ← 最小可行：检索+组装
MVP-2: 机器路线                     ← 路径规划
MVP-3: MCP工具 + 权限              ← 工具调用
MVP-4: Agent角色矩阵               ← 多Agent分工
MVP-5: 任务包生成 (CODEX/DEEP)     ← 可执行任务
MVP-6: 执行审计 + 反馈学习         ← 完整闭环
```

---

## 12. 许可证与吸收策略

### 低风险优先
MIT / Apache-2.0 / BSD → 可考虑依赖或吸收接口思想

### 谨慎参考
商业附加条款 / Source Available / 混合许可证 / AGPL/GPL → 只参考产品逻辑，不复制代码

### 吸收策略
```text
1. 先吸收思想和数据模型
2. 再做 adapter
3. 最后决定是否依赖
```

### 最终推荐组合
```text
LangGraph + OpenHands + DSPy + promptfoo + Langfuse + Mem0/Zep + LiteLLM
```

---

## 13. 与现有项目代码的映射

| B线模块 | 现有位置 | 状态 |
|---------|---------|------|
| Machine Knowledge | pk_radar/b_line/machine_knowledge.py | ✅ 已有框架 |
| Agent Orchestrator | pk_radar/b_line/agent_orchestrator.py | ✅ 已有框架 |
| Context Engine | pk_radar/b_line/context_engine.py | ✅ 已有框架 |
| Route Engine | pk_radar/b_line/route_engine.py | ✅ 已有框架 |
| Eval Engine | pk_radar/b_line/eval_engine.py | ✅ 已有框架 |
| Feedback Loop | pk_radar/b_line/feedback_loop.py | ✅ 已有框架 |
| Trace Audit | pk_radar/b_line/trace_audit.py | ✅ 已有框架 |
| A-to-B | pk_radar/b_line/a_to_b.py | ✅ 已有框架 |
| MCP Tool Registry | pk_radar/mcp/tool_registry.py | ❌ 待实现 |
| MCP Permissions | pk_radar/mcp/permissions.py | ❌ 待实现 |
| Agent Roles | pk_radar/agents/roles.py | ❌ 待实现 |
| TaskPack Codex | pk_radar/taskpacks/codex.py | ❌ 待实现 |
| TaskPack Deep | pk_radar/taskpacks/deep.py | ❌ 待实现 |
| Execution Sandbox | pk_radar/execution/sandbox.py | ❌ 待实现 |
