# HANDOFF — T08 云端模型联网交叉核查（CODEX）

交接人：DeepSeek（集成者）· 日期：2026-09-05 · 难度：高 · 目标代理：CODEX

## 目标
有界联网核查闭环（决策 SUP-008 提前至本轮）：
- 真实搜索/抓取、查询规划、原始来源锚点、来源归组与反证；
- 云端结构化逐命题评估；Core 检查引用存在与修订绑定；
- coverage/成本/时限/失败恢复；原件和个人定义不受证据门槛阻止保存；
- 真实网页核查可重现，重复转载不算独立证据；搜索失效/断网/预算耗尽给 PARTIAL；无原文不得假引用。

## 现状与上下文
- crates/archeaxis-application/src/research/**、crates/archeaxis-api/src/research/**、services/python-workers/research/** 尚为空/骨架（需确认）。
- 协议相关：packages/contracts/v1/errors.catalog.yaml、coverage-receipt.schema.json 已存在（coverage 收据语义）。
- Legacy 有研究模块（shared/research_store.py、research_migration.py、app/research/github.py）作为“行为来源/样例”，
  但 vNext 主库写者=Rust；不复制旧库写链。
- 决策：SUP-008（云端核查提前）、SUP-004（证据是使用约束而非准入门槛 → 个人定义/无证据笔记正常保存）。

## 范围与允许路径（任务包 T08）
crates/archeaxis-application/src/research/**、crates/archeaxis-api/src/research/**、
services/python-workers/research/**、tests/integration/research/**。

## 验收（任务包原文）
- 真实网页核查可重现，重复转载不算独立证据；
- 搜索失效/断网/预算耗尽给 PARTIAL；无原文不得假引用。

## 环境事实与阻塞
- **产品级云端/搜索凭据当前未配置（T00 记录）**：产品运行时真实搜索需要凭据——把“凭据注入点”
  做成配置/环境通道并写清接线文档；验证时允许：harness 级 web_search 已由集成者用于语义验证，
  以及可公开访问的抓取（尊重 robots/ToS、超时预算）做端到端样例；
  不得把“mock 成功”当作真实核查证据——可区分：契约单测（假来源=错误注入）与真实样例（真 URL）。
- 若 CODEX 环境具备可用云端凭据，可在其自身运行通道配置；不许把密钥写入仓库。

## 建议切片
1. 领域模型：核查任务/来源组/命题评估/PARTIAL 词汇（对齐 T02 冻结的状态词）+ 单测；
2. 抓取与去重（canonical URL/转载检测）+ 预算/超时/失败路径；
3. 逐命题云端评估 + 引用存在性与修订绑定校验（Core 侧）；
4. 端到端真实网页样例 + 成本/覆盖收据。

## 输出契约
- 每切片：变更原因、真实验证输出、剩余风险、回滚路径、SHA；收据落 docs/authority/taskpack-0905/T08/；
- 完成后报告：commit SHA、真实样例清单（URL 与结果）、验收对照表。
