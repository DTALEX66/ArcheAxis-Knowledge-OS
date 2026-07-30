# ArcheAxis OS 产品定位

> **ArcheAxis OS is a local-first, evidence-driven, bidirectional learning and knowledge system for individuals and AI.**

> **同一份知识，人学得更深，AI 用得更准。**

## 定位边界

ArcheAxis OS 的产品中心是受治理的学习与知识底座，而不是通用 Agent 平台。它将个人学习和 AI 使用连接到同一份可追溯的 Source、Claim、Evidence 与 Knowledge 之上。

本页定义对外定位和术语边界；它不宣称当前所有产品页面、Agent 功能或自动化能力已实现。当前可验证能力和限制以 [`PROJECT_STATUS.md`](PROJECT_STATUS.md) 与 [`VERIFICATION_POLICY.md`](VERIFICATION_POLICY.md) 为准。

## 一源、双学、双向反馈

```text
原始资料 / Source Asset / Evidence
                    │
                    ▼
          受治理的统一知识底座
              ┌─────┴─────┐
              ▼           ▼
          个人学习链     AI 使用链
              │           │
              └─────┬─────┘
                    ▼
        人工审核与双向知识演进
```

### 个人学习链

```text
资料 → 理解 → 结构化 → 课程/笔记 → 练习 → 复习 → 掌握 → 应用 → Teach Back → 迁移
```

### AI 使用链

```text
Knowledge Unit → Retrieval → Context Pack → Machine Knowledge
→ Task Support → Tool / Agent → Trace → Evaluation → Candidate Lesson
```

## 治理原则

- 人的学习笔记、纠错、练习、人工标注和审批决定，先成为 Candidate。
- AI 生成的新来源、Claim、冲突、解释、练习、任务结果和 Lesson，也先成为 Candidate。
- Candidate 不能自动成为 verified truth，或自动进入 Runtime。
- 用户页面只显示可由本地持久化 API 读回的状态；没有真实合同时必须清楚标明“尚未接入”。
- Agent 是 AI 使用层，不是产品中心；稳定的知识、证据和学习治理不依赖特定模型或 Agent。

## 对外术语

| 不再作为对外主定位 | 对外推荐表达 |
| --- | --- |
| 认知操作系统 / Cognitive OS | Learning & Knowledge System |
| 通用认知 OS / Agent OS | 本地优先、证据驱动的学习知识系统 |
| 认知闭环 | 学习—知识—应用闭环 |
| 认知检查器 | 上下文与证据检查器 |
| 认知演化 | 双向反馈与知识演进 |
| Cognitive Workspace | Human–AI Learning Workspace |

内部架构、历史文档和稳定 canonical ID 可继续保留兼容术语；任何术语替换都不得改变 API、数据库、迁移或 Release 状态。
