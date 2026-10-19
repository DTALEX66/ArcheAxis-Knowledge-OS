"""冻结本轮源码/失败证据，刷新已有接手导航；不建立第二权威。"""
from pathlib import Path
from datetime import datetime, timezone
import difflib
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
REF = 'docs/history/oss-absorption-evidence/20261019-handoff-snapshot-reader'
ARC = ROOT / REF
RECEIPT = 'docs/current/receipts/AAOS-HANDOFF-SNAPSHOT-READER-20261019.json'
sha = lambda b: hashlib.sha256(b).hexdigest()
load = lambda p: json.loads(p.read_text(encoding='utf-8'))

def put(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode('utf-8'))

def dump(p, data):
    put(p, json.dumps(data, ensure_ascii=False, indent=2) + '\n')

def identity(p):
    raw = p.read_bytes()
    return dict(path=p.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=sha(raw))

assert not ARC.exists(), '不得覆盖旧冻结归档'
ARC.mkdir(parents=True)
navs = [
    'docs/current/AAOS-AGENT-HANDOFF-CURRENT.md',
    'docs/current/AAOS-ACTIVE-EXECUTION.json',
    'docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md',
    'docs/DOCUMENTATION_AUTHORITY_INDEX.md',
]
for ref in navs + ['.gitattributes']:
    p = OUT / 'navigation-before' / ref
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes((ROOT/ref).read_bytes())

# 只更新当前导航；原39项来源与旧快照均不回写。
p = ROOT/navs[0]
t = p.read_text(encoding='utf-8')
marker = '## 最新验证快照（2026-10-19，对话接续／BE10预览／PDF依赖与版本）'
assert marker in t
t = t.replace(marker, '''## 最新验证快照（2026-10-19，固定引用全文与接续归档）

[限定回执](receipts/AAOS-HANDOFF-SNAPSHOT-READER-20261019.json)、[源码／红绿测试／截图身份冻结](../history/oss-absorption-evidence/20261019-handoff-snapshot-reader/README.md)。原39主题及OD039本次归档原话保持原字节；权威／规划／路径／入口／外置共用库仍按上述规范源导航。独立只读复核39主题、28主题引用和47唯一路径均存在，不以此提升运行或完整会话资格。

BE10已新增本机human只读snapshot固定路由和现有page16显式阅读入口：同事务绑定workspace／restore epoch／ID／版本及原始editor JSON SHA，读取原冻结全文；CURRENT仅预览观察，读取时STALE保留旧版并明确提示。过期、恢复、关闭或停放窗口清除正文与迟到响应；全局诊断只保留身份。不会改成最新版、送入可编辑Library或导出Observer正文。元数据预览和全文读取是分别授权的用户动作，不授予执行／知识接纳。

实际90前端、26 Python、Core进程22＋共享合同2、native有限桥29项与TypeScript／生产前端构建通过；每组命令、时间、源码patch分别绑定，不相加称全量。浏览器真实页面源码＋隔离模拟桥，宽1280／窄390截图逐张实看，旧版提示、无横向溢出、Escape焦点返回、409错误及原交换页保留通过。axe无自动violation但6项incomplete，人工完整无障碍、性能、原生UI／安装／对端投递仍未验证；测试工具初轮失败保留。

''' + marker.replace('最新验证快照', '前轮验证快照'))
t = t.replace('BE10正文snapshot／固定引用原生界面／真实外部投递及OS URI、', 'BE10正文snapshot及page16本机human阅读已应用；固定引用原生界面／真实外部投递及OS URI、')
t = t.replace('本轮4份导航更新前原字节保存在', '本轮4份导航与.gitattributes更新前原字节保存在 `.project-local/audits/be10-snapshot-integration-20261019/navigation-before/`；前轮4份导航更新前原字节保存在')
put(p, t)

p = ROOT/navs[1]
d = load(p)
e = d['continuation_context']['evidence_navigation']
e['latest_archival_checkpoint'] = REF + '/README.md'
e['handoff_snapshot_reader_current'] = RECEIPT
e['handoff_snapshot_reader_checkpoint'] = REF + '/README.md'
dump(p, d)

