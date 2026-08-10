# ArcheAxis Apple Desktop 全套界面任务包

- 项目：`DTALEX66/Cognitive-Loop-OS`
- 产品：元枢系统 / ArcheAxis OS
- 包版本：`v1.0`
- 生成时间：`2026-07-28T00:13:07+00:00`
- 本次连接可见云端基线：`2cdf11e2b85154c15cfd621c04dae8f6c90d693b`
- 视觉方向：苹果式明亮桌面 + Human/Agent/Cognitive Governance 融合

## 这不是单纯换皮

本包将当前 Cognitive Workspace 逐步升级为一套完整的：

> Human 入口 + Agent 任务驾驶舱 + Research/Knowledge 工作台 + 认知画布 + 证真回放 + 连接与系统控制

视觉采用苹果式产品设计语言：

- 明亮柔和的中性色；
- 大面积留白；
- 低透明磨砂玻璃；
- 精细阴影；
- 14–16px 中等圆角；
- 轻量蓝紫渐变；
- 高信息密度但不拥挤；
- 强调真实状态和可验证数据。

## 重要真相边界

参考图中的以下内容只是目标视觉占位，不能直接写成静态数据：

- Agent 名称、运行数量和进度；
- GPT-5.6、其他模型名称与路由；
- Token、费用、耗时；
- 任务 ID；
- 任务阶段；
- Evidence 数量；
- 系统资源；
- 项目数量与知识统计。

实现时必须：

1. 有真实 API 就接真实 API；
2. 无真实 API 就显示“尚未接入”；
3. 不伪造 Agent、模型、成本和进度；
4. 不暴露内部 `package_id/job_id/command_id/event_id`；
5. 不降低 Loopback、CSP、Tauri 导航和数据库治理边界。

## 包内内容

- 全局产品与视觉规范；
- 8 个核心页面详细拆解；
- 组件库与 Design Tokens；
- 当前 API 到新界面的映射；
- 分阶段 TaskPack；
- HERMES 单 Writer 总命令；
- Codex 只读审查提示词；
- 验收矩阵、风险与回滚；
- PowerShell 基线和测试脚本；
- 8 张全套界面参考图；
- 一个可离线打开的桌面壳结构原型。

## 推荐执行顺序

1. `AXAPPLE-A0`：基线冻结与视觉合同。
2. `AXAPPLE-A1`：苹果式统一桌面壳。
3. `AXAPPLE-A2`：观心总览、察微、藏识真实页面。
4. `AXAPPLE-A3`：知行任务与智体中心。
5. `AXAPPLE-A4`：认知画布与证真回放。
6. `AXAPPLE-A5`：连接管理与系统控制。
7. 最后统一做 exact-SHA Windows/Tauri/NSIS 验收。

先完成 A1，不要一次把 8 张图全部硬塞进仓库。
