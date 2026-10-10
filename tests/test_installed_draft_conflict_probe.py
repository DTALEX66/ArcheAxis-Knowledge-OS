"""SIMULATED pure adapter contracts. Does not launch Core/native UI."""
import copy
import hashlib
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "scripts/probes/aaos01_installed_draft_conflict_loop.py"
SPEC = importlib.util.spec_from_file_location("installed_conflict", PATH)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)
SOURCE = {"commit": "56d5ec83", "patch_sha256": "a" * 64}


class SyntheticHttp:
    def __init__(self):
        self.documents = {}
        self.calls = []
        self.backup_state = None
        self.read = {"schema": "archeaxis.ui-working-state/v1", "workspace_id": "owned",
                     "restore_epoch": "before", "state_revision": 0,
                     "state": {"drafts": {}, "opened_documents": [], "active_document": None,
                               "page_id": None, "pending_original": None, "pending_jobs": {}},
                     "draft_digests": {}, "pending_document_id": None,
                     "recovery_requires_confirmation": False, "recovery_candidates": None}

    def __call__(self, method, path, body, expected):
        self.calls.append((method, path, copy.deepcopy(body), expected))
        if method == "GET" and path == "/api/v1/documents":
            return {"documents": list(self.documents.values()), "next_cursor": None}
        if path == probe.ROUTE:
            if method == "PUT":
                assert probe.basis(self.read) == {key: body[key] for key in probe.basis(self.read)}
                self.read["state"] = copy.deepcopy(body["state"])
                self.read["state_revision"] += 1
                self.read["draft_digests"] = {key: "b" * 64 for key in body["state"]["drafts"]}
            return copy.deepcopy(self.read)
        if method == "POST" and path == "/api/v1/documents":
            identity = "doc" + str(len(self.documents))
            doc = {"document_id": identity, "version": 1, "source_id": None,
                   "title": body["title"], "editor_json": copy.deepcopy(body["editor_json"]),
                   "content_sha256": hashlib.sha256(repr(body["editor_json"]).encode()).hexdigest()}
            self.documents[identity] = doc
            return copy.deepcopy(doc)
        if path.endswith("/draft"):
            identity = path.split("/")[-2]
            doc = self.documents[identity]
            assert body["expected_version"] == doc["version"]
            doc["version"] += 1
            doc["editor_json"] = copy.deepcopy(body["editor_json"])
            doc["content_sha256"] = "c" * 64
            return copy.deepcopy(doc)
        if path == "/api/v1/workspace/backups":
            self.backup_state = copy.deepcopy(self.read["state"])
            return {"backup_id": "d" * 32, "filename": "d" * 32 + ".sqlite", "sha256": "e" * 64}
        return copy.deepcopy(self.documents[path.split("/")[-1]])


def initialized():
    transport = SyntheticHttp()
    fixture = probe.initialize_fixture(transport, owned_fresh_workspace=True, source_identity=SOURCE)
    return transport, fixture


def test_initializer_backup_before_explicit_cas_discard_and_retains_optional_fields():
    transport, fixture = initialized()
    assert fixture["installed_ui"] == "NOT_EXECUTED"
    assert fixture["initialization"] == "SYNTHETIC_INITIALIZATION"
    assert transport.backup_state == fixture["journal_backup_state"]
    assert len(transport.backup_state["drafts"]) == 2
    assert transport.read["state"]["drafts"] == {}
    assert "pending_jobs" in fixture["clean_state"]
    assert fixture["current_a"]["version"] == 2
    assert fixture["drafts"][fixture["documents"]["A"]["document_id"]]["base_version"] == 1
    assert [call[0] for call in transport.calls if call[1] == probe.ROUTE] == ["GET", "PUT", "PUT", "GET"]


def test_existing_workspace_refused_before_mutation():
    transport = SyntheticHttp()
    transport.documents["private"] = {"document_id": "private"}
    with pytest.raises(AssertionError):
        probe.initialize_fixture(transport, owned_fresh_workspace=True, source_identity=SOURCE)
    assert all(call[0] == "GET" for call in transport.calls)


def test_live_discard_cas_refusal_is_not_bypassed():
    transport = SyntheticHttp()
    original = transport.__call__
    writes = []
    def refused(method, path, body, expected):
        if method == "PUT" and path == probe.ROUTE:
            writes.append(body)
            if len(writes) == 2:
                raise AssertionError("actual Core CAS rejection")
        return original(method, path, body, expected)
    with pytest.raises(AssertionError, match="CAS rejection"):
        probe.initialize_fixture(refused, owned_fresh_workspace=True, source_identity=SOURCE)
    assert len(writes) == 2 and len(transport.read["state"]["drafts"]) == 2


@pytest.mark.parametrize("field,value", [("workspace_id", "other"), ("restore_epoch", "wrong"),
    ("draft_digests", {}), ("recovery_requires_confirmation", True)])
def test_journal_identity_or_digest_mismatch_rejected(field, value):
    transport, fixture = initialized()
    read = copy.deepcopy(transport.read)
    read["state"]["drafts"] = fixture["drafts"]
    read["draft_digests"] = {key: "f" * 64 for key in fixture["drafts"]}
    read[field] = value
    with pytest.raises(AssertionError):
        probe.assert_journal(read, fixture["drafts"], "owned", "before")


@pytest.mark.parametrize("field,value", [("version", 4), ("document_id", "different"),
    ("source_id", "different-source"), ("editor_json", probe.editor("wrong", "owned-conflict-A"))])
