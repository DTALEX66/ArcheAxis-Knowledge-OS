# AXM G0 Golden Corpus Plan

> Legacy-source names in the inventory below are retained solely to identify
> immutable imported files; they are not current product naming.

> Status: INCOMPLETE. This is a rights- and hash-bound candidate inventory,
> not a claim that Tier A or an installed Green runtime has qualified every
> format. It contains no user learning material.

## Admission rule

A Golden corpus entry is eligible only when its original bytes, SHA-256,
license/right-to-use, privacy classification, expected conversion result and
anchor expectation are all recorded. A fixture without rights metadata remains
a test candidate, not an accepted corpus item.

## Current repository candidates

| Format | Candidate | SHA-256 | Rights/privacy evidence | Expected result | Status |
| --- | --- | --- | --- | --- | --- |
| TXT | `tests/fixtures/sample.txt` | `191386cbeb9a0c6e593c85e94d9763001bfce25666c4921812e55fb71a0951a5` | No standalone rights record | Raw retention and plaintext conversion | HOLD — add rights record |
| HTML | `tests/fixtures/tier_a_article.html` | `8ee4b1fa807f81dc0a3a3e17c2723256e8fb47915bbc6a837c59ec04c603896d` | Repository test fixture; no standalone rights record | Main-content anchor persists | HOLD — add rights record |
| PPTX | `tests/fixtures/sample.pptx` | `92354555af75b4c41e10edadbe29570fa0a3d58d05d8421e53c367bdace137e5` | Repository test fixture; no standalone rights record | Slide 1/2 anchors persist | HOLD — add rights record |
| XLSX | `tests/fixtures/sample.xlsx` | `d2de79afde88872c2e69c73da3fbed4ae1eae53d25bab5c14209b1ee365ef683` | Repository test fixture; no standalone rights record | `Data`/`Notes` sheet and formula anchors persist | HOLD — add rights record |
| DOCX | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/ArcheAxis OS Overview.docx` | `b4437158ad8f08dbbfe79a08212666056ce0347169f3bd7d8c8a46b8a3efb8b5` | Imported legacy design delivery; no current rights statement | Heading and source-Markdown anchors persist | HOLD — verify provenance/right-to-use |
| TXT replacement | `tests/fixtures/golden/golden-text-anchor.txt` | `36bfbbcdb2d4137343d41fa843cb561962aa411ae5cb5128eebce9620e0e118d` | Project-authored synthetic test fixture; no personal data | Line 1 `Plaintext evidence anchor` | ACCEPTED FOR TXT STRUCTURAL EVALUATION ONLY |
| HTML replacement | `tests/fixtures/golden/golden-web-anchor.html` | `e997211f4343167b93c9abba0e8f2a59c65972abdfb9639c0e5e7b81d51f4bb5` | Project-authored synthetic test fixture; no personal data | Main-content `Web evidence anchor` | ACCEPTED FOR HTML STRUCTURAL EVALUATION ONLY |
| DOCX replacement | `tests/fixtures/golden/golden-docx-anchor.docx` | `6356fbba83f683723a3d202a443af2d10ad5957dc2b7be2d275be0247349855b` | Project-authored synthetic test fixture; no personal data | Heading/source-Markdown `Document evidence anchor` | ACCEPTED FOR DOCX STRUCTURAL EVALUATION ONLY |
| PPTX replacement | `tests/fixtures/golden/golden-pptx-anchor.pptx` | `461e7fac8132e74ae142e35b77acf434ca90e8892a71f97b27230e6f69325eeb` | Project-authored synthetic test fixture; no personal data | Slide 1 `Slide evidence anchor` | ACCEPTED FOR PPTX STRUCTURAL EVALUATION ONLY |
| XLSX replacement | `tests/fixtures/golden/golden-xlsx-anchor.xlsx` | `c70fd35b6cb3d18a6a8779c1fab21c312ba03fc07893ccaff422a5ea9be0466a` | Project-authored synthetic test fixture; no personal data | `Evidence` sheet `Sheet evidence anchor` | ACCEPTED FOR XLSX STRUCTURAL EVALUATION ONLY |
| PDF | `tests/fixtures/golden/golden-journey-evidence.pdf` | `0f0ffc50c79d9d977efb925351ca1d64a063184e4bdd71507b9ac44992f7adcf`; deterministic generator `tests/golden_pdf_fixture.py` | Project-authored synthetic test fixture; no personal data; fixture manifest records rights basis | Page 1 anchor and `Golden Journey Evidence` text persist | ACCEPTED FOR PDF STRUCTURAL EVALUATION ONLY |
| Screenshot/image OCR | `tests/fixtures/golden/golden-screenshot-ocr.png` | `050538c71fc63ee2d0e8327f2fbdffad6f8cab135d35069aa86dc371300f68c8`; generator `tests/golden_ocr_image_fixture.py` | Project-authored synthetic test fixture; no personal data; fixture manifest records rights basis | `OCR GOLDEN ANCHOR`, full-image region, `pytesseract+tesseract` / `eng` expectation | ACCEPTED FOR IMAGE OCR STRUCTURAL EVALUATION ONLY |
| Audio ASR | `tests/fixtures/golden/golden-audio-anchor.wav` | `9f0297fb94b378d742772caede9bf5302813775c80ebb1bcead0fee4ec30e9bd`; generator `tests/golden_media_fixture.ps1` | Project-authored local-speech fixture; no personal data; fixture manifest records rights basis | `Learning evidence anchor`, one time-range block, local ASR | ACCEPTED FOR CURRENT-MACHINE AUDIO ASR EVALUATION ONLY |
| Video ASR | `tests/fixtures/golden/golden-video-anchor.mp4` | `7ec5d082608cb4fc190b67ca245b8d1d9d1c8d036b9291bd16b89b55abcf2ddb`; generator `tests/golden_media_fixture.ps1` | Project-authored black-frame + local-speech fixture; no personal data; fixture manifest records rights basis | `Learning evidence anchor`, one time-range block, local ASR | ACCEPTED FOR CURRENT-MACHINE VIDEO ASR EVALUATION ONLY |
| OCR truth pairs | `tests/fixtures/corpus/manifest.json` | `def00afb02d96ee5dcc097eb971444ba169dda0417db5e7639961143229908c1` | Manifest declares self-authored, public-domain-style, no personal data for three text pairs | CER/WER evaluation | ACCEPTED FOR TEXT-PAIR EVALUATION ONLY |
| Markdown/Canvas | `tests/fixtures/golden/learning-evidence.canvas` | `79f3decaf1398fada1cd2b4f6b85bcad5a37a62e4beac8cdd0c7b7ed098540f5` | Project-authored synthetic test fixture; no personal data; fixture manifest records the rights basis | Source/evidence edge, unknown-field round-trip and validation | ACCEPTED FOR CANVAS STRUCTURAL EVALUATION ONLY |

## Required additions before a complete Tier-A baseline

1. Fresh-workspace and existing-workspace snapshot receipts that bind original
   hashes, schema/fingerprint, API projection, screenshots, failure paths and
   performance observations. All generated evidence remains under `.hermes/`.

## Current executed evidence

- `tests/test_tier_a_fixture_matrix.py`: `2 passed` for DOCX/PPTX/XLSX/HTML/PDF
  conversion-run persistence and anchors.
- `tests/test_axw023b_f_adapters.py` plus `tests/test_adapter_contract.py`:
  `100 passed` for adapter success/degradation contracts.
- `tests/test_workspace_pipeline_multiformat.py`: `7 passed` for local and
  service-owned batch intake, original retention, conversion readback,
  sanitised failure and recovery.
- `tests/test_media_extractor.py` plus `tests/test_pdf_extraction.py`: `5 passed,
  1 skipped` for synthetic FFmpeg/PDF processing.
- `tests/test_golden_canvas_fixture.py`, `tests/test_axw043b_canvas_write.py`
  plus `tests/test_compat_c3.py`: `12 passed` for the committed Canvas fixture,
  round-trip and compatibility slice.
- `tests/test_golden_pdf_fixture.py` plus `tests/test_tier_a_fixture_matrix.py`:
  committed raw PDF integrity and page-anchor conversion are covered; the PDF,
  Canvas and Tier-A slice combined as `4 passed` on 2026-09-02.
- `tests/test_golden_ocr_image_fixture.py` plus the stale-environment resolver
  regression: committed screenshot integrity and shared-Tesseract language
  discovery are covered as `2 passed`; an actual local conversion of the raw
  fixture produced `OCR GOLDEN ANCHOR` through `pytesseract+tesseract`.
- Local probes (not committed golden corpus entries) exercised public webpage
  fetch → `safe-http+trafilatura`, a 5.6-second local audio sample → three
  local-ASR time anchors, and a temporary MP4 → the same time-anchored local
  ASR path. They establish current-machine component evidence only.
- `tests/test_golden_media_fixture.py`: project-owned WAV and MP4 bytes, hashes,
  rights and time-anchor truth are covered as `1 passed`. On the current
  machine and the Green bundled Python, both raw fixtures exactly transcribed
  `Learning evidence anchor` with one time-anchored block each; that is not a
  CI or installed-UI qualification.
- `tests/test_golden_tier_a_owned_fixtures.py`: project-owned TXT/HTML/DOCX/
  PPTX/XLSX bytes, hashes, rights and anchor expectations are covered as
  `1 passed`. Green bundled conversion read all five relevant non-media
  fixtures with their expected text and native anchors; the repository test
  environment's missing `python-docx` does not change that Green evidence.

None of these local test results substitutes for a user corpus, a model-quality
benchmark, Windows installed-runtime evidence, or full exact-SHA CI.
