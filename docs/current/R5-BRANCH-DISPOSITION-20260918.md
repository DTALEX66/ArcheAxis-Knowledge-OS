# R5 Remote Branch Disposition Report (read-only, base 44bd821)

> **与既有收敛记录的关系**：R5 分支收敛附包已存在，本报告是对**当前基线**的补充复审，
> 不是首次远端分支审计，也不替代既有记录：
> - `docs/current/BRANCH-CONVERGENCE.md`（收敛附包方法与顺序：分类不等于删除批准；先完成
>   合并资格与证据落盘，再逐条删除已批准分支）；
> - `docs/current/BRANCH-DISPOSITION-20260918.md`（2026-09-18 处置证据：PR #149 合并、
>   10 个远端分支按逐条吸收审查删除、收敛分支随后删除、再删 3 个 `SUPERSEDED` 分支后远端计数 18）；
> - `docs/current/BRANCH-CONVERGENCE.json`（逐分支分类基线，18 行）。
>
> 本报告新增的是：在 `44bd821` 这一基线上，对**现存 17 个非 main 分支**重新做 blob 级判定，
> 并给出删除候选/保留/上报的现行处置。

- Repository: `DTALEX66/ArcheAxis-Knowledge-OS`
- Base: `main` @ `44bd821da82d9beeacf4e3c6f581c0fd90521ba4` (matches local checkout HEAD on branch `main`)
- Remote read path: `gh` CLI (account DTALEX66), GET only. `git fetch` is broken in this environment, so all remote state came from
  `GET /repos/.../branches`, `GET /repos/.../compare/main...<branch>`, `GET /repos/.../pulls` and `GET /repos/.../releases`.
- Method: for every branch I read `ahead_by` / `behind_by` / `status` and the changed-file list from `compare`; then, because the
  local object database already holds every branch tip, I tested absorption locally with `git merge-base --is-ancestor`,
  `git rev-parse <rev>:<path>` blob comparison, and `git cat-file -e main:<path>`.
- **Critical structural finding:** every one of the 17 branches reports `status=diverged` with `ahead_by > 0` and
  `git merge-base --is-ancestor <tip> main` = 1 (true), i.e. **no branch tip is an ancestor of `main`**. That is *not* evidence of
  unabsorbed work: 15 of the 17 have a closed **merged** PR, and each merged PR's `merge_commit_sha` *is* an ancestor of `main`
  (`merge-base --is-ancestor` = 0). These were **squash merges**, so the branch tip can never be an ancestor. Absorption therefore
  had to be judged by comparing each branch tip's blob content against its PR's squash-merge commit, and then against current `main`.
- Existing in-repo baseline consulted: `docs/current/BRANCH-CONVERGENCE.json` (schema `archeaxis.branch-convergence/v1`,
  generated 2026-09-17, 18 rows). It marks all 17 rows `action=AUDIT_BEFORE_ACTION`,
  `latest_intent_verdict=PENDING_DETAILED_AUDIT`. Its provisional classes are reproduced in the per-branch notes and **three of
  them are contradicted by the evidence below** (`ci-release-optimization`, `recovery-shell-closed-loop`,
  `execution-reliability-standards`).

## 中文摘要（2026-09-18）

- 结论：17 个非 main 分支全部分类并给出处置；**未删除 / 未修改 / 未重命名任何分支、标签、发布或 PR**，远端分支数仍为 18。
- 分类计数：语义已吸收 **11**、仅历史归档 **1**、仅发布历史 **4**、供体能力 **1**、有效缺失工作 **0**。
- 处置计数：**删除候选 9 / 保留 4 / 上报 4**（合计 17）。
- 删除候选（9，**实际删除 0**）：`chore/naming-repo-refs`、`chore/placeholder-hygiene`、`docs/intake-h2`、`docs/naming-handoff`、`docs/verification-summary-2026-08-09`、`feat/naming-package-identity`、`feat/naming-step3`、`feat/naming-v2-contract`、`fix/mfx001-marker-block`。
- 保留（4）：`codex/execution-reliability-standards`（供体能力：无 PR，8 个文件在主线一个都没有）、`codex/post-release-v0.6.9`、`codex/release-v0.6.9`、`codex/v0.6.8-release-closure`。
- 上报（4）：`codex/frozen-roadmap-deepseek-v1`、`codex/recovery-shell-closed-loop`、`codex/ci-release-optimization`、`release/v0.4.0-contract`。四个受保护分支**无一**落入删除候选。
- 结构性发现：17 个分支全部 `diverged` 且无 tip 为主线祖先，因为其中 15 个是**压缩合并**；吸收与否必须按文件内容对压缩提交比对，**不能**用祖先关系判定。
- 与仓库内既有基线的分歧：`docs/current/BRANCH-CONVERGENCE.json` 把 `ci-release-optimization`、`recovery-shell-closed-loop` 标为 `DONOR_CAPABILITY_TO_REIMPLEMENT`，把 `execution-reliability-standards` 标为 `HISTORICAL_ARCHIVE_ONLY`；本报告证据与之相反（见下方逐分支说明）。该基线自身仍为 `PENDING_DETAILED_AUDIT`，**未被改写**。
- 更正记录：本文件自报合计行原写 `DELETE_CANDIDATE 8, RETAIN 4, ESCALATE 5`，与上方逐分支汇总表（9/4/4）自相矛盾；已按表中逐条证据更正（提交 `57dccc1e`），并注明错误原因。
- 环境说明：采集时 `git fetch`（SSH）在执行环境被拒，远端状态只经 GitHub REST 读回；该限制随后解除，本报告关键结论已独立抽验复核（分支数 18；PR#140/#142 合并提交为主线祖先且其 head 等于所称 tip；供体分支确无 PR 且其关键文件在主线不存在）。
- 明细与逐分支证据见下方正文（作为证据附录保留）。

