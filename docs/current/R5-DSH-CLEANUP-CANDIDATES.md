# DSH cleanup candidates inside `.project-local/runs`

Measured 2026-09-13 13:02 by `.project-local/runs/r5-dsh-runs-audit/audit_runs.py`
(read-only; nothing deleted). The R5 handoff measured `runs` at 0.78 GiB and said to preserve
it; it is now 6.82 GiB. The evidence inside it is tiny, so the size is temp trees.

| class inside runs | size | files | paths |
| --- | ---: | ---: | ---: |
| tmp (run working files) | 6.476 GiB | 90,562 | 840 |
| tmp/pytest (test temp trees) | 0.011 GiB | 3,123 | 659 |
| cache | 0.000 GiB | 36 | 381 |
| **candidate total** | **6.487 GiB** | | 1,880 |

Preserved by construction: everything under `artifacts/**` (the receipts the ledger cites:
`execution.json`, `binding.json`, `inventory.json`, `result.json`, OCR observation output),
which totals about 9 MB across 807 runs.

## What the mass actually is (inspected, not assumed)

The largest candidates were opened rather than trusted by their directory name, and **all** of them
are the same thing: `<run>/tmp/pytest/**`, the temporary tree a pytest session leaves behind. The
five biggest are 342,569,337–342,573,682 bytes / 3,335 files each from 2026-09-07, and the current
`r5-checkpoint-python-primary` carries 238,140,827 bytes / 3,454 files from today — each holding the
same fixture names (`outside-c3.md`, `test_accuracy_requires_human_t0/ocr.json`). So this is
per-session test scratch, not evidence and not build state.

Two documented facts to weigh before approving:

* the R5 ledger records one thing that does live in a run's `tmp`: the desktop smoke test's SQLite
  ("默认烟测SQLite位于本run/tmp"). Deleting run `tmp` would remove that database; the recorded
  receipt for that slice is under `artifacts/**`, which this list does not touch.
* the deep UNC fixture directories inside these pytest trees are the ones that need the Windows
  long-path prefix to remove; the removal helper already retries with it.

## Largest 30 candidate paths

