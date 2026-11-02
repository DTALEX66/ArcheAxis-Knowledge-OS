# OpenMAIC text slide reply candidate

This unregistered, offline candidate accepts a caller-supplied reply and
directly invokes two preserved, unchanged upstream functions:

- `@openmaic/generation` 0.3.28 `parseJsonResponse` from
  `vendor/scene-content-0.3.28-original/generation/src/json-repair.ts`.
- `@openmaic/dsl` 0.12.0 `normalizeElement` from
  `vendor/scene-content-0.3.28-original/dsl/src/normalize.ts`.

The corresponding OpenMAIC 1.3.0 originals and package licenses are MIT;
the already preserved `jsonrepair` 3.13.3 dependency is ISC. The worker checks
the fixed original manifests, actual TS files, package metadata and licenses,
and the exact required `jsonrepair` ESM dependency members against their
recorded SHA-256 values. Node's module hook maps only these listed imports.
There is no installation, package script, new dependency, Core route or model
call. This source-only adapter is separate from the quiz replay and the
scene-shaped slide normalizer: it can inspect the raw reply before a scene or
canvas exists.

The worker expects one bounded UTF-8 JSON frame with schema
`archeaxis.openmaic-slide-reply/v1`, canonical base64 `reply_utf8_base64`, and
boolean `include_private`. It allows at most 32,768 frame bytes and 16,384 reply
bytes. The caller keeps the original bytes. Default output contains only fixed
status and boundary fields, never the reply or parsed result. With explicit
`include_private: true`, a valid frame returns the exact reply bytes in base64,
byte count and SHA-256, as well as a serializable upstream observation and
counts of upstream diagnostic levels. The wrapper discards all original logger
arguments: the upstream parser can otherwise include raw response excerpts in
logs. A non-serializable observation is marked `UNREPRESENTABLE`, not silently
converted. If the frame or source identity itself fails, private detail is not
returned and the caller must retain its original input.

For eligible text elements the private candidate also includes the normalized
JSON bytes and the precise fields where the original DSL filled or replaced an
empty font name/color. Re-serialization can change whitespace and key order;
the original reply remains separately available. Upstream parser fallbacks may
extract fenced JSON, repair malformed input or silently accept duplicate keys.
Their actual result is retained as a private observation where representable,
but the candidate quarantines anything that is not one complete strict JSON
value with unique decoded object keys. This includes extracted/repaired text,
unknown fields, unsupported element types and unrepresentable values; no
derived candidate is returned for them.

Numbers must also survive the conservative JavaScript lexical round trip
`JSON.stringify(Number(token)) === token`, and be finite. This rejects, for
example, `1.0`, `1e3` and `-0` even where they are otherwise valid JSON. Passing
this test does **not** prove a decimal value has an exact binary floating-point
representation: `0.1` is one example. Original bytes are preserved so a later
consumer can make its own accuracy decision.

The admitted envelope has `elements` and optional solid `background` and
nonempty `remark`. Elements must all be bounded text elements with finite
geometry, zero rotation, nonempty content and only listed fields. Caller IDs
may be absent; when present they must be unique. `normalizeElement` does not
assign IDs or fully validate geometry, so those checks belong to this wrapper.
The original `generateSlideContent` later resets text rotation, assigns new
random IDs and processes other content, including media and KaTeX. This worker
does none of that, does not claim to reproduce the complete generator, and
does not invent a final scene or model result. Empty/missing fonts are the only
admitted changes; unexpected normalizer changes quarantine the reply.

Text element `content` can itself contain rich text or HTML. The worker treats
it as an untrusted string and does not render, execute or sanitize it. A
`CANDIDATE` status is a narrow structural admission, not proof that the content
is safe to render, free of external links or scripts, true, authorized, or
ready for a learner. Any later renderer needs its own appropriate checks.

This file is a **direct Node worker**, not the existing slide prompt/normalize
runner. It does not inherit their per-instance slot, deadline, cancellation,
bounded pipes or child cleanup guarantees. The synthetic tests explicitly
launch the fixed Node with a minimal environment, hold the direct child handle,
bound pipe reads and enforce a deadline; that test harness is not a production
host. A future host must bind worker/runtime identity before startup and own
the child and pipe lifecycle. The worker rejects `NODE_OPTIONS`/`NODE_PATH` if
present after startup, but Node may process options before the worker starts,
so the host must clear them beforehand.

The upstream parser actually processes up to 16 KiB of invalid input before
strict admission. Its CPU time and memory are not proven bounded by an OS
sandbox. Neither source hash checking, Node's hook nor the worker is a network
sandbox or a general I/O monitor; source verification and path import remain
subject to replacement/ancestor races. No claim is made about a local model,
an installed product, durable Core storage or authorization. Raw replies,
observations, diagnostics and even unsalted hashes can disclose private
information and must not be written to ordinary logs or public receipts.

The dedicated target is `tests/integrations/test_openmaic_slide_reply.py`, using
the project test launcher and an explicitly verified `ARCHEAXIS_TEST_NODE`.
Tests use synthetic inputs and isolated copies of the selected preserved files;
they do not run a model or make network requests. Their results are not an
installed-app or full-generation qualification.
