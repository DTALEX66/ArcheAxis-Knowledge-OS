"""Synthetic only: no npm process, actual registry request or package script."""
import base64
import copy
import hashlib
import io
import json
import os
import stat
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

from scripts.runtime import openmaic_npm_fetch as npm


SINGLE_DEPENDENCIES = [
    ("postcss-value-parser", "4.2.0", "4.2.1", "POSTCSS_VALUE_PARSER"),
    ("es-module-lexer", "2.0.0", "2.0.1", "ES_MODULE_LEXER"),
]


def archive(name="jsonrepair", version="3.13.3", *, license_name="MIT", extra=(), manifest_extra=None):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        manifest = {"name": name, "version": version, "license": license_name}
        manifest.update(manifest_extra or {})
        data = {"package/package.json": json.dumps(manifest).encode(),
                "package/LICENSE": b"synthetic license text\n", "package/index.js": b"export const value = 1;\n"}
        for path, body in data.items():
            info = tarfile.TarInfo(path)
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))
        for info, body in extra:
            tar.addfile(info, io.BytesIO(body) if info.isfile() else None)
    return buffer.getvalue()


def sri(data):
    return "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode("ascii")


def read_native(path):
    with open(npm.portable.native(path), "rb") as source:
        return source.read()


def write_native(path, data):
    with open(npm.portable.native(path), "wb") as target:
        target.write(data)


@pytest.fixture
def growth(tmp_path, monkeypatch):
    portable = npm.portable
    monkeypatch.setattr(npm, "REPO", tmp_path)
    monkeypatch.setattr(portable, "REPO", tmp_path)
    run = tmp_path / ".project-local/runs/0123456789/npm-growth"
    artifacts = run / "artifacts"
    artifacts.mkdir(parents=True)
    (run / "tmp").mkdir()
    cache = tmp_path / ".project-local/cache"
    (cache / "npm").mkdir(parents=True)
    paths = {"root": tmp_path, "run": run, "artifacts": artifacts, "cache": cache}
    monkeypatch.setattr(portable.dev, "layout", lambda *args: paths)
    monkeypatch.setattr(portable.dev, "git", lambda *args: str(tmp_path / ".git"))
    report = {"schema": "aaos.storage-footprint/v2", "repository": str(tmp_path),
              "measured_at": "2026-11-02T00:00:00+00:00", "readable_bytes": 30 * 1024 ** 3,
              "measurement_status": "PARTIAL", "measurement_errors": [{"error": "synthetic"}],
              "excluded_private": ["private-preserved"], "excluded_checkouts": [], "out_of_layout": [],
              "dev_root": [
                  {"name": "cache/", "bytes": 1024 ** 3, "budget_gb": None, "over_budget": False,
                   "errors": [], "excluded_private": [], "links": []},
                  {"name": "runs/", "bytes": 3 * 1024 ** 3, "budget_gb": 2.0, "over_budget": True,
                   "errors": [], "excluded_private": [], "links": []},
                  {"name": "build/", "bytes": 10 * 1024 ** 3, "budget_gb": 22.0, "over_budget": False},
              ]}
    baseline = tmp_path / ".project-local/runs/0123456789/checkpoint/artifacts/storage.json"
    baseline.parent.mkdir(parents=True)
    raw = json.dumps(report).encode()
    baseline.write_bytes(raw)
    pointer = tmp_path / "docs/current/AAOS-ACTIVE-EXECUTION.json"
    pointer.parent.mkdir(parents=True)
    descriptor = {"schema": portable.CHECKPOINT_SCHEMA, "path": baseline.relative_to(tmp_path).as_posix(),
                  "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                  "report_schema": report["schema"], "recorded_by": "synthetic test",
                  "measurement_scope": "partial synthetic coverage"}
    pointer.write_text(json.dumps({"execution_control": {"owner_priority_20261030": {
        "operator_storage_checkpoint": descriptor}}}), encoding="utf-8")
    measures = []
    def measure(root):
        measures.append(root)
        return copy.deepcopy(report)
    monkeypatch.setattr(portable.storage_report, "measure", measure)
    monkeypatch.setattr(npm, "_locked_inputs", lambda *_: None)
    context = {"paths": paths, "purpose": "synthetic fetch", "sharing": "project only",
               "retention_reason": "test evidence"}
    return SimpleNamespace(paths=paths, report=report, measures=measures, baseline=baseline,
                           pointer=pointer, context=context)


def test_fixed_plan_accounts_for_two_copies_and_two_expansions():
    assert npm.PLAN_BYTES == 293_601_280
    assert npm.PLAN_BYTES >= 2 * (2 * npm.MAX_COMPRESSED + npm.MAX_UNPACKED) + npm.TEMP_EVIDENCE_ALLOWANCE
    assert npm.PARTIAL_JSON_PLAN_BYTES == 167_772_160
    assert npm.PARTIAL_JSON_PLAN_BYTES >= 2 * npm.MAX_COMPRESSED + npm.MAX_UNPACKED + npm.TEMP_EVIDENCE_ALLOWANCE
    assert npm.POSTCSS_VALUE_PARSER_PLAN_BYTES == npm.PARTIAL_JSON_PLAN_BYTES == 167_772_160
    assert npm.ES_MODULE_LEXER_PLAN_BYTES == npm.PARTIAL_JSON_PLAN_BYTES == 167_772_160


def test_postcss_selection_binds_exact_owner_lock_and_keeps_default_unchanged():
    expected = {"version": "4.2.0", "sri": "sha512-1NNCs6uurfkVbeXG4S8JFT9t19m45ICnif8zWLd5oPSZ50QnwMfK+H3jv408d4jw/7Bttv5axS5IiHoLaVNHeQ=="}
    packages, plan = npm._selection("postcss-value-parser")
    assert packages == {"postcss-value-parser": expected} and plan == 167_772_160
    packages["postcss-value-parser"]["version"] = "modified"
    assert npm._selection("postcss-value-parser")[0] == {"postcss-value-parser": expected}
    assert set(npm._selection("default")[0]) == {"jsonrepair", "nanoid"}
    assert npm._selection("default")[1] == 293_601_280


def test_es_module_lexer_selection_binds_exact_owner_lock_and_keeps_other_selections():
    expected = {"version": "2.0.0", "sri": "sha512-5POEcUuZybH7IdmGsD8wlf0AI55wMecM9rVBTI/qEAy2c1kTOm3DjFYjrBdI2K3BaJjJYfYFeRtM0t9ssnRuxw=="}
    packages, plan = npm._selection("es-module-lexer")
    assert packages == {"es-module-lexer": expected} and plan == 167_772_160
    packages["es-module-lexer"]["version"] = "modified"
    assert npm._selection("es-module-lexer")[0] == {"es-module-lexer": expected}
    assert set(npm._selection("default")[0]) == {"jsonrepair", "nanoid"}
    assert set(npm._selection("postcss-value-parser")[0]) == {"postcss-value-parser"}
    assert set(npm._selection("partial-json")[0]) == {"partial-json"}


def test_geometry_selection_is_fixed_to_three_external_direct_dependencies():
    packages, plan = npm._selection("geometry")
    assert packages == {
        "entities": {"version": "6.0.1", "sri": "sha512-aN97NXWF6AWBTahfVOIrB/NShkzi5H7F9r1s9mD3cDj4Ko5f2qhhVoYMibXF7GlLveb/D2ioWay8lxI97Ven3g=="},
        "svg-pathdata": {"version": "8.0.0", "sri": "sha512-2Zqf5zsrX44Ws9y52EdHYrzGGnzyQG0jgREw+S3nP7zdx7QeH3QJonnGPvjtxPmYzU5mJMJ2YM+q2hUWGENWFg=="},
        "tinycolor2": {"version": "1.6.0", "sri": "sha512-XPaBkWQJdsf3pLKJV9p4qN/S+fm2Oj8AIPo1BTUhg5oxkvm9+SVEGFdhyOz7tTdUTfvxMiAs4sp6/eZO2Ew+pw=="},
    }
    assert plan == 419_430_400
    packages["entities"]["version"] = "mutated"
    assert npm._selection("geometry")[0]["entities"]["version"] == "6.0.1"
    assert set(npm._selection("default")[0]) == {"jsonrepair", "nanoid"}


def test_parse5_selection_keeps_both_entities_versions_distinct():
    packages, plan = npm._selection("parse5")
    assert packages == {
        "parse5": {"version": "8.0.1", "sri": "sha512-z1e/HMG90obSGeidlli3hj7cbocou0/wa5HacvI3ASx34PecNjNQeaHNo5WIZpWofN9kgkqV1q5YvXe3F0FoPw=="},
        "entities": {"version": "8.0.0", "sri": "sha512-zwfzJecQ/Uej6tusMqwAqU/6KL2XaB2VZ2Jg54Je6ahNBGNH6Ek6g3jjNCF0fG9EWQKGZNddNjU5F1ZQn/sBnA=="},
    }
    assert plan == 293_601_280
    assert npm._selection("geometry")[0]["entities"]["version"] == "6.0.1"
    packages["entities"]["version"] = "modified"
    assert npm._selection("parse5")[0]["entities"]["version"] == "8.0.0"


