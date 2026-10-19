# Green UI contract delta — 2026-10-01

## Scope and evidence

Formal current source: 14 targeted UI contract modules, **259 passed, 1 pytest configuration warning**. Green isolated task tree (`D:\All projects\ArcheAxis.Knowledge.Green-x64\.ui-task-tree\ArcheAxis-Knowledge-OS-mainline`): the same list contains one absent module (`tests/test_home_heading_b10_contract.py`). The 13 present modules returned **263 passed, 32 failed, 1 warning**. These are static source/UI contracts, not a desktop runtime, visual raster, backend, or installed Green acceptance result. The Green run used `scripts/runtime/dev.py` and the existing `venv-aaos-ui-312` interpreter with `pytest -q -p no:cacheprovider`; no cache or historical data was cleaned.

The four contracts directly affected by this handoff (theme fallback, brand foreground, seven visible narrow navigation actions) pass in Green. The remaining 32 failures below are retained. Most Green source and test files predate or diverge from Formal; a literal test assertion mismatch alone cannot establish which implementation is correct. Compare each against B10, current Core contracts and a live window before changing it.

## Complete failure classification

Class `SOURCE` means the asserted UI feature/structure is absent or different in Green source. `EXPECTATION` means a literal or exact-shape assertion differs while equivalent behavior is possible; verify behavior before changing test or source. `CONTRACT` means route/data provenance behavior requires interface and runtime inspection. Impact is the user-facing risk if the asserted requirement is real.