## Summary

| branch | tip_sha | ahead | behind | category | disposition | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| chore/naming-repo-refs | a9aa0665cc0b99fb222b04169a004cd23b04c7cc | 3 | 1100 | SEMANTICALLY_ABSORBED | DELETE_CANDIDATE | PR#132 merged → `04273c93` (ancestor of main); all 8 declared files byte-identical tip↔squash. Residual = 2 post-merge CI cache-key commits (`037bd8c6`, `a9aa0665`) targeting the removed `desktop/src-tauri` lane. |
| chore/placeholder-hygiene | 116874006901baf401007def80b5715afe460e0a | 1 | 1103 | SEMANTICALLY_ABSORBED | DELETE_CANDIDATE | PR#129 merged → `98f7546b` (ancestor). `app/agent/tool_router.py`, `app/core/attention.py` byte-identical; the 2 `knowledge_base/**/builder.py` deletions have no counterpart in main. |
| codex/ci-release-optimization | 74ca55361371551030838257280d19fc343ac5cb | 7 | 853 | SEMANTICALLY_ABSORBED | ESCALATE | PR#140 **MERGED**, `headRefOid` = tip, merge commit `93e58a3b` (ancestor). 97/100 files byte-identical tip↔squash; 3 removed report snapshots are deleted, not missing; `frontend/src/api/runtime.ts` blob `99dc3205` identical in squash, later refactored away on main. |
| codex/execution-reliability-standards | affc0abcea7d080542e3f294322403f27ec6352a | 2 | 1160 | DONOR_CAPABILITY | RETAIN | **No PR at all.** 0/8 blobs present in main: `docs/CODEX_EXECUTION_RELIABILITY.md` (7 865 B), `docs/taskpacks/DEEPSEEK_POST_AUDIT_FULL_EXECUTION_TASKPACK_v1_2026-08-11.md` (14 025 B), `workspace/intake/2026-08-10-codex-execution-reliability-policy.md` (1 663 B). |
| codex/frozen-roadmap-deepseek-v1 | fcfac4a8dac0cf285599a757e63ddb14e1f2ef6f | 149 | 1162 | HISTORICAL_ARCHIVE_ONLY | ESCALATE | **No PR at all.** 118/137 files absent from main; 103 are `.../historical-sources-2026-07-14-to-2026-08-08/**`, 10 `.../planning-2026-08-09/**`; no code, no test, no config file. |
| codex/post-release-v0.6.9 | e50aad0d0407a3d726d048d56136e3bbe35455e1 | 2 | 849 | RELEASE_HISTORY_ONLY | RETAIN | PR#144 merged → `b3367958` (ancestor); 11/11 files byte-identical. `reports/release/v0.6.9/release-evidence.json` and `RELEASE_LEDGER.md` v0.6.9 rows are on main. |
| codex/recovery-shell-closed-loop | 14afe9376adfa9e528a93cbfbd943bdfe59b3d33 | 13 | 851 | SEMANTICALLY_ABSORBED | ESCALATE | PR#142 **MERGED**, `headRefOid` = tip, merge commit `52f4c7ff` (ancestor); 22/22 files byte-identical. `frontend/src/components/RecoveryShell.tsx`, `src-tauri/src/recovery.rs`, `frontend/src/runtime/recovery.ts` all present in main. |
| codex/release-v0.6.9 | c64278dfcb77da8698d5edff72a55a3eae90ee9a | 2 | 850 | RELEASE_HISTORY_ONLY | RETAIN | PR#143 merged → `de5b5ba6` (ancestor, and `RELEASE_LEDGER.md` cites it); 29/29 files byte-identical. Version truth on main is now `0.6.14`. |
| codex/v0.6.8-release-closure | 42e7c0cc36fa6c7b8296c59be1ac885dd94c920e | 2 | 852 | RELEASE_HISTORY_ONLY | RETAIN | PR#141 merged → `2d1186d9` (ancestor); 16/16 files byte-identical; `reports/release/v0.6.8/release-evidence.json` present on main. |
| docs/intake-h2 | d618b659ebc34ee0de0b69fd79499daa930bcbf9 | 1 | 1102 | SEMANTICALLY_ABSORBED | DELETE_CANDIDATE | PR#130 merged → `996462f5` (ancestor); the single file `workspace/intake/2026-08-12-h2-pipeline-integration.md` is blob-identical on main (both `f396d96a`). |
| docs/naming-handoff | c16ce899b1916715087cc92fd04a84f2e5f60e3a | 1 | 1096 | SEMANTICALLY_ABSORBED | DELETE_CANDIDATE | PR#134 merged → `66c6aac2` (ancestor); file byte-identical tip↔squash and present on main; main copy differs from tip only by a later 6-line edit. |
| docs/verification-summary-2026-08-09 | 8cc9c69080786f9aeceaa882aba65a0e4c6a8848 | 1 | 1162 | SEMANTICALLY_ABSORBED | DELETE_CANDIDATE | PR#70 closed unmerged, but the doc was re-landed by PR#137 → `b44fabbb` at `docs/verification/VERIFICATION_SUMMARY_2026-08-09.md`, whose own header records its origin as this branch. |
| feat/naming-package-identity | 12a2a5f6d8b546f3892a6b4722892e079a1e6054 | 1 | 1101 | SEMANTICALLY_ABSORBED | DELETE_CANDIDATE | PR#131 merged → `2694d861` (ancestor); 17/17 files byte-identical tip↔squash. `pyproject.toml` name on main is still `archeaxis-workspace`; `desktop/scripts/prepare_bundle.py` still globs `archeaxis_workspace-*.whl`. |
| feat/naming-step3 | bc4a234ffe4d84b2495a06080bded4a53db92898 | 1 | 1094 | SEMANTICALLY_ABSORBED | DELETE_CANDIDATE | PR#136 closed unmerged; its content was re-landed in PRs #137/#138 (see `docs/HANDOFF_2026-08-12_naming-migration.md`). Intent verified on main: `ARCHEAXIS_*` env prefix + legacy aliases in `shared/config.py`, naming-registry gate in `scripts/check_repository_conventions.py`, `product == "ArcheAxis Knowledge"` in `desktop/src-tauri/src/protocol.rs`. |
| feat/naming-v2-contract | b7234af47163f7c6e3498d7fc7344da5a6e002a3 | 1 | 1094 | SEMANTICALLY_ABSORBED | DELETE_CANDIDATE | PR#137 merged → `b44fabbb` (ancestor); 15/15 files byte-identical. `docs/truth/NAMING_CONTRACT_V2.md` present on main and referenced as the locked contract by `check_repository_conventions.py`. |
| fix/mfx001-marker-block | af7a20f109c3dadeac97031d27c6a554fa651aad | 1 | 1104 | SEMANTICALLY_ABSORBED | DELETE_CANDIDATE | PR#128 merged → `a2056d04` (ancestor); 2/2 files byte-identical. The decision is live on main: `app/ingestion/multi_format.py:9` records `marker-pdf REVIEW-BLOCK, excluded`. |
| release/v0.4.0-contract | 75cb72ef4642b5dab4fdae5c81807b94757e6a69 | 4 | 1281 | RELEASE_HISTORY_ONLY | ESCALATE | PRs #21 (`5369ae6c`, ancestor) and #22 (`34936f13`, ancestor) both merged from this branch and preserve the released v0.4.0 artifact contract. |

