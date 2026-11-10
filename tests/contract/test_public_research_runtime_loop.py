"""Offline launch and consent guards for the public-research runtime probe."""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scripts/probes/aaos_public_research_runtime_loop.py"


def test_probe_requires_explicit_network_and_backup_for_restore():
    base = [sys.executable, str(PROBE), "--core-exe", "nonexistent-core", "--public-query", "public words"]
    denied = subprocess.run(base, capture_output=True, text=True, timeout=15, check=False)
    assert denied.returncode != 0 and "no request has been sent" in denied.stderr
    no_backup = subprocess.run([*base, "--public-network", "--restore"],
        capture_output=True, text=True, timeout=15, check=False)
    assert no_backup.returncode != 0 and "--restore requires --backup" in no_backup.stderr


def test_admission_fixture_uses_a_selected_family_in_subset_runs():
    from scripts.probes import aaos_public_research_runtime_loop as probe

    def material(family):
        return {"id": family, "reference": {"kind": "source", "source_id": "source-" + family}}

    assert probe.admission_material([material("community")]) == ("community", "source-community")
    assert probe.admission_material([material("encyclopedia")]) == ("encyclopedia", "source-encyclopedia")
    assert probe.admission_material([material("community"), material("research")]) == ("research", "source-research")
    with pytest.raises(ValueError, match="no selected family"):
        probe.admission_material([material("community_raw")])


def test_backup_object_verification_handles_long_local_paths(tmp_path):
    from scripts.probes import aaos01_office_runtime_loop as office
    from scripts.probes import aaos_public_research_runtime_loop as probe

    launcher = office.load("public_probe_path_test_launcher", ROOT / "scripts/release/backend_launcher.py")
    folder = tmp_path / ("a" * 100) / ("b" * 70)
    launcher.filesystem_path(folder).mkdir(parents=True)
    backup = folder / "fixture.sqlite"
    backup_bytes, object_bytes = b"synthetic backup", b"synthetic public source"
    launcher.filesystem_path(backup).write_bytes(backup_bytes)
    object_dir = Path(str(backup) + ".objects")
    launcher.filesystem_path(object_dir).mkdir()
    digest = hashlib.sha256(object_bytes).hexdigest()
    source = object_dir / digest
    launcher.filesystem_path(source).write_bytes(object_bytes)
    if os.name == "nt":
        assert len(str(source)) > 260
    probe.verify_backup_objects(backup, object_dir, [digest], hashlib.sha256(backup_bytes).hexdigest(),
                                launcher.filesystem_path)


@pytest.mark.skipif(not os.environ.get("AAOS_TEST_CORE_EXE"), reason="explicit real Core binary required")
def test_source_core_launch_registers_public_worker_without_search(tmp_path):
    from scripts.probes import aaos01_office_runtime_loop as office
    from scripts.probes import aaos_public_research_runtime_loop as probe

    launcher = office.load("public_probe_test_launcher", ROOT / "scripts/release/backend_launcher.py")
    client = office.load("public_probe_test_client", ROOT / "shared/core_client.py")
    exe = Path(os.environ["AAOS_TEST_CORE_EXE"]).resolve(strict=True)
    child, base, token, worker = probe.source_core_start(exe, tmp_path, launcher)
    records = []
    try:
        assert any(route["capability"] == "research.public" for route in worker["routes"])
        status, response = client.call(base, "GET", "/api/v1/capabilities/research.public", token)
        assert status == 200, response
    finally:
        probe.stop_owned(child, launcher, records)
    assert len(records) == 1 and records[0]["wait_reaped"] is True
