"""Synthetic contract tests. No Tauri, Core, installer or model is executed."""
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.release import local_pinned_packaging as local


def put(path, content=b"synthetic"):
    os.makedirs(local.portable.native(path.parent), exist_ok=True)
    with open(local.portable.native(path), "wb") as stream:
        stream.write(content)
    return local.file_row(path)


@pytest.mark.parametrize("path,existed", [
    ("desktop/scripts/verify_nsis_install.ps1", True),
    ("tests/test_release_manifest.py", True),
    ("tests/test_local_pinned_installer_identity.py", False),
    ("tests/fixtures/local_pinned_verifier_functions.ps1", False),
])
def test_explicit_installer_verification_tooling_delta(path, existed):
    before = {"bytes": 1, "sha256": "a" * 64}
    after = {"bytes": 2, "sha256": "b" * 64}
    files = {"frontend/a.ts": before}
    if existed:
        files[path] = before
    snapshot = {"schema": "aaos.per-file-source-snapshot/v1", "files": files}
    delta = {path: {"before": before if existed else None, "after": after}}
    assert local.compare_sources(snapshot, {"frontend/a.ts": before, path: after}, {}, delta) == delta


def test_explicit_document_delta_and_fixed_tool_delta():
    row = {"bytes": 1, "sha256": "a" * 64}
    after = {"bytes": 2, "sha256": "b" * 64}
    snapshot = {"schema": "aaos.per-file-source-snapshot/v1", "files": {
        "docs/current.md": {**row, "class": "documentation"}, "frontend/a.ts": row}}
    current = {"docs/current.md": after, "frontend/a.ts": row,
               "scripts/release/local_pinned_packaging.py": after}
    docs = {"docs/current.md": {"before": row, "after": after}}
    tools = {"scripts/release/local_pinned_packaging.py": {"before": None, "after": after}}
    assert set(local.compare_sources(snapshot, current, docs, tools)) == set(docs) | set(tools)
    current["frontend/new.svg"] = row
    with pytest.raises(ValueError, match="undeclared"):
        local.compare_sources(snapshot, current, docs, tools)
    with pytest.raises(ValueError, match="tool delta"):
        local.compare_sources(snapshot, current, docs, {"frontend/new.svg": {"before": None, "after": row}})


@pytest.mark.parametrize("mutation", ["changed", "deleted", "new", "stale"])
def test_product_changes_fail_closed(mutation):
    row = {"bytes": 1, "sha256": "a" * 64}
    snapshot = {"schema": "aaos.per-file-source-snapshot/v1", "files": {"src-tauri/main.rs": row}}
    current = {"src-tauri/main.rs": row}
    docs = {}
    if mutation == "changed":
        current["src-tauri/main.rs"] = {**row, "bytes": 2}
    elif mutation == "deleted":
        current.clear()
    elif mutation == "new":
        current["frontend/untracked.ts"] = row
    else:
        docs["docs/stale.md"] = {"before": row, "after": row}
    with pytest.raises(ValueError):
        local.compare_sources(snapshot, current, docs, {})


def test_only_named_packaging_contract_is_an_allowed_tool_delta():
    row = {"bytes": 1, "sha256": "a" * 64}
    snapshot = {"schema": "aaos.per-file-source-snapshot/v1", "files": {"frontend/a.ts": row}}
    contract = "workspace/intake/20261029-local-pinned-packaging-contract.md"
    current = {"frontend/a.ts": row, contract: row}
    delta = {contract: {"before": None, "after": row}}
    assert local.compare_sources(snapshot, current, {}, delta) == delta
    with pytest.raises(ValueError, match="tool delta"):
        local.compare_sources(snapshot, current, {}, {"workspace/intake/arbitrary.md": {"before": None, "after": row}})


