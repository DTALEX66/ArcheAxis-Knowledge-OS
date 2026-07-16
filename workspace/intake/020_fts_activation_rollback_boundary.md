# Phase 3 TaskPack：FTS Candidate Activation and Rollback Boundary

> 状态：completed checkpoint
> 范围：现有 `kb_documents`/`kb_cards` FTS5 candidate 的显式激活、canonical source drift 校验与 rollback copy
> 不包含：active FTS 表重命名、schema migration、自动切换、历史删除或通用 Migration Runner

## 本轮完成

- `FtsIndexCandidate.verify()` 从仅校验 ID/cardinality 扩展为校验完整索引 payload、canonical source payload 与 canonical rowid；
- 新增 `FtsIndexCandidate.activate()`，激活前重新验证，并在同一事务边界内将 active FTS 行复制到唯一 rollback FTS 表，再按原 rowid 写入 candidate；
- 新增 `FtsIndexRollback.rollback()`，恢复 active 行并清理 candidate/rollback 表；rollback source 缺失时 fail closed；
- `kb_cards` candidate 使用 canonical `tags_json` 投影为 FTS `tags`，避免 shadow rebuild 丢失字段；
- 测试覆盖 valid switch/rollback、source drift 拒绝、active FTS 未被错误修改和重复 rollback 拒绝。

## 验证证据

- RED：2 个新增激活测试在缺少 `activate()` 时按预期失败；
- GREEN：FTS 定向测试 `5 passed`；FTS+Vector 受影响测试 `27 passed`；Knowledge Base 套件 `38 passed`；
- 未执行 active 表 rename/drop migration；candidate 与 rollback 表均为本轮显式操作对象，失败路径清理，不触碰 canonical rows。
