# AAOS-01: mount condition closed empirically - one binary, two launch inputs, two route sets

## 1. Experiment design

| variable | value |
| --- | --- |
| binary | C:/Windows/Temp/aaos-target/release/archeaxis-api.exe, built from the CURRENT source |
| launch document | two versions, differing only by a text_worker block |
| database and port | separate scratch paths and ports |

## 2. Result: same binary, two different route sets

| route | without text_worker | with text_worker |
| --- | --- | --- |
| GET /api/v1/capabilities | 404 | 200 |
| POST /api/v1/machine/answers | 404 | 422 (route exists, body wrong) |
| GET /api/v1/evidence/anchors | 200 | 200 (always mounted) |

## 3. And the capabilities response lists exactly what I declared

I declared only the default text worker script and no additional routes. The core reported a single
capability, text.extract, with no others - matching the documented behaviour that an absent route list
keeps the single-route behaviour exactly.

That turns the earlier source-level conclusion into a runtime-visible fact: capability routes exist
because a launch declared them.

## 4. The machine answers contract

The route now expects knowledge_id and question, not the knowledge_type field I had guessed by borrowing
the Python backend's name.

Compare an early round: the same route once returned 503 'no worker is registered'. With a worker
declared it returns 422 instead. The failure moved forward from a missing worker to a wrong field - the
same progression seen repeatedly in this project.

## 5. Q03 accounting after this round

| item | status |
| --- | --- |
| canonical core runnable | done |
| v2 launch contract | done |
| launch-layer actor validation | done |
| five request-layer credential boundaries | done |
| actor identity classification (positive) | done |
| complete route set | 36, from source |
| mount condition | CLOSED EMPIRICALLY |
| capability routes declared at launch | runtime-visible |
| machine/answers contract | measured (422 lists fields) |
| canonical data model | still awaiting your decision |

## 6. What I do NOT claim

| not claimed | reason |
| --- | --- |
| declaring extra routes would lengthen the list | only the default script was declared |
| machine/answers can answer successfully | only the 422 was reached |

## 7. What changed this round

Only a rerun of the mounting test with a real script path, under .project-local/runs/mount-condition/.

No repository file was changed; nothing in the green directory was created, modified or deleted;
the official green data and libraries were untouched; nothing was installed.
