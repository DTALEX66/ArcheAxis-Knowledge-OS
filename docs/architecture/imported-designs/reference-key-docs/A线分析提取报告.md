# A线极限增强包 — 深度分析提取报告

> Generated 2026-06-23 | Agent-5 (Lorentz)
> Source: reference/A线极限增强包_vFinal/ (23 files, ~54KB total)

---

## 1. 系统定位

A线从"卡片/复习/宫殿模块"升级为 **Human Learning OS**（人类学习能力增强操作系统）。

```text
A线 = 帮人把信息变成知识，把知识变成记忆，把记忆变成能力，把能力变成输出和可迁移经验的系统。
```

---

## 2. 16大系统总表

| # | 系统 | 解决的问题 | 核心对象 | 关键算法 |
|---|------|-----------|---------|---------|
| 1 | 捕获系统 | 信息怎么进来 | sources/assets/clips | source trust |
| 2 | 知识结构系统 | 信息怎么变知识 | blocks/entities/relations | atomization/graph |
| 3 | 学习诊断系统 | 该从哪里学 | diagnostics | prerequisite scoring |
| 4 | 学习路线系统 | 先学什么后学什么 | routes/units | DAG/topological sort |
| 5 | 认知负荷系统 | 一次学多少 | cognitive_load | load score |
| 6 | 记忆编码系统 | 怎么更容易记 | encodings/anchors | modality fit |
| 7 | 间隔复习系统 | 什么时候复习 | cards/reviews | SRS/SM-2/FSRS |
| 8 | 知识宫殿系统 | 知识放在哪 | palace/room/locus | spatial placement |
| 9 | 主动训练系统 | 怎么练 | quiz/training | weakness priority |
| 10 | 技能实战系统 | 会不会做 | skill_tasks | rubric scoring |
| 11 | 元认知系统 | 是否知道自己会不会 | confidence/reflection | confidence gap |
| 12 | 反馈错误系统 | 错在哪里怎么改 | mistakes/weakness | error taxonomy |
| 13 | 输出教学系统 | 能否讲清楚 | teach_back/reports | explanation score |
| 14 | 学习画像系统 | 个性化怎么做 | learner_profile | adaptive policy |
| 15 | 长期巩固系统 | 知识怎么整合 | consolidation | merge/evolve |
| 16 | A转B翻译系统 | 人学会后机器怎么用 | machine_units | distillation |

---

## 3. 核心算法详解

### 3.1 认知负荷评分 (系统5)

```python
cognitive_load_score = weighted_sum(
    new_concept_count * 0.30,
    prerequisite_gaps * 0.25,
    complexity_level * 0.20,
    attention_span_remaining * 0.15,
    fatigue_index * 0.10
)
# 输出: 0-100，>70触发分块建议
```

### 3.2 记忆编码适配 (系统6)

```python
encoding_fit = max(
    visual_score(auditory_score, textual_score, kinesthetic_score)
)
# 根据学习画像选择最佳编码模态
# 支持: 图表/思维导图/语音/节奏/文字/公式/操作/演练/
#       多模态组合编码
```

### 3.3 间隔复习 (系统7) — 已集成

- **当前实现**: FSRS-5 (19参数权重)，`DEFAULT_W` 已通过优化器调整
- **优化器**: `fsrs_optimizer.py` — 随机爬山法，RMSE 0.3748→0.3628
- **遗留**: SM-2 作为fallback

### 3.4 Rubric评分矩阵 (系统10)

```python
skill_score = sum(
    w[i] * level_score[i] for i in dimensions
) / sum(w)

Dimensions = {
    "correctness": 0.30,    # 正确性
    "completeness": 0.20,   # 完整性
    "efficiency": 0.20,     # 效率
    "clarity": 0.15,        # 清晰度
    "creativity": 0.15,     # 创造性
}
```

### 3.5 元认知信心差 (系统11)

```python
confidence_gap = predicted_score - actual_score
# >0: 过度自信 → 增加复习频率
# <0: 自信不足 → 增加鼓励/减少复习压力
# |gap| > 0.3: 触发元认知反思提示
```

### 3.6 费曼解释评分 (系统13)

```python
explanation_score = weighted_sum(
    simplicity=0.25,      # 简单度
    accuracy=0.35,        # 准确度
    completeness=0.25,    # 完整度
    audience_fit=0.15,    # 受众适配（小白/专家分级）
)
```

### 3.7 自适应策略 (系统14)

```python
adaptive_policy = compute_policy(
    learner_profile,        # 学习画像（优势/劣势/风格/节奏）
    historical_performance, # 历史表现
    current_cognitive_load, # 当前认知负荷
    time_availability,      # 可用时间
    goal_alignment,         # 目标对齐
)
# 输出: 下次学习任务的类型/难度/时长/模态建议
```

### 3.8 A转B蒸馏协议 (系统16)

```text
pipeline: mastery_check → evidence_packet → machine_unit → publish
检查:  mastery_score >= 0.85 才能触发A转B
输出:  带有来源/证据/审核状态的 machine_knowledge_unit
```

---

## 4. 完整学习闭环

### 最小闭环 → 标准闭环 → 高级闭环

