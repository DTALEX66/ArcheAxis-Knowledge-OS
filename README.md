# 星环知识平台（ArcheAxis Knowledge）

<!-- Legacy/Migration names below are compatibility context only. -->

> **v0.6.9 已发布（2026-08-23）**：Recovery Shell 闭环、薄前端实时开发路径和风险选择 CI 已交付。精确提交 `de5b5ba` 的 main CI、NSIS/Green/Portable 生命周期、9 项公开资产、checksum 和 schema v3 identity 读回均通过。正式 Release：[`v0.6.9`](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.6.9)。发布成功不等于所有长期蓝图能力已实现。

> **ArcheAxis Knowledge — a local-first, evidence-driven, bidirectional Human–AI Learning & Trusted-Knowledge Workspace for individuals and AI.**
>
> **同一份可信知识，人学得更深，AI 用得更准。**

> **GitHub 交付**：上传/审核见 [`GITHUB_DELIVERY.md`](GITHUB_DELIVERY.md)（WORK-LAB 交付加速器）。

主品牌 **ArcheAxis**（固定拼写）；英文产品名 **ArcheAxis Knowledge**；中文产品名 **星环知识平台**。
仓库技术 ID `archeaxis-workspace` 仅为 Git/分发兼容身份（历史兼容身份，不是产品名）；旧名"元枢/元枢工作台"只保留在 Legacy/Migration/兼容说明中。
项目状态：**Personal Research Project / 个人研究项目**（不等同于许可证）。

> 官方定位：**本地优先、原件保全、证据可追溯、开放互操作的人机双向学习与可信知识治理工作台。**
> 完整长版：本地优先、原件永久保全、全链路证据锚定交叉核验、开放全格式兼容、数据主权可控的人机双向学习与可信知识治理工作台。
> 它是**系统级**人机双向学习与可信知识系统，**不等于**通用操作系统、通用 Agent Runtime、自治工作流平台或多 Agent 产品。

**权威文档（定死，不可漂移，更新需 Owner 决策）**：
- 产品身份：[`docs/truth/PRODUCT_IDENTITY_V2.md`](docs/truth/PRODUCT_IDENTITY_V2.md)
- 命名契约：[`docs/truth/NAMING_CONTRACT_V1.md`](docs/truth/NAMING_CONTRACT_V1.md)
- 权威规则：[`docs/truth/AUTHORITY_AND_STATUS_RULES_V1.md`](docs/truth/AUTHORITY_AND_STATUS_RULES_V1.md)
- 能力图谱：[`docs/truth/CAPABILITY_ATLAS_V2.yaml`](docs/truth/CAPABILITY_ATLAS_V2.yaml)
- 总蓝图：[`docs/blueprint/SYSTEM_MASTER_BLUEPRINT_V2.md`](docs/blueprint/SYSTEM_MASTER_BLUEPRINT_V2.md)

**当前阶段（可随实现更新）**：Obsidian-compatible Workspace foundation。
Markdown、JSON Canvas 和 Vault 互操作是第一条高保真纵切；在编辑、附件、冲突、回滚和 Windows/Tauri 重启回读全部有证据前，不宣称全面或双向兼容。
详见 [`docs/current/CURRENT_PRODUCT_PLAN_V2.md`](docs/current/CURRENT_PRODUCT_PLAN_V2.md) 与 [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)。

---

## 外置依赖与不可吸收开源项目（锁死展示）

> 本节内容**定死**：吸收不了的开源项目与需要外置的开源依赖链接在此锁死展示，不随阶段描述漂移。

### 外置环境与工具链（必须单独安装/下载）

| 依赖 | 用途 | 下载链接 |
|---|---|---|
| Python 3.11+ | 运行时 | https://www.python.org/downloads/windows/ |
| uv | Python 包管理器 | https://github.com/astral-sh/uv/releases |
| Tesseract-OCR 5.x | 图像 OCR 引擎 | https://github.com/UB-Mannheim/tesseract/wiki |
| Tesseract 语言包 | OCR 中文/英文识别（chi_sim + eng） | https://github.com/tesseract-ocr/tessdata |
| FFmpeg | 音视频处理 | https://ffmpeg.org/download.html |
| Git | 版本控制 | https://git-scm.com/download/win |
| Node.js LTS | 桌面构建（可选） | https://nodejs.org/ |
| Rust toolchain | Tauri 桌面构建 | https://rustup.rs |
| VS Build Tools (MSVC) | Rust/桌面编译链 | https://visualstudio.microsoft.com/visual-cpp-build-tools/ |
| Playwright 浏览器 | 浏览器自动化 | https://playwright.dev/python/docs/browsers |
| scoop | Windows 包管理（可选） | https://scoop.sh |

