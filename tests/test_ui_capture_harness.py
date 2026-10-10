"""The capture harness must tell a real screenshot from an empty file, and leave nothing running.

This covers the harness itself, not the desktop. The end-to-end check is the last test and skips
when no built desktop is present, so the suite still runs where the shell was never built.
"""

import importlib.util
import os
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "runtime" / "ui_capture.py"
DESKTOP = (ROOT / ".project-local" / "build" / "dotnet" / "ArcheAxis.Desktop" / "bin"
           / "Debug" / "net10.0" / "ArcheAxis.Desktop.exe")
SHARED = Path(r"D:\All projects\OS External Configuration")
DOTNET = SHARED / "10-toolchains" / "dotnet-sdk-10.0.401"
CORE = ROOT / ".project-local" / "build" / "cargo-gnu" / "debug" / "archeaxis-api.exe"
PROFILE = ROOT / ".project-local" / "runs" / "product-ingest-20261003" / "worker-profile.json"


def _capture_env(db: Path) -> dict:
    """The same environment a real capture needs: the shared SDK, a workspace and the core."""
    env = dict(os.environ)
    env["DOTNET_ROOT"] = str(DOTNET)
    env["PATH"] = str(DOTNET) + os.pathsep + env.get("PATH", "")
    env["AAOS_UI_CAPTURE_WAIT_CORE"] = "1"
    env["AAOS_REDUCED_MOTION"] = "1"
    env["ARCHEAXIS_VNEXT_DB"] = str(db)
    if PROFILE.is_file():
        env["ARCHEAXIS_WORKER_PROFILE"] = str(PROFILE)
    if CORE.is_file():
        env["ARCHAXIS_CORE_BIN"] = str(CORE)
    return env


def _harness():
    spec = importlib.util.spec_from_file_location("ui_capture_under_test", HARNESS)
    module = importlib.util.module_from_spec(spec)
    # The module has to be reachable by name: dataclass resolves its own class through
    # sys.modules to read the string annotations that the future import leaves behind.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def _png(width: int, height: int) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", b"\x00")
            + _chunk(b"IEND", b""))


def test_an_empty_file_is_not_a_screenshot(tmp_path: Path) -> None:
    blank = tmp_path / "blank.png"
    blank.write_bytes(b"")
    ok, detail = _harness().png_is_decodable(blank)
    assert not ok, "a zero-byte file is what the failed captures produced; it must not pass"
    assert "empty" in detail


def test_a_file_that_is_not_a_png_is_not_a_screenshot(tmp_path: Path) -> None:
    other = tmp_path / "other.png"
    other.write_bytes(b"not an image, just some bytes")
    ok, detail = _harness().png_is_decodable(other)
    assert not ok and "signature" in detail


def test_a_truncated_png_is_not_a_screenshot(tmp_path: Path) -> None:
    cut = tmp_path / "cut.png"
    cut.write_bytes(_png(4, 4)[:12])
    ok, detail = _harness().png_is_decodable(cut)
    assert not ok, "a header with nothing behind it is not a rendered window"
    assert "IHDR" in detail or "no pixels" in detail or "no image data" in detail


def test_a_real_png_decodes_and_reports_its_dimensions(tmp_path: Path) -> None:
    good = tmp_path / "good.png"
    good.write_bytes(_png(1560, 980))
    ok, detail = _harness().png_is_decodable(good)
    assert ok, detail
    assert "1560x980" in detail


def test_the_drain_consumes_output_that_would_otherwise_fill_the_pipe() -> None:
    """A pipe left unread blocks the child; the harness reads it to the end on its own thread."""
    module = _harness()
    child = subprocess.Popen(
        [sys.executable, "-c", "import sys\nfor i in range(20000): sys.stdout.write('line %d\\n' % i)"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    lines: list[str] = []
    thread = module.drain(child.stdout, lines)
    assert child.wait(timeout=60) == 0, "the child must finish; an unread pipe would stall it"
    thread.join(timeout=10)
    assert len(lines) == 20000, f"the drain must consume every line, got {len(lines)}"


def test_a_missing_executable_is_loud_rather_than_a_blank_success(tmp_path: Path) -> None:
    # OSError rather than one specific subclass: the point is that a missing binary raises, and
    # which errno a host maps that to (absent, not a directory, denied) is not the property here.
    with pytest.raises(OSError):
        _harness().capture(tmp_path / "no-such-desktop.exe", tmp_path / "out.png", "home")


@pytest.mark.skipif(
    os.environ.get("AAOS_RUN_UI_CAPTURE") != "1"
    or not (DESKTOP.is_file() and DOTNET.is_dir() and CORE.is_file()),
    reason=(
        "an end-to-end capture needs a built desktop, the shared SDK, the core binary, and "
        "AAOS_RUN_UI_CAPTURE=1; it also competes with any other desktop the suite starts, so "
        "it is invoked on purpose rather than on every run"
    ),
)
def test_a_real_capture_decodes_and_leaves_no_process_behind(tmp_path: Path) -> None:
    """The whole point of the harness: a real window, a real image, and nothing still running."""
    module = _harness()
    result = module.capture(
        DESKTOP, tmp_path / "home.png", "home", env=_capture_env(tmp_path / "ws.sqlite")
    )
    assert result.ok, result.why_not()
    assert not result.left_running, result.why_not()
