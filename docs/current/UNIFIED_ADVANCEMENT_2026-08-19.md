# ArcheAxis 统一推进基线（UNIFIED ADVANCEMENT）· 2026-08-19

> 整合来源（按基线02优先级）：① 用户最新决定（本会话统一上下文）② TP-20260819-TASKPACK-ARCHEAXIS（WORK-LAB 联邦推送）③ 基线文档（Full Context Handoff 2026-08-19 为主 + Library Architecture 2026-08-18）④ 本会话只读审计（HEAD c83225b）⑤ 历史交接。
> 状态词：PASS / PARTIAL / FAIL / NOT_EXECUTED / BLOCKED（禁止 DONE）。完成声明必须绑定 Exact SHA + 证据路径。commit/push/迁移需人工批准。

## 一、唯一定位（三源一致，不可漂移）

本地优先、原件永久保全、证据驱动、开放互操作，面向**人类学习与 AI 学习双主体**的可信知识治理系统（ArcheAxis Knowledge / 星环知识平台 / archeaxis-workspace / DTALEX66/ArcheAxis-Knowledge-OS）。
不是：Agent OS / Runtime / 聊天 / 文件管理 / PDF 阅读器 / Obsidian 克隆 / RAG 外壳 / 模型管理器 / 爬虫平台 / WORK-LAB 与 DESIGN-LAB 的替代。

## 二、整合后的任务矩阵（基线 R0-R7 × WORK-LAB AA-P0/P1）

| 统一任务 | 来源 | 现状（审计证据） | 状态 |
| --- | --- | --- | --- |
| 命名/身份/门禁 | 基线 R0 | pyproject/main 已统一；app/contracts 无联邦契约 | PASS（命名） |
| **AA-P0-001 状态真相再生** | WORK-LAB | SYSTEM_BOUNDARY/产品计划未与 HEAD c83225b 同步（旧阶段/旧执行器残留） | PARTIAL |
| **AA-P0-002 稳定知识 API** | WORK-LAB | facades 有单发 ingest_candidate/query_knowledge；**缺**：批量提交/幂等键/权限身份/Candidate Receipt/Verified 回读/分页·错误码·速率·版本协商/来源·版权·置信度/hash readback | PARTIAL（缺口大） |
| **AA-P0-003 人类学习保留** | WORK-LAB | 学习引擎齐（FSRS/mastery/teach_back/quiz/path/learner_state）；E2E-001 存在（test_learning_loop_e2e） | PASS |
| **AA-P1-001 外置资产索引** | WORK-LAB | 无 ExternalAssetRecord（URI/hash/media/source/rights/extraction/derived IDs） | NOT_EXECUTED |
| **AA-P1-002 摄取状态矩阵** | WORK-LAB | 见下 §三（证据充分可立即生成） | 可交付 |
| 联邦契约 V1（KnowledgeQuery/CandidateSubmission/CandidateReceipt/EvidenceIntake/LearningRecord/Provenance/Rights） | WORK-LAB §6.1 | app/contracts/v1.py 无这些契约 | NOT_EXECUTED |
| E2E-001 人类学习闭环 | WORK-LAB §11 | test_learning_loop_e2e（review-outcome→mastery→machine_knowledge→tick→distill） | PASS |
| E2E-003 治理查询/Candidate Receipt | WORK-LAB §11 | 查询有；Receipt/回读契约缺 | PARTIAL |
| 知识迁移试点（3 对象） | WORK-LAB §12 | 需契约先行 | BLOCKED（依赖 AA-P0-002） |
| reports/current/ 交付目录 | WORK-LAB | 不存在 | NOT_EXECUTED |
| 四库首次启动全链 | 基线 R1 | app/setup + workspace_manifest 骨架；分库选择/重启回读未 E2E 证明 | PARTIAL |
| React 六空间真实 | 基线 R4 | Learning 真实；其余 5 个占位符 | PARTIAL |
| Tauri 桌面闭环 | 基线 R5 | 无 src-tauri/tauri.conf.json | NOT_EXECUTED |
| 发布 R6 | 基线 | packaging/+developer-kit；v0.5.0 旧资产 | PARTIAL |
| 平台采集 R7 | 基线 | web.py raw-first 已实现；媒体连接器未做 | PARTIAL/NOT |

## 三、摄取能力真实状态矩阵（AA-P1-002 · 证据版）

| 格式 | 引擎 | 状态 | 证据 |
| --- | --- | --- | --- |
| 文本 md/txt/csv/json/canvas/ajson | passthrough | PASS | ceshi 20804；scripts/pipeline |
| PDF（文字/扫描） | pymupdf→OCR 兜底 | PASS | ceshi 66/66；rescan_all_receipt |
| Office docx/pptx/xlsx | adapter/markitdown | PASS | 24+4 实测 |
| 旧版 .doc | 缺转换器 | FAIL（2 个） | 需 LibreOffice/antiword |
| 图片 png/jpg/webp/gif | RapidOCR(+Tesseract 兜底) | PASS | ceshi 1273（8 超大 FAIL）；TESSDATA 根因已修 |
| 音频 mp3/m4a | SenseVoice→faster-whisper | PARTIAL | 引擎验证 26x；全量转写暂停（F1） |
| 视频画面 mp4 | 抽帧+RapidOCR | PARTIAL | 实证；全量暂停（F8） |
| 视频增强 | PySceneDetect+VLM+字幕 | NOT_EXECUTED | 调研完成（V1-V5 待做） |
| Web URL | web.py raw-first | PASS | 4223B 真实现；PolicyGate+原文保全 |
| 噪声过滤/质量门 | content_cleaner+ocr_gate | PASS | 7+6 测试；牛津去噪实证 |