def test_parse5_lock_requires_generation_import_and_exact_transitive_edge(tmp_path, monkeypatch):
    packages = npm._selection("parse5")[0]
    lock = {
        "lockfileVersion": "9.0",
        "importers": {"packages/@openmaic/generation": {"dependencies": {"parse5": {"version": "8.0.1"}}}},
        "packages": {f'{name}@{row["version"]}': {"resolution": {"integrity": row["sri"]}}
                     for name, row in packages.items()},
        "snapshots": {"parse5@8.0.1": {"dependencies": {"entities": "8.0.0"}}, "entities@8.0.0": {}},
    }
    owner = tmp_path / "parse5-owner.zip"
    monkeypatch.setattr(npm, "OWNER_ZIP", owner)
    def check(candidate):
        raw = npm.yaml.safe_dump(candidate).encode()
        with zipfile.ZipFile(owner, "w") as archive_file:
            archive_file.writestr(npm.LOCK_MEMBER, raw)
        monkeypatch.setattr(npm, "OWNER_ZIP_SHA256", hashlib.sha256(owner.read_bytes()).hexdigest())
        monkeypatch.setattr(npm, "LOCK_SHA256", hashlib.sha256(raw).hexdigest())
        npm._locked_inputs(packages)
    check(lock)
    for mutation in ("importer", "parent_version", "wrong_edge", "extra_edge", "optional", "parent_peer",
                     "child_sri", "child_null", "child_extra"):
        changed = copy.deepcopy(lock)
        if mutation == "importer":
            changed["importers"] = {"packages/@openmaic/geometry": changed["importers"]["packages/@openmaic/generation"]}
        elif mutation == "parent_version":
            changed["importers"]["packages/@openmaic/generation"]["dependencies"]["parse5"]["version"] = "8.0.0"
        elif mutation == "wrong_edge":
            changed["snapshots"]["parse5@8.0.1"]["dependencies"]["entities"] = "6.0.1"
        elif mutation == "extra_edge":
            changed["snapshots"]["parse5@8.0.1"]["dependencies"]["other"] = "1.0.0"
        elif mutation == "optional":
            changed["snapshots"]["parse5@8.0.1"]["optionalDependencies"] = {"other": "1.0.0"}
        elif mutation == "parent_peer":
            changed["packages"]["parse5@8.0.1"]["peerDependencies"] = {"other": "*"}
        elif mutation == "child_sri":
            changed["packages"]["entities@8.0.0"]["resolution"]["integrity"] = "sha512-wrong"
        elif mutation == "child_null":
            changed["snapshots"]["entities@8.0.0"] = None
        else:
            changed["snapshots"]["entities@8.0.0"] = {"unexpected": "value"}
        with pytest.raises(npm.FetchError, match="exact dependency-free or pinned-edge"):
            check(changed)
    # A child without its exact parent is not a direct geometry dependency.
    check(lock)
    with pytest.raises(npm.FetchError):
        npm._locked_inputs({"entities": packages["entities"]})


def test_parse5_manifest_requires_only_the_pinned_entities_edge():
    npm._inspect_archive(archive("parse5", "8.0.1", manifest_extra={"dependencies": {"entities": "^8.0.0"}}), "parse5", "8.0.1")
    npm._inspect_archive(archive("entities", "8.0.0"), "entities", "8.0.0")
    for extra in ({}, {"dependencies": {"entities": "^6.0.0"}},
                  {"dependencies": {"entities": "^8.0.0", "other": "1"}},
                  {"dependencies": {"entities": "^8.0.0"}, "optionalDependencies": {"other": "1"}}):
        with pytest.raises(npm.FetchError, match="pinned-edge"):
            npm._inspect_archive(archive("parse5", "8.0.1", manifest_extra=extra), "parse5", "8.0.1")
    for field in ("dependencies", "optionalDependencies", "peerDependencies", "bundledDependencies"):
        value = ["unexpected"] if field == "bundledDependencies" else {"unexpected": "1"}
        with pytest.raises(npm.FetchError, match="dependency-free"):
            npm._inspect_archive(archive("entities", "8.0.0", manifest_extra={field: value}), "entities", "8.0.0")


def test_parse5_group_keeps_exact_package_versions_and_archives(growth, monkeypatch):
    payloads = {
        "parse5": archive("parse5", "8.0.1", manifest_extra={"dependencies": {"entities": "^8.0.0"}}),
        "entities": archive("entities", "8.0.0"),
    }
    packages = {name: {**row, "sri": sri(payloads[name])} for name, row in npm.PARSE5_PACKAGES.items()}
    monkeypatch.setattr(npm, "PARSE5_PACKAGES", packages)
    def download(name, version, part, expected):
        assert (version, expected) == (packages[name]["version"], packages[name]["sri"])
        write_native(part, payloads[name])
        return {"archive_bytes": len(payloads[name]), "sri": expected}
    monkeypatch.setattr(npm, "_download", download)
    result = npm.run(growth.context, "parse5")
    target = growth.paths["cache"] / "npm" / ("openmaic-owner-" + npm.LOCK_SHA256) / growth.paths["run"].name
    assert {(row["name"], row["version"]) for row in result} == {("parse5", "8.0.1"), ("entities", "8.0.0")}
    for name, row in packages.items():
        assert read_native(target / f'{name}-{row["version"]}.tgz') == payloads[name]
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["selection"] == "parse5" and receipt["planned_payload_bytes"] == 293_601_280
    assert receipt["copy_outcome"] == "VERIFIED_ARCHIVES_AND_LICENSE_FILES"


def test_entities_versions_cannot_borrow_each_others_archive_identity(tmp_path, monkeypatch):
    payload = b"synthetic entities 8 archive"
    packages = copy.deepcopy(npm.PARSE5_PACKAGES)
    packages["entities"]["sri"] = sri(payload)
    monkeypatch.setattr(npm, "PARSE5_PACKAGES", packages)
    monkeypatch.setattr(npm, "_tls_context", lambda: "system-trust")
    calls = []
    class Response:
        status = 200
        def __init__(self): self.data = io.BytesIO(payload)
        def getheader(self, key, default=None): return default
        def read(self, count): return self.data.read(count)
    class Connection:
        sock = None
        def __init__(self, host, port, **kw): calls.append((host, port))
        def request(self, method, path, headers): calls.append((method, path))
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(npm.http.client, "HTTPSConnection", Connection)
    with pytest.raises(npm.FetchError, match="outside"):
        npm._download("entities", "6.0.1", tmp_path / "wrong.part", sri(payload))
    assert not calls
    assert npm._download("entities", "8.0.0", tmp_path / "ok.part", sri(payload))["sri"] == sri(payload)
    assert calls == [("registry.npmjs.org", 443), ("GET", "/entities/-/entities-8.0.0.tgz")]


def test_parse5_fixed_https_rejects_wrong_identity_and_redirect(tmp_path, monkeypatch):
    payload = b"synthetic parse5 archive"
    packages = copy.deepcopy(npm.PARSE5_PACKAGES)
    packages["parse5"]["sri"] = sri(payload)
    monkeypatch.setattr(npm, "PARSE5_PACKAGES", packages)
    monkeypatch.setattr(npm, "_tls_context", lambda: "system-trust")
    calls = []
    class Response:
        status = 200
        def __init__(self): self.data = io.BytesIO(payload)
        def getheader(self, key, default=None): return default
        def read(self, count): return self.data.read(count)
    class Connection:
        sock = None
        def __init__(self, host, port, **kw): calls.append((host, port))
        def request(self, method, path, headers): calls.append((method, path, headers))
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(npm.http.client, "HTTPSConnection", Connection)
    for version, checksum in (("8.0.0", sri(payload)), ("8.0.1", sri(b"different"))):
        with pytest.raises(npm.FetchError, match="outside"):
            npm._download("parse5", version, tmp_path / "refused.part", checksum)
    assert not calls
    assert npm._download("parse5", "8.0.1", tmp_path / "ok.part", sri(payload))["sri"] == sri(payload)
    assert calls[0] == ("registry.npmjs.org", 443)
    assert calls[1][0:2] == ("GET", "/parse5/-/parse5-8.0.1.tgz")
    assert not {key.lower() for key in calls[1][2]}.intersection({"authorization", "cookie", "proxy-authorization"})
    Response.status = 302
    with pytest.raises(npm.FetchError, match="redirect"):
        npm._download("parse5", "8.0.1", tmp_path / "redirect.part", sri(payload))
    assert not (tmp_path / "redirect.part").exists()


@pytest.mark.parametrize("selection,name,version,expected_sri", [
    ("katex", "katex", "0.16.38", "sha512-cjHooZUmIAUmDsHBN+1n8LaZdpmbj03LtYeYPyuYB7OuloiaeaV6N4LcfjcnHVzGWjVQmKrxxTrpDcmSzEZQwQ=="),
    ("katex-commander", "commander", "8.3.0", "sha512-OkTL9umf+He2DZkUq8f8J9of7yL6RJKI24dVITBmNfZBmri9zYZQrKkuXiKhyfPSu8tUhnVBB1iKXevvnlR4Ww=="),
])
def test_katex_selections_are_single_fixed_packages_with_bounded_plans(selection, name, version, expected_sri):
    selected, plan = npm._selection(selection)
    assert set(selected) == {name} and selected[name] == npm.KATEX_PACKAGES[name]
    assert selected[name] == {"version": version, "sri": expected_sri} and plan == 167_772_160
    selected[name]["version"] = "changed"
    assert npm._selection(selection)[0][name]["version"] == version


