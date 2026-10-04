"""Run the desktop capture so a test cannot leave a process behind or accept a blank image.

Driving the capture by hand went wrong twice on this host: assigning the child's output to a
discarded variable left the desktop process running, and the runs after it produced zero-byte PNGs
while the lingering process held the output file and the build directory. A harness that only said
"a file exists" could not tell the difference.

So three properties are measured rather than assumed:

* the child's stdout and stderr are drained on their own threads, so a full pipe buffer cannot
  block a capture that has otherwise finished;
* a run that overruns its deadline is killed as a process tree, not as a single process;
* a screenshot is accepted only when it decodes as a PNG with real dimensions, and the same image
  name is not left running afterwards.
"""

from __future__ import annotations

import os
import signal
import struct
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
IHDR = b"IHDR"


def png_is_decodable(path: Path) -> tuple[bool, str]:
    """A PNG that decodes: right signature, an IHDR carrying real dimensions, and image bytes.

    Size alone is not the test - an empty file is small, and a truncated one is not empty. This
    reads the structures that must be right before a viewer would show anything.
    """
    try:
        raw = path.read_bytes()
    except OSError as error:
        return False, f"unreadable: {error}"
    if not raw:
        return False, "the file is empty"
    if not raw.startswith(PNG_SIGNATURE):
        return False, "not a PNG: signature missing"
    after = raw[len(PNG_SIGNATURE):]
    if len(after) < 8 or after[4:8] != IHDR:
        return False, "not a PNG: no IHDR chunk"
    if len(after) < 8 + 13:
        return False, "not a PNG: IHDR is truncated"
    width, height = struct.unpack(">II", after[8:16])
    if width == 0 or height == 0:
        return False, f"a PNG with no pixels: {width}x{height}"
    if len(after) < 8 + 12 + 12:
        return False, f"a PNG with no image data: {len(after)} bytes after the signature"
    return True, f"{width}x{height}, {len(raw)} bytes"


def drain(stream, sink: list[str]) -> threading.Thread:
    """Consume a pipe to its end on its own thread, so the child can never block on a full buffer."""

    def pump() -> None:
        try:
            for line in iter(stream.readline, b""):
                sink.append(line.decode("utf-8", "replace"))
        except (OSError, ValueError):
            pass
        finally:
            try:
                stream.close()
            except OSError:
                pass

    thread = threading.Thread(target=pump, daemon=True)
    thread.start()
    return thread


def running_pids(image_name: str) -> set[int]:
    """PIDs whose executable image is `image_name`; empty when the host will not say.

    Best effort on purpose. This is a diagnostic, and `tasklist` writes in the console codepage,
    whose bytes are not always decodable as UTF-8 - decoding it as text raised UnicodeDecodeError
    and failed the capture it was only trying to describe. An unreadable answer is reported as
    "cannot say" rather than raised, so listing processes can never break a run.
    """
    if os.name != "nt":
        return set()
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image_name}", "/FO", "CSV", "/NH"],
            capture_output=True, check=False,
        )
    except OSError:
        return set()
    output = result.stdout.decode("utf-8", "replace")
    pids: set[int] = set()
    for line in output.splitlines():
        fields = [part.strip().strip('"') for part in line.split(",")]
        if len(fields) >= 2 and fields[0].lower() == image_name.lower():
            try:
                pids.add(int(fields[1]))
            except ValueError:
                continue
    return pids


def _kill_tree(pid: int) -> None:
    """Kill the child and everything it started: terminating one process leaves grandchildren."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, check=False)
        return
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass


@dataclass
class CaptureResult:
    returncode: int | None
    timed_out: bool
    stdout: str
    stderr: str
    decodable: bool
    detail: str
    left_running: list[int] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return (not self.timed_out and self.returncode == 0 and self.decodable
                and not self.left_running)

    def why_not(self) -> str:
        if self.timed_out:
            return "the capture overran its deadline and was killed as a tree"
        if self.returncode != 0:
            return f"the capture exited {self.returncode}: {self.stderr[-400:]}"
        if not self.decodable:
            return f"the screenshot did not decode: {self.detail}"
        if self.left_running:
            return f"these pids outlived the capture: {self.left_running}"
        return ""


def capture(
    executable: Path,
    out_png: Path,
    route: str,
    *,
    width: int = 1560,
    height: int = 980,
    theme: str = "deep-space",
    env: dict[str, str] | None = None,
    timeout: float = 120.0,
) -> CaptureResult:
    """Run one capture and report what happened, never merely that a file appeared."""
    out_png.parent.mkdir(parents=True, exist_ok=True)
    if out_png.exists():
        out_png.unlink()
    before = running_pids(executable.name)
    process = subprocess.Popen(
        [str(executable), "--ui-capture", str(out_png), route, str(width), str(height), theme],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(executable.parent),
    )
    out_lines: list[str] = []
    err_lines: list[str] = []
    out_thread = drain(process.stdout, out_lines)
    err_thread = drain(process.stderr, err_lines)
    timed_out = False
    try:
        returncode = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_tree(process.pid)
        try:
            returncode = process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            returncode = None
    out_thread.join(timeout=10)
    err_thread.join(timeout=10)
    decodable, detail = png_is_decodable(out_png)
    left_running = sorted(running_pids(executable.name) - before)
    return CaptureResult(
        returncode=returncode,
        timed_out=timed_out,
        stdout="".join(out_lines),
        stderr="".join(err_lines),
        decodable=decodable,
        detail=detail,
        left_running=left_running,
    )
