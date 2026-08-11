# Intake: H2 Pipeline Integration & MFX-001 Compliance Closure

> 日期：2026-08-12

## 摘要

本批次完成 H2 管线整合（route/quality/evidence/learning/bakeoff）与
MFX-001 供应链接收合规修复，全部经 PR merge 至 main。

## 变更

1. **H2 routing**（早期批次）：`file_detection`（Magika ONNX）接入摄入
   路由替代扩展名判断（#105）。
2. **H2 quality**：`text_quality` CER/WER 质量门接入转换管线（#82）。
3. **H2 evidence**（#124）：pipeline Stage 7 `evidence` action——
   EvidenceConnectors（Crossref/DataCite/OpenAlex/Wikidata）接入交叉
   验证；DOI 存在直接查询，否则 claim-text 搜索；`public-evidence`
   分类永不提升为 verified。
4. **H2 learning**（#125）：`record_practice_evidence` 硬编码调度
   （interval=1/ease=2.5/next=now）→ `knowledge_base.reviews._sm2_interval`
   真实 SM-2 间隔重复（quality=5 连续 3 次 → 1/6/16 天）。
5. **H2 bakeoff**（#126）：`scripts/run_bakeoff.py` 可重复 OCR/ASR
   引擎对比 CLI；RapidOCR 三语种 CER 0.0 实测最优、faster-whisper
   英文 CER 0.0。
6. **MFX-001 合规修复**（#128）：账本 B003（Marker）REVIEW-BLOCK
   （权重修改版 OpenRAIL-M 需单独审查）却注册为默认 PDF 引擎 →
   移除；测试改用账本 blocked 集合驱动断言。

## 附带

- 依赖锁定漂移修复（#123）：httpx2 幽灵包、faster-whisper/rapidocr
  从未入 lock。
- 占位卫生（#129）：2 个死壳 builder 删除、2 个 deferred 模块标注。
- 远程分支清理 68 个；kb 内部 38 测试激活（#119）。
- 文档双写：EXTERNAL_DEPENDENCIES（rapidocr/faster-whisper 登记）、
  THIRD_PARTY_NOTICES（Magika vendored 模型登记）。

## 待办（需 Owner）

- 命名迁移阶段 3（打包/仓库名/底层模块）。
- `docs/verification-summary-2026-08-09` 归档方式。
- ASR 重模型 / torch 下载（~2GB）；PaddleOCR/EasyOCR 重依赖。

## 回滚

每个 PR 均为独立 squash merge 至 main；回滚 = revert 对应 merge commit。