@pytest.mark.parametrize("failure", [None, "digest", "patch", "snapshot", "commit", "index", "changed", "new_input", "extra_coverage"])
def test_reconstruction_only_supplements_exact_historical_bytes(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(local, "owned_path", lambda root, path, **kwargs: path)
    row = {"bytes": 1, "sha256": "a" * 64}
    snapshot = {"schema": "aaos.per-file-source-snapshot/v1", "source_commit": "b" * 40,
                "source_patch_sha256": "c" * 64, "files": {"frontend/old.ts": row}}
    original = copy.deepcopy(snapshot)
    snapshot_pin = {"path": str(tmp_path / "source-files-after.json"), "sha256": "d" * 64}
    historical = [{"path": name, **row, "historical_individual_snapshot": False}
                  for name in sorted(local.RECONSTRUCTED_INPUTS)]
    evidence = {"schema": "aaos.frozen-worktree-reconstruction/v1",
                "status": "PASS_EXACT_ORIGINAL_FULL_WORKTREE_IDENTITY",
                "source_commit": snapshot["source_commit"], "expected_patch": "c" * 64,
                "reconstructed_patch": "c" * 64, "snapshot": snapshot_pin,
                "historical_untracked_inputs": historical, "reconstructed_tracked": [],
                "current_tool_delta": ["scripts/release/local_pinned_packaging.py"],
                "real_index_unchanged": True, "source_consistent": True,
                "candidate_built_again": False, "install_qualification": "NOT_GRANTED_BY_THIS_RECEIPT"}
    current = {"frontend/old.ts": row, **{name: row for name in local.RECONSTRUCTED_INPUTS}}
    if failure == "patch":
        evidence["reconstructed_patch"] = "0" * 64
    elif failure == "snapshot":
        evidence["snapshot"] = {**snapshot_pin, "sha256": "0" * 64}
    elif failure == "commit":
        evidence["source_commit"] = "0" * 40
    elif failure == "index":
        evidence["real_index_unchanged"] = False
    elif failure == "changed":
        current[historical[0]["path"]] = {**row, "bytes": 2}
    elif failure == "new_input":
        current["frontend/unrelated-new.ts"] = row
    elif failure == "extra_coverage":
        historical.append({"path": "frontend/unrelated-new.ts", **row, "historical_individual_snapshot": False})
    path = tmp_path / "reconstruction.json"
    pin = {"path": str(path), "sha256": put(path, json.dumps(evidence).encode())["sha256"]}
    if failure == "digest":
        pin["sha256"] = "0" * 64
    def verify():
        coverage = local.reconstructed_coverage(tmp_path, pin, snapshot_pin, snapshot, current)
        augmented = {**snapshot, "files": {**snapshot["files"], **coverage["supplemental_inputs"]}}
        assert local.compare_sources(augmented, current, {}, {}) == {}
        return coverage
    if failure:
        with pytest.raises(ValueError):
            verify()
    else:
        assert verify()["historical_individual_snapshot"] is False
    assert snapshot == original


def test_inventory_includes_untracked_frontend_and_tauri(tmp_path, monkeypatch):
    for name in ("tracked.txt", "frontend/new.svg", "src-tauri/new.rs"):
        put(tmp_path / name)
    def fake_git(root, *args):
        if args[0] == "rev-parse":
            return str(tmp_path).encode()
        return b"tracked.txt\0" if "--cached" in args else b"frontend/new.svg\0src-tauri/new.rs\0"
    monkeypatch.setattr(local, "git", fake_git)
    assert set(local.source_inventory(tmp_path, [])) == {"tracked.txt", "frontend/new.svg", "src-tauri/new.rs"}
    with pytest.raises(ValueError, match="exclusion"):
        local.source_inventory(tmp_path, ["missing-private"])


def test_source_inventory_accepts_real_dotfiles_and_unicode(tmp_path, monkeypatch):
    names = [".gitattributes", ".github/workflows/检查.yml", "frontend/素材/星环.svg", ".cargo/config.toml"]
    expected = {name: put(tmp_path / name, name.encode("utf-8")) for name in names}
    def fake_git(root, *args):
        if args[0] == "rev-parse":
            return os.fsencode(tmp_path)
        return b"\0".join(os.fsencode(name) for name in names) + b"\0" if "--cached" in args else b""
    monkeypatch.setattr(local, "git", fake_git)
    assert local.source_inventory(tmp_path, []) == expected


@pytest.mark.parametrize("name", ["", "/absolute", "../escape", "a/../escape", "./file", "a/./file",
                                  "a//file", "a/", "C:/absolute", "a\\file", "a\x00file", "a\nfile", "a\x7ffile", "a\x85file"])
def test_source_paths_reject_traversal_absolute_and_controls(tmp_path, name):
    with pytest.raises(ValueError, match="unsafe source"):
        local.source_path(tmp_path, name)


def test_source_path_rejects_real_symlink(tmp_path):
    target = tmp_path / "real.txt"
    put(target)
    link = tmp_path / ".linked"
    try:
        link.symlink_to(target)
    except OSError as error:
        pytest.skip("symlink creation unavailable: " + type(error).__name__)
    with pytest.raises(ValueError, match="linked"):
        local.source_path(tmp_path, ".linked")


def test_source_path_rejects_reparse_point(tmp_path, monkeypatch):
    original = Path.lstat
    def lstat(path, *args, **kwargs):
        if local.candidate._plain_path(str(path)) == tmp_path / ".reparse":
            return SimpleNamespace(st_mode=0, st_file_attributes=0x400)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "lstat", lstat)
    with pytest.raises(ValueError, match="linked"):
        local.source_path(tmp_path, ".reparse")


