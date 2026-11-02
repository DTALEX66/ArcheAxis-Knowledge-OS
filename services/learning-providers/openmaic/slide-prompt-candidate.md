# OpenMAIC slide prompt candidate

This is an **unregistered, private, text-only prompt construction candidate**.
It directly calls the preserved `buildSlideContentPrompt` from the original
OpenMAIC 1.3.0 `@openmaic/generation` 0.3.28 source. It does not call a model,
produce a slide, generate actions, render, read a business database, establish
Core authorization, or persist a result. It is not a product capability.

The worker pins the preserved generation package manifest, MIT license,
package metadata, `src/scene-prompts.ts`, its `prompts/index.ts`, `prompts/loader.ts`
and `interactive-libraries.ts` runtime closure, the two slide templates and
all three referenced media snippets. The checked-in `ORIGINALS.json` records
the corresponding Owner ZIP members. The original `scene-prompts.ts` SHA-256
is `06a030bff670868992e37d131fe30e0358304eaa37c4b8f27246560b98a6f1ec`.
No donor source or template is modified. Each source read is limited to the
observed size plus one byte, up to the local 1,000,000-byte file limit, before
identity and digest checks. The package's `LICENSE` remains the applicable
OpenMAIC MIT license for these originals.

The worker uses a narrow Node `registerHooks` mapping from the original
relative `.js` imports to the matching original `.ts` files. During the
synchronous upstream call, a child-local `node:fs` adapter serves the five
expected template/snippet reads from previously hash-checked buffers and
requires their observed order. The upstream loader expands all three media
snippets **before** it removes disabled conditional sections, so a missing or
changed snippet rejects even though this candidate sets all three media flags
to false. The original loader also evaluates interactive-library values during
construction. The runner does not inherit `INTERACTIVE_ASSET_BASE_URL`,
`NODE_OPTIONS` or `NODE_PATH`; the worker rejects their presence. Unknown
imports and nonlisted template reads reject. The environment is changed only
for the owned child; neither global product settings nor the caller are changed.

The input is UTF-8 JSON, at most 16,384 bytes, with exactly these fields:

```json
{"outline":{"title":"Example","description":"Example","key_points":["One"]},"language_directive":""}
```

There may be at most 20 points. Title is nonblank and at most 1,024 UTF-8
bytes; description at most 6,000; each nonblank point at most 512; language
directive at most 2,000. NUL, unpaired surrogates, duplicate keys, unsupported
fields, invalid UTF-8 and JSON nesting beyond 64 are rejected. Media, agents,
edit instructions and video-only modes are not supported. They are rejected,
not silently discarded; this is not coverage of the original video branch.
The adapter copies the no-media/no-agent/no-edit argument mapping from
`scene-generator.ts` (including numbered key points), and then calls the
unchanged original prompt function. The caller retains the original input.

`slide_prompt_runner.run_candidate(request_json, node_executable=...)` requires
a trusted, explicitly configured Node executable; it never searches PATH.
The pinned executable is the separately verified Node 24.21.0 binary, size
93,580,104 bytes, SHA-256
`ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32`.
This is a local test identity, not evidence that Node or the worker is shipped
or installed with the product. The hash and size do not restrict the binary to
one installation path; an identical copy can pass. The runner rejects lexical
UNC/device paths before any filesystem probe, but cannot establish that a
mapped drive or ancestor reparse point is local. The runner also checks the worker SHA before
launch. Default output is only fixed status/process metadata and contains no
caller prompt, material or input hash. `include_private=True` explicitly
returns the exact generated `system` and `user` strings with their UTF-8 SHA-256
digests. They can contain sensitive material and must not be logged or exposed
as public telemetry. These unsalted hashes can disclose low-entropy contents
through guessing; they compare bytes and do not authenticate input, output,
source or permissions. `CALLER_SUPPLIED_UNVERIFIED` remains the identity scope.

The runner uses a directly spawned child with a minimal environment, no shell,
Windows `CREATE_NO_WINDOW`, a 32,768-byte frame limit, 196,608-byte stdout
limit, 8,192-byte stderr limit, a default 30-second deadline and a per-module
single slot. Cancellation is best effort. A spawn that may have created a
process without returning a handle, unconfirmed child/pipe cleanup, and pipe
close failures remain unknown and retain the slot. The runner only owns and
can reap the direct child; descendant status is `UNKNOWN`. It is not a
cross-process concurrency limit. The standalone worker has no internal stdin
deadline, so callers must use a supervising runner. A zero child exit means
the protocol completed; callers still must inspect `status`.

File hashes and the restricted resolver reduce accidental mismatches but do
not close file replacement races between verification and module import, nor
all ancestor/reparse races. The loader adapter and child process are **not**
an OS sandbox, network isolation, a general I/O monitor, HTML safety filter,
or prompt-injection protection. URLs or asset names in the original prompt do
not demonstrate that any resource exists or is available offline. Node flags
can run before a script begins, so the clean launch environment is essential.
Results and original inputs are private even when they are synthetic in tests.

The dedicated tests compare private prompt strings to a separate synthetic
call of the original function, verify the fixed source closure and each
disabled media snippet, and exercise a bounded staged-file growth race, wrong
Node identity, lexical UNC rejection, unsupported input, environment,
owned-child cancellation, limits and uncertain cleanup. They use the explicit
`ARCHEAXIS_TEST_NODE` selected by the project verification launcher. A suitable
target for a source-consistent project run is
`tests/integrations/test_openmaic_slide_prompt.py`; tests and their process
observations do not qualify the installed app, Core integration or real model.
