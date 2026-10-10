historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

> 归档（2026-10-08 文档收敛，批次 d-docs-20261008）：本文件自 `docs/current/` 原样移入 `docs/history/aaos01-20261005/`，正文、日期与原始证据未改写；该主题的当前入口是 `docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`。

# 🎉 AAOS-01 Q02：**迁移跑通了 —— `MIGRATE_EXIT=0`**

## 1. 我做了什么

我按启动器的方式**自己执行了那条命令**（因为界面会截断日志）：

```bat
"%PY%" -B -I -m app.runtime_entrypoint migrate > out.txt 2>&1
rem cwd = 临时目录；env 复现 backend.rs:299-312
rem   ARCHEAXIS_DATA_DIR / ARCHEAXIS_DB_PATH=data/archeaxis.sqlite
rem   ARCHEAXIS_CAPABILITY_ROOT / ARCHEAXIS_RUNTIME_PROFILE=installed-stable
rem   PYTHONDONTWRITEBYTECODE=1 / PYTHONNOUSERSITE=1 / NO_PROXY=127.0.0.1
```

## 2. 🎉 结果：**成功**

```
MIGRATE_EXIT=0
```

```json
{"database": "...\migration-manual\archeaxis.sqlite",
 "operator_results": [
   {"kind": "sqlite_core", "operation": "apply", "owner": "core.sqlite", "state": "applied",
    "applied_migrations": ["core_sqlite_baseline_v1"],
    "backup_sha256": "cbd37c40f86036e1…",
    "schema_contract_objects": 69, "target": "core_schema_v1", "version": 1},
   {"kind": "sqlite_knowledge", "state": "applied",
    "applied_migrations": ["phase5_knowledge_candidate_governance_v1", … 共 10 个]},
   {"kind": "sqlite_research", "state": "applied", "applied_migrations": ["phase4_research_package_v1"]},
   {"kind": "sqlite_sleep", "state": "applied", "version": 2},
   …]}
```

**多 owner 迁移全部 `applied`**：core（**69 个 schema 契约对象**）· 10 个 knowledge 迁移 ·
research v1 · sleep v2 —— **每个都带前置备份与 sha256**。

## 3. 这说明什么

| 结论 | 依据 |
| --- | --- |
| **迁移本身没有固有故障** | 同一命令、同一 runtime，**退出码 0** |
| **第 97-98 轮的依赖修复是有效的** | 迁移真的执行到了所有 owner |
| **应用的 `exit code: 1` 是那次调用的环境差异** | 我这边成功，它那边失败 |

## 4. 一个具体的差异假设（待验证）

启动器设的是：

```rust
294:  command.current_dir(&runtime.cwd);              // cwd = 数据目录
303:      .env("ARCHEAXIS_DB_PATH", "data/archeaxis.sqlite")   // 【相对路径】
```

**`data/archeaxis.sqlite` 是相对路径** → 它相对 `cwd` 解析 → **要求 `<数据目录>/data/` 存在**。
而我的手动运行里，数据库落在 `<RUN>\archeaxis.sqlite`（因为我也设了 `ARCHEAXIS_DATA_DIR`）。

**所以假设是**：**启动器的那个 cwd 下没有 `data/` 子目录**，导致它那条路径解析不同。

**这是假设，未验证。** 下一轮可以只读地检查那个数据目录有没有 `data/`。

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「Q02 通过」 | 交付物是**完整**生命周期 —— 迁移只是其中一步，**还有 `core` 与 readiness** |
| 「应用一定失败在 `data/` 上」 | **未验证** —— 上面的差异只是最可能的假设 |

**但「迁移能跑通」这一条，现在已经确证。**

## 6. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 在临时目录跑了一次迁移 | `.project-local/runs/migration-manual/` | **项目自有开发输出**，生成的是临时数据库与备份 |

**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；**未删除仓库内任何东西**。
