"""R15/F15: a container gets an inventory route, never a text decode.

A ZIP is binary. Decoding it as text would produce noise that looks like content, so
the Core routes `.zip` to a capability of its own and the worker projects an
inventory listing - one member per line - while the receipt states plainly that this
is an inventory and not the members' contents.

The samples are built here with zipfile, so nothing private is involved.
"""

from __future__ import annotations

import importlib.util
import json
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


def test_finder_metadata_keeps_original_bytes_and_leaves_slots_for_user_files(tmp_path, monkeypatch):
    archive = tmp_path / "workspace.zip"
    apple = bytes.fromhex("0005160700020000") + b"resource fork"
    files = {
        "__MACOSX/._page.md": apple,
        "ui/.DS_Store": bytes.fromhex("0000000142756431") + b"finder view",
        "page.md": b"# Page",
        "rows.csv": b"Name\nFirst",
        "other/.DS_Store": b"user-authored data",
        "__MACOSX/._rows.csv": b"notes for the table",
        "._unpaired": apple,
    }
    with zipfile.ZipFile(archive, "w") as z:
        for name, payload in files.items():
            z.writestr(name, payload)
    monkeypatch.setattr(worker, "MEMBER_JOB_CAP", 5)
    result = worker.extract(str(archive), tmp_path / "offered")
    detail = result["loss_receipt"]["params"]["structure"]
    assert detail["member_count"] == 7
    assert [m["name"] for m in detail["extractable_members"]] == list(files)[2:]
    assert detail["extractable_members"][0]["file"].startswith("0003-")
    metadata = detail["member_extraction"]["container_metadata"]
    assert metadata["total"] == 2 and [m["kind"] for m in metadata["members"]] == ["appledouble_v2", "finder_store"]
    with zipfile.ZipFile(archive) as z:
        assert all(z.read(m["name"]) == files[m["name"]] for m in metadata["members"])


def test_anki_prefers_versioned_collection_and_imports_media_by_native_name(tmp_path: Path):
    example = REPO / "tests/fixtures/anki-apkg/review.apkg"
    sample = tmp_path / "collection.apkg"
    with zipfile.ZipFile(example) as source, zipfile.ZipFile(sample, "w") as package:
        package.writestr("meta", b"\x08\x02")
        package.writestr("collection.anki2", b"old-client placeholder")
        package.writestr("collection.anki21", source.read("collection.anki2"))
        package.writestr("media", source.read("media"))
        package.writestr("0", source.read("0"))
        media_name = json.loads(source.read("media"))["0"]
        media_bytes = source.read("0")
    result = worker.extract(str(sample), tmp_path / "members")
    receipt = result["loss_receipt"]["params"]["structure"]
    assert receipt["anki"]["native_import_semantics"] == "replace_collection"
    assert receipt["anki"]["notes"][0]["fields"] == ["front", "back"]
    member, = receipt["extractable_members"]
    assert member["name"] == media_name and (tmp_path / "members" / member["file"]).read_bytes() == media_bytes


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
    assert route["media_types"] == {"application/zip", "application/x-tar", "application/x-joplin-jex",
                                    "application/x-anki-package", "application/x-anki-collection"}
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


def _tar_sample(path, entries):
    import io
    import tarfile

    with tarfile.open(path, "w") as archive:
        for name, payload, kind in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.size = len(payload)
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                info.linkname = "../../outside.txt"
            archive.addfile(info, io.BytesIO(payload))


def test_tar_declares_actual_bytes_and_digest_for_existing_core_member_chain(tmp_path):
    import hashlib
    import tarfile

    sample = tmp_path / "bundle.tar"
    payload = b"Known TAR member value 37\n"
    _tar_sample(sample, [("notes/a.txt", payload, tarfile.REGTYPE)])
    result = worker.extract(str(sample), tmp_path / "members")
    members = result["loss_receipt"]["params"]["structure"]["extractable_members"]
    assert len(members) == 1
    assert members[0]["name"] == "notes/a.txt"
    assert members[0]["sha256"] == hashlib.sha256(payload).hexdigest()
    assert (tmp_path / "members" / members[0]["file"]).read_bytes() == payload
    assert "NOT the members' contents" in result["loss_receipt"]["params"]["projection_note"]


