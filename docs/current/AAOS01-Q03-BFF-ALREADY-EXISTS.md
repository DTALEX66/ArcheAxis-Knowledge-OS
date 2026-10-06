# AAOS-01 Q03 **重大发现**：只读 BFF **已经存在**，且带书面契约（2026-10-04）

前几轮我把选项 C 当作"**要从零写 61 条路由**"。**这个前提是错的。**

## 1. 已经存在的东西

| 资产 | 事实 |
| --- | --- |
| `app/workspace/router.py` | **1319 行**，服务 `/workspace/api/*` |
| `docs/contracts/WORKSPACE_BFF_V1.md` | **书面契约**，状态 "**BE01 implementation candidate — read-only contract**"，Owner "**Cognitive-OS workspace boundary**" |

契约原文关键句：

> "The v1 BFF is a **server-owned projection boundary** for the product shell. **It is not a second persistence API** and it is not an authorization credential."
> "Base path: `/workspace/api/v1`"
> "**Methods in this contract: `GET` only**"
> "**Existing `/workspace/api/*` endpoints remain a compatibility surface and are not part of this contract. UI migration must not silently mix the two surfaces.**"

## 2. 它是**只读**的 —— 这直接决定它能不能用

在 `app/workspace/router.py`（1319 行）中检索：

```
sqlite3.connect / INSERT / UPDATE / DELETE FROM   -> 零命中
```

**它不是写者。** 所以：

- 与"**Rust Core 是唯一 canonical 写者**"**不冲突** ✓
- 与包内"**不把旧 Python 后端重新接成权威**"**不冲突** ✓ —— 投影边界不是权威
- 正是 `AGENTS.md` §1 说的 **projection / adapter** 路线 ✓

## 3. 而且契约**已经点出**了当前的违规

契约说"**UI migration must not silently mix the two surfaces**"。而第 11 轮我实测前端**同时**打两套：

- `/workspace/api/v1/*`（**新的 BFF 契约面**）
- `/workspace/api/*`（**legacy 兼容面，契约明确说"不属于本契约"**）

**所以现在的树里，UI 正在混用两个面 —— 正是该契约禁止的事。** 这是一个**具体的、有文档依据的**发现。

## 4. 因此 C 的成本要**大幅下调**（这次是往下修）

| 轮次 | 我对 C 的估计 | 依据 |
| --- | --- | --- |
| 11 | "~75 条映射" | 只数了路径 |
| 12 | "61 条都要覆盖，不薄" | 零重叠 |
| 13 | "部分可能是别名，略轻" | 按名字 |
| 14 | "**上调**，别名预期下调" | 核了 1 条载荷 |
| **15（本轮）** | **"已有一个只读投影边界，工作主要是把它对准 Rust Core"** | **契约 + 零写者证据** |

**第 14 轮的"上调"是在不知道 BFF 已存在的情况下做的 —— 本轮证据更强，因此覆盖它。**

## 5. 但**必须**加一句限定

我**没有**核 `router.py` 的数据**来源** —— 它既没有 `sqlite3.connect`，也没有 HTTP 客户端（只有 `urllib.parse` 的 quoting），

**这可能是个好消息**（若它已通过一个可替换的数据源适配器读取，换源即可），**也可能不是**（若它读的是旧 Python 后端的内部状态，就没有可替换的边界）。
**在这一点查明之前，我不把"对准 Rust Core 很容易"当成结论。**

## 6. 下一轮（明确、可验证）

**把 61 条路径按"属于哪个面"分类**：

1. 哪些是 **BFF v1 契约面**（`/workspace/api/v1/*`，GET）；
2. 哪些是 **legacy 兼容面**（`/workspace/api/*`，契约说本就不属于 v1）；
3. 哪些是 `/api/v1/*`（**Rust Core 的面**）。

分类做完，"C 要覆盖多少"才有**真实基数**。**这才是该先测的东西。**

## 7. 本轮**未**做

1. **未改任何实现文件**（未写适配层）；未建 schema；未构建未运行；
2. **未查明** `router.py` 的数据来源（§5）；
3. **仍未读完** `RuntimeClient.test.ts`（**连续第三轮欠账**）；
4. **未读** `WORKSPACE_BFF_V1.md` 全文（只读了前 26 行）。