def test_bundle_requires_exact_reviewed_consumers(tmp_path, monkeypatch):
    monkeypatch.setattr(local, "qualify", lambda *args: {})
    monkeypatch.setattr(local, "bundle_consumer_inventory", lambda *args: {"actual": True})
    with pytest.raises(ValueError, match="consumer inputs differ"):
        local.bundle(tmp_path, {}, tmp_path / "out", tmp_path / "node.exe", {"reviewed": True})
    assert not (tmp_path / "out").exists()


def test_pinned_evidence_and_links_are_rejected(tmp_path):
    path = tmp_path / "evidence.json"
    row = put(path, b"{}")
    assert local.read_pinned(path, row["sha256"]) == {}
    with pytest.raises(ValueError, match="changed"):
        local.read_pinned(path, "0" * 64)
    link = tmp_path / "hardlink.json"
    os.link(path, link)
    with pytest.raises(ValueError, match="hardlinked"):
        local.file_row(link)


@pytest.mark.parametrize("name", ["runtime/Lib/site-packages/aiohttp/.hash/_cparser.pxd.hash", "runtime/Scripts/.empty"])
def test_formal_payload_dotdirs_are_valid(tmp_path, name):
    row = put(tmp_path / name)
    assert local.payload_path(tmp_path, name) == tmp_path / name
    assert local.file_row(local.payload_path(tmp_path, name)) == row


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/absolute", "a\\file", "a//file",
                                  "a/./file", "a/../file", "a./file", "a /file", "a/file.", "a/file ",
                                  "a\x00file", "a\nfile", "runtime/.env/secret"])
def test_formal_payload_unsafe_paths_are_rejected(tmp_path, name):
    with pytest.raises(ValueError):
        local.payload_path(tmp_path, name)


def test_formal_payload_reparse_point_is_rejected(tmp_path, monkeypatch):
    original = os.lstat
    def lstat(path, *args, **kwargs):
        if local.candidate._plain_path(str(path)) == tmp_path / ".linked":
            return SimpleNamespace(st_mode=0, st_file_attributes=0x400)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(os, "lstat", lstat)
    with pytest.raises(ValueError, match="Linked"):
        local.payload_path(tmp_path, ".linked/file")


def test_owned_output_refuses_foreign_existing_and_link(tmp_path, monkeypatch):
    runs = tmp_path / ".project-local/runs"
    runs.mkdir(parents=True)
    monkeypatch.setattr(local.candidate, "project_local_root", lambda root: tmp_path / ".project-local")
    monkeypatch.setattr(local.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=0))
    assert local.owned_path(tmp_path, runs / "new", fresh=True) == runs / "new"
    with pytest.raises(ValueError, match="outside"):
        local.owned_path(tmp_path, tmp_path / "foreign", fresh=True)
    with pytest.raises(ValueError, match="exists"):
        local.owned_path(tmp_path, runs, fresh=True)


