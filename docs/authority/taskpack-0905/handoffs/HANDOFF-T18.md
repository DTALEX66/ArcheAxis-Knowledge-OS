# HANDOFF — T18 GPT/图像模型驱动前端全面升级（CODEX）

交接人：DeepSeek（集成者）· 2026-09-05 · 难度：高 · 目标代理：CODEX

## 目标
- 以 12-UI-REDESIGN.md 为输入重新规划用户旅程/信息架构/布局/阅读器/组件状态（旧界面仅参照，允许彻底更换布局）；
- 核验执行时最新可用 GPT/视觉/图像模型：推理模型写设计规格、图像模型做风格探索与素材、视觉审查截图对照；记录模型与提示版本；
- 产出可编码设计 token、关键页状态图、动效/键盘/高对比/缩放规范；真实 UI 映射不缺席。

## 上下文
- 12-UI-REDESIGN.md（任务包内）定义重设计范围；产品当前壳：apps/ArcheAxis.Desktop（Avalonia 12.1.x/.NET10）已有 App/MainWindow/Views 骨架与 CoreSupervisor。
- T18 先于 T12；T12 消费本任务产出（Views/ViewModels/Services 实施由 T12 负责）。
- 阻塞记录：产品级 GPT/图像凭据未配置；本机可用 qwen2.5vl:7b（ollama 11434）做视觉审查替代初稿，
  设计规格以本地/可用模型推理完成并注明模型与提示版本。若 CODEX 通道具备云端模型凭据，可自行使用（勿入库）。

## 允许路径（任务包 T18）
docs/design/vnext/**、apps/ArcheAxis.Desktop/Design/**、apps/ArcheAxis.Desktop/Assets/**、tests/journey/visual/**。

## 验收（任务包 T18）
- 12-UI-REDESIGN.md 全部核心场景都有设计与实际 UI 映射；
- 模型输出落实为 Avalonia 组件；效果图不能代替真实可操作界面。

## 输出契约
- 设计 token/规范/状态图/映射表 + 所用模型与提示版本清单 → docs/design/vnext/（提交）；
- 不直接大改 View 实现（那属 T12）；可提供 Design/Assets 落地片段与视觉测试夹具；
- 报告 commit SHA 与验收对照。
