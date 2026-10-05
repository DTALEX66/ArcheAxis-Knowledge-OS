# AAOS-01 Q06 PDF 切片：六项判据全部成立（2026-10-05）

**在同一份权威候选上端到端跑通，并由 Core 自己的记录给出全部判据。**

## 判据与证据

| # | 判据 | 证据 |
| --- | --- | --- |
| 1 | **原件正确** | `POST /api/v1/imports` → `sha256 = 0f0ffc50c79d9d977efb925351ca1d64a063184e4bdd71507b9ac44992f7adcf`，与金样本一致 |
| 2 | **succeeded** | `GET /api/v1/jobs/pdf-c1759c8f` → `state: succeeded` · `attempt: 1` · `error: null` |
| 3 | **正文与样本一致** | `GET …/outputs/text` → `"Golden Journey Evidence\nOriginal SHA and anchored conversion\nCriterion\nVerified\nPage Anchor\nPASS\n"`；`byte_length: 97`；`authority_effect: candidate_or_measurement_only` |
| 4 | **引擎身份** | `GET …/quality` → **`engine: "pymupdf-native-pdf"` · `engine_version: "pymupdf"`** |
| 5 | **定位与损失** | 同上 → **`coverage: 1.0` · `covered: 6` / `total: 6` · `loss_count: 1` · `pages: 1`** |
| 6 | **重启读回** | **全新 Core 进程**（`SECOND_BOOT_READY`）后 `state` 仍 `succeeded`，`outputs/text` 逐字相同 |

## 关键定位经验（避免重犯）

- **引擎身份在 `jobs/:id/quality`，不在 `capabilities`**。
  `capabilities` 报告的是 **worker 握手**（`handshake_ready` · `worker_identity: python-worker-pdf-ndjson` · `task_executed: false`），
  **它自己写明「a job has to run to verify engines and output」** —— 作业跑完后，**引擎信息出现在 quality 记录里**。
  我曾两次误判为「Core 不报告引擎身份」，**是在错误的端点里找**。
- **输出的种类只有 `text`**（`pages`/`anchors`/`location`/`loss`/`structure`/`receipt` 均 404）；
  **定位与覆盖在 `jobs/:id/quality`**；`sources/:id/members` 给出容器成员（此例 0）。
- **`capabilities` 只有在声明 `text_worker` 时才挂载**（`main.rs` 的挂载条件），否则 18 条 projections 而非 36 条。

## 复现要求

1. 资源表须含 `core`/`runtime`/`workers`/`shared` **与候选四个根层文件**；
2. 启动文档的 `text_worker` 路径**不得带 `\\?\` 前缀**（已修）；
3. 用**全新数据根**（Core 打不开旧 Python 库，见迁移缺口记录）。
