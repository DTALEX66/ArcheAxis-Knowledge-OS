# Cognitive-Loop-OS

> **元枢·观心 / ArcheAxis Cognitive Workspace**：本地优先、证据驱动的认知工作台，连接真实导入、candidate 治理和可追溯的认知执行基础链。

## 当前重点

- **真实 Workspace 基础链**：网页、GitHub URL、本地文件导入 → candidate Research/Evidence → Knowledge/Learning/Mastery 治理；执行侧当前以 `read file:` 受限 Planner tracer 和局部闭环为主。
- **可治理的运行时**：SQLite 持久化、Outbox/Receipt、失败不改状态、重试与回读，以及不暴露内部审计 ID 的公开投影。
- **双端验证**：CI 已包含 Windows Tauri 构建、运行时和 NSIS 生命周期门禁；完整 HTTP → SQLite → Chromium/Tauri UI 投递、点击级 WebView 证据和公开发布资产仍在收口。
- **当前版本**：`0.4.0`；Release Manifest 仍为 `unreleased / public=false`，公开 Alpha/Beta/Stable 发布尚未宣告。

Research candidate 仍必须经过人工审查和来源独立性验证，不能自动当作 verified truth。当前事实、限制和验证证据见 [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) 与 [`docs/VERIFICATION_POLICY.md`](docs/VERIFICATION_POLICY.md)。

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

[![CI](https://github.com/DTALEX66/Cognitive-Loop-OS/actions/workflows/ci.yml/badge.svg)](https://github.com/DTALEX66/Cognitive-Loop-OS/actions/workflows/ci.yml)

Cognitive-Loop-OS 的目标不是堆积 AI 功能，而是建立一条可追溯、可审核、可回滚的认知闭环：

```text
Research → Evidence → Knowledge → Learning
→ Plan → Permission → Execution → Trace → Evaluation → Lesson
```

项目采用本地优先的 FastAPI/SQLite 模块化单体。candidate Research、Knowledge/Learning/Mastery/Machine Knowledge 治理、Evaluation、Sleep Loop 与受限 Planner tracer 已有受治理构件和局部闭环；GitHub metadata/README 仍不会自动成为 verified truth。Workspace 已提供真实本地导入入口、迁移 owner 管理的 Job/Outbox/receipt 同事务边界和只读 Job Center；dispatcher 已有服务级成功/失败/重试/lease 保护，但完整 HTTP → SQLite → Chromium/Tauri UI 投递、统一 audit timeline、SSE、通用 Planner、异步 Worker 和交互式用户级 Job Center 尚未实现。当前已有 Release Manifest、媒体基础链、图像 OCR、Windows 构建和 NSIS 生命周期门禁；ASR、公开发布资产与 Tauri WebView 点击级证据仍未闭环。

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
| Product Stage A0 | 产品真相、诊断、媒体摄入与发布门禁 | 🟡 收口中 | Job/Outbox/OCR 基线与 Windows/NSIS 门禁已接入；真实 UI 投递、ASR、公开发布资产仍待完成 |

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

下一刀：把已有 Job/Outbox/Receipt 服务级证据接到真实 HTTP → SQLite → Chromium/Tauri UI 投递，补齐 pending/delivered、失败→retry→replay、无重启回读和 Tauri WebView 点击级证据；随后再推进通用 Planner、异步 Worker、SSE 和用户级 Job Center。图像 OCR 基础依赖和真实图像门禁已接入；ASR、媒体时间戳、内容匹配 Evidence 与人工真值准确率仍未闭环。任何门禁通过都不会自动把 candidate 提升为 verified truth。

本阶段明确不宣称：单个 GitHub 仓库已构成独立交叉验证、candidate 已成为 verified truth，或完整认知执行闭环、Tauri WebView 点击级 UI、公开发布资产、公开 Alpha/Beta/Stable 已完成。

未来设计与候选执行轨道见 [`docs/FUTURE_EXECUTION_BLUEPRINT.md`](docs/FUTURE_EXECUTION_BLUEPRINT.md)；当前事实与限制见 [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)。

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
app/                    核心认知运行时、摄入、工具、工作流
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
