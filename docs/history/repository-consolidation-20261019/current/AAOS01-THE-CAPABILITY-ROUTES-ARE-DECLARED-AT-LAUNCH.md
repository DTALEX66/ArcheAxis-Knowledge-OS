# 🎯 AAOS-01：**能力↔路由的「连接」找到了 —— 它在启动文档里**

## 1. 我把第 79 轮的问题追到了源头

第 79 轮我搜遍 atlas 与 capability-map，找不到「能力 ↔ 路由」的映射，结论是「缺一张表」。
第 129 轮发现 `worker-profile.json` 在**分发时生成**。
**本轮在 Core 的启动结构里找到了它的**权威定义**：**

```rust
// crates/archeaxis-api/src/launch.rs
14: #[derive(Clone, Deserialize)]
15: #[serde(deny_unknown_fields)]
16: pub struct Launch {
17:     launch_token: String,
18:     session_id: String,
20:     pub actor: Option<String>,
21:     pub text_worker: Option<TextWorker>,
23:     protocol: Option<String>,
25:     machine_token: Option<String>,
26: }
...
30: #[derive(Clone, Deserialize)]
31: #[serde(deny_unknown_fields)]
32: pub struct TextWorker {
33:     pub python: std::path::PathBuf,
34:     pub script: std::path::PathBuf,
35:     pub staging: std::path::PathBuf,
36:     /// Additional capability routes, declared by whoever built the launch.
38:     /// The default `script` serves `text.extract`. Each entry here registers one
39:     /// more capability against the worker that implements it, so a PDF or OCR job
40:     /// reaches its own engine. The list is declared rather than guessed: the Core
41:     /// does not assume a checkout layout, and an absent list keeps the previous
42:     /// single-route behaviour exactly.
43:     #[serde(default)]
44:     pub routes: Vec<WorkerRoute>,
```

## 2. 🎯 所以那张「表」在哪

| 我此前的寻找 | 实际 |
| --- | --- |
| 在 atlas 里找 capability → route | ❌ 不在那里 |
| 在 `capability-map.v1.json` 里找 | ❌ 它只指向 atlas |
| 在仓库里找一份 mapping 文件 | ❌ 不存在 |
| **在启动文档的 `text_worker.routes` 里** | ✅ **就是这里** |

**源码注释自己说明了这个设计**：

> **"The list is declared rather than guessed: the Core does not assume a checkout layout,
> and an absent list keeps the previous single-route behaviour exactly."**

**即：Core**故意不假设**仓库布局 —— 路由由启动它的人**声明**。**

## 3. 🎯 于是第 59 轮那个 503 也有了确切解释

第 59 轮我实测 `POST /api/v1/machine/answers` 返回
**503 `no worker is registered for machine.answer`**，当时我写在报告里的结论是**错的**，
后来更正为「是我的启动只声明了 `text.extract`」。

**本轮拿到了它的机制依据**：

```
The default `script` serves `text.extract`. Each entry here registers one more
capability against the worker that implements it, so a PDF or OCR job reaches its own engine.
```

**默认只注册 `text.extract`** ✓ → **`machine.answer` 没有声明 → 503 是正确的** ✓✓

**与老 Green 候选的 `worker-profile.json` 有 11 条路由完全对得上** ✓
（注释里还提到一份 **13 条路由**的 profile 实测过体积 ✓）

## 4. 顺带一条工程细节（值得记）

```rust
45:     /// One directory the other paths may be written relative to.
47:     /// A launch that names every worker absolutely pays for the install prefix on every route: a
48:     /// thirteen-route profile measured 2741 bytes from a short root and 4405 from a deep one.
49:     /// One declared root plus relative paths keeps the document small however deep the install sits.
50:     /// Absolute paths are unchanged, and a relative path with no root is refused rather than guessed.
52:     pub root: Option<std::path::PathBuf>,
```

**它为一个「文档体积」问题写了实测数据（2741 vs 4405 字节），并给出设计**：
**一个声明的 root + 相对路径**；**绝对路径不变**；**没有 root 的相对路径被拒绝而不是猜** ✓

**这与 `resolve_runtime_path` 那条「不猜」的原则一脉相承。**

## 5. 因此现在**可以**让它真正起来

启动文档需要且只需要这些字段（`deny_unknown_fields` 会把多余的字段判为非法）：

```json
{
  "launch_token": "<64 位十六进制>",
  "session_id":   "<32 位十六进制>",
  "actor":        "human"            // 或 "machine" / 省略
  // 可选: "text_worker": {"python": "...", "script": "...", "staging": "...", "routes": [...]}
}
```

**下一轮就能用它实测 `machine/answers` 的 actor 行为 —— 那才是 Q03 的实测。**

## 6. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「Q03 已测」 | **进程仍未起来** |
| 「`WorkerRoute` 的字段已确认」 | **本轮只在注释层读到它**，**未读其定义** |

## 7. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（grep + 读一个文件）。
**未改任何仓库文件**；**Green 目录内未创建/修改/删除任何文件**；**未触碰官方 Green 的 `data/` 与资料库**。