@pytest.mark.parametrize("selection", ["katex", "katex-commander"])
def test_each_katex_selection_requires_the_entire_exact_owner_lock_graph(tmp_path, monkeypatch, selection):
    packages = npm.KATEX_PACKAGES
    lock = {
        "lockfileVersion": "9.0",
        "importers": {"packages/@openmaic/generation": {"dependencies": {"katex": {"version": "0.16.38"}}}},
        "packages": {f'{name}@{row["version"]}': {"resolution": {"integrity": row["sri"]}}
                     for name, row in packages.items()},
        "snapshots": {"katex@0.16.38": {"dependencies": {"commander": "8.3.0"}}, "commander@8.3.0": {}},
    }
    owner = tmp_path / "katex-owner.zip"
    monkeypatch.setattr(npm, "OWNER_ZIP", owner)
    def check(candidate):
        raw = npm.yaml.safe_dump(candidate).encode()
        with zipfile.ZipFile(owner, "w") as archive_file:
            archive_file.writestr(npm.LOCK_MEMBER, raw)
        monkeypatch.setattr(npm, "OWNER_ZIP_SHA256", hashlib.sha256(owner.read_bytes()).hexdigest())
        monkeypatch.setattr(npm, "LOCK_SHA256", hashlib.sha256(raw).hexdigest())
        npm._locked_inputs(npm._selection(selection)[0])
    check(lock)
    for mutation in ("importer", "parent_version", "parent_sri", "child_sri", "edge", "extra_edge",
                     "optional", "parent_peer", "child_peer", "parent_null", "child_null", "child_extra"):
        changed = copy.deepcopy(lock)
        if mutation == "importer":
            changed["importers"] = {"packages/@openmaic/geometry": changed["importers"]["packages/@openmaic/generation"]}
        elif mutation == "parent_version":
            changed["importers"]["packages/@openmaic/generation"]["dependencies"]["katex"]["version"] = "0.0.0"
        elif mutation == "parent_sri":
            changed["packages"]["katex@0.16.38"]["resolution"]["integrity"] = "sha512-wrong"
        elif mutation == "child_sri":
            changed["packages"]["commander@8.3.0"]["resolution"]["integrity"] = "sha512-wrong"
        elif mutation == "edge":
            changed["snapshots"]["katex@0.16.38"]["dependencies"]["commander"] = "0.0.0"
        elif mutation == "extra_edge":
            changed["snapshots"]["katex@0.16.38"]["dependencies"]["other"] = "1"
        elif mutation == "optional":
            changed["snapshots"]["katex@0.16.38"]["optionalDependencies"] = {"other": "1"}
        elif mutation == "parent_peer":
            changed["packages"]["katex@0.16.38"]["peerDependencies"] = {"other": "*"}
        elif mutation == "child_peer":
            changed["packages"]["commander@8.3.0"]["peerDependencies"] = {"other": "*"}
        elif mutation == "parent_null":
            changed["snapshots"]["katex@0.16.38"] = None
        elif mutation == "child_null":
            changed["snapshots"]["commander@8.3.0"] = None
        else:
            changed["snapshots"]["commander@8.3.0"] = {"unexpected": "value"}
        with pytest.raises(npm.FetchError, match="KaTeX"):
            check(changed)


def test_katex_archives_require_the_single_exact_declared_edge():
    npm._inspect_archive(archive("katex", "0.16.38", manifest_extra={"dependencies": {"commander": "^8.3.0"}}), "katex", "0.16.38")
    npm._inspect_archive(archive("commander", "8.3.0"), "commander", "8.3.0")
    for extra in ({}, {"dependencies": {"commander": "^9.0.0"}},
                  {"dependencies": {"commander": "^8.3.0", "other": "1"}},
                  {"dependencies": {"commander": "^8.3.0"}, "optionalDependencies": {"other": "1"}}):
        with pytest.raises(npm.FetchError, match="pinned-edge"):
            npm._inspect_archive(archive("katex", "0.16.38", manifest_extra=extra), "katex", "0.16.38")
    with pytest.raises(npm.FetchError, match="dependency-free"):
        npm._inspect_archive(archive("commander", "8.3.0", manifest_extra={"dependencies": {"other": "1"}}), "commander", "8.3.0")


@pytest.mark.parametrize("selection,name", [("katex", "katex"), ("katex-commander", "commander")])
def test_katex_single_selection_retains_only_the_selected_archive(growth, monkeypatch, selection, name):
    packages = copy.deepcopy(npm.KATEX_PACKAGES)
    version = packages[name]["version"]
    payload = archive(name, version, manifest_extra={"dependencies": {"commander": "^8.3.0"}} if name == "katex" else None)
    packages[name]["sri"] = sri(payload)
    monkeypatch.setattr(npm, "KATEX_PACKAGES", packages)
    def download(actual_name, actual_version, part, expected):
        assert (actual_name, actual_version, expected) == (name, version, sri(payload))
        write_native(part, payload)
        return {"archive_bytes": len(payload), "sri": expected}
    monkeypatch.setattr(npm, "_download", download)
    result = npm.run(growth.context, selection)
    target = growth.paths["cache"] / "npm" / ("openmaic-owner-" + npm.LOCK_SHA256) / growth.paths["run"].name
    assert [row["name"] for row in result] == [name]
    assert read_native(target / f"{name}-{version}.tgz") == payload
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["selection"] == selection and receipt["planned_payload_bytes"] == 167_772_160
    assert receipt["copy_outcome"] == "VERIFIED_ARCHIVES_AND_LICENSE_FILES"


@pytest.mark.parametrize("name", ["katex", "commander"])
def test_katex_fixed_https_rejects_wrong_identity_and_redirect(tmp_path, monkeypatch, name):
    payload = b"synthetic public archive"
    packages = copy.deepcopy(npm.KATEX_PACKAGES)
    version = packages[name]["version"]
    packages[name]["sri"] = sri(payload)
    monkeypatch.setattr(npm, "KATEX_PACKAGES", packages)
    monkeypatch.setattr(npm, "_tls_context", lambda: "system-trust")
    calls = []
    class Response:
        status = 200
        def __init__(self): self.data = io.BytesIO(payload)
        def getheader(self, key, default=None): return default
        def read(self, count): return self.data.read(count)
    class Connection:
        sock = None
        def __init__(self, host, port, **kw): calls.append((host, port))
        def request(self, method, path, headers): calls.append((method, path, headers))
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(npm.http.client, "HTTPSConnection", Connection)
    for bad_version, bad_sri in (("0.0.0", sri(payload)), (version, sri(b"different"))):
        with pytest.raises(npm.FetchError, match="outside"):
            npm._download(name, bad_version, tmp_path / "refused.part", bad_sri)
    assert not calls
    assert npm._download(name, version, tmp_path / "ok.part", sri(payload))["sri"] == sri(payload)
    assert calls[0] == ("registry.npmjs.org", 443)
    assert calls[1][0:2] == ("GET", f"/{name}/-/{name}-{version}.tgz")
    assert not {key.lower() for key in calls[1][2]}.intersection({"authorization", "cookie", "proxy-authorization"})
    Response.status = 302
    with pytest.raises(npm.FetchError, match="redirect"):
        npm._download(name, version, tmp_path / "redirect.part", sri(payload))
    assert not (tmp_path / "redirect.part").exists()


POSTCSS_FIXED = [
    ("postcss", "postcss", "8.5.23", "sha512-g50586zr4bZmwFiTlflMu8E0bDTb5I5gertgwAKmsdUlTQIhZtunzUlD1WSzwcVWPoAVpsrA6vlfCD7oXvRwgg=="),
    ("postcss-nanoid", "nanoid", "3.3.19", "sha512-Y2tUNy4ouw6tq5oDSKeQYGOyhkUBhNOcGV/02KC+6kd9eDGqdZd++mjMiIDilrBYvjEnCYvVtsuHCuP+okSfug=="),
    ("postcss-picocolors", "picocolors", "1.1.1", "sha512-xceH2snhtb5M9liqDsmEw56le376mTZkEX/jEb/RxNFyegNul7eNslCXP9FDj/Lcu0X8KEyMceP2ntpaHrDEVA=="),
    ("postcss-source-map", "source-map-js", "1.2.1", "sha512-UXWMKhLOwVKb728IUtQPXxfYU+usdybtUrK/8uGE8CQMvrhOpwvzDBwj0QhSL7MQc7vIsISBG8VQ8+IDQxpfQA=="),
]


@pytest.mark.parametrize("selection,name,version,expected_sri", POSTCSS_FIXED)
def test_postcss_each_selection_is_one_fixed_package(selection, name, version, expected_sri):
    selected, plan = npm._selection(selection)
    assert selected == {name: {"version": version, "sri": expected_sri}} and plan == 167_772_160
    selected[name]["version"] = "changed"
    assert npm._selection(selection)[0][name]["version"] == version
    assert npm._selection("default")[0]["nanoid"]["version"] == "5.1.14"


@pytest.mark.parametrize("selection,name,version,expected_sri", POSTCSS_FIXED)
def test_each_postcss_selection_requires_the_complete_fixed_lock_graph(tmp_path, monkeypatch, selection, name, version, expected_sri):
    packages = npm.POSTCSS_PACKAGES
    parent_key = "postcss@8.5.23"
    lock = {
        "lockfileVersion": "9.0",
        "importers": {"packages/@openmaic/generation": {"dependencies": {"postcss": {"version": "8.5.23"}}}},
        "packages": {f'{key}@{row["version"]}': {"resolution": {"integrity": row["sri"]}}
                     for key, row in packages.items()},
        "snapshots": {"postcss@8.5.23": {"dependencies": {"nanoid": "3.3.19", "picocolors": "1.1.1", "source-map-js": "1.2.1"}},
                      "nanoid@3.3.19": {}, "picocolors@1.1.1": {}, "source-map-js@1.2.1": {}},
    }
    owner = tmp_path / "postcss-owner.zip"
    monkeypatch.setattr(npm, "OWNER_ZIP", owner)
    def check(candidate):
        raw = npm.yaml.safe_dump(candidate).encode()
        with zipfile.ZipFile(owner, "w") as archive_file:
            archive_file.writestr(npm.LOCK_MEMBER, raw)
        monkeypatch.setattr(npm, "OWNER_ZIP_SHA256", hashlib.sha256(owner.read_bytes()).hexdigest())
        monkeypatch.setattr(npm, "LOCK_SHA256", hashlib.sha256(raw).hexdigest())
        npm._locked_inputs(npm._selection(selection)[0])
    check(lock)
    for mutation in ("importer", "parent_version", "parent_sri", "child_sri", "picocolors_sri", "source_map_sri", "edge", "extra_edge", "optional",
                     "parent_peer", "child_peer", "parent_null", "child_null", "child_extra"):
        changed = copy.deepcopy(lock)
        if mutation == "importer":
            changed["importers"] = {"packages/@openmaic/geometry": changed["importers"]["packages/@openmaic/generation"]}
        elif mutation == "parent_version":
            changed["importers"]["packages/@openmaic/generation"]["dependencies"]["postcss"]["version"] = "8.5.15"
        elif mutation == "parent_sri":
            changed["packages"][parent_key]["resolution"]["integrity"] = "sha512-wrong"
        elif mutation == "child_sri":
            changed["packages"]["nanoid@3.3.19"]["resolution"]["integrity"] = "sha512-wrong"
        elif mutation == "picocolors_sri":
            changed["packages"]["picocolors@1.1.1"]["resolution"]["integrity"] = "sha512-wrong"
        elif mutation == "source_map_sri":
            changed["packages"]["source-map-js@1.2.1"]["resolution"]["integrity"] = "sha512-wrong"
        elif mutation == "edge":
            changed["snapshots"][parent_key]["dependencies"]["nanoid"] = "5.1.14"
        elif mutation == "extra_edge":
            changed["snapshots"][parent_key]["dependencies"]["other"] = "1"
        elif mutation == "optional":
            changed["snapshots"][parent_key]["optionalDependencies"] = {"other": "1"}
        elif mutation == "parent_peer":
            changed["packages"][parent_key]["peerDependencies"] = {"other": "*"}
        elif mutation == "child_peer":
            changed["packages"]["nanoid@3.3.19"]["peerDependencies"] = {"other": "*"}
        elif mutation == "parent_null":
            changed["snapshots"][parent_key] = None
        elif mutation == "child_null":
            changed["snapshots"]["nanoid@3.3.19"] = None
        else:
            changed["snapshots"]["nanoid@3.3.19"] = {"unexpected": "value"}
        with pytest.raises(npm.FetchError, match="PostCSS"):
            check(changed)


