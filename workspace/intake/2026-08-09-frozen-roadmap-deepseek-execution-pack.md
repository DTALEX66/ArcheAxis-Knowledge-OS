# Frozen roadmap and DeepSeek execution pack intake

Date: 2026-08-09

## Decision

The repository now separates long-range execution governance into three artifacts:

1. an immutable task-definition baseline;
2. an append-only status and evidence log;
3. a resumable execution protocol tailored for a long-running coding model.

This prevents status reporting, implementation discoveries, and model-generated summaries from rewriting the comparison baseline. A new baseline version requires explicit owner approval; the original remains in Git history and is protected by a repository convention hash check.

## Scope

This intake adds planning and governance artifacts only. It does not claim that any roadmap implementation task, release gate, Windows installed flow, or future Horizon is complete.

The execution baseline preserves the repository safety boundaries, open-source-first decision order, Windows-first qualification, single-writer rule, exact-SHA evidence requirement, and deferral of general agents, multi-agent autonomy, Marketplace, 3D/VR, sync, and enterprise work.

## Update protocol

Future progress is appended to `docs/truth/EXECUTION_STATUS_LOG.md`. The frozen task list is never edited for ordinary progress, corrections, blockers, or new findings. Proposed scope changes are recorded as change proposals until the owner approves a new versioned baseline.
