# 三项目分层架构审计（基于 GitHub 权威定位核实）

> 审计日期：2026-08-18。方法：直接读取三个仓库的 README / PROJECT_POSITIONING.md 定位原文，对照"三项目联动分层架构决策文档"逐条核验。

## 一、三个项目 GitHub 真实定位（已核实）

| 项目 | GitHub 权威定位原文 | 关键约束 |
|---|---|---|
| **ArcheAxis-Knowledge-OS** | "local-first, evidence-driven, bidirectional Human-AI Learning & Trusted-Knowledge Workspace. NOT an Agent OS" | 系统级人机双向学习与可信知识治理工作台；不等于通用 OS/Agent Runtime/自治工作流/多 Agent 产品 |
| **WORK-LAB** | "client-neutral workflow control plane for the user's whole AI workflow — owns the highest user-level capability layer (global configuration)" | **明确 NOT**: agent runtime / model gateway / credential store / chat UI / prompt archive / platform deployment / second database |
| **DESIGN-LAB** | "面向职业视觉设计的、AI 原生、平台中立的设计智能与生产能力实验室。Host-native；当前参考宿主 Open Design" | host-native first，不重建画布/编辑器/模型网关/SaaS；Agent-platform-neutral |

## 二、文档的错误（按严重度）

### 🔴 错误 1（最严重）：WORK-LAB 被定位成"运行时操作系统"，实际是"控制平面"

**文档说**（第 5.1/7.2 节）：
> WORK-LAB = AI Control Plane / 运行时操作系统，负责 Agent Runtime、Model Runtime、Tool Runtime、Vision Runtime（GPU 调度、SAM2/Qwen-VL 运行时）

**GitHub 实际**（PROJECT_POSITIONING.md "Explicit non-positioning"）：
> WORK-LAB is **not**: Hermes/Codex/CC Switch or another **agent runtime**; a **model/provider gateway**, credential store, chat UI...

**真相**：WORK-LAB 是 **control plane（控制平面）**，只管理"全局配置层（Rules/Skills/plugins/MCP/Memory/Capabilities/policy）+ 工作流治理 + 只读观测"。它**不部署任何运行时**：
- Agent 执行 → 客户端（DSH/Hermes/Codex）承担，DSH 就是 "replaceable Agent Runtime"
- 模型/GPU/视觉运行时 → 宿主（Open Design 等）承担
- WORK-LAB 只是"投影配置到客户端 + 治理工作流 + 观测"——**它管的是"怎么管"，不是"怎么跑"**

### 🔴 错误 2：第 8 节"视觉能力三分"把视觉运行时归 WORK-LAB

文档说"视觉运行时（GPU 调度、SAM2/Qwen-VL）由 WORK-LAB 统一部署管理"——**错**。WORK-LAB 明确不是 model gateway、不部署运行时。视觉运行时归**宿主**（Open Design 的设计运行时）或客户端。

### 🟡 错误 3：三层依赖方向（DESIGN-LAB 构建在 WORK-LAB 之上）

文档说 DESIGN-LAB "第三层，构建在 WORK-LAB + ArcheAxis 之上"。实际 DESIGN-LAB 是 **Host-native**（宿主 Open Design 是主角），通过 Adapter 接入宿主，不是"构建在 WORK-LAB 之上"。WORK-LAB 管理 DESIGN-LAB 宿主（Open Design）的全局配置层投影，但 DESIGN-LAB 的设计产品/能力是独立领域。

### 🟡 错误 4：ArcheAxis "不做执行"表述过严

文档说 ArcheAxis "不拥有 Agent Runtime、不调度任务、不调用外部工具"。基本正确（NOT an Agent OS），但 ArcheAxis 有**受限 Planner tracer**（read file: 纵向切片）+ Plan→Permission→Execution→Trace→Evaluation→Lesson 闭环——它做**受治理的受限执行**（局部闭环），只是不做通用 Agent Runtime/多 Agent 调度。表述应精确为"不做通用 Agent 调度，但保留受限受治理执行 tracer"。

## 三、正确的分层（基于真实定位）

