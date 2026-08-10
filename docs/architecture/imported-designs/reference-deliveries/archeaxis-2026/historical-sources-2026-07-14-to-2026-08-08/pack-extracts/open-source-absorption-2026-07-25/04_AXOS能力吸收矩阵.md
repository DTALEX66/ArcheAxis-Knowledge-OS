# AXOS 能力吸收矩阵

## ASRProvider

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| faster-whisper | A2 | 稳定通用ASR Provider | 第二批接入 |

## Agent Memory / Runtime Reference

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Letta | C1 | 只借鉴内存分层与可编辑状态 | 不整体接入 |

## AgentExecutorProvider

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| PydanticAI | A1 | Python最小闭环默认SDK候选 | 首批验证 |

## AgentRun Telemetry

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| OpenInference | A1 | 直接采用语义并映射AXOS合同 | 首批设计 |

## Audit / Trace Backbone

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| OpenTelemetry | A1 | 正式采用标准 | 首批设计 |

## CompressedArtifactV1 / Context Pack

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| TinyJuice | A1 | 先Sidecar验证，再自研兼容合同 | 重点专项 |

## Cross-cutting Capability Reference

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| OpenHuman | A2 | 只吸收能力；绝不作为AXOS入口或替代平台 | 综合拆解样本 |

## Derived Retrieval Index

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| LanceDB | A1 | 多模态派生索引；SQLite仍是事实源 | 首批验证 |

## EmbedderProvider

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Qwen3-Embedding-0.6B | A1 | 本地常驻文本向量模型 | 首批接入 |

## End-to-end Benchmark

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| RAGFlow | C1 | 借鉴流程、引用UX和评测 | 不整体集成 |

## EvalProvider

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| DeepEval | A1 | Agent和输出回归组件 | 首批验证 |

## External Capability Boundary

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| MCP Python SDK | A2 | 锁定稳定主版本作为工具边界 | 协议接入 |

## External Execution Runtime

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Hermes Agent | A1 | 保留现有执行角色，强化Bridge、合同、Trace和回写 | 现有主执行器 |

## Future Rust Agent Runtime

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| TinyAgents | A2 | 吸收运行合同并隔离对照 | 重点架构对照 |

## Human Console / Workbench

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| React Flow / XYFlow | A1 | 观心统一图形基础 | 首批前端设计 |

## Human Query / Risk Gating

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| VeriOS | A2 | 吸收何时询问人的策略和测试集 | 安全研究 |

## Human-AI Learning Loop / Outcome Proof

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| NOUS OS | A2 | 吸收结果证明、纠错吸收和权威边界 | 架构对标 |

## Interactive Simulation Lab

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| marimo | A1 | P08实验和可视化执行环境 | 首批验证 |

## Knowledge Compilation / Audit

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Bob's Big Brain Compiler | A1 | 重点吸收确定性内核、六层存储、晋升与认知procfs | 重点专项 |

## Knowledge Graph Benchmark

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Cognee | C1 | 图谱构建对照 | 观察 |

## Knowledge Ingestion / ParserProvider

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Docling | A1 | 默认主解析Provider候选 | 首批验证 |

## Knowledge Tracing Research

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| pyKT | C1 | 后期离线研究 | 后期研究 |

## LearningArtifactProvider

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| H5P | B1 | 导出/嵌入格式 | 第二阶段 |

## LearningSchedulerProvider

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Py-FSRS | A1 | 直接接入Human Learning OS | 首批接入 |

## Legacy Framework Reference

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| AutoGen | D1 | 不作为新核心依赖 | 排除 |

## Lightweight Vector Index Option

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| sqlite-vec | B1 | LanceDB轻量对照 | 对照PoC |

## Local Reasoning Model

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Qwen3.5-4B | A2 | 量化后用于分类、转化和草稿 | 第二批验证 |

## LocalModelProvider

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| llama.cpp | A1 | Windows本地推理正式底座候选 | 首批接入 |