p = ROOT/navs[3]
t = p.read_text(encoding='utf-8')
first = '# Documentation Authority Index\n'
assert t.startswith(first)
t = t.replace(first, first + '''
> 2026-10-19 后继限定增量：[固定引用全文／现有page16消费回执](current/receipts/AAOS-HANDOFF-SNAPSHOT-READER-20261019.json)、[本轮源码与失败证据归档](history/oss-absorption-evidence/20261019-handoff-snapshot-reader/README.md)。替代前轮“snapshot／UI未应用”的当前状态，旧快照保留原SHA；仍非原生UI、外部产品、安装或整个BE10通过。39项对话及规范路径继续沿原固定读序，不复制第二权威或资源默认值。
''', 1)
put(p, t)

p = ROOT/'docs/contracts/project-handoff-preview-v1.md'
t = p.read_text(encoding='utf-8')
t = t.replace('BE10原逻辑操作', '> 2026-10-19 后继：下文预览合同继续有效，“确切剩余接线”是前轮形成时的缺口。其第1—3项已由下方snapshot／page16切片实施，实际资格读[限定回执](../current/receipts/AAOS-HANDOFF-SNAPSHOT-READER-20261019.json)；第4项仍待独立授权与验证。\n\nBE10原逻辑操作', 1)
t += '''
## 后继snapshot及现有页面消费（2026-10-19）

`POST /api/v1/project-handoff/snapshot`和原native `core_command`中的`project_handoff_snapshot`为本机human只读固定端口；与preview使用同一严格context提案（无query、未知／重复字段拒绝、输入64KiB），不接受用户指定URL／路径／命令。Observer／machine不获正文。3秒有限桥、响应24MiB；原始editor JSON超过8MiB或序列化响应超限均拒绝，不截断为成功。

同一DEFERRED事务核对已有workspace身份、restore epoch和冻结document/version，先限原始JSON字节，再核对原始UTF8 SHA＝存储SHA＝提案引用SHA；不对重新序列化的对象做替代hash。只返回核对后的`editor_json`及有限身份/时间/状态，不混入未受此hash覆盖的当前title、source、blocks或text_projection。历史版本仍可读，`STALE`保留旧版且不回退最新版；缺失404、身份/hash/过期409、过大413、不可用503。请求排队、事务后和序列化后均复核有效期，重复读取无业务写入。

`archeaxis.project-handoff-snapshot/v1`严格DTO/Schema及14共同正负case，scope固定`LOCAL_HUMAN_READ_ONLY`，来源认证／选区仍`UNVERIFIED`，执行及知识接纳均false。前端类型和运行时校验由单一合同生成器产生，核对原提案fingerprint、producer/reference/期限及snapshot身份；JSON重复键（含转义键）和不安全数值拒绝。

现有page16显式“预览跨项目引用”→预览元数据→打开固定版本全文；保留原交换页、不导航可编辑Library。关闭、过期、workspace恢复、窗口停放或输入变化丢弃正文与迟到响应，Escape返回入口焦点；原始回执的诊断不保留editor_json。全文只在本机human阅读状态内，不将引用视为执行或接纳授权。

实际Core进程/排队回归及src-tauri有限桥调用自建Core属于真实工程接线、合成业务数据；真实页面浏览器采用隔离模拟桥。它们均不等于原生UI启动、已安装运行、OS URI注册、外部WORK-LAB／DESIGN-LAB真实返回链、完整无障碍或Owner验收。BE10仍PARTIAL。
'''
put(p, t)

