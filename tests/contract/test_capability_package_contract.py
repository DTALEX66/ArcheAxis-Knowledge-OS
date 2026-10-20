"""真实Schema/只读语义校验；合成声明不是安装或启动资格。"""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    path = ROOT / f"scripts/contracts/{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


VALIDATE = module("validate_capability_package")
GEN = module("generate_capability_package")
SCHEMA = json.loads(
    (ROOT / "packages/contracts/v2/capability-package.schema.json").read_text(encoding="utf-8")
)
CASES = json.loads(
    (ROOT / "packages/contracts/v2/capability-package.cases.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_real_schema_cases(case):
    Draft202012Validator.check_schema(SCHEMA)
    assert Draft202012Validator(SCHEMA).is_valid(case["value"]) == case["schema_valid"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_catalog_join_and_lifecycle_cases(case):
    if case["semantic_valid"]:
        assert VALIDATE.validate_manifest(case["value"], ROOT, SCHEMA) is None
    else:
        with pytest.raises(VALIDATE.ManifestValidationError) as error:
            VALIDATE.validate_manifest(case["value"], ROOT, SCHEMA)
        assert str(error.value).startswith("MANIFEST_")
        assert "SYNTHETIC_PRIVATE_VALUE" not in str(error.value)


def test_exact_bytes_identity_without_self_hash_or_state_change():
    value = CASES[0]["value"]
    raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
    compact = json.dumps(value, separators=(",", ":")).encode("utf-8")
    identity = VALIDATE.parse_manifest_bytes(raw, ROOT, SCHEMA)
    assert identity["sha256"] == hashlib.sha256(raw).hexdigest()
    assert identity["sha256"] != VALIDATE.parse_manifest_bytes(compact, ROOT, SCHEMA)["sha256"]
    assert set(identity) == {"schema", "package_id", "version", "sha256"}
    refs = [
        "config/capability-map.v1.json",
        "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
        "services/python-workers/routes.json",
    ]
    before = {p: (ROOT / p).read_bytes() for p in refs}
    VALIDATE.parse_manifest_bytes(raw, ROOT, SCHEMA)
    assert before == {p: (ROOT / p).read_bytes() for p in refs}


@pytest.mark.parametrize(
    "raw",
    [b'{"schema":"x","schema":"y"}', b"\xff", b"{", b"x" * 262145],
    ids=["duplicate-key", "invalid-utf8", "truncated-json", "oversized-bytes"],
)
def test_duplicate_invalid_and_oversized_bytes_rejected_without_echo(raw):
    with pytest.raises(VALIDATE.ManifestValidationError) as error:
        VALIDATE.parse_manifest_bytes(raw, ROOT, SCHEMA)
    assert str(error.value).startswith("MANIFEST_")


def test_generated_ts_is_exact_and_drift_is_detected(tmp_path):
    source = ROOT / "packages/contracts/v2/capability-package.schema.json"
    target = ROOT / "frontend/src/api/generated/capability-package.ts"
    assert GEN.generate(source, target, True)
    generated = tmp_path / "contract.ts"
    assert GEN.generate(source, generated)
    assert generated.read_bytes() == target.read_bytes()
    generated.write_text("stale", encoding="utf-8")
    assert not GEN.generate(source, generated, True)


def test_negative_control_extra_runtime_state_requires_strict_schema():
    value = copy.deepcopy(CASES[0]["value"])
    value["installed"] = True
    assert not Draft202012Validator(SCHEMA).is_valid(value)
    permissive = copy.deepcopy(SCHEMA)
    permissive["$defs"]["CapabilityPackageManifest"]["additionalProperties"] = True
    assert Draft202012Validator(permissive).is_valid(value)


def test_semantic_gate_is_required_not_schema_only():
    cases = [x for x in CASES if x["schema_valid"] and not x["semantic_valid"]]
    assert len(cases) >= 10
    for case in cases:
        assert Draft202012Validator(SCHEMA).is_valid(case["value"])
        with pytest.raises(VALIDATE.ManifestValidationError):
            VALIDATE.validate_manifest(case["value"], ROOT, SCHEMA)


def test_modified_contract_bytes_are_rejected_even_when_schema_is_valid():
    value = copy.deepcopy(CASES[0]["value"])
    value["compatibility"]["contract_refs"][0]["sha256"] = "0" * 64
    assert Draft202012Validator(SCHEMA).is_valid(value)
    with pytest.raises(VALIDATE.ManifestValidationError, match="^MANIFEST_SOURCE_DRIFT$"):
        VALIDATE.validate_manifest(value, ROOT, SCHEMA)
