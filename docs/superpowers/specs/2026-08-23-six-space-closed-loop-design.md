# Six-Space Real Closed Loop Design

Date: 2026-08-23

Authority: owner-approved full execution of the v0.6.0 Minimum Closed Loop TaskPack

Status: approved for implementation by the standing full-execution instruction

## Problem

The canonical `frontend/ + src-tauri/` line renders six named spaces and reads
real APIs, but most spaces remain shallow read-only tables. The v0.6.7 Release
proves packaging and lifecycle, not the task-pack requirement that Library,
Evidence, AI Assets, Inspector and Activity Dock expose usable product actions.

## Considered approaches

1. **Use existing operational APIs and add only missing governed commands
   (selected).** This preserves the production backend and closes UI gaps with
   the least new authority surface.
2. Build a consolidated Workspace BFF V2 before changing the UI. This gives a
   cleaner long-term contract but delays user-visible closure and duplicates
   already-stable commands.
3. Reuse `app/workspace/ui/` or another legacy UI. This violates the canonical
   implementation ADR and would reintroduce two UI truths.

## Architecture

`frontend/src/api/runtime.ts` remains the single authenticated runtime adapter.
It gains strict DTOs and command helpers for existing Workspace endpoints. A
command ID is generated in memory for every governed write. The launch token
stays inside the API-client closure.

The six spaces consume these contracts:

- Workspace: BFF home counts, components and recent activity.
- Library: Source Archive list, client-side search/state filter, local file
  upload, details and content-addressed original open/download.
- Evidence: pending Research review queue plus physical anchors; approve actions
  use the identity-bound server command and then refresh.
- Learning: existing review, Teach Back, quiz and mastery paths stay intact.
- AI Assets: candidate/approved/deprecated projection with evidence source,
  scope and version; approve and independently deprecate by unique title.
- Settings: explicit quick/advanced setup wizard, readiness/health steps,
  backup create/verify and truthful diagnostics.

Inspector accepts structured metadata instead of a single free-form detail.
Activity Dock uses the stable BFF activity feed, opens object details, and
exposes real dispatch/retry controls. A control with no valid backend action is
disabled and labelled; no fake cancel success is shown.

## Minimal backend additions

1. A content-addressed Source Archive read endpoint validates lowercase
   SHA-256, resolves only through `RawAssetStore`, and returns the original with
   a safe display name and `nosniff`/no-store headers.
2. A governed AI deprecation command resolves exactly one approved title and
   appends the existing machine-knowledge approval event with decision
   `deprecated`. It never deletes the candidate or mutates Human Learning.
3. Machine-knowledge projections expose only user-safe evidence source, scope,
   schema version and lifecycle fields; persistence IDs remain internal.

## Browser evidence

A real Chromium test builds/serves the canonical React bundle, starts an
isolated real FastAPI backend, and injects only the Tauri `backend_info` bridge.
All HTTP data and commands remain real. It walks all six spaces, uploads a
fixture, opens Inspector, exercises review/AI/Activity actions when the seeded
state permits, and checks keyboard/focus plus reduced-motion CSS.

The browser receipt records exact source SHA/tree, backend/frontend endpoints,
named assertions and status. It stays under ignored `.hermes/task-artifacts/`.

## Error and truth contract

- Loading, empty, retryable error and command-in-progress states are explicit.
- A failed command remains visible and can be retried; no optimistic PASS label
  survives a failed response.
- Absolute storage paths are not shown in Library, Inspector or AI Assets.
- Setup is the one deliberate path-display surface because the user selected
  those library locations.
- Release evidence and this product/browser evidence remain separate.

## Verification

- Python RED→GREEN tests for new Source Archive and AI-deprecation endpoints.
- Vitest user-event tests for each changed space and command/error state.
- TypeScript typecheck and production build.
- Real Chromium six-space test against isolated production APIs.
- Existing Golden Journey and targeted backend regression suite.
