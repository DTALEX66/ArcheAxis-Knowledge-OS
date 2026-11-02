# Private DeepTutor practice-candidate readback comparison

`practice_candidate_readback.py` compares one previously prepared private
practice candidate with caller-supplied Core-shaped HTTP responses. It does not
make requests, authenticate Core or a caller, open SQLite, run a model or
grade, or record learning state. Even a match can be produced entirely from
fabricated but mutually consistent inputs. It is not evidence of production
integration, authorization, source derivation or independent mastery.

The caller must use `prepare_practice_row(data, format, row, material_snapshot,
question_id, create_request_id, title)` in **this same loaded module instance**
before calling `reconcile(prepared, data, format, row, material_snapshot,
question_id, create_request_id, title, import_response, original_response,
create_response, document_response, view_response)`. Preparation invokes the
fixed `practice_candidate_document.py`; XLSX can start its existing private
child. Readback compares the already prepared object and **never reparses the
file, starts a child or automatically retries**. It does not verify that the
selected row was extracted from the source independently of preparation.

This module instance caches one pinned practice module and one pinned existing
readback comparator. Calls are serialized by a non-blocking lock. It retains at
most the latest prepared candidate and its fingerprint; starting a new
preparation invalidates the previous candidate even if the new preparation
fails. A previous caller may retain its own reference and data in memory, but
readback here refuses it. The fingerprint detects changes to retained private
fields and raw bytes; it is not a secret, authentication or a protection from
arbitrary code in the same Python process. The returned Core request is a fresh
mutable dictionary, not the comparator's retained expected object. Before
fingerprinting private strings, each has a character bound and an independent
UTF-8 byte bound; the private row receipt retains the existing 16 MiB limit.
These resource limits do not turn in-process objects into a security boundary.

An XLSX cleanup-unknown condition does not discard or recreate the cached
practice module: its existing per-instance slot remains the same. A different
loaded module, process or restarted host has a different slot; this helper does
not coordinate them. The host must avoid automatic retry on unknown cleanup and
separately establish any process-tree ownership and cross-instance fence.
XLSX child output can be internally consistent without proving the row came
from the workbook, so a successful comparison reports
`XLSX_CHILD_SOURCE_LINK_UNVERIFIED`. See `PRACTICE_CANDIDATE_DOCUMENT.md` and
`PRACTICE_IMPORT_UPSTREAM.md` for the original processing and containment
limits.

Each response is a `(status, bytes)` pair containing one bounded UTF-8 JSON
object. Duplicate keys, non-finite numbers, invalid Unicode and excessive
structure are rejected. Expected response shapes and statuses are:

| Argument | Status | Caller-supplied response kind |
| --- | ---: | --- |
| `import_response` | 202 | `/api/v1/imports`: source ID, SHA and duplicate flag |
| `original_response` | 200 | `/api/v1/sources/{source_id}/original`: ID, name, MIME, SHA and base64 bytes |
| `create_response` | 201 | `/api/v1/documents` creation response |
| `document_response` | 200 | The same version-1 Document read |
| `view_response` | 200 | Human `/api/v1/learning/deeptutor/question-view` response |

The source input is limited to 5 MiB. Its original-response JSON has its own
limit of 7,056,044 bytes: the maximum base64 encoding plus 64 KiB for JSON and
metadata. An unusually large legacy source name or other oversized envelope is
rejected, even if Core might return it. The import receipt is limited to 4 KiB,
Document responses to 4 MiB each, and the question view to 512 KiB. These
limits apply only to this helper. The existing generated-question readback's
180,000-byte source and 320 KiB source-response limits remain unchanged. Core's
source import permits up to 64 MiB and the Tauri SourceOriginal transport up to
90 MiB; the smaller bounds here are deliberate, not a claim about all Core
responses. The tests exercise the 5 MiB boundary in memory and do not create a
large workbook or source file on disk.

The pinned existing comparator checks source identity, canonical base64, exact
source bytes and SHA; for a new source it checks Core's derived source ID,
while a duplicate may retain a prior ID, name and MIME. It checks the
Document's create-request ID, source reference, private candidate attributes,
paragraphs, blocks, projection and consistency across create/read responses,
then compares the question view's snapshot, material reference, question and
options. This helper checks the prepared row number/scope, original source,
material snapshot and caller-chosen IDs against the same retained object; it
compares its normalized private fields with the constructed Document. It does
not independently recompute Rust's Document content SHA, block IDs, question
version or visible digest. Status values `current`, `historical`, and
`unavailable` are the supplied view's claims and cannot prove future currency.
Portable-import question views are outside this finite comparator.

Preparation and all supplied HTTP response bytes may contain the complete
original file, answers, learner answers or other private values. They must not
be logged. `report` contains only fixed labels and supplied status values;
omitting an answer field is not encryption or access control, and unsalted
digests can be guessable. The private row/loss receipt is not persisted by this
helper. Source import and Document creation are separate calls; a failed
Document creation may leave the source in Core. No cross-call atomicity,
restart durability, backup/restore, model call, provider execution, installed
runtime or Owner acceptance is established.

The module pins `practice_candidate_document.py` (17,679 bytes / SHA-256
`219e04721d662198b1fa1169c4be8e3acc63be24e3c7595d3e01847d1c2ead17`)
and `candidate_readback.py` (18,952 bytes / SHA-256
`04936dbd2f8a2b7c1dbb5b75c5b7b7995f9624613b17ccc817390de603105072`).
Observed file-identity and digest checks do not establish a trusted Python
runtime or eliminate every filesystem race.
