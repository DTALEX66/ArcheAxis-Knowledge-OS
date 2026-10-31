"""Synthetic local installer identity guards; never install or start the product.

Runtime branch checks run cross-platform. The Windows-only helper suite loads
audited function AST definitions rather than executing the lifecycle script.
"""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = Path(os.environ.get("AAOS_TEST_LOCAL_PINNED_VERIFIER", str(ROOT / "desktop/scripts/verify_nsis_install.ps1")))
if not VERIFIER.is_absolute():
    raise ValueError("explicit verifier test override must be an absolute path")


def embedded_probe():
    source = VERIFIER.read_text(encoding="utf-8-sig")
    marker = "$probe = @'"
    assert source.count(marker) == 1, "review changed embedded probe boundaries"
    return source.split(marker, 1)[1].split("\n'@", 1)[0].lstrip("\n")


def local_runtime_code():
    # Parse the real embedded probe, executing only its local requirement guard.
    module = ast.parse(embedded_probe())
    guards = [node for node in module.body if isinstance(node, ast.If)
              and isinstance(node.test, ast.Compare)
              and isinstance(node.test.left, ast.Name) and node.test.left.id == "requirement"
              and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Eq)
              and len(node.test.comparators) == 1
              and isinstance(node.test.comparators[0], ast.Constant)
              and node.test.comparators[0].value == "local-pinned"]
    assert len(guards) == 1, "review changed local identity guard"
    guard = copy.deepcopy(guards[0])
    guard.orelse = []
    return compile(ast.Module(body=[guard], type_ignores=[]), str(VERIFIER) + "::local-pinned", "exec")


