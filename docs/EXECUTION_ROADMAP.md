# Cognitive-Loop-OS 执行路线图

> 状态：执行基线。完成度必须以代码接入、测试、安全、审计和回滚证明，不以文件、API 或测试数量代替。

## 项目边界

- 唯一开发目标：本仓库 Cognitive-Loop-OS。
- 外部 A 项目 Obsidian-Assistance 已完成分析与通用能力吸收，后续严格只读且不再扫描、测试、修改或同步。
- Obsidian 只保留为可选输入/投影适配器，不是系统核心。
- 保持单 Git 仓库、模块化单体、单 API 网关、统一配置、统一迁移和统一审计。

## 执行原则

1. **Existing Assets First**：优先包装、修复和接入现有实现。
2. **Contracts First**：跨模块对象先形成版本化合同。
3. **Copy → Validate → Switch**：Facade、合同测试、新旧结果比较、切换、兼容期、最后清理。
4. **No Fake Completion**：stub、echo、preview、dry-run、文件存在和置信度都不能冒充真实成功。
5. **Candidate by Default**：外部资料和 AI 输出默认进入 quarantine/candidate；正式知识与机器知识必须可追溯、可审核、可撤销。
6. **Small Auditable Patches**：安全、数据迁移、功能和目录迁移分开提交；禁止一次性搬树。

## 当前架构

```text
app/                    当前认知运行时
knowledge_base/         可安装的知识、学习和领域 API 包
Inspiration-Research/   当前研究雷达和研究资产
shared/                 现有跨域实现，逐步通过 Facade 收口
shared-contracts/       现有 Schema、适配器与项目注册
```

长期目标采用可运行 Facade 渐进形成：

```text
apps/ + modules/ + platform/ + integration/
```

新目录不得是空壳；每个入口必须调用真实实现并具备合同测试。

## Phase 0：最新真实基线

在当前安全、质量和 `knowledge_base` 打包改动提交后，生成：

```text
migrations/reports/phase-0/
├── ASSET_MAP.md
├── FILE_INVENTORY.csv
├── API_ROUTE_MAP.json
├── DEPENDENCY_REPORT.md
├── TEST_BASELINE.md
├── SECURITY_BASELINE.md
├── ARCHITECTURE_GAPS.md
├── REUSE_DECISIONS.md
└── PHASE_1_TASKPACK.md
```

Phase 0 只审计本仓库，不访问 Obsidian-Assistance，不移动业务代码，不改数据库结构。

## Phase 1：Facade 与 Architecture Guard

- 建立 Research、Knowledge、Enhancement、Runtime、Contracts 公共 Facade。
- Facade 先调用当前 `app/shared/knowledge_base/Inspiration-Research` 实现。
- CI 阻止 Contracts/Platform 反向依赖业务模块。
- 新代码禁止增加 `sys.path.insert`。
- 禁止运行时代码引用 A 项目路径。

## Phase 2：版本化 Contracts

首批合同：

- SourceRecord
- Claim / Evidence / ResearchPackage
- KnowledgeUnit / Relation
- LearningArtifact / MasterySignal
- MachineKnowledgeUnit
- TaskPack / ExecutionTrace / Evaluation / Lesson

现有 SQLite 对象先通过纯 Adapter 映射，不立即复制或替换当前表。

## Phase 3：安全和数据正确性 P0

按顺序关闭：

1. 移除代码内默认管理员 Key。
2. 阻止 Token 请求者自选管理员角色。
3. 统一 Safe HTTP：DNS、私网、metadata、redirect、大小、类型、timeout。
4. Approved Source Roots 和 symlink/junction containment。
5. 用稳定哈希替换持久化 Python `hash()`。
6. FTS/Vector 可重建、可回滚迁移。
7. Rate Limiter 接入主网关。
8. 正式 Migration Runner、备份、重复运行和回滚测试。

设计包的 `ALPHA_SCHEMA.sql` 仅作为目标模型；当前表与目标表必须逐表映射，禁止直接执行。

## Phase 4：Research

```text
Source → Collect → Parse → Claim → Evidence
→ Cross Validate → Conflict/Unknown/Risk → Research Package
```

所有外部内容先 quarantine；推荐来源不等于已验证；同一来源的多种提取方式不计为独立来源。

## Phase 5：Knowledge 与学习治理

```text
Research/User Source → Knowledge Unit → Relation
→ Card → Review → Mistake → Mastery Signal
→ Machine Candidate → Approval → Active → Deprecated
```

机器知识必须包含来源、scope、risk、allowed/blocked tasks 和撤销路径。课程证据、转换总账与核验能力在本仓库原生实现，不再读取 A 项目。

## Phase 6：Enhancement

统一 LearningArtifact：简单解释、专业解释、摘要、卡片、问题、图示和质量报告。复用现有 Mermaid、Canvas、Progressive Summary；生成结果默认 candidate。

## Phase 7：真实 Runtime

当前固定 echo Planner 和二值 Evaluator 是核心缺口。目标闭环：

```text
Goal → Intent → Context → Dynamic Plan → Permission
→ Tool Evidence → Trace → Multi-dimensional Evaluation
→ Candidate Lesson → Reviewed Feedback
```

无有效工具证据不得 success；simulated/no-op 不得生成成功 Lesson。

## Phase 8：统一 Sleep Loop

Sleep Loop 复用同一 Planner、Permission、Executor、Evidence、Evaluation 和 Lesson，支持 dependency、retry、replan、pause、approval 与崩溃恢复，不维护第二套“完成”语义。

## Phase 9：Minimum Complete System Alpha

必须真实通过五条闭环：

1. GitHub URL → Research → Knowledge → Artifact → Task → Evaluation。
2. Document → Card → Review → Mistake → Mastery → Machine Candidate。
3. Goal → Dynamic Plan → Permission → Evidence → Evaluation → Lesson。
4. New Evidence → Conflict → Knowledge Version → Machine Knowledge Deprecated。
5. Long Goal → Dependency Queue → Execute → Evidence → Resume/Replan。

## Phase 10：产品化

Phase 9 通过后再推进完整学习科学、Research Intelligence、多模态课件、MCP/Model Router/Multi-Agent、Web/Desktop/Mobile、Installer、Upgrade、Diagnostics 和 Public Alpha/Beta/Stable。

## 每个 TaskPack 的门禁

1. 读取当前 Phase 和 Git 状态。
2. 声明 Ownership 与禁止范围。
3. 先写失败测试，再最小实现。
4. 运行定向测试、changed-file Ruff/type gate。
5. 运行相关合同、集成和安全测试。
6. 检查 secrets、路径、运行时产物与 diff。
7. 独立规范审查和代码质量审查。
8. 显式路径暂存，不使用 `git add .`。
9. 提交中写明回滚方式。
10. Gate 通过后才进入下一 TaskPack。

## 当前最近任务

1. 完成安装后运行时可写路径。
2. 每次阻塞修复后重新运行 Root、Knowledge Base、Integration、Ruff、wheel 和安全冒烟。
3. 对最终冻结 diff 重新做独立审查；先前审查结果不自动覆盖后续修改。
4. 分逻辑提交并同步远端。
5. 基于最新干净 HEAD 执行 Phase 0，而不是继续访问 A 项目。
