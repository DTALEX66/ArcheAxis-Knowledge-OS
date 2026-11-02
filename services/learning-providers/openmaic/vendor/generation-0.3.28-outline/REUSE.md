# Outline-generation donor

`ORIGINALS.json` identifies the unmodified files extracted from the Owner-provided
OpenMAIC 1.3.0 archive, `@openmaic/generation` 0.3.28. The original MIT license
and copyright are retained in `LICENSE`. Prompt templates and snippets are the
original package assets, not rewritten approximations.

The offline replay adapter maps the original imports to the exact runtime members
of `nanoid` 5.1.14 (MIT) and `jsonrepair` 3.13.3 (ISC), each retained under
`../npm/` with its original licence and package manifest. `SOURCE.json` records
the locked archive SRI, audit run, and individual source byte hashes. No npm
scripts or installation were executed. The adapter checks the selected bytes
before import; the check and later import are separate path operations.

The original repair code may observe malformed input, but this adapter never
admits a repaired or ambiguous JSON response as a candidate. Non-exact upstream
parsing outcomes are observations, not successful work.

Before importing the upstream TypeScript, the adapter also checks a fixed digest
for `ORIGINALS.json` and the original byte digest of all 18 listed files. These
path-based checks do not create a process sandbox or eliminate replacement races.

The input is a synthetic response replay, not an actual model call. This isolated
slice does not connect to the Core's model policy, persist a task or replay its
first result, or generate scene content/actions. It is not a packaged runtime.
