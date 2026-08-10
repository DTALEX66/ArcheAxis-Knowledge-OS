# OpenHuman 系列专项拆解

## 正确定位

OpenHuman 不是 AXOS 的入口、替代平台或主运行时。它是一个综合能力参考项目。

```text
Human
→ AXOS Human Console
→ AXOS Control Plane
→ Hermes / Codex / Model & Tool Providers
→ AXOS Artifact / Trace / Eval / Memory
```

## 吸收项

### OpenHuman
- Human-first 交互
- Agent 提议、用户审核、再执行
- SuperContext 式任务前置检索
- 分层 Agent：Reflex / Reasoning Core / Workers / Reviewer
- 运行时间线、成本回放和失败根因
- Privacy Mode、凭据引用、审批门

### TinyCortex
- 摄取准入：先判断值不值得记忆
- 新鲜度衰减、互动权重和主动遗忘
- Summary Tree
- Markdown/标准知识单元为可检查源
- 向量、图、关键词、摘要树为可重建索引
- Taint / Provenance

### TinyAgents
- root_run_id / parent_run_id
- Agent-as-tool
- recursion_depth 和递归限制
- Durable Graph、Checkpoint、Interrupt、Resume、Time Travel
- 子 Agent 成本和事件向根运行汇总
- 声明式工作流与受控 REPL 的设计思想

### TinyFlows
- WorkflowDraft → Validate → Compile → Approve → Run → Resume
- 条件、Switch、并行、Merge、Sub-workflow
- stop / continue / route 错误策略
- 人工审批节点
- schema_version / type_version

### TinyJuice
- 工具输出压缩
- 被省略内容必须生成 Recovery Token
- 支持日志、JSON、Diff、代码、搜索结果和HTML
- 压缩产物必须有原始校验和、策略、恢复引用和过期规则

## 不吸收项
- OpenHuman 自有客户端、账号体系和后端
- 第二套 Memory / Job / Workflow / Audit 事实源
- Agent Economy、支付和社交网络
- 未经确认的自动后台行为
