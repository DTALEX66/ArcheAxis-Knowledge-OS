# LER — Visual & Spatial Learning Blueprint V1（AXW-1205）

> 权威：任务包 v1 2026-08-11 §4.5/§4.6
> 状态：**binding_long_term**（蓝图即交付；能力激活 H1-H8）
> LER = Learning Experience & Representation Layer，正式产品层，不是设计装饰。

## 1. 四层模型

```text
Fact（事实/证据层）→ Memory（记忆/复习层）→ Visual（视觉表征层）→ Teaching（教学表达层）
```

`LearningRoutePackage` 连接四层与原文/证据/知识版本/练习。

## 2. 能力族与保留内容

| 层级 | 能力族 | 正式保留内容 | Horizon |
|---|---|---|---|
| 结构化基础 | 表格、卡片、对比、时间线、层级图、Learning Map、Canvas、Graph | 连接原文、证据、知识版本和练习 | H3+ |
| 视觉教学 | 图解、概念图、数据图表、标注图、讲义、课件、演示 | Visual Teaching、Courseware、可审阅脚本与素材清单 | H6 |
| 动态解释 | 动画、步骤演示、动态视觉课件、过程/因果模拟 | Animation Script、Scene/Step、输入输出、静态帧/文本降级 | H7 |
| 互动实践 | Simulation & Practice Lab、交互演示、可执行练习、实验记录 | 操作事件、反馈、评估、可复现实验配置 | H7 |
| 空间记忆 | 2D 地图、2.5D 路线、记忆宫殿 | Locus、路线、对象、线索、移动映射、复习事件 | H7 |
| 沉浸空间 | 3D、VR、AR 记忆宫殿与学习场景 | 引擎无关场景数据、模型/纹理/声音/动画资产账本、2D/text fallback | H8 |

## 3. 统一资产 Manifest 最小契约

所有 LER 资产包（Courseware/Visual/Animation/Simulation/SpatialMemory）必须包含：

```yaml
manifest:
  asset_id: <stable-id>
  type: courseware|visual|animation|simulation|spatial_memory
  source_evidence_anchors: []
  version: <semver>
  generation_process: []
  inputs: []
  outputs: []
  asset_licenses: []      # 模型/纹理/HDRI/字体/声音/动画资产独立记录
  fallback: []            # 静态帧/文本/无障碍降级
  export_format: []
  loss_report: []
  performance_budget: {}
  accessibility: {}
  learning_evidence: []   # 学习效果评估证据
```

## 4. 渐进策略（2D → 2.5D → 3D → VR/AR）

| 层 | 技术 | 条件 |
|---|---|---|
| 文本路线 | Markdown/TXT | 永备 fallback |
| 2D Map | SVG/Canvas | 无依赖 |
| 2.5D | CSS/Canvas 投影 | 低预算 |
| 3D | WebGL/Three/R3F | 性能预算 + 学习证据 |
| VR/AR | A-Frame/WebXR | 设备能力探针 + 无障碍降级 |

**高级视觉或沉浸能力不能凭"更酷"晋升**。必须评估可用性、认知负荷、行为、延迟保持和迁移效果；没有证据时仅能标 `prototype` 或 `experimental`。

## 5. Spatial Memory 数据合同（engine-agnostic）

```text
SpatialMemoryPackage
  World → Palace → Room → Locus → Object → Route
  + StablePosition + Cue + Knowledge/Evidence Anchor
  + MoveMap + ReviewEvent + Fallback + AssetLedger
```

- canonical 数据不是 Three.js/Unity/WebXR 场景文件，而是引擎无关的包结构
- 不得在 H0-H5 固定永久引擎赢家
- 商业模型/纹理/HDRI/字体/声音/动画资产必须过许可证账本

## 6. 学习效果指标（不设"沉浸感即学习效果"断言）

可用性、认知负荷、行为、延迟保持、迁移效果。

## 7. 修订记录

| 版本 | 日期 | 变更 | 授权 |
|---|---|---|---|
| V1 | 2026-08-12 | LER 蓝图冻结（AXW-1205） | Owner 任务包 |
