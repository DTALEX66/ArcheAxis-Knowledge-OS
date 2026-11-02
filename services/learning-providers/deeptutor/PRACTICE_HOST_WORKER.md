# Private DeepTutor practice host worker

`practice_host_worker.py` is an **unregistered**, one-request process protocol
for a future controlled host. It turns one caller-supplied CSV, TSV or JSON
practice row into the existing private Core Document create-request shape. It
does not import a source, call Core, start a provider or model, grade an answer,
or write a database. It is not yet a product route or an integration claim.
XLSX is deliberately rejected before candidate preparation: its isolated child
does not establish source-to-row authenticity or complete descendant cleanup.

The host sends one UTF-8 JSON object followed by LF, then closes stdin. Extra
bytes after that line, unknown or duplicate object keys, floats/non-finite
numbers, invalid UTF-8 and noncanonical base64 are rejected. The request limit
is 7,056,044 bytes **including** LF; decoded source is nonempty and at most
5,242,880 bytes. This is a source-size ceiling, not acceptance of every file
within it: the original preview's row, cell, structure and loss limits still
apply. CSV and TSV retain their existing UTF-8/GB18030 handling. The worker
reads no source path supplied by the caller.

The exact request fields are:

* `schema`: `archeaxis.deeptutor-practice-host-worker/v1`.
* `request_id`: a caller-chosen ASCII token, 1–128 bytes.
* `source`: exactly `format` (`csv`, `tsv`, or `json`), `content_base64` and
  lowercase `sha256` of the complete decoded file.
* `source_row`: an integer from 1 to 502; JSON uses one-based array positions,
  while CSV/TSV use one-based logical record numbers including the header.
* `material_snapshot`: exactly `document_id`, positive integer `version`, and
  `content_sha256`, using the existing candidate's snapshot shape.
* `question_id`, `create_request_id` and `title`: caller-chosen values subject
  to the existing Core candidate token and UTF-8 bounds.
* `import_receipt`: exactly `source_id`, lowercase `sha256` and boolean
  `duplicate`. Its SHA must match the supplied file. For `duplicate=false`,
  the current Core first-import source-ID formula is also checked. A duplicate
  may retain an older source ID; its previous filename/MIME are not assumed.

These values and the receipt are **caller supplied**, even if a real host
obtains them from Core. Shape, hash and ID consistency do not authenticate a
receipt, prove Core stored the file, select or authorize the material, or bind
the supplied row to a real user. A future host must obtain and independently
check the actual Core import result, bytes and material version. It must
recheck workspace/restore and cancellation state at the Core write boundary;
this worker has no access to those states. The future import-and-create host
must authenticate the intended human actor itself: the existing source-import
route alone is not a human-only gate. Ordinary local document saving does not
require an external-provider grant.

On success, stdout is exactly one bounded UTF-8 JSON line containing
`status=PRIVATE_CANDIDATE`, the request ID, SHA-256 of the exact input line
including LF, and `document_create_request`. The 1,114,112-byte reply limit
includes LF. The returned create request contains the **question, answer key,
explanation and title**. The input contains the complete original file and may
also contain learner answers and other private content. Input and output
digests can be guessable and are not confidentiality mechanisms. This pipe is
only for a trusted, controlled host: never put the raw request, private reply,
stderr, or full Core Document into ordinary job outputs, logs or a learning
view. Core source reads, ordinary Document reads, export and backup can still
contain answers; no access-control or encryption guarantee is made here.

Failure returns a fixed `INVALID_REQUEST`, `REJECTED`, or `UNAVAILABLE` JSON
line and nonzero exit code, without echoing input or exception details. A
`REJECTED` candidate deliberately combines invalid input and a potentially
unavailable nested dependency; it is not a diagnosis. The worker code does not
log request values. Interpreter startup, OS errors, and host logging behavior
are outside that statement; a host must discard rather than record child stderr
and treat a malformed, truncated or missing reply as failure.

The worker reuses `prepare_practice_row` and the existing
`PrivatePracticeCandidate.document_create_request` without inventing an import
receipt or another normalization pipeline. It returns neither the private row
receipt nor its loss analysis, and does not persist them; the caller must not
claim that row mapping or full transformation loss is preserved. An eventual
Core source import can retain the full original file, but source import and
Document creation are separate operations: a failed later step can leave the
source behind. A create-request dictionary is mutable, and Core does not
rederive the chosen row from the original file.

The worker pins `practice_candidate_document.py` at 17,679 bytes / SHA-256
`219e04721d662198b1fa1169c4be8e3acc63be24e3c7595d3e01847d1c2ead17`.
That adapter separately pins `candidate_document.py` at 23,478 bytes /
`96ad414a1d35e842ad42362ea6ba1327ab7dfd8b3bb06d6e5bab39073a25953c` and
`practice_import.py` at 47,396 bytes /
`fd8e8bbdf0700b84995f8b83fcd22b40770112e9414d2ea1c29cf65cf364a477`.
The latter selects the retained DeepTutor 1.7.1 `practice/importing.py` at
8,880 bytes /
`9ee4dd1abfa150fd81c3e3e31e2321761bab05509f6e4a5fca555ede2bbfd260`;
its license and precise upstream behavior are documented in
`PRACTICE_IMPORT_UPSTREAM.md`. The checks bind the bytes each adapter executes,
but do not authenticate the Python runtime or eliminate every concurrent path
replacement race. The CSV/TSV/JSON path uses the standard library, and does
not need the optional XLSX libraries.

For a future real host, the worker itself and its runtime must be pinned and
launched using an owned, bounded process and private pipes. The host must drain
stdout while writing/closing stdin, enforce a deadline, and independently
confirm cancellation, process-tree cleanup and pipe-thread joins. This worker
does not provide an OS sandbox, a hard memory/time limit, or a cancellation
protocol, and does not establish any of those properties. A timeout or
uncertain cleanup must remain UNKNOWN without automatic replay; bytes already
sent cannot be recalled. The host must strictly validate the reply and use
Core's single writer, preserving the actual material/version and restore
fences, before exposing only an appropriate redacted view. Direct synthetic
subprocess tests do not prove Windows Job containment, actual Core persistence,
installed-runtime behavior or Owner acceptance.
