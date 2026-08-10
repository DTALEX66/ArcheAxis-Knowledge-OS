# 交给 Hermes 的执行任务包

## 总目标
在不替换现有 AXOS 主体、不改项目目录外文件的前提下，建立可插拔开源能力吸收层。

## 强制规则
1. 禁止删除项目目录外任何文件。
2. 禁止整仓复制 OpenHuman、RAGFlow、Letta、Cognee。
3. SQLite 保持事实源；向量和摘要索引必须可重建。
4. GPL 项目只能进入 `experiments/sidecars/` 或 `benchmarks/`。
5. 所有变更必须走新分支，先测试再合并。
6. 不允许 Agent 自动晋升正式知识或修改安全策略。
7. 所有模型、工具和外部服务必须通过 Provider 合同。

## 建议目录
```text
packages/contracts/
packages/control-plane/
packages/knowledge-ingestion/
packages/memory/
packages/retrieval/
packages/agent-runtime/
packages/evaluation/
packages/human-console/
providers/parser-docling/
providers/ocr-paddle/
providers/embed-qwen/
providers/rerank-qwen/
providers/model-llamacpp/
sidecars/tinyjuice/
benchmarks/openhuman/
benchmarks/tinycortex/
benchmarks/tinyagents/
benchmarks/tinyflows/
```

## Sprint 0
- 读取当前仓库结构。
- 输出 `docs/audits/open-source-absorption-baseline.md`。
- 只创建接口、测试夹具和空Provider，不安装重依赖。
- 建立 Feature Flags。
- 建立 License Manifest 和 SBOM。

## Sprint 1
- 接入 Docling、PaddleOCR-VL、Qwen Embedding/Reranker、LanceDB。
- 完成一条 PDF → 引文回答闭环。
- 增加 Ragas 和 Promptfoo 测试。

## Sprint 2
- 打通 Hermes AgentRunV1、取消、重试、Artifact、Trace。
- 加入 OpenTelemetry/OpenInference。
- 做 TinyJuice Sidecar 对照，不合并GPL代码。

## Sprint 3
- TinyCortex、Graphiti、Bob's Big Brain Compiler 三组记忆/知识编译PoC。
- 产出 ADR，选择自研/Provider/仅借鉴。

## 完成定义
- 全流程可视化。
- 每个结果有来源、版本、运行ID、模型、工具和测试证据。
- 删除任一Provider后，核心系统仍可启动。
- 没有新增第二套不可控事实源。
