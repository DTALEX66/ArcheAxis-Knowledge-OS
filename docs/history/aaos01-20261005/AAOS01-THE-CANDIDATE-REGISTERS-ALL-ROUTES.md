# AAOS-01: the candidate's core registers all thirteen declared routes plus the default

Ran the assembled candidate's own core with a launch document built from its own worker-profile.json.

| evidence | value |
| --- | --- |
| core started from the candidate | ready on a loopback port, 0.5 s |
| routes declared in the launch | 13 |
| capabilities the core reported | 14 - the default text.extract plus all 13 |
| pdf sample | project golden fixture, 1120 bytes, sha256 0f0ffc50c79d9d97... |
| png sample | project golden fixture, 21329 bytes |
| imports with an empty body | 422, missing field name |
| jobs with an empty body | 422, missing field job_id |

The capabilities route is the same one that returned not-found when a launch declared no worker. It now
reports fourteen, so the candidate's profile routes reach the core's registry through the launch document.
Both capabilities in question, pdf.extract and image.ocr, are among them.

The 422 responses supply the request contract for the next step without any guessing: imports needs a name,
and jobs needs a job_id.

## Not established

The capabilities are registered, not exercised. No import, enqueue or execution has been performed yet, so
nothing is claimed about whether pdf.extract or image.ocr produce readable output - the receipt's actual
question. Registration and working output are different claims and must not be merged.

## What changed

A run under project-local and this document. No repository source file was changed; nothing in the green
directory was created, modified or deleted; the official green data and libraries were untouched; nothing
was installed.
