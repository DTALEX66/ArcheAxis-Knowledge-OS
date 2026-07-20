# 项目当前状态

> 更新：2026-07-20。本页是当前状态入口；旧审计文件是历史快照。

## 当前阶段

项目已完成 **Phase 9：Minimum Complete System Alpha**。GitHub Research、Knowledge/Learning/Mastery/Machine Knowledge 治理、Dynamic Planner、reviewed Evaluation 与统一 Sleep Loop 已形成五条受治理端到端闭环，并通过完整本地 release 门禁。Phase 10 已建立首个本地只读 diagnostics baseline：安全汇总 health 与 migration 状态计数，缺失 runtime database 或 migration 状态时 fail-closed 为 `unavailable`，且不暴露路径或 provenance。GitHub repository 仍只形成 quarantined、可追溯、持久化且必须人工复核的 ResearchPackage；尚未完成 Installer、多端发布或公开 Alpha/Beta/Stable，不能自动将 candidate 提升为 verified truth。

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
- 持久化哈希已使用 versioned SHA-256；TaskPack、Vector、FTS 与 Research schema 已统一注册到 migration operator。
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
- CI 的 test/lint job 使用 `uv` 与 `requirements-ci.txt` 最小依赖；wheel-smoke 仍安装完整 `requirements.txt` 并在仓库外验证真实 wheel/runtime，避免以提速为由削弱发布覆盖。
- `scripts/run_taskpack_agent.py`：一个 TaskPack 使用一个可续接 writer lineage；高风险任务同步 exact-tree reviewer，允许最多 N 次 NO-GO 修复并在最后一次修复后保留终局 review，发布后强制 clean、`HEAD == origin/main` 与 exact-SHA CI。固定时间片反复重启 agent 的旧 runner 已废弃。

## 仍保留的债务

1. `knowledge_base/api.py` 仍包含遗留领域路由；复合、质量、投影路由已经拆出，后续继续按领域迁移。
2. `knowledge_base` 与 `inspiration_research` 均可安装；`Inspiration-Research` 只保留 launcher 兼容，不再保存第二份业务实现。
3. 旧细粒度 API 仍公开，路由面尚未真正缩减。
4. 生产部署尚缺独立容器/反向代理/并发负载验证。
5. OCR/ASR 的真实准确率取决于用户提供人工标注金标准，代码不能代替人工真值。
6. Mypy 尚未作为零错误门禁；当前历史模块仍有返回类型、异构字典和可选导入类型债务。
7. `file_read` 已打通 Planner/Evidence/Evaluation/Lesson 首条纵向 tracer；通用 Dynamic Planner、更多真实工具意图、Reviewed Feedback 和统一 Runtime/Sleep Loop 仍属于后续路线图。
8. Research、Knowledge candidate、Learning Artifact、Mastery Signal 与 Machine Knowledge 的治理构件已有真实路径；尚缺将它们收敛为单一 command/outbox/worker/audit 时间线的可交互最小闭环。未来编排方向见 `FUTURE_EXECUTION_BLUEPRINT.md`。

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

The implementation persists source records, source provenance, claims, evidence, research packages, governance findings, and the package-to-intake relation in SQLite tables owned exclusively by `MigrationOperator` owner `research.sqlite` / migration `004_phase4_research_package_v1`. Apply and rollback require owner-bound backup hashes and manifests; status revalidates the live schema. The storage and strict-read boundaries reconstruct and validate the complete candidate provenance graph. Legacy external trending/auto routes fail closed. External GitHub content is never promoted to verified truth, same-repository metadata/README extraction counts as one independent source group, and every package requires human review. Phase 5+, general Alpha, and full five-loop system closure remain out of scope.
