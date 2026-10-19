"""保存本轮限定证据与接续导航；只写当前项目，不改历史归档。"""
from pathlib import Path
import hashlib,json,shutil,subprocess,datetime

ROOT=Path(__file__).resolve().parents[3]
RUNS=ROOT/'.project-local/runs/be268a2d33'
DEST=ROOT/'docs/history/oss-absorption-evidence/20261019-review-title'
DEST.mkdir(exist_ok=False)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def copy(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,dst)

files=['crates/archeaxis-domain/src/learning.rs','crates/archeaxis-api/src/lib.rs','packages/contracts/v1/core-document.schema.json','crates/archeaxis-api/tests/learning_state_api.rs','frontend/src/api/generated/core-contract.ts','frontend/src/presentation/learningTitle.ts','frontend/src/test/learningQueue.ts','frontend/src/spaces/CanonicalLearningSpace.tsx','frontend/src/spaces/CanonicalWorkspaceSpace.tsx','frontend/src/presentation/workspaceReview.ts','frontend/src/presentation/learningJourney.ts','frontend/src/spaces/CanonicalTeachingSpace.tsx','frontend/src/__tests__/CanonicalLearningDrafts.test.tsx','frontend/src/__tests__/CanonicalReviewLearning.test.tsx','frontend/src/__tests__/LearningPracticeJourney.test.tsx','frontend/src/__tests__/LiveRegionBudget.test.tsx','frontend/src/__tests__/ThreeLevelNavigation.test.tsx','frontend/src/__tests__/UiFirstWorkspace.test.tsx','frontend/src/__tests__/CoreBridge.test.ts','frontend/src/__tests__/LearningTitle.test.ts','scripts/probes/aaos01_grouped_owner_loop.py','scripts/probes/aaos01_tauri_webdriver_loop.py','tests/test_grouped_native_owner_probe.py','tests/test_tauri_shell_authority.py']
for f in files: copy(ROOT/f,DEST/'source'/f)
runs=['review-title-contract-red-1019','review-title-ui-red-1019','review-title-binding-red-1019','review-selection-echo-red-1019','review-title-core-final-1019','review-title-probes-green-1019','review-title-echo-full-1019','review-title-echo-final-1019','review-title-echo-build-1019','review-title-browser-1019','review-title-browser-final-1019','review-title-browser-echo-1019']
for name in runs:
    copy(RUNS/name/'artifacts/execution.json',DEST/'runs'/f'{name}.json')
    copy(RUNS/name/'logs/execution.log',DEST/'runs'/f'{name}.log')
pilot=RUNS/'review-title-browser-echo-1019/artifacts/ui-pilot'
for f in ['summary.json','checks.json','environment.json','axe-results.json','screenshots.json','preflight.json','owned-processes.json','browser-shutdown.json','shutdown.json']:
    copy(pilot/f,DEST/'browser'/f)
for f in ['prepare.py','fixture-base.js','fixture-title.js','audit.spec.cjs','launch.cjs','playwright.config.cjs','run.py','archive.py']:
    copy(Path(__file__).parent/f,DEST/'harness'/f)
