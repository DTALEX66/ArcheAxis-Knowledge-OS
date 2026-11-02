# DeepTutor caller-supplied readback comparison

`candidate_readback.py` is an offline, private comparison helper. It does not
send requests, open SQLite, run a model, read credentials, authenticate Core or
authorize a provider. It accepts caller-supplied data, which can be fabricated.
Even a passing comparison says only that those supplied values agree with the
local candidate reconstructed from the caller's replay and response bytes.

`reconcile(replay_request, original_response_bytes, material_snapshot,
create_request_id, title, import_response, original_response, create_response,
document_response, view_response)` takes each response as a `(status, bytes)`
pair. The bytes must be one bounded UTF-8 JSON object, with no duplicate member
names, non-finite numbers or invalid Unicode. JSON structure is additionally
limited to 20,000 structural tokens and 64 nesting levels. The currently
expected statuses and Core response kinds are:

| Argument | Expected | Existing Core response |
| --- | ---: | --- |
| `import_response` | 202 | `/api/v1/imports` response: source ID, SHA-256, duplicate flag |
| `original_response` | 200 | `/api/v1/sources/{source_id}/original`: ID, name, MIME, SHA-256 and base64 bytes |
| `create_response` | 201 | `/api/v1/documents` creation response |
| `document_response` | 200 | The same document's version-1 readback |
| `view_response` | 200 | Human `/api/v1/learning/deeptutor/question-view` response for that snapshot |

An HTTP status is itself a caller declaration here. Non-success is a fixed
stage-specific error; response text is never included in an error. The
question-view endpoint is available as Core HTTP, not one of the current five
Tauri provider-activity commands. The helper does not obtain or use a token.
The formal launch middleware authenticates requests and determines the actor;
this helper cannot tell whether supplied bytes came from it. A real consumer
must obtain responses through the appropriate already-authenticated human host.
Ordinary source and document reads currently are not human-only views and can
contain the full response, answer and explanation.

For each call the helper checks and loads the exact local
`candidate_document.py` (23,478 bytes / SHA-256
`96ad414a1d35e842ad42362ea6ba1327ab7dfd8b3bb06d6e5bab39073a25953c`) in a new
namespace and reruns its pinned question-turn/normalizer path from the same
private bytes. It compares the source ID and SHA across import, source and
document responses, decodes canonical base64, and compares the actual bytes to
the caller-supplied response. A duplicate source can retain a different name;
the name and MIME are not used as content identity. For `duplicate: false`,
the helper also checks Core's new-source ID formula: `src_` plus the first 24
hex characters of SHA-256 over the ASCII bytes of the raw-content SHA-256 hex
string. For `duplicate: true`, the existing source ID is not forced to follow
the new-row formula. Neither calculation authenticates the supplied receipt.

The creation and version-1 document readbacks must refer to the same document
snapshot and source. The document ID is checked against the Core rule
`doc_req_` plus SHA-256 of the supplied `create_request_id`; the checker does
not create an ID or treat the unkeyed calculation as authentication. The
expected candidate attributes, including answer and
explanation, must match; the ordinary paragraphs, generated block IDs, blocks,
ordinals and text projection must agree. Only the Core-added `block_id` is
allowed as a difference from the original paragraph request. Its format and
cross-reference are checked, but its Rust-generated digest is not recomputed.
Other top-level document metadata is not independently validated. The
question-view's document ID/version/content SHA, declared material snapshot,
question and options must match; its provider/authorization flags must retain
their unverified meaning. This finite checker supports documents created by
the candidate builder, not portable-import question documents.

Core `document::append` computes `content_sha256` over the UTF-8 serialization
of the **normalized editor JSON**, after adding block IDs. It is distinct from
the raw-response source SHA. The ordinary document read does not itself use
`read_verified`; question-view does, when it actually runs in Core. This
offline helper verifies the document content SHA's syntax and consistency
across the supplied readbacks only. It does not reproduce Rust JSON
serialization, independently recalculate this SHA, or recompute the view's
`question_version` and `visible_sha256` values. It checks their format only.
Those unkeyed digests can include or reveal low-entropy answer information and
are not secrets or authentication.

The matched response reports the supplied question status as `current` or
`historical`, and the material-reference status as `current`, `historical`, or
`unavailable`; these are claims within the supplied view, not a promise of
future currentness. An unavailable question-view HTTP response has its own
fixed failure code. A valid match never grants new provider execution, proves
the reference material was selected by a human, verifies answer correctness or
establishes source derivation, restart durability, Core authorization or a
real model/worker invocation. Import and document creation remain separate
operations; a successful import may remain if creation fails.

The source original, candidate document and replay may contain private text and
answer keys. Do not log the inputs, intermediate objects, or decoded response.
The returned comparison contains only fixed labels and the two reported status
values; this projection is not encryption or access control. A real host must
perform any required lifetime, cancellation and authorization checks itself.
The helper is synchronous because its existing candidate adapter runs the
question-turn via `asyncio.run`; it cannot be called directly on a thread with
an active event loop. Source pin checks reject observed links, hardlinks and
identity changes but do not prove every filesystem race or Python runtime
identity is impossible.

## Opt-in labeled-source comparison

`reconcile_recovered(...)` takes the same five caller-supplied response pairs
as `reconcile`, plus explicit keyword-only `completed`, `finish_reason`,
`tool_calls`, `function_call` and `allow_recovery=False`. Its raw input is the
complete labeled response, while `replay_request.response_body` is the exact
recovered body. On every call it reconstructs the opt-in recovery and the full
existing replay/normalizer candidate; it does not trust a prior recovery
object. The original model-text parser must agree and parser fallback is not
enabled. The exact labeled bytes and their SHA are compared against the supplied
source receipt and original readback before the common Document and question-view
checks. Body-only source receipts, changed answers, mismatched snapshots and
malformed response JSON fail closed. A duplicate source's existing name or MIME
is not required to match the new `.txt` import request.

The additional result labels describe this local comparison and caller-declared
terminal/tool state. They do not prove actual Core identity, origin, model
generation, opt-in history, authorization, durable recovery metadata or that
sequential reads form one atomic snapshot. The original source, private
recovery receipt and document attributes may contain the answer; no logging or
secrecy guarantee is made. Import followed by document creation is still two
separate calls and a failed create can leave the source behind.
