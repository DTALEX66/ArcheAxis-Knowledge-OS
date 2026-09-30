from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READER_XAML = (ROOT / "apps/ArcheAxis.Desktop/Views/SourceReaderView.axaml").read_text(encoding="utf-8")
READER_CODE = (ROOT / "apps/ArcheAxis.Desktop/Views/SourceReaderView.axaml.cs").read_text(encoding="utf-8")
EVIDENCE_XAML = (ROOT / "apps/ArcheAxis.Desktop/Views/EvidenceCenterView.axaml").read_text(encoding="utf-8")
EVIDENCE_CODE = (ROOT / "apps/ArcheAxis.Desktop/Views/EvidenceCenterView.axaml.cs").read_text(encoding="utf-8")


def test_source_reader_rows_show_type_icons_and_keyboard_focus_feedback() -> None:
    assert 'IconName="{Binding DisplayIcon}"' in READER_XAML
    assert 'Border.source-reader-row' in READER_XAML
    assert 'ListBoxItem:focus Border.source-reader-row' in READER_XAML
    assert 'DisplayIcon => "Source"' in READER_CODE
    assert 'DisplayIcon => "Review"' in READER_CODE


def test_evidence_detail_mother_layout_scales_its_source_chain_illustration() -> None:
    assert 'x:Name="EvidenceSourceChainIllustration"' in EVIDENCE_XAML
    assert '<Viewbox x:Name="EvidenceSourceChainIllustration"' in EVIDENCE_XAML
    assert "EvidenceSourceChainIllustration.Width =" in EVIDENCE_CODE
    assert "EvidenceSourceChainIllustration.Height =" in EVIDENCE_CODE
    assert "EvidenceDetailPageGrid" in EVIDENCE_CODE
    assert "Core anchor_id 未读取" in EVIDENCE_XAML
    assert "不表示真实关联数量" in EVIDENCE_XAML


def test_evidence_empty_state_explains_real_core_boundary_and_has_actions() -> None:
    assert 'x:Name="EvidenceEmptyTitleText"' in EVIDENCE_XAML
    assert 'x:Name="EvidenceEmptyDescriptionText"' in EVIDENCE_XAML
    assert 'Click="OnOpenCaptureClick"' in EVIDENCE_XAML
    assert 'Click="OnOpenJobsClick"' in EVIDENCE_XAML
    assert "未生成示例记录" in EVIDENCE_CODE
