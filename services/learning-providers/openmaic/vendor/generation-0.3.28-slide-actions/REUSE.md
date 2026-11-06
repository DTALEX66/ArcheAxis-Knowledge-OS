# OpenMAIC slide actions: provenance and limits

This is the donor's slide action branch, retained for a two-stage prompt
replay: capture the original slide-action prompt, then replay the declared
local model's reply through the same original branch. It is not the complete
`generateSceneActions` function, model generation, a Core task, or permission
to execute or render an action.

## Retained upstream code

The Owner-provided `OpenMAIC-1.3.0.zip` has SHA-256
`7cea2a5850083bdc261114d8433daa6ea24c1c0157beae3939a2e9fac3a98f40`.
`@openmaic/generation` 0.3.28 and `@openmaic/dsl` 0.12.0 are MIT licensed; both
original licenses and package manifests are retained. The exact upstream
`src/action-parser.ts`, `src/prompt-formatters.ts`, slide action prompt
templates and speech snippet are retained here. The full upstream
`scene-generator.ts` remains at
`../scene-content-0.3.28-original/generation/src/scene-generator.ts`.

`slide-actions-functions.ts` embeds byte-identical upstream source lines
1781–1783 (options, logger and agents), 1793–1821 (the slide branch), and the
complete helper functions at 1943–1965 (`formatElementsForPrompt`),
1984–2035 (`processActions`) and 2040–2066 (`generateDefaultSlideActions`).
Their hashes are in `ORIGINALS.json`. AAOS adds the slide-only wrapper,
imports, a prompt-root adapter and a wrapper around the original action parser
which records its result count. Branch and helper bodies are unchanged.

The original branch passes `content.elements` to `processActions`, which
rewrites a spotlight target that is not a mounted element to the first element.
That rewrite stays in the donor code; the AAOS worker reports it as a
transformation and Core refuses any focus action whose target is not a real
element. The upstream parser tries exact JSON, then `jsonrepair`, then
`partial-json`, may drop malformed items, trim speech and truncate after the
first discussion. If it returns no actions, the original branch generates a
fixed default slide narration; this worker never admits that fallback as model
output. Generated IDs are random.

## Admission boundary

Only `speech`, `spotlight` and `laser` actions are admitted. Every other named
verb (`play_video`, `discussion`, whiteboard and widget actions) is refused by
name, and a reply whose parsed items do not map one-to-one onto the admitted
actions is quarantined. Nothing is executed or rendered; the scene candidate
stays inert until human review.

## Locked npm members

`../npm/` retains the exact `nanoid`, `jsonrepair` and `partial-json` members,
their licenses and manifests; identities are checked before import. Identity
checks do not create a process sandbox or eliminate the check-to-use race.
