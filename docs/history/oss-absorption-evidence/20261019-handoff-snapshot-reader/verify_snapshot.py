"""只读核对冻结载荷、规范导航及隔离Git原字节；不授予产品/运行资格。"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import stat
import subprocess
import uuid

ARCHIVE = Path(__file__).resolve().parent
REPO = ARCHIVE.parents[3]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
load = lambda p: json.loads(p.read_text(encoding="utf-8"))

def confined(base, ref):
    pure = PurePosixPath(ref)
    if pure.is_absolute() or ".." in pure.parts or ":" in ref or "\\" in ref:
        raise ValueError("unsafe reference")
    p = base.joinpath(*pure.parts)
    for q in (p, *p.parents):
        if q == base:
            break
        if q.exists() and (q.is_symlink() or getattr(q.lstat(), "st_file_attributes", 0) & getattr(stat,"FILE_ATTRIBUTE_REPARSE_POINT",0x400)):
            raise ValueError("linked reference rejected")
    p.resolve().relative_to(base.resolve())
    return p

def check(base, row):
    raw=confined(base,row["path"]).read_bytes()
    assert (len(raw),sha(raw)) == (row["bytes"],row["sha256"]),row["path"]

def long_path(p):
    return Path("\\\\?\\" + str(p.absolute())) if os.name == "nt" else p

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--require-local-evidence",action="store_true")
parser.add_argument("--git-checkout",action="store_true")
args=parser.parse_args()
entries=load(ARCHIVE/"MANIFEST.json")["members"]
names={r["path"] for r in entries}
actual={p.relative_to(ARCHIVE).as_posix() for p in ARCHIVE.rglob("*") if p.is_file() and p != ARCHIVE/"MANIFEST.json" and "__pycache__" not in p.parts}
assert len(names)==len(entries) and names==actual,"frozen member set changed"
for row in entries: check(ARCHIVE,row)
navigation=load(ARCHIVE/"NAVIGATION.json")
for ref in navigation["references"]: assert confined(REPO,ref).is_file(),ref
local=load(ARCHIVE/"LOCAL-EVIDENCE.json")["files"]
if args.require_local_evidence:
    for row in local:
        assert row["path"].startswith(".project-local/")
        check(REPO,row)
active=load(REPO/"docs/current/AAOS-ACTIVE-EXECUTION.json")
assert active["active_progress"] == "docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md"
assert active["continuation_context"]["resource_navigation"]["owner_dialogue_archive"]=="docs/history/owner-dialogue-20261019/README.md"
assert "../history/owner-dialogue-20261019/README.md" in (REPO/"docs/current/AAOS-AGENT-HANDOFF-CURRENT.md").read_text(encoding="utf-8")
git_count=0
if args.git_checkout:
    fixture=REPO/".project-local/audits"/("snapshot-reader-checkout-"+uuid.uuid4().hex)
    fixture.resolve().relative_to((REPO/".project-local/audits").resolve())
    fixture.mkdir()
    names={p.relative_to(REPO).as_posix() for p in ARCHIVE.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    # 同时核对原39主题冻结成员；旧大快照仍由原验证器按其原SHA独立验证。
    old=REPO/"docs/history/owner-dialogue-20261019"
    names.update({".gitattributes",(old/"MANIFEST.json").relative_to(REPO).as_posix()})
    for row in load(old/"MANIFEST.json")["members"]:
        check(old,row)
        names.add((old/row["path"]).relative_to(REPO).as_posix())
    expected={}
    for ref in sorted(names):
        raw=confined(REPO,ref).read_bytes();expected[ref]=sha(raw)
        p=long_path(fixture/ref);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    env={k:v for k,v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1",GIT_CONFIG_GLOBAL=os.devnull)
    prefix=["git","-c","core.longpaths=true","-c","core.safecrlf=false","-c","core.fsmonitor=false"]
    for args_git in (["init","--quiet","--template="],["add","--",".gitattributes","docs/history"],["checkout-index","--all","--force","--prefix="+(fixture/"owned-checkout").as_posix()+"/"]):
        child=subprocess.run(prefix+args_git,cwd=fixture,env=env,capture_output=True)
        assert child.returncode==0,"isolated Git roundtrip failed"
    for ref,digest in expected.items(): assert sha(long_path(fixture/"owned-checkout"/ref).read_bytes())==digest,ref
    git_count=len(expected)
print(json.dumps(dict(status="PASS",evidence_level="STRUCTURAL_HASH_AND_GIT_BYTES_NOT_PRODUCT_QUALIFICATION",frozen_members=len(entries),navigation_targets=len(navigation["references"]),local_evidence_checked=len(local) if args.require_local_evidence else "NOT_EXECUTED",git_roundtrip_files=git_count if args.git_checkout else "NOT_EXECUTED",whole_product="PARTIAL",private_full_transcript="UNVERIFIED"),ensure_ascii=False,indent=2))
