"""Toast motion preserves B10 timing, status semantics, and reduced-motion behavior."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XAML = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml"
CODE = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml.cs"


def test_toast_has_b10_translate_scale_opacity_and_eased_220ms_motion() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    toast = xaml.split('x:Name="ToastSurface"', 1)[1].split("</Border>", 1)[0]

    assert "<ScaleTransform ScaleX=\"0.98\" ScaleY=\"0.98\" />" in toast
    assert 'ScaleX="0.98" ScaleY="0.98"' in toast
    assert "<TranslateTransform Y=\"12\" />" in toast
    assert 'Y="12"' in toast
    assert "<Border.Transitions><Transitions /></Border.Transitions>" in toast
    assert "ToastMotionDurationMs = 220" in code
    assert "Math.Pow(1 - progress, 3)" in code
    assert "ToastEntranceTranslation.Y" in code
    assert "ToastEntranceScale.ScaleX" in code
    assert "ToastSurface.Opacity" in code


def test_toast_reduced_motion_skips_animation_and_keeps_accessible_live_region() -> None:
    xaml = XAML.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    toast = xaml.split('x:Name="ToastText"', 1)[1].split(" />", 1)[0]

    assert 'AutomationProperties.LiveSetting="Polite"' in toast
    assert '"toast-success", "toast-error", "toast-info", "toast-review", "toast-warning"' in code
    show = code.split("private void ShowToast(", 1)[1].split("private void OnToastTimerTick(", 1)[0]
    assert "if (_reducedMotion)" in show
    assert "_toastMotionTimer.Stop()" in show
    assert "ToastSurface.IsVisible = true" in show
