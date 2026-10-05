# AAOS-01: the single-source route manifest exists, and two of my conclusions were wrong

## 1. The file

services/python-workers/routes.json, schema archeaxis.worker-routes/v1, thirteen routes from capability to
implementing worker. Its own note reads: the single mapping from capability to the worker that implements
it, beside the workers it names; every path is relative to services/python-workers and callers add the
prefix their own layout uses. And then the sentence that settles an old question: this replaced three
hand-written copies that drifted and shipped 503s.

## 2. Two corrections to my own earlier conclusions

| when | what I concluded | what is true |
| --- | --- | --- |
| round 79 | there is no capability-to-route mapping in the repository | it exists, at services/python-workers/routes.json |
| round 140 | the join is only a runtime artifact, declared at launch, not in the repository | the single source is checked in; the launch declaration is built from it |

Round 140 was half right: a launch document does declare routes and the core does register them, which I
demonstrated. What I missed is that the repository holds the single source those declarations are
supposed to be built from. So my later statement that such a mapping should not be checked in was the
wrong conclusion, drawn from not having found the file.

## 3. It also explains a measurement from round 59

I once measured a machine.answer request returning 503, no worker registered. The note says the
hand-written copies this replaced drifted and shipped 503s. So that status was a symptom of exactly the
drift this file was created to end, which is why the file names machine.answer to
machine/worker_machine_answer.py.

## 4. The frontier, in the pack's own words

The receipt's last section states what is undone: no candidate was restaged with dependencies and the
pdf and image capabilities rerun, so their real callability inside a candidate is still unverified - only
that they are correctly refused. It names the cause and the instrument: the staged runtime used a bare
CPython with no project site-packages, while the staging script already accepts a dependency source and
dependency list, which is what puts dependencies into a candidate, and which was not used.

So the concrete next step is to stage a candidate with its dependencies and rerun pdf.extract and
image.ocr inside it. That is the pack's own named incomplete item, not a task I invented.

## 5. What I do NOT claim

| not claimed | reason |
| --- | --- |
| that staging with dependencies will make pdf and image succeed | not attempted |
| that the drift note refers only to round 59's 503 | it explains it; it may explain others |

## 6. What changed this round

Nothing but this document. Read-only reading of the route manifest and the receipt's frontier sections.
No repository file was changed; nothing in the green directory was created, modified or deleted;
the official green data and libraries were untouched; nothing was installed.