@pytest.mark.parametrize("selection,name,version,expected_sri", POSTCSS_FIXED)
def test_postcss_archive_manifest_matches_pinned_edges(selection, name, version, expected_sri):
    edges = {"nanoid": "^3.3.16", "picocolors": "^1.1.1", "source-map-js": "^1.2.1"}
    extra = {"dependencies": edges} if name == "postcss" else {}
    npm._inspect_archive(archive(name, version, manifest_extra=extra), name, version)
    mutated = {"dependencies": {**edges, "nanoid": "^5.0.0"}} if name == "postcss" else {"dependencies": {"other": "1"}}
    with pytest.raises(npm.FetchError, match="dependency-free or pinned-edge"):
        npm._inspect_archive(archive(name, version, manifest_extra=mutated), name, version)


@pytest.mark.parametrize("selection,name,version,expected_sri", POSTCSS_FIXED)
def test_postcss_single_selection_retains_only_the_selected_archive(growth, monkeypatch, selection, name, version, expected_sri):
    packages = copy.deepcopy(npm.POSTCSS_PACKAGES)
    extra = {"dependencies": {"nanoid": "^3.3.16", "picocolors": "^1.1.1", "source-map-js": "^1.2.1"}} if name == "postcss" else {}
    payload = archive(name, version, manifest_extra=extra)
    packages[name]["sri"] = sri(payload)
    monkeypatch.setattr(npm, "POSTCSS_PACKAGES", packages)
    def download(actual_name, actual_version, part, expected):
        assert (actual_name, actual_version, expected) == (name, version, sri(payload))
        write_native(part, payload)
        return {"archive_bytes": len(payload), "sri": expected}
    monkeypatch.setattr(npm, "_download", download)
    result = npm.run(growth.context, selection)
    target = growth.paths["cache"] / "npm" / ("openmaic-owner-" + npm.LOCK_SHA256) / growth.paths["run"].name
    assert [row["name"] for row in result] == [name]
    assert read_native(target / f"{name}-{version}.tgz") == payload
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["selection"] == selection and receipt["planned_payload_bytes"] == 167_772_160
    assert receipt["copy_outcome"] == "VERIFIED_ARCHIVES_AND_LICENSE_FILES"


@pytest.mark.parametrize("selection,name,version,expected_sri", POSTCSS_FIXED)
def test_postcss_fixed_https_rejects_wrong_identity_and_redirect(tmp_path, monkeypatch, selection, name, version, expected_sri):
    payload = b"synthetic public archive"
    packages = copy.deepcopy(npm.POSTCSS_PACKAGES)
    packages[name]["sri"] = sri(payload)
    monkeypatch.setattr(npm, "POSTCSS_PACKAGES", packages)
    monkeypatch.setattr(npm, "_tls_context", lambda: "system-trust")
    calls = []
    class Response:
        status = 200
        def __init__(self): self.data = io.BytesIO(payload)
        def getheader(self, key, default=None): return default
        def read(self, count): return self.data.read(count)
    class Connection:
        sock = None
        def __init__(self, host, port, **kw): calls.append((host, port))
        def request(self, method, path, headers): calls.append((method, path, headers))
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(npm.http.client, "HTTPSConnection", Connection)
    for bad_version, bad_sri in (("0.0.0", sri(payload)), (version, sri(b"different"))):
        with pytest.raises(npm.FetchError, match="outside"):
            npm._download(name, bad_version, tmp_path / "refused.part", bad_sri)
    assert not calls
    assert npm._download(name, version, tmp_path / "ok.part", sri(payload))["sri"] == sri(payload)
    assert calls[0] == ("registry.npmjs.org", 443)
    assert calls[1][0:2] == ("GET", f"/{name}/-/{name}-{version}.tgz")
    assert not {key.lower() for key in calls[1][2]}.intersection({"authorization", "cookie", "proxy-authorization"})
    Response.status = 302
    with pytest.raises(npm.FetchError, match="redirect"):
        npm._download(name, version, tmp_path / "redirect.part", sri(payload))
    assert not (tmp_path / "redirect.part").exists()


def test_geometry_lock_requires_its_own_importer_and_all_fixed_dependency_free_entries(tmp_path, monkeypatch):
    packages = npm._selection("geometry")[0]
    lock = {
        "lockfileVersion": "9.0",
        "importers": {"packages/@openmaic/geometry": {"dependencies": {
            name: {"version": row["version"]} for name, row in packages.items()}}},
        "packages": {f'{name}@{row["version"]}': {"resolution": {"integrity": row["sri"]}}
                     for name, row in packages.items()},
        "snapshots": {f'{name}@{row["version"]}': {} for name, row in packages.items()},
    }
    owner = tmp_path / "geometry-owner.zip"
    monkeypatch.setattr(npm, "OWNER_ZIP", owner)

    def check(candidate):
        raw = npm.yaml.safe_dump(candidate).encode()
        with zipfile.ZipFile(owner, "w") as archive_file:
            archive_file.writestr(npm.LOCK_MEMBER, raw)
        monkeypatch.setattr(npm, "OWNER_ZIP_SHA256", hashlib.sha256(owner.read_bytes()).hexdigest())
        monkeypatch.setattr(npm, "LOCK_SHA256", hashlib.sha256(raw).hexdigest())
        npm._locked_inputs(packages)

    check(lock)
    for name, row in packages.items():
        key = f'{name}@{row["version"]}'
        for mutation in ("wrong_importer", "version", "sri", "dependency", "optional", "peer", "snapshot", "null_snapshot", "false_snapshot", "list_snapshot", "extra_snapshot"):
            changed = copy.deepcopy(lock)
            if mutation == "wrong_importer":
                changed["importers"]["packages/@openmaic/generation"] = copy.deepcopy(changed["importers"]["packages/@openmaic/geometry"])
                del changed["importers"]["packages/@openmaic/geometry"]["dependencies"][name]
            elif mutation == "version":
                changed["importers"]["packages/@openmaic/geometry"]["dependencies"][name]["version"] = "0.0.0"
            elif mutation == "sri":
                changed["packages"][key]["resolution"]["integrity"] = "sha512-wrong"
            elif mutation == "dependency":
                changed["snapshots"][key]["dependencies"] = {"unexpected": "1.0.0"}
            elif mutation == "optional":
                changed["snapshots"][key]["optionalDependencies"] = {"unexpected": "1.0.0"}
            elif mutation == "peer":
                changed["packages"][key]["peerDependencies"] = {"unexpected": "*"}
            elif mutation == "null_snapshot":
                changed["snapshots"][key] = None
            elif mutation == "false_snapshot":
                changed["snapshots"][key] = False
            elif mutation == "list_snapshot":
                changed["snapshots"][key] = []
            elif mutation == "extra_snapshot":
                changed["snapshots"][key] = {"unexpected": "value"}
            else:
                del changed["snapshots"][key]
            with pytest.raises(npm.FetchError, match="exact dependency-free"):
                check(changed)


@pytest.mark.parametrize("name", ["entities", "svg-pathdata", "tinycolor2"])
def test_geometry_archive_rejects_unlisted_runtime_dependencies(name):
    version = npm.GEOMETRY_PACKAGES[name]["version"]
    npm._inspect_archive(archive(name, version), name, version)
    for field in ("dependencies", "optionalDependencies", "peerDependencies", "bundledDependencies"):
        value = ["unexpected"] if field == "bundledDependencies" else {"unexpected": "1"}
        with pytest.raises(npm.FetchError, match="dependency-free"):
            npm._inspect_archive(archive(name, version, manifest_extra={field: value}), name, version)


def test_geometry_three_archives_retain_identity_and_use_combined_growth_review(growth, monkeypatch):
    payloads = {name: archive(name, row["version"]) for name, row in npm.GEOMETRY_PACKAGES.items()}
    packages = {name: {**row, "sri": sri(payloads[name])} for name, row in npm.GEOMETRY_PACKAGES.items()}
    monkeypatch.setattr(npm, "GEOMETRY_PACKAGES", packages)
    calls = []
    def download(name, version, part, expected):
        calls.append((name, version, expected))
        write_native(part, payloads[name])
        return {"archive_bytes": len(payloads[name]), "sri": expected}
    monkeypatch.setattr(npm, "_download", download)
    result = npm.run(growth.context, "geometry")
    target = growth.paths["cache"] / "npm" / ("openmaic-owner-" + npm.LOCK_SHA256) / growth.paths["run"].name
    assert {name for name, _, _ in calls} == set(packages) == {row["name"] for row in result}
    for name, row in packages.items():
        stem = f'{name}-{row["version"]}'
        assert read_native(target / f"{stem}.tgz") == payloads[name]
        assert read_native(target / stem / "LICENSE") == b"synthetic license text\n"
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["selection"] == "geometry" and receipt["planned_payload_bytes"] == 419_430_400
    assert receipt["copy_outcome"] == "VERIFIED_ARCHIVES_AND_LICENSE_FILES"
    assert receipt["deletion_authorized"] is False and len(growth.measures) == 2


