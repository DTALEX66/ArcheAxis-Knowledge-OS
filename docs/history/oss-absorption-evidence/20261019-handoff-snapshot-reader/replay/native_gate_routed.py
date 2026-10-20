"""正式native测试使用当前源码真实前端构建及受控Core，不绕过Tauri构建路由。"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
NODE="C:/Users/ALEX/.local/node-v24.21.0-win-x64/node.exe"
summary=OUT/"native-routed-checks.json"
assert not summary.exists()
records=[]
def run(name,args,env=None):
    start=datetime.now(timezone.utc).isoformat()
    p=subprocess.run(args,cwd=ROOT,env=env,capture_output=True)
    log=OUT/("native-routed-"+name+".log")
    assert not log.exists();log.write_bytes(p.stdout+b"\n"+p.stderr)
    records.append(dict(name=name,command=args,started_at=start,ended_at=datetime.now(timezone.utc).isoformat(),exit_code=p.returncode,log=log.relative_to(ROOT).as_posix(),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
    summary.write_text(json.dumps(records,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(name+" exit="+str(p.returncode),flush=True)
    if p.returncode:
        print((p.stdout+p.stderr).decode("utf-8","replace")[-6000:]);raise SystemExit(p.returncode)

receipt=Path(os.environ["ARCHEAXIS_RUN_ROOT"])/"artifacts/frontend-for-native.json"
run("current-frontend-build",[NODE,"scripts/runtime/frontend.mjs","build","--receipt",str(receipt)])
build=json.loads(receipt.read_text(encoding="utf-8"))
assert build["exit_code"]==0 and build["source_consistent"] is True
assert build["source_patch_sha256"]==os.environ["ARCHEAXIS_SOURCE_PATCH_SHA256"]
dist=Path(build["frontend_dist"]);overlay=Path(build["tauri_config"])
dist.resolve().relative_to((ROOT/".project-local").resolve())
assert (dist/"index.html").is_file() and overlay.is_file()
core=Path(os.environ["CARGO_TARGET_DIR"])/"debug/archeaxis-api.exe"
assert core.is_file()
env=dict(os.environ,BE10_PREVIEW_CORE=str(core.resolve()),ARCHEAXIS_FRONTEND_DIST=str(dist),TAURI_CONFIG=overlay.read_text(encoding="utf-8"),ARCHEAXIS_TAURI_CONFIG=str(overlay))
run("actual-preview-consumer",["cmd","/d","/c",r"scripts\ci\cargo_test.bat","test","--manifest-path",str(ROOT/"src-tauri/Cargo.toml"),"--offline","--locked","--test","project_handoff_preview","--","--test-threads=1"],env=env)
(OUT/"native-owned-binding.json").write_text(json.dumps(dict(core_path=core.relative_to(ROOT).as_posix(),core_sha256=hashlib.sha256(core.read_bytes()).hexdigest(),frontend_build_receipt=receipt.relative_to(ROOT).as_posix(),frontend_source_patch=build["source_patch_sha256"],scope="actual src-tauri Rust finite consumer calling freshly built owned Core; not UI launch/installer/cloud CI"),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
