# AGENTS.md - 星环知识平台（ArcheAxis Knowledge）Operating Guide

> 全局执行标准（跨软件跨项目）：见 WORK-LAB `00-governance/global-execution-standard.md`（执行生命周期：理解→扫技能→分片→执行→验证→落地；全局边界：E盘禁访/数据不外溢/官方优先/全功率）。
> 经验教训铁律（核实优先/治理最小化/官方优先）：见本项目 `LESSONS_LEARNED.md`。

This file is the public, sanitized operating configuration for agent work inside
this repository. It describes how to work on ArcheAxis Knowledge — a local-first,
evidence-driven, bidirectional Human–AI Learning & Trusted-Knowledge Workspace —
without exposing credentials, private keys, tokens, machine-specific secrets, or
personal files. Config authority is indexed in `docs/CONFIGURATION_AUTHORITY_INDEX.md`.

## 1. Project Mission

ArcheAxis Knowledge is a local-first, evidence-driven, bidirectional Human–AI
Learning & Trusted-Knowledge Workspace. The current minimum closed loop is broad
compatibility: absorbing mature capabilities from comparable software. The first
high-fidelity vertical slice is Obsidian Vault / Markdown / JSON Canvas.
Implementation prefers legal dependencies, SDKs/APIs/CLIs, fork/vendor, and
Adapter/sidecar before building from scratch. Heavy blueprints (general Agent
Runtime, multi-agent, Marketplace, 3D/VR, enterprise collaboration) are deferred;
3D/VR/AR, animation, simulation and spatial memory are retained as binding
long-term capabilities (see `docs/truth/CAPABILITY_ATLAS_V2.yaml`). Product
identity and naming are locked by `docs/truth/NAMING_CONTRACT_V2.md`
(ArcheAxis Knowledge / 星环知识平台).

Legacy systems (Knowledge-Base, Inspiration-Research, Cognitive-OS, Obsidian)
exist as compatibility surfaces only; current routing, capability truth and
migration history are documented under `docs/truth/` and `workspace/intake/`.

## 2. Configuration Categories

| Category | Repository Location | Purpose |
| --- | --- | --- |
| Runtime defaults | `config/defaults.yaml` | App thresholds, execution defaults, memory backend (single default truth) |
| Runtime profiles | `config/profiles/*.yaml` | Per-environment differences only |
| Model settings | `config/models.yaml` | Product-internal model/embedding adapter config (not agent provider routing) |
| Tool registry | `config/tools.yaml` | Product-internal tool names and risk levels |
| Verification policy | `docs/VERIFICATION_POLICY.md` | Test cadence, review triggers, evidence retention |
| Gate registry | `.worklab/gate-registry.v1.yaml` | Stable Gate IDs |
| Path risk profile | `.worklab/project-validation.v1.yaml` | Changed-path → risk class → Gate mapping |

## 3. Safety Rules

- Work inside the current repository unless the user explicitly names another exact project path.
- Do not access `E:\` unless the user explicitly confirms the exact path, action, and impact range.
- Do not upload or print secrets: `.env`, `.codex`, SSH private keys, API keys, tokens, cookies, credentials, or password files.
- Do not commit runtime memory, local caches, virtual environments, logs, or generated databases.
- Project-owned development outputs use the ignored `<repo>/.project-local/` root through `scripts/runtime/dev.py`. PowerShell 7: `scripts/ci/run_tests.ps1`; Bash: `scripts/ci/run_tests.sh`. Each worktree/run has separate temporary files and evidence. `.hermes/` is preserved legacy material: no new development writes and no blanket deletion. Agent-private state and product workspaces are separate ownership classes.
- Do not claim ownership of Hermes, Codex, CC Switch, Workflow-assistance, GitHub delegation, session, cron, Kanban, or other workflow-infrastructure files merely because their names mention this project.
- Files found in `%TEMP%`, a user home, or another project are ambiguous until content, Git worktree, process, and generation command establish ownership; preserve and mark unresolved rather than delete or move them.
- Prefer small, auditable changes that can be reverted with one commit.
- Do not use destructive actions (recursive deletion, hard reset, forced push, mass overwrite) unless the user separately confirms scope.

## 4. Git Rules

- `git status --short` before modifying; `git diff --stat` + `git status --short` after.
- Use explicit paths when staging; avoid `git add .`.
- Do not commit or push unrelated local changes; do not force push.
- Commit messages describe the functional scope.

## 5. Network Rules

- Default work is local. Network access is allowed when the user asks to pull, push, clone, verify remote status, or fetch current external information.
- GitHub remote for this repository uses HTTPS: `https://github.com/DTALEX66/ArcheAxis-Knowledge-OS.git`.

## 6. Implementation Workflow

The user-approved active plan is the 2026-09-06-r1 Full Loop TaskPack; progress and
source provenance are in `docs/authority/taskpack-0906/EXECUTION.md`. The formal
desktop is `apps/ArcheAxis.Desktop/` (C#/Avalonia), with the separate vNext Rust
Core database and isolated Python workers. `frontend/`, `src-tauri/`, `desktop/`
and the existing Green v0.6.14 remain recovery/behavior references. Do not dual-write
legacy and vNext databases. The older G0/shadow-cutover route is superseded by
`DECISION_SUPERSESSION_LEDGER.yaml`; historical receipts retain their tested SHA.

1. Confirm repository status.
2. Read the relevant files first.
3. Make the smallest coherent change.
4. Add an intake note under `workspace/intake/` when the change affects framework direction.
5. Run the smallest useful verification.
6. Report what changed, what was tested, what remains uncertain, and how to roll back.

## 7. Current System Boundaries

- Core file ingestion reads only inside the project root.
- Multi-format adapters support text, PDF, Office, HTML, images, media and canvas through optional engines; scanned PDFs require OCR (TESSDATA_PREFIX set).
- Resumable directory conversion records every latest file state in a JSONL manifest; failures retry.
- High-risk content routes to `REVIEW` before action.
- Current tool execution is conservative and uses a risk registry.
- Accuracy claims require human truth/prediction pairs; model confidence is not accuracy.
- Evidence images require a semantic text match; random pages or frames are not evidence.

## 8. Private Configuration Not Stored Here

- Real Codex desktop settings and session state
- SSH private keys and GitHub credentials
- API keys and model provider credentials
- `.env`, `.npmrc`, `.pypirc`, cookies, and browser data
- Local Obsidian vault paths unless the user explicitly chooses a project-local import/export path
- Runtime `data/`, memory stores, logs, caches, and virtual environments

## 9. External Coordination (Optional)

WORK-LAB is an independent repository that may optionally coordinate this project
via stable CLI/API protocol; it is never a runtime prerequisite. This project
runs standalone locally, in CI, RC and Release without WORK-LAB. Cross-repo
changes are two tasks, two branches, two PRs, two test suites, two rollbacks.
`.codex.example/config.example.toml` is a minimal project pointer only; real
`.codex/` state remains private and uncommitted.