@pytest.mark.parametrize("name", ["entities", "svg-pathdata", "tinycolor2"])
def test_geometry_download_uses_fixed_identity_and_registry_only(tmp_path, monkeypatch, name):
    payload = b"synthetic public archive"
    packages = copy.deepcopy(npm.GEOMETRY_PACKAGES)
    version = packages[name]["version"]
    packages[name]["sri"] = sri(payload)
    monkeypatch.setattr(npm, "GEOMETRY_PACKAGES", packages)
    monkeypatch.setattr(npm, "_tls_context", lambda: "system-trust")
    calls = []
    class Response:
        status = 200
        def __init__(self): self.data = io.BytesIO(payload)
        def getheader(self, key, default=None): return default
        def read(self, count): return self.data.read(count)
    class Connection:
        sock = None
        def __init__(self, host, port, **kw): calls.append((host, port, kw))
        def request(self, method, path, headers): calls.append((method, path, headers))
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(npm.http.client, "HTTPSConnection", Connection)
    for bad_version, bad_sri in (("0.0.0", sri(payload)), (version, sri(b"different"))):
        with pytest.raises(npm.FetchError, match="outside"):
            npm._download(name, bad_version, tmp_path / "refused.part", bad_sri)
    assert not calls
    assert npm._download(name, version, tmp_path / "ok.part", sri(payload))["sri"] == sri(payload)
    assert calls[0][0:2] == ("registry.npmjs.org", 443)
    assert calls[1][0:2] == ("GET", f"/{name}/-/{name}-{version}.tgz")
    assert not {key.lower() for key in calls[1][2]}.intersection({"authorization", "cookie", "proxy-authorization"})


@pytest.mark.parametrize("selection", ["geometry", "parse5", "katex", "katex-commander",
                                       "postcss", "postcss-nanoid", "postcss-picocolors", "postcss-source-map"])
def test_selected_growth_review_refuses_before_first_network_call(growth, monkeypatch, selection):
    monkeypatch.setattr(npm, "_download", lambda *_: pytest.fail("unexpected network"))
    growth.report["dev_root"][1]["bytes"] += 2 * 1024 ** 3
    with pytest.raises(npm.portable.GrowthReviewRequiredError):
        npm.run(growth.context, selection)
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["copy_outcome"] == "NOT_STARTED" and len(growth.measures) == 2


@pytest.mark.parametrize("selection,constant", [("geometry", "GEOMETRY_PACKAGES"), ("parse5", "PARSE5_PACKAGES")])
def test_selected_group_second_download_failure_preserves_partial_but_not_group_success(growth, monkeypatch, selection, constant):
    original = getattr(npm, constant)
    payloads = {name: archive(name, row["version"], manifest_extra={"dependencies": {"entities": "^8.0.0"}} if name == "parse5" else None)
                for name, row in original.items()}
    packages = {name: {**row, "sri": sri(payloads[name])} for name, row in original.items()}
    monkeypatch.setattr(npm, constant, packages)
    calls = []
    def download(name, version, part, expected):
        calls.append(name)
        if len(calls) == 2:
            write_native(part, b"synthetic failed partial")
            raise npm.FetchError("synthetic download failure")
        write_native(part, payloads[name])
        return {"archive_bytes": len(payloads[name]), "sri": expected}
    monkeypatch.setattr(npm, "_download", download)
    with pytest.raises(npm.FetchError, match="synthetic download failure"):
        npm.run(growth.context, selection)
    target = growth.paths["cache"] / "npm" / ("openmaic-owner-" + npm.LOCK_SHA256) / growth.paths["run"].name
    first = calls[0]
    assert len(calls) == 2 and read_native(target / f'{first}-{packages[first]["version"]}.tgz') == payloads[first]
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["copy_outcome"] == "STARTED" and [row["name"] for row in receipt["packages"]] == [first]
    assert receipt["original_error"]["type"] == "FetchError" and len(growth.measures) == 2


@pytest.mark.parametrize("name,version,bad_version,constant", SINGLE_DEPENDENCIES)
def test_single_package_lock_fails_closed_on_changed_identity_or_dependencies(tmp_path, monkeypatch, name, version, bad_version, constant):
    row = dict(getattr(npm, constant))
    key = f'{name}@{row["version"]}'
    lock = {"lockfileVersion": "9.0",
            "importers": {"packages/@openmaic/generation": {"dependencies": {
                name: {"specifier": f"^{version}", "version": row["version"]}}}},
            "packages": {key: {"resolution": {"integrity": row["sri"]}}},
            "snapshots": {key: {}}}
    owner = tmp_path / "owner-single.zip"
    monkeypatch.setattr(npm, "OWNER_ZIP", owner)

    def check(candidate):
        raw = npm.yaml.safe_dump(candidate).encode()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            z.writestr(npm.LOCK_MEMBER, raw)
        payload = buffer.getvalue()
        write_native(owner, payload)
        monkeypatch.setattr(npm, "OWNER_ZIP_SHA256", hashlib.sha256(payload).hexdigest())
        monkeypatch.setattr(npm, "LOCK_SHA256", hashlib.sha256(raw).hexdigest())
        npm._locked_inputs({name: row})

    check(lock)
    for mutation in ("direct", "version", "sri", "dependencies", "optional", "peer", "snapshot"):
        changed = copy.deepcopy(lock)
        if mutation == "direct":
            del changed["importers"]["packages/@openmaic/generation"]["dependencies"][name]
        elif mutation == "version":
            changed["importers"]["packages/@openmaic/generation"]["dependencies"][name]["version"] = bad_version
        elif mutation == "sri":
            changed["packages"][key]["resolution"]["integrity"] = "sha512-wrong"
        elif mutation == "dependencies":
            changed["snapshots"][key]["dependencies"] = {"unexpected": "1.0.0"}
        elif mutation == "optional":
            changed["snapshots"][key]["optionalDependencies"] = {"unexpected": "1.0.0"}
        elif mutation == "peer":
            changed["packages"][key]["peerDependencies"] = {"unexpected": "*"}
        else:
            del changed["snapshots"][key]
        with pytest.raises(npm.FetchError, match="exact dependency-free"):
            check(changed)
    check(lock)
    write_native(owner, read_native(owner) + b"tampered")
    with pytest.raises(npm.FetchError, match="Owner ZIP identity"):
        npm._locked_inputs({name: row})


def test_partial_json_owner_lock_requires_exact_version_sri_and_no_dependencies(tmp_path, monkeypatch):
    row = dict(npm.PARTIAL_JSON)
    key = f'partial-json@{row["version"]}'
    lock = {"lockfileVersion": "9.0",
            "importers": {"packages/@openmaic/generation": {"dependencies": {
                "partial-json": {"version": row["version"]}}}},
            "packages": {key: {"resolution": {"integrity": row["sri"]}}},
            "snapshots": {key: {}}}
    owner = tmp_path / "owner.zip"
    monkeypatch.setattr(npm, "OWNER_ZIP", owner)

    def check(candidate):
        raw = npm.yaml.safe_dump(candidate).encode()
        with zipfile.ZipFile(owner, "w") as z:
            z.writestr(npm.LOCK_MEMBER, raw)
        monkeypatch.setattr(npm, "OWNER_ZIP_SHA256", hashlib.sha256(owner.read_bytes()).hexdigest())
        monkeypatch.setattr(npm, "LOCK_SHA256", hashlib.sha256(raw).hexdigest())
        npm._locked_inputs({"partial-json": row})

    check(lock)
    for mutation in ("version", "sri", "dependencies", "optional", "peer", "missing_snapshot"):
        changed = copy.deepcopy(lock)
        if mutation == "version":
            changed["importers"]["packages/@openmaic/generation"]["dependencies"]["partial-json"]["version"] = "0.1.8"
        elif mutation == "sri":
            changed["packages"][key]["resolution"]["integrity"] = "sha512-wrong"
        elif mutation == "dependencies":
            changed["snapshots"][key]["dependencies"] = {"unexpected": "1.0.0"}
        elif mutation == "optional":
            changed["snapshots"][key]["optionalDependencies"] = {"unexpected": "1.0.0"}
        elif mutation == "peer":
            changed["packages"][key]["peerDependencies"] = {"unexpected": "*"}
        else:
            del changed["snapshots"][key]
        with pytest.raises(npm.FetchError, match="exact dependency-free"):
            check(changed)


def test_selection_is_fixed_before_storage_or_network(growth, monkeypatch):
    monkeypatch.setattr(npm, "_locked_inputs", lambda *_: pytest.fail("unexpected Owner input read"))
    monkeypatch.setattr(npm, "_download", lambda *_: pytest.fail("unexpected network"))
    for invalid in ("", "jsonrepair", "katex@0.16.38", "partial-json@0.1.7", "../../partial-json",
                    "postcss@8.5.23", "postcss-value-parser@4.2.0", "../../postcss-value-parser",
                    "POSTCSS-VALUE-PARSER", "es-module-lexer@2.0.0", "../../es-module-lexer", "ES-MODULE-LEXER"):
        with pytest.raises(npm.FetchError, match="unknown OpenMAIC npm selection"):
            npm.run(growth.context, invalid)
    assert not growth.measures
    assert not (growth.paths["run"] / "tmp/openmaic-locked-npm").exists()

    monkeypatch.setattr(sys, "argv", ["openmaic_npm_fetch", "--selection", "katex@0.16.38"])
    monkeypatch.setattr(npm.cargo_test_growth, "_owned_run", lambda: pytest.fail("unexpected run setup"))
    with pytest.raises(SystemExit) as error:
        npm.main()
    assert error.value.code == 2


