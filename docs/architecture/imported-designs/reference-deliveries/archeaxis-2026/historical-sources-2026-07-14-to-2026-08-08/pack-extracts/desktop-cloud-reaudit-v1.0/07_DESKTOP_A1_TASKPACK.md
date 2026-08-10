# TaskPack AXDESK-A1：统一桌面壳与紫曜主题

## 元数据

- ID：`AXDESK-A1`
- 风险：中等
- 基线：远端执行时重新读取；本包可见基线 `2cdf11e2b85154c15cfd621c04dae8f6c90d693b`
- 目标：在不改业务数据模型的前提下，把现有 Workspace 升级为统一桌面壳。
- 单 Writer：HERMES
- Reviewer：Codex 只读审计
- 分支：`feat/archeaxis-desktop-a1-violet-core`

## 允许路径

- `app/workspace/ui/index.html`
- `app/workspace/ui/assets/styles.css`
- `app/workspace/ui/assets/app.js`
- `scripts/a0_browser_smoke.py`
- Workspace UI 直接相关测试
- 必要的文档状态说明

## 禁止路径

- 其他项目；
- 用户 Vault；
- E 盘资料；
- 数据库文件；
- 迁移；
- Research/Knowledge 核心持久化；
- Runtime Planner；
- Tauri 安全边界；
- Release 状态虚假升级。

## 任务步骤

### 1. 冻结真实基线

- `git fetch --all --prune`
- 确认当前分支和远端目标；
- 确认工作树 clean；
- 记录 HEAD；
- 如果不等于本包 SHA，以新 HEAD 为准重审差异；
- 不允许 reset --hard 覆盖远端新提交。

### 2. 重构视觉 token

- 新增 `violet-core`；
- 默认主题设为 Violet Core；
- 保留旧主题 localStorage 兼容；
- 不使用外部字体；
- 加 `prefers-reduced-motion`；
- 修正长文对比度。

### 3. 重构 Desktop Shell

实现：

- 一级 Rail；
- 动态二级栏；
- 顶部标签区；
- 项目/工作空间状态；
- 全局命令入口诚实空状态；
- 右侧 Inspector 容器；
- 底部活动坞；
- Inspector 和 Dock 可折叠；
- 960×640 可用；
- 390px 无横向溢出。

### 4. 重组真实页面

- 观心：overview/status；
- 知行：runtime/jobs/delivery；
- 察微：research/evidence；
- 藏识：knowledge/learning/evolution/machine；
- 系统：diagnostics；
- 其他入口显示 Planned，不显示伪数据和假按钮。

### 5. 激活现有专业组件原语

仅在有真实数据的页面使用：

- timeline；
- evidence-chain；
- runtime step；
- pane；
- split。

不要为未来功能生成静态假节点。

### 6. 实现真实活动坞

来源：

- `/workspace/api/jobs`
- `/workspace/api/delivery`
- `/workspace/api/status`

显示：

- 真实任务数量；
- pending/failed delivery；
- receipt；
- 待审核 Research。

不得显示：

- 虚构 Agent；
- 虚构模型；
- 虚构耗时；
- 虚构进度。

### 7. 实现认知检查器框架

A1 可展示聚合或所选行已有字段：

- Status；
- Source；
- Evidence Count；
- Lifecycle；
- Delivery；
- Capability。

没有任务详情投影时，明确显示“任务级 Inspector 将在 A2 接入”。

### 8. 更新测试

保留并更新：

- intake 错误与成功；
- Partial payload fail closed；
- Research queue；
- 真实 upload → outbox → dispatch → receipt → reload；
- no internal IDs；
- 响应式；
- console/page error 为零。

新增：

- Violet Core 默认；
- 一级/二级导航；
- Planned 页面诚实空状态；
- Inspector toggle；
- Dock toggle；
- keyboard focus；
- Escape modal；
- reduced-motion 不影响操作。

## 验收门禁

```bash
python scripts/check_repository_conventions.py --source worktree
python scripts/check_architecture.py
node --check app/workspace/ui/assets/app.js
python -m ruff check app shared knowledge_base inspiration_research Inspiration-Research shared-contracts/adapters app/workflow integration-tests scripts
python -m pytest tests/ -q --tb=short
cd knowledge_base && python -m pytest tests/ -q --tb=short
cd ..
python -m pytest integration-tests/ -q --tb=short
COGNITIVE_DATA_DIR=<isolated-dir> python scripts/a0_browser_smoke.py
```

Windows/Tauri/NSIS 由远端完整 CI 统一验证。

## 完成定义

- 所有现有真实动作可用；
- 不泄露内部 ID；
- 不新增假数据；
- 不降低 CSP/Loopback；
- 浏览器门禁通过；
- Wheel 仍包含 UI；
- 视觉与旧紫晶概念统一；
- 当前页面从后台感升级为桌面感；
- A2 能在此壳上继续开发。
