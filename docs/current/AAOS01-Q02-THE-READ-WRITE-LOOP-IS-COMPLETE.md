historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# 🎉🎉 AAOS-01 Q02：**读写闭环完整了 —— 而且带出真实的治理行为**

## 1. 走的正是产品自己认可的通道

```json
"desktop_control_set": false      // 不设桌面控制变量 -> 走非桌面路径
"launch_token_set": false         // 不设令牌 -> expected_token 为空
"smoke_bypass_set": "1"           // 声明浏览器冒烟 -> 授权层放行
"serving_port": 8805
```

**这不是绕过授权，是第 113 轮从文档字符串读到的 `the explicit browser-smoke process`。**

## 2. 🎉 写入被接受，返回 200

**我发出的请求体（只有意图，没有任何真值字段）**：

```json
{"node_id": "smoke-node-1", "learner_id": "smoke-learner-1",
 "action_intent": "review", "idempotency_key": "<hex>"}
```

**服务端返回**：

```json
{"node_id": "smoke-node-1",
 "action": "review_evidence",
 "state": {"node_id": "smoke-node-1",
           "human":     {"level": "M0",   "label": "M0 SEEN"},     // 【服务端派生】
           "machine":   {"level": "NONE", "label": "NONE"},        // 【服务端派生】
           "evidence":  "unverified",                             // 【服务端派生】
           "action": "review_evidence", "delta": 0},
 "payload": {"kind": "review_evidence",
             "reason": "evidence is not current — outranks mastery"}}
```

## 3. 🎯 这才是真正的收获：治理行为是**活的**

### (a) 真值**由服务端派生**，客户端只能表达意图

| 我发的 | 服务端派的 |
| --- | --- |
| 没有 `human` | **`human: M0 SEEN`** |
| 没有 `machine` | **`machine: NONE`** |
| 没有 `evidence_verified` | **`evidence: unverified`** |

**与第 110 轮读到的 `forbidden` 集合完全对应** ✓ —— **源码里的约束在运行时确实生效。**

### (b) 🎯 产品**拒绝在没有凭据时推断掌握度**

```
"reason": "evidence is not current — outranks mastery"
```

**这正对应处理器文档字符串的承诺**：

> > Until durable evaluation receipts exist for the requested node, this path
> > deliberately returns ``review_evidence`` rather than inferring mastery.

**也与文档里「模型置信度不等于准确率」「准确率需要人类真值/预测对」同向** ✓

**这是我在这个会话里见到的最强的一条「治理不是声明，而是运行时行为」的证据。**

### (c) 幂等

同一个 `idempotency_key` 再发一次 → **同样 200，同样结果** ✓ —— 幂等键在起作用 ✓

## 4. Q02 的验收要素（现在的记账）

| 要素 | 状态 |
| --- | --- |
| 宿主启动 | ✅ 第 102 轮 |
| 只读桥接 | ✅ 第 103 · 108 轮（含后端原始响应） |
| **读写闭环** | ✅ **本轮 —— 写被接受（200），且返回结构化结果** |

**我仍不写「Q02 全部通过」** —— 因为本轮的写走的是**冒烟通道**，
而**桌面路径的写**需要宿主签发的令牌（第 113 轮已证）。
**两者是不同的授权级别，我不混同。**

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「桌面路径的写也成功」 | **未测** —— 那条路要宿主令牌 |
| 「冒烟通道等同于产品正常路径」 | **不等同** —— 文档字符串明说它「无法模拟已启动的桌面 Core」 |
| 「数据已持久化」 | **本轮的读回是响应的结果**，我没有另做一次独立读取来确认落盘 |

## 6. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 建 scratch 数据根、以冒烟通道跑 migrate + core 并写入一次 | `.project-local/runs/smoke-write/` | **项目自有开发输出** |

**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；
**未修改真实产品数据目录**；**未删除任何东西**；只 kill 自己起的句柄。
