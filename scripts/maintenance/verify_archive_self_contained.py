"""Read-only verification of repository-local source copies; never opens provenance paths.

Originals stay in ignored local archives. A Git clone alone does not include them.
Only stdlib and the existing archive path/hash helpers are used; ZIPs are streamed,
never extracted or executed. Success qualifies source availability, not the product.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from archive_record_materials import bounded, digest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "workspace/intake/20261101-project-archiving-reconciliation/LOCAL-SOURCES.json"


def verify(root: Path, manifest_path: str = MANIFEST) -> dict:
    document = json.loads(bounded(root, manifest_path).read_text(encoding="utf-8"))
    if document.get("schema") != "archeaxis.repository-local-source-closure/v1":
        raise ValueError("unsupported local-source schema")
    rows = document["objects"]
    expected = document["expected_counts"]
    if any(type(expected[key]) is not int or expected[key] < 0 for key in ("aaos_objects", "source_records")):
        raise ValueError("invalid expected counts")
    if len(rows) != expected["aaos_objects"] + expected["source_records"]:
        raise ValueError("local-source count mismatch")
    if Counter(row["kind"] for row in rows) != Counter({"aaos_object": expected["aaos_objects"], "source_record": expected["source_records"]}):
        raise ValueError("source kind count mismatch")
    if len({row["record_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate record identity")
    source_ids = {row["sha256"] for row in rows if row["kind"] == "aaos_object"}
    source_index = bounded(root, document["source_index"])
    indexed = [json.loads(line) for line in source_index.read_text(encoding="utf-8").splitlines()]
    if source_ids != {row["sha256"] for row in indexed} or len(source_ids) != expected["aaos_objects"] or len(indexed) != len(source_ids):
        raise ValueError("AAOS source identity set mismatch")
    if {(row["record_id"], row["sha256"]) for row in rows if row["kind"] == "aaos_object"} != {(row["source_id"], row["sha256"]) for row in indexed}:
        raise ValueError("AAOS record identity mismatch")
    index_by_sha = {row["sha256"]: row for row in indexed}
    declared = json.loads(bounded(root, document["source_manifest"]).read_text(encoding="utf-8"))["source_records"]
    management = {(row["record_id"], row["sha256"], row["bytes"]) for row in rows if row["kind"] == "source_record"}
    if management != {("source:" + row["path"], row["sha256"], row["bytes"]) for row in declared}:
        raise ValueError("source-record identity set mismatch")
    checked = {}
    for row in rows:
        if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) or type(row["bytes"]) is not int or row["bytes"] < 0:
            raise ValueError("invalid expected source identity")
        if row["kind"] == "aaos_object" and row["bytes"] != index_by_sha[row["sha256"]]["bytes"]:
            raise ValueError("source size declaration mismatch")
        ref = row["local"]
        if ref["type"] not in {"file", "zip_member"}:
            raise ValueError("unsupported local locator")
        if ref["type"] == "file" and "member" in ref:
            raise ValueError("file reference cannot declare a ZIP member")
        if ref["type"] == "zip_member":
            member = ref["member"]
            if not member or ":" in member or "\\" in member or PurePosixPath(member).is_absolute() or ".." in PurePosixPath(member).parts:
                raise ValueError("unsafe member locator")
        # No external/archive_original/provenance field is read or resolved here.
        path = bounded(root, ref["path"])
        key = (ref["path"], ref.get("member"))
        if key not in checked:
            if ref["type"] == "file":
                checked[key] = (path.stat().st_size, digest(path))
            elif ref["type"] == "zip_member":
                member = ref["member"]
                with zipfile.ZipFile(path) as archive:
                    matches = [info for info in archive.infolist() if info.filename == member]
                    if len(matches) != 1 or matches[0].is_dir() or matches[0].file_size != row["bytes"]:
                        raise ValueError("ambiguous or wrong-sized ZIP member")
                    hasher, count = hashlib.sha256(), 0
                    with archive.open(matches[0]) as stream:
                        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                            count += len(chunk)
                            if count > row["bytes"]:
                                raise ValueError("member exceeds declared size")
                            hasher.update(chunk)
                    checked[key] = (count, hasher.hexdigest())
            else:
                raise ValueError("unsupported local locator")
        if checked[key] != (row["bytes"], row["sha256"]):
            raise ValueError("local source hash/size mismatch: " + row["record_id"])
    return {"status": "LOCAL_SOURCE_CLOSURE_VERIFIED", "aaos_objects": expected["aaos_objects"],
            "source_records": expected["source_records"], "unique_local_locators": len(checked),
            "external_reads": 0, "product_acceptance": "NOT_EVALUATED",
            "git_clone_includes_ignored_originals": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=MANIFEST)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(ROOT, args.manifest), ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        print("local source closure failed: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
