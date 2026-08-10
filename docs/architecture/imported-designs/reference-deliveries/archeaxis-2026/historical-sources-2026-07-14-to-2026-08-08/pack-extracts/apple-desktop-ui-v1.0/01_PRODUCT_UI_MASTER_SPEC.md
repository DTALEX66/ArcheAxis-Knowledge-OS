# 元枢桌面全套产品界面总规范

## 1. 产品定位

元枢桌面不是普通知识库，也不是代码 Agent IDE，而是面向个人重型使用的：

> Human–Agent Cognitive Workspace

核心循环：

```text
Capture / Goal
→ Research / Source / Claim / Evidence
→ Knowledge / Learning / Mastery
→ Plan / Permission / Execution
→ Trace / Evaluation / Human Review
→ Lesson / Knowledge Promotion
```

## 2. 一级导航

1. **观心总览**：对话入口、今日状态、快速任务、真实系统概览。
2. **智体中心**：Agent 模板、实例、技能、模型、工具、权限。
3. **知行任务**：任务收件箱、执行、审批、产出物、失败与恢复。
4. **认知画布**：Research、Knowledge、Task、Agent、Outcome 的空间化关系。
5. **证真回放**：任务时间线、Context、Tool、Evidence、Evaluation、Audit。
6. **察微研究**：Source、Claim、Evidence、Conflict、Unknown、Research Package。
7. **藏识知识**：Knowledge Unit、关系、学习、掌握度、机器知识。
8. **流程自动化**：TaskPack、Workflow、调度、无人值守、运行记录。
9. **连接管理**：模型、MCP、GitHub、本地目录、浏览器、Skills。
10. **系统控制**：Job、Outbox、Receipt、Migration、Backup、安全、日志、发布。

A1 可以将“连接管理/系统控制”作为两个入口；后期可在同一系统设置中合并。

## 3. 桌面结构

```text
顶部全局栏
├── 品牌与项目
├── 全局搜索/命令
├── 本地/远程环境
├── 模型路由
├── 通知
└── 用户

左侧主导航
├── 一级模块
└── 项目空间

中央工作区
├── Dashboard
├── List / Table
├── Editor
├── Mission Control
├── Canvas
└── Replay

右侧认知检查器
├── Context
├── Source
├── Evidence
├── Permission
├── Trace
├── Evaluation
└── Audit

底部状态栏
├── Local/Core/SQLite
├── 真实后台任务
├── 待审批/失败
├── 模型路由
└── 版本
```

## 4. 四类工作模式

### 普通模式

适合观心首页和快速任务，留白较多，减少技术细节。

### 专业模式

适合 Research、Knowledge、任务详情，显示高密度表格和 Inspector。

### 画布模式

左右属性栏 + 中央无限画布。

### 回放模式

时间线 + 执行详情 + Evidence/Evaluation Inspector。

## 5. 页面状态

每个页面必须支持：

- Loading；
- Empty；
- Partial；
- Available；
- Error；
- Unauthorized；
- Offline；
- Planned。

不允许只做“完美有数据”的效果图状态。