真正的分层不是"三层运行时依赖"，而是**知识层 / 控制层 / 领域层 + 横向运行时**：

    ┌───────────────────────────────────────────────┐
    │  DESIGN-LAB  设计智能（Host-native）           │ 领域智能层
    │  设计判断/方法/质量/交付，宿主=Open Design     │
    └───────────────────┬───────────────────────────┘
                        │ Adapter 接入宿主
    ┌───────────────────▼───────────────────────────┐
    │  WORK-LAB  控制平面（NOT runtime）             │ 控制/治理层
    │  全局配置层(Rules/Skills/MCP/Memory/Policy)    │
    │  + 工作流治理 + 只读观测                       │
    │  → 投影到客户端(Hermes/Codex/DSH/OpenDesign)   │
    └───────────────────┬───────────────────────────┘
                        │ 知识读写走 ArcheAxis API
    ┌───────────────────▼───────────────────────────┐
    │  ArcheAxis  人机双向学习 + 可信知识（NOT Agent OS）│ 知识根基层
    │  唯一知识真源 + candidate 治理 + 人类学习链     │
    └───────────────────────────────────────────────┘

横向（不属于分层，是"被管理对象"）：
  Agent Runtime     = 客户端 DSH / Hermes / Codex
  模型/GPU/视觉运行时 = 宿主 Open Design 等
  这些由 WORK-LAB 通过 Adapter 治理，但运行时不归 WORK-LAB

## 四、文档"正确"的部分（保留）

1. ✅ ArcheAxis 定位引用准确，四条红线（人机双向/独立系统/唯一治理权/不做 Agent）与 GitHub 一致
2. ✅ 唯一知识真源 + 唯一治理权：WORK-LAB/DESIGN-LAB 不自建知识库，candidate 治理归 ArcheAxis 独占——方向正确
3. ✅ 三个项目不合并、不都做 Agent、不都做知识库——正确
4. ✅ 消除重复建设的动机（知识/Agent/模型视觉各自重复部署）——正确

## 五、修正后的收敛建议

1. WORK-LAB 保持控制平面：不部署 GPU/模型/视觉运行时，只做"配置投影 + 工作流治理 + 观测"。删掉文档里"运行时操作系统/GPU 调度/SAM2/Qwen-VL 运行时"的错误定位。
2. 运行时归属澄清：Agent Runtime = 客户端（DSH/Hermes/Codex）；模型/视觉运行时 = 宿主（Open Design）。WORK-LAB 通过 Adapter 治理它们，不拥有它们。
3. 视觉能力三分修正：视觉运行时 → 宿主；视觉记忆（embedding/理解结果）→ ArcheAxis；视觉智能（美学判断）→ DESIGN-LAB。WORK-LAB 不部署视觉运行时。
4. DESIGN-LAB 关系修正：不是"WORK-LAB 之上"，是"Host-native，通过 Adapter 接入宿主（Open Design）"，WORK-LAB 只投影其全局配置。
5. ArcheAxis 表述精确化："不做通用 Agent Runtime/多 Agent 调度"，但保留"受限受治理执行 tracer"（read file: 等局部闭环）。
6. 分层结论修正：三层 = 知识层（ArcheAxis）+ 控制层（WORK-LAB）+ 领域层（DESIGN-LAB），运行时是横向被管理对象（客户端/宿主），不属于分层成员。

## 六、最终结论

文档的动机和 ArcheAxis 部分正确，但 WORK-LAB 定位错了：它不是"运行时操作系统"，而是"客户端中立的控制平面"。这个修正很关键——它决定了：
- WORK-LAB 做减法：不建运行时，只做配置治理 + 工作流 + 观测（这正是它现在的实际状态）
- 视觉/模型/Agent 运行时归属客户端宿主，不重复部署
- 三层分工清晰：ArcheAxis 管知识，WORK-LAB 管控制，DESIGN-LAB 管设计判断，运行时由宿主/客户端承担

一句话：不是"知识库 + 运行时 + 应用"三层，而是"知识 + 控制 + 领域"三层，运行时横向挂在客户端宿主上、由 WORK-LAB 治理但不由 WORK-LAB 拥有。
