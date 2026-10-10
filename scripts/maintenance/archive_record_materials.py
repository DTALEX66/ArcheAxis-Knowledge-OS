"""Local, lossless Record intake. Source documents never grant execution authority.

archive copies reviewed project/shared material; find and verify are read-only.
Only stdlib is needed. No deletion, upload, extraction of recovery data, or staging.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_ROOT = Path(subprocess.check_output(
    ["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"],
    text=True).strip()).parent
REVIEWED_SOURCE = CANONICAL_ROOT.parent / "Record"
MANIFEST_REL = Path('docs/history/record-archive-20261009/MANIFEST.json')
ARCHIVE_REL = Path('.project-local/archives/record-20261009')
SHARED = {
    '01_汇总报告.html', '01_审计报告与三项目融入建议.md',
    '03_价格与额度工作簿.xlsx', '05_附件完整性与工作簿审计.json',
    '总览.html', '汇总报告.md',
    '三项目_AI生态全生命周期收敛实施清单_2026-10-01.json',
    '三项目_AI生态全生命周期收敛最终方案_2026-10-01.html',
    '三项目_VI_UI_UX_作品集完整交付包.zip',
}
GENERIC_AAOS = {
    'AUDIT-REPORT.md', 'CI-JOBS.csv', 'deep-research-report.md',
    'DSH_纠偏接管指令_20261005.txt', 'R5-TASK-RECONCILIATION.csv', 'TaskPack.md',
}
PORTFOLIO = 'DT_ALEX_STUDIOS_10_CASE_PORTFOLIO_COMPLETE_20261007 (1)'
PROTECTED_NAME = re.compile(
    r'(^|/)(\.env(?:\..*)?|\.codex|\.hermes|sessions?|credentials?|'
    r'id_rsa|id_ed25519|cookies?)(/|$)', re.I)


def now():
    return datetime.now(timezone.utc).isoformat()


def safe(path: Path) -> Path:
    raw = str(path)
    if re.match(r'^[EF]:[\\/]', raw, re.I) or raw.startswith('\\\\'):
        raise ValueError('protected or UNC path')
    path = Path(os.path.abspath(path))
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError(f'reparse path rejected: {part}')
    return path


def bounded(root: Path, rel: str | Path) -> Path:
    rel = Path(rel)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('non-relative archive entry')
    path = safe(root / rel)
    if not path.is_relative_to(safe(root)):
        raise ValueError('archive entry escaped root')
    return path


def digest(path):
    h = hashlib.sha256()
    with safe(path).open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inventory(source):
    rows = []
    def visit(directory):
        for p in sorted(directory.iterdir(), key=lambda p: p.name.casefold()):
            safe(p)
            if p.is_dir():
                visit(p)
            elif p.is_file():
                info = p.stat()
                rows.append({'relative_path': p.relative_to(source).as_posix(),
                             'bytes': info.st_size, 'mtime_ns': info.st_mtime_ns})
    visit(safe(source))
    return rows


def classify(rel):
    parts = PurePosixPath(rel).parts
    name = parts[-1]
    if PROTECTED_NAME.search(rel):
        return None, 'PROTECTED_PRIVATE_STATE'
    if parts[0] == 'AAOS-project-archives':
        return 'AAOS_RECOVERY_OR_HISTORICAL_ARTIFACT', '项目恢复与历史证据；只保全，不解包运行'
    if parts[0] == PORTFOLIO:
        return 'SHARED_PORTFOLIO_REFERENCE', '含 AAOS 的完整共享作品集；保留资源依赖，非执行权威'
    if parts[0] == 'system-software-audit':
        if name in {'aaos-tree-size-scan.json', 'scan-aaos-tree-sizes.ps1'}:
            return 'AAOS_STORAGE_AUDIT_HISTORY', '指定 AAOS 体积审计资料；不执行脚本'
        return None, '非本项目系统审计材料；未读取内容'
    if len(parts) != 1:
        return None, '未识别为本项目资料'
    if re.search(r'aaos|archeaxis', name, re.I) or name in GENERIC_AAOS:
        return 'AAOS_SOURCE_INPUT_HISTORY', '本项目来源、方案、任务包或历史审计；不自动成为当前任务'
    if name in SHARED or name.startswith('Three_Project_Logos_'):
        return 'SHARED_TRI_PROJECT_REFERENCE', '包含 AAOS 的三项目共享资料；不合并其他项目执行边界'
    return None, 'WORK-LAB / DESIGN-LAB 专属或非本项目资料；保留在 Record'


def copy_verified(src, dst):
    before = src.stat()
    dst.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    if dst.exists():
        sha = digest(src)
        if digest(dst) != sha:
            raise ValueError(f'existing archive differs; no overwrite: {dst}')
    else:
        with src.open('rb') as a, dst.open('xb') as b:
            for chunk in iter(lambda: a.read(4 * 1024 * 1024), b''):
                h.update(chunk)
                b.write(chunk)
            b.flush()
            os.fsync(b.fileno())
        sha = h.hexdigest()
        shutil.copystat(src, dst)
    after = src.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
            after.st_size, after.st_mtime_ns, after.st_ino):
        raise RuntimeError(f'INVALIDATED source changed: {src}')
    if dst.stat().st_size != before.st_size or digest(dst) != sha:
        raise RuntimeError(f'archive readback failed: {dst}')
    return sha


def member_name(info):
    """Handle legacy UTF-8 names lacking the ZIP UTF-8 flag, without rewriting ZIP."""
    if not info.flag_bits & 0x800:
        try:
            return info.filename.encode('cp437').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return info.filename


def inspect_public_zip(path):
    """Stream CRC/SHA checks of bounded public task packs, never run embedded code."""
    try:
        with zipfile.ZipFile(path) as z:
            infos = [i for i in z.infolist() if not i.is_dir()]
            if sum(i.file_size for i in infos) > 1024 ** 3:
                return {'status': 'NOT_RUN_EXPANSION_LIMIT'}
            members = []
            for i in infos:
                name = member_name(i).replace('\\', '/')
                if '..' in PurePosixPath(name).parts or name.startswith('/') or ':' in name:
                    return {'status': 'UNSAFE_MEMBER_NAME'}
                if PROTECTED_NAME.search(name):
                    return {'status': 'NOT_RUN_PROTECTED_MEMBER'}
                h = hashlib.sha256()
                with z.open(i) as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b''):
                        h.update(chunk)
                members.append({'path': name, 'zip_header_name': i.filename, 'bytes': i.file_size,
                                'sha256': h.hexdigest(), 'crc32': f'{i.CRC:08x}'})
            by_name = {m['path']: m for m in members}
            declared = []
            for i in infos:
                if i.filename.endswith('/SHA256SUMS.txt') or i.filename == 'SHA256SUMS.txt':
                    base = i.filename.rsplit('/', 1)[0] + '/' if '/' in i.filename else ''
                    for line in z.read(i).decode('utf-8-sig').splitlines():
                        match = re.match(r'^([a-fA-F0-9]{64})\s+\*?(.+)$', line)
                        if match:
                            expected, rel = match.groups()
                            item = by_name.get(base + rel) or by_name.get(rel)
                            # UI's first independent package declares the entire four-package union.
                            declared.append({'path': rel, 'status': 'DEFERRED_TO_UI_UNION' if item is None
                                             and path.name.startswith('AAOS_UI_补交_') else
                                             'PASS' if item and item['sha256'] == expected.lower() else 'FAIL'})
            return {'status': 'CRC_PASS', 'file_count': len(members), 'members': members,
                    'internal_declared_sha256': declared}
    except (zipfile.BadZipFile, EOFError, RuntimeError) as e:
        return {'status': 'SOURCE_CONTAINER_INVALID', 'diagnostic': str(e)}


def validate_supplements(rows, source):
    declaration = source / 'AAOS_补交文件_大小与SHA256_20261009.txt'
    if not declaration.exists():
        return {'status': 'NOT_RUN_DECLARATION_MISSING'}
    text = declaration.read_text('utf-8-sig')
    expected = re.findall(r'([^\r\n]+\.zip)\r?\nbytes=(\d+)\r?\nSHA256=([a-f0-9]{64})\r?\nmembers=(\d+)', text)
    by_name = {Path(r['source_relative_path']).name: r for r in rows}
    checks = []
    for name, size, sha, count in expected:
        row = by_name.get(name)
        ok = bool(row and row['bytes'] == int(size) and row['sha256'] == sha and
                  row.get('container', {}).get('status') == 'CRC_PASS' and
                  row['container']['file_count'] == int(count))
        checks.append({'file': name, 'status': 'PASS' if ok else 'FAIL'})
    ui = [r for r in rows if Path(r['source_relative_path']).name.startswith('AAOS_UI_补交_')]
    union = {}
    duplicate_conflicts = []
    for r in ui:
        for m in r.get('container', {}).get('members', []):
            if m['path'] in union and union[m['path']]['sha256'] != m['sha256']:
                duplicate_conflicts.append(m['path'])
            union[m['path']] = m
    sums = []
    for r in ui:
        if r.get('container', {}).get('status') != 'CRC_PASS':
            continue
        with zipfile.ZipFile(source / r['source_relative_path']) as z:
            for n in z.namelist():
                if n.endswith('/SHA256SUMS.txt'):
                    base = n.rsplit('/', 1)[0] + '/'
                    for line in z.read(n).decode('utf-8-sig').splitlines():
                        match = re.match(r'^([a-fA-F0-9]{64})\s+\*?(.+)$', line)
                        if match:
                            sha, rel = match.groups()
                            item = union.get(base + rel) or union.get(rel)
                            sums.append({'member': rel, 'status': 'PASS' if item and item['sha256'] == sha.lower() else 'FAIL'})
    ok = len(checks) == 5 and all(c['status'] == 'PASS' for c in checks)
    ok = ok and len(ui) == 4 and len(union) == 155 and not duplicate_conflicts and bool(sums)
    ok = ok and all(c['status'] == 'PASS' for c in sums)
    return {'status': 'PASS' if ok else 'FAIL', 'declared_files': checks,
            'ui_independent_packages': len(ui), 'ui_union_files': len(union),
            'duplicate_conflicts': duplicate_conflicts, 'ui_internal_sha256': sums,
            'scope': '完整分包并集已校验；未创建声明中的重建 ZIP；未执行任务包'}


def write_json(path, data):
    safe(path).parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.pending')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    os.replace(temp, path)


def archive(root, source):
    root, source = safe(root), safe(source)
    if root != safe(CANONICAL_ROOT) or source != REVIEWED_SOURCE:
        raise ValueError('archive command is limited to this checkout and reviewed Record source')
    previous_manifest = root / MANIFEST_REL
    if previous_manifest.exists() and json.loads(previous_manifest.read_text('utf-8')).get('consolidation'):
        raise ValueError('既有归档已合并去重；请使用 find / verify，不重新复制旧恢复包。新增批次需登记新版本。')
    subprocess.run(['git', '-C', str(root), 'check-ignore', '-q', '--', '.project-local/'], check=True)
    dest = bounded(root, ARCHIVE_REL)
    dest.mkdir(parents=True, exist_ok=True)
    before = inventory(source)
    status_before = subprocess.check_output(['git', '-C', str(root), 'status', '--short'], text=True, encoding='utf-8')
    head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    report = {'schema': 'archeaxis/record-material-archive/v1', 'started_at': now(),
              'source_root': str(source), 'canonical_project_root': str(root),
              'archive_root': str(dest), 'head': head, 'git_status_before': status_before,
              'tool': {'python': sys.version, 'command': [sys.executable, *sys.argv]},
              'authorization': '用户 2026-10-09：全部完整归档，做好索引和登记；原件保留；不实施任务包',
              'originals_policy': '独立字节复制、无删除、无原件改写、无硬链接、无上传',
              'authority': 'SOURCE_INPUT_HISTORY; archive availability is not execution approval',
              'files': [], 'excluded': []}
    selected = [(r, classify(r['relative_path'])) for r in before]
    needed = sum(r['bytes'] for r, (role, _) in selected if role)
    if shutil.disk_usage(root).free < needed + 1024 ** 3:
        raise RuntimeError('insufficient space for independent copies')
    for item, (role, reason) in selected:
        rel = item['relative_path']
        if not role:
            report['excluded'].append({**item, 'reason': reason, 'content_read': False})
            continue
        src = bounded(source, rel)
        dst = bounded(dest / 'originals' / 'Record', rel)
        mapping = 'SOURCE_RELATIVE_PATH_PRESERVED'
        if len(str(dst)) >= 240:
            # Preserve source identity in the manifest without changing global long-path policy.
            key = hashlib.sha256(rel.encode('utf-8')).hexdigest()[:20]
            dst = bounded(dest / 'originals' / 'Record', Path('_long-paths') / key / src.name)
            mapping = 'SHORT_ARCHIVE_PATH_COMPLETE_SOURCE_MAPPING'
        print(f'COPY {rel} ({item["bytes"]} bytes)', flush=True)
        sha = copy_verified(src, dst)
        row = {'source_relative_path': rel, 'source_path': str(src),
               'archive_relative_path': dst.relative_to(root).as_posix(), 'archive_path': str(dst),
               'bytes': item['bytes'], 'source_mtime_ns': item['mtime_ns'],
               'sha256': sha, 'copy_status': 'PASS', 'role': role, 'reason': reason,
               'path_mapping': mapping}
        if src.suffix.lower() == '.zip':
            row['container'] = ({'status': 'NOT_RUN_OPAQUE_RECOVERY_COPY_VERIFIED'}
                                if role == 'AAOS_RECOVERY_OR_HISTORICAL_ARTIFACT'
                                else inspect_public_zip(dst))
        report['files'].append(row)
        write_json(dest / 'progress.json', report)
    after = inventory(source)
    report['source_inventory_unchanged'] = before == after
    report['supplement_verification'] = validate_supplements(report['files'], source)
    internal_failures = [{'file': r['source_relative_path'], 'member': c['path']}
                         for r in report['files'] for c in r.get('container', {}).get('internal_declared_sha256', [])
                         if c['status'] == 'FAIL']
    report['internal_declared_hash_failures'] = internal_failures
    report['status'] = 'PASS' if before == after and not internal_failures and report['supplement_verification']['status'] == 'PASS' else 'INVALIDATED_OR_PARTIAL'
    report['archived_files'] = len(report['files'])
    report['archived_bytes'] = sum(r['bytes'] for r in report['files'])
    report['inventoried_files'] = len(before)
    report['excluded_files'] = len(report['excluded'])
    report['completed_at'] = now()
    blueprint = next(r for r in report['files'] if r['source_relative_path'] == '01_AAOS_完整项目描述与未来蓝图_20261006.docx')
    with zipfile.ZipFile(blueprint['archive_path']) as z:
        xml = ET.fromstring(z.read('word/document.xml'))
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        paras = [''.join(t.text or '' for t in p.findall('.//w:t', ns)) for p in xml.findall('.//w:p', ns)]
    textpath = dest / 'derived' / 'AAOS-完整项目描述与未来蓝图-可检索文本.txt'
    textpath.parent.mkdir(parents=True, exist_ok=True)
    textpath.write_text('\n'.join(paras) + '\n', 'utf-8')
    report['derived'] = [{'path': str(textpath), 'sha256': digest(textpath),
                          'role': 'DERIVED_SEARCH_TEXT_NOT_ORIGINAL', 'source_sha256': blueprint['sha256']}]
    write_json(bounded(root, MANIFEST_REL), report)
    write_json(dest / 'MANIFEST.json', report)
    create_index(root, report)
    print(json.dumps({k: report[k] for k in ['status', 'archived_files', 'archived_bytes', 'inventoried_files', 'excluded_files']}, ensure_ascii=False), flush=True)
    return 0 if report['status'] == 'PASS' else 1


def link(path):
    return str(path).replace('\\', '/')


def create_index(root, report):
    lines = ['# AAOS / ArcheAxis Record 完整资料索引', '',
             '这是资料查找入口，不是执行权威。历史任务包、补交分析和设计方案不会自动改写当前任务或实现状态。', '',
             f'登记时间：{report["completed_at"]}；原始来源：`{report["source_root"]}`。',
             f'已归档 **{report["archived_files"]} 文件 / {report["archived_bytes"]:,} 字节**；逐文件独立复制、SHA-256 与目标读回一致。',
             f'Record 共登记 {report["inventoried_files"]} 文件；其余 {report["excluded_files"]} 文件按归属排除并逐条记录理由。原件全部保留。', '',
             f'[机器可读登记与完整哈希](<{link(root / MANIFEST_REL)}>).', '',
             '## 快速查找', '',
             '- 项目蓝图：搜索 `完整项目描述与未来蓝图`；DOCX 原件与派生可检索文本均在本项目。',
             '- 最新任务：搜索 `最后任务包`、`补齐材料与分析增量`。登记不代表已经实施。',
             '- UI：使用四个 `AAOS_UI_补交_01`—`04` 独立完整分包，155 文件并集与内置 SHA256SUMS 已核验。',
             '- 旧 `AAOS_UI_前端更新任务包_20261009.zip` 按原字节保留，但容器截断、已被补交说明废弃；不要当完整包使用。',
             '- 历史安装/恢复/证据：搜索 `AAOS-project-archives`；仅保全文件，不运行或恢复到正式知识库。', '',
             '```powershell',
             "& '.\\.venv\\Scripts\\python.exe' '.\\scripts\\maintenance\\archive_record_materials.py' find '蓝图'",
             "& '.\\.venv\\Scripts\\python.exe' '.\\scripts\\maintenance\\archive_record_materials.py' find 'screens/4K/21.png'",
             "& '.\\.venv\\Scripts\\python.exe' '.\\scripts\\maintenance\\archive_record_materials.py' verify",
             '```', '',
             '查询默认匹配名称、来源路径、资料身份、ZIP 内文件路径；返回可直接打开的项目内归档位置。', '',
             '## 文件登记', '', '| 资料 | 身份 | 大小（字节） | 复制校验 / 容器 |', '| --- | --- | ---: | --- |']
    for r in report['files']:
        state = r.get('container', {}).get('status', '原字节已保全')
        if r.get('storage_kind') == 'SHARED_COMPRESSED_ZIP_RECIPE':
            state = '项目内共享压缩 / 原 ZIP 精确重建 SHA256 PASS；链接为重建清单'
        elif r.get('storage_kind') == 'REUSE_VERIFIED_PROJECT_FILE':
            state = '复用项目内相同 SHA256 原件；不保留新增重复副本'
        lines.append(f'| [{r["source_relative_path"]}](<{link(r["archive_path"])}>) | {r["role"]} | {r["bytes"]} | PASS / {state} |')
    lines += ['', '## 派生可检索材料', '']
    for r in report.get('derived', []):
        lines.append(f'- [{Path(r["path"]).name}](<{link(r["path"])}>); 派生文本，原 DOCX 字节未改写。')
    lines += ['', '## 范围登记与限制', '',
              '- 三项目研究资料与作品集按完整共享参考容器保留；不把 WORK-LAB/DESIGN-LAB 专属任务归入本项目。',
              '- 系统审计目录只保全两个明确属于 AAOS 的文件，其他系统记录排除。',
              '- 大型恢复 ZIP 仅核验整体字节与 SHA-256；未展开数据库、未执行安装生命周期、未宣称内部业务数据可恢复。',
              '- 原始目录的空间未释放；原件与归档副本均保留。此轮未实施 UI、前后端、开源池、模板或 CI 任务。',
              '- 所有排除路径、原因、所有文件完整 SHA-256、原路径→项目路径映射见 MANIFEST.json。',
              '- 本索引在主检出和治理工作树均提供入口；唯一原件保全目录属于主项目 `.project-local/archives/record-20261009/`。', '']
    if report.get('consolidation'):
        c = report['consolidation']
        lines[5] = (f'已登记 **{report["archived_files"]} 文件 / 原始逻辑字节 {report["archived_bytes"]:,}**；'
                    f'所有内容保存在本项目，历史 ZIP 使用共享压缩片段与精确重建清单。')
        lines += ['## 合并去重与恢复', '',
                  f'13 个历史 ZIP 原始 {c["original_bytes"]:,} 字节，合并存储 {c["stored_bytes"]:,} 字节；'
                  f'全部原 ZIP 完整重建哈希匹配。另复用 {len(report.get("reused_project_files", []))} 项项目内已有原件。', '',
                  f'[历史材料关键信息与恢复要点](<{link(root / MANIFEST_REL.parent / "HISTORICAL-SUMMARY.md")}>).',
                  f'[合并清单与校验结果](<{link(root / MANIFEST_REL.parent / "CONSOLIDATION.json")}>).', '',
                  '需要某个历史 ZIP 时按查询结果的 sha256 执行以下命令，输出限于项目 `.project-local/`：', '',
                  '```powershell',
                  "& '.\\.venv\\Scripts\\python.exe' '.\\scripts\\maintenance\\compact_record_archives.py' restore --sha256 <原ZIP哈希> --output '.\\.project-local\\restored\\历史包.zip'",
                  '```', '',
                  'Record 原件未迁出、未删除；项目内压缩副本可独立恢复，无须依赖 Record。未迁到外库。', '']
    index = bounded(root, MANIFEST_REL.parent / 'INDEX.md')
    index.write_text('\n'.join(lines), 'utf-8')
    entry = root / 'AAOS-资料索引.md'
    entry.write_text('# AAOS / ArcheAxis 资料查找入口\n\n'
                     f'[完整索引、原始文件与补交材料登记](<{link(index)}>).\n\n'
                     f'[JSON 路径映射与 SHA-256](<{link(root / MANIFEST_REL)}>).\n\n'
                     '查资料先查本入口。原件已保全到本项目 `.project-local/archives/record-20261009/`；'
                     '历史 TaskPack 仅为来源资料，不授予执行权限。\n', 'utf-8')


def verify(root):
    manifest = json.loads(bounded(root, MANIFEST_REL).read_text('utf-8'))
    owner = safe(Path(manifest['canonical_project_root']))
    failures = []
    for row in manifest['files']:
        p = bounded(owner, row['archive_relative_path'])
        print(f'VERIFY {row["source_relative_path"]}', flush=True)
        if row.get('storage_kind') == 'SHARED_COMPRESSED_ZIP_RECIPE':
            import compact_record_archives as compact
            try:
                recipe = json.loads(p.read_text('utf-8'))
                if recipe['original_sha256'] != row['sha256'] or recipe['original_bytes'] != row['bytes']:
                    raise RuntimeError('recipe does not match registered original')
                compact.verify_recipe(bounded(owner, manifest['consolidation']['bundle_relative_path']), recipe)
            except (ValueError, OSError, RuntimeError):
                failures.append(row['source_relative_path'])
        elif not p.is_file() or p.stat().st_size != row['bytes'] or digest(p) != row['sha256']:
            failures.append(row['source_relative_path'])
    for row in manifest.get('derived', []):
        p = safe(Path(row['path']))
        if not p.is_relative_to(owner / ARCHIVE_REL) or digest(p) != row['sha256']:
            failures.append(row['path'])
    print(json.dumps({'status': 'PASS' if not failures else 'FAIL', 'checked_files': len(manifest['files']), 'failures': failures}, ensure_ascii=False))
    return int(bool(failures))


def find(root, query):
    manifest = json.loads(bounded(root, MANIFEST_REL).read_text('utf-8'))
    query = query.casefold()
    hits = []
    for row in manifest['files']:
        matches = [m['path'] for m in row.get('container', {}).get('members', []) if query in m['path'].casefold()]
        fields = [row['source_relative_path'], row['source_path'], row['role'], row['sha256']]
        if matches or any(query in s.casefold() for s in fields):
            hits.append({'source': row['source_path'], 'archive': row['archive_path'],
                         'sha256': row['sha256'], 'matching_zip_members': matches,
                         'storage_kind': row.get('storage_kind', 'ORIGINAL_FILE'),
                         'restore_command': row.get('restore_command'),
                         'exists': safe(Path(row['archive_path'])).is_file()})
    print(json.dumps(hits, ensure_ascii=False, indent=2))
    return 0 if hits else 2


def reindex(root):
    """Recheck public container metadata after parser fixes, without copying payloads."""
    if safe(root) != safe(CANONICAL_ROOT):
        raise ValueError('reindex must run in the canonical main checkout')
    report = json.loads(bounded(root, MANIFEST_REL).read_text('utf-8'))
    expected = [{'relative_path': r['source_relative_path'], 'bytes': r['bytes'],
                 'mtime_ns': r['source_mtime_ns']} for r in report['files']]
    expected += [{k: r[k] for k in ('relative_path', 'bytes', 'mtime_ns')}
                 for r in report['excluded']]
    actual = inventory(safe(Path(report['source_root'])))
    report['source_inventory_unchanged'] = sorted(expected, key=lambda r: r['relative_path']) == sorted(actual, key=lambda r: r['relative_path'])
    for r in report['files']:
        if r.get('container') and r['role'] != 'AAOS_RECOVERY_OR_HISTORICAL_ARTIFACT':
            p = bounded(root, r['archive_relative_path'])
            if digest(p) != r['sha256']:
                raise RuntimeError(f'archive changed: {p}')
            r['container'] = inspect_public_zip(p)
    report['supplement_verification'] = validate_supplements(report['files'], Path(report['source_root']))
    failures = [{'file': r['source_relative_path'], 'member': c['path']}
                for r in report['files'] for c in r.get('container', {}).get('internal_declared_sha256', [])
                if c['status'] == 'FAIL']
    report['internal_declared_hash_failures'] = failures
    report['status'] = 'PASS' if report['source_inventory_unchanged'] and not failures and report['supplement_verification']['status'] == 'PASS' else 'INVALIDATED_OR_PARTIAL'
    report['reindexed_at'] = now()
    report['reindex_script_sha256'] = digest(Path(__file__))
    write_json(root / MANIFEST_REL, report)
    write_json(root / ARCHIVE_REL / 'MANIFEST.json', report)
    create_index(root, report)
    print(json.dumps({'status': report['status'], 'internal_failures': failures}, ensure_ascii=False))
    return int(report['status'] != 'PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['archive', 'find', 'verify', 'reindex'])
    parser.add_argument('query', nargs='?', default='')
    parser.add_argument('--source', type=Path, default=None)
    args = parser.parse_args()
    if args.action == 'archive':
        if args.source is None:
            parser.error('archive requires the explicitly reviewed --source path')
        return archive(ROOT, args.source)
    if args.action == 'reindex':
        return reindex(ROOT)
    return find(ROOT, args.query) if args.action == 'find' else verify(ROOT)


if __name__ == '__main__':
    raise SystemExit(main())
