# Formal historical dotnet publish expansions — 2026-09-30

## Scope and decision

Audited six isolated historical desktop publish directories under
`.project-local/build/dotnet/`. Each full source file path, byte length and
SHA-256 matched the corresponding retained candidate ZIP's `desktop/` subtree.
The ZIP files stay at their existing paths; this operation removes only the
redundant expanded desktop trees after the preflight receipt is revalidated.
The installed/current Formal desktop, all Green roots, source code, databases,
and user data are outside scope.

Owner: ArcheAxis-Knowledge-OS (`IGNORED_DEVELOPMENT`, historical generated
publish outputs). Deletion grant: user's active C:/D: cleanup authorization,
applied to this exact reviewed allowlist. Rollback: extract only the listed ZIP
member prefix to the corresponding source path and verify against
`.project-local/mig/formal-dotnet-publish-dedupe-20260930/preflight.json`.

## Exact source and recovery map

All source paths are children of
`D:\All projects\ArcheAxis-Knowledge-OS\.project-local\build\dotnet`.

| Source directory | Files | Bytes | Existing recovery ZIP | ZIP SHA-256 |
|---|---:|---:|---|---|
| `green-desktop-current10` | 225 | 217,569,283 | `green-candidates/ArcheAxis.Knowledge.Green-vcurrent10-20260925/ArcheAxis.Knowledge.Green-vcurrent10-20260925-x64.zip` | `c46e51fbe745ac5fe7d24eda35ffafe6143873c3de8c9c6f129bcc60ee5a4cd8` |
| `green-desktop-current11` | 225 | 217,569,255 | `green-candidates/ArcheAxis.Knowledge.Green-vcurrent11-20260925/ArcheAxis.Knowledge.Green-vcurrent11-20260925-x64.zip` | `63770f4cd4ec0988bd19f915208be905e3913ec9592ebec9e4a5ac3f268b1437` |
| `green-desktop-current12` | 225 | 217,569,255 | `green-candidates/ArcheAxis.Knowledge.Green-vcurrent12-20260925/ArcheAxis.Knowledge.Green-vcurrent12-20260925-x64.zip` | `65bcf9edb9c942ad553ea9eee880cbd68127e4ec2bb2aed6c115af98021d9c3d` |
| `green-desktop-current13` | 225 | 217,569,775 | `green-candidates/ArcheAxis.Knowledge.Green-vcurrent13-20260925/ArcheAxis.Knowledge.Green-vcurrent13-20260925-x64.zip` | `4abf50fba49a441a25cb2558a0b9d9fa1fbf4fc943d015478377542215a2d44e` |
| `green-desktop-452b5d0c` | 225 | 215,309,735 | `green-candidates-r6/ArcheAxis.Knowledge.Green-vr6-452b5d0c-x64.zip` | `441f67be549cab0ac2a9f1a9391fa4e2192e0129d2f26afbac9321b42546663c` |
| `archeaxis-green-compatible-selfcontained` | 224 | 215,262,400 | `green-candidates/ArcheAxis.Knowledge.Green-vheadd1bb2b99-x64.zip` | `cbc3df430a5b665f1c9593ad390e1feab329ffd9221a5879d1d0667924ab1ba9` |
| **Total** | **1,349** | **1,300,849,703** | | |

For each row, recover the `desktop/` subtree below the ZIP's top-level
candidate directory back into the original source directory. Do not extract
the entire candidate ZIP over another candidate or the Green installation.

## Consumer and preservation audit

- Search of 2,106 tracked and 295 untracked text files found no current code
  consumers. The historical source reference in
  `docs/current/R6-GREEN-CANDIDATE-20260921.json` names
  `green-desktop-452b5d0c`; historical R5 smoke notes name
  `archeaxis-green-compatible-selfcontained`. Both references remain valid as
  archive-backed evidence and now point to this recovery map.
- No visible running process had an executable path under the six source
  directories at the audit readback. This was not a protected process-handle
  scan.
- No database, WAL, SHM, lock file, or reparse point was found in these six
  source trees. The active Formal `build/dotnet/ArcheAxis.Desktop` tree is not
  part of the allowlist; its 19 EXE/DLL sentinels were checked in the separate
  desktop-publish cleanup and remain protected.
- The six directories are ignored generated outputs; the existing dirty UI
  source/docs/tests have disjoint paths and are preserved. No branch, commit,
  push, release, or product test is part of this local cleanup.

## Execution evidence

- Exact per-file source and ZIP member hashes, paths and lengths passed before
  removal: `.project-local/mig/formal-dotnet-publish-dedupe-20260930/preflight.json`.
- Final receipt: `.project-local/mig/formal-dotnet-publish-dedupe-20260930/final.json`.
- Final status: `PASS`; all six source paths are absent, all six recovery ZIP
  SHA-256 values still match the table above, and 545 EXE/DLL hashes under the
  separate current Formal `build/dotnet/ArcheAxis.Desktop` output are unchanged.
- Removed 1,349 files / 1,300,849,703 logical bytes. D: free-space observation
  increased by 1,303,855,104 B across the operation; concurrent volume activity
  may account for the difference, so logical-tree accounting is authoritative.