Totals: SEMANTICALLY_ABSORBED 11, HISTORICAL_ARCHIVE_ONLY 1, RELEASE_HISTORY_ONLY 4, DONOR_CAPABILITY 1,
VALID_MISSING_WORK 0. Dispositions: DELETE_CANDIDATE 9, RETAIN 4, ESCALATE 4.
（合计 17 = 9 + 4 + 4；此前本行误写为 8/4/5，与上方逐分支汇总表矛盾，已按表中逐条证据更正。四个受保护分支 codex/frozen-roadmap-deepseek-v1、codex/recovery-shell-closed-loop、codex/ci-release-optimization、release/v0.4.0-contract 全部为 ESCALATE，无一落入删除候选。）

## Per-branch justification

### chore/naming-repo-refs — SEMANTICALLY_ABSORBED / DELETE_CANDIDATE
`compare` reports ahead=3, behind=1100 against merge-base `2694d861`. PR#132 ("chore(naming): update repo references after GitHub rename (step 2)") is `MERGED` with `merge_commit_sha=04273c9385a06334165263aa32fe72780965ae5f`, and `git merge-base --is-ancestor 04273c93 main` returns 0, so the squash is on main. All 8 files the branch declares (`.github/workflows/ci.yml`, `AGENTS.md`, `README.md`, `app/release.py`, `docs/environment/EXTERNAL_DEPENDENCIES.md`, `scripts/ci/classify.py`, `scripts/release_inject_identity.py`, `tests/test_release_manifest.py`) have **byte-identical blobs** between tip `a9aa0665` and `04273c93`.
Residual: two commits made *after* the squash, `037bd8c6` and `a9aa0665`, only retune Rust cache `restore-keys` (`${{ runner.os }}-cargo-naming-v2-`) for the `desktop/src-tauri` cargo lane. Main no longer has that lane at all (`git grep desktop/src-tauri main -- .github/workflows/ci.yml` → no match; main keys the cache on `src-tauri/Cargo.lock` with `-naming-v6`), so the residual is stale, not missing work. Baseline class was `CHECK_FOR_VALID_RESIDUAL`; the residual is resolvable and does not block deletion.

