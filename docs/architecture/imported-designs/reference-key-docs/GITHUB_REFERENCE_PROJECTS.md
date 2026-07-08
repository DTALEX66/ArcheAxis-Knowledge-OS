# GitHub 开源参考项目清单

> Generated 2026-06-23 | Agent-5 (Lorentz)
> 对A线/B线各环节有帮助的开源项目

---

## 1. 学习诊断系统

| 项目 | URL | 许可 | 为什么有用 |
|------|-----|------|-----------|
| Khan Academy Exercises | https://github.com/Khan/khan-exercises | MIT | 自适应诊断框架，prerequisite scoring参考 |
| Adaptive Learning | https://github.com/adaptive-learning/adaptive-learning-research | Mixed | 自适应学习论文+实现收集 |
| Oppia | https://github.com/oppia/oppia | Apache-2.0 | 交互式学习诊断，exploration结构 |

---

## 2. 记忆编码/间隔重复算法

| 项目 | URL | 许可 | 为什么有用 |
|------|-----|------|-----------|
| py-fsrs | https://github.com/open-spaced-repetition/py-fsrs | MIT | FSRS官方Python实现 |
| rs-fsrs | https://github.com/open-spaced-repetition/rs-fsrs | MIT | FSRS Rust实现（性能基准） |
| fsrs4anki | https://github.com/open-spaced-repetition/fsrs4anki | MIT | Anki集成，优化器参考 |
| Anki | https://github.com/ankitects/anki | AGPL-3.0 | SRS黄金标准，只参考算法不复制代码 |
| Mnemosyne | https://github.com/mnemosyne-proj/mnemosyne | AGPL-3.0 | 记忆研究工具，SM-2实现参考 |

---

## 3. Rubric评分引擎

| 项目 | URL | 许可 | 为什么有用 |
|------|-----|------|-----------|
| Gradescope | https://www.gradescope.com | 商业 | Rubric UI设计参考 |
| Criterion | https://github.com/ets/criterion | 研究 | ETS自动评分引擎 |
| Rubrix | https://github.com/argilla-io/argilla | Apache-2.0 | 标注+评估平台，Rubric数据管理 |

---

## 4. Agent执行框架

| 项目 | URL | 许可 | 为什么有用 |
|------|-----|------|-----------|
| LangGraph | https://github.com/langchain-ai/langgraph | MIT | 状态机路由参考（吸收思想不依赖） |
| AutoGen | https://github.com/microsoft/autogen | MIT | 多Agent对话+工具调用模式 |
| CrewAI | https://github.com/crewAIInc/crewAI | MIT | 角色+任务+团队Agent编排 |
| OpenHands | https://github.com/All-Hands-AI/OpenHands | MIT | 代码Agent沙箱执行参考 |
| SWE-agent | https://github.com/SWE-agent/SWE-agent | MIT | ACI(Agent-Computer Interface)设计 |
| MetaGPT | https://github.com/geekan/MetaGPT | MIT | 软件公司多Agent SOP流程 |
| CAMEL | https://github.com/camel-ai/camel | Apache-2.0 | 多Agent角色扮演框架 |

---

## 5. 自主优化/反馈学习

| 项目 | URL | 许可 | 为什么有用 |
|------|-----|------|-----------|
| DSPy | https://github.com/stanfordnlp/dspy | MIT | 编程式Prompt优化，自动权重调整 |
| promptfoo | https://github.com/promptfoo/promptfoo | MIT | LLM回归测试/红队评估 |
| Langfuse | https://github.com/langfuse/langfuse | MIT | LLM可观测性+Prompt管理 |
| Phoenix | https://github.com/Arize-AI/phoenix | Apache-2.0 | LLM trace可视化+评估 |
| Ragas | https://github.com/explodinggradients/ragas | Apache-2.0 | RAG质量评估(faithfulness/relevancy) |

---

## 6. 机器记忆/知识图谱

