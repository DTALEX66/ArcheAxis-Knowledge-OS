# AAOS-01: the capability-to-route join demonstrated end to end

## 1. Experiment

Same binary (built from the current source). Same launch document except for the text_worker routes list.
One case declares no extra routes; the other declares two. Both then GET /api/v1/capabilities.

## 2. Result

| case | declared routes | capability names reported | count |
| --- | --- | --- | --- |
| no_routes | none | text.extract | 1 |
| two_routes | diag.alpha, diag.beta | text.extract, diag.alpha, diag.beta | 3 |

Declaring a route makes the core register that capability, and the registration is visible in the
capabilities listing. With no extra routes the listing holds exactly one entry, the default; with two
extra routes it holds exactly three - the default plus the two declared, and nothing else.

## 3. The complete chain, now observable

launch document text_worker.routes
  -> the core registers each declared capability
    -> GET /api/v1/capabilities lists exactly those

This closes the question I first asked many rounds ago, when I searched the repository for a mapping
between capabilities and routes and could not find one. There is no such file, by design: the mapping is
declared at launch and generated into a distribution artifact, and it is observable at runtime.

## 4. Each capability record carries thirteen fields

automatic_failure_fallback, capability, default_provider, enabled, enabled_basis, fallback, fallback_note,
health, health_basis, health_details, is_default, provider, registered

Three of those deserve note: enabled_basis, health_basis and fallback_note. Each judgement the core
reports arrives with its basis attached, which matches this project's evidence discipline that a claim
should carry what supports it.

## 5. Q03 accounting after this round

| item | status |
| --- | --- |
| canonical core runnable | done |
| v2 launch contract | done |
| launch-layer actor validation | done |
| five request-layer credential boundaries | done |
| actor identity classification (positive) | done |
| complete route set | 36, from source |
| mount condition | closed empirically |
| capability-to-route join | DEMONSTRATED END TO END |
| machine/answers contract | measured (422 lists fields) |
| canonical data model | still awaiting your decision |

## 6. What I do NOT claim

| not claimed | reason |
| --- | --- |
| a capability declared this way can actually run a job | this round measured registration only |
| the route entry field set is complete | the struct has capability and script; enabling may need more |

## 7. What changed this round

Only two probe reruns under .project-local/runs/ (route-declare-two, route-declare-three).
My first attempt was inconclusive because I truncated the response body to 700 characters, which broke
JSON parsing and fell back to raw text; the rerun read the full body.

No repository file was changed; nothing in the green directory was created, modified or deleted;
the official green data and libraries were untouched; nothing was installed.
