"""R15: the language boundary needs a check that can actually fail.

A gate that only ever passes proves nothing, so every ownership rule and every
cross-language agreement is exercised against a synthetic tree that breaks it.
The last test runs the same check against the real repository, which is what makes
the passing result meaningful.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "scripts" / "check_language_boundaries.py"

RUST_LIB = """pub const PROTOCOL_VERSION: u32 = 1;

pub fn request_schema() -> &'static str {
    "archeaxis.worker-request/v1"
}

pub fn response_schema() -> &'static str {
    "archeaxis.worker-response/v1"
}
"""

PY_TRANSPORT = """SCHEMA_REQUEST = "archeaxis.worker-request/v1"


def hello():
    return {"schema": "archeaxis.worker-hello/v1", "type": "hello",
            "protocol": {"major": 1, "min_minor": 0, "max_minor": 0},
            "response": "archeaxis.worker-response/v1"}
"""

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://archeaxis.local/contracts/v1/worker-protocol.schema.json",
    "$defs": {
        "hello": {
            "type": "object",
            "properties": {
                "schema": {"const": "archeaxis.worker-hello/v1"},
                "protocol": {"type": "object", "properties": {"major": {"const": 1}}},
                "response": {"const": "archeaxis.worker-response/v1"},
            },
        }
    },
}

CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Avalonia" Version="12.1.2" />
  </ItemGroup>
</Project>
"""


def _load():
    spec = importlib.util.spec_from_file_location("language_boundaries_under_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = _load()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _tree(tmp_path: Path) -> Path:
    """A minimal tree that keeps every boundary: the baseline for the negatives."""
    _write(tmp_path / "crates/archeaxis-sidecar-protocol/src/lib.rs", RUST_LIB)
    _write(tmp_path / "crates/archeaxis-store-sqlite/Cargo.toml", '[package]\nname = "s"\n\n[dependencies]\nrusqlite = "0.32"\n')
    _write(tmp_path / "services/python-workers/transport/text_ndjson.py", PY_TRANSPORT)
    _write(
        tmp_path / "packages/contracts/v1/worker-protocol.schema.json",
        json.dumps(SCHEMA, indent=2),
    )
    _write(tmp_path / "apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj", CSPROJ)
    _write(tmp_path / "apps/ArcheAxis.Desktop/Program.cs", "internal static class Program { }\n")
    return tmp_path


def test_a_boundary_respecting_tree_passes(tmp_path):
    failures, detail = check.run(_tree(tmp_path))
    assert failures == []
    assert detail["protocol_version"] == 1
    assert detail["contracts_version"] == 1
    assert detail["envelope_names"] == ["hello", "request", "response"]


def test_a_sql_driver_declared_outside_the_crates_is_refused(tmp_path):
    root = _tree(tmp_path)
    _write(root / "app/Cargo.toml", '[package]\nname = "side"\n\n[dependencies]\nrusqlite = "0.32"\n')
    failures, _ = check.run(root)
    assert len(failures) == 1
    assert "app/Cargo.toml" in failures[0]
    assert "outside crates/" in failures[0]


def test_a_worker_that_opens_the_database_is_refused(tmp_path):
    root = _tree(tmp_path)
    _write(root / "services/python-workers/document/worker_sneaky.py", "import sqlite3\n\n\ndef go():\n    return sqlite3.connect('x')\n")
    failures, _ = check.run(root)
    assert len(failures) == 1
    assert "worker_sneaky.py" in failures[0]
    assert "'sqlite3'" in failures[0]


def test_a_byte_order_mark_does_not_hide_a_violation(tmp_path):
    """Windows editors write BOMs; a line-anchored rule must still match line 1."""
    root = _tree(tmp_path)
    path = root / "services/python-workers/document/worker_bom.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xef\xbb\xbfimport sqlite3\n")
    failures, _ = check.run(root)
    assert len(failures) == 1
    assert "worker_bom.py" in failures[0]
    assert "'sqlite3'" in failures[0]


def test_a_byte_order_mark_does_not_hide_a_version_disagreement(tmp_path):
    root = _tree(tmp_path)
    path = root / "services/python-workers/vision/worker_bom.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\xef\xbb\xbfSCHEMA = "archeaxis.worker-request/v2"\n')
    failures, _ = check.run(root)
    assert any("disagree inside one language" in line for line in failures)


