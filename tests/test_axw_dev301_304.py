"""AXW-DEV-301..304 — external-dev hot reload: watcher, supervisor, clone.

Covers:

* ``app/workspace/hotreload.py`` — mtime polling detects *.py changes and
  invokes the callback; ignore rules (``.git/.venv/.project-local/__pycache__/
  node_modules``) never fire; bounded ``last_events`` ring buffer;
  fail-closed start (only external-dev + reload:true + source_root dir).
* ``BackendSupervisor`` reload semantics — request_reload()/reload() are
  gated (fail-closed for non-external-dev or reload:false, state never
  moves), the READY→RECONNECTING→READY cycle increments reload_count and
  sets last_reload_at, and /api/v1/system/status exposes the reload block.
* ``app/workspace/test_workspace.py`` — clone_test_workspace copies real
  domain files + manifest, regenerates workspace_id (uuid4), preserves
  data_ownership, and refuses an existing destination (fail-closed).

Assertions on watcher timing use polling loops (``_wait_until``), never
bare sleeps.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.workspace.hotreload import HotReloadWatcher
from app.workspace.supervisor import BackendSupervisor, BackendSupervisorState
from app.workspace.test_workspace import clone_test_workspace
from shared.runtime_profile import RuntimeProfile
from shared.workspace_manifest import ASSET_DOMAINS, create_workspace

EXTERNAL_DEV = RuntimeProfile(
    name="external-dev",
    backend="external-source",
    data_policy="isolated-test-workspace",
    reload=True,
    source_root=None,
)

INSTALLED_STABLE = RuntimeProfile(
    name="installed-stable",
    backend="bundled",
    data_policy="installed-user-data",
    reload=False,
    source_root=None,
)

EXTERNAL_DEV_NO_RELOAD = RuntimeProfile(
    name="external-dev",
    backend="external-source",
    data_policy="isolated-test-workspace",
    reload=False,
    source_root=None,
)


def _external_profile(root: Path) -> RuntimeProfile:
    return RuntimeProfile(
        name="external-dev",
        backend="external-source",
        data_policy="isolated-test-workspace",
        reload=True,
        source_root=str(root),
    )


def _wait_until(predicate, timeout: float = 5.0, step: float = 0.05) -> bool:
    """Poll ``predicate`` until true or the deadline passes (no bare sleeps)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(step)
    return predicate()


# ── AXW-DEV-301: hot reload watcher ────────────────────────────────────


def test_watcher_detects_py_changes_and_invokes_callback(tmp_path: Path) -> None:
    changed: list[list[Path]] = []
    watcher = HotReloadWatcher(
        profile=_external_profile(tmp_path), callback=changed.append, interval=0.05
    )
    handle = watcher.start()
    assert isinstance(handle, threading.Thread)
    assert handle.is_alive()
    try:
        target = tmp_path / "backend_mod.py"
        target.write_text("VALUE = 1\n", encoding="utf-8")
        assert _wait_until(lambda: bool(watcher.last_events))
        assert watcher.last_events[-1]["event"] == "created"
        assert watcher.last_events[-1]["path"] == str(target)
        assert changed == [[target]]

        target.write_text("VALUE = 22\n", encoding="utf-8")
        assert _wait_until(
            lambda: any(event["event"] == "modified" for event in watcher.last_events)
        )
        assert len(changed) == 2

        target.unlink()
        assert _wait_until(
            lambda: any(event["event"] == "deleted" for event in watcher.last_events)
        )
    finally:
        watcher.stop()
    assert not handle.is_alive()


@pytest.mark.parametrize(
    "ignored_dir", [".git", ".venv", ".project-local", "__pycache__", "node_modules"]
)
def test_watcher_ignores_standard_dirs(tmp_path: Path, ignored_dir: str) -> None:
    changed: list[list[Path]] = []
    watcher = HotReloadWatcher(
        profile=_external_profile(tmp_path), callback=changed.append, interval=0.05
    )
    watcher.start()
    try:
        nested = tmp_path / ignored_dir / "sub"
        nested.mkdir(parents=True)
        (nested / "ignored.py").write_text("x = 1\n", encoding="utf-8")
        # Poll for several cycles: the watcher must never fire for ignored dirs.
        assert not _wait_until(lambda: bool(watcher.last_events), timeout=0.4)
        assert changed == []
    finally:
        watcher.stop()


