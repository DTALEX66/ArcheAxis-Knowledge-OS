# AAOS-01 Q08：**我没能证明那个 403 —— 反而记录下了一次被接受的复习**

**这是本轮最重要、也最不舒服的发现。我原样写出。**

## 1. 我做了什么

为了**如实验证**「人类专属」，我先**重建 Core**（确认与所读源码一致），
然后对 `/api/v1/learning/reviews` **显式声明 `x-archeaxis-actor: machine`** 发了一次请求 ——
**如实声明我是机器主体，期望看到 403。**

## 2. 实际结果

```
"machine_actor_status": 201        <- 期望 403，实际 201
"machine_actor_refused_with_403": false
"machine_actor_message_names_the_reason": false
"unknown_actor_status": 200        <- 连 actor: "robot" 也被接受（重复回放）
```

返回体里是**一条被记录下来的复习**：`event_id: 1`、`mastery_projection.attempts: 1`、
`correct_streak: 1`、`last_correct_at: 2026-10-04 13:23:34`、`basis: fsrs_review_state_and_learner_observation`。

> **我想要的是「证明系统会拒绝」。我得到的是「系统接受了，并写下了记录」。**

## 3. 影响范围（先把边界说清）

- 这次写入落在 **`.project-local/runs/actor-refusal` 的临时库**，**不是 canonical 库**；
- 我**没有**声明自己是人（声明的是 `machine`）；
- **该临时库已删除**，不留残留；
- 官方 Green、官方资料库**零触碰**。

**但事实仍然是：一次未获人类身份的请求，被系统当成可写并记录了一条复习。**

## 4. 为什么会这样（两个候选解释，我不判定）

源码 docstring 写着（第 46 轮引用过）：

> Production requests go through **the launch middleware which OVERWRITES this header**
> with the launch-session claim (C02), **so a client cannot escalate**.

| 候选解释 | 与观察是否相符 |
| --- | --- |
| **(A) 启动中间件把我的 `machine` 覆写成了会话声明的 actor**（很可能是 human），于是守卫看到 human 就放行 | **高度相符** —— 这**正是** docstring 描述的行为，只是方向对我不利 |
| (B) 我打的这条路由并非那个带守卫的处理器 | 未核 |

**若 (A) 成立**，结论难看但重要：

> **在这条启动路径上，调用方既不能自报 machine（会被覆写），而会话身份默认就是 human ——**
> **于是「人类专属」实际由启动会话的身份决定，而不是由每个请求的头决定。**

**我第 46 轮说「两半缺一不可」—— 本轮观察到的行为与那个模型相符，但后果比我当时写的更严重：被接受，而不是被拒绝。**

## 5. 我**不**声称的

1. **不声称**已查明机制 —— (A)/(B) 我**没有判定**；
2. **不声称**这是产品缺陷 —— 也可能**启动会话本就声明为 human**（我的 launch JSON 没有声明 actor，于是走 `None` 默认）；
3. **不声称**第 45/46 轮引用的 403 代码不存在 —— 它存在；**是本条路径上它没有生效**。

## 6. 下一轮（必须先做）

1. **查明启动声明里是否有 actor 字段**（若有，我那份 launch JSON **没有设它** → 默认 human）；
2. **查明启动中间件是否/如何覆写**该头；
3. 查清之后才能对「人类专属」给准确结论 —— 在那之前，本轮证据只说明 **「按我这种启动方式，它没有拦住」**。
