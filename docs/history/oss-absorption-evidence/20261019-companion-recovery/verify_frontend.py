import datetime,json,os,pathlib,subprocess,sys,time
root=pathlib.Path.cwd(); out=pathlib.Path(os.environ['ARCHEAXIS_RUN_ROOT'])/'artifacts'
node=r'C:\Users\ALEX\.local\node-v24.21.0-win-x64\node.exe'
command=[node,str(root/'frontend/node_modules/vitest/vitest.mjs'),'run',*sys.argv[1:],'--maxWorkers=1','--minWorkers=1','--reporter=default','--reporter=json','--outputFile='+str(out/'vitest.json')]
start=datetime.datetime.now(datetime.timezone.utc).isoformat(); t=time.monotonic()
result=subprocess.run(command,cwd=root/'frontend')
(out/'test-command.json').write_text(json.dumps({'command':command,'started_at':start,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seconds':time.monotonic()-t,'exit_code':result.returncode},indent=2),encoding='utf-8')
raise SystemExit(result.returncode)
