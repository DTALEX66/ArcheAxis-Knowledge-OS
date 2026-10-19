"""核对冻结原字节、规范入口和隔离Git检出；不运行产品或读取私人客户端。"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import uuid

ARCHIVE = Path(__file__).resolve().parent
REPO = ARCHIVE.parents[3]

def confined(base, ref):
    pure = PurePosixPath(ref)
    if pure.is_absolute() or ".." in pure.parts or ":" in ref or "\\" in ref:
        raise ValueError("Unsafe reference")
    path = base.joinpath(*pure.parts)
    for item in (path, *path.parents):
        if item == base:
            break
        if item.exists() and (item.is_symlink() or getattr(item.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise ValueError("Linked reference refused")
    path.resolve().relative_to(base.resolve())
    return path

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def long_path(path):
    return Path("\\\\?\\" + str(path.absolute())) if os.name == "nt" else path

args_parser = argparse.ArgumentParser()
args_parser.add_argument("--require-local-evidence", action="store_true")
args_parser.add_argument("--git-checkout", action="store_true")
args = args_parser.parse_args()
manifest = load(ARCHIVE / "MANIFEST.json")
expected = {row["path"] for row in manifest["members"]}
assert len(expected) == len(manifest["members"])
actual = {p.relative_to(ARCHIVE).as_posix() for p in ARCHIVE.rglob("*") if p.is_file() and p.name != "MANIFEST.json" and "__pycache__" not in p.parts}
assert expected == actual, "Frozen member set changed"
for row in manifest["members"]:
    raw = confined(ARCHIVE, row["path"]).read_bytes()
    assert len(raw) == row["bytes"] and digest(raw) == row["sha256"], row["path"]
navigation = load(ARCHIVE / "NAVIGATION.json")
for ref in navigation["references"]:
    assert confined(REPO, ref).is_file(), ref
local = load(ARCHIVE / "LOCAL-EVIDENCE.json")
if args.require_local_evidence:
    for row in local["files"]:
        assert row["path"].startswith(".project-local/")
        raw = confined(REPO, row["path"]).read_bytes()
        assert digest(raw) == row["sha256"] and len(raw) == row["bytes"], row["path"]
git_count = 0
if args.git_checkout:
    # 只复制本次与已登记的冻结文本/回执，不复制运行时、浏览器profile、环境或整源码树。
    fixture = REPO / ".project-local/audits" / ("continuity-checkout-" + uuid.uuid4().hex)
    fixture.mkdir()
    names = {p.relative_to(REPO).as_posix() for p in ARCHIVE.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    old = load(ARCHIVE / "eol/FINAL-VERIFICATION.json")
    for record in old["frozen_readback"]:
        assert digest(confined(REPO, record["path"]).read_bytes()) == record["before_sha256"], record["path"]
        names.add(record["path"])
        for member in record["members"]:
            assert digest(confined(REPO, member["path"]).read_bytes()) == member["sha256"], member["path"]
            names.add(member["path"])
    names.add(".gitattributes")
    before = {}
    for ref in sorted(names):
        raw = confined(REPO, ref).read_bytes()
        before[ref] = digest(raw)
        target = long_path(fixture / ref)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    prefix = ["git", "-c", "core.longpaths=true", "-c", "core.safecrlf=false", "-c", "core.fsmonitor=false"]
    for command in (["init", "--quiet", "--template="], ["add", "--", ".gitattributes", "docs/history"],
                    ["checkout-index", "--all", "--force", "--prefix=" + (fixture / "owned-checkout").as_posix() + "/"]):
        child = subprocess.run(prefix + command, cwd=fixture, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert child.returncode == 0, "Isolated Git checkout failed: " + child.stderr
    for ref, sha in before.items():
        assert digest(long_path(fixture / "owned-checkout" / ref).read_bytes()) == sha, ref
    git_count = len(before)
print(json.dumps({"status": "PASS", "evidence_level": "STRUCTURAL_AND_GIT_BYTE_READBACK_NOT_PRODUCT_QUALIFICATION",
    "frozen_members": len(expected), "navigation_targets": len(navigation["references"]),
    "local_evidence_checked": len(local["files"]) if args.require_local_evidence else "NOT_EXECUTED",
    "git_checkout_files": git_count if args.git_checkout else "NOT_EXECUTED", "product_status": "PARTIAL"}, ensure_ascii=False, indent=2))
