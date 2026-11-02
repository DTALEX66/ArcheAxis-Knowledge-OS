"""Finite synthetic HTML rewrite observation; never render the returned HTML."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import threading

import pytest

from scripts.release.tauri_portable_candidate import native
from tests.integrations.test_openmaic_interactive_url_map import (
    ORIGINALS,
    checked_node,
    digest,
    read_bytes,
    stage_sources,
    write_new,
)


ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "services/learning-providers/openmaic/interactive-html-rewrite-probe.mjs"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
SCHEMA = "archeaxis.openmaic-interactive-html-probe/v1"
SENTINEL = b'{"version":3,"sources":["input.css"],"names":[],"mappings":"AAAA","sourcesContent":["SYNTHETIC_MAP"]}'
SENTINEL_SHA256 = "8b993d109374915bc45c805deb02b9a4ce695dd912f511efd67833f4c51d58fd"
requires_node = pytest.mark.skipif(not NODE, reason="explicit, preverified ARCHEAXIS_TEST_NODE is required; PATH is not searched")


def stage_probe(stage: Path) -> None:
    stage_sources(stage)
    write_new(stage / PROBE.name, read_bytes(PROBE))
    assert digest(SENTINEL) == SENTINEL_SHA256
    write_new(stage / "fixture.css.map", SENTINEL)


def call_probe(stage: Path, case: bytes, *, override: dict[str, str] | None = None) -> tuple[dict, bytes, bytes]:
    node = checked_node()
    env = {key: os.environ[key] for key in ("SystemRoot", "SYSTEMROOT", "WINDIR") if key in os.environ}
    if override:
        env.update(override)
    process = subprocess.Popen([str(node), str(stage / PROBE.name)], cwd=str(stage), env=env,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    streams: dict[str, bytes] = {}
    errors: list[str] = []

    def bounded(pipe, name):
        try:
            data = pipe.read(8193)
            streams[name] = data
            if len(data) > 8192:
                try:
                    process.kill()
                except OSError:
                    pass
        except OSError as error:
            errors.append(type(error).__name__)

    def send():
        try:
            process.stdin.write(case)
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass

    readers = [threading.Thread(target=bounded, args=(process.stdout, "stdout"), daemon=True),
               threading.Thread(target=bounded, args=(process.stderr, "stderr"), daemon=True)]
    writer = threading.Thread(target=send, daemon=True)
    for thread in (*readers, writer):
        thread.start()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
        raise AssertionError("owned synthetic Node probe exceeded its deadline")
    finally:
        for thread in (*readers, writer):
            thread.join(timeout=5)
    assert not any(thread.is_alive() for thread in (*readers, writer)), "owned process pipe cleanup unconfirmed"
    assert not errors and process.returncode == 0
    assert len(streams["stdout"]) <= 8192 and len(streams["stderr"]) <= 8192
    return json.loads(streams["stdout"]), streams["stdout"], streams["stderr"]


def assert_boundaries(result: dict) -> None:
    assert result["schema"] == SCHEMA and result["scope"] == "FIXED_SYNTHETIC_UNVERIFIED"
    assert result["expected_source_sha256"] == ORIGINALS["src/interactive-library-mapper.ts"]
    assert "source_sha256" not in result
    assert result["source_verification"] == ("VERIFIED_SELECTED_MEMBERS" if result["status"] == "OBSERVED" else "NOT_ASSERTED")
    assert result["node_version"] == "24.21.0"
    assert result["recorded_owner_archive_sha256"] == "7cea2a5850083bdc261114d8433daa6ea24c1c0157beae3939a2e9fac3a98f40"
    assert result["owner_archive_reverified_in_probe"] is False
    assert "input_script_executed" not in result
    if result["status"] == "OBSERVED":
        assert result["synthetic_marker_observed"] is False
        assert result["synthetic_marker_control"] == "NONE"
    elif result.get("error_code") == "SYNTHETIC_MARKER_TRIGGERED":
        assert result["synthetic_marker_observed"] is True
        assert result["synthetic_marker_control"] == "FORCED_BY_PROBE"
    else:
        assert result["synthetic_marker_observed"] == "NOT_OBSERVED"
    assert result["resource_availability"] == "NOT_VERIFIED"
    assert result["network_isolation"] == "NOT_ESTABLISHED"
    assert result["security_sanitizer"] is False and result["core_authorization"] == "NOT_ESTABLISHED"


@pytest.fixture(scope="module")
def probe_stage(tmp_path_factory) -> Path:
    stage = tmp_path_factory.mktemp("html-probe") / "h"
    stage_probe(stage)
    return stage


def observe(stage: Path, case: str) -> dict:
    result, stdout, stderr = call_probe(stage, (case + "\n").encode())
    # Preserve only fixed, non-private fixtures and raw result receipts in the
    # owned pytest temporary directory for later inspection.
    write_new(stage / "observations" / (case + ".json"), stdout)
    assert_boundaries(result)
    assert result["status"] == "OBSERVED" and result["fixture"] == case, (
        f"fixture {case} was not observed: {result.get('error_code')}")
    assert digest(result["input_html"].encode("utf-8")) == result["input_sha256"]
    assert digest(result["output_html"].encode("utf-8")) == result["output_sha256"]
    assert result["sentinel_preflight_read"] is True
    assert result["sentinel_calls"]["mapper_exists"] == result["sentinel_calls"]["mapper_read"] == 0
    assert b"SYNTHETIC_NANOID_DECOY" not in stdout + stderr
    assert b"SYNTHETIC_ENTITIES_DECOY" not in stdout + stderr
    return result


@requires_node
def test_original_html_rewrite_reports_synthetic_transformations(probe_stage):
    cases = ("attributes", "crlf", "unscanned", "broken_css", "input_script", "unicode")
    observed = {case: observe(probe_stage, case) for case in cases}
    attrs = observed["attributes"]
    assert "SRC='https://unpkg.com/chart.js@4'" in attrs["input_html"]
    assert 'src="/vendor/interactive/chart.js@4.4.8/dist/chart.umd.js"' in attrs["output_html"]
    assert "sha384-old" in attrs["input_html"] and "sha384-old" not in attrs["output_html"]
    assert "crossorigin='use-credentials'" in attrs["input_html"]
    assert 'crossorigin="anonymous"' in attrs["output_html"]

    crlf = observed["crlf"]
    assert "<p>outside\r\nkeep</p>" in crlf["input_html"] and "<p>outside\r\nkeep</p>" in crlf["output_html"]
    style_before = crlf["input_html"].split("<style>", 1)[1].split("</style>", 1)[0]
    style_after = crlf["output_html"].split("<style>", 1)[1].split("</style>", 1)[0]
    assert "\r\n" in style_before and "\r" not in style_after
    assert "/vendor/interactive/chart.js@4.4.8/dist/chart.umd.js" in style_after

    missed = observed["unscanned"]
    assert "https://outside.invalid/p.png" in missed["output_html"]
    assert "https://hidden.invalid/a.js" in missed["output_html"]
    assert "/vendor/interactive/chart.js@4.4.8/dist/chart.umd.js" in missed["output_html"]
    assert missed["unmatched_external_hosts"] == {}

    broken = observed["broken_css"]
    assert broken["output_html"] == broken["input_html"] and broken["unmatched_external_hosts"] == {}
    assert observed["input_script"]["output_html"] == observed["input_script"]["input_html"]
    assert "😀before" in observed["unicode"]["output_html"] and "字后" in observed["unicode"]["output_html"]
    assert "/vendor/interactive/chart.js@4.4.8/dist/chart.umd.js" in observed["unicode"]["output_html"]


@requires_node
def test_original_html_rewrite_source_maps_and_synthetic_file_control(probe_stage):
    cases = ("external_map", "inline_valid", "inline_invalid", "inline_broken_css")
    observed = {case: observe(probe_stage, case) for case in cases}
    external = observed["external_map"]
    assert "/vendor/interactive/chart.js@4.4.8/dist/chart.umd.js" in external["output_html"]
    assert external["source_map_positive_control"] == "COMPLETED"
    assert external["sentinel_calls"]["control_exists"] > 0 and external["sentinel_calls"]["control_read"] > 0

    assert "/vendor/interactive/chart.js@4.4.8/dist/chart.umd.js" in observed["inline_valid"]["output_html"]
    assert observed["inline_invalid"]["output_html"] == observed["inline_invalid"]["input_html"]
    assert observed["inline_broken_css"]["output_html"] == observed["inline_broken_css"]["input_html"]
    assert observed["inline_broken_css"]["trusted_template_compilations"] > 0


@requires_node
def test_fixed_inline_css_dynamic_fingerprint(probe_stage):
    result, stdout, stderr = call_probe(probe_stage, b"inline_broken_css\n")
    write_new(probe_stage / "observations" / "inline_broken_css_diagnostic.json", stdout)
    assert_boundaries(result)
    assert b"SYNTHETIC_NANOID_DECOY" not in stdout + stderr
    assert b"SYNTHETIC_ENTITIES_DECOY" not in stdout + stderr
    assert result["status"] == "OBSERVED" and result["fixture"] == "inline_broken_css"
    assert result["trusted_template_compilations"] > 0
    assert result["trusted_dynamic_observation"] == {
        "kind": "construct", "argument_count": 1, "argument_type": "string", "utf8_bytes": 2509,
        "sha256": "8f0039413e6feed51fa7ac4093658fda70d90fb5877ca2343b0ed4be7a3dafe0",
    }


@requires_node
def test_probe_rejects_unlisted_input_environment_and_tampering(probe_stage):
    stage = probe_stage
    # The sole input is a fixed fixture selector. An arbitrary string is not
    # passed to the upstream HTML parser and is not reflected into a rejection.
    result, stdout, stderr = call_probe(stage, b"SYNTHETIC_PRIVATE_INVALID\n")
    assert_boundaries(result)
    assert result["status"] == "REJECTED" and result["error_code"] == "INVALID_FIXTURE"
    assert b"SYNTHETIC_PRIVATE_INVALID" not in stdout + stderr
    result, _, _ = call_probe(stage, b"a" * 129 + b"\n")
    assert_boundaries(result)
    assert result["status"] == "REJECTED" and result["error_code"] == "INPUT_TOO_LARGE"

    result, _, _ = call_probe(stage, b"attributes\n", override={"INTERACTIVE_ASSET_BASE_URL": "https://wrong.invalid"})
    assert_boundaries(result)
    assert result["status"] == "REJECTED" and result["error_code"] == "ENVIRONMENT_OVERRIDE"
    # The probe sets this one marker itself; no input script is executed.
    result, _, _ = call_probe(stage, b"marker_red\n")
    assert_boundaries(result)
    assert result["status"] == "REJECTED" and result["error_code"] == "SYNTHETIC_MARKER_TRIGGERED"

    # Tamper only this test's temporary copies. Restore each before proceeding.
    targets = (
        ("UPSTREAM_IDENTITY_MISMATCH", stage / "vendor/scene-content-0.3.28-original/generation/src/interactive-library-mapper.ts", False),
        ("DEPENDENCY_IDENTITY_MISMATCH", stage / "vendor/npm/nanoid-3.3.19/non-secure/index.cjs", False),
        ("DEPENDENCY_IDENTITY_MISMATCH", stage / "vendor/npm/entities-8.0.0/dist/decode.js", True),
        ("SENTINEL_IDENTITY_MISMATCH", stage / "fixture.css.map", False),
    )
    for expected, target, missing in targets:
        original = read_bytes(target)
        try:
            if missing:
                os.unlink(native(target))
            else:
                with open(native(target), "ab") as stream:
                    stream.write(b"\n/* synthetic tamper */\n")
            result, stdout, stderr = call_probe(stage, b"attributes\n")
            assert_boundaries(result)
            assert result["status"] == "REJECTED" and result["error_code"] == expected
            assert b"SYNTHETIC_NANOID_DECOY" not in stdout + stderr
            assert b"SYNTHETIC_ENTITIES_DECOY" not in stdout + stderr
        finally:
            with open(native(target), "wb") as stream:
                stream.write(original)
            assert read_bytes(target) == original
