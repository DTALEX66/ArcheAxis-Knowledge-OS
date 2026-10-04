# AAOS-01 Q08：**「人类专属」的落实有两半，而且默认值方向要看清**

第 45 轮我引用了 Core 的 403 拒绝。本轮**读了 `request_actor` 本身**，发现必须补上两点。

## 1. 原文（`crates/archeaxis-api/src/lib.rs:32-45`）

```rust
/// Resolve the trusted actor for a request. Production requests go through
/// the launch middleware which OVERWRITES this header with the launch-session
/// claim (C02), so a client cannot escalate. In-process projections default to
/// human when the header is absent.
pub(crate) fn request_actor(headers: &HeaderMap) -> Result<&'static str, StatusCode> {
    match headers.get("x-archeaxis-actor").and_then(|v| v.to_str().ok()) {
        Some("machine") => Ok("machine"),
        Some("human") | None => Ok("human"),
        Some(_) => Err(StatusCode::BAD_REQUEST),
    }
}
```

## 2. 两点必须看清（第 45 轮我没写）

### (a) 头缺席时默认是 human

```rust
Some("human") | None => Ok("human")
```

**没有该头 → 被当作 human。** 所以「只有 human 可写」**不是靠这个头把机器挡在外面** ——
一个不带头、或声明 human 的调用方，**都会被当成人类**。

### (b) 真正的保护是启动中间件覆写该头

docstring 明写：

> Production requests go through **the launch middleware which OVERWRITES this header** with the
> launch-session claim (C02), **so a client cannot escalate**.

| 组成 | 作用 |
| --- | --- |
| `request_actor` 的头检查 | 声明 `machine` 即被 403 拒绝 |
| 启动中间件覆写 | **防止调用方把 actor 声明成 human 来提权** |

**两者缺一不可**：只有前者，调用方只要不传头就是 human；有了后者，客户端**无法自行声明身份**。

## 3. 这**修正**了第 45 轮的说法

第 45 轮我写「这比 Q07 更强：有入口但明确拒绝机器」。**方向对，但不完整。** 准确说法是：

> 接口拒绝自报机器的调用方；而自报人类或不报的调用方之所以不能被信，靠的是**启动中间件的覆写**。

**我上一轮把这条安全性质说得比证据更强，在此更正。**

## 4. 对下一步（取 403 回执）的影响

要取到 403，我必须**显式声明 `x-archeaxis-actor: machine`** —— 这是**如实声明**（我就是机器主体）。

| 场景 | 期望 |
| --- | --- |
| 带头 machine | **403 FORBIDDEN**（与中间件无关） |
| 不带头 | **被当作 human** —— 这正是中间件要防的事 |

**所以取 403 回执是安全且诚实的；但我绝不用不带头的方式去试写人类复习** ——
那是在**利用中间件缺失**，不是在**验证保护**。

## 5. 本轮未做

1. **未**取 403 回执（下一轮，只带 `machine` 头）；
2. **未**核启动中间件在**直接起 Core**时是否安装 —— **很关键，记为未查**；
3. **未改任何实现文件**；官方 Green 与资料库**零触碰**。
