# AAOS-01 Q13：**worker 何时派生 —— 第 56 轮的问题已由源码回答**

第 56 轮我看到「Core 就绪后没有子进程」，并**明确说我没证实原因**。本轮读源码，**答案是：按调用派生**。

## 1. 源码（三处，连起来就清楚了）

```rust
// crates/archeaxis-api/src/main.rs:213-228  启动时
let (store, router) = if let Some(profile) = &launch.text_worker {
    let extra = profile.extra_routes();
    match archeaxis_application::executor::Executor::open_routes(
        Path::new(db_path), &profile.staging, &profile.python, &profile.script, &extra_refs,
    ).await {
```

```rust
// crates/archeaxis-application/src/executor.rs
73:   pub async fn open_routes(...)          <- 只注册路由，【没有 spawn】
139:  pub async fn machine_answer(...)
153:      tokio::task::spawn_blocking(move || -> Result<serde_json::Value, String> {
159:      let mut command = Command::new(&python);
168:      .spawn()                          <- Python 进程【在这里】被派生
```

## 2. 所以机制是

| 时刻 | 发生什么 |
| --- | --- |
| **启动** | `open_routes` **只登记**「哪个能力由哪个脚本服务」 |
| **调用一次 machine answer** | **才**在 `machine_answer` 里 `Command::new(python).spawn()` |

> **Python worker 不是常驻进程，而是按调用派生。**

## 3. 这正好解释了第 56 轮的观察

第 56 轮：`children_of_core = []`（就绪后 3 秒）。

**当时我什么都没请求**，所以**没有任何 machine answer 调用**，也就**不会派生 worker** ✓。

**观察与机制一致** —— 而第 56 轮我只敢说「可能是按需」，现在**可以依据源码断言了**。

## 4. 这个方法上的分别，值得写明

| 来源 | 我能说什么 |
| --- | --- |
| **源码** | 「**是按调用派生的**」—— 可断言 |
| **一次运行** | 「**就绪后 3 秒没有子进程**」—— 只能记录 |

**第 56 轮我只有后者，本轮拿到了前者。** 这是同一条纪律的又一次应用：**源码事实可断言，一次运行的行为只能记录。**

## 5. 还差一块（诚实的缺口）

**我还没有真的看到那个 Python 子进程出现。**

源码说它会在 `machine_answer` 里派生，但我**没有触发过一次 machine answer 调用**，
所以**进程树里仍然没有那个 worker**。

**「它会派生」是源码事实；「我亲眼见它派生」还缺一次实测。** 两者我都写清楚，不混为一谈。

## 6. 本轮未做

1. **未**触发 machine answer 调用（下一轮）；
2. **未**取性能与故障记录（Q13 另两类）；
3. **未**改任何实现文件；**未**触碰官方 Green 与资料库。

## 7. 下一轮

找一个会走到 `machine_answer` 的路由（例如导入或机器任务），**触发一次**，
**在调用期间**快照进程树 —— 期望看到 **Core 的 Python 子进程**，命令行指向 `services/python-workers/...`。
