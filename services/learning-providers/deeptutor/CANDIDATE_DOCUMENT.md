# DeepTutor private question-document preparation

`candidate_document.py` prepares a private request for the existing Core
Document contract. It does not open a database, make an HTTP request, run a
model or register a provider route. No Core consumption is established by this
adapter or by its synthetic tests.

`prepare_candidate(replay_request, original_response_bytes, material_snapshot,
create_request_id, title)` accepts the existing question-turn **replay** request,
the exact UTF-8 bytes of its final JSON body, a separately selected material
snapshot, a caller-chosen Core create request ID and a title. The UTF-8 body in
the replay request must exactly equal the supplied bytes. The material
`document_id`, positive `version` and `content_sha256` have the Core snapshot
shape, but their existence, currency, source derivation and authorization are
caller declarations here. The template's existing `question_id` is used as-is;
the adapter generates no document, source, question, or authorization ID.

Each call verifies the fixed size and SHA-256 of `question_turn_worker.py`,
compiles it into a fresh private namespace, and executes its pinned upstream
question step in replay mode. A wrapper local to that namespace captures the
complete `QuizPair` returned by the selected original `_payload_to_qa_pair`.
The existing pinned normalizer separately processes the *same* response. The
adapter compares question type, displayed text, options, answer and explanation
between both results and compares the displayed fields with the turn receipt;
any mismatch rejects the candidate. No previously loaded worker module or
shared global is patched. The pin is 24,499 bytes / SHA-256
`e77a572778a1738195684dcaa672c7e68afc316a8ac7e6312f9ae4eb6f958570`;
its own fixed source checks and limitations are described in
`QUESTION_TURN_UPSTREAM.md`. Observed link and file-identity checks do not prove
the absence of every filesystem race or authenticate the Python runtime.

The prompt and final body are still caller-supplied. Their unkeyed SHA-256s do
not authenticate a model, a prior preview, a user selection, a source, or an
authorization. The result is labeled `user_import_unverified`. It does not
establish the correctness of the supplied answer, grounding or independent
mastery, and is not the complete upstream generation pipeline. Distinct
caller inputs can produce the same upstream prompt after normalization.

The result is a `PrivateCandidate` with an intentionally redacted `repr`:

* `original_response_bytes()` returns the exact private response bytes.
* `raw_import_request()` constructs the `name` and `content_base64` body for
  the existing Core source-import API, without sending it.
* `document_create_request(claimed_import_receipt)` requires the ordinary
  `source_id`, `sha256` and `duplicate` receipt shape, checks the SHA against
  those exact bytes, and constructs the existing Core Document create body.
  Its editor contains `attrs.archeaxis_deeptutor_question`, including the
  answer and explanation, and refers to the caller-selected material snapshot.
  The document's `source_id` and `source_revision` refer to the response
  bytes, not to the selected material document. A matching receipt is only a
  caller claim until Core checks the source/CAS and accepts the document.
  Initial ordinary document paragraphs contain the same normalized question,
  then each option as `key. text` in ascending ASCII key order. They contain no
  separate answer-key or explanation field. For non-choice questions the body
  contains only the question. Core does not continuously check that a later
  ordinary edit to the body agrees with the question in `attrs`.
* `report()` returns bounded metadata, including field paths changed by
  upstream normalization and the conversion of absent or null options. It
  explicitly says that Core import, Core write and report persistence have not
  occurred. It does not return answer values or the response digest.

Source import and Document creation are two independent Core calls. If a caller
later imports the source but document creation fails, the source may remain;
this adapter neither rolls it back nor deletes it. The constructed request is a
mutable Python dictionary: a caller can change its question or answer after it
is returned without changing `source_revision`. Core currently checks the
source/CAS identity but does not independently re-derive the candidate from the
raw response. The adapter's consistency check applies at preparation and
initial request construction only; a successful Core write must not be called
verified merely because it carries the same source SHA. A later integration
must compare the actual Core readback against the intended original response
or add a separately reviewed Core check.

Only the strict response fields accepted by the existing turn worker are
considered; unknown fields, duplicate JSON keys and non-finite JSON are
rejected rather than silently discarded. Whitespace and other normalization
changes, and a change to option ordering in the initial body projection, are
reported by field path without original values. JSON whitespace,
member order and original bytes are not represented in the candidate document;
the exact response remains in memory and can be submitted as the source-import
body. The replay envelope's original bytes were not supplied, and plan,
exploration and previous-question context are not preserved in the candidate.
The report itself is not written to Core; a later integration must explicitly
preserve it and verify the raw import and readback if restart recovery matters.

