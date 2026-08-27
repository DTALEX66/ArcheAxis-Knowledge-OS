# 界面设计与生产接线历史

> 本文记录设计资产、生产入口和发布版本之间的真实关系。设计文件存在不等于生产已采用。

## 时间线

| 日期 | Commit / Release | 事实 | 当时证据层 |
| --- | --- | --- | --- |
| 2026-08-12 | `d64ccff` | 交付 OSUI v3 研究工作台：Archive Desk、证据关系、学习工作台、视觉课件和空间记忆设计 | 设计原型；Mock/UNBOUND |
| 2026-08-13 | `d0fb756` | 清理后的 OSUI bundle 进入仓库 | 设计资产；未绑定生产路由 |
| 2026-08-15 | `588e5b9` | 文档记录 OSUI downgrade，但没有把 OSUI 变成生产入口 | 文档层 |
| 2026-08-22 | `v0.6.7` | 发布继续使用旧 Workspace 壳层 | 功能/发布层通过；设计层未验收 |
| 2026-08-23 | `v0.6.8` | 六空间闭环发布，仍未生产接入 OSUI | 功能层扩展 |
| 2026-08-23 | `v0.6.9` | Recovery Shell 发布，仍未生产接入 OSUI | 壳层/发布层 |
| 2026-08-23 | `v0.6.10` | Activity Dock 发布，仍保留普通卡片后台构图 | 功能层 |
| 2026-08-27 | `v0.6.11` | R2 truth/product-base 发布；仍未把 OSUI 和中文一致性作为发布门 | 产品能力层通过、UI 设计层漏验 |
| 2026-08-27 | 当前生产接线 | OSUI token、Archive Desk 壳层、中文优先词典、视觉课件/空间记忆规划面和设计史进入生产 Workspace | 生产迁移中 |

## 根因

1. `production-handoff-manifest.json` 明确写着 `workbench-prototype-unbound-v3`，但后续没有生成对应的 production binding task。
2. 发布资格矩阵覆盖代码、数据库、安全、浏览器功能、Tauri 和安装生命周期，却缺少“设计稿视觉对比”和“中文一致性”门。
3. OSUI 原型的 Mock 数据不允许直接发布，因此团队选择继续维护旧 UI，而不是实施真实 Adapter；这把“不能直接复制 Mock”错误演化成“完全不使用设计”。
4. 进度文档不断记录新能力和新 release，却没有单一页面说明设计底座、吸收边界、路线图和生产状态。

## 权威关系

```text
OSUI DESIGN-v2 / previews / component manifest
        ↓ 视觉与信息架构合同
生产 Workspace DOM/CSS/JS
        ↓ 真实 Adapter
Workspace API / canonical SQLite truth
```

设计稿不得反向定义假数据；旧端点也不得反向破坏设计中的原件、主张、证据、学习和 AI 资产边界。

## 发布门修订

以后每个 UI 版本必须同时提供：

- 设计源及版本；
- 生产绑定矩阵；
- 中文词典扫描；
- 桌面与窄屏真实截图；
- 可见 Mock/UNBOUND/内部 ID 扫描；
- 与权威设计图的视觉复核；
- 浏览器功能与 console 错误门；
- Tauri/WebView 和安装生命周期。
