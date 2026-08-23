+# AXR-060-401 Unified Client Write Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the React desktop client accept only a compatible Core handshake and attach the launch token, an issued write scope, and an idempotency key to every product write it performs.

**Architecture:** `src-tauri` owns the ephemeral launch credential and the single issued `workspace:write` scope. `frontend/src/api/client.ts` is the only credential-bearing request layer: it validates the complete handshake before exposing reads and creates write headers centrally. `runtime.ts` is removed; `workspace.ts` supplies typed endpoint DTOs only. The Workspace, Learning, Setup, and System HTTP boundaries independently reject missing/mismatched desktop write credentials; existing domain command receipts remain the replay authority for commands that persist one.

**Tech Stack:** TypeScript/Vitest, Python/FastAPI/Pytest, Rust/Tauri.

**Spec:** `D:/All projects/ArcheAxis_v0.6.0_Minimum_Closed_Loop_Release_TaskPack_2026-08-20.md` (AXR-060-401)

## Global Constraints

- Token and issued scope are in-memory only; do not persist them to browser storage, files, logs, or diagnostics.
- Handshake must reject product/API/runtime/workspace/migration/capability contract incompatibility before UI projections or writes.
- Every React product write has `X-ArcheAxis-Launch-Token`, `X-ArcheAxis-Scopes`, and `Idempotency-Key`; commands retain their existing body `command_id` when their API contract requires one.
- Server enforcement applies to the React-backed Workspace, Learning, Setup, and System write surface; unrelated legacy and federation contracts are not silently rewritten in this task.
- A non-desktop browser must not fabricate a desktop write credential.

---

### Task 1: Define the issued desktop write credential

**Files:**
- Modify: `src-tauri/src/main.rs:273-276,369-382,397-460`
- Modify: `desktop/src-tauri/src/backend.rs:20-105`
- Test: `tests/test_tauri_security_contract.py`

**Interfaces:**
- Produces: Tauri `backend_info` payload `{ port, token, scopes }`, where `scopes` is `string[]` and includes `workspace:write` for a launched desktop Core.
- Produces: Core environment variable `ARCHEAXIS_DESKTOP_WRITE_SCOPES=workspace:write` alongside the existing ephemeral launch token.

- [ ] **Step 1: Write failing contract tests**

```python
assert 'scopes: vec!["workspace:write".to_owned()]' in source
assert 'ARCHEAXIS_DESKTOP_WRITE_SCOPES' in backend_source
```

- [ ] **Step 2: Run the focused contract test and verify RED**

Run: `python -m pytest tests/test_tauri_security_contract.py -q`
Expected: FAIL because the Tauri payload/environment omit issued write scopes.

- [ ] **Step 3: Implement the narrow desktop payload/environment change**

Add `scopes: Vec<String>` to the active root Tauri `BackendInfo`; supply `workspace:write` from `backend_info` and retry paths. Set the matching Core environment variable in `BackendProcess::launch`. Do not write either field to disk or recovery DTOs.

- [ ] **Step 4: Run the focused contract test and verify GREEN**

Run: `python -m pytest tests/test_tauri_security_contract.py -q`
Expected: PASS.

### Task 2: Enforce desktop write intent at the HTTP boundary

**Files:**
- Modify: `app/workspace/router.py:53-89` and React-facing write routes
- Modify: `app/setup/router.py:20-51`
- Modify: `app/workspace/system.py:105-130`
- Test: `tests/test_workspace_api.py`

**Interfaces:**
- Consumes: `X-ArcheAxis-Launch-Token`, `X-ArcheAxis-Scopes`, `Idempotency-Key`.
- Produces: `require_desktop_write_request(request)` which returns 403 for a missing/mismatched token or missing issued `workspace:write` scope, and 422 for a missing idempotency key.

- [ ] **Step 1: Write failing FastAPI tests**

```python
response = client.post('/workspace/api/backup/create', json={'name': 'release'})
assert response.status_code == 403
response = client.post('/workspace/api/backup/create', headers=authorized_headers, json={'name': 'release'})
assert response.status_code == 200
```

