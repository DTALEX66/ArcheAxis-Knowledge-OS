# Mandatory web knowledge ingestion intake

Date: 2026-08-09

## Owner decision

Web knowledge ingestion is a mandatory product capability across the Workspace frontend and backend. The execution plan must absorb Crawl4AI and a second user-named Spidering provider, while preserving Safe HTTP, candidate review, provenance, evidence, Windows packaging, and project data boundaries.

## Current evidence

- `unclecode/crawl4ai` is the confirmed Crawl4AI upstream. The repository already declares a dependency and contains a named adapter, but the current runtime path delegates to `convert_url()` and does not prove a direct Crawl4AI invocation.
- The user-provided name `Spidering` is ambiguous on GitHub. `spider-rs/spider` is the current capability-aligned MIT candidate; `duzluk/spidering` is a small GPL-3.0 project and must not be selected merely because its repository name is an exact text match.
- The Workspace has a single-URL intake form and endpoint, but not a governed site-crawl product surface with provider selection, scope preview, progress, pause/cancel/resume, per-page results, raw snapshots, format routing, and installed qualification.

## Governance decision

The already-published frozen v1 baseline remains byte-for-byte unchanged. A separately hashed mandatory addendum adds the Web task DAG. The DeepSeek execution pack treats the addendum as an additional source and requires `AXW-WEB-EXIT` before H2, the end-to-end learning qualifier, or v1.0 release qualification can pass.

This intake and the addendum are planning/governance artifacts only. They do not claim Crawl4AI, Spidering, dynamic crawling, site crawling, or the frontend/backend flow is currently release-qualified.
