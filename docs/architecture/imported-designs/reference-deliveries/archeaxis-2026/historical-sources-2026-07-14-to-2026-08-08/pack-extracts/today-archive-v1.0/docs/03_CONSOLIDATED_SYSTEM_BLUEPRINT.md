# 元枢系统集中总蓝图

## 1. 总体模型

```text
Sources / Assets
→ Research / Evidence
→ Governed Knowledge
→ Human Learning
→ AI-Usable Knowledge
→ Knowledge Application
→ Review / Evaluation
→ Bidirectional Improvement
```

## 2. 核心层

### 来源与证据层

- Local File；
- Web；
- GitHub；
- PDF；
- Office；
- Image；
- Audio；
- Video；
- SourceAsset；
- SourceRecord；
- Claim；
- Evidence；
- Conflict；
- Unknown；
- ResearchPackage；
- Provenance。

### 统一知识层

- KnowledgeUnit；
- Relation；
- Version；
- Project Knowledge；
- Domain Knowledge；
- Candidate；
- Approved；
- Deprecated；
- Supersedes；
- Graph；
- Search；
- Context Pack。

### 个人学习层

- Course；
- Note；
- LearningArtifact；
- Card；
- Practice；
- Review；
- Mistake；
- Mastery；
- Teach Back；
- Visualization；
- Simulation；
- Memory Palace；
- Transfer。

### AI 使用层

- MachineKnowledge；
- Retrieval；
- ContextPack；
- TaskPack；
- Permission；
- Tool；
- Agent；
- Trace；
- Evaluation；
- Lesson；
- Anti-pattern。

### 双向治理层

- Human Review；
- Candidate Promotion；
- Version；
- Deprecation；
- Conflict Resolution；
- Audit；
- Replay；
- Provenance；
- Migration；
- Rollback。

## 3. 桌面工作空间

最终桌面不以 Agent 为中心，而以知识与学习为中心：

1. 总览；
2. 资料库；
3. 研究验证；
4. 知识库；
5. 学习中心；
6. AI 知识；
7. 双向转化；
8. 任务应用；
9. 画布与回放；
10. 连接；
11. 系统。

## 4. 最小完整闭环

```text
Local File / URL
→ Research Candidate
→ Human Review
→ Knowledge Candidate
→ Learning Artifact
→ Practice
→ Mastery
→ Machine Knowledge Candidate
→ Human Review
→ AI-Usable Knowledge
→ Task Use
→ Trace / Evaluation
→ Candidate Feedback
```

## 5. 主要合同

- SourceAssetV1（待补）
- SourceRecordV1
- ClaimV1
- EvidenceV1
- ResearchPackageV1
- KnowledgeUnitV1
- RelationV1
- LearningArtifactV1
- MasterySignalV1
- MachineKnowledgeUnitV1
- ContextPackV1（仍需深化）
- TaskPackV1
- ExecutionTraceV1
- EvaluationV1
- LessonV1
- VisualArtifactV1
- SimulationPackageV1
- PalacePackageV1

## 6. Agent 的位置

Agent 是 AI 使用层的一种执行方式，不是系统最终定位。

Agent 应当：

- 从受治理知识读取；
- 只获得明确 Context；
- 经 Permission；
- 调用受控工具；
- 输出 Trace；
- 接受 Evaluation；
- 结果先成为 Candidate；
- 不能直接污染正式知识库。
