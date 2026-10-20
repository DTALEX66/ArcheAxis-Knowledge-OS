# AAOS-01 Q03 更正与细化：**两处路由不符，且我第 9 轮的 A 案不完整**（2026-10-04）

## 1. 更正：前端**不**调 Core 的 `/system/version`

`frontend/src/__tests__/RuntimeClient.test.ts` 的既有测试固定了真实语义：

```ts
window.__TAURI__ = { core: { invoke: vi.fn().mockResolvedValue({ port: 4312, token: "memory-only" }) } };
// 然后直接 HTTP：
GET /api/v1/system/handshake        // 头：X-ArcheAxis-Launch-Token: <token>
   期望 { product_id, product_name, api_contract, backend_version, source_commit,
          schema_version, runtime_mode, workspace_id, capabilities, migration_state }

GET http://127.0.0.1:4312/workspace/api/status   // ← 注意 /workspace/api 前缀
```

## 2. 所以**不符之处有三层**，不只是字段缺

| 维度 | 前端期望 | Rust Core 有 |
| --- | --- | --- |
| **路由名** | `/api/v1/system/handshake` | `/api/v1/system/version`（**无 handshake**） |
| **路径前缀** | `/workspace/api/...` | `/api/v1/...`（**无 `/workspace` 前缀**） |
| **字段** | 10 项 | 3 项（只对上 `schema_version`） |

**我第 9 轮只说了第三层（字段），漏了前两层。**

## 3. 因此我第 9 轮的「A 案」**不完整** —— 必须更正

第 9 轮我提议"**宿主合成握手交给前端，Core 不动**"。**这条单独做不到**，因为：

> 前端是**从后端端口用 HTTP 取** handshake（`X-ArcheAxis-Launch-Token` 头），**不是**通过 Tauri IPC 取。

**能确认的、已经工作是**：宿主↔前端 IPC 供 `{port, token}`（`window.__TAURI__.core.invoke`）✓ —— **这一段不用改**。

## 4. 于是有三个选项（新增 C，且它最贴合本项目成文策略）

| 选项 | 内容 | 代价 |
| --- | --- | --- |
| **A′** | **Core 增补** `handshake` 路由 + `/workspace/api` 兼容前缀 + 9 个字段 | 把宿主事实写进 canonical 写者；提前冻结 `0.1.0-outline` 契约 |
| **B′** | **前端改路由与判据**去对齐 Core 现有 `/api/v1/system/version` | 要改前端 10 项判据与全部 `/workspace/api/*` 调用点；**会动 16/119 基线** |
| **C** | **薄兼容适配层**：在 Core 前提供前端期望的旧形状（`/handshake`、`/workspace/api/*`），翻译到 Core | 多一个要维护的进程/层；但**Core 与前端都不动** |

**为什么把 C 列出来**：`AGENTS.md` §1 成文写着 ——

**C 正是 adapter/sidecar 路线**，而它还有一个决定性优点：**把契约之争隔离在一个可丢弃的层里**，等 Core 的 `0.1.0-outline` 稳定后再决定是否上提为正式合同。

## 5. 本轮**未**做

1. **未改任何实现文件**；**未建任何 schema**；
2. **未构建、未运行**（未实际握手一次）；
3. **未读** `frontend/src/api/workspace.ts` —— 那里应该有**全部** `/workspace/api/*` 调用点，**数量未核**（所以 §4 里"全部调用点"的工作量**是估计，不是测量**）；
4. 本轮的 `RuntimeClient.test.ts` 只读了前 ~110 行（共 537 行），**其余未读**。

## 6. 下一轮

**先测量再选**：读 `frontend/src/api/workspace.ts` 数清 `/workspace/api/*` 调用点数量与形状，并读完 `RuntimeClient.test.ts`，然后给出 A′/B′/C 的**工作量对比**（用计数，不用形容词）。

**在你裁决之前，我不动实现。** 第 9 轮我说过"不回答就按 A 推进" —— 本轮发现 A 不完整，**所以那个默认作废**，改为"先测量再提"。"
