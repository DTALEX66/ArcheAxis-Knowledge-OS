# OpenMAIC quiz replay: provenance and limits

This is an offline, synthetic-response replay of the quiz helper, not the full
`generateSceneContent` function, a model call, a Core task, or an assessment of
whether an answer is correct. No scene actions, media, database or network are
executed by this slice. It does not establish independent mastery.

## OpenMAIC generation 0.3.28

The Owner-provided `OpenMAIC-1.3.0.zip` has SHA-256
`7cea2a5850083bdc261114d8433daa6ea24c1c0157beae3939a2e9fac3a98f40`.
The exact archive prefix is `OpenMAIC-1.3.0/packages/@openmaic/generation/`.
This package is MIT licensed; its original `LICENSE` and `package.json` are
retained here. `ORIGINALS.json` binds the unmodified source and prompt files.

`src/scene-generator.ts` is the complete upstream source member. The exact
upstream lines 914–1108 are embedded without changes in `quiz-functions.ts`:
`generateQuizContent`, `findQuizOptionsContractFailure`,
`normalizeQuizOptions` and `normalizeQuizAnswer`. The excerpt SHA-256 is
`a0efe8acb84c22e66ae3911f45279e5a4875f00cf6a223621a6b5a4e279f98cd`.
AAOS adds imports, a wrapper selecting this directory as the prompt root, and an
export around that excerpt. The enclosing full `generateSceneContent` and all
other content and action generators are **not** included in this adapter.

`templates/quiz-content/system.md`, `templates/quiz-content/user.md`, and
`snippets/json-output-rules.md` are exact archive members. The prompt loader,
logger, JSON parser and their loaded local dependencies are the original
members retained under `../generation-0.3.28-outline/`; that directory's
`ORIGINALS.json` and each member are checked before loading. The model callback
is replaced by an explicit synthetic reply or synthetic failure. Prompt bodies
are not sent anywhere; replay reports only their hashes and lengths.

## Locked third-party dependencies

`../npm/jsonrepair-3.13.3/` is the original ISC-licensed npm package subset;
the retained production files are `lib/esm/index.js`,
`lib/esm/regular/jsonrepair.js`, `lib/esm/utils/JSONRepairError.js`, and
`lib/esm/utils/stringUtils.js`, together with its original `LICENSE.md` and
`package.json`. Archive SRI:
`sha512-BTznj0owIt2CBAH/LTo7+1I5pMvl1e1033LRl/HUowlZmJOIhzC0zbX5bxMngLkfT4WnzPP26QnW5wMr2g9tsQ==`.

`../npm/nanoid-5.1.14/` is the original MIT-licensed npm package subset; the
retained production files are `index.js` and `url-alphabet/index.js`, together
with its original `LICENSE` and `package.json`. Archive SRI:
`sha512-5c8l8kVzqpnDPaicbEop/fV0Q1w16FmbWtVhMqugTozAwYdlIQojWH5a/M7UfziFmGdQRrUdV+EPzc9Xng3VAQ==`.

Both package `SOURCE.json` records retain member hashes and archive provenance;
the selected members were independently compared with the locked archives and
no npm lifecycle scripts were run. The replay checks those exact member bytes,
but a hash check before import is not a process sandbox and does not remove the
check-to-use race. It does not establish an installed Node runtime. Random IDs
from the actual `nanoid` make repeated result bytes non-deterministic.

The original input and synthetic reply remain in successful and rejected
replay results where parsing has succeeded. Repaired JSON is observed only to
report the upstream recovery; it is not admitted as a candidate. Unknown
fields, types and media/action data are refused instead of being silently
projected away. Results are unverified content candidates, not persisted facts
or verified provider grades.
