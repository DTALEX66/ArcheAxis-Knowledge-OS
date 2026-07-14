# Cognitive-Loop-OS 全面审计报告

审计日期：2026-07-07
审计角色：Backend Architect / Code Reviewer
审计范围：`app/`、`shared/`、`Knowledge-Base/`、`Inspiration-Research/`、`tests/`、配置、CI、Docker 与主要文档。`workspace/imports/` 视为吸收参考库，不计入主运行时代码，但涉及风险会单独标注。

---

## 0. 总结结论

项目已经具备较完整的知识系统能力骨架：FastAPI 统一入口、KB 子应用、SQLite/FTS5/sqlite-vec、Pipeline、备份、鉴权、CLI、Docker/CI 雏形都已存在；分目录测试共 **106 passed**。但“可上线后端工程”还没有达标，主要原因是：

1. **P0：核心 `/run` 认知闭环当前不可用**：运行时报 `NameError: retrieve is not defined`。
2. **P0/P1：安全边界存在假阳性完成感**：鉴权中间件已启用，但配置里 `auth.enabled: false`；默认硬编码 dev key 仍可用；CORS 为 `*`；`/export?tables=` 可把用户输入表名传进动态 SQL。
3. **P1：API 并未真正减少**：递归统计仍有 **135 HTTP routes**，其中 `/kb` 下 **113 routes**；复合接口是新增覆盖层，旧接口基本仍保留。
4. **P1：质量门禁不绿**：目标目录测试通过，但 `python -m pytest -q` 全仓收集失败；`ruff` 有 **97 errors**，其中包含 `F821 undefined-name retrieve` 和重复路由函数。
5. **P1：版本与文档漂移**：README 写 v0.2，`pyproject.toml` 为 v0.3.0，运行时/配置/Compose 写 v0.4.0。

综合判断：

```text
能力覆盖：高         8 环节能力基本具备
工程可信度：中       有测试，但全仓门禁与 lint 不绿
生产安全：中低       鉴权/CORS/动态表名/默认 key 需收口
API 可维护性：中低   仍是 100+ KB 路由，需版本化/网关化/废弃旧接口
上线状态：不可直接生产上线；适合继续本地迭代/内网试运行
```

---

## 1. 审计基线

### 1.1 Git 状态

命令：

```bash
git status --short && git rev-parse --abbrev-ref HEAD && git log --oneline -5
```

结果：

```text
branch: main
最近提交：
d48de47 feat(backend-final): 参数校验+限流+CLI — 后端工程完整交付
f478cb8 feat(backend): 鉴权+配置+备份+架构图 — 后端工程基线完整
9e432e5 feat(consolidate): API合并 + 批量/导出/定时
4fc2077 feat(pipeline): 统一管道 — 1个/pipeline端点替代15+分散调用
00978e6 feat(absorb-complete): Obsidian-Assistance 全量吸收完成
```

审计时工作区原本干净；本报告为新增文档。

### 1.2 规模统计

排除 `.git/data/workspace/__pycache__/.pytest_cache/.ruff_cache/venv` 后：

```text
active_files: 139
python_files: 134
markdown_files: 2
active_python_loc_nonblank_noncomment: 10,712
```

### 1.3 路由统计

递归统计 FastAPI 主应用 + mounted KB 子应用：

```text
recursive_http_routes: 135
/kb routes: 113
重复路由: POST /kb/evidence × 2
```

按前缀：

```text
/kb        113
/convert     3
/ingest      3
/backup      2
/memory      2
/health      1
/version     1
/tools       1
/route       1
/run         1
/auth        1
/architecture 1
```

结论：API“入口体验”已新增 `/kb/pipeline`、`/kb/garden` 等复合端点，但旧端点没有移除/隐藏/废弃，接口面仍然很大。

---

## 2. 质量门禁结果

### 2.1 测试

分目录目标测试通过：

```bash
python -m pytest tests -q --tb=short
# 78 passed in 2.76s

cd Knowledge-Base && python -m pytest tests -q --tb=short
# 28 passed in 1.07s
```

合计：**106 passed**。

但全仓测试失败：

```bash
python -m pytest -q --tb=short
```

失败摘要：

```text
ERROR Knowledge-Base/tests/test_cards.py
ModuleNotFoundError: No module named 'tests.test_cards'
ERROR Knowledge-Base/tests/test_context_pack.py
ERROR Knowledge-Base/tests/test_taskpack.py
ERROR Knowledge-Base/tests/test_vector_search.py
4 errors during collection
```

判断：CI 里分两段运行可通过，但本地/开发者直觉命令 `pytest` 会失败。建议加入 root `pytest.ini` 或改造包名，避免 `tests` 包冲突。

