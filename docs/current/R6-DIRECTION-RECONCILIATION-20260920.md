# R6 方向校准记录（2026-09-20）

## 记录性质

- `source_report`: `D:\All projects\Record\deep-research-report.md`
- `source_report_last_write`: `2026-09-20 00:03:04`（本机文件属性）
- `authority`: `docs/authority/taskpack-0919-r6/` 与 `docs/current/R6-STATE.json`
- `active_plan_id`: `AAK-LOCAL-GREEN-ABSORB-FIRST-20260919-R6`
- `taskpack_sha256`: `dcc51e922a35d30ca361e9014e040674b62cee644a3ea57aae12ffa6c2949529`
- `record_scope`: 仅记录调研报告与当前 R6 的差分和执行方向；不改写外部报告，不替代 TaskPack，不改变 Owner Gate。

## 当前真值快照

本次校准以当前工作区、R6 权威文件和 GitHub 只读回读为准：

| 项目 | 当前证据 | 结论 |
| --- | --- | --- |
| 本地分支 | `main` | R6 的持续开发主线 |
| 本地 HEAD | `9a7c6568cd84c8017ed9c324379231a03fee02df` | 当前代码事实；报告中的 `0e934f33...` 已过时 |
| 远端 `main` | `9a7c6568cd84c8017ed9c324379231a03fee02df` | 与本地当前提交一致 |
| 远端分支 | GitHub API 只读回读共 18 个分支 | 报告中未完成的分支快照已补成当前观测；不据此删除分支 |
| 远端规则集 | `main-protection` active，要求状态 `a0-gates`；`tag-protection` active | 与当前 CI 聚合 job 名称一致；推送回执提示 required check 被 bypass，不能算 CI PASS |
| 远端主分支保护 API | `/branches/main/protection` 返回 403 | 保护详情不可用，保持 `UNVERIFIED`，不推断缺失配置 |
| 主 CI | `.github/workflows/ci.yml` 含 `a0-gates` 聚合 job | 具备 fail-closed 聚合实现；仍需 exact-SHA 运行回读才能声明 CI 验证 |
| 发布工作流 | `.github/workflows/release.yml` 仅由 `v*` tag 触发 | 作为历史能力保留；R6 禁止创建 tag/release，不能把工作流存在解释为已发布 |
| R6 状态 | `release_status=FROZEN`、`overall_status=IN_PROGRESS` | 当前方向仍是 Local Green Qualification，不是产品发布 |

工作区还存在未跟踪的 `docs/history/**` 和私有交接文件。它们不属于本记录的变更范围，继续保留，不读取、不提交、不清理。

## 报告中可以直接吸收的方向

以下内容与 R6 TaskPack、项目契约和现有实现边界相符，纳入当前执行解释：

1. R6 采用 **Local Green Convergence + Capability Absorption + Human/Machine Learning + Domain Learning Packs** 的主线。
2. 继续执行 **Absorb First → Integrate Second → Build Last**；先查现有实现、legacy、登记的共享资源和成熟 upstream，再决定是否新增代码。
3. Rust SQLite 是唯一 canonical writer。Avalonia、Python workers、sidecar、插件、向量/图索引和模型只能通过契约产生结果或可重建投影。
4. `personal_experience`、`personal_note`、`project_observation` 可以在没有外部证据时成为用户自己的 Accepted Knowledge；机器输出仍从 Candidate 开始，不能用引用或 confidence 代替验证。
5. Local Green Candidate 必须经过项目内 staging、真实首次使用、重启回读、迁移和回滚证据；最终状态只能是 `LOCAL_GREEN_READY_FOR_OWNER_REVIEW` 或 `NOT_READY`。
6. 领域学习包、课程制品和机器经验要通过统一 Core 状态闭环，不能另建第二个知识库或把外部项目原样复制进仓库。

这些原则在当前 R6 权威中已有对应条款；本记录不重新定义它们。

## 必须修正或降级的报告内容

