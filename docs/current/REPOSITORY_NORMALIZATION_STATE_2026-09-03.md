# Repository Normalization State — 2026-09-03

> Current operational queue for directory hygiene, authority references and
> language-boundary work. This record is evidence-bound: it does not turn a
> local test, a source scan, a cleanup action or a built executable into cloud
> CI, a language cutover, a release or an installed-runtime claim.

## One authority chain

| Decision surface | Binding index | Current operating rule |
| --- | --- | --- |
| Document lookup and truth class | [Documentation authority](../DOCUMENTATION_AUTHORITY_INDEX.md) | Read current records before plans; cite history only as history. |
| Path ownership, cleanup and moves | [Directory authority](../DIRECTORY_AUTHORITY_INDEX.md) | Classify a path and record consumers, rollback and deletion state before moving or removing it. |
| Writer and runtime-language ownership | [Language boundary authority](../LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md) | One aggregate has one writer; no Rust/Python dual writer. |
| Desktop source-to-Green delivery | [Runtime/delivery authority](../RUNTIME_DELIVERY_AUTHORITY_INDEX.md) | Candidate, Green hash readback and visible product-path verification are separate evidence layers. |
| CI and gate selection | [Configuration authority](../CONFIGURATION_AUTHORITY_INDEX.md) | Fast CI, full qualification and release are distinct gates. |

## Current normalization queue

| Priority | Work item | Status on 2026-09-03 | Completion evidence required |
| --- | --- | --- | --- |
| P0 | Prevent transient browser residue from becoming repository noise | Done locally: `.playwright-cli/` is ignored; the verified two-file residue was removed. | `.gitignore` entry plus absence check for the exact directory. |
| P0 | Keep checked-out text consistent with repository EOL policy | Done locally: 44 tracked `eol=lf` paths with stale CRLF/mixed checkout bytes were normalized after rejecting unstaged paths and lone CR; 8 declared Windows command paths retain CRLF. | `.gitattributes`, `git ls-files --eol`, and repository convention check. |
| P0 | Keep generated/runtime data bounded | Active constraint | `.hermes/` only for generated task data; retain build cache/worktrees/runtime packages until an exact inventory authorizes cleanup. |
| P0 | Preserve user runtime data | Binding constraint | Never inspect, alter, move or clean Green `data/`. |
| P1 | Establish a single current index route | Done locally | This state record is linked from document, directory and language authority indexes. |
| P1 | Classify the mixed dirty tree before any publication | Open | Per-path owner/class/verification inventory; do not stage or push unrelated modifications. |
| P1 | Clean only confirmed generated residues | In progress | Exact-path precondition, removal postcondition, and no worktree/runtime dependency. |
| P2 | Close G0 evidence prerequisites | Open: G0-001 remains open | Exact-SHA full qualification and all-format journey receipts; the historical `db13d056` nightly failure is not erased by local passes. |
| P2 | Accelerate language migration safely | G0-only | Static owner/consumer/rejection evidence, then read-only Rust differential reports; Python remains the current writer. |
| P3 | Directory convergence | Not started | AX-DIR-010 inventory rows and explicit move/delete authorization for every path. |

## Language acceleration without semantic risk

The fastest valid route is to remove ambiguity before moving code:

1. Keep React/TypeScript as the product surface, root Rust/Tauri as the
   Windows host, and Python as the current product-domain writer and
   parse/OCR/ASR sidecar.
2. Close the named G0 facts first: exact-SHA full qualification (`G0-001`),
   corpus journey evidence, writer/consumer evidence and rejected-write
   evidence. A full local suite is useful but cannot close the cloud fact.
3. Introduce Rust only as a read-only, differential-report consumer for one
   named aggregate. Retain Python as the sole writer and record two
   zero-semantic-difference receipts before proposing a cutover.
4. Make any later cutover one aggregate at a time with backup, rollback,
   exact-SHA CI and a Windows product-path result. Do not use a directory move
   or a successful compile as a substitute.

## Cleanup boundary

`TRANSIENT_AUTOMATION` paths are generated browser/test session files such as
`.playwright-cli/`. They must be ignored and may be removed only when their
exact path, contents and lack of runtime/worktree role are verified. Rust
`src-tauri/target/`, root `.hermes/` worktrees and the packaged runtime beneath
`.hermes/rt/` are rebuild/performance/runtime assets, not automatically safe
cleanup targets. The size of a cache is not deletion authorization.

## Publication boundary

The current `main` checkout is mixed and dirty. Therefore the safe next
publication unit is a reviewed, explicitly owned path list—not `git add .`.
Before a local/cloud equality claim, record `HEAD`, the intended commit,
`origin/main`, the exact CI SHA and the release/runtime evidence independently.
