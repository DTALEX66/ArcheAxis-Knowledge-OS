# Native probe identity correction — isolated proposal

Status: PROPOSAL_ONLY_NOT_APPLIED. Evidence: SIMULATED. No host, browser, service,
business database or real inference was started. All writes belong to this audit
directory; the main checkout and preserved historical snapshots were not edited.

## Scope

`proposed.patch` changes two probes and adds/updates their synthetic tests:

- Reading recovery now checks the rendered current page, business title, editor
  content and version. It opens the existing document fingerprint diagnostic
  with a trusted UI action, compares document/source/revision/content identity,
  and requires full `document_get` equality. Same-title/same-content wrong IDs
  and hidden/wrong pages cannot pass. The owned diagnostic is closed afterwards.
- Learning recovery checks the visible business question, opens the existing
  learning-item diagnostic, compares item/assessment/question/knowledge/source/
  anchor identity and requires full `assessment_get` equality. Raw IDs remain in
  diagnostics; the old `body.innerText` knowledge-ID wait is removed.
- `GroupedUI` opens only the two current learning disclosures: manual key lookup
  and learning queue. It observes the visible semantic page and `.open`, clicks
  the existing summary through `click_revealed_selector`, and verifies it opened
  on the same page. This covers manual typing, `读取项目`, identity queue selection
  and review-title layout reveal. It performs no execution/review submission and
  never assigns DOM `.open` from JavaScript. Unwrapped visible queues still work.
- Cancelled material recovery waits for the actual failed-history message; the
  companion recovery checks the actual cancellation message and interrupted
  avatar. Exact cancellation identity/plan, no answer, unchanged Core receipts/
  history, and zero observed execution calls remain required. Provider stop and
  startup calls retain UNKNOWN/UNVERIFIED boundaries.
- `explicit_output_budget` separates `requested_cli_max_tokens` from
  `effective_by_purpose` for persisted answer/retest/material/companion requests.
  Saved DEEP 1024 and requested CLI 2048/4096 are distinct. No request payload,
  saved profile, provider, model, endpoint or effective model budget is changed.

## Evidence and readback

- `before/` holds the exact source inputs. `source-before.json` records hashes.
- `proposal/` holds isolated probe copies and their read-only transitive inputs.
- `tests/` runs the real probe functions and emitted observation JavaScript.
  `dom_harness.py` uses the project's existing jsdom; its layout visibility is
  simulated explicitly and is not native screenshot qualification.
- `red.log`: five actual original-behavior regressions fail: reader raw-ID wait,
  cancelled material history copy, scalar CLI budget misreport, omitted manual
  disclosure, and omitted review-title queue disclosure.
- `green.log`: final proposed behavior regression result. Earlier intermediate
  logs are retained separately, including missing isolated dependencies and
  test-fixture corrections; they are not claimed as successful qualification.
- `hashes.json` gives each proposed file's before/after SHA-256 and patch SHA-256.
- No product/source application, native rerun, actual model result, CI, commit,
  publication, Green replacement or Owner acceptance is claimed.

Main probe sources must still match the before hashes when applying. Root owns
application and verification. The proposal depends on the now-applied business
title/diagnostic separation and the two learning details; it does not modify
learning product components or weaken protected navigation.

## Reproduce without services

From the repository root in PowerShell, set only this process's environment:

```powershell
$audit = Join-Path (Get-Location).Path '.project-local/audits/probe-identity-fix-20261019'
$env:AAOS_PROBE_TEST_ROOT = Join-Path $audit 'proposal'
$env:AAOS_PROBE_SOURCE_REPO = (Get-Location).Path
$env:ARCHEAXIS_CAPABILITY_MANIFEST = Join-Path $env:AAOS_PROBE_TEST_ROOT 'config/environment/capability-requirements.yaml'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
$env:PYTHONIOENCODING = 'utf-8'
& '.venv/Scripts/python.exe' -B -m pytest -c "$audit/pytest.ini" -q --confcutdir="$audit/tests" "$audit/tests"
```

For the original-source negative control, select `before` instead of `proposal`
and run the five node IDs listed in the final red log. A nonzero exit is expected.
Use the project environment only; install or service changes are unnecessary.
