# FE06 specialized document writer lease integration

The shared Dock business session now guards existing versioned document writes in Expression, Research, Context, AI Assets, asset grants, teaching preparation and TemplateWorkspace. A separate object may keep its own writer; another view of the same object stays readonly. New-document creation and independent teaching records retain their existing contracts. The lease does not turn ordinary saves into an approval workflow, change Core CAS, cancel reasoning or delete retained drafts.

Actual Canvas and Research consumers are tested against a reader-held object lease with synthetic Core receipts; no document_draft is dispatched. Existing save, retry and unknown-payload regression suites remain required. Library and Relation integration was delivered in the prior slice. Standalone components without the Dock provider retain their prior behavior.

Evidence remains local/SYNTHETIC: installed native concurrency and real material qualification are UNVERIFIED. Object-instance layout persistence, grouped floating layouts, empty/all-floating layouts and persisted lock require the parent-owned Core DTO upgrade. The current adapter explicitly refuses unsupported layouts instead of claiming persistence.
