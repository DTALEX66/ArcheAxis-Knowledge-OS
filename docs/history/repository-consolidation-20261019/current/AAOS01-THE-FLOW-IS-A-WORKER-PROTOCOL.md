# AAOS-01: the flow is a worker protocol, and execute is not the worker's path

Reading the enqueue and receipt handlers shows the shape of this slice: durable enqueue plus a terminal
receipt. The Core records a job as queued when it is enqueued. The execute route calls the executor, which
refuses a queued job with a generic conflict, and a comment at that site says why the message is generic - the
executor reports failures as strings, so the route cannot say more. A separate receipts route records a
terminal state of succeeded or failed, described as the canonical job-status vocabulary.

So the conflict I reached is not a missing field. It is that I treated execute as the way to make a worker
run, whereas this slice is built so that a worker takes the work and reports back.

## What I am marking as unfinished rather than concluding

The set of legal kind values lives in the application crate's jobs module, and I have not read it. Until I
do, the statement that execute is the wrong route for a worker job is a direction supported by evidence, not
an established fact. The alternative remains open: that a legal kind exists which execute accepts.

## Where the flow actually stands

| step | result |
| --- | --- |
| candidate core with thirteen declared routes | starts, reports fourteen capabilities |
| import with content_base64 | 202, hash matches the golden fixture byte for byte |
| enqueue | 202, {job_id, state: queued} |
| execute | 409 AAK-CON-003, job cannot start in its current state |
| job state | remains queued |
| outputs/result | 404 AAK-VAL-004 output not found, correctly |

The receipt's question - whether pdf.extract produces readable output - is still unanswered, and the reason
is now structural rather than mysterious.

## What changed

Read-only inspection of the enqueue and receipt handlers, plus this document. No repository source file was
changed; nothing in the green directory was created, modified or deleted; the official green data and
libraries were untouched; nothing was installed.