p = ROOT/navs[2]
put(p, p.read_text(encoding='utf-8') + '''

### 2026-10-19 固定引用snapshot／page16消费与归档接续

[限定回执](receipts/AAOS-HANDOFF-SNAPSHOT-READER-20261019.json)、[本轮冻结源码与证据](../history/oss-absorption-evidence/20261019-handoff-snapshot-reader/README.md)。本机human固定snapshot与原page16阅读已应用，workspace／恢复epoch／冻结版本及原始JSON SHA同事务绑定，队列和序列化后重验期限，超限拒绝不截断。前端严格生成合同、显式预览再阅读全文、STALE保留旧版、关闭／到期／恢复／停放丢弃正文及迟到响应；独立复核发现诊断保留正文已修复并增加回归。原页面／草稿保留，无Library编辑／Observer正文／执行或接纳。

正式仓90项前端（5文件）、26项Python合同、Core进程22项及Rust合同2项（内部preview16／snapshot14共享case）、native有限桥29项与TypeScript／生产前端构建通过，各组patch和时间单列，未跑整仓全量。隔离浏览器采用实际SpaceView page16及模拟有限桥，宽窄截图已逐张查看；旧版文案、无横向溢出、Escape焦点返回、409无正文及原页面保留通过。axe自动violation0但6项incomplete，完整人工无障碍／性能UNVERIFIED。旧Core route404预期RED、格式操作导致源码变化失效、测试路径与浏览器入口／只读teaching_list白名单遗漏的初轮FAIL全部保存；修正工具路径及准确有限操作后复验，不删除失败或降低产品标准。

原39主题和OD039本次归档原话保持冻结，独立只读核对39主题／28规范引用／47唯一路径均存在；当前handoff、活动指针及文档索引已链接本次回执，旧snapshot未实施仅归原源码。68项继承资格state/value不变，只重绑生成客户端两处SHA。完整Cowork正文／云端备份UNVERIFIED，ASTRYN源仍NOT_READY_TO_DELETE。BE10原生UI／外部投递／OS URI、HUB004安装更新、模型质量和原完整AI链retest超时、全格式／安装／Owner验收仍按原合同推进，整体RUNNING_BY_OWNER/PARTIAL。本轮本地未提交，无共享配置／provider／endpoint修改、Green替换或来源删除。
''')

sources = '''crates/archeaxis-api/src/project_handoff_preview.rs
crates/archeaxis-api/src/lib.rs
crates/archeaxis-contracts/src/project_handoff_preview.rs
packages/contracts/v2/project-handoff-snapshot.schema.json
packages/contracts/v2/project-handoff-snapshot.cases.json
crates/archeaxis-api/tests/project_handoff_preview_process.rs
crates/archeaxis-api/tests/project_handoff_snapshot_queue.rs
src-tauri/src/core_bridge.rs
src-tauri/tests/project_handoff_preview.rs
packages/contracts/v1/core-command.schema.json
frontend/src/api/generated/core-contract.ts
docs/current/AAOS-RESOURCE-QUALIFICATION-20261010.json
frontend/src/api/generated/resource-catalog.ts
scripts/contracts/generate_project_handoff.py
frontend/src/api/generated/project-handoff.ts
frontend/src/api/projectHandoff.ts
frontend/src/api/core.ts
frontend/src/components/ProjectHandoffReader.tsx
frontend/src/components/DocumentSnapshot.tsx
frontend/src/spaces/SpaceView.tsx
frontend/src/__tests__/ProjectHandoffReader.test.tsx
frontend/src/__tests__/ProjectHandoffContract.test.ts
tests/contract/test_project_handoff_snapshot_contract.py'''.splitlines()
rows, delta, local = [], [], {}
for ref in sorted(sources):
    raw = (ROOT/ref).read_bytes()
    pre = OUT/'before'/ref
    old = pre.read_bytes() if pre.is_file() else b''
    dest = ARC/'source'/ref
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    rows.append(dict(path=ref, before_sha256=sha(old) if pre.is_file() else None, after_sha256=sha(raw), bytes=len(raw), frozen_source=dest.relative_to(ARC).as_posix()))
    delta.extend(difflib.unified_diff(old.decode('utf8').splitlines(keepends=True),raw.decode('utf8').splitlines(keepends=True),fromfile='a/'+ref,tofile='b/'+ref))
    if pre.is_file(): local[pre.relative_to(ROOT).as_posix()] = identity(pre)
