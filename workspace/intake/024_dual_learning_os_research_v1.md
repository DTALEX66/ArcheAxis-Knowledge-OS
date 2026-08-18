# 024 双向学习知识 OS 调研（V1）+ 在线核实（V2）—— 框架方向影响记录

- 日期：2026-08-18
- 关联文档：docs/three-project-analysis/09_双向学习知识OS调研报告_V1_2026-08-18.md（第 11 节为在线核实附录）
- 影响范围：框架方向（V3 架构参考地图 / 吸收矩阵扩展）

## 结论

1. 调研报告 42 个具名项目经 2026-08-18 在线核实：**41 个真实存在**，仅 "Paperless AI Research Brain" 查无此名（应按能力方向改为 pdf-brain / PaperLeaf 等真实项目）。
2. 匹配度：exact 21 / close 21 / partial 2 / not_found 1 —— 报告主体无系统性虚构，个别描述存在名字歧义（OpenSwarm、Agent OS、AI Desktop Environment）或细节偏差（Hermes Memory OS 层名、DeepTutor "ChatOrchestrator"、Zep CE 停维护）。
3. "无人完整覆盖人机双向闭环" 的定位结论维持：人侧（DeepTutor/Studyield/OpenTutor/FSRS 系）、机侧（Cognee/Graphiti/ReMe/OpenViking/Corpus2Skill/ReasoningBank/EvolveR/Hermes Agent Self-Evolution）、桥（colleague-skill/awesome-human-distillation）各自只覆盖单侧。

## 框架方向影响

- ArcheAxis 定位更新为 **Human–AI Co-Learning Knowledge Operating System（人机双向学习知识操作系统）**：同一知识同时经历人类学习链与机器学习链，掌握结果汇聚为可验证、可持续进化、可调用的知识能力。
- 建议 V3 架构增加：Dual Mastery Engine（Human M0-M7 / Machine K0-K8 / Evidence Maturity 三轴 + Mastery Gap Engine）、Human Knowledge Distillation Engine、Knowledge Distillation Engine（Corpus→Knowledge→Procedure→Skill→Tool）、Skill Runtime、Temporal Knowledge（valid_from/valid_to/supersedes/contradicts）、知识晋升机制（RAW→MEMORY→CANDIDATE→VERIFIED→CANONICAL）。
- 学习状态中立化：Learner Model 属 ArcheAxis 而非 LLM（Tutor MCP 模式），模型仅作临时老师。

## 后续动作（待 Owner 确认）

1. 将第 11.5 节建议并入 docs/three-project-analysis/04_开源项目吸收矩阵.md（S/A/B/C 分级）。
2. 对 S/A 级候选（colleague-skill、Graphiti、DeepTutor、Hermes Agent Self-Evolution 等）做代码级拆解与选型实验。
3. 下一轮深挖方向：Human Mastery → Machine Skill 自动蒸馏的具体实现与评测；Machine Skill → 个人最优学习路径的生成。

## 回滚

- 本记录与调研报告均为新增文档，无代码影响；删除/还原文件即可回滚。


## 2026-08-18 追加：吸收批次已落地（Owner 授权执行）

- 后端 10 个新模块（BKT 知识追踪 / 双轴掌握 / Teach-Back 评分 / 人机蒸馏 / 时序知识图 / 推理记忆 / 技能演化 / 分层记忆 / RAG 真实嵌入索引 / 学习者状态 API）+ 前端 Learning 空间三视图，全部含测试。
- 验证：新后端 61 passed、既有相关 24 passed、前端 vitest 13 passed、tsc 0 错误。
- 明细与未吸收清单见 docs/three-project-analysis/09_双向学习知识OS调研报告_V1_2026-08-18.md 第 12 节。
