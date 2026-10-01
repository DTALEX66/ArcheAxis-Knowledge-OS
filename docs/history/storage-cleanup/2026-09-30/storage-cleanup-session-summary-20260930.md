# Storage cleanup session summary — 2026-09-30

> 更新入口：`storage-cleanup-current-goal-20260930.md` 记录后续实际删除、归档替代、累计载荷及最新盘点限制。下文旧体积、保留/拒绝状态是此前阶段记录，不能当作当前状态。

> 历史审计口径：各“当前/最新/本轮”限于对应记录阶段，不是 2026-10-01 实时断言。软件静态检查、历史系统修复和存储完整性不能升级为当前产品或软件 runtime PASS。

## Latest continuation (supersedes older same-day size/worktree notes)

- Reclaimed two clean registered worktrees with normal Git lifecycle commands. `dsh-backend-20260927` (8,150,694,370 B) was removed after preserving its 164 unique runtime/migration files (55,447,266 B) and a SHA-256 path/length/timestamp receipt (78,044 B) under `.project-local/mig/dsh-backend-worktree-state-20260930/`; all payload hashes matched. Its commit remains reachable from `main` and remote refs. `github-delivery-repair` (42,281,670 B) was removed after verifying it was clean, unused, and its exact commit remains on local/remote branch `codex/github-delivery-docs-20260929`.
- Official `uv cache prune` on `.project-local/cache/uv` removed 655 unused entries / 9,269,671 logical bytes. Running it on `.project-local/cache/uv-desktop` found no unused entries. Current remaining cache still includes NuGet/Cargo packages used for locked/offline builds; no blanket cache clearing was performed.
- Read-only run audit found no additional safe large deletion in `.project-local/runs` or `mig`. The largest run trees are referenced current/historical evidence and contain SQLite sidecar groups; the failed/pass `4260083704` subruns are materially different. Keep them.
- Green root outside its protected dirty `.ui-task-tree`: `backups` 1,351,203,798 B (22 full restore snapshots and distinct SQLite migration generations), `runtime` 654,538,073 B (bundled app runtime/dependencies), `data` 41,080,145 B (database and WebView state). Retain pending rollback/data semantics. Audit-agent incident: one initial backup scan computed SQLite file hashes; no writes/deletions or DB contents were emitted, and subsequent review did not read SQLite files.
- Formal/Green scans remain incomplete lower bounds; E:/F: not accessed. UI changes and product code were not touched. No product build/test, commit, or push occurred.
- Repaired the missing registered D-drive VS Code user install using Microsoft's official signed 1.131.0 installer. Installer exit code 0; installed binary signature/version and uninstall registration match. A version-launch verification restored a window unexpectedly; that audit-started process was closed, so GUI runtime remains unverified. The 232,347,808 B installer and 1,103,707 B log remain in `.project-local/tmp/vscode-repair-20260930` because exact cleanup was rejected; no alternate deletion method was used.
- Fresh repository-native metadata inventory after the install: 76,369,164,224 B / 587,984 observed files; `.project-local` 74,630,740,767 B; 491 errors, 86 skipped reparse points, 2,050 excluded entries. These figures omit opaque `.git`, `.hermes` and private boundaries, and are logical readable lower bounds, not allocated-space measurements. The prior Green lower bound is 16,960,578,768 B.
- C/D software findings remain unresolved for Adobe hash-mismatched executables, KMSpico provenance, Defender/360 protection freshness, elevated DISM/SFC, LibreOffice's wrong registration, DSH version registration and the 2.12 GB iFonts `font-cache`. No corresponding repairs/deletions were performed. A C-audit subagent queried E:/F: capacity metadata once and checked D path metadata outside its C-only scope; no E/F contents were enumerated/read/written and no D content scan or change was made. The deviation is disclosed in the detailed report.

## Scope and safety boundary

User authorized cleanup and migration for this project and related AAOS material on C: and D:. A C-audit subagent queried E:/F: capacity metadata once, as disclosed above; no E/F contents were enumerated/read/written. This is a recorded scope deviation, not an assertion that E/F were never accessed. Database, WAL, SHM, writer-lock, runtime user data, current UI release output, and unresolved ownership data were preserved within the reviewed storage scope. No source-code or product runtime files were intentionally changed by storage cleanup.