dump(ARC/'SOURCE-IDENTITY.json', dict(status='APPLIED', files=rows, note='源码冻结仅适用于各组execution所列patch；文档后续导航不改变旧测试所属源码'))
put(ARC/'OWNED-DELTA.patch', ''.join(delta))

def copy_file(p, dest):
    assert p.is_file()
    raw = p.read_bytes()
    dst = ARC/dest
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(raw)
    local[p.relative_to(ROOT).as_posix()] = identity(p)

executions=[]
for p in sorted((ROOT/'.project-local/runs/be268a2d33').glob('be10-snapshot-*/artifacts/execution.json')):
    d=load(p)
    run=p.parent.parent.name
    copy_file(p,'executions/'+run+'.json')
    log=Path(d['log']);log.resolve().relative_to((ROOT/'.project-local').resolve())
    copy_file(log,'logs/'+run+'.log')
    executions.append(dict(run_id=run, exit_code=d['exit_code'], source_consistent=d['source_consistent'], source_patch_sha256=d['source_patch_sha256'], command=d['command'], started_at=d['started_at'], ended_at=d['ended_at']))
assert len(executions)==12
dump(ARC/'EXECUTIONS.json',executions)
for pattern in ['*-checks.json','*.log']:
    for p in OUT.glob(pattern):copy_file(p,'checks/'+p.name)
for name in ['source-rebind.json','baseline-red-process.json','native-owned-binding.json','process-readback.json','process-readback-first-self-match.json','recovered-preimage-provenance.json','gates.py','baseline_red.py','native_gate_routed.py','browser.mjs','browser-first-attempt.mjs','browser-second-attempt.mjs','browser-third-attempt.mjs','browser-results.json','archive.py']:
    copy_file(OUT/name,'replay/'+name)
for name in ['v3','v4']:
    copy_file(OUT/('browser-'+name)/'browser-results.json','browser/'+name+'-results.json')
for p in (OUT/'browser-v4/visual').glob('*'):
    if p.is_file():local[p.relative_to(ROOT).as_posix()] = identity(p)
for ref in navs+['.gitattributes']:
    copy_file(OUT/'navigation-before'/ref,'navigation-before/'+ref)
for ref in navs+['docs/contracts/project-handoff-preview-v1.md']:
    p=ARC/'navigation-at-observation'/ref
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/ref).read_bytes())
for relative in ['.project-local/audits/be10-snapshot-policy-20261019/continuity-readback.json','.project-local/audits/be10-snapshot-policy-20261019/static-review/REVIEW.md','.project-local/audits/be10-snapshot-policy-20261019/static-review/READBACK.json']:
    p=ROOT/relative
    if p.is_file():copy_file(p,'reviews/'+p.name)
build=ROOT/load(OUT/'native-owned-binding.json')['frontend_build_receipt']
copy_file(build,'checks/frontend-for-native.json')
dump(ARC/'LOCAL-EVIDENCE.json',dict(scope='项目内有限证据身份；不含私人会话、凭据、数据库、浏览器profile；PNG/trace只留忽略目录',files=sorted(local.values(),key=lambda x:x['path'])))

