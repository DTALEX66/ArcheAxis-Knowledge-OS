"""The recovery shell must never collide with the canonical product installer."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_recovery_shell_has_distinct_identity_and_no_release_bundle():
    primary = json.loads((ROOT / "src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
    recovery = json.loads(
        (ROOT / "desktop/src-tauri/tauri.conf.json").read_text(encoding="utf-8")
    )

    assert primary["productName"] == "ArcheAxis Knowledge"
    assert primary["identifier"] == "com.archeaxis.workspace"
    assert primary["bundle"]["active"] is True
    assert recovery["productName"] == "ArcheAxis Knowledge Recovery"
    assert recovery["identifier"] == "com.archeaxis.workspace.recovery"
    assert recovery["bundle"]["active"] is False
    assert primary["identifier"] != recovery["identifier"]


def load_probe(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts/probes"))
    spec = importlib.util.spec_from_file_location("native_probe_test", ROOT / "scripts/probes/aaos01_tauri_webdriver_loop.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("tamper", [None, "epoch", "revision", "state", "confirmation"])
def test_restored_journal_requires_explicit_ui_decision_and_exact_readback(monkeypatch, tamper):
    """SYNTHETIC helper regression; does not qualify an installed runtime."""
    import copy
    probe = load_probe(monkeypatch)
    candidates = {"drafts": {}, "opened_documents": ["owned-note"], "active_document": "owned-note",
                  "page_id": "03", "pending_original": None}
    before = {"schema": "archeaxis.ui-working-state/v1", "workspace_id": "owned-workspace",
              "restore_epoch": "new-restore", "state_revision": 7,
              "recovery_requires_confirmation": True, "recovery_candidates": candidates}
    after = {**copy.deepcopy(before), "state_revision": 8, "state": copy.deepcopy(candidates),
             "recovery_requires_confirmation": False, "recovery_candidates": None}
    if tamper == "epoch": after["restore_epoch"] = "other"
    if tamper == "revision": after["state_revision"] = 7
    if tamper == "state": after["state"]["opened_documents"] = []
    if tamper == "confirmation": after["recovery_requires_confirmation"] = True
    calls = []
    replies = iter([before, after])
    def bridge(operation):
        calls.append(("read", operation))
        return next(replies)
    def click(label): calls.append(("click", label))
    def wait(script): calls.append(("wait", script))
    if tamper:
        with pytest.raises(AssertionError): probe.confirm_restored_working_state(bridge, click, wait)
    else:
        result = probe.confirm_restored_working_state(bridge, click, wait)
        assert result["decision"] == "EXPLICIT_UI_PRESERVE" and result["after"]["state"] == candidates
    assert [item for item in calls if item[0] != "wait"] == [
        ("read", "ui_state_read"), ("click", "保留恢复候选"), ("read", "ui_state_read")]


def test_installation_limitation_matches_the_run_it_describes(monkeypatch):
    """A receipt must not call the executable a candidate when a parent supplied the installed host.

    The literal string used to be unconditional, so the CI receipts carried a limitation that
    contradicted their own ``installation_context`` and ``host.path`` -- the installed host under
    the per-user install directory. Reading only that string is enough to conclude the journey did
    not run an installed build, which is the opposite of what the receipt records.
    """
    probe = load_probe(monkeypatch)

    local = probe.installation_limitation(None)
    assert "Candidate executable" in local

    installed = probe.installation_limitation(Path("ArcheAxis Knowledge_0.6.14_x64-setup.exe"))
    assert "Candidate executable" not in installed, (
        "a parent-supplied installed host is not a candidate executable; saying so contradicts "
        "the receipt's own installation_context"
    )
    assert "parent installer verifier" in installed


def test_native_observer_excludes_recycled_parent_pid_and_unrelated_processes(monkeypatch):
    probe = load_probe(monkeypatch)
    rows = [
        {"pid": 1, "parent_pid": 0, "created": 100},
        {"pid": 2, "parent_pid": 1, "created": 110},
        {"pid": 3, "parent_pid": 2, "created": 120},
        {"pid": 4, "parent_pid": 2, "created": 105},
        {"pid": 5, "parent_pid": 99, "created": 130},
    ]
    assert [row["pid"] for row in probe.owned_process_rows(rows, 1)] == [1, 2, 3]
    with pytest.raises(RuntimeError, match="identity unavailable"):
        probe.owned_process_rows(rows, 99)


@pytest.mark.parametrize("runtime,expected", [
    ("Edg/154.0.4258.62", True),
    ("Edg/154.0.4258.48", True),
    ("Edg/154.0.4259.48", False),
    ("Edg/153.0.4258.48", False),
    ("Edg/154.0.4258", False),
    ("Edg/154.0.4258.48 unexpected", False),
])
def test_edge_patch_update_uses_official_build_compatibility(monkeypatch, runtime, expected):
    probe = load_probe(monkeypatch)
    assert probe.compatible_edge_versions("Microsoft Edge WebDriver 154.0.4258.48 (official build)", runtime) is expected
    assert not probe.compatible_edge_versions("unverified 154.0.4258.48", runtime)


def test_description_does_not_change_exact_object_button_label(monkeypatch):
    from lxml import etree
    probe = load_probe(monkeypatch)
    tree = etree.HTML("<ul aria-label='资料库对象导航'><li><button><b>来源锚点</b><small>绑定原件版本的引用记录</small></button></li><li><button><b>来源锚点副本</b><small>来源锚点</small></button></li></ul>")
    scope = "//ul[@aria-label='资料库对象导航']"
    assert not tree.xpath(f"{scope}//button[normalize-space(.)='来源锚点']")
    found = tree.xpath(probe.navigation_button_selector("来源锚点", scope))
    assert len(found) == 1 and found[0].find("b").text == "来源锚点"
    assert probe.navigation_button_selector("保存") == "//button[normalize-space(.)='保存']"


def test_native_profile_observer_does_not_read_profile_contents(monkeypatch, tmp_path):
    probe = load_probe(monkeypatch)
    profile = tmp_path / "profile"
    (profile / "EBWebView").mkdir(parents=True)
    (profile / "DevToolsActivePort").write_bytes(b"not read")
    monkeypatch.setattr(Path, "read_bytes", lambda _path: pytest.fail("Profile content read"))
    monkeypatch.setattr(Path, "read_text", lambda _path, **_kwargs: pytest.fail("Profile content read"))
    assert probe.profile_metadata([profile])[0] == {
        "path": str(profile), "exists": True, "ebwebview_exists": True,
        "devtools_active_port_exists": True, "ebwebview_devtools_active_port_exists": False,
    }


@pytest.mark.skipif(os.name != "nt", reason="Win32 process metadata API")
def test_native_process_observer_reads_current_owned_identity(monkeypatch):
    probe = load_probe(monkeypatch)
    rows = probe.native_process_rows()
    owned = probe.owned_process_rows(rows, os.getpid())
    assert any(row["pid"] == os.getpid() and row["created"] > 0 for row in owned)
    assert all(set(row) == {"pid", "parent_pid", "name", "created"} for row in owned)
    elevation = probe.process_elevation(os.getpid())
    assert elevation["elevation_verified"] is True
    assert isinstance(elevation["elevated"], bool)
