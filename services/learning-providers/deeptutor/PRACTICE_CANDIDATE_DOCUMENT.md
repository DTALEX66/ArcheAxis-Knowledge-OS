# Private DeepTutor practice-row document preparation

`practice_candidate_document.py` prepares one private candidate for the
existing Core Document shape from caller-supplied CSV, TSV, JSON or XLSX bytes.
It is unregistered and offline: it sends no HTTP request, opens no Core
database, calls no model or grade worker, records no user answer, and grants
no provider authority. Its output and tests do not establish Core consumption.

`prepare_practice_row(data, format, row, material_snapshot, question_id,
create_request_id, title)` reparses the supplied bytes with the existing
`practice_import._private_preview`. It selects exactly one valid normalized
row and uses the existing `candidate_document.PrivateCandidate` source and
Document request construction. It does not fabricate a generation replay,
prompt, Core import receipt, or second normalization pipeline. The source is
at most 5 MiB. Source rows mean:

* JSON: one-based array position.
* CSV/TSV: one-based logical record number, including the header; a quoted
  record may span several physical lines.
* XLSX: one-based worksheet row number, including the header.

The format's retained original `parse_rows` and `normalize_question` are
selected from the exact upstream `importing.py`; their narrower accepted input
and XLSX isolation limits remain those in `PRACTICE_IMPORT_UPSTREAM.md`. The
candidate uses that row's normalized question type, question, options, correct
answer and explanation. It does not convert `user_answer` into an attempt,
result, grade, or mastery state. Original difficulty, tags and learner answer
remain in the private row receipt and original source rather than the Core
question shape.

The caller independently supplies stable ASCII token IDs: `question_id` (up to
256 bytes) and `create_request_id` (up to 128 bytes). The upstream
`import:<sha256>` identity is retained only in the private row receipt; its
colon is not a valid Core question token, and its unsalted digest includes the
answer and can be guessed. Two equal upstream questions in different rows may
have the same upstream ID. Distinct caller-chosen IDs keep their intended
document identities separate. Reusing the same IDs and source is a caller
decision; this module does not persist the mapping or establish cross-restart
batch recovery.

The selected `material_snapshot` is a separate caller-declared Document ID,
positive version and content SHA. Its shape is checked, including rejection of
the document ID derived from this create request itself. Its existence,
currentness, authorship, relationship to the imported question and authority
are not established here. It is not the workbook's source ID. Any later
provider dispatch must independently make the required human selection and
check material/question grants, attempt, cancellation and restore epoch.
Ordinary source and Document saving are not conditioned on a provider grant.

The wrapper provides:

* `original_source_bytes()` and `raw_import_request()`: exact complete input
  and an unsent source-import body with a format-appropriate fixed extension.
  CSV/TSV may be GB18030; the extension does not declare UTF-8. Core source
  deduplication can retain an older filename/MIME for identical bytes.
* `document_create_request(claimed_import_receipt)`: the existing builder
  checks the supplied receipt shape and SHA against the complete original
  bytes and uses that SHA as `source_revision`. The caller must pass the actual
  receipt obtained from an authenticated Core host; this module does not make
  or authenticate a receipt. Returned dictionaries can be mutated and Core
  does not rederive the row from the source.
* `private_import_receipt()`: a fresh private copy of the source format and
  SHA, row number/scope, raw parsed row, unselected top-level fields, recorded
  option changes, normalized upstream candidate (including original ID,
  answer, user answer, difficulty and tags) and skipped row numbers.
* `report()`: fixed status and limitation labels, without the title, row,
  question, answer, user answer, tags, original ID or source SHA.

The private receipt is only held in this process unless its caller explicitly
persists it. A successful future Core source import can preserve the complete
original file, but that does not by itself persist the selected row number,
loss analysis, or prove a derived answer. Source import, optional material
creation and per-question Document creation are separate operations; a failure
can leave the earlier source or Documents in place. The adapter does not delete
them or automatically retry. The existing readback helper is limited to much
smaller response bodies and does not support these 5 MiB source readbacks.

The recorded loss analysis contains known option overrides and unselected
top-level fields, not a complete comparison of every selected value. A
`null` option-change list means UNKNOWN. Saving the complete source permits a
later caller to inspect original bytes, but neither source SHA nor a private
receipt authenticates their origin. The request, receipt, original file,
ordinary Document reads, exports and backups can contain answers and personal
content; question-view's omitted direct answer field is not an access-control
or secrecy guarantee. Unkeyed hashes can be guessable. Do not log private
getters or request bodies.

To avoid producing a Core-invalid candidate, the adapter checks Core's UTF-8
byte limits, token syntax, source snapshot shape and a conservative 1 MiB
editor upper bound. This bound may reject inputs that Core itself would accept;
Core still applies its exact validation. The preview preflights each input
string leaf at 20,000 UTF-8 bytes, but the original importer's character-counted
`_cell` can stringify a nested value into a larger UTF-8 value. Therefore its
acceptance alone does not establish Core's output byte limits.
The adapter also rejects option aliases that the original practice grader's
case/whitespace folding could associate with multiple keys or with a different
multi-key selection, including continuous `AB`/`AA` forms. This is deliberately
narrower than the upstream importer and does not prove answer correctness. It
also conservatively rejects a multi-character key that can be read as other
single-character keys, even when the original grader prioritizes that whole key
and therefore does not take its continuous-key fallback.
On rejection the adapter returns a fixed error without source text or a private
row; the caller still owns the original input bytes. No rejected-row receipt is
persisted by this interface.

## Source loading and XLSX limits

Each instance of this module checks fixed local source size and SHA-256 before
use: `candidate_document.py` 23,478 B / `96ad414a1d35e842ad42362ea6ba1327ab7dfd8b3bb06d6e5bab39073a25953c`,
and `practice_import.py` 47,396 B / `fd8e8bbdf0700b84995f8b83fcd22b40770112e9414d2ea1c29cf65cf364a477`.
The latter independently pins the retained upstream `importing.py` as described
in its source document. Loading uses a unique temporary `sys.modules` entry for
dataclass initialization and removes only that entry if it still owns it.
The module instance caches one loaded practice module. Calls through that
instance are serialized with a non-blocking lock; its existing XLSX slot stays
with the cached module and is not discarded after an unknown cleanup. A source
identity mismatch observed after XLSX processing also blocks later XLSX calls
through that instance. No state here coordinates a different module instance,
process or restarted host; the host must avoid automatic retry when cleanup is
unknown and establish any cross-instance ownership separately.

The existing XLSX preview launches a Python child from its file path and
validates a bounded child reply. Parent checks bind the supplied SHA and
normalize the returned row but do **not** independently prove that a
self-consistent child row was parsed from those bytes. Thus its result is
explicitly `XLSX_CHILD_SOURCE_LINK_UNVERIFIED`; its source and candidate must
not be treated as an authenticated binding. Observed pre/post source checks do
not prove absence of TOCTOU. The process separator is not an OS sandbox, and
direct child/pipe cleanup is not proof that all descendants stopped. Timeout,
cleanup and dependency limits remain those of `PRACTICE_IMPORT_UPSTREAM.md`.
This module does not authenticate the Python runtime or installed libraries.

The synthetic tests do not open a real Core database, perform a model call or
establish authorization, persistent batch mapping, 5 MiB readback, restart,
backup/restore, installed runtime or production-route qualification.
