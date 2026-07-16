# Phase 3 TaskPack：Vector Candidate Switch and Rollback Boundary

> 状态：completed checkpoint
> 范围：现有 `VectorDB` candidate 的显式 active 内容切换、迁移备份与离线 rollback
> 不包含：FTS rebuild、canonical source 接入、数据库 schema migration、在线 operator CLI 或自动切换

## 本轮完成

- 新增 `VectorIndexCandidate.activate()`；激活前强制重新验证 candidate 的 cardinality 与 object ID 集合。
- 激活前把 active index 的完整 `(object_id, embedding)` 记录复制到唯一 rollback 表；只在备份成功后替换 active 内容。
- active replacement 使用单连接事务，失败时尽力恢复原 active 内容并清理本轮 rollback 表。
- 新增 `VectorIndexRollback.rollback()`；恢复旧记录后清理 candidate 与 rollback 表，重复 rollback 在 rollback source 缺失时 fail closed。
- 保持现有 active 表名和查询入口不变；未执行 FTS、schema 或破坏性 drop migration。

## 验证证据

- RED：未实现 `activate()` 时，2 个新增测试均按预期失败。
- GREEN：Vector 定向测试 `22 passed`。
- 全量 pytest：`378 passed, 1 warning`（使用项目 `.venv` 并清除 Hermes 注入的 `PYTHONPATH`）。
- Ruff changed-file check、architecture guard、repository convention check 均通过。
