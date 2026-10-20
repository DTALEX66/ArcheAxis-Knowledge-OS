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

## 后续只读投影增量（2026-08-24）

- Evidence Space 增加真实 `GET /workspace/api/evidence/bundles` 摘要列表及按
  Bundle id 获取的 `GET /workspace/api/evidence/bundles/{id}/inspection`；两者只读取
  已持久化的账本、人工审核和候选版本溯源，不新增写路径或独立前端状态库。
- Inspector 对该投影明确呈现 supports/refutes 冲突、权利、范围、最近人工复核和关联
  KnowledgeVersion/Conflict 状态。缺失或不可读的 Bundle 返回不可用，而非推断为已验证。
- 本地验证：`tests/test_evidence_bundle_ledger.py` 和 Workspace 路由定向测试共 8 passed；
  `frontend/src/__tests__/ClosedLoopSpaces.test.tsx` 11 passed；`npm run build`、变更 Python
  文件 Ruff 均通过。
- `main@20fb72ad86b876a993f1ffe1a4c25da70bc0a0c2` 的风险选择 CI
  [`32669760922`](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/32669760922)
  已 success（gateplan、lint、browser-smoke 和主测试）。因此该代码提交为
  `CI_VERIFIED_EXACT_SHA`；按 GatePlan 跳过的桌面打包/安装器作业不构成运行时验证。

这仍不是跨库 RawAsset 实体存在性核验、干净 Windows 桌面 E2E 或真实旧数据迁移证据；
上述三项必须继续单独记录，不能由此 UI 读模型升级为运行时闭环结论。
