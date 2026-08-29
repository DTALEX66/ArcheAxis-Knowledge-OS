# 前端单壳收敛与成熟产品模式吸收记录（2026-08-28）

- 分支：`feat/frontend-consolidation-v1`
- 基线：`main@5ce0d3c`（分支建立时）
- canonical 产品壳：`frontend/src/app/App.tsx` + `src-tauri/`
- loopback `/workspace`：产品页已退役（HTTP 410）；仅 `/workspace/api/*` 作为本地 API 兼容边界
- `/kb/`：旧 Dashboard 已退役（HTTP 410），不再跳转到另一套界面
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
- PDF 只通过后端 `%PDF-` 魔数、大小上限和内容身份校验端点读取，再以 sandboxed Blob frame 在同一产品壳内打开。
- 全量分页读取 EvidenceAnchor，并按当前原件摘要过滤；界面只显示“证据锚点 N · 第 N 页”，不显示 anchor/hash。
- 文本原件显示有界预览；其他格式保留原件并诚实交给系统关联应用。
- 原件打开使用 generation 身份门；旧下载、旧分页、旧文本读取与旧失败不能覆盖较新的原件或撤销其 Blob URL。

### 真值与失败边界

- Workspace API 2xx 响应增加对象/数组/关键字段运行时校验；部分或错类型 2xx 返回 `incompatible`，不再强制类型转换后渲染。
- Home、Status、Setup、Delivery、Jobs 与 Evidence Bundle 对实际消费字段执行运行时类型校验；错误 2xx 不再降级成空态或“投递可用”。
- 全局命令面板使用 portal、背景 inert、焦点陷阱、方向键导航与关闭后焦点恢复。
- 首次设置必须 `preflight.ready === true` 才能创建工作区。
- Tauri 先创建 Recovery WebView，再在线程中执行 migration/Core readiness；只读恢复状态不再等待长启动锁，重试/安全模式在启动占用时快速返回 busy。

### 遗留清退

- 删除根目录旧 HERMES 就寝面板 `index.html`。
- 删除旧紫色 Knowledge Dashboard 模板。
- `/workspace`、`/kb/` 与 `/kb/dashboard` 的旧产品页面返回 410；API 路径继续保留。
- 删除并停止打包 `app/workspace/ui/`，同步移除旧 PDF.js vendored 资产、旧 UI 测试和旧浏览器门。
- 视觉课件、空间记忆及永久禁用的取消投递入口不再出现在普通用户导航。
- `UI_CONTRACT_V2` 将 canonical shell 从 DeepTutor 改为 ArcheAxis React/Tauri；DeepTutor 降级为 optional learning sidecar。

## 3. 响应式与视觉证据

项目内验收脚本：`scripts/a0_browser_smoke.py`

证据目录：`.hermes/task-artifacts/browser-smoke/`

已验证：

- 1440×1000、1280×800、390×844、360×640；
- 无页面错误、无 console error；
- 所有尺寸 `scrollWidth <= clientWidth`；
- Activity Dock 始终在布局流内，底边不超过 viewport；
- 390/360 一级导航为 64px 横向栏；
- 小屏 Inspector 默认关闭、上下文侧栏隐藏；
- 全局命令面板、六空间和空态均有真实截图。

## 4. 仍然诚实保留的边界

- 视觉课件和空间记忆只保留在设计/路线图资料，不进入普通用户导航。
- React PDF 阅读使用后端强校验的 application/pdf + sandboxed WebView2/浏览器内置呈现；旧 PDF.js loopback 纵切已删除。
- URL/文件 Intake、完整 Vault 搜索/读写、Canvas、Exchange，以及 PDF 文本层选区/锚点创建尚未迁成 React 产品控件；对应 API 继续保留，但当前不宣称为可见前端能力，也不恢复第二套 UI。
- 通用原件读取具有独立硬上限、内容摘要复核并拒绝 PDF；PDF 端点执行有界读取、摘要复核、魔数与 MIME 校验。
- DeepTutor 只有 authority bridge/sidecar 资格，不是当前前端底座。
- 发布前仍需 Windows 原生 WebView 当前树点击读回、Rust/NSIS、exact-SHA CI 和人工视觉复审。

## 5. 管线落地补充（2026-08-29，`feat/pipeline-multiformat-console`）

在单壳收敛基础上，把多格式摄取管线从前端只读投影落成真实产品闭环：

### 后端管线闭环

- 批量目录导入不再写死端 artifacts：每个文件先按内容寻址保留到 Source Archive（失败也保留原件），再转换、记录不可变 ConversionRun + EvidenceAnchor，失败原因可读且脱敏（无绝对路径、≤300 字符）。
- 批量任务失败必须抛异常才会计入 failed 并触发有界重试（controller 语义：返回即完成）。
- `workspace_library` 投影增加 format、engine、error_reason、converted_char_count；`conversion_state` 从 RawAsset 失败记录读取真实原因。
- 新端点：`GET /api/library/{sha256}/converted`（有界返回最新转换文本）、`GET /api/library/{sha256}/conversion-run`（engine/version/block_count/loss_notes/preview）。
- 交换验证成功显式返回 `valid: true`（与备份验证契约一致）。

### 前端新增产品空间

| 空间 | 内容 |
|---|---|
| 导入（intake） | 网页 URL 导入、单文件上传（多格式回执：格式/引擎/字符数/预览）、批量目录导入（进度、暂停/继续/安全停止、失败清单） |
| 知识库（vault） | 打开本地目录只读扫描、文件树、全文搜索、Markdown 编辑（expected-hash 乐观锁、409 冲突提示重读）、可恢复备份列表 |
| 知识库画布 | JSON Canvas 文档节点级读取/新增/编辑/删除，写回经校验端点 + 乐观锁 |
| 交换（exchange） | 开放交换包导出（清单哈希回执）与验证（valid + verified_items） |
| 资料库增强 | 格式/引擎/状态列、需关注原因、转换文本阅读器 |
| 证据锚点 | PDF 阅读器内页级锚点创建（页码输入 + 内容寻址写入 + 列表刷新），非法页码前端拒绝 |

### 多格式 DTO fail-closed

- IntakeResult、BatchStatus、ConvertedContent、ConversionRun、Vault inspect/file/search/write/backups/canvas、Exchange export/verify、EvidenceAnchor create 均做运行时字段校验；畸形 2xx 返回 `incompatible`，不渲染部分真值。
- 内部标识（conversion_run_id、anchor_id、backup 绝对路径）不跨产品边界。
