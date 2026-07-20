# 元枢系统 ArcheAxis OS · 观心工作台 UI Prototype

## 交付物

运行时资源已经归属 Python 包并随 wheel 发布；本目录只保留设计说明。

- `app/workspace/ui/index.html` — 真实 `/workspace` 产品外壳，保留原型的信息架构并逐区接入后端。
- `app/workspace/ui/assets/styles.css` — 双主题 Design Token、响应式布局、组件样式。
- `app/workspace/ui/assets/app.js` — 导航、主题、导入 API、详情抽屉、Job Center 与 Toast 交互。

## 信息架构

### Core

- 观心总览 / Guanxin Overview
- 项目 / Projects
- 察微研究 / VeriScope
- 证据中心 / Evidence
- 藏识知识 / Knowledge Archive
- 知衡机器知识 / Machine Knowledge
- 知行任务执行 / Praxis Runtime
- 知新评估进化 / Evolution Loop

### Learning OS

- 课程中心 / Courses
- 学习路线 / Learning
- Review 复习 / Review
- Training 训练 / Training
- 显象可视化教学 / Visual Teaching Studio
- 知境空间宫殿 / Spatial Memory Engine
- Skills 技能实战 / Skills
- Teach Back 输出教学 / Teach Back
- Consolidation 长期巩固 / Consolidation
- Report 学习报告 / Report

### System

- 全局搜索 / Search
- 模型与工具 / Models & Tools
- Agent 管理 / Agents
- 审计记录 / Audit
- Diagnostics 系统诊断 / Diagnostics
- Settings 设置 / Settings

## 页面地图

- `#overview` 观心总览
- `#projects` 项目工作台
- `#project-detail` 项目详情（Tab：总览 / 资料 / 研究 / 知识 / 视觉 / 任务 / Agent / 文件 / 决策 / 版本 / 评估 / 经验 / 作品）
- `#research` 察微研究（来源 / 主张 / 证据三栏）
- `#evidence` 证据中心（Provenance Chain）
- `#knowledge` 藏识知识库（表格 / 卡片 / 图谱 / Canvas 切换位）
- `#knowledge-detail` 知识详情（正文 + 右侧属性）
- `#courses` 课程中心
- `#learning` 致知学习中心
- `#review` Review 专注模式
- `#training` Training 训练
- `#visual` 显象四层 Editor Shell
- `#palace` 知境空间宫殿（2D / 2.5D / 3D / 路线 / 复习）
- `#skills` Skills 技能实战
- `#teachback` Teach Back 输出教学
- `#consolidation` Consolidation 长期巩固
- `#report` Report 学习报告
- `#machine` 知衡机器知识
- `#runtime` 知行任务与 Agent Runtime
- `#evolution` 知新评估进化中心
- `#search` 全局搜索
- `#models` 模型与工具
- `#agents` Agent 管理
- `#audit` 审计中心
- `#diagnostics` 本地系统诊断
- `#settings` 设置

## 核心任务路径

1. 本地启动 → 观心总览 → 优先处理（审批 / 研究 / 复习）。
2. 项目工作台 → 项目详情 → 资料 / 研究 / 知识 / 任务 / Agent / 评估。
3. 察微研究 → 主张 → 证据链 → 审核 → 藏识正式知识。
4. 知识详情 → 学习资产 → Review → Training → Teach Back → 学习报告。
5. 显象编辑器 → Fact / Memory / Visual / Teaching → 审核 / Freeze / Fork / 导出。
6. 知行 Runtime → Goal / Plan / TaskPack / Agent / Permission / Trace / Evaluation → Lesson。
7. Diagnostics → 服务状态 → 一键诊断 / 重启服务 / 重建索引 / 备份 / 脱敏导出。

## 主题 Token

### 曜金本源

- bg: `#0F1E36`
- deep: `#0A1426`
- panel: `#162844`
- accent: `#C8A972`
- text: `#F0F2F5`
- muted: `#AAB2C0`
- success: `#2D8F64`
- warning: `#D4A017`
- danger: `#C24848`
- info: `#4E83C3`

### 深空轴心

- bg: `#0A0E1A`
- deep: `#060911`
- panel: `#121726`
- accent: `#7C5CFF`
- accent2: `#38A8FF`
- text: `#F3F5FA`
- muted: `#929AAA`
- success: `#35A777`
- warning: `#D5A83C`
- danger: `#D05252`

## 组件拆分（前端落地）

- `AppShell`：TopBar / SideNav / Main / JobCenter
- `PageHeader`：Eyebrow / Title / Description / Actions
- `StatusBadge`：内容状态 / 任务状态 / 学习状态 / 视觉资产状态
- `MetricCard`：总览指标
- `DataTable`：知识、机器知识、审计、模型
- `Timeline` / `EvidenceChain`：Trace、Provenance、项目阶段
- `Drawer`：对象详情
- `CommandPalette`：Ctrl+K
- `PermissionDialog`：Agent 权限审批
- `EditorShell`：显象四层编辑器
- `PalaceViewport`：2D / 2.5D / 3D 空间记忆
- `RuntimeGrid`：计划 / 实时执行 / 权限 / Trace
- `DiagnosticsPanel`：服务健康与操作

## 响应式规则

- 1536×1024：主设计尺寸，左侧导航 248px，右抽屉 420px。
- 1440：导航 220px，四列指标降为两列，右抽屉 380px。
- 1280：导航折叠为 72px 图标栏，三栏研究降为两栏，Editor 右侧属性下移，Runtime 改为两段式。
- 1920+：导航 256px，内容最大宽度扩展，卡片与标题尺度略增。

## 已验证

- 本地静态服务 `http://127.0.0.1:8765/index.html` 可打开。
- 浏览器实测：26 个 `.page`，24 个主导航项，初始主题 `yaojin`。
- 实测点击“深空”后主题切换为 `deepspace`。
- 实测点击“知行任务执行”后显示 `page-runtime`，hash 为 `#runtime`。
- `node --check workspace/ui/archeaxis/app.js` 通过。
