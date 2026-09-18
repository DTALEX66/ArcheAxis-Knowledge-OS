"""The machine-readable capability manifest must obey its own declared schema.

`config/environment/capability-requirements.yaml` states that its fields
correspond strictly to `config/schemas/capability-requirements.schema.json`, and
`scripts/workflow/environment_registry.py` consumes the manifest to resolve
external capabilities. Until this module existed, nothing validated the real
manifest against that schema: the schema was referenced only by itself and by
historical ledgers, so a drift could sit unnoticed.

Running the validator for the first time found three pre-existing deviations.
They are pinned here rather than silently accepted, and they are **not** repaired
in this repository because every available repair is a governance decision:

* `plugins` is required with `minItems: 1`, and the manifest declares no vendored
  plugin asset at all. Removing the requirement or inventing an entry are both
  decisions about what the project really vendors.
* `models/sense-voice-zh-en-ja-ko-yue.external_paths` is
  `../Model library/sherpa-onnx`. The schema forbids `..`, and
  `environment_registry._external_path` deliberately skips it, so this entry can
  never resolve through the declared external root: the shared Model library is
  not under that root. Reconciling the two needs a schema/semantics decision.
* The same entry uses `install_method: shared-model-library`, which is not in the
  schema's enumeration.

The assertion compares the *exact* deviation set, so it fails both when new drift
appears and when a recorded deviation is repaired without updating this record.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "config" / "schemas" / "capability-requirements.schema.json"
MANIFEST = ROOT / "config" / "environment" / "capability-requirements.yaml"

# label|validator -> why it is recorded instead of repaired here
KNOWN_DEVIATIONS = {
    "capabilities|required": (
        "the schema requires a plugins category with minItems 1; the manifest "
        "declares no vendored plugin asset, and neither relaxing the schema nor "
        "inventing an entry is this executor's decision"
    ),
    "models/sense-voice-zh-en-ja-ko-yue:external_paths/0|pattern": (
        "'../Model library/sherpa-onnx' escapes the declared external root and is "
        "skipped by environment_registry._external_path, so it can never resolve; "
        "the Model library is outside OS External Configuration"
    ),
    "models/sense-voice-zh-en-ja-ko-yue:install_method|enum": (
        "'shared-model-library' is not one of the schema's install_method values"
    ),
}


def _deviations() -> set[str]:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    found: set[str] = set()
    for error in validator.iter_errors(manifest):
        parts = list(error.path)
        label = "/".join(str(part) for part in parts)
        if len(parts) >= 3 and parts[0] == "capabilities":
            category, index = parts[1], parts[2]
            entry = manifest["capabilities"][category][index]
            label = f"{category}/{entry.get('name')}:" + "/".join(
                str(part) for part in parts[3:]
            )
        found.add(f"{label}|{error.validator}")
    return found


def test_capability_manifest_deviates_from_its_schema_only_where_recorded() -> None:
    deviations = _deviations()

    assert deviations == set(KNOWN_DEVIATIONS), (
        "the capability manifest's schema deviations changed: "
        f"new={sorted(deviations - set(KNOWN_DEVIATIONS))} "
        f"repaired={sorted(set(KNOWN_DEVIATIONS) - deviations)}"
    )


def test_recorded_deviations_explain_themselves() -> None:
    # A pin without a reason becomes a silent allowance.
    for label, reason in KNOWN_DEVIATIONS.items():
        assert reason.strip(), label


def test_the_manifest_is_the_one_the_registry_consumes() -> None:
    """Guard against validating a copy nobody reads."""
    from scripts.workflow import environment_registry

    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    report = environment_registry.resolve(MANIFEST)

    assert report["schema"] == "archeaxis.environment-registry/v1"
    assert report["install_performed"] is False
    assert report["private_state_opened"] is False
    declared = sum(len(entries or []) for entries in manifest["capabilities"].values())
    assert report["summary"]["total"] == declared
    assert {item["name"] for item in report["capabilities"]} >= {
        "dotnet",
        "tesseract",
        "msvc",
        "rust",
    }
