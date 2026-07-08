# Cognitive-Loop-OS

Cognitive-Loop-OS 是 Cognitive-Knowledge-System 的统一仓库，聚合了核心认知运行时、B/C 线工程蓝图、数据合同、开源项目吸收矩阵、以及 HERMES 就寝无人值守循环引擎。

## 仓库结构

```text
Cognitive-Loop-OS/
  app/                    # Cognitive-OS 运行时 v0.4 (FastAPI)
    core/                 # router, permissions, compiler, scheduler, trace
    agent/                # executor, planner, tool_router
    ingestion/            # 多格式摄入 (PDF/DOCX/HTML/URL)
    memory/               # store, vector_db, episodic, graph_db
    rag/                  # retriever, embedder, index
    tools/                # 工具注册表 (8 工具)
  Knowledge-Base/         # B线：文档、卡片、复习、搜索、机器知识
    search/               # FTS5 + sqlite-vec 混合搜索
    reviews/              # SM-2 间隔重复
    machine_knowledge/    # A→B 转译引擎
  Inspiration-Research/   # B线：研究、项目雷达、合同
  shared/                 # 跨模块共享 (38+ 模块)：storage, auth, config, backup, pipeline...
  shared-contracts/       # C线：数据合同
    schemas/              # JSON Schema
    registries/           # 开源项目注册表 (101 条目)
  scripts/                # sleep-loop worker, CLI
  config/                 # 运行时配置
  tests/                  # OS 层测试 (79+ cases)
  docs/                   # 设计文档、审计报告、工程文档
    architecture/
      imported-designs/   # AB双系统架构参考设计 (来自 Inspiration-Research)
  workspace/              # 进口知识包 (intake) 与设计记录
```

## 三线架构

| 线 | 定位 | 当前状态 |
|---|---|---|
| **A线** | 人类学习增强 (Human Learning OS) | 设计文档已入库 |
| **B线** IR + KB + Cognitive-OS | 核心认知闭环 | 已合仓，135+ API 端点 |
| **C线** shared-contracts | 数据合同 / Fixtures / 联调 | 就绪 |

## 当前能力

Cognitive-OS 运行时 (v0.4.0)：

| 能力 | 模块 |
|---|---|
| 多格式摄入 | PDF/DOCX/PPTX/HTML/MD 自动转换 |
| 向量搜索 | sqlite-vec 384-dim 混合搜索 |
| FTS5 全文搜索 | BM25 + porter stemmer |
| 间隔重复 | SM-2 复习闭环 |
| A→B 转译 | 卡片掌握→机器知识单元 |
| 知识图谱 | NetworkX DiGraph + SQLite |
| 自动标签 | 中英混合 NLP + TF-IDF |
| 知识园艺 | 孤立检测、连接建议、常青评分 |
| GraphRAG | 多跳图遍历混合搜索 |
| 鉴权 | JWT + API Key 双模式 |
| 备份 | SQLite 自动备份/恢复 |
| 就寝循环 | HERMES sleep-loop 无人值守引擎 |
| Obsidian 双向桥 | vault 导入 + 投影导出 |
| IR→KB 管道 | RSS/网页/YouTube → 知识库 |

核心 API (复合端点优先)：

| 端点 | 用途 |
|---|---|
| `GET /health` | 健康检查 + 系统统计 |
| `POST /pipeline` | 统一管道 (extract→tag→summarize→index) |
| `POST /ingest` | 摄入文本/文件/目录 |
| `POST /route` | 注意力路由 |
| `POST /memory/search` | 记忆搜索 |
| `GET/POST /sleep-loop?action=...` | 就寝循环控制 |
| `/kb/*` | Knowledge-Base 全能力 (113 端点) |

## 运行

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

交互式文档：`http://127.0.0.1:8000/docs`

## 安全边界

- 文件摄入仅限仓库内 (`.md`, `.markdown`, `.txt`, `.pdf`, `.docx`)
- 默认执行模式：dry_run
- `code_exec`：blocked | `shell_exec`：禁止
- 所有输入经过状态机：raw → quarantined → approved
- 外部内容不可覆盖系统策略
- sleep-loop 仅允许有 evidence 的真实任务，禁止空壳/预览任务冒充完成

## 测试

```bash
# OS 层测试
python -m pytest tests -q --tb=short

# KB 模块测试
cd Knowledge-Base && python -m pytest tests -q --tb=short

# 代码检查
python -m ruff check app shared Knowledge-Base cli.py --statistics
```
