"""Real native teaching inputs, cold recovery and canonical preparation readback.

Only the document-create ACK is synthetically lost, after Core executes it.
No direct state writes, Owner material, teaching submissions or model calls.
"""
from __future__ import annotations

import json

def form_scope(page):
    if page not in ('11', '12'):
        raise ValueError('Teaching probe only operates pages 11/12')
    return ("//div[contains(concat(' ',normalize-space(@class),' '),' dock-business-host ')"
            + " and contains(@data-session-key,':" + page + ":workspace')]"
            + "//form[@aria-label='创建教学记录' and not(ancestor-or-self::*[@hidden or @aria-hidden='true'])]")


OBSERVE = """const page=location.hash.slice(6);
const forms=[...document.querySelectorAll('form[aria-label="创建教学记录"]')].filter(n=>
 n.getClientRects().length>0&&!n.closest('[hidden],[aria-hidden="true"]')&&
 n.closest('.dock-business-host')?.dataset.sessionKey?.endsWith(':'+page+':workspace'));
const form=forms.length===1?forms[0]:null;
const field=label=>[...(form?.querySelectorAll('label')??[])].find(n=>[...n.childNodes].filter(x=>x.nodeType===3).map(x=>x.textContent).join('').trim()===label)?.querySelector('input,textarea,select');
const observed={form_count:forms.length,page,purpose:field('用途')?.value,content:field('内容')?.value,
rubric_version:field('评测准则版本')?.value,feedback_class:field('反馈分类')?.value??null,
editable:!!field('内容')&&!field('内容').disabled&&!field('内容').closest('fieldset')?.disabled};
"""


def assert_draft(state, key, expected):
    assert state['recovery_requires_confirmation'] is False
    entry = state['state'].get('teaching_drafts', {}).get(key)
    assert entry is not None, 'Missing durable teaching draft'
    page, context = key.split(':', 1)
    assert entry['page_id'] == page and entry['context_item_key'] == (context or None)
    assert entry['pending_record'] is None, 'Raw draft became a formal teaching submission'
    for field, value in expected.items():
        assert entry['form'][field] == value, 'Raw teaching field changed: ' + field
    return entry


def assert_visible(observed, expected, page):
    assert observed['form_count'] == 1 and observed['page'] == page, 'No unique visible current-page teaching form'
    assert observed['editable'] is True
    for field, value in expected.items():
        assert observed[field] == value, 'Visible teaching input changed: ' + field


def assert_cleanup(before, after, key):
    expected = dict(before['state'].get('teaching_drafts', {}))
    assert key in expected
    del expected[key]
    assert after['state'].get('teaching_drafts', {}) == expected, 'Wrong teaching draft cleared'
    assert (before['workspace_id'], before['restore_epoch']) == (after['workspace_id'], after['restore_epoch'])


def assert_document(document, expected, frozen):
    body = frozen['payload']['body']
    assert frozen['operation'] == 'document_create'
    assert document['version'] == 1 and document['title'] == expected['purpose'].strip()
    assert document['source_id'] is None and document['source_revision'] is None
    assert document['editor_json'] == body['editor_json'], 'Canonical editor differs from frozen request'
    lines = [''.join(child['text'] for child in node.get('content', [])) for node in document['editor_json']['content']]
    assert '\n'.join(lines) == expected['content'], 'Canonical paragraphs lost whitespace or empty lines'
    assert document['text_projection'] == '\n'.join(line for line in lines if line)


def install_create_observer(js, lose):
    js("""const original=window.__TAURI__,invoke=original.core.invoke;
window.__aaosTeachingOriginal=original;window.__aaosTeachingProof={rows:[],faults:0};
const lose=""" + json.dumps(lose) + """;
const observed=async function(command,args,...rest){
 const op=args?.request?.operation;
 if(command==='core_command'&&['machine_answer','machine_retest'].includes(op))throw new Error('TEACHING_PROBE_MODEL_FORBIDDEN');
 const value=await Reflect.apply(invoke,original.core,[command,args,...rest]);
 if(command==='core_command'&&op==='document_create'){
 window.__aaosTeachingProof.rows.push({payload:args.request.payload,status:value.status,document_id:value.body?.document_id});
 if(lose&&value.status>=200&&value.status<300&&window.__aaosTeachingProof.faults===0){window.__aaosTeachingProof.faults++;throw new Error('SYNTHETIC_TEACHING_CREATE_ACK_LOST');}}
 return value;
};window.__TAURI__={...original,core:{...original.core,invoke:observed}};
if(window.__TAURI__.core.invoke!==observed)throw new Error('Observer installation refused');""")


def remove_create_observer(js):
    proof = js('return window.__aaosTeachingProof;')
    js('window.__TAURI__=window.__aaosTeachingOriginal;delete window.__aaosTeachingOriginal;delete window.__aaosTeachingProof;')
    return proof


