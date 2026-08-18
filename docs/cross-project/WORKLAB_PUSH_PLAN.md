# WORK-LAB → ArcheAxis 推送更新规划（v1 · 2026-08-18）

> 依据：THREE_PROJECT_LAYERING_DECISION.md（v5，两仓同步）+ ArcheAxis AGENTS.md §9（WORK-LAB 可选经稳定 CLI/API 协议协调，永不是运行时前置）+ 本仓 docs/cross-project/ 现状。
> 三项目不变式：ArcheAxis = 唯一知识总库 + 人机双向重型学习系统（NOT Agent OS）；WORK-LAB = 控制转化器 + 控制平面；DESIGN-LAB = 设计转化器。知识单向归 ArcheAxis，项目开放扩展，分阶段演进。

## 1. 当前机制（阶段 1 · 已有事实）

- 现状：无自动化同步脚本。前序会话将 WORK-LAB `00-governance/` 的 3 份文档（v4→v5 分层决策 / 分层审计 / 未来蓝图分析）复制到 ArcheAxis `docs/cross-project/` 并 push GitHub。
- 本仓已收：`docs/cross-project/THREE_PROJECT_LAYERING_DECISION.md`（v5）、`THREE_PROJECT_LAYERING_AUDIT.md`、`THREE_PROJECT_FUTURE_BLUEPRINT_ANALYSIS.md`。

## 2. 推送内容分类（按 v5 分层）

| 类别 | 现在（阶段 1） | 未来（阶段 2，OS 治理闭环完整后） |
| --- | --- | --- |
| 治理/决策/审计文档 | ✅ 推送到 docs/cross-project/ | ✅ 继续推送 |
| 规则 / 技能 / 插件（可执行资产） | ❌ 归各项目所有，不迁移 | ⬆️ 逆向归档为 Knowledge Unit / Machine Knowledge Unit（candidate→review→verified） |
| 知识（事实/经验/方法/Lesson） | 由项目执行产出回写 Candidate（经 API） | 统一治理后为唯一真源 |
| 项目/模块状态（Observer 只读投影） | 不推送，读 ArcheAxis 只读投影即可 | 不变 |

## 3. 推送机制（约定，先人后自动化）

### 3.1 文档推送（现在即可用）

- 来源：WORK-LAB `00-governance/`（治理/决策/审计/蓝图）；DESIGN-LAB `project-memory/cross-project/`（设计侧镜像）。
- 目标：ArcheAxis `docs/cross-project/`。
- 触发：治理版本更新（如 layering v5→v6）或有新的跨项目决策时。
- 动作（Agent 可执行）：
  1. 核对 WORK-LAB 对应文件内容（exact 内容一致，只允许头部加"来源：WORK-LAB 00-governance/xxx"说明）
  2. 复制到 `docs/cross-project/`
  3. 两仓分别 commit + push（先 WORK-LAB 后 ArcheAxis，或同 commit message 前缀）
  4. 在 ARCHIVE 侧更新索引（docs/cross-project/README.md，本规划落盘后补建）
- 验收：内容一致 + 双端 git 记录 + 头部标注来源。

### 3.2 知识/资产推送（阶段 2 触发后）

- 触发条件（v5 §3 阶段 2）：ArcheAxis 知识治理闭环完整可用（candidate → review → verified 全链路 + 稳定知识 API 契约）。
- 当前相关进度：`app/knowledge/promotion.py`（Research→Candidate+人工批准）、`machine_knowledge.py`（mastered signal→candidate）、`distillation.py`（人机蒸馏候选→规则）已落地 —— 治理闭环骨架存在，但"稳定知识 API 契约 + verified 全链路"尚未完整，阶段 2 未触发。
- 动作：各项目把规则/技能/插件逆向提炼为 Knowledge Unit / Machine Knowledge Unit，经 candidate→review→verified 归档，单向不回头。

### 3.3 自动化方向（后置，非当前必需）

- WORK-LAB 侧可新增 sync 脚本（如 `10-workflow/workflow-assistance/scripts/workflow/sync_cross_project.py`），经稳定 CLI/API 协议（ArcheAxis AGENTS.md §9）做文档镜像；
- 前提：协议契约稳定 + 双端验收门禁（内容 hash 一致）；不做运行时耦合，ArcheAxis 可脱离 WORK-LAB 独立运行。

## 4. 门禁与纪律

- 红线（v5 §7）8 条全部适用；推送不得改变 ArcheAxis 定位（NOT Agent OS、唯一治理权、人机双向不可偏废）。
- 受控调用边界：ArcheAxis P3 = 知识/学习资产调用，不是 Agent/工具调用；P10 = 知识治理辅助受限 tracer，不是通用 Agent 执行。
- 推送内容不得包含凭据/密钥/私有路径（两仓安全规则一致）。
- 双端单 writer：一次推送 = WORK-LAB 一个任务卡 + ArcheAxis 一个任务卡（或同一 Agent 顺序执行），各仓独立 commit/回滚。

## 5. 待办（本规划落盘后）

1. 补建 `docs/cross-project/README.md` 索引（来源文件 ↔ 本仓副本 ↔ 最近同步 commit）。
2. 建立 WORK-LAB 侧镜像文档（00-governance/CROSS_PROJECT_SYNC_PLAN.md 或并入现有决策文档）。
3. 每次推送在 intake 留痕（如 workspace/intake/0XX_cross_project_sync.md）。
4. 阶段 2 触发条件在 ArcheAxis 侧设检查点（知识 API 契约发布时复核本文档）。
