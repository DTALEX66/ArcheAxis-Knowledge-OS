# OSUI 前端交接包

## 范围

此目录承载 ArcheAxis Knowledge 的 OSUI 前端交付物：两套界面实现、原始任务包，以及本轮生成的可预览知识工作台。它仅包含前端演示与 Mock Adapter 边界，不包含真实后端、端点、个人数据、凭据或运行时缓存。

## 目录

- `archeaxis-knowledge-ui/`：基础版本的多页面前端 UI。
- `archeaxis-knowledge-ui-v2/`：液态玻璃方向的强化版本；其中 `visual-lesson-studio.html` 等页面通过共享的 `app.js` 与 `app.css` 组织。
- `deliverables/archeaxis-knowledge-workspace.html`：本轮主预览页面，展示“原件阅读面 + 证据路径 + 上下文检查器”的前端工作台。
- `deliverables/archeaxis-knowledge-workspace-preview.png`：主预览页面的静态核验图。
- `ArcheAxis-Knowledge-OPEN-DESIGN-UI-TaskPack-v1-2026-08-12.zip`：随本地 OSUI 项目一并交接的任务包归档。

## 运行与边界

页面可作为静态 HTML 预览。界面中的数据、状态和交互均为前端演示；`Mock Adapter` 与 `UNBOUND` 表示后端集成尚未接入。后续实现应复用既有 `mock-adapter.js` 的边界约定，并在连接真实数据前单独完成接口与安全评审。

## 本轮核验

- 主工作台 HTML 已通过内嵌脚本与完整标签的静态检查。
- 已导出并人工检查主工作台预览图。
- 未执行真实接口、后端服务、发布部署或用户数据读取。

## 交接记录

本目录由 OSUI 本地前端项目导入至 `DTALEX66/archeaxis-workspace` 的 `OSUI/` 子目录。提交记录是本次交接的可回滚边界。
