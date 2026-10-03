from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "apps/ArcheAxis.Desktop/Views/SourceReaderView.axaml"
CODE = ROOT / "apps/ArcheAxis.Desktop/Views/SourceReaderView.axaml.cs"
ICON = ROOT / "apps/ArcheAxis.Desktop/AaosIcon.axaml.cs"


def test_source_reader_dynamic_icon_uses_bindable_avalonia_property():
    xaml = VIEW.read_text(encoding="utf-8")
    icon = ICON.read_text(encoding="utf-8")
    assert 'IconName="{Binding DisplayIcon}"' in xaml
    assert 'StyledProperty<string> IconNameProperty' in icon
    assert 'GetValue(IconNameProperty)' in icon
    assert 'SetValue(IconNameProperty, value)' in icon


def test_source_reader_uses_vector_icons_and_hierarchical_provenance_actions():
    xaml = VIEW.read_text(encoding="utf-8")
    for icon in ("Source", "Evidence", "Connection", "Review", "Refresh", "Import", "Plus", "Copy", "Link"):
        assert f'IconName="{icon}"' in xaml
    for name in (
        "SourceReaderChainSourceText",
        "SourceReaderChainMemberText",
        "SourceReaderChainJobText",
        "SourceReaderChainShaText",
    ):
        assert f'x:Name="{name}"' in xaml
    assert 'AutomationProperties.Name="复制来源链"' in xaml
    assert 'AutomationProperties.Name="复制引用元数据"' in xaml


def test_source_reader_keeps_responsive_breakpoints_and_selection_feedback():
    xaml = VIEW.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert 'StackBreakpoint="{DynamicResource AaosSourceReaderStackBreakpoint}"' in xaml
    assert 'NarrowActionsBreakpoint="{DynamicResource AaosSourceReaderNarrowActionsBreakpoint}"' in xaml
    assert "SourceReaderReturnActions.Orientation = narrowActions ? Orientation.Vertical" in code
    assert "SourceReaderContextActions.Orientation = narrowActions ? Orientation.Vertical" in code
    assert 'DoubleTransition Property="Opacity" Duration="0:0:0.16"' in xaml
    assert "AnimateChainSelection();" in code
    assert "Dispatcher.UIThread.Post(() => SourceReaderChainBorder.Opacity = 1" in code


def test_source_reader_visuals_do_not_introduce_fake_source_content():
    xaml = VIEW.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    assert "Core 来源成员投影" in xaml
    # The reader must state that an unextracted original has no body to show, rather than
    # rendering placeholder text as if it were the document.
    assert "原件正文暂未提供" in code
    assert "evidence anchor" in xaml
