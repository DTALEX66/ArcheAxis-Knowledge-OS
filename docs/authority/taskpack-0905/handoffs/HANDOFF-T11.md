# HANDOFF — T11 机器侧 HTTP/MCP 调用与反馈学习（CODEX）

交接人：DeepSeek（集成者）· 2026-09-05 · 难度：高 · 目标代理：CODEX

## 目标
- 同领域实现提供搜索/上下文/来源/提案/反馈；上下文带权限和预算；
- 本地模型与云端模型真实消费；案例/技能资产版本化，留出任务评测；
- 纠正候选审核后生效，导出训练候选但不伪称已微调；
- 真实 MCP 客户端完成读取和反馈；错误修订撤销后再调用不泄漏；未测能力显示 UNMEASURED。

## 上下文
- crates/archeaxis-api/src/mcp/**、application/src/machine/**、services/python-workers/machine-evaluation/**、
  tests/integration/machine/**（骨架为主）。
- 契约词汇：assessment-vocabulary.schema.json（含 UNMEASURED 语义）；T02 冻结的 MCP 映射。
- 预算/权限由 Core 授予（SUP-009 权限归 Rust）。

## 验收（任务包 T11）
- 真实 MCP 客户端完成读取和反馈；
- 错误修订撤销后再调用不泄漏；未测能力显示 UNMEASURED。

## 环境事实
- 本地模型 ollama qwen3:8b/qwen3-coder 可作真实消费方与供应方（HTTP）；
- MCP 需真实进程/stdio 或 streamable-http 客户端，不允许假客户端。

## 切片建议
1. 机器上下文 API（搜索/来源/预算/权限）契约单测；2. MCP 服务端+真实客户端往返；
3. 技能/案例版本化与留出评测；4. 纠正候选审核→生效→撤销不泄漏；5. 未测能力 UNMEASURED 输出。

## 输出契约
切片证据+收据 docs/authority/taskpack-0905/T11/；报告 commit SHA 与验收对照。