def test_partial_json_uses_own_plan_and_retains_verified_package(growth, monkeypatch):
    payload = archive("partial-json", "0.1.7", license_name="MIT")
    monkeypatch.setattr(npm, "PARTIAL_JSON", {"version": "0.1.7", "sri": sri(payload)})
    calls = []
    def download(name, version, part, expected):
        calls.append((name, version, expected))
        write_native(part, payload)
        return {"archive_bytes": len(payload), "sri": expected}
    monkeypatch.setattr(npm, "_download", download)
    before = (growth.baseline.read_bytes(), growth.pointer.read_bytes())
    result = npm.run(growth.context, "partial-json")
    target = growth.paths["cache"] / "npm" / ("openmaic-owner-" + npm.LOCK_SHA256) / growth.paths["run"].name
    assert calls == [("partial-json", "0.1.7", sri(payload))]
    assert len(result) == 1 and result[0]["name"] == "partial-json" and result[0]["license"] == "MIT"
    by_path = {item["path"]: item for item in result[0]["files"]}
    assert by_path["index.js"]["sha256"] == hashlib.sha256(b"export const value = 1;\n").hexdigest()
    assert read_native(target / "partial-json-0.1.7.tgz") == payload
    assert read_native(target / "partial-json-0.1.7/LICENSE") == b"synthetic license text\n"
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["selection"] == "partial-json" and receipt["planned_payload_bytes"] == 167_772_160
    assert receipt["copy_outcome"] == "VERIFIED_ARCHIVES_AND_LICENSE_FILES"
    assert set(receipt["alternative_projected_reviews"]) == {"runs/", "build/"}
    assert receipt["deletion_authorized"] is False and receipt["measurement_status"] == "PARTIAL"
    assert len(growth.measures) == 2 and before == (growth.baseline.read_bytes(), growth.pointer.read_bytes())


def test_partial_json_rejects_non_mit_or_wrong_identity_before_extraction():
    for payload in (archive("partial-json", "0.1.7", license_name="Apache-2.0"),
                    archive("partial-json", "0.1.8", license_name="MIT"),
                    archive("another", "0.1.7", license_name="MIT")):
        with pytest.raises(npm.FetchError, match="identity or explicit supported license"):
            npm._inspect_archive(payload, "partial-json", "0.1.7")


def test_partial_json_direct_fetch_uses_only_fixed_url_and_sri(tmp_path, monkeypatch):
    payload = b"synthetic public archive"
    monkeypatch.setattr(npm, "PARTIAL_JSON", {"version": "0.1.7", "sri": sri(payload)})
    monkeypatch.setattr(npm, "_tls_context", lambda: "system-trust")
    calls = []
    class Response:
        status = 200
        def __init__(self): self.data = io.BytesIO(payload)
        def getheader(self, key, default=None):
            return str(len(payload)) if key == "Content-Length" else default
        def read(self, count): return self.data.read(count)
    class Connection:
        sock = None
        def __init__(self, host, port, **kw): calls.append((host, port, kw))
        def request(self, method, path, headers): calls.append((method, path, headers))
        def getresponse(self): return Response()
        def close(self): calls.append(("closed",))
    monkeypatch.setattr(npm.http.client, "HTTPSConnection", Connection)
    for version, checksum in (("0.1.8", sri(payload)), ("0.1.7", sri(b"different"))):
        with pytest.raises(npm.FetchError, match="outside"):
            npm._download("partial-json", version, tmp_path / "refused.part", checksum)
    assert not calls and not (tmp_path / "refused.part").exists()
    part = tmp_path / "accepted.part"
    result = npm._download("partial-json", "0.1.7", part, sri(payload))
    assert result["sri"] == sri(payload) and read_native(part) == payload
    assert calls[0][0:2] == ("registry.npmjs.org", 443)
    assert calls[1][0:2] == ("GET", "/partial-json/-/partial-json-0.1.7.tgz")
    assert not {key.lower() for key in calls[1][2]}.intersection({"authorization", "cookie", "proxy-authorization"})


def test_partial_json_changed_archive_stops_before_extract_and_records_post(growth, monkeypatch):
    expected = archive("partial-json", "0.1.7", license_name="MIT")
    monkeypatch.setattr(npm, "PARTIAL_JSON", {"version": "0.1.7", "sri": sri(expected)})
    def altered(name, version, part, checksum):
        payload = archive("partial-json", "0.1.8", license_name="MIT")
        write_native(part, payload)
        return {"archive_bytes": len(payload), "sri": checksum}
    monkeypatch.setattr(npm, "_download", altered)
    with pytest.raises(npm.FetchError, match="changed after download"):
        npm.run(growth.context, "partial-json")
    target = growth.paths["cache"] / "npm" / ("openmaic-owner-" + npm.LOCK_SHA256) / growth.paths["run"].name
    assert os.path.isdir(npm.portable.native(target)) and not os.listdir(npm.portable.native(target))
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["selection"] == "partial-json" and receipt["packages"] == []
    assert receipt["planned_payload_bytes"] == 167_772_160 and len(growth.measures) == 2


@pytest.mark.parametrize("name,version,bad_version,constant", SINGLE_DEPENDENCIES)
def test_single_manifest_requires_exact_identity_license_and_no_runtime_dependencies(name, version, bad_version, constant):
    good = archive(name, version, manifest_extra={"dependencies": {}, "optionalDependencies": {},
                                                  "peerDependencies": {}, "bundledDependencies": [],
                                                  "devDependencies": {"test-only": "1.0.0"}})
    _, _, description = npm._inspect_archive(good, name, version)
    assert description["name"] == name and description["version"] == version
    for payload in (archive(name, bad_version), archive("other", version),
                    archive(name, version, license_name="UNLICENSED")):
        with pytest.raises(npm.FetchError, match="identity or explicit supported license"):
            npm._inspect_archive(payload, name, version)
    for field, value in (("dependencies", {"extra": "1.0.0"}), ("dependencies", []),
                         ("optionalDependencies", {"extra": "1.0.0"}),
                         ("peerDependencies", {"extra": "*"}),
                         ("bundledDependencies", ["extra"]), ("bundleDependencies", True)):
        payload = archive(name, version, manifest_extra={field: value})
        with pytest.raises(npm.FetchError, match="dependency-free"):
            npm._inspect_archive(payload, name, version)


@pytest.mark.parametrize("name,version,bad_version,constant", SINGLE_DEPENDENCIES)
def test_synthetic_single_package_records_plan_and_never_runs_scripts(growth, monkeypatch, name, version, bad_version, constant):
    payload = archive(name, version,
                      manifest_extra={"scripts": {"preinstall": "must-never-run"}})
    monkeypatch.setattr(npm, constant, {"version": version, "sri": sri(payload)})
    calls = []
    def download(name, version, part, expected):
        calls.append((name, version, expected))
        write_native(part, payload)
        return {"archive_bytes": len(payload), "sri": expected}
    monkeypatch.setattr(npm, "_download", download)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("package script was executed"))
    monkeypatch.setattr(os, "system", lambda *a: pytest.fail("package script was executed"))
    before = (read_native(growth.baseline), read_native(growth.pointer))
    result = npm.run(growth.context, name)
    target = growth.paths["cache"] / "npm" / ("openmaic-owner-" + npm.LOCK_SHA256) / growth.paths["run"].name
    assert calls == [(name, version, sri(payload))]
    assert len(result) == 1 and result[0]["name"] == name and result[0]["license"] == "MIT"
    assert read_native(target / f"{name}-{version}.tgz") == payload
    for item in result[0]["files"]:
        assert hashlib.sha256(read_native(target / f"{name}-{version}" / item["path"])).hexdigest() == item["sha256"]
    receipt = json.loads(read_native(growth.paths["artifacts"] / "portable-storage-receipt.json"))
    assert receipt["selection"] == name and receipt["planned_payload_bytes"] == 167_772_160
    assert receipt["copy_outcome"] == "VERIFIED_ARCHIVES_AND_LICENSE_FILES"
    assert len(growth.measures) == 2 and before == (read_native(growth.baseline), read_native(growth.pointer))


@pytest.mark.parametrize("name,version,bad_version,constant", SINGLE_DEPENDENCIES)
def test_single_package_budget_review_blocks_before_network_or_extraction(growth, monkeypatch, name, version, bad_version, constant):
    monkeypatch.setattr(npm, "_download", lambda *a, **k: pytest.fail("unexpected network"))
    growth.report["dev_root"][1]["bytes"] += 2 * 1024 ** 3
    with pytest.raises(npm.portable.GrowthReviewRequiredError):
        npm.run(growth.context, name)
    receipt = json.loads(read_native(growth.paths["artifacts"] / "portable-storage-receipt.json"))
    assert receipt["selection"] == name and receipt["planned_payload_bytes"] == 167_772_160
    assert receipt["copy_outcome"] == "NOT_STARTED" and receipt["packages"] == []
    assert len(growth.measures) == 2 and not npm._present(growth.paths["run"] / "tmp/openmaic-locked-npm")


@pytest.mark.parametrize("name,version,bad_version,constant", SINGLE_DEPENDENCIES)
def test_single_modified_download_rejected_before_extraction(growth, monkeypatch, name, version, bad_version, constant):
    expected = archive(name, version)
    monkeypatch.setattr(npm, constant, {"version": version, "sri": sri(expected)})
    def altered(package_name, package_version, part, checksum):
        payload = archive(package_name, bad_version)
        write_native(part, payload)
        return {"archive_bytes": len(payload), "sri": checksum}
    monkeypatch.setattr(npm, "_download", altered)
    with pytest.raises(npm.FetchError, match="changed after download"):
        npm.run(growth.context, name)
    target = growth.paths["cache"] / "npm" / ("openmaic-owner-" + npm.LOCK_SHA256) / growth.paths["run"].name
    assert os.path.isdir(npm.portable.native(target)) and not os.listdir(npm.portable.native(target))
    receipt = json.loads(read_native(growth.paths["artifacts"] / "portable-storage-receipt.json"))
    assert receipt["selection"] == name and receipt["packages"] == []
    assert receipt["planned_payload_bytes"] == 167_772_160 and len(growth.measures) == 2