完整清单与安装步骤见 [`docs/environment/EXTERNAL_DEPENDENCIES.md`](docs/environment/EXTERNAL_DEPENDENCIES.md)（同步于 `D:\All projects\OS External Configuration\EXTERNAL_DEPENDENCIES.md`）。

### 已吸收（代码/依赖已并入）

JiWER、RapidFuzz、JSON Canvas（格式）、Crossref/DataCite/OpenAlex/Wikidata（API 连接器）、py-fsrs、Magika（ONNX 模型 vendored）、MarkItDown、Trafilatura、pytesseract、sqlite-vec、NetworkX、LiteLLM、Langfuse、Loguru、structlog、APScheduler、PDF.js（vendored）。
权威决策账本：[`docs/truth/SUPPLY_CHAIN_LEDGER.json`](docs/truth/SUPPLY_CHAIN_LEDGER.json)。

### 吸收不了 / 许可或边界阻断（外置保留，仅链接）

| 项目 | 阻断原因 | 上游链接 |
|---|---|---|
| MinerU | Apache-2.0 + 附加 MAU/收入阈值/在线服务义务 | https://github.com/opendatalab/MinerU |
| Marker | 代码 Apache-2.0，但权重受修改版 OpenRAIL-M 许可 | https://github.com/datalab-to/marker |
| PyMuPDF4LLM | AGPL-3.0 | https://github.com/pymupdf/pymupdf4llm |
| FunASR / SenseVoice | 代码 MIT，模型许可含行为条款/自动修订 | https://github.com/modelscope/FunASR |
| tldraw | 生产使用要求商业 license key | https://github.com/tldraw/tldraw |
| Firecrawl | 主体 AGPL-3.0（部分 SDK/UI MIT） | https://github.com/firecrawl/firecrawl |
| H5P PHP Library | GPL-3.0（HTML Purifier 依赖） | https://github.com/h5p/h5p-php-library |
| Phoenix (Arize) | Elastic License 2.0（非 OSS） | https://github.com/Arize-ai/phoenix |
| SearXNG | AGPL-3.0 | https://github.com/searxng/searxng |
| Kùzu | 上游已归档（2025-10-10） | https://github.com/kuzudb/kuzu |

### 待 bake-off（H2 识别转译，需模型/硬件评估）

