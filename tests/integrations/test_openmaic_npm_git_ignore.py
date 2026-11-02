"""Check source availability in Git; this is not release qualification."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "services/learning-providers/openmaic/vendor/npm"
SOURCES = {
    "partial-json-0.1.7": (4, "b2513602f3097aa7f6d090fa50290b9f7e00603a61a71c20882f5fb0963e5403"),
    "es-module-lexer-2.0.0": (8, "2c222673e20d94f84a03d8a277df5a91c842053a6e991a44cec6b62e8aa45d71"),
    "entities-6.0.1": (86, "2931e2cb2561ccdd29a1c14eb11527e983138ecc2dc31021ede7123f95d11bf6"),
    "svg-pathdata-8.0.0": (176, "2d619e3e74942771048204c6740274bfb04e5eb544cde3ad11da982aa121481b"),
    "tinycolor2-1.6.0": (14, "523960b84b6cde69b861ec911da3d58fdc75035f1bcf825ca75963402c958bfb"),
    "parse5-8.0.1": (33, "fb5a2c507c9c2d2c59073df562e2131ada5860b3370ebc9508762bc4be1cad30"),
    "entities-8.0.0": (58, "91fd19349c025f903464fe8d0e4ab5464708db4386024dbd9957c273c91a422c"),
}


def checked_paths() -> dict[str, list[str]]:
    result = {}
    for stem, (count, source_sha) in SOURCES.items():
        root = VENDOR / stem
        raw = (root / "SOURCE.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == source_sha
        files = json.loads(raw)["files"]
        assert isinstance(files, dict) and len(files) == count
        actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
        assert actual == set(files) | {"SOURCE.json"}
        paths = []
        for name, identity in files.items():
            relative = PurePosixPath(name)
            assert not relative.is_absolute() and ".." not in relative.parts
            path = root.joinpath(*relative.parts)
            assert path.is_file() and not path.is_symlink()
            data = path.read_bytes()
            assert (len(data), hashlib.sha256(data).hexdigest()) == (identity["bytes"], identity["sha256"])
            paths.append(path.relative_to(ROOT).as_posix())
        paths.append((root / "SOURCE.json").relative_to(ROOT).as_posix())
        assert any("/dist/" in path for path in paths)
        result[stem] = sorted(paths)
    assert sum(map(len, result.values())) == 386
    return result


def clean_environment(index_path: Path) -> dict[str, str]:
    # Git environment overrides can hide ignore rules or select another repo.
    # Preserve normal user/system configuration; never replace it with /dev/null
    # for the real checkout. The isolated, absent index is never written.
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env["GIT_INDEX_FILE"] = str(index_path)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return env


def invoke_git(git: str, root: Path, env: dict[str, str], *args, data=None, allowed=(0,)):
    process = subprocess.run([git, "-c", f"safe.directory={root}", "-C", str(root), *args],
                             input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=20, env=env, check=False)
    assert process.returncode in allowed, f"Git exited {process.returncode}; ignore status is unverified"
    assert not process.stderr, "Git reported a configuration or ignore warning; ignore status is unverified"
    assert not Path(env["GIT_INDEX_FILE"]).exists(), "Git unexpectedly wrote the isolated index"
    return process


def require_readable_effective_excludes(git: str, root: Path, env: dict[str, str]) -> None:
    configured = invoke_git(git, root, env, "config", "--path", "--get", "core.excludesFile", allowed=(0, 1))
    if configured.returncode == 0:
        lines = configured.stdout.splitlines()
        assert len(lines) == 1 and lines[0], "Git global ignore path is ambiguous"
        path = Path(os.fsdecode(lines[0]))
        if not path.is_absolute():
            path = root / path
    else:
        assert not configured.stdout
        xdg = env.get("XDG_CONFIG_HOME")
        if xdg:
            assert Path(xdg).is_absolute(), "relative XDG_CONFIG_HOME makes the Git ignore path ambiguous"
            path = Path(xdg) / "git/ignore"
        else:
            home = env.get("HOME") or env.get("USERPROFILE")
            assert home and Path(home).is_absolute(), "Git home is unavailable; global ignore status is unverified"
            path = Path(home) / ".config/git/ignore"
    try:
        path.stat()
    except FileNotFoundError:
        return
    except OSError as error:
        raise AssertionError("Git global ignore path is unreadable; ignore status is unverified") from error
    try:
        with path.open("rb") as stream:
            stream.read(1)
    except OSError as error:
        raise AssertionError("Git global ignore file is unreadable; ignore status is unverified") from error


def ignored_paths(git: str, root: Path, env: dict[str, str], paths: list[str]) -> set[str]:
    assert paths and len(paths) == len(set(paths))
    encoded = [path.encode("utf-8") for path in paths]
    assert all(b"\0" not in value for value in encoded)
    process = invoke_git(git, root, env, "check-ignore", "--no-index", "-z", "--stdin",
                         data=b"\0".join(encoded) + b"\0", allowed=(0, 1))
    if process.returncode == 1:
        assert not process.stdout
        return set()
    records = process.stdout.split(b"\0")
    assert records[-1] == b"" and len(records) > 1
    ignored = [value.decode("utf-8") for value in records[:-1]]
    assert len(ignored) == len(set(ignored)) and set(ignored) <= set(paths)
    return set(ignored)


def configuration_environments(index: Path) -> list[dict[str, str]]:
    env = clean_environment(index)
    if os.name == "nt" and env.get("HOME") and env.get("USERPROFILE"):
        if Path(env["HOME"]).resolve() != Path(env["USERPROFILE"]).resolve():
            pytest.skip("HOME differs from the Windows profile; global ignore status is ambiguous")
    environments = [env]
    # Check the effective XDG configuration and the usual home configuration
    # separately so an alternate XDG directory cannot conceal a default ignore.
    if env.get("XDG_CONFIG_HOME"):
        without_xdg = dict(env)
        without_xdg.pop("XDG_CONFIG_HOME")
        environments.append(without_xdg)
    return environments


def test_no_preserved_member_is_git_ignored(tmp_path):
    git = shutil.which("git")
    if not git:
        pytest.skip("Git is unavailable")
    if not (ROOT / ".git").exists():
        pytest.skip("not a Git checkout")
    groups = checked_paths()
    index = tmp_path / "unused-index"
    assert not index.exists()
    paths = [path for group in groups.values() for path in group]
    for candidate_env in configuration_environments(index):
        probe = invoke_git(git, ROOT, candidate_env, "rev-parse", "--show-toplevel")
        assert Path(os.fsdecode(probe.stdout.strip())).resolve() == ROOT.resolve()
        require_readable_effective_excludes(git, ROOT, candidate_env)
        ignored = ignored_paths(git, ROOT, candidate_env, paths)
        assert not ignored, f"preserved npm members would be omitted by Git: {sorted(ignored)}"


def test_unlisted_fictional_dist_paths_remain_ignored_by_project_rule(tmp_path):
    git = shutil.which("git")
    if not git:
        pytest.skip("Git is unavailable")
    if not (ROOT / ".git").exists():
        pytest.skip("not a Git checkout")
    paths = ["services/learning-providers/openmaic/vendor/npm/unlisted-probe-0.0.0/dist/file.js",
             "frontend/unlisted-ignore-probe/dist/file.js"]
    assert all(not (ROOT / path).exists() for path in paths)
    index = tmp_path / "unused-index"
    for env in configuration_environments(index):
        require_readable_effective_excludes(git, ROOT, env)
        process = invoke_git(git, ROOT, env, "check-ignore", "--no-index", "-v", "-z", "--stdin",
                             data=b"\0".join(path.encode() for path in paths) + b"\0")
        records = process.stdout.split(b"\0")
        assert records[-1] == b"" and len(records) == 4 * len(paths) + 1
        for offset, path in enumerate(paths):
            source, line, pattern, actual = records[4 * offset:4 * offset + 4]
            assert source == b".gitignore" and line.isdigit() and pattern == b"dist/" and actual == path.encode()


def test_synthetic_dist_ignore_is_detected_without_real_index(tmp_path, monkeypatch):
    git = shutil.which("git")
    if not git:
        pytest.skip("Git is unavailable")
    # A hostile inherited config override must not control the checked repo.
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.excludesFile")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", os.devnull)
    index = tmp_path / "unused-index"
    env = clean_environment(index)
    assert "GIT_CONFIG_COUNT" not in env and "GIT_CONFIG_KEY_0" not in env and "GIT_CONFIG_VALUE_0" not in env
    # Isolate only this synthetic repo from user/system ignores.
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    temp_repo = tmp_path / "ignore-red"
    temp_repo.mkdir()
    empty_templates = tmp_path / "empty-templates"
    empty_templates.mkdir()
    empty_global = tmp_path / "empty-global-ignore"
    empty_global.write_bytes(b"")
    # Apply the task-owned ignore configuration to every Git call in this
    # synthetic repository, including the later check-ignore subprocess.
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "core.excludesFile"
    env["GIT_CONFIG_VALUE_0"] = str(empty_global)
    invoke_git(git, temp_repo, env, "-c", f"core.excludesFile={empty_global}", "init", "--quiet",
               f"--template={empty_templates}")
    (temp_repo / ".gitignore").write_bytes(b"dist/\n")
    expected = set()
    controls = set()
    for stem in SOURCES:
        ignored = f"{stem}/dist/probe.js"
        control = f"{stem}/SOURCE.json"
        (temp_repo / ignored).parent.mkdir(parents=True, exist_ok=True)
        (temp_repo / ignored).write_bytes(b"synthetic\n")
        (temp_repo / control).write_bytes(b"{}\n")
        expected.add(ignored)
        controls.add(control)
    actual = ignored_paths(git, temp_repo, env, sorted(expected | controls))
    assert actual == expected and not actual.intersection(controls)
    assert not (temp_repo / ".git/index").exists()