## Completed, hash-verified cleanup

| Area | Removed from project tree | New archive on Record | Net retained logical storage reduction (source minus new Record archive) |
|---|---:|---:|---:|
| Cargo debug regenerable intermediates (`deps`, `build`, `examples`, `.fingerprint`) | 14,307,581,655 B | 0 B | 14,307,581,655 B |
| Six expanded AAOS UI candidate trees with exact sibling ZIP matches | 4,810,102,438 B | 0 B (existing ZIPs reused) | 4,810,102,438 B |
| Five historical Formal run build outputs | 1,468,732,984 B | 423,551,386 B | 1,045,181,598 B |
| Two old Green publish outputs | 454,415,128 B | 170,123,195 B | 284,291,933 B |
| NuGet HTTP cache | 392,421,775 B | 390,210,198 B | 2,211,577 B |
| Exact duplicate `desktop-publish/a5de4b13` | 217,420,057 B | 0 B (existing candidate ZIP reused) | 217,420,057 B |
| Exact duplicate `runs/candidate-r5-20260913-c` | 8,239,994 B | 0 B (existing sibling ZIP reused) | 8,239,994 B |
| Regenerable compiler/obj intermediates (`VBCSCompiler`, `ui-finalbuild`, `r6-a12-release-obj`) | 11,024,013 B | 0 B | 11,024,013 B |
| 22 historical Formal `desktop-publish` output directories | 4,798,503,361 B | 1,659,496,511 B | 3,139,006,850 B |
| Six historical dotnet desktop expansions, verified against existing candidate ZIPs | 1,300,849,703 B | 0 B (existing ZIPs reused) | 1,300,849,703 B |
| **Total** | **27,769,291,108 B** | **2,643,381,290 B** | **25,125,909,818 B** |

All archive-first removals had path/length/SHA-256 and CRC verification, immediate source rechecks, and post-removal readback. The two existing-archive dedupes were verified against the archive and retained manifest/tree before removal. Receipts and restore instructions are linked below. The 27,769,291,108 B column records source bytes removed from project trees; subtracting 2,643,381,290 B retained on Record gives 25,125,909,818 B across those storage locations, not the project-tree-only reduction or allocated disk recovery.

## Project size and volume readback

The final metadata-only traversal counted 81,465,787,187 B / 522,751 files for the Formal project before removal of the 22 historical publish directories (4,798,503,361 B; derived post-cleanup lower bound 76,667,283,826 B, file count reduced by 4,984) and 17,027,262,895 B / 144,794 files for the Green root. The Green traversal had no errors. The Formal traversal had 1,301 enumeration/stat errors in nested worktree and run/cache paths; its figure is therefore a lower bound, not a certified full-tree size. Earlier Explorer screenshots showed larger totals and are not directly comparable to this incomplete scan.

At the latest `Get-PSDrive` readback, C: had 260,817,674,240 B free and D: had 169,094,393,856 B free. D: initially measured 153,503,076,352 B free, a system-wide increase of 15,591,317,504 B. Concurrent activity can offset this volume-level delta; the verified project-tree reduction above is the cleanup accounting figure.

## Preserved and unresolved

