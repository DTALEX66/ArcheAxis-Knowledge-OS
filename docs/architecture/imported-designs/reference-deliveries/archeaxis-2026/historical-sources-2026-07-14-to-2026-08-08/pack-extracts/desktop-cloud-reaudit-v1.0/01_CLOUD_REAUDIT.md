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
