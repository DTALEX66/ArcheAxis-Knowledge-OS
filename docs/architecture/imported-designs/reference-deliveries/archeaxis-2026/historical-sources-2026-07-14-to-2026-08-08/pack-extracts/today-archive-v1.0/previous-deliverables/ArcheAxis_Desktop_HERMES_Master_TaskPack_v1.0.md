# ArcheAxis Desktop 云端重审与前端修改包

- 仓库：`DTALEX66/Cognitive-Loop-OS`
- 云端分支：`main`
- 本次连接可见基线：`2cdf11e2b85154c15cfd621c04dae8f6c90d693b`
- 包版本：`v1.0`
- 生成时间：`2026-07-27T16:38:46+00:00`
- 目标：把现有 Cognitive Workspace 升级为统一的 **Human + Agent + Cognitive Governance Desktop**。

## 先看结论

当前前端不是空页面，已经具备真实的 Research、Knowledge、Learning、Machine Knowledge、
Job、Outbox、Receipt 和 Lifecycle 投影；但是产品形态仍然是“治理后台”，尚未形成每天可用的
Agent 桌面。

这次修改不推翻现有后端和 Tauri 壳。采用以下融合路线：

1. 保留当前 Python / FastAPI / SQLite / Tauri 真相链。
2. 以旧概念图的深色紫晶皮肤作为旗舰主题：**元枢·紫曜 / Violet Core**。
3. 吸收新版 OpenHuman 的人机入口和双层导航。
4. 吸收 OpenHands、Cursor、Windsurf 的任务指挥逻辑。
5. 保留 Cognitive-Loop-OS 独有的 Source、Claim、Evidence、Permission、Trace、
   Evaluation、Lesson 和知识晋升体系。
6. 不伪造多 Agent、异步 Worker、实时进度或不存在的工具。

## 推荐执行顺序

- 先执行 `Desktop A1`：统一桌面壳、紫曜主题、动态导航、真实状态卡片、右侧检查器框架、
  底部真实活动坞。
- A1 验收并合并后，再执行 `Desktop A2`：任务驾驶舱和公开任务投影。
- A2 完成后执行 `Desktop A3`：认知画布与证真回放。
- 多 Agent、电脑控制和社区能力继续后置。

## 关键文件

- `01_CLOUD_REAUDIT.md`：云端重新审计。
- `02_FRONTEND_FUSION_MASTER_PLAN.md`：前端融合总方案。
- `04_VIOLET_CORE_DESIGN_SYSTEM.md`：紫曜主题设计系统。
- `07_DESKTOP_A1_TASKPACK.md`：第一阶段可直接执行任务。
- `10_HERMES_MASTER_PROMPT.md`：直接发给 HERMES 的总命令。
- `prompts/HERMES_EXECUTE_A1.txt`：第一阶段执行提示词。
- `prototype/archeaxis_desktop_a1.html`：离线结构原型。
- `references/`：你上传的 OpenHuman 与旧紫晶概念图参考。

## 基线漂移规则

你表示云端有新更新，但本次 GitHub 连接可见的 `main` 头仍为 `2cdf11e2b85154c15cfd621c04dae8f6c90d693b`。
执行前必须运行 `scripts/00_verify_baseline.ps1`：

- 如果远端已经更新，不得硬重置、不得覆盖；
- 先读取新 HEAD 和差异；
- 在新 HEAD 上重放本修改包；
- 禁止直接以本包中的旧 SHA 强制写回。


---

# Cognitive-Loop-OS 云端重新审计

## 1. 审计基线

当前 GitHub 连接器可见：

- 仓库：`DTALEX66/Cognitive-Loop-OS`
- 默认分支：`main`
- 可见 HEAD：`2cdf11e2b85154c15cfd621c04dae8f6c90d693b`
- HEAD 提交：`test(workspace): prove Chromium delivery readback (#12)`
- 仓库公开、未归档。
- 当前连接没有返回该 SHA 的可验证 Actions 状态，因此不能仅凭提交信息宣称远端 CI 已 Green。

若你在其他分支或本地已经推送了更新，先用包内基线脚本确认真实远端。

## 2. 当前前端已经完成的能力

当前 `app/workspace/ui/index.html` 已包含真实页面：

