# Cognitive-Loop-OS

Cognitive-Loop-OS 是 Cognitive-Knowledge-System 的统一仓库，聚合了核心认知运行时、B/C 线工程蓝图、数据合同以及开源项目吸收矩阵。

## 仓库结构

```
Cognitive-Loop-OS/
  app/                    # Cognitive-OS 运行时 v0.2 (FastAPI)
  config/                 # 运行时配置 (settings / models / tools / agent_profile)
  shared-contracts/       # C线：数据合同 (A↔B 桥接)
    schemas/              # 10 个 JSON Schema (Draft 2020-12)
    fixtures/             # 10 个脱敏模拟数据
    validators/           # 2 个 Python 验证脚本
    registries/           # 开源项目吸收注册表 (JSON + CSV, 50 条目)
  docs/                   # 设计与分析文档
    bc-lines/             # B+C 线全流程设计 (14 篇)
    three-project-analysis/  # IR+KB+OS 三项目聚合分析 (9 篇)
  codex-taskpacks/        # 3 个 CODEX 任务包 (20 个开发任务)
  integration-tests/      # B+C 联调测试清单
  workspace/              # 进口知识包与设计记录
```

## 三线架构

| 线 | 定位 | 当前状态 |
|----|------|----------|
| **A线** Obsidian-Assistance | 用户前端 / 笔记渲染 | 待对接 |
| **B线** IR + KB + Cognitive-OS | 核心认知闭环 | OS 可运行，IR/KB 待建仓 |
| **C线** shared-contracts | 合同 / Fixtures / 联调 | 10 schema + 10 fixture 已就绪 |

## 当前能力

Cognitive-OS 运行时 (v0.2)：

| 端点 | 用途 |
|------|------|
| `GET /health` | 健康检查 |
| `POST /ingest` | 摄入文本对象 |
| `POST /ingest/file` | 摄入仓库内 Markdown/文本文件 |
| `POST /ingest/directory` | 摄入仓库内目录 |
| `POST /route` | 返回注意力路由 (TASK/IR/KB/DROP/REVIEW) |
| `POST /run` | 执行最小认知循环 |
| `POST /memory/search` | 搜索记忆记录 |
| `GET /memory/lessons` | 列出机器课程 |
| `GET /traces` | 列出执行追踪 |
| `GET /tools` | 列出已注册工具及风险等级 |

## 运行

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

交互式文档：`http://127.0.0.1:8000/docs`

## 目标认知循环

```
外部输入 → 注意力路由 → [DROP | REVIEW | KB | IR | TASK]
                              ↓ (TASK)
           上下文检索 → 任务编译 → 权限检查 → 执行 → 追踪 → 评估 → 机器课程 → 回流
```

## 安全边界

- 文件摄入仅限仓库内 (`.md`, `.markdown`, `.txt`)
- 默认执行模式：dry_run
- `code_exec`：blocked | `shell_exec`：禁止
- 所有输入经过 raw → quarantined → approved 状态机
- 外部内容不可覆盖系统策略 (Prompt Injection 防护)

## 下一步开发

按 B+C 线蓝图推进：

1. **Cognitive-OS SQLite 迁移** — JSONL → 9 表结构化存储
2. **RoutePolicy 可配置化** — 关键词/风险词从代码拆出
3. **PermissionDecision 体系** — 执行前权限检查
4. **创建 IR + KB 仓库** — 完成三项目骨架
5. **B 线全链路联调** — ResearchNote → … → MachineLesson
