from pathlib import Path

from scripts.workflow.environment_registry import resolve


def test_registry_resolves_declared_capabilities_without_installing(tmp_path: Path, monkeypatch):
    manifest = tmp_path / "capabilities.yaml"
    manifest.write_text(
        """
schema_version: '1.0'
capabilities:
  toolchains:
    - name: demo
      version_range: '>=1'
      required_by: [tests]
      local_only: true
      source_url: vendored
      healthcheck_command: 'demo --version'
""",
        encoding="utf-8",
    )
    monkeypatch.setattr("scripts.workflow.environment_registry.shutil.which", lambda name: None)
    report = resolve(manifest)
    assert report["schema"] == "archeaxis.environment-registry/v1"
    assert report["summary"] == {"total": 1, "available": 0, "missing": 1}
    assert report["capabilities"][0]["id"] == "toolchains/demo"
    assert report["install_performed"] is False
    assert report["private_state_opened"] is False
