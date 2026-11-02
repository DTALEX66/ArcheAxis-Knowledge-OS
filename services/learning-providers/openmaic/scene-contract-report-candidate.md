# AAOS scene contract reference derivation candidate

Unregistered, offline reference derivation of the scene contract reports that Rust
Core persists for an OpenMAIC scene candidate. The canonical implementation is
`crates/archeaxis-domain/src/course.rs` (`openmaic_refusal`, `openmaic_projection`,
`openmaic_render_contract`). This module exists because Core cannot be compiled in
the current growth-gated build state: a test can then check the *rules* against the
real pinned worker and the real donor projection instead of asserting them from
reading Rust. A divergence between this module and the Rust implementation is a
defect in one of them, never a second contract.

`scene-contract-report.mjs` imports nothing from `vendor/` and builds no scene. It
takes one bounded UTF-8 JSON frame with schema
`archeaxis.openmaic-scene-contract-input/v1`:

```json
{"schema": "archeaxis.openmaic-scene-contract-input/v1",
 "request": {"schema": "archeaxis.openmaic-scene-build/v1", "...": "the exact worker request"},
 "worker_document": {"schema": "archeaxis.openmaic-scene-build-result/v1", "...": "the reply, or null"}}
```

It answers `archeaxis.openmaic-scene-contract-report/v1` with one of:

- `REFUSED` — the request names a request version, scene content version or scene
  kind this offline slide/quiz slice cannot build. The refusal object names the
  declared value and the supported ones. No worker is needed and none is implied.
- `NO_CANDIDATE` — the reply is not a candidate scene. The projection report is
  still derived; the render contract is `null`, so an empty field cannot be read as
  "playable".
- `REPORT` — `projection` lists every request field the donor projection does not
  carry (`outline.description`, `outline.keyPoints` and a slide's `remark` are the
  observed losses), and `render` lists what a renderer can and cannot play.
- `INVALID_REQUEST` — malformed UTF-8/JSON, unknown fields, more than 512,000 input
  bytes, or an unusable report beyond 1,000,000 output bytes.

`authority_effect` is always `none_reference_only`. The module has no model, network,
Core write, installation, rendering or scheduler, and it is not registered in the
launch profile, the runtime staging manifest or the capability registry. Text and
question content in a report can be private material: a caller keeps and protects the
input and the output. Duplicate-key detection, frame identity and Core admission stay
in the worker and Rust Core; this candidate does not re-implement them.

Verified by `tests/integrations/test_openmaic_scene_contract_report.py` against the
pinned `scene-build-worker.mjs` (SHA-256
`c4a2dad9c96ebd13aa20827410227d2650cda0dac80e3a3927968d1e024779e9`, unmodified by
this slice). That test hashes the explicit Node executable around each call; it is
local synthetic evidence, not a real course, model, Core persistence or installed-app
qualification.
