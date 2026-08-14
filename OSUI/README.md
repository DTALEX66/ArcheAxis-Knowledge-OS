> **状态：设计参考 / 被采纳资产源（AXW-UI-803，2026-08-15）**
>
> 本目录不再是可运行 UI 真相。当前唯一运行前端是 Tauri `frontendDist`
> （`desktop/bootstrap/`，Recovery Shell）与后端 `/workspace` 页面；OSUI
> 的组件、配色与布局作为设计资产被采纳，任何改动不影响运行 UI。
> 迁移完成（AXW-UI-801 React 渐进迁移）后本目录归档为纯参考。

# OSUI 前端交接包

## 范围

此目录承载 ArcheAxis Knowledge 的 OSUI 前端交付物：两套界面实现、原始任务包，以及本轮生成的可预览知识工作台。它仅包含前端演示与 Mock Adapter 边界，不包含真实后端、端点、个人数据、凭据或运行时缓存。

## 目录

- `archeaxis-knowledge-ui/`：基础版本的多页面前端 UI。
- `archeaxis-knowledge-ui-v2/`：当前主交付版本。各路由在保留 `app.js` 的 Mock Adapter 合同后加载 `app-v3.js`，形成统一的桌面工作台壳层、原件阅读器、证据账本、Canvas 与学习任务面；视觉规则位于 `liquid-glass.css`。
- `deliverables/archeaxis-knowledge-workspace.html`：本轮主预览页面，展示“原件阅读面 + 证据路径 + 上下文检查器”的前端工作台。
- `deliverables/archeaxis-knowledge-workspace-preview.png`：主预览页面的静态核验图。
- `ArcheAxis-Knowledge-OPEN-DESIGN-UI-TaskPack-v1-2026-08-12.zip`：随本地 OSUI 项目一并交接的任务包归档。

## 运行与边界

页面可作为静态 HTML 预览。请从 `archeaxis-knowledge-ui-v2/index.html` 打开工作台总览；各功能页均有语义化 HTML 入口。界面中的数据、状态和交互均为前端演示；`Mock Adapter` 与 `UNBOUND` 表示后端集成尚未接入。后续实现应复用既有 `mock-adapter.js` 的边界约定，并在连接真实数据前单独完成接口与安全评审。

## 本轮核验

- 主工作台 HTML 已通过内嵌脚本与完整标签的静态检查。
- 已导出并人工检查主工作台预览图。
- 未执行真实接口、后端服务、发布部署或用户数据读取。

## 交接记录

本目录由 OSUI 本地前端项目导入至 `DTALEX66/ArcheAxis-Knowledge-OS` 的 `OSUI/` 子目录。提交记录是本次交接的可回滚边界。

详见 `HANDOFF-2026-08-12.md`，其中包含交付范围、路由入口、验证证据、未绑定接口和后续绑定顺序。
