# AXR-060 Evidence Truth Reset

## Decision

Release publication evidence and product-capability evidence are separate authorities.

- Immutable public-release readback lives under `reports/release/<tag>/` and binds tag, commit, tree, CI run, Release run, assets, hashes and dependency locks.
- Mutable current-source reports are generated into ignored `.hermes/task-artifacts/` only. A checked-in file cannot truthfully claim to contain the commit that includes itself.
- SHA-bound journey generation refuses a dirty worktree.
- A successful Release may close packaging/publication gates, but it must not promote six-space UI, complete Golden Journey, clean-machine or Tier-A coverage without their own executable evidence.

## Trigger

The v0.6.7 Release was successfully published and read back, while the previous checked-in current reports still described older SHAs and projected unrelated capabilities as partial/not executed. The original v0.6.0 task pack contains 24 tasks and 12 blockers, so release success alone was not a valid completion receipt.

## Verification impact

- New contract tests require complete task/blocker audit coverage.
- Current-report tests require clean-tree exact-SHA semantics and release/product separation.
- Golden Journey receipts name the local journey coverage and explicitly retain unexecuted UI/runtime gates.
- The project test launcher resolves the Git common-dir owner for project-local pytest state, avoiding Win32 path overflow in deeply nested worktrees.
