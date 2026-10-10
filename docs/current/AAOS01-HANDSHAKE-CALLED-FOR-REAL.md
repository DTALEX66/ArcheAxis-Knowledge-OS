# AAOS-01 ✅ **握手真实调用成功（第一次）**，并限定第 24 轮的强断言

第 26 轮，26 轮里第一次**真的调用到了** `/api/v1/system/handshake`。

## 1. 正当驱动方式（**不是绕过，也不是伪造授权**）

```
python -m app.runtime_entrypoint migrate
  -> exit 0
  -> owner: "workspace.sqlite", target: "workspace_delivery_receipts_v1", version 2, state: applied
  -> 先产出备份 pre_migration_20261004T104835_129878Z_ad115255.sqlite
```

依据（源码）：`app/runtime_entrypoint.py:204-207` ——

```python
for owner in operator.registry.owners:        # owner 来自注册表
    if not owner.kind.startswith("sqlite"): continue
    results.append(operator.apply(owner.owner))
```

**它用注册表登记的 owner 逐个应用迁移** —— 这正是 `MigrationOperator` 要求的正当驱动方式，**我没有给 `--owner` 编一个名义**。

（上一轮我按签名直接调 `research.migrate(...)` 被拒，是因为**绕过了注册表**；这一轮走的是**正式入口**。）

## 2. 真实回执（原文）

```
database after migrate: True 999424 bytes

GET /api/v1/system/handshake -> 200
    product_id      = 'archeaxis-workspace'
    product_name    = 'ArcheAxis Knowledge'
    api_contract    = '1.x'
    backend_version = '0.6.14'
    source_commit   = '9cf99a26'
    schema_version  = 1
    runtime_mode    = 'installed-stable'
    workspace_id    = 'e29894f04c05a298'
    capabilities    = []
    migration_state = 'ready'
```

## 3. 逐项对照前端判据（`frontend/src/api/client.ts`）

| 前端要求 | 实测值 | 通过 |
| --- | --- | --- |
| `product_id === "archeaxis-workspace"` | `'archeaxis-workspace'` | ✅ |
| `product_name` 非空 | `'ArcheAxis Knowledge'` | ✅ |
| `api_contract === "1.x"` | `'1.x'` | ✅ |
| `backend_version` 非空 | `'0.6.14'` | ✅ |
| `source_commit` 非空 | **`'9cf99a26'`（真实 HEAD）** | ✅ |
| `schema_version` 整数 ≥1 | `1` | ✅ |
| `runtime_mode` 非空 | `'installed-stable'` | ✅ |
| `workspace_id` 非空 | `'e29894f04c05a298'` | ✅ |
| `capabilities` 字符串数组 | `[]` | ✅（空数组合法） |
| `migration_state === "ready"` | `'ready'` | ✅ |

**十项全过。** 也就是说：**前端的握手判据是可以被满足的** —— 它现在是**对着 Python BFF** 满足的。

## 4. **限定第 24 轮的强断言**（重要更正）

第 24 轮我写：「**两栈在同一库上无法共存**」。本轮实测表明**这句话说得太重**：

| 条件 | 结果 |
| --- | --- |
| **Core 正持库打开（WAL 旁文件在场）** | ❌ Python 只读都被拒（第 24 轮实测） |
| **Core 不持库 + 已跑受管辖的迁移** | ✅ **Python 完全能工作，握手 200** |

**准确表述**：不是永久不兼容，而是**「同一时刻只能有一个栈持有那个库」**。这是**同步/租约问题**，不是数据模型不可调和。

**这反而让 canonical 裁决更好做**：若引入明确的**租约/交接**机制，共存是可能的。

## 5. 仍然值得注意的两点

1. **`capabilities = []`** —— 握手报告**零能力**。前端拿到的是一份空能力目录。**这说明能力目录还没接上**（属 Q09 范畴），**我没有深究**；
2. `schema_version = 1` 而 Core 建了 26 张表且 `user_version` 为 0 —— **仍然未查明**口径。

## 6. 本轮**未**做

1. **没有改任何实现文件**；
2. **没有测**「Core 与 app 真的同时运行」时的租约/交接行为（只测了两者**先后**）；
3. **未**把这件事变成自动化测试（它现在是一次成功的手工观察，**尚未固化为门禁**——按我自己的纪律，手工证据应尽快门禁化）；
4. 官方 Green 与官方资料库**零触碰**；原库**零改动**。

## 7. 下一轮

**把这次手工观察固化成可重复的验证**：一个探针（对着临时库，走 `runtime_entrypoint migrate` + 起 app + 调握手），断言十项判据，**并入测试**。
这样它就**不会因为环境漂移而悄悄失效**。
