# 🎯 AAOS-01 Q03：**完整的凭据模型 —— 并更正我在第 132 轮用错的头**

## 1. 唯一凭据头

```rust
// crates/archeaxis-api/src/launch.rs
349: async fn authenticate(State(session): State<Session>, request: Request, next: Next) -> Response {
350:     let values = request.headers().get_all("x-archeaxis-launch-token");   // ★ 唯一
352:     let value = values.next().map(|v| v.as_bytes()).unwrap_or_default();
353:     let expected = session.launch.launch_token.as_bytes();
354:     let matches = |expected: &[u8]| {
355:         value.len() == expected.len()
358:                 .fold(0u8, |diff, (a, b)| diff | (a ^ b)) == 0      // 常数时间比较
362:     let primary = matches(expected);
363:     let machine = session.launch.machine_token.as_ref()
367:         .map(|token| matches(token.as_bytes())).unwrap_or(false);
369:     if !(primary || machine) || values.next().is_some() {           // ★ 重复头也 401
370:         return error(StatusCode::UNAUTHORIZED, "AAK-AUTH-001", "invalid launch credentials");
375:     }
376:     let actor = if machine || session.launch.actor.as_deref() == Some("machine") {
377:         "machine"
378:     } else {
379:         "human"
380:     };
```

## 2. 🎯 而测试文件把两个「容易搞错」的点写在了抬头

```
// crates/archeaxis-api/tests/contract_auth_boundaries.rs
1: //! The §2 authentication boundaries, pinned against the real binary.
3: //! Every line of the contract's credential model was exercised against a live Core before being
4: //! asserted here, and two findings are the kind a client gets wrong:
6: //! * both principals use the same header. The machine token travels in
7: //!   `x-archeaxis-launch-token`; there is no machine header. A client that sends the machine
8: //!   token under `x-archeaxis-machine-token` - a name this protocol has never read, and the name
9: //!   the launcher itself wrongly used once - gets `401`, not a machine request.
10: //! * the actor comes from which token matched, not from the request, so a machine token that
11: //!   also claims `x-archeaxis-actor: human` still succeeds as a machine.
```

**两点都直击我的错误**：

| 规则 | 我在第 132 轮做的事 |
| --- | --- |
| **两个主体都用 `x-archeaxis-launch-token`** | ❌ 我发了 **`x-archeaxis-machine-token`** —— **一个协议从不读取的头** |
| **actor 由「哪个 token 匹配」决定，不由请求头决定** | ⚠️ 我还在发 `x-archeaxis-actor` —— **它被忽略** |

**所以第 132 轮那三个 401 的根因找到了：头名错了。**
**而这份测试的抬头甚至说这个错误名字「the launcher itself wrongly used once」——
项目自己记录过同一个坑。**

## 3. 顺带一条安全设计（值得记）

```rust
381:     // Formal desktop is a native client. Do not allow browser origins to turn
382:     // this localhost API into a credentialed cross-origin write surface.
383:     if request.headers().contains_key("origin") {
384:         return error(StatusCode::FORBIDDEN, "AAK-AUTH-002", "browser origin not allowed");
385:     }
```

**带 `origin` 头 → 403 `AAK-AUTH-002`** ✓ —— **显式的反 CSRF 措施** ✓
**注释写明了意图**：**不让浏览器来源把本机 API 变成一个「带凭据的跨源写入面」。** ✓

## 4. 于是完整的凭据模型

```
启动（stdin JSON）：
   launch_token  64 位十六进制   -> 人类凭据
   machine_token 64 位十六进制   -> 机器凭据（可选，需 protocol 声明 v2）
   session_id    32 位十六进制
   actor         可选

请求（HTTP 头）：
   x-archeaxis-launch-token: <人类凭据 或 机器凭据>     // 【唯一】凭据头，且【不得重复】
   origin: <任意>                                      // 出现即 403 AAK-AUTH-002

actor 判定：
   machine_token 匹配 或 启动 actor == "machine"  -> "machine"
   否则                                             -> "human"
   （请求头 x-archeaxis-actor 被忽略）
```

## 5. 因此下一轮**可以**测到 actor 的真实差别

```
启动文档含 launch_token=<A> 与 machine_token=<B>
  -> 用 A 发请求  => actor 应为 human
  -> 用 B 发请求  => actor 应为 machine
  -> 再用 B 发请求但附 x-archeaxis-actor: human => 仍应为 machine（证明头被忽略）
  -> 附 origin 头 => 应 403 AAK-AUTH-002
  -> 同一头发两次 => 应 401
```

**这五条正好对应那份测试文件钉住的边界。**

## 6. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「已测到 actor 差别」 | **仍未跑那五条** |
| 「`machine/answers` 的 human/machine 行为差别」 | **未测** |

## 7. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（grep + 读文件）。
**未改任何仓库文件**；**Green 目录内未创建/修改/删除任何文件**；**未触碰官方 Green 的 `data/` 与资料库**。
