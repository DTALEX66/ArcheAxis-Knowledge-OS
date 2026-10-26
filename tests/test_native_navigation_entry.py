"""SIMULATED DOM; actual probe JS, no Host, model or business storage."""
import ast
import importlib.util
import json
import os
import re
from unittest.mock import Mock
from pathlib import Path

import pytest

from tests.dom_harness import evaluate

ROOT = Path(os.environ.get("AAOS_PROBE_TEST_ROOT", str(Path(__file__).resolve().parents[1])))
SOURCE = ROOT / "scripts/probes/aaos01_grouped_owner_loop.py"
SPEC = importlib.util.spec_from_file_location("native_navigation_entry_probe", SOURCE)
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)

MENU = '''<nav class="stitch-workspace-menu" aria-label="应用菜单"><div class="stitch-menus">
<details><summary>文件</summary><div><button data-page-id="02">知识库</button><button data-page-id="03">阅读</button></div></details>
<details><summary>知识</summary><div><button data-page-id="03">阅读</button></div></details>
<button aria-label="全部页面，打开产品导航">全部页面</button></div></nav>
<nav class="stitch-workspace-dock" aria-label="工作空间快捷导航"><button data-page-id="01">工作台</button></nav>'''
IDENTITY = '<div class="stitch-page-identity" data-current-page-id="01"><h1>工作台</h1></div>'
GUIDE = '''<section role="dialog" class="first-use-guide"><h2>首次使用引导</h2>
<button aria-label="暂时跳过，暂停并关闭首次使用引导">暂时跳过</button>
<label><input type="checkbox">我已核对这一步（手动记录）</label></section>'''


def shell(content=MENU, *, hidden=False):
    if content == MENU:
        menu, dock = content.split('<nav class="stitch-workspace-dock"', 1)
        inner = menu + '<section class="console-window"><div class="app-shell" data-stitch-workspace>' + IDENTITY + '</div></section>' + '<nav class="stitch-workspace-dock"' + dock
    else:
        inner = '<div class="app-shell" data-stitch-workspace>' + IDENTITY + content + '</div>'
    # Actual App: menu, ConsoleWindow and Dock are siblings; Radix hides their root.
    return '<div id="root"' + (' aria-hidden="true"' if hidden else '') + '>' + inner + '</div>'


class ObservedUI:
    def __init__(self, markup):
        self.markup = markup
        self.clicks = []

    def js(self, script):
        return evaluate(script, self.markup)

    def wait(self, script):
        assert self.js(script), script

    def click_selector(self, selector):
        count = evaluate('return document.evaluate(' + json.dumps(selector) + ',document,null,XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,null).snapshotLength;', self.markup)
        assert count == 1
        self.clicks.append(selector)
        self.markup = self.markup.replace(GUIDE, '').replace(' aria-hidden="true"', '')


def test_first_guide_is_paused_by_one_real_ui_action_without_completion():
    ui, evidence = ObservedUI(shell(hidden=True) + GUIDE), []
    probe.prepare_rendered_navigation(ui, evidence)
    assert len(ui.clicks) == 1 and "暂时跳过" in ui.clicks[0]
    assert evidence[0] == {"action":"first_use_guide_pause", "decision":"PAUSED_BY_RENDERED_UI", "business_completion":False, "guide_steps_marked_complete":False}
    assert evidence[-1]["mode"] == "menu" and evidence[-1]["page"] == "01"
    assert 'localStorage.setItem' not in SOURCE.read_text()
    assert re.search(r'location\.hash\s*=(?!=)', SOURCE.read_text()) is None


def test_startup_uses_the_real_menu_console_dock_sibling_topology():
    markup = shell()
    assert evaluate("return document.querySelector('.app-shell').querySelectorAll('nav').length;", markup) == 0
    assert evaluate("return document.querySelectorAll('#root > nav').length;", markup) == 2
    ui, evidence = ObservedUI(markup + GUIDE), []
    probe.prepare_rendered_navigation(ui, evidence)
    assert len(ui.clicks) == 1 and evidence[-1]['mode'] == 'menu'


def test_returning_user_needs_no_guide_action_but_navigation_is_still_required():
    ui, evidence = ObservedUI(shell()), []
    probe.prepare_rendered_navigation(ui, evidence)
    assert ui.clicks == [] and evidence[0]["decision"] == "NOT_PRESENT"
    with pytest.raises(AssertionError):
        probe.prepare_rendered_navigation(ObservedUI(shell('')), [])