For non-choice questions the original `options: null` becomes `{}` because the
existing Core question schema requires a dictionary. The report records that
conversion and labels grading unassessed. The retained original practice
grader returns `provider_correct: null` for empty options: this is ungraded,
not a positive or negative grade. A subject answer must not be fabricated.

The candidate, raw-import body and Document create body all contain or encode
the answer and can contain private material. They are private handoff objects,
not display receipts, logs, encryption or access control. Even visible question
text or an unkeyed digest can reveal an answer. Do not print them. A caller must
separately obtain the necessary human action and Core authorization; the source
receipt must never be treated as proof of either. Core's ordinary document
reads and exports retain the full editor, including the answer.

The adapter applies the turn worker's 256 KiB request and 180,000-byte final
body limits. The existing normalizer has its own 240,000-byte serialized request
limit, which can reject a body before either outer bound is reached. It does
not fetch dependencies, private files or configuration; callers must run it
with the project interpreter and an appropriate isolated environment.
Preparation is synchronous and invokes the existing turn worker's
`asyncio.run`. It explicitly rejects a call made on a thread with an already
running event loop; such a caller must arrange execution in an appropriate
separate thread or process. Python object privacy or its immutability helpers
are API discipline, not a security boundary against in-process code.

## Explicitly selected label recovery

`prepare_recovered_candidate(replay_request, original_response_bytes,
material_snapshot, create_request_id, title, *, completed, finish_reason,
tool_calls, function_call, allow_recovery=False)` handles a narrower separate
case. It requires an explicit `allow_recovery=True` and caller declarations of
completed content, `finish_reason="stop"`, and no tool or function call. These
are not authenticated provider envelope fields. It checks and privately loads
the fixed `response_recovery.py` (22,259 bytes / SHA-256
`4887e46b88a32b3145535840adf1e215f741b5c41f8b17d903a282c544f9f4fb`), then
actually invokes its restricted upstream label recovery. The label must need
that recovery; a strict-label success is not silently recategorized. The
separate object-parser fallback is always disabled. An original model-text
parser mismatch, unknown error, incomplete or multi-label response is rejected.
See `RESPONSE_RECOVERY_UPSTREAM.md` for the original recovery's narrower scope:
this is not the original question agentic loop accepting the response.

The labeled input is a maximum of 180,000 bytes and must exactly equal the
recovered prefix plus body. The body must exactly equal `response_body` in the
replay request. The existing `prepare_candidate` then executes its complete
question-turn replay and independent pinned normalizer against those body
bytes; the five normalized private fields are also compared against the
independently reconstructed recovery candidate. Non-choice `null` options become
`{}` only for the existing Core question schema, with the earlier ungraded
limitation. No second normalization rule or invented import receipt is used.

For this path, `original_response_bytes()` and `raw_import_request()` contain
the **complete labeled response**, not only the replay body. The suggested new
source name is `deeptutor-question-response.txt`, accurately naming this UTF-8
text rather than JSON. The same `document_create_request` checks the supplied
import receipt against the complete labeled bytes and uses its matching SHA as
`source_revision`. The receipt remains a caller claim unless an authenticated
host actually obtains and checks it from Core. Core can deduplicate identical
source bytes, in which case an older source row may retain a different original
name and MIME; the newly requested `.txt` name does not overwrite it.

`private_recovery_receipt()` provides a fresh in-memory copy of the existing
recovery receipt, including original bytes, removed prefix, byte offset, hashes,
private candidate and normalization changes. It contains an answer and may
contain private material. Neither adapter persists this receipt or proves what
the caller does with it. Core's existing source/CAS can retain the full bytes
and their SHA, but its Document contract does not independently verify that the
candidate, policy choice, completion or no-tool declaration came from those
bytes. Recovery metadata is not stored as a validated Core claim. A later
caller can re-run the pinned policy against retained bytes, but cannot thereby
prove who opted in, the original provider envelope, authorization, or prior
execution. Source import and document creation remain separate operations.

The private receipt, source bytes, document attributes, ordinary document reads,
exports and backups may expose the answer. The question-view projection omits
the direct answer field; it is not an access-control or secrecy guarantee.
Unkeyed hashes may themselves be guessable. This offline preparation does not
make an HTTP request, authenticate a receipt, run a model, register a route or
submit a grade.
