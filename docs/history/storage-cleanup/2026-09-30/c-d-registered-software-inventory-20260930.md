# C/D registered software static inventory — 2026-09-30

## Scope and interpretation

Read-only inventory of Windows uninstall entries whose non-empty `DisplayName` had an `InstallLocation`, `DisplayIcon`, or `UninstallString` pointing to C: or D:. Sources: HKLM 64-bit, HKLM 32-bit (`WOW6432Node`), and HKCU uninstall registration. This is not a full filesystem discovery or runtime test. `PASS` means the selected main executable exists and its Authenticode signature is valid, unless the row explicitly says the entry is a shared/runtime component. `FAIL` is a concrete missing-path or signature-integrity issue. `UNKNOWN` means the selected path exists but signature/provenance or component completeness could not be established. `NotSigned` and `UnknownError` do not by themselves prove malware.

Recorded follow-up after VS Code repair: **42 registrations: 21 static PASS, 3 FAIL, 18 UNKNOWN**. C: has 26 registrations (10/2/14); D: has 16 (11/1/4). The prior 42-row snapshot was 20/4/18 before the VS Code static finding closed; the earlier 41-row count omitted Feishu. This reconciles the recorded rows, not a new software/runtime health check. Twelve entries had missing icon-path EXEs in an initial triage; some icons point to `.ico`, uninstallers or shared components, so that count is not a count of missing applications.

## C: registrations

| Status | Software | Static evidence and limit |
|---|---|---|
| PASS | Git | `git.exe` exists; Authenticode `Valid`. |
| PASS | Krita | `krita.exe` exists; `Valid`. |
| PASS | Logitech G HUB | `lghub.exe` exists; `Valid`. |
| PASS | 360 compression | Registered C: `360zip.exe` and `UnInstaller.exe` both exist and are `Valid`; registered version 4.0.0.1680 differs from executable 4.0.0.1590 and uninstaller 4.0.0.1130, so reconcile the version residue. |
| PASS | Google Chrome | `chrome.exe` exists; `Valid`. |
| PASS | Microsoft Edge | `msedge.exe` exists; `Valid`. |
| PASS | Edge WebView2 | `msedgewebview2.exe` exists; `Valid`. |
| PASS | LM Studio | Registered main EXE exists; `Valid`; user configuration was not read. |
| PASS | MiniMax Design | Registered main EXE exists; `Valid`. |
| PASS | WPS Office | Registered main EXE exists; `Valid`. |
| FAIL | Adobe Illustrator 2025 | Main EXE exists under `Support Files\Contents\Windows`, but Authenticode is `HashMismatch`; do not treat as healthy. |
| FAIL | Adobe Photoshop 2025 | `Photoshop.exe` exists, but Authenticode is `HashMismatch`. |
| UNKNOWN | Tesseract OCR | `tesseract.exe` exists; signature query returned `UnknownError`. |
| UNKNOWN | KMSpico | `KMSELDI.exe` exists; `UnknownError`. No infection conclusion is supported by this result. |
| UNKNOWN | NVIDIA Graphics Driver | Driver component; registration icon points to a DLL. Install location exists, but this is not a main-app runtime check. |
| UNKNOWN | NVIDIA Install App | Installer component exists and `SETUP.EXE` is `Valid`; this does not validate the installed driver. |
| UNKNOWN | Adobe UXP WebView Support 1.1.0 | Shares a directory with another UXP registration; cannot verify version-specific mapping. |
| UNKNOWN | Adobe UXP WebView Support 1.3.0 | Shares a directory with another UXP registration; cannot verify version-specific mapping. |
| UNKNOWN | Microsoft Visual C++ 2012 x86 | Package-cache installer exists and is `Valid`; runtime completeness not established. |
| UNKNOWN | Microsoft Visual C++ 2012 x64 | Package-cache installer exists and is `Valid`; runtime completeness not established. |
| UNKNOWN | Microsoft Visual C++ 2013 x86 | Package-cache installer exists and is `Valid`; runtime completeness not established. |
| UNKNOWN | Microsoft Visual C++ 2013 x64 | Package-cache installer exists and is `Valid`; runtime completeness not established. |
| UNKNOWN | Microsoft Visual C++ v14 x86 | Package-cache installer exists and is `Valid`; runtime completeness not established. |
| UNKNOWN | Microsoft Visual C++ v14 x64 | Package-cache installer exists and is `Valid`; runtime completeness not established. |
| UNKNOWN | Windows SDK | Cached installer exists and is `Valid`; complete SDK/runtime health not established. |
| UNKNOWN | Penpot Desktop | EXE exists but is `NotSigned`; verify provenance with its publisher. |

## D: registrations

