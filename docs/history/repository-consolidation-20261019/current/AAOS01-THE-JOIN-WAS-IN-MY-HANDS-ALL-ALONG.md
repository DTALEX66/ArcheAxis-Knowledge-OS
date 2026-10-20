# 🎯🎯 AAOS-01：**那张「表」找到了 —— 它一直在我手里**

## 1. 字段确认

```rust
// crates/archeaxis-api/src/launch.rs
58: pub struct WorkerRoute {
59:     pub capability: String,
60:     pub script: std::path::PathBuf,
61: }
```

**`WorkerRoute = { capability, script }`** —— **能力名 → 实现脚本**。

**这正是第 79 轮我描述的那个「缺失的连接」**：

> 「**能力与实现之间真正的对应关系** —— 而它现在没有权威来源。」

**它有权威来源，就是这里。**

## 2. 完整链条（现在没有缺口了）

```
Launch {
    launch_token: <64 hex>,
    session_id:   <32 hex>,
    actor:        Option<"human"|"machine">,
    text_worker:  Option<TextWorker {
        python, script, staging,
        routes: Vec<WorkerRoute { capability, script }>   // ★ 那张表
    }>,
    protocol, machine_token,
}
```

**`routes` 就是「能力 ↔ 实现」的逐一对应**，**由启动者声明**。

## 3. 🎯 而实例**一直在我手里**

老 Green 候选的 `worker-profile.json` 就是一个实例 —— 我早早读过它：

```
{"schema": "archeaxis.worker-profile/v1",
 "python": "runtime/python.exe",
 "script": "workers/transport/text_ndjson.py",
 "routes": [
   {"capability": "archive.inventory", "script": "workers/document/worker_archive.py"},
   {"capability": "canvas.structure",  "script": "worker_canvas.py"},
   … 共 11 条 …
 ]}
```

**`{capability, script}` 对** —— **与 `WorkerRoute` 结构逐字段对应** ✓✓

**所以第 79 轮我说「找不到」，是因为我在找一份**签入仓库的 mapping 文件**；
而它是一个**运行时分发产物**，通常叫作 `worker-profile.json`。**

## 4. 三次追问的合流

| 轮次 | 我的问题 | 答案 |
| --- | --- | --- |
| **59** | `machine.answer` 为何 503 | **我的启动只声明了默认的 `text.extract`** |
| **79** | 能力↔路由的映射在哪 | **在启动文档的 `text_worker.routes`** |
| **129** | 为何仓库里没有它 | **`stage_backend_runtime.py` 在分发时生成 `worker-profile.json`** |
| **131（本轮）** | `WorkerRoute` 到底是什么 | **`{capability, script}` —— 一字不差就是那张表** |

**三次追问合流到同一个答案，而且这个答案在三处独立来源上自洽**：
**Core 的结构定义 · 分发脚本的生成逻辑 · 老 Green 的实物 profile。**

## 5. 我要更正第 80 轮草案的定位

第 80 轮我起草过一份「能力↔路由映射」的草案，并标注「**缺权威来源**」。

**现在看，那份草案的问题是**方向错了**：**

| 我当时的做法 | 正确理解 |
| --- | --- |
| 试图在**仓库里**新建一份映射文件 | **映射是**运行时分发产物**（`worker-profile.json`），不是签入文件** |
| 用**名称相似**去猜 `CAP-00x0` ↔ 路由 | **对应关系由启动者显式声明**（`{capability, script}`），不需要猜 |

**所以那份草案不该被采纳为权威文件** —— **它想固化的东西，本来就该由分发时生成。**
**我把它留在 `docs/current/` 作历史记录，并在此更正其定位。**

## 6. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「Core 一定能起来」 | **仍未启动过** |
| 「`worker-profile.json` 与 atlas 的 CAP-00x0 可直接互译」 | **未验证** —— 两侧命名体系不同（第 79 轮已记） |

## 7. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（grep + 读文件）。
**未改任何仓库文件**；**Green 目录内未创建/修改/删除任何文件**；**未触碰官方 Green 的 `data/` 与资料库**。
