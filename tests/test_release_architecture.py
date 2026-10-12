from pathlib import Path

from scripts.release.verify_release_architecture import verify


def test_release_architecture_requires_formal_chain(tmp_path: Path):
    (tmp_path / "src-tauri").mkdir(parents=True)
    (tmp_path / "frontend").mkdir(parents=True)
    (tmp_path / "src-tauri/tauri.conf.json").write_text("{}", encoding="utf-8")
    (tmp_path / "frontend/package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "crates/archeaxis-api").mkdir(parents=True)
    (tmp_path / "services/python-workers").mkdir(parents=True)
    workflow = tmp_path / "release.yml"
    workflow.write_text(
        "src-tauri/frontend\ncrates/archeaxis-api\nservices/python-workers\n"
        "release-candidate.json candidate.commit GITHUB_SHA candidate.installer.sha256 candidate.executable.sha256 candidate.frontend.sha256 verify_nsis_install.ps1\n"
        "Tauri formal\n  publish:\n    if: ${{ false }} # R6 release freeze\n",
        encoding="utf-8",
    )
    assert verify(tmp_path, workflow) == []


def test_release_architecture_rejects_removing_current_freeze(tmp_path: Path):
    (tmp_path / "src-tauri").mkdir(parents=True)
    (tmp_path / "frontend").mkdir(parents=True)
    (tmp_path / "src-tauri/tauri.conf.json").write_text("{}", encoding="utf-8")
    (tmp_path / "frontend/package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "crates/archeaxis-api").mkdir(parents=True)
    (tmp_path / "services/python-workers").mkdir(parents=True)
    workflow = tmp_path / "release.yml"
    workflow.write_text(
        "src-tauri/frontend\ncrates/archeaxis-api\nservices/python-workers\n"
        "release-candidate.json candidate.commit GITHUB_SHA candidate.installer.sha256 candidate.executable.sha256 candidate.frontend.sha256 verify_nsis_install.ps1\n"
        "Tauri formal\n  publish:\n    if: ${{ github.ref_type == 'tag' }}\n",
        encoding="utf-8",
    )
    assert "release publish job is not disabled by the current R6 freeze" in verify(tmp_path, workflow)


def test_current_release_workflow_matches_formal_host():
    root = Path(__file__).resolve().parents[1]
    assert verify(root, root / ".github/workflows/release.yml") == []
