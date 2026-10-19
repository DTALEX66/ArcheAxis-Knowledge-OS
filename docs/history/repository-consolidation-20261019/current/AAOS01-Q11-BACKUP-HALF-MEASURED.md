# AAOS-01 Q11（**备份半边**）：备份可用，且带可校验清单

**本轮只测了「备份」这一半。「独立恢复」那一半未测，见 §5。**

## 1. 用**受认可的驱动器**，不手写 SQL

```
python -m app.runtime_entrypoint migrate
python -m app.runtime_entrypoint backup
python -m app.runtime_entrypoint integrity
```

三者 exit 均为 0。

## 2. 迁移**自动**留下迁移前快照（带哈希）

一次 `migrate` 产生了 **6 个** `pre_migration_*.sqlite`（各带 `.manifest.json`），
且迁移输出里含 `backup_path` 与 **`backup_sha256`**：

```json
"provenance": {"applied_migrations": ["core_sqlite_baseline_v1"],
               "backup_path": ".../pre_migration_20261004T140631_845612Z_1c4b1217.sqlite",
               "backup_sha256": "cbd37c40f86036e180bce6b1eeb14ce1e1b406eb42514bd..."}
```

**即：迁移前自动快照 + 记录哈希** —— 这正是「一致快照」值得记的一点。

## 3. `backup` 产出的清单内容（实测）

```json
"backup":   {"path": ".../backups/cognitive_os_20261004T140632_116178Z.sqlite",
             "sha256": "a2ebcea2880f127ea3da04cf8542f79a56d90fc8f4aa51126d9ce2e7d969b9b3",
             "size_bytes": 999424}
"created_at_utc": "2026-10-04T14:06:32.129167+00:00"
"kind": "cognitive-os-sqlite-backup"
"manifest_version": 1
"domain_invariants": {"required_tables": [core_objects, ir_daily_briefs, ir_research_notes,
                      kb_cards, kb_documents, kb_taskpacks, schema_migrations],
                      "row_counts": {...6 张表各自的行数...}}
"migration_status": {"applied": 2, "pending": [], "total": 2, "applied_list": [...]}
"schema_migrations": [ {version, name, applied_at} ... ]
```

**清单记了哈希、字节数、时间、kind、manifest 版本、域不变量（必需表 + 行数）与迁移状态。**
**这是一份可核对的清单，不是一句「已备份」。**

## 4. 三处值得记下的观察

1. **遗留命名仍在**：库文件叫 `archeaxis.sqlite`，但备份名是 **`cognitive_os_*.sqlite`**、
   `kind` 是 **`cognitive-os-sqlite-backup`** —— 与第 16 轮「Python 面仍带 cognitive_os 命名」一致。
2. **两套计数不是一回事**：`migration_status.applied: 2`（列表是 `002_*`、`003_*`），
   而 `schema_migrations` 列出的是 **version 2…15+**。**我按字面记录，不替它们统一含义。**
3. **同一次运行还留下** `.archeaxis.sqlite.runtime.lock`、`.cognitive-volume-id`、
   `migration_operator_locks.lockdb` —— 说明**运行会持有锁与卷标识**。

## 5. **未**测到的（必须说清）

| 项 | 状态 |
| --- | --- |
| `integrity` 的**输出文本** | ❌ **本轮未捕获到**（我的命令输出被截断）—— 只有 exit=0 |
| **独立恢复**（`restore-candidate` / `restore-activate`） | ❌ **完全未测** —— 这是 Q11 的另一半 |
| 恢复后**读回同一份数据** | ❌ 未测 |

**所以本轮不能声称 Q11 通过。** 只能说：**备份侧成立，且清单可核对。**

## 6. 本轮未做

1. **未**改任何实现文件；
2. **未**触碰官方 Green 与资料库；
3. 探针临时库**保留**（下一轮继续用它做恢复试验），**位于 `.project-local`，属项目自有临时区**。

## 7. 下一轮

用同一份临时库做**独立恢复**：把备份恢复到一个**独立位置**，然后**读回**并在冷启动后再读一次 ——
取到「一致快照 + 独立恢复」的**完整**证据，再谈 Q11 是否通过。
