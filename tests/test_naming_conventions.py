from __future__ import annotations

import hashlib
import json
import subprocess
import tomllib
import unicodedata
from pathlib import Path

import pytest
import yaml

from scripts.check_repository_conventions import (
    main as conventions_main,
)
from scripts.check_repository_conventions import (
    normalize_text_bytes,
    scan_git_repository,
    scan_naming_forbidden_terms,
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

_PRESERVED_FIXTURE_HASHES = {
    "tests/fixtures/f01-quality/controlled.md": "70aff728005d7580260391e6754f30209ec5fbecd9803f30a31e48d72eb7b176",
    "tests/fixtures/f01-quality/capped-lines.md": "71c0029230e042d72e9ec8db74f9a28196b37fdfb29f7df7d68e3b425af38928",
    "tests/fixtures/f01-quality/fallback-gbk.txt": "8ba7ed5cd0f33c11b7bb447337b0ce852b0a4f52c5ee854b6107943408b2b215",
    "tests/fixtures/p1-quality/bom-then-non-utf8.txt": "7b8e66f5da41888eb5cdd9ba9e142df708b548040f70aa7c6e417287ca4af188",
    "tests/fixtures/p1-quality/capped-crlf.txt": "9a9af8502c625be793d85c664d7b2c728dc5052b4f60b73e059416118c6a310a",
    "tests/fixtures/p1-quality/fallback-gbk-markdown.md": "8b593c1ffc2e113962d12485f54b381af29c4ae029b8c2e98c762d686138e6b7",
    "tests/fixtures/p1-quality/one-long-line.txt": "d9785ad494215a183ceaf55c11aeed1433227e88469f61159f2daf27e6929100",
}
_PRESERVED_HISTORICAL_REPORT_HASHES = {
    "docs/current/dsh-review/branch-batch-03.md": "def1136dd39c48db9a04cf149fccee2a6744d64a5053ef3ffb498b50eeb1d959",
    "docs/current/dsh-review/branch-batch-03.json": "1d3d6ba80319d4445c771f54802cb46c4c6ed74bdcd662338e74324078d6ff53",
}


@pytest.mark.parametrize("path,expected_hash", _PRESERVED_FIXTURE_HASHES.items())
def test_intentional_raw_quality_fixtures_are_hash_pinned(path: str, expected_hash: str) -> None:
    content = (ROOT / path).read_bytes()
    assert hashlib.sha256(content).hexdigest() == expected_hash
    assert scan_text_bytes(path, content) == []
    assert [issue.code for issue in scan_text_bytes(path, content + b" ")] == [
        "preserved-fixture-mismatch"
    ]


@pytest.mark.parametrize("path,expected_hash", _PRESERVED_HISTORICAL_REPORT_HASHES.items())
def test_historical_branch_audit_names_are_hash_pinned(path: str, expected_hash: str) -> None:
    content = (ROOT / path).read_bytes()
    assert hashlib.sha256(content).hexdigest() == expected_hash
    assert scan_naming_forbidden_terms(path, content) == []
    assert [issue.code for issue in scan_naming_forbidden_terms(path, content + b" ")] == [
        "historical-report-mismatch"
    ]


@pytest.mark.parametrize('path', [
    'docs/authority/taskpack-0910-r3/MANIFEST.json',
    'docs/authority/taskpack-0910-r3/TASKS.json',
    *[f'docs/authority/taskpack-0912-r5/{prefix}research-v15/{name}.json'
      for prefix in ('', 'frozen-r4/')
      for name in ('学科数据', '方法数据', '研究数据', '资源数据')],
])
def test_frozen_original_bytes_are_preserved_and_mutations_rejected(path):
    original = (ROOT / path).read_bytes()
    assert scan_text_bytes(path, original) == []
    assert 'missing-final-newline' in {
        issue.code for issue in scan_text_bytes(f'docs/copied/{Path(path).name}', original)
    }
    for changed in (original + b'\n', original.replace(b'{', b'{ ', 1)):
        assert 'frozen-original-mismatch' in {
            issue.code for issue in scan_text_bytes(path, changed)
        }


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


def test_product_naming_contract_v2_has_one_default_display_identity() -> None:
    registry = yaml.safe_load(
        (ROOT / "config" / "product-naming-registry.yaml").read_text(encoding="utf-8")
    )
    product = registry["product"]
    assert product["name"] == {
        "en-US": "ArcheAxis Knowledge",
        "zh-CN": "星环知识平台",
        "class": "display",
    }
    assert registry["rules"]["default_ui_product_name"] == "ArcheAxis Knowledge"
    assert "元枢·观心" in registry["forbidden_default_terms"]
    assert "ArcheAxis Workspace" in [
        d["value"] for d in product["deprecated_display"]
    ]

    ui = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "ArcheAxis Knowledge" in ui
    assert "星环知识平台" in ui
    assert "元枢工作台" not in ui
    assert "元枢·观心" not in ui
    assert "全局命令入口尚未接入" not in ui


def test_forbidden_terms_reject_legacy_name_in_active_doc() -> None:
    issues = scan_naming_forbidden_terms(
        "docs/current/CURRENT_PRODUCT_PLAN_V2.md",
        "当前计划：元枢工作台 是主产品。".encode(),
    )
    assert any(i.code == "legacy-product-name" for i in issues)


def test_forbidden_terms_allow_legacy_context_docs() -> None:
    issues = scan_naming_forbidden_terms(
        "docs/current/CURRENT_PRODUCT_PLAN_V2.md",
        "迁移说明：旧名元枢工作台 仅在 Legacy 语境出现。".encode(),
    )
    assert not [i for i in issues if i.code == "legacy-product-name"]


def test_forbidden_terms_allow_generated_audit_receipts() -> None:
    """Generated branch/lineage audit receipts quote historical commits verbatim.

    They are evidence, so retired product names inside them are expected and must
    not be flagged; rewriting the receipt would falsify the audit.
    """
    receipt = json.dumps(
        {
            "schema_version": "aaos-branch-commit-path-audit/v1",
            "generated_at": "2026-09-25T09:04:15Z",
            "records": [{"subject": "feat: ArcheAxis OS rename and ArcheAxis Workspace sweep"}],
        }
    ).encode()
    assert not [
        i
        for i in scan_naming_forbidden_terms(
            "docs/current/AAOS-BRANCH-COMMIT-PATH-AUDIT-20260925.json", receipt
        )
        if i.code == "legacy-product-name"
    ]


def test_forbidden_terms_still_reject_that_text_without_the_receipt_schema() -> None:
    """The audit-receipt exemption is keyed on the declared schema, not the path."""
    same_text_without_schema = json.dumps(
        {"records": [{"subject": "feat: ArcheAxis OS rename"}]}
    ).encode()
    issues = scan_naming_forbidden_terms(
        "docs/current/AAOS-BRANCH-COMMIT-PATH-AUDIT-20260925.json",
        same_text_without_schema,
    )
    assert any(i.code == "legacy-product-name" for i in issues)


def test_forbidden_terms_skip_historical_surfaces() -> None:
    issues = scan_naming_forbidden_terms(
        "workspace/intake/2026-07-01-note.md",
        "当时产品名：元枢工作台。".encode(),
    )
    assert not [i for i in issues if i.code == "legacy-product-name"]


def test_forbidden_terms_skip_non_active_paths() -> None:
    issues = scan_naming_forbidden_terms(
        "knowledge_base/readme.md",
        "元枢工作台 相关。".encode(),
    )
    assert not [i for i in issues if i.code == "legacy-product-name"]
