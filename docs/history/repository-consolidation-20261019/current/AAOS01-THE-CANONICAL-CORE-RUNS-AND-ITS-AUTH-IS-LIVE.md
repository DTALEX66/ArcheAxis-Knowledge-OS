# 🎉 AAOS-01 Q03：**规范 Rust Core 起来了 —— 权限模型当场生效**

## 1. 我做了什么

按第 131 轮读到的结构，构造启动文档并**写到 stdin**：

```json
{"launch_token": "<64 位十六进制>", "session_id": "<32 位十六进制>", "actor": "…"}
```

运行方式：`archeaxis-api.exe <scratch-db> <port>`，**二进制取自老 Green 候选的副本**，**数据根在 scratch**。

## 2. 🎉 它起来了

```
"human":   "output": ["archeaxis-api ready on http://127.0.0.1:8817"]
           "up_after_halfsecs": 1   "exit": null
           "token_hex64": true      "session_hex32": true
"machine": "output": ["archeaxis-api ready on http://127.0.0.1:8818"]
```

**即：**0.5 秒内就绪**；**我构造的 `launch_token`（64 位）与 `session_id`（32 位）**被启动层接受**** ✓

**第 130 轮那个 `invalid launch input`，是因为我把身份放错了地方（命令行而不是 stdin）。**
**本轮改正后即通过 —— 说明**契约读对了**。**

## 3. 🎯 启动层的 actor 校验当场生效

第三个用例 `actor: "robot"`：

```
"output": ["invalid launch actor"]
"up_after_halfsecs": null      // 【进程根本没起来】
```

**这与 `launch.rs:206` 那条规则逐字对应**：

```rust
if !matches!(launch.actor.as_deref(), None | Some("human") | Some("machine"));
```

**即：未知 actor **不能启动** —— 不是「启动后拒绝」，是**启动层就挡住** ✓

## 4. ✅ 而且**请求层**也要求凭据

Core 起来之后，**所有**我用过的请求都返回：

```json
401 {"code": "AAK-AUTH-001", "message": "invalid launch credentials", "retryable": false}
```

包括：

| 请求 | 结果 |
| --- | --- |
| `GET /api/v1/capabilities` | **401** |
| `POST /api/v1/machine/answers`（actor machine） | **401** |
| `POST /api/v1/machine/answers`（actor human） | **401** |
| `POST /api/v1/machine/answers`（无 actor 头） | **401** |

**所以 Rust Core 的鉴权是**两层**的：**

```
层一（启动）：launch_token 64位 + session_id 32位 + actor ∈ {None,human,machine}
   actor 非法 -> invalid launch actor，进程不启动
层二（每次请求）：必须携带启动凭据
   缺失或不匹配 -> 401 AAK-AUTH-001 invalid launch credentials
```

**两层都是 fail-closed，而且都在**活的进程**上得到了确认。**

**这也解释了为什么我此前对 Rust Core 的任何探测都不可能成功** —— 缺凭据。

## 5. Q03 的记账（显著前进）

| 项 | 状态 |
| --- | --- |
| **规范 Core 能被运行** | ✅ **首次 —— 用 stdin 启动文档** |
| **启动层身份校验** | ✅ **实测 `invalid launch actor`** |
| **请求层凭据校验** | ✅ **实测 `401 AAK-AUTH-001`** |
| **actor 的「human/machine」语义差异** | ⏳ **未测到** —— 要先知道请求怎么携带凭据 |
| **canonical 数据模型** | ⏳ **仍等你决定** |

## 6. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「actor 的 human/machine 差别已测」 | **所有请求都停在 401** —— **还没带上凭据** |
| 「Rust Core 与 Python 后端行为等价」 | **未比较** |

**下一轮**：只读地读 Rust Core 的鉴权中间件，看请求**怎么携带**凭据（哪个头、什么格式），
**然后就能测到 actor 的真实差别。**

## 7. 守住的两条边界（本轮尤其重要）

| 做法 | 理由 |
| --- | --- |
| **二进制从 Green 候选【复制】出来，在 scratch 目录运行** | Green 目录本身**零改动** —— 未创建/修改/删除任何文件 |
| **用 scratch 的 DB 路径与端口** | 不碰任何既有数据 |

**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；**未执行任何安装**。