## Long-term OS Architecture Research

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| AOHP | B1 | 吸收Agent身份、资源治理和信息流 | 研究观察 |

## Memory Algorithm Benchmark

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Mem0 | B1 | 算法与评测对照 | 对照研究 |

## MemoryFactV1 / Temporal Memory

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Graphiti | A2 | 吸收语义和算法，不整体部署 | 拆解吸收 |

## MemoryProvider / Cognitive Memory

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| TinyCortex | A1 | 隔离PoC后拆解吸收或Provider化 | 重点专项 |

## ModelProvider Adapter

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| LiteLLM | A2 | 薄适配层或实现参考 | 可选接入 |

## Multimodal EmbedderProvider

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Qwen3-VL-Embedding-2B | A2 | 按需视觉检索Provider | 第二批验证 |

## Multimodal RerankerProvider

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Qwen3-VL-Reranker-2B | B1 | 高价值视觉检索按需重排 | 性能允许后验证 |

## OCR Benchmark

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Chandra OCR | C1 | 高难文档精度基准 | 只做基准 |

## OCRProvider / Document Evidence

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| PaddleOCR-VL / PaddleOCR | A1 | 中文复杂文档主OCR Provider | 首批验证 |

## OCRProvider / Parse Arbitration

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| GLM-OCR | A2 | 备份OCR和低置信度仲裁 | 第二批验证 |

## Optional Whiteboard

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| tldraw | C1 | 视觉能力对照 | 不作核心画布 |

## ParserProvider Benchmark

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| MinerU | B1 | 解析质量基准及可选Provider | 基准对照 |
| Marker | C1 | 仅做精度对照 | 不进入核心 |

## Periodic Model Evaluation

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Inspect AI | A2 | 周期性能力评估和升级验收 | 第二批接入 |

## Pipeline Design Reference

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Haystack | B2 | 借鉴组件接口和可测试Pipeline | 架构参考 |

## Process Runtime Research

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Quine | B2 | 借鉴进程身份、退出码、标准流和资源隔离 | 架构研究 |

## RepositoryParserProvider / ResearchPackageV1

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Repomix | A1 | 代码研究预处理器 | 立即验证 |

## RerankerProvider

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Qwen3-Reranker-0.6B | A1 | 本地文本重排 | 首批接入 |

## Retrieval Eval

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Ragas | A1 | 建立检索和回答基线 | 首批验证 |

## Retrieval Strategy

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| LightRAG | B1 | 借鉴Local/Global Query与增量图 | 算法对照 |

## Schema / Reasoning Reference

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| OpenSPG / KAG | B2 | 借鉴Schema治理与多跳推理 | 后期研究 |

## Security Eval / Model Matrix

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Promptfoo | A1 | 安全及多模型路由测试 | 首批验证 |

## Self-State Security / Backup / Integrity

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Self-State Attacks on Self-Hosted AI Agents | A1 | 转化为威胁模型和回归矩阵 | 立即吸收 |

## Vector Index Option

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| SQLite-Vector | C1 | 仅性能对照 | 不进默认核心 |

## WebCaptureProvider / Inspiration Research

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| Crawl4AI | A2 | 隔离浏览器Worker接入 | 隔离验证 |

## Workbench / Operator UX Reference

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| CoWork OS | B1 | 吸收运行可见性、Artifact工作台和Mission Control | 界面对标 |

## WorkbenchPanelProvider / Plugin UI

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| MCP Apps | A2 | 插件面板协议参考/兼容层 | 第二批验证 |

## Workflow Schema / Executor Reference

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| TinyFlows | A2 | 吸收节点合同、审批与恢复 | 重点拆解 |

## WorkflowExecutorProvider

| 项目 | 优先级 | 吸收方式 | 决策 |
|---|---:|---|---|
| LangGraph | B1 | 仅作可选长任务适配器 | 可选 |
