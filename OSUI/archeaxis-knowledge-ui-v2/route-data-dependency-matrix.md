# 路由与数据依赖矩阵

所有路由在本轮均由 `ArcheAxisUIAdapter` 的 Mock 实现驱动；最终真实 URL、Tauri command、SQLite 查询与文件系统操作均为 `UNBOUND`。

| Route ID | 页面 | 主要 Adapter 方法 | 状态 | 真实绑定 |
| --- | --- | --- | --- | --- |
| `workspace.overview` | 工作台总览 | `getWorkspaceOverview` | AVAILABLE | UNBOUND |
| `workspace.intake` | 通用摄取 | `createIntakeDraft`, `inspectIntake`, `submitIntake` | PARTIAL | UNBOUND |
| `workspace.jobs` | 任务与回执 | `listJobs`, `retryJob` | AVAILABLE | UNBOUND |
| `library.sources` | 资料库 | `listSources`, `getOriginalAsset` | AVAILABLE | UNBOUND |
| `library.reader` | 多格式阅读器 | `getDocument`, `resolveAnchor` | PARTIAL | UNBOUND |
| `library.canvas` | 知识 Canvas | `getDocument`, `resolveAnchor` | AVAILABLE | UNBOUND |
| `evidence.workbench` | Claim–Evidence | `getClaimEvidence`, `recordReviewDecision` | PARTIAL | UNBOUND |
| `evidence.claims` | 复核队列 | `listClaims`, `recordReviewDecision` | PARTIAL | UNBOUND |
| `learning.home` | 学习主页 | `listLearningRoutes` | PARTIAL | UNBOUND |
| `learning.session` | 专注复习 | `getLearningSession`, `recordLearningResponse` | PARTIAL | UNBOUND |
| `learning.teachback` | Teach Back | `submitTeachBack` | PLANNED | UNBOUND |
| `ai_asset.registry` | AI 资产注册表 | `listAIAssets` | PARTIAL | UNBOUND |
| `ai_asset.detail` | AI 资产详情 | `getAIAsset`, `decideAIAsset` | PARTIAL | UNBOUND |
| `settings.capabilities` | 能力矩阵 | `getCapabilityMatrix`, `getSettings` | AVAILABLE | UNBOUND |
| `learning.visual_lesson` | 动态视觉课件 | 不发请求 | PLANNED | UNBOUND |
| `learning.spatial_memory` | 空间记忆 | 不发请求 | PLANNED | UNBOUND |

## 事件占位

页面只允许订阅领域事件摘要：`archeaxis.source.intake.updated.v1`、`archeaxis.conversion.job.updated.v1`、`archeaxis.evidence.review.updated.v1`、`archeaxis.learning.session.updated.v1`、`archeaxis.ai_asset.lifecycle.updated.v1`、`archeaxis.job.receipt.recorded.v1`。事件对象不得直接渲染。
