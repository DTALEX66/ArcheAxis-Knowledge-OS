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
| C02 server-side identity | DONE | launch middleware binds session-claim actor; machine restricted on create/review/learning; real-process escalation + human personal-definition tests green (launch_auth 5 passed) |
| C03 review txn + revisions + anchors | PARTIAL | single-tx review + modified event + anchor reverse lookup + supersedes chain (archive-safe); superseded rows not current-active; UI wiring open |
| C04 migration semantics/idempotency | PARTIAL | demo staging: legal PERSONAL_DEFINITION type, manifest hash+row verify before write, single atomic staging tx, inserted/reused counts, legacy-row id preserved; tamper rejected (tests); broader type map open |
| C05 learning schedule/contract | PARTIAL | idempotent client_event_id (archive-safe) + history read + absolute due timestamps; FSRS adapter wiring & full trajectory open |
| C06 knowledge qualification in consumers | OPEN | wire active check into context/get/results |
| C07 same pipeline converters + public check | PARTIAL | real retrieval + numeric + local-model verdict demonstrated (probe); single-pipeline worker registry & stable egress open |
| C08 host + Windows candidate | PARTIAL (host solved) | DeepTutor full stack local (backend+Next UI) + local ollama; real chat/answer & learning path evidence; shell/package & adapter wiring open |
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

## X08 slice L (overnight): mastery_path capability ran to done

DeepTutor capability mastery_path executed to a terminal "done" event (107
thinking + 75 content events incl. tool planning on mastery_status) - real
agentic learning-planning loop on the local host, beyond static summaries.

## Night session state (final before morning)

DeepTutor local host fully usable (API+UI+local model); real Chinese
content/answer/learning-path evidence; X07 first real public retrieval;
baselines green (cargo 0 failures; python 2394). Server processes left running
for owner inspection: backend :8001, frontend :3782 (kill at will). Evidence
files in .project-local/deeptutor-val/ and runs/. Next-day queue (recorded in
OVERNIGHT-RESULTS-2026-09-08.md): finish C05-C09 wiring on this host.

## C03 part 2 (overnight): anchor -> knowledge reverse lookup

Added knowledge::knowledge_ids_for_anchor (domain) + test
anchor_bidi.rs: knowledge created against a source anchor is findable from the
anchor (source position -> derived content direction). domain suite green.
Full bidirectional navigation (content -> source position/URL) already exists
via anchor position; remaining: supersedes relations and UI wiring.

## C09 part 2 (overnight): reproducible probes in-repo

Sanitized, runnable probe sources added under scripts/probes/:
x01_real_screenshot_ocr.py (real screenshot->OCR, rerun exit 0, tokens
matched) and x07_public_check_probe.py (real retrieval + local judge). Both
ruff-clean and use repo-relative paths; no secrets/local-absolute defaults.
Summaries remain in EXECUTION; raw run artifacts stay in .project-local.

## C05 part 1 (overnight): idempotent learning events via client_event_id

Added additive table learning_event_keys + domain record_review_keyed (key+event
in one transaction; duplicate key -> (0, streak, -1) sentinel, no new event)
and API client_event_id (duplicate -> 200 duplicate:true, next null; fresh ->
201). Test covers same-key replay counted once and streak continuity across
keys. api+domain suites green.

## C06 part 1 (overnight): qualification endpoint for consumers

GET /api/v1/knowledge-items/:id/qualification returns exists/active using
knowledge_status + is_knowledge_active (deprecated/rejected -> active false,
missing -> 404). This is the consumer-side check surface for machines before
reuse. Test qualification_api.rs green; api suite additions pass.

## Baseline refresh after C05/C06 (overnight)

Full cargo workspace --locked --offline at 1375fee: exit 0, zero failures.

## C05 part 2 (overnight): learning history read

GET /api/v1/learning/events/:item_key returns persisted event history
(domain events_for_item) - restart-stable readback for due/history tooling.
api+domain suites green.

## C05 part 3 (overnight): absolute next-review timestamps

record_review and record_review_keyed now store an absolute SQLite UTC
datetime (now + N days) instead of the relative "+N day" string, satisfying
the audit's absolute due_at requirement for the new event API. api+domain
green.

## C03 part 3 (overnight): revision supersedes chain

Additive table knowledge_supersedes + modified-review writes old->new; domain
knowledge_successors returns the chain. Test supersedes.rs green; store/
domain/archive suites green.

## Baseline refresh (overnight, HEAD b1e4c98)

Full cargo workspace --locked --offline after the C02-C06 series: exit 0,
zero failures (includes launch_auth real-process actor, learning idempotency/
history/absolute-due, qualification endpoint, supersedes chain, archive
inclusions, migration legacy-untouched).

