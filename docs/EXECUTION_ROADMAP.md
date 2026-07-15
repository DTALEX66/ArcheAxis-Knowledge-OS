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

当前进度：`TaskPackV1` 已建立 KB dataclass 无损往返、SQLite row 合同与安全字段映射、Runtime 显式窄投影；`kb_taskpacks` 已通过带备份的幂等 migration 增加 `context_id`、`requires_review`，并由 v3 repair migration 修复历史 `DEFAULT 0` 非严格 Schema：重建时把不可信审核状态提升为需审核，支持并发串行、真实 WAL 数据库、verified backup 与离线 rollback。`ExecutionTraceV1` 已建立 Runtime 无损往返和 SQLite/KB decoded row adapter，未知行字段拒绝静默丢弃；`EvaluationV1` 已建立当前 Runtime evaluation 的无损往返 adapter，并对未映射扩展字段 fail closed；`LessonV1` 已建立 Runtime 与 SQLite decoded row 无损往返 adapter，未知行字段 fail closed。

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

## 每个 TaskPack 的最小门禁

详细频率、触发条件和证据规则以 `docs/VERIFICATION_POLICY.md` 为准，路线图不再复制执行清单。

1. 声明 Ownership、允许范围和禁止范围。
2. 新行为执行定向 RED → GREEN；纯文档/格式变更只做 convention 与 diff 检查。
3. 冻结 diff 后按变更类型运行一次必要完整本地门禁。
4. 显式路径暂存并检查 secrets、运行时产物和 staged diff。
5. 推送后只验收新提交对应的一次 GitHub Actions run。

独立审查只用于安全、权限、数据库迁移、架构移动和高风险外部写入；普通低风险修复不反复审计。

## 当前执行计划：Phase 2 Research/Knowledge Contracts

1. 完成 `SourceRecordV1` 与 legacy KB document/SQLite row adapter；外部来源默认 `unverified` 和 quarantine/candidate，不允许治理状态静默降级。
2. 依次建立 `ClaimV1`、`EvidenceV1`、`ResearchPackageV1`，明确 provenance、来源独立性、冲突、未知与风险边界。
3. 再推进 `KnowledgeUnit/Relation`、`LearningArtifact/MasterySignal`、`MachineKnowledgeUnit`，保持 candidate/approval/deprecation 可追溯。
4. 每次只选择一条现有真实路径做纯合同与 Adapter tracer；除非有独立迁移 TaskPack，不直接复制或替换旧表。
5. 完成 Phase 2 全部必要合同及门禁后才进入 Phase 3；已前置完成的 TaskPack migration runner 只计为复用资产，不代表 Phase 3 整体完成。