### chore/placeholder-hygiene — SEMANTICALLY_ABSORBED / DELETE_CANDIDATE
Single commit, ahead=1, behind=1103. PR#129 `MERGED` → `98f7546b` (ancestor of main). Of the 4 changed files, `app/agent/tool_router.py` and `app/core/attention.py` are byte-identical between the tip and the squash, and `knowledge_base/context_pack/builder.py` + `knowledge_base/taskpack/builder.py` are **removed by this branch**, so their absence from main is the intended outcome. Nothing unabsorbed.

### codex/ci-release-optimization — SEMANTICALLY_ABSORBED / ESCALATE
This is the branch whose baseline class (`DONOR_CAPABILITY_TO_REIMPLEMENT`) the evidence contradicts. PR#140 ("Release v0.6.8: close six-space trusted-knowledge loops") is `MERGED`; `gh pr view 140 --json headRefOid` returns exactly the branch tip `74ca5536`, and `merge_commit_sha=93e58a3b` is an ancestor of main. 97 of the 100 changed files are byte-identical between the tip and `93e58a3b`. The remaining 3 (`reports/current/CLOUD_BASELINE.json`, `CURRENT_CAPABILITY_MATRIX.json`, `EXACT_SHA_VERIFICATION.json`) were **deleted by this PR** (that is why main's `reports/current/` holds only `README.md`), and `frontend/src/api/runtime.ts` is identical in the squash (`99dc3205`) but was later reorganised into `frontend/src/api/{client,learning,workspace}.ts` by the v0.6.9+ shell consolidation. Marked `ESCALATE` solely because the escalation rule forbids ever marking this branch `DELETE_CANDIDATE`.

### codex/execution-reliability-standards — DONOR_CAPABILITY / RETAIN
Ahead=2, behind=1160, merge-base `ae59790f`. **There is no pull request for this branch** (the full `pulls?state=all` list contains no head `codex/execution-reliability-standards`), and no other PR absorbed it: 0 of its 8 changed blobs exist anywhere in main's object database. Three files exist on no path in main: `docs/CODEX_EXECUTION_RELIABILITY.md` (7 865 B — durable local-execution/Windows-shell/Git-delivery/test-environment rules), `docs/taskpacks/DEEPSEEK_POST_AUDIT_FULL_EXECUTION_TASKPACK_v1_2026-08-11.md` (14 025 B) and `workspace/intake/2026-08-10-codex-execution-reliability-policy.md` (1 663 B). The other five (`AGENTS.md`, `docs/VERIFICATION_POLICY.md`, `docs/truth/EXECUTION_STATUS_LOG.md`, `docs/truth/H0_H1_STATUS_HANDOFF.md`, `workspace/configuration/README.md`) were modified on the branch and main has since written its own, much larger versions. The content is agent/operator reliability policy rather than shipped product capability, and that guidance now lives operationally in the operator's skill library, so the disposition is `RETAIN` for owner judgement, not a merge demand. Baseline class `HISTORICAL_ARCHIVE_ONLY` is contradicted: this is not an absorbed archive.

