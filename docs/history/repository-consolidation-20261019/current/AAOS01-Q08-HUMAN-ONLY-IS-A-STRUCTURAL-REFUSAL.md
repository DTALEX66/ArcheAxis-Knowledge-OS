# AAOS-01 Q08：**「只有 human 可写」是结构性拒绝，而且拒绝本身可测**

## 1. 找到了落实处（Rust Core）

```rust
// crates/archeaxis-api/src/lib.rs:731-743
async fn record_stateful_review(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<StatefulReviewBody>,
) -> impl IntoResponse {
    match request_actor(&headers) {
        Ok("human") => {}
        Ok(_) => {
            return (
                StatusCode::FORBIDDEN,
                "machine principal cannot record human reviews",
            )
                .into_response();
```

## 2. 它保证了什么

| 性质 | 实现 |
| --- | --- |
| **演员身份来自请求头** | `request_actor(&headers)` |
| **只允许 human** | `Ok("human") => {}` |
| **其它一律拒绝** | **`403 FORBIDDEN`**，且**消息点名原因**：`machine principal cannot record human reviews` |

**这比 Q07 的运行时候选路径更强一点**：那里是「根本没有这个字段」；这里是「**有这个入口，但明确拒绝机器**」——
**并且给出可引用的 403 与错误文案**。

## 3. 因此**拒绝可以被测量，而且不需要冒充任何人**

我可以**如实声明自己是机器主体**（那本来就是事实），然后**观察系统拒绝**：

```
期望：403 FORBIDDEN
期望文案：machine principal cannot record human reviews
```

> **这是我最想要的形态：不用假装成人，就能证明「假装不成人」这件事是真的。**

**下一轮就去取这条 403 的真实回执。**

## 4. 顺带记下 BFF 的学习面（`app/api/learning.py`）

```
GET  /mastery/{card_id} · GET /review-queue · GET /principles · GET /quiz
POST /teach-back · POST /distill · POST /trajectory · POST /tick
POST /learning-path · POST /review-outcome        <- 写操作，均需桌面写凭据
```

该模块还有 `_HUMAN_FIELDS = {"reviewed", "review_state", "stability_days", "bkt_mastery", ...}`
与 `_human_evidence(payload)` —— **「人类证据」是按字段白名单挑出来的**，
即：**调用方可以传这些字段，但它们被归为「人类证据」**。

**这一处我没有继续追**（谁校验这些字段确实来自人）—— **记为未查**，而不是当成已解决。

## 5. 本轮未做

1. **未**取那条 403 的真实回执（下一轮）；
2. **未**读 `request_actor` 的具体取值规则（从哪个头、允许哪些值）；
3. **未**追 `_human_evidence` 字段白名单的校验者；
4. **未改任何实现文件**；官方 Green 与资料库**零触碰**。
