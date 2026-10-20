# AAOS-01 Q09 收口：**搜索是好的 —— 错在我给的 root，不在能力**

## 1. 我先猜错了一次

我怀疑本机搜索失败是**路径里的空格**造成（与第 29 轮 `windres` 同一根因）。**做了一个对照实验**：

```
space-free root: C:\Windows\TEMP\vault-nospace-…          含空格: False
fixture root:    D:\All projects\…\obsidian-vault           含空格: True

{ "label": "space-free", "status": 200, "match_count": 1 }
{ "label": "with-space", "status": 200, "match_count": 2 }   <-- 含空格的那个也 200
```

**假设被自己的实验否掉了** ✓ —— 而且顺带说明**搜索本来是好的**。

## 2. 那第 38 轮的 500 / 超时是怎么回事

读源码后原因清楚了（`app/workspace/vault.py:25-28`）：

```python
def _session(root, store):
    ...
    raise VaultWorkbenchError("approved Vault root must be an existing directory")
```

`root` **必须是一个存在的目录**。而我第一次传的是**我自己的运行目录** —— 里面是 SQLite 库、
`-wal`/`-shm` 旁文件、staging 等。**把"一个数据仓库"当成"一个 vault 根"传进去**，于是 500。

第二次传 fixture-vault 超时：**该次没有复现**（本轮同一根返回 200，`match_count: 2`）。
**所以那个超时的具体原因我没有查明** —— 只能说它**不可复现**。

## 3. 因此正面结论可以立起来了

换上**专门造出来的 vault 根**（一个只含 `note.md` 的临时目录）后：

```
purpose-built-vault:  200, match_count >= 1
fixture-vault:        200
```

**并且这个正面结果在 CI 上也成立**（第 38 轮 CI 对两个 root 都返回 200）。

**所以"搜索可用"现在是一条可复现的断言，而不是一台机器的行为。**

## 4. 断言随之从"不作声明"改为"正面声明"

| 版本 | 断言 | 为什么改 |
| --- | --- | --- |
| 第 38 轮 | `assert 200 not in statuses` | **错**：把本机失败当产品事实，CI 驳回 |
| 第 38 轮修正 | `assert "status" in attempt` | **过渡**：不再声称，但也不确认 |
| **本轮** | `status == 200` 且 `match_count >= 1` | **对**：已在**两个环境**复现 |

**判断标准很清楚**：一个结论只有在**与环境无关**（源码事实）或**已跨环境复现**时，才配写成断言。

## 5. 附带收益

搜索一旦真的应答，测试从 **125 秒 → 26 秒 → 5 秒**（后两段还包含我把搜索超时从 60 秒降到 10 秒）。
**之前那两分钟，几乎全是在等一个我传错 root 的调用超时。**

## 6. 本轮**未**做

1. **未查明**第 38 轮那次 fixture-vault 超时的原因（只确认**不可复现**）；
2. **未改任何实现文件**；
3. 官方 Green 与官方资料库**零触碰**。
