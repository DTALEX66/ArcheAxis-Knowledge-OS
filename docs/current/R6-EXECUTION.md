# R6 执行台账

- plan_id: AAK-LOCAL-GREEN-ABSORB-FIRST-20260919-R6
- taskpack_revision: R6
- taskpack_sha256: $sha
- baseline_head_at_registration: $head
- delivery line: main = Local Green Development Line
- release status: FROZEN; no tag/release/product-version promotion

## 当前切片

### A00 — Authority Reset

状态：IMPLEMENTED_LOCAL_PENDING_TEST

已完成：

- 将用户提供的 R6 任务包保存到 docs/authority/taskpack-0919-r6/TASKPACK.md。
- 生成 EXECUTOR-START.md、TASKS.json、MANIFEST.json，并绑定任务包 SHA-256。
- 将 AGENTS.md 与 docs/CONFIGURATION_AUTHORITY_INDEX.md 的当前计划指针切换到 R6。
- 保留 R5、R3.1 及更早任务包和收据，不删除历史。

待验证：

- JSON/Markdown 权威索引定向检查。
- R6 状态文件与当前 Git SHA 绑定。

### A01–A16

状态：PLANNED 或 BLOCKED_BY_PRECONDITION，不从 R5 的 PARTIAL 或 DEFERRED 自动提升。每个切片须先登记真实代码、输入边界、测试命令和证据等级。

## 证据规则

文档、计划、静态检查和构建结果不能替代运行时、独立审计或 Owner Gate。未测项目标记 NOT_EXECUTED；缺外部资源、Owner 决策、证书、干净机或真实 Green 资格时标记 BLOCKED。

### A03 — Capability Absorption Registry

状态：`TESTED_LOCAL`

- subject_sha: `9c66fbce27c47d63ca8d6cffd75edba114d548bb`
- changed_paths: `config/schemas/capability-absorption-registry.schema.json`, `docs/truth/CAPABILITY_ABSORPTION_REGISTRY.yaml`, `tests/test_capability_absorption_registry.py`, `docs/CONFIGURATION_AUTHORITY_INDEX.md`
- upstream_absorbed: none; donor entries are candidates/reference/algorithm or sidecar roles only
- upstream_version_or_sha: `UNPINNED_REVIEW_REQUIRED` for unverified upstreams
- license: every unverified upstream is explicitly marked pending readback; internal core is first-party MIT
- tests: `tests/test_documentation_authority_index.py tests/test_capability_absorption_registry.py` — 12 passed, exit 0
- actual_runtime_result: registry/schema validation only; no external provider was started
- data_touched: repository registry and schema only
- external_paths_touched: none
- limitations: exact upstream revisions, licenses, model licenses, benchmarks and runtime probes remain open
- rollback: revert commit `9c66fbce27c47d63ca8d6cffd75edba114d548bb`; canonical existing supply-chain ledger remains preserved
- remaining_gap: A02 resource schema decision and A04 Knowledge/Source V3 contract

