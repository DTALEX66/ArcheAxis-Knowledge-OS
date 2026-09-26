# AAOS 云端审计复核与目标增量记录（2026-09-23）

> **FROZEN AUDIT SNAPSHOT / NON-AUTHORITY.** This record preserves a review of a cloud repository snapshot and its proposed target increments. Any React/Tauri canonical-shell recommendation or UI priority in the source report was superseded by the September local project authority: C#/Avalonia is the formal desktop shell, Rust Core is the canonical writer, and React/Tauri is legacy recovery/behavior reference. Do not execute this document's proposals without rechecking the current R6/M0 authority chain.

## 记录性质

本文件把用户提供的《ArcheAxis 云端全量审计与前次架构结论复核报告》转化为 AAOS 当前项目的可执行目标增量。它不是云端全量审计的替代品，也不把报告中的云端文件树、未展开的 workflow、外部仓库或历史对话自动认定为当前事实。

- source: 用户粘贴附件 `C:\Users\ALEX\.codex\attachments\1135fb25-19a7-4786-b51f-c3fc5ea4ab98\已粘贴的文本.txt`
- source_sha256: `A11CAF0B48596FFD1CB227CB308AB430230043D98816F80BD5BF1D3BAF180FF9`
- reviewed_against_commit: `c1e426ad5842eaa6ba90b26c798c3d315f74183c`
- status: `ANALYZED / TARGET_ADDED / IMPLEMENTATION_NOT_STARTED`

## 复核结论

### 接受为架构方向

以下方向与 AAOS 当前 R6/M0 权威边界一致，加入后续目标：

1. ArcheAxis 继续作为 Knowledge–Evidence–Learning–Experience Authority，不新增第四套 Agent Runtime。
2. 外部项目和社区内容只能通过 Adapter/Receipt → Candidate 进入，不能直接写入 Active Knowledge。
3. Candidate 的正确路线是加固现有入口，而不是另建第二套 Candidate/Prompt Library。
4. Evidence、Validation、Promotion、Applicability、Expiry/Revalidation 必须成为可检查的系统不变量。
5. WORK-LAB、DESIGN-LAB、Beacon、Jev、GEP、AutoResearch 的角色必须保持边界：Receipt/Adapter/Evaluator/实验侧车，不能替代 AAOS Canonical Truth。
6. AutoResearch/RSI 不得获得 Self-Merge、Self-Deploy、Self-Declare-Truth 权限。

### 当前 checkout 的事实校正

报告引用的下列云端路径在当前 checkout 中不存在：

```text
src/aaos/candidate.py
src/aaos/components/candidate.py
knowledge-workspace/scripts/aaos_candidate_import.py
tests/test_candidate_import.py
tests/test_candidate_enrichment.py
tests/test_candidate_hash_identity.py
tests/test_aaos_candidate_import.py
```

当前 checkout 中可定位到的相关能力表面是：

```text
app/evidence/graph.py
app/evidence/relations.py
app/evidence/ledger.py
app/knowledge/promotion.py
app/agent/experience_harvest.py
shared-contracts/schemas/github_project_candidate.schema.json
shared-contracts/validators/validate_project_candidates.py
tests/test_evidence_graph.py
tests/test_research_to_knowledge_promotion.py
tests/test_knowledge_candidate_versioning.py
tests/test_machine_knowledge_candidates.py
```

因此，报告中“云端 main 存在 Candidate 源码/测试”的结论当前只登记为：
`CLOUD_MAIN_REPORTED / LOCAL_PATH_DRIFT_REQUIRES_RECONCILIATION`。
不能把它直接写成当前分支已经实现，也不能据此重复创建 Candidate Pipeline。

当前 `.github/workflows/` 确实存在 `ci.yml`、`nightly.yml`、`release.yml`、`vnext-ci.yml`，但本次只核对了目录元数据；workflow 权限、Action SHA、下载、Secrets、`pull_request_target` 和运行日志仍然是 `NOT_AUDITED`。

## 加入当前任务目标的后续队列

本队列排在当前前端 Candidate/staging 与 Local Green Owner Gate 之后；不改变 R6/M0 的 no-release、外置库和 Green 数据边界。

### P0-A — Canonical Object Model 逐文件复核

