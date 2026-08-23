# 项目当前状态

> **v0.6.8 发布裁决（2026-08-23）**：`v0.6.8 stable — RELEASED`。标签精确绑定 `93e58a3b2c537dd348903dd2296933e0cfb5a503`；main CI `32607097436`、Release `32607789507`、三种 Windows 分发包生命周期和 9 项公开资产独立下载读回均通过。该裁决只证明发布层，不证明 v0.6.0 任务包全部完成；产品逐项结论仍为 `PARTIAL`，见 [`current/AXR_060_COMPLETION_AUDIT_2026-08-23.md`](current/AXR_060_COMPLETION_AUDIT_2026-08-23.md)。

> 更新：2026-08-09。本页是能力状态入口；旧审计文件是历史快照。机器无关的恢复检查见 [`HANDOFF_2026-07-21.md`](HANDOFF_2026-07-21.md)，实时分支、SHA、dirty 状态与 CI 必须从 Git/GitHub 读取。

## 发布真相

- 当前源码版本为 `0.6.8`；packaged source manifest 按合同仍是 `unreleased / public=false`，公开 v0.6.8 资产中的 schema v3 identity 是 `stable / public=true`；两者分别表达源码占位真相和已发布资产真相。
- `v0.4.0` 是保留的 historical release，但 readback 已证明 incomplete checksum payload coverage：公开 installer 名称与 manifest 名称不一致，且有一个额外公开 payload 未被 manifest 覆盖。历史 tag、Release 和资产不原地替换。
- `v0.6.8` 已满足 tag 精确绑定 `main`、exact-SHA Full Qualification、NSIS/Green/Portable 生命周期、公开资产集合与 checksum payload allowlist 双向一致、provider digest、下载后 SHA-256、schema v3 identity 和依赖锁读回；当前没有 Authenticode 签名声明。

## 当前阶段

历史 **Phase 9：Contract & Tracer Alpha** 已完成，但不代表完整产品 Alpha。当前处于 ArcheAxis Knowledge 的 Obsidian-compatible Workspace foundation 阶段：GitHub/普通网页/本地文件 Research，以及 Knowledge/Learning/Mastery/Machine Knowledge 的后端治理构件已有真实路径；Planner 只有 `read file:` 首条受限 tracer，统一 Runtime/Sleep Loop、Reviewed Feedback 和通用 Planner 属于 deferred 能力，不是当前产品入口。本地 Workspace 已具备打包页面、loopback-only 写入、真实导入入口、只返回聚合事实的状态接口，以及不暴露内部 ID 的 Job/Delivery 投影。Workspace Job/Outbox migration owner、同事务写入、同步终态、严格 readback、按需 dispatcher、服务级 lease/retry、SSE 和 lease-fenced Worker 已交付；本地真实 Chromium upload → dispatch → receipt → reload 门禁已验证，Tauri WebView 点击级验收和交互式 Job Center 仍属于后续产品证据。图像 OCR 基础依赖、真实图像门禁、Windows 构建、NSIS lifecycle 和公开 `v0.5.0` installer 资产已验证；ASR、签名发布、多端发布及更高阶 Alpha/Beta 能力仍未完成。外部来源仍只形成可追溯、持久化且必须复核的 candidate，不能自动提升为 verified truth。产品命名契约见 `docs/truth/NAMING_CONTRACT_V1.md`（ArcheAxis / 星环知识平台）。

## 已验证能力