- Green `home-master`, current preview bundles, current Release outputs, shared NuGet/UV caches, virtual environments, and outputs cited by current UI reports remain. Several old generated outputs are still referenced by R6/history or have no exact restorable archive.
- Formal historical `desktop-publish` 22 output directories (4,984 files / 4,798,503,361 B) have been archived and removed after full member/path/length/SHA/CRC and source recheck; 1,659,496,511 B ZIP retained in Record. The parent remains empty. Formal current `build/dotnet/ArcheAxis.Desktop` was protected by 19 EXE/DLL hash sentinels (9 Release), all unchanged. Details and recovery map: [desktop-publish history archive](desktop-publish-history-archive-20260930.md).
- Formal run trees with database sidecars remain. In particular, `audit-final-x64` remains expanded because its SQLite/WAL/SHM/writer-lock state is not represented in its sibling ZIP. DB contents were not read. DeepTutor web runtime bundles remain separate because their contents differ and adjacent directories include user settings/workspace/logs.
- The old Green linked worktree is **not a duplicate to delete**: it is detached and 40 commits behind mainline, but holds 31 dirty/untracked file versions differing from mainline (810,742 B). Only 3 files match byte-for-byte. Preserve it until those changes are reviewed or independently archived; the worktree link points into Formal `.git/worktrees`.
- DSH source directories `D:\All projects\AAOS candidate run`, `D:\All projects\AAOS-DSH-BACKEND-RUNTIME`, and `D:\All projects\AAOS-DSH-WHEEL-QUAL` were not found at final readback. Existing migration receipt `docs/current/AAOS-SPILLOVER-MIGRATION-20260928.md` records prior Formal/Green `.project-local/mig` copies and their verification limits. The original owner roots are absent, so ownership consolidation cannot be completed from the current paths without a valid DSH destination.
- C/D volume health was previously read as NTFS Healthy/OK. Elevated DISM `/RestoreHealth` and SFC `/scannow` completed with exit code 0; final DISM `/CheckHealth` reported no component store corruption and SFC `/verifyonly` returned 0. No current installed-runtime launch was performed.
- Windows Application logs previously showed 2026-09-26 crashes from an old Green acceptance executable and an old Formal publish artifact. They were not reproduced against the current installed Green runtime; cause remains unverified.

## Reports and recovery evidence

- [Cargo debug cache cleanup](cargo-debug-cache-prune-20260930.md), receipts `.project-local/mig/cargo-debug-cache-prune-20260930/`
- [Expanded candidate dedupe](aaos-ui-candidate-expansion-dedupe-20260930.md), receipts `.project-local/mig/aaos-current-candidate-expansion-dedupe-20260930/`
- [Formal run build archive](formal-run-builds-archive-20260930.md), receipts `.project-local/mig/formal-run-builds-archive-20260930/`
- Green historical publish archive validation and restore note: `D:\All projects\ArcheAxis.Knowledge.Green-x64\.ui-task-tree\ArcheAxis-Knowledge-OS-mainline\docs\current\AAOS-UI-REVIEW-20260929.md`; machine receipts and archive are listed below.
- [a5de4b13 publish dedupe](a5de4b13-publish-dedupe-20260930.md), receipts `.project-local/mig/a5de4b13-publish-dedupe-20260930/`
- [NuGet HTTP cache archive](../2026-09-29/nuget-http-cache-archive-20260930.md), receipts `.project-local/mig/nuget-http-cache-archive-20260930/`
- [R5 candidate expanded dedupe](r5-candidate-expanded-dedupe-20260930.md), receipts `.project-local/mig/r5-candidate-expanded-dedupe-20260930/`
- [Compiler/obj intermediate cleanup](run-compiler-obj-prune-20260930.md), receipts `.project-local/mig/run-compiler-obj-prune-20260930/`
- [Green old linked-worktree preservation review](green-old-linked-worktree-preservation-20260930.md)
- [Historical desktop-publish archive](desktop-publish-history-archive-20260930.md), exact recovery manifest and receipts `.project-local/mig/desktop-publish-history-archive-20260930/`; Record archive index `D:\All projects\Record\AAOS-project-archives\2026-09-30\README-historical-desktop-publish-22dirs-20260930.md`
- [Historical dotnet publish expansion dedupe](formal-dotnet-publish-expansion-dedupe-20260930.md); six exact candidate ZIP mappings, restore instructions, and receipts `.project-local/mig/formal-dotnet-publish-dedupe-20260930/`. All six source trees are absent; the current Formal `build/dotnet/ArcheAxis.Desktop` tree was outside the allowlist and its 545 EXE/DLL sentinels stayed unchanged.
- C/D software review and official repair evidence: `D:\All projects\Record\system-software-audit\2026-09-30\software-health-review.md`
- Green archive: `D:\All projects\Record\AAOS-project-archives\2026-09-30\green-mainline-historical-publish-20260930.zip`; SHA-256 `01DB0A64AB6D2BC96982E5B15F53F086D6676D4CE64C91860FB9B48598489BEB`
- NuGet HTTP cache archive: `D:\All projects\Record\AAOS-project-archives\2026-09-30\nuget-http-cache-20260930.zip`; SHA-256 `7B4706D4298CF64EE3800BA091AB863BEE5B1770E93FA62A1FE204B2CC1A7673`

