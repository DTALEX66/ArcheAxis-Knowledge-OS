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
