# ArcheAxis Desktop 云端重审与前端修改包

- 仓库：`DTALEX66/Cognitive-Loop-OS`
- 云端分支：`main`
- 本次连接可见基线：`2cdf11e2b85154c15cfd621c04dae8f6c90d693b`
- 包版本：`v1.0`
- 生成时间：`2026-07-27T16:38:46+00:00`
- 目标：把现有 Cognitive Workspace 升级为统一的 **Human + Agent + Cognitive Governance Desktop**。

## 先看结论

当前前端不是空页面，已经具备真实的 Research、Knowledge、Learning、Machine Knowledge、
Job、Outbox、Receipt 和 Lifecycle 投影；但是产品形态仍然是“治理后台”，尚未形成每天可用的
Agent 桌面。

这次修改不推翻现有后端和 Tauri 壳。采用以下融合路线：

1. 保留当前 Python / FastAPI / SQLite / Tauri 真相链。
2. 以旧概念图的深色紫晶皮肤作为旗舰主题：**元枢·紫曜 / Violet Core**。
3. 吸收新版 OpenHuman 的人机入口和双层导航。
4. 吸收 OpenHands、Cursor、Windsurf 的任务指挥逻辑。
5. 保留 Cognitive-Loop-OS 独有的 Source、Claim、Evidence、Permission、Trace、
   Evaluation、Lesson 和知识晋升体系。
6. 不伪造多 Agent、异步 Worker、实时进度或不存在的工具。

## 推荐执行顺序

- 先执行 `Desktop A1`：统一桌面壳、紫曜主题、动态导航、真实状态卡片、右侧检查器框架、
  底部真实活动坞。
- A1 验收并合并后，再执行 `Desktop A2`：任务驾驶舱和公开任务投影。
- A2 完成后执行 `Desktop A3`：认知画布与证真回放。
- 多 Agent、电脑控制和社区能力继续后置。

## 关键文件

- `01_CLOUD_REAUDIT.md`：云端重新审计。
- `02_FRONTEND_FUSION_MASTER_PLAN.md`：前端融合总方案。
- `04_VIOLET_CORE_DESIGN_SYSTEM.md`：紫曜主题设计系统。
- `07_DESKTOP_A1_TASKPACK.md`：第一阶段可直接执行任务。
- `10_HERMES_MASTER_PROMPT.md`：直接发给 HERMES 的总命令。
- `prompts/HERMES_EXECUTE_A1.txt`：第一阶段执行提示词。
- `prototype/archeaxis_desktop_a1.html`：离线结构原型。
- `references/`：你上传的 OpenHuman 与旧紫晶概念图参考。

## 基线漂移规则

你表示云端有新更新，但本次 GitHub 连接可见的 `main` 头仍为 `2cdf11e2b85154c15cfd621c04dae8f6c90d693b`。
执行前必须运行 `scripts/00_verify_baseline.ps1`：

- 如果远端已经更新，不得硬重置、不得覆盖；
- 先读取新 HEAD 和差异；
- 在新 HEAD 上重放本修改包；
- 禁止直接以本包中的旧 SHA 强制写回。
