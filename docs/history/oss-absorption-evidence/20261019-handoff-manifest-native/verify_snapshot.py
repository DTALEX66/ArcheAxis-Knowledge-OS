"""只读核对冻结成员和现行导航；本地证据可选，结构不替代产品验收。"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
REF = 'docs/history/oss-absorption-evidence/20261019-handoff-manifest-native'

def confined(base, name):
    pure = PurePosixPath(name)
    if pure.is_absolute() or '..' in pure.parts or ':' in name or '\\' in name:
        raise ValueError('不安全的引用：' + name)
    p = base.joinpath(*pure.parts)
    for item in (p, *p.parents):
        if item == base:
            break
        if item.exists() and (item.is_symlink() or getattr(item.lstat(), 'st_file_attributes', 0)
                              & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)):
            raise ValueError('引用包含重解析点：' + name)
    p.resolve().relative_to(base.resolve())
    return p

def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def check(p, item):
    data = p.read_bytes()
    assert len(data) == item['bytes'], str(p)
    assert hashlib.sha256(data).hexdigest() == item['sha256'], str(p)

def verify(local):
    members = load(BASE/'MANIFEST.json')['members']
    names = [m['path'] for m in members]
    actual = {p.relative_to(BASE).as_posix() for p in BASE.rglob('*')
              if p.is_file() and p.name != 'MANIFEST.json' and '__pycache__' not in p.parts}
    assert len(names) == len(set(names)) and set(names) == actual
    for item in members:
        check(confined(BASE, item['path']), item)
    context = load(BASE/'NAVIGATION-OBSERVATION.json')
    assert context['source_records'] == 39
    for item in context['references']:
        assert confined(ROOT,item['path']).is_file()
    active = load(ROOT/'docs/current/AAOS-ACTIVE-EXECUTION.json')
    assert active['active_progress'] == 'docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md'
    assert active['continuation_context']['evidence_navigation']['handoff_manifest_native_checkpoint'] == REF+'/README.md'
    assert '20261019-handoff-manifest-native/README.md' in (ROOT/'docs/current/AAOS-AGENT-HANDOFF-CURRENT.md').read_text(encoding='utf-8-sig')
    checked = 0
    if local:
        for item in load(BASE/'EXECUTION-READBACK.json')['runs']:
            check(confined(ROOT,item['execution_receipt']),item['execution_identity'])
            check(confined(ROOT,item['log']),item['log_identity'])
            checked += 1
        for item in load(BASE/'native/VISUAL-READBACK.json')['screenshots']:
            check(confined(ROOT,item['path']),{k:item[k] for k in ['bytes','sha256']})
        native = load(BASE/'native/receipt.json')
        assert native['ok'] is False and native['owned_ports_released'] is True
        assert native['source_consistent'] is True

    return dict(status='PASS', evidence_level='STRUCTURAL_READBACK_NOT_PRODUCT_QUALIFICATION',
                frozen_members=len(members), source_records=39, navigation_targets=len(context['references']),
                local_executions_checked=checked, local_evidence='PASS' if local else 'NOT_EXECUTED', product_status='PARTIAL')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-local-evidence', action='store_true')
    print(json.dumps(verify(parser.parse_args().require_local_evidence),ensure_ascii=False,indent=2))
