# AAOS-01 Q08：**学习面在这里是只读的，人类复习决定在 Core 侧且为人类专属**

## 1. BFF 暴露的学习路由

```
app/workspace/router.py:897   GET  /api/learning              <- 只读：学习状态
app/workspace/router.py:927   POST /api/knowledge/start-learning
app/workspace/router.py:937   POST /api/learning/practice
app/workspace/router.py:1004  POST /api/commands/start-learning
```

另有独立模块 `app/api/learning.py`。

**这个面是关于「开始学习」与「练习」的** —— 没有「人类批准一次复习」这个动作。

## 2. 人类复习决定在 Core 侧，且**人类专属**

`docs/CONFIGURATION_AUTHORITY_INDEX.md` 第 16 行（此前读到）写明：

> `/api/v1/learning/reviews` 从 Core 事件恢复完整 FSRS 状态，独立于旧 `/events` 收据契约；**只有 human 可写**，
> 状态由 Core 与 worker 产生，**默认 UI 接线仍需验收**。

**所以：我不以人类身份提交复习。** 这与 Q07 同一条纪律。

## 3. 本轮实际测的（只读，不需要任何身份）

在既有探针里加了 `GET /workspace/api/learning`，并加了两条测试：

| 测试 | 断言 |
| --- | --- |
| 学习面**只读可应答** | `learning_status` 已记录；200 时记录其 shapes |
| **没有任何复习被提交、也没有声称人类** | 回执里**不得出现** `reviewer` / `approved_by` / `human_review` |

第二条同样**断的是不存在**：**让「探针跑过」永远不会看起来像「发生过人类复习」。**

**结果**：10 passed，4.99 秒。

## 4. 我**没有**做的

1. **未**提交任何复习（人类专属）；
2. **未**调用 `start-learning` / `practice`（属写入面，且本轮先只读测量）；
3. **未改任何实现文件**；官方 Green 与资料库**零触碰**。

## 5. 下一轮

读 `app/api/learning.py`（独立学习路由器）与 Core 侧复习路由的**授权方式**，弄清：

- 「只有 human 可写」在代码里**怎么落实**（某一字段？某一令牌？某一路径？）；
- **如果能落实**，那 Q08 的人类环节就有结构性保证（与 Q07 的运行时候选路径同样漂亮）；
- 若**靠约定**，我就把它明确登记为**需要人自觉的边界**。