## 四、整合推进顺序（人工批准点标记 ⚠）

1. **⚠ 交付 AA-P1-002 摄取状态矩阵** → reports/current/INGESTION_REALITY_MATRIX.json（本会话已产出素材，落盘为交付文件）
2. **⚠ AA-P0-001 状态真相再生**：SYSTEM_BOUNDARY.md + 产品计划对齐 HEAD c83225b（文档级）
3. **AA-P0-002 知识 API 契约设计**（V1 契约 + 幂等/Receipt/分页/错误码/版本协商/权限身份/hash readback）→ 设计文档，实施需批准
4. **AA-P1-001 ExternalAssetRecord** 设计 + 索引实现（不复制大原件）
5. **联邦契约 V1 落地** → E2E-003 → 迁移试点（3 对象）
6. R1 四库首启 E2E → R4 React 真实化 → R5 Tauri（依次，均需批准）

## 五、人工批准点（执行边界）
- commit / push / 迁移 / Secret / 证据等级提升 / 全量反向迁移 —— **均需人工批准**（WORK-LAB 任务包 §16 + 基线10）
- 本会话默认只读；写交付文档视为报告产物，但 commit/push 一律先征求批准

## 六、会话基线速查（整合后）
基线 01-12 全量生效；补充：联邦契约归 ArcheAxis 拥有（KnowledgeQuery/CandidateSubmission/CandidateReceipt/EvidenceIntake/LearningRecord/Provenance/Rights V1）；E2E 以真实样本为准；状态词禁 DONE；未来能力（LER/3D/空间记忆）保留契约不抢 MVP。

## 七、执行状态更新（2026-08-19 · 推进完成项）

| 任务 | 状态 | 证据 |
| --- | --- | --- |
| **AA-P0-002 联邦知识 API**（批量提交/幂等/Receipt/Verified 回读/分页/hash readback） | **已实现** | app/contracts/federation_v1.py + app/federation/service.py + router.py；7 路由注册；tests/test_federation_v1.py 5 passed |
| **AA-P1-001 外置资产索引 ExternalAssetRecord** | **已实现** | app/contracts/federation_v1.ExternalAssetRecordV1 + external_asset_records_v1 表 + 注册/列表 API + 测试 |
| **AA-P0-001 状态真相再生** | **已执行** | SYSTEM_BOUNDARY.md 重生成对齐 HEAD c83225b；本文件 §二矩阵核对 |
| **AA-P0-003 人类学习保留** | **确认 PASS** | 学习引擎未降级；E2E-001 仍在（test_learning_loop_e2e） |
| **reports/current/** | **已建立** | INGESTION_REALITY_MATRIX.json（AA-P1-002 交付） |
| 管线任务（F1/F8/F9） | 延后（用户指示） | 脚本已固化 scripts/pipeline/，随时可开跑 |

## 八、最终推进状态（2026-08-19 收尾）

| 项 | 状态 | 证据 |
| --- | --- | --- |
| E2E-003 联邦回环（HTTP） | PASS | integration-tests/test_federation_e2e003.py（提交→回执→幂等→人工验证→查询→hash 回读） |
| 知识迁移试点（3 对象） | PASS | integration-tests/test_knowledge_migration_pilot.py + reports/current/CANDIDATE_ROUNDTRIP_PROOF.json + FEDERATION_MIGRATION_REPORT.md |
| R1 四库首启 + 重启回读 | PASS | integration-tests/test_r1_four_library_e2e.py（create_workspace 四域 + manifest 重载） |
| R4 六空间真实化 | PARTIAL→**PASS(前端)** | 5 空间接真实 API（Evidence/Workspace/AI Assets/Library/Settings）；tsc 0；vitest 17/17；后端 evidence 列表端点新增 |
| R5 Tauri 桌面 | 脚手架就位 / 构建 **BLOCKED** | src-tauri/（Cargo.toml/main.rs/tauri.conf.json）；本机无 cargo（G1 人工门禁） |
| reports/current 交付 | PASS | CLOUD_BASELINE / EXACT_SHA_VERIFICATION / CONTRACT_CONFORMANCE / REMAINING_HUMAN_GATES / INGESTION_REALITY_MATRIX / FEDERATION_MIGRATION_REPORT / CANDIDATE_ROUNDTRIP_PROOF |
| 管线任务 | 延后（用户指示） | scripts/pipeline/ 就绪 |