## Verification status

`git diff --check` passed after documentation and receipt updates. Product build/tests were not run because this session performed storage cleanup and did not change product source. No commit or push was made. Existing UI and historical documentation changes in the worktree remain uncommitted and unstaged.

## C/D 软件与过期安装登记复核（追加，2026-09-30）

- 清除一个指向已不存在 `Cognitive-Loop-OS\.hermes\toolchains\vs-build-tools` 的 Visual Studio Build Tools 2022 17.14.36 实例。使用微软官方 Visual Studio 安装器按精确 installPath 卸载；退出码 0，事后 `vswhere` 实例及精确 HKLM 卸载项均已消失。卸载前 `.reg` 备份及 SHA-256 见 `D:\All projects\Record\system-software-audit\2026-09-30\software-health-review.md`。未处理其他 VS 安装。
- C 盘 Illustrator 2025 与 Photoshop 2025 可重复报告 Authenticode `HashMismatch`。没有证据判断成因，未启动、修复或删除。需要由用户在已登录的 Creative Cloud 桌面会话中按 Adobe 官方流程选择重新安装/保留偏好，再验签。
- 360 主程序与更新程序签名有效，主动防御服务运行；病毒库/实际防护效果未验证。Defender 服务停止且状态查询受限，未改变任何安全服务。D 盘 LibreOffice 状态仍 UNKNOWN；全 D 可遍历范围未找到 `soffice.exe`，但 617 个路径读取/枚举错误使其不能形成全盘不存在结论。
- Windows 组件存储初检可修复；经授权运行 DISM `/RestoreHealth` 与 SFC `/scannow` 后均返回退出码 0，CBS 显示无需修复的系统文件组件；最终 DISM `/CheckHealth` 显示未检测到组件存储损坏，SFC `/verifyonly` 返回 0。Windows 系统组件复核 PASS。Adobe 两个主程序签名异常及 360/Defender 与 LibreOffice 的验证限制见软件复核报告。
- 最新动态卷读数在本报告较早时为 C: 剩余 263,062,863,872 B、D: 剩余 168,588,087,296 B；运行 Windows servicing 后仍需重新读数。两卷上次 `Healthy` / `OK`。逐项、哈希与限制见 `D:\All projects\Record\system-software-audit\2026-09-30\software-health-review.md`。


## Formal historical publish archive — completed

- 22 historical output directories: 4,984 files / 4,798,503,361 B archived and removed after full path/length/SHA-256/CRC archive verification, immediate source rehash, and ZIP post-delete readback.
- Record ZIP: `D:\All projects\Record\AAOS-project-archives\2026-09-30\historical-desktop-publish-22dirs-20260930.zip`, 1,659,496,511 B; SHA-256 `98bb8ffbdabe2cbdb3d4fcf4c0ae7324a2e0b7a3dd985fd912e6a6c718b9c22c`; member-list SHA-256 `e8c831ab9d7f379a4b094c925ca83cb8cab1c77b470a73bd3be6d46b832444b4`.
- Net retained logical storage reduction across source and Record: 3,139,006,850 B. That stage's combined accounting totals 26,468,441,405 B removed, 2,643,381,290 B newly archived, 23,825,060,115 B net retained storage reduction. Project-tree removal uses the first value without subtracting archives stored outside the project; dynamic volume free-space deltas are separate.
- Evidence: `desktop-publish-history-archive-20260930.md`, `.project-local/mig/desktop-publish-history-archive-20260930/` receipts, and `D:\All projects\Record\AAOS-project-archives\2026-09-30\README-historical-desktop-publish-22dirs-20260930.md`.
- Final sentinel readback: all 19 EXE/DLL hashes in current `build/dotnet/ArcheAxis.Desktop` (including 9 Release files) unchanged. No DB/lock/reparse paths in the archived batch; all 22 source directories absent after deletion.

## Follow-up — historical dotnet publish expansions — 2026-09-30