@pytest.mark.parametrize("name,version,bad_version,constant", SINGLE_DEPENDENCIES)
def test_single_fixed_https_rejects_unknown_version_sri_and_redirect(tmp_path, monkeypatch, name, version, bad_version, constant):
    payload = b"synthetic public archive"
    monkeypatch.setattr(npm, constant, {"version": version, "sri": sri(payload)})
    monkeypatch.setattr(npm, "_tls_context", lambda: "system-trust")
    calls = []
    class Response:
        status = 200
        def __init__(self): self.data = io.BytesIO(payload)
        def getheader(self, key, default=None):
            return str(len(payload)) if key == "Content-Length" else default
        def read(self, count): return self.data.read(count)
    class Connection:
        sock = None
        def __init__(self, host, port, **kw): calls.append((host, port, kw))
        def request(self, method, path, headers): calls.append((method, path, headers))
        def getresponse(self): return Response()
        def close(self): calls.append(("closed",))
    monkeypatch.setattr(npm.http.client, "HTTPSConnection", Connection)
    for candidate_version, checksum in ((bad_version, sri(payload)), (version, sri(b"wrong"))):
        with pytest.raises(npm.FetchError, match="outside"):
            npm._download(name, candidate_version, tmp_path / "refused.part", checksum)
    assert not calls and not npm._present(tmp_path / "refused.part")
    part = tmp_path / "accepted.part"
    assert npm._download(name, version, part, sri(payload))["sri"] == sri(payload)
    assert read_native(part) == payload and calls[0][0:2] == ("registry.npmjs.org", 443)
    assert calls[0][2]["context"] == "system-trust"
    assert calls[1][0:2] == ("GET", f"/{name}/-/{name}-{version}.tgz")
    assert not {key.lower() for key in calls[1][2]}.intersection({"authorization", "cookie", "proxy-authorization"})
    Response.status = 302
    with pytest.raises(npm.FetchError, match="redirect"):
        npm._download(name, version, tmp_path / "redirect.part", sri(payload))
    assert not npm._present(tmp_path / "redirect.part")


