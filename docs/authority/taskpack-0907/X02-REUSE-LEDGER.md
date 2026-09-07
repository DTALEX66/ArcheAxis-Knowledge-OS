# X02 reuse ledger — first slice (current-loop donors)

Plan: AAK-REUSE-FIRST-20260907-R2 / X02. Recorded: 2026-09-07 on
`codex/full-loop-0906`. Purpose: register the code assets the current M0 loop
actually reuses, with original path, HEAD hash, intended target, mode,
difference, behavior evidence and rollback. This is a semantic-reuse register
for the current loop only; it is NOT a claim that all 1246 legacy items were
read (X02 acceptance requires exactly this scoping). Items not listed here stay
preserved in LEGACY_MANIFEST.yaml with retained direction.

Evidence referenced below was produced on this branch before this ledger:
BULK-0907 runs (P08-P18, aggregate P22 = 211 passed / 124 subtests), R2/R09
(91 passed), DS06 format cases; run artifacts live in
`.project-local/runs/be268a2d33/` (ignored). Worker files have no DB handle;
all are isolated computation consumed through Rust/Core contracts (X04/X06).

| # | Original asset (tracked HEAD sha) | Purpose / capability | Reuse mode | Required vNext acceptance | Behavior evidence | Difference / limits | Rollback |
|---|---|---|---|---|---|---|---|
| 1 | `services/python-workers/transport/text_ndjson.py` (`2c5b2426`) | NDJSON text transport, stdlib-only, child runs with `-S` | direct reuse (interface unchanged) | X04/X06: attempt-claimed durable execution, structure/loss receipts | `tests/workers/test_text_ndjson.py`, `test_bulk_transport.py` (P17); R09 91 passed; P22 aggregate | no DB handle; single direct text child only | revert adapter wiring slice; file itself unchanged |
| 2 | `services/python-workers/document/worker_canvas.py` (`8ea403a2`) | JSON Canvas nodes/edges → document projection + anchors | direct reuse (+ P09 anchor recompute fix already merged) | X06: canvas into format chain with real anchors | `tests/workers/test_bulk_structured.py` (12), `test_document_fixture_matrix.py` (11+), fixture `canvas-zh-group.canvas` | anchor bounds now recomputed from final projected text | revert P09 fix if needed; fixture + tests tracked |
| 3 | `services/python-workers/document/worker_subtitles.py` (`1178c3a2`) | SRT/VTT parse: unicode, overlaps kept, malformed rejected | direct reuse | X06: subtitle lane | `test_document_fixture_matrix.py`, fixture `sample-overlap.srt` | no VTT cue-region loss reporting yet | revert test/fixture additions |
| 4 | `services/python-workers/document/worker_office.py` (`3a656ee8`) | DOCX/XLSX/PPTX via stdlib ZIP/XML + openpyxl/python-pptx adapters | direct reuse (engine = `worker_office._docx_text`, NOT python-docx for docx text) | X06: Office structure/truncation declared per DS06/F-matrix | `tests/workers/test_bulk_office.py` (6), DS06 quality asserted on golden substrings | embedded-image OCR (F12+) not qualified yet | revert engine lock changes; originals untouched |
| 5 | `services/python-workers/evaluation/worker_quality.py` (`43120e4b`) | CER/WER + metric validation (`evaluate`, `validate_report_metrics`) | direct reuse | X07: hierarchical golden metrics, error>1 not clamped | `tests/workers/test_quality_regressions.py`, `test_bulk_quality.py` (8) | quality-report measured/unmeasured schema coupling enforced at contract level | revert metric test additions |
| 6 | `services/python-workers/web/worker_html.py` (`922e4009`) | static HTML raw-first extraction | direct reuse | X06: redirect/deadline/byte-limit/encoding recorded; dynamic page = BLOCKED_RESOURCE until playwright | `tests/workers/test_bulk_html.py` (8), DS06 | F03 dynamic DOM needs playwright+chromium (not self-installed) | revert additions |
| 7 | `services/python-workers/vision/worker_ocr.py` (`d638f16c`) | Tesseract OCR with explicit tessdata profile | direct reuse | X06: real OCR sample (eng passed; chi_sim/table pending), fail-closed probes | `tests/workers/test_bulk_ocr.py` (4, needs TESSDATA_PREFIX else 4 skipped - not fake pass), DS06 | host TESSDATA_PREFIX is stale; profile must bind explicit shared tessdata dir | revert OCR profile wiring only |
| 8 | `services/python-workers/media/worker_transcribe.py` (`48a9cd8a`) | media lane via ffmpeg/ffprobe (≤30s wav generation, duration/hash) | direct reuse (ASR lane separate) | X06: ASR transcription execution group BLOCKED until authorized project model profile (P14) | `tests/workers/test_bulk_media.py` (2), DS06 | ASR model profile not yet authorized; do not fake | revert media test additions |