- Removed six exact expanded desktop output trees under `.project-local/build/dotnet`: 1,349 files / 1,300,849,703 logical bytes. Each source tree matched its existing candidate ZIP `desktop/` members by complete relative path set, length, and SHA-256; archive ZIP hashes were read back unchanged. No database/WAL/SHM/lock or reparse paths were present, and the process-path check found zero matches among 253 processes.
- The current `build/dotnet/ArcheAxis.Desktop` output was outside the deletion allowlist. All 545 EXE/DLL hash sentinels under that tree matched before and after. R5 and R6 historical ledgers now point to their exact ZIP member prefixes and the restore receipt; dated evidence was not rewritten.
- The final D: free-space sample increased by 1,303,855,104 B during the operation. This is a volume-level observation; cleanup accounting uses the exact 1,300,849,703 B removed logical source size.
- A post-cleanup metadata inventory of the Formal repository read 85,974,144,668 B / 628,262 files, but returned `partial` with 491 path errors and 86 skipped reparse points; `repository_total_bytes` remains unknown. `.project-local` alone had 84,235,809,438 readable B with 491 errors and 2,042 excluded entries. Receipt: `.project-local/mig/post-dotnet-dedupe-inventory-20260930.json`.
- The latest Green root cross-check remains the same-day 16.96–16.99 GB readable logical range with scan errors; it includes active UI task trees and is not a distributable Green payload measurement. Current exclusions and unresolved size limits are recorded above and in the Green tree audit.
- Combined verified accounting at that stage is **27,769,291,108 B removed from project trees**, **2,643,381,290 B retained in new Record ZIPs**, and **25,125,909,818 B net retained logical storage reduction across those locations**. Existing ZIP reuse adds no archive bytes. These are logical sizes, not allocated-block attribution or latest cumulative totals.
- Detailed restore map and machine evidence: [six-dotnet-output dedupe](formal-dotnet-publish-expansion-dedupe-20260930.md), `.project-local/mig/formal-dotnet-publish-dedupe-20260930/{preflight,delete-ready,final}.json`.



## 2026-09-30 C/D final size and system readback

- Windows servicing PASS: DISM `/RestoreHealth` exit 0 (“restore completed”), SFC `/scannow` exit 0 (CBS reports zero components repaired), final DISM `/CheckHealth` exit 0 (“no component store corruption detected”), final SFC `/verifyonly` exit 0. C: and D: volumes read `Healthy` / `OK`; final free-space sample C: 265,273,843,712 B, D: 172,242,001,920 B.
- Current Formal tree scans are incomplete and differ: metadata scanner read 92,224,573,749 B / 733,536 files while reporting 9,121 path/attribute errors; independent Robocopy `/L /E /XJ` read 88,284,229,099 B / 669,373 files and reported 568 failed directories (exit code 9). Report only a measured range of 88.3–92.2 GB logical bytes, not an exact/full size. Sample errors occur under deeply nested staging/run paths; cause remains unconfirmed.
- Current Green root: metadata scan 16,994,515,872 B / 144,518 files with 276 errors; Robocopy `/L /E /XJ` 16,960,578,768 B / 144,040 files with 40 failed directories (exit code 9). Readable range 16.96–16.99 GB; not certified complete.
- The screenshot paths `C:\EDTemp`, `C:\SoftInst`, `C:\symbols` and C-root files are itemized in the Record software report. Two `SoftInst` child directories were empty, but an exact delete attempt was rejected by the command execution policy; nothing was deleted there. Identical but unowned `EDTemp\sqlite3.dll` copies and crash-debugging kernel symbols were preserved.
- D-root reparse-point audit found 86 junctions and zero targets on E:/F:; metadata scanning explicitly skipped reparse points, and no E/F paths were traversed.
- The empty `C:\SoftInst` deletion attempt was blocked by the shell execution policy (`Rejected`) after identity/emptiness checks. No fallback deletion route was used.
- Full evidence and system repair logs: `D:\All projects\Record\system-software-audit\2026-09-30\software-health-review.md` and sibling JSON/log files. Adobe Illustrator/Photoshop `HashMismatch`, 360/Defender protection state, and LibreOffice ownership remain unresolved.

