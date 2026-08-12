> **SUPERSEDED (2026-08-12)**: 本文档为历史文档。产品命名与身份以
> `docs/truth/NAMING_CONTRACT_V1.md`（ArcheAxis / ArcheAxis Knowledge / 星环知识平台）
> 与 `docs/truth/PRODUCT_IDENTITY_V2.md` 为准。本文档仅保留历史与迁移语境，不再维护。
>
# Product Stage: Obsidian-compatible Workspace

## Product truth

**ArcheAxis Knowledge（星环知识平台）** is a local-first, evidence-driven Human–AI learning and knowledge workspace. The user-owned open-format workspace is primary; AI is a cited usage layer, not the product center.

## Current vertical

The first high-fidelity vertical is:

```text
Vault selection / approved root
→ Markdown and JSON Canvas inspection
→ links, properties, tags, attachments and loss report
→ governed edit / revision / conflict / rollback
→ restart and export readback
```

The current repository has compatibility foundation and semantic analyzers. It is not yet a user-closed bidirectional Vault product. A capability may only move through this state machine:

```text
not_scoped
→ researched
→ license_approved
→ adapter_ready
→ fixture_verified
→ desktop_verified
→ released
```

`available` in a service or release manifest means an implementation surface is callable; it does not prove the complete product vertical or a public release.

## Product boundaries

The default UI must not be centered on Runtime, Agent, MCP, model, workflow-builder, or internal audit concepts. Those remain implementation or developer-support surfaces. The user-facing workspace is organized around documents, files, Canvas, learning, cited sources and settings.

The following are explicitly deferred until the compatibility vertical has release evidence:

- general multi-agent runtime and marketplace;
- remote sync and enterprise collaboration;
- 3D/VR;
- broad third-party application adapters;
- public Alpha/Beta/Stable claims.

## Evidence required for vertical completion

A controlled fixture Vault must pass in Chromium and Tauri/Windows:

```text
open → inspect → edit → atomic save → restart/reopen
→ verify relations and attachments → external change
→ conflict resolution → rollback → export/reopen
```

Silent loss, unsafe overwrite, unreported missing attachment, or failed readback blocks the `released` state. Naming and product claims must be checked against `docs/NAMING_CONTRACT_V2.md` before any 0.5.0 release decision.