### 2.2 Ruff / 静态质量

命令：

```bash
python -m ruff check app shared Knowledge-Base cli.py --statistics
```

结果：**97 errors**。

统计：

```text
38 I001   unsorted-imports
20 F401   unused-import
17 E402   module-import-not-at-top-of-file
 8 SIM105 suppressible-exception
 3 F541   f-string-missing-placeholders
 3 F841   unused-variable
 2 B007   unused-loop-control-variable
 1 E401   multiple-imports-on-one-line
 1 E741   ambiguous-variable-name
 1 F811   redefined-while-unused
 1 F821   undefined-name
 1 SIM102 collapsible-if
 1 SIM103 needless-bool
```

关键阻断：

- `app/main.py:233 F821 Undefined name retrieve`
- `Knowledge-Base/api.py:1192 F811 evidence_add redefined`
- `Knowledge-Base/api.py` 多处未使用导入/未排序导入

### 2.3 API Smoke Test

使用 `fastapi.testclient.TestClient` 实测：

```text
GET  /health          200
GET  /version         200
GET  /tools           401 未授权，符合预期
GET  /tools + key     200
GET  /kb              401  ← 与文档“Dashboard http://localhost:8000/kb”不一致
GET  /kb/             200
GET  /kb/health       401
POST /kb/pipeline     200
POST /run + key       EXC NameError: retrieve is not defined
```

结论：

- `/kb/` 可访问，但 `/kb` 被主鉴权中间件拦截，用户按文档访问会撞 401。
- `/run` 是核心认知闭环入口，但目前不可用。
- `/kb/pipeline` 可用，是当前最稳的统一入口。

### 2.4 依赖健康

```bash
python -m pip check
# No broken requirements found.
```

但 `requirements.txt` 与 `pyproject.toml` 不一致：

`pyproject.toml` 有但 `requirements.txt` 缺失：

```text
litellm, loguru, markitdown, networkx, sqlite-vec, structlog, trafilatura
```

Docker/CI 目前安装的是 `requirements.txt`，因此容器或 CI 环境可能缺运行时依赖。

### 2.5 安全扫描工具

```bash
python -m bandit -q -r app shared Knowledge-Base -x Knowledge-Base/tests,tests
# No module named bandit
```

Bandit 未安装，安全审计本轮使用正则/源码审阅完成；建议加入 dev dependency 和 CI gate。

---

## 3. 安全与生产红线扫描

### 3.1 已确认的安全正项

主运行时代码中未发现：

```text
eval(...)
exec(...)
os.system(...)
subprocess(..., shell=True)
pickle.load / pickle.loads
```

注：`workspace/imports/` 参考代码中存在 `eval/exec/shell=True`，但不属于主运行时路径。仍建议在吸收参考代码时加扫描，避免未来误迁入。

### 3.2 高风险/需整改项

#### P0/P1 — 动态表名 SQL 风险

`shared/storage.py` 使用动态表名：

```python
c.execute(f"PRAGMA table_info({table})")
c.execute(f"INSERT OR REPLACE INTO {table} ...")
c.execute(f"SELECT * FROM {table} ORDER BY {order} LIMIT ?")
```

内部调用可接受，但 `shared/bulk_ops.py` 暴露：

```python
def export_kb(format="json", tables: list[str] | None = None)
# /kb/export?tables=... 可传入 tables
rows = select_all(table, limit=500)
```

如果 `tables` 未白名单过滤，用户输入会进入动态 SQL。建议：

- 增加 `ALLOWED_TABLES` 白名单。
- `select_all(table, order=...)` 对 table/order 做枚举校验。
- `/kb/export` 只允许预定义表集合或导出 profile 名。

#### P1 — 默认开发 Key 硬编码

`shared/auth.py`：

```python
"dev-key-change-me": {"role": "admin", "name": "default-dev-key"}
```

建议：

- 仅 `COGNITIVE_ENV=development` 时启用。
- production 无 `COGNITIVE_API_KEY` 时启动失败。
- 文档明确 `.env.example`。

#### P1 — CORS 全开放

`app/main.py` 和 `Knowledge-Base/api.py` 均为：

```python
allow_origins=["*"]
allow_methods=["*"]
allow_headers=["*"]
```

建议从 `config/settings.yaml` 读取，并生产环境拒绝 `*`。

#### P1 — 鉴权配置与实际行为不一致

`config/settings.yaml`：

```yaml
auth:
  enabled: false
```

但 `app/main.py` 中间件无条件执行 `requires_auth()`。实际行为是大部分接口需要鉴权。建议：

- 将 `auth.enabled` 真正接入中间件。
- 或改配置为 `enabled: true`，避免误导。
- 区分 dev/local/production profile。

