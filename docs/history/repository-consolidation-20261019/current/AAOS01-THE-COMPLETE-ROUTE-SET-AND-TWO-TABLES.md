# 🎉 AAOS-01 Q03：**完整的 Rust Core 路由集 —— 且分两个路由表**

## 1. 36 条路由注册（源码为准，不再逐条试）

### 主路由（`crates/archeaxis-api/src/lib.rs:55-97`）
```
GET  /api/v1/system/version
POST /api/v1/imports                     POST /api/v1/jobs
POST /api/v1/sources/:source_id/anchors
POST /api/v1/knowledge-items             GET  /api/v1/knowledge-items/:id/v3
POST /api/v1/learning/events             POST /api/v1/learning/reviews
GET  /api/v1/learning/events/:item_key   GET  /api/v1/learning/items
GET  /api/v1/learning/items/:key/state
POST /api/v1/machine/tasks               GET  /api/v1/machine/tasks/:task_id
GET  /api/v1/search                      GET  /api/v1/jobs/:job_id/quality
GET  /api/v1/evidence/anchors            // 【我实测 200】
GET  /api/v1/sources/:source_id/members  GET  /api/v1/sources/:source_id/jobs
GET  /api/v1/workspaces/info
POST /api/v1/jobs/:job_id/receipts
```

### runtime 子路由（`crates/archeaxis-api/src/runtime/mod.rs:36-81`）
```
GET  /api/v1/jobs/:job_id                GET  /api/v1/jobs/:job_id/outputs/:kind
POST /api/v1/jobs/:job_id/executions
GET  /api/v1/capabilities                // 【我实测 404】
GET  /api/v1/capabilities/:capability
POST /api/v1/machine/answers             // 【我实测 404】
POST /api/v1/ask                         POST /api/v1/search/semantic
POST /api/v1/machine/corrections         POST /api/v1/machine/retests
POST /api/v1/courses                     GET  /api/v1/courses/:id
POST /api/v1/courses/:id/render
POST /api/v1/vault/links                 POST /api/v1/vault/links/record
POST /api/v1/vault/members
```

## 2. 🎯 两个 404 现在有确切解释

| 路由 | 所在表 | 我实测 | 一致性 |
| --- | --- | --- | --- |
| `GET /api/v1/evidence/anchors` | **`lib.rs`** | **200** | ✅ 一致 |
| `GET /api/v1/capabilities` | **`runtime/mod.rs`** | **404** | ✅ 一致 |
| `POST /api/v1/machine/answers` | **`runtime/mod.rs`** | **404** | ✅ 一致 |

**即：我跑的那个二进制挂了 `lib.rs` 的路由，**没有挂 `runtime/mod.rs` 的子路由**。**

**而「是否挂载 runtime 子路由」很可能取决于启动文档里有没有 `text_worker`** ——
**因为那张表里的能力路由（`capabilities`）与 `machine.answer` 正是 **worker 相关**的。**

**这一条把三件事串起来了**：

| 轮次 | 现象 | 同一个原因 |
| --- | --- | --- |
| **59** | Python 侧 `machine.answer` → **503 no worker is registered** | **没声明 worker** |
| **131** | 读源码发现路由来自 `text_worker.routes` 的**声明** | **声明决定注册** |
| **136（本轮）** | Rust 侧 `capabilities`/`machine-answers` → **404** | **没声明 `text_worker` → runtime 子路由未挂载** |

**三次都指向同一条设计**：**能力路由由启动声明决定，未声明就不存在。**

## 3. 我**要标为推断**的部分

> **「runtime 子路由的挂载条件是 `text_worker` 是否存在」** ——
> **这是我从「哪些路由在哪个表里」推断的，**我尚未读挂载处的那行代码**。**
**下一轮只读地确认 `lib.rs` 里如何 merge `runtime::router`，即可把它从推断变成事实。**

## 4. Q03 的记账

| 项 | 状态 |
| --- | --- |
| **规范 Core 可运行** | ✅ |
| **v2 启动契约** | ✅ |
| **启动层 actor 校验** | ✅ |
| **请求层凭据五条边界** | ✅ |
| **actor 身份判定（正面）** | ✅ `actor: "human"` |
| **完整路由集** | ✅ **本轮 —— 36 条，来自源码** |
| **两张路由表与挂载条件** | 🔶 **路由表已明确；挂载条件待确认** |
| **canonical 数据模型** | ⏳ **仍等你决定** |

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「挂载条件就是 `text_worker`」 | **推断** —— 未读挂载代码 |
| 「36 条全部可用」 | **我只实测了其中 4 条的状态码** |

## 6. 守住的两条边界

**二进制从 Green 候选【复制】出来、在 scratch 目录运行** —— Green 目录**零改动** ✓
**scratch 的 DB 路径与端口** —— 不碰任何既有数据 ✓
**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；**未执行任何安装**。
