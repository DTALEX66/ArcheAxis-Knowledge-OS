# DeepTutor Product Base — immutable upstream and authority boundary

- Adoption: `ADOPT_PRODUCT_BASE`
- Upstream: <https://github.com/HKUDS/DeepTutor>
- Version/tag: `v1.5.17`
- Annotated tag object: `2e522f754c61be7760392151fd22939d570941b8`
- Commit: `bd80a4d28a2093347ef080f98ae7cf8e3eee488e`
- Codeload archive SHA-256: `95f6519174069c73f91bc694cfb9e661e8d8d44239003ba9916b450ee77a4ac3`
- License: Apache-2.0
- Upstream tag signature: unsigned
- Recorded: 2026-08-27

## Local installation boundary

- Immutable source/venv body: shared external dependency library under `10-toolchains/deeptutor/1.5.17/`.
- Project-owned settings, databases, logs, browser evidence and generated output: `.hermes/task-runtime/deeptutor-home/` and `.hermes/task-runtime/deeptutor-browser/`.
- External library is local only and is not committed or uploaded.
- A failed shallow clone left a locked partial `source/.git/objects/pack/tmp_pack_*` entry. Normal deletion returned `WinError 5`; it is preserved as blocked residue rather than changing ACLs or force deleting it. The verified `source-archive/` and wheel venv are independent of that residue.

## 2026-08-27 real runtime readback

| Probe | Result |
|---|---|
| wheel metadata | `deeptutor==1.5.17` |
| frontend | `http://127.0.0.1:3782/` → 200 |
| backend docs | `http://127.0.0.1:8001/docs` → 200 |
| real Chromium | redirected to `/home`; title `DeepTutor`; UI shows `v1.5.17`; console errors `[]` |
| offline doctor storage | PASS, writable project-local `data/user` |
| offline doctor LLM | FAIL: no active model and no provider credentials |
| Knowledge/RAG | SKIP: no knowledge base configured |
| provider online probe | NOT EXECUTED |

The shell is therefore **RUNTIME LIVE / GOLDEN FLOW BLOCKED**. The model-dependent import → lesson → exercise → review flow must not be declared passed until an owner configures a provider in the product UI. This repository never reads, imports, logs, or fabricates provider credentials.

## Authority firewall

DeepTutor owns only replaceable product-shell projections:

- navigation, session presentation and learning interactions;
- derivative indexes, caches, embeddings and product-local session state;
- proposed learning events, candidate claims and user actions.

ArcheAxis remains the only writer for:

- `SourceObjectV2`, version/fixity/rights and original retention;
- `AnchorV2`, selector state (`CURRENT/STALE/ORPHANED`);
- Claim/Evidence/Knowledge lifecycle;
- append-only `LearningEvent`, HumanLearning projection;
- verified EvidenceBundle receipts and MachineCompetence K levels.

`app/adapters/deeptutor/authority.py` enforces this boundary: inbound payloads containing verified status, human/mastery levels, source/provenance writes or machine competence are rejected. A projection can be deleted and rebuilt from the ArcheAxis canonical state without losing truth.

## Patch queue

No upstream patch is currently applied. Branding, route mounting and authority-adapter injection remain project-side integration work. Any future upstream modification must record source commit, patch hash, license/NOTICE impact and rollback before it enters the release tree.
