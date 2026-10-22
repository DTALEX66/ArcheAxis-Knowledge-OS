"""Read-only authored saved collection UI probe; actual Core, synthetic native transport. No business writes."""
import argparse
import base64
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
from urllib.parse import urlsplit, quote

ROOT = Path.cwd().resolve()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-receipt', type=Path, required=True)
    parser.add_argument('--runtime-receipt', type=Path, required=True)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--ui-only-build', action='store_true', help='Interim built UI + hash-identical existing Core; not qualification of a new portable candidate')
    parser.add_argument('--discovery', action='store_true', help='Verify saved collection discovery through the normal library before opening the reader')
    args = parser.parse_args()
    run = Path(os.environ['ARCHEAXIS_RUN_ROOT']).resolve()
    run.relative_to(ROOT / '.project-local/runs')
    build = json.loads(args.build_receipt.read_text(encoding='utf-8'))
    runtime = json.loads(args.runtime_receipt.read_text(encoding='utf-8'))
    assert build['status'] == 'PASS' and build['source_consistent']
    assert (runtime['schema'],runtime['status']) == (('archeaxis.collection-discovery-runtime/v1','PASS_AUTHORED_DISCOVERY_SUBSET') if args.discovery else ('archeaxis.collection-reader-runtime/v1','PASS_AUTHORED_COLLECTION_SUBSET'))
    assert runtime['candidate_unchanged'] and runtime['independent_restore_equal']
    dist = Path(build['frontend_dist']).resolve()
    dist.relative_to(ROOT / '.project-local/runs')
    candidate, workspace = (args.candidate or Path(runtime['candidate'])).resolve(), Path(runtime['independent_workspace']).resolve()
    for p in (candidate, workspace):
        p.relative_to(ROOT / '.project-local/runs')
    office = load('embed_real_browser_office', ROOT / 'scripts/probes/aaos01_office_runtime_loop.py')
    helper = load('embed_real_browser_helper', ROOT / 'scripts/probes/aaos_public_research_runtime_loop.py')
    launcher = load('embed_real_browser_launcher', ROOT / 'scripts/release/backend_launcher.py')
    client = load('embed_real_browser_client', ROOT / 'shared/core_client.py')
    harness = load('embed_real_browser_harness', ROOT / 'scripts/probes/stitch_ui_browser.py')
    # Bind relevant candidate identities directly; full assembly retains its own receipt.
    assert runtime['candidate_unchanged']
    manifest = json.loads((candidate / 'candidate-manifest.json').read_text(encoding='utf-8'))
    if not args.ui_only_build:
        assert manifest['build_receipt']['sha256'] == hashlib.sha256(args.build_receipt.read_bytes()).hexdigest()
    assert manifest['core_sha256']==build['core_sha256']
    assert manifest['files']['backend-runtime-manifest.json']['sha256']==build['backend_manifest_sha256']
    if args.candidate:
        previous = json.loads((Path(runtime['candidate']) / 'candidate-manifest.json').read_text(encoding='utf-8'))
        assert set(previous['files']) == set(manifest['files'])
        changed = [name for name in manifest['files'] if manifest['files'][name] != previous['files'][name]]
        assert set(changed).issubset({'ArcheAxis.exe'}), changed
    prior = {'document_id':runtime['baseline_document_id'],'item_key':runtime['baseline_item_key']}
    def candidate_identity():
        names = ['ArcheAxis.exe', 'core/archeaxis-api.exe', 'backend-runtime-manifest.json', 'worker-profile.json', 'candidate-manifest.json']
        return {name: hashlib.sha256((candidate / name).read_bytes()).hexdigest() for name in names}
    identity_before = candidate_identity()
    for name in ('ArcheAxis.exe', 'core/archeaxis-api.exe', 'worker-profile.json', 'backend-runtime-manifest.json'):
        assert identity_before[name] == manifest['files'][name]['sha256']
    if not args.ui_only_build: assert manifest['host_sha256'] == build['host_sha256']
    out = run / 'artifacts/real-collection-reader-browser'
    out.mkdir(exist_ok=False)
    receipt = {'schema': 'archeaxis.collection-reader-real-browser/v1', 'status': 'RUNNING',
               'evidence_level': 'INTEGRATED_REAL_CORE_WITH_SIMULATED_HOST_TRANSPORT',
               'native_host': 'NOT_EXECUTED', 'installed': 'NOT_EXECUTED', 'portable_qualification':'NOT_EXECUTED_INTERIM_UI_ONLY' if args.ui_only_build else 'read bound candidate manifest; host not executed',
               'candidate': str(candidate), 'built_ui': str(dist), 'built_host_sha256': build['host_sha256'], 'runtime_candidate_host_sha256':manifest['host_sha256'], 'candidate_host_executed':False, 'ui_only_build':args.ui_only_build,
               'core_sha256': build['core_sha256'], 'source_patch_sha256': build['source_patch_sha256'],
               'probe_source_patch_sha256': runtime.get('probe_source_patch_sha256', 'recorded in runtime wrapper'),
               'execution_source_patch_sha256': os.environ['ARCHEAXIS_SOURCE_PATCH_SHA256'],
               'runtime_api_evidence_candidate': runtime['candidate'],
               'backend_member_reuse': 'exact manifest members equal except rebuilt host' if args.candidate else 'same candidate',
               'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'candidate_identity_scope': 'host/Core/runtime-manifest/worker-profile/candidate-manifest; existing candidate assembler verified all members at its own recorded time',
               'candidate_identity_before': identity_before,
               'real_core_calls': [], 'simulated_operations': [], 'console_errors': [], 'blocked_external': [],
               'stopped': [], 'cleanup': {}}
    child = context = server = thread = None
    browser_pids = []
    base = token = None

    def checkpoint():
        (out / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def core_read(op, payload):
        # Finite, read-only test transport. No launch address/token reaches JS.
        p = payload or {}
        method,body='GET',None
        identity = lambda key: quote(str(p[key]), safe='')
        if op == 'system_version': path = '/api/v1/system/version'
        elif op == 'documents_list': path = '/api/v1/documents' + ('?cursor='+identity('cursor') if p.get('cursor') else '')
        elif op == 'sources_list': path = '/api/v1/sources'
        elif op == 'source_jobs': path = f'/api/v1/sources/{identity("source_id")}/jobs'
        elif op == 'document_get': path = f'/api/v1/documents/{identity("document_id")}'
        elif op == 'document_version': path = f'/api/v1/documents/{identity("document_id")}/versions/{int(p["version"])}'
        elif op == 'collection_query':
            path = f'/api/v1/documents/{identity("document_id")}/collection?view_id={identity("view_id")}&version={int(p["version"])}&offset={int(p["offset"])}&limit={int(p["limit"])}'
        elif op == 'document_checks': path = f'/api/v1/documents/{identity("document_id")}/checks?version={int(p["version"])}'
        elif op == 'source_original': path = f'/api/v1/sources/{identity("source_id")}/original'
        elif op == 'knowledge_get': path = f'/api/v1/knowledge-items/{identity("id")}/v3'
        elif op == 'knowledge_qualification': path = f'/api/v1/knowledge-items/{identity("id")}/qualification'
        elif op == 'course_get': path = f'/api/v1/courses/{identity("course_id")}'
        elif op == 'teaching_list': path = '/api/v2/teaching/records'
        elif op == 'course_list': path = '/api/v1/courses'
        elif op == 'learning_items': path = '/api/v1/learning/items'
        elif op == 'learning_state': path = f'/api/v1/learning/items/{identity("item_key")}/state'
        elif op == 'learning_history': path = f'/api/v1/learning/events/{identity("item_key")}'
        elif op == 'assessment_get': path = f'/api/v1/learning/items/{identity("item_key")}/assessment'
        elif op == 'document_graph': path = f'/api/v1/documents/{identity("document_id")}/relations'
        elif op == 'source_get': path = f'/api/v1/sources/{identity("source_id")}'
        elif op == 'anchors_list': path = f'/api/v1/sources/{identity("source_id")}/anchors'
        elif op == 'anchor_resolve': path = f'/api/v1/sources/{identity("source_id")}/anchors/{identity("anchor_id")}/resolve'
        elif op == 'source_pages': path = f'/api/v1/sources/{identity("source_id")}/pages'
        elif op == 'source_members': path = f'/api/v1/sources/{identity("source_id")}/members'
        elif op == 'jobs_get': path = f'/api/v1/jobs/{identity("job_id")}'
        elif op == 'job_output':
            assert p['kind'] in ('text','document_structure','loss_report')
            path = f'/api/v1/jobs/{identity("job_id")}/outputs/{identity("kind")}'
        elif op == 'job_quality': path = f'/api/v1/jobs/{identity("job_id")}/quality'
        elif op == 'job_execution_status': path = f'/api/v1/jobs/{identity("job_id")}/execution-status'
        elif op == 'source_job_transform': path = f'/api/v1/sources/{identity("source_id")}/jobs/{identity("job_id")}/transform'
        elif op == 'capabilities_list': path = '/api/v1/capabilities'
        else: raise ValueError('Unexpected operation ' + op)
        status, value = client.call(base, method, path, token, body, timeout=45)
        receipt['real_core_calls'].append({'op': op, 'payload': p, 'method':method, 'status': status})
        checkpoint()
        return {'status': status, 'body': value}

    class StaticHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_): pass

    try:
        child, base, token, _ = helper.hidden_start(office, candidate, workspace, launcher)
        receipt['core_pid'] = child.pid
        main_before = core_read('document_get', {'document_id': prior['document_id']})['body']
        history_before = core_read('learning_history', {'item_key': prior['item_key']})['body']
        collection_before=core_read('document_get',{'document_id':runtime['document_id']})['body']
        server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(StaticHandler, directory=str(dist)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_port
        receipt['server_port'] = port
        a0 = harness.load_a0()
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            chromium = a0._declared_tool('ext.toolchains.playwright-chromium', 'playwright-chromium')
            assert chromium
            assert next(x for x in Path(chromium).parts if x.startswith('chromium-')) == next(x for x in Path(playwright.chromium.executable_path).parts if x.startswith('chromium-'))
            context = playwright.chromium.launch_persistent_context(str(run / 'tmp/real-collection-profile'), executable_path=chromium,
                headless=True, viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce', service_workers='block', accept_downloads=False,
                args=['--disable-background-networking', '--disable-component-update', '--no-first-run', '--no-default-browser-check', '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1'])
            session = context.browser.new_browser_cdp_session()
            browser_pids = [p['id'] for p in session.send('SystemInfo.getProcessInfo')['processInfo'] if p['type'] == 'browser']
            session.detach()
            assert browser_pids
            receipt['browser_pids'] = browser_pids
            context.expose_function('__embedRealRead', core_read)
            script = a0.host_bridge_stub() + '''
(() => {
 const previous=window.__TAURI__.core.invoke;
 const reads=new Set(['system_version','documents_list','sources_list','source_jobs','document_get','document_version','document_checks','source_original','knowledge_get','knowledge_qualification','learning_items','learning_state','learning_history','assessment_get','document_graph','course_list','course_get','teaching_list','source_get','anchors_list','anchor_resolve','source_pages','source_members','jobs_get','job_output','job_quality','job_execution_status','source_job_transform','capabilities_list','collection_query']);
 window.__embedShimCalls=[];
 window.__TAURI__.core.invoke=async(command,request)=>{
   const op=request?.request?.operation,p=request?.request?.payload??{};
   if(command==='core_command'&&reads.has(op)){const result=await window.__embedRealRead(op,p);return result;}
   if(command==='core_command'&&['document_draft','document_create','ingest_member_relations_apply','learning_review','knowledge_review','assessment_create','learning_reference','job_execute','job_enqueue','anchor_create','knowledge_from_transform','source_import','course_from_knowledge','capability_set_enabled'].includes(op))throw new Error('READ_ONLY_BROWSER_PROBE');
   window.__embedShimCalls.push({command,operation:op});
   return previous(command,request);
 };
})();'''
            context.add_init_script("if(location.protocol==='http:'){" + script + '}')
            def route_request(route):
                url = urlsplit(route.request.url)
                if url.hostname != '127.0.0.1' or url.port != port or url.scheme != 'http':
                    receipt['blocked_external'].append(route.request.url)
                    route.abort('blockedbyclient')
                elif url.path.startswith('/api') or url.path.startswith('/workspace/api'):
                    route.fulfill(status=200, content_type='application/json', body=json.dumps(a0.api_payload(route.request.url)))
                else: route.continue_()
            context.route('**/*', route_request)
            context.route_web_socket('**/*', lambda _: None)
            page = context.new_page()
            page.set_default_timeout(10000)
            page.on('pageerror', lambda e: receipt['console_errors'].append(str(e)))
            page.on('console', lambda m: receipt['console_errors'].append(m.text) if m.type == 'error' else None)
            try:
                from playwright.sync_api import expect
                page.goto(f'http://127.0.0.1:{port}/#page=02',wait_until='networkidle')
                if page.get_by_role('button',name='收起小栖窗口').is_visible(): page.get_by_role('button',name='收起小栖窗口').click()
                if args.discovery:
                    page.get_by_role('button',name='打开文档 '+runtime['latest_target']['title'],exact=True).wait_for()
                    tab=page.get_by_role('button',name='集合文档',exact=True)
                    tab.focus();page.keyboard.press('Enter')
                    expect(tab).to_have_attribute('aria-pressed','true')
                    expect(page.get_by_role('button',name='打开文档 '+runtime['latest_target']['title'],exact=True)).to_have_count(0)
                    expect(page.get_by_role('button',name='打开文档 '+runtime['document']['title'],exact=True)).to_be_visible()
                    expect(page.get_by_text('含保存版集合',exact=True)).to_be_visible()
                    expect(page.get_by_text('部分已加载文档未提供集合信息',exact=False)).to_have_count(0)
                    page.screenshot(path=str(out/'collection-discovery.png'))
                    receipt['discovery']={'actual_summary_flag':True,'ordinary_document_excluded':True,'keyboard_selects_collection_filter':True,'document_identity_retained':True,'scope':'Loaded summary page; further pages use the existing document cursor'}
                page.get_by_role('button',name='打开文档 '+runtime['document']['title'],exact=True).click()
                reader=page.get_by_role('region',name='阅读与编辑文档视图',exact=True)
                reader.get_by_role('heading',name=runtime['document']['title'],exact=True).wait_for()
                panel=reader.get_by_role('region',name='集合属性与视图',exact=True)
                expect(panel.get_by_role('textbox')).to_have_count(0)
                expect(panel.get_by_text('添加属性',exact=True)).to_have_count(0)
                receipt['views']=[]
                for kind in ('table','list','board','calendar','gallery','filtered'):
                    panel.get_by_role('combobox',name='读取保存版视图',exact=True).select_option(kind)
                    panel.get_by_role('button',name='读取已保存视图',exact=True).click()
                    start=21 if kind=='filtered' else 0
                    expect(panel.get_by_text(f'资料条目 {start:02}',exact=True)).to_be_visible()
                    bounds=reader.locator('.ui-reader-document').evaluate('''(root)=>{const panel=root.querySelector(':scope > .collection-panel'),editor=root.querySelector(':scope > .document-editor');const p=panel.getBoundingClientRect();const children=[...editor.querySelectorAll('nav,.tiptap')].map(e=>e.getBoundingClientRect().bottom);return {panel_top:p.top,editor_content_bottom:Math.max(...children),nonoverlap:p.top>=Math.max(...children)-1}}''')
                    assert bounds['nonoverlap'], f'Reader editor overlaps saved collection: {bounds}'
                    receipt.setdefault('layout_bounds',[]).append({'kind':kind,**bounds})
                    if kind=='table':
                        table=panel.get_by_role('table')
                        expect(table.get_by_role('row')).to_have_count(21)
                        expect(table.get_by_role('row').nth(2).get_by_role('cell').last).to_have_text('2')
                        panel.get_by_role('button',name='下一页',exact=True).click()
                        expect(panel.get_by_text('资料条目 20',exact=True)).to_be_visible()
                        expect(table.get_by_role('row')).to_have_count(7)
                        expect(panel.get_by_role('button',name='下一页',exact=True)).to_have_count(0)
                    if kind in ('board','calendar'): expect(panel.get_by_label('分组总数',exact=True)).to_be_visible()
                    receipt['views'].append({'kind':kind,'actual_core_values_visible':True,'pagination_checked':kind=='table'})
                    if kind=='gallery':
                        page.set_viewport_size({'width':640,'height':480})
                        panel.get_by_text('资料条目 00',exact=True).scroll_into_view_if_needed()
                        expect(panel.get_by_text('资料条目 00',exact=True)).to_be_visible()
                        assert panel.locator('.collection-gallery').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
                        page.screenshot(path=str(out/'collection-gallery-narrow.png'))
                        receipt['narrow_gallery_visible']=True
                        page.set_viewport_size({'width':1440,'height':1000})
                panel.get_by_role('button',name='查看文档 v1',exact=True).first.click()
                pinned=page.get_by_role('complementary',name='固定版本引用阅读',exact=True)
                expect(pinned.get_by_role('heading',name=runtime['target']['title']+' · v1',exact=True)).to_be_visible()
                expect(pinned.locator('pre').first).to_have_text(runtime['target']['text_projection'])
                assert runtime['latest_target']['text_projection'] not in pinned.inner_text()
                pinned.locator('pre').first.scroll_into_view_if_needed()
                expect(pinned.locator('pre').first).to_be_visible()
                page.screenshot(path=str(out/'collection-fixed-v1.png'))
                receipt['fixed_v1_despite_current_v2']=True
                pinned.get_by_role('button',name='关闭引用',exact=True).click()
                panel.scroll_into_view_if_needed()
                page.screenshot(path=str(out/'collection-filtered.png'))

                receipt['simulated_operations']=page.evaluate('window.__embedShimCalls')
                assert all(c['method']=='GET' for c in receipt['real_core_calls'])
                assert any(c['op']=='collection_query' and c['status']==200 for c in receipt['real_core_calls'])
                assert not receipt['console_errors'] and not receipt['blocked_external']
            except Exception:
                page.screenshot(path=str(out / 'failure.png'))
                (out / 'failure.txt').write_text(page.locator('body').inner_text()[:18000], encoding='utf-8')
                receipt['simulated_operations'] = page.evaluate('window.__embedShimCalls')
                raise
            context.close()
            context = None
        assert core_read('document_get', {'document_id': prior['document_id']})['body'] == main_before
        assert core_read('learning_history', {'item_key': prior['item_key']})['body'] == history_before
        assert core_read('document_get',{'document_id':runtime['document_id']})['body']==collection_before
        receipt['collection_unchanged']=True
        receipt['learning_history_unchanged'] = True
        receipt['document_unchanged'] = True
        receipt['status'] = 'PASS'
    except Exception as e:
        receipt.update(status='FAIL', error=f'{type(e).__name__}: {e}')
    finally:
        if context:
            try: context.close()
            except Exception as e: receipt['cleanup']['context_close_observation'] = str(e)
        if server:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            receipt['cleanup']['server_closed'] = not thread.is_alive() and not harness.port_open(receipt['server_port'])
        if child:
            try: helper.stop_owned(child, launcher, receipt['stopped'])
            except Exception as e: receipt.update(status='FAIL', cleanup_error=str(e))
        receipt['cleanup']['browser'] = [{'pid': p, 'exited': not harness.pid_running(p)} for p in browser_pids]
        if any(not p['exited'] for p in receipt['cleanup']['browser']) or receipt['cleanup'].get('server_closed') is False:
            receipt['status'] = 'FAIL'
        try:
            receipt['candidate_identity_after'] = candidate_identity()
            assert receipt['candidate_identity_after'] == identity_before
            receipt['candidate_identity_unchanged'] = True
        except Exception as e: receipt.update(status='FAIL', candidate_identity_unchanged=False, identity_error=str(e))
        checkpoint()
    print(json.dumps({'status': receipt['status'], 'real_calls': len(receipt['real_core_calls']), 'receipt': str(out / 'receipt.json')}, ensure_ascii=False))
    return 0 if receipt['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
