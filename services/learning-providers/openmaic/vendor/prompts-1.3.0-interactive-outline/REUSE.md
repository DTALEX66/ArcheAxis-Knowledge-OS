# Interactive-outline prompt donor

`ORIGINALS.json` identifies the unmodified prompt assets taken from the
Owner-provided OpenMAIC 1.3.0 archive (`lib/prompts/`): the interactive-outline
system and user templates, the prompt-package README and the upstream MIT
license. The templates are the original app assets, not rewritten approximations.

Rendering uses the already vendored `@openmaic/generation` 0.3.28 prompt loader
(`../generation-0.3.28-outline/src/prompts/`) with this directory passed as its
template root, so no loader is duplicated here. Only
`templates/interactive-outlines/` is selected from the app prompt package.

The adapter never calls a model, never persists a task, never builds a scene and
never authorizes rendering. It renders one prompt for a request and, on replay,
admits a caller-supplied reply into a bounded outline candidate. Repair is the
donor's own json-repair path; a repaired reply is reported as non-exact and any
structural difference is refused rather than trimmed.

Path-based identity checks cannot create a process sandbox or remove replacement
races between verification and import. This is not a packaged runtime.
