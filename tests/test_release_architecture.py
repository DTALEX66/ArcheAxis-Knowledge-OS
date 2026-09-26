from pathlib import Path

from scripts.release.verify_release_architecture import verify


def test_release_architecture_requires_formal_chain(tmp_path: Path):
    (tmp_path / "apps/ArcheAxis.Desktop").mkdir(parents=True)
    (tmp_path / "apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj").write_text("", encoding="utf-8")
    (tmp_path / "crates/archeaxis-api").mkdir(parents=True)
    (tmp_path / "services/python-workers").mkdir(parents=True)
    workflow = tmp_path / "release.yml"
    workflow.write_text(
        "ArcheAxis.Desktop\ncrates/archeaxis-api\nservices/python-workers\n"
        "green-candidate-vnext\nverify_green_candidate.py --require-runtime\n"
        "Tauri recovery\n  publish:\n    if: ${{ false }} # R6 release freeze\n",
        encoding="utf-8",
    )
    assert verify(tmp_path, workflow) == []


def test_release_architecture_rejects_removing_current_freeze(tmp_path: Path):
    (tmp_path / "apps/ArcheAxis.Desktop").mkdir(parents=True)
    (tmp_path / "apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj").write_text("", encoding="utf-8")
    (tmp_path / "crates/archeaxis-api").mkdir(parents=True)
    (tmp_path / "services/python-workers").mkdir(parents=True)
    workflow = tmp_path / "release.yml"
    workflow.write_text(
        "ArcheAxis.Desktop\ncrates/archeaxis-api\nservices/python-workers\n"
        "green-candidate-vnext\nverify_green_candidate.py --require-runtime\n"
        "Tauri recovery\n  publish:\n    if: ${{ github.ref_type == 'tag' }}\n",
        encoding="utf-8",
    )
    assert "release publish job is not disabled by the current R6 freeze" in verify(tmp_path, workflow)
