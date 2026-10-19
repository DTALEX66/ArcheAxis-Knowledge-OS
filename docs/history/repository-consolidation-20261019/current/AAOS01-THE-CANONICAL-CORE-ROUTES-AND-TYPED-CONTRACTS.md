# 🎉 AAOS-01 Q03：**规范 Rust Core 的路由集与类型化契约**

## 1. 正面证据：两条 200

```
GET /api/v1/system/version  ->  200
  {"actor": "human",
   "contract": "0.1.0-outline",
   "launch_protocol": "archeaxis.desktop-launch/v2",
   "runtime": "archeaxis-api",
   "schema_version": 6,
   "session_id": "cccccccccccccccccccccccccccccccc",
   "workspace_db": "\\\\?\\D:\\All proj…"}

GET /api/v1/evidence/anchors  ->  200   {"items": []}
```

**三点值得记：**

| 观察 | 意义 |
| --- | --- |
| **`actor: "human"`** | **人类凭据派生出了人类 actor** —— 第 134 轮只证明「授权通过」，本轮证明**身份被正确判定** |
| **`schema_version: 6`** | 与 Python 后端的 schema 版本不同（那边是 9）—— **两个面各自演进** |
| **`contract: "0.1.0-outline"`** | 它**自述为 outline** —— 与「未发布」的定位一致 |

**`evidence/anchors` 是一条**真实数据路由**（返回 `{items: []}`）** ✓

## 2. 🎯 405 与 422 一起把路由集描出来了

```
GET  /api/v1/knowledge-items   ->  405   // 方法不允许 => 【路由存在】
GET  /api/v1/learning/reviews  ->  405   // 同上

POST /api/v1/knowledge-items   ->  422
  "Failed to deserialize the JSON body into the target type:
   missing field `knowledge_type` at line 1 column 16"

POST /api/v1/learning/reviews  ->  422
  "unknown field `note`, expected one of `item_key`, `client_event_id`,
   `correct`, `rating`, `now`, `answer`, `assessment_id`, `question_version`, `knowledge_v…"
```

**405 告诉我「路由在、方法不对」；422 告诉我「字段不对，这是正确的字段列表」。**

**两者合起来，比任何文档都精确。**

## 3. 🎯 这确证了两条 API 面的**性质差异**

| | Rust Core | Python 后端 |
| --- | --- | --- |
| **请求体** | **类型化**（422 列出确切字段） | **裸 `dict`**（无 schema） |
| **证据** | 本轮实测 | 第 108 轮实测：`/api/v1/workspace/api/knowledge` **只有 GET**；`/openapi.json` 里 `fields: null` |
| **路由文档** | **无 OpenAPI**（靠 422 与 405 反推） | **有 `/openapi.json`** |

**这解释了第 110 轮我的困惑**：我从 Python 后端的 `/openapi.json` 看不到请求体；
**而 Rust Core 的契约是**编译进类型**的** —— **两边的「可发现性」正好相反** ✓

## 4. 已枚举的路由（**只列实测过的**）

```
GET  /api/v1/system/version     200  返回 runtime/contract/schema_version/session_id/workspace_db/actor
GET  /api/v1/evidence/anchors   200  返回 {items: []}
GET  /api/v1/knowledge-items    405  路由存在，方法不对
POST /api/v1/knowledge-items    422  需要 knowledge_type
GET  /api/v1/learning/reviews   405  路由存在，方法不对
POST /api/v1/learning/reviews   422  需要 item_key/client_event_id/correct/rating/now/answer/…

404（在本次尝试中未发现）:
  /  /api/v1/health  /api/v1/capabilities  /api/v1/machine/answers
  /api/v1/objects  /api/v1/sessions  /api/v1/system/status  /api/v1/workspaces
```

**⚠️ 404 只说明**我试过的这些路径**不存在，**不说明路由集就这些** ✓

## 5. Q03 的记账

| 项 | 状态 |
| --- | --- |
| **规范 Core 可运行** | ✅ |
| **v2 启动契约** | ✅ |
| **启动层 actor 校验** | ✅ |
| **请求层凭据五条边界** | ✅ 实测 |
| **actor 身份判定（正面）** | ✅ **`actor: "human"` 实测** |
| **部分路由集与类型化契约** | ✅ **本轮** |
| **完整路由集** | ⏳ **未枚举完** —— 需要更系统地扫 |
| **canonical 数据模型** | ⏳ **仍等你决定** |

## 6. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「Rust Core 只有这几条路由」 | **我只扫了 12 条路径** |
| 「`machine/answers` 在 Rust Core 上不存在」 | **它可能用别的路径** —— 我只试了一个 |
| 「`schema_version: 6` 与 9 的差异是问题」 | **两面各自演进是正常现象**，我未追证 |

## 7. 守住的两条边界

**二进制从 Green 候选【复制】出来、在 scratch 目录运行** —— Green 目录**零改动** ✓
**scratch 的 DB 路径与端口** —— 不碰任何既有数据 ✓
**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；**未执行任何安装**。
