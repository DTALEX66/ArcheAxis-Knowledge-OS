# OpenMAIC quiz actions replay: provenance and limits

This is an offline, synthetic-response observation of the upstream quiz action
branch. It is not the complete `generateSceneActions` function, model
generation, a Core task, or permission to render or execute an action. Its
inputs, including the exact synthetic reply, remain caller-supplied and are
not verified as canonical material. Prompt text cannot prove that a response
does not reveal an answer; emitted speech requires review.

## Retained upstream code

The Owner-provided `OpenMAIC-1.3.0.zip` has SHA-256
`7cea2a5850083bdc261114d8433daa6ea24c1c0157beae3939a2e9fac3a98f40`.
The exact source prefixes and member identities are in this directory's and
`../dsl-0.12.0-actions/ORIGINALS.json`. `@openmaic/generation` 0.3.28 and
`@openmaic/dsl` 0.12.0 are MIT licensed; both original licenses and package
manifests are retained. The exact upstream `src/action-parser.ts`,
`src/prompt-formatters.ts`, quiz action prompt templates and speech snippet are
retained here. The full upstream `scene-generator.ts` remains at
`../generation-0.3.28-quiz/src/scene-generator.ts`.

`quiz-actions-functions.ts` embeds byte-identical upstream source lines
1781–1783 and 1823–1849 for the quiz branch, plus complete helper functions at
1970–1979, 1984–2035 and 2071–2080. Their hashes are in `ORIGINALS.json`.
AAOS adds the quiz-only wrapper, imports, a prompt-root adapter, and a wrapper
around the original action parser which records its result count. Parser logic,
branch bodies, and helper bodies are unchanged. The original `@openmaic/dsl`
runtime import is resolved to the retained original `src/action.ts`, whose
only import is type-only; the original logger is reused from
`../generation-0.3.28-outline/`. Other scene branches are not supplied.

The upstream parser tries exact JSON, then `jsonrepair`, then `partial-json`.
It may extract an array from surrounding text, drop malformed items, trim
speech, truncate after the first discussion, or remove slide-only spotlight
and laser actions from a quiz. The quiz branch does not supply an action
allowlist. If the parser returns no actions, the original branch generates a
fixed default opening speech. This replay retains the original input, reports
these observations, quarantines recovery/unknown or lossy output, and never
claims fallback speech was supplied by the model. Generated IDs are random.

## Locked npm members

`../npm/partial-json-0.1.7/` contains the actual MIT-licensed npm members
`dist/index.js` and `dist/options.js`, plus `LICENSE` and `package.json`. The
archive SRI is
`sha512-Njv/59hHaokb/hRUjce3Hdv12wd60MtM9Z5Olmn+nehe0QDAsRtRbJPvJ0Z91TusF0SuZRIvnM+S4l6EIP8leA==`.
The archive and all nine original members were independently checked against
the Owner lock and the controlled cache; no npm lifecycle script ran. The
retained CommonJS runtime files have no declared production dependencies.

`../npm/jsonrepair-3.13.3/` supplies its original ISC-licensed
`lib/esm/index.js`, `lib/esm/regular/jsonrepair.js`,
`lib/esm/utils/JSONRepairError.js`, and `lib/esm/utils/stringUtils.js`; its
original license and package manifest are retained.
`../npm/nanoid-5.1.14/` supplies its original MIT-licensed `index.js` and
`url-alphabet/index.js`, with its original license and manifest. Their exact
SRI and member identities remain in the respective `SOURCE.json` files.

Identity checks before import do not create a process sandbox or eliminate
the check-to-use race. No Node installation, Core model integration, network
isolation, persistence or independent learning outcome is established here.
