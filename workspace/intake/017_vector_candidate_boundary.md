# Phase 3 TaskPack：Vector Candidate Rebuild Boundary

> 状态：completed checkpoint
> 范围：现有 `VectorDB` 的 inactive shadow candidate 构建、输入校验和显式 discard
> 不包含：active switch、rollback、FTS rebuild、数据库 schema migration 或 canonical source 接入

## 本轮完成

- 新增 `VectorDB.build_candidate(records)`，在 active index 之外生成唯一 candidate 表；
- 在创建 candidate 表前拒绝空 ID、重复 ID、错误向量维度和非法 record 结构；
- candidate 构建后校验记录数与 object ID 集合；
- 增加 `VectorIndexCandidate.verify()`：切换前可重复验证 candidate 的记录数和 object ID 集合，异常或不一致时 fail closed；验证只读 candidate，不触碰 active index；
- 构建阶段校验失败时自动清理 candidate 表；
- `VectorIndexCandidate.discard()` 只删除 candidate，不触碰 active index；
- 测试证明 active index 在 candidate 构建和 candidate 验证失败期间保持不变。

## 本轮边界

`verify()` 只建立 candidate 完整性前置条件，不执行 active switch、rollback、FTS rebuild 或数据库 schema migration。
