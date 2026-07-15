# Cognitive-Loop-OS

[![CI](https://github.com/DTALEX66/Cognitive-Loop-OS/actions/workflows/ci.yml/badge.svg)](https://github.com/DTALEX66/Cognitive-Loop-OS/actions/workflows/ci.yml)

Cognitive-Loop-OS 的目标不是堆积 AI 功能，而是建立一条可追溯、可审核、可回滚的认知闭环：

```text
Research → Evidence → Knowledge → Learning
→ Plan → Permission → Execution → Trace → Evaluation → Lesson
```

项目采用本地优先的 FastAPI/SQLite 模块化单体。Phase 0 基线、Phase 1 Facade/Architecture Guard 与 Phase 2 首批版本化 Contracts 已完成；下一阶段是 Phase 3 安全和数据正确性 P0。Phase 3 尚未开始，Phase 7 真实 Runtime 和 Phase 9 Alpha 闭环也尚未完成。

## 规划与进度

进度按“真实闭环 + 回滚证据”判定，不按文件、接口或测试数量计算。

| 阶段 | 目标 | 状态 | 当前检查点 |
| --- | --- | --- | --- |
| Phase 0 | 仓库资产、API、依赖、测试与安全基线 | ✅ 已完成 | 基线报告已进入 `migrations/reports/phase-0/` |
| Phase 1.0 | 命名、编码、Git index/HEAD 治理 | ✅ 已完成 | registry、scanner、pre-commit、CI 已接通 |
| Phase 1.1 | Runtime/Knowledge/Research/Enhancement/Contracts Facade + Architecture Guard | ✅ 已完成 | 五个 Facade、canonical Research 包、Architecture Guard 与兼容测试已接通 |
| Phase 2 | 版本化 Contracts 与旧对象 Adapter | ✅ 已完成首批合同 | 路线图列出的 Research、Knowledge/Learning、Machine Knowledge 与 Runtime 合同均已有严格 tracer |
| Phase 3 | 鉴权、Safe HTTP、approved roots、迁移与回滚 P0 | ⬜ 规划中 | 安全任务独立提交，不混入 Facade |
| Phase 4–6 | Research、Knowledge/Learning、Enhancement 闭环 | ⬜ 规划中 | 以 evidence/candidate 治理为前提 |
| Phase 7–8 | Dynamic Planner、多维 Evaluation、统一 Sleep Loop | ⬜ 规划中 | 替换固定 echo 与二值评价缺口 |
| Phase 9 | Minimum Complete System Alpha | ⬜ 规划中 | 五条端到端闭环必须真实通过 |
| Phase 10 | 产品化、诊断、升级与多端发布 | ⬜ 规划中 | 仅在 Alpha 闭环完成后启动 |

### 当前里程碑：Phase 2 Contracts Release Train

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
→ Phase 3 安全 P0（下一步）
```

当前刀：**Phase 3 第一项——移除代码内默认管理员 Key**。该安全任务必须使用独立 frozen tree、完整门禁、必要 reviewer 与 exact-SHA CI，不混入本次低风险合同 Release Train。

本阶段明确不宣称：Phase 3 安全 P0、Phase 4 Research 闭环、Phase 7 Dynamic Planner、Phase 8 统一 Sleep Loop 或 Phase 9 Minimum Complete System Alpha 已完成。

完整计划见 [`docs/EXECUTION_ROADMAP.md`](docs/EXECUTION_ROADMAP.md)，当前交接与执行顺序见 [`docs/HANDOFF_2026-07-14.md`](docs/HANDOFF_2026-07-14.md)。

## 五分钟启动

```bash
python -m pip install -e ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

- Core API：`http://127.0.0.1:8000/docs`
- Knowledge Dashboard：`http://127.0.0.1:8000/kb`
- Knowledge API：`http://127.0.0.1:8000/kb/docs`
- 实时健康与路由数：`http://127.0.0.1:8000/health`

## 当前可运行基线

| 入口 | 作用 |
|---|---|
| `POST /run` | route → retrieve → echo-based compile → permission → registered tool execution → binary evaluation → memory |
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
