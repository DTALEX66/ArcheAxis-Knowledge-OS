"""BULK-0907 P03: tests for scripts/maintenance/bulk_fixture_factory.py."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/maintenance/bulk_fixture_factory.py"


def _run(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *args],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), env=env,
    )


def _env_without_run_root() -> dict:
    return {k: v for k, v in os.environ.items() if k != "ARCHEAXIS_RUN_ROOT"}


def _env_contained_in(root: Path) -> dict:
    """Declare `root` as this test's run root.

    The factory refuses any output outside `ARCHEAXIS_RUN_ROOT`, so a test that
    writes under `tmp_path` has to say what contains it. Pytest scratch now
    lives in `.project-local/task-runtime` rather than inside a launcher run,
    so the ambient value no longer contains `tmp_path` and an inherited one
    cannot stand in for it.
    """
    return {**os.environ, "ARCHEAXIS_RUN_ROOT": str(root)}


def _read_manifest(out_dir: Path, fmt: str) -> dict:
    return json.loads((out_dir / f"{fmt}-manifest.json").read_text(encoding="utf-8"))


def test_same_seed_produces_identical_bytes(tmp_path):
    first = tmp_path / "a"
    second = tmp_path / "b"
    for out in (first, second):
        result = _run(["--out-dir", str(out), "--seed", "42", "--format", "srt"],
                      env=_env_contained_in(tmp_path))
        assert result.returncode == 0, result.stdout + result.stderr
    m1 = _read_manifest(first, "srt")["entries"][0]
    m2 = _read_manifest(second, "srt")["entries"][0]
    assert m1["sha256"] == m2["sha256"]
    assert (first / m1["name"]).read_bytes() == (second / m2["name"]).read_bytes()


def test_different_seed_changes_output(tmp_path):
    first = tmp_path / "a"
    second = tmp_path / "b"
    _run(["--out-dir", str(first), "--seed", "1", "--format", "canvas"],
         env=_env_contained_in(tmp_path))
    _run(["--out-dir", str(second), "--seed", "2", "--format", "canvas"],
         env=_env_contained_in(tmp_path))
    m1 = _read_manifest(first, "canvas")["entries"][0]
    m2 = _read_manifest(second, "canvas")["entries"][0]
    assert m1["sha256"] != m2["sha256"]


def test_manifest_expectations_are_independent_and_hold(tmp_path):
    out = tmp_path / "gen"
    result = _run(["--out-dir", str(out), "--seed", "7", "--format", "srt"],
                  env=_env_contained_in(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr
    entry = _read_manifest(out, "srt")["entries"][0]
    text = (out / entry["name"]).read_text(encoding="utf-8")
    numbered = [b for b in text.strip().split("\n\n") if b.splitlines()[0].isdigit()]
    assert len(numbered) == entry["expectations"]["cues"]
    assert "核聚变" in text or "研究" in text or "测量" in text
    expected_offsets = entry["expectations"]["offsets_ms"]
    assert len(expected_offsets) == len(numbered)
    assert expected_offsets[0] == 1000


def test_corrupt_preserves_original_hash_and_changes_bytes(tmp_path):
    gen = tmp_path / "gen"
    result = _run(["--out-dir", str(gen), "--seed", "5", "--format", "text"],
                  env=_env_contained_in(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr
    text_entry = _read_manifest(gen, "text")["entries"][0]
    original_sha = hashlib.sha256((gen / text_entry["name"]).read_bytes()).hexdigest()
    bad = _run(["--out-dir", str(gen), "--seed", "5", "--format", "corrupt",
                "--input", text_entry["name"], "--output", "corrupted.txt"],
               env=_env_contained_in(tmp_path))
    assert bad.returncode == 0, bad.stdout + bad.stderr
    corrupt_entry = _read_manifest(gen, "corrupt")["entries"][0]
    assert corrupt_entry["original_file"] == text_entry["name"]
    assert corrupt_entry["original_sha256"] == original_sha
    assert corrupt_entry["corrupt_sha256"] != original_sha
    assert (gen / "corrupted.txt").read_bytes() != (gen / text_entry["name"]).read_bytes()


def test_html_and_vtt_are_deterministic_with_expectations(tmp_path):
    out = tmp_path / "gen"
    _run(["--out-dir", str(out), "--seed", "9", "--format", "html"],
         env=_env_contained_in(tmp_path))
    _run(["--out-dir", str(out), "--seed", "9", "--format", "vtt"],
         env=_env_contained_in(tmp_path))
    html_entry = _read_manifest(out, "html")["entries"][0]
    vtt_entry = _read_manifest(out, "vtt")["entries"][0]
    html_text = (out / html_entry["name"]).read_text(encoding="utf-8")
    assert html_text.count("<li>") == html_entry["expectations"]["li_count"]
    assert html_entry["expectations"]["title"] in html_text
    vtt_text = (out / vtt_entry["name"]).read_text(encoding="utf-8")
    assert vtt_text.startswith("WEBVTT")
    assert vtt_entry["expectations"]["cues"] >= 1


def test_missing_run_root_writes_nothing(tmp_path):
    target = tmp_path / "never"
    result = _run(["--out-dir", str(target), "--seed", "3", "--format", "text"],
                  env=_env_without_run_root())
    assert result.returncode == 2
    assert not target.exists()


def test_output_escape_is_rejected(tmp_path):
    result = _run(["--out-dir", "../escape", "--seed", "3", "--format", "text"],
                  env=_env_contained_in(tmp_path))
    assert result.returncode == 2
    assert "escape" in (result.stderr or "").lower()


def test_absolute_output_outside_run_root_is_rejected(tmp_path):
    allowed = tmp_path / 'allowed'
    target = tmp_path / 'outside'
    result = _run(['--out-dir', str(target), '--seed', '1', '--format', 'text'],
                  env={**os.environ, 'ARCHEAXIS_RUN_ROOT': str(allowed)})
    assert result.returncode == 2
    assert not target.exists()


def test_linked_output_inside_run_root_is_rejected(tmp_path):
    import pytest
    target = tmp_path / 'target'
    target.mkdir()
    link = tmp_path / 'link'
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip('host cannot create a directory symlink')
    result = _run(['--out-dir', str(link / 'generated'), '--seed', '1', '--format', 'text'],
                  env=_env_contained_in(tmp_path))
    assert result.returncode == 2
    assert not (target / 'generated').exists()


def test_corrupt_output_cannot_escape_its_directory(tmp_path):
    out = tmp_path / 'fixtures'
    out.mkdir()
    (out / 'input.txt').write_text('original')
    escaped = tmp_path / 'escaped.txt'
    for name in ('../escaped.txt', str(escaped)):
        result = _run(['--out-dir', str(out), '--seed', '1', '--format', 'corrupt',
                       '--input', 'input.txt', '--output', name],
                      env=_env_contained_in(out))
        assert result.returncode == 2
        assert not escaped.exists()


def test_final_file_and_manifest_links_are_not_followed(tmp_path):
    import pytest
    for name in ('text-00.txt', 'text-manifest.json'):
        out = tmp_path / name.replace('.', '-')
        out.mkdir()
        target = tmp_path / ('protected-' + name)
        target.write_bytes(b'preserve')
        try:
            (out / name).symlink_to(target)
        except OSError:
            pytest.skip('host cannot create symlinks')
        result = _run(['--out-dir', str(out), '--seed', '1', '--format', 'text'],
                      env=_env_contained_in(out))
        assert result.returncode == 2
        assert target.read_bytes() == b'preserve'