## Rules carried forward

- Every row above must keep original bytes: original assets are read/reused,
  never rewritten as part of "absorption" (SUP-010/SUP-015).
- Any adapter added later must record its own original path/hash, target,
  behavior sample, regression evidence and rollback before X06 wiring.
- Remaining legacy items (LEGACY_MANIFEST.yaml) stay preserved with direction;
  finishing a semantic review of all 1246 is not a prerequisite for M0 (X02
  acceptance). R03's 20-item semantic review + ds02 reuse scan remain the
  authoritative prior input for the next review wave.
- Rollback = revert the specific adapter/test/ledger commit, never delete the
  original asset or its run evidence.

## Wave 2 (2026-09-07): legacy learning/knowledge donors for X08/X09

Basis: function-body reading of each file (heads + key symbols above) plus
existing test files that reference them. All listed tests ran green inside the
2026-09-07 overall regression (run `be268a2d33/e31758dd7698`: 2394 passed).
These are legacy-database writers (sqlite via app/shared); the vNext rule
stands: legacy Python remains the only legacy-database writer, Rust never
touches it; reuse here means the semantic/algorithm layer is the donor for
adapter wiring in X08/X09, not a live dual-write.

| # | Original asset (tracked HEAD sha) | Purpose / capability | Reuse mode | Target | Difference / limits | Behavior evidence (existing tests) | Rollback |
|---|---|---|---|---|---|---|---|
| 9 | `app/knowledge/co_learning_loop.py` (`21f885e5`) | bidirectional human-AI loop orchestrator; REVIEW_EVIDENCE outranks; teach_plan suggestions only, skill candidate until human review | adapter (X08 wires flow semantics; no legacy DB writes) | X08 human side | legacy sqlite + legacy DB schema; must be re-expressed over Rust Core events | `tests/test_co_learning_loop.py`, `test_learning_loop_e2e.py` | revert adapter; original preserved |
| 10 | `shared/learning_scheduler.py` (`14ecab54`) | FSRS v6 wrapper (py-fsrs, MIT) requiring EvidenceAnchor on every card | adapter (one scheduling authority per collection) | X08 review scheduling | upstream py-fsrs pinned; events must be replayed via Core, not Anki dual-write | `tests/test_learning_scheduler.py` | revert pin/adapter |
| 11 | `app/knowledge/learning_artifact.py` (`f20d0634`) | candidate-only LearningArtifact projection from reviewed Knowledge + approval gating | semantic donor | X08 artifact/approval state | legacy approval model; vNext knowledge/user-acceptance dims separate (X04) | `tests/test_knowledge_to_learning_artifact.py`, `test_learning_artifact_card_projection.py`, `test_learning_artifact_contract.py` | revert donor copy |
| 12 | `shared/evidence_verification.py` (`9e4ef049`) | text-grounded evidence matching; never random page/frame fallback | direct semantic reuse | X07 evidence gates | candidates must carry text; OCR/transcript still separate lanes | `tests/test_evidence_contract.py` (+hardening/coverage-gap) | revert additions |
| 13 | `app/learning/distillation.py` (`54943ab6`) | human-reviewed, evidence-gated, reversible distillation promotion (approval decisions approved/deprecated) | semantic donor | X09 machine side | legacy sqlite tables; re-express over Core candidate/proposal + revocation | `tests/test_distillation.py`, `test_distillation_review.py`, `test_machine_knowledge_candidates.py` | revert |
| 14 | `app/knowledge/machine_knowledge.py` (`29ae9861`) | governed MachineKnowledge candidates from mastered signals; reviewer decides approved/deprecated | semantic donor | X09 machine knowledge/revocation | approval & scope semantics to map into Rust domain (X04/X09) | `tests/test_machine_knowledge_contract.py`, `test_knowledge_governance_migration.py` | revert |

Rules in Wave 1 apply unchanged; adapter wiring in X08/X09 must keep original
bytes and record per-donor diff + regression before activation.
