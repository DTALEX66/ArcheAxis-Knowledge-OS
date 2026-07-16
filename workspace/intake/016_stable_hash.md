# Phase 3 TaskPack：Stable Persistent Hash

> 状态：completed
> 范围：稳定哈希 Facade 与现有 VectorDB 持久化 hash 调用迁移
> 不包含：FTS/Vector shadow rebuild、数据库迁移、rollback runner

## 完成内容

- 新增 `shared.stable_hash`，算法版本为 `sha256-v1`；
- 支持 namespaced bytes/text hash，拒绝空 namespace；
- `VectorDB` rowid 映射改用 `vector-rowid` namespace；
- `SimpleTextEmbedder` n-gram bucket 改用 `embedding-ngram` namespace；
- 清除运行时代码中的 Python `hash()` 持久化调用；
- 新增跨调用稳定性与算法版本合同测试。

## 后续边界

正式 FTS/Vector shadow rebuild、算法切换、索引验证和 rollback 仍由独立 Migration TaskPack 处理。
