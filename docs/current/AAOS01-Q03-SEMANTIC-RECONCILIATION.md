# AAOS-01 Q03 语义核对：**路径零重叠，但概念层有不少对应**（2026-10-04）

## 1. Core 的**完整** HTTP 面（`crates/archeaxis-api/src/lib.rs:55-99`，逐条抄录）

```
/api/v1/system/version                        GET
/api/v1/imports                               POST
/api/v1/jobs                                  POST
/api/v1/jobs/:job_id/quality                  GET
/api/v1/jobs/:job_id/receipts                 POST
/api/v1/sources/:source_id/anchors            POST
/api/v1/sources/:source_id/jobs               GET
/api/v1/sources/:source_id/members            GET
/api/v1/sources/:source_id/jobs/:job_id/transform   GET
/api/v1/knowledge-items                      POST
/api/v1/knowledge-items/from-transform       POST
/api/v1/knowledge-items/:id/v3               GET
/api/v1/learning/events                      POST
/api/v1/learning/events/:item_key            GET
/api/v1/learning/items                       GET
/api/v1/learning/items/:item_key/state       GET
/api/v1/learning/items/:item_key/assessment  POST
/api/v1/learning/reviews                     POST
/api/v1/machine/tasks                        POST
/api/v1/machine/tasks/:task_id               GET
/api/v1/search                               GET
/api/v1/evidence/anchors                     GET
/api/v1/workspaces/info                      GET
```

## 2. **更正我做过的比较口径**

第 12 轮我报"**ALREADY SERVED by core: 0 / NEEDS TRANSLATION: 61**"。那个数是**按字面路径相等**算的，**那个结论仍然成立**。

**但概念层并非如此。** 至少有这些是**同一件事、不同写法**：

| 前端 | Core | 判断依据 |
| --- | --- | --- |
| `/workspace/api/evidence/anchors` | `/api/v1/evidence/anchors` | **同名同概念** |
| `/workspace/api/evidence/anchor` | `/api/v1/sources/:source_id/anchors` | 都是"建锚点" |
| `/workspace/api/jobs` | `/api/v1/jobs` | 同名 |
| `/workspace/api/knowledge` | `/api/v1/knowledge-items` | 同概念 |
| `/workspace/api/library` | `/api/v1/imports` | 入库/摄取 |
| `/api/v1/learning*`（前端） | `/api/v1/learning/items\|events\|reviews` | 学习域 |

**所以 61 条不是"61 条全新能力"** —— 其中一部分是**同一能力的别名**。

## 3. 但**我这次只比了名字，没比载荷**

**必须说清**：上表依据的是**路径与函数名**，不是**请求/响应语义**。

## 4. 看上去 Core **没有**对应概念的部分（同样只是按名字判断）

`exchange/export`·`exchange/import`·`exchange/verify`（互通）· `delivery/dispatch`·`delivery/retry` ·

**其中一部分可能本就不该由 Core 承担**（`setup`/`backup`/`home`/`status` 更像宿主职责，呼应我第 9 轮的判断），**但这是我按名字的推测，不是结论**。

## 5. 对三选项的影响（**修正**而非推翻）

- **C 的成本可能低于 61 条全透传**：若某条只是别名，映射是"改前缀 + 改字段名"，比"新建能力"轻；
- **但 C 仍必须覆盖 61 条**：**没有一条能原样通过**（第 12 轮的字面结论不变）；
- **A′/B′ 的相对成本不变**（A′ 仍要 61 条 Core 侧路由，B′ 仍要 124 处编辑）。

## 6. 本轮**未**做

1. **未改任何实现文件**；未建 schema；未写适配层；
2. **未构建、未运行**；
3. **未逐条比对载荷语义**（§3 明说了）——**这是下一轮最该做的**；
4. `RuntimeClient.test.ts`（537 行）**仍只读前 ~110 行**（我上一轮说要读完，**没做到，如实记下**）。