| # | Failing test (`tests/`) | Class / impact | Current mismatch and next file to inspect |
|---:|---|---|---|
| 1 | `test_b10_brand_mark_contract.py::test_main_window_uses_48_dip_b10_brand_tile` | SOURCE / medium | Green `MainWindow.axaml` lacks the asserted `TopbarBrand` container; compare B10 brand placement and `SidebarBrandMark` before adjusting the assertion. |
| 2 | `test_avalonia_visual_authority.py::test_suite_scale_and_distinct_search_review_capture_surfaces_exist` | SOURCE / high | Green `MainWindow.axaml.cs` lacks the 420px capture type reflow expression; inspect actual 720px layout. |
| 3 | `test_avalonia_visual_authority.py::test_primary_shell_matches_archeaxis_master_icon_navigation_geometry` | SOURCE / high | Green `MainWindow.axaml` rail geometry differs from the asserted B10 280px hierarchy. |
| 4 | `test_avalonia_visual_authority.py::test_desktop_shell_matches_final_b10_brand_sidebar_and_main_column_header` | SOURCE / medium | Green `MainWindow.axaml` has no `TopbarBrand`; compare topbar/brand hierarchy to B10. |
| 5 | `test_avalonia_visual_authority.py::test_master_icon_system_is_reused_by_primary_and_mobile_navigation` | EXPECTATION / medium | Green `AaosIcon.axaml.cs` lacks the exact `NavigationDot` path string; compare rendered vector geometry. |
| 6 | `test_avalonia_visual_authority.py::test_capture_page_uses_b05_split_capture_and_recent_capture_composition` | SOURCE / high | Green `MainWindow.axaml` capture grid is `*,*` where this assertion expects six auto columns; verify B10 and responsive design. |
| 7 | `test_avalonia_visual_authority.py::test_evidence_page_has_four_core_backed_metrics_and_dense_six_column_table` | SOURCE / high | Green `MainWindow.axaml`/`Views/EvidenceCenterView.axaml` lacks expected metrics/table composition. |
| 8 | `test_avalonia_visual_authority.py::test_evidence_and_all_new_page_grids_reflow_at_compact_widths` | SOURCE / high | Green `MainWindow.axaml.cs` lacks asserted compact reflow for several page grids. |
| 9 | `test_avalonia_visual_authority.py::test_settings_and_machine_learning_match_l5_page_structure_without_fake_values` | SOURCE / high | Green `MainWindow.axaml.cs` lacks the asserted settings grid reflow. |
| 10 | `test_avalonia_visual_authority.py::test_memory_graph_illustration_matches_b10_gold_nodes_and_in_node_labels` | SOURCE / medium | Green `AaosMemoryMapConstellation.axaml` has zero of eight asserted gold nodes; inspect B10 graph composition. |
| 11 | `test_avalonia_visual_authority.py::test_memory_graph_core_uses_b10_three_second_pulse_and_reduced_motion` | SOURCE / medium | Green `AaosMemoryMapConstellation.axaml(.cs)` lacks the asserted graph pulse/visibility contract. |
| 12 | `test_desktop_routes_v1.py::test_navigation_sections_and_contract_page_ids_are_distinct_sets` | CONTRACT / high | Green `MainWindow.axaml.cs` route set differs from expected page contract; compare route registry and current page IDs. |
| 13 | `test_desktop_navigation_contract.py::test_library_to_source_reader_preserves_a_guarded_return_context` | CONTRACT / high | Green `MainWindow.axaml.cs`/`Views/SourceReaderView.axaml` lacks asserted guarded return action. |
| 14 | `test_desktop_navigation_contract.py::test_mobile_layout_avoids_fixed_rail_and_tight_toolbar_rows` | EXPECTATION / medium | Green `MainWindow.axaml.cs` uses `<=` rather than exact `<` breakpoint expression; test the 840px boundary before deciding. |
| 15 | `test_desktop_navigation_contract.py::test_source_reader_and_knowledge_expose_source_context_navigation` | CONTRACT / high | Green `MainWindow.axaml` lacks asserted source context action wording; inspect real route and accessibility. |
| 16 | `test_desktop_navigation_contract.py::test_source_reader_surface_reads_real_core_members_projection` | CONTRACT / high | Green `Views/SourceReaderView.axaml` lacks asserted `Core transform` label; verify Core data projection. |
| 17 | `test_desktop_navigation_contract.py::test_aaos_brand_workspace_empty_and_kpi_typography_use_shared_tokens` | SOURCE / medium | Green `MainWindow.axaml` lacks a requested shared text class; identify exact token. |
| 18 | `test_desktop_navigation_contract.py::test_home_brand_illustration_uses_the_master_constellation_language` | SOURCE / medium | Green `MainWindow.axaml` lacks 14 asserted brand illustration elements. |
| 19 | `test_desktop_navigation_contract.py::test_source_reader_distinguishes_container_members_from_durable_jobs` | CONTRACT / high | Green `Views/SourceReaderView.axaml.cs` lacks asserted job/member state action. |
| 20 | `test_desktop_navigation_contract.py::test_source_reader_has_a_structured_selected_member_detail_card` | CONTRACT / high | Green `Views/SourceReaderView.axaml.cs` lacks `original_name` handling. |
| 21 | `test_desktop_navigation_contract.py::test_home_deduplicates_core_learning_entry_and_labels_optional_workbench` | CONTRACT / medium | Green `MainWindow.axaml` lacks asserted real learning entry wording. |
| 22 | `test_desktop_navigation_contract.py::test_home_surface_uses_plain_language_for_primary_status_and_actions` | SOURCE / medium | Green `MainWindow.axaml` misses the asserted primary action accessibility text. |
| 23 | `test_desktop_navigation_contract.py::test_evidence_center_projects_only_existing_core_read_models` | CONTRACT / high | Green `MainWindow.axaml.cs` lacks asserted memory map toolbar/Core projection behavior. |
| 24 | `test_desktop_navigation_contract.py::test_evidence_library_first_fold_keeps_metrics_and_anchor_table_primary` | SOURCE / high | Green `Views/EvidenceCenterView.axaml` lacks `EvidenceTableBodyGrid`. |
| 25 | `test_desktop_navigation_contract.py::test_memory_map_projects_core_knowledge_lineage_without_fabricating_graph` | CONTRACT / high | Green `MainWindow.axaml` lacks asserted `AaosMemoryMapConstellation` event hookup. |
| 26 | `test_desktop_navigation_contract.py::test_compact_home_and_source_reader_use_explicit_single_column_reflow` | SOURCE / high | Green `MainWindow.axaml.cs` lacks asserted home details reflow. |
| 27 | `test_desktop_navigation_contract.py::test_command_palette_can_execute_evidence_route` | CONTRACT / medium | Green `MainWindow.axaml.cs` route registration differs from asserted Evidence entry. |
| 28 | `test_desktop_navigation_contract.py::test_command_palette_restores_focus_after_close_or_execute` | SOURCE / medium | Green `MainWindow.axaml.cs` lacks explicit `returnFocus?.Focus()` call. |
| 29 | `test_desktop_navigation_contract.py::test_b10_brand_illustration_is_recreated_as_native_vectors` | SOURCE / medium | Green `AaosHomeHeroOrbit.axaml` lacks asserted 380×380 vector composition. |
| 30 | `test_desktop_navigation_contract.py::test_evidence_center_uses_a_b10_native_empty_state_icon` | SOURCE / medium | Green `Views/EvidenceCenterView.axaml` lacks asserted 28×28 native evidence icon. |
| 31 | `test_desktop_navigation_contract.py::test_memory_graph_core_pulse_is_a_smooth_three_second_cycle_and_honors_reduced_motion` | SOURCE / medium | Green `AaosMemoryMapConstellation.axaml.cs` lacks asserted three-second cycle. |
| 32 | `test_toast_b10_motion_contract.py::test_toast_has_b10_translate_scale_opacity_and_eased_220ms_motion` | EXPECTATION / low | Green `MainWindow.axaml` differs from one exact `Border.Transitions` serialization; inspect actual runtime transition before changing. |

## Priority and boundaries

1. **P0:** Resolve the high-impact `CONTRACT`/`SOURCE` items that can affect real Core provenance, Source Reader, evidence, route identity and compact usability (#2, #3, #6–9, #12, #13, #15, #16, #19, #20, #23–26). Use current Formal implementation as a comparison, never as an unreviewed whole-file replacement.
2. **P1:** Check B10 visual composition and live window behavior for #1, #4, #5, #10, #11, #17, #18, #21, #22, #27–31.
3. **P2:** Resolve exact-string/test-shape divergences #14 and #32 using rendered or runtime evidence, then revise only stale assertions.

None of the 32 failures is in the four checks directly changed by this handoff; those four pass separately in Green. The missing `test_home_heading_b10_contract.py` is a separate **missing test file**, not a 33rd failing test. No test was skipped, xfailed or weakened to make the Green result pass. The Green tree remains unqualified for complete UI acceptance.
