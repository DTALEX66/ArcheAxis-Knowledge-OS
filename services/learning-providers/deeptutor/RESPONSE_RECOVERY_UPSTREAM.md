# DeepTutor private final-response recovery candidate

`response_recovery.py` is an unregistered, offline adapter. It does not modify
the existing question-turn worker or its strict agentic-loop behavior, start a
model, connect to Core, write a database, dispatch a tool, or make a network
request. Its input and result are caller-supplied, unverified candidates.

## Source and license

The Owner-supplied `DeepTutor-1.7.1.zip` has SHA-256
`9614f50cfe2cef476c25ad378631f5a5d15a7c0f3f54ef1fa3180c8f41286262`.
The original `deeptutor/runtime/agentic/labels.py` is preserved byte-for-byte as
`upstream/agentic_labels.py` (7,559 bytes, SHA-256
`5b72f0efb922741b8dde7c9082c12778dfb21cf087c431d872d7f4c806705c05`). The
retained Apache-2.0 `LICENSE` has SHA-256
`cd2f54e1e5066644023203dcbd956776a9f4ef6eb8b6225afe1ffa2d380fede4`; the
archive's retained `upstream/THIRD_PARTY_NOTICES.md` has SHA-256
`d59dc01b43d1916db9418bc1ebcc213a4859047dc07e2766c4234391f9db033c`.
The current repository source registers this raw member in the byte-preserving
Git attributes, SBOM source list and third-party notices. The corresponding
project gates, a shared checkout and a release remain separately unverified.

The adapter checks bounded source bytes and observed file identities, then
compiles only the original label constants and `strip_label_probe_prefix`,
`classify_label`, `recover_finished_label`, and `find_inline_labels`. It does
not execute the upstream module's top level. A concurrent filesystem swap is
not proven impossible merely because the observed checks pass.

For question validation it selects the existing strict response validator from
the pinned `question_turn_worker.py` without executing that worker's top level;
the pinned `question_normalizer.py` supplies its existing original question
parser, normalizer and issue checks from `upstream/question_pipeline.py`. This
path requires only the Python standard library and the Python version already
needed by the normalizer's `StrEnum`; it does not use PyYAML or construct a
prompt. Changed or missing pinned sources fail closed until deliberately reviewed
and repinned.

## Explicit recovery policy

Call `prepare_response(content_bytes, question_type, *, completed,
finish_reason, tool_calls, function_call, allow_recovery=False,
allow_parser_fallback=False)` with exact
UTF-8 content bytes, one of the six existing question types, and explicit
caller declarations. `completed` must be `True`, `finish_reason` must be
`"stop"`, `tool_calls` must be `None` or an empty list, and `function_call`
must be `None`. These values are **caller declarations**, not proof that a
provider finished or emitted no tool calls. Unknown/missing Python arguments,
nonempty calls, malformed or oversized input are rejected.

The pinned upstream `classify_label(..., final=True)` runs first. A strict
`FINISH` is validated without calling recovery or changing the original bytes;
strict `THINK` and `TOOL` are rejected. If the strict classifier fails, the
default is `RECOVERY_DISABLED`. Only explicit `allow_recovery=True` permits a
call to the upstream research-path `recover_finished_label`. The adapter accepts
only the narrower, unambiguous first-line subset of one to three opening
backticks, `FINISH`, zero to three closing backticks and LF or CRLF. After that
line only JSON whitespace may be removed before the body; prefaces, cross-line
labels and extra punctuation are rejected. Other forms the original recovery
helper might accept are intentionally unsupported. A second action label is
rejected.

The resulting body must be a strict JSON object: duplicate keys, non-finite
numbers, trailing prose, fenced JSON, unknown fields, incomplete questions,
invalid question types and ambiguous choice aliases are rejected. Existing
strict question rules and the original normalizer run on the same body; the
question and options are compared to that body. This is an additional adapter
policy. It is **not** evidence that the original question agentic loop would
automatically recover this label: the original question loop calls the strict
classifier and its own retry path, not this research recovery helper.

The original text parser scans the entire response for its first Markdown
fence, including inside JSON string values. A valid question containing an
embedded code fence can therefore be parsed as the wrong object or rejected.
By default this adapter rejects any mismatch between that parser's object and
the strictly decoded object. The separate `allow_parser_fallback=False` option
can be explicitly enabled without enabling label recovery. Only when the first
match of the **same pinned original regex and flags** is proven to lie entirely
inside one original JSON string token may the strictly decoded, already
validated object go directly to the original normalization and issue checks.
All retained fields are independently checked against the same body and the
original supported trim/type rules. A cross-token match, parser exception,
changed source, invalid input, nonempty issues or normalization mismatch never
enables this fallback. No synthetic `pipeline_result` is constructed. Both the
metadata and private receipt identify the actual parser route as
`ORIGINAL_MODEL_TEXT_PARSER` or `OPT_IN_STRICT_OBJECT_NORMALIZATION`.

## Private receipt and limits

The returned `PrivateRecovery` hides its contents in `repr`. `report()` returns
fixed metadata without the content, answers or low-entropy digests. Explicit
private getters return the original bytes, exact removed prefix, body suffix and
`private_receipt()`. The private receipt contains the original content in
base64, its SHA-256, the body byte offset and digest, the exact removed prefix,
the normalized candidate including the answer key, and field-level
normalization changes. The original content is reconstructible exactly from
the private receipt. Base64 is not encryption, and unsalted hashes may reveal
low-entropy material; neither getter nor receipt is safe to log by default.

Content is limited to 180,000 UTF-8 bytes and a serialized private receipt to
512 KiB; malformed structures and over-limit output are refused with fixed
reason codes. This adapter itself does not persist inputs or results; callers
or external systems may already have stored them. No secure erasure,
sandboxing, or access control is provided. The supplied content
is not the original provider envelope, full HTTP body, or preserved reasoning.
The candidate does not establish factual grounding, answer correctness,
provider identity, authorization or independent mastery. Non-choice questions
remain ungraded; ordinary question text or options may themselves reveal an
answer.

The accompanying tests use independently authored synthetic examples only.
They do not include the stored local-model replies or establish a real model,
Core, production-process, installed-runtime or Owner acceptance result.
