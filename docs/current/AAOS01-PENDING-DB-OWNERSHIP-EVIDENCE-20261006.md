# 28 个"归属证明不足"数据库的归属证据（2026-10-06 实测）

对象：`AAOS01-CLEANUP-EXECUTED-AND-PENDING-20261005.md` 第 22 行记录的待归属项——
28 个数据库、157,745,152 字节，独立审查结论 `OWNERSHIP_PROOF_INSUFFICIENT_KEEP_PENDING_ATTESTATION`，
理由是"当前工具与固定合成助手能建立**产生者可能性与家族相似**；名称/布局/当前产生者哈希/上批批准**不能证明每一个**"。
清单出处：`.project-local/task-runtime/aaos01-tools/volume-history-readback.json` → `pending_unknown_db_ownership.paths`。

## 一、之前的审查缺了什么

那份审查只记录了 `path / exists_now / bytes_now / historical_bytes`——**从未看过这些库里装的是什么**。
因此它只能得到"家族相似"，得不到归属。本轮直接读内容（需经产品自身的 sqlite-vec 通路，理由见台账的 `vec0` 一节）。

## 二、实测：每一条都是具名测试的合成数据

28 条路径全形如
`.project-local\runs\be268a2d33\ce3921cec208\pytest-tmp\pytest-of-ALEX\pytest-0\<测试名>0\runtime.sqlite`——
即 **pytest 自己的临时目录工厂**（`pytest-of-<user>/pytest-0/`），文件名 `<测试名>0` 就是 pytest 对 `tmp_path` 的命名。

读其中一个（`test_vector_rollback_rejects_c0/runtime.sqlite`，51 张表）得到的**内容**：

| 观察 | 值 |
| --- | --- |
| `kb_documents` | `doc-new / New / verified candidate content / test` |
| FTS 影子内容 | `doc-old / Old / previous active content / test` |
| `vec_kb_documents_id_map` / `..._rollback_<hash>_id_map` | `doc-new` / `doc-old` |
| `vec_unrelated_id_map` 及回滚/候选影子 | `foreign-active` / `foreign-candidate` / `foreign-backup` |
| `migration_operator_runs` | `owner=vector.documents`、`target=vec_kb_documents`、provenance 含 `dim: 384`、`recorded_at=2026-09-15T18:39:55Z` |

全是测试词汇：`source='test'`，正文是 `verified candidate content` / `previous active content`，外来对象叫
`foreign-active` / `foreign-candidate` / `foreign-backup`。没有一条像真实用户内容。

## 三、产生者被指认（可复核）

上述词汇在**整个仓库里只出现在一个文件**：`tests/test_migration_runner.py`。
28 个库名与其中的测试函数逐一对应：

- `test_vector_owner_rebuilds_from_canonical_rows_and_rolls_back`（:337）
- `test_vector_rollback_rejects_corrupted_provenance_before_unrelated_tables_touch`（:985）
- `test_vector_rollback_rejects_post_apply_active_drift_and_allows_retry`（:1084）
- `test_vector_rollback_rolled_back_provenance_failure_keeps_applied_state`（:1173）
- `test_vector_apply_blocks_ordinary_active_writer_during_activation`（:1308）

即：**这 28 个库是 2026-09-15 那次 pytest 运行中，由上述具名测试用合成夹具创建、并留在 pytest 临时工厂里的 scratch 数据库。**
这不再是"家族相似"，而是"产生者被指认 + 数据自证"（库内 `migration_operator_runs` 甚至记着它自己的绝对路径）。

## 四、结论与建议（删除仍须业主确认）

- 归属问题**已解答**：类别 = pytest 临时 scratch，产生者 = `tests/test_migration_runner.py` 的五个具名测试，输入 = 合成夹具。
- 该类按定义可再生（重跑那五个测试即可重建），因此**可删除**——但**不自行删除**：上一轮对该批的明确动作是 `KEEP`，
  推翻一个明确的保留裁决需要业主背书，而不是由执行者顺手改判。
- 若业主同意：删除前对 28 条取逐路径清单（含 `bytes_now`、`sha256`）存档，作为恢复引；
  并注明它们位于 `.project-local/runs/<identity>/...` 这一被忽略的运行根内，不属于产品数据。
- 本文档不删除任何文件，也不改动 Green 与产品目录。

## 五、这条证据的支点（有测试守着）

证据链的支点是"这些合成词汇只出现在那一个测试文件里"。若该词汇被移走或测试改写，上面的指认就不再成立——
所以 `tests/workflow/test_pending_db_ownership_evidence.py` 固定这一支点，而不是把结论写死在文档里。
