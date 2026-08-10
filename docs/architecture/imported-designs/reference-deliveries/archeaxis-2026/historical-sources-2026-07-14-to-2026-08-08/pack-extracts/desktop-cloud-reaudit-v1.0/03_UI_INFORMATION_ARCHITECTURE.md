# UI 信息架构与页面路由

## A1 路由模型

### 一级模块

- `guanxin`
- `zhiti`
- `zhixing`
- `chawei`
- `cangshi`
- `workflow`
- `connect`
- `system`

### 当前可用子页面

#### 观心

- `overview`

#### 知行

- `runtime`
- `delivery`

#### 察微

- `research`
- `evidence`

#### 藏识

- `knowledge`
- `learning`
- `evolution`
- `machine`

#### 系统

- `diagnostics`

### Planned 页面

- `agents`
- `skills`
- `models`
- `workflow-builder`
- `workflow-runs`
- `integrations`
- `mcp`
- `settings`
- `audit`
- `projects`
- `review`
- `canvas`
- `palace`

Planned 页面必须显示具体原因：

- 后端尚未提供真实数据；
- 当前阶段何时接入；
- 相关真实页面入口；
- 不出现可执行假按钮。

## 页面布局规则

### Dashboard

- 左上：问候/今日状态；
- 中上：最近真实活动；
- 右上：系统与审批；
- 中部：任务、Research、学习；
- 底部：能力状态和真实活动图；
- 右侧检查器默认折叠。

### 列表页

- 左栏：筛选与队列；
- 中央：真实列表；
- 右侧：所选项 Inspector；
- 没有公开引用前，A1 不提供任务详情 URL。

### 编辑器

- 左：原始来源树；
- 中：转换文本与知识成品；
- 右：Source / Claim / Evidence / Quality；
- A1 只做结构原型，不接入未经治理的写入。

### Agent 任务舱

- 左：任务时间线；
- 中：工作现场；
- 右：Inspector；
- 底部：控制栏；
- A2 实现。

### Canvas

- 中央画布；
- 右侧节点属性；
- 小地图；
- A3 实现。

## 导航状态

每个入口必须带状态：

- `available`
- `partial`
- `planned`
- `blocked`

状态从前端静态能力表 + Release Manifest 合并，不从文案猜测。
