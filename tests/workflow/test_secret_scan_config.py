"""The secret-scan absorption must stay narrow, pinned and actually wired.

`gitleaks` (MIT, v8.30.1) is absorbed as a pinned, checksum-verified CI step with a
`.gitleaks.toml` allowlist. The danger of an allowlist is the opposite of a missed
secret: a broad one (a whole source tree) silently turns the scanner off. These
tests pin the narrow shape rather than trust the file to stay that way.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / ".gitleaks.toml"
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"
PINNED_VERSION = "8.30.1"


def config() -> dict:
    return tomllib.loads(CONFIG.read_text(encoding="utf-8"))


def job_section(name: str, following: str) -> str:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    start = workflow.index(f"  {name}:")
    end = workflow.index(f"  {following}:", start)
    return workflow[start:end]


def test_the_default_ruleset_is_kept() -> None:
    assert config()["extend"]["useDefault"] is True, (
        "turning the default ruleset off would replace a broad scanner with only this repo's rules"
    )


def test_the_allowlist_names_values_not_whole_source_trees() -> None:
    allowlists = config()["allowlists"]
    regexes = [pattern for entry in allowlists for pattern in entry.get("regexes", [])]
    paths = [pattern for entry in allowlists for pattern in entry.get("paths", [])]

    assert len(regexes) >= 5, "the known test-fixture credentials must be named explicitly"
    # Every allowlisted value is a specific literal, never a wildcard that matches anything.
    assert all(len(pattern) >= 12 and ".*" not in pattern for pattern in regexes)
    # No allowlisted path is a source tree: only generated/vendored locations may be skipped.
    for pattern in paths:
        assert not pattern.strip("^$").startswith(("tests", "crates", "app", "services", "shared", "scripts")), (
            f"allowing {pattern!r} would stop the scanner from ever reading a source tree"
        )


def test_the_ci_step_is_pinned_verified_and_uses_this_config() -> None:
    security = job_section("security-targeted", "py-compat")

    assert "gitleaks" in security
    assert f"version={PINNED_VERSION}" in security, "the absorbed revision must be pinned"
    assert "--config .gitleaks.toml" in security, "the reviewable allowlist must be the one used"
    assert "sha256sum -c -" in security, "the downloaded scanner must be verified against upstream checksums"
