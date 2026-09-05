# HANDOFF — T02 契约冻结评审范围（CODEX 评审用）

交接人：DeepSeek（集成者）· 2026-09-05 · 难度：中高 · 目标代理：CODEX（评审角色）

## 背景
T02 “冻结最小跨语言协议”由 DeepSeek 线主笔（初稿），CODEX 负责**评审高风险语义区**后集成者定稿。
范围（任务包 T02 允许路径）：packages/contracts/**、crates/archeaxis-contracts/**、
crates/archeaxis-sidecar-protocol/**、tests/contract/**。

## 请评审的高风险语义（对初稿逐项给结论）
1. 状态词汇：任务/作业/核查/学习/机器反馈状态枚举是否跨 C#/Rust/Python 一致且可版本化拒绝；
2. 幂等与 idempotency-key 语义（长度/作用域/过期）是否覆盖重复回写场景；
3. 结构块/字符/页/时间锚点坐标的 JSON 表示与校验（错误坐标拒绝）；
4. 错误目录 errors.catalog.yaml 与 HTTP/NDJSON/MCP 三通道映射；
5. 生成代码单一来源与漂移检查设计。

## 输入
- 初稿由 DeepSeek 交付于 packages/contracts/v1/** 与 crates/archeaxis-contracts 测试（T02 完成后 SHA 附于此文档更新处）；
- 既有文件：worker-protocol.schema.json、coverage-receipt.schema.json、assessment-vocabulary.schema.json、
  openapi-outline.yaml、errors.catalog.yaml、compatibility-policy.md。

## 输出契约
- 评审结论：每项 PASS/需修改+具体改法；不替代实现，只冻结语义；
- 结论落 docs/authority/taskpack-0905/T02/REVIEW-CODEX.md（或直接对初稿 PR comment）。