## 2026-09-30 回合补充：R6 绿色版候选与跨项目归属

本轮针对三个历史 R6 绿色版候选展开目录进行了重新复核。已有只读审计曾报告其完整 ZIP 成员可恢复（差异仅为生成的 `.pyc` 缓存），但本轮独立重算 ZIP 成员 SHA-256 的脚本在完成前被停止；因此未把旧审计冒充本轮完整 readback，也未删除这三个目录。三个 ZIP/展开目录均保持原位。逐包路径、SHA、可恢复结论与本轮未完成事项见 [R6 候选交接记录](r6-green-expanded-candidate-handoff-20260930.md)。

本轮实际完成的可证明清理仍为六个正式 `.project-local/build/dotnet` 展开目录：1,300,849,703 逻辑字节、1,349 个文件；逐个归档映射与删除后回读见 [正式 dotnet 展开去重报告](formal-dotnet-publish-expansion-dedupe-20260930.md) 及 `.project-local/mig/formal-dotnet-publish-dedupe-20260930/{preflight,delete-ready,final}.json`。当前新扫描 `status=partial`，统计下界 85,974,144,668 B / 628,262 文件，并有 491 个读取错误、86 个跳过联接点；不得当作仓库精确总量。C/D 卷动态剩余空间与项目逻辑字节不是同一指标。

归属交接：确认属于其他项目的材料只应进其所有者仓库或该仓库认可的归档位置。本轮 DSH 源目录均不存在，Formal 中现有 DSH CAS/快照位于 `.project-local/mig/dsh-backend-runtime-20260928`、`dsh-wheel-qual-20260928`、`candidate-run-20260928`；保持现状并在交接清单里记录校验状态，不复制成第二份、不放入 AAOS 产品源码，也不虚构 DSH Git 分支。Obsidian-Assistance / LibreOffice、C 盘 EDTemp SQLite DLL、Cognitive-Loop-OS 历史残留等 owner/path 未完全确认，继续留在原位置并保持 UNKNOWN。没有本轮迁往其他项目或创建分支。

4.71 GB `.project-local/build/4260083704/cargo` 属于已注销 worktree 的历史 Cargo 构建缓存，没有精确恢复 ZIP；`scripts/runtime/dev.py` 明确写有不得移动/删除历史缓存的保护注释。本轮保留它。`.project-local/build/32a18f7418/cargo` 对应已登记 worktree，同样保留。Green linked worktree、当前候选包、数据库及 WAL/SHM/lock sidecar 均不在删除范围。

本轮无 commit、push 或新分支；没有运行产品构建/测试。本节新增文档与机器回执属于未提交工作树修改，不能表述为远端双端一致。


## 系统/软件与剩余项目体积续审（2026-09-30）

详见 [系统软件与存储续审](system-software-and-storage-continuation-20260930.md)。本轮 Cargo 孤儿缓存 4.71 GB 的逐文件 SHA 清单回读通过，但递归删除命令被执行策略拒绝，仍保留；不得把 hash verification 说成 cleanup。ArcheAxis 两份 C 盘 WER 已复制至 D 盘 Record 并回读哈希通过，C 源删除同样被策略拒绝，原件保留。可读目录下界：build 37.49 GB、runs 25.04 GB、worktrees 9.94 GB、staging 7.33 GB、cache 3.31 GB；数千拒绝访问路径导致非精确总量。C/D Healthy/OK；Adobe 两主程序 HashMismatch、Defender防护状态 UNKNOWN、D: VS Code陈旧登记等均见续审表。


### Current-source candidate expansion recheck (2026-09-30)

The 801,672,850 B current-source candidate expansion exactly matches its retained 285,115,521 B ZIP (18,247 paths/lengths/SHA, CRC PASS; ZIP SHA 49AD275391B6B78DCB611F196A0DAF2FD3DCB1431D1CD6648ABD7025AD3BC471). The current R6 record cites this expansion, so both are preserved. Restore pointer/report: [candidate expansion review](current-candidate-expanded-dedupe-review-20260930.md); machine verification .project-local/mig/current-candidate-dedupe-20260930/verification.json. No space reclaimed.