@pytest.mark.parametrize('guide', [GUIDE + GUIDE, GUIDE.replace('>暂时跳过</button>', '>其他</button>'), GUIDE.replace('>首次使用引导</h2>', '>未知对话</h2>')])
def test_ambiguous_or_unrecognized_pause_dialog_is_not_bypassed(guide):
    ui = ObservedUI(shell() + guide)
    with pytest.raises(AssertionError):
        probe.prepare_rendered_navigation(ui, [])
    assert ui.clicks == []


def test_duplicate_menu_pages_resolve_to_one_actual_group_without_hash_navigation():
    observed = evaluate(probe.product_navigation_observation('03'), shell())
    assert observed['mode'] == 'menu' and observed['scope'].endswith('details:nth-of-type(1)')
    selector = observed['scope'] + ' button[data-page-id="03"]'
    assert evaluate('return document.querySelectorAll(' + json.dumps(selector) + ').length;', shell()) == 1
    assert evaluate(probe.product_navigation_observation('22'), shell())['scope'] is None


@pytest.mark.parametrize('content,mode', [('<button aria-label="打开产品导航">全部页面</button>', 'drawer'), ('<nav class="navigation-sidebar"><button data-page-id="03">阅读</button></nav>', 'sidebar')])
def test_legacy_navigation_is_used_only_when_actually_present(content, mode):
    ui, evidence = ObservedUI(shell(content)), []
    probe.prepare_rendered_navigation(ui, evidence)
    assert evidence[-1]['mode'] == mode
    assert evaluate(probe.product_navigation_observation('03'), shell(content, hidden=True))['mode'] is None


def test_main_harness_prepares_navigation_instead_of_waiting_for_removed_exact_trigger():
    source = (ROOT / 'scripts/probes/aaos01_tauri_webdriver_loop.py').read_text()
    tree = ast.parse(source)
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    launch = next(node for node in main.body if isinstance(node, ast.FunctionDef) and node.name == 'launch')
    assert any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'prepare_rendered_navigation' for node in ast.walk(launch))
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'wait' and any(isinstance(arg, ast.Constant) and 'stitch-workspace-menu button[aria-label="打开产品导航"]' in str(arg.value) for arg in node.args) for node in ast.walk(launch))


def harness_helper(name):
    source = (ROOT / 'scripts/probes/aaos01_tauri_webdriver_loop.py').read_text()
    node = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace = {'json': json, 're': re}
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<navigation-helper>', 'exec'), namespace)
    return namespace[name]


@pytest.mark.parametrize('recovery_status', [200, 409])
def test_guide_deferred_by_restore_confirmation_is_paused_only_after_valid_ack(recovery_status):
    """SIMULATED delayed guide; execute the actual journal fence and pause helper."""
    restore_dialog = '<section role="dialog"><button>保留恢复候选</button></section>'
    ui = ObservedUI('<div class="app-body" aria-busy="false">' + shell() + '</div>' + restore_dialog)
    evidence, events = [], []
    probe.prepare_rendered_navigation(ui, evidence)
    assert evidence[0]['decision'] == 'NOT_PRESENT' and ui.clicks == []
    candidate = {'page_id': '01', 'drafts': {'research': 'SYNTHETIC retained original'}}
    before = dict(schema='archeaxis.ui-working-state/v1', workspace_id='synthetic-workspace',
                  restore_epoch='synthetic-epoch', state_revision=3,
                  recovery_requires_confirmation=True, recovery_candidates=candidate)
    acknowledged = {**before, 'state_revision': 4, 'state': candidate,
                    'recovery_requires_confirmation': False, 'recovery_candidates': None}
    reads = iter([before, acknowledged])

    def bridge(operation):
        assert operation == 'ui_state_read'
        value = next(reads)
        events.append('read-confirmed' if value is acknowledged else 'read-pending')
        return value

    def click(label):
        assert label == '保留恢复候选'
        events.append('preserve')
        # The real guide waits for the other dialog to close before auto-opening.
        ui.markup = ui.markup.replace(restore_dialog, GUIDE)

    def js(script):
        if script == 'return window.__aaosRecoveryReplies':
            return [{'operation': 'ui_state_recover',
                     'value': {'status': recovery_status, 'body': acknowledged}}]

    def prepare():
        assert events == ['read-pending', 'preserve', 'read-confirmed']
        probe.prepare_rendered_navigation(ui, evidence)
        events.append('guide-paused')

    confirm = harness_helper('confirm_restored_working_state')
    if recovery_status != 200:
        with pytest.raises(AssertionError):
            confirm(bridge, click, ui.wait, js, prepare_navigation=prepare)
        assert ui.clicks == [] and GUIDE in ui.markup
        return
    result = confirm(bridge, click, ui.wait, js, prepare_navigation=prepare)
    assert result['decision'] == 'EXPLICIT_UI_PRESERVE'
    assert result['after']['state'] == candidate
    assert events[-1] == 'guide-paused'
    assert len(ui.clicks) == 1 and '暂时跳过' in ui.clicks[0]
    assert evidence[-2]['decision'] == 'PAUSED_BY_RENDERED_UI'
    assert evidence[-2]['guide_steps_marked_complete'] is False
    assert GUIDE not in ui.markup and evidence[-1]['mode'] == 'menu'


