# AGENTS.md - Cognitive-OS Agent Operating Guide

This file is the public, sanitized operating configuration for Codex/agent work inside this repository. It describes how an agent should work on Cognitive-OS without exposing local credentials, private keys, tokens, machine-specific secrets, or personal files.

## Rule ownership and precedence

Global Hermes workflow rules own the general execution protocol: single-writer coordination, project-data containment, secret handling, safe editing, testing, and exact-SHA delivery. This file owns only Cognitive-Loop-OS-specific boundaries, architecture facts, and repository conventions. When a global rule and this file overlap, follow the stricter rule and keep the project wording as a concrete exception or example rather than duplicating the global procedure.

## 1. Project Mission

Cognitive-OS is the front runtime for two primary systems:

| System | Role | Current Relationship |
| --- | --- | --- |
| Knowledge-Base | A system for understanding, structure, memory, learning, review, and knowledge reuse. Packaged at `knowledge_base/` in this repository | Receives `KB` routed material |
| Inspiration-Research | B system for research, comparison, inspiration, framework design, and strategy. Packaged at `inspiration_research/`; the hyphenated directory is a deprecated launcher | Receives `IR` routed material |
| Cognitive-OS | Front operating layer that routes information, runs tasks, stores traces, evaluates results, and forms machine lessons | This repository |
| Obsidian | Upstream capture/source layer for a subset of KB inputs | Not the whole system |

The target cognition loop is:

```text
information -> attention -> understanding -> structure -> memory -> learning -> action -> feedback
```

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

## 3. Project-Specific Safety Boundaries

- The external A project named `Obsidian-Assistance` is already audited and absorbed: do not scan, test, modify, synchronize, or use it as a migration target in future Cognitive-Loop-OS work.
- Do not access `E:\` unless the user explicitly confirms the exact path, action, and impact range.
- Project-owned outputs from Cognitive-OS code, tests, ingestion, builds, and reviews must use the project-local ignored runtime/build locations defined by the global project-data boundary; a wrapper is preferred but is not an OS sandbox.
- Do not claim ownership of Hermes, Codex, CC Switch, Workflow-assistance, GitHub delegation, session, cron, Kanban, or other workflow-infrastructure files merely because their names mention this project. Those artifacts remain in their owning workflow directory.
- Files found in `%TEMP%`, a user home, or another project are ambiguous until content, Git worktree, process, and generation command establish ownership; preserve and mark unresolved rather than delete or move them.

## 4. Project-Specific Git Conventions

Before modifying repository files:

```bash
git status --short
```

After modifying repository files:

```bash
git diff --stat
git status --short
```

Upload policy:

- Use explicit paths when staging files.
- Keep the working tree limited to the requested project scope; the global Git safety rules govern force pushes, destructive commands, and unrelated changes.
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

