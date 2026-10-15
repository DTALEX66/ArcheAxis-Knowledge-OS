# Scope-bounded operation readiness

BE07 reads the existing Core launch route registry and capability settings. It does not create a second capability catalog or infer runtime qualification from Atlas/page mappings. POST `/api/v1/operation-readiness` accepts one scope and at most 32 unique finite operation names. The native command is `operation_readiness`.

Each observation separates implementation, dependency file presence, connection, runtime qualification and effective capability enablement. Queries never spawn a worker, probe an engine, query model inventory, load a model or perform network access. Connection remains UNKNOWN and qualification UNVERIFIED. Registered files and enabled operations therefore aggregate UNVERIFIED, never READY. Missing/disabled entries are NOT_READY; unreadable permissions remain UNKNOWN. Unknown operations have no implementation. Parent aggregation considers every requested child and expiry; one ready child cannot qualify its siblings. Snapshots expire after 30 seconds and authorize no execution.

The existing Atlas capability page consumes only the selected entry's runtime operation mapping, discards wrong-scope and late responses, and clears observations on expiry. Opening the catalog alone no longer triggers all-worker handshakes. Refresh is scoped to the current view and does not poll models. The legacy explicit capabilities endpoints remain available for diagnostic callers; they are not used by this readiness consumer.

Answer and retest execution call `require_execution_dependencies` immediately before the worker invocation. That obtains fresh dependency/enablement state rather than trusting a UI snapshot. Existing frozen model configuration, human grants, source/context checks, model inventory and execution receipt validation remain separate mandatory checks. This dependency check is not model readiness, permission to use arbitrary input, or an installed-runtime qualification.

Integration qualification is PARTIAL until final API/native/installed receipts. No model or engine is declared operational by the no-probe status endpoint. Download/install planning and heavy readiness engines are outside BE07.
