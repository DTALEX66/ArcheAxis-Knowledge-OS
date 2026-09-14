from pathlib import Path

from scripts.release.verify_release_architecture import verify


def test_release_architecture_requires_formal_chain(tmp_path: Path):
    (tmp_path / "apps/ArcheAxis.Desktop").mkdir(parents=True)
    (tmp_path / "apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj").write_text("", encoding="utf-8")
    (tmp_path / "crates/archeaxis-api").mkdir(parents=True)
    (tmp_path / "services/python-workers").mkdir(parents=True)
    workflow = tmp_path / "release.yml"
    workflow.write_text(
        "ArcheAxis.Desktop\ncrates/archeaxis-api\nservices/python-workers\nTauri recovery\n",
        encoding="utf-8",
    )
    assert verify(tmp_path, workflow) == []
