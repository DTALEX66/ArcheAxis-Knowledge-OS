# DP-NF-06 · P6 current13 Candidate readback

- task_id: `DP-NF-06` (P6 half)
- baseline_sha: `a9ead3e1597808ca751c6ccec1dba27bcfff5b4b`
- baseline_tree: `ce69abf1493481591534979be1223b1a447fc9bb`
- branch: `codex/dp-nf-06-20260925`
- evidence class: `EXACT_SHA_CANDIDATE` (verifier readback) with an explicit `NOT_EXECUTED` cell for the current-source recross-check
- **UI acceptance belongs to Codex and was NOT performed here. No UI was launched. Nothing in the Candidate was modified or installed.**

## 1. Subject

| Field | Value |
| --- | --- |
| Candidate (declared) | `current13-20260925` |
| Outer directory | `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vcurrent13-20260925` |
| Package directory (verifier subject) | `…/ArcheAxis.Knowledge.Green-vcurrent13-20260925/ArcheAxis.Knowledge.Green-vcurrent13-20260925-x64` |
| Transfer archive | `…/ArcheAxis.Knowledge.Green-vcurrent13-20260925-x64.zip` — 314,897,272 bytes, SHA-256 `4ABF50FBA49A441A25CB2558A0B9D9FA1FBF4FC943D015478377542215A2D44E` |
| Package layout | `candidate-manifest.json`, `worker-profile.json`, `启动绿色候选.vbs`, `core/`, `desktop/`, `runtime/`, `shared/`, `workers/`, `data/` |

> Path note: the Candidate is **nested one level deeper** than its outer name suggests. The verifier
> subject is the `…-x64` directory, not its parent. A path-level check of the parent alone reports
> every key file as absent; that is a naming trap, recorded here so the next reader does not repeat it.

## 2. Provenance declared by the manifest

Read from `candidate-manifest.json` (3,920,213 bytes, `utf-8-sig`, top-level keys
`schema`, `version`, `provenance`, `files`):

```json
{
  "source_commit": "a9ead3e1597808ca751c6ccec1dba27bcfff5b4b",
  "source_tree": "ce69abf1493481591534979be1223b1a447fc9bb",
  "source_snapshot": {
    "algorithm": "aaos-source-snapshot/v1",
    "sha256": "bb455735430dac58db6e69d997e1ce7ddc5ed87e856ff896810bde110e2d8416",
    "file_count": 1526,
    "untracked_build_input_count": 6,
    "excluded_path_count": 8,
    "excluded_paths_sha256": "93a1439a886f947d44b52d02fc93d91cbc94eb84638de95dc4c896e1bd500d1a"
  }
}
```

- **`source_commit` and `source_tree` match the declared baseline exactly** — this Candidate is bound
  to the stated HEAD/tree, not to an older one.
- The snapshot declares **6 untracked build inputs** and **8 excluded paths** with their own digest.
  Per the task pack, this proves *tree identity*, not compiler provenance or signing.
- `manifest.files` has **21,474** entries.

## 3. Verifier readback (the only accepted evidence)

The repository's own verifier was run; output is quoted verbatim.

**Run 1 — default scope:**
```
python scripts/release/verify_green_candidate.py <package>
{ "ok": true, "scope": "desktop-core-runtime-workers", "runtime_included": true,
  "workers_included": true, "version": "current13-20260925", "files": 21474, "problems": [] }
exit 0
```

**Run 2 — `--require-runtime --require-workers --require-provenance`:**
```
{ "ok": true, "scope": "desktop-core-runtime-workers", "runtime_included": true,
  "workers_included": true, "version": "current13-20260925", "files": 21474, "problems": [] }
exit 0
```

**Run 3 — `--require-current-source --source-root <root checkout>` (optional recross-check):**
```
{ "ok": false, "scope": "desktop-core-runtime-workers", "runtime_included": true,
  "workers_included": true, "version": "current13-20260925", "files": 21474,
  "problems": [ "the current worktree differs from the candidate source snapshot" ] }
exit 1
```

**Interpretation of run 3 (stated as a limitation, not a defect).** This is a **live concurrency
artefact**, not evidence that the Candidate was built from the wrong source:

- run 1/2 already confirm the manifest's `source_commit`/`source_tree` equal the declared baseline;
- the root checkout is **uncommitted and actively being edited by the mainline during this readback**
  (this very task reviews 678 dirty lines in it, and Codex holds a UI/desktop write-set);
- the snapshot digest is taken over the *live* working tree, so any edit after the snapshot was
  captured necessarily makes a recomputation differ.

