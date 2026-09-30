from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml.cs"


def test_learning_and_machine_metrics_use_compact_mobile_cards() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert "MachineMetricGrid.ItemHeight = mobile ? 112 : 126;" in code
    assert "LearningMetricsGrid.ItemHeight = mobile ? 112 : 126;" in code


def test_learning_and_machine_metrics_keep_separate_width_adaptation() -> None:
    code = CODE.read_text(encoding="utf-8")
    assert "var machineMetricColumns = machineMetricContentWidth < 580 ? 1 : machineMetricContentWidth < 920 ? 2 : 4;" in code
    assert "var learningMetricColumns = learningMetricContentWidth < 580 ? 1 : learningMetricContentWidth < 920 ? 2 : 4;" in code
    assert "MachineMetricGrid.ItemWidth = Math.Max(180, machineMetricWidth);" in code
    assert "LearningMetricsGrid.ItemWidth = Math.Max(180, learningMetricWidth);" in code
