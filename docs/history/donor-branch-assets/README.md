# Donor branch residual assets (preserved 2026-09-18)

Per `docs/current/BRANCH-CONVERGENCE.md` step 2, the files below exist at a
residual local branch tip but have **never existed in `main`**. They are copied
here byte for byte, as historical source material with provenance, so the branch
can later be disposed of without losing the content. Nothing here is absorbed into
the product: no code was ported, and every branch, worktree and remote ref is
unchanged.

Paths that `main` deliberately deleted (retired surfaces) are **not** preserved
here; they were excluded on purpose because they are retired, not missing.
Source command: `git cat-file -p <branch>:<path>`. Files are copied byte for byte.
Note that the repository's `.gitattributes` (`* text=auto eol=lf`, plus
`*.bat/*.cmd/*.ps1 text eol=crlf`) may normalise line endings in the stored blob, so
the `blob sha256` column records the digest of the ORIGINAL bytes and stays the
fidelity reference.

| branch | tip | original path | blob sha256 | bytes |
| --- | --- | --- | --- | --- |
| `agent/phase5-research-knowledge-governance` | `0a5e1bfa` | `app/adapters/research_knowledge.py` | `f1cdc14382aef541…` | 9743 |
| `agent/phase5-research-knowledge-governance` | `0a5e1bfa` | `shared/knowledge_migration.py` | `ab387c5dfc972d7d…` | 10684 |
| `agent/phase5-research-knowledge-governance` | `0a5e1bfa` | `tests/test_research_knowledge_candidate_contract.py` | `4c1fd3618cb3ef6f…` | 4203 |
| `agent/phase5-research-knowledge-governance` | `0a5e1bfa` | `workspace/intake/011_phase5_p01_governed_candidate_checkpoint.md` | `c20e997c03ff35e8…` | 3579 |
| `feat/archeaxis-desktop-a1-violet-core` | `376281c6` | `requirements-ci-adapters.txt` | `e215c62a6e99560e…` | 243 |
| `feat/archeaxis-desktop-a1-violet-core` | `376281c6` | `workspace/intake/2026-07-28-archeaxis-pack-analysis.md` | `dc98024bf5bd038b…` | 8595 |
| `feat/p1-compat-kernel-hardening` | `a4f2de19` | `tests/test_format_capabilities.py` | `442aa9906ea913d7…` | 1105 |
| `feat/p1-compat-kernel-hardening` | `a4f2de19` | `workspace/intake/2026-08-09-multiformat-capability-boundary.md` | `7d960bfb75ddc4a3…` | 2432 |
| `feat/p1-compat-kernel-hardening` | `a4f2de19` | `workspace/intake/2026-08-09-online-learning-corpus.md` | `0b59ae3a4d615e86…` | 1947 |
| `feat/portable-data-root` | `4e1a3ed8` | `scripts/project_env.bat` | `831825bcce144c30…` | 1549 |
| `feat/portable-data-root` | `4e1a3ed8` | `scripts/project_env.ps1` | `7ddfaac273276ebd…` | 1443 |
| `feat/portable-data-root` | `4e1a3ed8` | `scripts/project_env.sh` | `5fda8a7763156fbc…` | 1212 |
| `fix/desktop-close-request-destroy` | `801edea8` | `docs/workflow/HANDOFF_DESKTOP_CLOSE_LIFECYCLE_2026-08-06.md` | `b1c5252df93eb181…` | 3705 |

Total files: 13 across 5 branches.
Excluded as retired-by-main: 8

## Excluded (retired by main, not preserved here)

- `agent/phase5-research-knowledge-governance:docs/NEXT_TASKS.md`
- `feat/archeaxis-desktop-a1-violet-core:app/workspace/ui/assets/app.js`
- `feat/archeaxis-desktop-a1-violet-core:app/workspace/ui/assets/styles.css`
- `feat/archeaxis-desktop-a1-violet-core:app/workspace/ui/index.html`
- `feat/archeaxis-desktop-a1-violet-core:requirements-ci.txt`
- `feat/portable-data-root:app/workspace/ui/assets/app.js`
- `feat/portable-data-root:app/workspace/ui/assets/styles.css`
- `feat/portable-data-root:app/workspace/ui/index.html`

## Review note

These versions are older than main's. Where both sides changed the same file, main
has advanced by hundreds of lines, so nothing here may be applied wholesale. The
content is for semantic review only; absorption decisions belong to the owner or to
CODEX/HERMES.
