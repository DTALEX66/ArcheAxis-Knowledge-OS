# Review title frontend + native probe proposal

Status: NOT_EXECUTED / UNAPPLIED. No product files, generated DTOs or existing tests
were written. No tests, build, host, browser, model or services were run.
Only these two requested ignored proposal files were created.

Dependency: first review/apply proposed-core.patch and regenerate
frontend/src/api/generated/core-contract.ts from the optional display_title schema:

```powershell
& .\.venv\Scripts\python.exe -B scripts/contracts/generate_core_document.py
```

Scope: preserve item_key as React key, callback/API argument, breadcrumb id and
persisted identity. Display the optional Core title in both queues and breadcrumb;
old Core missing-title results display 学习项目. No title=id fixture substitution.
Teaching and resolved learning journey titles use only already verified course and
fixed assessment content, with no extra Core request. Identity checks are unchanged.
The display helper matches Core whitespace/control rules and 80 Unicode scalars.
Generated DTO consumers are reused rather than handwritten item DTO shadows.

Two queue buttons expose data-learning-item-key. Existing lifecycle tests use a
shared test identity selector helper; independent tests assert actual visible titles,
same-title items preserving distinct callback/API keys, legacy fallback and breadcrumb.
Native probes use the original trusted click flow, with a queue-scope-only selector
branch using exact escaped attributes and hidden-view filtering. Synthetic native
course wait observes the key attribute, then clicks through existing ui_click.
No JavaScript input, synthetic click, execute bypass or additional model call.

Proposed checks include old Core absence acceptance, null/empty/number/81-emoji
rejection, 80-emoji acceptance, Unicode display parity, fixed assessment title,
Teaching course title, duplicate-title selection, unchanged call count, and Python
DOM selector identity/quote/hidden-view tests. All are NOT_EXECUTED.

Suggested targeted commands after BOTH proposals and DTO generation are applied:

```powershell
& .\.venv\Scripts\python.exe scripts/runtime/dev.py --run-id review-title-frontend -- node frontend/node_modules/vitest/vitest.mjs run --root frontend src/__tests__/LearningTitle.test.ts src/__tests__/CoreBridge.test.ts src/__tests__/CanonicalLearningDrafts.test.tsx src/__tests__/CanonicalReviewLearning.test.tsx src/__tests__/LearningPracticeJourney.test.tsx src/__tests__/LiveRegionBudget.test.tsx src/__tests__/ThreeLevelNavigation.test.tsx src/__tests__/UiFirstWorkspace.test.tsx
& .\.venv\Scripts\python.exe scripts/runtime/dev.py --run-id review-title-probe --pytest -- tests/test_grouped_native_owner_probe.py tests/test_tauri_shell_authority.py -q
```

Static-only validation performed while preparing proposal: Python AST parse (not
execution), exact replacement anchors and resulting patch context matching. No
TypeScript compiler, Vitest, pytest, native run or bundle validation was executed.

Existing selector replacement counts (no fixture titles forged):
- `frontend/src/__tests__/CanonicalLearningDrafts.test.tsx`: 13
- `frontend/src/__tests__/CanonicalReviewLearning.test.tsx`: 4
- `frontend/src/__tests__/LearningPracticeJourney.test.tsx`: 1
- `frontend/src/__tests__/LiveRegionBudget.test.tsx`: 1
- `frontend/src/__tests__/ThreeLevelNavigation.test.tsx`: 1
- `frontend/src/__tests__/UiFirstWorkspace.test.tsx`: 1

Proposal file set and base on-disk SHA-256 (NEW means absent at generation):
- `frontend/src/presentation/learningTitle.ts`: `NEW`
- `frontend/src/test/learningQueue.ts`: `NEW`
- `frontend/src/spaces/CanonicalLearningSpace.tsx`: `a8a34c5b5eeb3c4b76009fd37bae3b0def30268a7ba6c00fd5809bc5d5eacd62`
- `frontend/src/spaces/CanonicalWorkspaceSpace.tsx`: `89b6ee72810ad2557d771b2220c6f71606e7883dee5d488dfdf9fd89f6200f54`
- `frontend/src/presentation/workspaceReview.ts`: `eb4aee42d44bab83077c108d45adf68ee27351f6888f0b2763f5bd903fbb0e0b`
- `frontend/src/presentation/learningJourney.ts`: `0be07ea7aa11a4d0dc685ea97b97338d9fd5c50ffcf81ed694010fb4daecdbd3`
- `frontend/src/spaces/CanonicalTeachingSpace.tsx`: `6d0a692b03c358d59df4c6f6eb6a1f0905a49976a4cc28db08beb1d1f6cbb1c6`
- `frontend/src/__tests__/CanonicalLearningDrafts.test.tsx`: `047fece8d1c5fd4462027146d655c98a5a8f31a96be2cb25f3583074ff137f5d`
- `frontend/src/__tests__/CanonicalReviewLearning.test.tsx`: `29c47531d16adb547297e7aecaaef4cb870be6fd4a1c9cf2cd93c688dd52d108`
- `frontend/src/__tests__/LearningPracticeJourney.test.tsx`: `af32f9fcd7b63f2fcdfe1d444bdc50d7c43294d9cbf58d7fec6cfe91bad71906`
- `frontend/src/__tests__/LiveRegionBudget.test.tsx`: `7c206393364c09f6a8c81a8e311b737a52b5984905b9480cabaaeb56fa3f49cb`
- `frontend/src/__tests__/ThreeLevelNavigation.test.tsx`: `eb519adefb4e4c707baf426a13250dee20d4ea40ad9392cfa65e0a5412d5c508`
- `frontend/src/__tests__/UiFirstWorkspace.test.tsx`: `11ebf1f97894bc875d2e7a017a179f086430d68652cf4037a882141a5e01c38c`
- `frontend/src/__tests__/CoreBridge.test.ts`: `ff5b6bf83fb272f27ef591ed9fe45610c2c93639348b418c878d28b6a1bc82ee`
- `frontend/src/__tests__/LearningTitle.test.ts`: `NEW`
- `scripts/probes/aaos01_grouped_owner_loop.py`: `ac6aa884a259322bdc26c0f721206579b71658119b02c2798753b5c4d4b47467`
- `scripts/probes/aaos01_tauri_webdriver_loop.py`: `f948a27efa6732cd13703a37cbd4774bad0b55aae2bb347173309765335be130`
- `tests/test_grouped_native_owner_probe.py`: `6cb352d6c3361e334cb9392355a603a6ed85bcde3a479aaee66697e42db77a11`
- `tests/test_tauri_shell_authority.py`: `b59a3c45201bbdad707536016bb1f01399b2b81ebd74a2fff80663d1b4ceafd1`

Proposal SHA-256: `73551dc2b7cabd94e0c15edda157e5c9e5510ea1f2b1d26611b18c52b815ed15`
