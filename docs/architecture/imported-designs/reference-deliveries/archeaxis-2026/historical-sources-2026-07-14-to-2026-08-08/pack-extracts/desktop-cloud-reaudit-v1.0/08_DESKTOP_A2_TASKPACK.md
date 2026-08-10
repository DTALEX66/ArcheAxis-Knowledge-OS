# TaskPack AXDESK-A2：知行 Agent 任务驾驶舱

## 风险

高风险：涉及公开任务投影、任务状态、动作能力与审计边界。

必须独立分支、独立完整门禁、独立 reviewer、exact-SHA CI。

## 前置条件

- A1 已合并；
- 当前主分支 Green；
- Evaluation/Lesson 语义债务至少已有明确合同；
- 后端确认公开 task ref 方案；
- 不暴露内部 ID。

## 目标

构建真实任务驾驶舱：

- 任务列表；
- 任务摘要；
- 时间线；
- Inspector；
- Artifact；
- 可用动作；
- Retry；
- Delivery；
- Evaluation；
- Audit。

## 必须实现

1. Public task/case reference。
2. Task summary DTO。
3. Task detail DTO。
4. 后端返回 action capabilities。
5. 每个动作都有命令回执和冲突重放规则。
6. UI 不展示不存在的 Pause/Resume。
7. 任务页面支持刷新后回读。
8. Tauri 和 Chromium 使用同一隔离数据集验证。

## 页面结构

- 左：任务时间线；
- 中：工作现场/产出物；
- 右：Context、Source、Evidence、Permission、Trace、Evaluation、Audit；
- 底：后端允许的动作。

## 验收

- 任务详情不包含内部 ID；
- 修改绑定后 strict readback 失败；
- Retry 不重复产生副作用；
- 非允许动作前端不可触发；
- 直接调用非法动作后端拒绝；
- Refresh 后状态一致；
- 失败、等待、成功的视觉语义正确；
- 无虚构 Agent、模型、成本。
