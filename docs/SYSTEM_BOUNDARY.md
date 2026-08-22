# v0.6.1 System Boundary (v0.6.0 task scope)

ArcheAxis Knowledge is a local-first trusted-knowledge workspace. The v0.6.1
remediation release carries the following v0.6.0-defined closed-loop boundary:

```text
Windows startup → four user-chosen libraries → RawAsset SHA-256 preservation
→ conversion + physical anchors + LossReport → candidate evidence
→ identified human review → EvidenceBundle / KnowledgeVersion
→ independently governed Human Learning and AI assets → display/export/restart readback
```

The canonical desktop implementation is `frontend/` plus root `src-tauri/`.
`desktop/`, `OSUI/`, `app/workspace/ui/`, and root static pages are migration or
reference surfaces, never v0.6.1 release authority.

WORK-LAB and DESIGN-LAB are external coordinators. They interact only through
versioned APIs, commands, receipts, and events; they do not share the product's
authoritative databases. Optional OCR, ASR, model, and external-resource
capabilities are replaceable adapters and must report honest degradation when
missing. No installed build may require a development-machine absolute path.

This document defines a release boundary, not a completion assertion. The
current release state is `v0.6.1 development — PARTIAL` until exact-SHA tests,
Golden Journey evidence, and Windows lifecycle evidence are available.
