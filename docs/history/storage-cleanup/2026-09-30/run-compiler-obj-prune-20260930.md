# Generated compiler shadow/obj cleanup — 2026-09-30

Status: PASS for exact-path deletion readback. Completed at 2026-09-30T01:18:46+08:00.

All paths below are relative to `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs`.

| Removed directory | Files | Logical bytes | Complete inventory SHA-256 |
|---|---:|---:|---|
| `tmp\VBCSCompiler` | 17 | 8,430,920 | `444a5d13e3d51ccd7a3dd942960c1842a644b8e59e8fa89ee3451c62d940569d` |
| `ui-finalbuild` | 15 | 2,082,170 | `4ca3d36ddc899fa69e12719d3f82ccc6022a4ae3da9e428a7d89a8eb976ea286` |
| `r6-a12-release-obj` | 24 | 510,923 | `03b35573bececad6e37e320e6863dc7258fcabb5c6f13a606cbb3e60eab53876` |

Total: 56 files / 11,024,013 logical bytes. No archive created: these were compiler analyzer DLL shadow copies and generated .NET obj intermediates. No source files, installed dependency packages, current product binaries or historical result receipts were removed.

Immediate preflight found no visible dotnet/VBCSCompiler/ArcheAxis.Desktop process. Each resolved source was within the approved runs root; complete traversal found no reparse points or DB/SQLite/WAL/SHM/lock files. Full per-file hashes, bytes, counts and sorted manifest hashes matched the preceding read-only audit; a second source rehash agreed. Native PowerShell `Remove-Item -LiteralPath` deleted only the three exact directories. All three paths are absent after deletion; the parent `runs\tmp` remains.

Receipts: `.project-local/mig/run-compiler-obj-prune-20260930/preflight.json` contains all 56 file hashes and `final.json` contains post-deletion readback. Sorted inventory hash format is relative path, TAB, byte count, TAB, lowercase file SHA-256, LF, encoded UTF-8.

Recovery is regeneration through the project .NET build and SDK analyzer loader using retained source/dependencies. Rebuilding may produce different bytes as source/compiler versions change; no bit-exact rollback archive exists. This batch did not run a build, product test or runtime launch, and does not establish product/runtime PASS. The existing output-path rules remain authoritative for subsequent builds.

Visible process inspection does not prove absence of all protected-process handles. Adjacent runs, DeepTutor state, databases and E/F were not operated.
