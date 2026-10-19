# AAOS-01 Q11（续）：**恢复有绑定守卫；我这次的现场设错了**

**结论先说：独立恢复仍未达成。** 但本轮查明了它的**前置条件**与一道**真实守卫**。

## 1. 我做了什么

把第 52 轮的备份恢复到**独立位置** `.project-local/runs/restore-target`（全新目录）：

```
restore-candidate <backup>     -> exit 0，产出候选路径
restore-activate  <candidate>  -> exit 1
```

## 2. 两道发现

### (a) 恢复候选**绑定到特定目标库** —— 这是一道守卫

```
shared/backup.py:499  raise RuntimeError("restore candidate is bound to a different target database")
```

**候选不能被激活到「另一个」目标库上。** 这是**好事**：它防的是「把 A 的备份灌进 B」。

### (b) 目标库**必须已经存在**

```
migration-status -> FileNotFoundError: SQLite database not found: .../restore-target/archeaxis.sqlite
```

**一个全新的空目录不是有效的恢复目标** —— 目标得是一个**已经建立**的库。

## 3. 所以我的现场错在哪

我把目标目录**建成空的**就去恢复。正确的次序应当是：

```
1. 在目标位置建立并迁移一个库（目标已存在）
2. restore-candidate <backup>   （此时候选绑定到这个目标）
3. restore-activate  <candidate>
4. 读回，并冷启动后再读一次
```

**我把第 1 步漏了。**

## 4. 本轮**学到**的（不是失败，是前置条件）

| 事实 | 来源 |
| --- | --- |
| `restore-candidate` **会**产出候选并 exit 0 | 实测 |
| 候选**绑定**目标库，激活到别处会被拒 | `shared/backup.py:499` 实测 |
| 目标库**必须已存在** | `FileNotFoundError` 实测 |
| `restore-backup` = 上面两步合一 | `app/runtime_entrypoint.py` 读源码 |

## 5. 本轮**未**达成

| 项 | 状态 |
| --- | --- |
| **独立恢复成功** | ❌ **未达成** —— 目标未预先建立 |
| 恢复后**读回同一份数据** | ❌ 未测（库根本没建起来） |
| 冷启动后一致性 | ❌ 未测 |
| `after_restore` / `after_cold_start` 都是 `db_present: false` | —— 如实记录 |

（探针里那个 `stable_across_restart: true` 是**两个 `false` 相等**得出的 —— **无意义，我不拿它当证据**。）

## 6. 本轮未做

1. **未**改任何实现文件；
2. **未**触碰官方 Green 与资料库；
3. 临时目录保留，供下一轮按正确次序重做。

## 7. 下一轮

**按正确次序**：在目标位置 `migrate` 出一个库 → `restore-candidate` → `restore-activate` →
**读回 + 冷启动再读**。这才可能给出 Q11 的完整证据。
