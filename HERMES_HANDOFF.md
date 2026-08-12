# Hermes handoff — archeaxis-workspace

Generated: 2026-07-23

## Current continuation point

- Repository: `D:\All projects\ArcheAxis-Knowledge-OS`
- Branch: `feat/runtime-evaluation-sleep-leases`
- Cloud target: `git@github.com:DTALEX66/ArcheAxis-Knowledge-OS.git`
- The branch contains the governed runtime/sleep-loop release train. Before
  resuming any work, re-check `git status --short --branch`, the exact HEAD,
  and the associated GitHub Actions result.

## Completed in this continuation

- Audited project-local and external temporary storage. Project size was
  reduced from 7.315 GiB to approximately 4.232 GiB without deleting runtime
  data, migration evidence, the desktop Python runtime, or Visual Studio Build
  Tools.
- Moved the Playwright browser runtime to
  `D:\All projects\OS configuration\toolchains\playwright`; activation
  scripts and the user environment now set `PLAYWRIGHT_BROWSERS_PATH`.
  Chromium launch was verified both before and after removing the project copy.
- Integrated the real ArcheAxis benchmark TaskPack under
  `.hermes/task-artifacts/benchmarks/AXOS-KB-BENCHMARK-001/`. The registry
  validates 14 cases and 14 sources. No benchmark input has been downloaded or
  written into the formal knowledge base.

## Current release scope

The candidate release closes two governed-runtime integrity gaps:

1. A reviewed artifact runtime trace is persisted to the caller-selected
   SQLite database, together with its evaluation candidate, rather than being
   split across the supplied database and the global runtime database.
2. Sleep runtime dependency proof is a scheduler-issued process-local capability
   bound to scheduler-read durable task state, run, task and the persisted
   `dependencies_json` set,
   then revalidated against SQLite and the current unexpired task lease
   immediately before runtime execution.
   Dependency IDs supplied in an arbitrary task payload are not trusted.

The candidate includes tests for both boundaries, durable trace readback,
dependency-proof rejection, scheduler-to-runtime handoff, leases, replay-safe
recovery, and unknown write outcomes.

## Next operational task

After the exact candidate commit is green in GitHub Actions, DeepSeek should
run only Wave 1 of the benchmark using:

```text
.hermes/task-artifacts/benchmarks/AXOS-KB-BENCHMARK-001/DEEPSEEK_WAVE1_HANDOFF.md
```

Wave 1 is limited to `A0-DOCX-001`, `A0-DOCX-002`, `A1-XLSX-001`, and
`A1-XLSX-002`. It must retain source URL, resolved URL, timestamp, content
type, byte count, license and SHA-256; write output only below
`.hermes/task-runtime/benchmarks/AXOS-KB-BENCHMARK-001/<run-id>/`; and stop
before Wave 2. Unverified model output remains Candidate, never Ground Truth.

## Boundaries

- Do not access or modify E: without a new exact user authorization.
- Do not use Obsidian-Assistance as a source, migration target, or test target.
- Do not commit `.hermes/` runtime data, generated databases, logs, caches,
  virtual environments, browser binaries, credentials, or benchmark downloads.
- Review and gate a frozen staged tree. Report CI only for its exact commit
  SHA; do not reuse a result for a later edited tree.
