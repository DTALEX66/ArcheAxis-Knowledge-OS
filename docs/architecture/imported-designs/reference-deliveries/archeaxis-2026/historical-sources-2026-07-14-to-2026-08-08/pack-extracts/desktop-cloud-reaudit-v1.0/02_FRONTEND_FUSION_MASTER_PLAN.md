# 元枢桌面前端融合总方案

## 1. 产品定义

最终产品不是“知识后台 + 一个聊天框”，而是：

> Human 入口 + Agent 执行 + Cognitive Governance 的统一桌面。

正式名称：

- 中文：元枢桌面
- 英文：ArcheAxis Desktop
- 默认工作空间：元枢·观心
- 默认主题：元枢·紫曜 / Violet Core

## 2. 融合来源

### 从新版 OpenHuman 吸收

- 面向人的一级入口；
- 固定一级导航 + 动态二级导航；
- 对话、大脑、流程、连接统一在一个桌面；
- 欢迎页和空状态简洁；
- 模型与技术细节隐藏在系统内部。

### 从旧紫晶概念图吸收

- 黑蓝深色底；
- 紫晶品牌核心；
- 顶部多标签；
- 左侧项目树；
- 右侧属性/认知检查器；
- 高密度 Dashboard；
- 双栏知识编辑器；
- Canvas；
- Review + AI Assistant；
- 底部状态栏；
- 克制的玻璃与荧光。

### 从 Agent 桌面吸收

- 任务收件箱；
- Kanban / 状态队列；
- 任务独立工作区；
- 计划、步骤、工作现场、产出物；
- 暂停、批准、拒绝、重试、接管；
- 本地/远端执行环境；
- Skills/MCP/模型隐藏在 Agent 后面。

### Cognitive-Loop-OS 自己强化

- Source；
- Claim；
- Evidence；
- Candidate / Approved；
- Permission；
- Trace；
- Evaluation；
- Lesson；
- Knowledge Promotion；
- Migration / Rollback；
- Outbox / Receipt。

## 3. 一级信息架构

1. 观心：对话、总览、目标、快速捕获。
2. 智体：Agent 模板、实例、技能、模型、工具和权限。
3. 知行：任务收件箱、执行中、等待批准、失败与恢复。
4. 察微：Research、Source、Claim、Evidence、Conflict、Unknown。
5. 藏识：Knowledge、Learning、Mastery、Machine Knowledge、Review、Graph。
6. 流程：Workflow、TaskPack、调度、无人值守、运行记录。
7. 连接：GitHub、本地目录、MCP、模型、CC Switch、Hermes、Codex。
8. 系统：Job、Outbox、Receipt、Migration、Backup、安全、日志、发布。

## 4. 当前真实页面映射

| 目标模块 | 当前数据/页面 |
|---|---|
| 观心 | overview + status |
| 知行 | runtime + jobs + delivery |
| 察微 | research + evidence/lifecycle |
| 藏识 | knowledge + learning + evolution + machine |
| 系统 | diagnostics |
| 智体 | Planned，A1 只做诚实空状态 |
| 流程 | Planned，现有 sleep-loop 后续独立接入 |
| 连接 | Planned，A1 只做可验证配置入口说明 |

## 5. 桌面六层结构

1. 顶部：标签、项目、全局命令、搜索、审批、状态。
2. 一级图标栏：八大模块。
3. 动态二级栏：列表、资源树、队列。
4. 中央自适应工作区：Dashboard / 编辑器 / 任务舱 / 画布 / 回放。
5. 右侧认知检查器：Context / Source / Evidence / Permission / Trace / Evaluation / Audit。
6. 底部活动坞：真实 Job、Delivery、审批、错误和系统状态。

## 6. 四种工作面

### 观心会话

- 简洁；
- 快速上传；
- 创建 Research；
- 创建任务；
- 继续最近 Case；
- 待审批提示。

A1 不接入伪聊天模型，可把输入框标记为“全局命令入口规划中”。

### 知行任务舱

A1 只展示真实 Job/Delivery。
A2 才提供：

- 任务摘要；
- 时间线；
- 当前步骤；
- 任务级 Inspector；
- Artifact；
- 真实可用的重试和审批。

### 认知画布

A3 才提供：

- Research Canvas；
- Knowledge Canvas；
- Workflow Canvas；
- 节点和边均来自后端真实合同。

### 证真回放

A3 才提供任务级：

- Input；
- Context；
- Plan；
- Permission；
- Tool Result；
- Evidence；
- Evaluation；
- Human Decision；
- Lesson；
- Retry / Replay。

## 7. 项目空间

后续统一容器：

- 目标；
- 对话；
- Research；
- Source Asset；
- Knowledge；
- Agent Run；
- Workflow；
- Artifact；
- Decision；
- Lesson。

A1 只实现项目切换 UI 框架，当前默认项目为本地工作台，不伪造项目数据。

## 8. 明确不做

- 不复制 OpenHuman 的品牌、图标、代码和社区模块；
- 不继续使用 Obsidian Workspace 名称和近似标志；
- 不展示假 Agent；
- 不展示虚构 Token、成本和进度；
- 不把单一 `file_read` 描述成通用 Agent；
- 不在 A1 引入大规模前端框架重写；
- 不破坏 Tauri、CSP、Loopback、Wheel 和浏览器门禁。
