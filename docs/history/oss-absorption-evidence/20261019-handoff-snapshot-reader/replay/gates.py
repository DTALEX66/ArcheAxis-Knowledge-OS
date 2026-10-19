from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
NODE='C:/Users/ALEX/.local/node-v24.21.0-win-x64/node.exe'
mode=sys.argv[1]
records=[]
def run(name,args,cwd=ROOT):
    log=OUT/(mode+'-'+name+'.log');assert not log.exists()
    start=datetime.now(timezone.utc).isoformat();p=subprocess.run(args,cwd=cwd,capture_output=True)
    log.write_bytes(p.stdout+b'\n'+p.stderr)
    records.append(dict(name=name,command=list(map(str,args)),cwd=str(cwd),started_at=start,ended_at=datetime.now(timezone.utc).isoformat(),exit_code=p.returncode,log=log.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
    (OUT/(mode+'-checks.json')).write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'{name}: exit{p.returncode}',flush=True)
    if p.returncode: print((p.stdout+p.stderr).decode('utf-8','replace')[-6500:]);raise SystemExit(p.returncode)
cargo=['cmd','/d','/c',r'scripts\ci\cargo_test.bat']
if mode=='rust':
    run('workspace-format',cargo+['fmt','--all','--','--check'])
    run('native-format',cargo+['fmt','--manifest-path','src-tauri/Cargo.toml','--all','--','--check'])
    run('contracts',cargo+['test','--offline','--locked','-p','archeaxis-contracts','project_handoff_preview::'])
    run('real-process-and-queue',cargo+['test','--offline','--locked','-p','archeaxis-api','--test','project_handoff_preview_process','--test','project_handoff_snapshot_queue','--test','project_observer_process','--test','project_handoff_process','--','--test-threads=1'])
elif mode.startswith('frontend'):
    run('typescript',[NODE,str(ROOT/'frontend/node_modules/typescript/bin/tsc'),'--noEmit'],ROOT/'frontend')
    run('affected-components',[NODE,str(ROOT/'frontend/node_modules/vitest/vitest.mjs'),'run','--maxWorkers=1','--minWorkers=1','src/__tests__/ProjectHandoffReader.test.tsx','src/__tests__/ProjectHandoffContract.test.ts','src/__tests__/CoreBridge.test.ts','src/__tests__/CanonicalExchangeSpace.test.tsx','src/__tests__/ExchangePinnedIntegration.test.tsx'],ROOT/'frontend')
elif mode=='sources':
    run('python-contracts',[sys.executable,'-X','utf8','-B','-m','pytest','-q','-p','no:cacheprovider','tests/contract/test_project_handoff_snapshot_contract.py','tests/contract/test_project_handoff_preview_contract.py','tests/contract/test_project_handoff_contract.py','tests/contract/test_resource_catalog_projection.py','tests/test_native_preview_ci.py'])
    run('changed-python-lint',[sys.executable,'-m','ruff','check','scripts/contracts/generate_project_handoff.py','tests/contract/test_project_handoff_snapshot_contract.py'])
    run('generated-handoff',[sys.executable,'-X','utf8','-B','scripts/contracts/generate_project_handoff.py','--check'])
    run('generated-catalog',[sys.executable,'-X','utf8','-B','scripts/contracts/generate_resource_catalog.py','--check'])
    run('details-generation',[sys.executable,'-X','utf8','-B','scripts/contracts/generate_capability_package_details.py','--check'])
    run('authority',[sys.executable,'-X','utf8','-B','scripts/ci/check_document_authority.py'])
else:raise SystemExit('unknown mode')
