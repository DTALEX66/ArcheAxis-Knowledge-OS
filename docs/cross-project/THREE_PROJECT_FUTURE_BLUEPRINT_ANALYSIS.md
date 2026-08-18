# 三项目未来蓝图重新分析（2026-08-18 二次载入）

> 依据：三个项目的未来蓝图/规划文档（非 README 一句话定位）。ArcheAxis SYSTEM_MASTER_BLUEPRINT_V2（P0-P10）+ FROZEN_EXECUTION_BASELINE（H0-H10）；WORK-LAB CONTROL_PLANE_CONVERGENCE；DESIGN-LAB ROADMAP（J0-J4）+ PRODUCT_DEFINITION。

## 1. 三个项目的终极形态（未来蓝图）

### ArcheAxis = 双向人机重型学习系统（终极形态）
- P0-P10 能力地图：P0 原件/文档理解、P1 证据/知识/研究生产、P2 人类学习系统、P3 AI 学习资产与受控调用、P4 LER 视觉教学课件、P5 空间记忆与 3D/VR/AR、P6 研究课程项目工作空间、P7 开放互操作生态、P8 搜索图谱隐私治理、P9 桌面平台协作、P10 严格受限探索
- 完整系统蓝图：研究与知识生产 → 完整学习方法 → 课程/动态视觉/动画/仿真 → 2D/2.5D/3D 空间记忆 → VR/AR → 多设备/协作
- 核心合同 3.1 人机双向双学习：HumanLearningAsset（练习/复习/迁移/TeachBack）+ GovernedAIAsset（调用/复用/组合/评估）→ Candidate Review → 受控修订
- 这是教育/学习系统级的重型愿景，远超知识库，含完整学习方法 + 视觉教学 + 空间记忆 + VR/AR

### WORK-LAB = 本地 AI 工程控制平面（终极形态）
- 五大核心能力：Agent Registry · Work Unit Engine · Runtime Control · Governance Engine · Evidence System
- 报告定义：Local AI Engineering Control Plane，不拥有 Agent 只管理 Agent，Model 与 Agent 分离
- 未来任务：Work Unit 状态机、Agent 注册、Policy Engine、Action Receipt、Runtime Adapter
- 暂缓：Sandbox Manager、MCP Gateway、Memory 三层、Harness Benchmark
- Ignore：不新建 Agent Framework、不做聊天 UI、不做模型训练

### DESIGN-LAB = 设计智能与生产能力实验室（终极形态）
- 六能力域：Design Intelligence / Professional Visual Domains / Visual Quality / Creative Toolchain / Production & Handoff / Research & Evidence
- J0-J4：产品化（Jury V1 + Preflight V1）+ 工具适配器（Adobe PS / ComfyUI / MiniMax H3）
- Host-native：宿主 Open Design 是主角，不重建画布/编辑器/模型网关

## 2. 未来蓝图的三个重叠点（会打架的地方）

### 重叠 1：AI 资产受控调用
- ArcheAxis P3 GovernedAIAsset → Call/Reuse/Compose/Evaluate（知识/学习资产的受控调用）
- WORK-LAB Runtime Control（Agent 生命周期/工具调用/调度）
- 边界：ArcheAxis 调的是知识/学习资产（检索/复用/组合/评估），不调 Agent/工具；WORK-LAB 调的是 Agent/工具执行。同词「调用」两层含义。

### 重叠 2：研究/证据
- ArcheAxis P1/P6 研究与知识生产 + 项目工作空间（通用知识研究：证据→知识）
- DESIGN-LAB Research & Evidence 能力域（设计研究：设计案例/合规/材料规范）
- 边界：通用知识研究（来源/Claim/Evidence 治理）归 ArcheAxis；设计领域研究（设计案例/合规/视觉规范）归 DESIGN-LAB，但其事实性知识归档 ArcheAxis 真源。

### 重叠 3：受控执行/探索
- ArcheAxis P10 严格受限探索能力（exploration，H8-H10）
- WORK-LAB Agent 执行调度（Runtime Adapter）
- 边界：ArcheAxis 探索 = 知识治理辅助的受限 tracer（read file: 级别），不滑向通用 Agent 执行；WORK-LAB 执行 = 生产 Agent 调度。ArcheAxis 必须守住 NOT Agent OS。

## 3. 重新分析结论（未来蓝图层面）

1. 三个项目未来蓝图各自宏大，重叠风险真实存在，集中在「调用/研究/执行」三个词上——同词不同层。
2. ArcheAxis 未来蓝图是重型学习系统（P0-P10 锁定），但它内部的 P3（受控调用）和 P10（受限探索）必须锚定在知识层，不滑向 Agent OS。这是它未来最大的漂移风险。
3. WORK-LAB 未来是控制平面（管 Agent 不拥有 Agent），不滑向运行时——已有明确 Ignore 边界。
4. DESIGN-LAB 未来是设计智能（Host-native），不滑向通用知识/通用 Agent。
5. 分层结论不变（v3.1）：ArcheAxis 重型学习系统（知识真源）+ WORK-LAB 控制平面 + DESIGN-LAB 领域智能；知识全量归档 ArcheAxis，后两者转化。

## 4. 需要在决策文档中新增的未来蓝图边界（3 条）

1. ArcheAxis P3 的「受控调用」= 知识/学习资产的调用复用组合评估，不是 Agent/工具调用（后者归 WORK-LAB）
2. ArcheAxis P10 的「受限探索」= 知识治理辅助的受限 tracer，不是通用 Agent 执行（守住 NOT Agent OS）
3. DESIGN-LAB 的「Research & Evidence」= 设计领域研究（案例/合规/材料），通用知识研究归 ArcheAxis，设计研究的事实性知识归档 ArcheAxis 真源