- 目标：以当前 checkout 为准，建立 Source、Candidate、Claim、Evidence、Artifact、Validation、Knowledge、Method、Skill、Experience、Experiment、Review、LearningState 的对象/字段/序列化/写入者矩阵。
- 首读范围：`app/`、`packages/contracts/`、`shared-contracts/`、`crates/`、`tests/`。
- 验收：每一项必须有文件与行号；重复事实源、legacy/vNext 重叠和未实现项分别标记；不只根据文件名下结论。
- 前置：只读；不修改 schema，不改数据库，不触碰外置库。

### P0-B — 现有 Candidate 入口加固

- 目标：审计并加固当前 `github_project_candidate`、Evidence/Research candidate 和 promotion 入口的 normalize、hash、dedup、provenance、license、quarantine 与路径/命令边界。
- 首读范围：`shared-contracts/schemas/github_project_candidate.schema.json`、`shared-contracts/validators/validate_project_candidates.py`、`app/agent/experience_harvest.py`、`app/knowledge/promotion.py` 及对应测试。
- 验收：外部输入不能绕过 Candidate；imported/reviewed/validated/active 语义不可混同；补充的每个 invariant 均有负例测试和真实命令证据。
- 明确禁止：不创建第二套 Prompt Library，不自动执行外部 Prompt，不把报告中的云端旧路径复制回当前仓库。

### P0-C — Evidence Graph 与 Provenance Replay

- 目标：核对 Source → Claim → Evidence → Validation → Promotion 的实际可追溯性，区分“Evidence 概念存在”和“完整 Graph 已实现”。
- 首读范围：`app/evidence/graph.py`、`app/evidence/relations.py`、`app/evidence/ledger.py`、`app/evidence/bundle.py`、`tests/test_evidence_graph.py`、`tests/test_evidence_bundle.py`、`tests/test_evidence_contract.py`。
- 验收：抽样对象可以读回 source identity/version、evidence/artifact、validation、review/promotion；断链必须标记 `TRACEABILITY_GAP`，不得用模型分数替代存在性检查。

### P0-D — Promotion State Machine 与 Experience 生命周期

- 目标：审计/补齐 `RAW → CANDIDATE → NORMALIZED → REVIEWED → EXPERIMENTAL → VALIDATED → ACTIVE → STALE/DEPRECATED/REJECTED/CONFLICTED/QUARANTINED` 的合法转换、不可变 receipt、适用条件和失效重验证。
- 首读范围：`app/knowledge/promotion.py`、`app/agent/experience_harvest.py`、`tests/test_research_to_knowledge_promotion.py`、`tests/test_knowledge_candidate_versioning.py`。
- 硬门禁：禁止 Candidate/Quarantined/未重验证 Stale 直接 Active；每次 promotion 要有 actor、policy、evidence、validation、timestamp、source commit。
- 前置：先完成 P0-A 的对象矩阵；不引入 GEP 作为 Canonical Model。

### P0-E — CI / 供应链与运行时下载审计

- 目标：只读审计 workflow、依赖锁、脚本和运行时下载/执行边界。
- 范围：`.github/workflows/*.yml`、`pyproject.toml`、`requirements*.txt`、`uv.lock`、`package*.json`、`scripts/`、Docker/Make 文件（若存在）。
- 检查项：Action 是否 SHA pin、最小 permissions、`pull_request_target`、动态下载执行、未 pin 依赖、`shell=True`/`os.system`、runtime install、SBOM/checksum、Secrets exposure。
- 验收：每个结论有文件/行号；未读日志/规则/Secrets 元数据保持 `NOT_AUDITED`，不宣称 CI 安全。

### P0-F — 跨项目 Receipt Boundary

- 目标：确认 WORK-LAB/DESIGN-LAB/Beacon 的输出只能形成 Receipt/Candidate，不得直接写 AAOS Active Knowledge。
- 前置：用户明确授权对应外部仓库的精确只读路径和范围；当前不扫描外置共享库、真实资料库或私有会话。
- 验收：形成跨仓调用路径、权限边界、exchange schema、receipt 位置和绕过 Candidate 的负例；不创建共享数据库或自由写 Memory。

### P1 — 受治理 Adapter 与实验侧车

只有 P0 治理链通过后，才评估 Prompts.chat Source Adapter、GEP Experience Adapter、Beacon Receipt Adapter、Jev Evaluation Sidecar、Experiment Registry、AutoResearch Sandbox 和 Evidence-aware Retrieval。