def test_owner_zip_and_lock_bind_the_exact_two_versions(tmp_path, monkeypatch):
    packages = {"jsonrepair": {"version": "3.13.3", "sri": "sha512-synthetic-one"},
                "nanoid": {"version": "5.1.14", "sri": "sha512-synthetic-two"}}
    importer = {name: {"version": row["version"]} for name, row in packages.items()}
    entries = {f'{name}@{row["version"]}': {"resolution": {"integrity": row["sri"]}}
               for name, row in packages.items()}
    snapshots = {key: {} for key in entries}
    lock = {"lockfileVersion": "9.0", "importers": {"packages/@openmaic/generation": {"dependencies": importer}},
            "packages": entries, "snapshots": snapshots}
    raw = npm.yaml.safe_dump(lock).encode()
    owner = tmp_path / "owner.zip"
    with zipfile.ZipFile(owner, "w") as z:
        z.writestr(npm.LOCK_MEMBER, raw)
    monkeypatch.setattr(npm, "OWNER_ZIP", owner)
    monkeypatch.setattr(npm, "OWNER_ZIP_SHA256", hashlib.sha256(owner.read_bytes()).hexdigest())
    monkeypatch.setattr(npm, "LOCK_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(npm, "PACKAGES", packages)
    npm._locked_inputs()
    with zipfile.ZipFile(owner, "w") as z:
        z.writestr(npm.LOCK_MEMBER, raw.replace(b"3.13.3", b"3.13.4"))
    monkeypatch.setattr(npm, "OWNER_ZIP_SHA256", hashlib.sha256(owner.read_bytes()).hexdigest())
    with pytest.raises(npm.FetchError, match="lock identity"):
        npm._locked_inputs()


def test_owner_zip_duplicate_lock_members_are_rejected(tmp_path, monkeypatch):
    owner = tmp_path / "owner.zip"
    with pytest.warns(UserWarning):
        with zipfile.ZipFile(owner, "w") as z:
            z.writestr(npm.LOCK_MEMBER, b"first")
            z.writestr(npm.LOCK_MEMBER, b"second")
    monkeypatch.setattr(npm, "OWNER_ZIP", owner)
    monkeypatch.setattr(npm, "OWNER_ZIP_SHA256", hashlib.sha256(owner.read_bytes()).hexdigest())
    with pytest.raises(npm.FetchError, match="duplicated"):
        npm._locked_inputs()


def test_formal_npm_role_is_exact_primary_cache_and_cannot_borrow_ci(growth, monkeypatch):
    target = growth.paths["cache"] / "npm" / ("openmaic-owner-" + npm.LOCK_SHA256) / growth.paths["run"].name
    for bad in (target.parent, target.parent / "another", growth.paths["cache"] / "elsewhere"):
        with pytest.raises(ValueError, match="exact project cache"):
            npm.portable._storage_pre(bad, 1, growth.context, formal_npm=True)
    with pytest.raises(ValueError, match="mutually exclusive"):
        npm.portable._storage_pre(target, 1, growth.context, formal_npm=True, formal_cargo=True)
    with pytest.raises(ValueError, match="exact project cache"):
        npm.portable._storage_pre(target, 1, {**growth.context, "ci_checkpoint": {}}, formal_npm=True)
    monkeypatch.setattr(npm.dev, "git", lambda *args: str(growth.paths["root"] / ".git/worktrees/other"))
    with pytest.raises(ValueError, match="exact project cache"):
        npm.portable._storage_pre(target, 1, growth.context, formal_npm=True)
    assert not growth.measures


def test_two_verified_packages_are_retained_without_any_package_execution(growth, monkeypatch):
    payloads = {name: archive(name, row["version"], license_name="MIT" if name == "nanoid" else "ISC")
                for name, row in npm.PACKAGES.items()}
    packages = {name: {**row, "sri": sri(payloads[name])} for name, row in npm.PACKAGES.items()}
    monkeypatch.setattr(npm, "PACKAGES", packages)
    calls = []
    def download(name, version, part, expected):
        calls.append((name, version, expected))
        write_native(part, payloads[name])
        return {"archive_bytes": len(payloads[name]), "sri": expected}
    monkeypatch.setattr(npm, "_download", download)
    before = (growth.baseline.read_bytes(), growth.pointer.read_bytes())
    result = npm.run(growth.context)
    target = growth.paths["cache"] / "npm" / ("openmaic-owner-" + npm.LOCK_SHA256) / growth.paths["run"].name
    assert len(calls) == 2 and {row["name"] for row in result} == {"jsonrepair", "nanoid"}
    assert {row["license"] for row in result} == {"MIT", "ISC"}
    for row in result:
        by_path = {item["path"]: item for item in row["files"]}
        assert by_path["index.js"]["sha256"] == hashlib.sha256(b"export const value = 1;\n").hexdigest()
        assert by_path["LICENSE"]["sha256"] == hashlib.sha256(b"synthetic license text\n").hexdigest()
    for name, row in packages.items():
        stem = f'{name}-{row["version"]}'
        assert read_native(target / f"{stem}.tgz") == payloads[name]
        assert read_native(target / stem / "LICENSE") == b"synthetic license text\n"
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["projected_storage_class"] == "cache/"
    assert receipt["planned_payload_bytes"] == 293_601_280
    assert receipt["copy_outcome"] == "VERIFIED_ARCHIVES_AND_LICENSE_FILES"
    assert set(receipt["alternative_projected_reviews"]) == {"runs/", "build/"}
    assert receipt["deletion_authorized"] is False and receipt["measurement_status"] == "PARTIAL"
    assert len(growth.measures) == 2 and before == (growth.baseline.read_bytes(), growth.pointer.read_bytes())
    with pytest.raises(ValueError, match="already exists"):
        npm.run(growth.context)


def test_review_or_unmeasured_target_blocks_network_before_output(growth, monkeypatch):
    monkeypatch.setattr(npm, "_download", lambda *a, **k: pytest.fail("unexpected network"))
    growth.report["dev_root"][1]["bytes"] += 2 * 1024 ** 3
    with pytest.raises(npm.portable.GrowthReviewRequiredError):
        npm.run(growth.context)
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["copy_outcome"] == "NOT_STARTED" and len(growth.measures) == 2
    assert not (growth.paths["run"] / "tmp/openmaic-locked-npm").exists()


@pytest.mark.parametrize("field", ["errors", "excluded_private", "links"])
def test_skipped_or_redirected_target_blocks_network(growth, monkeypatch, field):
    monkeypatch.setattr(npm, "_download", lambda *a, **k: pytest.fail("unexpected network"))
    target = growth.paths["cache"] / "npm" / ("openmaic-owner-" + npm.LOCK_SHA256) / growth.paths["run"].name
    member = str(target / "unknown")
    value = member if field == "excluded_private" else {"link" if field == "links" else "path": member}
    growth.report["dev_root"][0][field].append(value)
    with pytest.raises(ValueError, match="skipped, private or redirected"):
        npm.run(growth.context)
    assert len(growth.measures) == 2


@pytest.mark.parametrize("bad_name", ["package/../escape", "package/CON.txt", "package/a:b",
                                      "package/a\\b", "package/path./x", "package/invalid?.js",
                                      "package/.npmrc", "package/nested/.env", "package/.env.production",
                                      "package/.git/config", "package/.codex/config", "package/.ssh/config",
                                      "package/.agents/state", "package/.hermes/data", "package/" + "a/" * 65 + "x"])
def test_archive_rejects_nonportable_or_escaping_paths(tmp_path, bad_name):
    info = tarfile.TarInfo(bad_name)
    info.size = 1
    part = tmp_path / "payload.tgz"
    part.write_bytes(archive(extra=[(info, b"x")]))
    with pytest.raises(npm.FetchError):
        npm._inspect_archive(part.read_bytes(), "jsonrepair", "3.13.3")
    assert not (tmp_path.parent / "escape").exists()


def test_archive_rejects_links_duplicates_identity_and_license(tmp_path):
    cases = []
    link = tarfile.TarInfo("package/link")
    link.type, link.linkname = tarfile.SYMTYPE, "../../outside"
    cases.append(archive(extra=[(link, b"")]))
    sparse = tarfile.TarInfo("package/sparse")
    sparse.type = tarfile.GNUTYPE_SPARSE
    cases.append(archive(extra=[(sparse, b"")]))
    dupe = tarfile.TarInfo("package/INDEX.JS")
    dupe.size = 1
    cases.append(archive(extra=[(dupe, b"x")]))
    cases.append(archive(name="not-jsonrepair"))
    cases.append(archive(license_name="UNLICENSED"))
    for index, payload in enumerate(cases):
        part = tmp_path / f"bad-{index}.tgz"
        part.write_bytes(payload)
        with pytest.raises(npm.FetchError):
            npm._inspect_archive(part.read_bytes(), "jsonrepair", "3.13.3")


def test_duplicate_json_yaml_and_expansion_limits_fail_closed(tmp_path, monkeypatch):
    with pytest.raises(npm.FetchError, match="duplicate"):
        npm._json_no_duplicates(b'{"name":"one","name":"two"}')
    with pytest.raises(npm.FetchError, match="duplicate"):
        npm.yaml.load(b"key: one\nkey: two\n", Loader=npm.UniqueLoader)
    part = tmp_path / "payload.tgz"
    part.write_bytes(archive())
    monkeypatch.setattr(npm, "MAX_TAR_STREAM", 100)
    with pytest.raises(npm.FetchError, match="expansion limit"):
        npm._inspect_archive(part.read_bytes(), "jsonrepair", "3.13.3")


@pytest.mark.parametrize("token", [b"NaN", b"Infinity", b"-Infinity", b"1e9999", b"-1e9999"])
def test_manifest_json_rejects_nonfinite_numbers_even_in_nested_unknown_fields(token):
    with pytest.raises(npm.FetchError, match="non-finite"):
        npm._json_no_duplicates(b'{"unknown":{"number":' + token + b'}}')
    assert npm._json_no_duplicates(b'{"number":1.25}') == {"number": 1.25}


@pytest.mark.parametrize("name,version", [("jsonrepair", "3.13.3"), ("nanoid", "5.1.14"),
                                          ("partial-json", "0.1.7"), ("postcss-value-parser", "4.2.0"),
                                          ("es-module-lexer", "2.0.0")])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")], ids=["nan", "positive-inf", "negative-inf"])
def test_fixed_package_manifest_rejects_nonfinite_nested_values(name, version, value):
    payload = archive(name, version, manifest_extra={"uninspected_field": {"number": value}})
    with pytest.raises(npm.FetchError, match="non-finite"):
        npm._inspect_archive(payload, name, version)


def test_direct_fixed_https_sri_and_redirect_rejection(tmp_path, monkeypatch):
    payload = b"synthetic public archive"
    monkeypatch.setattr(npm, "PACKAGES", {"jsonrepair": {"version": "3.13.3", "sri": sri(payload)}})
    monkeypatch.setattr(npm, "_tls_context", lambda: "system-trust")
    calls = []
    class Response:
        status = 200
        def __init__(self): self.data = io.BytesIO(payload)
        def getheader(self, key, default=None):
            return str(len(payload)) if key == "Content-Length" else default
        def read(self, count): return self.data.read(count)
    class Connection:
        sock = None
        def __init__(self, host, port, **kw): calls.append((host, port, kw))
        def request(self, method, path, headers): calls.append((method, path, headers))
        def getresponse(self): return Response()
        def close(self): calls.append(("closed",))
    monkeypatch.setattr(npm.http.client, "HTTPSConnection", Connection)
    result = npm._download("jsonrepair", "3.13.3", tmp_path / "ok.part", sri(payload))
    assert result["sri"] == sri(payload) and calls[0][0:2] == ("registry.npmjs.org", 443)
    assert calls[1][0:2] == ("GET", "/jsonrepair/-/jsonrepair-3.13.3.tgz")
    assert not {key.lower() for key in calls[1][2]}.intersection({"authorization", "cookie", "proxy-authorization"})
    with pytest.raises(npm.FetchError, match="outside"):
        npm._download("foreign", "1", tmp_path / "bad.part", "sha512-fake")
    Response.status = 302
    with pytest.raises(npm.FetchError, match="redirect"):
        npm._download("jsonrepair", "3.13.3", tmp_path / "redirect.part", sri(payload))
    assert not (tmp_path / "redirect.part").exists()


@pytest.mark.parametrize("kind", ["wrong_sri", "oversize"])
def test_network_limit_and_sri_failure_preserve_only_bounded_partial(tmp_path, monkeypatch, kind):
    payload = b"synthetic public archive"
    expected = sri(b"a different payload") if kind == "wrong_sri" else sri(payload)
    monkeypatch.setattr(npm, "PACKAGES", {"jsonrepair": {"version": "3.13.3", "sri": expected}})
    monkeypatch.setattr(npm, "_tls_context", lambda: "system-trust")
    if kind == "oversize":
        monkeypatch.setattr(npm, "MAX_COMPRESSED", 4)
    class Response:
        status = 200
        def __init__(self): self.data = io.BytesIO(payload)
        def getheader(self, key, default=None): return default
        def read(self, count): return self.data.read(min(count, 1))
    class Connection:
        sock = None
        def __init__(self, *a, **k): pass
        def request(self, *a, **k): pass
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(npm.http.client, "HTTPSConnection", Connection)
    part = tmp_path / "partial.tgz"
    with pytest.raises(npm.FetchError, match="SRI mismatch" if kind == "wrong_sri" else "compressed limit"):
        npm._download("jsonrepair", "3.13.3", part, expected)
    assert part.is_file() and part.stat().st_size <= npm.MAX_COMPRESSED


def test_sri_mismatch_retains_partial_and_never_extracts(growth, monkeypatch):
    def fail_after_partial(name, version, part, expected):
        write_native(part, b"synthetic invalid partial")
        raise npm.FetchError("SRI mismatch")
    monkeypatch.setattr(npm, "_download", fail_after_partial)
    with pytest.raises(npm.FetchError, match="SRI mismatch"):
        npm.run(growth.context)
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["copy_outcome"] == "STARTED" and receipt["packages"] == []
    assert receipt["original_error"]["type"] == "FetchError" and len(growth.measures) == 2
    assert read_native(growth.paths["run"] / "tmp/openmaic-locked-npm/jsonrepair-3.13.3.tgz.part") == b"synthetic invalid partial"


def test_changed_archive_is_rejected_before_any_extraction(growth, monkeypatch):
    def altered(name, version, part, expected):
        write_native(part, archive(name, version))
        return {"archive_bytes": os.stat(npm.portable.native(part)).st_size, "sri": expected}
    monkeypatch.setattr(npm, "_download", altered)
    with pytest.raises(npm.FetchError, match="changed after download"):
        npm.run(growth.context)
    target = growth.paths["cache"] / "npm" / ("openmaic-owner-" + npm.LOCK_SHA256) / growth.paths["run"].name
    assert os.path.isdir(npm.portable.native(target)) and not os.listdir(npm.portable.native(target))
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["packages"] == [] and len(growth.measures) == 2


def test_member_readback_mismatch_fails_and_preserves_partial(growth, monkeypatch):
    payloads = {name: archive(name, row["version"]) for name, row in npm.PACKAGES.items()}
    packages = {name: {**row, "sri": sri(payloads[name])} for name, row in npm.PACKAGES.items()}
    monkeypatch.setattr(npm, "PACKAGES", packages)
    def download(name, version, part, expected):
        write_native(part, payloads[name])
        return {"archive_bytes": len(payloads[name]), "sri": expected}
    monkeypatch.setattr(npm, "_download", download)
    original = npm._hash_file
    def altered_hash(path, algorithm):
        return "0" * 64 if path.name == "index.js" else original(path, algorithm)
    monkeypatch.setattr(npm, "_hash_file", altered_hash)
    with pytest.raises(npm.FetchError, match="readback mismatch"):
        npm.run(growth.context)
    target = growth.paths["cache"] / "npm" / ("openmaic-owner-" + npm.LOCK_SHA256) / growth.paths["run"].name
    assert read_native(target / "jsonrepair-3.13.3/index.js") == b"export const value = 1;\n"
    assert not os.path.exists(npm.portable.native(target / "jsonrepair-3.13.3.tgz"))
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["packages"] == [] and receipt["copy_outcome"] == "STARTED" and len(growth.measures) == 2


@pytest.mark.skipif(os.name != "nt", reason="real Windows extended path behavior")
def test_windows_deep_member_download_extract_and_retain(tmp_path, monkeypatch):
    nested = ("d" * 75) + "/" + ("e" * 75) + "/payload.js"
    info = tarfile.TarInfo("package/" + nested)
    info.size = 1
    payload = archive(extra=[(info, b"x")])
    data, members, _ = npm._inspect_archive(payload, "jsonrepair", "3.13.3")
    target = tmp_path / "deep-package"
    npm._extract(data, members, target)
    member = target.joinpath(*nested.split("/"))
    assert len(str(member)) > 260 and read_native(member) == b"x"
    monkeypatch.setattr(npm, "PACKAGES", {"jsonrepair": {"version": "3.13.3", "sri": sri(payload)}})
    monkeypatch.setattr(npm, "_tls_context", lambda: "system-trust")
    class Response:
        status = 200
        def __init__(self): self.data = io.BytesIO(payload)
        def getheader(self, key, default=None): return default
        def read(self, count): return self.data.read(count)
    class Connection:
        sock = None
        def __init__(self, *a, **k): pass
        def request(self, *a, **k): pass
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(npm.http.client, "HTTPSConnection", Connection)
    part = member.parent / "download.part"
    npm._download("jsonrepair", "3.13.3", part, sri(payload))
    verified = npm._read_verified_archive(part, sri(payload))
    retained = member.parent / "retained.tgz"
    npm._retain_archive(verified, retained, sri(payload))
    assert len(str(part)) > 260 and len(str(retained)) > 260
    assert read_native(retained) == payload


def test_long_path_checker_still_rejects_reparse_ancestors(tmp_path, monkeypatch):
    blocked = tmp_path / "redirect"
    real_lstat = os.lstat
    def fake_lstat(path, *args, **kwargs):
        if os.fspath(path) == npm.portable.native(blocked):
            return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
        return real_lstat(path, *args, **kwargs)
    monkeypatch.setattr(npm.os, "lstat", fake_lstat)
    with pytest.raises(npm.FetchError, match="linked npm path"):
        npm._checked(blocked / ("x" * 100) / "file")
