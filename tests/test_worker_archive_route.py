"""R15/F15: a container gets an inventory route, never a text decode.

A ZIP is binary. Decoding it as text would produce noise that looks like content, so
the Core routes `.zip` to a capability of its own and the worker projects an
inventory listing - one member per line - while the receipt states plainly that this
is an inventory and not the members' contents.

The samples are built here with zipfile, so nothing private is involved.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "services" / "python-workers" / "document" / "worker_archive.py"
TRANSPORT = REPO / "services" / "python-workers" / "transport" / "text_ndjson.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = _load("worker_archive_under_test", WORKER)
transport = _load("archive_transport_under_test", TRANSPORT)


def _sample(path: Path, *, nested: bool = False) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as container:
        container.writestr("notes/index.md", "# Index\nThe value is 6371 km.\n")
        container.writestr("notes/atomic.md", "# Atomic\nOne idea per note.\n")
        container.writestr("assets/", b"")
        container.writestr("data/table.csv", "name,qty\nbolt,4\n")
        if nested:
            inner = path.parent / "inner.zip"
            with zipfile.ZipFile(inner, "w") as nested_container:
                nested_container.writestr("inside.txt", "inner\n")
            container.write(inner, "nested/inner.zip")


def test_the_inventory_is_one_line_per_member_with_line_anchors(tmp_path: Path):
    sample = tmp_path / "bundle.zip"
    _sample(sample)
    result = worker.extract(str(sample))
    assert result["engine"] == worker.ENGINE
    lines = result["text"].splitlines()
    assert len(lines) == 4
    assert lines[0].startswith("notes/index.md\t")
    names = [line.split("\t")[0] for line in lines]
    assert names == ["notes/index.md", "notes/atomic.md", "assets/", "data/table.csv"]
    # canonical line anchors over the listing, covering it completely
    structure = result["structure"]
    assert [anchor["kind"] for anchor in structure] == ["line"] * 4
    assert structure[-1]["char_end"] == len(result["text"])
    receipt = result["loss_receipt"]
    assert receipt["covered"] == receipt["total"] == len(structure)
    assert receipt["coverage"] == 1.0


def test_the_receipt_says_it_is_an_inventory_not_the_contents(tmp_path: Path):
    sample = tmp_path / "bundle.zip"
    _sample(sample)
    result = worker.extract(str(sample))
    structure = result["loss_receipt"]["params"]["structure"]
    params = result["loss_receipt"]["params"]
    assert params["projection"] == "container inventory (one member per line: name, size)"
    assert "NOT the members' contents" in params["projection_note"]
    assert "no member was extracted" in params["projection_note"]
    assert structure["member_count"] == 4
    assert structure["file_count"] == 3
    assert structure["directory_count"] == 1
    assert structure["uncompressed_bytes"] > 0
    assert structure["compression_methods"] == ["deflate"]
    members = {member["name"]: member for member in structure["members"]}
    assert members["assets/"]["directory"] is True
    assert members["data/table.csv"]["size"] == len("name,qty\nbolt,4\n")
    # nothing claims an accuracy figure anywhere
    assert "accuracy" not in str(result["loss_receipt"]).lower()


def test_a_nested_container_is_listed_but_not_opened(tmp_path: Path):
    sample = tmp_path / "outer.zip"
    _sample(sample, nested=True)
    result = worker.extract(str(sample))
    structure = result["loss_receipt"]["params"]["structure"]
    assert structure["nested_containers"] == ["nested/inner.zip"]
    losses = result["loss_receipt"]["losses"]
    assert any("listed, not opened" in loss for loss in losses)
    # the inner archive's member never appears in the projection
    assert "inside.txt" not in result["text"]


def test_a_corrupt_container_fails_loudly(tmp_path: Path):
    sample = tmp_path / "broken.zip"
    sample.write_bytes(b"PK\x03\x04 not really a container")
    try:
        worker.extract(str(sample))
    except ValueError as error:
        assert "unreadable archive" in str(error)
    else:  # pragma: no cover - the refusal is the point
        raise AssertionError("a corrupt container must not produce a success envelope")


def test_an_empty_container_is_refused_rather_than_reported_as_empty_success(tmp_path: Path):
    sample = tmp_path / "empty.zip"
    with zipfile.ZipFile(sample, "w"):
        pass
    try:
        worker.extract(str(sample))
    except ValueError as error:
        assert "no members" in str(error)
    else:  # pragma: no cover
        raise AssertionError("an empty container has nothing to inventory and must say so")


def test_the_transport_route_declares_the_archive_capability_and_media_type():
    route = transport.ROUTES["archive.inventory"]
    assert route["media_types"] == {"application/zip"}
    assert route["worker"] == "services/python-workers/document/worker_archive.py"
    assert route["call"] == "path"
    # the text route must not accept a zip, so a container cannot fall back to a decode
    assert "application/zip" not in transport.ROUTES["text.extract"]["media_types"]


def test_the_worker_prints_exactly_one_envelope_on_stdout(tmp_path: Path):
    sample = tmp_path / "bundle.zip"
    _sample(sample)
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(WORKER), str(sample)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1, f"stdout must be exactly one envelope: {lines[:3]}"
    assert '"engine": "python-worker-archive"' in lines[0]
