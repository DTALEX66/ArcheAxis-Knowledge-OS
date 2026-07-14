# Cognitive-Loop-OS

[![CI](https://github.com/DTALEX66/Cognitive-Loop-OS/actions/workflows/ci.yml/badge.svg)](https://github.com/DTALEX66/Cognitive-Loop-OS/actions/workflows/ci.yml)

Cognitive-Loop-OS 是本地优先、证据约束的认知与知识运行时。当前模块化单体以 FastAPI、SQLite 和可安装 Knowledge Base 为核心，覆盖研究发现、内容摄入、检索、知识结构化、学习复习、受控执行、追踪和候选证据；动态规划、多维评估与端到端可信闭环仍在路线图中。

## 五分钟启动

```bash
python -m pip install -e ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- Core API：`http://127.0.0.1:8000/docs`
- Knowledge Dashboard：`http://127.0.0.1:8000/kb`
- Knowledge API：`http://127.0.0.1:8000/kb/docs`
- 实时健康与路由数：`http://127.0.0.1:8000/health`

## 稳定入口

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
Inspiration-Research/   研究发现与候选项目雷达
shared/                 SQLite、管道、证据、图谱、配置、鉴权等共享能力
shared-contracts/       Schema、fixture、适配器和开源项目注册表
tests/                  Core/共享能力测试
knowledge_base/tests/   KB 独立测试
config/                 运行时策略与 canonical naming registry
workspace/              Intake 与方向性记录，不是主运行时
```

项目交接见 [`docs/HANDOFF_2026-07-14.md`](docs/HANDOFF_2026-07-14.md)，当前真实架构见 [`docs/architecture/CURRENT_ARCHITECTURE.md`](docs/architecture/CURRENT_ARCHITECTURE.md)，Phase 0–10 规划见 [`docs/EXECUTION_ROADMAP.md`](docs/EXECUTION_ROADMAP.md)，文档入口见 [`docs/README.md`](docs/README.md)。命名与编码契约见 [`docs/NAMING_ENCODING_CONVENTIONS.md`](docs/NAMING_ENCODING_CONVENTIONS.md)，验证频率以 [`docs/VERIFICATION_POLICY.md`](docs/VERIFICATION_POLICY.md) 为唯一流程记录。

## 命名与仓库治理

- 机器标识使用稳定英文 canonical ID；中英文只用于显示层。
- `config/naming-registry.yaml` 是服务名称、别名、包名和 API 前缀的单一事实源。
- pre-commit 检查 staged index，CI 检查 Git HEAD，避免本地工作树掩盖提交内容。
- 文本默认 UTF-8、NFC 与 LF；Windows 命令脚本保留 CRLF 例外。

## Obsidian-Assistance 吸收

本仓库吸收的是通用能力，不复制正式 Vault、课程正文、私人路径、媒体、OCR/ASR 全文或缓存。最新吸收包括：

- 文件级 JSONL 处理总账与失败重试；
- 同名源文件防碰撞键；
- 人工真值 CER/WER 准确率基准；
- 内容命中后才允许生成证据候选；
- 所有调用者提供的证据最高只作为候选；当前实现不具备服务端 provenance 注册或签名，因此不能自动升级为已核验；
- 可恢复多格式目录摄入。

完整映射见 [`docs/ABSORPTION_OBSIDIAN_ASSISTANCE_2026-07-13.md`](docs/ABSORPTION_OBSIDIAN_ASSISTANCE_2026-07-13.md)。

## 安全模式

默认配置是本机开发模式：

```yaml
app.environment: development
auth.enabled: false
cors.allow_origins: ["*"]
```

生产模式必须显式设置：

```bash
export COGNITIVE_ENV=production
export COGNITIVE_AUTH_ENABLED=true
export COGNITIVE_API_KEY='<secret-from-deployment-system>'
export COGNITIVE_JWT_SECRET='<independent-jwt-secret-from-deployment-system>'
export COGNITIVE_CORS_ORIGINS='https://your-ui.example'
```

CORS 来源也可写入 `config/settings.yaml`。生产环境保留开发默认值、弱密钥、非法 key 文件或错误 CORS schema 时应用会拒绝启动。固定开发 Key 只在 development/local/test 环境加载。

数据库 `restore` 命令只生成并校验离线恢复候选，不覆盖活动数据库；实际切换必须先停止全部 API、healthcheck 和 worker，再由运维人员离线完成。

## 验证

```bash
python -m pytest tests/test_naming_conventions.py -q --tb=short  # 定向测试示例
python scripts/check_repository_conventions.py --source worktree
pre-commit run --all-files
```

开发中只运行受影响的定向测试；diff 冻结后运行一次必要完整门禁，推送后以一次 GitHub CI 为准。详细触发规则见 [`docs/VERIFICATION_POLICY.md`](docs/VERIFICATION_POLICY.md)。

CI 使用 `pyproject.toml` 作为依赖与工具配置单一事实源；`requirements.txt` 仅作为兼容安装清单并与核心依赖保持同步。
