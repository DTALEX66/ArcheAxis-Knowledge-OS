# Configuration Catalog

This folder indexes active, public configuration. It never contains local Codex sessions, credentials, provider secrets, SSH keys, or personal paths.

## Active Sources of Truth

| Concern | File | Notes |
| --- | --- | --- |
| Agent scope and safety | `AGENTS.md` | Auto-discovered repository operating rules |
| Verification and review cadence | `docs/VERIFICATION_POLICY.md` | When to run each gate and require frozen review |
| Codex execution reliability | `docs/CODEX_EXECUTION_RELIABILITY.md` | Windows shell, Git, environment, cleanup, and evidence rules |
| Runtime settings | `config/settings.yaml` | Application defaults |
| Model placeholders | `config/models.yaml` | Runtime provider placeholders, not agent routing |
| Tool risk registry | `config/tools.yaml` | Runtime tool names and risk levels |
| Portable Codex example | `.codex.example/config.example.toml` | Optional template only; never real local state |
| Intake records | `workspace/intake/*.md` | Historical design/implementation evidence, not active policy |

## Boundaries

- `AGENTS.md`, `docs/VERIFICATION_POLICY.md`, and
  `docs/CODEX_EXECUTION_RELIABILITY.md` are the only active agent
  operating-policy sources. Their ownership is scope/safety, verification
  cadence, and execution reliability respectively; avoid duplicating detailed
  rules across them.
- `.codex.example/` is a non-secret example. Real `.codex/` state remains ignored.
- Runtime configuration under `config/` is consumed by the application; it must not duplicate agent behavior or Git/review policy.
- Historical intake and migration reports may mention retired files as past evidence; they must state when the design is superseded.
- Private values belong in ignored local environment/configuration, never committed templates with real values.
