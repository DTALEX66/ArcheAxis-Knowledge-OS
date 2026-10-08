"""The generated OSS-reuse tables stay out of Git, and the tracked manifest keeps proving it.

Why this gate exists rather than a comment: the round that produced the crosswalk also produced a
20,584-line / 992,500-byte JSON and a 692-line CSV, and committed both beside the 137-line script
that derives them. A committed derived table can only ever be in one of two states — regenerated on
every input edit (a 20k-line diff each time), or left behind (a stale table that still *looks*
authoritative). The incoming payload was already in the second state: it hashed two of its six
inputs at digests matching no committed revision of those files, so the table described somebody's
working tree rather than any recorded state of the repository.

So Git tracks the generator plus one small manifest, and the payload is regenerated into the
project-owned ignored artifact root. What the assertions below refuse to accept is the failure mode
a generated table always invites: "the file exists, therefore it is verified".

Each assertion is paired with a control that plants the matching fault, because a check that cannot
fail guards nothing.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "docs/current/OSS-REUSE-CROSSWALK-20261008.manifest.json"
GENERATOR = ROOT / "scripts/audit/build_oss_reuse_inventory.py"
DECISIONS = ROOT / "docs/current/OSS-REUSE-DECISIONS-20261008.json"
VERIFICATION = ROOT / "docs/current/OSS-REUSE-VERIFICATION-20261008.json"
TRACKED_TABLES = (
    "docs/current/OSS-REUSE-CROSSWALK-20261008.json",
    "docs/current/OSS-REUSE-CROSSWALK-20261008.csv",
)
VERIFY_SCRATCH = ROOT / ".project-local/runs/manifest-verify/artifacts"

CRLF = bytes([13, 10])
LF = bytes([10])


def portable_digest(raw: bytes) -> str:
    """Hash the bytes with the line terminator folded to LF.

    The generator writes the JSON through text-mode ``Path.write_text`` and the CSV through
    ``csv.writer`` with no explicit lineterminator, so on Windows both land as CRLF while
    ``.gitattributes`` pins tracked text to LF. Only this normalised form compares across machines;
    the manifest also records the raw on-disk digest, but as a fact about the machine that produced
    it, never as something asserted here.

    Applies to the GENERATED tables only. The generator hashes its INPUTS with ``read_bytes()`` and
    ``hashlib`` directly, so an input's own terminator is part of its identity — the historical
    369-row pool CSV really does carry CRLF in its committed blob, and folding it reports a drift
    that has not happened. Inputs are therefore compared raw, below.
    """
    return hashlib.sha256(raw.replace(CRLF, LF)).hexdigest()


def input_digest(path: Path) -> str:
    """An input's identity exactly the way the generator computes it: raw bytes, no folding."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked_files(pattern: str | tuple[str, ...]) -> list[str]:
    """Paths Git currently tracks under `pattern` — read from the index, not the filesystem."""
    args = (pattern,) if isinstance(pattern, str) else pattern
    listing = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--", *args],
                             capture_output=True, text=True, encoding="utf-8")
    assert listing.returncode == 0, f"git ls-files failed, so this check has no subject: {listing.stderr}"
    return sorted(line for line in listing.stdout.splitlines() if line.strip())


