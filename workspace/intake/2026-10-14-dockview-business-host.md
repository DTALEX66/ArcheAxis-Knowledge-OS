# FE06 Dockview business host slice

The formal desktop App now consumes Dockview 8.5.1. Dependency manifest and lock
pin dockview-react, dockview and dockview-core to 8.5.1, MIT, official npm registry.
Existing locked dependencies remain unchanged. CSS is imported from the installed
package; the project adds only scoped theme/geometry overrides.

PanelRegistry retains stable DOM hosts across Dock panel close, relocation and
layout reset. React portals remain mounted to those same hosts. The App-owned
CoreWorkingStateSession continues to own document drafts and frozen requests.
Reader/library/history share one reader family; AI pages share one model family;
catalog/detail share one catalog family. Layout reset issues no document delete,
draft clear, inference cancel or new model call. Confirmed workspace replacement
still replaces the App-owned working session under the existing restore guards.

WorkspaceController consumes BE02 finite layout_read/write/recover with strict
public DTO validation, workspace/epoch/device identity and revision CAS. Presets
persist finite trees and floating bounds only, excluding arbitrary component
names, object content and Dockview params. Readback does not automatically merge
unsaved layout; explicit apply and recovery controls expose the decision.

Status: PARTIAL. This slice retains one reader per workspace, with multiple
document drafts in the existing shared journal; it does not implement separate
concurrent object views or a new cross-editor write lease service. Floating
single-panel groups roundtrip; floating multi-tab/nested groups, popout/edge
groups, empty/all-floating trees are visibly refused by the finite contract.
Lock is a current-session control; BE02 does not yet persist lock. Device UUID
is the sole browser preference; layout/content are not stored in browser storage.
Actual installed restart, screen geometry and native interaction remain UNVERIFIED.

Tests use actual Dockview serialization and DOM consumers with synthetic viewport
geometry and mock business surfaces/native receipts. They establish behavior,
not REAL user material, installed runtime, pixel fidelity or Owner acceptance.
