# AAOS-01 Q11 收口：**备份与恢复已固化成门禁，并如实记下一处「不是字节复制」**

## 1. 新探针 + 测试

`scripts/probes/backup_restore_probe.py` + `tests/test_backup_restore_probe.py`

**它不需要 core 二进制**，所以与第 50 轮那个机器会话探针不同 —— **这条能在 CI 里真跑**。

## 2. 实测结果（全部确定性）

| 检查 | 结果 |
| --- | --- |
| **清单里的 `sha256` == 备份文件本身的哈希** | ✅ **True** |
| 清单 `size_bytes` == 实际字节数 | ✅ 999424 |
| 清单 `kind` / `manifest_version` | `cognitive-os-sqlite-backup` / `1` |
| 目标库**恢复前已存在** | ✅ True |
| 恢复后 | ✅ **97 表**，`integrity_check: ok`，999424 字节 |
| **跨冷启动一致** | ✅ True |
| 清单 `required_tables` | `core_objects, ir_daily_briefs, ir_research_notes, kb_cards, kb_documents, kb_taskpacks, schema_migrations` |

## 3. 一处我**必须如实写下**的否定结果

```
restore_is_byte_identical_to_backup = False
```

**恢复后的库与备份文件不是字节相同的。**

**所以正确的说法是：这是一次逻辑恢复，不是字节复制。** 我**没有**声称字节一致。
测试里也**只断言「这个布尔值被记录下来了」**，而**不要求**它是 True 或 False ——
**将来若真变成字节复制，测试仍通过，而回执会显示出来。**

**该被禁止的不是「不是字节复制」，而是「这件事没人观察」。**

## 4. Q11 最终状态

| 侧 | 状态 |
| --- | --- |
| 备份 | ✅ 自动迁移前快照 + `backup_sha256`；清单**哈希可自证** |
| 恢复 | ✅ 独立目标先建后恢复；**逻辑一致、跨冷启动稳定**（**非字节复制**） |
| 守卫 | ✅ 候选绑定目标库，激活到别处被拒 |
| 门禁 | ✅ **8 项测试，2.17 秒，无需 core 二进制** |

## 5. 仍未解决（保留）

恢复后的 `schema_migrations` 是 **17 行**，而备份清单 `migration_status.applied` 是 **2**。
**两个数字口径不同，我仍未查明** —— 与第 52/54 轮同一个未决点。

## 6. 本轮未做

1. **未**改任何实现文件；
2. **未**触碰官方 Green 与资料库；
3. 探针**自清理**其临时目录。
