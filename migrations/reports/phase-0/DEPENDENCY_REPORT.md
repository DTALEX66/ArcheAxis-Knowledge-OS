# Phase 0 依赖基线

> Git 基线：`82b9df3f719d9212111536b454654f2243150f16`。声明来源：`pyproject.toml`。

## Python 与打包

- Python：`>=3.10`
- 构建后端：`setuptools.build_meta`
- CLI：`cognitive-os = app.cli:main`
- 打包范围：`app*`、`shared*`、`knowledge_base*`、`config*`
- 当前 CI：Python 3.10、3.11、3.12。

## 运行依赖

| 声明 | 作用域 |
|---|---|
| `fastapi>=0.133,<0.134` | runtime |
| `uvicorn[standard]>=0.22` | runtime |
| `pydantic>=2.0` | runtime |
| `numpy>=1.24` | runtime |
| `requests>=2.28` | runtime |
| `pyyaml>=6.0` | runtime |
| `beautifulsoup4>=4.11` | runtime |
| `apscheduler>=3.10` | runtime |
| `sqlite-vec>=0.1.6` | runtime |
| `loguru>=0.7` | runtime |
| `structlog>=24.0` | runtime |
| `markitdown>=0.1` | runtime |
| `trafilatura>=1.6` | runtime |
| `networkx>=3.0` | runtime |
| `litellm==1.91.0` | runtime |

## 可选依赖

| 声明 | 组 |
|---|---|
| `pytest>=7.0` | `dev` |
| `ruff>=0.5` | `dev` |
| `mypy>=1.8` | `dev` |
| `cognitive-loop-os[dev,ingestion]` | `full` |
| `crawl4ai>=0.1` | `ingestion` |
| `langfuse>=4.0` | `ingestion` |
| `promptfoo>=0.1` | `ingestion` |

## 基线判断

1. `litellm` 被精确固定，其他大多数依赖使用下限或兼容范围。
2. `Inspiration-Research/` 不在 setuptools 包发现范围内，仍依赖兼容入口。
3. `requirements.txt` 与 `pyproject.toml` 并存，后续应建立一致性检查。
4. Mypy 已配置但不在正式 CI 门禁中。
5. Phase 1 不升级依赖；只建立 Facade、依赖方向守卫和合同测试。
