# Phase 3 TaskPack：Vector Candidate Rebuild Boundary

> 状态：completed checkpoint
> 范围：现有 `VectorDB` 的 inactive shadow candidate 构建、输入校验和显式 discard
> 不包含：active switch、rollback、FTS rebuild、数据库 schema migration 或 canonical source 接入

## 本轮完成

- 新增 `VectorDB.build_candidate(records)`，在 active index 之外生成唯一 candidate 表；
- 在创建 candidate 表前拒绝空 ID、重复 ID、错误向量维度和非法 record 结构；
- candidate 构建后校验记录数与 object ID 集合；
- 构建或校验失败时自动清理 candidate 表；
- `VectorIndexCandidate.discard()` 只删除 candidate，不触碰 active index；
- 测试证明 active index 在 candidate 构建期间保持不变。

## 后续边界

candidate 只是迁移的中间态，不代表已切换或已完成 rollback。后续独立切片必须先定义 canonical rows/FTS 对应合同，再实现 verify → switch → rollback，并保持 active index 在失败路径可恢复。
