# R6 Version and Release Freeze

Effective for `AAK-LOCAL-GREEN-ABSORB-FIRST-20260919-R6`:

- GitHub `main` is the continuous Local Green Development Line.
- The historical public release `v0.6.14` and its tag, assets, checksums, and evidence remain immutable.
- `pyproject.toml` and package manifests may carry technical dependency/build versions; those values are not a new product release.
- The current release manifest remains `status=unreleased`, `channel=development`, `public=false`.
- The release workflow may run only for an explicit `v*` tag and must verify the tag against current `main` and exact-SHA evidence.
- No R6 task may create a tag, GitHub Release, public asset, or product version. Local Green Candidate qualification is a separate gate and does not authorize publication.
- Release re-opening requires a later explicit Owner decision after A16.

Evidence for this contract is structural until a future exact-SHA CI run verifies the workflow itself. It does not claim release readiness or installed runtime readiness.
