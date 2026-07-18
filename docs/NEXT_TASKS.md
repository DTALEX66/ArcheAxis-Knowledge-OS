# Cognitive-Loop-OS 后续任务列表

> 更新：2026-07-18
> 当前基线：`daf16f291a504689957101427f382890687d37cd`
> 原则：Git 是唯一源码真相；每个任务使用独立分支；先定向 RED/GREEN，再执行必要完整门禁；推送后核对 exact-SHA CI。

## 当前结论

- Phase 0–4 基线已完成：安全边界、Facade/Contracts 起点、Migration Runner、GitHub Research candidate-only 闭环。
- Vector/FTS candidate、显式 activation、rollback boundary 已完成。
- 生产容器栈已完成；开发容器已改为 Git-mounted reusable toolchain。容器不再作为独立源码副本。
- GHCR 自动发布已移除；当前容器职责是可复现部署与 CI smoke，不阻塞业务主线。
- 旧的 `P00A_CONTAINER_CORRECTION_RELEASE` 是历史 reconciliation 报告，不是当前未完成任务。
- 当前工作区应保持 clean，主分支应与 `origin/main` 一致。

## P0：开发环境收口（当前电脑完成后关闭）

### P0.1 Docker Desktop 首次初始化

**目标：** 在本机完成开发容器的真实 build/run，消除目前唯一的环境验证缺口。

**动作：**

1. 重启 Docker Desktop；如 Linux engine 仍为 stopped，重启 Windows 并确认 WSL2。
2. 在仓库执行 `docker compose -f docker-compose.dev.yml config --quiet`。
3. 执行 `docker compose -f docker-compose.dev.yml build dev`。
4. 执行 `./run_dev_container.ps1 pytest tests/test_dev_container_contract.py -q`。
5. 记录真实 Docker build/run 结果；不要把静态 YAML 解析当作容器实测。

**验收：** dev image build 成功，容器内测试通过，源码修改能在宿主机 `git diff` 看到。

## P1：Phase 5 Knowledge/Learning/Mastery/Machine Knowledge 治理（下一条业务主线）

### P1.1 Research candidate → KnowledgeUnit/Relation

**目标：** 将已持久化、quarantined 的 `ResearchPackageV1` 通过显式人工审批转换为候选 KnowledgeUnit/Relation。

**约束：**

- 默认 candidate，不得自动成为 verified/approved truth。
- 保留 source、claim、evidence、finding、package provenance。
- 同一 GitHub repository metadata/README 仍只计一个 source group。
- 审批、拒绝、弃用必须可追溯、幂等、可回滚。

**主要路径：** `inspiration_research/`、`knowledge_base/`、`app/contracts/`、`shared/migration.py`、`tests/`、`workspace/intake/`

**验收：** candidate package 可生成 KnowledgeUnit/Relation candidate；无审批不得升级；拒绝/弃用保留 provenance；定向 RED/GREEN、迁移测试、全量 pytest、exact-SHA CI 通过。

### P1.2 KnowledgeUnit/Relation 版本与弃用

**目标：** 建立知识版本、冲突和弃用状态边界。

**约束：**

- 不覆盖旧版本；新版本必须保留 parent/provenance。
- 冲突进入 review，不静默覆盖。
- Machine Knowledge 不得把旧 active 行静默提升为 approved。

**验收：** version graph、conflict review、deprecated projection、rollback/backup 证据完整。

### P1.3 LearningArtifact/Mastery/MachineKnowledge 审批链

**目标：** 将 Knowledge candidate 接入学习产物、掌握信号和机器知识候选治理。

**验收：**

```text
ResearchPackage candidate
→ KnowledgeUnit/Relation candidate
→ human review
→ LearningArtifact
→ MasterySignal
→ MachineKnowledge candidate
→ explicit approval/deprecation
```

不得把模型置信度、默认值或 dry-run 当作真实审批证据。

## P2：通用 Runtime 闭环

### P2.1 Dynamic Planner 最小真实切片

**目标：** 在现有 `file_read` tracer 之外，建立一个受约束的通用 Goal → Plan → Permission → Execute → Evidence 流程。

**范围：** 先实现一个真实工具意图，不实现大而全 Planner。

**必须复用：** 现有 Runtime、Permission、Executor、Evidence、Evaluation、Lesson contracts。

**禁止：** 模型自由执行、无工具证据 success、把单一 tracer 宣称为通用 Planner。

### P2.2 多维 Evaluation 与 Reviewed Feedback

**目标：** 将 correctness、completeness、evidence、safety、efficiency、maintainability、knowledge contribution 接入真实审核。

**验收：** 失败任务不生成 success Lesson；reviewed feedback 可被下一次 planner 消费；无样本/无证据明确为 unverified。

## P3：统一 Sleep Loop

**目标：** Sleep Loop 只复用同一套 Planner、Permission、Executor、Evidence、Evaluation、Lesson，不维护第二套完成语义。

**顺序：**

1. 将现有 sleep task ledger 对接 Runtime execution port。
2. 实现 dependency queue、retry、pause、approval、crash recovery。
3. 实现 resume/replan 证据。
4. 为长任务补充状态、租约、失败恢复和幂等测试。

**验收：** pending/running/blocked/failed/paused/completed 状态有明确证据；崩溃恢复不重复写入；统一 Runtime/Sleep Loop 测试通过。

## P4：Phase 9 Minimum Complete System Alpha

必须逐条真实闭环，不提前宣称 Alpha：

1. `GitHub URL → Research → Knowledge → Artifact → Task → Evaluation`
2. `Document → Card → Review → Mistake → Mastery → Machine Candidate`
3. `Goal → Dynamic Plan → Permission → Evidence → Evaluation → Lesson`
4. `New Evidence → Conflict → Knowledge Version → Machine Knowledge Deprecated`
5. `Long Goal → Dependency Queue → Execute → Evidence → Resume/Replan`

每条闭环都需要真实运行证据、失败路径、持久化 provenance、测试与 CI SHA。

## P5：产品化（Phase 9 通过后）

仅在 Phase 9 完成后考虑：

- 完整学习科学与 Research Intelligence
- 多模态课件
- MCP/Model Router/Multi-Agent
- Web/Desktop/Mobile
- Installer/Upgrade/Diagnostics
- Public Alpha/Beta/Stable

当前不提前做 UI、移动端、3D/VR、Kubernetes、GHCR 发布或大规模微服务拆分。

## 每个任务的固定执行协议

1. 从 `origin/main` 创建 `agent/<task-name>` 分支。
2. 读取相关 intake、合同、`AGENTS.md` 和当前实现。
3. 写定向 RED 测试，确认失败原因真实且唯一。
4. 实现最小 GREEN，不扩大范围。
5. 运行受影响测试，再运行必要完整门禁。
6. 检查 secrets、运行时产物、staged diff 和 `git diff --check`。
7. commit + push 分支；不直接覆盖另一台电脑的工作区。
8. 主机审查并合并；合并后核对 local SHA == origin SHA 和对应 CI run。
9. 更新本文件和对应 intake 的状态，避免历史报告继续冒充当前待办。

## 当前唯一推荐顺序

```text
P0.1 Docker engine 实测
→ P1.1 Research candidate 接 KnowledgeUnit/Relation
→ P1.2 版本/冲突/弃用
→ P1.3 Learning/Mastery/MachineKnowledge 审批链
→ P2.1 Dynamic Planner 最小切片
→ P2.2 Evaluation/Feedback
→ P3 Sleep Loop 统一执行
→ P4 五条 Alpha 闭环
→ P5 产品化
```
