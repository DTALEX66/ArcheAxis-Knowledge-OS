"""Per-worktree size must mean bytes that worktree owns, not bytes it can reach.

`frontend/node_modules` is a link to one shared install that several worktrees point at. While the
walker followed links, every such worktree reported the same ~190 MB as its own, so the report's
central question - which bytes are duplicated and which are shared once - could not be answered
from it. The junction here is created for real, because the defect only exists for real reparse
points: `Path.is_symlink()` says False and `is_dir(follow_symlinks=False)` says True for one.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "storage_report_under_test", ROOT / "scripts" / "runtime" / "storage_report.py")
assert SPEC and SPEC.loader
report = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = report
SPEC.loader.exec_module(report)


def make_junction(link: Path, target: Path) -> None:
    if os.name != "nt":
        pytest.skip("junctions are a Windows reparse-point concept")
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        pytest.skip(f"could not create a junction here: {result.stdout.strip()[-160:]}")


@pytest.fixture()
def tree(tmp_path: Path) -> Path:
    shared = tmp_path / "shared-install"
    shared.mkdir()
    (shared / "big.js").write_bytes(b"x" * 5000)
    worktree = tmp_path / "worktree"
    frontend = worktree / "frontend"
    frontend.mkdir(parents=True)
    (frontend / "app.ts").write_bytes(b"y" * 1000)
    make_junction(frontend / "node_modules", shared)
    return worktree


def test_a_linked_directory_is_not_counted_as_owned_bytes(tree: Path) -> None:
    assert report.directory_size(tree) == 1000, "the shared install was counted into the worktree"
    assert report.directory_size(tree / "frontend" / "node_modules") == 0


def test_ordinary_directories_are_still_walked(tmp_path: Path) -> None:
    """The companion assertion that keeps the previous test from passing by measuring nothing."""
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "file").write_bytes(b"z" * 4096)
    (tmp_path / "sibling").write_bytes(b"w" * 64)
    assert report.directory_size(tmp_path) == 4096 + 64


def test_links_are_reported_with_their_target_so_shared_bytes_have_one_owner(tree: Path) -> None:
    links = report.links_under(tree)
    assert len(links) == 1, links
    assert links[0]["link"].endswith("node_modules")
    assert (Path(links[0]["link"]) / "big.js").read_bytes() == b"x" * 5000, "target is wrong"


def test_is_link_distinguishes_a_junction_from_a_real_directory(tree: Path, tmp_path: Path) -> None:
    entries = {Path(entry.path).name: entry
               for entry in os.scandir(tree / "frontend")}
    assert report.is_link(entries["node_modules"]) is True
    assert report.is_link(entries["app.ts"]) is False
    plain = tmp_path / "plain-dir"
    plain.mkdir()
    with os.scandir(tmp_path) as scanned:
        found = {entry.name: entry for entry in scanned}
    assert report.is_link(found["plain-dir"]) is False


def test_the_report_names_the_link_it_excluded(tmp_path: Path, monkeypatch) -> None:
    """Excluding shared bytes silently would read as "the install disappeared".

    The record has to carry the link and its target, so a reader can see that 190 MB is someone
    else's line rather than missing from this one.
    """
    subprocess.run(["git", "init", "-q", str(tmp_path / "repo")], check=True)
    repo = tmp_path / "repo"
    frontend = repo / "frontend"
    frontend.mkdir()
    (frontend / "app.ts").write_bytes(b"y" * 1000)
    shared = tmp_path / "shared-install"
    shared.mkdir()
    (shared / "big.js").write_bytes(b"x" * 5000)
    make_junction(frontend / "node_modules", shared)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)

    monkeypatch.setattr(report, "REPO", repo)
    measured = report.measure()
    entry = next(item for item in measured["root"] if item["name"] == "frontend/")
    assert entry["bytes"] == 1000, entry
    assert [Path(link["target"]).name for link in entry["links"]] == ["shared-install"], entry


def test_unreadable_subtree_is_reported_with_readable_lower_bound(tmp_path, monkeypatch):
    (tmp_path / "good.bin").write_bytes(b"abc")
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    real_scandir = os.scandir

    def denied(path):
        if Path(path) == blocked:
            raise PermissionError(13, "fixture denial", str(path))
        return real_scandir(path)

    monkeypatch.setattr(report.os, "scandir", denied)
    measured = report.directory_measurement(tmp_path)
    assert measured["bytes"] == 3
    assert measured["errors"] == [{"path": str(blocked), "error": "PermissionError", "errno": 13}]


def test_private_subtree_is_excluded_before_any_descent(tmp_path, monkeypatch):
    private = tmp_path / ".codex"
    private.mkdir()
    (private / "fixture.bin").write_bytes(b"excluded")
    real_scandir = os.scandir

    def guarded(path):
        assert not Path(path).is_relative_to(private), "private subtree was accessed"
        return real_scandir(path)

    monkeypatch.setattr(report.os, "scandir", guarded)
    measured = report.directory_measurement(tmp_path)
    assert measured["bytes"] == 0
    assert measured["excluded_private"] == [str(private)]
    assert report.links_under(tmp_path) == []
    assert report.directory_measurement(private)["excluded_private"] == [str(private)]


def test_report_cannot_certify_complete_measurement_after_access_denial(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    source = repo / "frontend"
    source.mkdir()
    (source / "app.ts").write_bytes(b"x")
    subprocess.run(["git", "add", "frontend/app.ts"], cwd=repo, check=True)
    real_scandir = os.scandir

    def denied(path):
        if Path(path) == source:
            raise PermissionError(13, "fixture denial", str(path))
        return real_scandir(path)

    monkeypatch.setattr(report.os, "scandir", denied)
    measured = report.measure(repo)
    assert measured["measurement_status"] == "PARTIAL"
    assert measured["measurement_errors"][0]["path"] == str(source)
    assert measured["root"][0]["bytes"] == 0  # explicitly a lower bound, not a complete zero
    assert "lower bound" in measured["byte_semantics"]


def test_foreign_checkout_is_filtered_before_filesystem_probe(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    foreign = tmp_path / ".ui-task-tree" / "private"
    real_is_dir = Path.is_dir

    def guarded(path):
        assert path != foreign, "private checkout was probed"
        return real_is_dir(path)

    calls = iter([
        subprocess.CompletedProcess([], 0, str(repo / ".git") + "\n", ""),
        subprocess.CompletedProcess([], 0, f"worktree {foreign}\n", ""),
    ])
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: next(calls))
    monkeypatch.setattr(Path, "is_dir", guarded)
    excluded = []
    assert report.checkout_roots(repo, excluded) == [repo]
    assert excluded == [str(foreign)]


def test_measurement_rejects_protected_root_before_scanning(monkeypatch):
    monkeypatch.setattr(report.os, "scandir", lambda *a: pytest.fail("protected root scanned"))
    with pytest.raises(ValueError, match="protected"):
        report.measure(Path("F:/not-authorized"))


def test_declared_local_roots_are_not_relocation_candidates():
    import yaml
    authority = yaml.safe_load((ROOT / "DIRECTORY_AUTHORITY.yaml").read_text(encoding="utf-8"))
    names = [Path(path.rstrip("/")).name for path in authority["ignored_local_roots"]]
    assert all(report.dev_allowed(name) for name in names), names


def test_retained_cache_pass_does_not_probe_private_or_link_targets(tmp_path, monkeypatch):
    dev = tmp_path / '.project-local/build'
    agents = dev / 'agents'
    agents.mkdir(parents=True)
    shared = tmp_path / 'shared'
    (shared / 'cargo').mkdir(parents=True)
    make_junction(dev / 'linked-identity', shared)
    real_is_dir = Path.is_dir
    def guarded(path):
        assert not path.is_relative_to(agents), 'private agents probed'
        assert not path.is_relative_to(dev / 'linked-identity'), 'linked target probed'
        return real_is_dir(path)
    monkeypatch.setattr(Path, 'is_dir', guarded)
    assert report.protected_bytes(dev) == 0


def test_nested_sensitive_filename_is_not_statted_or_read(tmp_path, monkeypatch):
    secret = tmp_path / 'nested/.env.local'
    secret.parent.mkdir()
    secret.write_bytes(b'fixture-only')
    real_scandir = os.scandir
    class GuardedEntry:
        def __init__(self, entry): self.entry=entry
        def __getattr__(self, name):
            assert self.entry.path != str(secret), 'protected file was probed'
            return getattr(self.entry,name)
        @property
        def name(self): return self.entry.name
        @property
        def path(self): return self.entry.path
    class GuardedScan:
        def __init__(self,path): self.scanner=real_scandir(path)
        def __enter__(self): return iter(GuardedEntry(e) for e in self.scanner.__enter__())
        def __exit__(self,*args): return self.scanner.__exit__(*args)
    monkeypatch.setattr(report.os,'scandir',GuardedScan)
    measured=report.directory_measurement(tmp_path)
    assert measured['bytes']==0
    assert measured['excluded_private']==[str(secret)]


def test_cargo_named_recovery_archive_is_not_exempt_compile_cache(tmp_path):
    recovery=tmp_path/'.project-local/recovery'
    archive=recovery/'cargo-msvc-pdb-20261006'
    archive.mkdir(parents=True)
    (archive/'pdb.zip').write_bytes(b'recovery evidence')
    assert report.protected_bytes(recovery)==0
    build=tmp_path/'.project-local/build'
    cargo=build/'0123456789/cargo'
    cargo.mkdir(parents=True)
    (cargo/'cached-object').write_bytes(b'compiled')
    assert report.protected_bytes(build)==8


def test_run_ranking_reports_unknown_checkout_without_qualifying_deletion(tmp_path, monkeypatch):
    repo = tmp_path / 'repo'
    runs = repo / '.project-local/runs/0123456789'
    (runs / 'small').mkdir(parents=True)
    (runs / 'small/file').write_bytes(b'a')
    (runs / 'large').mkdir()
    (runs / 'large/file').write_bytes(b'abc')
    monkeypatch.setattr(report, 'known_run_identities', lambda root: set())
    measured = report.rank_runs(repo)
    assert measured['measurement_status'] == 'PASS'
    assert measured['readable_bytes'] == 4
    assert [row['run_id'] for row in measured['rows']] == ['large', 'small']
    assert all(not row['checkout_present'] for row in measured['rows'])
    assert all(row['retention'] == 'UNCLASSIFIED_PRESERVE' for row in measured['rows'])
    assert measured['deletion_qualified'] is False


def test_run_ranking_rejects_junction_and_private_entries_before_descent(tmp_path, monkeypatch):
    repo = tmp_path / 'repo'
    runs = repo / '.project-local/runs'
    private = runs / '.codex'
    private.mkdir(parents=True)
    outside = tmp_path / 'outside'
    outside.mkdir()
    make_junction(runs / '0123456789', outside)
    real_iterdir = Path.iterdir
    def guarded(path):
        assert path not in (outside, private, runs / '0123456789'), 'excluded directory accessed'
        return real_iterdir(path)
    monkeypatch.setattr(Path, 'iterdir', guarded)
    monkeypatch.setattr(report, 'known_run_identities', lambda root: set())
    measured = report.rank_runs(repo)
    assert measured['measurement_status'] == 'PARTIAL'
    assert measured['rows'] == []
    assert measured['excluded'] == [str(private)]
    assert measured['errors'][0]['error'] == 'ValueError'


def test_run_ranking_keeps_access_denial_as_unknown(tmp_path, monkeypatch):
    repo = tmp_path / 'repo'
    run = repo / '.project-local/runs/0123456789/denied'
    run.mkdir(parents=True)
    real_scandir = os.scandir
    def denied(path):
        if Path(path) == run:
            raise PermissionError(13, 'fixture denial', str(path))
        return real_scandir(path)
    monkeypatch.setattr(report.os, 'scandir', denied)
    monkeypatch.setattr(report, 'known_run_identities', lambda root: {'0123456789'})
    measured = report.rank_runs(repo)
    assert measured['measurement_status'] == 'PARTIAL'
    assert measured['rows'][0]['measurement_status'] == 'PARTIAL'
    assert measured['errors'][0]['path'] == str(run)
    assert measured['deletion_qualified'] is False


def test_linked_development_and_runs_roots_are_not_enumerated(tmp_path, monkeypatch):
    repo=tmp_path/'repo'
    subprocess.run(['git','init','-q',str(repo)],check=True)
    outside=tmp_path/'outside'
    outside.mkdir()
    make_junction(repo/'.project-local',outside)
    real_iterdir=Path.iterdir
    def guarded(path):
        assert path not in (outside,repo/'.project-local'), 'linked development target enumerated'
        return real_iterdir(path)
    monkeypatch.setattr(Path,'iterdir',guarded)
    with pytest.raises(ValueError,match='linked'):
        report.measure(repo)
    dev=tmp_path/'ordinary-dev'
    dev.mkdir()
    make_junction(dev/'runs',outside)
    with pytest.raises(ValueError,match='linked'):
        report.runs_layout(dev,repo)