def build_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(local, "owned_path", lambda root, path, **kw: path)
    source = {"source_commit": "a" * 40, "source_tree": "b" * 40, "source_patch_sha256": "c" * 64}
    payload = {"files": {name: {"bytes": 1, "sha256": digest * 64} for name, digest in (
        ("ArcheAxis.exe", "d"), ("core/archeaxis-api.exe", "e"), ("backend-runtime-manifest.json", "f"))}}
    core = {**source, "status": "LOCAL_PASS", "exit_code": 0, "source_consistent": True,
            "source_commit_after": source["source_commit"], "source_patch_sha256_after": source["source_patch_sha256"],
            "core_build": {"schema": "archeaxis.core-build/v1", "artifact": {"sha256": "e" * 64}}}
    timing = {"schema": "archeaxis.build-timings/v1",
              "source": {"ARCHEAXIS_" + k.upper(): v for k, v in source.items()},
              "stages": [{"name": "tauri-with-bundle", "status": "PASS", "exit_code": 0, "ended_at": "then"}]}
    build = {**source, "schema": "archeaxis.frontend-build/v1", "mode": "tauri", "status": "PASS", "exit_code": 0,
             "source_consistent": True, "worktree_root": str(tmp_path),
             "source_patch_sha256_after": source["source_patch_sha256"],
             "portable_build_arguments": ["build", "--no-bundle", "--", "--offline", "--locked"],
             "host_sha256": "d" * 64, "core_sha256": "e" * 64, "backend_manifest_sha256": "f" * 64}
    for key, value in (("core_build_receipt", core), ("build_timings", timing)):
        path = tmp_path / (key + ".json")
        build[key] = {"path": str(path), **put(path, json.dumps(value).encode())}
    return build, source, payload


def test_original_build_receipt_dependencies_are_exact(tmp_path, monkeypatch):
    build, snapshot, payload = build_fixture(tmp_path, monkeypatch)
    assert local.verify_build(tmp_path, build, snapshot, payload) == snapshot
    put(Path(build["core_build_receipt"]["path"]), b"{}")
    with pytest.raises(ValueError, match="dependency changed"):
        local.verify_build(tmp_path, build, snapshot, payload)


@pytest.mark.parametrize("field,value", [("source_patch_sha256_after", "0" * 64), ("status", "FAIL"),
                                        ("source_consistent", False), ("core_sha256", "0" * 64)])
def test_build_failure_and_mismatched_payload_refused(tmp_path, monkeypatch, field, value):
    build, snapshot, payload = build_fixture(tmp_path, monkeypatch)
    build[field] = value
    with pytest.raises(ValueError):
        local.verify_build(tmp_path, build, snapshot, payload)


def test_ci_fields_are_not_local_qualification(tmp_path):
    with pytest.raises(ValueError, match="CI identities forbidden"):
        local.qualify(tmp_path, {"verification_ci_run_id": 123})


@pytest.mark.parametrize("failure", [None, "count", "payload", "new_input"])
def test_full_readonly_qualification_separates_build_and_packaging(tmp_path, monkeypatch, failure):
    build, source, payload = build_fixture(tmp_path, monkeypatch)
    row = {"bytes": 1, "sha256": "1" * 64}
    snapshot = {"schema": "aaos.per-file-source-snapshot/v1", **source,
                "files": {"frontend/a.ts": row}, "excluded_private_paths": []}
    snapshot_path = tmp_path / "source-files-after.json"
    host_path = tmp_path / "frontend-build.json"
    candidate_root = tmp_path / "candidate"
    request = {"snapshot": {"path": str(snapshot_path), **put(snapshot_path, json.dumps(snapshot).encode())},
               "snapshot_count": 2 if failure == "count" else 1,
               "host_receipt": {"path": str(host_path), **put(host_path, json.dumps(build).encode())},
               "candidate": str(candidate_root),
               "candidate_manifest": put(candidate_root / "candidate-manifest.json", json.dumps(payload).encode())["sha256"],
               "docs_delta": {}, "tools_delta": {}}
    current = {"frontend/a.ts": row}
    if failure == "new_input":
        current["frontend/new.svg"] = row
    monkeypatch.setattr(local, "source_inventory", lambda *args: current)
    visited = []
    def verify(path):
        visited.append(path)
        return {} if failure == "payload" else payload
    monkeypatch.setattr(local.portable, "verify", verify)
    monkeypatch.setattr(local, "git", lambda root, *args: b"f" * 40)
    if failure:
        with pytest.raises(ValueError):
            local.qualify(tmp_path, request)
    else:
        identity = local.qualify(tmp_path, request)
        assert identity["build_source"] == source
        assert identity["packaging_source"]["commit"] == "f" * 40
        assert identity["ci_qualification"] == "NOT_CLAIMED"
        assert identity["installed_qualification"] == "NOT_RUN"
        assert visited == [candidate_root]


