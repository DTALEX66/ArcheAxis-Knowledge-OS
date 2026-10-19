# AXR-060-302：四账本 SQL 白名单与迁移/回滚矩阵

## 范围与边界

本矩阵仅覆盖 `app.federation.service` 所拥有、由调用方明确传入路径的联邦 SQLite 库；它不是
`shared.knowledge_governance_migration` 所拥有的全局治理库，不能错误地注册到后者的 migration
operator。受控表恰为：

| 记录类型 | 表 |
| --- | --- |
| Evidence | `federation_evidence_records_v1` |
| Learning | `federation_learning_records_v1` |
| Provenance | `federation_provenance_records_v1` |
| Rights | `federation_rights_records_v1` |

服务只从静态表/列映射派生以下 SQL：建表、带明确列名的 `INSERT INTO`、带上限的 `SELECT`，以及四表的
`UPDATE`/`DELETE` 拒绝触发器。`_append_record` 对任何不在白名单内的表 fail closed；没有
`INSERT OR REPLACE`、`UPDATE` 或 `DELETE` 写入路径。

## 迁移与回滚矩阵

| 起始状态 | 受控前向步骤 | 成功后的读回 | 失败处理 / 回滚 | 已有记录后的降级 |
| --- | --- | --- | --- | --- |
| 无联邦账本表 | 原子创建四表与八个拒绝触发器 | 新记录可重启读取；四表拒绝直接更新/删除 | 同一 SQLite 事务回滚，不能留下部分表或触发器 | 不适用 |
| 旧 Provenance 表（无 `reason`） | 原子补 `reason`，再安装全部触发器 | 旧行保留；新 `revoked` / `superseded` 行保留 parent 与 reason，并可重启读取 | 任一步（包括触发器安装）失败即回滚；`reason` 不会残留 | 不自动反向 `ALTER TABLE`；只能在升级前的经验证数据库备份上执行用户授权恢复 |
| 已是当前表结构 | 仅幂等确认表、列与触发器 | 同一记录集合和约束可重启读取 | 无写入数据变更；异常仍回滚本事务 | 不适用 |
| 已采集任一账本记录 | 不存在“覆盖式修复”迁移 | 修正必须新增有原因的 Provenance 事件 | 事务失败不会提交部分 schema 变更 | 禁止自动降级或删除列/行；恢复必须使用升级前备份并经用户授权 |

“回滚”在这里有两个严格含义：未提交的 schema 前向步骤由事务自动回滚；已提交且可能已新增证据的
数据库不允许脚本化降级，因为那会破坏 append-only 历史。后者的恢复路径是升级前的、已验证的数据库备份，
不是删除新字段或记录。

## 验证证据（本地）

`tests/test_federation_records.py` 覆盖：

1. 四表完整的直接 `UPDATE` / `DELETE` 拒绝；
2. 全部四表的静态插入 SQL 白名单与未列名表 fail-closed；
3. 旧 Provenance 库的前向迁移与重启读回；
4. 在补列之后强制触发器安装失败，确认事务回滚且 `reason` 未残留。

已执行：

```text
pytest tests/test_federation_records.py \
       tests/test_knowledge_governance_migration.py \
       tests/test_knowledge_governance_schema_tamper.py -q
23 passed
```

上述是本地测试证据；合并后的 exact-SHA CI 仍需单独读取，不能由本文或本地测试替代。

## 安全界限

SQLite 触发器阻止常规产品连接的行级修改与删除；拥有数据库文件写权限的外部行为者仍可使用 SQLite DDL
移除触发器。因此该实现提供产品写入路径和常规 SQL 的 append-only 合同，而不是把本地 SQLite 声称为
对文件所有者的加密不可篡改存储。