- 观心总览
- 系统诊断
- 知行任务执行
- 察微研究
- 藏识知识
- 学习路线
- 知新评估进化
- 知衡机器知识
- 证据中心·生命周期
- 本地资料导入

当前 `app.js` 已经：

- 验证 Workspace DTO；
- 读取真实状态、Job、Delivery、Research、Knowledge、Learning、Evolution、Machine Knowledge；
- 执行按需 Outbox 投递和失败重试；
- 执行 Research 批准、开始学习、记录练习、Runtime 知识批准；
- 隐藏内部 package/job/command/event 编号；
- 对无效结果失败关闭；
- 保持没有真实数据时显示空状态，而不是样例数字。

当前 `styles.css` 已经存在但未被充分使用的组件原语：

- split 三栏布局
- pane
- evidence-chain
- timeline
- editor
- canvas node / edge
- palace
- runtime
- step / log

说明仓库已经为专业工作区预留了视觉构件，但当前 DOM 仍主要使用列表与卡片，形成“设计能力存在、产品工作区未落地”的状态。

## 3. 前端主要问题

### P0：产品形态仍是治理后台

当前 Runtime 页仅展示“最近任务”和 Outbox/Receipt 聚合，用户看不到：

- 任务目标；
- 执行计划；
- 当前步骤；
- 工作现场；
- Context；
- Evidence；
- Permission；
- Trace；
- Evaluation；
- Artifact；
- Checkpoint；
- 接管与重试边界。

不能称为 Agent Desktop。

### P0：导航结构过平

当前导航按 `Core / Learning OS / System` 平铺大量项目。
大量入口只跳到统一 unavailable 页面，用户难以建立“观心—智体—知行—察微—藏识—流程—连接—系统”
的稳定心智模型。

### P1：搜索入口是只读占位

顶部搜索明确标记“尚未接入”。可以保留，但应改成全局命令入口的真实空状态，
不得看起来像已经能搜索所有知识。

### P1：缺少动态二级导航、标签页和项目容器

旧概念图擅长：

- 顶部标签；
- 项目资源树；
- 右侧属性检查器；
- 多面板；
- 底部状态栏。

当前页面只有固定顶栏、单左栏和主内容区，没有形成重型桌面。

### P1：视觉主题与最终品牌未统一

当前有：

- `曜金`
- `深空`

但你确认更偏好旧概念图的黑蓝紫晶皮肤。
建议新增并默认启用：

- `violet-core`：元枢·紫曜
- 保留 `yaojin` 兼容旧设置
- 保留一个低发光阅读模式，后续再实现

### P1：CSS/JS 单体且压缩在少量超长行中

优点是当前 Wheel 打包简单，缺点是：

- 维护困难；
- 组件边界不清；
- 设计 token、布局、组件、页面状态耦合；
- 很难进行 changed-file 审查；
- 浏览器测试定位修改影响困难。

A1 不建议立刻引入 React；先把现有三文件重构为可读、分区明确的静态实现，
保持 Wheel、CSP 和 Tauri 边界稳定。

### P1：现有真实能力与未来信息架构混杂

当前导航同时展示已接入和未来能力。需要明确三种状态：

- Available：有真实数据和真实动作；
- Read-only / Partial：只读投影或局部闭环；
- Planned：只显示解释性空状态，不出现可点击假动作。

### P2：没有全局活动坞

CSS 预留了底部空间，但当前 HTML 没有形成统一的 Agent/Job 活动坞。
A1 只能展示真实 Job、Outbox、Receipt 和审批数量，名称应为“后台活动”；
在异步 Worker 和多 Agent 未完成前，不得显示“3 个 Agent 正在工作”等伪状态。

## 4. 后端与桌面壳判断

### 保留

- FastAPI 本地服务；
- Loopback-only Workspace；
- CSP 和安全响应头；
- Tauri 外部 URL 严格限制；
- Python Runtime 嵌入；
- Migration / Backup / Receipt；
- 当前 public projection 不泄露内部 ID 的原则；
- Chromium、Windows Runtime、Tauri/NSIS 门禁。

### 需要扩展但不能在 A1 强行完成

- 用户可访问的公开任务引用，而不是暴露内部 job_id；
- 任务时间线投影；
- Inspector 投影；
- Artifact 投影；
- Pause / Resume / Checkpoint 的真实后端合同；
- SSE 或等价的增量事件；
- 多 Agent 实例与环境隔离。

