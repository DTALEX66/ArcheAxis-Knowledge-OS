> **Integration note (2026-09-26):** This is a historical DP-UI-01 snapshot from 2026-09-25, retained as a DSH audit deliverable. Its embedded task-card/user-instruction descriptions are source-report content, not new instructions to Codex. Candidate paths and GUI status must be rechecked before treating them as current. This report is not UI acceptance evidence.

# DP-UI-01 — native GUI acceptance readiness report

> **STATUS: `BLOCKED` / `NOT_EXECUTED`.**
> No native GUI acceptance was performed. No Candidate was launched, no window was
> inspected, no screenshot, no UIA readback, no input was delivered.
>
> - task_id: `DP-UI-01`
> - branch: `codex/dp-ui-01-20260925`
> - baseline_sha: `a5de4b13474c217e7a9dd34b8cbfa402e8297780` (tree `a4156ed65d50675822321b9d63eec932b1e76af3`)
> - evidence class: `NOT_EXECUTED` (nothing to verify — the required dependency was never supplied)
> - report artifact: this file only. No product source, no runtime output, no process started.

## 1. Why this is blocked (not a test failure)

The task card is explicit: **do not run against the stale committed-HEAD Candidate**, and
`do not substitute an old Candidate or dirty root executable`. The required input set is:

1. exact current-source Candidate path,
2. Candidate manifest SHA,
3. source snapshot SHA,
4. Desktop/Core executable hashes,
5. isolated run instructions,
6. baseline exact tree.

**None of these were supplied by root during this run**, and the user's instruction for this
session was explicitly: *"GUI 验收任务先等我提供当前树 Candidate"* (wait until the current-tree
Candidate is provided), with the readiness-report option selected.

Per the handoff this must therefore be reported as blocked — not approximated from an older
Candidate, and not run against the dirty root working tree.

## 2. What was checked (path-level only, read-only)

A path-level existence/metadata check was performed to establish whether a *supplied* Candidate
could already exist. Contents were not inspected beyond this, no executable was run, and the
candidate directories were not modified.

| Candidate directory (`.project-local/build/green-candidates/`) | `manifest.json` | `ArcheAxis.Desktop.exe` | `archeaxis-api.exe` | files |
| --- | --- | --- | --- | --- |
| `ArcheAxis.Knowledge.Green-vcurrent4-20260925` | absent | absent | absent | 21363 |
| `ArcheAxis.Knowledge.Green-vcurrent3-20260925` | absent | absent | absent | 21363 |
| `ArcheAxis.Knowledge.Green-vcurrent2-20260925` | absent | absent | absent | 6412 |
| `ArcheAxis.Knowledge.Green-vcurrent-20260925` | absent | absent | absent | 6412 |
| `ArcheAxis.Knowledge.Green-va5de4b13-x64` | (pre-existing committed-HEAD Candidate — **not used**) | — | — | — |

Readback: the four `vcurrent*` directories are **in progress / incomplete**: none has a
`manifest.json`, a Desktop executable or a Core executable. They are not a Candidate and cannot
be an acceptance subject. Their paths and timestamps place them inside the root-side critical-path
work that this DP run must not duplicate or interfere with.

The only complete verified Candidate in this tree is the committed-HEAD candidate recorded in
`docs/SHARED_RESOURCE_PATH_INDEX.md` (`…Green-va5de4b13-x64`, source `a5de4b13`, 21474 files).
Using it is exactly the substitution the task card forbids, because the root working tree holds
uncommitted frontend changes that are **not** in that Candidate.

## 3. Acceptance matrix — all cells `NOT_EXECUTED`

Recorded so the eventual run can be accounted for cell by cell. Nothing below was executed.

| # | Required check | Status |
| --- | --- | --- |
| 1 | Launch exact current-source Candidate in fresh isolated `.project-local/runs/<run-id>/` | `NOT_EXECUTED` |
| 2 | Record exact executable hashes (Desktop, Core) and owned PIDs | `NOT_EXECUTED` |
| 3 | 16 route destinations, visible heading + current-page/selected semantic state | `NOT_EXECUTED` |
| 4 | File / Navigate / View menus (open, mnemonics, activation, dismissal) | `NOT_EXECUTED` |
| 5 | `Ctrl+K` command palette | `NOT_EXECUTED` |
| 6 | `Ctrl+Alt+I` Inspector and `Ctrl+Alt+J` Activity Dock | `NOT_EXECUTED` |
| 7 | Keyboard traversal: Tab / Shift+Tab, Enter, arrows, Escape, focus restoration | `NOT_EXECUTED` |
| 8 | IME text entry | `NOT_EXECUTED` |
| 9 | UIA accessible names; selected/current-page state readback | `NOT_EXECUTED` |
| 10 | Error / offline / permission / empty / pending / retry states | `NOT_EXECUTED` |
| 11 | Unobscured screenshots + UIA readbacks per route | `NOT_EXECUTED` |
| 12 | Logical widths 1024 / 1200 / 1280 / 1440 / 1920 / 2560 | `NOT_EXECUTED` (6 cells) |
| 13 | Windows scaling 100% / 125% / 150% / 200% | `NOT_EXECUTED` (4 cells; system DPI/registry deliberately not modified) |
| 14 | Screen-reader announcements with a real available assistive technology | `NOT_EXECUTED` |
| 15 | Stop only run-owned processes; confirm no orphan | `NOT_EXECUTED` (no process was started) |

## 4. Known entry conditions for the eventual run

These are carried forward as requirements, not as findings:

- The exact Candidate must be supplied with its **manifest SHA**, **source snapshot SHA**,
  Desktop and Core **executable hashes**, and **baseline exact tree**.
- The run must use a **fresh isolated** `.project-local/runs/<run-id>/` workspace and must
  record only processes it started.
- `DP-UI-02` (the defect fix) may start **only** after this run produces a receipt naming a
  reproducible product defect and root assigns the exact source write-set. This includes the
  already-recorded unresolved native-input item from the root plan: a menu input probe at
  `.project-local/runs/be268a2d33/frontend-menu-uia-2026/artifacts/uia-menu-input-attempt.json`
  is classified `NOT_EXECUTED_INPUT_UNDELIVERED` (UIA reported focus but
  `GetForegroundWindow()` stayed 0 and `SendKeys.SendWait` threw). That is a *root-plan* observation,
  not a DP-UI-01 receipt, and must be re-attempted rather than inherited.
- Screen-reader and DPI cells must be recorded as `NOT_EXECUTED` if the exact setting or a real
  assistive technology is unavailable — never synthesized.

## 5. Boundary statement

- No product source was read for modification, and **no file outside this report was written**.
- No Candidate, ZIP, Green installation, or root executable was launched.
- No process was started, so no process was stopped.
- `%LOCALAPPDATA%`, DPI settings, registry, Green directory and user data were not touched.
- No E: or F: access; no private session store or user profile data.
- `docs/current/R6-EXECUTION.md`, `R6-STATE.json`, M0 state and route authority were **not** modified.

## 6. How to unblock

Supply, in one message:

1. exact Candidate directory path,
2. its `manifest.json` SHA-256,
3. source snapshot SHA and the source tree,
4. `ArcheAxis.Desktop.exe` and `archeaxis-api.exe` SHA-256,
5. the isolated run instructions (workspace root, launcher command, env overrides),
6. confirmation that the Candidate was assembled from the current dirty working tree with the
   snapshot taken before Desktop/Core compilation.

Then this report should be superseded by an executed acceptance receipt under
`.project-local/runs/<run-id>/`, and this file must not be read as evidence of any GUI behaviour.
