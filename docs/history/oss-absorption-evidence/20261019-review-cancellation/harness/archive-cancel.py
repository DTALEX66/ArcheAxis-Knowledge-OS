"""本次限定证据快照。只复制显式项目文件，绝不扫描会话或浏览器资料。"""
from pathlib import Path
import json,hashlib,shutil,datetime,subprocess
ROOT=Path(__file__).resolve().parents[3]
RUNS=ROOT/'.project-local/runs/be268a2d33'
DEST=ROOT/'docs/history/oss-absorption-evidence/20261019-review-cancellation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def copy(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
def main():
 DEST.mkdir(exist_ok=False)
 files=['frontend/src/spaces/ui-first.css','frontend/src/api/conversation.ts','frontend/src/components/MaterialQuestionPanel.tsx','frontend/src/__tests__/ConversationPanel.test.tsx','frontend/src/__tests__/MaterialQuestionPanel.test.tsx','crates/archeaxis-api/tests/conversation_api.rs','scripts/probes/aaos01_material_companion_loop.py','scripts/probes/aaos01_grouped_owner_loop.py','scripts/probes/aaos01_tauri_webdriver_loop.py','tests/test_material_companion_native_probe.py']
 for f in files:copy(ROOT/f,DEST/'source'/f)
 runs=['review-wrap-browser-red-1019','review-wrap-contracts-1019','review-wrap-build-1019','review-wrap-browser-green-1019','conversation-identity-red-1019','conversation-identity-green-1019','material-cancel-ack-red-1019','conversation-cancel-final-ui-1019','conversation-cancel-core-1019','conversation-cancel-probes-1019','review-cancel-probes-frozen-1019','review-cancel-frontend-full-1019','review-cancel-model-load-1019','review-cancel-core-frozen-build-1019','review-cancel-host-frozen-build-1019','review-cancel-native-1019','review-cancel-navigation-probes-1019','review-cancel-navigation-core-1019','review-cancel-navigation-host-1019','review-cancel-native-navigation-1019','review-cancel-document-guard-probes-1019']
 for name in runs:
  for folder,fn in [('artifacts','execution.json'),('logs','execution.log')]:
   src=RUNS/name/folder/fn;copy(src,DEST/'runs'/(name+('.json' if folder=='artifacts' else '.log')))
 pilot=RUNS/'review-wrap-browser-green-1019/artifacts/ui-pilot'
 for f in ['summary.json','environment.json','axe-results.json','desktop-bounds.json','browser-shutdown.json','shutdown.json']:
  copy(pilot/f,DEST/'browser'/f)
 for f in ['prepare.py','audit.spec.cjs','run.py','archive-cancel.py']:
  copy(Path(__file__).parent/f,DEST/'harness'/f)
 copy(RUNS/'closure-native-stage/candidate-build-current-20261018T193831Z.json',DEST/'candidate-build-before-navigation.json')
 copy(RUNS/'closure-native-stage/candidate-build-current-20261018T194829Z.json',DEST/'candidate-build.json')
 copy(ROOT/'.project-local/runs/lm-studio-profile/1792352221528-load.json',DEST/'model-load-readback.json')
 nav=json.loads((ROOT/'docs/current/AAOS-ACTIVE-EXECUTION.json').read_text(encoding='utf-8'))['continuation_context']
 paths=set(nav['read_order'])|set(nav['resource_navigation'].values())|set(nav['evidence_navigation'].values())
 assert all((ROOT/f).is_file() for f in paths)
 write(DEST/'navigation-snapshot.json',{'role':'DATED_NAVIGATION_ONLY','paths':{f:sha(ROOT/f) for f in sorted(paths)}})
 copy(ROOT/'docs/history/oss-absorption-evidence/20261019-review-title/decision-coverage.json',DEST/'decision-coverage.json')
 copy(Path(__file__).parent/'handoff-before-review-cancel.md',DEST/'handoff-before-update.md')
 for f in ['aaos01_material_companion_loop.py','aaos01_grouped_owner_loop.py','aaos01_tauri_webdriver_loop.py']:
  copy(Path(__file__).parent/'native-before-navigation-fix'/f,DEST/'failed-native-probe-source'/f)
 shots=[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'visually_reviewed':True} for p in pilot.glob('*.png')]
 write(DEST/'browser-screenshots.json',shots)
 write(DEST/'source-identities.json',{f:sha(ROOT/f) for f in files})
 print(json.dumps({'archive':str(DEST),'run_count':len(runs),'source_count':len(files),'navigation_count':len(paths)},ensure_ascii=False))
if __name__=='__main__':main()
