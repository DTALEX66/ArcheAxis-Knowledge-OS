> Historical snapshot: 2026-09-27 至 2026-09-29 的过程记录，非当前状态或执行权威。
> 当前清理、交付、验证与阻塞请读 [2026-10-01 交接](../../current/STORAGE-CLEANUP-HANDOFF-20261001.md)。

> 归档（2026-10-08 文档收敛，批次 d-docs-20261008）：本文件自 `docs/current/` 原样移入 `docs/history/ui-handoff-20260928/`，正文、日期与原始证据未改写；该主题的当前入口是 `docs/current/AAOS-UI-HANDOFF-20261001.md`。

## 现行解释（2026-10-01）

- B10 最终可部署母版是最高视觉依据；Aurora/黑白共用布局、状态及缩放规则。正文中此前 B03 最高或 B10 仅作风格参考的判断已被取代。
- r97/r38/r30、旧截图数、PID、HEAD、测试/构建及上传结果仅证明对应历史快照；不能推断今天界面、完整原生交互/DPI/动画或安装态已经验收。
- “49 项失败全为旧标题”是当时判断，后续发现并修复真实交互行为问题，不能沿用为全部豁免理由。
- 旧76项保留/未授权、原位展开仍在、未上传及换连接器建议都是早期阶段记录，今天以最新交接和删除回读为准；不再要求沿用旧认证建议。
- SHM PARTIAL、wheel UNVERIFIED、未知归属与历史拒绝如实保留；当前整体仍 PARTIAL，静态/编译通过不等于用户数据库或完整产品健康。

原快照源 SHA-256：`d31bff64c78c0517e4aa1e00cfdd2cf1b46a302eb8de7aacf5f689f664f70026`。以下保留历史正文，只统一文本格式，不将旧叙述重新认定为当前真值。

---

# AAOS UI 前端交接与验收摘要（2026-09-28 · r97）

## 当前交付状态

- `IMPLEMENTED_LOCAL / TESTED_LOCAL_BUILD / TESTED_LOCAL_UI_CAPTURE / PARTIAL_VISUAL_ACCEPTANCE`。
- r97 Release 构建退出码 0；16 路由、Aurora/Monochrome 双主题、1920×1080/720×900 DIP 及 Home 900×900 共 66 张原生 Avalonia 截图，另有 Reader/Evidence 在 1280×900、1024×768 的 4 张窄宽回读截图，共 70/70 成功。
- Home 已将“今日学习 + 快速捕获”置于主内容区，隐藏未提供真实数据的 KPI 占位并显示 Core-backed 最近证据空态；Reader 三栏和 Evidence 表格已调整响应式断点。11 个主导航入口为语义图标。
- Green 独立验收目录已逐文件更新为 r97，并已重新启动供用户查看；原稳定版 `ArcheAxis.exe`、`archeaxis.sqlite`、`启动星环知识.vbs` 保留。候选只使用独立 `candidate-workspace.sqlite`。
- UI 全目标仍为 `PARTIAL`；截图生成不是逐像素视觉验收，也不是后端交互验收。

## 路径

1. 正式源码工作树：`D:\All projects\ArcheAxis-Knowledge-OS`
2. Green 隔离 UI 任务树：`D:\All projects\ArcheAxis.Knowledge.Green-x64\.ui-task-tree\ArcheAxis-Knowledge-OS-mainline`
3. Green 验收入口：`D:\All projects\ArcheAxis.Knowledge.Green-x64\AAOS-Frontend-Acceptance-v4\Start-AAOS-Frontend-Acceptance-v4.cmd`
4. 验收截图：`D:\All projects\ArcheAxis.Knowledge.Green-x64\AAOS-Frontend-Acceptance-v4\screenshots\`（70 张；manifest 70/70）
5. r97 候选发布目录：Green UI 任务树下 `.project-local\acceptance\AAOS-UI-CANDIDATE-20260928-r97\`
6. 截图清单：验收目录 `screenshots\capture-manifest.json`

Green 项目根不是 Git 工作树；隔离源码仓库在 `.ui-task-tree` 下。

## 视觉母版和资产

- B03/B05 是页面结构与内容母版，B10 是风格、图标、交互、动效参考，B04/B06/B07/B09 补充组件与响应式规则。
- B10 没有可独立部署的图片/Icon 包；品牌、图标、图表用 Avalonia 原生矢量/控件复刻。Home 使用 Aurora 和 Monochrome 双主题 Hero 生成图。
- r97 Home 已按“学习/待处理/最近知识优先，统计为辅”重排；当前 KPI 占位隐藏，最近证据由 Core 请求填充，Core 离线时如实显示空态。B03/B05 逐页精确视觉差分仍未通过。
- UI Asset Index 与 Fidelity Status 仍需随完整资产/逐页差分工作更新，不能因截图矩阵通过而标记全量完成。

## 构建与回读

- Release `win-x64` 构建退出码 0；SDK 10.0.400；通过项目 `scripts/runtime/dev.py` 使用隔离目录构建。
- DLL SHA-256：`C8F40B3C905A918BAFA915FCC11531419C5DC1E738EA9FC4E2B8E318B954D51E`；验收目录 DLL 哈希一致。
- 截图：70/70 成功，失败 0；包含 Reader/Evidence 的中等宽度视图。此前 125% 主矩阵的逻辑尺寸→物理像素映射一致。
- NuGet 漏洞服务索引不可达（`NU1900`）；全套测试 `NOT_EXECUTED`。新增定向契约测试 RED→GREEN，1 passed；标准项目测试入口曾因 `uv trampoline ... permission denied` 无法启动，改用 bundled Python 加载现有 pytest 环境执行定向测试。

## 未完成/阻塞

- Core 未包含在验收包，运行窗口为 `core offline`；真实数据读写、按钮端到端及冷启动持久化未验证。
- B10 浏览器母版 `file://` 被浏览器安全策略阻止，逐像素对照为 `UNVERIFIED`。
- 100%/125%/150%/200% Windows DPI、多显示器、中文 IME、屏幕阅读器、键盘焦点完整路径尚未单独回读；四张中等宽度 capture 不是完整 DPI 矩阵。
- 动态轨道动画和 reduced-motion 逐帧对照、全页面细节差异及图标/配图资产逐项映射尚未完成。
- 用户之前报告的 `0xe0434352` / 空地址异常没有进程 EventLog、dump、确切运行路径和依赖证据；未确认根因或修复。
- 完整 UI fidelity 仍 `PARTIAL`；R6 UI 子任务状态应以 `docs/current/R6-STATE.json` 的当前证据为准，不由这份交接摘要改写。

## 回滚及发布状态

- 关闭验收窗口并通过 Green 原启动入口回到稳定版；稳定程序与主数据库未覆盖。
- r94→v4 曾发生截图目录旧图未被覆盖；本轮逐文件覆盖后回读 Home/Reader/Evidence 代表图哈希、DLL 哈希和截图清单，70 张 PNG、manifest 70/70。
- Git 提交/推送/合并未执行。现有工作树有用户修改；双端并无可确认的共同远端目标，不将本地同步称作远端上传。