def test_save_readback_wrong_identity_version_or_body_rejected(field, value):
    _, fixture = initialized()
    original = fixture["documents"]["A"]
    body = fixture["drafts"][original["document_id"]]["editor_json"]
    actual = {**original, "version": 3, "editor_json": body}
    actual[field] = value
    with pytest.raises(AssertionError):
        probe.assert_document(actual, original, 3, body)


def test_ui_bridge_rejects_all_mutations_before_transport():
    calls = []
    read = probe.readonly(lambda *args: calls.append(args))
    for operation in ("document_draft", "ui_state_write", "ui_state_recover", "workspace_backup"):
        with pytest.raises(AssertionError, match="forbids"):
            read(operation, {})
    assert calls == []


def test_installed_source_drift_rejected_before_any_ui_action():
    _, fixture = initialized()
    with pytest.raises(AssertionError, match="baseline drift"):
        probe.run_ui(fixture, ui=None, bridge=None, js=None, wait=None, navigate=None,
            accept_navigation_alert=None, restart=None, screenshot=None,
            host_identity={"installed": True, "source": {"commit": "other"}}, verify_source=None)


@pytest.mark.parametrize("field,value", [("normal_exit", False), ("exit_code", 1),
    ("new_pid", 11), ("new_session", "old"), ("new_portable_root", "other")])
def test_restart_requires_normal_full_exit_fresh_session_same_owned_root(field, value):
    receipt = {"normal_exit": True, "exit_code": 0, "old_pid": 11, "new_pid": 12,
               "old_session": "old", "new_session": "new",
               "old_portable_root": "owned-data", "new_portable_root": "owned-data"}
    probe.assert_restart(receipt)
    receipt[field] = value
    with pytest.raises(AssertionError):
        probe.assert_restart(receipt)


def test_simulated_ui_adapter_preserves_B_and_separates_fixture_from_real_UI_evidence(monkeypatch):
    transport, fixture = initialized()
    observed = copy.deepcopy(transport.read)
    docs = copy.deepcopy(transport.documents)
    a, b = (fixture['documents'][key] for key in ('A', 'B'))
    actions = []
    comparisons = {'原基准': a['editor_json'], '当前已保存': fixture['current_a']['editor_json'],
                   '我的草稿': fixture['drafts'][a['document_id']]['editor_json']}
    class Controls:
        def click(self, label, scope=''):
            actions.append(('trusted_click_contract', label, scope))
            if label == '确认恢复整个工作区':
                observed.update(restore_epoch='restored', recovery_requires_confirmation=True,
                    recovery_candidates=copy.deepcopy(fixture['journal_backup_state']))
            if label == '保留恢复候选':
                observed.update(state=copy.deepcopy(observed['recovery_candidates']),
                    recovery_requires_confirmation=False, recovery_candidates=None,
                    draft_digests={key:'f'*64 for key in fixture['drafts']})
            if label == '明确保留本稿并按已比较版本保存':
                docs[a['document_id']] = {**docs[a['document_id']], 'version':3,
                    'editor_json':copy.deepcopy(comparisons['我的草稿'])}
                del observed['state']['drafts'][a['document_id']]
                del observed['draft_digests'][a['document_id']]
        def click_selector(self, selector, using):
            actions.append(('trusted_element_contract', selector, using))
    def bridge(operation, payload):
        actions.append(('readonly_bridge', operation))
        if operation == 'ui_state_read': return copy.deepcopy(observed)
        if operation == 'workspace_backups': return {'backups':[fixture['backup']]}
        if operation == 'document_get': return copy.deepcopy(docs[payload['document_id']])
        if operation == 'document_version':
            return copy.deepcopy({1:a,2:fixture['current_a'],3:docs[a['document_id']]}[payload['version']])
        raise AssertionError(operation)
    def js(script):
        import json
        if '.textContent' in script and 'details pre' in script:
            return json.dumps(next(value for label,value in comparisons.items() if label in json.loads(script.split("document.querySelector(",1)[1].rsplit(").textContent",1)[0])))
        return fixture['drafts'][b['document_id']]['editor_json']['content'][0]['content'][0]['text']
    def restart():
        actions.append(('normal_restart_contract',))
        return {'normal_exit':True,'exit_code':0,'old_pid':11,'new_pid':12,
                'old_session':'old','new_session':'new','old_portable_root':'owned','new_portable_root':'owned'}
    def poll_once(read, operation, payload, predicate):
        value=read(operation,payload)
        assert predicate(value)
        return value
    monkeypatch.setattr(probe,'poll',poll_once)
    report=probe.run_ui(fixture, ui=Controls(), bridge=bridge, js=js,
        wait=lambda script: actions.append(('observation_only_wait', script)),
        navigate=lambda page: actions.append(('trusted_sidebar_alert_contract',page)),
        accept_navigation_alert=lambda: actions.append(('native_alert_contract',)),
        restart=restart, screenshot=lambda name: actions.append(('screenshot',name)),
        host_identity={'installed':True,'source':SOURCE}, verify_source=lambda:SOURCE)
    # This is a SIMULATED adapter test, never an actual installed receipt.
    assert report['saved_a']['version']==3 and report['remaining_b']=={b['document_id']:fixture['drafts'][b['document_id']]}
    assert report['owner_acceptance']=='NOT_EXECUTED'
    labels=[action[1] for action in actions if action[0]=='trusted_click_contract']
    assert labels.index('保留恢复候选') < labels.index('保存草稿') < labels.index('读取当前版本并比较（保留草稿）')
    assert labels.count('明确保留本稿并按已比较版本保存')==1
    assert all(action[1] in probe.READS for action in actions if action[0]=='readonly_bridge')
    assert docs[b['document_id']]==b