#### P2 — RateLimiter 未接入

`shared/rate_limit.py` 已有 `default_limiter`，但全项目仅定义未使用。建议接入 HTTP middleware，对 API key/IP 做滑动窗口限制。

#### P2 — broad except/pass 较多

主运行时代码至少 16 处 `except Exception: pass`，典型位置：

```text
app/memory/episodic.py
app/memory/store.py
shared/pipeline.py
shared/obsidian_importer.py
shared/auth.py
shared/config.py
```

建议：非关键路径至少 `logger.warning`，关键路径返回结构化错误。

---

## 4. 架构与全流程覆盖审阅

### 4.1 当前架构

实际是“统一主应用 + KB 子应用”的模块化单体：

```text
Client / Agent / Cron
        ↓
FastAPI app.main  :8000
        ├── Core OS endpoints: /ingest /route /run /memory /tools /backup
        └── Mounted Knowledge-Base: /kb/*
                ├── search/cards/reviews/mku/graph/canvas/obsidian
                ├── IR: feed/web/youtube/facts/cross-reference
                ├── pipeline/composite endpoints
                └── export/bulk/cron/project
        ↓
SQLite + FTS5 + sqlite-vec + file-backed logs/backups
```

### 4.2 八环节覆盖判断

| 环节 | 当前能力 | 状态 |
|---|---|---|---|
| 发现 Discovery | RSS/Web/Search/Source discovery | ✅ 已有 |
| 提取 Extraction | text/url/pdf/video/youtube 可选提取 | ✅/⚠️ 依赖不齐时降级 |
| 识别 Recognition | tag/keyword/fact/atomicity | ✅ 已有 |
| 结构化 Structuring | documents/cards/MKU/taskpack/contextpack | ✅ 已有 |
| 分析 Analysis | cross-reference/diversity/evidence/graph | ✅ 已有 |
| 学习 Learning | SM-2/review/streak/mission/retro | ✅ 已有 |
| 转化 Translation | A→B card→Mku/project/export | ✅ 已有 |
| 可视化 Visualization | dashboard/canvas/mermaid/bases | ✅ 已有 |

结论：**能力覆盖层面已经完整**；当前问题不是“缺能力”，而是“能力入口、质量门禁、安全边界和文档可信度未收口”。

### 4.3 API 过多问题

当前新增复合端点包括：

```text
/kb/pipeline
/kb/garden
/kb/analytics
/kb/mermaid
/kb/evidence
/kb/retro
/kb/projects
/kb/sources
/kb/diversity
/kb/bulk/import
/kb/export
/kb/cron/discover
```

但旧接口仍然公开，因此 API 面没有真正收敛。建议进入 V1 网关策略：

```text
保留公开稳定入口：/api/v1/pipeline, /api/v1/search, /api/v1/kb, /api/v1/admin/*
内部/旧接口：标记 deprecated，移动到 /internal/* 或默认不出现在 schema
OpenAPI tags：按 Domain 分组，而不是一堆平铺端点
```

### 4.4 数据闭环

核心链路理论上是：

```text
输入 → route → retrieve → compile_task → permission → execute → trace → evaluate → lesson → memory
```

但实际 `/run` 卡在 `retrieve` 未导入，闭环不可用。当前可用闭环主要是 `/kb/pipeline` 的知识入库链路。

---

## 5. 文档/版本漂移

发现明显漂移：

| 文件/接口 | 版本/描述 |
|---|---|
| `README.md` | Cognitive-OS 运行时 v0.2 |
| `pyproject.toml` | version = 0.3.0 |
| `app/main.py` | version = 0.4.0 |
| `config/settings.yaml` | version = 0.4.0 |
| `docker-compose.yml` | v0.4.0 |
| `/health` | version 0.4.0，endpoints core=11 kb=102 total=113 |
| `cli.py stats` | 声称 `Total API endpoints: ~40`，但实际递归 HTTP routes=135 |

建议：

- 单一版本源：`pyproject.toml` 或 `shared/version.py`。
- `/health`、CLI、README、Docker Compose 均从版本源读取。
- README 更新真实启动命令、真实 API、鉴权方式与 `/kb/` trailing slash 行为。

---

## 6. 优先级整改清单

### P0 — 立即修复

1. **修复 `/run` NameError**
   - 在 `app/main.py` 正确导入 `from app.rag.retriever import retrieve`。
   - 添加 TestClient 测试覆盖 `/run` 的 TASK/KB/REVIEW/DROP 路由。

2. **锁定 `/kb/export` 表名白名单**
   - `ALLOWED_EXPORT_TABLES = {...}`。
   - 非法表名返回 400。
   - `shared.storage` 层增加 table/order whitelist 或专用 repository 函数。

