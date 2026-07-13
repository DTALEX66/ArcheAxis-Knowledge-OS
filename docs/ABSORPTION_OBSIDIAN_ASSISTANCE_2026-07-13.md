# Obsidian-Assistance 能力吸收总账

> 日期：2026-07-13
> 源：外部 A 项目 Obsidian-Assistance（只读审计，源仓库存在用户未提交修改）
> 目标：本仓库 Cognitive-Loop-OS

## 边界

本轮只吸收通用算法、状态合同和验证规则。未复制：

- 正式 Obsidian Vault；
- E 盘课程源文件；
- OCR/ASR 全文、媒体、截图和缓存；
- 用户私人路径、token、密钥和本地数据库；
- 一次性迁移脚本及课程专属报告。

## 已有能力复核

| 源能力 | 目标已有实现 | 决策 |
|---|---|---|
| V4 safe vault writer | `shared/safe_writer.py` | 保留目标实现 |
| V4 Mermaid/Canvas/Bases | `shared/mermaid_gen.py`、`canvas.py`、`collection_views.py` | 不重复复制 |
| V5 diversity/review | `shared/diversity_audit.py`、KB reviews/cards | 不重复复制 |
| V6 PDF/关键帧/来源发现 | `shared/media_extractor.py`、`source_discovery.py` | 保留；新增语义证据门禁 |
| V7 项目生成 | `shared/project_generator.py` | 不重复复制 |
| V8 streak/mission/retro | `learning_analytics.py`、`retro_summary.py` | 不重复复制 |
| V10 Dataview/facts/pipeline | `dataview.py`、`fact_extractor.py`、`pipeline.py` | 不重复复制 |
| V10 task ledger | `shared/sleep_loop_engine.py` | 保留更严格的真实证据规则 |

## 本轮新增吸收

| 源文件/思路 | 目标落点 | 吸收内容 |
|---|---|---|
| `tools/pipeline.py` | `shared/processing_manifest.py`、`convert_directory_resumable()` | 原子落盘 Markdown、源/输出 SHA-256、失败重试、指纹校验恢复 |
| `tools/pipeline.py::source_key` | `source_artifact_key()` | 相对路径 SHA-256 防止同名文件碰撞 |
| `tools/benchmark_accuracy.py` | `shared/accuracy_benchmark.py` | 人工真值 CER，并扩展 WER；无金标准不得声称准确率 |
| `tools/content_keyframes.py` | `shared/evidence_verification.py` | 术语必须出现在提取文本中才返回页/帧候选；禁止随机证据 |
| V10 `course_verification_audit.py` | `verification_status()` | 调用者证据只作候选；当前无服务端可信 provenance，不自动升级 |
| `tools/audit_vault.py` | `shared/content_quality.py` | 乱码、水印、虚假 100%、断链静态审计 |
| V9 `oer_crosswalk_generator.py` | `shared/oer_crosswalk.py` | 静态开放来源发现建议；不检索、不检查许可、不构成 crosswalk 或核验 |
| V10 单入口思想 | `knowledge_base/routers/quality.py` | `/kb/quality` 复合质量入口 |

## 没有直接复制的内容

### 重型 OCR/ASR 实现

源项目使用 EasyOCR、SenseVoice、ffmpeg、PyMuPDF、antiword、pandoc 等本机工具。目标保留可选引擎和适配边界，没有把重型模型设为核心依赖。原因：

- 会显著扩大安装体积；
- 不同机器的模型/GPU/系统二进制条件不同；
- 模型置信度不能替代金标准准确率；
- Cognitive-Loop-OS 应保存通用管道与证据合同，而不是课程专属运行环境。

### Vault 专属生成器

课程主页、TALOS 模板、sidecar 和课程目录写入仍属于 Obsidian-Assistance。Cognitive-Loop-OS 吸收其算法和合同，不复制正式 Vault 操作。

## API 使用

```json
{"action":"evidence_match","terms":["向量数据库"],"candidates":[{"source":"slides.pdf","location":"page:3","text":"向量数据库支持相似度检索"}]}
```

```json
{"action":"verification","evidence":[{"kind":"pdf","source":"course.pdf","status":"matched"},{"kind":"oer","source":"https://example.edu/course","status":"matched"}]}
```

```json
{"action":"content_audit","content":"完成度: 100% ...","known_targets":["课程主页"]}
```

```json
{"action":"oer_crosswalk","content":"RAG 使用向量检索与 rerank","terms":["RAG"]}
```

质量接口不会把推荐 URL、单个文件、单次抽样或 dry-run 当作完成证据。