def regenerate(out_dir: Path) -> dict[str, bytes]:
    """Run the tracked generator out of the tracked inputs and hand back the produced bytes."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "OSS-REUSE-CROSSWALK-20261008.json"
    # main() calls output.relative_to(root), so the output must sit inside the repository; a system
    # temp directory is refused by the generator itself. This scratch is under the ignored root.
    command = [sys.executable, str(GENERATOR), "--root", str(ROOT),
               "--decisions", str(DECISIONS), "--verification", str(VERIFICATION),
               "--output", str(target)]
    proc = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    assert proc.returncode == 0, f"generator failed rc={proc.returncode}: {proc.stdout}\n{proc.stderr}"
    produced = {"json": target.read_bytes(), "csv": target.with_suffix(".csv").read_bytes()}
    # The floor an emptied table trips: content, not existence, is what makes a payload verifiable.
    for key, raw in produced.items():
        assert len(raw) > 1000, f"{key}: produced {len(raw)} bytes, an empty or truncated payload"
    return produced


def pairing_failures(manifest_path: Path, produced: dict[str, bytes]) -> list[str]:
    """Every way the tracked pointer can fail to describe the generator's real output.

    Returns reasons rather than a boolean so no caller can mistake "I did not read this" for a pass.
    `produced` may be empty when only the always-available halves are being checked.
    """
    if not manifest_path.is_file():
        return [f"manifest-missing: {manifest_path} is absent, so nothing records which bytes the "
                "generated tables are supposed to have"]
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"manifest-unparsable: {error}"]

    reasons: list[str] = []

    generator_raw = GENERATOR.read_bytes()
    if hashlib.sha256(generator_raw).hexdigest() != data["generator"]["sha256"]:
        reasons.append(
            "generator-drift: the tracked generator no longer hashes to the value the manifest "
            f"records ({data['generator']['sha256'][:16]}...). The tables it produces are not the "
            "ones described here, so regenerate them and re-record the manifest."
        )
    if portable_digest(generator_raw) != hashlib.sha256(generator_raw).hexdigest():
        reasons.append("generator-not-lf: the tracked generator itself carries CRLF bytes, so the "
                       "recorded raw digest would stop being comparable across machines")

    for key, raw in produced.items():
        entry = data["outputs"][key]
        digest = portable_digest(raw)
        if digest != entry["sha256_portable"]:
            reasons.append(f"digest-mismatch[{key}]: produced bytes hash to {digest[:16]}... but the "
                           f"manifest records {entry['sha256_portable'][:16]}...")
        if len(raw) != entry["bytes"]:
            reasons.append(f"size-mismatch[{key}]: produced {len(raw)} bytes, manifest records "
                           f"{entry['bytes']}")

    # The structural floor for "lossless", taken from the crosswalk's own definition: one record per
    # source row, and one CSV data row per record. An emptied or silently collapsed table fails here
    # even if a digest were somehow made to agree with it.
    source_rows = sum(meta["recorded_rows"] for meta in data["inputs"].values())
    json_out, csv_out = data["outputs"]["json"], data["outputs"]["csv"]
    if json_out["record_count"] != source_rows:
        reasons.append(f"record-count-not-lossless: the manifest records {json_out['record_count']} "
                       f"records against {source_rows} source rows across the six inputs")
    if csv_out["data_rows"] != json_out["record_count"]:
        reasons.append(f"csv-record-disagreement: csv carries {csv_out['data_rows']} data rows against "
                       f"{json_out['record_count']} json records")

    for path, meta in data["inputs"].items():
        current = input_digest(ROOT / path) if (ROOT / path).is_file() else "ABSENT"
        if meta["sha256_of_bytes_read_by_generator"] != current:
            reasons.append(f"input-drift[{path}]: the payload recorded input digest "
                           f"{meta['sha256_of_bytes_read_by_generator'][:16]}... but this file is "
                           f"{current[:16]}...")

    re_tracked = tracked_files(TRACKED_TABLES)
    if re_tracked:
        reasons.append(f"payload-is-tracked-again: {re_tracked} are in the index. The rule this "
                       "manifest records is that the generator is tracked and the derived payload "
                       "is not.")
    return reasons


def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def produced() -> dict[str, bytes]:
    try:
        yield regenerate(VERIFY_SCRATCH)
    finally:
        for name in ("OSS-REUSE-CROSSWALK-20261008.json", "OSS-REUSE-CROSSWALK-20261008.csv"):
            (VERIFY_SCRATCH / name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------------------------
# The real verdict.
# ---------------------------------------------------------------------------------------------

def test_the_checker_is_not_vacuous_and_the_recorded_generator_is_the_tracked_one() -> None:
    """The always-available half: pointer, generator identity, structure, and the index."""
    assert MANIFEST_PATH.is_file(), MANIFEST_PATH
    assert pairing_failures(MANIFEST_PATH, {}) == []


def test_regenerating_from_tracked_inputs_reproduces_the_recorded_digest(produced) -> None:
    assert pairing_failures(MANIFEST_PATH, produced) == []
    data = manifest()
    payload = json.loads(produced["json"].decode("utf-8"))
    assert len(payload["records"]) == data["outputs"]["json"]["record_count"]
    assert payload["pool_counts"] == data["outputs"]["json"]["pool_counts"]
    assert payload["schema"] == data["outputs"]["json"]["schema"]


def test_no_input_is_recorded_at_a_digest_no_committed_revision_has() -> None:
    """The defect the payload arrived with, kept from recurring.

    The table committed in 15f79cf7 hashed docs/truth/SUPPLY_CHAIN_LEDGER.json (17 committed
    revisions) and docs/current/AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json (2 committed revisions)
    at digests matching none of them. A reader could not tell from the file that its own provenance
    block was describing bytes that existed nowhere recorded.
    """
    data = manifest()
    for path, meta in data["inputs"].items():
        assert meta["sha256_of_bytes_read_by_generator"] == input_digest(ROOT / path), (
            f"{path}: the recorded input digest is not this file. Regenerate the tables and rebuild "
            "the manifest before treating any row as current."
        )


def test_the_generated_tables_stay_out_of_git() -> None:
    assert tracked_files(TRACKED_TABLES) == []


def test_the_pointers_do_not_send_a_reader_to_a_file_that_is_no_longer_there() -> None:
    ledger = json.loads((ROOT / "docs/truth/SUPPLY_CHAIN_LEDGER.json").read_text(encoding="utf-8"))
    overlay = json.loads((ROOT / "docs/current/AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json")
                         .read_text(encoding="utf-8"))["current_evidence_overlay"]
    for label, target in (("SUPPLY_CHAIN_LEDGER.current_crosswalk", ledger["current_crosswalk"]),
                          ("current_evidence_overlay.crosswalk", overlay["crosswalk"])):
        assert (ROOT / target).is_file(), f"{label} points at {target}, which is not in the tree"
        assert target.endswith(".manifest.json"), f"{label} points at a payload instead of a pointer"


# ---------------------------------------------------------------------------------------------
# Controls: each plants the fault the assertions above are meant to catch.
# ---------------------------------------------------------------------------------------------

def test_control_an_absent_manifest_is_a_failure_not_an_empty_pass(tmp_path) -> None:
    reasons = pairing_failures(tmp_path / "no-such-manifest.json", {"json": b"x", "csv": b"y"})
    assert [reason for reason in reasons if reason.startswith("manifest-missing")] == reasons[:1]
    assert len(reasons) == 1


def test_control_a_forged_digest_fails_the_pairing(tmp_path) -> None:
    forged = json.loads(json.dumps(manifest()))
    forged["outputs"]["json"]["sha256_portable"] = hashlib.sha256(b"a different table").hexdigest()
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(forged), encoding="utf-8")
    # Bytes that are not the recorded payload: the checker must refuse them on both axes at once.
    reasons = pairing_failures(path, {"json": b"short"})
    assert any(reason.startswith("digest-mismatch[json]") for reason in reasons), reasons
    assert any(reason.startswith("size-mismatch[json]") for reason in reasons), reasons


def test_control_an_edited_generator_is_reported_as_drift(tmp_path) -> None:
    forged = json.loads(json.dumps(manifest()))
    forged["generator"]["sha256"] = hashlib.sha256(b"#!/bin/sh\n").hexdigest()
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(forged), encoding="utf-8")
    reasons = pairing_failures(path, {})
    assert [reason for reason in reasons if reason.startswith("generator-drift")], reasons


def test_control_a_hollowed_out_record_count_is_refused(tmp_path) -> None:
    """A silent collapse of the 691 source rows cannot pass by agreeing with its own digest."""
    forged = json.loads(json.dumps(manifest()))
    forged["outputs"]["json"]["record_count"] = 369
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(forged), encoding="utf-8")
    reasons = pairing_failures(path, {})
    assert any("record-count-not-lossless" in reason for reason in reasons), reasons
    assert any("csv-record-disagreement" in reason for reason in reasons), reasons


def test_control_the_tracked_payload_probe_reads_the_index_not_a_hardcoded_empty() -> None:
    """The probe fires on a tracked file, so its silence on the two tables is evidence."""
    assert tracked_files("docs/current/OSS-REUSE-DECISIONS-20261008.json") == [
        "docs/current/OSS-REUSE-DECISIONS-20261008.json"]
    assert tracked_files(TRACKED_TABLES) == []


def test_control_a_stale_input_digest_is_named(tmp_path) -> None:
    forged = json.loads(json.dumps(manifest()))
    next(iter(forged["inputs"].values()))["sha256_of_bytes_read_by_generator"] = "0" * 64
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(forged), encoding="utf-8")
    reasons = pairing_failures(path, {})
    assert [reason for reason in reasons if reason.startswith("input-drift[")]
