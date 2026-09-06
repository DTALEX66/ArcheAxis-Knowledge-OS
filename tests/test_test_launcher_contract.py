"""Shell entrypoints share the behavior-tested Python development resolver."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_both_shells_use_the_shared_resolver():
    for filename in ("run_tests.sh", "run_tests.ps1"):
        launcher = (ROOT / "scripts/ci" / filename).read_text(encoding="utf-8")
        assert "scripts/runtime/dev.py" in launcher
        assert ".hermes" not in launcher
        assert "ARCHEAXIS_PYTHON" in launcher


def test_bash_entrypoint_has_no_windows_only_pwd():
    launcher = (ROOT / "scripts/ci/run_tests.sh").read_text(encoding="utf-8")
    assert "pwd -W" not in launcher