```text
[最小] 资料 → 卡片 → 审核 → 复习 → 掌握度 → 报告
[标准] 资料 → 结构化 → 路线 → 卡片 → 宫殿 → 训练 → 错误 → 复习 → 输出 → 巩固
[高级] 学 → 练 → 错 → 改 → 复习 → 输出 → 实战 → 巩固 → 再学 (无限循环)
```

---

## 5. 数据模型 (SQL)

关键新增表（从13_数据模型总补充SQL.md提取）：

| 表名 | 核心字段 | 用途 |
|------|---------|------|
| knowledge_blocks | id, title, content, parent_id, type, mastery | 知识块原子化 |
| encoding_anchors | block_id, modality, anchor_data | 记忆编码锚点 |
| skill_tasks | block_id, rubric_json, difficulty, time_estimate | 技能实战任务 |
| learner_profile | strengths, weaknesses, pace, cognitive_style | 学习画像 |
| consolidation_events | block_id, action, evidence | 长期巩固记录 |
| teach_back_records | block_id, audience_level, score | 费曼输出记录 |
| experiment_runs | hypothesis, variant_a, variant_b, result | A/B学习实验 |

---

## 6. API 端点设计

| 路径 | 系统 | 用途 |
|------|------|------|
| /capture | 捕获系统 | 信息摄入 |
| /structure | 知识结构 | 知识图谱 |
| /diagnostics | 诊断 | 学习诊断 |
| /routes | 路线 | 学习路径规划 |
| /review | 复习 | 间隔复习调度 |
| /palace | 宫殿 | 知识宫殿 |
| /training | 训练 | 主动练习 |
| /skills | 实战 | 技能评估 |
| /teach | 输出 | 费曼教学 |
| /report | 报告 | 综合报告 |
| /profile | 画像 | 学习者档案 |
| /consolidation | 巩固 | 长期维护 |
| /translation | A转B | 机器知识转化 |

---

## 7. 前端组件清单

| 组件 | 用途 |
|------|------|
| CognitiveLoadMeter | 认知负荷实时仪表 |
| NextActionPanel | 下一步行动推荐面板 |
| MetacognitionPanel | 元认知自信vs实际对比 |
| SkillTaskCard | 技能任务交互卡片 |
| RubricScorePanel | Rubric多维度评分面板 |
| TeachBackEditor | 费曼输出编辑器 |
| LearnerProfileRadar | 学习画像雷达图 |
| ConsolidationTimeline | 知识巩固时间线 |
| EvidencePacketViewer | A转B证据包查看器 |

---

## 8. 7级验收矩阵

| 级别 | 主题 | 验收标准 |
|------|------|---------|
| L1 能学 | 基础闭环 | 导入→生成知识点→生成卡片→复习 |
| L2 能记 | 记忆增强 | 调度复习→记录错误→建宫殿→沿路径回忆 |
| L3 能用 | 能力转化 | 完成训练→完成技能任务→生成作品→按rubric评分 |
| L4 能反思 | 元认知 | 预测自信vs实际表现→比较→输出反思→调整策略 |
| L5 能教 | 输出教学 | 费曼解释→输出演示→给小白/专家不同版本 |
| L6 能巩固 | 长期维护 | 合并重复知识→发现过时知识→更新宫殿→生成周报 |
| L7 能转机器 | 机器知识 | 生成evidence packet→判断mastery→A转B→发布machine knowledge |

---

## 9. MVP收敛路线

```text
MVP-1: 卡片 + 复习 + 错误      ← 当前项目已基本完成
MVP-2: 宫殿 + 路径游走         ← 待实现
MVP-3: 技能任务 + Rubric       ← 待实现
MVP-4: 元认知 + 费曼输出       ← 待实现
MVP-5: 巩固 + A转B             ← 待实现
```

---

## 10. 删减边界

**不加**: 短视频社区、排行榜、游戏化勋章、纯聊天陪练、无来源AI出题、大量无人审核卡片、过度3D宫殿、重型LMS复制

**保留原则**: 只保留增强「理解、记忆、回忆、练习、实战、输出、反思、巩固、迁移」的功能

---

## 11. 与现有项目代码的映射

| A线系统 | 现有模块 | 状态 |
|---------|---------|------|
| 系统7: 间隔复习 | pk_radar/core/fsrs5.py + optimizer | ✅ 已实现+优化 |
| 系统3: 学习诊断 | pk_radar/core/learning_system.py | ✅ 已实现 |
| 系统7: 复习数据 | pk_radar/core/store.py (cards/reviews) | ✅ 已实现 |
| 系统15: 长期巩固 | pk_radar/core/evolution.py | ✅ 已实现 |
| 系统16: A转B | pk_radar/b_line/machine_knowledge.py | ✅ 已有框架 |
| 系统5: 认知负荷 | pk_radar/core/cognitive_load.py | ❌ 待实现 |
| 系统6: 记忆编码 | pk_radar/core/encoding.py | ❌ 待实现 |
| 系统10: Rubric | pk_radar/core/rubrics.py | ❌ 待实现 |
| 系统13: 费曼输出 | pk_radar/core/teach_back.py | ❌ 待实现 |
| 系统14: 学习画像 | pk_radar/core/profile.py | ❌ 待实现 |