### codex/frozen-roadmap-deepseek-v1 — HISTORICAL_ARCHIVE_ONLY / ESCALATE
Ahead=149, behind=1162, unique commits 149, merge-base `492fac59`. **No PR exists** for this branch and none of its history is on main. 118 of its 137 changed files are absent from main, but the composition is documentation/archive only: 103 under
`docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/**` (pack-extracts for `apple-desktop-ui-v1.0`, `desktop-cloud-reaudit-v1.0`, `open-source-absorption-2026-07-25`, `today-archive-v1.0`, plus `plans/**`, `source-documents/*.docx`, `.sha256` manifests and one `.zip`), 10 under `.../archeaxis-2026/planning-2026-08-09/**`, and the rest are `docs/ARCHEAXIS_DYNAMIC_UI_GENERATION_PROMPT_PACK_v1_2026-08-09.md`, one `docs/change-proposals/*TaskPack*.md`, and 3 `workspace/intake/*.md`. Main's `docs/architecture/imported-designs` holds 71 files but does **not** contain the `historical-sources-2026-07-14-to-2026-08-08` directory. Four files are byte-identical to main and six more have their exact blob elsewhere in main (the canonical `docs/taskpacks/DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md`, the two MANDATORY addenda, `docs/truth/AUTHORITY_CONTRACT.md`, `docs/truth/CURRENT_STATE_TRUTH.md`, `docs/truth/README.md`), and `docs/truth/FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md` is the same 22 381 bytes on both sides. Marked `ESCALATE` per the mandatory rule. Overlap note: its `docs/taskpacks/*` additions are the same family as the also-unmerged `codex/execution-reliability-standards` post-audit taskpack; the two branches are not independent.

### codex/post-release-v0.6.9 — RELEASE_HISTORY_ONLY / RETAIN
PR#144 `MERGED` → `b3367958` (ancestor of main); 11/11 changed files byte-identical between tip `e50aad0d` and the squash. Main carries the outcome: `reports/release/v0.6.9/release-evidence.json` exists, and `docs/RELEASE_LEDGER.md` records the v0.6.9 row and `## v0.6.9 release evidence` section. Retained because it preserves the released v0.6.9 record.

### codex/recovery-shell-closed-loop — SEMANTICALLY_ABSORBED / ESCALATE
Second branch whose baseline class (`DONOR_CAPABILITY_TO_REIMPLEMENT`) the evidence contradicts. PR#142 `MERGED`; `gh pr view 142 --json headRefOid` = tip `14afe937`; `merge_commit_sha=52f4c7ff` is an ancestor of main; 22/22 changed files byte-identical tip↔squash. The headline capability files are all present in main: `frontend/src/components/RecoveryShell.tsx`, `frontend/src/runtime/recovery.ts`, `src-tauri/src/recovery.rs`, plus the modified `src-tauri/src/main.rs`, `desktop/src-tauri/src/{backend,runtime}.rs` and `frontend/src/__tests__/RecoveryShell.test.tsx`. `frontend/src/api/runtime.ts` (`576dd50e`) is likewise identical in the squash and was later folded into `client.ts`/`workspace.ts`. Marked `ESCALATE` per the mandatory rule.

### codex/release-v0.6.9 — RELEASE_HISTORY_ONLY / RETAIN
PR#143 `MERGED` → `de5b5ba6`, which is an ancestor of main and is the SHA `docs/RELEASE_LEDGER.md` cites for the released v0.6.9; 29/29 changed files byte-identical tip↔squash. Version truth has moved on (`app/release-manifest.json` on main is `0.6.14`), so nothing here is pending.

### codex/v0.6.8-release-closure — RELEASE_HISTORY_ONLY / RETAIN
PR#141 `MERGED` → `2d1186d9` (ancestor); 16/16 files byte-identical; `reports/release/v0.6.8/release-evidence.json` and the `docs/RELEASE_LEDGER.md` v0.6.8 row are on main.

### docs/intake-h2 — SEMANTICALLY_ABSORBED / DELETE_CANDIDATE
Ahead=1. PR#130 `MERGED` → `996462f5` (ancestor). The single added file `workspace/intake/2026-08-12-h2-pipeline-integration.md` is the same blob (`f396d96a`, 2 083 B) at the tip, in the squash, and on main.

