# AAOS-01 Q08：**403 拿到了 —— 人类专属两侧都有实测**

## 1. 机制（第 49 轮读全）

身份**不是**由请求头决定，而是**由匹配到哪一个凭据决定**：

```rust
// crates/archeaxis-api/src/launch.rs:376-380
let actor = if machine || session.launch.actor.as_deref() == Some("machine") {
    "machine"
} else {
    "human"
};
```

```rust
// crates/archeaxis-api/src/launch.rs:400-410
// Overwrite self-reported identity with the role of the matched bootstrap
// credential, including for machine requests to the same human-owned Core.
parts.headers.insert("x-archeaxis-actor", ... if actor == "machine" { "machine" } else { "human" });
```

**legacy 启动允许声明 `actor: "machine"`**（`launch.rs:206-211`）；
**v2 则要求 launch actor 必须是 human**，机器身份另由 **`machine_token`** 提供（`launch.rs:213-221`）。

## 2. 两侧实测（同一路由 `/api/v1/learning/reviews`）

| 会话 | 我发的头 | 结果 | 轮次 |
| --- | --- | --- | --- |
| **human**（launch 未声明 actor） | `machine` | **201**，记录了一条复习 | 第 47 轮 |
| **machine**（launch 声明 `actor: "machine"`） | `machine` | **403**，`machine principal cannot record human reviews` | **本轮** |

**同一路由、同一种头、不同会话 → 不同结果。** 这正是机制说明的行为：

> **客户端自报的身份被覆写；说了算的是启动会话。**

## 3. 所以 Q08「人类专属」的结论是完整的

| 结论 | 证据 |
| --- | --- |
| 人类会话**可以**记录复习 | 201（第 47 轮） |
| **机器会话被明确拒绝** | **403 + 具名原因**（本轮） |
| 客户端**无法**通过头部提权 | 我发 `machine` 却被当成 human（第 47 轮）；反之亦然 |
| 身份在**启动时**确定 | `launch.rs:376` + 覆写逻辑 |

## 4. 我**自己**在这一轮拦下了一件事（值得记）

我第一版脚本里，**请求头写的是 `x-archeaxis-actor: human`** —— 想用「被覆写」来证明机制。

**我把它改掉了**：**即使是为了测试一次拒绝，我也不发出虚假的人类声明。** 改成如实写 `machine`。

**结果 403 照样拿到** —— 说明**那句假声明对结论毫无必要**。
**这条比结论本身更值得记：我不需要在测试里越线，也能拿到证据。**

（顺带：该脚本第一版还漏给 `/api/v1/system/version` 带 launch token，得到 401；那是我的错，已修。）

## 5. 本轮未查

1. `schema_version` 在 Core 的 version 里是 **9**，而 Python 握手报的是 **1** —— **两个来源口径不同，我未追**；
2. `machine_token`（v2 路径）我**未**实测；
3. **未改任何实现文件**；官方 Green 与资料库**零触碰**；
4. 探针临时库**已自清理**，无残留复习。
