# Phase 3 TaskPack：FTS5 Candidate Rebuild Boundary

> 状态：completed checkpoint
> 范围：`kb_documents`/`kb_cards` 的 FTS5 inactive shadow candidate 构建与 fail-closed 验证
> 不包含：active switch、rollback、删除或重命名 active FTS 表、SQLite schema migration、自动切换

## 本轮完成

- 新增 `shared.storage.build_fts_candidate(source_table)`，只从 canonical KB rows 构建唯一 candidate FTS5 virtual table；
- 仅允许 `kb_documents` 与 `kb_cards` 作为受支持的 FTS source table，其他表 fail closed；
- candidate 创建后验证完整 object ID 集合与 cardinality；验证失败自动清理 candidate；
- 新增 `FtsIndexCandidate.verify()` 与 `discard()`；验证只读 candidate，discard 只删除 candidate；
- 测试证明 candidate 构建、篡改后验证失败期间 active FTS 搜索结果保持可用。

## 本轮边界

本轮只建立 FTS5 candidate 与验证合同，不执行 active switch、rollback、FTS schema migration 或运行时自动 rebuild。后续切片必须独立设计双索引切换失败语义与 rollback 证明。