### docs/naming-handoff — SEMANTICALLY_ABSORBED / DELETE_CANDIDATE
Ahead=1. PR#134 `MERGED` → `66c6aac2` (ancestor); the added `docs/HANDOFF_2026-08-12_naming-migration.md` is byte-identical tip↔squash and present on main. Main's copy differs from the tip by a later 6-line edit only, and its body already records PR#131's merge into main at `2694d86`.

### docs/verification-summary-2026-08-09 — SEMANTICALLY_ABSORBED / DELETE_CANDIDATE
PR#70 is `CLOSED` with no merge, so this branch was never merged as such; its tip is not on main. Its content was nevertheless re-landed: PR#137's squash `b44fabbb` added `docs/verification/VERIFICATION_SUMMARY_2026-08-09.md`, and that file on main opens with `> ARCHIVED 2026-08-12 — 历史验证快照（2026-08-09），来源分支 docs/verification-summary-2026-08-09（git 对象无损保留）`. The only delta is the historical-name/archival header (main's copy is 11 870 B vs the branch's 11 525 B) and the outdated NO-GO conclusion, which the header explicitly supersedes. Baseline class `HISTORICAL_ARCHIVE_ONLY` is consistent with the content, but absorption is documented, so I classify it absorbed.

### feat/naming-package-identity — SEMANTICALLY_ABSORBED / DELETE_CANDIDATE
PR#131 `MERGED` → `2694d861` (ancestor of main, and also the merge-base of `chore/naming-repo-refs`); 17/17 changed files byte-identical between tip `12a2a5f6` and the squash. The delivered identity is still live on main: `pyproject.toml` → `name = "archeaxis-workspace"`, and `desktop/scripts/prepare_bundle.py:71` still globs `archeaxis_workspace-*.whl`.

### feat/naming-step3 — SEMANTICALLY_ABSORBED / DELETE_CANDIDATE
PR#136 is `CLOSED` with no merge, so the tip is not on main and its per-file blobs have since drifted. The *intent*, however, is verifiably live on main, and `docs/HANDOFF_2026-08-12_naming-migration.md` (on main) records that the naming migration was carried by PRs #131/#133/#137/#138 — the superseding sweep re-landed step 3's content rather than merging this branch. Checked against the three things the commit title claims: env vars → `shared/config.py` on main carries the `ARCHEAXIS_*` primary names with `COGNITIVE_*` aliases and the comment "Primary names use the ARCHEAXIS_* prefix (naming contract §4)"; API/Tauri identity → `desktop/src-tauri/tauri.conf.json` on main is `productName: "ArcheAxis Knowledge Recovery"`, `identifier: "com.archeaxis.workspace.recovery"`, and `desktop/src-tauri/src/protocol.rs` asserts `product == "ArcheAxis Knowledge"`; gate → `scripts/check_repository_conventions.py` on main implements `scan_naming_registry_bytes` and `scan_naming_forbidden_terms` against `docs/truth/NAMING_CONTRACT_V2.md`. Baseline class `CHECK_FOR_VALID_RESIDUAL`; I found no residual worth integrating.

### feat/naming-v2-contract — SEMANTICALLY_ABSORBED / DELETE_CANDIDATE
PR#137 `MERGED` → `b44fabbb` (ancestor); 15/15 changed files byte-identical between tip `b7234af4` and the squash. `docs/truth/NAMING_CONTRACT_V2.md` (6 306 B on main) is present and is named as the locked contract by the naming gate.

### fix/mfx001-marker-block — SEMANTICALLY_ABSORBED / DELETE_CANDIDATE
PR#128 `MERGED` → `a2056d04` (ancestor); both changed files (`app/ingestion/multi_format.py`, `tests/test_mfx001_supply_chain_ledger.py`) are byte-identical tip↔squash. The decision is still in force on main: `app/ingestion/multi_format.py:9` reads `PDF | markitdown → docling (marker-pdf REVIEW-BLOCK, excluded)`, with `_via_marker()` retained only as a non-default engine.

### release/v0.4.0-contract — RELEASE_HISTORY_ONLY / ESCALATE
Ahead=4, behind=1281, merge-base is `5369ae6c` itself. Two PRs merged from this branch: #21 `MERGED` → `5369ae6c` (ancestor of main) and #22 `MERGED` → `34936f13` (ancestor of main), and `34936f13`'s diff against its parent touches exactly `.github/workflows/release.yml` and `tests/test_release_manifest.py` — precisely the pair matching the branch commit `5f66f710` ("fix(release): bind published assets to checksum manifest"). The tip `75cb72ef` is a `merge main into release closure remediation` commit, so the tip's blobs for those two files are newer than either squash and legitimately differ from main today. Its purpose is the published `v0.4.0` asset/checksum contract (`releases` list contains `v0.4.0`, published 2026-07-30T16:27:19Z). Marked `ESCALATE` per the mandatory `release/*` rule.