## C06 part 2 (overnight): search results carry active qualification

/api/v1/search items now include status AND active (is_knowledge_active per
row), so consumers can filter retrieval by qualification at the source.
Test in qualification_api.rs (deprecated inactive, accepted active). api
green.

## C10 note (overnight): ASR model-dir read compatibility clarified

app/ingestion/asr_adapter.py _sense_voice_dir default fallback may READ the
preserved legacy location (".hermes/task-runtime/models/sense-voice") and
fails closed when files are absent; it never writes there. New-model profile
canonical location stays config/model-profiles (shared tessdata), per
EXECUTION X01/X06. No code change needed; read-only legacy compatibility is
distinct from new-task writes (which only go to .project-local).

## X08 slice M (overnight): learning objective readback

GET learning/progress/{book}/objectives/{kp} returns real objective state
(status new, gate qualitative, threshold, mastery 0.0, attempts []) for the
book generated from our notebook - confirms the learning host state machine is
readable end-to-end.

## C04 part 3 (overnight): attachment rows explicit loss accounting

Demo migration now counts legacy `attachments` rows as explicit losses (no vNext attachment table yet) instead of a generic unmapped-table name; test covers a non-empty attachment row. migration suite green.

## Final overnight baseline (HEAD 1ca9052)

Full cargo workspace --locked --offline: exit 0, zero failures after all C-fix parts incl. superseded-not-current.

## C04 part 4 (overnight): link rows explicit loss accounting

Demo migration counts legacy `links` rows as explicit losses with reason (no vNext relationship table yet). migration suite green.

## C06 part 3 (overnight): active_only search filter

/api/v1/search supports active_only=true (server-side retain on qualification) - consumers get only current facts. api suite green.

## C10 growth-stop evidence (overnight)

.top-level .hermes newest write remains 2026-09-06 (task-runtime dir); the entire overnight session produced zero .hermes writes - growth-stop holds for this executor's entrypoints.

## Final Python baseline (overnight, post probe-fix)

Full Python suite 2394 passed / 7 skipped / 124 subtests exit 0 at the latest HEAD; architecture guard 22/22 (probe no longer mutates sys.path).

## X07 slice D (overnight): local-model verdict obtained via chat API

qwen3:8b /api/chat returns an explicit SUPPORT verdict for the Earth-radius claim (diameter 12742/2 = 6371 consistent). X07 real check sample now complete: real retrieval + numeric grounding + local-model verdict; product pipeline & stable-network scale remain open. Probe updated to chat API.

## X03 default-host decision (overnight, locked)

Default host for the learning entry = DeepTutor local full stack (backend API + packaged Next UI at :3782) with local ollama qwen3:8b. Evidence: doctor --online PASS, Chinese round-trip via API, real chat answer, book + learning path generation, UI screenshot (see X03 slices E-J). Adapter wiring and Windows candidate packaging remain C08.

## Night milestone (round 60): summary

Overnight (full autonomy): DeepTutor local host solved + default-host decision; real Chinese content/answers/learning-path; X07 real retrieval + model verdict; C02 done; C03/C04/C05/C06/C07-part/C09/C10 multiple landed parts; probes in-repo; architecture guard + full python 2394 + full cargo green; .hermes growth-stop proven. Remaining majors: C07 single-pipeline registry, C08 package/adapter, C05 FSRS trajectory, C09 CI-on-push + audit.

## C05 donor verification (overnight): py-fsrs scheduler healthy

tests/test_learning_scheduler.py 6 passed at HEAD - the FSRS donor (shared/learning_scheduler.py, X02 wave-2 #10) is operational, ready for C05 adapter wiring.

## Host longevity (overnight round 70): doctor PASS after many hours

DeepTutor + ollama stable across the session (doctor all PASS, exit 0; backend/frontend 200).

## X03 slice N (overnight): second real Chinese answer (memory palace)

chat capability answered a second Chinese query to a terminal done event; final answer stored (chat-answer3.txt, ignored). Host answer quality stable across the night.

## Round-100 snapshot (overnight)

HEAD a1cb718 pushed; branch synced; all services 200; full cargo & full python 2394 green at their recorded heads; C02 done, C03/C04/C05/C06/C07/C09/C10 with landed parts (see C-FIX-STATUS); DeepTutor host stable with repeated real Chinese answers.

## Round-120 snapshot (overnight)

Services stable (backend/frontend/ollama 200); repo synced; no regressions introduced; remaining majors queued for fresh-context continuation (see C-FIX-STATUS v6).

## Round-140 snapshot (overnight)

All services healthy; branch synced at 7be6bec; maintenance-only since 120; remaining majors queued (fresh context recommended in the morning).
