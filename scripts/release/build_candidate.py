"""Build a candidate bundle from a real build, and bind it to a commit by hash.

    python -X utf8 scripts/release/build_candidate.py [--out DIR] [--allow-debug] [--zip]

What lands: the Core binary, a generated README, and ``CANDIDATE.json`` recording the source
commit, the build kind and the size and sha256 of every file. The bundle is written under the
governed ``.project-local`` location by default and is never committed: the repository tracks
the recipe and the manifest rules, not build output.

Refusals are named: a missing binary, a commit that is not in this repository, a release build
that was asked for when only a debug binary exists. Nothing is copied before those checks pass.
"""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = REPO / ".project-local" / "build" / "cargo"


def _load_candidate_module():
    spec = importlib.util.spec_from_file_location("archeaxis_candidate", Path(__file__).with_name("candidate.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("candidate.py is missing beside this script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


candidate = _load_candidate_module()


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _tree_state() -> tuple[bool, bool]:
    """(clean tracked tree, untracked paths present). Untracked files are recorded, not fatal."""
    modified = _git("status", "--porcelain", "--untracked-files=no")
    untracked = _git("status", "--porcelain", "--untracked-files=all")
    return (not modified.strip(), bool(untracked.strip()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="build a candidate bundle")
    parser.add_argument("--out", type=Path, default=None, help="bundle directory")
    parser.add_argument("--commit", default=None, help="source commit (default: HEAD)")
    parser.add_argument("--binary", type=Path, default=None, help="binary to bundle")
    parser.add_argument("--allow-debug", action="store_true", help="accept a debug build and label it as one")
    parser.add_argument("--allow-dirty", action="store_true", help="bundle an uncommitted tree, labelled as such")
    parser.add_argument("--zip", action="store_true", help="also write a zip and its sha256")
    args = parser.parse_args(argv)

    try:
        commit = args.commit or _git("rev-parse", "HEAD")
        subject = _git("log", "-1", "--format=%s", commit)
        if not _git("cat-file", "-t", commit).strip() == "commit":
            raise RuntimeError(f"{commit} is not a commit")
    except (RuntimeError, subprocess.SubprocessError) as error:
        print(f"cannot bind a candidate to a source commit: {error}", file=sys.stderr)
        return 3

    kind = "release-build"
    binary = args.binary
    if binary is None:
        release = DEFAULT_TARGET / "release" / "archeaxis-api.exe"
        debug = DEFAULT_TARGET / "debug" / "archeaxis-api.exe"
        if release.is_file():
            binary = release
        elif debug.is_file() and args.allow_debug:
            binary = debug
            kind = "debug-build"
        elif debug.is_file():
            print(
                f"only a debug binary exists at {debug}: pass --allow-debug to bundle it and label it "
                "as a debug build, or build the release profile first",
                file=sys.stderr,
            )
            return 2
        else:
            print(f"no Core binary found under {DEFAULT_TARGET}", file=sys.stderr)
            return 2
    if not binary.is_file():
        print(f"the requested binary does not exist: {binary}", file=sys.stderr)
        return 2
    if "release" not in binary.parts and kind == "release-build":
        kind = "debug-build"
        print("the given binary is not under a release target directory, so it is labelled a debug build")

    name = f"archeaxis-core-{commit[:12]}-{kind}"
    out = args.out or (REPO / ".project-local" / "dist" / name)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    target_binary = out / binary.name
    shutil.copy2(binary, target_binary)

    clean, untracked = _tree_state()
    # The same rule scripts/launch/core_launch.py --manifest already applies to artifacts: a
    # manifest may only describe a tested commit, so a modified tracked file stops the bundle
    # unless the caller says out loud that it wants one built anyway.
    if not clean and not args.allow_dirty:
        print(
            "the tracked worktree has uncommitted changes, so a bundle built now would not "
            "correspond to a commit: commit first, or pass --allow-dirty to record the label",
            file=sys.stderr,
        )
        return 5
    built_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = candidate.write_bundle(
        out,
        [target_binary],
        commit=commit,
        commit_subject=subject,
        kind=kind,
        built_at=built_at,
        tree_clean=clean,
        untracked_present=untracked,
        python_hint=f"{sys.version_info.major}.{sys.version_info.minor}",
    )

    problems = candidate.verify_manifest(out, manifest, known_commits={commit})
    if problems:
        print("the bundle does not match its own manifest, so it is not offered:")
        for item in problems:
            print(f"  - {item}")
        return 4

    print(f"candidate written to {out}")
    print(f"  source commit   {commit[:12]} ({subject[:60]})")
    print(f"  build kind      {kind}")
    print(f"  tracked tree    {'clean' if clean else 'HAS UNCOMMITTED CHANGES'} when built")
    print(f"  files           {len(manifest['files'])}, total {sum(item['bytes'] for item in manifest['files'])} bytes")
    for item in manifest["files"]:
        print(f"  {item['path']:20s} {item['bytes']:>12,d} bytes  sha256 {item['sha256'][:16]}...")

    if args.zip:
        archive = out.with_suffix(".zip")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(p for p in out.rglob("*") if p.is_file()):
                bundle.write(path, path.relative_to(out).as_posix())
        digest = candidate.sha256_of(archive)
        sidecar = archive.with_suffix(".zip.sha256")
        sidecar.write_text(f"{digest}  {archive.name}\n", encoding="utf-8", newline="\n")
        print(f"archive         {archive}")
        print(f"  sha256        {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
