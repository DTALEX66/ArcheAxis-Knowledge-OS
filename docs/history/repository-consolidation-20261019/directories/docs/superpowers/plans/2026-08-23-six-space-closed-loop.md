# Six-Space Real Closed Loop Implementation Plan

> Execute in the existing isolated writer worktree. Follow RED → GREEN and
> keep release/product evidence separate.

**Goal:** Close the shallow-projection blocker for the canonical six-space UI
and produce a real Chromium receipt against an isolated production backend.

**Architecture:** Extend the existing typed runtime client and Workspace
commands. Add only a content-addressed original read and governed AI deprecation
backend command. Keep persistence identities server-owned.

**Stack:** FastAPI/Pydantic/SQLite, React 18/TypeScript/Vitest, Python Playwright,
Tauri bridge injection for browser qualification.

---

## Task 1: Safe Source Archive open

**Files:** `app/workspace/router.py`, `app/workspace/service.py`,
`tests/test_workspace_public_closed_loop.py`

1. Add failing tests for invalid digest, missing content and successful bytes.
2. Add a service resolver that returns path plus safe metadata through
   `RawAssetStore` only.
3. Add the authenticated loopback endpoint with safe headers.
4. Run the focused endpoint tests.

## Task 2: Governed AI deprecation

**Files:** `app/workspace/router.py`, `app/workspace/service.py`,
`tests/test_workspace_public_closed_loop.py`

1. Add failing tests proving approved-only title resolution, append-only receipt,
   idempotent replay and independent Human Learning state.
2. Add strict command payload and server-owned reviewer/rationale.
3. Extend the user-safe candidate projection with scope/version/evidence fields.
4. Run focused governance tests.

## Task 3: Typed runtime commands

**Files:** `frontend/src/api/runtime.ts`,
`frontend/src/__tests__/RuntimeClient.test.ts`

1. Add failing tests for command paths, JSON/FormData handling and in-memory
   idempotency IDs.
2. Add typed home/activity/object/library/research/AI/setup/backup functions.
3. Keep one handshake client and avoid manually setting multipart boundaries.

## Task 4: Workspace, Library and Evidence

**Files:** space components plus new focused Vitest files.

1. Replace generic Workspace key/value rows with counts, components and recent
   activity.
2. Add Library upload/search/filter/detail/open actions.
3. Add Evidence pending review plus anchor views and governed approve/refresh.
4. Verify loading, empty, error and success states with user-event tests.

## Task 5: AI Assets, Inspector and Activity Dock

**Files:** AI/Inspector/Dock components and focused Vitest files.

1. Show lifecycle, scope, version and evidence; add approve/deprecate/export.
2. Render structured Inspector metadata and history.
3. Render stable activity items, object detail, dispatch and retry; label
   unavailable cancellation honestly.

## Task 6: Settings first-run and recovery operations

**Files:** `SettingsSpace.tsx`, runtime API, Settings tests.

1. Implement welcome, quick/advanced path forms, readiness steps, create and
   completion states.
2. Add backup create/verify and diagnostics panels.
3. Keep blocked setup from exposing import-ready state.

## Task 7: Real Chromium qualification

**Files:** `scripts/six_space_browser_e2e.py`, browser tests/contracts, CI gate
mapping if needed.

1. Add a failing runner contract test.
2. Start isolated migrated backend and built frontend on random loopback ports.
3. Inject only `backend_info`; drive real APIs through all six spaces.
4. Emit ignored exact-SHA receipt and run it locally.

## Task 8: Phase verification and delivery

1. Run focused Python/Vitest gates and production build.
2. Re-run Golden Journey on the final clean commit.
3. Push exact SHA, run Full Qualification CI and read back every required job.
4. Update completion audit/handoff without promoting remaining installed-runtime
   or Tier-A gates.
