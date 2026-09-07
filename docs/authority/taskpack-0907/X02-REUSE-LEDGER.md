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
