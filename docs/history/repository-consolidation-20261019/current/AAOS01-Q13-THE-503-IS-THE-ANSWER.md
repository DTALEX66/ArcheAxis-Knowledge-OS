# AAOS-01 Q13：**503 给出了确定答案 —— worker 不在那条路上**

追了四轮（56–59）的那件事，本轮**有了确定的答案**：**不是「暂时没看到」，而是「这条路上根本不会派生」**。

## 1. 本轮的三步与三个结果

| 步 | 我做的 | 结果 |
| --- | --- | --- |
| 1 | `knowledge_type: "concept"` | **400** `unknown knowledge_type: concept` |
| 2 | 查到合法值是大写，改 `PERSONAL_DEFINITION` | **201** ✅ 真知识项 `k_6e7f685c91afddd254d4ee0c` |
| 3 | 用这个 id 发 machine answer | **503** **`no worker is registered for machine.answer`** |

## 2. 那个 503 就是答案

```
503  no worker is registered for machine.answer
```

对照源码（第 57 轮读到的）：

```rust
// crates/archeaxis-application/src/executor.rs:91
vec![("text.extract".to_string(), default_worker.to_owned(), false)]
// executor.rs:168  .spawn()   <- 只会在「有注册 worker 的能力」上发生
```

**默认注册的能力是 `text.extract`，而 `machine.answer` 没有注册 worker。**

> **所以 `machine/answers` 这条路**永远不会**派生 Python worker —— 与我看不看、看多久无关。**

**这解释了第 56–58 轮的全部观察**，而且不是「没抓到」，是「不会发生」。

## 3. 因此 worker 该在哪里看

**在 `text.extract` 那条路上** —— 即**导入 / 提取**（`/api/v1/imports` → `/api/v1/jobs`），
而不是 machine answer。**下一轮改走那条路。**

（我上一轮说「先造知识项再问」是**对的方向、错的路**：知识项确实需要，但那条路由本身没有 worker。）

## 4. Q13 的「故障」这一类，现在很充实

| 状态码 | 信息 | 质量 |
| --- | --- | --- |
| **422** | 点名不该发的字段 + **列出该发的四个** | 极好 |
| **400** | `unknown knowledge_type: concept` | 尚可（**未列出合法值**） |
| **404** | `no knowledge item … with an active accepted/personal body` | 好（说明领域前置） |
| **503** | `no worker is registered for machine.answer` | **极好**（点名缺什么能力） |

**四条都指向可行动的原因**，三条直接告诉你要做什么。**这本身是 Q13 想要的「故障记录」。**

## 5. 顺带）一行值得记的观察

```rust
// lib.rs:1388 struct KnowledgeBody { ... created_by: String, ... }
// 但同一处理器上方注释：
// C02: actor comes from the trusted header (set by the launch middleware
// from the launch-session claim), never from the request body.
```

**结构体里有一个 `created_by` 字段，而代码注释明确说身份不来自请求体。**
**即：字段存在，但不被信任。** 这与第 46 轮 actor 头被覆写是同一类设计。

## 6. 性能（Q13 第一类，起步）

| 操作 | 耗时 |
| --- | --- |
| 就绪（第 56 轮） | **0.02 秒** |
| 建知识项 | ~0.02 秒 |
| machine answer（被拒） | **0.01 秒** |

**注意：被拒的耗时只反映拒绝路径，不代表真实作答耗时** —— 我不拿它充当性能数据。

## 7. 仍未达成

**我依然没有亲眼看到那个 Python 子进程。** 但现在**知道了它不会在这条路上出现**，
并**知道了该去哪条路**（`text.extract` / 导入）。
**「为什么看不到」已完全回答；「看到」仍欠一次实测。**

## 8. 本轮未做

1. **未**走导入/提取那条路（下一轮）；
2. **未**改任何实现文件；**未**触碰官方 Green 与资料库。
