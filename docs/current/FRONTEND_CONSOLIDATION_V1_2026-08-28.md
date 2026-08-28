# 前端单壳收敛与成熟产品模式吸收记录（2026-08-28）

- 分支：`feat/frontend-consolidation-v1`
- 基线：`main@5ce0d3c`（分支建立时）
- canonical 产品壳：`frontend/src/app/App.tsx` + `src-tauri/`
- loopback `/workspace`：兼容/能力纵切；不再定义第二套产品身份
- `/kb/`：旧 Dashboard 已退役，重定向到 `/workspace#knowledge`
- DeepTutor：可替换学习 sidecar，不拥有产品导航

## 1. 对标产品与已吸收模式

| 对标 | 权威资料 | 吸收进入本项目的模式 |
|---|---|---|
| Obsidian | https://obsidian.md/help/mobile | 桌面多栏、侧栏可折叠；移动端改横向快捷导航；命令面板作为全局能力入口 |
| Zotero PDF Reader | https://www.zotero.org/support/pdf_reader | 原件阅读器 + 页级锚点侧栏；锚点回到原件上下文；不把批注当原件字节 |
| RemNote | https://help.remnote.com/en/articles/7925835-the-flashcard-home | 全局复习队列、到期/新内容分离、对象级练习入口；不让用户手工维护调度状态 |
| Linear | https://linear.app/docs/keyboard-shortcuts | Ctrl/Cmd+K 全局命令；详情 Inspector 按需打开；键盘优先但不牺牲鼠标/触控 |
| Vercel / Apple / Linear | 项目内 `popular-web-designs` 模板 | 冷白纸面、克制边界、系统字体、玻璃仅用于壳层、数据区避免营销渐变 |

不直接复制第三方前端代码、品牌资产或商业 UI。吸收的是信息架构、交互模式、失败边界和视觉令牌，生产实现继续由 ArcheAxis 原生 React/Tauri 承担。

## 2. 本轮已落实的代码

### 单一产品壳

- 顶部增加全局命令入口与 `Ctrl/Cmd+K`。
- 增加当前空间二级导航，只列真实六空间，不列 Agent/MCP/规划占位。
- Inspector 默认收起，选中对象后自动打开，可手动展开/关闭。
- Activity Dock 默认收起为 44px 真值摘要，可展开查看投递操作。
- 840px 以下一级导航转为横向滚动，不再永久占据左侧 72px。

### 原件与证据

- canonical React Library 增加原件阅读工作台。
- PDF 通过认证后的 Blob URL 在同一产品壳内打开。
- 全量分页读取 EvidenceAnchor，并按当前原件摘要过滤；界面只显示“证据锚点 N · 第 N 页”，不显示 anchor/hash。
- 文本原件显示有界预览；其他格式保留原件并诚实交给系统关联应用。

### 真值与失败边界

- Workspace API 2xx 响应增加对象/数组/关键字段运行时校验；部分或错类型 2xx 返回 `incompatible`，不再强制类型转换后渲染。
- 首次设置必须 `preflight.ready === true` 才能创建工作区。
- Loopback Intake 不再直接渲染后端 `detail`。
- Tauri 先创建 Recovery WebView，再在线程中执行 migration/Core readiness；最长启动等待不再造成“无窗口”。

### 遗留清退

- 删除根目录旧 HERMES 就寝面板 `index.html`。
- 删除旧紫色 Knowledge Dashboard 模板。
- `/kb/` 与 `/kb/dashboard` 保留兼容地址，但只重定向至统一产品壳。
- `UI_CONTRACT_V2` 将 canonical shell 从 DeepTutor 改为 ArcheAxis React/Tauri；DeepTutor 降级为 optional learning sidecar。

## 3. 响应式与视觉证据

项目内验收脚本：`.hermes/task-runtime/react-visual-acceptance.py`

证据目录：`.hermes/task-artifacts/frontend-consolidation/`

已验证：

- 1440×1000、1280×800、390×844、360×640；
- 无页面错误、无 console error；
- 所有尺寸 `scrollWidth <= clientWidth`；
- Activity Dock 始终在布局流内，底边不超过 viewport；
- 390/360 一级导航为 64px 横向栏；
- 小屏 Inspector 默认关闭、上下文侧栏隐藏；
- 全局命令面板、六空间和空态均有真实截图。

## 4. 仍然诚实保留的边界

- 视觉课件和空间记忆仍是规划面，不开放假播放/假生成。
- React PDF 阅读目前使用 WebView2/浏览器内置 PDF 呈现；PDF.js 精确文本层批注仍保留在 loopback 纵切，后续迁移为 React PDF.js 组件。
- DeepTutor 只有 authority bridge/sidecar 资格，不是当前前端底座。
- 发布前仍需 Windows 原生 WebView 当前树点击读回、Rust/NSIS、exact-SHA CI 和人工视觉复审。
