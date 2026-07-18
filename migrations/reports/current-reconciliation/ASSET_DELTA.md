# Asset Delta

Generated: `2026-07-17T22:31:07+08:00`

## Package integrity

- ZIP safely extracted outside the repository after path-traversal validation.
- ZIP contains 97 files total: 96 checksum-governed package files plus `CHECKSUMS.json`.
- All 96 declared SHA-256 checksums verified; no missing, changed, or undeclared extracted files.
- Attached XLSX was fully extracted and read; Star values are a 2026-07-17 planning snapshot, many explicitly approximate.

## Existing repository registry

### `main`

- Current path: `shared-contracts/registries/open_source_project_registry.json` plus CSV compatibility copy.
- Actual JSON rows: 101.
- ID range: `osp_0001` through `osp_0103`.
- Missing legacy IDs: `osp_0093`, `osp_0095`.
- Exact duplicate names present: Firecrawl, browser-use, MinerU.
- Canonical duplicate groups additionally identified by the XLSX: Marker and sqlite-vec.

### Container/Phase 4 lineage

- Registry was packaged at `inspiration_research/resources/open_source_project_registry.json` and old registry files were removed from that candidate tree.
- Actual packaged rows remain 101 with the same missing IDs and duplicate groups.
- This relocation is a package-resource delivery change, not Registry V2 governance.

## New planning assets

The package adds governance designs, not integrated runtime capabilities:

- Registry V2 schema, inheritance map, priority backlog and migration TaskPack.
- Five Claude assets: Claude Code, Skills, GitHub Action, Python SDK, TypeScript SDK.
- Two xAI assets: `grok-1` and `grok-build`.
- Model Registry V1 design and provider/model policy foundation.
- Cognitive Workspace, plugin, sync/publish and future model/agent plans.

Attached XLSX contains 101 raw `osp_*` rows plus 7 `ext_*` rows. Duplicate raw rows must be preserved through migration provenance but canonical repositories must be deduplicated in V2 views.

## Required corrections to package assumptions

1. “103-entry registry” means the historical ID namespace ends at `osp_0103`; the actual current row count is 101 because IDs 0093 and 0095 are absent.
2. The package path `shared-contracts/registries/...` is true for `main`, but the Phase 4/container candidate has already relocated the JSON resource. A V2 migration must support both source layouts and choose one runtime SSOT after branch reconciliation.
3. PR #1 and PR #2 already contain work newer than the package’s verified `main@9a0886a`; their actual diffs must be reconciled before applying file-level plans.
4. Star counts marked approximate are not verification evidence and must never drive automatic absorption.
5. Claude/xAI/Open-source candidates remain candidate/research assets. No cloning, execution, dependency installation, Grok-1 weight download, or production provider activation occurred in P00.

## Disposition

- Existing registry rows: preserve losslessly.
- Duplicate/missing IDs: preserve as migration provenance; resolve through V2 canonical IDs/aliases, not destructive deletion.
- Registry V2: eligible only after Phase 3 release closure as its own low-risk data-governance train.
- Model Registry foundation: contract-only candidate after release reconciliation; no production calls or secrets.
- Claude/Grok assets: Phase 11 / isolated Research-Intake-Contract TaskPacks; may not preempt Phase 3–9.
- Security-research candidates: metadata-only, isolated research, never auto-install or expose to Cognitive Runtime.