- Core `/run` 的 route/execute/trace/evaluate/lesson 链可运行；显式 `read file: <repo-relative-path>` 已规划为真实 `file_read`，并要求非 dry-run、可归因工具证据和多维 Evaluation。其他 Goal 尚无通用 Dynamic Planner，不能把单一 tracer 视为完整认知闭环。
- Runtime、Knowledge、Research、Enhancement、Contracts 五个 Facade 已有真实 tracer bullet；Phase 1 的 Contracts 起点是 identity re-export，不代表全量版本化 Schema。
- Phase 2 已建立 `TaskPackV1`、`ExecutionTraceV1`、`EvaluationV1`、`LessonV1`、`SourceRecordV1`、`ClaimV1`、`EvidenceV1`、`ResearchPackageV1`、`KnowledgeUnitV1`、`RelationV1`、`LearningArtifactV1`、`MasterySignalV1` 与 `MachineKnowledgeUnitV1`。新增 Learning Artifact 对现有 Enhancement candidate 无损往返且禁止 caller-supplied 状态升级；Machine Knowledge 对 decoded legacy row 无损往返，将旧 active 状态明确标为 unverified/deprecated，并拒绝 approved 治理语义向旧行静默降级。
- Research 已迁为可安装的 `inspiration_research` 包；旧连字符目录只保留 deprecated source-checkout launcher。
- Architecture Guard 在 CI 阻止新增路径注入、反向依赖和外部绝对路径硬编码。
- Core 与 Knowledge-Base 使用单端口挂载。
- Ruff 覆盖 `app shared knowledge_base inspiration_research Inspiration-Research` 及集成适配器和脚本。
- OS 与 KB 使用分离测试套件，避免包名和 sleep-loop 状态账本互相干扰。
- `/health` 实时递归统计 HTTP 操作，不再维护手写端点数字。
- 数据库通用表名、排序字段经过标识符/Schema 校验。
- `/kb/export` 只允许明确的知识表白名单。
- `auth.enabled` 已接入中间件；生产模式拒绝关闭鉴权、通配 CORS 或缺少 API Key。
- Runtime 源码不再内置管理员 Key；开发和测试凭据必须显式配置，Token 请求者不能自行提升为管理员。
- 主网关已接入分策略 Rate Limiter；所有受跟踪 Uvicorn 入口禁用隐式 proxy-header rewriting，未受信代理头、双凭据与无效认证的早期拒绝也必须消耗 pre-auth 限额并进入确定性 429 边界。
- 外部 HTTP 调用已收敛到 Safe HTTP policy，覆盖私网/metadata/redirect/响应大小/类型/timeout；本地摄入与投影使用 approved roots 和 symlink/junction containment。
- 持久化哈希已使用 versioned SHA-256；Core、TaskPack、Vector、FTS、Research、Knowledge Governance 与 Workspace 共九个 owner 已统一注册到 migration operator。
- Workspace 可将普通网页、GitHub URL 与 approved-root 本地文件持久化为候选 ResearchPackage，并通过独立连接严格读回；浏览器写入仅允许 loopback，本地页面不收集 API key/JWT；本地 Chromium upload → dispatch → receipt → reload smoke 已验证。
- Workspace 总览已移除静态运营数字和伪服务状态，只读取本地数据库聚合与 packaged unreleased Release Manifest；Job/Delivery 页面已提供真实 pending/delivered/receipt 聚合与按需操作，尚未接线的产品入口明确显示无真实数据。
- Learning 审批与卡片投影使用同事务持久收据；Runtime 只读取 approved Machine Knowledge，Machine Knowledge 审批/弃用使用 append-only migration-owned 收据并拒绝冲突重放。
- 媒体基础链已用真实 FFmpeg 验证 MP4 → 16 kHz mono PCM WAV、WAV 元数据读取和关键帧 PNG 尺寸核验；图像 OCR 基础适配器已用真实图片验证，ASR、媒体时间戳、内容匹配 Evidence 与人工真值准确率仍未闭环。
- n8n、Airflow、LiteLLM 和 crawler 适配器不再返回 stub 假成功。
- Obsidian 外部路径必须显式传入，API 不再默认访问个人 E 盘。
- 外部 A 项目（Obsidian-Assistance）的分析与通用能力吸收已结束；后续严格只读且不再扫描或作为迁移目标。

## 质量能力

- `shared/processing_manifest.py`：文件级 JSONL、源/输出 SHA-256 和指纹校验恢复。
- `app/ingestion/multi_format.py::convert_directory_resumable()`：原子落盘 Markdown、失败重试、变更重跑。
- `shared/accuracy_benchmark.py`：人工真值 CER/WER；无样本明确 `unverified`。
- `shared/evidence_verification.py`：文本命中证据；所有调用者提供的内容最高为候选，当前没有服务端可信 provenance，必须人工复核。
- `shared/content_quality.py`：乱码、水印、误导性 100% 和 Wikilink 静态审计。
- `shared/oer_crosswalk.py`：静态开放来源发现建议（遗留文件名），不检索内容、不检查许可、不做 claim-level crosswalk。
- CI 的 test/lint、browser 和 Windows runtime job 从 `pyproject.toml` 的锁定 `uv` dependency groups 导出带哈希的最小依赖；wheel-smoke 仍在仓库外验证真实 wheel/runtime，避免以提速为由削弱发布覆盖。
- 全局 TaskPack runner 由 `D:/All projects/Workflow-assistance/scripts/workflow/run_taskpack_agent.py` 维护；OS 调用时显式传入 `ArcheAxis-Knowledge-OS`、实际目标远端与本项目 TaskPack。它提供单 writer、冻结复审和 exact-SHA 编排，但不替代本项目的架构/数据库/权限门禁。
- 开源项目、知识库软件与 Obsidian/PKM 的阶段化吸收矩阵见 `docs/ABSORPTION_EXECUTION_MATRIX.md`（v2，2026-08-11 更新）；权威吸收决策账本见 `docs/truth/SUPPLY_CHAIN_LEDGER.json`（v2，46 个组件含吸收决策）。旧 101 行 registry/ledger（2026-07-22）已被替代。

## 仍保留的债务

