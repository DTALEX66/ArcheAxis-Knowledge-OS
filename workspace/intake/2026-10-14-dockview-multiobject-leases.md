# FE06 incremental multi-object session slice

First-slice delivery remains immutable under
`.project-local/artifacts/fe06-delivery-20261014/`; its 15 source files were
SHA-256 verified and preserved as the incremental baseline before new changes.

The actual DockWorkspace now opens stable `document.<object_id>` views beside
the existing reader. Repeated opening focuses that same instance. Closing only
detaches its retained DOM host; reopening reuses the same React tree and draft.
The session identity is workspace + restore epoch + document object ID. View
identity is separate. DocumentBusinessSessions holds one write owner per object,
not one writer per visual pane. Different objects can independently hold leases.

CanonicalLibrarySpace consumes this lease for editor creation, draft writes and
historical restore. Duplicate object views present shared Core-journal drafts
read-only; they do not mount another DocumentEditor. CanonicalRelationSpace and
its collection mutation port consume the same object lease for mutations/save.
The original CAS, frozen requests, journal-before-save, post-ACK cleanup and
unknown-receipt recovery semantics are retained. A lease is runtime ownership,
not a persisted permission grant or an idempotency key. During an in-flight write,
object switching defers lease release until completion and never cancels the write.

The current BE02 DTO accepts canonical page IDs only. Saving any object-instance
layout is explicitly refused before native dispatch. No browser layout substitute
or discarded-object serialization is used. Parent owns the negotiated Core DTO
extension for instance bindings, floating groups, empty/all-floating layouts and
persisted locking. Until that lands, object layout restart is UNVERIFIED.

Status: PARTIAL. Lease consumers currently cover reader/history and relation/
collection writes. Canvas/research and other specialized writer integration remains
outside this slice. Tests exercise real Dockview and these actual consumers with
synthetic material/Core receipts; installed concurrency and real user data are
UNVERIFIED. No commit/push, new permission request or shared dependency write.
