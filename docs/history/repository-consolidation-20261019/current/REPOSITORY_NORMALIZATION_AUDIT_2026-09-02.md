# Repository Normalization Audit — 2026-09-02

> Status: **IN PROGRESS / deletion blocked by migration gates**. This is a
> read-only inventory and routing record, not authority to erase a tracked
> path, Green data, ignored runtime evidence, or a dangling Git object.

## Verified baseline

- `HEAD` and `origin/main` both resolve to
  `db13d0564ac2971d4b1eb3e3a5bff9c9256af313`; the working tree is not clean,
  so ref equality is not evidence that local work has reached cloud.
- The tracked `docs/` surface contains 268 files and about 1.34 MiB. Document
  payload is not the material repository-size problem.
- [`DOCUMENTATION_AUTHORITY_INDEX.md`](../DOCUMENTATION_AUTHORITY_INDEX.md)
  now supplies the canonical lookup order and separates current authority,
  frozen truth, task packs, migration records, imported references and history.

## Retention decisions

| Class | Paths | Decision |
| --- | --- | --- |
| Binding/current | `AGENTS.md`, `docs/CONFIGURATION_AUTHORITY_INDEX.md`, `docs/truth/`, `docs/current/CURRENT_REALITY_2026-09-01.md`, `docs/PROJECT_STATUS.md` | Retain in place |
| Active execution | `docs/taskpacks/AXR-FINAL-20260826-R2-OSS-FAST-TRACK.md`, G0 migration records under `docs/current/` | Retain in place |
| Reference inputs | `docs/architecture/imported-designs/` | Retain read-only; do not treat as implementation proof |
| Root legacy history | `docs/HANDOFF_*`, `docs/SUMMARY_*`, `docs/PROJECT_AUDIT_2026-07-07.md` | Preserve; archive move is pending reference-compatible manifest and a frozen writer |
| Ignored runtime/evidence | `.hermes/` | Preserve unless an individually verified project-runtime cleanup command has an explicit target |
| Green user runtime | `ArcheAxis.Knowledge.Green-x64/data` | Out of scope; never inspected, copied or cleaned |

## Legacy-root manifest

The following 19 tracked records are historical-only. They remain at their
current paths until their consumers are rewritten and path/hash/readback gates
are complete. Their aggregate tracked size is 92,265 bytes.

| File | SHA-256 | Known consumer decision |
| --- | --- | --- |
| `HANDOFF_2026-07-21.md` | `11cc41b6cb1166d03ca70d6a81a4f246793d42a85c58e1c3e3f5b4dd1943da94` | `tests/test_release_manifest.py` reads it; move requires test update |
| `HANDOFF_2026-07-23.md` | `7ec7bd667a40c08e04fdf2f92e2bf4983f0c641316636cbdc8776779b98c8c5b` | No non-self textual reference found |
| `HANDOFF_2026-08-07_audit-cleanup.md` | `8eba982b5d2488489a30a1a4b013ed2735cf2caaf622e78f0d58ae400c532ccf` | No non-self textual reference found |
| `HANDOFF_2026-08-07_session-summary.md` | `feb030c92d7ecaaf433fa4f5f1cb37d9126c03749d8e4e04966f2d44da6ac56f` | No non-self textual reference found |
| `HANDOFF_2026-08-07_stage-summary.md` | `4f673a753e866479975532a5e35d8bca4da7758f93be7a4f121cd699eb07b018` | Convention checker contains a path allowlist |
| `HANDOFF_2026-08-12_naming-migration.md` | `03f85697c508d2aaa61f4f74f4ceeab6c38b4ea29c5f1d8f7cd60ee569824795` | No non-self textual reference found |
| `HANDOFF_2026-08-18_dual-learning-absorption.md` | `ce2e15633f0420c94ea5a812aa0bd7153f795c44c8f975e588f8ac620de88f47` | `HERMES_HANDOFF.md` reference; update only with its owner |
| `HANDOFF_2026-08-19_full-advance.md` | `fa545177f3588027fd2e5bd6a5d17561915db887bddd420f1d99bcbf756766b6` | No non-self textual reference found |
| `HANDOFF_2026-08-19_pipeline-cleanup.md` | `705fb42948ac0d17b104f60468a9ac913c616a35fd32a221da21fce79ee29f51` | `HERMES_HANDOFF.md` reference; update only with its owner |
| `HANDOFF_2026-08-20_session.md` | `d18acaf29ea1644409403f0d4f846bf905f916bd0327c0cae66c88a76a083288` | No non-self textual reference found |
| `HANDOFF_2026-08-23_v0.6.7-release.md` | `3f7ee843ef9c5f43912d590d7f11b2e79fd10f859522227f168eff4fd23b0b63` | No non-self textual reference found |
| `HANDOFF_2026-08-23_v0.6.8-release.md` | `4107dc58fa804366296510ede53108b1468681d1dc23a5143b75efff8c8f1334` | No non-self textual reference found |
| `HANDOFF_2026-08-23_v0.6.9-release.md` | `aab88aead6f03f87aa9d42168c7ec3a29ca7376acc7c7f7213213a17b135b76b` | No non-self textual reference found |
| `HANDOFF_2026-08-24_v0.6.10-release.md` | `c4a8f0f02bfa72746b89c4306ea2134d7a56b96c541832c93d29cf0818b4cc9c` | No non-self textual reference found |
| `HANDOFF_DEEPSEEK_REAL_CASE_E2E_2026-07-23.md` | `3b3d23f676d3cc11040ce277c0707fdd4b077d3f32ff0690ba11d0e3ce7245ef` | No non-self textual reference found |
| `PROJECT_AUDIT_2026-07-07.md` | `777bbbecaeb316955264327fa262a5527d929df63c99a09b9f04d9560b2d943f` | Historical inventory mention only |
| `SUMMARY_2026-08-23_v0.6.8.md` | `5780b5dfcda434bbf49c88518705a740b411ead4d02b46e90aaa202479127214` | No non-self textual reference found |
| `SUMMARY_2026-08-23_v0.6.9.md` | `d0c7cb3f057c7399d693e869c264d5fa1261dfe22fb78c4ad08dbe53827e2bfb` | No non-self textual reference found |
| `SUMMARY_2026-08-24_v0.6.10.md` | `1b0d9207a6f880e6d3051c6212c1d4938ba9a5e0bc48813d7746f1a085197a68` | No non-self textual reference found |

## Git/runtime cleanup gate

- `.git/objects/pack` has five temporary `tmp_pack_*` files created on
  2026-08-12, totaling 8.95 MiB. `git fsck --full --no-reflogs` also reports
  dangling commits/trees/blobs, so deletion is not safe until their retention
  decision is explicit.
- Two Git processes were alive during the audit. Do not run `git gc --prune`,
  delete temporary pack files, or remove dangling objects while any writer may
  still be publishing or retaining recovery history.
- Once the Git writer count is zero, the next bounded step is a fresh
  `git fsck --full`, a reachability/age report, and an official Git cleanup
  invocation with postcondition checks. No broad filesystem deletion is allowed.