## Not performed / limits

- **No remote branch, tag, release, or PR was created, deleted, renamed, pushed, force-pushed, or otherwise modified.** Every remote
  interaction was a read: `gh api repos/.../branches`, `gh api repos/.../compare/main...<branch>`, `gh api repos/.../pulls?state=all`,
  `gh api repos/.../releases`, and `gh pr view <n> --json ...`. No `git push`, `git branch -D`, or mutating REST call was issued.
- **No file in the working tree was modified except the one permitted report file.** The checkout already carried unrelated
  uncommitted modifications when I started (`git status --short` shows ~17 modified/untracked paths including
  `.github/workflows/nightly.yml`, several `crates/**` and `tests/**` files, and `docs/current/*`); I did not touch, stage, or revert
  any of them. My only workspace write is `docs/current/R5-BRANCH-DISPOSITION-20260918.md`, a path that did not exist on `main` or
  in the working tree before this task. All intermediate scratch files were written outside the repository, under
  `%TEMP%\r5-branch-audit\`.
- **`git fetch` was not attempted.** Per the task constraints it cannot work here; all remote reads went through `gh` GET requests.
- **Limits I could not fully close, and how I handled them:**
  - `codex/execution-reliability-standards` has **no PR** and no absorbing commit. I verified non-absorption by absence of its 8
    blobs from main's object database, but I did not attempt to judge whether its 7.8 KB/14 KB policy documents are still desired;
    disposition is `RETAIN`, never `DELETE_CANDIDATE`.
  - `codex/frozen-roadmap-deepseek-v1` has **no PR** and 118 files absent from main. I verified the file list is documentation/archive
    only and that no code/test/config path appears in it, but I did not open every one of the 137 files; disposition is `ESCALATE`.
  - `docs/verification-summary-2026-08-09`, `feat/naming-step3` and `release/v0.4.0-contract` were **closed unmerged**, so no
    absorbing commit contains their tip blobs. For these I relied on (a) the successor squash commits that did land, (b) the origin
    note written into main's own archived copy, and (c) live symbol checks in main. Absorption is documented for the first two; the
    third is preserved as release history.
  - `gh` returned `merge_commit_sha` for all 15 merged PRs and every one is an ancestor of `main`, but I could not fetch (network
    fetch is disabled here) to confirm whether any post-merge rewrite exists on the *remote*; I relied on the local object database,
    which already contains all 17 tips and all 15 merge commits, and `main` matches the requested base `44bd821`.
  - The compare endpoint returns at most 300 files per branch; the largest branch here changed 137 files, so no file list was
    truncated, and I confirmed the paginated form returns the same 137 rows plus an empty page.
- **Overlaps stated explicitly:** `codex/release-v0.6.9` (base `52f4c7ff`), `codex/post-release-v0.6.9` (base `de5b5ba6`) and
  `codex/v0.6.8-release-closure` (base `93e58a3b`) are a **chained** release sequence — each one's merge-base is the previous one's
  squash commit — so they are not independent and should be disposed of as a single release-history set. Likewise
  `feat/naming-package-identity` → `docs/intake-h2` → `chore/naming-repo-refs` form a chain (`2694d861` → `996462f5`), and
  `feat/naming-step3`/`feat/naming-v2-contract` share the merge-base `66c6aac2`. `codex/execution-reliability-standards` and
  `codex/frozen-roadmap-deepseek-v1` overlap in their `docs/taskpacks/*` post-audit/frozen-roadmap material.
- **Divergence from the in-repo baseline:** `docs/current/BRANCH-CONVERGENCE.json` classifies `codex/ci-release-optimization` and
  `codex/recovery-shell-closed-loop` as `DONOR_CAPABILITY_TO_REIMPLEMENT` and `codex/execution-reliability-standards` as
  `HISTORICAL_ARCHIVE_ONLY`. The first two are contradicted by their merged PRs (`headRefOid` = tip, squash ancestor of main,
  97/100 and 22/22 blobs identical); the third is contradicted by the absence of all 8 of its blobs from main. That file itself
  labels every row `latest_intent_verdict=PENDING_DETAILED_AUDIT` and its `limitations` field says semantic equivalence requires
  per-branch review — which is what this report supplies.

## 逐分支吸收详审（判据：与**自身 squash 提交**比对，2026-09-18）

### 方法更正

第一版详审把分支 tip 与**当前 main** 逐行比对，得出"多数分支有几百行独有内容、需保全"——**这是错的**：
压缩合并之后主线必然继续重构，把"主线已改名/重写的旧文本"算成"分支独有内容"。正确判据是
**把分支 tip 与它自己 PR 的 squash 提交（`merge_commit_sha`）比对**，那才是该分支内容真正落到主线时
产生的树；只有对没有合并 PR 的分支才退回与 main 比对。

### 结论一：13 个分支与自身吸收提交**零文件差异**

| 分支 | PR | squash |
|---|---|---|
| `chore/naming-repo-refs` | #132 | `04273c93` |
| `chore/placeholder-hygiene` | #129 | `98f7546b` |
| `codex/ci-release-optimization` | #140 | `93e58a3b` |
| `codex/post-release-v0.6.9` | #144 | `b3367958` |
| `codex/recovery-shell-closed-loop` | #142 | `52f4c7ff` |
| `codex/release-v0.6.9` | #143 | `de5b5ba6` |
| `codex/v0.6.8-release-closure` | #141 | `2d1186d9` |
| `docs/intake-h2` | #130 | `996462f5` |
| `docs/naming-handoff` | #134 | `66c6aac2` |
| `feat/naming-package-identity` | #131 | `2694d861` |
| `feat/naming-v2-contract` | #137 | `b44fabbb` |
| `fix/mfx001-marker-block` | #128 | `a2056d04` |
| `release/v0.4.0-contract` | #21 / **#22** | `5369ae6c` / `34936f13` |

`release/v0.4.0-contract` 的判法：它有两个合并 PR；其 tip 的 2 个差异文件与 **#22 的 squash
`34936f13` 逐字节相同**，故同样属"吸收完全"。→ 这 13 个分支删除不会丢任何内容。

### 结论二：另 4 个分支含主线没有的残留 → 已按收敛附包第 2 步入历史层

| 分支 | 情况 | 保全 |
|---|---|---|
| `codex/frozen-roadmap-deepseek-v1` | 无 PR；103 个路径主线从未有过（历史归档：imported-designs 抽取、planning 文档、source-documents） | **100 个文本文件**已保全；3 个二进制（2×docx、1×zip，约 264 KB）因文本编码规范**未复制**，仅在索引登记 SHA-256 |
| `feat/naming-step3` | PR#136 关闭未合并；13 个文件与 main 不同（命名迁移意图已由 #137/#138 落地） | **13 个文件**已保全 |
| `codex/execution-reliability-standards` | 无 PR；8 个文件，其中 3 个主线从未有过 | **8 个文件**已保全 |
| `docs/verification-summary-2026-08-09` | PR#70 关闭未合并；文档已由 #137 以新路径再落地，但版本不同（主线加了归档头） | **1 个文件**已保全 |

保全位置：`docs/history/remote-branch-assets/`（扁平化文件名 + `README.md` 索引，记录分支、tip 短 SHA、
原路径、**原始字节 SHA-256**、大小；并说明归档为逐字节保真、可能保留原行尾空白与 CRLF）。
共 **122 个文本文件**。

### 删除前置条件（**未执行**）

- **删除候选 = 结论一的 13 个分支**（逐条有"与自身 squash 零差异"证据）。
- **本执行器不得删除远端分支**（任务包 §13/§15 明令转 CODEX/HERMES），故此处只给清单与前置条件：
  1. 备份必须包含**全部对象**（尤其 4 个残留分支里那 3 个未入仓的二进制 blob）：
     `git bundle create <file> --all`，随后 `git bundle verify <file>`；
  2. 逐条删除并回读：`git push origin --delete <branch>`，再 `git ls-remote --heads origin` 核对计数（18 → 5）；
  3. 删除后重跑 exact-SHA CI 与 nightly，证据绑定新 SHA。
- 结论二的 4 个分支在人工确认残留无价值前**不得删除**。

### 复核命令

```powershell
# 某分支是否与自身吸收提交零差异（0 即完全吸收）
git diff --name-only 52f4c7ff "origin/codex/recovery-shell-closed-loop" | Measure-Object

# 某分支是否有主线从未有过的文件
git diff --name-only (git merge-base main "origin/codex/frozen-roadmap-deepseek-v1") "origin/codex/frozen-roadmap-deepseek-v1" |
  Where-Object { git cat-file -e "main:$_" 2>$null; $LASTEXITCODE -ne 0 }
```
