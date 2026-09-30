from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "apps/ArcheAxis.Desktop/AaosCaptureScanSweep.axaml"
CODE = ROOT / "apps/ArcheAxis.Desktop/AaosCaptureScanSweep.axaml.cs"
MAIN_XAML = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml"
MAIN_CODE = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml.cs"


def test_capture_scan_sweep_uses_theme_primary_and_clips_scan_bar():
    xaml = CONTROL.read_text(encoding="utf-8")
    assert 'x:Class="ArcheAxis.Desktop.AaosCaptureScanSweep"' in xaml
    assert 'DynamicResource AaosPrimaryBrush' in xaml
    assert 'ClipToBounds="True"' in xaml


def test_capture_scan_sweep_runs_linear_2_4_second_cycle_over_reference_travel():
    code = CODE.read_text(encoding="utf-8")
    assert 'TimeSpan.FromMilliseconds(16)' in code
    assert 'TimeSpan.FromSeconds(2.4)' in code
    assert 'const double start = -1.2' in code
    assert 'const double travel = 5.4' in code
    assert 'TranslateTransform' in code


def test_capture_scan_sweep_stops_and_resets_when_hidden_or_reduced_motion():
    code = CODE.read_text(encoding="utf-8")
    assert 'SetReducedMotion(bool reducedMotion)' in code
    assert 'SetSweepActive(bool active)' in code
    assert 'OnPropertyChanged(AvaloniaPropertyChangedEventArgs change)' in code
    assert 'OnDetachedFromVisualTree' in code
    assert 'SweepTimer.Stop()' in code
    assert 'ResetSweep()' in code
    assert 'IsVisible = _sweepActive && !_reducedMotion;' in code


def test_capture_scan_sweep_is_bound_to_import_lifecycle_and_app_motion_preference():
    xaml = MAIN_XAML.read_text(encoding="utf-8")
    code = MAIN_CODE.read_text(encoding="utf-8")

    assert '<local:AaosCaptureScanSweep x:Name="CaptureScanSweep"' in xaml
    assert 'CaptureScanSweep.SetReducedMotion(_reducedMotion);' in code
    assert 'CaptureScanSweep.SetSweepActive(true);' in code
    assert 'CaptureScanSweep.SetSweepActive(false);' in code