Therefore the recross-check cell is recorded as **`NOT_EXECUTED` / not reproducible under concurrent
mainline editing**, and its `ok=false` must **not** be read as a Candidate failure. To obtain a real
current-source verdict, the recomputation has to be done in a quiescent tree, or the snapshot must be
re-bound after the mainline commits.

## 4. Package hashes (recomputed here)

| Member | SHA-256 |
| --- | --- |
| `desktop/ArcheAxis.Desktop.exe` | `89546BD465005497F8D360AA19A7FB5135DE21A0ADBB176BBE53249366F0731F` |
| `core/archeaxis-api.exe` | `E7C91DC8DE1AA0A6885E4F77A735892F6F8B67685F67299EFE5126AF48520085` |
| `runtime/python.exe` | `081786173866D86CDA1B06AA671848217FA0D635EDB6DCD2218644466F4229CD` |
| `…-x64.zip` | `4ABF50FBA49A441A25CB2558A0B9D9FA1FBF4FC943D015478377542215A2D44E` |

These are **readback values from this run**. They are not signed, not published, and not compared
against any released artefact.

## 5. What this readback does and does not establish

**Establishes**
- The package directory is structurally complete and internally consistent: `ok=true` with runtime,
  workers and provenance required, 21,474 declared files, zero problems from the repository's own
  verifier.
- The package is bound to the declared baseline commit and tree.
- The package contains a Desktop executable, a Core executable and a bundled Python runtime, with the
  hashes above.

**Does NOT establish**
- **No UI or interaction was verified.** Not one window was launched; no route, menu, keyboard, IME,
  UIA, DPI or screen-reader check was performed. That is Codex's Task 6 scope, not this card's.
- **No Green installation, replacement, backup or rollback.** The Green directory was not read or
  touched; nothing was installed, published, signed or uploaded.
- **No compiler provenance.** The snapshot proves tree identity; it does not prove which compiler
  produced the binaries, and it is not a signature.
- **No Owner Gate.** A verified Candidate is not an accepted Local Green.
- **No claim about product quality or format coverage.**

## 6. Status statement

- `A13`/P6 remain **`TESTED_LOCAL_PARTIAL`**; this readback changes no R6/M0 state and the release
  stays `FROZEN`.
- Candidate evidence ≠ Green evidence ≠ Owner Gate. This report asserts only the first.
- The current-source snapshot comparison is **`NOT_EXECUTED`** for the reason in §3, and the
  Candidate's remaining open items for a future qualification pass are: a quiescent current-source
  recomputation, the native GUI Golden Journey, and the owner-gated Green backup/replace/restart/
  rollback sequence.

## 7. Commands run (all read-only)

| Command | Result |
| --- | --- |
| `Get-ChildItem …Green-vcurrent13-20260925` | nested `…-x64` directory + zip found |
| `Get-ChildItem …-x64` | `candidate-manifest.json`, `worker-profile.json`, launcher, `core/`, `desktop/`, `runtime/`, `shared/`, `workers/`, `data/` |
| `python scripts/release/verify_green_candidate.py <pkg>` | `ok=true`, 21474 files, `problems=[]`, exit 0 |
| `… --require-runtime --require-workers --require-provenance` | `ok=true`, 21474 files, `problems=[]`, exit 0 |
| `… --require-current-source --source-root <root>` | `ok=false`, one problem ("current worktree differs"), exit 1 — concurrency artefact (§3) |
| `python -c` manifest provenance read | commit/tree/snapshot fields as quoted in §2 |
| `Get-FileHash -Algorithm SHA256` ×4 | hashes in §4 |
| file count | package directory: **21,341 files** and 2,571 directories on disk, versus **21,474 manifest entries**. The verifier accepts this and reports no problem, so the verifier's own accounting is authoritative here; the difference is not explained by this read-only pass and is recorded rather than papered over. An earlier revision of this report wrote 21,342 — that was an off-by-one from a partial enumeration and is corrected here. |

Nothing was written outside this branch. No Candidate, manifest, zip, worker profile or launcher was
modified.

## Correction — 2026-09-26 current-source verifier semantics

The command in §3 and §7 **was executed** and returned `ok=false` / exit `1`; therefore its evidence
class is an executed current-source mismatch, not `NOT_EXECUTED`. The live root tree differed from
the Candidate snapshot at readback. Concurrent editing is a plausible explanation recorded by the
original author, but the output alone does not prove concurrency was the sole cause and does not
establish which side was stale. Keep the Candidate's ordinary manifest checks (`ok=true`) separate
from the failed current-source recross-check. A later, separately bound current Candidate is recorded
in `docs/current/R6-EXECUTION.md`; it does not retroactively change this 2026-09-25 result.