### P2 — 优化项

Experience ranking、adaptive retrieval、冲突建议、实验调度和受控 knowledge evolution candidate 只能在 P0/P1 稳定后进入；Controlled RSI 继续后置，不进入生产治理路径。

## 访问与交付边界

- 本记录不授权访问 E/F 盘、`.codex/.zcode/.hermes`、凭据、浏览器状态、Green 数据或真实资料库。
- 外置资源只按 `docs/SHARED_RESOURCE_PATH_INDEX.md` 定位；不复制共享库到本项目。
- 本轮不实施上述 P0/P1/P2，只把经过复核的任务加入当前目标队列。
- 前端当前优先级不被本审计替换；云端审计治理任务在前端 staging/Green Owner Gate 之后执行。


## Follow-up — 2026-09-25 second cloud-audit crosswalk against current authority

- Source fingerprint: user-pasted `ArcheAxis 云端全量审计：主线、分支、权威文档、前端可视化、上下文连续性与后续治理` snapshot, SHA-256 `0D4E3826D4F5000E71FCC9BAE584947D5028842C5FFEAFA3F07E2A7B23AA0FE4`. Its cloud observations date to 2026-09-24 and are not current local/remote state.
- Authority correction: the source's recommendation for a canonical React/Tauri single shell (including its P0 shell-migration checklist and final conclusion) conflicts with current `AGENTS.md` §6, `docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md` and the R6/M0 baseline. Freeze that proposal as historical input; the formal product desktop remains C#/Avalonia, Rust Core remains the canonical writer, Python remains isolated workers, and React/Tauri remains legacy Green recovery/behavior reference. No React/Tauri migration is authorized by this audit.
- Reconciled usable work: the source's generic frontend-evidence and accessibility concerns are represented by `docs/superpowers/plans/2026-09-24-aaos-commercial-frontend-completion.md` Tasks 1–8 and live R6 receipts; context/unfinished-work continuity is represented by the R6 `EXECUTOR-START.md`, `TASKPACK.md`, `docs/current/R6-EXECUTION.md` and `R6-STATE.json`; dependency locations are governed by `docs/SHARED_RESOURCE_PATH_INDEX.md`. Do not create a competing task ledger, frontend authority, or dependency registry from the cloud snapshot.
- Current local branch readback: `codex/aaos-p3-ui-convergence-20260922`, HEAD `a5de4b13474c217e7a9dd34b8cbfa402e8297780`, tree `a4156ed65d50675822321b9d63eec932b1e76af3`; R6 remains `IN_PROGRESS`, release remains `FROZEN`, and 70 tracked paths remain modified. These are live local facts from this reconciliation pass, not cloud facts.
- Branch disposition: 32 local branches and 4 worktrees remain. Only the current feature branch, local `main`, and `codex/worker-quality-0906` have tips contained in the current feature tip; the latter is still attached to a dirty worktree. The other tips have not been proven mergeable/redundant. A fresh `git ls-remote --heads origin` failed because this host could not read SSH `known_hosts`; the current remote state is therefore `UNKNOWN` despite a prior AAOS-9.21 readback that reported the branch synchronized at this SHA. No branch was merged, deleted, or moved.
- Spill disposition: the previous metadata-only snapshot counted 995 untracked files, 989 under `docs/history/`, plus mixed project-local runtime artifacts. Path names/extensions do not establish ownership or safe retention. No historical payload or browser-profile-shaped path was opened, migrated, or deleted; per-path provenance and cleanup eligibility remain `UNKNOWN`.
- Frontend evidence added this pass: the HEAD-bound candidate was reverified against the exact commit/tree with runtime, workers and provenance required (`ok=true`, 21,474 files, no problems). Its Desktop and Core started against a fresh `.project-local` synthetic workspace and exited cleanly. Windows process metadata showed a visible titled window, but the supported Sky `list_apps`/`list_windows` inventory did not expose it, so no menu, keyboard, pointer, screenshot or accessibility interaction was executed. This candidate represents committed HEAD only and does not include the 70 modified paths; it is not a dirty-tree Candidate or Green installation.
- Remaining authoritative work: Task 5's Core contracts, Task 6's native interaction/accessibility/responsive acceptance, Task 8's exact dirty-tree Candidate, P3/Mastery closure, A02/A16 owner decisions, A13 real Legacy semantics, A14 real-model loop, and path-level branch/data provenance remain open. This crosswalk changes no R6 task status and does not claim M0 readiness.