def test_rendered_page_helper_uses_current_native_menu_navigation_and_rejects_missing_ui():
    navigate = harness_helper('navigate_rendered_product_page')
    actions = []
    class UI:
        def page(self, page, confirm_navigation=False):
            actions.append((page, confirm_navigation))
    ui = UI()
    accept = lambda: None
    navigate(ui, lambda source: evaluate(source, shell()), lambda source: None, '03', accept)
    assert actions == [('03', True)] and ui.accept_navigation_alert is accept
    with pytest.raises(AssertionError, match='No visible product navigation'):
        navigate(ui, lambda source: evaluate(source, shell('')), lambda source: None, '03', accept)


def test_library_object_navigation_recognizes_exact_current_all_pages_label():
    open_scope = harness_helper('library_object_navigation_scope')
    markup, actions = [shell()], []
    def wait(source):
        assert evaluate(source, markup[0])
    def click(label):
        actions.append(label)
        markup[0] += '<section role="dialog" class="ui-navigation-drawer"><ul aria-label="资料库对象导航">' + '<li><button>对象</button></li>' * 4 + '</ul></section>'
    scope = open_scope(lambda source: evaluate(source, markup[0]), wait, click)
    assert actions == ['全部页面']
    assert scope.endswith("//ul[@aria-label='资料库对象导航']")


def binding_fixture():
    build = dict(status='PASS', source_consistent=True, source_commit='a'*40, source_tree='b'*40,
                 source_patch_sha256='f'*64, source_patch_sha256_after='f'*64,
                 host_sha256='1'*64, core_sha256='2'*64, backend_manifest_sha256='3'*64)
    env = dict(ARCHEAXIS_SOURCE_COMMIT='c'*40, ARCHEAXIS_SOURCE_TREE='d'*40, ARCHEAXIS_SOURCE_PATCH_SHA256='f'*64)
    return build, env, {'sha256':'1'*64}, {'sha256':'2'*64}, {'sha256':'3'*64}


def test_compiled_binding_keeps_both_source_identities_and_accepts_exact_probe_only_commit_delta():
    qualify = harness_helper('qualify_candidate_build')
    paths = ['scripts/probes/aaos01_grouped_owner_loop.py', 'scripts/probes/aaos01_tauri_webdriver_loop.py',
             'tests/test_native_navigation_entry.py', 'tests/test_grouped_native_owner_probe.py']
    result = qualify(*binding_fixture(), paths)
    assert result['status'] == 'PASS'
    assert result['build_source']['commit'] == 'a'*40 and result['probe_source']['commit'] == 'c'*40
    assert result['build_source']['patch_sha256'] == result['probe_source']['patch_sha256'] == 'f'*64
    assert result['committed_changed_paths'] == result['allowed_probe_paths'] == sorted(paths)
    assert result['runtime_manifest']['sha256'] == '3'*64


@pytest.mark.parametrize('path', ['frontend/src/app/App.tsx', 'src-tauri/src/main.rs', 'services/python-workers/worker.py', 'docs/current/progress.md', 'tests/unrelated.py'])
def test_compiled_binding_refuses_any_other_committed_path(path):
    with pytest.raises(AssertionError, match='outside exact probe/test allowance'):
        harness_helper('qualify_candidate_build')(*binding_fixture(), [path])