def test_bundle_command_cannot_compile_or_sign():
    assert local.bundle_command(Path("node.exe"), Path("tauri.js"), Path("config.json")) == [
        "node.exe", "tauri.js", "bundle", "--config", "config.json", "--no-sign",
        "--no-binary-patching", "--bundles", "nsis"]


def test_tool_inventory_enumeration_failure_is_not_silent(tmp_path, monkeypatch):
    def inaccessible_walk(*args, **kwargs):
        kwargs["onerror"](PermissionError("synthetic enumeration denied"))
        return iter(())
    monkeypatch.setattr(local.os, "walk", inaccessible_walk)
    with pytest.raises(PermissionError, match="enumeration denied"):
        local.tree_inventory(tmp_path)


def test_overlay_removes_old_mutable_resource_keys(tmp_path):
    put(tmp_path / "src-tauri/tauri.conf.json", json.dumps({"bundle": {"resources": {
        "../.project-local/rt/runtime": "runtime", "../.project-local/rt/core": "core"}}}).encode())
    copies = {"/owned/new/runtime/python.exe": "runtime/python.exe"}
    overlay = local.bundle_overlay(tmp_path, copies, "/configuration/path/only")
    patch = overlay["bundle"]["resources"]
    assert patch == {"../.project-local/rt/runtime": None, "../.project-local/rt/core": None, **copies}
    assert {name: value for name, value in patch.items() if value is not None} == copies
    assert overlay["bundle"]["useLocalToolsDir"] is True
    assert overlay["build"]["beforeBundleCommand"] == ""


@pytest.mark.parametrize("failure", [None, "exit", "patch", "inputs", "resource", "overlay", "consumer", "precopy"])
def test_bundle_wrapper_only_runs_bundle_and_preserves_failures(tmp_path, monkeypatch, failure):
    source = tmp_path / "candidate"
    row = put(source / "ArcheAxis.exe")
    put(source / "portable.flag", b"")
    resource = put(source / "workers/worker.py", b"worker")
    identity = {"payload": {"files": {"ArcheAxis.exe": row, "portable.flag": local.file_row(source / "portable.flag"),
                                      "workers/worker.py": resource}}}
    for name in ("runtime/Lib/site-packages/aiohttp/.hash/_cparser.pxd.hash", "runtime/Scripts/.empty"):
        identity["payload"]["files"][name] = put(source / name)
    # Exercise real filesystem creation/copy beyond MAX_PATH, without mocks,
    # junctions, a long-path policy change, or changing any payload content.
    long_member = "runtime/" + "/".join(["long-directory-segment"] * 14) + "/.hash/member.bin"
    assert len(str(source / long_member)) > 260
    long_row = put(source / long_member, b"synthetic-long-path")
    identity["payload"]["files"][long_member] = long_row
    calls = []
    def qualify(root, request):
        return {**identity, "changed": True} if failure == "inputs" and calls else copy.deepcopy(identity)
    monkeypatch.setattr(local, "qualify", qualify)
    monkeypatch.setattr(local, "owned_path", lambda root, path, **kw: path)
    monkeypatch.setattr(local, "build_frontend_dist", lambda *args: str(source))
    node = tmp_path / "node.exe"
    put(node)
    put(tmp_path / "frontend/node_modules/@tauri-apps/cli/tauri.js")
    put(tmp_path / "src-tauri/tauri.conf.json", b'{"bundle":{"resources":{"old-runtime":"runtime"}}}')
    nsis_root = tmp_path / "source-nsis"
    nsis_row = put(nsis_root / "makensis.exe")
    consumers = {"tool_trees": {"nsis": {"path": str(nsis_root), "files": {"makensis.exe": nsis_row}}}}
    monkeypatch.setattr(local, "bundle_consumer_inventory", lambda *args:
                        {} if failure == "consumer" and calls else copy.deepcopy(consumers))
    output = tmp_path / "new-run"
    def run(command, **kwargs):
        calls.append(command)
        overlay = json.loads((output / "bundle-config.json").read_text())
        assert overlay["build"]["beforeBundleCommand"] == ""
        assert overlay["build"]["beforeBuildCommand"] == ""
        assert overlay["bundle"]["resources"]["old-runtime"] is None
        assert kwargs["env"]["CARGO_TARGET_DIR"] == str(output / "target")
        assert kwargs["cwd"] == tmp_path / "src-tauri"
        put(output / "target/release/bundle/nsis/new.exe")
        if failure == "patch":
            put(output / "target/release/ArcheAxis.exe", b"patched")
        if failure == "resource":
            put(output / "target/release/workers/worker.py", b"tampered")
        if failure == "overlay":
            put(output / "bundle-config.json", b"{}")
        return SimpleNamespace(returncode=7 if failure == "exit" else 0)
    monkeypatch.setattr(local.subprocess, "run", run)
    if failure == "precopy":
        real_copy = local.shutil.copyfileobj
        def fail_copy(incoming, outgoing, *args, **kwargs):
            if str(incoming.name).endswith("worker.py"):
                raise ValueError("synthetic payload copy refusal")
            return real_copy(incoming, outgoing, *args, **kwargs)
        monkeypatch.setattr(local.shutil, "copyfileobj", fail_copy)
    if failure:
        with pytest.raises(ValueError):
            local.bundle(tmp_path, {"candidate": str(source)}, output, node, consumers)
    else:
        assert local.bundle(tmp_path, {"candidate": str(source)}, output, node, consumers)["status"] == "LOCAL_PACKAGING_PASS"
    receipt = json.loads((output / "packaging-receipt.json").read_text())
    assert receipt["installed_qualification"] == "NOT_RUN"
    assert receipt["status"] == ("FAIL" if failure else "LOCAL_PACKAGING_PASS")
    if failure == "precopy":
        assert calls == [] and receipt["cli_started"] is False and receipt["exit_code"] is None
        assert receipt["stage"] == "PAYLOAD_COPY" and receipt["error_type"] == "ValueError"
    else:
        assert len(calls) == 1 and calls[0][2] == "bundle"
    assert local.file_row(source / "ArcheAxis.exe") == row
    if failure != "precopy":
        assert local.file_row(output / "target/release" / long_member) == long_row


