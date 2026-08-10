# 云端仓库最新重审

## 当前可见状态

- 仓库：`DTALEX66/Cognitive-Loop-OS`
- 默认分支：`main`
- 当前最后可见 SHA：`a92e6730a267f4268ff64d92be5d2fc17bce59e5`
- 提交：`feat(absorption): complete evidence baseline and project boundary repair (#13)`

该提交晚于此前前端修改包使用的：

`2cdf11e2b85154c15cfd621c04dae8f6c90d693b`

因此此前两个前端任务包不能直接假定基线不变，执行前必须重放审计。

## 本次更新的主要意义

### 1. 项目边界更严格

新增规则强调：

- 项目输出必须留在项目本地忽略目录；
- Hermes、Codex、CC Switch、Workflow-assistance 等仍归其各自工作流目录所有；
- TEMP、用户目录和其他项目中的文件不能仅凭名称判定归属；
- 无法确认归属的文件应保留并标记，不得删除或搬运。

### 2. Chromium Delivery 状态更新

本地真实：

```text
HTTP
→ SQLite
→ Chromium Upload
→ Dispatch
→ Receipt
→ Reload Readback
```

已通过本地验证。

仍缺：

- exact-SHA CI 证明；
- Tauri WebView 点击级证据；
- 失败→Retry→Replay 完整矩阵；
- 公开发布资产。

### 3. 吸收矩阵深化

新增 `docs/ABSORPTION_EXECUTION_MATRIX.md`。

当前 Registry/Ledger：

- 总项目：101；
- implemented：8；
- adapter_contract_pending：27；
- deferred_review：38；
- reference_only：28。

这些是候选吸收状态，不代表 101 个项目已集成。

### 4. 多格式摄入 Adapter 化

文档摄入开始转向统一 AdapterResult / Adapter Contract：

- MarkItDown；
- Marker；
- Docling；
- Trafilatura；
- OCR；
- Media；
- Fallback / Unavailable Evidence。

方向是正确的，符合新项目定位中的“重型资料摄入层”。

## 当前重新判断

### 继续保持

- Python / FastAPI；
- SQLite；
- Tauri；
- Candidate / Approved；
- Research / Knowledge / Learning；
- Job / Outbox / Receipt；
- Adapter Foundry；
- Product Truth。

### 需要优先修正

1. README、描述、关键词和界面仍偏“认知系统”；
2. 原始资产 SourceAsset Provenance；
3. Success / Correctness / Lesson 语义；
4. 配置 Profile；
5. 搜索和 Embedding Profile；
6. 个人学习主线在前端中的优先级；
7. 旧前端任务包需要基于新 SHA 重放。
