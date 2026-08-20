# 管线全链路通畅度审计（CLOSED_LOOP_AUDIT）· 2026-08-20

> 按统一基线最短闭环（选择四库→导入→哈希→转化→证据→候选→复核→Verified→双写→检索→导出→重启回读）逐环节核验。

## 1. 全链路通畅度矩阵（证据=测试/实测）

| 环节 | 证据 | 状态 |
| --- | --- | --- |
| 四库选择/初始化/重启回读 | test_r1_four_library_e2e（create_workspace 四域 + manifest 重载） | ✅ PASS |
| 导入真实文件 + 哈希保全 | test_ingestion + ceshi 22,422 实测（raw_sha256） | ✅ PASS |
| 多格式转化（文本/PDF/Office/图片/音频/视频/Web/svg） | 全量回执（知识类 100%）+ test_web_full_chain_e2e | ✅ PASS |
| OCR/ASR | RapidOCR（1273 图）+ SenseVoice（14/14 mp3）实测 | ✅ PASS |
| 证据锚定（anchor/时间码） | test_evidence_anchor + /api/evidence/anchors | ✅ PASS |
| Candidate → 人工复核 → Verified | promotion 状态机 + test_axw_main_chain_e2e（read-back 断言） | ✅ PASS |
| 双写（Human Learning / AI Assets） | test_learning_outcome + main_chain（learning card + machine 候选） | ✅ PASS |
| 带引用检索 | test_rag_pipeline + 评估集（qwen3-embedding 0.35，GPU 100%） | ✅ PASS |
| 导出 | exchange/export（test 覆盖） | ✅ PASS |
| 重启回读 | R1 manifest 重载 + main_chain 回读断言 | ✅ PASS |
| 联邦知识 API | E2E-003（提交→回执→幂等→复核→查询→hash 回读） | ✅ PASS |
| Web 全链路 | test_web_full_chain_e2e 3/3（摄取→截图→OCR→转化） | ✅ PASS |

**本轮实测：6 个全链 E2E 共 12 passed**（main_chain + 四库 + 学习闭环 + 联邦 + Web + 迁移试点）；后端 170+ 单测、前端 tsc 0 + vitest 17/17。

## 2. 结论：链路已通畅，无需继续链路测试
- 管线全链路（摄取→知识→双写→检索→回读）**已真实跑通并有 E2E 证据**，无需再测链路本身。
- 剩余为**数据覆盖项**（非链路问题）：
  - mp4 音轨 64 个（延后；--audio-only 就绪，F8 画面已覆盖）
  - .doc 2 个（缺 LibreOffice/antiword 转换器）
  - 20 低文本截图（按设计 gate-fail）；svg 1 个光栅化失败
- 剩余为**人工/外部门禁**：ollama 升级（rerank+视觉）、MinerU 模型下载、安装包干净机验收、R7 平台连接器。

## 3. 如需继续测试（可选，非必需）
- mp4 音轨转写全量（产出最终 100% 覆盖回执）——建议跑
- 四库 UI 走查（Settings 初始化按钮人工验收）
