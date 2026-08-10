# 页面 03：知行任务驾驶舱

## 参考图

`references/screens/03_task_mission_control.png`

## 目标

显示一个任务的真实生命周期，而不是聊天日志。

## 布局

- 左：任务阶段与整体状态；
- 中：
  - 当前执行；
  - 子任务；
  - 运行实例；
  - 实时/刷新日志；
  - 待审批；
  - 已完成；
  - 失败；
  - 产出物；
- 右：认知检查器；
- 顶部：后端允许的 Pause/Stop/Takeover/More。

## A3 必须新增

- public task reference；
- task summary/detail；
- timeline；
- artifacts；
- backend action capabilities；
- approval command receipt；
- retry/replay lineage。

## 禁止

前端不能根据状态字符串自行决定“暂停/接管”是否可用。