## Follow-up correction — live origin branch readback, 2026-09-25

The preceding paragraph recorded remote state as UNKNOWN after a default SSH `known_hosts` failure. A later read-only `git ls-remote --heads origin` succeeded with a one-shot SSH host-key option; no SSH config or credential file was changed. The live readback supersedes only that remote-UNKNOWN statement:

- Origin exposed 19 branch heads; the local repository has 32 branch names. Thirteen same-name local/remote refs had identical SHAs, including the active `codex/aaos-p3-ui-convergence-20260922` at `a5de4b13474c217e7a9dd34b8cbfa402e8297780`.
- Six remote-only names were `chore/placeholder-hygiene`, `docs/intake-h2`, `docs/naming-handoff`, `feat/naming-package-identity`, `feat/naming-v2-contract`, and `fix/mfx001-marker-block`. Each remote tip is already patch-equivalent to the current branch (`git cherry` reported zero new patches and one equivalent patch). Patch equivalence does not establish PR disposition, branch ownership, or safe remote deletion.
- Nineteen local-only names remain as listed in the lineage table. Across all 32 local tips, three are ancestors of the current tip (`current`, `main`, `codex/worker-quality-0906`); `audit/r5-independent-audit-20260919` contributes no new patch but its cached upstream is absent from the live heads; the other 28 have at least one patch not in the current branch.
- No branch was merged, deleted, moved, or rewritten. Dirty registered worktrees and unknown branch owners remain preserved. Remote readback resolves branch-tip visibility only; PRs, owners, and cleanup authorization remain open.

## Open-work matrix — current audit disposition (2026-09-25)

This is a live follow-up to the pasted audit, subordinate to R6/M0. It records what remains after current-source and Git readback; it does not change any R6 acceptance status.

| Area | Current evidence / aligned state | Still open | Disposition |
| --- | --- | --- | --- |
| Product language and shell | `LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md` is coherent with `AGENTS.md` and R6: Avalonia/C# desktop, Rust sole vNext writer, isolated Python workers; React/Tauri legacy Green reference. | A13 real legacy-data migration and R6 runtime/Green qualification are partial; directory movement is not migration. | Keep old React/Tauri proposals frozen. No language rewrite or data movement. |
| Frontend, highest priority | Tasks 1–4 source/build slices are marked complete; source-bound synthetic Learning UIA/restart path is evidenced; 16-route UIA route smoke and several visual captures exist. | Task 5 Research/Plugin/Model readiness, Editor writes, graph and Evidence bundle/citation require canonical versioned Core contracts. Task 6 menu/input, complete screenshots, viewport/DPI, IME, assistive technology, contrast are open. Task 7 M0 P3 remains PARTIAL/Mastery `closed=false`. Task 8 exact dirty-tree Candidate, affected full suites, staged Golden Journey and owner-review package remain open. | Continue code/source contracts only where current authority and Core truth suffice. Do not fake unavailable contracts. Native input delivery previously returned NOT_EXECUTED; committed-HEAD Candidate launch is not dirty-tree Candidate evidence. |
| Branch audit / integration | Live origin readback: 19 remote heads, 32 local names; all 13 same-name SHAs match. No ref changed. | 19 local-only refs, 6 remote-only refs and unique patches/owners/PR disposition need mapping. Three local tips are ancestors; one R5 audit branch is patch-equivalent but has stale cached upstream; 28 branches contain new patches. Dirty auxiliary worktrees need owner/recovery receipts. | No merge, delete, rename, worktree cleanup or remote mutation absent exact owner decisions. |
| Repository rules / history | Current authority indexes point to R6/M0 and label old G0/React/Tauri plans as superseded; language responsibilities match implementation targets. | Root-level superseded documents and imported historical files still need reference/hash manifest and compatibility-link audit before physical moves. Untracked `docs/history/**` provenance and inclusion intent are unknown. | Historical items remain preserved/frozen; do not infer active work from old TaskPacks or move files based on date/name. |
| External/spill data | Path index distinguishes shared model library, Green install and real Green material library; no external root or browser-state contents were read. Metadata counts exist for `.project-local/`. | 995 untracked records in the earlier metadata snapshot (989 under `docs/history/`); exact origin/generator/owner, hash/bytes, consumer, retention, and cleanup eligibility remain unknown. A browser-profile-shaped subtree under task artifacts is unresolved sensitive state. | Keep unresolved. No content inspection of that subtree, no copy/migration/deletion, and no access to Green/shared data without an exact authorized scope. |
| R6 overall | `R6-STATE.json`: `IN_PROGRESS`; release `FROZEN`; A00/A01/A03 tested local, most A04–A15 partial; A02 and A16 owner-blocked. | A04–A15 evidence/acceptance gaps, especially A08 Mastery/adaptive learning, A13 real migration, A14 real-model loop, A15 qualification, plus A02/A16 owner decisions. | R6 stays in progress; release/Green transition stays frozen. Synthetic/local evidence is not real-user, exact-SHA-CI, installed, or owner approval evidence. |

