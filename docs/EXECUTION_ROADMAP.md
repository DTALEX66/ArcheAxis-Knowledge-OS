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
inspiration_research/   可安装的当前研究雷达和研究资产
Inspiration-Research/   deprecated source-checkout launcher
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

### Phase 1.0 前置门禁：命名与编码契约

- `config/naming-registry.yaml` 是服务 ID、Python package、兼容别名和中英文展示名的唯一机器真相。
- `scripts/check_repository_conventions.py` 在 pre-commit 扫 index、在 CI 扫 HEAD，阻断编码、Unicode、路径和大小写差异。
- 详细规则见 `docs/NAMING_ENCODING_CONVENTIONS.md`；历史名称只能作为显式 deprecated alias 迁移。

### Phase 1.1 Facade 与架构守卫

- **已完成** Research、Knowledge、Enhancement、Runtime、Contracts 公共 Facade。
- Facade 调用当前 `app/shared/knowledge_base/inspiration_research` 真实实现。
- CI 已阻止 Contracts/Platform 反向依赖业务模块。
- 新代码禁止增加 `sys.path` 变异。
- 禁止运行时代码引用 A 项目路径。

## Phase 2：版本化 Contracts

当前进度：首批合同已完成。Runtime 组、Research 组、Knowledge/Relation、Learning Artifact/Mastery Signal 与 Machine Knowledge 均已建立显式 `V1` canonical model 和现有真实路径 Adapter tracer。旧对象可表示字段无损往返；未知字段 fail closed；窄投影显式报告损失；caller-supplied 或 legacy-unverified 数据不得自动升级为 verified、reviewed、approved 或 published。既有 `kb_taskpacks` migration 是已验证复用资产，不代表 Phase 3 完成。

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

1. ✅ 移除代码内默认管理员 Key。
2. ✅ 阻止 Token 请求者自选管理员角色。
3. ✅ 统一 Safe HTTP：DNS、私网、metadata、redirect、大小、类型、timeout 与 hostile XML 边界。
4. ✅ Approved Source Roots 和 symlink/junction containment。
5. ✅ 用稳定哈希替换持久化 Python `hash()`；VectorDB 已使用 versioned `sha256-v1`，索引重建仍独立处理。
6. 🟡 FTS/Vector 可重建、可回滚迁移：shadow candidate rebuild、验证、切换与 rollback 已完成；尚待通用 migration registry/operator 接管 owner 生命周期。
7. ✅ Rate Limiter 接入主网关；已覆盖身份分桶、proxy trust、早期拒绝预算和真实启动入口。
8. **当前刀**：正式 Migration Runner——TaskPack migration 的备份、幂等、rollback 已成熟，下一步统一 registry/operator CLI、Vector/FTS owner 与 Phase 3 集成验收。

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

`read file: <repo-relative-path>` 已形成第一条真实 Planner → Permission → Evidence → Evaluation → Lesson tracer；echo/no-op/dry-run 不再能通过成功评估。当前核心缺口是把该单一显式意图扩展为通用 Dynamic Planner，并让更多工具和 Sleep Loop 复用同一证据语义。目标闭环：

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

## 每个 TaskPack 的最小门禁

详细频率、触发条件和证据规则以 `docs/VERIFICATION_POLICY.md` 为准，路线图不再复制执行清单。

1. 声明 Ownership、允许范围和禁止范围。
2. 新行为执行定向 RED → GREEN；纯文档/格式变更只做 convention 与 diff 检查。
3. 冻结 diff 后按变更类型运行一次必要完整本地门禁。
4. 显式路径暂存并检查 secrets、运行时产物和 staged diff。
5. 推送后只验收新提交对应的一次 GitHub Actions run。

独立审查只用于安全、权限、数据库迁移、架构移动和高风险外部写入；普通低风险修复不反复审计。

## 当前执行计划：Phase 3 安全和数据正确性 P0

1. Phase 2 首批合同 Release Train 已完成；`ContextPackV1` 与通用 `validate_contract` 不在首批合同清单中，继续保持 deferred，不以空壳扩大 Facade。
2. Phase 3 的管理员凭据、Token 角色提升、Rate Limiter、Safe HTTP、approved roots、稳定哈希和 Vector/FTS shadow switch/rollback 边界已关闭。
3. 下一项是通用 Migration Runner registry/operator CLI、Vector/FTS owner 接入与 Phase 3 集成验收。
4. Phase 3 每个安全、权限或 migration 任务独立冻结、完整验证、审查和发布，不进入普通低风险批量。
5. Phase 7 的 `file_read` tracer 不等于通用 Dynamic Planner；Phase 3–9 整体仍未完成，不得提前宣称 Alpha 闭环完成。
