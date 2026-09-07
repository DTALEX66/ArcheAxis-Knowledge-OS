# 2026-09-07 Full Loop execution (AAK-REUSE-FIRST-20260907-R2)

This ledger is the live execution state for the REUSE-FIRST taskpack. It was
re-encoded to strict UTF-8 after the independent GPT audit (C01). Historical
per-slice detail lives in the git commits referenced below; audit record:
`Q00-Q01-AUDIT-2026-09-07.md`. Do not treat frozen `TASKS.json` TODO states as
completion; current status is this file.

## Plan and package identity

- Package: ARCHEAXIS-REUSE-FIRST-FULL-TASKPACK-2026-09-07 (R2), 15 files,
  MANIFEST hash-verified; TASKPACK.md sha256 `a9093a72...`; audit base
  `4ca46eaf...` (= origin/main). Frozen plan: docs/authority/taskpack-0907/
  TASKS.json (`plan_only`, 23 tasks X00-X14, Q00/Q01, F01-F06).
- Decisions D01-D16 recorded as SUP-012..SUP-016 in
  DECISION_SUPERSESSION_LEDGER.yaml.

## Repository state

- Branch `codex/full-loop-0906`; work pushed to origin at `74720bf6c7...`
  (33 commits ahead of the intake baseline `2daf8d7c`; same-name remote ref).
  `main` untouched at `4ca46eaf...`. Working tree clean unless noted.
- Baselines at `74720bf` + audit follow-ups: full `cargo test --workspace
  --locked --offline` green; full Python suite 2393 passed / 7 skipped / 1
  failure = sandbox child-egress TLS restriction on a real-URL test (not code).

## Independent GPT audit (Q00/Q01, 2026-09-07)

Verdict: Q00 not passed; Q01 pre-audited, conditions not met. Findings
C01-C10 assigned back to the original X tasks; recommended single queue
C01 -> C02 -> C03 -> C04 -> C07 -> C08 -> C05 -> C06 -> C10 -> C09.
G01-G14 conclusions and fix criteria: see `Q00-Q01-AUDIT-2026-09-07.md`.

### C-item status board (updated as fixes land)

| Item | Fix status | Notes |
| --- | --- | --- |
| C01 entry/encoding | DONE | AGENTS/indexes point to R2 + live ledger + audit board; ledger/audit/X14 re-encoded strict UTF-8 |
| C02 server-side identity | PARTIAL | launch middleware overwrites actor header from session claim; machine restricted in create/review/learning (unit tests green); real-process escalation scenario pending |
| C03 review txn + revisions + anchors | PARTIAL | knowledge::review is one transaction (status+event commit/rollback together; modified creates candidate AND records event); supersedes relations & bidirectional anchors open |
| C04 migration semantics/idempotency | PARTIAL | demo staging: legal PERSONAL_DEFINITION type, manifest hash+row verify before write, single atomic staging tx, inserted/reused counts, legacy-row id preserved; tamper rejected (tests); broader type map open |
| C05 learning schedule/contract | OPEN | reuse FSRS adapter; event contract; idempotent; absolute due |
| C06 knowledge qualification in consumers | OPEN | wire active check into context/get/results |
| C07 same pipeline converters + public check | OPEN | controlled capability registry; one product path |
| C08 host + Windows candidate | PARTIAL | DeepTutor host unblocked headless: settings catalog API configured local ollama (qwen3:8b), doctor --online PASS incl real model response; shell/UI + Windows candidate open |
| C09 same-commit qualification + locked CI | PARTIAL | vNext CI cargo test now --locked; reproducible probe receipts + candidate-hash gate open |
| C10 cleanup terminal state + growth-stop | PARTIAL | same-tool terminal census 57.241 GiB (805,837 files, 129 pre-existing errors) recorded + D: free ~240.7 GiB; growth-stop entrypoint checks partly covered by dev.py tests; ASR legacy model-dir read fallback still open |

## Slices landed before this re-encode (commit -> evidence)

- `976eea7` X00 intake + decisions (SUP-012..016), EXECUTION ledgers.
- `fd5182c`,`31b028c` X01 run-root doc + dev.py run evidence (14 passed,
  run be268a2d33/ea458cee118a).
