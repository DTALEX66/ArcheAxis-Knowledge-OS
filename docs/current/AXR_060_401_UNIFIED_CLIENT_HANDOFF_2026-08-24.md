# AXR-060-401 Unified Client Handoff

## Scope

This change establishes one React desktop request authority. `runtime.ts` has
been removed. `client.ts` owns the in-memory launch credential, handshake
validation, write headers, and public error projections; `workspace.ts` is a
typed endpoint facade only and cannot construct a credential-bearing request.

The root Tauri shell issues `workspace:write` only in the in-memory
`backend_info` payload and sets the matching Core environment value at process
launch. The Workspace, Setup, and System routes used by the React product
surface reject writes without the exact launch token, issued scope, and a
bounded `Idempotency-Key`.

## Handshake and write contract

- Handshake accepts only product ID `archeaxis-workspace` and API contract
  `1.x`; it requires a non-empty product name, backend version, source commit,
  runtime mode, workspace ID, a positive schema version, string capabilities,
  and migration state `ready`.
- `migrating`, offline, backend-starting, incompatible, unauthorized, and
  unavailable states map to safe Recovery Shell text. No endpoint, token, path,
  response body, or scope is rendered as a diagnostic.
- React writes use the launch token header, `X-ArcheAxis-Scopes`, and
  `Idempotency-Key`; commands that already have `command_id` reuse it as their
  idempotency key.
- The server-side scope check covers the React-backed Workspace, Learning,
  Setup, and System writes. Requested scopes must be a subset of the launcher's
  issued scopes. Federation and legacy non-React APIs retain their own
  contracts and are not claimed as covered by AXR-060-401.

## Local evidence

| Layer | Command/result |
| --- | --- |
| Backend boundary | `pytest tests/test_workspace_api.py tests/test_axw_data402_setup.py tests/test_tauri_security_contract.py tests/test_learning_loop_e2e.py tests/test_machine_knowledge_candidates.py tests/test_mastery_signal_contract.py tests/test_teach_back_eval.py -q` — 60 passed. |
| Frontend regression | `npm test -- --run` — 58 passed. |
| Frontend production build | `npm run build` — passed. |
| Python compilation | `python -m compileall app` — passed. |
| Lint/diff | targeted Ruff check and `git diff --check` — passed. |

The Python test environment printed the pre-existing migration warning that
only `COGNITIVE_DATA_DIR` was set. It did not fail a test. The worktree has no
Cargo toolchain, so Rust compilation was **NOT EXECUTED**; the Tauri payload
and launcher environment have Python structural-contract coverage only.

## Delivery status

- `IMPLEMENTED_LOCAL`: yes.
- `TESTED_LOCAL`: yes, within the commands above.
- `CI_VERIFIED_EXACT_SHA`: not executed; feature-branch pushes do not trigger
  the current workflow.
- `MERGED_MAIN`: not executed.
- `INSTALLED_RUNTIME_VERIFIED`: not executed.

## Follow-up gates

1. Review and merge the feature branch, then bind CI evidence to the resulting
   exact main SHA.
2. Run the Windows Tauri build and installed-runtime handshake/write journey
   when Cargo and the packaging toolchain are available.
3. Extend the same write-intent dependency when a future React endpoint adds a
   write operation; do not introduce a direct credential-bearing request or a
   second credential store.
