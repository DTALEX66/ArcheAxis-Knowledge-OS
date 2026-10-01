from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml.cs"


def test_home_dashboard_uses_the_active_section_for_home_only_surfaces():
    source = CODE.read_text(encoding="utf-8")
    start = source.index("private void ComposeHomeDashboard()")
    end = source.index("private static void AttachAccessibleTextSync", start)
    method = source[start:end]

    assert "section ==" not in method
    assert 'HomeGraphContentGrid.IsVisible = _activeSection == "home";' in method
    assert 'HomeNodeDetailsCard.IsVisible = _activeSection == "home";' in method
    assert 'HomeTrendCard.IsVisible = _activeSection == "home";' in method
