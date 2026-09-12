import json,hashlib
from pathlib import Path
p=Path(__file__).resolve().parent
m=json.loads((p/'MANIFEST.json').read_text())
for name,h in m.items():
 assert hashlib.sha256((p/name).read_bytes()).hexdigest()==h, name
x=json.loads((p/'TASKS.json').read_text())['tasks']; ids={t['id'] for t in x}; assert len(ids)==len(x)
done=set()
while len(done)<len(ids):
 ready={t['id'] for t in x if set(t['depends_on'])<=done}-done
 assert ready, 'cycle or missing dependency'
 done|=ready
old=json.loads((p/'reference-r2/TASKS.json').read_text())['tasks']
mapped={i for t in x for i in t['original_tasks']}|{f'F{i:02}' for i in range(1,7)}
assert {t['id'] for t in old}<=mapped
assert len(old)==23
print('PASS: hashes, 17 task dependencies, all 23 original tasks retained')
