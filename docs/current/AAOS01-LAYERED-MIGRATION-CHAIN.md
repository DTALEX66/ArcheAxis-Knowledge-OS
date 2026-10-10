# AAOS-01 **一个可用库需要两栈的迁移，而 Python 那道由 MigrationOperator 把关**

本轮把「让 app 起来」这件事追到了底，得到一条**分层的依赖链**，每一层都是实测。

## 1. 依赖链（逐层实测）

| 层 | 要求 | 状态 | 证据 |
| --- | --- | --- | --- |
| 1 | **Rust Core 建立 schema** | ✅ **已达成** | Core 建的库有 **26 张表** |
| 2 | **WAL 旁文件必须被 checkpoint 掉** | ✅ **已达成** | `PRAGMA wal_checkpoint(TRUNCATE)` 后 `-wal`/`-shm` **消失**，该报错**不再出现** |
| 3 | **phase4 research schema 迁移必须已应用** | ❌ **当前阻挡** | `RuntimeError: phase4 research schema migration is pending`（`shared/research_migration.py:195`） |

## 2. 第 3 层**不是随便能调的** —— 它自己把关

我按签名调用了它：

```
research.migrate(db_path=DB, backup_dir=...)
  -> RuntimeError: research schema migration must be driven by MigrationOperator
```

**它拒绝被直接驱动，要求由 `MigrationOperator` 执行。**

**这是好事，而且我不绕它** —— 包内明文"**不伪造许可**"，而这道守卫正是「该操作需要正当驱动者」的表达。

（过程记录：我先按 `migrate(DB)` 调，报 `takes 0 positional arguments`；再按无参调，报缺 `db_path`/`backup_dir` 关键字；补上后得到上面这条**语义性拒绝** —— 前两次是我签名读错，**第三次才是真正的约束**。）

## 3. 本轮**最重要的结论**

> **canonical 库不是任何单一栈的产物：Rust 建自己的 schema，Python 还要再应用一道 phase4 研究迁移，而后者受 `MigrationOperator` 管辖。**

这把第 18/24 轮的结论又推进了一步：

| 轮次 | 结论 | 依据 |
| --- | --- | --- |
| 18 | 两套并行数据模型共用一个文件 | 读源码 |
| 24 | **Core 持 WAL 时 Python 连只读都做不了** | 实测硬失败 |
| **25** | **即便解决 WAL，还差 Python 侧一道受 Operator 管辖的迁移** | 实测 + 明确错误 |

**所以「让 Tauri 前端改连 Rust Core」不是换一个 URL 的事** —— 它牵动**两套迁移制度**与**一个 Operator 权限边界**。

## 4. 其他实测到的细节（存档，免得以后重查）

- Core 退出后库里除 `-wal`/`-shm` 外还有 **`archeaxis.sqlite.writer.lock`**（checkpoint 后仍在）；
- `user_version` 在 Core 建完 26 张表后仍是 **0**（**未查明是否有意**）；
- `wal_checkpoint(TRUNCATE)` 返回 `(0, 0, 0)` 却已把旁文件清掉。

## 5. 本轮**未**做

1. **仍未调用到握手** —— 被第 3 层挡住，**如实记录**（这是第 25 轮，握手仍未成功，我不粉饰）；
2. **未找 `MigrationOperator`**（下一轮第一件事）；
3. **未改任何实现文件**；
4. 官方 Green 与官方资料库**零触碰**；原库**零改动**。

## 6. 下一轮

定位并用**正当方式**驱动 `MigrationOperator`（不是绕过它）：弄清它的构造、它需要什么授权/输入，
然后在**临时库**上跑完第 3 层，**调用握手**。

**若它需要人工授权而现场没有，我就登记为阻塞并继续别的独立任务** —— 按包内「不因一个边界阻塞全部」。

## 7. 2026-10-06 补记：第 3 层的驱动者**已存在且有测试**，但「跑完并握手」仍未做

本节只补上自第 25 轮起缺失的定位结果，并明确区分**已核**与**未做**。

**已核（仓库内可复核）**

- `MigrationOperator` 在 `shared/migration_runner.py`，并已被四个入口使用：`app/cli.py:73-75`、`app/runtime_entrypoint.py:196-202`、`app/main.py:404-407`、`app/facades/research_runtime.py:40`（后者在库里以 `MigrationOperator(db_path=…, backup_dir=…).apply("core.sqlite")` 驱动）。即"下一轮第一件事"（定位它）已由后续工作完成，本文件此前未记录。
- `shared/research_migration.py:192-195` 的 `_require_applied_connection` 是**读侧守卫**：库的 phase4 research schema 未应用时拒绝读取并报 `phase4 research schema migration is pending`。它不是在说"没有人能应用"，而是在说"应用必须走正当驱动者"——即本文件 §2 的那条约束。
- 该驱动者的提交测试本轮实跑：`cargo_test.bat test -p archeaxis-migration --tests --offline` → **24 passed / 0 failed**，含 `non_empty_legacy_library_stages_notes_and_learning_history_without_touching_the_source`、`legacy_db_never_modified`、`staging_never_modifies_the_legacy_database_bytes`、`inventory_readonly`、`manifest_table_removal_is_rejected_before_any_write`、`tampered_jsonl_is_rejected_before_any_write`、`export_refuses_to_overwrite_existing_snapshot`；`tests/test_migration_runner.py` + `test_migrate_rowidless_tables.py` + `test_axw_data403_migrate.py` → **51 passed / 0 failed**（operator 侧 36 个用例，覆盖 apply/rollback 来源证明、owner 租约、schema 漂移时 fail-closed、并发单一 owner）。日志 `.project-local/task-runtime/q11-migration-rust-20261006.log`、`q11-migration-python-20261006.log`。

**未做（本轮的明确边界）**

- **没有**把 operator 真正跑在一个 phase4 待迁移库上以走完第 3 层并调用握手：本轮只验证了"驱动者存在、已接线、测试通过"，没有执行一次端到端迁移。因此第 3 层在"能力是否具备"上已有依据，在"本机是否已跑通"上**仍是未做**——两者不得互相代替。
- 原库、官方 Green、官方资料库**零触碰**；未改任何实现文件。