def test_a_worker_referencing_rusqlite_is_refused(tmp_path):
    root = _tree(tmp_path)
    _write(root / "services/python-workers/document/worker_other.py", "# rusqlite is for the Core only\n")
    failures, _ = check.run(root)
    assert len(failures) == 1
    assert "worker_other.py" in failures[0]
    assert "rusqlite" in failures[0]


def test_a_desktop_sql_client_package_is_refused(tmp_path):
    root = _tree(tmp_path)
    _write(
        root / "apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj",
        CSPROJ.replace(
            '<PackageReference Include="Avalonia" Version="12.1.2" />',
            '<PackageReference Include="Avalonia" Version="12.1.2" />\n'
            '    <PackageReference Include="Microsoft.Data.Sqlite" Version="9.0.0" />',
        ),
    )
    failures, _ = check.run(root)
    assert len(failures) == 1
    assert "ArcheAxis.Desktop.csproj" in failures[0]
    assert "sqlite" in failures[0].lower()


def test_desktop_code_opening_sql_directly_is_refused(tmp_path):
    root = _tree(tmp_path)
    _write(
        root / "apps/ArcheAxis.Desktop/CoreSupervisor.cs",
        "using Microsoft.Data.Sqlite;\n\ninternal class CoreSupervisor { }\n",
    )
    failures, _ = check.run(root)
    assert len(failures) == 1
    assert "CoreSupervisor.cs" in failures[0]
    assert "must not open SQL" in failures[0]


def test_a_python_hello_that_advertises_another_major_is_refused(tmp_path):
    root = _tree(tmp_path)
    _write(
        root / "services/python-workers/transport/text_ndjson.py",
        PY_TRANSPORT.replace('"major": 1', '"major": 2'),
    )
    failures, _ = check.run(root)
    assert any("python hello advertises major 2" in line for line in failures)


def test_a_language_that_drops_the_envelope_literal_is_refused(tmp_path):
    root = _tree(tmp_path)
    _write(root / "services/python-workers/transport/text_ndjson.py", "SCHEMA_REQUEST = 'something-else'\n")
    failures, _ = check.run(root)
    assert any("python: no archeaxis.worker-*/vN envelope literal found" in line for line in failures)


def test_two_versions_inside_one_language_are_refused(tmp_path):
    root = _tree(tmp_path)
    _write(
        root / "services/python-workers/vision/worker_ocr.py",
        'SCHEMA = "archeaxis.worker-request/v2"\n',
    )
    failures, _ = check.run(root)
    assert any("disagree inside one language" in line for line in failures)


def test_a_contract_directory_that_disagrees_with_the_protocol_version_is_refused(tmp_path):
    root = _tree(tmp_path)
    (root / "packages/contracts/v1").rename(root / "packages/contracts/v2")
    failures, _ = check.run(root)
    assert any("packages/contracts/v2 disagrees with PROTOCOL_VERSION=1" in line for line in failures)


def test_a_missing_protocol_constant_is_refused(tmp_path):
    root = _tree(tmp_path)
    _write(root / "crates/archeaxis-sidecar-protocol/src/lib.rs", 'pub fn request_schema() -> &\'static str { "archeaxis.worker-request/v1" }\n')
    failures, _ = check.run(root)
    assert any("PROTOCOL_VERSION not found" in line for line in failures)


def test_the_real_repository_keeps_its_language_boundary():
    """The synthetic negatives only matter because this tree is the real one."""
    failures, detail = check.run(REPO)
    assert failures == []
    assert detail["protocol_version"] == detail["contracts_version"] == 1
    assert detail["python_hello_major"] == detail["schema_hello_major"] == 1
    assert "hello" in detail["envelope_names"]


def _load_gate():
    spec = importlib.util.spec_from_file_location(
        "contracts_gate_under_test", REPO / "scripts" / "ci" / "check_vnext_contracts.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_contracts_vnext_gate_runs_the_boundary_check(capsys):
    """The CI job that runs this script must now enforce the boundary too."""
    gate = _load_gate()
    assert gate.main() == 0
    printed = capsys.readouterr().out
    assert "contracts-vnext check passed" in printed
    assert "language boundary agrees on protocol major 1" in printed


def test_the_contracts_vnext_gate_surfaces_a_boundary_failure(tmp_path):
    gate = _load_gate()
    root = _tree(tmp_path)
    _write(root / "services/python-workers/document/worker_sneaky.py", "import sqlite3\n")
    gate.ROOT = root
    failures, detail = gate.language_boundary_result()
    assert any("worker_sneaky.py" in line for line in failures)
    assert detail["root"] == str(root)
