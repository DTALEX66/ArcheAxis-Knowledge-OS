historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# AAOS-01 Q02：**知识路由只读 —— 但读桥接得到确证**

## 1. 结果

```json
"knowledge_methods": [ "GET" ]        // 【只有 GET】
"knowledge_before":  [200, "{\"schema_version\":\"v1\",\"items\":[]}"]
"ready_after_seconds": 1
"core_alive": true
```

## 2. ✅ 读桥接：确证（这次有结构化载荷）

上一轮我从**页面**推断状态与计数来自 Core；**本轮直接向后端请求，拿到了它的原始响应**：

```json
{"schema_version": "v1", "items": []}
```

**这是后端自己给出的结构化数据** —— 比读界面转述更直接。

| 证据层级 | 强度 |
| --- | --- |
| 界面显示「本地数据库 可用」 | 中（可能是前端文案） |
| **直接请求返回 `{schema_version, items}`** | **强（后端原始响应）** |

## 3. ⚠️ 但这条路由不接受写

`GET /api/v1/workspace/api/knowledge` **只有 GET** —— 所以**「读写闭环」的写要用其它路由**。

按第 107 轮从 `/openapi.json` 拿到的权威清单，可能的写入口有：

```
/api/v1/workspace/api/commands/promote-research
/api/v1/workspace/api/commands/record-practice
/api/v1/workspace/api/commands/start-learning
/api/v1/workspace/api/evidence/anchor
/api/v1/workspace/api/intake/upload
/api/v1/workspace/api/intake/url
/api/v1/workspace/api/knowledge/start-learning
/api/v1/workspace/api/backup/create
/api/v1/workspace/api/exchange/import
```

**哪些真的接受写、各自的请求体是什么** —— 下一轮从 schema 里逐个确认，**不再猜**。

## 4. 我要认的一处方法问题

我的探针里写了一段「从 `requestBody` 里取模型名」的代码，**它取出来的是一堆无意义的碎片**
（`request_model: "{"`、`request_fields: []`）。**因为那条路由根本没有 POST**，
**而我的取法也只是粗糙的字符串切分。**

**教训**：**先确认方法存在，再谈请求体** —— 顺序反了就会得到一堆空值，还容易被我误读成「契约很简单」。

## 5. Q02 现状

| 验收要素 | 状态 |
| --- | --- |
| 宿主启动 | ✅ 第 102 轮 |
| **只读桥接** | ✅ **第 103 轮（界面）+ 本轮（后端原始响应）** |
| 读写闭环的**写** | ⏳ **未做** —— 入口候选已列出，待逐个确认契约 |

## 6. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「读写闭环已通过」 | **我一次都没写成功** |
| 「`items: []` 说明库是空的」 | 这只是**这条路由**的返回；空库是旁证不是我本轮的结论 |

## 7. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 建 scratch 数据根、跑 migrate + core、发只读请求 | `.project-local/runs/readwrite2/` | **项目自有开发输出** |

**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；
**未修改真实产品数据目录**；**未删除任何东西**；只 kill 自己起的句柄。
