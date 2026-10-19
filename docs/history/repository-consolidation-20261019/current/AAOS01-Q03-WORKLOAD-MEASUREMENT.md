# AAOS-01 Q03 测量结果：**124 处调用 · 75 条路径 · 11 个文件**（2026-10-04）

用计数替代形容词。扫描 `frontend/src` 中所有 `/(workspace/api|api/v1)…` 字面量路径：

```
occurrences:            124
distinct literal paths: 75
files containing them:  11
```

（少数条目是我的正则在抓尾部注释（如 `-> 500`），**量级可信，尾部噪声不逐条清理**。）

## 1. **结构性事实**：前端同时打两套前缀

| 前缀 | 例子 |
| --- | --- |
| `/api/v1/...` | `system/handshake`、`home`、`learning`、`learning/review-queue`、`setup/status`、`setup/initialize`、`setup/preflight`、`setup/backup` |
| **`/workspace/api/...`** | **主体** —— `backup/*`、`batch/*`、`delivery/*`、`evidence/*`、`exchange/*`、`intake/*`、`jobs`、`knowledge`、`library/*`、`pdf/*`、`research/*`、`runtime/*`、`setup/status`、`status` |

**Rust Core** 暴露的是 `/api/v1/*`（`imports`/`jobs`/`knowledge-items`/`learning`…）—— **既没有 `/workspace/api/*`，也没有 `/system/handshake`**。

## 2. **决定性结构**：所有调用只经过一个 base

```ts
// frontend/src/api/client.ts:105,109
export function createApiClient(baseUrl: string, token: string, scopes: string[] = []) {
      response = await fetch(`${baseUrl}${path}`, { ... });
```

**路径是相对字面量，base 由参数给定。** 这一条把三个选项的成本拉开。

## 3. 三选项的**可数**对比

| 选项 | 要改的量（计数） | 契约影响 |
| --- | --- | --- |
| **A′** Core 增补 | 需新增 **~75 条** `/workspace/api/*` 路由 + `/system/handshake` + **9** 个字段 | 宿主事实进 canonical 写者；**提前冻结 `0.1.0-outline`** |
| **B′** 前端对齐 Core | **11 个文件**、**124 处**调用点、**75** 条路径 + **10** 项判据；**并且要重建 16 套件/119 用例的基线** | 前端判据离开旧契约 |
| **C** 薄兼容适配层 | **前端 0 改动、Core 0 改动**；新增一层覆盖 **~75 条路径 + 1 个握手** | 契约之争被隔离在**可丢弃的一层**里 |

## 4. 由此得到的判断（可被数字推翻）

**C 的工作面 ≈ 75 条映射 + 1 个握手合成**；**B′ 的工作面 = 124 处编辑 + 11 个文件 + 10 项判据 + 基线重建**。

而且两者**风险性质不同**：B′ 要**改动一个已有 119 个绿色用例的模块**；C **完全不碰它**。

再叠加 `AGENTS.md` §1 的成文偏好（"**Adapter/sidecar before building from scratch**"），**C 在成本、风险、成文策略三条上同时占优**。

## 5. 一个**尚未核**的重叠点（不夸大为已解决）

`/api/v1/learning*`、`/api/v1/home`、`/api/v1/setup/*` 与 Core 已有的 `/api/v1/learning` 等**可能部分重叠** —— 也就是说 **A′/C 需要新增的路由数可能少于 75**。**我没有逐条比对，所以 75 是上界，不是精确值。**

## 6. 本轮**未**做

1. **未改任何实现文件**；**未建任何 schema**；**未新增适配层**；
2. **未构建、未运行**（未实际握手一次）；
3. **未逐条比对** 75 条路径与 Core 现有路由的重叠（§5）；
4. `RuntimeClient.test.ts`（537 行）**仍只读了前 ~110 行**。

## 7. 需要的一句话

**A′ / B′ / C 选哪个？** 我建议 **C**。若不回答，**本轮之后我不动实现**，继续做只读的逐条重叠比对（§5）与 `RuntimeClient.test.ts` 剩余部分 —— **因为这三条路互相排斥，选错方向的实现改动是最贵的返工。**
