"""Q00's invariant: the declared storage scene must not be left unknown.

Q00 asks for the scene to be covered — observed facts recorded, unknowns marked as unknown.
Until 2026-10-06 the receipt did not name any storage location at all, while
`config/defaults.yaml` declared a database path and a backup directory, and the file
actually on disk had a different name from the declared one. That is exactly the
"uncovered unknown scene" Q00 exists to prevent, so it gets a gate rather than a note:

* every storage location the configuration declares must be named in the receipt, so a
  config change cannot silently introduce an unexplained location;
* every `*.sqlite` present in the declared directory must be recorded too, so a renamed or
  newly appeared database cannot sit outside the scene.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "config" / "defaults.yaml"
RECEIPT = REPO / "docs" / "current" / "AAOS01-Q00-SCENE-RECEIPT.md"


def declared_storage() -> dict[str, str]:
    """The storage locations the product configuration claims, as written."""
    payload = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    database = payload["database"]
    return {"path": str(database["path"]), "backup_dir": str(database["backup_dir"])}


def test_the_scene_receipt_names_every_declared_storage_location() -> None:
    receipt = RECEIPT.read_text(encoding="utf-8")
    for field, value in declared_storage().items():
        assert value in receipt, (
            f"config/defaults.yaml database.{field} = {value!r} is not named in the Q00 scene "
            "receipt: a declared storage location nobody recorded is an uncovered unknown scene"
        )


def test_a_database_present_on_disk_is_recorded_by_name() -> None:
    directory = (REPO / declared_storage()["path"]).parent
    if not directory.is_dir():
        return  # the ignored data root is absent in a fresh checkout: nothing to compare
    present = sorted(entry.name for entry in directory.glob("*.sqlite"))
    if not present:
        return
    receipt = RECEIPT.read_text(encoding="utf-8")
    for name in present:
        assert name in receipt, (
            f"{directory.name}/{name} exists but the Q00 scene receipt never names it: a database "
            "the receipt does not record is an uncovered unknown scene"
        )
