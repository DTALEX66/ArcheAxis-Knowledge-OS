"""Actual Chromium fixture + AST guards; no installed Host/Core qualification."""
import ast
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from playwright.sync_api import sync_playwright
from scripts import a0_browser_smoke

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'scripts/probes/aaos01_tauri_webdriver_loop.py'
TREE = ast.parse(SOURCE.read_text(encoding='utf-8'))
NAMES = {'NATIVE_FRONTEND_OBSERVATION_JS', 'wait_for_native_frontend'}
NODES = [n for n in TREE.body if (isinstance(n, ast.FunctionDef) and n.name in NAMES)
         or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in NAMES for t in n.targets))]


def helper(clock=time):
    scope = {'time': clock}
    exec(compile(ast.Module(body=NODES, type_ignores=[]), str(SOURCE), 'exec'), scope)
    return scope['wait_for_native_frontend'], scope['NATIVE_FRONTEND_OBSERVATION_JS']


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as playwright:
        options = {'headless': True}
        if sys.platform == 'win32':
            executable = a0_browser_smoke._declared_tool('ext.toolchains.playwright-chromium', 'playwright-chromium')
            assert executable, 'Use declared Chromium; never install implicitly'
            options['executable_path'] = executable
        instance = playwright.chromium.launch(**options)
        yield instance
        instance.close()


@pytest.mark.parametrize('setup', [
    '',
    "window.__TAURI__={core:{invoke(){window.businessCalls++}}}",
    "document.body.innerHTML='<div class=app-shell data-stitch-workspace></div>'",
    "document.body.innerHTML='<div class=app-shell data-stitch-workspace></div>';window.__TAURI__={core:{invoke:true}}",
    "document.body.innerHTML='<div class=app-shell data-stitch-workspace></div>';window.__TAURI__={core:{invoke(){window.businessCalls++}}};Object.defineProperty(document,'readyState',{value:'loading'})",
])
def test_real_browser_rejects_incomplete_frontend_without_any_invocation(browser, setup):
    page = browser.new_page()
    try:
        page.goto('about:blank')
        page.evaluate('window.businessCalls=0;' + setup)
        wait, _ = helper()
        attempt = {}
        with pytest.raises(TimeoutError, match='startup readiness'):
            wait(lambda script: page.evaluate('()=>{' + script + '}'), attempt, timeout=.2)
        assert attempt['frontend_readiness']['status'] == 'TIMEOUT'
        assert set(attempt['frontend_readiness']['last_observation']) == {'url','document_state','bridge_ready','root_ready'}
        assert page.evaluate('window.businessCalls') == 0
    finally:
        page.close()


def test_real_browser_waits_for_delayed_mount_and_keeps_recovery_fence(browser):
    page = browser.new_page()
    try:
        page.set_content('<div class="app-body" aria-busy="true"></div>')
        page.evaluate('''window.businessCalls=0;
setTimeout(()=>{window.__TAURI__={core:{invoke(){window.businessCalls++}}}},30);
setTimeout(()=>{document.querySelector('.app-body').innerHTML='<div class="app-shell" data-stitch-workspace></div><section role="dialog">保留恢复候选</section>'},80);''')
        wait, _ = helper()
        observations, attempt = [], {}
        def observe(script):
            value = page.evaluate('()=>{' + script + '}')
            observations.append(value)
            return value
        result = wait(observe, attempt, timeout=2)
        assert result['bridge_ready'] and result['root_ready']
        assert any(not row['root_ready'] for row in observations)
        assert attempt['frontend_readiness']['status'] == 'PASS'
        assert page.get_by_role('dialog').inner_text() == '保留恢复候选'
        assert page.locator('.app-body').get_attribute('aria-busy') == 'true'
        assert page.evaluate('window.businessCalls') == 0
    finally:
        page.close()


def test_transport_failure_is_not_retried_or_converted_to_ready():
    wait, _ = helper()
    js = Mock(side_effect=RuntimeError('explicit transport refusal'))
    attempt = {}
    with pytest.raises(RuntimeError, match='transport refusal'):
        wait(js, attempt)
    assert js.call_count == 1
    assert attempt['frontend_readiness']['status'] == 'ERROR'


def test_actual_browser_observation_excludes_query_fragment_and_body(browser):
    page = browser.new_page()
    try:
        page.route('http://readyguard.invalid/**', lambda route: route.fulfill(body='<p>SYNTHETIC body that must not be recorded</p>'))
        page.goto('http://readyguard.invalid/start?token=SYNTHETIC#private')
        _, script = helper()
        observed = page.evaluate('()=>{' + script + '}')
        assert observed == {'url':'http://readyguard.invalid/start','document_state':'complete',
                            'bridge_ready':False,'root_ready':False}
    finally:
        page.close()


@pytest.mark.parametrize('scheme', ['data', 'file', 'about'])
def test_actual_browser_observation_redacts_nonproduct_scheme_bodies_and_paths(browser, tmp_path, scheme):
    page = browser.new_page()
    try:
        if scheme == 'file':
            fixture = tmp_path / 'SYNTHETIC-personal-path.html'
            fixture.write_text('<p>SYNTHETIC private body</p>', encoding='utf-8')
            page.goto(fixture.as_uri())
        elif scheme == 'data':
            page.goto('data:text/html,<p>SYNTHETIC private body</p>#SYNTHETIC-fragment')
        else:
            page.goto('about:blank#SYNTHETIC-fragment')
        _, script = helper()
        observed = page.evaluate('()=>{' + script + '}')
        assert observed == {'url':'about:blank' if scheme == 'about' else scheme+':',
                            'document_state':'complete','bridge_ready':False,'root_ready':False}
        assert 'SYNTHETIC' not in str(observed)
    finally:
        page.close()


def test_deadline_is_bounded_and_leaves_last_observed_facts():
    now = [0.0]
    sleeps = []
    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds
    wait, _ = helper(SimpleNamespace(monotonic=lambda: now[0], sleep=sleep))
    js = Mock(return_value={'url':'about://blank','bridge_ready':False,'root_ready':False,'document_state':'complete'})
    attempt = {}
    with pytest.raises(TimeoutError):
        wait(js, attempt, timeout=.3)
    assert now[0] == pytest.approx(.3)
    assert max(sleeps) <= .15
    assert js.call_count == 3
    assert attempt['frontend_readiness']['last_observation']['bridge_ready'] is False


def test_all_launches_wait_before_any_recovery_or_navigation():
    main = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    launch = next(n for n in main.body if isinstance(n, ast.FunctionDef) and n.name == 'launch')
    guard = next(i for i,n in enumerate(launch.body) if isinstance(n, ast.Expr)
                 and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)
                 and n.value.func.id == 'wait_for_native_frontend')
    navigation = next(i for i,n in enumerate(launch.body) if isinstance(n, ast.Assign)
                      and any(isinstance(t,ast.Name) and t.id=='launch_navigation' for t in n.targets))
    assert guard < navigation
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                   and n.func.id in {'bridge','native_command','bridge_status'}
                   for node in launch.body[:guard] for n in ast.walk(node))
    helper_node = next(n for n in NODES if isinstance(n,ast.FunctionDef))
    assert {n.func.id for n in ast.walk(helper_node) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)} <= {'js','TimeoutError','min'}
