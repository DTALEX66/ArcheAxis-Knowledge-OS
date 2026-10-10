# 🎯 AAOS-01 Q03：**权限契约的权威依据 —— Rust Core 从 stdin 读启动身份**

## 1. 我为什么找不到它的输入

我按用法行 `archeaxis-api <workspace-db-path> [port]` 运行，得到 `invalid launch input`。
**去源码找抛出点，答案清楚了**：**启动身份**不走命令行，**走 stdin 的一份 JSON**。

```rust
// crates/archeaxis-api/src/launch.rs
170: impl Launch {
171:     pub fn from_stdin() -> Result<Self, &'static str> {
172:         // A std thread (not the async blocking pool) lets main exit on a parent
173:         // that holds stdin open. Never include input or parse details in errors.
177:             std::io::stdin().take(MAX_LAUNCH_BYTES as u64 + 1).read_to_end(&mut bytes);
182:         let bytes = receive.recv_timeout(Duration::from_secs(5))
184:             .map_err(|_| "launch input timed out")?
185:             .map_err(|_| "launch input failed")?;
186:         if bytes.len() > MAX_LAUNCH_BYTES { return Err("launch input exceeds limit"); }
191:         if std::str::from_utf8(&bytes).is_err() { return Err("launch input is not utf-8"); }
194:         let mut launch: Self =
195:             serde_json::from_slice(&bytes).map_err(|_| "invalid launch input")?;
196:         if !hex(&launch.launch_token, 64) || !hex(&launch.session_id, 32) {
197:             return Err("invalid launch identity");
198:         }
199:         // Legacy preserves its single actor; v2 gives one owned session two
200:         // distinct credentials. Unknown/null/partial v2 claims never downgrade.
201:         match launch.protocol.as_deref() {
202:             None => {
203:                 if launch.machine_token.is_some() { return Err("machine token requires v2"); }
206:                 if !matches!(launch.actor.as_deref(), None | Some("human") | Some("machine")
```

## 2. 🎯 这就是 Q03「权限」的**权威契约**

| 规则 | 源码依据 |
| --- | --- |
| **启动身份从 stdin 的 JSON 来** | 第 171 · 194 行 |
| **`launch_token` 必须 64 位十六进制** | 第 196 行 |
| **`session_id` 必须 32 位十六进制** | 第 196 行 |
| **`actor` 只能是 `None` / `"human"` / `"machine"`** | 第 206 行 —— **与我在第 104 轮读到的完全一致** |
| **`machine_token` 必须走 v2 协议** | 第 203 行 |
| **「未知/空/部分 v2 声明永不降级」** | 第 200 行注释 —— **一条 fail-closed 的身份规则** |

**所以第 104 轮我从 `lib.rs` 读到的 actor 规则，本轮在**启动层**得到了独立印证** ✓
**两层一致：启动时校验身份，请求时再校验 actor。**

## 3. 它的安全设计值得记一笔

| 设计 | 源码 |
| --- | --- |
| **错误信息不含输入或解析细节** | 第 173 行注释 |
| **读取有上限**（`MAX_LAUNCH_BYTES`） | 第 177 · 186 行 |
| **超时**（5 秒） | 第 182-184 行 |
| **拒绝非 UTF-8** | 第 191 行 |
| **用独立线程读 stdin**，好让持有 stdin 的父进程退出时本进程也能退出 | 第 172 行注释 |

**这是一套把「不泄露、不失控、不降级」都考虑到的输入处理。**

## 4. 所以下一轮我**可以**让它真正启动

```
往它的 stdin 写一份 JSON，含：
  launch_token = 64 位十六进制
  session_id   = 32 位十六进制
  actor        = "human" 或 "machine" 或省略
且不设 machine_token（或设时声明 v2）
  -> 它应当起来，然后我就能实测 /api/v1/machine/answers 的 actor 行为
```

**注意**：这需要**构造一份合法的启动身份** —— 但那是**它自己的协议**，
**不是绕过授权**：我给的是它要求我给的凭据格式，且全部在**我的 scratch 数据根**上。

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「Q03 已测」 | **进程还没起来** —— 本轮只读到了契约 |
| 「构造 stdin 后一定能起」 | **未试** |

## 6. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（grep + 读一个文件）。
**未改任何仓库文件**；**Green 目录内未创建/修改/删除任何文件**；
**未触碰官方 Green 的 `data/` 与资料库**；**未执行任何安装**。