@pytest.mark.parametrize('change', ['dirty', 'host', 'core', 'manifest', 'build-dirty', 'same-commit-tree'])
def test_compiled_binding_never_waives_patch_binary_or_manifest_mismatch(change):
    build, env, host, core, manifest = binding_fixture()
    if change == 'dirty':
        env['ARCHEAXIS_SOURCE_PATCH_SHA256'] = '0'*64
    elif change == 'build-dirty':
        build['source_patch_sha256_after'] = '0'*64
    elif change == 'same-commit-tree':
        env['ARCHEAXIS_SOURCE_COMMIT'] = build['source_commit']
    else:
        {'host': host, 'core': core, 'manifest': manifest}[change]['sha256'] = '0'*64
    with pytest.raises(AssertionError):
        harness_helper('qualify_candidate_build')(build, env, host, core, manifest, [])


def test_same_commit_binding_still_requires_matching_tree_and_unchanged_full_patch():
    build, env, host, core, manifest = binding_fixture()
    env.update(ARCHEAXIS_SOURCE_COMMIT=build['source_commit'], ARCHEAXIS_SOURCE_TREE=build['source_tree'])
    result = harness_helper('qualify_candidate_build')(build, env, host, core, manifest, [])
    assert result['status'] == 'PASS' and result['committed_changed_paths'] == []


def native_close_fixture():
    """SIMULATED Win32 observation; no actual HWND or native acceptance claim."""
    return {"hwnd": 101, "pid": 12, "created": 77, "class": "#32770", "visible": True,
        "owner": 100, "main_windows": [100], "title": "确认退出星环知识系统",
        "text": ["还有未保存的草稿。\n\n选择“是”将放弃尚未保存的页面内容并退出。\n选择“否”返回保存或保留文字。", "是(&Y)", "否(&N)"],
        "default_button_id": 7, "buttons": {
            str(number): {"hwnd": 200 + number, "pid": 12, "class": "Button", "id": number, "is_child": True}
            for number in (6, 7)}}


def test_synthetic_close_prompt_matches_product_and_never_accepts_unresponsive_fallback():
    source = (ROOT / 'src-tauri/src/main.rs').read_text(encoding='utf-8')
    branch = source.split('let message = if unresponsive {', 1)[1].split('};', 1)[0]
    variants = re.findall(r'"(?:\\.|[^"\\])*"', branch)
    assert len(variants) == 2
    fallback, acknowledged = [json.loads(value) for value in variants]
    observed = native_close_fixture()
    assert observed['text'][0] == acknowledged
    validate = harness_helper('validate_owned_close_confirmation')
    validate({'pid': 12, 'created': 77}, observed)
    for rejected in (fallback, '还有未保存的草稿。\n\n选择“是”将放弃未保存的页面内容并退出。\n选择“否”返回并保留全部草稿。'):
        observed['text'][0] = rejected
        with pytest.raises(AssertionError, match='Unknown native confirmation text'):
            validate({'pid': 12, 'created': 77}, observed)


def synthetic_close_controller():
    controller = harness_helper('confirm_synthetic_close')
    clock = Mock()
    elapsed = [0.0]
    clock.monotonic.side_effect = lambda: elapsed[0]
    clock.sleep.side_effect = lambda seconds: elapsed.__setitem__(0, elapsed[0] + seconds)
    controller.__globals__.update(time=clock, validate_owned_close_confirmation=harness_helper('validate_owned_close_confirmation'))
    return controller


@pytest.mark.parametrize('change', ['foreign-pid', 'recycled-pid', 'unknown-title', 'unknown-text',
    'fallback-only', 'default-yes', 'foreign-owner', 'foreign-button', 'wrong-button-id',
    'not-a-button', 'not-a-child', 'hidden-dialog'])
def test_synthetic_restart_never_accepts_an_unknown_or_foreign_native_dialog(change):
    observed = native_close_fixture()
    if change == 'foreign-pid':
        observed['pid'] = 13
    elif change == 'recycled-pid':
        observed['created'] = 78
    elif change == 'unknown-title':
        observed['title'] = 'Unknown application'
    elif change == 'unknown-text':
        observed['text'][0] = 'Approve an unrelated operation'
    elif change == 'fallback-only':
        observed['text'][0] = '编辑器未响应退出检查，可能存在未保存文字。'
    elif change == 'default-yes':
        observed['default_button_id'] = 6
    elif change == 'foreign-owner':
        observed['owner'] = 999
    elif change == 'foreign-button':
        observed['buttons']['6']['pid'] = 13
    elif change == 'wrong-button-id':
        observed['buttons']['6']['id'] = 1
    elif change == 'not-a-button':
        observed['buttons']['6']['class'] = 'Static'
    elif change == 'not-a-child':
        observed['buttons']['6']['is_child'] = False
    else:
        observed['visible'] = False
    choose, record = Mock(), {}
    with pytest.raises(AssertionError):
        synthetic_close_controller()(Mock(pid=12, poll=Mock(return_value=None)),
            {'pid': 12, 'created': 77}, record, 15, lambda: observed, choose)
    choose.assert_not_called()
    assert record['native_confirmation']['posted'] is False