Immediate safe next sequence: (1) finish frontend contracts and native acceptance that current authorities define; (2) build/test a Candidate from the exact current working tree and produce its review receipt; (3) prepare per-branch unique-path and per-untracked-path manifests without touching owners' state; (4) seek only the specific A02/A16 and cleanup/migration decisions that cannot be derived from current authority. Current authority gives no basis to invent those decisions.

### Candidate binding constraint confirmed from current build scripts

Task 8 cannot be closed by rebuilding the committed-HEAD Candidate: 70 tracked paths are modified and the Candidate plan's local receipts include new, untracked frontend/API files. `scripts/release/build_candidate.py` rejects tracked dirt unless `--allow-dirty`, while its provenance still binds a commit; `scripts/release/assemble_green_candidate.py` records a commit and Git tree but does not independently hash a dirty working tree. Therefore an `--allow-dirty` bundle bound only to HEAD would misstate source identity. No commit is authorized by the current instruction/project grant, and no Git index/branch mutation was attempted. The exact-current-source Candidate remains BLOCKED until task-owned changes have an authorized immutable source identity and are rebuilt; the existing HEAD Candidate is valid only for committed HEAD.

### Remote recheck and expanded local branch/path readback — 2026-09-25

A new `git ls-remote --heads origin` attempt failed before listing refs: SSH could not add the host to the configured known-hosts path and GitHub returned `Permission denied (publickey)`. No credentials/configuration were changed. The successful origin readback recorded above remains the last successful remote snapshot; current origin tip/PR state is now `UNVERIFIED`, not refreshed.

Current local-only graph calculation (current feature tip `a5de4b13474c217e7a9dd34b8cbfa402e8297780`): three refs are ancestors when including the checked-out ref (`main` and `codex/worker-quality-0906` are the other ancestor refs); `audit/r5-independent-audit-20260919` is one commit ahead with one patch-equivalent path change; the other 28 non-current refs have new commits/patches. Their divergence ranges from one to 1,793 commits in the recorded local graph, so branch names or age cannot establish safe merge/delete disposition. The worker-quality ref still has a registered dirty worktree. No merge, delete, fetch, prune, checkout or worktree movement occurred.

## Live reconciliation — 2026-09-26

This section supersedes the 2026-09-25 branch-count and dirty-Candidate statements above where current readback now differs. It does not promote R6/M0 status.

