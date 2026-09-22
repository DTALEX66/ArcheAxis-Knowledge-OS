"""The formal Avalonia shell exposes honest first-use domain navigation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
XAML = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml"
APP_XAML = ROOT / "apps" / "ArcheAxis.Desktop" / "App.axaml"
THEME_XAML = ROOT / "apps" / "ArcheAxis.Desktop" / "Themes" / "AaosTheme.axaml"
CODE = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml.cs"


def test_aaos_theme_is_shared_at_application_scope() -> None:
    app = APP_XAML.read_text(encoding="utf-8")
    theme = THEME_XAML.read_text(encoding="utf-8")
    assert 'StyleInclude Source="avares://ArcheAxis.Desktop/Themes/AaosTheme.axaml"' in app
    assert '<Styles xmlns="https://github.com/avaloniaui"' in theme
    for token in ("AaosBackgroundBrush", "AaosPrimaryBrush", "AaosSuccessBrush", "AaosErrorBrush"):
        assert f'x:Key="{token}"' in theme
    assert 'RequestedThemeVariant="Dark"' in app
    assert 'x:Key="AaosPrimaryGradientBrush"' in theme
    assert '<Style Selector="Button.primary-action">' in theme
    assert '<Setter Property="Foreground" Value="{DynamicResource AaosPrimaryTextBrush}" />' in theme
    assert '<Setter Property="Foreground" Value="#061118" />' not in theme
    assert '<Style Selector="Button:focus">' in theme
    assert '<Style Selector="Button:disabled">' in theme
    assert '<Style Selector="TextBox:disabled">' in theme
    assert '<Style Selector="ComboBox:disabled">' in theme
    assert '<Style Selector="ListBoxItem:pointerover">' in theme
    assert '<Style Selector="ComboBoxItem:pointerover">' in theme
    assert '<Style Selector="TextBox:pointerover">' in theme
    assert '<Style Selector="ComboBox:pointerover">' in theme
    assert '<Style Selector="CheckBox:focus">' in theme
    assert '<Style Selector="TextBlock.status-loading">' in theme


def test_aaos_theme_absorbs_suite_spacing_density_breakpoint_and_command_tokens() -> None:
    theme = THEME_XAML.read_text(encoding="utf-8")
    for token in (
        "AaosSpace4",
        "AaosSpace8",
        "AaosSpace12",
        "AaosSpace16",
        "AaosSpace24",
        "AaosSpace32",
        "AaosSpace48",
        "AaosSpace64",
        "AaosRadius4",
        "AaosRadius12",
        "AaosRadius18",
        "AaosRadius24",
        "AaosDensityDefault",
        "AaosDensityCompact",
        "AaosTabletBreakpoint",
        "AaosMobileBreakpoint",
        "AaosCommandPaletteGesture",
        "AaosOverlayBrush",
    ):
        assert f'x:Key="{token}"' in theme


def test_aaos_theme_exposes_reusable_provenance_and_surface_component_styles() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    theme = THEME_XAML.read_text(encoding="utf-8")
    for selector in (
        '<Style Selector="Border.aaos-card"',
        '<Style Selector="Border.aaos-card-compact"',
        '<Style Selector="TextBlock.provenance-original"',
        '<Style Selector="TextBlock.provenance-evidence"',
        '<Style Selector="TextBlock.provenance-machine"',
        '<Style Selector="TextBlock.provenance-projection"',
        '<Style Selector="TextBlock.provenance-review"',
    ):
        assert selector in theme
    assert 'Classes="aaos-card"' in xaml
    assert 'Classes="provenance-projection"' in xaml


def test_learning_review_card_uses_provenance_semantics_without_new_truth_fields() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    theme = THEME_XAML.read_text(encoding="utf-8")
    assert 'x:Name="LearningEvidenceText" Classes="provenance-evidence"' in xaml
    assert 'x:Name="LearningOriginalText" Classes="provenance-original"' in xaml
    assert 'x:Name="LearningVersionText" Classes="provenance-projection"' in xaml
    assert 'x:Name="LearningMemoryText" Classes="provenance-review"' in xaml
    assert 'x:Name="ReviewOutcomeBox" Classes="review-control"' in xaml
    assert '<Style Selector="ComboBox:focus"' in theme
    assert 'assessment_id' in xaml or 'assessment_id' in CODE.read_text(encoding="utf-8")


def test_inspector_source_chain_is_a_structured_reusable_surface() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    theme = THEME_XAML.read_text(encoding="utf-8")
    assert 'x:Name="InspectorSourceChain"' in xaml
    assert 'Classes="aaos-card-compact"' in xaml
    assert 'x:Name="InspectorChainSourceText" Classes="provenance-projection"' in xaml
    assert 'x:Name="InspectorChainVersionText" Classes="provenance-projection"' in xaml
    assert 'x:Name="InspectorChainProjectionText" Classes="provenance-projection"' in xaml
    assert '<Style Selector="StackPanel.aaos-source-chain"' in theme


def test_command_palette_has_real_keyboard_open_close_and_route_contract() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'KeyDown="OnWindowKeyDown"' in xaml
    assert 'x:Name="CommandPaletteOverlay"' in xaml
    assert 'x:Name="CommandPaletteBox"' in xaml
    assert 'KeyDown="OnCommandPaletteKeyDown"' in xaml
    assert 'private void OnWindowKeyDown' in code
    assert 'private void OnCommandPaletteKeyDown' in code
    assert 'KeyModifiers.Control' in code
    assert 'Key.Escape' in code
    assert 'Key.Enter' in code
    for command in ("首页", "捕获", "资料库", "原件阅读", "知识库", "原件编辑", "记忆地图", "学习", "任务", "恢复", "设置"):
        assert command in code
    assert 'x:Name="CommandPaletteResultsList"' in xaml
    assert 'TextChanged="OnCommandPaletteTextChanged"' in xaml
    assert 'private void RefreshCommandPaletteResults' in code
    assert 'CommandPaletteResultsList.SelectedItem as string' in code
    assert 'e.Key is Key.Up or Key.Down' in code
    assert 'CommandPaletteResultsList.SelectedIndex = next;' in code


def test_library_selected_evidence_detail_uses_only_search_projection_fields() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="LibrarySelectedDetailBorder"' in xaml
    assert 'x:Name="LibrarySelectedDetailText"' in xaml
    assert 'LibrarySelectedDetailText.Text = selected.InspectorDetails;' in code
    assert 'LibrarySelectedDetailBorder.IsVisible = true;' in code
    assert 'LibrarySelectedDetailBorder.IsVisible = false;' in code
    assert '来自 Core 搜索投影' in code


def test_library_and_source_lists_support_direct_keyboard_and_pointer_activation() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for name in ("LibraryResultsList", "SourceReaderMembersList"):
        list_block = xaml.split(f'x:Name="{name}"', 1)[1].split('>', 1)[0]
        assert 'KeyDown="OnDetailListKeyDown"' in list_block
        assert 'DoubleTapped="OnDetailListDoubleTapped"' in list_block
    assert 'private void OnDetailListKeyDown' in code
    assert 'private void OnDetailListDoubleTapped' in code
    assert 'private void ExecuteSelectedLibraryResult' in code
    assert 'OnOpenSelectedKnowledgeClick(this, new RoutedEventArgs())' in code
    assert 'OnOpenLibrarySourceClick(this, new RoutedEventArgs())' in code
    assert 'OnReadSourceTransformClick(sender, new RoutedEventArgs())' in code


def test_library_to_source_reader_preserves_a_guarded_return_context() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="BackToLibraryButton"' in xaml
    assert 'Content="返回资料库"' in xaml
    assert 'Click="OnBackToLibraryClick"' in xaml
    assert 'private LibraryResultRow? _selectedLibraryResult;' in code
    assert 'private bool _returnToLibraryAvailable;' in code
    assert 'private void OnBackToLibraryClick' in code
    assert 'LibraryResultsList.SelectedItem = _selectedLibraryResult;' in code
    assert 'private void ProjectSelectedLibraryResult' in code


def test_activity_dock_can_expand_current_session_receipts_without_history_claim() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="ActivityDockDetailsText"' in xaml
    assert 'x:Name="ActivityDockToggleButton"' in xaml
    assert 'Click="OnToggleActivityDockClick"' in xaml
    assert 'private bool _activityDockExpanded;' in code
    assert 'private void OnToggleActivityDockClick' in code
    assert 'ActivityDockDetailsText.Text = string.Join("\\n\\n", lines)' in code
    assert '不代表持久历史' in xaml or '不代表持久历史' in code


def test_activity_dock_escape_collapses_and_restores_focus() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert 'e.Key == Key.Escape && _activityDockExpanded' in code
    assert 'SetActivityDockExpanded(false, restoreFocus: true);' in code
    assert 'private void SetActivityDockExpanded(bool expanded, bool restoreFocus = false)' in code
    assert 'ActivityDockDetailsText.IsVisible = _activityDockExpanded;' in code
    assert 'ActivityDockReceiptList.IsVisible = _activityDockExpanded;' in code
    assert 'ActivityDockToggleButton.Focus();' in code


def test_learning_review_exposes_explicit_core_submission_status() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="LearningReviewStatusText"' in xaml
    assert 'SetStatus(LearningReviewStatusText' in code
    assert '复习提交中' in code
    assert '复习已记录' in code
    assert '复习提交失败' in code
    assert 'Mastery projection 未闭合' in code


def test_learning_review_card_exposes_fsrs_and_core_receipt_boundaries() -> None:
    xaml = XAML.read_text(encoding="utf-8")

    assert 'x:Name="LearningReviewCard"' in xaml
    assert 'Classes="aaos-card-compact review-card"' in xaml
    assert 'x:Name="LearningReviewReceiptPanel"' in xaml
    assert 'Text="复习难度"' in xaml
    assert '不代表知识已被确认，也不代表掌握度指标' in xaml
    assert 'Text="Core FSRS Receipt"' in xaml
    assert '掌握率' not in xaml


def test_aaos_controls_consume_compact_hit_target_token() -> None:
    theme = THEME_XAML.read_text(encoding="utf-8")
    assert '<Style Selector="Button">' in theme
    assert '<Style Selector="TextBox">' in theme
    assert '<Style Selector="ComboBox">' in theme
    assert theme.count('MinHeight" Value="{DynamicResource AaosDensityCompact}"') >= 3


def test_aaos_theme_exposes_semantic_state_and_projection_component_styles() -> None:
    theme = THEME_XAML.read_text(encoding="utf-8")
    for token in ("AaosWarningBrush", "AaosApprovalBrush", "AaosDisabledBrush"):
        assert f'x:Key="{token}"' in theme
    for selector in (
        '<Style Selector="Border.aaos-kpi"',
        '<Style Selector="Border.aaos-status"',
        '<Style Selector="Grid.aaos-toolbar"',
        '<Style Selector="Border.aaos-empty-state"',
        '<Style Selector="TextBlock.aaos-provenance-tag"',
        '<Style Selector="Button.aaos-compact"',
    ):
        assert selector in theme


def test_narrow_layout_reflows_core_search_and_lookup_toolbars() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for name in ("LibrarySearchGrid", "SourceReaderLoadGrid", "KnowledgeLoadGrid", "MachineTaskGrid", "JobLookupGrid"):
        assert f'x:Name="{name}"' in xaml
    assert 'private static void SetResponsiveToolbar' in code
    assert 'SetResponsiveToolbar(LibrarySearchGrid' in code
    assert 'SetResponsiveToolbar(SourceReaderLoadGrid' in code
    assert 'SetResponsiveToolbar(KnowledgeLoadGrid' in code
    assert 'SetResponsiveToolbar(MachineTaskGrid' in code
    assert 'SetResponsiveToolbar(JobLookupGrid' in code


def test_mobile_layout_avoids_fixed_rail_and_tight_toolbar_rows() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="PrimaryRail"' in xaml
    assert 'x:Name="WorkspaceScrollViewer"' in xaml
    for name in ("LibrarySearchGrid", "SourceReaderLoadGrid", "KnowledgeLoadGrid", "MachineTaskGrid", "JobLookupGrid"):
        grid = xaml.split(f'x:Name="{name}"', 1)[1].split('</Grid>', 1)[0]
        assert 'RowSpacing="10"' in grid
    assert 'var mobile = e.NewSize.Width < mobileBreakpoint;' in code
    assert 'MainFrameGrid.ColumnDefinitions[0].Width' in code
    assert 'WorkspaceScrollViewer.Padding' in code


def test_responsive_breakpoints_are_consumed_from_aaos_theme_resources() -> None:
    theme = THEME_XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for token in ("AaosInspectorBreakpoint", "AaosNarrowActionsBreakpoint", "AaosTabletBreakpoint", "AaosMobileBreakpoint"):
        assert f'x:Key="{token}"' in theme
    assert 'private double GetAaosBreakpoint' in code
    assert 'TryFindResource' in code
    assert 'GetAaosBreakpoint("AaosInspectorBreakpoint", 1440)' in code
    assert 'GetAaosBreakpoint("AaosNarrowActionsBreakpoint", 1280)' in code
    assert 'GetAaosBreakpoint("AaosTabletBreakpoint", 1024)' in code
    assert 'GetAaosBreakpoint("AaosMobileBreakpoint", 840)' in code


def test_shell_exposes_core_product_navigation() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    for label in ("工作台", "资料与知识", "学习", "机器知识", "系统", "资料库", "导入阅读", "知识库", "学习路径", "任务收据", "任务", "恢复", "设置"):
        assert f'Content="{label}"' in xaml

    for handler in (
        "OnHomeClick",
        "OnLibraryClick",
        "OnSourceReaderClick",
        "OnKnowledgeClick",
        "OnLearningNavigationClick",
        "OnMachineGrowthClick",
        "OnJobsClick",
        "OnRecoveryClick",
        "OnSettingsClick",
    ):
        assert f'Click="{handler}"' in xaml
        assert f"void {handler}" in code


def test_primary_navigation_and_system_actions_expose_stable_automation_names() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    for name in (
        'x:Name="RailWorkspaceButton"',
        'x:Name="RailCaptureButton"',
        'x:Name="RailKnowledgeButton"',
        'x:Name="RailReaderButton"',
        'x:Name="RailLearningButton"',
        'x:Name="RailEvidenceButton"',
        'x:Name="RailJobsButton"',
        'x:Name="RailSystemButton"',
    ):
        assert name in xaml
    for automation_name in (
        'AutomationProperties.Name="打开工作台"',
        'AutomationProperties.Name="打开捕获"',
        'AutomationProperties.Name="打开资料与知识"',
        'AutomationProperties.Name="打开原件阅读"',
        'AutomationProperties.Name="打开学习"',
        'AutomationProperties.Name="打开证据中心"',
        'AutomationProperties.Name="打开任务"',
        'AutomationProperties.Name="打开系统"',
        'AutomationProperties.Name="读取恢复边界状态"',
        'AutomationProperties.Name="读取当前 Core 状态"',
        'AutomationProperties.Name="刷新本次导入任务回执"',
        'AutomationProperties.Name="读取指定任务回执"',
        'AutomationProperties.Name="打开证据检查器"',
        'AutomationProperties.Name="复制来源链"',
        'AutomationProperties.Name="展开活动回执详情"',
        'AutomationProperties.Name="打开任务回执"',
        'AutomationProperties.Name="刷新活动回执"',
        'AutomationProperties.Name="命令面板输入"',
        'AutomationProperties.Name="命令面板结果"',
    ):
        assert automation_name in xaml
    code = CODE.read_text(encoding="utf-8")
    assert 'AutomationProperties.SetName(InspectorDrawerButton' in code
    assert 'AutomationProperties.SetName(ActivityDockToggleButton' in code
    assert '"关闭证据检查器"' in code
    assert '"收起活动回执详情"' in code


def test_home_exposes_honest_first_run_readiness_surface() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="FirstRunReadinessCard"' in xaml
    assert 'x:Name="FirstRunCoreStatusText"' in xaml
    assert 'x:Name="FirstRunWorkspaceStatusText"' in xaml
    assert 'x:Name="FirstRunOptionalStatusText"' in xaml
    assert 'x:Name="FirstRunImportButton"' in xaml
    assert 'Click="OnImportClick"' in xaml
    assert 'FirstRunCoreStatusText.Text' in code
    assert 'FirstRunWorkspaceStatusText.Text' in code
    assert '未接入权威 readiness 投影' in xaml
    assert '导入成功不等于转换、知识接受或学习完成' in xaml


def test_home_exposes_guarded_current_session_continue_reading() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="HomeContinueReadingCard"' in xaml
    assert 'x:Name="HomeContinueReadingText"' in xaml
    assert 'x:Name="HomeContinueReadingButton"' in xaml
    assert 'Click="OnOpenHomeReadingClick"' in xaml
    assert 'private void OnOpenHomeReadingClick' in code
    assert 'private void RefreshHomeReadingProjection' in code
    assert '仅当前会话，未宣称持久化阅读位置' in code
    assert 'RefreshHomeReadingProjection();' in code


def test_library_renders_structured_core_projection_rows() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="LibraryResultKindText"' in xaml
    assert 'x:Name="LibraryResultHeadText"' in xaml
    assert 'x:Name="LibraryResultStatusText"' in xaml
    assert 'x:Name="LibraryResultSourceText"' in xaml
    assert 'Text="{Binding KindLabel}"' in xaml
    assert 'Text="{Binding Head}"' in xaml
    assert 'Text="{Binding StatusLabel}"' in xaml
    assert 'Text="{Binding SourceLabel}"' in xaml
    assert 'public string KindLabel =>' in code
    assert 'public string StatusLabel =>' in code
    assert 'public string SourceLabel =>' in code


def test_settings_uses_explicit_core_state_semantics() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    theme = (ROOT / "apps/ArcheAxis.Desktop/Themes/AaosTheme.axaml").read_text(encoding="utf-8")
    assert 'x:Name="SettingsStateText"' in xaml
    assert 'Classes="status-empty"' in xaml
    assert 'TextBlock.status-permission' in theme
    assert 'TextBlock.status-version' in theme
    assert 'SetStatus(SettingsStateText, "正在读取 Core 版本与工作区状态。", "loading")' in code
    assert 'SetStatus(SettingsStateText, $"Core 会话凭据无效或已过期（HTTP {(int)response.StatusCode}）。", "permission")' in code
    assert 'SetStatus(SettingsStateText, $"Core 拒绝当前访问来源或权限范围（HTTP {(int)response.StatusCode}）。", "permission")' in code
    assert 'SetStatus(SettingsStateText, $"Core 版本端点读取失败（HTTP {(int)response.StatusCode}）。", "error")' in code
    assert 'hasVersionFields ? "Core 状态已读取。" : "Core 已响应，但版本字段未暴露。"' in code
    assert 'hasVersionFields ? "success" : "empty"' in code
    assert 'SetStatus(SettingsStateText, "Core 状态读取中断。", "error")' in code
    assert 'status-version", "status-unknown"' in code


def test_evidence_detail_uses_kind_specific_core_fields() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for name in (
        "LibraryDetailKindText",
        "LibraryDetailHeadText",
        "LibraryDetailStatusText",
        "LibraryDetailSourceText",
        "LibraryDetailKnowledgeText",
        "LibraryDetailTransformText",
        "LibraryDetailEngineText",
        "LibraryDetailBoundaryText",
    ):
        assert f'x:Name="{name}"' in xaml
    assert 'LibraryDetailKindText.Text = selected.KindLabel;' in code
    assert 'LibraryDetailHeadText.Text = selected.Head;' in code
    assert 'LibraryDetailKnowledgeText.Text = selected.Kind == "knowledge"' in code
    assert 'LibraryDetailTransformText.Text = selected.Kind == "transform"' in code
    assert 'LibraryDetailBoundaryText.Text = "Transform 投影不是 Knowledge 接受状态。";' in code
    assert 'public string StatusLabel => Kind == "transform"' in code
    assert 'InspectorDetails => Kind == "transform"' in code


def test_knowledge_detail_has_guarded_return_to_library_context() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="BackToLibraryFromKnowledgeButton"' in xaml
    assert 'Click="OnBackToLibraryFromKnowledgeClick"' in xaml
    assert 'private void OnBackToLibraryFromKnowledgeClick' in code
    assert '_knowledgeReturnToLibraryAvailable = true;' in code
    assert 'LibrarySearchBox.Text = _librarySearchQuery ?? string.Empty;' in code
    assert 'ProjectSelectedLibraryResult(_selectedLibraryResult);' in code


def test_source_reader_exposes_structured_member_provenance_fields() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for name in (
        "SourceReaderMemberFieldText",
        "SourceReaderOriginalNameFieldText",
        "SourceReaderReadableFieldText",
        "SourceReaderJobFieldText",
        "SourceReaderShaFieldText",
        "SourceReaderMemberBoundaryText",
    ):
        assert f'x:Name="{name}"' in xaml
    assert 'SourceReaderMemberFieldText.Text = selected.Member;' in code
    assert 'SourceReaderReadableFieldText.Text = selected.Readable;' in code
    assert 'SourceReaderJobFieldText.Text = selected.JobId;' in code
    assert 'SourceReaderShaFieldText.Text = selected.Sha256;' in code
    assert '原文正文未暴露；字段来自 Core 来源成员投影。' in code


def test_source_reader_uses_explicit_state_semantics() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert 'SetStatus(SourceReaderStatusText, "来源阅读：正在读取 Core。", "loading")' in code
    assert '"来源阅读：读取失败。"' in code
    assert 'IsPermissionStatus(response.StatusCode) ? "permission" : "error"' in code
    assert 'SetStatus(SourceReaderStatusText, "来源阅读：读取中断。", "error")' in code
    assert 'memberRows.Count == 0 ? "empty" : "success"' in code
    assert 'SetStatus(SourceReaderStatusText, "来源阅读：请输入 source_id。", "empty")' in code
    assert 'SetStatus(SourceReaderStatusText, "来源阅读：Core 未就绪。", "error")' in code


def test_source_reader_and_knowledge_expose_source_context_navigation() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="FindLibraryFromSourceButton"' in xaml
    assert 'Click="OnFindLibraryFromSourceClick"' in xaml
    assert 'x:Name="OpenKnowledgeSourceButton"' in xaml
    assert 'Click="OnOpenKnowledgeSourceClick"' in xaml
    assert 'private void OnFindLibraryFromSourceClick' in code
    assert 'private void OnOpenKnowledgeSourceClick' in code
    assert 'LibrarySearchBox.Text = selected.SourceId.Trim();' in code
    assert 'SourceReaderIdBox.Text = _activeKnowledgeSourceId;' in code
    assert 'selected.SourceId' in code
    assert '知识搜索结果仍需人工选择确认关联' in xaml


def test_learning_review_exposes_explicit_grade_controls() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for name, handler in (
        ("ReviewAgainButton", "OnReviewAgainClick"),
        ("ReviewHardButton", "OnReviewHardClick"),
        ("ReviewGoodButton", "OnReviewGoodClick"),
        ("ReviewEasyButton", "OnReviewEasyClick"),
    ):
        assert f'x:Name="{name}"' in xaml
        assert f'Click="{handler}"' in xaml
        assert f'private void {handler}' in code
    assert 'SetReviewRating(1);' in code
    assert 'SetReviewRating(2);' in code
    assert 'SetReviewRating(3);' in code
    assert 'SetReviewRating(4);' in code
    assert 'ReviewAgainButton.IsEnabled = assessmentReady;' in code
    assert 'ReviewEasyButton.IsEnabled = assessmentReady;' in code
    assert 'rating = _activeReviewRating ?? (correct ? 3 : 1)' in code


def test_knowledge_v3_uses_explicit_state_semantics() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="KnowledgeStateText"' in xaml
    assert 'Classes="status-empty"' in xaml
    assert 'SetStatus(KnowledgeStateText, "正在读取 Knowledge V3。", "loading")' in code
    assert 'SetStatus(KnowledgeStateText, "请输入 knowledge_id 后再读取。", "empty")' in code
    assert 'SetStatus(KnowledgeStateText, "核心未就绪，无法读取知识投影。", "error")' in code
    assert 'Knowledge V3 读取失败（HTTP {(int)response.StatusCode}）。' in code
    assert 'Knowledge V3：Core 拒绝当前访问权限，请检查会话或权限范围。' in code
    assert 'SetStatus(KnowledgeStateText, "Knowledge V3 响应不是有效 JSON。", "error")' in code
    assert 'SetStatus(KnowledgeStateText, hasKnowledgeIdentity ? "Knowledge V3 已读取。" : "Knowledge V3 已响应，但标识字段未暴露。", hasKnowledgeIdentity ? "success" : "empty")' in code


def test_navigation_maps_each_surface_to_one_section() -> None:
    code = CODE.read_text(encoding="utf-8")

    for mapping, handler in (
        ('SetSection("home", "首页")', "OnHomeClick"),
        ('SetSection("library", "资料库")', "OnLibraryClick"),
        ('SetSection("source-reader", "导入阅读")', "OnSourceReaderClick"),
        ('SetSection("knowledge", "知识库")', "OnKnowledgeClick"),
        ('SetSection("learning", "学习")', "OnLearningNavigationClick"),
        ('SetSection("machine-growth", "机器知识")', "OnMachineGrowthClick"),
        ('SetSection("jobs", "任务")', "OnJobsClick"),
        ('SetSection("settings", "设置")', "OnSettingsClick"),
    ):
        assert handler in code
        assert mapping in code


def test_navigation_state_controls_visible_surfaces() -> None:
    code = CODE.read_text(encoding="utf-8")

    assert "WorkspaceHeadingText.Text = heading" in code
    assert 'HomeSurface.IsVisible = section == "home"' in code
    assert 'LearningSurface.IsVisible = section == "learning"' in code
    assert 'HomeStatsSurface.IsVisible = section == "home"' in code
    assert 'LibrarySurface.IsVisible = section == "library"' in code
    assert 'SourceReaderSurface.IsVisible = section == "source-reader"' in code
    assert 'KnowledgeSurface.IsVisible = section == "knowledge"' in code
    assert 'MachineKnowledgeSurface.IsVisible = section == "machine-growth"' in code
    assert 'RecoverySurface.IsVisible = section == "recovery"' in code
    assert 'SettingsSurface.IsVisible = section == "settings"' in code
    assert 'JobsSurface.IsVisible = section == "jobs"' in code
    assert 'UnavailableSurface.IsVisible = section is "research" or "plugins" or "models" or "original-editor" or "memory-map"' in code
    assert 'ContextKnowledgeSubnav.IsVisible = section is "library" or "source-reader" or "knowledge" or "original-editor" or "memory-map"' in code
    assert 'ContextSystemSubnav.IsVisible = section is "jobs" or "recovery" or "settings"' in code


def test_memory_map_and_original_editor_routes_are_truthful_unavailable_surfaces() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'Click="OnOriginalEditorClick"' in xaml
    assert 'Click="OnMemoryMapClick"' in xaml
    assert 'private void OnOriginalEditorClick' in code
    assert 'private void OnMemoryMapClick' in code
    assert '"original-editor" => "当前 Core 只暴露来源成员与转换读取边界' in code
    assert '"memory-map" => "当前 Core 未暴露可验证的 Memory Graph 读模型' in code


def test_primary_space_rail_has_explicit_active_state_mapping() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    theme = THEME_XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    for name in (
        "RailWorkspaceButton",
        "RailKnowledgeButton",
        "RailLearningButton",
        "RailMachineButton",
        "RailSystemButton",
    ):
        assert f'x:Name="{name}"' in xaml
        assert 'Classes="rail-button"' in xaml
    assert 'Style Selector="Button.rail-button.active"' in theme
    assert 'var railSpace = section switch' in code
    for expression in (
        'RailWorkspaceButton.Classes.Set("active", railSpace == "workspace")',
        'RailKnowledgeButton.Classes.Set("active", railSpace == "knowledge")',
        'RailLearningButton.Classes.Set("active", railSpace == "learning")',
        'RailMachineButton.Classes.Set("active", railSpace == "machine")',
        'RailSystemButton.Classes.Set("active", railSpace == "system")',
    ):
        assert expression in code
    assert 'section is "library" or "source-reader" or "knowledge"' in code
    assert 'section is "jobs" or "recovery" or "settings"' in code


def test_activity_receipt_dock_is_current_session_only() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="ActivityDockText"' in xaml
    assert 'Content="刷新回执"' in xaml
    assert 'Click="OnRefreshJobsClick"' in xaml
    assert 'List<string> _sessionJobIds' in code
    assert 'if (_sessionJobIds.Count == 0)' in code
    assert 'ActivityDockText.Text' in code
    assert 'ActivityDockText.Text = $"本次会话 {lines.Count} 个任务' in code
    assert '_sessionJobIds.Add(jobId)' in code
    assert '"/api/v1/jobs/' in code
    assert '/quality' in code
    assert '不代表持久历史' in code


def test_unwired_domains_are_explicitly_empty_not_synthetic() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    surface = xaml + code

    assert "Core 当前没有全量任务列表投影" in surface
    assert "不展示已安装、启用、默认/回退或健康状态" in surface
    assert "不执行、预演或模拟恢复" in surface


def test_knowledge_and_machine_surfaces_read_real_core_projections() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="KnowledgeSurface"' in xaml
    assert 'Click="OnReadKnowledgeClick"' in xaml
    assert 'x:Name="KnowledgeResultsText"' in xaml
    assert '"/api/v1/knowledge-items/' in code
    assert '}/v3");' in code
    assert 'x:Name="MachineKnowledgeSurface"' in xaml
    assert 'Click="OnReadMachineTaskClick"' in xaml
    assert 'x:Name="MachineTaskResultsText"' in xaml
    assert '"/api/v1/machine/tasks/' in code
    assert 'ReadDisplayValue(root, "model_version")' in code


def test_recovery_surface_reads_core_status_without_simulating_restore() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="RecoverySurface"' in xaml
    assert 'Click="OnReadRecoveryStatusClick"' in xaml
    assert 'x:Name="RecoveryResultsText"' in xaml
    assert '"/api/v1/system/version"' in code
    assert '"/api/v1/workspaces/info"' in code
    assert "恢复点：当前 Core 未暴露" in code
    assert "未执行任何恢复动作" in code
    assert 'x:Name="RecoveryResultsText" Classes="status-empty"' in xaml
    assert 'permission · Core 拒绝读取恢复边界状态' in code
    assert '工作区来源：{FormatOptionalCount(sources)} · 锚点：{FormatOptionalCount(anchors)}' in code
    assert 'Recovery 响应不是有效 JSON' in code


def test_source_reader_surface_reads_real_core_members_projection() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="SourceReaderSurface"' in xaml
    assert 'Click="OnReadSourceMembersClick"' in xaml
    assert 'x:Name="SourceReaderResultsText"' in xaml
    assert 'x:Name="SourceReaderShellGrid"' in xaml
    assert 'Text="Source Tree / Outline"' in xaml
    assert 'Text="Main Reader · Core transform"' in xaml
    assert 'Text="Inspector · Source Chain"' in xaml
    assert '"/api/v1/sources/' in code
    assert '}/members");' in code
    assert 'ReadDisplayValue(root, "member_count")' in code


def test_library_surface_uses_the_existing_core_search_projection() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="LibrarySearchBox"' in xaml
    assert 'Click="OnSearchLibraryClick"' in xaml
    assert 'x:Name="LibraryResultsText"' in xaml
    assert "void OnSearchLibraryClick" in code
    assert '"/api/v1/search?q=' in code
    assert 'TryGetProperty("items"' in code
    assert 'TryGetProperty("transforms"' in code
    assert 'x:Name="LibraryWorkspaceGrid"' in xaml
    assert 'ColumnDefinitions="1.1*,0.9*"' in xaml
    assert 'Text="Header / Provenance / Boundary"' in xaml
    assert 'LibraryWorkspaceGrid.ColumnDefinitions = compact' in code
    assert 'Grid.SetRow(LibrarySelectedDetailBorder, compact ? 1 : 0);' in code


def test_settings_surface_reads_core_version_without_creating_local_truth() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="SettingsSurface"' in xaml
    assert 'x:Name="SettingsCoreStatusText"' in xaml
    assert '"/api/v1/system/version"' in code
    assert 'TryGetProperty("runtime"' in code
    assert 'TryGetProperty("schema_version"' in code


def test_settings_surface_exposes_explicit_core_refresh_and_workspace_readback() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="SettingsRefreshButton"' in xaml
    assert 'Click="OnSettingsRefreshClick"' in xaml
    assert 'x:Name="SettingsWorkspaceStatusText"' in xaml
    assert 'x:Name="SettingsCapabilityBoundaryText"' in xaml
    assert 'private void OnSettingsRefreshClick' in code
    assert '"/api/v1/workspaces/info"' in code
    assert 'SettingsWorkspaceStatusText.Text' in code
    assert '插件、模型、Sidecar 未接入权威 readiness 投影' in code
    assert 'var sources = ReadOptionalInt(workspace.RootElement, "sources");' in code
    assert 'FormatOptionalCount(sources)' in code


def test_learning_surface_has_a_direct_core_load_action() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    learning = xaml.split('x:Name="LearningSurface"', 1)[1].split('</StackPanel>', 1)[0]

    assert 'Click="OnLearningClick"' in learning


def test_learning_surface_exposes_traceable_source_chain() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for name in ("LearningEvidenceText", "LearningOriginalText", "LearningVersionText", "LearningMemoryText"):
        assert f'x:Name="{name}"' in xaml
    assert 'x:Name="OpenLearningKnowledgeButton"' in xaml
    assert 'Click="OnOpenLearningKnowledgeClick"' in xaml
    assert 'LearningEvidenceText.Text = referenceText;' in code
    assert 'LearningMemoryText.Text = readbackText;' in code
    assert 'KnowledgeIdBox.Text = _activeKnowledgeId;' in code


def test_learning_trace_does_not_promote_review_to_knowledge_acceptance() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert "不会自动表示知识已接受" in xaml
    assert "knowledge_version" in code
    assert "assessment_id" in code
    assert 'SetSection("knowledge", "知识详情")' in code


def test_learning_surface_has_explicit_loading_empty_and_failure_feedback() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="LoadLearningButton"' in xaml
    assert 'x:Name="LearningStatusText"' in xaml
    assert 'LoadLearningButton.IsEnabled = false;' in code
    assert 'LoadLearningButton.IsEnabled = true;' in code
    assert "学习路径：正在读取 Core" in code
    assert "学习路径：当前没有待复习项目" in code
    assert "学习路径：队列读取失败" in code


def test_workspace_learning_summary_does_not_turn_core_failure_into_zero() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert "learningAvailable" in code
    assert 'LearningCountText.Text = learningAvailable ? FormatOptionalCount(learning) : "—";' in code
    assert 'count 字段未暴露' in code
    assert 'HomeFocusText.Text = "Core 学习队列暂不可用。";' in code


def test_learning_partial_projections_remain_explicitly_unverified() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert "来源状态读取失败" in code
    assert "Assessment 未就绪" in code
    assert "学习记录读取失败" in code


def test_library_search_has_explicit_loading_empty_and_failure_feedback() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="LibrarySearchButton"' in xaml
    assert 'x:Name="LibrarySearchStatusText"' in xaml
    assert 'LibrarySearchButton.IsEnabled = false;' in code
    assert 'LibrarySearchButton.IsEnabled = true;' in code
    assert "资料库搜索：正在读取 Core" in code
    assert "资料库搜索：没有匹配结果" in code
    assert "资料库搜索：读取失败" in code


def test_jobs_surface_reads_only_current_session_job_receipts() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="JobsSurface"' in xaml
    assert 'Click="OnRefreshJobsClick"' in xaml
    assert 'x:Name="JobsResultsText"' in xaml
    assert "List<string> _sessionJobIds" in code
    assert "_sessionJobIds.Add(jobId)" in code
    assert '"/api/v1/jobs/' in code
    assert '/quality"' in code
    assert "本次会话" in code
    assert "jobs 全量历史" not in code


def test_navigation_is_ui_state_and_does_not_create_a_second_truth_store() -> None:
    code = CODE.read_text(encoding="utf-8")

    assert "_activeSection" in code
    assert "new SQLiteConnection" not in code


def test_aaos_theme_tokens_replace_the_legacy_indigo_shell_palette() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    theme = THEME_XAML.read_text(encoding="utf-8")

    for key in (
        "AaosBackgroundBrush",
        "AaosSidebarBrush",
        "AaosSurfaceBrush",
        "AaosSurface2Brush",
        "AaosBorderBrush",
        "AaosPrimaryBrush",
        "AaosGoldBrush",
        "AaosIvoryBrush",
        "AaosMutedBrush",
    ):
        assert f'x:Key="{key}"' in theme

    for color in ("#061118", "#091821", "#0C1C26", "#102630", "#1D5055", "#1FC8C5", "#E6BE73", "#F3EFE6", "#96AAB4"):
        assert color in theme

    assert 'Background="{DynamicResource AaosBackgroundBrush}"' in xaml
    assert 'BorderBrush="{DynamicResource AaosBorderBrush}"' in xaml
    for legacy in ("#6366F1", "#050505", "#111113", "#2B2E63"):
        assert legacy not in xaml


def test_home_surface_expresses_focus_and_evidence_without_demo_metrics() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    home = xaml.split('x:Name="HomeSurface"', 1)[1].split('x:Name="LibrarySurface"', 1)[0]

    assert 'Text="今日关注"' in home
    assert 'Text="当前会话回执"' in home
    assert 'x:Name="HomeFocusText"' in home
    assert 'x:Name="HomeEvidenceText"' in home
    assert "Core" in home
    for demo_metric in ('Text="248"', 'Text="12"', 'Text="72%"', 'Text="91%"'):
        assert demo_metric not in home


def test_home_receipt_uses_source_navigation_without_claiming_evidence() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="HomeOpenCurrentSourceButton"' in xaml
    assert 'Content="打开当前来源"' in xaml
    assert 'Click="OnOpenLatestSourceClick"' in xaml
    assert 'HomeOpenCurrentSourceButton.IsEnabled' in code


def test_home_evidence_projects_current_capture_receipt_with_boundary() -> None:
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="HomeEvidenceText"' in XAML.read_text(encoding="utf-8")
    assert "HomeEvidenceText.Text" in code
    assert "本次会话 Core 回执" in code
    assert "不代表 Knowledge 接受或 evidence anchor" in code


def test_home_focus_is_projected_from_the_real_learning_queue() -> None:
    code = CODE.read_text(encoding="utf-8")

    assert '"/api/v1/learning/items"' in code
    assert 'HomeFocusText.Text = learning is null' in code
    assert 'learning > 0' in code
    assert '$"Core 当前有 {learning} 个待学习项目；可从学习路径继续。"' in code


def test_home_lifecycle_strip_preserves_core_truth_boundaries() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="HomeLifecycleGrid"' in xaml
    for name in ("HomeLifecycleCaptureText", "HomeLifecycleSourceText", "HomeLifecycleKnowledgeText", "HomeLifecycleLearningText", "HomeLifecycleReviewText"):
        assert f'x:Name="{name}"' in xaml
    assert 'HomeLifecycleKnowledgeText.Text = "unavailable' in code
    assert 'HomeLifecycleReviewText.Text = "unavailable' in code
    assert 'HomeLifecycleGrid.ColumnDefinitions = compact' in code
    assert 'SetResponsiveToolbar(FirstRunReadinessGrid' in code
    assert 'SetResponsiveToolbar(HomeContinueReadingGrid' in code
    assert '"Core 当前没有待学习项目。"' in code
    assert 'HomeFocusText.Text = "Core 学习队列暂不可用。"' in code
    assert 'x:Name="HomeFocusLearningButton"' in xaml
    assert 'HomeFocusLearningButton.IsEnabled = learningAvailable;' in code
    assert 'HomeFocusLearningButton.IsEnabled = false;' in code


def test_home_stats_are_scoped_to_the_home_domain() -> None:
    code = CODE.read_text(encoding="utf-8")

    assert 'HomeStatsSurface.IsVisible = section == "home";' in code


def test_home_primary_actions_use_compact_resume_rows() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    home = xaml.split('x:Name="HomeSurface"', 1)[1].split('x:Name="LibrarySurface"', 1)[0]

    assert 'Text="继续工作"' in home
    assert 'Text="导入资料"' in home
    assert 'Text="资料与知识"' in home
    assert 'ColumnDefinitions="*,*,*,*"' not in home


def test_source_reader_is_a_first_level_product_space() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="RailReaderButton"' in xaml
    assert 'Content="原件阅读"' in xaml
    assert 'Click="OnSourceReaderClick"' in xaml
    assert '"source-reader" => "reader"' in code
    assert 'RailReaderButton.Classes.Set("active", railSpace == "reader");' in code


def test_capture_inbox_is_a_first_level_product_space() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="RailCaptureButton"' in xaml
    assert 'Content="捕获"' in xaml
    assert 'Click="OnCaptureClick"' in xaml
    assert 'x:Name="CaptureSurface"' in xaml
    assert 'x:Name="CaptureSelectionText"' in xaml
    assert 'x:Name="CaptureReceiptText"' in xaml
    assert 'CaptureSurface.IsVisible = section == "capture"' in code
    assert 'SetSection("capture", "捕获")' in code


def test_capture_inbox_reuses_import_and_receipt_boundary() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'Click="OnImportClick"' in xaml
    assert 'await RefreshJobsAsync();' in code
    assert 'ActivityDockText.Text' in code
    assert 'CaptureReceiptText.Text' in code
    assert '未创建虚构的 Core 状态' in xaml
    assert '"/api/v1/sources/{Uri.EscapeDataString(sourceId)}/members"' in code


def test_library_search_projects_core_results_as_selectable_items() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="LibraryResultsList"' in xaml
    assert 'SelectionChanged="OnLibraryResultSelected"' in xaml
    assert 'LibraryResultsList.ItemsSource = visibleRows;' in code
    assert 'private void OnLibraryResultSelected' in code
    assert '来自 Core 搜索投影。' in code


def test_library_results_preserve_core_provenance_fields() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert "public sealed class LibraryResultRow" in code
    for field in ("Kind", "KnowledgeId", "SourceId", "TransformId", "Status", "Active", "Engine"):
        assert f"public string {field}" in code
    for field in ("status", "active", "transform_id", "engine"):
        assert f'ReadDisplayValue(' in code and f'"{field}"' in code
    assert 'is not LibraryResultRow selected' in code
    assert 'selected.Kind != "knowledge"' in code
    assert "提取文本命中" in code


def test_library_result_can_open_source_reader_for_exposed_source_id() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="OpenLibrarySourceButton"' in xaml
    assert 'Click="OnOpenLibrarySourceClick"' in xaml
    assert 'private void OnOpenLibrarySourceClick' in code
    assert 'SourceReaderIdBox.Text = selected.SourceId.Trim();' in code
    assert 'SetSection("source-reader", "导入阅读")' in code
    assert 'OnReadSourceMembersClick(sender, e);' in code
    assert "未暴露 source_id" in code


def test_library_results_have_an_aaos_provenance_row_template() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    listbox = xaml.split('x:Name="LibraryResultsList"', 1)[1].split('</ListBox>', 1)[0]

    assert '<ListBox.ItemTemplate>' in listbox
    assert 'Background="{DynamicResource AaosSurfaceBrush}"' in listbox
    assert 'BorderBrush="{DynamicResource AaosBorderBrush}"' in listbox
    assert 'Text="{Binding Head}"' in listbox


def test_inspector_exposes_a_structured_source_chain_boundary() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'Text="来源链摘要"' in xaml
    assert 'x:Name="InspectorProvenanceText"' in xaml
    assert 'InspectorProvenanceText.Text = "未选择对象；来源链未加载。";' in code
    assert 'InspectorProvenanceText.Text = "来自受控 Core projection；字段缺失不推断。";' in code


def test_knowledge_search_hit_can_open_the_existing_v3_projection() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'Content="读取 Knowledge 详情"' in xaml
    assert 'Click="OnOpenSelectedKnowledgeClick"' in xaml
    assert 'private void OnOpenSelectedKnowledgeClick' in code
    assert 'SetSection("knowledge", "知识详情")' in code
    assert '"/api/v1/knowledge-items/{Uri.EscapeDataString(knowledgeId)}/v3"' in code


def test_knowledge_v3_detail_projects_structured_truth_fields() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    for name in ("KnowledgeStatusText", "KnowledgeSourceText", "KnowledgeTrustText", "KnowledgeReviewText"):
        assert f'x:Name="{name}"' in xaml
    assert 'KnowledgeStatusText.Text = ReadDisplayValue(root, "status");' in code
    assert 'KnowledgeSourceText.Text = ReadDisplayValue(root, "source_id");' in code
    assert 'KnowledgeTrustText.Text = $"支持：{ReadDisplayValue(root, "support_level")} · 置信：{ReadDisplayValue(root, "confidence")} · 风险：{ReadDisplayValue(root, "risk_level")}";' in code
    assert 'KnowledgeReviewText.Text = ReadDisplayValue(root, "requires_human_review");' in code


def test_source_reader_projects_members_as_selectable_provenance_rows() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="SourceReaderMembersList"' in xaml
    assert 'SelectionChanged="OnSourceMemberSelected"' in xaml
    assert 'SourceReaderMembersList.ItemsSource = memberRows;' in code
    assert 'private void OnSourceMemberSelected' in code
    assert 'job=' in code


def test_source_reader_rows_declare_projection_and_original_content_boundary() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    reader = xaml.split('x:Name="SourceReaderMembersList"', 1)[1].split('</ListBox>', 1)[0]

    assert 'Text="来源成员 · Core projection"' in reader
    assert 'Text="原文正文未在此列表中展示"' in reader


def test_source_reader_preserves_structured_member_provenance_fields() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'Text="{Binding}"' in xaml
    assert 'public sealed class SourceMemberRow' in code
    for field in ("SourceId", "Member", "OriginalName", "Sha256", "Readable", "JobId"):
        assert f"public string {field}" in code
    assert 'SourceReaderMembersList.ItemsSource = memberRows;' in code


def test_source_reader_has_explicit_loading_empty_and_failure_feedback() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="SourceReaderLoadButton"' in xaml
    assert 'x:Name="SourceReaderStatusText"' in xaml
    assert 'SourceReaderLoadButton.IsEnabled = false;' in code
    assert 'SourceReaderLoadButton.IsEnabled = true;' in code
    assert "来源阅读：正在读取 Core" in code
    assert "来源阅读：Core 返回空成员" in code


def test_source_reader_guards_against_stale_async_responses() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'private long _sourceReaderRequestVersion;' in code
    assert 'var requestVersion = ++_sourceReaderRequestVersion;' in code
    assert 'requestVersion != _sourceReaderRequestVersion' in code
    assert '来源阅读：输入已变化，请重新读取。' in code
    assert 'SourceReaderIdBox.IsEnabled = false;' in code
    assert 'SourceReaderIdBox.IsEnabled = true;' in code
    assert 'IsEnabled="True"' not in xaml


def test_source_member_can_open_a_real_job_receipt_without_claiming_success() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="ViewSourceJobButton"' in xaml
    assert 'Click="OnViewSourceJobClick"' in xaml
    assert 'x:Name="JobLookupIdBox"' in xaml
    assert 'x:Name="JobLookupResultsText"' in xaml
    assert 'Click="OnReadJobReceiptClick"' in xaml
    assert 'private void OnViewSourceJobClick' in code
    assert 'private async void OnReadJobReceiptClick' in code
    assert '"/api/v1/jobs/{Uri.EscapeDataString(jobId)}"' in code
    assert "不代表任务成功" in code


def test_source_reader_has_a_structured_selected_member_detail_card() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="SourceReaderSelectedText"' in xaml
    for field in ("source_id", "member", "original_name", "readable", "job_id", "sha256"):
        assert field in code
    assert 'SourceReaderSelectedText.Text =' in code
    assert "原文正文未在此详情卡片展示" in xaml


def test_inspector_has_structured_provenance_fields_without_inference() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for field in ("InspectorSourceText", "InspectorVersionText", "InspectorStatusText", "InspectorBoundaryText"):
        assert f'x:Name="{field}"' in xaml
        assert f'{field}.Text' in code
    assert 'private void SetInspectorProjection(' in code
    assert '未暴露' in code
    assert 'producer' not in code.lower()
    assert 'evidence_id' not in code.lower()


def test_inspector_provenance_drawer_has_layer_tags_and_source_chain() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for field in ("InspectorLayerText", "InspectorChainSourceText", "InspectorChainVersionText", "InspectorChainProjectionText"):
        assert f'x:Name="{field}"' in xaml
        assert f'{field}.Text' in code
    assert "Core projection" in xaml
    assert "字段缺失不推断" in xaml


def test_inspector_actions_reuse_existing_navigation_contract() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for token in (
        'x:Name="InspectorOpenSourceButton"',
        'x:Name="InspectorOpenKnowledgeButton"',
        'x:Name="InspectorBackLibraryButton"',
    ):
        assert token in xaml
    assert 'Click="OnInspectorOpenSourceClick"' in xaml
    assert 'Click="OnInspectorOpenKnowledgeClick"' in xaml
    assert 'Click="OnInspectorBackLibraryClick"' in xaml
    assert 'private void UpdateInspectorActions()' in code
    assert 'OnOpenKnowledgeSourceClick(sender, e);' in code
    assert 'OnOpenLibrarySourceClick(sender, e);' in code
    assert 'OnOpenSelectedKnowledgeClick(sender, e);' in code
    assert 'OnBackToLibraryFromKnowledgeClick(sender, e);' in code
    assert 'OnBackToLibraryClick(sender, e);' in code
    assert 'if (_knowledgeReturnToLibraryAvailable)' in code
    assert 'SourceReaderSurface.IsVisible' in code


def test_knowledge_source_reader_preserves_return_context() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="BackToKnowledgeFromSourceButton"' in xaml
    assert 'Click="OnBackToKnowledgeFromSourceClick"' in xaml
    assert 'private string? _sourceReaderReturnKnowledgeId;' in code
    assert 'private bool _sourceReaderReturnToKnowledgeAvailable;' in code
    assert '_sourceReaderReturnKnowledgeId = KnowledgeIdBox.Text?.Trim();' in code
    assert 'private void OnBackToKnowledgeFromSourceClick' in code
    assert 'OnReadKnowledgeClick(sender, e);' in code


def test_direct_navigation_clears_stale_library_context() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert 'private void OnLibraryClick' in code
    assert '_selectedLibraryResult = null;' in code
    assert '_librarySearchQuery = null;' in code
    assert '_knowledgeReturnToLibraryAvailable = false;' in code
    assert 'private void OnSourceReaderClick' in code
    assert 'private void OnKnowledgeClick' in code


def test_command_palette_exposes_reader_and_knowledge_fallback_routes() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert '原件阅读 / 知识库' in xaml
    assert 'new("原件阅读", "source-reader", "导入阅读", "导入阅读")' in code
    assert 'new("知识库", "knowledge", "知识库", "知识详情")' in code


def test_knowledge_has_main_workspace_evidence_context_fallback() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for field in (
        "KnowledgeContextSourceText",
        "KnowledgeContextVersionText",
        "KnowledgeContextProjectionText",
        "KnowledgeContextBoundaryText",
    ):
        assert f'x:Name="{field}"' in xaml
        assert f'{field}.Text =' in code
    assert "Knowledge 状态不等于学习掌握" in xaml


def test_source_reader_has_main_workspace_provenance_chain_fallback() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for field in (
        "SourceReaderChainSourceText",
        "SourceReaderChainMemberText",
        "SourceReaderChainJobText",
        "SourceReaderChainShaText",
        "SourceReaderChainBoundaryText",
    ):
        assert f'x:Name="{field}"' in xaml
        assert f'{field}.Text =' in code
    assert "sha256 不是正文或 anchor" in code


def test_home_deduplicates_core_learning_entry_and_labels_optional_workbench() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    home = xaml.split('x:Name="HomeSurface"', 1)[1].split('x:Name="LibrarySurface"', 1)[0]
    assert 'Text="可选 DeepTutor 工作台"' in home
    assert 'Core 待复习队列请从“今日关注 / Core 学习路径”进入' in home
    assert 'Content="打开 DeepTutor 工作台"' in home
    assert 'Content="打开 Core 学习路径"' in home


def test_knowledge_detail_has_object_header_and_body_projection_layers() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for field in ("KnowledgeObjectTitleText", "KnowledgeObjectMetaText", "KnowledgeBodyText"):
        assert f'x:Name="{field}"' in xaml
        assert f'{field}.Text =' in code
    assert 'Knowledge V3 投影，不自动等于已接受 Evidence' in xaml
    assert 'ReadDisplayValue(root, "owner")' in code
    assert 'ReadDisplayValue(root, "body")' in code


def test_learning_inspector_does_not_put_assessment_id_in_status_field() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert 'status: null,' in code
    assert 'assessment_id 不是对象状态' in code


def test_inspector_layer_labels_preserve_projection_boundaries() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert 'string layer = "Core projection · 类型未暴露"' in code
    for label in (
        "Core projection · Source member",
        "Core projection · Knowledge V3",
        "Core projection · Transform search",
        "Core projection · Learning/Assessment",
    ):
        assert label in code


def test_library_filters_use_only_real_active_only_and_returned_kind() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="LibraryActiveOnlyBox"' in xaml
    assert 'x:Name="LibraryKindFilterBox"' in xaml
    assert 'active_only={(LibraryActiveOnlyBox.IsChecked == true).ToString().ToLowerInvariant()}' in code
    assert '1 => "knowledge"' in code
    assert '2 => "transform"' in code
    assert 'rows.Where(row => row.Kind == kindFilter).ToList()' in code


def test_learning_inspector_does_not_promote_knowledge_id_to_source_id() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert 'source: null,' in code
    assert 'Learning learner.references' not in code


def test_library_transform_display_does_not_claim_knowledge_state() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert 'public string DisplayText => Kind == "transform"' in code
    assert 'transform_id={TransformId}' in code
    assert '· status={Status} · active={Active}";' in code


def test_learning_loading_guards_stale_requests_and_clears_previous_answer() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert 'private long _learningRequestVersion;' in code
    assert 'var requestVersion = ++_learningRequestVersion;' in code
    assert 'LearningAnswerBox.Text = string.Empty;' in code
    assert 'ReviewOutcomeBox.Text = string.Empty;' in code
    assert 'requestVersion != _learningRequestVersion' in code
    assert 'private void FinishLearningRequest(long requestVersion)' in code


def test_learning_unavailable_state_clears_stale_projection_and_exposes_permission() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert 'private void ResetLearningProjectionForUnavailable(string reason, string action)' in code
    assert '_activeAssessmentId = null;' in code
    assert '不保留上一条学习来源' in code
    assert 'permissionDenied ? "permission" : "error"' in code
    assert '学习路径：Core 拒绝当前访问权限，请检查会话或权限范围。' in code
    assert '请重新加载复习项目，或到设置页检查 Core 状态。' in code


def test_learning_review_permission_failure_is_not_reported_as_generic_error() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert '复习提交被 Core 拒绝：请检查会话或权限范围。' in code
    assert 'permissionDenied ? "permission" : "error"' in code


def test_library_and_source_reader_expose_explicit_core_permission_state() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert 'private static bool IsPermissionStatus(System.Net.HttpStatusCode statusCode)' in code
    assert '资料库搜索：Core 拒绝当前访问权限。' in code
    assert '来源阅读：Core 拒绝当前访问权限，请检查会话或权限范围。' in code
    assert 'Core 拒绝读取转换输出；原文正文仍未暴露。' in code


def test_home_source_lifecycle_does_not_promote_unknown_or_failed_jobs() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert 'context.JobState is "succeeded" or "completed"' in code
    assert 'error · {context.JobState}；请从来源阅读重试' in code
    assert 'unknown · {context.JobState}；未推断为可用' in code


def test_knowledge_v3_distinguishes_permission_not_found_and_server_failure() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert 'Knowledge V3：Core 拒绝当前访问权限，请检查会话或权限范围。' in code
    assert 'Knowledge V3：Core 未找到该知识对象。' in code
    assert 'permissionDenied ? "permission" : notFound ? "empty" : "error"' in code


def test_narrow_layout_keeps_inspector_available_as_an_evidence_drawer() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="InspectorDrawerButton"' in xaml
    assert 'Click="OnToggleInspectorDrawerClick"' in xaml
    assert 'private void OnToggleInspectorDrawerClick' in code
    assert 'InspectorDrawerButton.IsVisible = hideInspector;' in code


def test_inspector_drawer_escape_closes_and_restores_button_focus() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert 'e.Key == Key.Escape && _inspectorDrawerOpen && InspectorPanel.IsVisible' in code
    assert 'OnToggleInspectorDrawerClick(this, new RoutedEventArgs());' in code
    assert 'InspectorDrawerButton.Focus();' in code
    assert 'InspectorPanel.IsVisible = _inspectorDrawerOpen;' in code
    assert 'Grid.SetColumn(InspectorPanel, mobile ? 0 : 2);' in code
    assert 'InspectorPanel.ZIndex = 5;' in code


def test_inspector_drawer_enters_focus_and_reflows_scrollable_actions() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="InspectorPanel"' in xaml
    assert 'Focusable="True"' in xaml
    assert 'AutomationProperties.Name="来源与证据检查器"' in xaml
    assert 'VerticalScrollBarVisibility="Auto"' in xaml
    assert 'InspectorPanel.Focus();' in code
    assert 'InspectorActionPanel.Orientation = narrowActions' in code


def test_overlay_surfaces_have_reduced_motion_safe_reveal_feedback() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    theme = THEME_XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for name in ("InspectorPanel", "ActivityDock", "ToastSurface", "CommandPaletteOverlay"):
        surface = xaml.split(f'x:Name="{name}"', 1)[1].split('>', 1)[0]
        assert 'Classes="aaos-animated-surface' in surface
    assert '<Style Selector="Border.aaos-animated-surface">' in theme
    assert '<Style Selector="Grid.reduced-motion Border.aaos-animated-surface">' in theme
    assert 'private void RevealSurface(Control target)' in code
    assert 'Dispatcher.UIThread.Post' in code
    assert 'if (_reducedMotion)' in code


def test_exact_tablet_and_narrow_action_breakpoints_collapse_at_boundary() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert 'var compact = e.NewSize.Width <= tabletBreakpoint;' in code
    assert 'var narrowActions = e.NewSize.Width <= narrowActionsBreakpoint;' in code


def test_library_search_ignores_stale_responses_from_older_queries() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert 'private long _librarySearchRequestVersion;' in code
    assert 'var requestVersion = ++_librarySearchRequestVersion;' in code
    assert code.count('requestVersion != _librarySearchRequestVersion') >= 3
    assert 'var responseBody = await response.Content.ReadAsStringAsync();' in code


def test_inspector_overlay_and_source_reader_use_safe_narrow_layout_breakpoints() -> None:
    theme = THEME_XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Key="AaosSourceReaderStackBreakpoint"' in theme
    assert 'GetAaosBreakpoint("AaosSourceReaderStackBreakpoint", 1200)' in code
    assert 'var sourceReaderCompact = compact || e.NewSize.Width < sourceReaderStackBreakpoint;' in code
    assert 'Grid.SetColumnSpan(InspectorPanel, mobile ? 4 : 1);' in code


def test_capture_preserves_real_source_job_context_and_exposes_guarded_actions() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="CaptureContextText"' in xaml
    assert 'x:Name="OpenLatestSourceButton"' in xaml
    assert 'x:Name="OpenLatestJobButton"' in xaml
    assert 'private CaptureContextRow? _latestCaptureContext;' in code
    for field in ("FileName", "SourceId", "JobId", "JobState"):
        assert f'public string {field}' in code
    assert 'private void RefreshCaptureContextProjection()' in code
    assert 'SetSection("source-reader", "导入阅读")' in code
    assert 'SetSection("jobs", "任务")' in code
    assert 'JobId = "未提交";' in code


def test_capture_retains_each_multi_file_context_and_allows_selection() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="CaptureContextsList"' in xaml
    assert 'SelectionChanged="OnCaptureContextSelected"' in xaml
    assert 'private readonly List<CaptureContextRow> _captureContexts = new();' in code
    assert 'private CaptureContextRow? _selectedCaptureContext;' in code
    assert '_captureContexts.Add(captureContext);' in code
    assert 'CaptureContextsList.SelectedItem = captureContext;' in code
    assert 'private void OnCaptureContextSelected' in code
    assert 'source_id ↔ job_id ↔ file_name' in code


def test_learning_shows_capture_context_as_unassociated_session_context() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="LearningCaptureContextText"' in xaml
    assert 'x:Name="OpenLearningCaptureSourceButton"' in xaml
    assert 'x:Name="OpenLearningCaptureJobButton"' in xaml
    assert 'LearningCaptureContextText.Text' in code
    assert "未证明与当前学习项目关联" in code
    assert 'learner.references' in code


def test_source_reader_clears_stale_selection_on_invalid_or_empty_read() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert "ResetSourceReaderSelection" in code
    assert "JobLookupIdBox.Text = string.Empty;" in code
    assert "ViewSourceJobButton.IsEnabled = false;" in code
    assert "来源链未加载；字段缺失不推断。" in code
    assert "Core 返回 0 个来源成员" in code


def test_source_reader_surfaces_core_response_consistency_warnings() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert "container_source_id" in code
    assert "来源容器标识与请求不一致" in code
    assert "member_count" in code
    assert "成员计数与 Core 返回数组不一致" in code


def test_source_reader_preserves_core_note_and_http_diagnostic_context() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="SourceReaderCoreNoteText"' in xaml
    assert 'ReadDisplayValue(root, "note")' in code
    assert "Core 说明：" in code
    assert "source not found" in code
    assert "responseBody" in code


def test_job_quality_zeroes_are_not_presented_as_verified_without_coverage() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert 'TryGetProperty("coverage", out var coverage)' in code
    assert "质量回执：未生成" in code
    assert "覆盖：" in code
    assert "loss_count" in code
    assert "region_count" in code
    assert 'source_id={selected.SourceId}' in code
    assert 'sha256={selected.Sha256}' in code
    assert 'public override string ToString() => DisplayText;' in code


def test_source_member_selection_uses_added_items_only() -> None:
    code = CODE.read_text(encoding="utf-8")

    assert 'e.AddedItems.Count != 1' in code
    assert 'e.AddedItems[0] is not SourceMemberRow selected' in code


def test_activity_dock_can_open_the_current_session_receipt_surface() -> None:
    xaml = XAML.read_text(encoding="utf-8")

    assert 'Content="打开任务回执"' in xaml
    assert 'Click="OnJobsClick"' in xaml


def test_jobs_surface_projects_session_receipts_as_selectable_rows() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="JobsResultsList"' in xaml
    assert 'SelectionChanged="OnJobReceiptSelected"' in xaml
    assert 'JobsResultsList.ItemsSource = receipts;' in code
    assert 'public sealed class JobReceiptRow' in code
    assert 'e.AddedItems[0] is not JobReceiptRow selected' in code
    assert 'private void OnJobReceiptSelected' in code


def test_activity_dock_projects_selectable_receipts_and_explicit_status() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="ActivityDockStatusText"' in xaml
    assert 'x:Name="ActivityDockReceiptList"' in xaml
    assert 'SelectionChanged="OnActivityDockReceiptSelected"' in xaml
    assert 'ActivityDockReceiptList.ItemsSource = receipts;' in code
    assert 'permission · Core 拒绝部分任务回执' in code
    assert 'success · 当前会话 Core 回执已读取。' in code
    assert 'loading · 正在读取本次会话 Core 回执。' in code
    assert 'unknown · Core 返回了未识别任务状态；未推断为成功。' in code


def test_single_job_receipt_has_explicit_loading_empty_error_and_permission_states() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="JobLookupResultsText" Classes="status-empty"' in xaml
    assert 'loading · 正在读取 Core 任务回执。' in code
    assert 'permission · Core 拒绝读取任务回执' in code
    assert 'empty · Core 未找到该任务回执。' in code
    assert 'JobStateSemantic(state)' in code


def test_desktop_frame_has_bounded_responsive_column_behavior() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="MainFrameGrid"' in xaml
    assert 'SizeChanged="OnMainFrameSizeChanged"' in xaml
    assert 'x:Name="ContextSidebar"' in xaml
    assert 'x:Name="InspectorPanel"' in xaml
    assert 'GetAaosBreakpoint("AaosInspectorBreakpoint", 1440)' in code
    assert 'GetAaosBreakpoint("AaosTabletBreakpoint", 1024)' in code


def test_responsive_layout_reflows_home_cards_and_activity_dock() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="HomeFocusGrid"' in xaml
    assert 'x:Name="HomeFocusActionCard"' in xaml
    assert 'x:Name="HomeStatsSourceCard"' in xaml
    assert 'x:Name="HomeStatsKnowledgeCard"' in xaml
    assert 'x:Name="HomeStatsLearningCard"' in xaml
    assert 'x:Name="ActivityDock"' in xaml
    assert 'x:Name="ActivityDockGrid"' in xaml
    assert 'Grid.SetColumn(ActivityDock, compact ? 0 : 1);' in code
    assert 'Grid.SetColumnSpan(ActivityDock, compact ? 4 : 3);' in code
    assert 'HomeFocusGrid.ColumnDefinitions' in code
    assert 'HomeStatsSurface.ColumnDefinitions' in code
    assert 'Grid.SetColumn(HomeFocusActionCard, compact ? 0 : 1);' in code
    assert 'x:Name="CaptureContextActions"' in xaml
    assert 'x:Name="LearningCaptureActions"' in xaml
    assert 'GetAaosBreakpoint("AaosNarrowActionsBreakpoint", 1280)' in code
    assert 'CaptureContextActions.Orientation' in code
    assert 'LearningCaptureActions.Orientation' in code


def test_wide_workspace_has_a_readable_bounded_center_width() -> None:
    xaml = XAML.read_text(encoding="utf-8")

    assert 'MaxWidth="1200"' in xaml


def test_wide_desktop_keeps_inspector_and_bounded_workspace_at_1920_2560() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    theme = THEME_XAML.read_text(encoding="utf-8")

    assert 'ColumnDefinitions="256,220,*,300"' in xaml
    assert 'x:Name="InspectorPanel"' in xaml
    assert 'GetAaosBreakpoint("AaosInspectorBreakpoint", 1440)' in code
    assert 'InspectorDrawerButton.IsVisible = hideInspector;' in code
    assert 'InspectorPanel.IsVisible = true;' in code
    assert '<x:Double x:Key="AaosInspectorBreakpoint">1440</x:Double>' in theme
    assert 'MaxWidth="1200"' in xaml


def test_aaos_buttons_have_an_explicit_keyboard_focus_state() -> None:
    theme = THEME_XAML.read_text(encoding="utf-8")

    assert '<Style Selector="Button:focus"' in theme
    assert '<Style Selector="TextBox:focus"' in theme
    assert 'BorderBrush" Value="{DynamicResource AaosPrimaryBrush}"' in theme


def test_aaos_semantic_status_tokens_are_defined_and_used_for_core_state() -> None:
    theme = THEME_XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for brush in ("AaosSuccessBrush", "AaosErrorBrush", "AaosInfoBrush", "AaosReviewBrush"):
        assert f'x:Key="{brush}"' in theme
    for state in ("status-success", "status-error", "status-info", "status-review", "status-loading", "status-empty"):
        assert f'TextBlock.{state}' in theme
    assert 'CoreStatusText.Classes.Set("status-success", result.ok);' in code
    assert 'CoreStatusText.Classes.Set("status-error", !result.ok);' in code
    assert 'private void SetStatus(TextBlock target, string text, string semanticState)' in code
    assert 'SetStatus(LibrarySearchStatusText' in code
    assert 'SetStatus(LearningStatusText' in code


def test_aaos_lists_have_explicit_selected_and_keyboard_focus_states() -> None:
    theme = THEME_XAML.read_text(encoding="utf-8")
    assert '<Style Selector="ListBoxItem:selected"' in theme
    assert '<Style Selector="ListBoxItem:focus"' in theme
    assert 'AaosPrimaryBrush' in theme


def test_primary_rail_exposes_declared_product_domains() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for name, handler, domain in (
        ("RailResearchButton", "OnResearchClick", "research"),
        ("RailJobsButton", "OnJobsClick", "jobs"),
        ("RailPluginsButton", "OnPluginsClick", "plugins"),
        ("RailModelsButton", "OnModelsClick", "models"),
    ):
        assert f'x:Name="{name}"' in xaml
        assert f'Click="{handler}"' in xaml
        assert f'"{domain}" => "{domain}"' in code
        assert f'railSpace == "{domain}"' in code


def test_evidence_center_projects_only_existing_core_read_models() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    for name in ("RailEvidenceButton", "MobileEvidenceButton", "EvidenceSurface", "EvidenceAnchorsList", "EvidenceBundlesText"):
        assert f'x:Name="{name}"' in xaml
    assert 'Click="OnEvidenceClick"' in xaml
    assert 'Click="OnEvidenceRefreshClick"' in xaml
    assert 'SelectionChanged="OnEvidenceAnchorSelected"' in xaml
    assert '当前 Core 未暴露 Evidence 列表接口' in code
    assert '未调用旧 workspace API' in code
    assert 'semanticState == "unavailable"' in code
    assert 'SendWorkspaceAsync(' not in code
    assert '"/api/evidence/anchors?limit=50"' not in code
    assert '"/api/evidence/bundles?limit=50"' not in code
    assert 'public sealed class EvidenceAnchorRow' in code
    assert '不包含原文正文' in code
    assert '不把 Evidence 元数据升级为 Knowledge Truth' in code
    assert 'x:Name="EvidenceSurface"' in xaml
    assert 'Click="OnEvidenceOpenCaptureClick"' in xaml
    assert 'Click="OnEvidenceOpenJobsClick"' in xaml
    assert '不显示合成 anchor 或 bundle' in xaml


def test_unavailable_product_surfaces_have_truthful_next_actions() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="UnavailableSurface"' in xaml
    assert 'x:Name="UnavailableSurfaceStateText"' in xaml
    assert 'x:Name="UnavailableSurfaceBoundaryText"' in xaml
    assert 'x:Name="UnavailableSurfaceNextStepText"' in xaml
    assert 'UnavailableSurfaceNextStepText.Text = section switch' in code
    assert 'Click="OnUnavailableHomeClick"' in xaml
    assert 'Click="OnUnavailableSettingsClick"' in xaml
    assert 'private void OnUnavailableHomeClick' in code
    assert 'private void OnUnavailableSettingsClick' in code
    assert '尚未接入 Core' in code


def test_mobile_workspace_keeps_primary_navigation_discoverable() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="MobileRail"' in xaml
    assert 'HorizontalScrollBarVisibility="Hidden"' in xaml
    assert 'x:Name="MobileWorkspaceButton"' in xaml
    assert 'x:Name="MobileKnowledgeButton"' in xaml
    assert 'x:Name="MobileLearningButton"' in xaml
    assert 'x:Name="MobileSystemButton"' in xaml
    assert 'MobileRail.IsVisible = mobile;' in code
    assert 'PrimaryRail.IsVisible = !mobile;' in code
    assert 'Grid.SetColumn(WorkspaceScrollViewer, mobile ? 0 : 2);' in code
    assert 'Grid.SetColumnSpan(WorkspaceScrollViewer, mobile ? 4 : 1);' in code
    theme = THEME_XAML.read_text(encoding="utf-8")
    assert '<x:Double x:Key="AaosMobileBreakpoint">840</x:Double>' in theme


def test_compact_home_and_source_reader_use_explicit_single_column_reflow() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="SourceReaderShellGrid"' in xaml
    assert 'x:Name="SourceReaderOutlineBorder"' in xaml
    assert 'x:Name="SourceReaderMainBorder"' in xaml
    assert 'var sourceReaderCompact = compact || e.NewSize.Width < sourceReaderStackBreakpoint;' in code
    assert 'new ColumnDefinitions("1*")' in code
    assert 'new RowDefinitions("Auto,Auto,Auto")' in code
    assert 'Grid.SetRow(SourceReaderChainBorder, sourceReaderCompact ? 2 : 0);' in code
    assert 'x:Name="HomeHeroGrid"' in xaml
    assert 'x:Name="HomeHeroImage"' in xaml
    assert 'Grid.SetColumn(HomeHeroImage, compact ? 0 : 1);' in code


def test_compact_knowledge_facts_reflow_without_overlapping_two_column_cards() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'x:Name="KnowledgeFactsGrid"' in xaml
    for name in ("KnowledgeStatusCard", "KnowledgeSourceCard", "KnowledgeTrustCard", "KnowledgeReviewCard"):
        assert f'x:Name="{name}"' in xaml
    assert 'KnowledgeFactsGrid.ColumnDefinitions = compact' in code
    assert 'new RowDefinitions("Auto,Auto,Auto,Auto")' in code
    assert 'Grid.SetRow(KnowledgeReviewCard, compact ? 3 : 1);' in code
    assert 'HomeLifecycleGrid.ColumnDefinitions = compact' in code
    assert 'new RowDefinitions("Auto,Auto,Auto,Auto,Auto")' in code


def test_learning_review_actions_reflow_and_navigation_surfaces_auto_refresh() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="ReviewActionsGrid"' in xaml
    assert 'x:Name="LearningEmptyActions"' in xaml
    assert 'Click="OnLearningOpenLibraryClick"' in xaml
    assert 'Click="OnLearningOpenJobsClick"' in xaml
    assert 'ReviewActionsGrid.ColumnDefinitions = narrowActions' in code
    assert 'new RowDefinitions("Auto,Auto,Auto,Auto")' in code
    assert 'section == "learning"' in code
    assert '_ = LoadLearningIfNeededAsync();' in code
    assert 'section == "recovery"' in code
    assert '_ = ReadRecoveryStatusAsync();' in code


def test_core_learning_controls_expose_stable_automation_names_and_motion_tokens() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    theme = THEME_XAML.read_text(encoding="utf-8")

    for name in (
        'AutomationProperties.Name="学习回答输入框"',
        'AutomationProperties.Name="Core 正确性结果"',
        'AutomationProperties.Name="FSRS Again 重来"',
        'AutomationProperties.Name="FSRS Easy 轻松"',
        'AutomationProperties.Name="复习提交状态"',
    ):
        assert name in xaml
    assert '<DoubleTransition Property="Opacity" Duration="0:0:0.12" />' in theme
    assert '<x:Double x:Key="AaosMotionFastMs">120</x:Double>' in theme
    assert '<Setter Property="Opacity" Value="0.86" />' in theme
    assert 'x:Key="AaosPrimaryTextBrush" Color="#061118"' in theme
    assert '<Setter Property="Foreground" Value="{DynamicResource AaosPrimaryTextBrush}" />' in theme
    assert 'AAOS_REDUCED_MOTION' in code
    assert 'Grid.reduced-motion Button' in theme


def test_source_reader_can_read_existing_core_transform_output_without_calling_it_original_text() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="ReadSourceTransformButton"' in xaml
    assert 'Click="OnReadSourceTransformClick"' in xaml
    assert 'x:Name="SourceReaderTransformText"' in xaml
    assert 'private async void OnReadSourceTransformClick' in code
    assert '/outputs/text' in code
    assert 'string.Equals(selected.Readable, "true", StringComparison.OrdinalIgnoreCase)' in code
    assert 'StringComparison.OrdinalIgnoreCase' in code
    assert '不等于原文正文、理解或已接受 Knowledge' in code


def test_source_reader_can_copy_only_the_selected_core_provenance_chain() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="CopySourceProvenanceButton"' in xaml
    assert 'Click="OnCopySourceProvenanceClick"' in xaml
    assert 'private async void OnCopySourceProvenanceClick' in code
    assert 'await clipboard.SetTextAsync(text);' in code
    assert '不包含原文正文' in code
    assert 'HasProvenanceValue(selected.SourceId)' in code
    assert 'HasProvenanceValue(selected.Member)' in code
    assert 'HasProvenanceValue(selected.Sha256)' in code


def test_frontend_exposes_truthful_transient_toast_feedback() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="ToastSurface"' in xaml
    assert 'x:Name="ToastText"' in xaml
    assert 'AutomationProperties.Name="临时操作提示"' in xaml
    assert 'private void ShowToast' in code
    assert 'ToastSurface.Classes.Set(toastState, true);' in code
    for state in ("toast-success", "toast-error", "toast-info", "toast-review"):
        assert f'<Style Selector="Border.{state}">' in (ROOT / "apps/ArcheAxis.Desktop/Themes/AaosTheme.axaml").read_text(encoding="utf-8")
    assert 'DispatcherTimer' in code
    assert 'ShowToast("已复制来源链摘要")' in code
    assert 'ShowToast("复习结果已由 Core 记录")' in code
    assert '已接收 {imported}/{files.Count} 项；任务状态见回执' in code
    assert '导入已中断，已保留部分 Core 回执' in code


def test_source_reader_can_copy_a_bounded_citation_metadata_summary() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="CopySourceCitationButton"' in xaml
    assert 'Click="OnCopySourceCitationClick"' in xaml
    assert 'AutomationProperties.Name="复制引用元数据"' in xaml
    assert 'private async void OnCopySourceCitationClick' in code
    assert '引用元数据' in code
    assert '不包含原文正文' in code


def test_primary_and_mobile_navigation_have_stable_accessibility_names() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    expected = {
        'x:Name="RailMachineButton"': 'AutomationProperties.Name="打开机器知识"',
        'x:Name="RailResearchButton"': 'AutomationProperties.Name="打开研究"',
        'x:Name="RailPluginsButton"': 'AutomationProperties.Name="打开插件"',
        'x:Name="RailModelsButton"': 'AutomationProperties.Name="打开模型"',
        'x:Name="MobileMachineButton"': 'AutomationProperties.Name="打开机器知识"',
        'x:Name="MobileResearchButton"': 'AutomationProperties.Name="打开研究"',
        'x:Name="MobilePluginsButton"': 'AutomationProperties.Name="打开插件"',
        'x:Name="MobileModelsButton"': 'AutomationProperties.Name="打开模型"',
    }
    for control, automation_name in expected.items():
        assert control in xaml
        control_start = xaml.index(control)
        control_end = xaml.index(" />", control_start)
        assert automation_name in xaml[control_start:control_end]
    assert '来源链字段不完整，未复制占位值' in code
    assert 'private bool IsCurrentSourceTransformRequest' in code
    assert 'ReferenceEquals(SourceReaderMembersList.SelectedItem, selected)' in code


def test_source_reader_context_actions_reflow_at_narrow_widths() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")

    assert 'x:Name="SourceReaderContextActions"' in xaml
    assert 'SourceReaderContextActions.Orientation = narrowActions' in code


def test_learning_navigation_does_not_reenter_section_setup() -> None:
    code = CODE.read_text(encoding="utf-8")

    assert 'private bool _learningNavigationLoadInProgress;' in code
    assert 'section == "learning" && !_learningNavigationLoadInProgress' in code
    assert '_learningNavigationLoadInProgress = true;' in code
    assert '_learningNavigationLoadInProgress = false;' in code


def test_command_palette_can_execute_evidence_route() -> None:
    code = CODE.read_text(encoding="utf-8")

    assert 'new("证据中心", "evidence", "证据中心")' in code


def test_command_palette_routes_have_one_authoritative_definition() -> None:
    code = CODE.read_text(encoding="utf-8")

    assert "private sealed record CommandPaletteRoute" in code
    assert "CommandPaletteRoutes.FirstOrDefault" in code
    assert "CommandPaletteRoutes.Select" in code


def test_command_palette_placeholder_lists_all_primary_routes() -> None:
    xaml = XAML.read_text(encoding="utf-8")

    assert 'PlaceholderText="输入：首页 / 捕获 / 资料库 / 原件阅读 / 知识库 / 原件编辑 / 记忆地图 / 学习 / 证据中心 / 研究 / 机器知识 / 任务 / 插件 / 模型 / 恢复 / 设置"' in xaml


def test_command_palette_unknown_command_help_lists_every_route() -> None:
    code = CODE.read_text(encoding="utf-8")

    assert 'string.Join("、", CommandPaletteRoutes.Select(candidate => candidate.Label))' in code


def test_command_palette_restores_focus_after_close_or_execute() -> None:
    code = CODE.read_text(encoding="utf-8")

    assert 'private IInputElement? _commandPaletteReturnFocus;' in code
    assert 'private void SetCommandPaletteVisibility(bool visible)' in code
    assert '_commandPaletteReturnFocus = FocusManager.GetFocusedElement();' in code
    assert 'returnFocus?.Focus();' in code
    assert 'SetCommandPaletteVisibility(false);' in code


def test_command_palette_navigation_does_not_mutate_learning_empty_state() -> None:
    code = CODE.read_text(encoding="utf-8")
    method = code[code.index("private void OnCommandPaletteKeyDown"):code.index("private void OnCommandPaletteTextChanged")]

    assert "LearningEmptyActions.IsVisible" not in method


def test_command_palette_cycles_focus_between_input_and_results_on_tab() -> None:
    code = CODE.read_text(encoding="utf-8")
    method = code[code.index("private void OnCommandPaletteKeyDown"):code.index("private void OnCommandPaletteTextChanged")]

    assert "if (e.Key == Key.Tab)" in method
    assert "ReferenceEquals(sender, CommandPaletteResultsList)" in method
    assert "CommandPaletteBox.Focus();" in method
    assert "CommandPaletteResultsList.Focus();" in method


def test_knowledge_reads_ignore_stale_responses() -> None:
    code = CODE.read_text(encoding="utf-8")
    start = code.index("private async void OnReadKnowledgeClick")
    end = code.index("private async void OnReadMachineTaskClick")
    method = code[start:end]

    assert "private long _knowledgeRequestVersion;" in code
    assert "var requestVersion = ++_knowledgeRequestVersion;" in method
    assert method.count("if (requestVersion != _knowledgeRequestVersion)") >= 3


def test_source_copy_actions_report_clipboard_write_failures() -> None:
    code = CODE.read_text(encoding="utf-8")

    assert "private static async Task<bool> TrySetClipboardTextAsync" in code
    assert "if (!await TrySetClipboardTextAsync(clipboard, provenance))" in code
    assert "if (!await TrySetClipboardTextAsync(clipboard, citation))" in code
    assert "剪贴板写入失败" in code


def test_status_updates_refresh_the_accessible_status_name() -> None:
    code = CODE.read_text(encoding="utf-8")

    assert "Avalonia.Automation.AutomationProperties.SetName(target, text);" in code
    assert 'target.Classes.Set("status-warning", semanticState == "warning");' in code


def test_primary_status_surfaces_have_initial_accessible_names() -> None:
    xaml = XAML.read_text(encoding="utf-8")

    expected = {
        'x:Name="CoreStatusText"': 'AutomationProperties.Name="核心状态"',
        'x:Name="LibrarySearchStatusText"': 'AutomationProperties.Name="资料库搜索状态"',
        'x:Name="SourceReaderStatusText"': 'AutomationProperties.Name="来源阅读状态"',
        'x:Name="KnowledgeStateText"': 'AutomationProperties.Name="知识库状态"',
        'x:Name="EvidenceStatusText"': 'AutomationProperties.Name="证据中心状态"',
        'x:Name="SettingsStateText"': 'AutomationProperties.Name="系统状态"',
        'x:Name="ActivityDockStatusText"': 'AutomationProperties.Name="活动回执状态"',
        'x:Name="CommandPaletteStatusText"': 'AutomationProperties.Name="命令面板状态"',
    }
    for control, name in expected.items():
        segment = xaml.split(control, 1)[1].split(" />", 1)[0]
        assert name in segment


def test_named_product_actions_have_stable_accessible_names() -> None:
    xaml = XAML.read_text(encoding="utf-8")

    expected = {
        'x:Name="FirstRunImportButton"': 'AutomationProperties.Name="选择资料并导入"',
        'x:Name="HomeOpenCurrentSourceButton"': 'AutomationProperties.Name="打开当前来源"',
        'x:Name="HomeContinueReadingButton"': 'AutomationProperties.Name="打开当前来源"',
        'x:Name="HomeDeepTutorButton"': 'AutomationProperties.Name="打开 DeepTutor 工作台"',
        'x:Name="HomeImportButton"': 'AutomationProperties.Name="选择资料并导入"',
        'x:Name="OpenLatestSourceButton"': 'AutomationProperties.Name="打开最近来源"',
        'x:Name="OpenLatestJobButton"': 'AutomationProperties.Name="查看最近任务"',
        'x:Name="LibrarySearchButton"': 'AutomationProperties.Name="搜索"',
        'x:Name="SourceReaderLoadButton"': 'AutomationProperties.Name="读取来源成员"',
        'x:Name="KnowledgeLoadButton"': 'AutomationProperties.Name="读取知识"',
        'x:Name="SubmitReviewButton"': 'AutomationProperties.Name="提交复习结果"',
        'x:Name="MachineTaskLoadButton"': 'AutomationProperties.Name="读取任务收据"',
        'x:Name="EvidenceRefreshButton"': 'AutomationProperties.Name="读取证据"',
        'x:Name="OpenLibrarySourceButton"': 'AutomationProperties.Name="查看来源成员"',
        'x:Name="BackToLibraryButton"': 'AutomationProperties.Name="返回资料库"',
        'x:Name="BackToKnowledgeFromSourceButton"': 'AutomationProperties.Name="返回 Knowledge 详情"',
        'x:Name="ViewSourceJobButton"': 'AutomationProperties.Name="查看选中成员的任务回执"',
        'x:Name="FindLibraryFromSourceButton"': 'AutomationProperties.Name="在资料库查找关联投影"',
        'x:Name="ReadSourceTransformButton"': 'AutomationProperties.Name="读取转换内容"',
        'x:Name="BackToLibraryFromKnowledgeButton"': 'AutomationProperties.Name="返回资料库 Evidence Detail"',
        'x:Name="OpenKnowledgeSourceButton"': 'AutomationProperties.Name="查看 Knowledge 来源成员"',
        'x:Name="OpenLearningCaptureSourceButton"': 'AutomationProperties.Name="打开最近来源"',
        'x:Name="OpenLearningCaptureJobButton"': 'AutomationProperties.Name="查看最近任务"',
        'x:Name="OpenLearningKnowledgeButton"': 'AutomationProperties.Name="打开当前 Knowledge 详情"',
        'x:Name="InspectorOpenSourceButton"': 'AutomationProperties.Name="打开来源"',
        'x:Name="InspectorOpenKnowledgeButton"': 'AutomationProperties.Name="打开 Knowledge"',
        'x:Name="InspectorBackLibraryButton"': 'AutomationProperties.Name="返回资料库"',
    }
    for control, name in expected.items():
        segment = xaml.split(control, 1)[1].split(" />", 1)[0]
        assert name in segment


def test_every_desktop_button_declares_an_accessible_name() -> None:
    unnamed = []
    for line_number, line in enumerate(XAML.read_text(encoding="utf-8").splitlines(), start=1):
        if "<Button" in line and "AutomationProperties.Name=" not in line:
            unnamed.append(f"{line_number}: {line.strip()}")
    assert unnamed == []


def test_every_desktop_input_and_result_control_declares_an_accessible_name() -> None:
    unnamed = []
    control_prefixes = ("<TextBox ", "<TextBox>", "<ListBox ", "<ListBox>", "<ComboBox ", "<ComboBox>", "<CheckBox ", "<CheckBox>", "<ToggleSwitch ", "<ToggleSwitch>")
    for line_number, line in enumerate(XAML.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith(control_prefixes) and "AutomationProperties.Name=" not in line:
            unnamed.append(f"{line_number}: {line.strip()}")
    assert unnamed == []


def test_primary_lookup_inputs_submit_on_enter_through_existing_routes() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert xaml.count('KeyDown="OnToolbarInputKeyDown"') == 5
    assert "private void OnToolbarInputKeyDown" in code
    for route in (
        "OnSearchLibraryClick",
        "OnReadSourceMembersClick",
        "OnReadKnowledgeClick",
        "OnReadMachineTaskClick",
        "OnReadJobReceiptClick",
    ):
        assert route in code


def test_command_palette_status_updates_accessible_name_with_selection() -> None:
    code = CODE.read_text(encoding="utf-8")

    assert "private void SetCommandPaletteStatus(string text)" in code
    assert "AutomationProperties.SetName(CommandPaletteStatusText, text);" in code
    assert "SetCommandPaletteStatus($\"已选择“{selected}”；按 Enter 执行。\");" in code


def test_command_palette_results_keep_enter_handling_when_list_has_focus() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    list_start = xaml.index('x:Name="CommandPaletteResultsList"')
    list_end = xaml.index("</ListBox>", list_start)
    result_list = xaml[list_start:list_end]

    assert 'KeyDown="OnCommandPaletteKeyDown"' in result_list


def test_command_palette_results_support_pointer_activation() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    list_start = xaml.index('x:Name="CommandPaletteResultsList"')
    list_end = xaml.index("</ListBox>", list_start)
    result_list = xaml[list_start:list_end]

    assert 'DoubleTapped="OnCommandPaletteResultDoubleTapped"' in result_list
    assert "private void OnCommandPaletteResultDoubleTapped" in code
    assert "ExecuteCommandPaletteCommand(selected);" in code


def test_source_reader_action_group_is_attached_to_source_chain() -> None:
    xaml = XAML.read_text(encoding="utf-8")

    chain_start = xaml.index('x:Name="SourceReaderChainBorder"')
    chain_end = xaml.index('x:Name="KnowledgeSurface"')
    chain = xaml[chain_start:chain_end]
    assert 'x:Name="SourceReaderContextActions"' in chain
