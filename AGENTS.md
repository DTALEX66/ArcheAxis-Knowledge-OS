# AGENTS.md - ArcheAxis Workspace (Human–AI Learning Workspace) Operating Guide

This file is the public, sanitized operating configuration for Codex/agent work inside this repository. It describes how an agent should work on ArcheAxis Workspace — a local-first, evidence-driven Human–AI Learning Workspace — without exposing local credentials, private keys, tokens, machine-specific secrets, or personal files.

## 1. Project Mission

ArcheAxis Workspace is a local-first, evidence-driven Human–AI Learning & Knowledge
Workspace. The current minimum closed loop is broad compatibility: absorbing
mature capabilities from comparable software. The first high-fidelity vertical
slice is Obsidian Vault / Markdown / JSON Canvas. Implementation prefers legal
dependencies, SDKs/APIs/CLIs, fork/vendor, and Adapter/sidecar before building
from scratch. Heavy blueprints (general Agent Runtime, multi-agent,
Marketplace, 3D/VR, enterprise collaboration) are deferred.

The legacy runtime exposed two supporting surfaces:

| System | Role | Current Relationship |
| --- | --- | --- |
| Knowledge-Base | A system for understanding, structure, memory, learning, review, and knowledge reuse. Packaged at `knowledge_base/` in this repository | Receives `KB` routed material |
| Inspiration-Research | B system for research, comparison, inspiration, framework design, and strategy. Packaged at `inspiration_research/`; the hyphenated directory is a deprecated launcher | Receives `IR` routed material |
| Cognitive-OS | Front operating layer that routes information, runs tasks, stores traces, evaluates results, and forms machine lessons | This repository |
| Obsidian | Upstream capture/source layer for a subset of KB inputs | Not the whole system |

## 2. Configuration Categories

| Category | Repository Location | Purpose |
| --- | --- | --- |
| Runtime settings | `config/settings.yaml` | App thresholds, execution defaults, memory backend |
| Model settings | `config/models.yaml` | Current model/embedding provider placeholders |
| Tool registry | `config/tools.yaml` | Tool names and risk levels |
| Verification policy | `docs/VERIFICATION_POLICY.md` | Test cadence, review triggers, and evidence retention |
| Human/agent guide | `AGENTS.md` | Readable operating rules for Codex and future agents |
| Configuration index | `workspace/configuration/README.md` | Catalog of public vs private configuration categories |
| Intake history | `workspace/intake/` | Stepwise design and implementation log |

## 3. Safety Rules

- Work inside the current repository unless the user explicitly names another exact project path.
- The external A project named `Obsidian-Assistance` is already audited and absorbed: do not scan, test, modify, synchronize, or use it as a migration target in future ArcheAxis Workspace work.
- Do not access `E:\` unless the user explicitly confirms the exact path, action, and impact range.
- Do not upload or print secrets: `.env`, `.codex`, SSH private keys, API keys, tokens, cookies, credentials, or password files.
- Do not commit runtime memory, local caches, virtual environments, logs, or generated databases.
- Project-owned outputs from Cognitive-OS code, tests, ingestion, builds, and reviews must use the project-local ignored runtime/build locations; a wrapper is the preferred containment path but is not an OS sandbox.
- Do not claim ownership of Hermes, Codex, CC Switch, Workflow-assistance, GitHub delegation, session, cron, Kanban, or other workflow-infrastructure files merely because their names mention this project. Those artifacts remain in their owning workflow directory.
- Files found in `%TEMP%`, a user home, or another project are ambiguous until content, Git worktree, process, and generation command establish ownership; preserve and mark unresolved rather than delete or move them.
- Prefer small, auditable changes that can be reverted with one commit.
- Do not use destructive actions such as recursive deletion, hard reset, forced push, or mass overwrite unless the user separately confirms scope.

## 4. Git Rules

Before modifying repository files:

```powershell
git status --short
```

After modifying repository files:

```powershell
git diff --stat
git status --short
```

Upload policy:

- Use explicit paths when staging files.
- Avoid `git add .`.
- Do not commit or push unrelated local changes.
- Do not force push.
- Commit messages should describe the functional scope.

## 5. Network Rules

- Default work should be local.
- Network access is allowed when the user asks to pull, push, clone, verify remote status, or fetch current external information.
- GitHub remote for this repository is expected to use SSH:

```text
git@github.com:DTALEX66/Cognitive-Loop-OS.git
```

## 6. Implementation Workflow

For each implementation round:

1. Confirm repository status.
2. Read the relevant files first.
3. Make the smallest coherent change.
4. Add an intake note under `workspace/intake/` when the change affects framework direction.
5. Run the smallest useful verification.
6. Report what changed, what was tested, what remains uncertain, and how to roll back.

## 7. Current System Boundaries

- Core file ingestion reads only inside the project root.
- Multi-format adapters support text, PDF, Office, HTML and images through optional engines.
- Resumable directory conversion records every latest file state in a JSONL manifest; failures retry.
- High-risk content routes to `REVIEW` before action.
- Current tool execution is conservative and uses a risk registry.
- Accuracy claims require human truth/prediction pairs; model confidence is not accuracy.
- Evidence images require a semantic text match; random pages or frames are not evidence.

## 8. Private Configuration Not Stored Here

The following must stay local and must not be committed:

- Real Codex desktop settings and session state
- SSH private keys and GitHub credentials
- API keys and model provider credentials
- `.env`, `.npmrc`, `.pypirc`, cookies, and browser data
- Local Obsidian vault paths unless the user explicitly chooses a project-local import/export path
- Runtime `data/`, memory stores, logs, caches, and virtual environments

## 9. Codex Configuration

Repository behavior is defined by this file plus `docs/VERIFICATION_POLICY.md`. `.codex.example/config.example.toml` is the only portable Codex template; it is not loaded automatically and contains no credentials. Real `.codex/` state remains private and uncommitted.

