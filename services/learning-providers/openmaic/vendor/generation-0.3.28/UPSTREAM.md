# OpenMAIC scene builder source

- Source: `OpenMAIC-1.3.0/packages/@openmaic/generation/src/scene-builder.ts` from the Owner-provided archive, `@openmaic/generation` version `0.3.28`.
- Archive SHA-256: `7cea2a5850083bdc261114d8433daa6ea24c1c0157beae3939a2e9fac3a98f40`.
- Original member SHA-256: `4995900143631447590b9d212fd7c5e644fc42ad734f8463ae05aced7b7f1c5b`.
- Adapted member SHA-256: `e550ed528f9a017ea0fa1f9cc4a01f7eb22d541d5ada067967d3434393d1bf0a`.
- Modification: the single runtime import `nanoid` points to `./nanoid.mjs`, an AAOS Node `crypto.randomBytes` adapter. Original TypeScript type-only imports remain unchanged; Node strips them at runtime. The npm package and renderer are not installed by this copy.
- The original MIT license and copyright are retained in `LICENSE` (SHA-256 `ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19`).
- A supplied `sceneId` fixes the scene's logical ID. For slides, upstream still assigns a fresh canvas ID and uses `Date.now()` for timestamps, so repeated execution is not byte-identical. Core-owned first-result replay and task lifecycle are not yet connected.
