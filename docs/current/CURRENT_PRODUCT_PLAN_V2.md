# Current Product Plan — 当前产品计划 V2（AXW-1206/1210）

> v0.6.8 已发布基线（2026-08-23，承接 v0.6.0 任务包）：旧快照和笼统的“supported”表述已归档为历史规划输入。六空间真实 API 闭环、Tauri-origin token/CORS、原件读回与 AI 资产治理已推进并验证；精确 SHA CI、三包 Windows 生命周期和公开资产读回已通过，当前状态为 `v0.6.8 stable — RELEASED`。规范实现线为 `frontend/` + 根 `src-tauri/`，详见 `docs/architecture/ADR-060-001-IMPLEMENTATION-LINE.md`。

> 权威：v0.6.0 最小可信闭环任务包（2026-08-20）+ 当前 exact-SHA 报告
> 状态：阶段描述可随真实实现与 Receipt 更新；能力边界与命名不可漂移

## 1. 当前 Release Spine（必须优先可靠）

```text
真实 PDF/多格式 → 原件保全 → 可解释转换 → 阅读/编辑 → 证据锚点
→ 开放 Vault 往返 → 人类学习 ↔ AI 资产双向学习最小闭环 → 稳定单用户桌面版
```

**当前第一项 = 可安装、可导入、可阅读、可重启回读的真实材料流。**

## 2. 当前实现状态

权威逐项审计见 [`AXR_060_COMPLETION_AUDIT_2026-08-23.md`](AXR_060_COMPLETION_AUDIT_2026-08-23.md)。以下状态不由发布版本号自动提升：

| 能力 | 状态 | 证据 |
|---|---|---|
| 真实 PDF 导入、原件 SHA、页锚点与 LossReport | `TESTED_LOCAL` | 当前 Golden PDF 生产主链定向测试 |
| 四库 quick/advanced、迁移与重启回读 | `TESTED_LOCAL` | setup/manifest/migration/R1 定向测试 |
| 审核后 Human/AI 双主体写入 | `TESTED_LOCAL` | 主链、学习审批与机器知识定向测试 |
| 开放导出、备份与 fresh workspace 回读 | `TESTED_LOCAL` | export/backup 定向测试 |
| 六空间真实 API 闭环 | `PASS_LOCAL` | Workspace、Library、Evidence、Learning、AI Assets、Settings 均接真实后端；Chromium Tauri-origin 联调通过 |
| 根 React Chromium Golden Journey | `PARTIAL_BROWSER` | Tauri-origin 六空间真实后端点击联调 PASS；安装/升级/卸载/导出串行旅程仍未执行 |
| Recovery Shell 完整操作 | `PARTIAL` | 已有失败保活/retry；缺日志、安全模式、备份恢复、退出 |
| Tier A 完整格式矩阵/nightly | `NOT_EXECUTED_CURRENT_SHA` | 单格式/Golden 定向证据不等于完整矩阵 |
| Setup/Green/Portable 公开交付 | `RELEASE_PUBLISHED` | v0.6.8 精确 SHA CI、生命周期及下载读回 |
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
