# 当前文件到目标文件的修改映射

## A1 允许修改

### `app/workspace/ui/index.html`

目标：

- 改为统一桌面壳；
- 增加一级 Rail；
- 增加动态二级栏容器；
- 增加顶部标签/项目/命令区；
- 增加右侧 Inspector；
- 增加底部真实活动坞；
- 复用现有页面 section 和真实 data hook；
- 保留 intake modal 的可访问性。

### `app/workspace/ui/assets/styles.css`

目标：

- 从超长单体行整理为分区可读 CSS；
- 增加 Violet Core token；
- 保留 `yaojin` / `deepspace` 兼容；
- 实现 shell、rail、sidebar、tabs、inspector、dock；
- 激活已有 runtime、timeline、evidence-chain、editor 原语；
- 增加 responsive 和 reduced motion；
- 不引用外部字体或 CDN。

### `app/workspace/ui/assets/app.js`

目标：

- 重构为可读函数区；
- 将 nav 定义改为一级模块 + 动态子导航；
- 保留当前 DTO 验证；
- 保留内部 ID 隐藏；
- 保留当前 API 和真实动作；
- 新增 UI state：module、page、inspector、dock、theme；
- Planned 页面显示具体状态；
- 活动坞只使用真实 jobs/delivery/status；
- 不添加假 Agent。

### `scripts/a0_browser_smoke.py`

目标：

- 更新新布局选择器和标题；
- 保留原有失败关闭、响应式、导入、Research、真实 Delivery 回读；
- 新增：
  - 一级导航；
  - 二级导航；
  - Inspector 折叠；
  - 活动坞；
  - Violet Core 默认主题；
  - 内部 ID 不泄漏。

### Workspace UI 相关测试

- 更新 DOM 和 DTO 合同测试；
- 保留当前安全与隐私断言。

## A1 原则上不修改

- Research/Knowledge/Runtime 业务服务；
- SQLite Schema；
- Migration；
- Auth；
- Safe HTTP；
- Tauri Rust 后端；
- Release Manifest capability 含义。

若为了新静态资源必须修改资产路由，A1 应优先避免新增文件名，
继续使用现有 `styles.css` 和 `app.js`，降低 Wheel/CSP 风险。

## A2 新增或修改

- Workspace public task projection；
- public case reference；
- task detail / timeline / inspector DTO；
- router/service/tests；
- UI 任务舱；
- Release Manifest capability 只在真实完成后更新。

## A3 新增或修改

- Canvas projection；
- Replay projection；
- 节点/边合同；
- Inspector 详情；
- 任务回放；
- 写操作继续后置，先只读。
