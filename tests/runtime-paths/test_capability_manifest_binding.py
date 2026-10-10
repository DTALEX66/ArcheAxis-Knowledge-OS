"""The manifest must bind each engine and model to a named artifact, and the index must agree.

A row that names only a capability is the failure that keeps recurring here: the model is on disk, the
worker resolves through the declaration, and the capability is still reported missing - so "declared"
was never "bound". These two checks are host-independent on purpose: they compare what the manifest
declares against what the generated index records, so they gate the declaration rather than the
particular caches of this machine.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "config" / "environment" / "capability-requirements.yaml"
INDEX = ROOT / "config" / "environment" / "external-resources-index.json"

BINDABLE_CATEGORIES = ("engines", "models")
# only what genuinely has no artifact to name is exempt: `uv` resolves from the interpreter's own
# scripts dir, WebView2 is a system runtime, and the desktop runtime row names a path under probe
PATH_RESOLVED_NAMES = {"uv", "webview2-evergreen", "desktop-runtime-v1"}


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def _rows() -> list[dict]:
    document = _manifest()
    found = []
    for category, group in (document.get("capabilities") or {}).items():
        for entry in group or []:
            if isinstance(entry, dict):
                found.append({**entry, "category": category})
    return found


def _binds_an_artifact(row: dict) -> bool:
    """A row is bound when it names a location, an endpoint, or a probe path it can be checked at.

    A model served over loopback HTTP has no file to name — its artifact is the lane plus the model
    id the host answers with, and `probe.kind: path_exists`/`registry_key` rows carry their location
    in the probe because the shared resource itself is a directory the engine validates.
    """
    if row.get("external_paths"):
        return True
    if isinstance(row.get("endpoint"), dict) and row["endpoint"].get("base_url"):
        return True
    probe = row.get("probe") or {}
    return bool(probe.get("paths") or probe.get("patterns") or probe.get("cwd")
                or probe.get("interpreter") or probe.get("key") or probe.get("kind") == "not_run")


def _index() -> dict:
    return json.loads(INDEX.read_text(encoding="utf-8"))


def test_every_engine_and_model_row_names_the_artifact_it_resolves_through() -> None:
    unbound = [
        f"{row['category']}/{row['name']}"
        for row in _rows()
        if row["category"] in BINDABLE_CATEGORIES
        and row["name"] not in PATH_RESOLVED_NAMES
        and not _binds_an_artifact(row)
    ]
    assert not unbound, f"name-only rows are declared but not bound: {unbound}"


def test_every_row_declares_the_identity_its_version_claim_is_judged_by() -> None:
    """`version_identification` is the anti-inheritance field.

    Four engines were certified as `uv 0.12.23` because nothing said *which* command's output the
    row's version must come from. Each row now states its own identification method, and the probe
    that runs it, so a wrapper binary cannot answer for a library again.
    """
    missing = [f"{row['category']}/{row['name']}" for row in _rows()
               if not row.get("version_identification") or not (row.get("probe") or {}).get("kind")]
    assert missing == [], f"rows with no stated identification method or probe: {missing}"
    inherited = [f"{row['category']}/{row['name']}" for row in _rows()
                 if (row.get("probe") or {}).get("kind") == "interpreter_import"
                 and not (row.get("probe") or {}).get("interpreter")]
    assert inherited == [], f"import probes without their own interpreter: {inherited}"


def test_no_probe_inherits_a_version_from_a_wrapper_or_runs_a_non_executable() -> None:
    """`uv run python -c ...` reduced to `uv` is the exact shape that lied.

    A `command` probe is only honest when the thing it executes is the artifact the row is
    about: an executable file the row declares. For an engine that is a Python package
    directory, the probe must name its own interpreter; for a `.bat` initializer it must be a
    `cmd_chain`; for a model served over HTTP it must be the HTTP probe. Anything else lets a
    neighbouring binary's version be recorded as this row's identity.
    """
    suspects = []
    for row in _rows():
        probe = row.get("probe") or {}
        if probe.get("kind") != "command":
            continue
        healthcheck = str(row.get("healthcheck_command") or "").split()
        first = healthcheck[0] if healthcheck else ""
        declared = [p for p in (row.get("external_paths") or []) if isinstance(p, str)]
        target = declared[0] if declared else ""
        if row["category"] in BINDABLE_CATEGORIES and not target.endswith(".exe"):
            suspects.append(f"{row['category']}/{row['name']}: command probe on {target or first!r} "
                            "is not bound to an executable artifact")
        # A row that declares an artifact must execute *that* artifact. `uv --version` for the
        # uv row is not inheritance — uv declares no path of its own and the index labels it
        # `unbound_path_fallback` — but `uv run python -c "import X"` for an engine row is.
        if first in {"uv", "powershell", "pwsh", "cmd"} and declared:
            suspects.append(f"{row['category']}/{row['name']}: command probe driven by the {first} "
                            f"wrapper although the row declares {target!r}")
    assert suspects == [], "; ".join(suspects)
    # And a row with no declared location is only ever allowed to be reported as unbound.
    unbound = [f"{row['category']}/{row['name']}" for row in _rows()
               if not [p for p in (row.get("external_paths") or []) if isinstance(p, str)]
               and not row.get("sibling_root")
               and not (row.get("probe") or {}).get("interpreter")
               and (row.get("probe") or {}).get("kind") not in
               {"registry_key", "path_exists", "glob_exists", "http_get", "http_roundtrip", "not_run",
                "cmd_chain", "ocr_roundtrip", "list_langs"}]
    for reference in unbound:
        assert reference in {"toolchains/uv"}, f"{reference} resolves through PATH with no fallback label"


def test_the_generated_index_records_every_declared_path() -> None:
    index = _index()
    recorded = {row["name"]: {item["declared"] for item in row["external_paths"]} for row in index["entries"]}
    for row in _rows():
        declared = set(row.get("external_paths") or [])
        assert recorded.get(row["name"], set()) == declared, (
            f"{row['name']}: the index does not mirror the manifest"
        )


def test_the_index_builder_refuses_an_absolute_or_parent_traversing_declaration(tmp_path: Path) -> None:
    """A declaration is not allowed to name a location the runtime resolver cannot reach."""
    spec = importlib.util.spec_from_file_location(
        "build_external_resources_index", ROOT / "scripts" / "environment" / "build_external_resources_index.py"
    )
    assert spec and spec.loader
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    base = tmp_path / "external"
    (base / "10-toolchains").mkdir(parents=True)
    (base / "10-toolchains" / "tool.exe").write_bytes(b"MZ")
    assert builder.resolve(str(base / "outside.exe"), base) == ("", False), "an absolute declaration is refused"
    assert builder.resolve("../sibling/model", base) == ("", False), "a `..` declaration is refused"
    reached, exists = builder.resolve("10-toolchains/tool.exe", base)
    assert exists is True and Path(reached) == (base / "10-toolchains" / "tool.exe").resolve()
    assert builder.resolve("10-toolchains/missing.exe", base) == (
        str((base / "10-toolchains" / "missing.exe").resolve()), False), "a gap is recorded as MISSING, not as absent-by-assumption"
