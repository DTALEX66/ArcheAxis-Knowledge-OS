"""R15/F15: a member must be written even when the transfer area sits inside a deep workspace.

Windows refuses a create whose full path passes MAX_PATH with ERROR_FILE_NOT_FOUND, which the
worker's own problem line rendered as "could not be extracted: FileNotFoundError" - so on a
long enough checkout the container reported one member inventoried and zero offered, with no
sign that a path limit was the cause. The transfer directory is keyed by a 64-character
container digest, so this is reachable in an ordinary worktree rather than only in theory.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ARCHIVE = REPO / "services" / "python-workers" / "document" / "worker_archive.py"
MEMBER_NAME = "notes/known.csv"
MEMBER_FILE = "0001-known.csv"
CSV = b"id,label\n1,deep-path-value\n"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker_archive = _load("deep_path_worker_archive", ARCHIVE)


def _tar() -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        info = tarfile.TarInfo(MEMBER_NAME)
        info.size = len(CSV)
        archive.addfile(info, io.BytesIO(CSV))
    return buffer.getvalue()


def _deep_dir(tmp_path: Path) -> Path:
    """A transfer area whose member path is past the plain-path limit, as a digest-keyed one is.

    The chain is built through the helper because this repo's own pytest base is already 239
    characters long and a plain mkdir on this volume fails at 252, so the host shape cannot be
    reached from here. The other test in this file builds the host shape from a short base.
    """
    node = tmp_path
    while len(str(node / "members" / MEMBER_FILE)) < 265:
        node = node / ("container-" + "d" * 48)
        Path(worker_archive._long_path(node)).mkdir(parents=True, exist_ok=True)
    return node / "members"


def test_a_member_is_still_offered_when_its_transfer_path_passes_max_path(tmp_path: Path) -> None:
    source = tmp_path / "g3-known.tar"
    source.write_bytes(_tar())
    member_dir = _deep_dir(tmp_path)

    result = worker_archive.extract(str(source), member_dir)
    receipt = result["loss_receipt"]
    extracted = receipt["params"]["structure"]["extractable_members"]

    assert [item["name"] for item in extracted] == [MEMBER_NAME], extracted
    assert extracted[0]["sha256"] == hashlib.sha256(CSV).hexdigest()
    assert not any("could not be extracted" in line for line in receipt["losses"]), receipt["losses"]
    written = Path(worker_archive._long_path(member_dir / extracted[0]["file"]))
    assert written.read_bytes() == CSV


def test_the_extended_prefix_is_added_only_to_absolute_paths_on_windows(tmp_path: Path) -> None:
    absolute = tmp_path / "members"
    assert worker_archive._long_path(Path("members/relative")) == str(Path("members/relative"))
    if sys.platform == "win32":
        prefixed = worker_archive._long_path(absolute)
        assert prefixed.startswith("\\\\?\\") and len(str(absolute)) < len(prefixed)
    else:
        assert worker_archive._long_path(absolute) == str(absolute)


@pytest.mark.skipif(sys.platform != "win32", reason="the plain-path limit is a Windows fact")
def test_at_the_host_shape_the_depth_alone_is_what_lost_the_member(monkeypatch) -> None:
    """The host shape: a members directory a plain path can create, a member that it cannot.

    The window is narrow and measured, not assumed: on this volume a plain mkdir fails from 252
    characters, so the members directory has to sit at 247 to 251 while the member file lands past
    260. The lengths below are set to hit it from any base short enough to allow it.

    The probe is what gives this file its meaning. It shows on the machine running it that the
    depth, and not something incidental about this archive, is what refuses the create - and that
    the same write succeeds once the prefix is back. Without that, the test above could be green
    for a reason that has nothing to do with the fix.
    """
    box = Path(tempfile.mkdtemp())
    original = worker_archive._long_path
    try:
        # dir 247 + "\\0001-known.csv" = member 262, the pair the host run actually produced.
        node = box
        if len(str(node)) < 239:
            node = node / ("c" * (239 - len(str(node)) - 1))
        if len(str(node)) > 243:
            pytest.skip("the temporary base is already too deep to express the host shape")
        try:
            node.mkdir(parents=True, exist_ok=True)
            members = node / "members"
            members.mkdir()
        except OSError:
            pytest.skip("no plain-creatable members directory at the host depth from this base")

        assert len(str(members)) <= 251 and len(str(members / MEMBER_FILE)) >= 261
        try:
            (members / MEMBER_FILE).write_bytes(b"x")
        except OSError:
            pass
        else:
            pytest.skip("this machine creates files past the limit, so the pre-fix shape is absent")

        source = box / "g3-known.tar"
        source.write_bytes(_tar())

        monkeypatch.setattr(worker_archive, "_long_path", lambda path: str(path))
        without = worker_archive.extract(str(source), members)["loss_receipt"]
        offered = [item["name"] for item in without["params"]["structure"]["extractable_members"]]
        assert offered == [], offered
        assert any("could not be extracted" in line for line in without["losses"]), without["losses"]

        monkeypatch.setattr(worker_archive, "_long_path", original)
        with_fix = worker_archive.extract(str(source), members)["loss_receipt"]
        offered = [item["name"] for item in with_fix["params"]["structure"]["extractable_members"]]
        assert offered == [MEMBER_NAME], offered
        assert Path(original(members / MEMBER_FILE)).read_bytes() == CSV
    finally:
        shutil.rmtree(original(box), ignore_errors=True)
