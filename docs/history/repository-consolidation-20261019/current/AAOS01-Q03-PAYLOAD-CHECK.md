# AAOS-01 Q03 载荷核对：**同名的那条也不是别名**，C 的成本上调（2026-10-04）

第 13 轮我把 `/workspace/api/evidence/anchors` 与 `/api/v1/evidence/anchors` 列为"**同名同概念**"，

## 1. 前端要求什么（`frontend/src/api/workspace.ts:376-388`）

```ts
GET /workspace/api/evidence/anchors?limit=N[&cursor=...]
// 响应必须是 items 投影：
record.items[]  每项必须有 anchor_id / raw_sha256 / source_revision
raw_sha256 必须匹配 /^[0-9a-f]{64}$/i
item.locator 必须是对象；若含 page，必须是 >=1 的整数
record.count 必须是 number
record.next_cursor 必须是 null 或 string
```

## 2. Core 提供什么（`crates/archeaxis-api/src/lib.rs:1006-1013` 的 SQL）

```sql
SELECT a.anchor_id, a.source_id, s.sha256, a.source_revision, a.position,
       a.created_at, s.original_name, <最后一个 knowledge_id>, <其 status>
  FROM anchors a JOIN sources s ON s.source_id = a.source_id
 ORDER BY a.created_at ASC, a.anchor_id ASC
-- 无 WHERE，无 LIMIT，无 cursor
```

## 3. 逐项对照

| 维度 | 前端要求 | Core 查询提供 | 结论 |
| --- | --- | --- | --- |
| 路径 | `/workspace/api/…` | `/api/v1/…` | **不同** |
| 信封 | `{ items, count, next_cursor }` | 响应组装未读 | **待核** |
| 标识 | `anchor_id` | `a.anchor_id` | 一致 |
| 哈希字段名 | `raw_sha256` | `s.sha256` | **需改名** |
| 定位 | `locator` **对象（可含 `page`）** | **`a.position`（不透明）** | **形状不同** |
| 分页 | 请求带 `limit`/`cursor`，响应必带 `next_cursor` | **无参数、全量、无 cursor** | **Core 无此能力** |

## 4. 因此结论变了

**这条"同名同概念"的路径，并不是别名** —— 适配层必须做四件事，**不是一次改名**：

1. 改路径前缀；
2. **重塑信封**（裸结构 → `{items,count,next_cursor}`）；
3. **改字段名与形状**（`sha256`→`raw_sha256`；`position`→`locator{page?}`）；
4. **合成分页**（`count` 要真数；`next_cursor` Core **根本没有**，只能给 `null` 或自建游标）。

**其中第 4 项尤其要提醒**：如果 Core 不支持游标，适配层给 `next_cursor: null` 是**诚实**的（表示"没有更多"），

## 5. 对三选项的影响（**上调 C 的估计**）

| 选项 | 第 13 轮的估计 | 本轮修正 |
| --- | --- | --- |
| **C** | "部分只需改前缀 + 改字段名，比新建能力轻" | **至少这条不是**：要重塑信封 + 合成分页。**C 的成本上调** |
| **A′** | 不变 | 若 A′ 要在 Core 侧"支持 cursor 分页"，那是**真的加能力**，不是加路由 |
| **B′** | 不变 | 不变 |

## 6. 本轮**未**做（关键的诚实边界）

1. **未读 Core 的响应组装代码**（`:1020` 之后）—— 所以"信封形状"我标的是**待核**，不是"已确认不同"；
2. **只核了 1 条路径**（`evidence/anchors`），**不是 5 条**；我上一轮说要抽查 3–5 条，**只做到 1 条**；
3. **仍未读完** `RuntimeClient.test.ts`（537 行，只读前 ~110 行）——**连续第二轮欠账，明确记下**；
4. **未改任何实现文件**；未构建、未运行。

## 7. 我的判断（可被后续核对推翻）

一条"最强候选"（同名）都做不到透传，那么**"61 条里很多是别名"这个预期应当下调**。

**但我不据此改推荐** —— 因为 A′/B′ 的成本同样会随此上升（A′ 要真加分页能力，B′ 要改更多判据），

**下一步应当先把剩余路径按"是否需要新能力"分类**，再谈选哪条路。