def test_jex_projects_notes_and_resolves_native_relations_without_changing_source_bytes(tmp_path):
    import hashlib
    import tarfile

    folder, child, note, tag, relation, resource, missing = (str(i) * 32 for i in range(1, 8))
    body = f"中文 🙂\n\n![diagram](:/{resource}) and [missing](:/{missing})\n\nkey: still in the body"
    modified = "2024-02-03T04:05:06.000Z"
    rows = {
        f"{note}.md": f"Reading\n\n{body}\n\nid: {note}\nparent_id: {child}\nupdated_time: {modified}\ntype_: 1",
        f"{relation}.md": f"id: {relation}\nnote_id: {note}\ntag_id: {tag}\ntype_: 6",
        f"{tag}.md": f"Review\n\nid: {tag}\ntype_: 5",
        f"{child}.md": f"Week 1\n\nid: {child}\nparent_id: {folder}\ntype_: 2",
        f"{folder}.md": f"Course\n\nid: {folder}\ntype_: 2",
        f"{resource}.md": f"Source file\n\nid: {resource}\nmime: text/plain\nsize: 4\ntype_: 4",
        f"resources/{resource}.txt": "data",
    }
    sample = tmp_path / "study.jex"
    _tar_sample(sample, [(name, value.encode(), tarfile.REGTYPE) for name, value in rows.items()])
    result = worker.extract(str(sample), tmp_path / "members")
    receipt = result["loss_receipt"]
    structure = receipt["params"]["structure"]
    graph = structure["joplin"]
    item, = graph["notes"]
    assert item["id"] == note and item["updated_time"] == modified
    assert item["notebook_path"] == ["Course", "Week 1"]
    assert item["tag_ids"] == [tag] and graph["tags"][0]["title"] == "Review"
    assert item["reference_ids"] == [resource, missing]
    assert result["text"][item["body_start"]:item["body_end"]] == body
    assert any(missing in loss for loss in receipt["losses"])
    assert graph["resources"][0]["payload_sha256"] == hashlib.sha256(b"data").hexdigest()
    for entry in structure["extractable_members"]:
        assert (tmp_path / "members" / entry["file"]).read_bytes() == rows[entry["name"]].encode()


def test_tar_unsafe_entries_fail_before_any_member_is_written(tmp_path):
    import tarfile

    import pytest

    for index, (name, kind) in enumerate(
        [
            ("../escape.txt", tarfile.REGTYPE),
            ("/absolute.txt", tarfile.REGTYPE),
            ("C:/escape.txt", tarfile.REGTYPE),
            ("link", tarfile.SYMTYPE),
            ("hard", tarfile.LNKTYPE),
            ("device", tarfile.CHRTYPE),
        ]
    ):
        sample = tmp_path / f"unsafe-{index}.tar"
        output = tmp_path / f"out-{index}"
        _tar_sample(sample, [("safe.txt", b"safe", tarfile.REGTYPE), (name, b"", kind)])
        with pytest.raises(ValueError):
            worker.extract(str(sample), output)
        assert not output.exists()


def test_tar_member_count_and_bytes_budgets_are_enforced_before_output(tmp_path, monkeypatch):
    import tarfile

    import pytest

    sample = tmp_path / "budget.tar"
    _tar_sample(sample, [("a.txt", b"123", tarfile.REGTYPE), ("b.txt", b"456", tarfile.REGTYPE)])
    monkeypatch.setattr(worker, "MEMBER_CAP", 1)
    with pytest.raises(ValueError, match="count"):
        worker.extract(str(sample), tmp_path / "members")
    monkeypatch.setattr(worker, "MEMBER_CAP", 5000)
    monkeypatch.setattr(worker, "MEMBER_BYTES_CAP", 5)
    with pytest.raises(ValueError, match="bytes"):
        worker.extract(str(sample), tmp_path / "members")
    assert not (tmp_path / "members").exists()


def test_tar_does_not_recursively_decode_nested_archive(tmp_path):
    import tarfile

    sample = tmp_path / "outer.tar"
    _tar_sample(sample, [("inner.tar", b"opaque nested bytes", tarfile.REGTYPE)])
    result = worker.extract(str(sample), tmp_path / "members")
    assert result["loss_receipt"]["params"]["structure"]["extractable_member_count"] == 1
    assert "opaque nested bytes" not in result["text"]


def test_tar_canonical_duplicate_and_empty_names_are_refused(tmp_path):
    import tarfile

    import pytest

    for index, entries in enumerate(
        [
            [("a", b"", tarfile.DIRTYPE), ("a/", b"", tarfile.DIRTYPE)],
            [("", b"", tarfile.REGTYPE)],
            [(".", b"", tarfile.DIRTYPE)],
            [("./", b"", tarfile.DIRTYPE)],
            [("pretend/", b"x", tarfile.REGTYPE)],
        ]
    ):
        sample = tmp_path / f"names-{index}.tar"
        output = tmp_path / f"names-out-{index}"
        _tar_sample(sample, entries)
        with pytest.raises(ValueError):
            worker.extract(str(sample), output)
        assert not output.exists()