def test_watcher_ignores_non_python_files(tmp_path: Path) -> None:
    changed: list[list[Path]] = []
    watcher = HotReloadWatcher(
        profile=_external_profile(tmp_path), callback=changed.append, interval=0.05
    )
    watcher.start()
    try:
        (tmp_path / "notes.md").write_text("# note\n", encoding="utf-8")
        (tmp_path / "app.js").write_text("console.log(1);\n", encoding="utf-8")
        assert not _wait_until(lambda: bool(watcher.last_events), timeout=0.4)
        assert changed == []
    finally:
        watcher.stop()


def test_watcher_start_fails_closed_for_wrong_profile(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="external-dev"):
        HotReloadWatcher(
            profile=INSTALLED_STABLE, callback=lambda paths: None, interval=0.05
        )
    with pytest.raises(ValueError, match="external-dev"):
        HotReloadWatcher(
            profile=EXTERNAL_DEV_NO_RELOAD, callback=lambda paths: None, interval=0.05
        )
    with pytest.raises(ValueError, match="source_root"):
        HotReloadWatcher(profile=EXTERNAL_DEV, callback=lambda paths: None)
    with pytest.raises(ValueError, match="not a directory"):
        HotReloadWatcher(
            profile=_external_profile(tmp_path / "missing"), callback=lambda paths: None
        )


def test_watcher_refuses_double_start(tmp_path: Path) -> None:
    watcher = HotReloadWatcher(
        profile=_external_profile(tmp_path), callback=lambda paths: None, interval=0.05
    )
    watcher.start()
    try:
        with pytest.raises(ValueError, match="already running"):
            watcher.start()
    finally:
        watcher.stop()


def test_watcher_last_events_ring_buffer_capped(tmp_path: Path) -> None:
    watcher = HotReloadWatcher(
        profile=_external_profile(tmp_path), callback=lambda paths: None, interval=1.0
    )
    assert watcher.last_events.maxlen == 50
    for index in range(60):
        watcher._record(tmp_path / f"f{index}.py", "created")
    assert len(watcher.last_events) == 50
    assert watcher.last_events[-1]["path"].endswith("f59.py")


def test_module_level_start_stop_returns_thread(tmp_path: Path) -> None:
    from app.workspace import hotreload

    profile = _external_profile(tmp_path)
    handle = hotreload.start(profile, callback=lambda paths: None, interval=0.05)
    assert isinstance(handle, threading.Thread)
    assert handle.is_alive()
    assert hotreload.last_events.maxlen == 50
    try:
        (tmp_path / "mod.py").write_text("x = 1\n", encoding="utf-8")
        assert _wait_until(lambda: bool(hotreload.last_events))
    finally:
        hotreload.stop()
    assert not handle.is_alive()


# ── AXW-DEV-301: supervisor reload semantics ───────────────────────────


@pytest.mark.parametrize(
    "profile", [None, INSTALLED_STABLE, EXTERNAL_DEV_NO_RELOAD]
)
def test_reload_fails_closed_for_non_external_dev_or_reload_disabled(
    profile: RuntimeProfile | None,
) -> None:
    supervisor = BackendSupervisor(profile=profile)
    supervisor.start()
    assert supervisor.state is BackendSupervisorState.READY
    with pytest.raises(ValueError, match="hot reload requires external-dev"):
        supervisor.request_reload()
    with pytest.raises(ValueError, match="hot reload requires external-dev"):
        supervisor.reload()
    # fail-closed: state never moved, counters untouched
    assert supervisor.state is BackendSupervisorState.READY
    reload_status = supervisor.status()["reload"]
    assert reload_status["enabled"] is False
    assert reload_status["reload_count"] == 0
    assert reload_status["last_reload_at"] is None


