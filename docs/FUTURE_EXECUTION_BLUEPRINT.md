# ArcheAxis Learning Workspace Future Execution Blueprint

> 状态：未来设计与排序依据，不是当前能力声明、自动执行队列或发布承诺。
>
> 当前可验证状态、限制与质量门禁以 [`PROJECT_STATUS.md`](PROJECT_STATUS.md)、根目录 `README.md`、实时测试和 Git 历史为准。

## 目的

本蓝图将四份外部设计交付中的可复用原则，收敛为 archeaxis-workspace 的唯一未来方向：

- `ArcheAxis Learning Workspace Overview`：产品愿景与八个业务域；
- `ArcheAxis OS V3.0 Blueprint`：模块化单体、统一网关及渐进迁移；
- `ArcheAxis OS V3.1 Documentation`：事实/工作对象/投影区分、命令、Job、Outbox、审计与恢复；
- Google Research / 500 AI Delivery：候选资产治理与 Research-to-Practice 闭环。

这些材料是设计参考，不是供应链代码、运行时依赖、数据库迁移或自动导入授权。任何外部项目、模型、数据集或模板均先进入 Research candidate / quarantine，并遵循许可证、来源、风险、人工审核和回滚边界。

## 北极星

```text
World → Research → Source / Claim / Evidence → reviewed Knowledge
      → Human Learning / Visual Teaching / Spatial Memory
      → governed Machine Knowledge → Runtime Action
      → Evaluation / Lesson / Conflict → reviewed Knowledge Update
```

系统保持单仓库、模块化单体、统一 FastAPI 网关、统一合同、迁移与审计。未来能力通过真实 Facade、版本化 contract、行为对比和小型可回滚切片渐进接入；不得为愿景预建空目录、平行数据库、微服务或第二套运行时。

## 长期领域地图

| 领域 | 责任 | 未来边界 |
| --- | --- | --- |
| Research / VeriScope | 外部资料、quarantine、证据、冲突与审核 | 外部内容不自动成为真相 |
| Knowledge / Archive | 知识版本、关系、冲突、范围与弃用 | 审批和 supersedes 追加，不静默覆盖 |
| Human Learning | 学习资产、练习、错题、掌握与迁移 | 学习行为不等同于事实正确性 |
| Visual Teaching | 事实、记忆、视觉、教学四层资产 | 优先结构化、可编辑 `VisualArtifact`，不是只产 PNG |
| Spatial Memory | Palace / Room / Locus / Route | 语义数据与 2D/2.5D/3D renderer 分离；先 2D |
| Machine Knowledge | scope、风险、上下文、允许/禁止任务 | 仅审核后候选可供 Runtime 使用 |
| Runtime / Praxis | Goal、Plan、Permission、Tool、Trace、恢复 | 不授予 Agent 全磁盘、全知识库或无边界网络权限 |
| Evolution | Evaluation、Lesson、反模式、冲突和更新候选 | 只能提出变更，不能绕过正式审核 |

## 不变工程原则

1. **事实、工作对象、投影分离。** 来源、证据、审批、trace、evaluation 和已确认 lesson 追加或版本化；草稿与布局使用 revision / expected revision；索引与统计可重建。
2. **Candidate 默认。** 外部内容、模型输出、自动生成的知识/课程/视觉/机器知识默认 candidate，不能越过人工审核。
3. **命令与查询分离。** 关键写入采用 command ID、actor、idempotency key、expected revision、correlation/trace ID；读取不改变状态。
4. **事务 Outbox 与可恢复 Worker。** 跨领域派生通过事件而非直接写对方表；业务状态与 outbox 同事务，worker 支持 lease、checkpoint、retry、pause、cancel 和恢复。
5. **可解释审计。** 任一对象可反查来源、证据、审核、派生、模型/工具、版本、失效和 supersedes 关系。
6. **本地优先与安全失败。** 继续使用 approved roots、Safe HTTP、迁移 owner、备份哈希和 fail-closed 规则；密钥、私有正文、绝对路径不进入日志或诊断包。
7. **先最小闭环，后体验与规模。** 不先做微服务、Kubernetes、Neo4j、全量 React、多端同步、3D/VR、通用多 Agent 或模型激活。

## 未来执行序列

每个编号都是待排序的候选 Track；开始前必须建立独立 TaskPack，列明用户目标、范围、风险、contract、RED/GREEN、迁移/回滚和 release gate。没有被用户或当前任务明确选中时，不自动开始。

### Track A — 统一受治理最小闭环

目标是把现有 Research、candidate Knowledge、Learning Artifact、Mastery Signal 和 Machine Knowledge 构件收敛为一个可观察的命令/事件链，而非复制另一套 MCS。

```text
Research candidate → human review → Knowledge candidate/version
→ Learning candidate → approved practice → mastery evidence
→ Machine Knowledge candidate → human approval/deprecation
```

最低验收：拒绝路径、重复命令、revision conflict、worker 中断恢复和从最终对象反查 audit/provenance 都有真实测试。不得自动批准、自动 active 或把模型置信度当作审批。

### Track B — Core orchestration substrate

在 Track A 或由当前真实缺口证明需要时，建立小范围的 command/result、outbox event、job、lease、checkpoint 和 audit projection。复用现有 MigrationOperator；不新建平行 SQLite/migration 框架。SSE/WebSocket、多个 worker 和远端队列只有在已验证的本地 job 需要它们时才进入范围。

