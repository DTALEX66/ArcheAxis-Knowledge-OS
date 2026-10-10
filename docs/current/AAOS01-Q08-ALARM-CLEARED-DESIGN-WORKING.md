# AAOS-01 Q08：**第 47 轮的警报解除 —— 那是设计在生效，不是绕过**

第 47 轮我如实记录了一次「未拦住」的观察，并把它列为**未判定**。本轮**查明机制，结论反过来**。

## 1. 启动声明**有** actor 字段，而我的没有设

```rust
// crates/archeaxis-api/src/launch.rs
20:    pub actor: Option<String>,
```

## 2. 启动中间件**把该头盖章式写入**

```rust
// crates/archeaxis-api/src/launch.rs:376, 404-405
376:    let actor = if machine || session.launch.actor.as_deref() == Some("machine") {
404:        "x-archeaxis-actor",
405:        axum::http::header::HeaderValue::from_static(if actor == "machine" { ... } else { ... })
```

**中间件根据会话的 actor**写这个头 —— 所以**客户端的头会被覆写**，正是 docstring 说的
「so a client cannot escalate」。

## 3. 于是第 47 轮的 201 **是正确结果**

| 环节 | 值 |
| --- | --- |
| 我的 launch JSON | **没有 `actor` 字段** → `None` |
| 会话 actor | **human**（`None` 走默认） |
| 中间件盖章 | `x-archeaxis-actor: human`，**覆写我发的 `machine`** |
| 守卫看到 | **human** → 放行 |
| 结果 | **201，记录了一条复习** |

> **系统完全按设计工作：谁启动 Core，就声明了这个 Core 是什么。**

**所以第 47 轮那个「没拦住」不是缺陷、不是绕过** —— 是我**用了 human 会话**去发请求。

## 4. 我第 47 轮的错在哪（诚实归因）

我当时**假设**：请求头上的 `machine` 是权威的。
**实际是**：请求头**不是**权威 —— **启动声明才是**，中间件会用会话身份把它盖掉。

**我把「我声明了什么」当成了「系统认为我是什么」。** 这正是 docstring 明确警告的那件事。

## 5. 但**留下一条真结论**（重要，不是警报）

> **保护发生在启动时刻，不在每个请求上。**

| 含义 | 说明 |
| --- | --- |
| **不声明 actor 的 Core = human 会话** | 于是它可以记录人类复习 |
| **要拿到 403** | 必须**用声明 machine 的会话**启动 |
| **客户端无法自行提权** | 这一点成立，且是**强**保证 |

**这不是漏洞 —— 是「启动者即授权者」的模型。** 但它意味着：**谁能启动那个进程，谁就决定了它代表谁。**

## 6. 因此 403 是可以拿到的 —— 但要用 machine 会话

我第 47 轮用的是**无 actor 的会话**，所以永远拿不到 403。**下一轮**：
**以声明 machine 的会话启动 Core**，再发同样的请求 —— **预期这次真的 403**。
**这不是伪装：machine 会话本就该被拒绝写人类复习。**

## 7. 本轮未查

1. **未**核 `launch.rs:376` 的 `machine` 布尔量**从哪来**；
2. **未**核 v2 启动对 actor 的校验（`launch.rs:214-215` 有 `invalid v2 launch actor`）；
3. **未**用 machine 会话重跑（下一轮）；
4. **未改任何实现文件**；官方 Green 与资料库**零触碰**。