def test_request_reload_cycles_ready_and_increments_count() -> None:
    supervisor = BackendSupervisor(profile=EXTERNAL_DEV, reload_interval_ms=250)
    supervisor.start()
    supervisor.request_reload([Path("src/app.py"), Path("src/util.py")])
    assert supervisor.state is BackendSupervisorState.READY
    tail = supervisor.events()[-2:]
    assert tail[0]["from"] == "ready" and tail[0]["to"] == "reconnecting"
    assert tail[1]["from"] == "reconnecting" and tail[1]["to"] == "ready"
    reload_status = supervisor.status()["reload"]
    assert reload_status["enabled"] is True
    assert reload_status["interval_ms"] == 250
    assert reload_status["reload_count"] == 1
    assert reload_status["last_reload_at"] is not None

    supervisor.reload()
    assert supervisor.status()["reload"]["reload_count"] == 2
    assert supervisor.state is BackendSupervisorState.READY


def test_reload_requires_running_and_ready() -> None:
    supervisor = BackendSupervisor(profile=EXTERNAL_DEV)
    with pytest.raises(ValueError, match="not running"):
        supervisor.request_reload()
    supervisor.start()
    supervisor.fail("boom")
    assert supervisor.state is BackendSupervisorState.FAILED
    with pytest.raises(ValueError, match="cannot hot-reload from state failed"):
        supervisor.request_reload()
    assert supervisor.state is BackendSupervisorState.FAILED
    assert supervisor.status()["reload"]["reload_count"] == 0


def test_set_profile_enables_hot_reload() -> None:
    supervisor = BackendSupervisor()
    supervisor.start()
    with pytest.raises(ValueError, match="hot reload requires external-dev"):
        supervisor.request_reload()
    supervisor.set_profile(EXTERNAL_DEV, reload_interval_ms=500)
    supervisor.request_reload()
    reload_status = supervisor.status()["reload"]
    assert reload_status["enabled"] is True
    assert reload_status["interval_ms"] == 500
    assert reload_status["reload_count"] == 1


