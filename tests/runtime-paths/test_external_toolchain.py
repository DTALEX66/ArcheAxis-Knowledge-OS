"""Discovery of the registered external toolchain must stay conditional.

`scripts/runtime/dev.py::external_toolchain` is what stopped two environment
blockers that had nothing to do with the code: `cargo test` failed with
``linker `link.exe` not found`` and an OCR worker failed with ``AAK-WORKER-003``,
although the MSVC linker and tesseract were both installed under the registered
external root. The danger of a discovery step is the opposite failure - inventing a
path, or overriding a good one - so these tests pin the conditions rather than the
host's real layout.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

LAUNCHER = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(LAUNCHER))

from runtime import dev  # noqa: E402  (path set above, mirroring the other dev-path tests)


def _fake_root(
    base: Path, *, msvc: bool, rust: bool, tesseract: bool, tessdata: bool, ffmpeg: bool = False
) -> Path:
    root = base / "external"
    if msvc:
        version = root / "10-toolchains" / "msvc" / "VC" / "Tools" / "MSVC" / "14.44.35207"
        (version / "bin" / "Hostx64" / "x64").mkdir(parents=True)
        (version / "bin" / "Hostx64" / "x64" / "link.exe").write_bytes(b"MZ")
        (version.parents[2] / "Auxiliary" / "Build").mkdir(parents=True)
        (version.parents[2] / "Auxiliary" / "Build" / "vcvars64.bat").write_text("@echo off")
    if rust:
        (root / "toolchains" / "rust" / "cargo" / "bin").mkdir(parents=True)
        (root / "toolchains" / "rust" / "cargo" / "bin" / "cargo.exe").write_bytes(b"MZ")
    if tesseract:
        (root / "10-toolchains" / "scoop" / "apps" / "tesseract" / "current").mkdir(parents=True)
        (root / "10-toolchains" / "scoop" / "apps" / "tesseract" / "current" / "tesseract.exe").write_bytes(b"MZ")
    if tessdata:
        (root / "10-toolchains" / "scoop" / "apps" / "tesseract-languages" / "current").mkdir(parents=True)
    if ffmpeg:
        (root / "10-toolchains" / "scoop" / "apps" / "ffmpeg" / "current" / "bin").mkdir(parents=True)
        (root / "10-toolchains" / "scoop" / "apps" / "ffmpeg" / "current" / "bin" / "ffmpeg.exe").write_bytes(b"MZ")
    return root


class ExternalToolchainTest(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {
            name: __import__("os").environ.get(name)
            for name in (
                "OS_EXTERNAL_CONFIG",
                "ARCHEAXIS_EXTERNAL_ROOT",
                "ARCHEAXIS_MSVC_VCVARS",
                "ARCHEAXIS_RUST_TOOLCHAINS",
                "TESSDATA_PREFIX",
            )
        }
        import os

        for name in self._saved:
            os.environ.pop(name, None)
        self.os = __import__("os")

    def tearDown(self) -> None:
        for name, value in self._saved.items():
            if value is None:
                self.os.environ.pop(name, None)
            else:
                self.os.environ[name] = value

    def test_no_registered_root_discovers_nothing(self) -> None:
        """CI has no external root; discovery must be a no-op there."""
        self.assertEqual(dev.external_toolchain(), {})

    def test_empty_registered_root_discovers_nothing(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            self.os.environ["OS_EXTERNAL_CONFIG"] = str(Path(tmp) / "absent")
            self.assertEqual(dev.external_toolchain(), {})

    def test_complete_root_discovers_all_four(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = _fake_root(Path(tmp), msvc=True, rust=True, tesseract=True, tessdata=True, ffmpeg=True)
            self.os.environ["OS_EXTERNAL_CONFIG"] = str(root)
            found = dev.external_toolchain()
            self.assertEqual(
                set(found), {"ARCHEAXIS_MSVC_VCVARS", "ARCHEAXIS_RUST_TOOLCHAINS", "PATH", "TESSDATA_PREFIX"}
            )
            self.assertTrue(Path(found["ARCHEAXIS_MSVC_VCVARS"]).is_file())
            self.assertTrue((Path(found["ARCHEAXIS_RUST_TOOLCHAINS"]) / "cargo" / "bin" / "cargo.exe").is_file())
            self.assertTrue(found["PATH"].startswith(str(root / "10-toolchains" / "scoop" / "apps" / "tesseract" / "current")))
            # Both application trees are exposed, not the stale scoop shims.
            self.assertIn(str(root / "10-toolchains" / "scoop" / "apps" / "ffmpeg" / "current" / "bin"), found["PATH"])
            self.assertTrue(Path(found["TESSDATA_PREFIX"]).is_dir())

    def test_second_variable_name_is_accepted(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = _fake_root(Path(tmp), msvc=False, rust=True, tesseract=False, tessdata=False)
            self.os.environ["ARCHEAXIS_EXTERNAL_ROOT"] = str(root)
            self.assertEqual(set(dev.external_toolchain()), {"ARCHEAXIS_RUST_TOOLCHAINS"})

    def test_a_valid_inherited_value_wins(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = _fake_root(Path(tmp), msvc=True, rust=True, tesseract=False, tessdata=True)
            self.os.environ["OS_EXTERNAL_CONFIG"] = str(root)
            self.os.environ["TESSDATA_PREFIX"] = str(root)
            found = dev.external_toolchain()
            self.assertNotIn("TESSDATA_PREFIX", found, "a directory that exists is kept")

    def test_a_nonexistent_inherited_value_is_replaced(self) -> None:
        """This host's profile pointed TESSDATA_PREFIX at an absent sibling tree."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = _fake_root(Path(tmp), msvc=False, rust=False, tesseract=False, tessdata=True)
            self.os.environ["OS_EXTERNAL_CONFIG"] = str(root)
            self.os.environ["TESSDATA_PREFIX"] = str(Path(tmp) / "stale-language-directory")
            found = dev.external_toolchain()
            self.assertEqual(Path(found["TESSDATA_PREFIX"]), root / "10-toolchains" / "scoop" / "apps" / "tesseract-languages" / "current")

    def test_path_is_not_duplicated_when_already_present(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = _fake_root(Path(tmp), msvc=False, rust=False, tesseract=True, tessdata=False)
            tesseract = str(root / "10-toolchains" / "scoop" / "apps" / "tesseract" / "current")
            self.os.environ["OS_EXTERNAL_CONFIG"] = str(root)
            self.os.environ["PATH"] = tesseract + self.os.pathsep + self.os.environ.get("PATH", "")
            self.assertNotIn("PATH", dev.external_toolchain())


if __name__ == "__main__":
    unittest.main()
