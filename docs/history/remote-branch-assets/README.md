# Remote branch residual material (preserved 2026-09-18)

Single archive of every file that exists at a remote branch tip but not (identically)
in `main`: `residual-material-20260918.tar.gz` (members are `<branch>/<original path>`).

Extract with `tar -xzf residual-material-20260918.tar.gz` (Windows 10+ ships bsdtar).
Member contents are byte-faithful copies of the branch blobs: no line-ending, encoding
or whitespace normalisation was applied inside the archive. The expanded copy is *not*
kept in the working tree on purpose - extracting 122 files flat broke the relative
markdown links and carried the sources' trailing whitespace into the repository, which
the documentation preflight and the naming/encoding convention correctly reject.

The audit that selected these files compared each branch tip with the tree its own
merge produced (the squash commit of its merged pull request), not with current `main`;
comparing against current `main` misreports refactored-but-absorbed content as missing.
Thirteen of the seventeen non-main branches matched their squash commit exactly and
therefore contributed nothing here.

Members: 125 across 4 branches.

| branch | tip | original path | sha256 (original bytes) | bytes |
| --- | --- | --- | --- | --- |
| `codex/execution-reliability-standards` | `affc0abc` | `AGENTS.md` | `e9eb75d99c8e2e1c…` | 7440 |
| `codex/execution-reliability-standards` | `affc0abc` | `docs/CODEX_EXECUTION_RELIABILITY.md` | `0447babf46ad9ca3…` | 7865 |
| `codex/execution-reliability-standards` | `affc0abc` | `docs/VERIFICATION_POLICY.md` | `af3a7dca5bb5bd4b…` | 6413 |
| `codex/execution-reliability-standards` | `affc0abc` | `docs/taskpacks/DEEPSEEK_POST_AUDIT_FULL_EXECUTION_TASKPACK_v1_2026-08-11.md` | `8683197f4f276fe7…` | 14025 |
| `codex/execution-reliability-standards` | `affc0abc` | `docs/truth/EXECUTION_STATUS_LOG.md` | `529f2da93072e80d…` | 57654 |
| `codex/execution-reliability-standards` | `affc0abc` | `docs/truth/H0_H1_STATUS_HANDOFF.md` | `5d26d19b4717523c…` | 19733 |
| `codex/execution-reliability-standards` | `affc0abc` | `workspace/configuration/README.md` | `66d9480b47928004…` | 1825 |
| `codex/execution-reliability-standards` | `affc0abc` | `workspace/intake/2026-08-10-codex-execution-reliability-policy.md` | `a1c83636c0c75f47…` | 1663 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/ARCHEAXIS_DYNAMIC_UI_GENERATION_PROMPT_PACK_v1_2026-08-09.md` | `ad9f4e156f02bf59…` | 30149 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/ORIGINAL_SOURCE_MANIFEST.sha256` | `b93a3bda2a77c68f…` | 3038 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/README.md` | `fdbc59af0afaecdd…` | 3069 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/REPOSITORY_COPY_MANIFEST.sha256` | `eb393b66c79d5e80…` | 13313 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/SELECTED_ARCHIVE_ENTRY_MANIFEST.sha256` | `3cec5e6982fd76fb…` | 20508 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/00_START_HERE.md` | `38f3c58b4c486b5c…` | 2318 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/01_PRODUCT_UI_MASTER_SPEC.md` | `baf8ef39e49344e9…` | 2698 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/02_APPLE_STYLE_DESIGN_SYSTEM.md` | `09299abe5c60660a…` | 2977 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/03_GLOBAL_INFORMATION_ARCHITECTURE.md` | `adce27a1cebf2c30…` | 1414 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/04_COMPONENT_LIBRARY.md` | `5f5d921189d3aa35…` | 1264 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/05_FRONTEND_TECHNICAL_PLAN.md` | `cd3094e67075c8bb…` | 1752 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/06_API_AND_DATA_MAPPING.md` | `8936807db5c003c0…` | 1192 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/07_UI_TRUTH_BOUNDARY.md` | `bc23efc10f45971e…` | 1089 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/08_IMPLEMENTATION_FILE_MAP.md` | `0c8f0581196b6359…` | 936 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/09_EXECUTION_PHASES.md` | `e22f9c808f3f9bc3…` | 1029 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/11_ACCEPTANCE_MATRIX.md` | `628cc359cef02c23…` | 1647 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/12_RISK_AND_ROLLBACK.md` | `fafc014612664cf5…` | 950 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/docs/pages/01_GUANXIN_DASHBOARD.md` | `b2e98885521479b0…` | 1012 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/docs/pages/02_AGENT_CENTER.md` | `fef7c18a805cb29a…` | 759 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/docs/pages/03_TASK_MISSION_CONTROL.md` | `8cc40042ba418192…` | 753 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/docs/pages/04_RESEARCH_DASHBOARD.md` | `14a23785d95257e2…` | 590 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/docs/pages/05_KNOWLEDGE_EDITOR.md` | `c7f2a3946628970a…` | 661 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/docs/pages/06_COGNITIVE_CANVAS.md` | `2a10c981d005db86…` | 640 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/docs/pages/07_EXECUTION_REPLAY.md` | `306cee23ad1dccec…` | 578 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/docs/pages/08_CONNECTION_SYSTEM.md` | `157c2d2b2bdddddb…` | 677 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/manifests/assets.json` | `ed8ddb31812acdbd…` | 867 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/manifests/design-tokens.json` | `895adf9b648c4c1d…` | 843 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/manifests/route-map.json` | `0c1bf57dee0effc3…` | 1211 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/manifests/taskpacks/AXAPPLE-A0.json` | `8050dc531a45f8d0…` | 1537 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/manifests/taskpacks/AXAPPLE-A1.json` | `a159703a5285bb41…` | 1676 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/manifests/taskpacks/AXAPPLE-A2.json` | `90be3d5dc76a36bb…` | 1572 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/manifests/taskpacks/AXAPPLE-A3.json` | `312e2f6923a33162…` | 1661 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/manifests/taskpacks/AXAPPLE-A4.json` | `69bf2c900b358357…` | 1598 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/apple-desktop-ui-v1.0/manifests/taskpacks/AXAPPLE-A5.json` | `c2362fa28d2fbd4d…` | 1584 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/00_START_HERE.md` | `0f3a4129ad16502a…` | 2527 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/01_CLOUD_REAUDIT.md` | `d9edd71ce556402c…` | 5746 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/02_FRONTEND_FUSION_MASTER_PLAN.md` | `be479b285e623c7f…` | 4405 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/03_UI_INFORMATION_ARCHITECTURE.md` | `c408bb1fc7898592…` | 1764 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/04_VIOLET_CORE_DESIGN_SYSTEM.md` | `7111bbd2cfff6568…` | 2822 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/05_CURRENT_TO_TARGET_FILE_MAP.md` | `8721b99c3926d900…` | 2379 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/06_API_GAPS_AND_BACKEND_CHANGES.md` | `d21c9b811bbc00c2…` | 2185 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/07_DESKTOP_A1_TASKPACK.md` | `06b898834bd28409…` | 4063 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/08_DESKTOP_A2_TASKPACK.md` | `7f1e9a6e92d9af2e…` | 1464 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/09_DESKTOP_A3_TASKPACK.md` | `130d0088b47093fb…` | 1210 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/12_GITHUB_PR_CI_RELEASE_PLAN.md` | `c30e67d59b983142…` | 1227 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/13_ACCEPTANCE_TEST_MATRIX.md` | `29d4b298c02c0327…` | 1929 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/14_RISK_AND_ROLLBACK.md` | `158c9c92e9017a42…` | 1366 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/manifests/baseline.json` | `5b043f0856944520…` | 950 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/manifests/component-inventory.json` | `a1e0f07c354904b9…` | 859 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/manifests/design-tokens.json` | `054372aa16f78d29…` | 939 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/manifests/route-map.yaml` | `4b40bd085460ebaa…` | 1227 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/manifests/taskpack-a1.json` | `534ae394242b7201…` | 1327 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/manifests/taskpack-a2.json` | `7620f8a61be2a5d0…` | 1372 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/desktop-cloud-reaudit-v1.0/manifests/taskpack-a3.json` | `76f0de95cfbd0110…` | 1291 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/open-source-absorption-2026-07-25/manifest.json` | `5e74a271d1c372bf…` | 661 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/00_START_HERE.md` | `0eae119a3581e62f…` | 2014 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/09_HERMES_MASTER_TASKPACK.md` | `ceef3a4a4bc5ac03…` | 5277 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/docs/02_FINAL_PROJECT_POSITIONING.md` | `4a30bd06b5fcc074…` | 2635 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/docs/03_CONSOLIDATED_SYSTEM_BLUEPRINT.md` | `fe62069ccaaf9c1f…` | 2573 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/docs/04_CLOUD_REAUDIT_LATEST.md` | `c32caa021ddd4cdd…` | 2324 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/docs/05_TECH_STACK_AND_CONFIGURATION.md` | `5a6917f7f38d326c…` | 3329 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/docs/06_FRONTEND_DESKTOP_FUSION.md` | `02d3226b1e9169bf…` | 2314 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/docs/07_APPLE_UI_PAGE_MAP.md` | `114df7f498aa5178…` | 1650 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/docs/08_EXECUTION_ROADMAP.md` | `4f511c2e2539cf0b…` | 1618 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/docs/10_ACCEPTANCE_MATRIX.md` | `872fba160d624f18…` | 1337 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/docs/11_RISK_AND_ROLLBACK.md` | `3d1610624c423afe…` | 913 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/manifests/decision-register.json` | `cd8508bc3a5d8077…` | 1307 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/manifests/target-configuration.yaml` | `5260bb8e523089a0…` | 1168 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/manifests/taskpack-AXOS-TODAY-01.json` | `e96bb4d1d38d9f08…` | 1300 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/previous-deliverables/ArcheAxis_Desktop_HERMES_Master_TaskPack_v1.0.md` | `ac47a567cf08efcf…` | 14870 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/taskpacks/AXOS-TODAY-00_BASELINE.md` | `515a960809bc8a68…` | 267 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/taskpacks/AXOS-TODAY-01_REPOSITION.md` | `d75403cf46c95c3f…` | 361 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/taskpacks/AXOS-TODAY-02_CONFIG_PLAN.md` | `d9d2ef09b2c1baec…` | 318 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/taskpacks/AXOS-TODAY-03_APPLE_SHELL.md` | `7a719bfb867a50c8…` | 415 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/taskpacks/AXOS-TODAY-04_LEARNING_KNOWLEDGE_UI.md` | `c4b94ad719d490ee…` | 324 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/pack-extracts/today-archive-v1.0/taskpacks/AXOS-TODAY-05_AI_USAGE.md` | `e5f68a027422f1a8…` | 287 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/plans/2026-07-14_002006-cognitive-loop-os-integrated-execution.md` | `069c037ba69a0271…` | 20927 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/plans/2026-07-17_224545-deepseek-execution-handoff.md` | `d464821385cecf0c…` | 3135 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/plans/2026-07-20_192250-cognitive-workspace-minimum-closed-loop.md` | `6bc7201430bd678d…` | 15713 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/plans/2026-07-23_004441-unresolved-work-inventory.md` | `bd2751660933fa06…` | 6995 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/plans/2026-07-26_212205-full-absorption-roadmap.md` | `d9cb7bad00c1b3d6…` | 20043 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/plans/2026-07-28_platform-execution.md` | `4d32453fa7f5ebda…` | 12754 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/plans/2026-08-09_taskpack-followup.md` | `7f2868c90a656bef…` | 11254 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/source-documents/ArcheAxis OS Audit and Blueprint.docx` | `4a6bebdba90462d6…` | 26298 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/source-documents/ArcheAxis OS Test Cases.docx` | `6532e3054d7cf6ae…` | 27687 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/source-documents/ArcheAxis_OS_CI_Acceleration_WORKLAB_Compatible_HERMES_TaskPack_2026-08-07.md` | `03a4f77354c5e32a…` | 57315 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/source-documents/ArcheAxis_OS_Cloud_Full_Audit_Integrated_TaskPack_2026-08-07.md` | `d52c4d62bf7c4565…` | 48389 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/source-documents/ArcheAxis_OS_Minimum_Surface_Master_TaskPack_2026-08-06.md` | `0d8545c9f36d0c13…` | 42595 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/historical-sources-2026-07-14-to-2026-08-08/source-documents/ArcheAxis_OS_Only_Product_UI_Naming_Compatibility_Audit_2026-08-08.md` | `d49c8c7fb91f58d3…` | 33751 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/planning-2026-08-09/ArcheAxis_Workspace_CODEX_Final_Master_TaskPack_v3_2026-08-09.md` | `ea09069818d918a6…` | 148593 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/planning-2026-08-09/ArcheAxis_Workspace_Context_Handoff_2026-08-10.md` | `5999cf7f1674dd15…` | 10152 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/planning-2026-08-09/ArcheAxis_Workspace_Final_Master_TaskPack_v4_2026-08-09.md` | `e52a520be4417628…` | 248880 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/planning-2026-08-09/ArcheAxis_Workspace_Future_Master_Blueprint_v1_2026-08-09.md` | `bab757afd90c541c…` | 40898 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/planning-2026-08-09/ArcheAxis_Workspace_Planning_Sources_original_2026-08-09.zip` | `a2838ecc32ff1d0a…` | 210060 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/planning-2026-08-09/ArcheAxis_Workspace_v0.5_Multiformat_Full_Audit_and_Recovery_TaskPack_2026-08-09.md` | `d8e9cf99a145650f…` | 33285 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/planning-2026-08-09/ORIGINAL_SOURCE_MANIFEST.sha256` | `417c5dd9ca76355f…` | 649 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/planning-2026-08-09/PLANNING_SOURCE_LINEAGE_2026-08-10.md` | `529ae5a3bdb129a2…` | 3041 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/planning-2026-08-09/README.md` | `b9f441fec76c2339…` | 3518 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/planning-2026-08-09/REPOSITORY_COPY_MANIFEST.sha256` | `9902a1010ab4046a…` | 649 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `docs/change-proposals/ArcheAxis_Workspace_Multiformat_Recognition_Web_Verification_Enhancement_TaskPack_v1_2026-08-11.md` | `5331fdfa20ecf6de…` | 62990 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `workspace/intake/2026-08-09-capability-first-knowledge-lifecycle.md` | `81ca5b22892669d1…` | 4262 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `workspace/intake/2026-08-09-frozen-roadmap-deepseek-execution-pack.md` | `4ea10b66a374785b…` | 1383 |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | `workspace/intake/2026-08-09-mandatory-web-knowledge-ingestion.md` | `1bbb73377e397eb1…` | 1708 |
| `docs/verification-summary-2026-08-09` | `8cc9c690` | `docs/VERIFICATION_SUMMARY_2026-08-09.md` | `f5358da3dc7c17af…` | 11525 |
| `feat/naming-step3` | `bc4a234f` | `.github/workflows/ci.yml` | `329d43bd29a11e9e…` | 32966 |
| `feat/naming-step3` | `bc4a234f` | `app/cli.py` | `20b1ce93599b5943…` | 5056 |
| `feat/naming-step3` | `bc4a234f` | `app/main.py` | `94c5eb54292441a2…` | 25299 |
| `feat/naming-step3` | `bc4a234f` | `app/runtime_entrypoint.py` | `67a03b3b550794ac…` | 10482 |
| `feat/naming-step3` | `bc4a234f` | `app/workspace/router.py` | `ad49be97f0402e32…` | 27467 |
| `feat/naming-step3` | `bc4a234f` | `desktop/src-tauri/src/protocol.rs` | `a96d9e9cfd0ce619…` | 2126 |
| `feat/naming-step3` | `bc4a234f` | `desktop/src-tauri/tauri.conf.json` | `93b6753c0b156436…` | 683 |
| `feat/naming-step3` | `bc4a234f` | `docs/truth/SUPPLY_CHAIN_LEDGER.json` | `df31927c1aa1e9c4…` | 27405 |
| `feat/naming-step3` | `bc4a234f` | `scripts/a0_browser_smoke.py` | `7c2b225b532640e3…` | 19128 |
| `feat/naming-step3` | `bc4a234f` | `scripts/check_repository_conventions.py` | `2fdaabcdee190156…` | 15181 |
| `feat/naming-step3` | `bc4a234f` | `scripts/generate_phase0_baseline.py` | `8510c4205e468430…` | 49618 |
| `feat/naming-step3` | `bc4a234f` | `shared/config.py` | `7624cae082636fae…` | 14446 |
| `feat/naming-step3` | `bc4a234f` | `tests/test_phase0_baseline.py` | `8ae1d4406bcc066c…` | 10326 |

## Review note

These versions are older than `main`. They are for semantic review only; absorption
decisions belong to the owner or to CODEX/HERMES, and nothing here may be applied
wholesale. Deleting one of these branches without first making a `git bundle` backup
would still lose the 3 binary members (2 `.docx`, 1 `.zip`) that exist only here and on
the branch.
