from __future__ import annotations

import tomllib

import json
import subprocess
import unicodedata
from pathlib import Path

import pytest

from scripts.check_repository_conventions import (
    main as conventions_main,
)
from scripts.check_repository_conventions import (
    normalize_text_bytes,
    scan_git_repository,
    scan_naming_registry_bytes,
    scan_path_set,
    scan_text_bytes,
)
from shared.naming import (
    AmbiguousServiceAliasError,
    UnknownServiceNameError,
    load_naming_registry,
)

ROOT = Path(__file__).resolve().parents[1]


def test_registry_resolves_canonical_ids_and_deprecated_aliases() -> None:
    registry = load_naming_registry(ROOT / "config" / "naming-registry.yaml")

    canonical = registry.resolve_service("inspiration-research")
    legacy = registry.resolve_service("Inspiration_Research")

    assert canonical.service_id == "inspiration-research"
    assert canonical.deprecated_alias is False
    assert legacy.service_id == "inspiration-research"
    assert legacy.deprecated_alias is True
    assert legacy.python_package == "inspiration_research"
    assert legacy.display["zh-CN"] == "灵感研究"


def test_registry_rejects_unknown_service_names() -> None:
    registry = load_naming_registry(ROOT / "config" / "naming-registry.yaml")

    with pytest.raises(UnknownServiceNameError, match="unknown-service"):
        registry.resolve_service("unknown-service")


def test_registry_service_ids_match_the_api_route_contract() -> None:
    registry = load_naming_registry(ROOT / "config" / "naming-registry.yaml")
    route_map = json.loads(
        (ROOT / "migrations" / "reports" / "phase-0" / "API_ROUTE_MAP.json").read_text(
            encoding="utf-8"
        )
    )

    registry_ids = {identity.service_id for identity in registry.services}
    route_service_ids = {route["service"] for route in route_map["routes"]}

    assert registry_ids == route_service_ids == {
        "core",
        "inspiration-research",
        "knowledge-base",
    }