| 项目 | URL | 许可 | 为什么有用 |
|------|-----|------|-----------|
| Mem0 | https://github.com/mem0ai/mem0 | Apache-2.0 | Agent长期记忆，记忆抽取+合并 |
| Zep | https://github.com/getzep/zep | Apache-2.0 | 时序知识图谱，跨会话连续记忆 |
| projectmem | https://github.com/projectmem | 需核查 | local-first事件记忆 |
| ChromaDB | https://github.com/chroma-core/chroma | Apache-2.0 | 向量存储，语义检索 |

---

## 7. 模型网关/路由

| 项目 | URL | 许可 | 为什么有用 |
|------|-----|------|-----------|
| LiteLLM | https://github.com/BerriAI/litellm | MIT | 多模型统一API，预算+路由 |
| vLLM | https://github.com/vllm-project/vllm | Apache-2.0 | 高性能LLM推理服务 |
| Ollama | https://github.com/ollama/ollama | MIT | 本地LLM运行 |

---

## 8. 执行沙箱

| 项目 | URL | 许可 | 为什么有用 |
|------|-----|------|-----------|
| E2B | https://github.com/e2b-dev/e2b | Apache-2.0 | 云端代码沙箱 |
| Docker SDK | https://github.com/docker/docker-py | Apache-2.0 | 本地容器隔离 |

---

## 9. 知识管理/RAG

| 项目 | URL | 许可 | 为什么有用 |
|------|-----|------|-----------|
| LlamaIndex | https://github.com/run-llama/llama_index | MIT | RAG数据框架 |
| Haystack | https://github.com/deepset-ai/haystack | Apache-2.0 | NLP Pipeline框架 |
| Dify | https://github.com/langgenius/dify | Apache-2.0 | LLM应用平台（参考UX） |
| RAGFlow | https://github.com/infiniflow/ragflow | Apache-2.0 | 深度文档理解RAG |
| Qdrant | https://github.com/qdrant/qdrant | Apache-2.0 | 向量数据库 |

---

## 10. 前端/IDE集成

| 项目 | URL | 许可 | 为什么有用 |
|------|-----|------|-----------|
| Continue | https://github.com/continuedev/continue | Apache-2.0 | IDE内AI助手，上下文管理 |
| Aider | https://github.com/paul-gauthier/aider | Apache-2.0 | Git内AI结对编程 |

---

## 11. 吸收策略总结

### 可以直接依赖（MIT/Apache-2.0）
- LiteLLM: 模型网关
- pytest + ruff: 开发工具
- ChromaDB/Qdrant: 向量存储
- FastAPI + Uvicorn + Pydantic: Web框架

### 吸收思想+做Adapter
- LangGraph → 自建轻量状态机
- AutoGen/CrewAI → Agent角色分配算法
- DSPy → 反馈优化循环
- OpenHands → 沙箱执行模式

### 只参考不复制（AGPL/GPL/商业/未知）
- Anki → SM-2算法逻辑
- Mnemosyne → 记忆研究
- Gradescope → Rubric UI

### 核心原则
```text
1. 核心自己写
2. 开源项目做 adapter
3. 高风险许可证只参考
4. 所有第三方能力进隔离层
```

---

## 8. 新增推荐项目 (2026-06-25 更新)

| 项目 | URL | 许可 | 为什么有用 |
|------|-----|------|-----------|
| mellia-public | https://github.com/peter-coulson/mellia-public | MIT | AI语音+图片辅助记忆, FastAPI+React 19+PostgreSQL, 可作为对知识库前端/后端参考 |
| agent-orchestrator | https://github.com/JING04-PRODUCER/agent-orchestrator | MIT | 跨语言AI Agent编排, Python FastAPI + Java Spring Boot, 可参考多语言Agent协调模式 |
| Flashcards-using-LLM | https://github.com/HiteshAvula09/Flashcards-using-LLM | MIT | RAG+Groq+ChromaDB+SM-2, AI驱动抽认卡生成, 直接对齐A线学习诊断场景 |