copy(RUNS/'056543a77b63/artifacts/frontend-build.json',DEST/'frontend-build.json')
shots=[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':sha(p),'visually_reviewed':True} for p in pilot.glob('*.png')]
write(DEST/'screenshots.json',shots)
nav=json.loads((ROOT/'docs/current/AAOS-ACTIVE-EXECUTION.json').read_text(encoding='utf-8'))['continuation_context']
paths=set(nav['read_order'])|set(nav['resource_navigation'].values())
paths|={'docs/CONFIGURATION_AUTHORITY_INDEX.md','docs/current/AAOS-PROJECT-CLOSURE-20261018.md','docs/current/AAOS-XIAOQI-MIGRATION-20261018.md','docs/current/AAOS-AUDIT-TEST-COVERAGE-20261018.md'}
assert all((ROOT/f).is_file() for f in paths)
write(DEST/'navigation-snapshot.json',{'role':'DATED_NAVIGATION_ONLY','paths':{f:sha(ROOT/f) for f in sorted(paths)}})
coverage={
 '权威与唯一进度':['AUTHORITY.md','docs/current/AAOS-ACTIVE-EXECUTION.json','docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md'],
 '原件与历史交接':['AAOS-资料索引.md','docs/current/AAOS-PROJECT-CLOSURE-20261018.md','docs/current/AAOS-AUTHORITY-ROUTES.json'],
 'Codex与Claude与Cowork':['docs/current/AAOS-SESSION-RECONCILIATION-20261018.md','docs/current/AAOS-CODEX-SESSION-INDEX-20261018.md'],
 '共享路径与工具':['docs/SHARED_RESOURCE_PATH_INDEX.md','config/environment/capability-requirements.yaml','config/environment/external-resources-index.json'],
 'LM Studio与模型分层':['docs/current/AAOS-LOCAL-LLM-20261018.md','docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md'],
 '小栖并入与源库保全':['workspace/intake/20261018-xiaoqi-in-project.md','docs/current/AAOS-XIAOQI-MIGRATION-20261018.md'],
 '开源图谱与OpenMAIC与许可择优':['docs/current/AAOS-OSS-UI-DONORS-20261019.md','docs/current/AAOS-OPENMAIC-ABSORPTION-20261019.md','docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md'],
 '强底座与能力中心与插件技能MCP':['docs/current/AAOS-OSS-INTEGRATION-DECISION-20261019.md'],
 '审计边界与工程诊断归类':['docs/current/AAOS-AUDIT-TEST-COVERAGE-20261018.md','docs/current/receipts/AAOS-DIAGNOSTIC-CENTER-20261018.json'],
}
assert all((ROOT/f).is_file() for group in coverage.values() for f in group)
write(DEST/'decision-coverage.json',{'role':'NAVIGATION_NOT_SECOND_AUTHORITY','coverage':coverage,'private_complete_transcripts':'UNVERIFIED','cloud_backup':'NOT_EXECUTED','source_deletion':'NOT_AUTHORIZED_BY_ARCHIVE'})
receipt={
 'schema':'aaos.review-title-evidence/v1','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PARTIAL','implementation':'APPLIED','archive':str(DEST.relative_to(ROOT)).replace('\\','/'),
 'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_files':{f:sha(ROOT/f) for f in files},
 'qualifications':{'frontend':'176 files / 1741 tests PASS; React/jsdom, SYNTHETIC Core','core':'14 Rust API/course tests PASS; isolated SQLite/CAS and synthetic records','probes':'80 Python tests + 145 subtests PASS; selector contract checks','build':'TypeScript / Vite PASS; 056543a77b63','browser':'real Chrome production bundle, SYNTHETIC Core, 3 checks PASS, 3 screenshots reviewed','axe':'queue scope: zero violations, one incomplete color-contrast rule; not full compliance','native_for_this_patch':'NOT_EXECUTED','installed':'NOT_EXECUTED'},
 'source_binding':'Each execution receipt retains its own exact patch. Core/probe files unchanged after their tests; later React selection fix and test-only restore fixture repair do not grant a universal all-repo patch qualification.',
 'remaining':[{'severity':'P2','location':'1280px desktop review queue','observed':'80-scalar long button text clipped horizontally in screenshot 01; 640px wraps','next':'bounded wrapping for review buttons at desktop and narrow widths, measure both viewports'},{'severity':'UNVERIFIED','location':'review queue contrast','observed':'axe color-contrast incomplete due overlap/pseudo background','next':'manual contrast verification with rendered background'},{'severity':'NOT_EXECUTED','location':'native candidate','observed':'prior qualified candidate does not include title/selection changes','next':'build and qualify owned isolated candidate before claiming native pass'}],
 'preserved_failures':runs[:4]+['review-title-echo-full-1019','review-title-browser-1019'],
 'test_fixture_correction':'restore_epoch must be initial or 32 hex characters; invalid restored fixture replaced, then full suite PASS',
 'no_commit_push_cloud_release':True,'complete_private_transcripts':'UNVERIFIED','whole_project':'PARTIAL',
 'screenshots':shots,'navigation_targets_verified':len(paths),
}
write(DEST/'RECEIPT.json',receipt)
write(ROOT/'docs/current/receipts/AAOS-REVIEW-TITLE-20261019.json',receipt)
(DEST/'README.md').write_text('''# 复习标题、选择消重与接续归档（2026-10-19）

状态 PARTIAL；产品提案已应用。Core 从固定 assessment/课程绑定投影可读标题，校验课程、组件、知识版本、来源及 anchor；不改变持久化 key、排序或到期时间。前端兼容旧 Core；同名标题按稳定 key 操作。主壳选中项回传不再重复读同一项目，工作区／恢复 epoch／确认恢复变更仍重新读取。

`RECEIPT.json`记录限定资格和未完成项，`runs/`保存实际命令、UTC时间、退出码、源码绑定和原始日志。24个源码快照用于追溯，不是运行入口。`harness/`保存独立浏览器脚本；仅静态产物＋合成Core，1浏览器/1worker，不连接真实数据。PNG与trace留项目 `.project-local/`，截图哈希和实看记录见screenshots.json。没有创建或更新视觉基准。浏览器功能3项通过不代表整个页面视觉通过：桌面长标题仍裁切；axe对比度有一项incomplete。旧失败保留，没有为了全绿降低最终标准。

`decision-coverage.json`把可见对话决定收敛到既有权威／共享库／模型／迁移／审计／开源决定，不另建权威、资源配置或进度库。`navigation-snapshot.json`是本次观察；未来接手必须重新读取活动指针与manifest。完整私人客户端逐字正文未补齐，云端同步未执行。

前序continuation-checkpoint中的提案仍保留当时NOT_EXECUTED事实；本快照证明后来已应用。原生材料/陪伴资格仍属于其旧候选，不自动覆盖本次源码。后续先修复桌面裁切并测1280/640，再对自有候选进行原生验证；其余任务沿唯一UI执行记录推进。未提交、推送、发布、改全局配置或删除源库。
''',encoding='utf-8')
members={str(p.relative_to(DEST)).replace('\\','/'):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file()}
write(DEST/'MANIFEST.json',{'schema':'aaos.archive-members/v1','members':members})
assert all(sha(DEST/f)==digest for f,digest in members.items())
print(json.dumps({'archive':str(DEST),'members_verified':len(members),'navigation_targets':len(paths),'status':'PARTIAL'},ensure_ascii=False))