faster-whisper (https://github.com/SYSTRAN/faster-whisper)、whisper.cpp (https://github.com/ggml-org/whisper.cpp)、PaddleOCR (https://github.com/PaddlePaddle/PaddleOCR)、RapidOCR (https://github.com/RapidAI/RapidOCR)、EasyOCR (https://github.com/JaidedAI/EasyOCR)、Docling (https://github.com/docling-project/docling)、Silero VAD (https://github.com/snakers4/silero-vad)、Magika (https://github.com/google/magika)。
bake-off 框架：[`shared/bakeoff.py`](shared/bakeoff.py) + [`shared/bakeoff_engines.py`](shared/bakeoff_engines.py)。

---

## 当前重点

- **资料到知识的真实基础链**：网页、GitHub URL、本地文件导入 → candidate Research/Evidence → Knowledge/Learning/Mastery 治理；执行侧当前以 `read file:` 受限 Planner tracer 和局部闭环为主。
- **个人学习与 AI 使用的双向反馈**：学习笔记、纠错、练习和人工审核不会自动提升为事实；AI 的来源、Claim、解释、任务结果和 Lesson 同样必须先经 Candidate 治理。
- **可治理的本地运行时**：SQLite 持久化、Outbox/Receipt、失败不改状态、重试与回读，以及不暴露内部审计 ID 的公开投影。
- **桌面 Workspace A1**：默认 Apple-light，Violet Core 保留为暗色主题；一级 Rail、动态二级导航、上下文与证据检查器和真实活动坞均已接入。Chromium/Tauri 运行时证据与公开发布资产属于不同证据层；`v0.6.11` 是当前公开稳定版，已通过 exact-SHA Windows build、Setup/Green/Portable 生命周期、9 资产读回与 DeepTutor 本地模型黄金流。
- **当前版本**：`0.6.11`；源码 Release Manifest 按合同保持 `unreleased / public=false`，公开 artifact identity 为 `stable / public=true`；历史标签均不可改写。
- **发布真相**：`v0.4.0` 是保留且不可原地改写的 historical release，但具有 **incomplete checksum payload coverage**；后续历史标签同样不重写。`v0.6.11` 的 tag/commit/tree、exact-SHA CI `33076417510`、Release run `33077810146`、三分发生命周期与 9 资产身份/摘要读回证据见 [`docs/RELEASE_LEDGER.md`](docs/RELEASE_LEDGER.md)。

Research candidate 仍必须经过人工审查和来源独立性验证，不能自动当作 verified truth。产品定位见 [`docs/PRODUCT_POSITIONING.md`](docs/PRODUCT_POSITIONING.md)；当前事实、限制和验证证据见 [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) 与 [`docs/VERIFICATION_POLICY.md`](docs/VERIFICATION_POLICY.md)。

## Phase 4 Research Status

Phase 4 Research closure is implemented as a candidate-only workflow:

```text
canonical GitHub URL -> Safe HTTP collect -> quarantine -> parse -> claims
-> evidence -> cross-validation findings -> persisted ResearchPackageV1
```

Public entry points:

- Facade: `app.facades.research.research_github_repository()`
- Read facade: `app.facades.research.get_research_package()`
- API: `POST /research/github-repository`
- API: `GET /research/packages/{package_id}`

The workflow accepts only canonical `https://github.com/{owner}/{repo}` repository URLs, collects GitHub API metadata and README payloads through `shared.safe_http`, and revalidates status, final URL, media type, and byte limits at the production transport boundary. The complete provenance graph is persisted through the operator-only `research.sqlite` migration owner and revalidated on strict read. The storage boundary accepts candidate-only graphs (`status=candidate`, `provenance_status=caller_supplied`, `requires_human_review=True`); one GitHub repository does not satisfy verified-source independence. Candidate promotion remains governed by explicit review, version, deprecation, and provenance contracts. Legacy trending/daily/feed/cron/screening exports, caller-supplied IR-to-KB bridges, engineering-contract intake promotion, external research-note writes, KB Document/ContextPack/Card/Evidence/MachineKnowledge references, GraphDB entity/relation writes, Canvas card/connection writes, Episodic memory, processing manifests, and Core `/ingest*`/`/run` inputs that identify `research_package_*`, `intake_*`, `source_*`, `claim_*`, `evidence_*`, `finding_*`, or HTTP(S) sources all fail closed unless server-owned review provenance is present. External `url/search/youtube/rss` pipeline requests cannot use automatic KB ingestion; read-only search/extract/feed parsing remains available when it does not persist or promote external material. Local `file` ingestion requires the server-configured `COGNITIVE_APPROVED_SOURCE_ROOTS` containment boundary; local `text` ingestion retains its existing contract. This does not claim public release or verified truth from candidate material.

[![CI](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/workflows/ci.yml/badge.svg)](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/workflows/ci.yml)

ArcheAxis Knowledge 的目标不是堆积 AI 功能，而是建立一条可追溯、可审核、可回滚的资料—学习—引用闭环：

```text
Research → Evidence → Knowledge → Learning
→ Plan → Permission → Execution → Trace → Evaluation → Lesson
```

本项目采用本地优先的 FastAPI/SQLite 模块化单体。candidate Research、Knowledge/Learning/Mastery/Machine Knowledge 治理、Evaluation、Sleep Loop 与受限 Planner tracer 已有受治理构件和局部闭环；GitHub metadata/README 仍不会自动成为 verified truth。Workspace 已提供真实本地导入入口、迁移 owner 管理的 Job/Outbox/Receipt 同事务边界、按需 dispatcher 与用户级状态/投影页面；dispatcher 已有服务级成功/失败/重试/lease 保护，本地真实 Chromium upload → dispatch → receipt → reload gate 已通过验证。审计事件流、SSE、lease-fenced 异步 Worker 和 Job Center 投影已接入；通用 Planner、完整 Tauri WebView 点击级证据和更完整的用户级 Job Center 交互仍未闭环。当前已有 Release Manifest、媒体基础链、图像 OCR、Windows 构建、NSIS 生命周期门禁和公开 `v0.5.0` 发布资产；ASR 仍未闭环。

## 规划与进度

进度按“真实闭环 + 回滚证据”判定，不按文件、接口或测试数量计算。

| 阶段 | 目标 | 状态 | 当前检查点 |
| --- | --- | --- | --- |
| Phase 0 | 仓库资产、API、依赖、测试与安全基线 | ✅ 已完成 | 基线报告已进入 `migrations/reports/phase-0/` |
| Phase 1.0 | 命名、编码、Git index/HEAD 治理 | ✅ 已完成 | registry、scanner、pre-commit、CI 已接通 |
| Phase 1.1 | Runtime/Knowledge/Research/Enhancement/Contracts Facade + Architecture Guard | ✅ 已完成 | 五个 Facade、canonical Research 包、Architecture Guard 与兼容测试已接通 |
| Phase 2 | 版本化 Contracts 与旧对象 Adapter | ✅ 已完成首批合同 | 路线图列出的 Research、Knowledge/Learning、Machine Knowledge 与 Runtime 合同均已有严格 tracer |
| Phase 3 | 鉴权、Safe HTTP、approved roots、迁移与回滚 P0 | ✅ 核心边界完成 | Safe HTTP、roots、stable hash、Vector/FTS 与统一 Migration Runner 已接通 |
| Phase 4 | Research 闭环 | ✅ candidate-only 闭环完成 | GitHub URL → quarantined sources → claims/evidence/findings → SQLite → strict read |
| Phase 5–6 | Knowledge/Learning 与 Enhancement 闭环 | ✅ candidate 治理闭环完成 | 审批、版本、弃用与 provenance 边界已验证 |
| Phase 7–8 | 受限 Planner tracer、多维 Evaluation、Sleep Loop 构件 | 🟡 首条纵向 tracer 完成 | `read file:`、Permission、Evidence、Evaluation 与 Lesson 已验证；通用 Planner 和统一执行端口未完成 |
| Phase 9 | Contract & Tracer Alpha | ✅ 历史合同/追踪基线完成 | 不等于完整产品 Alpha，也不证明公开 release |
| Product Stage A0 | 产品真相、诊断、媒体摄入与发布门禁 | 🟡 收口中 | Job/Outbox/OCR 基线、按需 dispatcher、本地真实 Chromium delivery gate、Windows/NSIS 门禁与公开 `v0.5.0` 资产已验证；Tauri WebView 点击级证据、ASR、签名发布与更高阶用户交互仍待完成 |

### 冻结执行基线（权威任务包）

CODEX 冻结的后续执行蓝图与增补包已进入仓库 `docs/`，作为后续 Horizon（H1-H10 与 Web/KLC 增补）的唯一定义源：

- 冻结基线：[`docs/truth/FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md`](docs/truth/FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md)（H0-H10 全部任务定义）
- 执行任务包：[`docs/taskpacks/DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md`](docs/taskpacks/DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md)
- Web 增补：[`docs/taskpacks/MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md`](docs/taskpacks/MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md)
- Capability-first 增补：[`docs/taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md`](docs/taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md)
- 追加式状态日志：[`docs/truth/EXECUTION_STATUS_LOG.md`](docs/truth/EXECUTION_STATUS_LOG.md)
- 状态交接文档：[`docs/truth/H0_H1_STATUS_HANDOFF.md`](docs/truth/H0_H1_STATUS_HANDOFF.md)
- 权威契约：[`docs/truth/AUTHORITY_CONTRACT.md`](docs/truth/AUTHORITY_CONTRACT.md)

> 说明：这些文档与历史 `docs/FUTURE_EXECUTION_BLUEPRINT.md` 并存；冻结基线与增补包是当前任务的权威定义，历史蓝图仅作迁移输入（权威顺序见 `AUTHORITY_CONTRACT.md`）。H1 后端已完成但仍在 PR 中未 merge，`PROJECT_STATUS` 与 README 的产品能力描述以 main 实际状态为准。

### 当前里程碑：Product Stage A0 真相基线

```text
Phase 0 真实基线 ✅
→ Phase 1 五个 Facade + Architecture Guard ✅
→ TaskPackV1 + SQLite migration/rollback ✅
→ ExecutionTraceV1 ✅
→ EvaluationV1 ✅
→ LessonV1 ✅
→ SourceRecordV1 ✅
→ ClaimV1 ✅
→ EvidenceV1 ✅
→ ResearchPackageV1 ✅
→ KnowledgeUnitV1 + RelationV1 ✅
→ LearningArtifactV1 + MasterySignalV1 ✅
→ MachineKnowledgeUnitV1 ✅
→ 移除代码内默认管理员 Key ✅
→ 阻止 Token 请求者自选管理员角色 ✅
→ 主网关 Rate Limiter + proxy trust 边界 ✅
→ 统一 Safe HTTP + approved roots ✅
→ stable hash + Vector/FTS shadow switch/rollback ✅
→ 通用 Migration Runner + Phase 3 集成验收 ✅
→ GitHub Research candidate-only 持久化闭环 ✅
→ Knowledge/Learning/Mastery/Machine Knowledge 治理 ✅
→ `read file:` Planner tracer、Evaluation 与 Sleep Loop 构件 ✅
→ Phase 9 Contract & Tracer Alpha 历史基线 ✅
```

下一刀：继续补齐失败→retry→replay 的完整 UI/CI 矩阵、Tauri WebView 点击级证据和同一隔离数据集的桌面回读，并推进通用 Planner 与更完整的用户级 Job Center 交互。公开 `v0.5.0` 资产已完成独立 Release 门禁和下载回读；图像 OCR 基础依赖和真实图像门禁已接入；ASR、媒体时间戳、内容匹配 Evidence 与人工真值准确率仍未闭环。任何门禁通过都不会自动把 candidate 提升为 verified truth。

本阶段明确不宣称：单个 GitHub 仓库已构成独立交叉验证、candidate 已成为 verified truth，或完整认知执行闭环、Tauri WebView 点击级 UI、通用 Planner、完整用户级 Job Center、公开 Alpha/Beta 能力已完成；公开稳定 `v0.5.0` 发布资产本身已完成并有独立回读证据。

未来设计与候选执行轨道见 [`docs/FUTURE_EXECUTION_BLUEPRINT.md`](docs/FUTURE_EXECUTION_BLUEPRINT.md)；当前事实与限制见 [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)。

开源项目、知识库软件与 Obsidian/PKM 的吸收状态、前后端阶段、Adapter 边界和验收门禁见 [`docs/ABSORPTION_EXECUTION_MATRIX.md`](docs/ABSORPTION_EXECUTION_MATRIX.md)；候选登记不等于运行时集成。

## 五分钟启动

```bash
python -m pip install -e ".[dev]"
python -m app.runtime_entrypoint migrate
python -m app.runtime_entrypoint core
```

- Core API：`http://127.0.0.1:8000/docs`
- Knowledge Dashboard：`http://127.0.0.1:8000/kb`
- Knowledge API：`http://127.0.0.1:8000/kb/docs`
- 实时健康与路由数：`http://127.0.0.1:8000/health`

## 当前可运行基线

| 入口 | 作用 |
|---|---|
| `POST /run` | route → retrieve → supported-intent plan → permission → real tool evidence → multidimensional evaluation → lesson；当前已验证 `read file:` 纵向切片 |
| `GET /diagnostics` | 本地只读 runtime/health、migration 状态计数和安全的 unreleased manifest 摘要；不泄露路径或 provenance |
| `POST /kb/pipeline` | 提取、标签、摘要、事实候选与索引；不自动证明事实正确 |
| `POST /kb/search` | 关键词、向量或混合检索 |
| `GET/POST /sleep-loop?action=...` | 有证据约束的无人值守任务循环 |
| `POST /kb/quality` | 准确率测量与文件总账汇总；调用者证据、来源独立性、内容匹配和静态来源建议仍为候选 |

旧的细粒度接口仍为兼容层；新增能力优先进入复合端点，不再继续平铺路由。

## 当前模块边界

```text
app/                    核心服务、摄入、工具、工作流（技术实现边界）
knowledge_base/         可安装的文档、卡片、检索、复习、机器知识与领域路由包
  routers/              稳定复合 API、质量 API、投影 API
inspiration_research/   可安装的研究发现、Intake 与候选项目雷达包
Inspiration-Research/   deprecated source-checkout launcher 与说明
shared/                 SQLite、管道、证据、图谱、配置、鉴权等共享能力
shared-contracts/       Schema、fixture、适配器和开源项目注册表
tests/                  Core/共享能力测试
knowledge_base/tests/   KB 独立测试
config/                 运行时策略与 canonical naming registry
workspace/              Intake 与方向性记录，不是主运行时
```

当前真实架构见 [`docs/architecture/CURRENT_ARCHITECTURE.md`](docs/architecture/CURRENT_ARCHITECTURE.md)，文档入口见 [`docs/README.md`](docs/README.md)。命名与编码契约见 [`docs/NAMING_ENCODING_CONVENTIONS.md`](docs/NAMING_ENCODING_CONVENTIONS.md)，验证频率以 [`docs/VERIFICATION_POLICY.md`](docs/VERIFICATION_POLICY.md) 为唯一流程记录。

## 命名与仓库治理

- 机器标识使用稳定英文 canonical ID；中英文只用于显示层。
- `config/naming-registry.yaml` 是服务名称、别名、包名和 API 前缀的单一事实源。
- pre-commit 检查 staged index，CI 检查 Git HEAD，避免本地工作树掩盖提交内容。
- 文本默认 UTF-8、NFC 与 LF；Windows 命令脚本保留 CRLF 例外。

## 项目边界

外部项目能力吸收已经结束。后续只开发本仓库，不扫描、测试、修改或同步外部 `Obsidian-Assistance`、个人 Vault 或其他数据目录。历史映射保留在 [`docs/ABSORPTION_OBSIDIAN_ASSISTANCE_2026-07-13.md`](docs/ABSORPTION_OBSIDIAN_ASSISTANCE_2026-07-13.md)，不再作为新一轮迁移入口。

## 安全模式

默认配置是本机开发模式：

```yaml
app.environment: development
auth.enabled: false
cors.allow_origins: ["*"]
```

管理员凭据没有内置默认值。任何环境启用鉴权后，都必须通过部署系统显式提供强 `COGNITIVE_API_KEY`，或在 `auth.api_key_file` 指向的本地运行时文件中配置强 key；未配置时所有受保护入口均拒绝访问。测试使用隔离 fixture 注入临时 key，不依赖全局开发凭据。

生产模式必须显式设置：

```bash
export COGNITIVE_ENV=production
export COGNITIVE_AUTH_ENABLED=true
export COGNITIVE_API_KEY='<secret-from-deployment-system>'
export COGNITIVE_JWT_SECRET='<independent-jwt-secret-from-deployment-system>'
export COGNITIVE_CORS_ORIGINS='https://your-ui.example'
```

CORS 来源也可写入 `config/settings.yaml`。生产环境保留开发默认值、缺失或弱密钥、非法 key 文件或错误 CORS schema 时应用会拒绝启动。development/local/test 同样拒绝弱 API key，不会隐式获得管理员身份。

数据库 `restore` 命令只生成并校验离线恢复候选，不覆盖活动数据库；实际切换必须先停止全部 API、healthcheck 和 worker，再由运维人员离线完成。

## 验证

```bash
python -m pytest tests/test_naming_conventions.py -q --tb=short  # 定向测试示例
python scripts/check_repository_conventions.py --source worktree
pre-commit run --all-files
```

开发中只运行受影响的定向测试；diff 冻结后运行一次必要完整门禁，推送后以一次 GitHub CI 为准。详细触发规则见 [`docs/VERIFICATION_POLICY.md`](docs/VERIFICATION_POLICY.md)。

CI 使用 `pyproject.toml` 作为依赖与工具配置单一事实源；`requirements.txt` 仅作为兼容安装清单并与核心依赖保持同步。

## 许可、安全与变更记录

- 项目许可：[`LICENSE`](LICENSE)
- 第三方组件说明：[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
- 漏洞报告：[`SECURITY.md`](SECURITY.md)
- 发布历史与已知完整性限制：[`CHANGELOG.md`](CHANGELOG.md)