targets={ref for row in load(ROOT/'docs/history/owner-dialogue-20261019/decision-coverage.json')['records'] for ref in row['current_references']}
targets.update(navs+['AUTHORITY.md','AGENTS.md','docs/SHARED_RESOURCE_PATH_INDEX.md','config/environment/capability-requirements.yaml','config/environment/external-resources-index.json','docs/history/owner-dialogue-20261019/README.md','docs/history/owner-dialogue-20261019/decision-coverage.json','docs/history/oss-absorption-evidence/20261019-continuity-native-pdf/README.md','docs/contracts/project-handoff-preview-v1.md',RECEIPT])
dump(ARC/'NAVIGATION.json',dict(role='既有规范源导航；不建立另一套权威/共享默认值/进度',owner_topics=39,references=sorted(targets)))
put(ARC/'OWNER-REQUIREMENT.md','''# 本次原话与接续约定

> 这些对话和决定的内容一定要做好归档，避免换AGENT或者换会话又忘了，尤其不要像各类权威/路径/规划/入口/各类外置共用库等那样总是忘记了

此为原39主题中OD039的再次确认，原件保持冻结；先沿AUTHORITY→AGENTS→活动指针→现行决定→固定handoff→唯一UI进度读回。来源/旧路径、会话登记、共享根、模型、工具使用各自规范索引及manifest，现场核对版本/hash/进程，不从旧摘要、文件名CURRENT或私人记忆推导事实。

强底座／最短闭环／多格式保持核心，扩展通过模板、插件、技能、MCP等适配与能力中心按需呈现；模型治理属于底座，具体runtime/provider可替换，当前本地通道LM Studio，无Ollama或云端自动回退。原决定和任务范围见NAVIGATION中的现行决定，不在此复制第二规划。

本轮实际新状态：BE10本机human snapshot与原page16固定引用阅读已应用，替代前轮该切片未实施的当前结论。旧元数据preview、旧NOT_APPLIED/FAIL及各自源码原字节均保留；native有限consumer测试不等于原生UI或外部产品/OS URI/安装。实际状态只写唯一UI记录。

新决定应补来源、日期、适用范围、替代关系、规范入口和验证边界；路径移动/退役先保留原身份、替代路径及完整性/回退。未完成迁移的ASTRYN源不删除；完整Cowork正文及云端备份UNVERIFIED。本地归档不意味着新权限、私人会话齐备、提交/推送、云备份或产品完成。
''')
browser=load(OUT/'browser-v4/browser-results.json')
results=dict(
    overall='PARTIAL', public_delivery='UNCOMMITTED_LOCAL_ONLY', owner_topics=39,
    product_scope='BE10 LOCAL_HUMAN_READ_ONLY fixed snapshot and existing page16 reader',
    applied_source_paths=len(rows),
    passes=dict(frontend=dict(files=5,tests=90),python_contracts=26,api_process_tests=22,rust_contract_tests=2,shared_cases=dict(preview=16,snapshot=14),native_finite_consumer_tests=29,typescript=True,production_frontend_build=True,generation_and_authority=True),
    browser=dict(status=browser['status'],evidence_level='SYNTHETIC actual product page source with finite mocked bridge',browser_version=browser['browser_version'],viewports=['1280x900','390x844'],dpr=1,theme='cosmic',reduced_motion='reduce',screenshots_viewed=['wide.png','narrow.png','identity-error.png'],visual_observation='正文和中文状态可读，宽窄无横向溢出；长正文在对话框内滚动，关闭按钮可能在折叠下方，Escape已验证返回入口；不据此认定完整可用性/无障碍',automatic_violations=0,automatic_incomplete=len(browser['incomplete']),full_accessibility='UNVERIFIED',performance='UNVERIFIED'),
    failures_preserved=['old owned Core snapshot route 404 EXPECTED_RED','format mutations outer exit3 source_consistent=false not PASS','frontend initial Windows fixture URL error exit1','browser CJS/ESM entry import failures exit1','browser initial operation whitelist omitted existing read-only teaching_list exit1; source inspected, exact read-only operation added, no write wildcard'],
    unchanged_qualification=dict(inherited_entries=68,promotions=0,source_sha_references_refreshed=2),
    process_cleanup=dict(owned_browser_port_5173='CLOSED',owned_browser_and_core_processes='NONE_AT_READBACK',native_ephemeral_port='UNVERIFIED_NOT_EXPORTED_BY_FIXTURE',first_inspection_shell_self_match='PRESERVED_THEN_FILTERED_BY_EXECUTABLE_NAME_NO_PROCESS_TERMINATED'),
    not_executed=['whole repository full suite','native UI launch for current snapshot reader','OS URI registration / real external WORK-LAB or DESIGN-LAB handoff','installed runtime / Owner acceptance','model quality/performance and original full AI retest timeout repair','HUB004 installation/update and all-format qualification'],
    continuity=dict(original39='FROZEN_UNCHANGED',private_Cowork_full_transcript='UNVERIFIED',cloud_backup='UNVERIFIED',ASTRYN_source='NOT_READY_TO_DELETE',whole_product='PARTIAL'),
    source_binding_note='每组execution保留各自patch；最终frontend/native/browser为2064eb2e1f87ffbb2b535e5ae73acc9f514cd5a7a4c3b7163766c3ae6bb72bef，不将较早Rust/Python验证宣称为最终全仓测试',
)
dump(ARC/'RESULTS.json',results)
put(ARC/'README.md','''# 2026-10-19 固定引用全文与现有page16阅读归档

**PARTIAL／本地未提交**。本目录冻结本轮23路径源码、各次执行/失败及接续导航；现行权威、决定、规划、路径、外置共用库和实际进度仍从[固定接手入口](../../../current/AAOS-AGENT-HANDOFF-CURRENT.md)沿已有规范源读取。

- [本次原话与替代关系](OWNER-REQUIREMENT.md)、[原39主题来源](../../owner-dialogue-20261019/README.md)、[规范导航](NAVIGATION.json)。不复制第二权威／进度／共享默认值；完整私人会话与云同步未获证据。
- [实际结果与未验边界](RESULTS.json)、[23路径身份](SOURCE-IDENTITY.json)、[差异](OWNED-DELTA.patch)、[命令/时间/退出码/源码patch](EXECUTIONS.json)。保留预期RED、初轮FAIL及后继通过，不相加成全量或产品验收。
- browser/保存真实页面源码＋模拟桥结果；PNG及trace只按[本地证据身份](LOCAL-EVIDENCE.json)核对。三图已实际查看，axe的6个incomplete不能冒充完整合规。native有限桥实际调用自建Core，仍非原生UI、对端或已安装运行。
- navigation-before/保留旧导航，navigation-at-observation/仅为当时快照；current文件可继续更新。旧39主题、前轮134成员及失败原件均不回写。

根目录运行 `.venv/Scripts/python.exe -X utf8 -B docs/history/oss-absorption-evidence/20261019-handoff-snapshot-reader/verify_snapshot.py --require-local-evidence --git-checkout`。验证冻结成员／引用／隔离Git原字节，不授予产品、发布、来源删除或共享配置修改权限。
''')

