"""Discovery of the registered external toolchain must be driven by the declaration.

`scripts/runtime/dev.py::external_toolchain` is what stopped two environment
blockers that had nothing to do with the code: `cargo test` failed with
``linker `link.exe` not found`` and an OCR worker failed with ``AAK-WORKER-003``,
although the MSVC linker and tesseract were both installed under the registered
external root. The danger of a discovery step is the opposite failure - inventing a
path, or overriding a good one - so these tests pin the conditions rather than the
host's real layout.

They also pin the fix for the three-roots-for-one-tool defect: the launcher no longer
carries its own idea of where Rust or MSVC lives. It reads the same
`config/environment/capability-requirements.yaml` the workers and the index read, so a
layout that is not declared cannot be exported, and a fake root that satisfies the
declaration is enough to make discovery answer.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

LAUNCHER = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(LAUNCHER))

from runtime import dev  # noqa: E402  (path set above, mirroring the other dev-path tests)

# The locations the declaration names, as one place to keep them honest.
MSVC_VCVARS = Path("10-toolchains") / "msvc" / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
RUSTC = Path("toolchains") / "rust" / "cargo" / "bin" / "rustc.exe"
CARGO = Path("toolchains") / "rust" / "cargo" / "bin" / "cargo.exe"
RUSTUP = Path("toolchains") / "rust" / "rustup"
TESSERACT = Path("10-toolchains") / "scoop" / "apps" / "tesseract" / "current" / "tesseract.exe"
TESSDATA = Path("10-toolchains") / "scoop" / "apps" / "tesseract-languages" / "current"
FFMPEG = Path("10-toolchains") / "scoop" / "apps" / "ffmpeg" / "current" / "bin" / "ffmpeg.exe"


def _fake_root(
    base: Path, *, msvc: bool, rust: bool, tesseract: bool, tessdata: bool, ffmpeg: bool = False
) -> Path:
    """An external root that satisfies the declaration, in the shapes the declaration uses."""
    root = base / "external"
    for relative, is_dir in (
        (MSVC_VCVARS if msvc else None, False),
        (RUSTC if rust else None, False),
        (CARGO if rust else None, False),
        (RUSTUP if rust else None, True),
        (TESSERACT if tesseract else None, False),
        (TESSDATA if tessdata else None, True),
        (FFMPEG if ffmpeg else None, False),
    ):
        if relative is None:
            continue
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if is_dir:
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.write_bytes(b"MZ")
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
                "RUSTUP_HOME",
                "CARGO_HOME",
                "TESSDATA_PREFIX",
                "ARCHEAXIS_RESOURCE_PROBE_WORKDIR",
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

    def test_complete_root_discovers_the_declared_binding(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = _fake_root(Path(tmp), msvc=True, rust=True, tesseract=True, tessdata=True, ffmpeg=True)
            self.os.environ["OS_EXTERNAL_CONFIG"] = str(root)
            found = dev.external_toolchain()
            self.assertEqual(
                set(found),
                {"ARCHEAXIS_EXTERNAL_ROOT", "ARCHEAXIS_MSVC_VCVARS", "RUSTUP_HOME",
                 "ARCHEAXIS_RUST_TOOLCHAINS", "PATH", "TESSDATA_PREFIX"},
            )
            # The child gets the root variable too: the worker tool resolver reads it to find
            # a declared ffmpeg, and without it the windowed and OCR cases skip.
            self.assertEqual(found["ARCHEAXIS_EXTERNAL_ROOT"], str(root))
            self.assertTrue(Path(found["ARCHEAXIS_MSVC_VCVARS"]).is_file())
            self.assertEqual(Path(found["ARCHEAXIS_MSVC_VCVARS"]), root / MSVC_VCVARS)
            self.assertTrue((Path(found["ARCHEAXIS_RUST_TOOLCHAINS"]) / "cargo" / "bin" / "cargo.exe").is_file())
            # One Rust binding, three readers: the declared toolchain root, the RUSTUP_HOME the
            # rustup proxies need, and ARCHEAXIS_RUST_TOOLCHAINS (what cargo_test.bat expands)
            # must all name the same directory tree.
            self.assertEqual(Path(found["ARCHEAXIS_RUST_TOOLCHAINS"]), root / "toolchains" / "rust")
            self.assertEqual(Path(found["RUSTUP_HOME"]), root / RUSTUP)
            self.assertTrue(found["PATH"].startswith(str(root / TESSERACT.parent)))
            # Both application trees are exposed, not the stale scoop shims.
            self.assertIn(str(root / FFMPEG.parent), found["PATH"])
            # The Rust proxies live in cargo/bin, so the bare `rustc`/`cargo` a shell calls is
            # the declared one and not an ambient toolchain.
            self.assertIn(str(root / CARGO.parent), found["PATH"])
            self.assertTrue(Path(found["TESSDATA_PREFIX"]).is_dir())

    def test_the_rust_proxies_answer_with_the_discovered_environment(self) -> None:
        """The exported RUSTUP_HOME is not decoration: without it the declared rustc dies.

        Measured on this host: `toolchains/rust/cargo/bin/rustc.exe --version` with no
        RUSTUP_HOME returns rc 1 with ``Missing manifest in toolchain
        'stable-x86_64-pc-windows-msvc'``, while the neighbouring `cargo.exe` answers a
        *different* toolchain's version (1.98.1) from the host default - a silent
        substitution inside one declared row.
        """
        import shutil
        import subprocess
        import tempfile

        # setUp scrubs the host environment for isolation, so reading os.environ here would
        # always come back empty and this proof would self-skip forever. The pre-scrub snapshot
        # is the only place the host's declared root is still visible.
        root_text = ((self._saved.get("ARCHEAXIS_EXTERNAL_ROOT") or "").strip()
                     or (self._saved.get("OS_EXTERNAL_CONFIG") or "").strip())
        if not root_text:
            self.skipTest("no external root in this environment")
        self.os.environ["OS_EXTERNAL_CONFIG"] = root_text
        found = dev.external_toolchain(Path(__file__).resolve().parents[2])
        child = dict(self.os.environ)
        child.update(found)
        located = shutil.which("rustc", path=child.get("PATH"))
        self.assertIsNotNone(located, "the discovered PATH must carry the declared rustc")
        result = subprocess.run([located, "--version"], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", env=child, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("rustc", result.stdout)
        cargo = shutil.which("cargo", path=child.get("PATH"))
        second = subprocess.run([cargo, "--version"], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", env=child, timeout=60)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        # Both proxies resolve the same toolchain, which is what a single binding means.
        self.assertEqual(result.stdout.split()[1], second.stdout.split()[1])

    def test_second_variable_name_is_accepted(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = _fake_root(Path(tmp), msvc=False, rust=True, tesseract=False, tessdata=False)
            self.os.environ["ARCHEAXIS_EXTERNAL_ROOT"] = str(root)
            # ARCHEAXIS_EXTERNAL_ROOT is already set here, so it is not re-added.
            self.assertEqual(set(dev.external_toolchain()),
                             {"RUSTUP_HOME", "ARCHEAXIS_RUST_TOOLCHAINS", "PATH"})

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
            self.assertEqual(Path(found["TESSDATA_PREFIX"]), root / TESSDATA)

    def test_home_is_never_exported_for_every_child(self) -> None:
        """antiword needs `$HOME/.antiword`, and that belongs to its own subprocess only.

        The declaration carries it because the engine requires it; the launcher must not turn
        it into a global HOME for every child it spawns. This is the AGENTS.md rule that the
        launcher "never changes HOME", tested against the field that made the temptation real.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = _fake_root(Path(tmp), msvc=False, rust=False, tesseract=False, tessdata=False)
            (root / "10-toolchains" / "antiword" / ".antiword").mkdir(parents=True, exist_ok=True)
            (root / "10-toolchains" / "antiword" / "antiword.exe").write_bytes(b"MZ")
            self.os.environ["OS_EXTERNAL_CONFIG"] = str(root)
            found = dev.external_toolchain()
            self.assertNotIn("HOME", found)
            self.assertNotIn("CARGO_HOME", found, "the launcher routes the dependency cache itself")

    def test_path_is_not_duplicated_when_already_present(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = _fake_root(Path(tmp), msvc=False, rust=False, tesseract=True, tessdata=False)
            tesseract = str(root / TESSERACT.parent)
            self.os.environ["OS_EXTERNAL_CONFIG"] = str(root)
            self.os.environ["PATH"] = tesseract + self.os.pathsep + self.os.environ.get("PATH", "")
            found = dev.external_toolchain()
            self.assertNotIn(tesseract, found.get("PATH", "").split(self.os.pathsep)[:1])

    def test_a_recorded_root_is_used_when_the_environment_registers_none(self) -> None:
        """The tracked index may supply the host's root, but never override the environment.

        Without this, a host whose root is recorded but not exported silently skips the nine
        tool-backed format cases -- 287 passed with 9 skipped instead of 296 with none. A
        recorded path that does not exist is ignored, which is what keeps CI unaffected.
        """
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "config" / "environment").mkdir(parents=True)
            index = repo / "config" / "environment" / "external-resources-index.json"
            root = _fake_root(repo / "host", msvc=False, rust=False, tesseract=True, tessdata=False)
            index.write_text(json.dumps({"external_root": str(root)}), encoding="utf-8")
            found = dev.external_toolchain(repo)
            self.assertEqual(found.get("ARCHEAXIS_EXTERNAL_ROOT"), str(root))

            index.write_text(json.dumps({"external_root": str(repo / "absent")}), encoding="utf-8")
            self.assertEqual(dev.external_toolchain(repo), {})

            # An exported root still wins over the index.
            self.os.environ["ARCHEAXIS_EXTERNAL_ROOT"] = str(repo / "absent")
            self.assertEqual(dev.external_toolchain(repo), {})

    def test_the_probe_workdir_follows_the_run_directory(self) -> None:
        """A verification sample must land in the task path, not in the machine temp."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = _fake_root(Path(tmp), msvc=False, rust=False, tesseract=True, tessdata=True)
            self.os.environ["OS_EXTERNAL_CONFIG"] = str(root)
            run_tmp = Path(tmp) / "run-tmp"
            found = dev.external_toolchain(run_tmp=run_tmp)
            self.assertEqual(Path(found["ARCHEAXIS_RESOURCE_PROBE_WORKDIR"]).parent, run_tmp)

    def test_an_explicit_probe_workdir_is_kept(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = _fake_root(Path(tmp), msvc=False, rust=False, tesseract=True, tessdata=True)
            self.os.environ["OS_EXTERNAL_CONFIG"] = str(root)
            self.os.environ["ARCHEAXIS_RESOURCE_PROBE_WORKDIR"] = str(Path(tmp) / "operator-chosen")
            found = dev.external_toolchain(run_tmp=Path(tmp) / "run-tmp")
            self.assertNotIn("ARCHEAXIS_RESOURCE_PROBE_WORKDIR", found, "an operator value wins")


if __name__ == "__main__":
    unittest.main()