def run(*, ui, bridge, read, js, wait, restart, poll, screenshot, report):
    report.update(engineering_status='IN_PROGRESS', status='PARTIAL', mode='TEACHING_DRAFT_ONLY',
                  evidence_level='REAL_NATIVE_SYNTHETIC_MATERIAL', model_calls='NOT_EXECUTED',
                  owner_acceptance='NOT_EXECUTED', closed_loop_verified=False,
                  context_coverage='UNBOUND_PAGE_CONTEXT_ONLY', fault_injection='SYNTHETIC_DOCUMENT_CREATE_ACK_LOSS')
    assert read('sources_list')['sources'] == [], 'Needs a fresh owned workspace'
    assert read('documents_list')['documents'] == []
    assert read('ui_state_read')['state'].get('teaching_drafts', {}) == {}
    first = dict(purpose='  Teach-back 原始用途  ', content='  第一行\n第二行  \n\n')
    other = dict(purpose='  反馈原始用途  ', content='  另一页原始正文\n保持独立\n\n', rubric_version='  rubric-probe-v1  ', feedback_class='professional_basis')

    def show(page, expected):
        ui.page(page, confirm_navigation=True)
        wait(OBSERVE + 'return observed.editable;')
        assert_visible(js(OBSERVE + 'return observed;'), expected, page)

    ui.page('11')
    ui.type('用途', first['purpose'], scope=form_scope('11'))
    ui.type('内容', first['content'], 'textarea', form_scope('11'))
    poll(read, 'ui_state_read', {}, lambda state: state['state'].get('teaching_drafts', {}).get('11:', {}).get('form', {}).get('content') == first['content'])
    ui.page('12', confirm_navigation=True)
    ui.type('用途', other['purpose'], scope=form_scope('12'))
    ui.type('内容', other['content'], 'textarea', form_scope('12'))
    ui.type('评测准则版本', other['rubric_version'], scope=form_scope('12'))
    ui.keys(form_scope('12') + "//label[normalize-space(text())='反馈分类']/select", '\ue015\ue007')
    before = poll(read, 'ui_state_read', {}, lambda state: state['state'].get('teaching_drafts', {}).get('12:', {}).get('form', {}).get('feedback_class') == other['feedback_class'])
    for key, expected in [('11:', first), ('12:', other)]:
        assert_draft(before, key, expected)
    ui.page('01', confirm_navigation=True)
    restart()
    after = read('ui_state_read')
    assert after['state'].get('teaching_drafts', {}) == before['state']['teaching_drafts']
    assert (after['workspace_id'], after['restore_epoch']) == (before['workspace_id'], before['restore_epoch'])
    show('11', first)
    show('12', other)
    show('11', first)
    screenshot('teaching-draft-pages-restored.png')
    report['raw_recovery'] = dict(status='PASS', pages=['11:', '12:'], exact_strings=True, cold_restart=True)

    install_create_observer(js, True)
    try:
        ui.click('保存准备正文草稿', form_scope('11'))
        wait("return window.__aaosTeachingProof.faults===1&&document.body.innerText.includes('操作未确认完成')")
    finally:
        lost = remove_create_observer(js)
    assert lost['faults'] == 1 and len(lost['rows']) == 1
    frozen_state = read('ui_state_read')
    frozen = assert_draft(frozen_state, '11:', first)['preparation_attempt']
    assert frozen['payload'] == lost['rows'][0]['payload']
    rows = read('documents_list')
    assert rows['next_cursor'] is None and len(rows['documents']) == 1
    document_id = rows['documents'][0]['document_id']
    assert document_id == lost['rows'][0]['document_id']
    assert_document(read('document_get', {'document_id': document_id}), first, frozen)
    restart()
    assert assert_draft(read('ui_state_read'), '11:', first)['preparation_attempt'] == frozen
    show('11', first)
    install_create_observer(js, False)
    try:
        ui.click('保存准备正文草稿', form_scope('11'))
        wait("return document.body.innerText.includes('准备正文已保存并读回')")
    finally:
        retried = remove_create_observer(js)
    assert len(retried['rows']) == 1 and retried['rows'][0]['payload'] == frozen['payload']
    assert retried['rows'][0]['document_id'] == document_id
    cleared = poll(read, 'ui_state_read', {}, lambda state: '11:' not in state['state'].get('teaching_drafts', {}))
    assert_cleanup(frozen_state, cleared, '11:')
    assert_document(read('document_get', {'document_id': document_id}), first, frozen)
    restart()
    assert_cleanup(frozen_state, read('ui_state_read'), '11:')
    assert read('documents_list') == rows, 'Retry created or revised another document'
    show('11', dict(purpose='', content=''))
    show('12', other)
    screenshot('teaching-draft-cleanup-other-page-preserved.png')
    report.update(engineering_status='PASS', status='PASS_IMPLEMENTED_UNBOUND_TEACHING_DRAFT_FIELDS',
                  preparation=dict(status='PASS', document_id=document_id, exact_body=True, one_document=True,
                                   same_create_request_across_restart=True, cleanup_survives_restart=True,
                                   other_page_preserved=True), formal_teaching_submission='NOT_EXECUTED')
    return report