def test_watcher_triggers_supervisor_request_reload(tmp_path: Path) -> None:
    supervisor = BackendSupervisor(profile=_external_profile(tmp_path))
    supervisor.start()
    watcher = HotReloadWatcher(
        profile=_external_profile(tmp_path), callback=supervisor.request_reload, interval=0.05
    )
    watcher.start()
    try:
        (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
        assert _wait_until(
            lambda: supervisor.status()["reload"]["reload_count"] >= 1, timeout=5.0
        )
        assert supervisor.state is BackendSupervisorState.READY
    finally:
        watcher.stop()


# ── AXW-DEV-301: /api/v1/system/status reload block ────────────────────


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ARCHEAXIS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("ARCHEAXIS_RUNTIME_PROFILE", raising=False)
    import app.workspace.system as system_module

    monkeypatch.setattr(system_module, "supervisor", BackendSupervisor(profile=EXTERNAL_DEV))
    from app.main import app

    return TestClient(app)


def test_status_endpoint_reports_reload_block(client: TestClient) -> None:
    import app.workspace.system as system_module

    response = client.get("/api/v1/system/status")
    assert response.status_code == 200, response.text
    reload_status = response.json()["reload"]
    # enabled reflects the bound external-dev profile, even before start
    assert reload_status == {
        "enabled": True,
        "interval_ms": 1000,
        "reload_count": 0,
        "last_reload_at": None,
    }
    system_module.supervisor.start()
    system_module.supervisor.request_reload()
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200, response.text
    reload_status = response.json()["reload"]
    assert reload_status["enabled"] is True
    assert reload_status["reload_count"] == 1
    assert reload_status["last_reload_at"] is not None


def test_status_endpoint_reload_disabled_without_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARCHEAXIS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("ARCHEAXIS_RUNTIME_PROFILE", raising=False)
    import app.workspace.system as system_module

    monkeypatch.setattr(system_module, "supervisor", BackendSupervisor())
    from app.main import app

    response = TestClient(app).get("/api/v1/system/status")
    assert response.status_code == 200, response.text
    assert response.json()["reload"]["enabled"] is False


def test_restart_endpoint_still_works_for_manual_reload(client: TestClient) -> None:
    import app.workspace.system as system_module

    system_module.supervisor.start()
    response = client.post("/api/v1/system/restart")
    assert response.status_code == 202, response.text
    assert response.json()["state"] == "ready"
    assert system_module.supervisor.state is BackendSupervisorState.READY


# ── AXW-DEV-303: isolated test workspace clone ─────────────────────────


def _make_src_workspace(tmp_path: Path) -> Path:
    create_workspace(tmp_path, "src-ws")
    src_dir = tmp_path / "src-ws"
    (src_dir / "source_archive" / "note.md").write_text("real content\n", encoding="utf-8")
    (src_dir / "ai_asset_vault" / "rule.json").write_text('{"k": 1}\n', encoding="utf-8")
    return src_dir


def test_clone_copies_real_domains_and_manifest_with_new_id(tmp_path: Path) -> None:
    src_dir = _make_src_workspace(tmp_path)
    src_manifest = json.loads((src_dir / "manifest.json").read_text(encoding="utf-8"))
    dst = tmp_path / "cloned-test-ws"

    cloned = clone_test_workspace(src_dir, dst)

    assert dst.is_dir()
    for key in ASSET_DOMAINS:
        assert (dst / key).is_dir()
    assert (dst / "manifest.json").is_file()
    assert (dst / "source_archive" / "note.md").read_text(encoding="utf-8") == "real content\n"
    assert (dst / "ai_asset_vault" / "rule.json").read_text(encoding="utf-8") == '{"k": 1}\n'
    # workspace_id regenerated as a UUID4 string
    assert cloned["workspace_id"] != src_manifest["workspace_id"]
    assert UUID(cloned["workspace_id"]).version == 4
    # other manifest fields preserved, domain paths rewritten to the clone
    assert cloned["name"] == src_manifest["name"]
    assert cloned["schema_version"] == src_manifest["schema_version"]
    assert cloned["domains"]["source_archive"]["path"] == str(dst / "source_archive")
    assert cloned["domains"]["ai_asset_vault"]["path"] == str(dst / "ai_asset_vault")
    # the manifest file on disk carries the new id
    on_disk = json.loads((dst / "manifest.json").read_text(encoding="utf-8"))
    assert on_disk["workspace_id"] == cloned["workspace_id"]


def test_clone_preserves_data_ownership(tmp_path: Path) -> None:
    src_dir = _make_src_workspace(tmp_path)
    manifest_path = src_dir / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["data_ownership"] = {"declared": True, "note": "cloned test data stays isolated"}
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    cloned = clone_test_workspace(src_dir, tmp_path / "cloned-ws")

    assert cloned["data_ownership"] == data["data_ownership"]
    assert cloned["workspace_id"] != data["workspace_id"]
    on_disk = json.loads((tmp_path / "cloned-ws" / "manifest.json").read_text(encoding="utf-8"))
    assert on_disk["data_ownership"] == data["data_ownership"]


def test_clone_rejects_existing_destination(tmp_path: Path) -> None:
    src_dir = _make_src_workspace(tmp_path)
    dst = tmp_path / "dst-ws"
    clone_test_workspace(src_dir, dst)
    with pytest.raises(ValueError, match="already exists"):
        clone_test_workspace(src_dir, dst)
    # the first clone is untouched by the failed second attempt
    assert (dst / "manifest.json").is_file()


def test_clone_fails_closed_on_missing_source_or_manifest(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="source workspace not found"):
        clone_test_workspace(tmp_path / "nope", tmp_path / "dst")
    empty = tmp_path / "empty-ws"
    empty.mkdir()
    with pytest.raises(ValueError, match="no workspace manifest"):
        clone_test_workspace(empty, tmp_path / "dst")
    with pytest.raises(ValueError, match="no workspace manifest"):
        clone_test_workspace(tmp_path, tmp_path / "dst")


def test_clone_accepts_workspace_manifest_json_name(tmp_path: Path) -> None:
    src_dir = _make_src_workspace(tmp_path)
    (src_dir / "manifest.json").rename(src_dir / "workspace-manifest.json")
    dst = tmp_path / "cloned-ws"
    cloned = clone_test_workspace(src_dir, dst)
    assert (dst / "workspace-manifest.json").is_file()
    assert UUID(cloned["workspace_id"]).version == 4
