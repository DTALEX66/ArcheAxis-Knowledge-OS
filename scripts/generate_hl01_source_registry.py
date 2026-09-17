"""Regenerate the checked-in HL01 source registration from R5 originals."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _record_id(item: object, fallback: int) -> str:
    if isinstance(item, dict):
        for key, value in item.items():
            if str(key).casefold() in {"id", "编号", "���"} and value:
                return str(value)
    return f"record-{fallback:04d}"


def generate(root: Path) -> Path:
    path = root / "docs/current/R5-HL01-SOURCE-REGISTRY.json"
    registry = json.loads(path.read_text(encoding="utf-8"))
    records: list[dict[str, object]] = []
    for category in registry["categories"]:
        source_path = root / Path(str(category["source_path"]))
        raw = source_path.read_bytes()
        data = json.loads(raw.decode("utf-8"))
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == category["sha256"]
        for index, item in enumerate(data, start=1):
            record_id = _record_id(item, index)
            namespace = str(category["namespace"])
            records.append(
                {
                    "namespace": namespace,
                    "record_id": record_id,
                    "core_id": f"hl01:{namespace}:{record_id}",
                    "version": 1,
                    "source_path": str(category["source_path"]),
                    "source_sha256": digest,
                    "qualification_state": "candidate",
                    "activation": "not_activated",
                }
            )
    assert len(records) == registry["total_records"]
    assert len({(item["namespace"], item["record_id"]) for item in records}) == len(records)
    registry["records"] = records
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    print(generate(Path(__file__).parents[1]))
