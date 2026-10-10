# AAOS-01 **实测到的跨栈硬约束**：Core 的 WAL 旁文件让 Python 只读访问**直接拒绝**

> **状态（2026-10-06 更新）：已解除，本文结论不再成立。**
> 下文把"Core 留下 WAL 旁文件"读成了"两栈不能在同一个库上工作"。实测表明障碍是**活着的写者**，
> 不是旁文件本身：`shared/backup.py::prepare_runtime_database`（应用每次启动、取得唯一运行时租约后执行）
> 会以读写方式打开库（自动恢复残留 WAL）、执行 `wal_checkpoint(TRUNCATE)`、用 `BEGIN EXCLUSIVE`
> 证明没有别的写者、并删除旁文件；随后 `validate_schema` 正常通过。
> 复现（真实被杀死的写者，非模拟）：被杀后 `-wal` 12,392 B、`-shm` 32,768 B → `prepare_runtime_database()`
> 之后**两者全部消失** → `validate_schema` 越过旁文件检查、只因玩具库缺真实 schema 而报出下一层错误。
> 证据与用例：`tests/workflow/test_offline_database_recovery.py`（2 项）与本轮台账。
> 仍然为真的是：**Core 正在运行时** Python 侧会被 `BEGIN EXCLUSIVE` 正确拒绝——那是单写者纪律，不是无法共存。
> 下文保留为当时的实测记录，不删改。

## 1. 这一轮真的把两栈放在一起跑了

1. 重新构建 Rust Core（**显式 target dir**，`EXE 97883043 bytes 10/04 18:27:19`）—— **对 HEAD 是最新的**，先前那个「旧构建」的顾虑**不再存在**；
2. 用临时目录启动 Core：**它建立了数据库**；
3. 把 Python app 指向**同一个临时库**。

## 2. 观察到的（原始输出）

```
core readiness port: 56396
database created by the core: True 4096 bytes
user_version the core set: 0 | tables: 26
```

然后 app **拒绝启动**，原因具体：

```
RuntimeError: read-only research access requires a checkpointed database without
  SQLite sidecars: archeaxis.sqlite-wal, archeaxis.sqlite-shm
  shared/research_migration.py:166  _connect_readonly
  shared/storage.py:432            validate_schema
  app/main.py:39                   core_runtime_lifespan
```

## 3. 这**证明了什么**（而且是实测，不是推断）

| # | 发现 | 证据 |
| --- | --- | --- |
| 1 | **Rust Core 确实建立 schema** | 它创建的库里 **26 张表** |
| 2 | **Core 用 WAL 模式** | 留下 `-wal` / `-shm` 旁文件 |
| 3 | **Python 只读路径拒绝带旁文件的库** | `research_migration._connect_readonly` 抛错，且**错误信息点名了两个旁文件** |
| 4 | **两栈在同一库上无法共存** | 上述 1+2+3 直接合成 |

## 4. 为什么这是**关键**发现

第 18 轮我说「两套并行数据模型共用一个文件」，那是**从源码读出来的**。
**本轮把它变成了一个可复现的硬失败**：

> **只要 Core 以 WAL 打开那个库，Python 侧连只读都做不了。**

也就是说，**这不是策略问题（谁该写），而是当前实现下「两个栈根本不能同时对同一个库工作」**。

**这正是「该迁移的迁移」必须做的技术理由**，而且它比第 18 轮的表述更强、更具体。

**对 canonical 裁决的意义**：

- 「让两者共存」这个选项**在当前实现下不存在**；
- 要么让 Core 成为唯一访问者（Python 侧改为经 Core HTTP），要么统一日志/只读模式；
- **后者需要实测验证**（例如 Core 关闭时是否会自动 checkpoint、旁文件是否消失）——**我没有测**。

## 5. 本轮**未**做（边界）

1. **仍未成功调用握手** —— 被上述跨栈约束挡住，**如实记录**；
2. **未测**「Core 正常退出后旁文件是否消失」/「`user_version=0` 是否正常」（Core 设了 26 张表却把 `user_version` 留成 0，**我没有核这是有意还是缺口**）；
3. **未改任何实现文件**；
4. 官方 Green 与官方资料库**零触碰**；原库**零改动**。

## 6. 下一轮

**把上一段第 2 条测掉**：Core 正常退出（而非被 kill）后，`-wal`/`-shm` 是否被 checkpoint 掉；若是，Python 能否启动并**成功调用握手**。
这是同一实验的一个变量，**代价很小，收益是第一次真正拿到握手回执**。
