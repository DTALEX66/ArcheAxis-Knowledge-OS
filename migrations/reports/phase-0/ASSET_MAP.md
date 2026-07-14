# Phase 0 资产地图

> Git 基线：`469c39dcedf187e4c99d816728a2b38524881694`。本报告只覆盖当前仓库中的 Git 跟踪文件。

## 总览

- 跟踪文件：341
- HTTP 路由条目：143
- HTTP 操作：143
- 审计边界：当前仓库；外部仓库、个人资料库和运行时用户数据均不在范围内。

## API 服务边界

| 服务 | 路由条目 | HTTP 操作 |
|---|---:|---:|
| `core` | 20 | 20 |
| `inspiration-research` | 14 | 14 |
| `knowledge-base` | 109 | 109 |

## 顶层资产

| 顶层区域 | 文件数 |
|---|---:|
| `.codex.example` | 2 |
| `.github` | 1 |
| `Inspiration-Research` | 21 |
| `app` | 43 |
| `codex-taskpacks` | 3 |
| `config` | 7 |
| `docker` | 1 |
| `docs` | 96 |
| `integration-tests` | 2 |
| `knowledge_base` | 29 |
| `root` | 15 |
| `scripts` | 4 |
| `shared` | 45 |
| `shared-contracts` | 39 |
| `tests` | 21 |
| `workspace` | 12 |

## 运行资产分工

- `app/`：核心认知运行时、路由、权限、执行、Trace、Evaluation 和 Lesson。
- `knowledge_base/`：可安装知识包、领域路由、检索、复习和机器知识。
- `Inspiration-Research/`：研究发现与项目雷达兼容目录。
- `shared/`：配置、鉴权、SQLite、备份、证据、摄入和 Sleep Loop。
- `shared-contracts/`：Schema、适配器和项目注册。
- `config/`：运行策略与运行时配置。
- `tests/`、`knowledge_base/tests/`、`integration-tests/`：三层门禁。
- `docs/`：当前事实、架构、路线图与历史审计。

## 证据入口

- 文件级证据：`FILE_INVENTORY.csv`
- API 证据：`API_ROUTE_MAP.json`
- 依赖证据：`DEPENDENCY_REPORT.md`
- 测试证据：`TEST_BASELINE.md`
- 风险和迁移决策：`SECURITY_BASELINE.md`、`ARCHITECTURE_GAPS.md`、
  `REUSE_DECISIONS.md`
