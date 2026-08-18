# 三项目分层架构决策（v4 · 知识中心 + 开放转化器生态）

本文档锁死三项目关系。核心不变式：ArcheAxis 是唯一知识总库 + 双向人机重型学习系统（定位永不漂移）；所有知识都归 ArcheAxis；周边项目只是知识的调用者与归档回写者（转化器），且未来开放，不限于现有两个项目。

## 1. 唯一知识总库（ArcheAxis = OS 系统）

所有知识都归 ArcheAxis。ArcheAxis 定位永不漂移：双向人类到 AI 的重型学习系统级项目（NOT an Agent OS，未来蓝图锁定重型学习系统级）。

知识分两侧：
- 人类学习侧：知识直接留在 ArcheAxis 供人类学习（摄入/结构化/课程/练习/复习/掌握/Teach Back/迁移），不转化出去
- AI 侧：知识通过 API 供给各转化器项目，由项目转化沉淀为可执行资产

## 2. 转化器项目（开放集合，当前两个 + 未来 N 个）

周边项目是知识的调用者与归档回写者，不是知识拥有者。它们只做两件事：
- 调用：从 ArcheAxis 读取知识
- 归档：把执行产出的新知识/经验回写 ArcheAxis 成为 Candidate

中间转化：AI 侧知识在项目中转化沉淀为本项目对应的可执行资产（规则/规范/技能/插件）：
- WORK-LAB：知识 → Rules / Skills / plugins / MCP 声明 / workflow policy（控制平面配置）
- DESIGN-LAB：知识 → 设计规范 / 方法 / Rubric / Domain 能力（设计智能）
- 未来项目 X/Y/Z：同样模式接入 ArcheAxis，做调用 + 转化 + 归档，不限于现有两个

## 3. 知识生命周期循环（单向真源 + 双向流转）

ArcheAxis 知识（真源，唯一治理权）
  → 项目调用（读知识）
  → 项目转化沉淀（知识 → 规则/规范/技能/插件）
  → 项目执行（用可执行资产跑，宿主/客户端执行）
  → 产出新知识/经验
  → 项目归档回写（Candidate 回写 ArcheAxis）
  → ArcheAxis 治理（candidate → review → verified）
  → 再次转化（新知识变成更新的规则/规范/技能）
  → 人和 AI 双向进化，越用越强

## 4. 分层

### 第一层 ArcheAxis（唯一知识总库 + 人类学习系统，NOT Agent OS）
- 所有知识真源 + 唯一治理权（candidate → verified）
- 人类学习侧直接在此完成（重型学习链，不转化出去）
- AI 侧知识 API：Knowledge / Memory / Evidence / Reasoning / Learning
- 不存可执行载体，不拥有 Agent 运行时

### 第二层 转化器项目（开放集合，调用 + 归档，不拥有知识）
- 当前：WORK-LAB（控制转化器）+ DESIGN-LAB（设计转化器）
- 未来：任意新项目接入，同样调用 + 转化 + 归档
- 转化产物 = 本项目可执行资产（规则/规范/技能/插件），但知识真源仍在 ArcheAxis

### 第三层 执行（宿主 + 客户端）
- Agent 执行 = 客户端（DSH/Hermes/Codex），模型/视觉运行时 = 宿主（Open Design 等），由 WORK-LAB 治理

## 5. 归属速查

| 内容 | 归属 |
|---|---|
| 所有知识（事实/经验/规则/方法/规范/Lesson）| ArcheAxis 唯一真源 |
| 人类学习侧知识 | ArcheAxis 原生，不转化出去 |
| AI 侧知识 → 规则/规范/技能/插件 | 项目转化沉淀（可执行资产），知识真源仍归 ArcheAxis |
| 项目角色 | 调用 + 归档（回写 Candidate），不拥有知识 |
| 未来新项目 | 开放接入，同样调用 + 转化 + 归档 |

## 6. 红线（8 条，含未来蓝图边界）

1. 人机双向不可偏废（人类重型学习链与 AI 使用链同等重要）
2. ArcheAxis 独立系统，不是任何项目的模块
3. 唯一知识真源 = 唯一治理权（candidate 治理 ArcheAxis 独占）
4. NOT an Agent OS（不拥有 Agent Runtime/多 Agent 调度）
5. 未来蓝图锁定重型学习系统级（FROZEN_EXECUTION_BASELINE H0-H10 + SYSTEM_MASTER_BLUEPRINT_V2）
6. 受控调用边界：ArcheAxis P3 受控调用 = 知识/学习资产调用，不是 Agent/工具调用
7. 受限探索边界：ArcheAxis P10 受限探索 = 知识治理辅助受限 tracer，不是通用 Agent 执行
8. 转化器开放性：周边项目是开放集合（当前 WORK-LAB/DESIGN-LAB，未来任意项目），只做调用 + 转化 + 归档，不拥有知识

## 7. 结论

所有知识归 ArcheAxis（OS 系统）：人类学习侧知识留在 ArcheAxis 供人学习，AI 侧知识转化沉淀为各项目的规则/规范/技能/插件。周边项目（当前 WORK-LAB/DESIGN-LAB，未来开放）只是知识的调用者与归档回写者——调用知识、转化执行、回写沉淀，不拥有知识、不各自建知识库。人和 AI 共享同一份知识底座，知识单向归 ArcheAxis，项目开放扩展，双向进化，越用越强。