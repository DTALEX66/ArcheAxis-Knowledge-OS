"""已应用manifest合同的真实业务消费；临时镜像测试不提供引擎/许可/运行资格。"""
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts/contracts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("details", SCRIPTS / "generate_capability_package_details.py")
DETAILS = importlib.util.module_from_spec(spec)
spec.loader.exec_module(DETAILS)


@pytest.fixture
def local(tmp_path):
    for source in DETAILS.build(ROOT)["sources"]:
        name = source["path"]
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    return tmp_path


def mutate(root, change):
    path = root / DETAILS.BUILTIN_MANIFEST
    manifest = json.loads(path.read_text(encoding="utf-8"))
    change(manifest)
    path.write_text(json.dumps(manifest), encoding="utf-8")


def test_actual_builtin_bytes_are_consumed_as_identity_only():
    data = DETAILS.build(ROOT)
    row = data["entries"][0]
    assert row["identity"]["sha256"] == hashlib.sha256((ROOT / DETAILS.BUILTIN_MANIFEST).read_bytes()).hexdigest()
    assert row["manifest"]["package_id"] == "archeaxis.pdf-extract"
    assert row["manifest"]["capability_ids"] == ["CAP-0020"]
    assert row["manifest"]["resource_keys"] == ["pymupdf"]
    assert row["manifest"]["license"] == {"expression": None, "review": "UNVERIFIED", "notice_refs": []}
    assert row["source_authenticity"] == "UNVERIFIED"
    assert row["qualification"] == row["runtime"] == "UNKNOWN"
    assert row["manifest"]["permissions"]["grants_execution"] is False
    assert "installed" not in row
    for source in data["sources"]:
        assert source["sha256"] == hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest()


@pytest.mark.parametrize("change,code", [
    (lambda m: m["capability_ids"].append("CAP-9999"), "MANIFEST_SCHEMA_REJECTED"),
    (lambda m: m["resource_keys"].append("unknown-donor"), "MANIFEST_CATALOG_REFERENCE_UNKNOWN"),
    (lambda m: m["compatibility"]["host_versions"].update(minimum="9.0.0", maximum_exclusive="10.0.0"), "MANIFEST_HOST_INCOMPATIBLE"),
    (lambda m: m["inputs"][0]["contract"].update(sha256="0" * 64), "MANIFEST_SOURCE_DRIFT"),
    (lambda m: m.update(capability_ids=["CAP-0090"], runtime_capabilities=[]), "MANIFEST_PROJECTION_CATALOG_JOIN_UNCONFIRMED"),
    (lambda m: m.update(runtime_capabilities=[]), "MANIFEST_PROJECTION_ROUTE_JOIN_UNCONFIRMED"),
], ids=["unknown-cap", "unknown-key", "host-incompatible", "source-hash-drift", "wrong-cap-join", "wrong-route-join"])
def test_unverified_or_mismatched_declarations_do_not_generate_fallback(local, change, code):
    mutate(local, change)
    with pytest.raises(DETAILS.ManifestValidationError, match="^" + code + "$"):
        DETAILS.generate(local)


def test_changed_raw_bytes_change_identity_even_for_same_declaration(local):
    before = DETAILS.build(local)["entries"][0]["identity"]
    path = local / DETAILS.BUILTIN_MANIFEST
    path.write_bytes(path.read_bytes() + b" ")
    after = DETAILS.build(local)["entries"][0]["identity"]
    assert before["sha256"] != after["sha256"]
    assert before["version"] == after["version"]


def test_missing_manifest_does_not_invent_identity(local):
    (local / DETAILS.BUILTIN_MANIFEST).unlink()
    with pytest.raises(DETAILS.ManifestValidationError, match="^MANIFEST_PROJECTION_SOURCE_UNAVAILABLE$"):
        DETAILS.build(local)


def test_cli_check_blocks_old_generated_projection_on_manifest_drift(local):
    target = local / DETAILS.TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(DETAILS.generate(local), encoding="utf-8")
    command = [sys.executable, "-B", str(SCRIPTS / "generate_capability_package_details.py"), "--root", str(local), "--check"]
    assert subprocess.run(command, capture_output=True).returncode == 0
    before = target.read_bytes()
    (local / DETAILS.BUILTIN_MANIFEST).write_bytes((local / DETAILS.BUILTIN_MANIFEST).read_bytes() + b" ")
    result = subprocess.run(command, capture_output=True)
    assert result.returncode != 0
    assert result.stderr.strip() == b"MANIFEST_PROJECTION_CHECK_FAILED"
    assert result.stdout == b""
    assert target.read_bytes() == before  # 保全旧字节，但门禁拒绝继续启动/构建。


def test_node_guard_source_identity_is_bound_in_projection(local):
    name = "scripts/contracts/check_capability_package_details.mjs"
    original = DETAILS.generate(local)
    source = local / name
    before = source.read_bytes()
    assert {"path": name, "sha256": hashlib.sha256(before).hexdigest()} in DETAILS.build(local)["sources"]
    source.write_bytes(before + b"\n// synthetic changed guard\n")
    assert DETAILS.generate(local) != original
