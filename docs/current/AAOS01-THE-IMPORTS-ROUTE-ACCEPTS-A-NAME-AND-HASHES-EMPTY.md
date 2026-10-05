# AAOS-01: the imports route accepts a name only, and hashes empty content

Driving the flow inside the candidate produced three facts and one anomaly.

| step | result |
| --- | --- |
| POST /api/v1/imports with a name and a path | 202, sha256 e3b0c442...b855, source_id src_cd372fb85148700fa88095e3 |
| POST /api/v1/jobs | 422, missing field kind |
| POST /api/v1/jobs/:id/executions | 422, AAK-VAL-001 invalid execution request |

## The anomaly, stated carefully

The returned sha256 is the SHA-256 of the empty string - a well-known constant. So the import recorded an
empty document rather than the 1120-byte PDF I generated. Asking the route what it requires showed that name
is its only required field, that an unknown field is silently accepted, and that a body containing only a
name still returns that same empty hash.

Two further observations: two requests with different names and different paths returned the same
source_id, and both reported duplicate as false, which is not what a content-addressed identifier would
usually do.

## Why I am not calling it a defect

The likeliest explanation remains my request. I have not found which field carries the document, so the
route has nothing to hash and hashes nothing. The same session contains three earlier cases where my call or
assembly was wrong and the artefact merely looked broken - a launch that registered one worker instead of
thirteen, a runtime passed in the wrong form, and a candidate missing its dependencies. In one of those I
published a conclusion and had to withdraw it.

So the finding is recorded as an open contract question: which field carries the document, and whether the
duplicate flag is expected to be false for a repeated content address. Both belong to whoever owns the
import route, not to a claim about pdf.extract.

## What is and is not established about the receipt's question

Established: the candidate starts, registers fourteen capabilities including pdf.extract and image.ocr, and
accepts an import call, an enqueue call and an execute call - the latter two telling me their required
fields through validation errors.

Not established: the receipt's actual question, whether pdf.extract produces readable output, because no
document has yet reached the core. The jobs route also still needs a kind, which I have not supplied.

## What changed

Runs under project-local and this document. No repository source file was changed; nothing in the green
directory was created, modified or deleted; the official green data and libraries were untouched; nothing
was installed.
