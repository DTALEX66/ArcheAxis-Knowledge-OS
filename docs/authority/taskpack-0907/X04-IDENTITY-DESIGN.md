# X04 identity & state semantics — design record (2026-09-07)

Status: PARTIAL. Purpose: record the concrete actor/identity design that will
close the residual X04 items, so the next implementer (or an independent audit
round with role-scope authority) can land it without re-deriving semantics.

## Current protections already on the branch (verified)

- `create_knowledge` (API): `evidence_status` is hard-coded `None`; `status`
  defaults to `candidate`; `knowledge_type` is validated against the contract
  vocabulary.
- Review transitions (`accepted|rejected|deprecated|modified`) produce
  immutable `review_events` rows; `modified` creates a new candidate row.
- Clients cannot attach external-verification state at creation.

## Residual gaps (why PARTIAL)

1. Create body may still set `status: accepted` (self-acceptance).
2. `created_by`/`reviewer` are free-text (client-claimed identity).

## Design decision (recorded, NOT half-implemented)

A blanket "initial status must be candidate" guard would wrongly block
legitimate human-authored personal definitions (X04/§3.3: personal
definitions may be saved and user-accepted without external proof). The
correct fix requires distinguishing the *request actor* from claimed labels.
Recommended actor model aligned with launch_auth's role-scope authority:

- Process/session-level identity already exists (launch credential via private
  stdin pipe, all production routes authenticated). Extend it with an
  explicit `actor` grant: `{scope: human|machine, session, role}`.
- Core rejects any body-provided `created_by`/`reviewer`/`status` label that
  contradicts the authenticated actor: human-session may submit personal
  content as `candidate` then accept via review; machine/AI workers may only
  submit candidates/proposals (never `accepted`, never `verified`, never
  reviewer-identity spoofing) - X09's "AI cannot self-grant human/verified".
- `evidence_status` may only be set by a future evidence subsystem, never by
  content writers.
- State dimensions stay separate: content_type, review flow state,
  user_acceptance, external_verification (no single candidate-review-verified
  axis) - maps onto existing `knowledge.status` + `evidence_status` + new
  `user_acceptance` when the actor model lands.

## Implementation plan (for the round that owns role-scope authority)

1. Add `actor` grant to launch payload and API request context.
2. Domain: `create_knowledge(actor, ...)` and `review(actor, ...)` validate
   labels against actor scope; tests for machine-claimed human rejections.
3. Add `user_acceptance` column/state only together with (2).
4. Re-run api/domain suites + full python regression.

## Why not landed now

The role-scope authority itself is an open launch_auth item (recorded in
EXECUTION.md remaining lists); landing the domain guard before the actor
exists would re-introduce self-claim through a different field. No half-guard
was applied.
