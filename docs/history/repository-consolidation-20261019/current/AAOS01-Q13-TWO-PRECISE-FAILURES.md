# AAOS-01 Q13：**两条精确的故障记录；worker 仍未亲眼见到**

Q13 要三类记录：**性能 / 故障 / 进程树**。本轮取到**故障**，而且两条质量都很高 ——
**但我要先说清：worker 还是没看到。**

## 1. 我找对了入口

```rust
// crates/archeaxis-api/src/mod.rs:54
.route("/api/v1/machine/answers", post(machine_answer))
// crates/archeaxis-api/src/colearning.rs:93
.machine_answer(          <- 这里调用 executor
```

`POST /api/v1/machine/answers` **就是**通往 `executor.rs:168 .spawn()` 的那条路。

## 2. 故障记录一：**422，且错误信息写明该发什么**

我按 `colearning.rs:165` 把 `machine_answer` 当成输入字段发过去（**这是我的误读**）——
路由回了一个**教科书级的** 422：

```
Failed to deserialize the JSON body into the target type: machine_answer: unknown field
`machine_answer`, expected one of `knowledge_id`, `question`, `max_tokens`, `timeout_s`
at line 1 column 82
```

**它点名了我不该发的字段，并列出该发的四个字段。** 这是「故障信息可行动」的正面样本。

**我的误读**：`body.machine_answer` 是**另一个结构体**（`colearning.rs:371`）的字段，不是这条请求的输入。

## 3. 故障记录二：**404，且说明了领域前置条件**

改成正确字段后再发：

```
404  "no knowledge item probe-knowledge with an active accepted/personal body to answer from"
```

**这条路由要求先存在一个知识项，且它有「active accepted/personal body」才能作答。**

## 4. 所以 worker 为什么还是没出现（诚实的缺口）

**两次调用都在到达 executor 之前就被拒了** —— 422 卡在反序列化，404 卡在领域校验。

```
"distinct_children_observed": []   <- 仍然是空的
```

**第 57 轮那个缺口，本轮没有补上。** 源码说 worker 在 `machine_answer` 里派生，
而**我还没让任何一次调用真正走到那里**。

**要看到它，得先造出一个满足条件的知识项** —— 这是本轮学到的**管线顺序**。

## 5. 顺带补上的一个小字段

第 56 轮我预备了 `powershell_used` 却留成 `null`。本轮填上了：

```
"powershell_used": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
```

**即：`pwsh` 不在那个子进程的 PATH 上，回退到 Windows PowerShell 5.1 才取到进程树。**

## 6. 本轮未做

1. **未**造知识项，所以**未**真正走到 `machine_answer`；
2. **未**取性能记录（Q13 第三类）；
3. **未**改任何实现文件；**未**触碰官方 Green 与资料库。

## 7. 下一轮

**先造一个知识项**（`/api/v1/knowledge-items`）并让它成为可作答状态，**再发 machine answer** ——
那一次才可能看到 Core 的 Python 子进程。