def test_registry_rejects_alias_collisions(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(
        """version: 1
required_locales: [en-US, zh-CN]
services:
  alpha:
    python_package: alpha
    api_prefix: /alpha
    display: {en-US: Alpha, zh-CN: 阿尔法}
    deprecated_aliases: [legacy]
  beta:
    python_package: beta
    api_prefix: /beta
    display: {en-US: Beta, zh-CN: 贝塔}
    deprecated_aliases: [LEGACY]
""",
        encoding="utf-8",
    )

    with pytest.raises(AmbiguousServiceAliasError, match="legacy"):
        load_naming_registry(registry_path)


def test_repository_scanner_validates_registry_semantics() -> None:
    registry_path = "config/naming-registry.yaml"
    valid = (ROOT / registry_path).read_bytes()
    invalid = b"version: 1\nrequired_locales: [en-US, zh-CN]\nservices: {}\n"

    assert scan_naming_registry_bytes(registry_path, valid) == []
    assert [
        issue.code for issue in scan_naming_registry_bytes(registry_path, invalid)
    ] == ["invalid-naming-registry"]


def test_text_scanner_reports_encoding_and_normalization_violations() -> None:
    decomposed = unicodedata.normalize("NFD", "é")
    content = ("\ufefftitle  \r\n" + decomposed + "\u200b").encode("utf-8")

    codes = {issue.code for issue in scan_text_bytes("docs/example.md", content)}

    assert codes == {
        "unexpected-bom",
        "crlf",
        "non-nfc-text",
        "zero-width-character",
        "missing-final-newline",
        "trailing-whitespace",
    }


def test_text_normalizer_produces_utf8_lf_nfc_without_formatting_debt() -> None:
    decomposed = unicodedata.normalize("NFD", "é")
    content = ("\ufefftitle  \r\n" + decomposed).encode("utf-8")

    normalized = normalize_text_bytes("docs/example.md", content)

    assert normalized == "title\né\n".encode()
    assert scan_text_bytes("docs/example.md", normalized) == []


def test_windows_script_crlf_matches_git_and_editor_contracts() -> None:
    content = b"Write-Host ok\r\n"

    assert normalize_text_bytes("run_windows.ps1", content) == content
    assert scan_text_bytes("run_windows.ps1", content) == []
    assert [issue.code for issue in scan_text_bytes("app/main.py", content)] == [
        "crlf"
    ]


def test_text_scanner_rejects_invalid_utf8_but_ignores_declared_binary() -> None:
    assert [issue.code for issue in scan_text_bytes("config/settings.yaml", b"\xff\xfe")] == [
        "invalid-utf8"
    ]
    assert scan_text_bytes("assets/logo.png", b"\x89PNG\r\n\x1a\n\xff") == []


def test_path_scanner_reports_cross_platform_collisions_and_invalid_names() -> None:
    decomposed = unicodedata.normalize("NFD", "é")
    issues = scan_path_set(
        [
            "app/Router.py",
            "app/router.py",
            f"docs/{decomposed}.md",
            "config/CON.yaml",
        ]
    )

    codes = {issue.code for issue in issues}

    assert codes == {"case-path-collision", "non-nfc-path", "windows-reserved-name"}


def test_git_scanner_keeps_head_and_worktree_sources_separate(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=tmp_path,
        check=True,
    )
    tracked = tmp_path / "tracked.md"
    tracked.write_bytes(b"\xef\xbb\xbfHEAD\n")
    subprocess.run(["git", "add", "tracked.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=tmp_path, check=True)
    tracked.write_text("clean worktree\n", encoding="utf-8", newline="\n")

    head_codes = {issue.code for issue in scan_git_repository(tmp_path, source="head")}
    worktree_codes = {
        issue.code for issue in scan_git_repository(tmp_path, source="worktree")
    }

    assert head_codes == {"unexpected-bom"}
    assert worktree_codes == set()


def test_cli_scans_staged_index_and_returns_json_failure(
    tmp_path: Path,
    capsys,
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=tmp_path,
        check=True,
    )
    tracked = tmp_path / "tracked.md"
    tracked.write_text("clean\n", encoding="utf-8", newline="\n")
    subprocess.run(["git", "add", "tracked.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=tmp_path, check=True)
    tracked.write_bytes(b"\xef\xbb\xbfSTAGED\n")
    subprocess.run(["git", "add", "tracked.md"], cwd=tmp_path, check=True)
    tracked.write_text("clean worktree\n", encoding="utf-8", newline="\n")

    exit_code = conventions_main(
        [str(tmp_path), "--source", "index", "--format", "json"]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["source"] == "index"
    assert output["issue_count"] == 1
    assert output["issues"][0]["code"] == "unexpected-bom"


def test_shadow_agent_profiles_are_retired_from_active_policy() -> None:
    retired = (
        "config/agent_profile.yaml",
        "config/codex_profile.yaml",
        "workspace/configuration/CODEX.md",
    )
    for relative in retired:
        assert not (ROOT / relative).exists(), relative

    active_policy = "\n".join(
        (ROOT / relative).read_text(encoding="utf-8")
        for relative in (
            "AGENTS.md",
            "workspace/README.md",
            "workspace/configuration/README.md",
        )
    )
    for relative in retired:
        assert relative not in active_policy
    assert "CODEX" not in active_policy

    for relative in (
        "workspace/intake/006_agent_configuration_pack.md",
        "workspace/intake/007_codex_configuration_pack.md",
    ):
        history = (ROOT / relative).read_text(encoding="utf-8")
        assert "Status: superseded" in history


def test_repository_convention_gates_are_wired() -> None:
    editorconfig = (ROOT / ".editorconfig").read_text(encoding="utf-8")
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    pre_commit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "charset = utf-8" in editorconfig
    assert "end_of_line = lf" in editorconfig
    assert "insert_final_newline = true" in editorconfig
    assert "* text=auto eol=lf" in attributes
    assert "*.png binary" in attributes
    assert "check_repository_conventions.py --source index" in pre_commit
    assert '"pre-commit>=' in pyproject
    assert "check_repository_conventions.py --source head" in ci


def test_workspace_upload_runtime_dependency_is_declared() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"python-multipart>=' in pyproject
    assert "python-multipart>=0.0.20" in project["dependency-groups"]["ci"]