@pytest.fixture
def runtime_proof(tmp_path):
    root = tmp_path / "synthetic-install"
    app = root / "runtime/Lib/site-packages/app"
    app.mkdir(parents=True)
    release_file = app / "release.py"
    release_file.write_text("# SYNTHETIC: never imported\n", encoding="utf-8")
    manifest = app / "release-manifest.json"
    frozen = {"release": {"status": "unreleased", "channel": "development", "public": False},
              "product": {"version": "0.6.14"}, "source": {"commit": "unavailable"},
              "capabilities": {"public_installer": "not_implemented", "local_feature": "available"}}
    raw = json.dumps(frozen).encode()
    manifest.write_bytes(raw)
    identity = {"payload": {"files": {manifest.relative_to(root).as_posix(): {
        "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}}}}
    identity_path = tmp_path / "local-pinned-identity.json"
    identity_raw = json.dumps(identity).encode()
    identity_path.write_bytes(identity_raw)
    scope = {"requirement": "local-pinned", "root": root, "Path": Path, "json": json, "hashlib": hashlib,
             "release": SimpleNamespace(__file__=str(release_file), load_artifact_release_identity=lambda: None),
             "summary": {"status": "unreleased", "version": "0.6.14", "channel": "development",
                         "public": False, "source_commit": "unavailable"},
             "capabilities": copy.deepcopy(frozen["capabilities"]),
             "sys": SimpleNamespace(argv=["probe", str(root), "synthetic-data", "seed", "local-pinned",
                                           str(identity_path), hashlib.sha256(identity_raw).hexdigest()])}
    code = local_runtime_code()
    return SimpleNamespace(scope=scope, manifest=manifest, identity_path=identity_path,
                           validate=lambda: exec(code, scope))


def test_original_runtime_summary_is_not_restamped_as_local_build(runtime_proof):
    runtime_proof.validate()
    assert runtime_proof.scope["summary"]["source_commit"] == "unavailable"


def test_local_runtime_rejects_artifact_identity(runtime_proof):
    runtime_proof.scope["release"].load_artifact_release_identity = lambda: {"schema_version": "candidate-1.0.0"}
    with pytest.raises(AssertionError):
        runtime_proof.validate()


def test_local_runtime_rejects_identity_digest_change(runtime_proof):
    runtime_proof.identity_path.write_bytes(b"{}")
    with pytest.raises(AssertionError):
        runtime_proof.validate()


def test_local_runtime_rejects_manifest_bytes_change(runtime_proof):
    runtime_proof.manifest.write_bytes(runtime_proof.manifest.read_bytes() + b" ")
    with pytest.raises(AssertionError):
        runtime_proof.validate()


def test_local_runtime_rejects_each_summary_field_change(runtime_proof):
    original = copy.deepcopy(runtime_proof.scope["summary"])
    for field, value in (("status", "qualified"), ("source_commit", "a" * 40),
                         ("channel", "stable"), ("public", True), ("version", "9.9.9")):
        runtime_proof.scope["summary"] = {**original, field: value}
        with pytest.raises(AssertionError):
            runtime_proof.validate()


def test_local_runtime_rejects_public_installer_available(runtime_proof):
    runtime_proof.scope["capabilities"]["public_installer"] = "available"
    with pytest.raises(AssertionError):
        runtime_proof.validate()


def test_local_runtime_rejects_other_capability_drift(runtime_proof):
    runtime_proof.scope["capabilities"]["local_feature"] = "not_implemented"
    with pytest.raises(AssertionError):
        runtime_proof.validate()


def test_local_runtime_rejects_release_module_outside_install(runtime_proof, tmp_path):
    runtime_proof.scope["release"].__file__ = str(tmp_path / "outside/release.py")
    with pytest.raises((ValueError, FileNotFoundError)):
        runtime_proof.validate()


@pytest.mark.parametrize("requirement", ["candidate", "release"])
def test_existing_ci_and_release_requirements_remain_enforced(requirement):
    # Same real validation boundary as test_release_manifest.py. The local guard
    # must not alter the existing CI/release publication and exact-SHA rules.
    probe = embedded_probe()
    validation = "summary, capabilities = " + probe.split("summary, capabilities = ", 1)[1].split("record_path = ", 1)[0]
    code = compile(validation, str(VERIFIER) + "::existing-requirements", "exec")
    expected = {"version": "0.6.14", "tag": "v0.6.14", "source_commit": "a" * 40,
                "status": "qualified" if requirement == "candidate" else "released", "public": requirement == "release"}
    capability = "available" if requirement == "release" else "unavailable"
    def validate(summary, state=capability, sha="a" * 40):
        release = SimpleNamespace(safe_release_summary=lambda: summary,
                                  effective_capabilities=lambda: {"public_installer": state})
        exec(code, {"release": release, "requirement": requirement,
                    "os": SimpleNamespace(environ={"GITHUB_SHA": sha})})
    validate(expected)
    for field, value in (("version", "0.0.0"), ("tag", "v0.0.0"),
                         ("public", not expected["public"]), ("status", "unreleased")):
        with pytest.raises(AssertionError):
            validate({**expected, field: value})
    with pytest.raises(AssertionError):
        validate(expected, "unavailable" if capability == "available" else "available")
    if requirement == "candidate":
        with pytest.raises(AssertionError):
            validate(expected, sha="b" * 40)


@pytest.mark.skipif(sys.platform != "win32", reason="real Windows path/link and PowerShell 7 helper guards")
def test_local_identity_powershell_functions_without_installation(tmp_path):
    pwsh = shutil.which("pwsh")
    if not pwsh:
        pytest.skip("PowerShell 7 is not available")
    fixture = ROOT / "tests/fixtures/local_pinned_verifier_functions.ps1"
    environment = {**os.environ, "ARCHEAXIS_RUN_ROOT": str(tmp_path), "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([pwsh, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(fixture),
                             "-Source", str(VERIFIER)], cwd=ROOT, env=environment,
                            capture_output=True, text=True, encoding="utf-8", timeout=180, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["verifier_sha256"] == hashlib.sha256(VERIFIER.read_bytes()).hexdigest()
    assert report["scope"] == "SYNTHETIC_FUNCTIONS_ONLY_NO_INSTALLATION"
    assert report["failed"] == 0
    assert report["passed"] + report["skipped"] == 42
    outcomes = {item["name"]: item for item in report["results"]}
    for name in ("valid full real filesystem payload with dotdirs and >260 path",
                 "literal LF codepoint reaches the production member guard", "unsafe member a[LF]file",
                 "changed installer between operations", "enumeration errors propagate"):
        assert outcomes[name]["status"] == "PASS"
    for key in ("ExpectedLocalPinnedIdentitySha256", "ExpectedInstallerSha256", "ExpectedHostSha256",
                "ExpectedCoreSha256", "ExpectedRuntimeManifestSha256"):
        assert outcomes["missing digest: " + key]["status"] == "PASS"
    skipped = [item for item in report["results"] if item["status"] == "SKIP"]
    assert all(item["name"] == "real symlink rejected" and item["reason"] == "symlink permission unavailable"
               for item in skipped)
    evidence = Path(report["fixture_root"])
    assert evidence.is_relative_to(tmp_path)
    assert json.loads((evidence / "test-results.json").read_text(encoding="utf-8")) == report
