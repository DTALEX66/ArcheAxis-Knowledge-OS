# 编程语言与配置最终建议

## 1. 最终语言组合

### Python：核心第一语言

负责：

- 文档与媒体摄入；
- OCR；
- Research；
- Evidence；
- Knowledge；
- Learning；
- AI Provider；
- Evaluation；
- FastAPI；
- 数据处理。

结论：保留，不重写为 Go/Java/Rust。

### Rust：桌面系统边界

负责：

- Tauri；
- Python 进程监督；
- Windows Job Object；
- 端口；
- 启动/关闭；
- WebView 导航；
- NSIS。

结论：保留，不承载知识业务。

### JavaScript → TypeScript + React

当前静态 HTML/CSS/JS：

- A0/A1 可继续使用；
- 长期重型桌面不够。

建议：

- A1 保持静态栈；
- A2 拆分模块；
- A3 单独迁移 TypeScript + React；
- 不与换皮同时迁移。

### SQLite

继续作为单用户本地核心数据库。

不急于迁 PostgreSQL。

## 2. Python 版本

建议：

- 正式桌面 Runtime：Python 3.12 x64；
- 最低版本后续调整：`>=3.11`；
- CI：3.11 / 3.12 / 3.13；
- 3.14 先作为实验兼容；
- 逐步移除 3.10。

升级必须单独 PR，不与 UI 改造混合。

## 3. 依赖管理

统一以：

- `pyproject.toml`
- `uv.lock`

为事实源。

普通测试和 Lint 也应逐步使用 frozen lock。

建议分组：

- core；
- documents；
- ocr；
- media；
- providers；
- research；
- observability；
- evaluation；
- dev；
- browser；
- build。

重型可选依赖不可拖垮核心启动。

## 4. 数据库建议

保留：

- SQLite；
- WAL；
- Migration Operator；
- Backup；
- Integrity Check。

建议配置：

```yaml
database:
  journal_mode: WAL
  synchronous: NORMAL
  foreign_keys: true
  busy_timeout_ms: 30000
  wal_autocheckpoint_pages: 1000
  integrity_check_on_startup: true
```

原始 PDF、Office、图片、音视频放文件系统，不放 SQLite Blob。

建议内容寻址：

```text
data/assets/sha256/<prefix>/<hash>
```

## 5. 搜索建议

当前 `vector_dim: 384` 不应永久全局写死。

改为版本化 Embedding Profile：

- provider；
- model_id；
- dimension；
- normalization；
- chunking_version；
- schema_version；
- source_snapshot。

中文搜索建议：

- 预分词 + FTS；
- Trigram 模糊索引；
- sqlite-vec；
- Keyword + Vector + Rerank。

不同场景使用不同 top_k。

## 6. Pipeline 建议

当前 `max_content_chars=10000` 应改为预览限制，不是摄入上限。

拆分：

- preview limit；
- file byte limit；
- chunking；
- processing；
- promotion。

核心规则：

```text
自动处理 Candidate：允许
自动晋升正式知识：禁止
```

## 7. 配置体系

建议：

```text
config/
  defaults.yaml
  profiles/
    desktop.yaml
    development.yaml
    test.yaml
    production.yaml
  policies/
    ingestion.yaml
    search.yaml
    permissions.yaml
    models.yaml
```

加载顺序：

```text
defaults
→ profile
→ local runtime config
→ environment
→ CLI
```

敏感信息禁止进入 Git。

## 8. 本地模型

3060 Ti 适合：

- Embedding；
- Rerank；
- OCR；
- 分类；
- 7B/9B 量化模型；
- 标签、结构化、简单摘要。

复杂推理和超长上下文交给 API。

接入方式：

```text
AXOS Core
→ Provider Adapter
→ OpenAI-compatible Local Endpoint
→ Local Model Runtime
```

权重不进入 Git/Wheel/NSIS。