| 报告内容 | 当前处理 |
| --- | --- |
| 报告把 `0e934f33...` 写成 HEAD | 降级为报告生成时的历史快照；当前证据是 `9a7c6568...` |
| 报告建议 Plan ID `AAK-R6-LOCAL-GREEN-ABSORB-FIRST-CONVERGENCE` | 不采用；当前唯一活动 Plan ID 是 `AAK-LOCAL-GREEN-ABSORB-FIRST-20260919-R6` |
| OpenMAIC、H5P、LearningMAP、DeepTutor、RAG-Anything、LightRAG、Graphiti、MemOS 等外部能力 | 仅是候选吸收清单；没有 exact commit/release、许可证、模型权重、运行时和 benchmark 证据前，不得写成已安装或已接入 |
| 报告列出的 30/90/180 天安排 | 作为规划建议保留；不能覆盖 R6 的依赖顺序、Owner 决策和真实证据门 |
| 报告中的“当前架构已成功”类表述 | 只适用于已验证的边界和局部证据；不能扩展成全链路、Green GUI、安装器、签名或发布通过 |
| 报告提出的三项机器动作 | 分支、ruleset、workflow 快照本次已只读复核；外部 provider/license/model-weight exact pin 仍是 A03/A11 的待办 |

## 依据当前证据的方向调整

R6 不切换计划、不重做 R5，也不因为报告的成熟能力列表而批量安装或复制外部项目。执行重心调整为：

### 1. 先收紧 authority 和资源语义

- A00：持续保持 R6 为唯一活动层，并把 live branch/ruleset/workflow 只读快照作为可审计附件；状态页和报告不能成为第二份手工 Current Truth。
- A02：仍由 Owner 决定 `Model library`、共享工具和插件资源根的 schema 语义；在决定前不得猜路径、复制模型或修改共享库。当前状态继续为 `BLOCKED_BY_OWNER_DECISION`。
- A03：只为实际要吸收的能力建立 capability registry 条目，要求 source pin、license、runtime、resource ref、input/output digest、fallback 和 benchmark；未 pin 的候选保持 `PIN_REQUIRED`。

### 2. 再做局部能力和真实闭环

- A04–A12 按已冻结契约推进，优先补当前状态中列出的 partial gap，不为“接入更多项目”而扩大范围。
- A13 当前已有精确候选、worker、合成非空迁移和两次重启身份证据，但仍没有真实 Green 激活、GUI 首次使用、安装器/签名和回滚证据。
- A14 是下一项真正的产品性证明：必须完成 source → knowledge → human learning → machine use → failure → correction → retest → restart readback；不得用 SQL、seed、mock 或 synthetic success 代替。

### 3. 最后独立审计和 Owner Gate

- A15 必须由独立审计完成，执行者不能自签通过。
- A16 只产生 `LOCAL_GREEN_READY_FOR_OWNER_REVIEW` 或 `NOT_READY`。在 Owner Gate 之前不创建 tag、release、公开资产，也不替换现有 Green 目录。

## 后续就绪度与阻塞

| 优先级 | 下一项 | 当前状态 | 前置或限制 |
| --- | --- | --- | --- |
| P0 | A02-01 资源根 schema 决策 | `BLOCKED_BY_OWNER_DECISION` | 需要 Owner 选择 canonical resource-root 语义；执行者不能代决 |
| P0 | A00-02 authority/live snapshot 归档 | `READY_FOR_PROJECT_LOCAL_RECORD` | 本记录已补入当前观测；后续变更仍需新快照和 exact SHA |
| P0 | A03-01 capability registry exact pin | `READY_AFTER_A02` | 只针对实际选定的 provider；不安装未选能力 |
| P1 | A04–A12 partial gap 收敛 | `IN_PROGRESS` | 依赖冻结契约和资源引用；每项要有定向测试与真实限制 |
| P1 | A13 staged candidate follow-up | `TESTED_LOCAL_PARTIAL` | 需要 owner-gated 的真实 Green/安装/签名/回滚范围，当前不执行替换 |
| P0 | A14 real first-use full loop | `OPEN` | 需要真实用户操作与重启回读证据，不能由执行者伪造 |
| P0 | A15 independent audit | `PLANNED` | 必须独立于实施收据 |
| P0 | A16 owner review | `PLANNED` | 仅 Owner 可决定是否进入未来 Release 讨论 |

## 本记录的结论

方向不需要另起 R7 或改写 R6。有效调整是：保持 R6 的 Local Green/Absorb-First 主线，把报告中的历史快照降级为背景，把 exact pin、A02 资源语义、A14 真实闭环和 A15 独立审计重新置于执行门之前。当前可声明的是本地代码和候选的分段证据；不能声明全链路闭环、现有 Green 已替换、CI exact-SHA PASS 或产品发布完成。

本次只读核对未访问 E/F 盘、未读取私有状态、未写外置共享库/真实资料库/现有 Green，未修改原调研报告。
