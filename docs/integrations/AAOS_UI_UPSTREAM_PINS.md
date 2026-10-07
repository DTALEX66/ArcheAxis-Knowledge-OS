# AAOS UI taskpack upstream pins — foreign repositories, not local objects

These commits belong to the named upstream repositories. None of them is a Git object in
ArcheAxis-Knowledge-OS, and citing one here is not a claim that it was released by this
project. Verify a pin by cloning that repository and running
`git -C <clone> cat-file -t <commit>`; the file-level provenance of what this repository
actually carries is in `docs/current/AAOS-UI-ASSET-MANIFEST-20261007.json` and the root
`THIRD_PARTY_NOTICES.md`.

`DavidHDev/react-bits` is pinned for reference only: its license is recorded upstream as
NOASSERTION and its current terms restrict component redistribution, so no component from
it is absorbed into the product bundle.

Recovered from the taskpack's `spec/pool-revisions.json` on 2026-10-07; the taskpack ZIP
was not modified.

- Upstream: <https://github.com/DavidHDev/react-bits>
- Commit: `ca44b3f9ee180676a06d7de8ec6bea84cddff85b`
- License: NOASSERTION
- Default branch at pin time: `main`
- Upstream: <https://github.com/ibelick/motion-primitives>
- Commit: `120f64f6ca60348e251f929e9c81f11ccbe45eda`
- License: MIT
- Default branch at pin time: `main`
- Upstream: <https://github.com/magicuidesign/magicui>
- Commit: `cdb348cb4c72a9b54b554d8617801e479fbc8714`
- License: MIT
- Default branch at pin time: `main`
- Upstream: <https://github.com/radix-ui/primitives>
- Commit: `1fe601abb217f23c92253ec1c42fa81b14fa710d`
- License: MIT
- Default branch at pin time: `main`
- Upstream: <https://github.com/shadcn-ui/ui>
- Commit: `debae9baea4d5c6bd0b1a857b09664db4b925818`
- License: MIT
- Default branch at pin time: `main`
- Upstream: <https://github.com/uiverse-io/galaxy>
- Commit: `adbd2adde0a299a3956ea288fb444ec01891ca41`
- License: MIT
- Default branch at pin time: `main`

## Files adapted under these pins

- `frontend/src/components/galaxy-states.css` and `GalaxyStates.tsx` are local adaptations
  of the Galaxy HTML/CSS pool, licensed MIT by the upstream record above.
- `docs/truth/THIRD_PARTY_NOTICES.md` is not part of this contract; the project notice file
  at the repository root carries the attribution and the lock.
