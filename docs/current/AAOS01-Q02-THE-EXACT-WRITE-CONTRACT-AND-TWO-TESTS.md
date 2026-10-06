historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# 🎯 AAOS-01 Q02：**确切契约 —— 而且是一条治理级设计**

## 1. 找到了最简写路由的处理器（`app/api/learning.py:218`）

```python
218: @router.post("/tick", dependencies=[Depends(_require_desktop_write_request)])
219: def learning_tick(payload: dict[str, object]) -> dict[str, object]:
220:     """Accept action intent only; truth-bearing axes are server-derived.
222:     Until durable evaluation receipts exist for the requested node, this path
223:     deliberately returns ``review_evidence`` rather than inferring mastery.
224:     """
228:     forbidden = {
229:         "human", "machine", "evidence_verified",
230:         "has_superseding", "has_contradiction",
231:     }
235:     asserted = sorted(forbidden.intersection(payload))
236:     if asserted:
237:         raise HTTPException(status_code=400,
239:             detail=("truth fields are server-derived and cannot be asserted by the client: "
242:                     + ", ".join(asserted)))
245:     node_id = str(payload["node_id"])
247:     str(payload["learner_id"])
248:     str(payload["action_intent"])
249:     idempotency_key = payload["idempotency_key"]
250:     if not isinstance(idempotency_key, str) or not idempotency_key.strip():
251:         raise HTTPException(status_code=400, detail="idempotency_key must be non-empty")
```

## 2. 请求体契约（现在**确定**了）

| 字段 | 要求 | 依据 |
| --- | --- | --- |
| `node_id` | 必填 | 第 246 行直接索引 |
| `learner_id` | 必填 | 第 247 行 |
| `action_intent` | 必填 | 第 248 行 |
| `idempotency_key` | 必填，且**非空字符串** | 第 249-251 行 |
| `teach` | 可选（dict） | 第 252-255 行 |
| `other_concepts` | 可选 | 第 263 行 |

**这也解释了为什么 `/openapi.json` 里 `fields: null`** —— 处理器收的是裸 `dict`，
**契约写在函数体里，不在签名里** ✓

## 3. 🎯 两个可直接验证的治理行为

### (a) 真值字段**不得由客户端断言**

```python
forbidden = {"human", "machine", "evidence_verified", "has_superseding", "has_contradiction"}
if asserted: raise HTTPException(status_code=400,
    detail="truth fields are server-derived and cannot be asserted by the client")
```

**这条正是「真值由服务端派生、客户端只能表达意图」的强制点** ——
与文档里「模型置信度不等于准确率」「准确率需要人类真值/预测对」的要求同向 ✓

### (b) 写操作**需要桌面写权限**

```python
dependencies=[Depends(_require_desktop_write_request)]
```

**这与启动器传的 `ARCHEAXIS_DESKTOP_WRITE_SCOPES=workspace:write` 对得上** ✓
**所以 Q03 的「权限」在这条路由上有明确的落点。**

## 4. 因此下一轮有**两个**可做的实测

```
① 合规写入：node_id + learner_id + action_intent + idempotency_key  -> 期望 200，且可读回
② 越权断言：额外带 human / evidence_verified                        -> 期望 400 且 detail 指名该字段
```

**② 是一条真正的权限/治理实测** —— 而且路径与方法都出自源码，不再需要猜。

## 5. 一个我自己的反复失误（第三次了）

**我又一次在 PowerShell 里用子串截取路径，把路径显示切坏了。**
第 105 轮犯过同样的错。**本轮我改用 grep 工具直接打印完整路径，就没再出错。**
记录在案：**涉及路径显示时，一律用工具的输出，不自己做字符串切分。**

## 6. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「写入会成功」 | **还没写** |
| 「`forbidden` 那条一定会返回 400」 | **还没试** —— 只有源码 |

## 7. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（grep + 读一个文件）。
**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；**未删除任何东西**。