| bytes | files | last write | path |
| ---: | ---: | --- | --- |
| 342,573,682 | 3,335 | 2026-09-07 23:26 | `<repo>\.project-local\runs\be268a2d33\d65406623fb5\tmp` |
| 342,573,676 | 3,335 | 2026-09-07 23:23 | `<repo>\.project-local\runs\be268a2d33\a3e589daf804\tmp` |
| 342,573,674 | 3,335 | 2026-09-07 22:48 | `<repo>\.project-local\runs\be268a2d33\6cc0ef22c7f1\tmp` |
| 342,569,337 | 3,335 | 2026-09-07 21:04 | `<repo>\.project-local\runs\be268a2d33\e31758dd7698\tmp` |
| 342,568,864 | 3,335 | 2026-09-07 21:37 | `<repo>\.project-local\runs\be268a2d33\3c90d6dcaff3\tmp` |
| 238,140,827 | 3,454 | 2026-09-13 04:23 | `<repo>\.project-local\runs\be268a2d33\r5-checkpoint-python-primary\tmp` |
| 236,428,092 | 2,922 | 2026-09-11 00:11 | `<repo>\.project-local\runs\be268a2d33\001c78752f07\tmp` |
| 236,426,979 | 2,917 | 2026-09-11 00:07 | `<repo>\.project-local\runs\be268a2d33\03bc52e71f00\tmp` |
| 236,415,628 | 2,893 | 2026-09-10 23:18 | `<repo>\.project-local\runs\be268a2d33\540316064989\tmp` |
| 236,415,391 | 2,893 | 2026-09-07 23:53 | `<repo>\.project-local\runs\be268a2d33\534b7c7e2a06\tmp` |
| 236,415,285 | 2,893 | 2026-09-10 22:22 | `<repo>\.project-local\runs\be268a2d33\0a1cf7092cc0\tmp` |
| 236,415,160 | 2,893 | 2026-09-10 23:44 | `<repo>\.project-local\runs\be268a2d33\3d6043004287\tmp` |
| 236,348,833 | 2,822 | 2026-09-06 13:55 | `<repo>\.project-local\runs\be268a2d33\82bf1c1f0ccf\tmp` |
| 236,347,876 | 2,822 | 2026-09-06 14:23 | `<repo>\.project-local\runs\be268a2d33\41d434c4c732\tmp` |
| 225,853,887 | 3,308 | 2026-09-11 03:57 | `<repo>\.project-local\runs\be268a2d33\384d98190d11\tmp` |
| 225,853,624 | 3,308 | 2026-09-11 04:03 | `<repo>\.project-local\runs\be268a2d33\df2a419ec589\tmp` |
| 225,850,853 | 3,307 | 2026-09-11 03:43 | `<repo>\.project-local\runs\be268a2d33\e1049bdd3f50\tmp` |
| 225,850,759 | 3,308 | 2026-09-11 03:51 | `<repo>\.project-local\runs\be268a2d33\8214d22e82eb\tmp` |
| 225,843,513 | 3,307 | 2026-09-11 03:35 | `<repo>\.project-local\runs\be268a2d33\6dcd620aade0\tmp` |
| 225,840,798 | 3,307 | 2026-09-11 03:25 | `<repo>\.project-local\runs\be268a2d33\23f0b8f15bb6\tmp` |
| 225,798,091 | 3,219 | 2026-09-11 03:15 | `<repo>\.project-local\runs\be268a2d33\1933a312de2c\tmp` |
| 225,699,690 | 3,213 | 2026-09-11 03:08 | `<repo>\.project-local\runs\be268a2d33\204905e0cc30\tmp` |
| 225,691,950 | 3,209 | 2026-09-11 03:05 | `<repo>\.project-local\runs\be268a2d33\a0c0f26468d2\tmp` |
| 225,634,501 | 3,165 | 2026-09-11 02:58 | `<repo>\.project-local\runs\be268a2d33\1e198b61bf02\tmp` |
| 225,610,732 | 3,160 | 2026-09-11 02:51 | `<repo>\.project-local\runs\be268a2d33\d933f216bc5f\tmp` |
| 225,596,983 | 3,160 | 2026-09-11 02:42 | `<repo>\.project-local\runs\be268a2d33\67cb14856a68\tmp` |
| 225,584,324 | 3,160 | 2026-09-11 02:36 | `<repo>\.project-local\runs\be268a2d33\f6c1123f7f7f\tmp` |
| 106,158,284 | 442 | 2026-09-07 23:54 | `<repo>\.project-local\runs\be268a2d33\86c27870eecc\tmp` |
| 8,430,920 | 17 | 2026-09-02 21:38 | `<repo>\.project-local\runs\be268a2d33\50fe8d007849\tmp` |
| 8,010,328 | 13 | 2026-09-02 21:38 | `<repo>\.project-local\runs\be268a2d33\023f1aff6108\tmp` |

The complete list (all 1,880 paths) is in
`.project-local/runs/be268a2d33/r5-dsh-runs-audit-2/candidates.json`.

## What deleting these would and would not do

* Would free about the candidate total above; every one is a temporary or staging tree that the
  tool which made it can recreate on the next run.
* Would NOT remove any receipt the R5 ledger cites, and would not touch `artifacts/**`.
* Would NOT touch `.project-local/build` (current Cargo and .NET outputs), `.project-local/cache`
  (written today, dev.py routes NuGet caches there), `.venv`, `data`, `frontend`, `.hermes`,
  `.zcode` or `.codex`.
* Costs nothing to rebuild: these are per-run scratch, not build state. Some are pytest temp
  trees whose deep UNC fixtures need the Windows long-path prefix to remove.

Rollback: nothing here is irreplaceable; a re-run of the owning tool recreates its own scratch.
