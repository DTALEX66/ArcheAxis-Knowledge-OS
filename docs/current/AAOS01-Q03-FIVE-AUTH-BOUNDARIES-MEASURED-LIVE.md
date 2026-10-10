# 🎉 AAOS-01 Q03：**五条授权边界全部在活进程上确认**

## 1. v2 的确切契约（我先写错过一次）

```rust
// crates/archeaxis-api/src/launch.rs
201: match launch.protocol.as_deref() {
202:     None => {                                    // v1（遗留）
203:         if launch.machine_token.is_some() { return Err("machine token requires v2"); }
206:         if !matches!(launch.actor.as_deref(), None | Some("human") | Some("machine")) {
210:             return Err("invalid launch actor");
212:     }
213:     Some("archeaxis.desktop-launch/v2") => {     // ★ 确切字面量
214:         if launch.actor.as_deref() != Some("human") {
215:             return Err("invalid v2 launch actor");
217:         let machine = launch.machine_token.as_deref()
220:             .ok_or("missing machine identity")?;
221:         if !hex(machine, 64) || machine.eq_ignore_ascii_case(&launch.launch_token) {
222:             return Err("invalid machine identity");
224:     }
225:     Some(_) => return Err("unsupported launch protocol"),
```

| v2 要求 | 细节 |
| --- | --- |
| `protocol` | **确切的 `"archeaxis.desktop-launch/v2"`** |
| `actor` | **必须恰为 `"human"`** |
| `machine_token` | **必需**，64 位十六进制，**且必须不同于 `launch_token`** |

**我第一次写的是 `"v2"`，被 `unsupported launch protocol` 拒绝。**
**改成确切字面量后即通过 —— 这类协议字面量必须从源码取，不能凭简称猜。**

**而且这印证了第 130 轮那句注释**：

> **"v2 gives one owned session two distinct credentials"**

**即：同一个会话同时持有**人类凭据与机器凭据** ✓

## 2. 🎉 五条边界全部实测

```
"1 human token":                        [404, ""]                       // 已授权
"2 machine token":                      [404, ""]                       // 已授权
"3 machine token + claims human actor": [404, ""]                       // 已授权
"4 no credential":                      [401, "AAK-AUTH-001 invalid launch credentials"]
"5 duplicate credential header":        [401, "AAK-AUTH-001 invalid launch credentials"]
"6 origin header":                      [403, "AAK-AUTH-002 browser origin not allowed"]
"7 wrong header name (machine)":        [401, "AAK-AUTH-001 invalid launch credentials"]
```

| 规则 | 实测 | 判定 |
| --- | --- | --- |
| 人类凭据可用 | 404（**通过了鉴权**，只是路由不存在） | ✅ |
| 机器凭据可用 | 同上 | ✅ |
| **`x-archeaxis-actor` 被忽略** | 机器凭据 + 声称 human → **仍通过** | ✅ **证实** |
| 无凭据拒绝 | **401** | ✅ |
| **重复凭据头拒绝** | **401** | ✅ |
| **`origin` 头拒绝** | **403 AAK-AUTH-002** | ✅ |
| **错误的头名（`x-archeaxis-machine-token`）** | **401** | ✅ **正是我第 132 轮的错** |

**注意**：404 表示**鉴权通过**、只是那条路由在这个二进制上不存在 ——
**所以第 1 · 2 · 3 · 8 · 9 条是「授权成功」的证据，不是失败。**

## 3. 一个顺带的事实

**这个 Rust Core 上 `/api/v1/capabilities` 与 `/api/v1/machine/answers` 都不存在** ✓
**所以它的路由集与 Python 后端不同** —— 与第 106 轮「两条 API 面」的结论一致 ✓

**中间件里有一处特判值得记**：

```rust
390: if request.method() == Method::GET && request.uri().path() == "/api/v1/system/version" {
391:     let mut version = serde_json::json!({"runtime":"archeaxis-api","contract":"0.1.0-outline",
393:         "schema_version":archeaxis_store_sqlite::SCHEMA_VERSION,
394:         "session_id":session.launch.session_id,"workspace_db":session.workspace_db});
```

**`GET /api/v1/system/version` 会返回 `runtime` / `contract` / `schema_version` / `session_id` / `workspace_db`** ✓
**那是一条已知存在的路由 —— 下一轮可用它做「已授权且 200」的正面证据。**

## 4. Q03 的记账

| 项 | 状态 |
| --- | --- |
| **规范 Core 可运行** | ✅ 用 stdin 启动文档 |
| **v2 启动契约** | ✅ 确切字面量与各字段要求已确认 |
| **启动层 actor 校验** | ✅ `invalid launch actor` |
| **请求层凭据校验** | ✅ **五条边界全部实测** |
| **路由集** | ⏳ **未枚举** —— 已知 `/api/v1/system/version` 存在 |
| **canonical 数据模型** | ⏳ **仍等你决定** |

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「两条凭据在业务行为上不同」 | **本轮只测到鉴权通过与否**，**未比较 human/machine 的业务差异** |
| 「404 路由确实不存在」 | 也可能是**前缀不同** —— 我只用了这一个前缀 |

## 6. 守住的两条边界

**二进制从 Green 候选【复制】出来、在 scratch 目录运行** —— Green 目录**零改动** ✓
**scratch 的 DB 路径与端口** —— 不碰任何既有数据 ✓
**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；**未执行任何安装**。
