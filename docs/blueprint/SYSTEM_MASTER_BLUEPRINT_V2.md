# System Master Blueprint — 系统总蓝图 V2（AXW-1200/1205）

> 权威：任务包 v1 2026-08-11
> 状态：**binding_long_term**。完整系统蓝图永久保留，不等于同时实现。

## 1. 两条路线（同时成立）

```text
当前 Release Spine（必须先可靠）
真实 PDF/多格式 → 原件保全 → 可解释转换 → 阅读/编辑 → 证据锚点
→ 开放 Vault 往返 → 人类学习 ↔ AI 资产双向学习最小闭环 → 稳定单用户桌面版

完整系统蓝图（必须永久保留）
研究与知识生产 → 完整学习方法 → 课程/动态视觉/动画/仿真
→ 2D/2.5D/3D 空间记忆 → VR/AR → 多设备/扩展/可选协作
```

## 2. 系统级能力地图（P0-P10）

| Pillar | 能力 | 状态 |
|---|---|---|
| P0 | 原件、来源、转换与文档理解 | `binding_core`，H0-H2 |
| P1 | 证据、知识与研究生产 | `binding_core`，H1 |
| P2 | 人类学习系统 | `binding_core`，H4 |
| P3 | AI 学习资产与受控调用 | `binding_long_term`，H4-H8 |
| P4 | LER 视觉教学与课件 | `binding_long_term`，H6-H7 |
| P5 | 空间记忆与 3D/VR/AR | `binding_long_term`，H7-H8 |
| P6 | 研究、课程与项目工作空间 | `binding_long_term`，H6-H7 |
| P7 | 开放互操作与生态适配器 | `binding_core`，H3 |
| P8 | 搜索、图谱、模型、资源与隐私治理 | `binding_core`/`long_term` |
| P9 | 桌面、平台、扩展与可选协作 | `binding_core`，H0-H5 |
| P10 | 严格受限的探索能力 | `exploration`，H8-H10 |

完整字段见 `CAPABILITY_ATLAS_V2.yaml`（CAP-0010~0160）。

## 3. 关键长期合同（不可删除）

### 3.1 人机双向双学习（P3 + P2）

```text
EvidenceBundle
  ├─→ HumanLearningAsset → Practice / Recall / Transfer / TeachBack
  │       └─→ HumanCorrection / Reflection / OutputProof → Candidate Review
  │
  └─→ GovernedAIAsset → Call / Reuse / Compose / Evaluate
          └─→ AIObservation / Conflict / Gap / EvalResult → Candidate Review

Candidate Review → Evidence / Knowledge / LearningAsset / AIAsset 的受控修订、撤销或保持原状
```

两条链路共享可信基底，各自"学习成功"指标不能混同；一侧结果不能自动改写另一侧正式知识状态。

### 3.2 LER 是正式产品层（P4）

Fact → Memory → Visual → Teaching 四层 + `LearningRoutePackage`。
所有 LER 资产必须拥有：来源/证据锚点、版本、生成过程、输入/输出、许可、开放导出、静态或无障碍 fallback 和损失说明。

### 3.3 空间记忆引擎无关数据合同（P5）

```text
SpatialMemoryPackage
  World → Palace → Room → Locus → Object → Route
  + StablePosition + Cue + Knowledge/Evidence Anchor
  + MoveMap + ReviewEvent + Fallback + AssetLedger
```

替代表现层：文本路线、2D Map、CSS/Canvas 2.5D、WebGL/Three/R3F 3D、A-Frame/WebXR VR/AR。
不得在 H0-H5 固定永久引擎赢家；商业资产不得绕过许可证账本。

### 3.4 开放互操作 C4 安全往返（P7）

Markdown、Properties、Links/Backlinks、Attachments、JSON Canvas、增量变更、expected-hash、原子写、备份、冲突和回滚。
适配池：Obsidian 开放格式/URI/Canvas、Zotero/BibTeX/CSL、Anki、Joplin、Logseq、SiYuan、Readwise 等。每个 Adapter 独立记录版本、许可、读写范围、损失、fixture、往返、升级、回滚和 kill switch。

## 4. Horizon 激活政策

| Horizon | 目标 | 状态 |
|---|---|---|
| H0 | Product Truth、真实 PDF、生存修复 | critical_now |
| H1 | RawAsset、转换、EvidenceAnchor、PDF | core_next |
| H2 | Office、OCR、网页、媒体 | 逐格式激活 |
| H3 | 开放 Vault、Editor、Canvas | 工作台纵切 |
| H4 | 双向学习最小闭环 | 先最小可证明 |
| H5 | 稳定桌面 | 性能/无障碍/恢复 |
| H6-H10 | 研究/课程/视觉/空间/3D/协作 | binding_long_term / exploration |

## 5. 修订记录

| 版本 | 日期 | 变更 | 授权 |
|---|---|---|---|
| V2 | 2026-08-12 | 系统总蓝图冻结（AXW-1200/1205） | Owner 任务包 |
