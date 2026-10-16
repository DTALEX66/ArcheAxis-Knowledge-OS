# 星栖 M0 架构理解说明

配套真相源：`docs/architecture/astryn-m0.structurizr.dsl`。逐条边与节点的取证索引：`docs/architecture/astryn-m0.evidence.md`。

## 面向谁、说明什么

| 读者 | 该看哪个视图 | 用途 |
| --- | --- | --- |
| 产品/负责人 | `landscape`（系统全景） | 星栖与 AAOS 的领地划分，以及"哪些格子还是空的" |
| 工程（P1 接入者） | `containers` + `components` | 挂载点、端口边界、可替换的渲染 seam |
| 架构/安全评审 | `components` + 证据索引 | 权威事件链是否闭合、有无旁路写宿主存储 |

## 阅读顺序

1. 先看**边的颜色**：绿=权威（AUTHORITATIVE，唯一能改任务状态）、蓝=观测（OBSERVED，只能改对话呈现）、黄虚线=合成（SYNTHETIC，测试夹具）、红虚线=阻塞（BLOCKED）或禁区（FORBIDDEN）。
2. 再看 `runtime` 容器内部：契约层 → 角色内核 → 适配层 → 表达层，是单向依赖；`contracts` 不 import React，因此可被非 React 宿主复用。
3. 最后看红色边：它们代表**当前不存在的能力**，不是"已实现待接线"。

## 关键假设（可证伪）

- A1：星栖 M0 只有一个可执行体（浏览器 bundle）+ 一个开发期进程（loopback 代理）。没有第二个后端、没有第二套数据库。若 P1 引入 Tauri Rust 侧，需新增容器而不是塞进 `runtime`。
- A2：任务状态权威完全在 AAOS job 链上；星栖侧的 `task.status` 只是宿主状态的**投影**，进程重启即丢失，不做持久化。
- A3：`AAOS Rust Core` 的端点、语义与限制来自 2026-10-13 的只读核验（`AAOS-HOST-CAPABILITY-MAP.md`，HEAD `0574c3ac`）。AAOS 一旦变更，本模型即过期——这是"活文档"要求，不是已完成事实。
- A4：所有 `BLOCKED` 边的根因都是**宿主合同缺失**，不是星栖实现缺失。

## 证据强度

- `high`：星栖自身代码（本仓库可直接读到路径与符号）+ 本地门禁与浏览器实测结果。
- `medium`：AAOS 侧端点与限制（只读代码/契约核验，**无一次真实调用**）。
- `low`/`unknown`：运行时可用性。AAOS Core 是否正在运行、Ollama/LM Studio 是否配置、真实模型是否可达，均未验证。

## 已知缺口（不粉饰）

| 缺口 | 影响 | 需要谁决定 |
| --- | --- | --- |
| 无 AAOS 真实调用证据 | 图上所有 `AUTHORITATIVE` 边目前只有"类型契约 + 合成链路"支撑，宿主侧为 `AVAILABLE_UNVERIFIED` | 集成任务授权 |
| 无流式宿主会话面 | `answersEp` 只能一次性问答；流式路线在 AAOS 侧缺位 | AAOS 架构决策 |
| Consumer 闭集不含星栖 | 记忆与上下文两条边无法从 BLOCKED 转实线 | AAOS 侧新增枚举 |
| 宿主无事件推送 | 权威进展只能轮询，`onAuthoritativeEvent` 在真实宿主下是空实现 | 已在契约中显式声明 `streamResume:false` |
| 本地非 Git 仓库 | 模型没有 exact-SHA 可锚定，`A3` 的过期检测只能靠人工 | 用户选定 Git 方案 |

## 怎么可视化检查

用 Qoder 的 Structurizr DSL 预览直接打开 `docs/architecture/astryn-m0.structurizr.dsl`；也可导入官方 Structurizr Playground。若某个视图渲染不出来，**改 DSL 源文件**，不要改导出的图片。