3. **处理 `/kb` 访问 401/重定向问题**
   - `requires_auth('/kb')` 放行或显式 redirect 到 `/kb/`。
   - 文档统一写 `/kb/` 或实现无斜杠兼容。

### P1 — 质量门禁修复

4. **让全仓 `python -m pytest -q` 通过**
   - 添加 root `pytest.ini`，限制 `testpaths = tests Knowledge-Base/tests` 并处理 hyphen 子包导入。
   - 或移除/避免 `Knowledge-Base/tests/__init__.py` 引起的 `tests.*` 收集冲突。

5. **Ruff 清零**
   - 先 `ruff check --fix` 解决 62 个自动修复项。
   - 手动处理 `F821`、`F811`、`E402`、`SIM105`。
   - CI 保持 `ruff check app/ shared/ Knowledge-Base/ cli.py`。

6. **统一版本与依赖**
   - `pyproject.toml` 改为 0.4.0 或以它为准反向更新运行时。
   - `requirements.txt` 同步 `pyproject.dependencies`。
   - Docker/CI 统一用 `pip install -e .[dev]` 或锁文件。

### P1/P2 — 生产安全

7. **移除生产默认 dev key**
   - production 下无显式 key 则启动失败。
   - `config/api_keys.example.json` 替代内置 key。

8. **CORS 配置化**
   - dev 可 `*`，production 必须白名单。

9. **接入 rate limiter**
   - Middleware 级别按 IP/API key 限流。
   - `/auth/token`、`/kb/pipeline`、`/kb/export` 使用更严格限制。

10. **加入 Bandit 或 Ruff security rules**
    - dev dependency 加 `bandit`。
    - CI 增加 `bandit -r app shared Knowledge-Base -x tests,Knowledge-Base/tests`。

### P2 — API 收敛

11. **真正的 API v1 网关化**
    - `/api/v1/pipeline`：唯一主流程入口。
    - `/api/v1/search`：统一检索入口。
    - `/api/v1/admin/*`：备份、导出、cron、统计。
    - 旧 KB 小接口标记 deprecated 或 internal。

12. **统一响应体**
    - `shared/schemas.py` 已存在，但未被主路由系统性使用。
    - 所有公开路由返回 `{status, data, error, meta}` 格式。

### P3 — 长期维护

13. **模块边界整理**
    - `Knowledge-Base/api.py` 已达 1327 行，应按 router 拆分：`routers/search.py`, `routers/review.py`, `routers/pipeline.py`, `routers/admin.py`。

14. **观测性完善**
    - 结构化 request id。
    - 错误计数、慢查询日志、pipeline stage metrics。

15. **备份恢复测试**
    - 当前有 backup/restore 代码，但缺自动化测试。

---

## 7. 建议下一阶段执行顺序

推荐按以下顺序进入“工程收口循环”：

```text
Phase 1: P0 修复
  1. /run retrieve import + smoke test
  2. /kb/export table whitelist
  3. /kb trailing slash/auth allowlist 修复

Phase 2: 门禁清零
  4. pytest root 收集修复
  5. ruff --fix + 手动修复 97→0
  6. CI 统一执行同一套命令

Phase 3: 生产安全
  7. dev key production 禁用
  8. CORS config profile
  9. rate limiter middleware
  10. bandit gate

Phase 4: API 收敛
  11. /api/v1 网关公开层
  12. legacy/internal 标注与 OpenAPI 隐藏
  13. README/CLI/health 路由数量同步
```

最小验收命令应固定为：

```bash
python -m pytest -q
python -m ruff check app shared Knowledge-Base cli.py
python -m pip check
python - <<'PY'
from fastapi.testclient import TestClient
import app.main as m
c = TestClient(m.app)
assert c.get('/health').status_code == 200
assert c.get('/kb/').status_code == 200
assert c.post('/kb/pipeline', headers={'X-API-Key':'dev-key-change-me'}, json={'source':'text','input':'smoke','auto_ingest':False}).status_code == 200
assert c.post('/run', headers={'X-API-Key':'dev-key-change-me'}, json={'content':'smoke','source':'smoke'}).status_code < 500
PY
```

---

## 8. 最终判定

```text
是否全流程覆盖：是，能力层已覆盖。
是否工程可上线：否，P0/P1 需要先修。
是否适合继续增强能力：不建议先增强；应先收口门禁、安全、API 面。
是否建议继续吸收新项目：暂停。先做工程固化，否则能力越多 API/风险越难管理。
```

一句话结论：**现在不是缺模块，而是缺“可信运行基线”。下一步应从 P0 修复和质量门禁清零开始。**