### Cache and Green-candidate audit correction (2026-09-30)

No safe cache deletion was proven: `.project-local/cache` has at least 3,242,568,004 readable bytes, and project offline builds, desktop bundling, and runtime depend on NuGet/UV/Cargo/Python caches. `vcurrent8` is **not** an exact source/ZIP duplicate: prior manifest audit found 225 ZIP members beyond the manifest, with historical consumers UNKNOWN. `vcurrent13` has two source-only empty directories and an explicit DSH readback reference. `vcurrent6` is missing ZIP payload files and is indexed; `va5de4b13` is the current official candidate. Preserve all four. See [continuation audit](system-software-and-storage-continuation-20260930.md) and corrected owner handoff in `docs/current/AAOS-SPILLOVER-MIGRATION-20260928.md`.

## 2026-09-30 后续完整续审

本节 supersede 本文件同日更早的 R6 “独立复核未完成”、C: 360 压缩“路径缺失”、以及 DSH “没有创建任何交接包”表述；逐项证据见 [续审计报告](continuation-audit-blockers-20260930.md)、[C/D 软件清单](c-d-registered-software-inventory-20260930.md) 和 [跨项目交接文档](cross-project-owner-handoff-20260930.md)。

- R6 三个展开目录当前 ZIP/manifest 对照已全量通过，逐文件路径、长度、SHA-256 和 ZIP CRC 均一致，额外文件仅是可再生 `.pyc`；合计 820,605,494 B，ZIP 原件 284,939,129 B。递归清理命令先前遭执行策略拒绝，三目录仍保留，本次没有换路径/工具或逐文件删除。
- 六个 Cargo `incremental` 子目录合计 3,754,348,748 B，是可由 Cargo 重建的纯编译增量数据；`deps`/构建产物/收据另存且不得折叠。当前未见 cargo/rustc 进程，`.cargo-lock` 探针未发现锁持有者；项目 `dev.py` 当前有历史缓存保留注释。用户明确授权清理，但执行策略曾拒绝精确递归删除，故该空间仍未回收。
- Staging 可读约 7.32 GiB，runs 可读下限 25,196,799,893 B（484 个访问拒绝、83 个 reparse 跳过），都未发现新的整目录可安全回收项。`4260083704/f1` 与 `f2` 共约 708 MB，哈希树比较显示 4,428/4,442 文件，仅 17,688,037 B 跨树完全相同，其余路径/内容不同；一个是失败、一个是通过的运行收据，均保留。
- Formal 注册的 8 个 worktree 合计 9,942,964,539 B；两个 Green UI 脏 worktree 至少 14,613,871,101 B，包含用户 UI 修改，均保留。四个 clean detached DSH commits 只有 worktree 当前引用。已创建 `.project-local/mig/dsh-detached-handoff-20260930.bundle`（46,095,363 B，SHA-256 `A0D70082D9E6B38D7FC3A34FF7FAB04E51BD93BA6CCD00CD8AB144B85BA2C1B9`）；bundle 验证为完整历史并列出四个目标提交。临时 refs 已移除，未在 AAOS 创建 DSH 分支。DSH owner 仓库缺失，bundle 仍待接收到 DSH-owned refs。
- C/D 静态卸载登记审计为 41 条：19 PASS / 4 FAIL / 18 UNKNOWN；不等于所有软件 runtime PASS。Adobe Illustrator 和 Photoshop 主程序均存在但 `HashMismatch`；VS Code 登记路径缺失；LibreOffice 登记路径指向 Obsidian-Assistance 源树且目标程序缺失。C: 360 压缩主程序/卸载器当前存在且签名有效，但文件版本落后登记版本。Defender 当前服务停用、提供者查询为空；PowerShell 非管理员，最新 DISM 返回 error 740，SFC 输出不可确认。不能声明 C/D 全部系统和软件正常。
- 当前目录大小扫描均为下限：Formal 87,037,391,912 B（568 个权限错误、86 个 reparse 跳过）；Green 16,960,578,768 B（40 个权限错误）。卷读数 C/D 均 Healthy/OK。E/F 未访问。

