historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

> 归档（2026-10-08 文档收敛，批次 d-docs-20261008）：本文件自 `docs/current/` 原样移入 `docs/history/aaos01-20261005/`，正文、日期与原始证据未改写；该主题的当前入口是 `docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`。

# AAOS-01 Q02：**写路由存在，但 schema 不声明请求体**

## 1. 本轮的方法修正（上一轮的教训已应用）

上一轮我错在「先谈请求体，再确认方法存在」。本轮**先按方法筛**，只列出真正接受
`POST/PUT/PATCH` 的路由。

## 2. 结果：写路由确实存在

```
POST /api/v1/learning/review-outcome    "Review Outcome"
POST /api/v1/learning/teach-back        "Submit Teach Back"
POST /api/v1/learning/tick              "Learning Tick"
POST /api/v1/learning/trajectory        "Save Trajectory"
POST /api/v1/setup/initialize           "Post Setup Initialize"
POST /api/v1/setup/preflight            "Post Setup Preflight"
POST /api/v1/system/restart             "System Restart"
POST /api/v1/workspace/api/batch/{batch_id}/pause   "Workspace Batch Pause"
POST /api/v1/workspace/api/batch/{batch_id}/resume  "Workspace Batch Resume"
```

## 3. ⚠️ 但每一条的请求体都是 `null`

```json
{"method": "POST", "path": "/api/v1/learning/tick",
 "summary": "Learning Tick", "model": null, "fields": null, "required": null}
```

**schema 里没有声明请求模型** —— 说明处理器接收的是**裸 body**（`dict`），而不是 Pydantic 模型。

**含义**：

| 事实 | 后果 |
| --- | --- |
| 路由签名不描述请求体 | **`/openapi.json` 帮不到我学契约** |
| 契约在处理器源码里 | **下一轮该读的是 `app/` 下对应 handler 的源码** |

**这不是缺陷，是 FastAPI 的常见写法** —— 但对我这种「靠 schema 学契约」的做法是死路。

## 4. ⚠️ 我没看到的：总数

我的输出被截断，`write_capable_count` **没显示出来**。

**所以我不报写路由的总数** —— 只报我实际看到的这几条。

**这是第 87 轮那次截断教训的又一次应用：看不到的部分不当作已知。**

## 5. 下一轮（具体）

**读一个最简写路由的处理器源码**（`/api/v1/learning/tick` 看起来参数最少），
拿到它的真实请求体形状，**然后真正写一次、再读回来**。

若 `tick` 需要的外部状态太多，就换 `/api/v1/setup/preflight`（无副作用、只读语义最强）。

## 6. Q02 现状

| 验收要素 | 状态 |
| --- | --- |
| 宿主启动 | ✅ 第 102 轮 |
| 只读桥接 | ✅ 第 103 轮 + 第 108 轮 |
| 读写闭环的**写** | ⏳ **未做** —— 但路径已收窄到「读一个 handler 源码」 |

## 7. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「写路由共 N 条」 | **输出被截断，我没看到总数** |
| 「这些路由都能写成功」 | **一条都没试** |

## 8. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 建 scratch 数据根、跑 migrate + core、取 schema 并筛选 | `.project-local/runs/write-contracts/` | **项目自有开发输出** |

**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；
**未修改真实产品数据目录**；**未删除任何东西**；只 kill 自己起的句柄。