### Track C — Cognitive Workspace MVP

只在可查询的命令、审核和 audit 事实稳定后开始。首个工作台是状态/审核/trace 可视化，不是全量品牌页面：

- Research evidence 与 review；
- Knowledge / Learning / Machine Knowledge 生命周期；
- Job、permission、trace、evaluation 与错误 remediation；
- diagnostics 和 capability 状态。

前端 API 类型从 OpenAPI/contract 生成或验证；不让前端直接读 SQLite。旧诊断页面可继续保留为兼容入口。

### Track D — Visual Teaching MVP

先引入经审核知识派生的 `VisualArtifact` 合同及可编辑结构化语义，再实现四类低风险 renderer：概念图、流程图、课程结构、卡片图解。图片、SVG、PPT 或 Canvas 是导出/renderer，不是唯一事实源。生成任务必须是 candidate 并绑定来源、审核和版本。

### Track E — ProjectPack 与受控 Runtime

把真实项目资料、知识、约束、任务、Trace、Evaluation 和 Lesson 连接为 ProjectPack。扩展 Runtime 前先证明每个新增 intent 有 permission、真实工具证据、失败语义、补偿/恢复与评估；不把现有单一 tracer 宣称为通用 Planner。

### Track F — Spatial Memory 2D

只在 Knowledge/Learning 和 VisualArtifact 稳定后创建 `PalacePackage`：稳定 Palace/Room/Locus/Object/Route ID、知识绑定、布局版本、回忆记录和非 3D 可访问视图。2.5D、3D 与 VR/AR 必须复用同一语义合同，不能创建平行事实库。

### Track G — Foundry、Sync 与产品分发

Model/provider、Agent/tool/MCP/plugin registry、sync、desktop/mobile、installer、upgrade、公开版本和企业/多租户均属于后续独立轨道。它们需要各自的风险、能力、隐私、离线恢复、供应链、兼容与发布验收；不得作为早期闭环的捷径。

### Track H–N — 全量候选吸收的依赖序列

候选开源项目、知识库软件和 Obsidian/PKM 生态已统一登记，但登记不代表运行时集成。后续按以下依赖序列逐个建立 TaskPack：

```text
R0 账本真相与 registry 对齐
→ A0 当前 Workspace/Tauri/恢复基线收口
→ H 文档摄入与 Research Adapter Foundry
→ I Knowledge / Search / Graph / Memory
→ J Obsidian / PKM Compatibility Layer
→ K Evaluation / Observability / Provider
→ L Runtime / Agent / Workflow
→ M Workspace Frontend / Desktop Product
→ N Release / Installer / Distribution
```

每个候选项目必须固定 source revision/license，明确 direct/adapter/reference/deferred 模式，拥有 contract、RED/GREEN、真实成功与 unavailable/fallback 测试、数据边界、回滚和 exact-SHA CI。`reference_only` 与 `deferred_review` 项目不得被描述为已安装或已吸收；Obsidian 全面兼容必须单独通过 Vault fixture、附件/链接/语义、增量/冲突和 Windows/Tauri readback 门禁。完整矩阵见 [`ABSORPTION_EXECUTION_MATRIX.md`](ABSORPTION_EXECUTION_MATRIX.md)。

## Google Research / 500 AI 候选资产

该交付包的长期价值是 **Research-to-Practice 选择标准**，不是批量导入任务：

```text
固定来源 → Research Package → reviewed Knowledge
→ Learning/Practice → reproducible evidence → Mastery
→ Machine Knowledge candidate → human review
```

优先候选方向包括 instruction-following evaluation、研究采集/验证、运行时可行性约束、不确定性与行为评测。开始任何一个候选前，必须固定来源 revision 与许可、限定读取范围、创建可重复 fixture，并证明其不会绕过 candidate/review/rollback 边界。500 AI 索引只可作为候选索引，不能自动克隆、运行、安装或升级课程/知识。

## 明确延后项

- 全量 Human Learning OS、完整课程生产线、通用动态 Planner、多 Agent 自治；
- 全量 React/桌面/移动端和同步发布；
- 3D/VR/AR 宫殿、开放世界、多用户实时协作；
- 微服务、Kafka/Kubernetes、Neo4j、为替换现有迁移系统而引入 ORM；
- 真实云模型/provider 激活、密钥集成、模型权重下载；
- 任何将规划、演示、dry-run、mock 或模型置信度描述为生产完成的行为。

## 进入执行前的统一门槛

1. 以 `PROJECT_STATUS.md`、实际代码、测试和 Git 状态确认当前事实，不使用历史规划判断完成度。
2. 为单一纵向切片写 TaskPack：目标、非目标、owner、数据边界、风险、失败/回滚语义。
3. 对新行为先写唯一可解释的 RED，再做最小 GREEN；纯文档只运行 convention 与 diff 检查。
4. 按 `VERIFICATION_POLICY.md` 运行受影响测试、必要完整门禁和独立审查；提交/推送只使用显式路径。
5. 更新 `PROJECT_STATUS.md` 的稳定事实，不重复保存易过期测试数字、临时任务列表或 handoff 指令。