本次后续续审创建/更新的记录仍在未提交工作树中；没有 push、没有产品 build/test、没有删除上述候选。总体状态 `PARTIAL`，未达到“清无可清”或“C/D 全部软件健康”完成条件。

## 后续回合：清理已验证的空闲 worktree

- 移除 `.project-local/worktrees/verify-0c9c`（32,854,287 B）。移除前确认 `git status --porcelain` 为空、HEAD `cdc07cd0027de525dc909c7b0df8a7dce1cba16e` 可从当前分支到达，未发现其他进程命令行引用该 worktree。
- 使用 `git worktree remove -- <exact-path>` 移除；事后确认目录不存在、worktree 注册已消失、提交仍可由现有分支到达。恢复方式：`git worktree add --detach <exact-path> cdc07cd0027de525dc909c7b0df8a7dce1cba16e`。
- 本次确认的工作树逻辑回收量为 32,854,287 B；未触碰 dirty UI worktrees、DSH detached worktrees、构建/运行目录或 C/D 软件。项目状态仍为 `PARTIAL`，完整性和软件健康审计继续进行。

## 后续并行复核、归属纠正与增量清理

- 并行审计发现旧交接误把“DSH 执行 AAOS 任务”解释成“DSH 独立项目所有”。R6 权威和任务分配均把 AAOS 列为目标仓库、DSH 列为执行器；四个 worktree 的 git-common-dir/origin 都指向 AAOS。修订后的 [跨项目归属与交接](cross-project-owner-handoff-20260930.md) 将 runtime/wheel/commit 归回 AAOS，保留 DSH Desktop 私有运行数据在原地。`793e06ee` 由本地 `codex/dp-f01-20260925` 精确保护；其余三个提交由 AAOS refs 可达。
- 移除了三个干净、无进程引用、提交仍可达的 worktree：`verify-0c9c` 32,854,287 B、`dsh-governance-20260927` 41,598,549 B、`dsh-backend-r5` 354,721,074 B。Governance ignored `task-runtime` 五文件（11,334 B）先复制到 `.project-local/mig/dsh-governance-worktree-state-20260930/task-runtime/` 并逐文件 SHA 校验；path/length/SHA receipt 为 1,335 B；编译 `__pycache__` 与 Cargo debug 输出随干净 worktree 移除。
- 46,095,363 B 误分类 DSH bundle（SHA-256 `A0D70082D9E6B38D7FC3A34FF7FAB04E51BD93BA6CCD00CD8AB144B85BA2C1B9`）已移除。删除前 bundle refs 与四个提交匹配，删除后 `793e06ee` 分支、其他三个提交 refs 均回读存在。以上毛回收 475,269,273 B，新增保留副本/回执 12,669 B，净逻辑缩减 475,256,604 B；不将 C/D 动态 free-space delta 归因于本操作。
- 同回合全量元数据重扫：Formal 可读下界 86,561,404,232 B / 660,469 文件 / 256,307 目录，1,136 错误、86 个 reparse 跳过；Green 16,960,578,768 B / 144,040 文件 / 20,336 目录，80 错误、无 reparse。仍非精确物理总量。
- 当时 C/D 软件登记快照为 42 条（20 静态 PASS、4 FAIL、18 UNKNOWN；C 26、D 16），D 侧新增 Feishu 签名证据。随后本文记录的 VS Code 官方安装及签名回读关闭其缺失路径发现，按原清单重分类为 21/3/18（D 11/1/4），GUI/runtime 仍 `UNVERIFIED`。LibreOffice 注册路径问题、C Adobe 两主程序 HashMismatch 保留。SecurityCenter2 记录返回 360 与 Defender；Defender 停止，360 有运行证据但防护新鲜度未知。CBS 有同日系统修复记录，此库存复核未做新的管理员完整性检查。异常关机、Intel 服务错误与 Codex 更新失败仍是已记录故障；不能声明 C/D 全软件健康。
- 用户 UI 工作区改动未触碰；AAOS 主要源码当前仍是未提交 dirty state，未运行产品 build/test、未 commit/push。E:/F: 未访问。总体仍为 `PARTIAL`，继续查找可验证可回收项并处理可修复软件问题。
