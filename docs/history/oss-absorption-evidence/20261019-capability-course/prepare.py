import ast, hashlib, json, os, pathlib, subprocess, sys
ROOT=pathlib.Path.cwd().resolve()
OUT=pathlib.Path(os.environ['ARCHEAXIS_RUN_ROOT'])/'artifacts/ui-pilot'
OUT.mkdir(parents=True,exist_ok=False)
LAB=pathlib.Path(r'C:\Users\ALEX\.codex\tools\visual-tool-lab')
AUDIT=pathlib.Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((LAB/'INSTALL-MANIFEST.json').read_text(encoding='utf-8'))
assert sha(LAB/'package-lock.json')==manifest['packageLockSha256']
packages=[]
for p in manifest['installedNodePackages']:
 f=LAB/'node_modules'/p['name']/'package.json';actual=json.loads(f.read_text(encoding='utf-8'))
 assert actual['version']==p['version'] and sha(f)==p['installedPackageJsonSha256']
 packages.append({'name':p['name'],'version':actual['version'],'sha256':sha(f)})
build=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
assert build['exit_code']==0 and build['source_consistent']
dist=pathlib.Path(build['frontend_dist']).resolve();assert dist.is_relative_to(ROOT/'.project-local')
docs=['README.md','INSTALL-MANIFEST.md','CAPABILITY-MATRIX.md','BROWSER-USAGE.md','PROJECT-GUIDANCE.md','CURRENT-INSTALLATION.md','scripts/browser.mjs']
for name in docs:(LAB/name).read_text(encoding='utf-8')
pre={'lab':str(LAB),'packages':packages,'lock_sha256':sha(LAB/'package-lock.json'),'documents':{p:sha(LAB/p) for p in docs},'build':build,'bundle_members':{str(p.relative_to(dist)):sha(p) for p in dist.rglob('*') if p.is_file()},'scripts':{p.name:sha(p) for p in AUDIT.iterdir() if p.is_file()}}
(OUT/'preflight.json').write_text(json.dumps(pre,ensure_ascii=False,indent=2),encoding='utf-8')
v={}
for n in ast.parse((ROOT/'scripts/a0_browser_smoke.py').read_text(encoding='utf-8')).body:
 if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
  try:v[n.targets[0].id]=ast.literal_eval(n.value)
  except(ValueError,TypeError):pass
stub=v['HOST_BRIDGE_STUB_TEMPLATE']
for a,b in {'__A0_SOURCES__':json.dumps([v['A0_SOURCE']]),'__A0_DOCUMENTS__':'[]','__A0_FAULTS__':'{}','__A0_STATEFUL_DOCUMENTS__':v['A0_STATEFUL_DOCUMENTS'],'__A0_ORIGINAL__':json.dumps({'source_id':v['A0_SOURCE']['source_id'],'name':v['A0_SOURCE']['original_name'],'media_type':'text/plain','sha256':v['A0_SOURCE']['sha256'],'content_base64':v['A0_ORIGINAL_CONTENT']})}.items():stub=stub.replace(a,b)
stub+='\n'+(AUDIT/'fixture.js').read_text(encoding='utf-8')
(OUT/'fixture.js').write_text(stub,encoding='utf-8')
(OUT/'executed-scripts').mkdir()
for p in AUDIT.iterdir():
 if p.is_file():(OUT/'executed-scripts'/p.name).write_bytes(p.read_bytes())
print(json.dumps({'dependencies_verified':len(packages),'build':str(dist),'out':str(OUT)},ensure_ascii=False))