| Area | Current readback | Disposition |
| --- | --- | --- |
| Local Git | Active branch `codex/aaos-p3-ui-convergence-20260922`, HEAD `2994efa08d3e4f6ea561831fd4088d6d1b290cdd`, tree `4fc581e7dcde90a30d8e9019f26fdf362bfa5cc9`; 28 local heads and 5 registered worktrees. Latest tracked-only status readback reports 102 changed entries; root status still warns `p-w7n3ehdf/ Permission denied`, so full visible-path counts/custody remain incomplete. | Preserve dirty/unreadable worktrees. Batch semantic review covers 52 SHAs, not all 28 local heads; remaining branches still need authority-based semantic audit before merge/disposition. No local branch or worktree was deleted. |
| Remote GitHub | Direct read-only `git ls-remote --heads origin` on 2026-09-26 returned 7 heads: active branch `a5de4b13474c217e7a9dd34b8cbfa402e8297780`, `codex/execution-reliability-standards`, `codex/frozen-roadmap-deepseek-v1`, `docs/verification-summary-2026-08-09`, `feat/naming-step3`, `main=e3875db0ee6d073d37839eb7b95f7ef4ce881bbb`, and `release/v0.4.0-contract`. Local HEAD remains 7 commits ahead of the remote active tip (`git rev-list --left-right --count <remote-tip>...HEAD` = `0 7`). GitHub exact-head lookup confirms PR #70 (docs summary) and #136 (naming) closed unmerged; PRs #21/#22 on `release/v0.4.0-contract` closed merged, with #22 head equal to the live tip. Exact-head searches found no PR match for active, execution-reliability, or frozen-roadmap branches. Receipt: `.project-local/runs/aaos-ui-current-candidate-20260926/remote-heads-live-20260926.json`; query states are in `AAOS-BRANCH-DISPOSITION-REVIEW-20260925.json`. | Current active dirty changes are not published; `main` and the active remote ref were untouched. The release branch remains retained under its explicit `merge_delete_authorized=false` history disposition; no PR status by itself grants deletion authority. |
| Remote branch cleanup | Twelve branches were matched to exact closed-and-merged PR heads: `chore/naming-repo-refs` (#132), `chore/placeholder-hygiene` (#129), `codex/ci-release-optimization` (#140), `codex/post-release-v0.6.9` (#144), `codex/recovery-shell-closed-loop` (#142), `codex/release-v0.6.9` (#143), `codex/v0.6.8-release-closure` (#141), `docs/intake-h2` (#130), `docs/naming-handoff` (#134), `feat/naming-package-identity` (#131), `feat/naming-v2-contract` (#137), `fix/mfx001-marker-block` (#128). | Owner ran `.project-local/cleanup-merged-remote-branches.ps1` through the authenticated SSH user session; expected-tip deletion was verified for all 12, with all other refs preserved. The earlier `gh` HTTP 401 was a failed attempt only and is superseded. Cleanup receipt `.project-local/runs/aaos-ui-current-candidate-20260926/remote-cleanup-verified.json`; current 7-head readback is in `remote-heads-live-20260926.json`. Preserve the seven remaining refs above, including `feat/naming-step3` (#136 closed unmerged), `docs/verification-summary-2026-08-09` (#70 closed unmerged), the active branch, no-PR governance/frozen branch, and `release/v0.4.0-contract`. |
| DSH/DP integration | `5bb89aa7` records the NF integration. NF02–NF07 delivery blobs and DP-F01 patch-equivalent changes match current HEAD; NF01 reports are present with an intentional correction. DP-GIT-01, DP-A11 and DP-GIT-02 report artifacts also match. | No NF/F01 package suites were rerun in this live audit. This does not equal remote publication, CI verification or promotion of R6 tasks. The P6 current13 `--require-current-source` invocation was executed and failed with a source-snapshot mismatch; its `NOT_EXECUTED` label was corrected, cause still unproven. |
| Current-source Candidate | Candidate `current-2994efa-final-20260926` binds base commit/tree plus source snapshot `52313a6d94df685e85e4e5cb66eb1884d71982285a55078e42737d2d3c743a6b` (1,541 included, 8 untracked build inputs, 9 path-only exclusions). Required runtime/workers/provenance/current-source verifier readback now returns `ok=true`, 18,246 files, no problems. | Candidate and headless smoke remain local/synthetic evidence. Native UI matrix, Mastery closure and Owner gates remain open; it is not installed Green or a release. |
| Authority/report drift | `CURRENT_STATE_TRUTH.md` identifies itself as a historical 2026-08-09 snapshot; configuration/documentation authority rows were corrected to point live status at R6/M0. The Research revision premise was corrected: `transforms.source_id` joins to canonical `sources.sha256`; remaining gap is the formal Research projection's provider/version/quality/error contract and runtime proof. | Old dated paragraphs are retained as history; their superseding correction is explicit. |
| External/spill paths | Latest accessible path-only Git enumeration reports 306 current untracked non-sensitive paths, 707 excluded sensitive path components not opened, and a root enumeration warning for `p-w7n3ehdf/`. Compared with the safe scope of the 2026-09-25 manifest (291 paths after excluding the session-path entry), there are 15 new safe paths and 0 missing prior paths. The 284 listed `docs/history/` file hashes were re-read and all match their prior SHA-256 values. | All hashes are current, but owner/generator remain unresolved, consumer search is partial, and AX-DIR-010 remains `SCHEMA ONLY / NO MOVE OR DELETE AUTHORISED`. No safe migration/deletion count is established; no path moved or deleted. Sensitive paths remain unopened. |

The working-tree repository convention checker previously passed with zero worktree issues after the targeted normalization; index/HEAD still carry one trailing-whitespace finding in the UI coverage document until the existing working-tree fix is committed. Current R6/M0 statuses remain unchanged: A02/A16 owner-blocked, A12/A13 partial, release frozen, product not ready for Green replacement.


## 2026-09-26 user-session SSH cleanup readback

The owner executed `.project-local/cleanup-merged-remote-branches.ps1` using the authenticated user SSH session. The 12 exact-tip, previously merged branches listed in the cleanup row above were deleted atomically with expected-tip leases. The earlier HTTP 401 receipt remains historical evidence of the failed attempt, not the current deletion status.

Independent comparison of the owner's before/after `git ls-remote --heads` exports confirms 19 -> 7 heads, exactly those 12 names absent, and all seven retained tips unchanged. Evidence: `.project-local/runs/aaos-ui-current-candidate-20260926/remote-cleanup-verified.json`; before export SHA-256 `334555f3de1d895d1c0beb7a476a5a1ff383e6c5782404827da1705bf6dbce5f`; after export SHA-256 `bc0612c5c35cc013147592ada055cfc4cf7fc6984ca0935ceb0bb473b7936811`.

Status: **PASS for this 12-branch cleanup only**, based on user-executed SSH and exported remote readback, not direct authenticated Codex API access. Main, active development, execution-reliability, frozen-roadmap, verification-summary, naming-step3 and v0.4.0-contract remain. This does not prove all branch governance, local integration publication, frontend acceptance or data migration complete.
### Live branch and spill recheck — 2026-09-26

#### Current Git/DSH branch readback

- Local repository currently has 28 branch refs and 5 registered worktrees. The current active branch is `codex/aaos-p3-ui-convergence-20260922` at `2994efa08d3e4f6ea561831fd4088d6d1b290cdd`, tree `4fc581e7dcde90a30d8e9019f26fdf362bfa5cc9`. Its live GitHub tip is `a5de4b13474c217e7a9dd34b8cbfa402e8297780`; local is 7 commits ahead and 0 behind. No push or merge occurred.
- Approved read-only `git ls-remote --heads origin` returned seven current heads: active AAOS, `codex/execution-reliability-standards`, `codex/frozen-roadmap-deepseek-v1`, `docs/verification-summary-2026-08-09`, `feat/naming-step3`, `main`, and `release/v0.4.0-contract`. All seven have local tracking refs; only active AAOS differs in tip. The 19 cached `origin/*` branch refs include 12 refs absent from this live response; cached refs are not live-cloud evidence.
- Existing `AAOS-BRANCH-DISPOSITION-REVIEW-20260925.json` covers 27 of the 28 current local branches; it omits `codex/dp-f01-20260925` and its active-branch tip is stale. `git cherry -v HEAD codex/dp-f01-20260925` marks both DSH commits (`56a76411624e450f2ecf50afdca070babe983cef`, `793e06ee040dcdb0248e2bbb322b44084620cf17`) patch-equivalent to current HEAD. The DP-F01 worktree is still registered and its Git status shows no tracked/untracked changes, but status emits `could not open directory ... Permission denied`; preserve its checkout/ref until custody/readability is resolved. Patch equivalence is not exact-commit ancestry or permission to remove the worktree.
- DSH DP-NF integration remains recorded by commit `5bb89aa7` and handoff artifacts. Current integrated-tree reruns passed `tests/workers/test_p1_quality_matrix.py` (11 passed) and `cargo test -p archeaxis-domain --test machine_loop_restart` (1 passed); the other DP-NF task suites were not rerun. No branch deletion, local worktree removal, push or merge was performed in this follow-up.

#### Spill-data metadata refresh

- Rechecked only the eight non-history paths named in the 2026-09-25 lineage manifest. All eight still exist. Seven non-session files were rehashed and all seven differ from their 2026-09-25 snapshot hashes (two code/assets, one Core test and four current audit/intake reports); the eighth, `docs/current/SESSION-RESTART-2026-09-12.md`, was stat-checked only and its body/hash was not read. Receipt: `.project-local/runs/aaos-ui-current-candidate-20260926/spill-eight-path-recheck.json`.
- At that readback time the 284 `docs/history/` entries had not been rehashed. The 705 profile/web-chain-debug exclusions remained unopened; `.project-local` and external-root ownership/consumer lineage were still partial/unknown. AX-DIR-010 remained pending; no move, cleanup or deletion was justified by that readback.

Overall branch disposition, external-data lineage and repository cleanup remain PARTIAL. The active branch's dirty files and unreadable worktree content were preserved.
#### Semantic review of remaining branch families

- A fresh local semantic pass covered nine donor refs; a second pass covered thirteen historical, naming, compatibility, PDF/annotation, recovery and release refs. The exact branch names and current tips are retained in the adjacent live-readback section of `AAOS-BRANCH-DISPOSITION-REVIEW-20260925.json`; all 28 current local heads now have a disposition row, and five additional report rows are historical refs no longer local. The active row's old snapshot tip remains historical; current active SHA is in `live_readback_20260926`.
- No whole-branch port is justified. Research/Source/Evidence units and immutable-ledger semantics still need current Core contract review; H2 bakeoff has no current quality benchmark; legacy Web/Tauri donor commits conflict with the Avalonia/Rust-writer authority; portable-root and Recovery donor behavior is not equivalent to complete formal Avalonia acceptance. AXW022A backend intent is present but PDF reader UI remains missing; AXW022B has anchor APIs but native annotation-to-source return is unverified. Frozen-roadmap donor contains 149 commits and 137 paths, including 113 historical/planning paths still needing content/provenance review. v0.4.0 checksum intent remains frozen; execution and historic test transition are unverified.
- Across both passes, owners/custody are UNKNOWN and the register continues to set `merge_delete_authorized=false`. Unique historical commits or a present-day same-path file do not establish behavioral equivalence or deletion eligibility. Preserve donor refs/worktrees until custody and the exact consumer/path review is complete.
- The live query showed the current local active branch 7 commits ahead of GitHub; this is not a clean publish unit because the worktree has substantial pre-existing modifications and inaccessible directories. No commit, push, local branch cleanup or merge was attempted in that follow-up. GitHub branch-head visibility is verified; PR disposition was still open at that readback and is refreshed below.

#### Latest direct branch and spill-data readback — 2026-09-26 03:56 UTC

- Current read-only GitHub SSH readback returns exactly seven heads; the 12 branches deleted by the owner are absent and all seven remaining tip SHAs match the cleanup receipt. GitHub connector exact-head query plus `fetch_pr` confirms #70 and #136 closed unmerged; #21 and #22 closed merged; #22 head equals `release/v0.4.0-contract`. No exact-head PR match was returned for the active, execution-reliability, or frozen-roadmap branches. The release ref remains preserved because its machine disposition is `HISTORICAL_RELEASE_OR_ROADMAP_FREEZE_RETAIN_EVIDENCE` and `merge_delete_authorized=false`, despite merged PR state. Current refs and PR states are recorded in the live branch disposition JSON and `.project-local/runs/aaos-ui-current-candidate-20260926/remote-heads-live-20260926.json`.
- Recomputed SHA-256 for all 284 exact `docs/history/` entries without decoding or emitting contents: 284/284 match, none missing or changed. `AAOS-HISTORY-PATH-DISPOSITION-20260926.json` now records `hash_current_verified=true` for each verified entry and records `current_hash_readback_20260926`; `frozen_snapshot=false`, owner/generator unresolved, and all move/delete gates remain blocked.
- Compared visible `git ls-files --others --exclude-standard` paths to the safe path set from the 2026-09-25 manifest, excluding path components containing `profile`, `web-chain-debug`, or `session` without opening them. Current accessible set: 306; prior safe set: 291; 15 additions and 0 disappeared prior paths. The 15 additions are individually SHA-256 recorded as `UNRESOLVED_PRESERVE` in `.project-local/runs/aaos-ui-current-candidate-20260926/external-lineage-readback-20260926.json`. Root status still reports `p-w7n3ehdf/ Permission denied`, so inventory is limited to accessible Git output and does not claim full-tree completeness.
- The new path/hash receipt improves traceability only. It does not identify owners, generators, dynamic consumers, migration targets or rollback routes. `AX-DIR-010` still forbids movement/deletion without a frozen tree, exact ownership and consumer records, readback and per-path authorization. No path moved or deleted.