@pytest.mark.skipif(os.name != "nt", reason="actual Windows long-path filesystem regression")
def test_windows_real_long_directory_payload_copy(tmp_path, monkeypatch):
    # The common synthetic wrapper executes real mkdir/open/stat operations;
    # only the external CLI is mocked. This verifies the production copy path.
    test_bundle_wrapper_only_runs_bundle_and_preserves_failures(tmp_path, monkeypatch, None)


@pytest.mark.parametrize("mutation", [None, "icon", "tool", "hook", "external"])
def test_real_bundle_consumer_inventory_binds_icons_tools_and_hooks(tmp_path, mutation):
    config = {"build": {"frontendDist": "not-present"}, "bundle": {"icon": ["icons/icon.ico"],
              "useLocalToolsDir": True, "windows": {"webviewInstallMode": {"type": "skip"}}}}
    config_path = tmp_path / "src-tauri/tauri.conf.json"
    icon = tmp_path / "src-tauri/icons/icon.ico"
    put(icon)
    node = tmp_path / "node.exe"
    put(node)
    for directory in ("frontend/node_modules/@tauri-apps/cli", "frontend/node_modules/@tauri-apps/cli-win32-x64-msvc",
                      ".project-local/build/tauri/.tauri/NSIS"):
        put(tmp_path / directory / "tool.bin")
    put(config_path, json.dumps(config).encode())
    expected = local.bundle_consumer_inventory(tmp_path, node)
    assert expected["frontendDist"] == "CONFIG_PATH_ONLY_NOT_REBUILT"
    if mutation == "icon":
        put(icon, b"changed")
    elif mutation == "tool":
        put(tmp_path / "frontend/node_modules/@tauri-apps/cli/tool.bin", b"changed")
    elif mutation == "hook":
        config["build"]["beforeBundleCommand"] = "forbidden"
    elif mutation == "external":
        config["bundle"]["externalBin"] = ["unbound"]
    if mutation in {"hook", "external"}:
        put(config_path, json.dumps(config).encode())
        with pytest.raises(ValueError):
            local.bundle_consumer_inventory(tmp_path, node)
    elif mutation:
        assert local.bundle_consumer_inventory(tmp_path, node) != expected
    else:
        assert local.bundle_consumer_inventory(tmp_path, node) == expected