The test must also assert that a valid token without `workspace:write` fails and a write missing `Idempotency-Key` returns 422.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python -m pytest tests/test_workspace_api.py -q`
Expected: FAIL because React-facing writes currently use only local-origin checks.

- [ ] **Step 3: Implement shared dependency and apply it only to React product writes**

Use constant-time token comparison with `ARCHEAXIS_DESKTOP_LAUNCH_TOKEN`; parse configured issued scopes from `ARCHEAXIS_DESKTOP_WRITE_SCOPES`; reject no-token/invalid-scope/missing-idempotency states without disclosing values. Apply the dependency to Workspace writes currently exposed by `frontend/src/api/runtime.ts`, setup initialization, and system restart. Preserve `testclient` as an explicit test-only bypass only when no launch token is configured.

- [ ] **Step 4: Run focused backend tests and verify GREEN**

Run: `python -m pytest tests/test_workspace_api.py tests/test_setup_api.py -q`
Expected: PASS.

### Task 3: Centralize handshake validation and client write headers

**Files:**
- Modify: `frontend/src/api/client.ts:1-59`
- Modify: `frontend/src/api/client.ts` and `frontend/src/api/workspace.ts`
- Test: `frontend/src/__tests__/RuntimeClient.test.ts`

**Interfaces:**
- Consumes: `createApiClient(baseUrl, token, scopes)` and full handshake payload.
- Produces: `client.write(path, body, { commandId? })`; it adds `Content-Type`, `X-ArcheAxis-Scopes`, and `Idempotency-Key`, while `runtime.ts` keeps typed endpoint DTOs only.
- Produces: `RuntimeProjection` of `offline | backend_starting | migrating | incompatible | unauthorized | unavailable`.

- [ ] **Step 1: Write failing client tests**

```ts
expect(writeInit.headers).toMatchObject({
  'X-ArcheAxis-Launch-Token': 'memory-only',
  'X-ArcheAxis-Scopes': 'workspace:write',
  'Idempotency-Key': expect.stringMatching(/^workspace-backup-/),
});
await expect(getStatus()).rejects.toMatchObject({ code: 'migrating' });
```

Also require rejection for an incompatible API contract, missing runtime identity, missing workspace ID, non-array capabilities, and a non-ready migration state.

- [ ] **Step 2: Run the focused frontend test and verify RED**

Run: `npm test -- RuntimeClient.test.ts --run`
Expected: FAIL because handshake only checks product ID and write requests omit scope/idempotency headers.

- [ ] **Step 3: Implement the one client authority**

Move credential/header handling into `client.ts`; make the typed Workspace facade pass only the `backend_info` in-memory values. Validate the complete typed handshake and map fetch/status/handshake failures to the public projection. Remove `runtime.ts`, replace its direct POST construction with `client.write`, and keep existing command ids in payloads where required.

- [ ] **Step 4: Run focused frontend test and verify GREEN**

Run: `npm test -- RuntimeClient.test.ts --run`
Expected: PASS.

### Task 4: Verify integration and record truthful scope

**Files:**
- Modify: `docs/current/AXR_060_401_UNIFIED_CLIENT_HANDOFF_2026-08-24.md`

- [ ] **Step 1: Run focused backend and frontend suites**

Run:

```powershell
python -m pytest tests/test_workspace_api.py tests/test_setup_api.py tests/test_tauri_security_contract.py -q
npm test -- RuntimeClient.test.ts App.test.tsx RecoveryShell.test.tsx --run
npm run build
```

Expected: all selected tests and frontend build pass.

- [ ] **Step 2: Inspect quality and diff**

Run:

```powershell
python -m compileall app
npx ruff check app/workspace/router.py app/workspace/system.py app/setup/router.py
git diff --check
git status --short
```

- [ ] **Step 3: Write handoff evidence and commit**

Record exact commands/results, source boundaries, and the distinction between local validation and unexecuted exact-SHA CI/install validation. Stage only task-owned files and commit with `feat: harden unified client write boundary`.