## 5. 重新分级结论

| 维度 | 当前判断 |
|---|---|
| 后端治理 | 强 |
| SQLite / Migration / Receipt | 强 |
| 本地安全边界 | 强 |
| 真实浏览器闭环 | 已有首条 |
| 前端信息架构 | 中等，入口过多且层级不清 |
| 视觉系统 | 已有基础，但未与紫晶概念统一 |
| Agent Desktop | 未完成 |
| 专业知识工作台 | CSS 有原语，页面未落地 |
| 证真回放 | 仅聚合页，未形成任务级回放 |
| 多 Agent | 不得宣称完成 |
| 正式公开发布 | 仍需 exact-SHA CI 和发布证据 |

## 6. 本轮修改边界

这次包重点修前端产品结构，不在同一 TaskPack 中处理：

- 原始资产 provenance P0；
- Evaluation/Lesson 语义拆分；
- 通用 Planner；
- 异步 Worker；
- 多 Agent；
- ASR；
- 社区、钱包、Tiny Place；
- 云端生产部署。

这些属于独立高风险 TaskPack，避免前端改造掩盖后端真相问题。


---

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


---

# 发给 HERMES 的最终总命令

你是 Cognitive-Loop-OS 本轮唯一 Writer。目标仓库：

`<repository-root>`

远端：

`DTALEX66/Cognitive-Loop-OS`

## 第一步：重新确认云端

本修改包记录的可见基线为：

`2cdf11e2b85154c15cfd621c04dae8f6c90d693b`

但用户表示云端可能已有新更新。你必须：

1. `git fetch --all --prune`
2. 读取当前分支、HEAD、upstream 和 remote refs；
3. 读取远端真实目标分支；
4. 如果远端 HEAD 已变化，以新 HEAD 为基线；
5. 禁止 `reset --hard` 覆盖新提交；
6. 禁止强推；
7. 禁止修改项目目录以外任何文件；
8. 禁止扫描或修改 Obsidian-Assistance、个人 Vault、E 盘资料和其他项目。

## 第二步：只执行 AXDESK-A1

读取：

- `07_DESKTOP_A1_TASKPACK.md`
- `02_FRONTEND_FUSION_MASTER_PLAN.md`
- `04_VIOLET_CORE_DESIGN_SYSTEM.md`
- `05_CURRENT_TO_TARGET_FILE_MAP.md`
- `13_ACCEPTANCE_TEST_MATRIX.md`
- `14_RISK_AND_ROLLBACK.md`

分支：

`feat/archeaxis-desktop-a1-violet-core`

## 硬性规则

- 单 Writer；
- 不创建第二套后端；
- 不引入假 Agent；
- 不展示伪进度、伪成本、伪模型和静态运营数字；
- 不暴露内部 package/job/command/event ID；
- 不降低 Loopback、CSP、导航限制和安全头；
- 不改 SQLite Schema；
- 不改 Planner；
- 不改其他项目；
- 保留并更新真实 Chromium delivery closed loop；
- 当前静态技术栈优先，不在 A1 强行迁移 React；
- 所有修改必须有定向 RED/GREEN；
- 形成可回滚 checkpoint commit；
- 完整门禁只在 frozen tree 上运行一次。

## UI 目标

把当前治理后台升级为：

- 顶部标签/项目/命令区；
- 一级 Rail；
- 动态二级导航；
- 中央自适应工作区；
- 右侧认知检查器；
- 底部真实活动坞；
- 默认 Violet Core 深色紫曜主题；
- 保留现有所有真实页面和动作。

## 停止条件

遇到以下情况立即停止并报告，不得猜测：

- 远端分支与预期不一致；
- 工作树有用户未提交变更；
- UI 改造需要数据库迁移；
- 当前 DTO 不足以显示任务级详情；
- 测试要求伪造数据；
- 需要访问项目外路径；
- Browser/Tauri 安全边界需要放宽；
- Release Manifest 与真实能力冲突。

完成后输出：

- 基线 SHA；
- 分支；
- 修改文件；
- RED/GREEN；
- 本地门禁；
- 已知限制；
- 未实现能力；
- commit SHA；
- 远端 CI URL；
- 明确说明没有完成 A2/A3。
