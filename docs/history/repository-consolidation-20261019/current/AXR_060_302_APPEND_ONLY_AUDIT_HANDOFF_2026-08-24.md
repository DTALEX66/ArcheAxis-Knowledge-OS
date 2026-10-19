# AXR-060-302 追加写入审计交接（2026-08-24）

## 本次已落地

- 联邦 Evidence、Learning、Provenance、Rights 四类记录通过统一的受控写入器使用明确列名的 `INSERT INTO`；该写入器不使用 `INSERT OR REPLACE`。
- 四类记录表新增数据库级 `UPDATE` / `DELETE` 拒绝触发器，常规 SQL 覆盖或删除会中止。
- `ProvenanceRecordV1` 的事件集合被限制为 `created`、`promoted`、`revoked`、`superseded`。
- `revoked` 与 `superseded` 必须携带 `parent_id`、`actor`、`reason`、`at`；修正会新增事件而非覆写旧事件。
- 已有联邦 SQLite 库在首次受控打开时以向前兼容方式补充 `reason` 列；写入改为显式列名，避免 SQLite `ALTER TABLE` 后的列序差异。回归测试覆盖旧库迁移后关闭并重新读取。

## 本地验证（2026-08-24）

```text
pytest tests/test_federation_v1.py tests/test_federation_router_security.py \
  tests/test_federation_records.py tests/test_learning_outcome.py \
  tests/test_knowledge_governance_schema_tamper.py \
  tests/test_knowledge_governance_migration.py \
  tests/test_knowledge_candidate_versioning.py \
  tests/test_research_knowledge_governance_lifecycle.py -q
35 passed, 2 warnings

python -m compileall -q app/contracts/federation_v1.py app/federation/service.py
python -m ruff check app/contracts/federation_v1.py app/federation/service.py tests/test_federation_records.py
All checks passed
git diff --check
PASS
```

警告为已存在的 Starlette TestClient 弃用提示和可选 NLTK 未安装提示；不影响本次断言。

## 重要边界

SQLite 是本地文件数据库。对直接取得数据库文件读写权限、且绕过应用 API 的外部程序，SQLite 本身不能提供密码学不可篡改性；特别是外部连接可选择自己的冲突策略。因此本次可验证承诺是：产品受控写入器不生成 `REPLACE`，常规更新/删除在数据库内被拒绝，修正遵循追加事件链。若需对恶意本地文件写入者作出防篡改承诺，需另行设计签名/哈希链、密钥边界和独立验证器，不能由此实现宣称达成。

本文件不构成全量 M3 完成声明。`CI_VERIFIED_EXACT_SHA`、合并主线、安装版与完整发布门禁仍未执行；M3-303 EvidenceBundle / KnowledgeVersion 也仍需单独闭环。