# 复用经过执行的只读校验器，保持旧快照独立可验。
old=ROOT/'docs/history/oss-absorption-evidence/20261019-continuity-native-pdf/verify_snapshot.py'
verifier=old.read_text(encoding='utf8').replace('continuity-pdf-checkout-','snapshot-reader-checkout-')
put(ARC/'verify_snapshot.py',verifier)
attrs=ROOT/'.gitattributes'
raw=attrs.read_bytes();rule=(REF+'/** -text\n').encode()
assert rule not in raw
attrs.write_bytes(raw+rule)
members=[]
for p in sorted(ARC.rglob('*')):
    if p.is_file():
        b=p.read_bytes();members.append(dict(path=p.relative_to(ARC).as_posix(),bytes=len(b),sha256=sha(b)))
dump(ARC/'MANIFEST.json',dict(schema='archeaxis.frozen-evidence/v1',created_at=datetime.now(timezone.utc).isoformat(),members=members))
dump(ROOT/RECEIPT,dict(schema='archeaxis.handoff-snapshot-reader-receipt/v1',observed_at=datetime.now(timezone.utc).isoformat(),overall='PARTIAL',archive=REF+'/README.md',manifest=identity(ARC/'MANIFEST.json'),frozen_members=len(members),source_paths=len(rows),owner_topics=39,fixed_handoff=navs[0],unique_progress=navs[2],results=REF+'/RESULTS.json',public_delivery='UNCOMMITTED_LOCAL_ONLY',archival_validation='PENDING_READBACK',actual_checks=results['passes'],browser=results['browser'],not_executed=results['not_executed']))
print(json.dumps(dict(status='ARCHIVE_CREATED_PENDING_READBACK',members=len(members),sources=len(rows),manifest=sha((ARC/'MANIFEST.json').read_bytes())),ensure_ascii=False))
