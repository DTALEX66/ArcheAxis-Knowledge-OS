"""Pure installed wiring contracts; no native/loopback process execution."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / 'scripts/probes/aaos01_tauri_webdriver_loop.py'
TREE = ast.parse(HARNESS.read_text(encoding='utf-8-sig'))
NAMES = {'WebDriverProtocolError','accept_native_alert','validate_conflict_branch'}
NAMESPACE = {}
exec(compile(ast.Module(body=[node for node in TREE.body if getattr(node,'name',None) in NAMES],type_ignores=[]),str(HARNESS),'exec'),NAMESPACE)


def flags(**updates):
    values=dict(installed_draft_conflict_loop=True,installer=Path('owned.exe'),
        grouped_common_owner_loop=False,synthetic_course_loop=False,
        synthetic_template_pagination=False,grouped_run_ai=False,grouped_authored_intervention=False)
    return SimpleNamespace(**{**values,**updates})


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
