# HANDOFF — T10 人类侧学习全流程（CODEX）

交接人：DeepSeek（集成者）· 2026-09-05 · 难度：高 · 目标代理：CODEX

## 目标
- 目标→路径→解释→笔记/卡片→测验→Teach-Back→迁移题→错因→FSRS→延迟复测全链；
- 复用旧领域样例，权威状态迁 Rust；模型开放题评分可纠正；
- 来源修订使相关题目失效/待复核，人类掌握证据独立保存；
- 真实完成学习会话及到期复习，重启继续；模型答错和用户纠正能改变后续练习，不自动宣告掌握。

## 上下文
- crates/archeaxis-domain/src/learning.rs、application/src/learning/**、api/src/learning/**、
  services/python-workers/tutoring/**、tests/integration/learning/**（多已为骨架；v01 journey 含 08_learning 单事件）。
- Legacy 领域样例：knowledge_base/cards、sleep_loop 复习调度（旧实现仅作行为来源/样例，权威状态迁 Rust）。
- 契约：packages/contracts/v1 学习/反馈 DTO 以 T02 冻结版为准；FSRS 参数与延迟复测需真实调度状态。

## 验收（任务包 T10）
- 真实完成学习会话及到期复习，重启继续；
- 模型答错和用户纠正能改变后续练习，不自动宣告掌握。

## 环境事实
- 本地模型：ollama qwen3:8b（文本问答/评分可由 qwen3 承担；探针先行）；
- 禁止以“保存一条学习事件”冒充全链路；复习到期需真实时间推进（测试用可控时钟并注明）。

## 切片建议
1. 领域：目标/路径/掌握证据模型 + 状态机与权限（机器不改人类掌握）；2. FSRS/调度与到期复习（重启继续）；
3. tutoring worker 协议接入 + 开放题评分可纠正；4. 错因→练习调整与来源修订失效传播；5. 全链旅程集成测试。

## 输出契约
切片证据+收据 docs/authority/taskpack-0905/T10/；报告 commit SHA 与验收对照。
