# HANDOFF — T09 知识版本、复核、检索与调用政策（CODEX）

交接人：DeepSeek（集成者）· 日期：2026-09-05 · 难度：高 · 目标代理：CODEX

## 目标
权威知识领域（Rust）：
- 不可变修订/复核事件；个人定义和候选区别；版本冲突与状态机；
- 源文和知识双索引、中文检索、锚点回链、撤销与失效传播；
- 查询模式/权限/时效过滤，事实与假设的用途保持显式；
- 来源可点回，旧修订不冒充当前；机器不能赋 USER_ACCEPTED；无证据个人笔记可正常保存。

## 现状与上下文
- crates/archeaxis-domain/src/knowledge.rs、anchor.rs、search.rs；crates/archeaxis-application/src/knowledge/**；
  crates/archeaxis-api/src/knowledge/** —— v01 journey 已覆盖 anchor roundtrip、personal/candidate、review
  immutable、fts5（receipt PASS 记录于 reports/vnext/v01-closed-loop-receipt.json）。
- 既有契约词汇：assessment-vocabulary.schema.json；learning/knowledge DTO 见 packages/contracts/v1（T02 冻结后为准）。
- Legacy 行为来源：shared/research_store.py 的 evidence 语义；个人笔记=personal（SUP-004）。
- 决策 SUP-004/008；任务包 T09 验收明确机器无 USER_ACCEPTED 权限。

## 范围与允许路径（任务包 T09）
crates/archeaxis-domain/src/knowledge.rs、anchor.rs、search.rs、
crates/archeaxis-application/src/knowledge/**、crates/archeaxis-api/src/knowledge/**。

## 验收（任务包原文）
- 来源可点回，旧修订不冒充当前；
- 机器不能赋 USER_ACCEPTED；无证据个人笔记可正常保存。

## 环境事实
- cargo 1.97.1 + vcvars（见总摘要）；cargo test --workspace 必须绿；
- FTS5 已在 store 中启用；中文检索用 tokenizer 验证（如 simple/unicode61 局限需记录并给替代）；
- 修订/复核事件的迁移表由 T03 迁移序列提供（先确认其合入状态）。

## 建议切片
1. 状态机与权限（候选/复核/USER_ACCEPTED 边界/机器角色）+ 冲突测试；
2. 不可变修订链 + 撤销/失效传播（旧修订不冒充当前）；
3. 双索引与中文检索、锚点回链；权限/时效过滤；
4. 个人笔记无证据保存旅程 + 与核查候选分层。

## 输出契约
- 切片证据 + 收据 docs/authority/taskpack-0905/T09/；报告 commit SHA 与验收对照表。