| Status | Software | Static evidence and limit |
|---|---|---|
| PASS | 360 Security | `360Safe.exe` exists; `Valid`. |
| PASS | iFonts | Main EXE exists; `Valid`. |
| PASS | Eagle | `Eagle.exe` exists; `Valid`. |
| PASS | KK Platform | `Platform.exe` exists; `Valid`, registered version matches. |
| PASS | UU accelerator | Launcher exists; `Valid`. |
| PASS | QQ | `QQ.exe` exists; `Valid`. |
| PASS | Steam | `Steam.exe` exists; `Valid`; uninstall/icon fields are not the main EXE. |
| PASS | Baidu Netdisk | `BaiduNetdisk.exe` exists; `Valid`. |
| PASS | Obsidian | `Obsidian.exe` exists; `Valid`. |
| PASS | Feishu | `D:\Feishu\Feishu.exe` exists; file version 7.70.10 matches registration; Authenticode `Valid`. |
| FAIL | LibreOffice | Registered install location points into the Obsidian-Assistance source tree; expected `program\soffice.exe` is missing there. This does not prove no other copy exists elsewhere. |
| PASS (static only) | Visual Studio Code | Earlier snapshot: registered root and `Code.exe` missing. Recorded repair follow-up: version 1.131.0, existing executable and Microsoft Authenticode `Valid`; GUI/runtime remains `UNVERIFIED`. |
| UNKNOWN | FlyintPro | EXE exists but `NotSigned`; source/provenance not established. |
| UNKNOWN | CC Switch | EXE exists but `NotSigned`; source/provenance not established. |
| UNKNOWN | Storm Player | EXE exists but `NotSigned`; source/provenance not established. |
| UNKNOWN | DSH Desktop | EXE exists but `NotSigned`; source/provenance not established. |

Separate D: version reconciliation found Baidu Netdisk registration/file versions 8.5.5 / 8.6.3.101 (uninstaller 8.5.8.105), and 360 Security registration/file versions 15.0.3.1005 / 15.0.0.2041. These may reflect upgrade residue; no installer or registry change was made. DSH Desktop is a DSH distribution/user-data tree, not a DSH source repository.

## Host-level checks and limits

- C: and D: report NTFS `Healthy/OK`; this does not prove every application works.
- The current shell token is not elevated. Current DISM `ScanHealth` failed with error 740; SFC output was not reliably decoded. Current system-file health is `UNVERIFIED`.
- Defender service is `Stopped/Manual`; the SecurityCenter2 provider query in the latest pass returned no rows. Active antivirus provider and protection freshness are `UNKNOWN`.

## Latest readback correction

The 42-registration count and Feishu row at the top supersede the earlier same-day 41-registration snapshot. A newer `root/SecurityCenter2:AntiVirusProduct` read returned both 360 Security and Windows Defender provider rows (so the earlier empty result was transient/stale). Defender remains `Stopped/Manual`, `Get-MpComputerStatus` shows enabled protections false with signature/update timestamps null. 360 service/process evidence indicates signed components are running, but the active provider's freshness and full protection effectiveness remain `UNKNOWN`.

CBS logs on 2026-09-30 record Windows component corruption detection/repair (1,506 repaired, result 0) and a later `RepairNeeded:no` / `S_OK`; this is positive repair evidence, but the latest pass did not run a new elevated DISM/SFC verification. System event review also found an unexpected shutdown, Intel service start failures, and an OpenAI.Codex update failure. Photoshop and Illustrator still report `HashMismatch`; no Adobe repair was executed. These unresolved items prevent a claim that all C: software/system health is PASS.
- During this read-only inventory pass, no application was launched and no registry, service, antivirus setting or application file was changed. This excludes the separate VS Code installation and audit-started window recorded in the follow-up reports. No user configuration/session contents were read. This pass did not access E:/F:; the separate C-audit capacity-metadata incident remains disclosed in `system-software-and-storage-continuation-20260930.md`.
- Full C/D software health remains `UNVERIFIED`; this inventory only covers the scoped uninstall registrations and selected executable/signature pairs.

## Follow-up readback after VS Code repair — 2026-09-30

- `D:\Programs\Microsoft VS Code\Code.exe` now exists, reports file version `1.131.0`, and has Authenticode status `Valid` with Microsoft Corporation as signer. This supersedes the earlier missing-executable `FAIL` for static path/signature checks only; GUI launch/runtime remains unverified.
- A fresh `Get-Volume -DriveLetter C,D` read reports both NTFS volumes `Healthy` / `OK`. At that snapshot C: had 261,722,128,384 B free and D: had 181,128,339,456 B free; free space is time-varying.
- A fresh Security Center query lists 360 Security and Windows Defender as registered antivirus providers. `Get-MpComputerStatus` reports Defender service, antivirus, real-time, behavior, IOAV and antispyware protections all disabled, with no signature-update timestamp. This does not establish 360's protection freshness or effectiveness; active antivirus health remains `UNKNOWN`.
- No application settings, services or registry values were changed during this readback. E:/F: were not queried.
