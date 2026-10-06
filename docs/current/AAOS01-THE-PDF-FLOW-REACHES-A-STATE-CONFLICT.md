# AAOS-01: the pdf flow reaches a job-state conflict rather than a request error

Four corrections took the flow from a malformed request to a state conflict. Each was found by reading or
asking, never by guessing, and each changed the error:

| correction | before | after |
| --- | --- | --- |
| the document travels as content_base64 in the body | import returned the empty string's hash | import returns the hash of my 1120-byte PDF |
| the job body needs input_ref | 422 missing field input_ref | 202, job queued |
| execute needs an idempotency-key header and a non-zero deadline_ms at most 300000 | 422 AAK-VAL-001 invalid execution request | 409 AAK-CON-003 |

## What the latest evidence says

| step | result |
| --- | --- |
| POST /api/v1/imports | 202, source_id src_f4eee107088575eabd4e19a7, matching the receipt's own recorded id |
| POST /api/v1/jobs | 202, {job_id: pdf-final-1, state: queued} |
| POST /api/v1/jobs/pdf-final-1/executions | 409, AAK-CON-003, job cannot start in its current state |
| GET /api/v1/jobs/pdf-final-1 | state stays queued |
| GET .../outputs/result | 404 AAK-VAL-004 output not found |

A 409 state conflict means the request was accepted as well formed. The blocker has moved from the request to
the job's state: something must move it out of queued before an execution can start.

## Two things worth noting

My import reproduces the receipt's own recorded source_id exactly, and its returned hash matches the hash of
the golden fixture byte for byte. So my candidate and my request now agree with what the pack recorded.

And the earlier empty-hash anomaly is fully explained: content_base64 defaults to empty, so the route had
nothing to hash, and because each run used a fresh database the repeat was not flagged as a duplicate. It was
my request, not a defect - which is why I did not call it one.

## Not established

The receipt's actual question is still unanswered. pdf.extract has not run: the job never left queued, so no
output exists and its readability is unknown. What is established is that the candidate starts, registers
fourteen capabilities, imports a real document with a matching hash, and queues a real job.

## What changed

Runs under project-local and this document. No repository source file was changed; nothing in the green
directory was created, modified or deleted; the official green data and libraries were untouched; nothing
was installed.
