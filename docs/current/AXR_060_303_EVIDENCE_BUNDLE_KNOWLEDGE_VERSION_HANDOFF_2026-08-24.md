# AXR-060-303 EvidenceBundle / KnowledgeVersion 交接（2026-08-24）

## 本次已落地

- `knowledge-governance.sqlite` 新增受所有者管理的 `phase5_evidence_bundle_ledger_v1` 迁移，包含 Bundle、Entry、Review 三张表及索引；沿用 `MigrationOperator` 的备份、前向迁移、回滚与状态读回路径。
- 每个 Entry 持久化完整小写十六进制 SHA-256、源修订、非空物理锚点快照、支持/反驳/未知关系、来源组织谱系、来源类型、有效期、范围和权利。
- Bundle 采用确定性内容指纹；同一 id 的不同内容会被拒绝，写入路径使用显式列的 `INSERT`。
- `verified` 审核要求至少两个不同的 `source_lineage`，因此单一网页、模型输出或 OCR 不能单独升级为 verified。审核收据是独立追加记录。
- `not_verifiable` 与 `rejected` 均被保留为人工审核结论；`get_reviewed_bundle` 只返回 verified Bundle，不会把它们误当 verified。
- `KnowledgeVersionProposal` 强制绑定 `evidence_bundle_id`。写入时在同一事务中要求 Bundle 已被人工审核，并在版本 `provenance_json` 持久化 Bundle id、内容指纹和审核结论。未审核 Bundle 被拒绝；`not_verifiable` 可生成候选版本但不会获得 verified-only 读取资格。

## 本地验证（2026-08-24）

```text
pytest tests/test_evidence_bundle.py tests/test_evidence_bundle_ledger.py \
  tests/test_evidence_contract.py tests/test_knowledge_candidate_versioning.py \
  tests/test_knowledge_governance_migration.py \
  tests/test_knowledge_governance_schema_tamper.py \
  tests/test_research_knowledge_governance_lifecycle.py -q
30 passed, 1 skipped

python -m compileall -q app/evidence/ledger.py app/knowledge/versioning.py \
  shared/knowledge_governance_migration.py shared/migration.py shared/migration_runner.py
python -m ruff check <changed Python files>
All checks passed
git diff --check
PASS
```

唯一跳过的是 `tests/test_evidence_contract.py` 的可选真实 OCR 测试：当前 `TESSDATA_PREFIX` 同时指向不存在的外置语言包路径，Tesseract 无法加载 `eng.traineddata`。这不是 Bundle/Version 逻辑失败，也未在本任务中修改外置工具链配置。

## 证据层级与边界

- `IMPLEMENTED_LOCAL`：PASS（迁移、持久化、审核和 KnowledgeVersion 绑定已在隔离工作树实现）。
- `TESTED_LOCAL`：PASS（上述 30 项定向回归；1 项可选 OCR 环境跳过）。
- `CI_VERIFIED_EXACT_SHA`：NOT EXECUTED（独立分支未触发 CI 前不可宣称）。
- `MERGED_MAIN` / `INSTALLED_RUNTIME_VERIFIED`：NOT EXECUTED。

Bundle 保存的是 RawAsset 身份与锚点的不可变快照，尚未在本切片中跨数据库强制解析到 `RawAssetStore` 的实际文件存在性；跨源导入→RawAsset→Bundle→KnowledgeVersion 的真实 UI/E2E 仍是后续闭环验证，不应由本地单元测试替代。
