# Current Product Plan — 当前产品计划 V2（AXW-1206/1210）

> v0.6.2 修复发布基线（2026-08-23，承接 v0.6.0 任务包）：本页此前的 `b97035e` 快照和“supported”表述均为历史规划输入。`v0.6.1` 发布运行暴露身份注入后未重建 NSIS 的缺陷且标签不可改写；当前状态统一为 `v0.6.2 development — PARTIAL`，只可由 exact-SHA Receipt 与发布资产读回提升；规范实现线为 `frontend/` + 根 `src-tauri/`，详见 `docs/architecture/ADR-060-001-IMPLEMENTATION-LINE.md`。

> 权威：v0.6.0 最小可信闭环任务包（2026-08-20）+ 当前 exact-SHA 报告
> 状态：阶段描述可随真实实现与 Receipt 更新；能力边界与命名不可漂移

## 1. 当前 Release Spine（必须优先可靠）

```text
真实 PDF/多格式 → 原件保全 → 可解释转换 → 阅读/编辑 → 证据锚点
→ 开放 Vault 往返 → 人类学习 ↔ AI 资产双向学习最小闭环 → 稳定单用户桌面版
```

**当前第一项 = 可安装、可导入、可阅读、可重启回读的真实材料流。**

## 2. 当前实现状态（以 main b97035e 为准）

| 能力 | 状态 | 证据 |
|---|---|---|
| 真实 PDF 导入/阅读/渲染 | `supported` | PR #72/#74，浏览器验证 |
| 证据锚点 API + PDF 批注 | `supported` | PR #78，浏览器验证 |
| DOCX Adapter | `in_progress` | PR #79（诚实降级） |
| 多格式摄入路由（Magika 内容检测） | `supported` | PR #81/#82 |
| 转换质量门（CER/WER） | `supported` | PR #82 |
| 证据连接器（Crossref/DataCite/OpenAlex/Wikidata） | `in_progress` | PR #82 |
| JSON Canvas 验证/处理 | `supported` | PR #81/#82 |
| FSRS 学习调度桥接 | `in_progress` | PR #82 |
| OCR/ASR bake-off 框架 | `in_progress` | PR #83（引擎未装） |
| OCR 真实可用 | `in_progress` | Tesseract 已装，PaddleOCR/RapidOCR 待 bake-off |
| ASR | `planned` | faster-whisper/whisper.cpp 桩就绪 |
| 3D/VR/AR / 动画 / 仿真 / 空间记忆 | `planned`（长期蓝图） | 未实现，不展示 |
| 通用 Agent / 自治演化 | `exploration` | 未实现，不展示 |

## 3. 公开页面强制状态标签

`已支持 / 适配中 / 未来蓝图 / 实验原型`

- 未来能力不得在一级导航出现空页面
- PDF/OCR/ASR/全网验证不能被元数据或菜单冒充完成
- UI 保持中央主工作区：阅读、编辑、Canvas、表格、课程、证据与 AI 资产；不以聊天或 Agent 为中心

## 4. 近期执行队列（AXW 规划治理编号）

| 任务 | 状态 |
|---|---|
| AXW-1200 事实快照 | done |
| AXW-1201 命名契约 | done（文档+UI 阶段 merged #85/#86/#87） |
| AXW-1202 产品身份 | done |
| AXW-1203 Capability Atlas | done |
| AXW-1204 需求/范围/任务图 | done |
| AXW-1205 LER 蓝图 | done |
| AXW-1206 当前现实 | done |
| AXW-1207 互操作策略 | done |
| AXW-1208 命名迁移计划 | done（执行阶段 3+ planned，需 Owner 授权） |
| AXW-1209 文档投影门禁 | done（命名禁词 lint merged #88） |
| AXW-1210 Release Spine | done（主线保持：真实材料进入→证据→双向学习闭环） |

## 5. 修订记录

| 版本 | 日期 | 变更 |
|---|---|---|
| V2 | 2026-08-12 | 按任务包重写当前计划（AXW-1206/1210） |