- `bfb2c37` X01 real screenshot->OCR eng (run 26510ae2b9d6); CI wiring audit.
- `76a3680` X02 wave-1 ledger (8 vNext workers, X02-REUSE-LEDGER.md).
- `f5cfa5b` X02 wave-2 (6 learning/knowledge donors).
- `d2f6516`,`637daa3`,`079da71`,`6b30203` X03 DeepTutor probes: local notebook
  ASCII ok; Chinese-import gap; LLM config interactive-bound (BLOCKED).
- `76f59a6`,`08debe0` X04 worker_quality dual-schema alignment (37 passed).
- `cecf4b8` worker CLI stdout UTF-8 hardening (full cargo green).
- `18f5c06` X04 identity analysis; X06 OCR engine tests real (run
  ce16a8410c76).
- `30ca5f4` X04 API actor guard (machine candidate-only; tests
  knowledge_actor_guard.rs). Audit C02 requires replacing body actor with a
  trusted principal - tracked above.
- `968c479`,`a2dbef5`,`3fdd32b` X05 provenance: source_origins table/domain,
  HTTP origin metadata, archive EXPORT_TABLES + round-trip test.
- `f803bfe` X06 chi_sim real OCR.
- `2bccf90` X06 PDF/Office reconfirmed (10 passed, run 718c063f8a0e).
- `cd450ae` X10 demo semantic staging + loss ledger (stage_demo.rs, 4 tests).
- `80bfed6` X10 migration recon; full cargo workspace green.
- `040e9a3` X08 minimal human review-event side (learning.rs + API + tests).
- `b4f37b9` X09 knowledge active-qualification gate (test knowledge_active.rs).
- `65519ec` X11 supervisor harness real journey green (C#->Core->Python->DB).
- `acdaa1c`,`24b8f7d`,`74720bf` baseline/status records.
- X14: census 66.625 GiB; wave-1 deletion -10.77 GiB; wave-2 (root target)
  -6.03 GiB; manifests under .project-local/inventory/x14-wave1|2;
  summary tracked in X14-CLEANUP-MANIFEST-PREP.md. No .hermes deletion.

## Per-task final status (2026-09-07 pre-fix)

X00 VERIFIED. X01/X02/X04/X05/X06/X08/X09/X10/X11/X14 PARTIAL with real
slices. X03/X07 BLOCKED (config-surface / egress) with evidence. F01-F06
DEFERRED_RETAINED. Q00/Q01 = audit above (not passed).

## Boundaries and rollback

- No E-drive access, no private .hermes reads/writes, no real-library content,
  no release/tag/version, no main merge. Deletions limited to recorded
  rebuildable caches.
- Rollback per commit (one checkpoint each); run evidence private under
  .project-local/runs|inventory (not uploaded).

## X03 slice E (overnight, 2026-09-07/08): DeepTutor local host UNBLOCKED

Earlier X03 was locked because the provider config surface looked
interactive-only. Discovered and used a programmatic path: `deeptutor serve`
(FastAPI, 127.0.0.1:3782) exposes settings catalog endpoints without auth in
single-user mode. PUT /api/v1/settings/catalog with a local-ollama profile
(binding openai, base_url http://127.0.0.1:11434/v1, model qwen3:8b) succeeded;
`deeptutor doctor --online` then PASSED every check including "Provider
response: the model returned a response" (exit 0). Conclusion: the DeepTutor
backend with a local model is usable headlessly on this host; the default-host
blocker is resolved for API/CLI use; only the interactive web UI build and
Windows candidate packaging remain (C08). Evidence config lives in the iso
workspace .project-local/deeptutor-val/data/user/settings/model_catalog.json
(ignored, not uploaded; contains no real secrets - dummy key).

## X03 slice F (overnight): Chinese round-trip OK via API + real model summary

DeepTutor notebook API on the local host: create notebook (a50e1cfa) + add_record
with Chinese title/output -> read back EXACT bytes (0 U+FFFD). The earlier
Chinese corruption was confined to the CLI file-reading path; the JSON/API path
preserves UTF-8. add_record also auto-generated an English summary - a REAL
local-model call (qwen3:8b) that succeeded. Conclusion: upstream Chinese
content round-trip is available through the API; X12/Obsidian interop should
use API/JSON, not the CLI md reader. Default-host candidate: DeepTutor local
backend (web UI still to build/run headless if needed).

## X03 slice G (overnight): question record + local-model summary persisted

add_record(record_type=question, Chinese query) on notebook a50e1cfa returned 200
and stored record c87158d0; stored bytes verified EXACT (0 U+FFFD, substring
checks true). The record pipeline auto-generated a summary via the local model
(qwen3:8b) - a second real model call succeeding on the product flow.

## X03 slice H (overnight): chat API surface note

openapi has no generic chat POST; chat flows are session/partner-based (not
exercised). Real local-model generation evidence on this host already: doctor
--online provider response + two add_record auto-summaries (chat & question).
CLI single-turn attempt was blocked by PowerShell quoting of the Chinese
argument (shell issue, not product) - not pursued further.

## Refreshed baselines at C-fix HEAD (overnight)

After C01-C04/C09/C10 fixes and the C-fix commits: full `cargo test --workspace
--locked --offline` exit 0 (zero failures); full Python suite 2394 passed /
7 skipped / 124 subtests exit 0 - this time the real-URL network test PASSED
(egress available intermittently), so no unexplained failure remains at this
HEAD.

## C08 / X03 slice I (overnight): DeepTutor full stack up + UI screenshot

`deeptutor start` launched packaged backend (uvicorn 0.0.0.0:8001) + frontend
(Next.js 16.2.3 at http://127.0.0.1:3782, "packaged runtime ready in 0ms").
Headless screenshot captured (`.project-local/deeptutor-val/ui-home.png`,
~50 KB, title "DeepTutor") - first real hosted UI evidence on this machine.
The host is therefore usable end-to-end locally; default-host decision for
ArcheAxis = DeepTutor local host (API + web) with local ollama, subject to
adapter wiring (C08 remaining: candidate shell/package).

## X03 slice J (overnight): real local-model chat answer via DeepTutor API

POST /api/v1/plugins/capabilities/chat/execute-stream with a Chinese query ran
to a terminal "done" event (session -> stage_start -> 231 thinking -> 24
content -> stage_end -> done) and produced a correct Chinese one-sentence
answer about spaced repetition (stored sample:
.project-local/deeptutor-val/chat-answer2.txt, ignored). This is a real
human-side tutoring answer on the configured local host (qwen3:8b via ollama),
completing X03's runnable-answer evidence beyond summaries.

## X03/X08 slice K (overnight): book + learning path generated from notebook

- create book (bk_e00b5ff13d) with user_intent zh -> local model produced
  title/proposal (draft); export placeholder exists.
- generate-from-notebook with record OBJECTS -> 200, module "Notebook Concepts"
  with knowledge point "Saving Personal Definitions and Hypotheses";
  learning progress map returns next action "probe". This is a real
  target->module->knowledge-point learning trajectory derived from our Chinese
  notebook content by the local host - X08 human-side evidence.

## X07 slice B (overnight): first real public retrieval succeeded

Probe re-run: Wikipedia REST summary for Earth fetched OK once (run
da547d4a84a8) - first successful real public-source retrieval on this host;
egress is INTERMITTENT (later requests failed). The extract did not contain
the claim's literal 6371 (phrasing variant), and the local-model verdict
returned empty, so numeric support is INCONCLUSIVE; no fabricated conclusion.
This upgrades X07 from "no egress at all" to "egress intermittent - one real
retrieval recorded; full check still needs a stable network run".

## X07 slice C (overnight): tolerant probe - numeric support found, model verdict inconclusive

X07 probe v2: real Wikipedia full-extract retrieval OK; extract contains
"12,742" (diameter km) - consistent with the 6371 km radius claim (numeric
support true, note records the diameter basis, no literal-radius overclaim).
Local model verdict empty: qwen3:8b returns thinking-only (response "") for
these short judge prompts - recorded, not fabricated. X07 status: first real
public retrieval + numeric grounding demonstrated; stable-network full check
and a judge-model verdict still open.
