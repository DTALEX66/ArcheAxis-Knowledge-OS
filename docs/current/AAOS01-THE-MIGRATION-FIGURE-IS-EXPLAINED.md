# 🎯 AAOS-01：**确切答案 —— 并更正我第 117 轮的「过度更正」**

## 1. 找到了确切的算法

```python
// app/workspace/service.py
1080:     try:
1081:         migration_states = dict(
1082:             Counter(
1083:                 item["state"]
1084:                 for item in MigrationOperator(
1085:                     db_path=Path(db_path),
1086:                     backup_dir=Path(db_path).parent / "backups",
1087:                 ).status()
1088:             )
1089:         ) or {"unavailable": 1}
1090:     except Exception:
1091:         migration_states = {"unavailable": 1}
1092:     manifest = load_release_manifest()
1093:     return {
1094:         "schema_version": "v1",
1095:         "observed_at": now_utc(),
1096:         "release": safe_release_summary(),
1097:         "migrations": migration_states,          // ★ 就是这个字段
```

**即**：

```
"migrations": Counter(item["state"] for item in MigrationOperator(...).status())
```

**`applied` 与 `pending` 不是「全库迁移数」** ——
**它们是 `MigrationOperator.status()` 返回项的 `state` 字段的**取值计数** ✓

**而 `MigrationOperator` 来自 `shared/migration_runner`（第 1054 行 import）** ✓

## 2. 🎯 所以我第 117 轮的「更正」**更正过头了**

三轮的表述变化：

| 轮次 | 我写的 | 评价 |
| --- | --- | --- |
| 115 · 116 | 「迁移并未完成」 | **方向对，但我没说清它的粒度** |
| **117** | 「那句话过宽了；主库有 18 条记录，所以不是只应用了 6 个」 | ❌ **过度更正** |
| **119（本轮）** | **`6/4` 是 operator 对 10 项的 state 计数** | ✅ **确切** |

**第 117 轮我拿「主库 `schema_migrations` 有 ~18 行」去否定 `6`，但那两者根本不是同一个度量**：

| 度量 | 来源 | 含义 |
| --- | --- | --- |
| `schema_migrations`（~18 行） | **数据库自己的记录** | 已被记录为应用的迁移 |
| **`{applied: 6, pending: 4}`** | **`MigrationOperator.status()`** | **operator 对迁移集合（10 项）的判定** |

**两个都真实，只是不是一回事。**
**而 `pending: 4` 是一条**真实**的「还有 4 个迁移待应用」信号** ✓

**所以第 117 轮我把一条正确的发现错误地降级了。** 这一轮把它恢复，并给出确切依据。

## 3. 顺带确认的几处

| 事实 | 依据 |
| --- | --- |
| 该路由**只读**数据库 | 第 1064 行 `PRAGMA query_only=ON` |
| 失败时降级为 **`{"unavailable": 1}`** | 第 1090-1091 行的 `except` |
| 同一返回体里还有 `research` / `jobs` / `outbox` / `learning` / `machine_knowledge` 的分组计数 | 第 1065-1079 行 |
| **`release` 用 `safe_release_summary()`** | 第 1096 行 —— 与第 112 轮实测到的 `unreleased / public: false` 一致 |

## 4. 下一轮（定性的最后一步）

**读 `shared/migration_runner.MigrationOperator.status()`** ——
看它返回哪些 `state` 取值、以及**哪 4 项被判为 `pending`**，
**这样才能回答「那 4 个是什么、为什么没应用」这个真问题。**

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「那 4 个 pending 是缺陷」 | **仍未读 `status()`** —— 不明其判据 |
| 「`applied` 一定是 6」 | 我只在那一轮读数里见过这个值 |

## 6. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（grep + 读一个文件）。
**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；**未删除任何东西**。
