# OpenMAIC scene-content source-only copy

This directory retains selected, unmodified members of the Owner-provided
`OpenMAIC-1.3.0.zip` (SHA-256
`7cea2a5850083bdc261114d8433daa6ea24c1c0157beae3939a2e9fac3a98f40`).
The package identities are `@openmaic/generation` 0.3.28, `@openmaic/dsl`
0.12.0 and `@openmaic/geometry` 0.1.0. Each package includes its original MIT
license, package metadata, TypeScript configuration and an `ORIGINALS.json`
whose paths are relative to that package. `SOURCE.json` identifies every copied
member's exact archive path, byte length and SHA-256.

The selection contains 46 TypeScript files reached by the static runtime
import/export graph from `generation/src/scene-generator.ts`, 16 content
templates, seven snippets, two single-call PBL templates, and nine package
metadata/configuration/license files. Existing separately retained copies are
not modified. The single-call PBL templates are included because the PBL
branch selects them dynamically; `planner-system.md` for a separate fallback,
action templates and other assets are not included.

This is a source-only, finite selection, **not a runnable package**. Type-only
imports and additional source files required by the original full `tsc`
project are not all present. npm runtime packages, a qualified Node runtime,
module resolution and packaged assets are not installed or registered here.
The package contains enums and parameter properties; existing Node type
stripping alone is insufficient. Node's transformation option and a separately
verified TypeScript build have not been tested for this copy. The original
package build scripts can recursively remove `dist`; do not run them in a
shared source directory. Any eventual build must use an isolated, governed
staging directory and independently verify its compiler and dependencies.

No model call, Core task, authorization, persistence, rendering or action
execution is established by copying these files. A manifest or hash check is
not a process sandbox or proof that a file remains unchanged until execution.
Third-party dependency licensing, runtime compatibility and release packaging
remain separate work.
