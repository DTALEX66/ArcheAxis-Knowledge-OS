# AAOS-01 **第一次真正执行产品能力**：legacy 迁移在授权副本上跑通

23 轮里我几乎全在做静态阅读。本轮执行了一次真实能力，并拿到真实回执。

## 1. 探针先**拒绝**，这是它该做的

第一次运行（未设 `ARCHEAXIS_LEGACY_COPY`）：

```
PROBE_EXIT=2
{"ok": false, "blocked": "set ARCHEAXIS_LEGACY_COPY to an authorised legacy database", "path": "None"}
```

**并且原库哈希在运行前后完全一致**（`b318c99e…`）—— **它没有碰原库**，符合其文档承诺。

## 2. 对着授权副本运行的结果（`PROBE_EXIT=0`）

```
copy created: 3223552 bytes
copy hash matches original: True

"hash_matches": true, "rollback_eligible": true,
"restore_candidate": ".project-local/mig/d41a5592/backups/cognitive_os.pre-20261004-102013-a7737a99.sqlite",
"restore_note": "restore by copying the backup file over the legacy path;
                 current workspace state is never overwritten",

"ledger": { "path": ".../workspace/evidence_ledger/ledger.sqlite",
            "tables": 65, "rows": 50 },

"original_untouched": true
receipt: .project-local/mig/d41a5592/legacy-migration-receipt.json
原库哈希运行后仍为 b318c99e…  （未变）
```

## 3. 这次执行**证明了什么**

| 断言 | 证据 |
| --- | --- |
| legacy 迁移路径在本机**可真实跑通** | `PROBE_EXIT=0`，产出 65 表 / 50 行的 `ledger.sqlite` |
| 迁移**可回滚** | `rollback_eligible: true` + 具体 `restore_candidate` 备份文件 |
| 迁移**幂等** | 探针自身断言（其文档第 5 条） |
| **原库未被改动** | 运行前后 sha256 一致 + `original_untouched: true` |

**这是本任务包的第一次「执行而非阅读」，也第一次有了可引用的回执 JSON。**

## 4. 但它**不等于**「应用能启动了」——必须说清

迁移产出的是 **workspace 布局**（`workspace/evidence_ledger/ledger.sqlite`），**不是** `data/archeaxis.sqlite`。而 app 的 `validate_schema` 查的是后者。

**所以「实际调用握手」的前置仍未满足**：需要一个由 **Rust Core** 建立 schema 的 `archeaxis.sqlite`。

## 5. 下一轮

用**已构建的 core 二进制**（`.project-local/build/2611ed9ca1/cargo/debug/archeaxis-api.exe`，10/03 构建）对**临时目录**启动一次，让它建立 schema，然后把 app 指向那个临时库，**真正调用握手**。

**注意（不掩饰的风险）**：那是**旧构建**（10/03），不一定与 HEAD 的 schema 一致；若用它，需说明这一点，或先重新构建。**我不会拿一个过期二进制的结果去声称当前 HEAD 的行为。**

## 6. 本轮**未**做

1. **未重新构建** Rust Core；
2. **未调用握手**（前置仍未满足）；
3. 官方 Green 与官方资料库**零触碰**；原库**零改动**（已用哈希证明）。