1. `knowledge_base/api.py` 仍包含遗留领域路由；复合、质量、投影路由已经拆出，后续继续按领域迁移。
2. `knowledge_base` 与 `inspiration_research` 均可安装；`Inspiration-Research` 只保留 launcher 兼容，不再保存第二份业务实现。
3. 旧细粒度 API 仍公开，路由面尚未真正缩减。
4. 生产部署尚缺独立容器/反向代理/并发负载验证。
5. OCR 的 Pillow/pytesseract 依赖、Tesseract `eng` 语言数据、真实图像测试和 CI 字体/语言门禁已 GREEN；H2 bake-off 已实跑闭环：Tesseract（eng/chi_sim）与 RapidOCR 三语种对比（RapidOCR avg CER 0.0076 实测最优）、faster-whisper ASR 转写（英文 CER 0.0；中文需 chi 模型）、可重复运行的 `scripts/run_bakeoff.py` CLI 已入库；人工标注准确率基准、PaddleOCR/EasyOCR 及更大 ASR 模型仍需重依赖下载。
6. Mypy 尚未作为零错误门禁；当前历史模块仍有返回类型、异构字典和可选导入类型债务。
7. `file_read` 已打通 Planner/Evidence/Evaluation/Lesson 首条纵向 tracer；通用 Dynamic Planner、更多真实工具意图、Reviewed Feedback 和统一 Runtime/Sleep Loop 仍属于后续路线图。
8. `workspace.sqlite` migration owner、connection-scoped Research writer、Research graph/Job/Outbox 同事务、严格 Job readback、同步命令终态、按需 Outbox dispatcher、Delivery Receipt 与不暴露内部 ID 的用户级 Job/Delivery 投影已交付；仍缺真实 Tauri WebView 点击级投递证据、失败→retry→replay 的完整 UI/CI 矩阵、SSE 审计时间线、异步 Worker 和更完整交互式 Job Center。未来编排方向见 `FUTURE_EXECUTION_BLUEPRINT.md`。

## 冻结执行基线（权威蓝图与增补）

CODEX 冻结的后续执行蓝图与增补包是后续 Horizon（H1-H10 与 Web/KLC 增补）的唯一定义源，位于仓库 `docs/`：

- 冻结基线：[`docs/truth/FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md`](truth/FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md)
- 执行任务包：[`docs/taskpacks/DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md`](../taskpacks/DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md)
- Web 增补：[`docs/taskpacks/MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md`](../taskpacks/MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md)
- Capability-first 增补：[`docs/taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md`](../taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md)
- 追加式状态日志：[`docs/truth/EXECUTION_STATUS_LOG.md`](truth/EXECUTION_STATUS_LOG.md)
- 状态交接文档：[`docs/truth/H0_H1_STATUS_HANDOFF.md`](truth/H0_H1_STATUS_HANDOFF.md)

当前进度：H0（v0.5.1）已完成并 merge main；H1 后端核心（PR #72）已 merge main；AXW-022A PDF.js 前端渲染（PR #74）已 merge main；MFX Batch 0 止损（#75/#76/#77）已 merge；AXW-022B 证据批注（#78）已 merge；AXW-023A DOCX Adapter（#79）已 merge；吸收总图谱分析（#80）已 merge；ADOPT 项吸收实现（#81）已 merge；H2 管线整合已 merge（#82 路由/质量门、#97/#99 bake-off 实跑、#105 Magika 检测、#124 Evidence 接入、#125 SM-2 学习调度、#126 bake-off CLI）。本页产品能力描述以 main 实际状态为准；任务/证据状态见上述权威文档。

## 正式门禁

```bash
python -m pytest tests -q --tb=short
cd knowledge_base && python -m pytest tests -q --tb=short
python -m pytest integration-tests -q --tb=short
python -m ruff check app shared knowledge_base inspiration_research Inspiration-Research shared-contracts/adapters app/workflow integration-tests scripts
```

最终交付时以这些命令的真实输出为准，不以本页手写数字证明完成。
## Phase 4 Research Closure Update

Phase 4 Research is now implemented for the GitHub repository source path. The current supported closure is:

```text
canonical GitHub URL -> Safe HTTP collect -> quarantine -> parse -> claims
-> evidence -> cross-validation findings -> persisted candidate ResearchPackageV1
```

The implementation persists source records, source provenance, claims, evidence, research packages, governance findings, and the package-to-intake relation in SQLite tables owned exclusively by `MigrationOperator` owner `research.sqlite` / migration `004_phase4_research_package_v1`. Apply and rollback require owner-bound backup hashes and manifests; status revalidates the live schema. The storage and strict-read boundaries reconstruct and validate the complete candidate provenance graph. Legacy external trending/auto routes fail closed. External GitHub content is never promoted to verified truth, same-repository metadata/README extraction counts as one independent source group, and every package requires human review. This section documents only Phase 4 Research closure; it does not claim general Alpha or full five-loop system closure.