@pytest.mark.parametrize('identity', [None, {}, {'pid': 12}, {'pid': 13, 'created': 77}])
def test_native_confirmation_requires_the_same_owned_launch_before_observation(identity):
    observe, choose = Mock(), Mock()
    with pytest.raises(AssertionError):
        synthetic_close_controller()(Mock(pid=12), identity, {}, 15, observe, choose)
    observe.assert_not_called()
    choose.assert_not_called()


def test_known_synthetic_draft_prompt_records_raw_default_no_before_one_scoped_yes():
    observed, record, choose = native_close_fixture(), {}, Mock(return_value=True)
    remaining = synthetic_close_controller()(Mock(pid=12, poll=Mock(return_value=None)),
        {'pid': 12, 'created': 77}, record, 15, lambda: observed, choose)
    choose.assert_called_once_with(observed)
    assert 0 <= remaining <= 15
    confirmation = record['native_confirmation']
    assert confirmation['observation'] == observed and confirmation['observation']['default_button_id'] == 7
    assert confirmation['chosen_button_id'] == 6 and confirmation['posted'] is True
    assert confirmation['authorization'] == 'EXPLICIT_SYNTHETIC_JOURNEY_ONLY'


def test_normal_synthetic_exit_without_native_prompt_never_posts_a_selection():
    observe, choose, record = Mock(return_value=None), Mock(), {}
    remaining = synthetic_close_controller()(Mock(pid=12, poll=Mock(side_effect=[None, 0])),
        {'pid': 12, 'created': 77}, record, 15, observe, choose)
    observe.assert_called_once_with()
    choose.assert_not_called()
    assert record == {} and 0 < remaining < 15


@pytest.mark.parametrize('rows,exit_code,accepted', [
    ([], 0, True), ([], None, False),
    ([{'pid': 12, 'created': 78}], 0, False),
    ([{'pid': 12, 'created': 78}], None, False),
])
def test_native_snapshot_exit_race_never_authorizes_a_live_or_recycled_process(rows, exit_code, accepted):
    observe = harness_helper('observe_owned_close_confirmation')
    observe.__globals__['native_process_rows'] = lambda: rows
    owned, host = Mock(), Mock(poll=Mock(return_value=exit_code))
    if accepted:
        assert observe(owned, {'pid': 12, 'created': 77}, host) is None
    else:
        with pytest.raises(AssertionError):
            observe(owned, {'pid': 12, 'created': 77}, host)
    assert owned.mock_calls == []


def test_missing_confirmation_uses_up_original_budget_without_automatic_approval():
    choose = Mock()
    remaining = synthetic_close_controller()(Mock(pid=12, poll=Mock(return_value=None)),
        {'pid': 12, 'created': 77}, {}, 15, lambda: None, choose)
    assert remaining == 0
    choose.assert_not_called()


def test_confirmed_exit_ack_still_requires_zero_exit_with_only_remaining_budget():
    import subprocess
    exit_owned = harness_helper('request_owned_product_exit')
    host = Mock(pid=12, poll=Mock(side_effect=[None, 0]), wait=Mock(return_value=0))
    send, confirm = Mock(return_value={'ok': True, 'value': None}), Mock(return_value=11.5)
    receipt = {}
    exit_owned(host, {'pid': 12, 'created': 77}, [{'pid': 12, 'created': 77}], send,
        receipt, confirm_synthetic=confirm)
    send.assert_called_once_with()
    confirm.assert_called_once_with(receipt['requested_product_exits'][0], 15)
    host.wait.assert_called_once_with(timeout=11.5)
    assert receipt['host_shutdowns'][0]['exit_code'] == 0
    host.poll.return_value = None
    host.poll.side_effect = None
    host.wait.side_effect = subprocess.TimeoutExpired('owned', 0)
    with pytest.raises(subprocess.TimeoutExpired):
        exit_owned(host, {'pid': 12, 'created': 77}, [{'pid': 12, 'created': 77}], send,
            {}, confirm_synthetic=lambda record, seconds: 0)
