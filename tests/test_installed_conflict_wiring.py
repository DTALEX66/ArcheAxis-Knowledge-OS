"""Pure installed wiring contracts; no native/loopback process execution."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / 'scripts/probes/aaos01_tauri_webdriver_loop.py'
TREE = ast.parse(HARNESS.read_text(encoding='utf-8-sig'))
NAMES = {'WebDriverProtocolError','accept_native_alert','validate_conflict_branch','navigate_rendered_product_page'}
NAMESPACE = {'json': __import__('json'), 're': __import__('re')}
exec(compile(ast.Module(body=[node for node in TREE.body if getattr(node,'name',None) in NAMES],type_ignores=[]),str(HARNESS),'exec'),NAMESPACE)


def flags(**updates):
    values=dict(installed_draft_conflict_loop=True,installer=Path('owned.exe'),
        grouped_common_owner_loop=False,synthetic_course_loop=False,
        synthetic_template_pagination=False,grouped_run_ai=False,grouped_authored_intervention=False)
    return SimpleNamespace(**{**values,**updates})


@pytest.mark.parametrize('mode', ['drawer', 'sidebar'])
def test_conflict_navigation_uses_rendered_page_and_visible_controls(mode):
    clicks=[]; waits=[]; alerts=[]
    ui=SimpleNamespace(click_selector=lambda selector,using:clicks.append((selector,using)))
    NAMESPACE['navigate_rendered_product_page'](
        ui, lambda script: {'page':'19','mode':mode}, waits.append, '02', lambda:alerts.append(True))
    expected=('.ui-navigation-drawer' if mode=='drawer' else '.navigation-sidebar')+' button[data-page-id="02"]'
    assert clicks[-1]==(expected,'css selector')
    assert len(clicks)==(2 if mode=='drawer' else 1)
    assert alerts==[True]
    assert len(waits)==2 and 'data-current-page-id' in waits[-1] and '"02"' in waits[-1]
    assert 'getClientRects' in waits[0] and '[inert]' in waits[0] and 'visibility' in waits[0]
    assert all('location.hash' not in script for script in waits)


def test_restored_current_page_never_clicks_hidden_sidebar_even_without_hash():
    def forbidden(*args): raise AssertionError('Current rendered page must not navigate')
    NAMESPACE['navigate_rendered_product_page'](
        SimpleNamespace(click_selector=forbidden),lambda script:{'page':'19','mode':None},forbidden,'19',forbidden)


def test_unavailable_navigation_fails_without_hidden_click_or_hash_mutation():
    def forbidden(*args): raise AssertionError('Hidden controls must not be clicked')
    with pytest.raises(AssertionError,match='visible product navigation'):
        NAMESPACE['navigate_rendered_product_page'](
            SimpleNamespace(click_selector=forbidden),lambda script:{'page':'19','mode':None},forbidden,'02',forbidden)


def test_navigation_error_is_not_silently_replayed():
    calls=[]
    def click(*args):
        calls.append(args)
        raise OSError('unknown click result')
    with pytest.raises(OSError,match='unknown click result'):
        NAMESPACE['navigate_rendered_product_page'](
            SimpleNamespace(click_selector=click),lambda script:{'page':'19','mode':'sidebar'},lambda _:None,'02',lambda:None)
    assert len(calls)==1


def test_independent_installed_branch_accepts_only_its_own_fixture():
    NAMESPACE['validate_conflict_branch'](flags())


@pytest.mark.parametrize('field',['grouped_common_owner_loop','synthetic_course_loop',
    'synthetic_template_pagination','grouped_run_ai','grouped_authored_intervention'])
def test_mixed_qualification_refused(field):
    with pytest.raises(AssertionError,match='mix'):
        NAMESPACE['validate_conflict_branch'](flags(**{field:True}))


def test_without_parent_installer_identity_refused():
    with pytest.raises(AssertionError,match='installer'):
        NAMESPACE['validate_conflict_branch'](flags(installer=None))


def test_actual_alert_get_then_accept_recorded():
    calls=[];evidence=[]
    def request(method,path,body=None):
        calls.append((method,path,body))
        return '有未保存内容，是否离开？' if method=='GET' else None
    NAMESPACE['accept_native_alert'](request,'actual-session',evidence)
    assert calls==[('GET','/session/actual-session/alert/text',None),
                   ('POST','/session/actual-session/alert/accept',{})]
    assert evidence==[{'action':'trusted_native_alert_accept','text':'有未保存内容，是否离开？'}]


def test_only_exact_no_such_alert_is_optional():
    evidence=[]
    def absent(*args):
        raise NAMESPACE['WebDriverProtocolError']({'error':'no such alert'})
    NAMESPACE['accept_native_alert'](absent,'session',evidence)
    assert evidence==[{'action':'native_alert_absent','error':'no such alert'}]


@pytest.mark.parametrize('code',['invalid session id','unexpected alert open','unknown error','no such window'])
def test_other_protocol_failures_propagate(code):
    def failure(*args): raise NAMESPACE['WebDriverProtocolError']({'error':code})
    with pytest.raises(NAMESPACE['WebDriverProtocolError']):
        NAMESPACE['accept_native_alert'](failure,'session',[])


def test_transport_failure_not_swallowed():
    def failure(*args): raise OSError('refused')
    with pytest.raises(OSError): NAMESPACE['accept_native_alert'](failure,'session',[])


def test_initializer_correct_db_before_host_and_mandatory_nsis_call():
    # Structural entry checks supplement behavior contracts; not runtime evidence.
    text=HARNESS.read_text(encoding='utf-8-sig')
    assert 'workspace_name="archeaxis.sqlite"' in text
    assert 'EXISTING_OWNED_LAUNCHER_TERMINATE_REAP' in text
    assert 'assert init_child.poll() is not None' in text
    assert text.index('fixture = conflict.initialize_fixture') < text.index('        launch()\n        if args.installed_draft_conflict_loop:')
    script=(ROOT/'desktop/scripts/verify_nsis_install.ps1').read_text(encoding='utf-8-sig')
    assert '--installed-draft-conflict-loop' in script
    assert 'actual installed document conflict recovery journey failed' in script
    assert 'installed_document_conflict_loop' in script
    assert '--grouped-common-owner-loop' in script


@pytest.mark.parametrize('flags', [[], ['--grouped-common-owner-loop'],
                                  ['--actual-model'], ['--grouped-authored-intervention'],
                                  ['--grouped-common-owner-loop', '--actual-model']])
def test_required_ai_rejects_missing_opt_ins_before_any_host_launch(flags):
    import subprocess
    import sys
    result = subprocess.run([sys.executable, str(HARNESS), '--host', 'NOT_A_REAL_HOST',
                             '--require-actual-ai-loop', *flags], capture_output=True, text=True)
    assert result.returncode == 2
    assert 'required actual AI loop requires' in result.stderr
    assert 'Traceback' not in result.stderr
