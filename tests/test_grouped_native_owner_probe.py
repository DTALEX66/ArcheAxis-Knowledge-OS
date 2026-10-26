"""SIMULATED probe guard checks. No host, browser, model or business database."""

import ast
import copy
import os
from tests.dom_harness import evaluate, reader_dom
import hashlib
import importlib.util
import json
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(os.environ.get("AAOS_PROBE_TEST_ROOT", str(Path(__file__).resolve().parents[1])))


def load_probe():
    path = ROOT / "scripts/probes/aaos01_grouped_owner_loop.py"
    spec = importlib.util.spec_from_file_location("grouped_native_probe_contract", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GroupedNativeProbeTests(unittest.TestCase):
    def test_restored_original_diagnostic_rejects_wrong_knowledge_body_or_grant(self):
        probe = load_probe()
        grant = {"knowledge_id":"original-k", "purpose":"answer"}
        document = {"document_id":"grant-doc", "version":1, "content_sha256":"a"*64,
                    "editor_json":{"attrs":{"archeaxis_context_grant":grant}}}
        knowledge = {"knowledge_id":"original-k", "body":"original body", "version":"original-k@v1"}
        selection = {"document":document, "grant":grant, "snapshot":probe.grant_snapshot(document), "knowledge":knowledge, "current":True}
        probe.assert_restored_original_selection(selection, document, knowledge)
        for field in ('knowledge_id', 'body'):
            wrong = copy.deepcopy(selection); wrong['knowledge'][field] = 'other'
            with self.assertRaises(AssertionError):
                probe.assert_restored_original_selection(wrong, document, knowledge)
        wrong = copy.deepcopy(selection); wrong['snapshot']['version'] = 2
        with self.assertRaises(AssertionError):
            probe.assert_restored_original_selection(wrong, document, knowledge)

    def test_native_option_click_reveals_select_and_verifies_selection(self):
        probe = load_probe()
        selector = "//select[@id='profile']/option[@value='local']"
        for mode in ('success', 'disabled', 'not_selected', 'wrong_value'):
            commands, reveals, evidence = [], [], []
            def observe(script):
                disabled = ' disabled' if mode == 'disabled' else ''
                selected = bool(commands) and mode != 'not_selected'
                markup = '<select id="profile"' + disabled + '><option value="other">Other</option><option value="local"' + (' selected' if selected else '') + '>Local</option></select>'
                value = evaluate(script, markup)
                if mode == 'wrong_value' and commands:
                    value['parent_value'] = 'other'
                return value
            ui = probe.GroupedUI(observe, lambda _: None, lambda *_: 'option', lambda *args: commands.append(args), evidence)
            with patch.object(ui, 'reveal_selector', lambda value: reveals.append(value)):
                if mode == 'success':
                    ui.click_selector(selector)
                    self.assertEqual(evidence[-1]['action'], 'trusted_native_option_click')
                    self.assertEqual(evidence[-1]['selected_value'], 'local')
                else:
                    with self.assertRaises(AssertionError):
                        ui.click_selector(selector)
                    self.assertFalse(evidence)
            self.assertEqual(reveals, ['(' + selector + ')/ancestor::select[1]'])
            self.assertEqual(commands, [] if mode == 'disabled' else [('option', 'click', {})])

    def test_regular_xpath_button_keeps_pointer_path(self):
        probe = load_probe()
        ui = probe.GroupedUI(lambda _: None, lambda _: None, lambda *_: None, lambda *_: None, [])
        with patch.object(ui, 'click_revealed_selector') as pointer, patch.object(ui, 'click_native_option') as option:
            ui.click_selector("//button[@id='save']")
        pointer.assert_called_once_with("//button[@id='save']")
        option.assert_not_called()

    def test_saved_model_configuration_scope_matches_current_panel_and_rejects_ambiguity(self):
        probe = load_probe()
        panel = '<div class="card"><h2>产品模型与用途绑定</h2><button>读取模型配置</button><p role="status">已读取版本 1</p></div>'
        hidden = '<section hidden>' + panel + '</section>'
        unrelated = '<div><h2>其他配置</h2><p>已读取版本 1</p></div>'
        for markup, expected in [(panel + hidden + unrelated, True), (panel + panel, False),
                                 (hidden + unrelated, False), (panel.replace('已读取版本 1', '读取失败'), False)]:
            with self.subTest(markup=markup):
                self.assertEqual(evaluate(probe.model_configuration_status_observation('已读取版本 1'), markup), expected)
        selector = probe.button_selector('读取模型配置', probe.MODEL_CONFIGURATION_SCOPE)
        script = 'return document.evaluate(' + json.dumps(selector) + ',document,null,XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,null).snapshotLength;'
        self.assertEqual(evaluate(script, panel + hidden + unrelated), 1)

    def test_saved_binding_probe_refuses_existing_configuration_before_ui_writes(self):
        probe = load_probe()
        class UI:
            def __getattr__(self, name):
                raise AssertionError('Existing workspace must not be edited')
        existing = {'revision': 1, 'profiles': {'owned': {}}, 'bindings': []}
        with self.assertRaisesRegex(AssertionError, 'fresh isolated'):
            probe.save_deep_model_binding(UI(), lambda *a: existing, lambda *a: None, {}, 'aaos-deep-27b-mtp')

    def test_model_advanced_disclosure_opens_by_trusted_summary_and_keeps_open_state(self):
        probe = load_probe()
        for initially_open in (False, True):
            state, clicks, evidence = {"open": initially_open}, [], []
            def observe(script):
                panel = '<div><h2>产品模型与用途绑定</h2><details class="model-advanced" ' + ('open' if state["open"] else '') + '><summary>' + probe.MODEL_ADVANCED_SUMMARY + '</summary><fieldset><label>本地服务地址 <input></label></fieldset></details></div>'
                return evaluate(script, '<main data-current-page-id="19"></main>' + panel + '<aside hidden>' + panel + '</aside>')
            def wait(script):
                self.assertTrue(observe(script), "Disclosure must be open before field interaction")
            def click(selector):
                clicks.append(selector)
                self.assertEqual(selector, probe.MODEL_ADVANCED_DETAILS_SCOPE + '/summary')
                state["open"] = True
            ui = probe.GroupedUI(observe, wait, lambda *_: "node", lambda *_: None, evidence)
            with patch.object(ui, 'click_revealed_selector', click):
                ui.open_model_advanced_configuration()
            self.assertEqual(len(clicks), 0 if initially_open else 1)
            self.assertEqual(evidence[-1]['decision'], 'ALREADY_OPEN' if initially_open else 'OPENED_BY_RENDERED_UI')
            self.assertFalse(evidence[-1]['business_completion'])

    def test_model_advanced_disclosure_rejects_wrong_page_missing_hidden_or_ambiguous_controls(self):
        probe = load_probe()
        panel = '<div><h2>产品模型与用途绑定</h2><details class="model-advanced"><summary>' + probe.MODEL_ADVANCED_SUMMARY + '</summary><input></details></div>'
        for page, markup in [('03', panel), ('19', ''), ('19', '<aside hidden>' + panel + '</aside>'),
                             ('19', panel + panel), ('19', panel.replace(probe.MODEL_ADVANCED_SUMMARY, '其他设置')),
                             ('19', panel.replace('<summary>', '<summary hidden>')),
                             ('19', panel.replace('</details>', '</details><details class="model-advanced"><summary>重复</summary></details>'))]:
            with self.subTest(page=page, markup=markup):
                ui = probe.GroupedUI(lambda script: evaluate(script, '<main data-current-page-id="' + page + '"></main>' + markup), lambda _: None, lambda *_: None, lambda *_: None, [])
                with patch.object(ui, 'click_revealed_selector') as click, self.assertRaisesRegex(AssertionError, 'model advanced disclosure'):
                    ui.open_model_advanced_configuration()
                click.assert_not_called()

    def test_model_advanced_disclosure_refuses_click_that_did_not_open_it(self):
        probe = load_probe()
        ui = probe.GroupedUI(lambda _: {"page": "19", "panels": 1, "count": 1, "summary": True, "open": False, "enabled": False}, lambda _: None, lambda *_: None, lambda *_: None, [])
        with patch.object(ui, 'click_revealed_selector') as click, self.assertRaisesRegex(AssertionError, 'did not open'):
            ui.open_model_advanced_configuration()
        click.assert_called_once_with(probe.MODEL_ADVANCED_DETAILS_SCOPE + '/summary')
        self.assertFalse(ui.evidence)

    def test_model_advanced_disclosure_waits_for_enabled_fields_after_load(self):
        probe = load_probe()
        for fieldset in ('<fieldset disabled><input></fieldset>', '', '<fieldset><input></fieldset><fieldset></fieldset>'):
            markup = '<main data-current-page-id="19"></main><div><h2>产品模型与用途绑定</h2><details class="model-advanced" open><summary>' + probe.MODEL_ADVANCED_SUMMARY + '</summary>' + fieldset + '</details></div>'
            ui = probe.GroupedUI(lambda script: evaluate(script, markup), lambda _: None, lambda *_: None, lambda *_: None, [])
            with self.subTest(fieldset=fieldset), patch.object(ui, 'click_revealed_selector') as click, self.assertRaisesRegex(AssertionError, 'editable fields'):
                ui.open_model_advanced_configuration()
            click.assert_not_called()
            self.assertFalse(ui.evidence)

    def test_saved_binding_waits_for_load_and_opens_advanced_before_all_fields_and_bindings(self):
        probe = load_probe()
        actions, state = [], {"loaded": False, "open": False, "saved": False}
        before = {"revision": 0, "profiles": {}, "bindings": [], "workspace_id": "isolated", "restore_epoch": "initial"}
        profile = {"endpoint": "http://127.0.0.1:1234/v1", "protocol": "openai", "model": "authorized-model", "credential_ref": None, "max_tokens": 4096, "timeout_s": 120}
        purposes = ("answer", "retest", "material", "companion")
        after = {**before, "revision": 1, "profiles": {"local": profile}, "bindings": [{"purpose": purpose, "lane": "deep", "profile_id": "local"} for purpose in purposes]}
        class UI:
            def page(self, page):
                assert page == '19'
            def click_revealed(self, label, scope):
                if label == '读取模型配置':
                    state['loaded'] = True
                else:
                    assert state['open'], 'Advanced action attempted while collapsed'
                if label == '保存配置与用途绑定':
                    state['saved'] = True
                actions.append(label)
            def open_model_advanced_configuration(self):
                assert state['loaded'] and actions[-1] == 'wait_loaded'
                state['open'] = True
                actions.append('advanced_open')
            def type(self, label, value, **_):
                assert state['open'], 'Hidden advanced field must not be typed'
                actions.append(label)
            def reveal_selector(self, selector):
                assert state['open']
                actions.append(selector)
            def click_selector(self, selector):
                assert state['open']
                actions.append(selector)
        def read(operation, args=None):
            if operation == 'model_configuration_get':
                return after if state['saved'] else before
            if operation == 'machine_tasks_list':
                return {"items": [], "next_cursor": None}
            assert operation == 'model_configuration_resolve' and state['saved']
            return {"purpose": args['body']['purpose'], "lane": "deep", "profile_id": "local", "profile": profile, "configuration_revision": 1, "workspace_id": "isolated", "restore_epoch": "initial"}
        def wait(script):
            if script == probe.model_configuration_status_observation('已读取版本 0'):
                actions.append('wait_loaded')
        stage = {}
        probe.save_deep_model_binding(UI(), read, wait, stage, 'authorized-model', purposes, budget=4096)
        self.assertLess(actions.index('advanced_open'), actions.index('本地服务地址'))
        self.assertEqual(stage['saved_deep_binding']['configuration'], after)
        self.assertEqual(stage['saved_deep_binding']['configuration_inference_calls'], 0)
        for purpose in purposes:
            self.assertTrue(any(purpose + " / DEEP" in action for action in actions))

    def test_saved_binding_receipt_rejects_stale_purpose_profile_epoch_or_budget(self):
        probe = load_probe()
        resolved = {'schema': 'archeaxis.resolved-model/v1', 'configuration_revision': 1,
                    'configuration_sha256': 'a'*64, 'workspace_id': 'w', 'restore_epoch': 'initial',
                    'purpose': 'answer', 'lane': 'deep', 'profile_id': 'local',
                    'profile': {'model': 'aaos-deep-27b-mtp', 'endpoint': 'http://127.0.0.1:1234/v1',
                                'protocol': 'openai', 'max_tokens': 1024, 'timeout_s': 120, 'credential_ref': None}}
        saved = {'resolved': {'answer': resolved}}
        value = {'request': {'model_configuration': resolved, 'resolved_model': resolved,
                            'model': resolved['profile']['model'], 'max_tokens': 1024, 'timeout_s': 120}}
        probe.assert_saved_model_request(value, saved, 'answer')
        for key, wrong in [('purpose', 'retest'), ('configuration_revision', 0), ('restore_epoch', 'old'),
                           ('profile_id', 'other'), ('configuration_sha256', 'b'*64)]:
            bad = copy.deepcopy(value); bad['request']['model_configuration'][key] = wrong
            with self.subTest(key=key), self.assertRaises(AssertionError):
                probe.assert_saved_model_request(bad, saved, 'answer')
        bad = copy.deepcopy(value); bad['request']['max_tokens'] = 2048
        with self.assertRaises(AssertionError): probe.assert_saved_model_request(bad, saved, 'answer')

    def test_saved_binding_budget_accepts_matching_profile_and_rejects_mismatch(self):
        probe = load_probe()
        for purpose in ("answer", "retest"):
            for budget in (1024, 2048, 4096):
                resolved = {"purpose": purpose, "lane": "deep",
                            "profile": {"model": "authorized-model", "max_tokens": budget, "timeout_s": 120}}
                saved = {"resolved": {purpose: copy.deepcopy(resolved)}}
                request = {"model_configuration": copy.deepcopy(resolved), "model": "authorized-model",
                           "max_tokens": budget, "timeout_s": 120}
                value = {"request": request}
                if purpose == "retest":
                    value["execution_request"] = {"resolved_model": copy.deepcopy(resolved)}
                else:
                    request["resolved_model"] = copy.deepcopy(resolved)
                with self.subTest(purpose=purpose, budget=budget):
                    probe.assert_saved_model_request(value, saved, purpose)
                    wrong = copy.deepcopy(value)
                    wrong["request"]["max_tokens"] = 2048 if budget == 1024 else 1024
                    with self.assertRaises(AssertionError):
                        probe.assert_saved_model_request(wrong, saved, purpose)

    def test_saved_binding_rejects_unsupported_probe_budget_before_io(self):
        probe = load_probe()
        def no_io(*args):
            raise RuntimeError("Unexpected product IO")
        for budget in (None, True, 0, 1025, 8192):
            with self.subTest(budget=budget), self.assertRaisesRegex(AssertionError, "Unsupported probe output budget"):
                probe.save_deep_model_binding(None, no_io, no_io, {}, "authorized-model", budget=budget)

    def test_saved_binding_retest_requires_executor_binding_not_only_request_selection(self):
        probe = load_probe()
        resolved = {'purpose':'retest','lane':'deep','profile':{'model':'aaos-deep-27b-mtp','max_tokens':1024,'timeout_s':120}}
        saved = {'resolved':{'retest':resolved}}
        value = {'request':{'model_configuration':resolved,'model':'aaos-deep-27b-mtp','max_tokens':1024,'timeout_s':120},
                 'execution_request':{'resolved_model':resolved}}
        probe.assert_saved_model_request(value, saved, 'retest')
        wrong = copy.deepcopy(value); wrong['execution_request']['resolved_model']['lane'] = 'fast'
        with self.assertRaises(AssertionError): probe.assert_saved_model_request(wrong, saved, 'retest')

    def test_saved_configuration_reopen_allows_only_current_restore_epoch_change(self):
        probe = load_probe()
        saved = {'schema':'archeaxis.model-configuration/v1','revision':1,'profiles':{'local':{'model':'selected'}},
                 'bindings':[{'purpose':'answer','lane':'deep','profile_id':'local'}], 'workspace_id':'w','restore_epoch':'initial'}
        class UI:
            def page(self, *_): pass
            def click_revealed(self, *_): pass
        for restored in (False, True):
            current = {**copy.deepcopy(saved),'restore_epoch':'restored' if restored else 'initial'}
            def read(op, *_): return current if op == 'model_configuration_get' else {'restore_epoch':'restored'}
            stage = {'saved_deep_binding':{'configuration':saved}}
            probe.read_saved_model_configuration(UI(), read, lambda *_:None, stage, restored=restored)
            for field in ('revision','profiles','bindings','workspace_id','restore_epoch'):
                bad = {**current,field:'wrong'}
                def bad_read(op, *_): return bad if op == 'model_configuration_get' else {'restore_epoch':'restored'}
                with self.subTest(restored=restored,field=field), self.assertRaises(AssertionError):
                    probe.read_saved_model_configuration(UI(),bad_read,lambda *_:None,stage,restored=restored)

    def test_restore_refusal_digest_binds_current_saved_model_and_effective_budget(self):
        probe = load_probe()
        document = {'document_id':'d','version':1,'content_sha256':'a'*64,
                    'editor_json':{'attrs':{'archeaxis_context_grant':{'purpose':'p'}}}}
        binding = {'purpose':'answer','lane':'deep','restore_epoch':'restored',
                   'profile':{'model':'aaos-deep-27b-mtp','max_tokens':1024,'timeout_s':120}}
        request = {'operation':'answer','request':{'knowledge_id':'k','question':'q','max_tokens':1024,'timeout_s':120,
                   'context_grant':probe.grant_snapshot(document),'asset_context_grant':None,'client_request_id':'machine_new',
                   'retest_of':None,'model':'aaos-deep-27b-mtp','model_configuration':binding}}
        receipt = {'schema':'archeaxis.context-admission-refusal/v1','reason_code':'RESTORED_GRANT_FENCED',
                   'execution_state':'NOT_EXECUTED','execution_scope':'CURRENT_INVOCATION','prior_request_execution':'UNVERIFIED',
                   'answer_published':False,'operation':'answer','knowledge_id':'k','retest_of':None,
                   'client_request_id':'machine_new','grant':{k:document[k] for k in ('document_id','version','content_sha256')},
                   'request_sha256':hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
        probe.restored_admission_receipt(receipt,document,'k','q',binding)
        for key, value in [('max_tokens',2048),('model','other')]:
            wrong = copy.deepcopy(binding); wrong['profile'][key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError):
                probe.restored_admission_receipt(receipt,document,'k','q',wrong)
        with self.assertRaises(AssertionError): probe.restored_admission_receipt(receipt,document,'k','q')

    def test_inventory_retries_only_reads_and_retains_failure_observations(self):
        probe = load_probe()
        for succeed in (True, False):
            texts = iter(["清单读取未确认；模型数量与可用性未知。"] * 2 +
                         ["清单已读取，共 6 项；声明模型已列出。" if succeed else "清单读取未确认；模型数量与可用性未知。"])
            clicks, proof = [], {}
            class UI:
                def click_revealed(self, label, clicks=clicks):
                    clicks.append(label)
                def js(self, script, texts=texts):
                    return next(texts)
            with self.subTest(succeed=succeed), patch.object(probe.time, "sleep", lambda _: None):
                if succeed:
                    self.assertIn("共 6 项", probe.read_local_model_inventory(UI(), lambda *a, **kw: None, proof, "initial"))
                else:
                    with self.assertRaisesRegex(AssertionError, "remains unverified"):
                        probe.read_local_model_inventory(UI(), lambda *a, **kw: None, proof, "initial")
            self.assertEqual(clicks, ["探测本地模型清单"] * 3)
            self.assertEqual(len(proof["inventory_observations"]), 3)
            self.assertTrue(all(row["inference_retried"] is False for row in proof["inventory_observations"]))

    def test_reveal_observer_scrolls_horizontal_table_but_refuses_hidden_overflow(self):
        probe = load_probe()
        scripts = []
        def js(script):
            scripts.append(script)
            return {"ready": True}
        probe.GroupedUI(js, lambda _: None, lambda *_: "node", lambda *_: None, []).reveal_selector("//button")
        harness = r"""
const nav={parentElement:null,clientLeft:0,clientTop:0,clientWidth:217,clientHeight:400,
 scrollWidth:500,scrollHeight:400,scrollLeft:0,scrollTop:0,
 getBoundingClientRect:()=>({left:322,right:539,top:100,bottom:500})};
const target={parentElement:nav,getBoundingClientRect:()=>({left:640,right:688,top:200,bottom:240,width:48,height:40}),contains:n=>n===target};
nav.contains=n=>n===nav||n===target;
const innerWidth=1000,innerHeight=700;
const document={evaluate:()=>({singleNodeValue:target}),elementFromPoint:x=>x>=322&&x<539?nav:null};
const XPathResult={FIRST_ORDERED_NODE_TYPE:1};
let overflow='auto';const getComputedStyle=()=>({overflowX:overflow,overflowY:'auto'});
const observe=new Function('document','XPathResult','innerWidth','innerHeight','getComputedStyle',SOURCE);
const observeNow=()=>observe(document,XPathResult,innerWidth,innerHeight,getComputedStyle);
const scroll=observeNow();overflow='hidden';const hidden=observeNow();
console.log(JSON.stringify({scroll,hidden}));
""".replace("SOURCE", json.dumps(scripts[0]))
        result = subprocess.run([shutil.which("node") or "node", "-e", harness], capture_output=True, text=True, check=True)
        proof = json.loads(result.stdout)
        self.assertEqual(proof["scroll"]["wheel"]["deltaX"], 240)
        self.assertEqual(proof["scroll"]["wheel"]["deltaY"], 0)
        self.assertNotIn("wheel", proof["hidden"])

    def test_pointer_observer_reads_semantic_page_identity_instead_of_old_title(self):
        probe = load_probe()
        scripts = []
        trace = {"events": [{"type": kind, "phase": "capture", "trusted": True, "targetPage": "06"}
                            for kind in ("pointerdown", "pointerup", "click")],
                 "samples": [{"phase": "click+1000", "hashPage": "06", "renderPage": "06", "currentPages": ["06"]}]}
        def js(script):
            scripts.append(script)
            return trace if script.startswith("return {events:") else None
        ui = probe.GroupedUI(js, lambda _: None, lambda *_: "node", lambda *_: None, [])
        ui.pointer_page("06")
        # Execute the actual observer against the current semantic DOM contract.
        # The obsolete display label deliberately disagrees with the rendered ID.
        harness = """
const button={dataset:{pageId:'06'},getBoundingClientRect:()=>({x:0,y:0,width:40,height:20})};
const root={querySelectorAll:()=>[button]};
const document={querySelector:s=>s==='.stitch-workspace-dock'?root:s==='.ui-page-heading'?{dataset:{currentPageId:'06'}}:s==='.ui-page-heading small'?{textContent:'UI / 20'}:s.includes('button')?button:null};
const location={hash:'#page=06'},window={addEventListener:()=>{},removeEventListener:()=>{}};
eval(OBSERVER);
console.log(JSON.stringify(window.__aaosNavPointerProbe.samples[0]));
""".replace("OBSERVER", json.dumps(scripts[0]))
        result = subprocess.run([shutil.which("node") or "node", "-e", harness], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)["renderPage"], "06")

    def test_revealed_click_is_one_pointer_click_after_hit_testing(self):
        probe = load_probe()
        commands = []
        ui = probe.GroupedUI(lambda _:{"ready":True,"point":{"x":30,"y":40}}, lambda _:None,
            lambda *_:"node", lambda *args:commands.append(args), [])
        ui.click_revealed_selector("//button[@id='target']")
        self.assertEqual(commands, [(None,"pointer_click",{"x":30,"y":40})])

    def test_reveal_uses_bounded_wheel_input_without_clicking_or_mutating_dom(self):
        probe = load_probe()
        commands, evidence = [], []
        values = iter([{"ready":False,"wheel":{"x":30,"y":40,"deltaX":0,"deltaY":240}}, {"ready":True}])
        ui = probe.GroupedUI(lambda _:next(values), lambda _:None, lambda *_:"node",
            lambda *args:commands.append(args), evidence)
        with patch.object(probe.time, "sleep", lambda _:None):
            ui.reveal_selector("//button[@id='target']")
        self.assertEqual(commands, [(None,"wheel",{"x":30,"y":40,"deltaX":0,"deltaY":240})])
        self.assertEqual(evidence[-1]["action"], "target_visible_and_hit_tested")

    def test_reveal_refuses_unreachable_target_and_stops_bounded_scroll(self):
        probe = load_probe()
        for observation, failure, expected_calls in [
            ({"ready":False,"reason":"covered"}, AssertionError, 0),
            ({"ready":False,"wheel":{"x":30,"y":40,"deltaX":0,"deltaY":240}}, TimeoutError, 16),
        ]:
            commands = []
            ui = probe.GroupedUI(lambda _:observation, lambda _:None, lambda *_:"node",
                lambda *args:commands.append(args), [])
            with patch.object(probe.time, "sleep", lambda _:None), self.assertRaises(failure):
                ui.reveal_selector("//button[@id='target']")
            self.assertEqual(len(commands), expected_calls)

    def test_reveal_waits_for_retained_panel_layout_before_trusted_click(self):
        probe = load_probe()
        commands, evidence = [], []
        values = iter([
            {"ready": False, "reason": "No reachable scroll container", "target": {"x": 1043, "y": 679}},
            {"ready": True, "point": {"x": 770, "y": 679}},
            True,
        ])
        ui = probe.GroupedUI(lambda _: next(values), lambda _: None, lambda *_: "node",
            lambda *args: commands.append(args), evidence)
        with patch.object(probe.time, "sleep", lambda _: None):
            ui.click_revealed_selector("//button[@id='restored-document']")
        self.assertEqual(commands, [(None, "pointer_click", {"x": 770, "y": 679})])
        self.assertTrue(any(row["action"] == "wait_for_target_layout" for row in evidence))

    def test_click_rechecks_the_point_instead_of_using_a_stale_coordinate(self):
        probe = load_probe()
        commands = []
        values = iter([
            {"ready": True, "point": {"x": 10, "y": 20}}, False,
            {"ready": True, "point": {"x": 30, "y": 40}}, True,
        ])
        ui = probe.GroupedUI(lambda _: next(values), lambda _: None, lambda *_: "node",
            lambda *args: commands.append(args), [])
        with patch.object(probe.time, "sleep", lambda _: None):
            ui.click_revealed_selector("//button[@id='moving']")
        self.assertEqual(commands, [(None, "pointer_click", {"x": 30, "y": 40})])

    def test_reader_source_tools_opens_current_stitch_disclosure_before_candidate(self):
        probe = load_probe()
        for initially_open in (False, True):
            state, clicks = {"open": initially_open}, []

            def observe(script):
                markup = '<section class="stitch-reader-page" aria-label="阅读与编辑文档视图"><details class="reader-source-tools" ' + ('open' if state["open"] else '') + '><summary>整理关联来源</summary><button>整理此来源为知识候选</button></details></section>'
                markup += '<div hidden><section aria-label="阅读与编辑文档视图"><details class="reader-source-tools"><summary>旧实例</summary></details></section></div>'
                return evaluate(script, markup)

            ui = probe.GroupedUI(observe, lambda _: None, lambda *_: "node", lambda *_: None, [])

            def click(selector):
                clicks.append(selector)
                if selector.endswith("/summary"):
                    state["open"] = True
                else:
                    self.assertTrue(state["open"], "Cannot click a collapsed source tool")

            with patch.object(ui, "click_revealed_selector", click):
                ui.open_reader_source_tools()
            self.assertEqual(len(clicks), 1 if initially_open else 2)
            self.assertIn("整理此来源为知识候选", clicks[-1])

    def test_reader_source_tools_refuses_failed_or_ambiguous_disclosure(self):
        probe = load_probe()
        for values, expected_clicks in [
            ([[{"open": False, "summary": True}], [{"open": False, "summary": True}]], 1),
            ([[{"open": False, "summary": True}] * 2], 0),
            ([[{"open": False, "summary": False}]], 0),
        ]:
            observations, clicks = iter(values), []
            ui = probe.GroupedUI(lambda _: next(observations), lambda _: None, lambda *_: "node", lambda *_: None, [])
            with patch.object(ui, "click_revealed_selector", lambda selector: clicks.append(selector)), self.assertRaises(AssertionError):
                ui.open_reader_source_tools()
            self.assertEqual(len(clicks), expected_clicks)

    def test_page_navigation_uses_current_stitch_menu_without_legacy_drawer(self):
        probe = load_probe()
        clicks, commands = [], []
        scope = 'nav.stitch-workspace-menu[aria-label="应用菜单"] .stitch-menus > details:nth-of-type(1)'
        # SIMULATED rendered menu; actual DOM readiness rejection is tested separately.
        ready = dict(open=True, summaryFocused=True, index=0, targetVisible=True,
            targetEnabled=True, hit=True, blockers=[], contentVisibility="visible",
            opacity="1", runningAnimations=0, ready=True)
        budgets = [30]
        def wait(script, seconds=30):
            if script.startswith("return !!document.querySelector("):
                selector = json.loads(script.removeprefix("return !!document.querySelector(")[:-1])
                self.assertIn(selector, [scope + ' button[data-page-id="03"]', scope + ' > summary'])
                return
            self.assertGreater(seconds, 0)
            self.assertLessEqual(seconds, budgets[-1])
            budgets.append(seconds)
            if script.endswith("})().ready;"):
                self.assertTrue(ready["ready"])
            else:
                self.assertTrue(script.startswith("return location.hash"))
        ui = probe.GroupedUI(lambda script: {"page":"01","mode":"menu","scope":scope,"opened":False} if "const requested=" in script else "#page=01" if script == "return location.hash" else ready if "summaryFocused:" in script else "document.activeElement===n" in script,
            wait, lambda _using, selector: selector, lambda *args: commands.append(args), [])
        with patch.object(ui, "click_selector", lambda *args: clicks.append(args)):
            ui.page("03")
        self.assertEqual(len(clicks), 1)
        self.assertEqual(scope + ' > summary', clicks[0][0])
        self.assertEqual(commands[-1][1:], ("value", {"text": "\ue007"}))
        self.assertIn('.stitch-workspace-menu', commands[-1][0])

    def test_type_replaces_react_controlled_value_instead_of_appending_after_clear(self):
        probe = load_probe()
        expected = "http://127.0.0.1:1234/v1"
        field = {"value": expected, "selected": False}
        commands = []

        def command(element, operation, payload):
            commands.append(operation)
            if operation == "clear":
                # 模拟 React 在 WebDriver clear 后重绘旧受控值。
                field["value"] = expected
            if operation == "value":
                if payload["text"] == "\ue009a\ue000":
                    field["selected"] = True
                else:
                    field["value"] = payload["text"] if field["selected"] else field["value"] + payload["text"]
                    field["selected"] = False

        def wait(script):
            if 'Object.is(n.value,' in script:
                self.assertEqual(field["value"], expected)

        ui = probe.GroupedUI(lambda _: None, wait, lambda *_: "endpoint", command, [])
        ui.type("本地服务地址", expected)
        self.assertEqual(field["value"], expected)
        self.assertNotIn("clear", commands)

    def test_review_navigation_requires_the_exact_retained_unsubmitted_draft(self):
        probe = load_probe()
        pin = dict(item_key="course:c1:artifact:a1", assessment_id="a1", knowledge_version="k1", knowledge_id="k1", source_id="s1", anchor_id="r1")
        draft = {key: pin[key] for key in ("item_key", "assessment_id", "knowledge_version")}
        draft.update(answer="  answer\n", answer_revealed=True, checked_correct=None, rating=None)
        for lose_draft in (False, True):
            state = dict(workspace_id="w1", restore_epoch="e1", recovery_requires_confirmation=False, state=dict(learning_drafts={"a1": draft}, pending_reviews={}))
            actions = []
            class UI:
                def page(self, page_id, confirm_navigation=False):
                    actions.append((page_id, confirm_navigation))
                    if lose_draft:
                        state["state"]["learning_drafts"] = {}
            def read(operation, payload=None):
                return copy.deepcopy({"ui_state_read": state, "assessment_get": pin, "learning_history": {"count": 0, "events": []}}[operation])
            with self.subTest(lose_draft=lose_draft):
                if lose_draft:
                    with self.assertRaises(AssertionError):
                        probe.navigate_retained_review(UI(), read, pin, draft["answer"])
                else:
                    self.assertEqual(probe.navigate_retained_review(UI(), read, pin, draft["answer"])["status"], "PASS")
                self.assertEqual(actions, [("12", True)])

    def test_delayed_navigation_confirmation_never_replays_the_action(self):
        probe = load_probe()
        actions = []
        # SIMULATED ready menu isolates delayed alert handling from DOM rendering.
        ready = dict(open=True, summaryFocused=True, index=0, targetVisible=True,
            targetEnabled=True, hit=True, blockers=[], contentVisibility="visible",
            opacity="1", runningAnimations=0, ready=True)
        budgets = [30]
        class Alert(Exception):
            value = {"error": "unexpected alert open"}
        def wait(script, seconds=30):
            if script.startswith("return !!document.querySelector("):
                selector = json.loads(script.removeprefix("return !!document.querySelector(")[:-1])
                self.assertIn(selector, [scope + ' button[data-page-id="12"]', scope + ' > summary'])
                return
            self.assertGreater(seconds, 0)
            self.assertLessEqual(seconds, budgets[-1])
            budgets.append(seconds)
            if script.endswith("})().ready;"):
                self.assertTrue(ready["ready"])
                return
            self.assertTrue(script.startswith("return location.hash"))
            actions.append("observe")
            if actions.count("observe") == 1:
                raise Alert()
        scope = 'nav.stitch-workspace-menu[aria-label="应用菜单"] .stitch-menus > details:nth-of-type(1)'
        ui = probe.GroupedUI(lambda script: {"page":"11","mode":"menu","scope":scope,"opened":True} if "const requested=" in script else "#page=11" if script == "return location.hash" else ready if "summaryFocused:" in script else True, wait, lambda selector, using: "element", lambda *args: actions.append("activate"), [], lambda: actions.append("confirm"))
        ui.page("12", confirm_navigation=True)
        self.assertEqual(actions, ["activate", "activate", "confirm", "observe", "confirm", "observe"])

    def test_cancel_ui_ack_does_not_imply_a_terminal_or_provider_stop(self):
        probe=load_probe();actions=[]
        class UI:
            def click(self,label): actions.append(label)
            def js(self,source): return "本地 worker 取消请求已接收；尚未确认停止"
        report=probe.request_owned_machine_cancellation(UI(),lambda source:None,{})
        self.assertEqual(actions,["请求取消当前本地 worker"])
        self.assertTrue(report["cancel_requested"])
        self.assertFalse(report["terminal_verified"])
        self.assertEqual(report["provider_stop_state"],"UNKNOWN")
        self.assertEqual(report["execution_state"],"UNKNOWN")

    def test_cancel_terminal_requires_the_separate_audit_ui_observation(self):
        probe=load_probe()
        class UI:
            def click(self,label): self.label=label
            def js(self,source): return "Core 已确认第 1 次尝试的本地 worker 取消审计；可结束请求并保留草稿"
        report=probe.confirm_owned_machine_cancellation(UI(),lambda source:None,{})
        self.assertTrue(report["terminal_verified"])
        self.assertEqual(report["local_worker_terminal"],"CANCELLED_LOCAL_WORKER")
        self.assertEqual(report["provider_stop_state"],"UNKNOWN")

    def test_trusted_pending_review_navigation_confirms_child_without_replaying_input(self):
        probe=load_probe();actions=[]
        # SIMULATED menu readiness keeps the trusted action/confirmation order explicit.
        ready = dict(open=True, summaryFocused=True, index=0, targetVisible=True,
            targetEnabled=True, hit=True, blockers=[], contentVisibility="visible",
            opacity="1", runningAnimations=0, ready=True)
        budgets = [30]
        def wait(source, seconds=30):
            self.assertGreater(seconds, 0)
            self.assertLessEqual(seconds, budgets[-1])
            budgets.append(seconds)
            if source.endswith("})().ready;"):
                self.assertTrue(ready["ready"])
            else:
                self.assertTrue(source.startswith("return location.hash"))
        def js(source):
            return {'page':'19','mode':'menu','scope':'nav.stitch-workspace-menu[aria-label="应用菜单"] .stitch-menus > details:nth-of-type(7)','opened':False} if 'const requested=' in source else '#page=19' if source=='return location.hash' else ready if 'summaryFocused:' in source else 'document.activeElement===n' in source
        ui=probe.GroupedUI(js,wait,lambda *args:'node',lambda *args:actions.append('child'),[],lambda:actions.append('confirm'))
        ui.find=lambda *args:'node'
        ui.click_selector=lambda *args:actions.append('parent')
        ui.page('12',confirm_navigation=True)
        # Disclosure does not navigate or open an alert; Tab then Enter precede confirmation.
        self.assertEqual(actions,['parent','child','child','confirm'])

    def test_machine_ack_qualification_rejects_missing_model_and_unfinished_inference_attempt(self):
        probe=load_probe()
        good={"status":"EXECUTED_CANDIDATE_NOT_EVALUATED","machine_ack_recovery":{"status":"PASS","cold_restart":True,"task_unchanged":True,"recovery_inference_calls":0,"initial":{"faults":1,"rows":[{"operation":"machine_answer","completed":True}]},"recovery":{"rows":[{"operation":"ui_state_clear_machine","completed":True}]}}}
        probe.require_machine_ack_recovery(good)
        for change in ('missing','model','attempt','unfinished'):
            candidate=copy.deepcopy(good)
            if change=='missing':candidate.pop('machine_ack_recovery')
            elif change=='model':candidate['status']='UNVERIFIED'
            elif change=='attempt':candidate['machine_ack_recovery']['recovery']['rows'].append({'operation':'machine_answer','completed':False,'status':None})
            else:candidate['machine_ack_recovery']['initial']['rows'][0]['completed']=False
            with self.subTest(change=change),self.assertRaises(AssertionError):probe.require_machine_ack_recovery(candidate)
    def test_selected_retest_failure_preserves_missing_task_instead_of_keyerror(self):
        probe = load_probe()
        self.assertFalse(probe.selected_retest_binding({"retest": "NOT_EXECUTED"}, "m1"))
        task = {"conditions": json.dumps({"request": {"model": "m1"}, "answer": {"model": "m1", "requested_model": "m1"}})}
        self.assertTrue(probe.selected_retest_binding({"retest_task": task}, "m1"))
        with self.assertRaises(AssertionError):
            probe.selected_retest_binding({"retest_task": task}, "m2")

    def test_metering_keeps_unknown_and_rejects_invented_or_invalid_counts(self):
        probe=load_probe()
        base={"cost":None,"cost_status":"UNKNOWN","usage":None,"usage_status":"UNKNOWN"}
        self.assertEqual(probe.assert_reported_metering(base)["usage"],None)
        self.assertEqual(probe.assert_reported_metering({**base,"usage_status":"REPORTED","usage":{"output_tokens":0}})["usage"],{"output_tokens":0})
        for values in ({"cost":0},{"usage_status":"REPORTED","usage":{}},{"usage_status":"REPORTED","usage":{"input_tokens":True}}):
            with self.assertRaises(AssertionError):probe.assert_reported_metering({**base,**values})
    def test_retest_retry_requires_explicit_503_and_retained_payload(self):
        probe = load_probe()
        observed = {"status": "OBSERVED", "retest_incomplete": True, "same_request_retry": True, "unknown": False, "retest_withheld": False, "retest_refused": False, "failure": {"phase": "invoke", "status": 503, "code": "unavailable"}}
        self.assertTrue(probe.retryable_retest_failure(observed))
        for key, value in (("unknown", True), ("retest_withheld", True), ("retest_refused", True), ("same_request_retry", False), ("failure", {"phase": "invoke", "status": None, "code": "offline"}), ("failure", {"phase": "task_readback", "status": 503, "code": "unavailable"})):
            with self.subTest(key=key, value=value):
                self.assertFalse(probe.retryable_retest_failure({**observed, key: value}))

    def test_pointer_proof_rejects_neighbour_untrusted_and_route_rebound(self):
        probe=load_probe()
        trace={"events":[{"type":kind,"phase":"capture","trusted":True,"targetPage":"06"} for kind in ("pointerdown","pointerup","click")],"samples":[{"phase":"click+1000","hashPage":"06","renderPage":"06","currentPages":["06"]}]}
        probe.assert_pointer_navigation(trace,"06")
        for field,value in (("targetPage","13"),("trusted",False)):
            wrong=copy.deepcopy(trace);wrong["events"][-1][field]=value
            with self.assertRaises(AssertionError):probe.assert_pointer_navigation(wrong,"06")
        wrong=copy.deepcopy(trace);wrong["samples"][0]["renderPage"]="13"
        with self.assertRaises(AssertionError):probe.assert_pointer_navigation(wrong,"06")

    def test_native_click_retries_only_explicit_stale_refusal(self):
        source = (ROOT / "scripts/probes/aaos01_tauri_webdriver_loop.py").read_text(encoding="utf-8")
        nodes = [node for node in ast.parse(source).body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in {"WebDriverProtocolError", "click_current_element"}]
        namespace = {}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "native_click", "exec"), namespace)
        for error, failures, expected in (("stale element reference", 1, 2), ("stale element reference", 3, 3), ("timeout", 1, 1), ("unknown error", 1, 1)):
            with self.subTest(error=error, failures=failures):
                calls = []; finds = []
                def find(*args):
                    finds.append(args)
                    return str(len(finds))
                def request(*args):
                    calls.append(args)
                    if len(calls) <= failures: raise namespace["WebDriverProtocolError"]({"error": error})
                    return "clicked"
                if error == "stale element reference" and failures == 1:
                    self.assertEqual(namespace["click_current_element"](request, find, "session", "selector"), "clicked")
                else:
                    with self.assertRaises(namespace["WebDriverProtocolError"]): namespace["click_current_element"](request, find, "session", "selector")
                self.assertEqual(len(calls), expected)
                self.assertEqual(len(finds), expected)

    def test_ui_original_restart_readback_rejects_changed_bytes(self):
        import base64
        source = (ROOT / "scripts/probes/aaos01_tauri_webdriver_loop.py").read_text(encoding="utf-8")
        node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "ui_original_import_readback")
        namespace = {"base64": base64, "hashlib": hashlib}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "original_readback", "exec"), namespace)
        raw = b"synthetic retained original"
        digest = hashlib.sha256(raw).hexdigest()
        for changed in (False, True):
            with self.subTest(changed=changed):
                proofs = [{"source_id": "source", "sha256": digest, "bytes": len(raw)}]
                def bridge(operation, payload):
                    self.assertEqual(operation, "source_original")
                    self.assertEqual(payload, {"source_id": "source"})
                    return {"sha256": digest, "content_base64": base64.b64encode(raw + (b" changed" if changed else b"")).decode()}
                if changed:
                    with self.assertRaises(AssertionError): namespace[node.name](bridge, proofs)
                    self.assertNotIn("host_restart_original_readback", proofs[0])
                else:
                    namespace[node.name](bridge, proofs)
                    self.assertEqual(proofs[0]["host_restart_original_readback"], "PASS")

    def test_recovery_observer_requires_exact_ack_and_only_scene_followup(self):
        source = (ROOT / "scripts/probes/aaos01_tauri_webdriver_loop.py").read_text(encoding="utf-8")
        node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "confirm_restored_working_state")
        namespace = {}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "recovery_observer", "exec"), namespace)
        run = namespace[node.name]
        candidate = {"drafts": {}, "opened_documents": [], "active_document": None, "page_id": None, "pending_original": None}
        before = {"schema": "archeaxis.ui-working-state/v1", "workspace_id": "workspace", "restore_epoch": "epoch", "state_revision": 4, "state": {}, "recovery_candidates": candidate, "recovery_requires_confirmation": True}
        ack = {**before, "state_revision": 5, "state": candidate, "recovery_candidates": None, "recovery_requires_confirmation": False}
        after = {**ack, "state_revision": 6, "state": {**candidate, "page_id": "01"}}
        for mutation in (None, "ack_revision", "ack_content", "followup_content", "after_identity"):
            with self.subTest(mutation=mutation):
                a, last = copy.deepcopy(ack), copy.deepcopy(after)
                if mutation == "ack_revision": a["state_revision"] = 6
                if mutation == "ack_content": a["state"]["drafts"] = {"lost": {}}
                if mutation == "followup_content": last["state"]["drafts"] = {"unexpected": {}}
                if mutation == "after_identity": last["workspace_id"] = "different"
                observed = [{"operation": "ui_state_recover", "value": {"status": 200, "body": a}}, {"operation": "ui_state_write", "value": {"status": 200, "body": last}}]
                reads = iter([copy.deepcopy(before), last]); actions = []
                def js(script):
                    actions.append(script)
                    return observed if script == "return window.__aaosRecoveryReplies" else None
                invoke = lambda: run(lambda *_: next(reads), actions.append, lambda *_: None, js)
                if mutation is None:
                    self.assertEqual(invoke()["acknowledged"], ack)
                else:
                    with self.assertRaises(AssertionError): invoke()
                self.assertIn("保留恢复候选", actions)
                self.assertTrue(any("delete window.__aaosRecoveryOriginal" in action for action in actions))

    def test_timeout_diagnostic_retains_reason_without_automatic_unknown_retry(self):
        probe = load_probe()

        class UI:
            def js(self, script):
                if "dataset.retestFailure" in script:
                    return json.dumps({"phase": "invoke", "status": 503, "code": "unavailable",
                                       "reason_code": "MODEL_CALL_TIMEOUT", "private_question": "PRIVATE",
                                       "diagnostics": {"elapsed_s": 118.03}})
                return {"panel_present": True, "answer_visible": True, "retest_visible": False,
                        "unknown": True, "retest_incomplete": True, "retest_refused": False,
                        "retest_withheld": False, "same_request_retry": True}

        observed = probe.machine_ui_diagnostic(UI())
        self.assertEqual(observed["failure"], {"phase": "invoke", "status": 503, "code": "unavailable",
                                              "reason_code": "MODEL_CALL_TIMEOUT"})
        self.assertFalse(probe.retryable_retest_failure(observed))
        self.assertNotIn("PRIVATE", json.dumps(observed))
        self.assertNotIn("diagnostics", observed["failure"])

    def test_machine_diagnostic_is_bounded_and_does_not_copy_private_text(self):
        probe = load_probe()
        keys = ("panel_present", "answer_visible", "retest_visible", "unknown",
                "retest_incomplete", "retest_refused", "retest_withheld", "same_request_retry")
        class UI:
            def js(self, script):
                return {**dict.fromkeys(keys, True), "private_question": "must not copy"}
        result = probe.machine_ui_diagnostic(UI())
        self.assertEqual(set(result), {"status", *keys})
        self.assertEqual(result["status"], "OBSERVED")
        class Invalid:
            def js(self, script):
                return {"panel_present": "true"}
        self.assertEqual(probe.machine_ui_diagnostic(Invalid()), {"status": "INVALID_OBSERVATION"})

    def test_frozen_job_journal_binds_all_original_fields_and_refuses_old_restore_epoch(self):
        frozen = {"job_id": "job", "request_id": "request", "body": {"deadline_ms": 60000, "split": False, "words": False}}
        entry = {**frozen, "source_id": "source", "source_revision": "a" * 64, "kind": "text", "surface": "manual", "mode": "single", "relative": None, "origin_restore_epoch": "initial"}
        read = {"schema": "archeaxis.ui-working-state/v1", "restore_epoch": "initial", "recovery_requires_confirmation": False, "state": {"pending_jobs": {"request": entry}}}
        self.assertEqual(self.probe.frozen_job_journal(read, frozen, "source", "a" * 64, "text"), entry)
        for field in ("job_id", "source_id", "source_revision", "kind", "body", "origin_restore_epoch"):
            bad = copy.deepcopy(read)
            bad["state"]["pending_jobs"]["request"][field] = "wrong"
            with self.assertRaises(AssertionError):
                self.probe.frozen_job_journal(bad, frozen, "source", "a" * 64, "text")

    def setUp(self):
        self.probe = load_probe()

    def test_review_requires_new_persisted_bound_answer_and_matching_projection(self):
        pin = {"item_key": "course:one:artifact:two", "assessment_id": "assessment", "knowledge_version": "knowledge"}
        before = {"item_key": pin["item_key"], "count": 0, "events": []}
        event = {"event_id": 7, "kind": "review", "next_review": None,
                 "outcome": json.dumps({"answer": "answer", "assessment_id": "assessment", "outcome": "correct",
                                        "review_evidence": {"knowledge_version": "knowledge"}})}
        after = {"item_key": pin["item_key"], "count": 1, "events": [event]}
        state = {"item_key": pin["item_key"], "learner": {"event_count": 1, "latest_review": {
            "event_id": 7, "kind": "review", "next_review": None, "answer": "answer", "assessment_id": "assessment"}}}
        self.probe.assert_review_readback(before, after, state, pin, " answer ")
        for target, field, value in (("history", "count", 0), ("state", "event_count", 0),
                                     ("latest", "answer", "wrong"), ("latest", "assessment_id", "wrong"),
                                     ("latest", "event_id", 8)):
            bad_history, bad_state = copy.deepcopy(after), copy.deepcopy(state)
            obj = bad_history if target == "history" else bad_state["learner"] if target == "state" else bad_state["learner"]["latest_review"]
            obj[field] = value
            with self.subTest(target=target, field=field), self.assertRaises(AssertionError):
                self.probe.assert_review_readback(before, bad_history, bad_state, pin, "answer")
        with self.assertRaises(AssertionError):
            self.probe.assert_review_readback(after, after, state, pin, "answer")
        for field, value in (("answer", "wrong"), ("assessment_id", "wrong"), ("outcome", "incorrect"),
                             ("review_evidence", {"knowledge_version": "wrong"})):
            bad = copy.deepcopy(after)
            outcome = json.loads(bad["events"][-1]["outcome"])
            outcome[field] = value
            bad["events"][-1]["outcome"] = json.dumps(outcome)
            with self.subTest(outcome=field), self.assertRaises(AssertionError):
                self.probe.assert_review_readback(before, bad, state, pin, "answer")
        prior = {"item_key": pin["item_key"], "count": 1, "events": [{**event, "event_id": 6}]}
        changed = {"item_key": pin["item_key"], "count": 2, "events": [{**event, "event_id": 5}, event]}
        with self.assertRaises(AssertionError):
            self.probe.assert_review_readback(prior, changed, state, pin, "answer")

    def test_mutations_refused(self):
        operations = [
            "source_import",
            "document_create",
            "document_draft",
            "anchor_create",
            "knowledge_from_transform",
            "knowledge_review",
            "course_from_knowledge",
            "learning_reference",
            "assessment_create",
            "learning_review",
            "machine_answer",
            "machine_correction",
            "machine_retest",
            "job_execute",
            "job_enqueue",
            "workspace_backup",
            "ui_state_write",
            "ui_state_recover",
            "capability_set_enabled",
        ]
        for operation in operations:
            with self.subTest(operation=operation):
                calls = []
                read = self.probe.readonly_bridge(
                    lambda op, payload, calls=calls: calls.append((op, payload))
                )
                with self.assertRaisesRegex(ValueError, "forbids bridge mutation"):
                    read(operation, {"body": {}})
                self.assertEqual(calls, [])

    def test_read_identity_preserved(self):
        calls = []
        read = self.probe.readonly_bridge(
            lambda op, payload, calls=calls: (
                calls.append((op, payload)) or {"document_id": payload["document_id"]}
            )
        )
        self.assertEqual(read("document_get", {"document_id": "exact"}), {"document_id": "exact"})
        self.assertEqual(calls, [("document_get", {"document_id": "exact"})])

    def test_assessment_same_object(self):
        pin = {
            "item_key": "course:c:artifact:a",
            "assessment_id": "assessment",
            "knowledge_id": "knowledge",
            "knowledge_version": "knowledge",
            "source_id": "source",
            "anchor_id": "anchor",
        }
        self.probe.assert_assessment(dict(pin), pin)
        for field in pin:
            with self.subTest(field=field), self.assertRaisesRegex(AssertionError, field):
                self.probe.assert_assessment({**pin, field: "another"}, pin)

    def test_learning_queue_selector_uses_identity_with_same_titles_and_hidden_views(self):
        from lxml import etree
        tree = etree.Element("ul", {"aria-label": "复习队列"})
        key = "course:one'quoted\"name:artifact:exact"
        first = etree.SubElement(tree, "button", {"data-learning-item-key": key})
        first.text = "同名学习主题"
        etree.SubElement(tree, "button", {"data-learning-item-key": "other"}).text = first.text
        hidden = etree.SubElement(tree, "li", {"hidden": ""})
        etree.SubElement(hidden, "button", {"data-learning-item-key": key}).text = first.text
        selector = self.probe.button_selector(key, "//ul[@aria-label='复习队列']")
        self.assertEqual(tree.xpath(selector), [first])
        self.assertIn("@data-learning-item-key", selector)

    def test_selectors_quote_and_hidden_boundary(self):
        self.assertTrue(self.probe.xpath_literal("one'quoted\"name").startswith("concat("))
        self.assertIn("ancestor-or-self::*[@hidden]", self.probe.button_selector("保存草稿"))
        self.assertTrue(
            self.probe.label_selector("学习项目键").endswith(
                "/input[not(ancestor-or-self::*[@hidden])]"
            )
        )
        with self.assertRaises(AssertionError):
            self.probe.one(
                [{"id": "same"}, {"id": "same"}], lambda row: row["id"] == "same", "duplicate"
            )

    def test_webdriver_only_interactions(self):
        commands, observations, actions = [], [], []
        ui = self.probe.GroupedUI(
            lambda script: observations.append(script) or {"ready": True, "point": {"x": 30, "y": 40}},
            lambda script, **_: observations.append(script),
            lambda using, selector: "actual-element",
            lambda element, action, body: commands.append((element, action, body)),
            actions,
        )
        ui.click("保存草稿")
        ui.type("知识候选正文", "authored fixture", "textarea")
        ui.keys(self.probe.label_selector("选择实际引文", "textarea"), "\ue009\ue008\ue010\ue000")
        folder = ROOT / ".project-local" / "artifacts" / "unittest-fixture-no-files-written"
        ui.upload_directory(folder)
        self.assertEqual(
            [row[1] for row in commands],
            ["pointer_click", "click", "value", "value", "pointer_click", "value", "value"],
        )
        self.assertIsNone(commands[0][0])
        self.assertTrue(
            all(row[0] == "actual-element" for row in commands if row[1] not in {"pointer_click", "wheel"})
        )
        self.assertTrue(all(row[0] is None for row in commands if row[1] in {"pointer_click", "wheel"}))
        self.assertEqual(commands[-1][2]["text"], str(folder.resolve()))
        self.assertFalse(
            any(
                ".click(" in script or "dispatchEvent(" in script or ".value=" in script
                for script in observations
            )
        )
        self.assertEqual(
            {row["action"] for row in actions},
            {"target_visible_and_hit_tested", "trusted_visible_pointer_click", "trusted_type", "trusted_keys", "trusted_directory_upload"},
        )

    def test_unconfirmed_route_never_grants_or_invokes(self):
        class ForbiddenUI:
            def __getattr__(self, _):
                raise AssertionError("No UI model/grant mutation allowed without confirmed route")

        for enabled, health in [(False, "healthy"), (True, "declared"), (True, "worker_missing")]:
            with self.subTest(enabled=enabled, health=health):
                calls = []

                def read(op, calls=calls, enabled=enabled, health=health):
                    calls.append(op)
                    return {
                        "capabilities": [
                            {"capability": "machine.answer", "enabled": enabled, "health": health}
                        ]
                    }

                stage = self.probe.run_ai_stage(ForbiddenUI(), read, None, None, {}, {}, True)
                self.assertEqual(
                    [stage["status"], stage["correction"], stage["retest"]], ["NOT_EXECUTED"] * 3
                )
                self.assertEqual(calls, ["capabilities_list"])

    def test_quote_selection_requires_native_range_and_react_display(self):
        text = "中文🌌\n尾行\n"
        proof = {
            "focused": True,
            "value": text,
            "start": 0,
            "end": len(text.encode("utf-16-le")) // 2,
            "displayed": "已选引文：" + text,
        }
        self.probe.assert_quote_selection(proof, text)
        for field, wrong in [
            ("focused", False),
            ("start", 1),
            ("end", proof["end"] - 1),
            ("value", text.rstrip()),
            ("displayed", "已选引文："),
        ]:
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.probe.assert_quote_selection({**proof, field: wrong}, text)
        commands, scripts, result = [], [], {}
        ui = self.probe.GroupedUI(
            lambda script: {"ready": True, "point": {"x": 3, "y": 4}} if "elementFromPoint" in script else proof,
            lambda script: scripts.append(script),
            lambda *_: "quote",
            lambda element, action, body: commands.append((action, body)),
            [],
        )
        self.probe.select_full_quote(
            ui, lambda _: proof, lambda script: scripts.append(script), text, result
        )
        self.assertEqual(commands, [("pointer_click", {"x": 3, "y": 4}), ("value", {"text": "\ue009a\ue000"})])
        self.assertEqual(result["quote_selection"]["status"], "PASS")
        self.assertFalse(
            any(
                token in script
                for script in scripts
                for token in ["setSelectionRange(", "dispatchEvent(", ".focus("]
            )
        )
        failed = {}

        def timeout(_):
            raise TimeoutError("native selection missing")

        with self.assertRaises(TimeoutError):
            self.probe.select_full_quote(ui, lambda _: {**proof, "end": 0}, timeout, text, failed)
        self.assertEqual(failed["quote_selection"]["status"], "FAIL")
        self.assertEqual(failed["quote_selection"]["selection"]["end"], 0)

    def test_answer_does_not_become_correctness_claim(self):
        task = {
            "scope": "runtime.answer",
            "outcome": "unmeasured",
            "conditions": json.dumps(
                {"answer": {**self.probe.ai_receipt_contract()[1][0], "answer": "correct answer"}}
            ),
        }
        self.assertEqual(self.probe.inference_status(task), "EXECUTED_CANDIDATE_NOT_EVALUATED")
        self.assertEqual(
            self.probe.inference_status(
                {**task, "conditions": json.dumps({"answer": {"model": "SIMULATED-model"}})}
            ),
            "UNVERIFIED",
        )
        self.assertEqual(self.probe.inference_status({**task, "outcome": "failed"}), "NOT_EXECUTED")

    def test_harness_separate_branch_retains_finally(self):
        source = (ROOT / "scripts/probes/aaos01_tauri_webdriver_loop.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        main = next(
            node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"
        )
        branch = next(
            node
            for node in ast.walk(main)
            if isinstance(node, ast.If)
            and ast.unparse(node.test) == "args.grouped_common_owner_loop"
            and any(isinstance(child, ast.Raise) for child in node.body)
        )
        code = ast.unparse(branch)
        self.assertIn("run_grouped_loop", code)
        for forbidden in [
            "navigate_compatibility_space",
            "synthetic_course_loop(",
            "native_command(",
        ]:
            self.assertNotIn(forbidden, code)
        self.assertIn("grouped_run_ai", code)
        self.assertIn("report=receipt['grouped_common_owner_loop']", code)
        self.assertIn("compatibility fixtures", source)
        enclosing = next(
            node for node in ast.walk(main) if isinstance(node, ast.Try) and branch in node.body
        )
        self.assertTrue(enclosing.finalbody)
        self.assertTrue(
            any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "close_session"
                for node in ast.walk(enclosing)
            )
        )

    def test_declared_route_with_explicit_optin_attempts_ui_without_claiming_model_health(self):
        class FirstUIActionError(Exception):
            pass

        class ActualUI:
            def page(self, page):
                if page != "13":
                    raise AssertionError("wrong page")
                raise FirstUIActionError

        capability = {
            "capability": "machine.answer",
            "enabled": True,
            "registered": True,
            "health": "declared",
            "provider": {"worker_present": True, "interpreter_present": True},
        }
        with self.assertRaises(FirstUIActionError):
            self.probe.run_ai_stage(
                ActualUI(),
                lambda op, *_: (
                    {"capabilities": [capability]}
                    if op == "capabilities_list"
                    else {"knowledge_id": "exact", "status": "accepted"}
                ),
                None,
                None,
                {"knowledge_id": "exact"},
                {},
                True,
            )
        # No explicit opt-in means no route or grant is consulted.
        self.assertEqual(
            self.probe.run_ai_stage(None, None, None, None, {}, {}, False)["status"], "NOT_EXECUTED"
        )

    def test_persisted_task_conditions_requires_exact_json_text(self):
        self.assertEqual(
            self.probe.task_conditions({"conditions": '{"answer_id":"exact"}'}),
            {"answer_id": "exact"},
        )
        for invalid in [{"answer_id": "exact"}, None, "[]", "null", "bad-json"]:
            with (
                self.subTest(invalid=invalid),
                self.assertRaises((AssertionError, json.JSONDecodeError)),
            ):
                self.probe.task_conditions({"conditions": invalid})

    def ai_fixture(self):
        grant = {
            "document_id": "original-grant",
            "version": 1,
            "content_sha256": "a" * 64,
            "purpose": "original",
        }
        original = {
            "schema": "archeaxis.machine-answer/v1",
            "answer_id": "answer",
            "knowledge_id": "original-knowledge",
            "question": "question",
            "answer": {
                "answer": "A correct actual-answer-shaped test value",
                **self.probe.ai_receipt_contract()[1][0],
            },
            "authority": "candidate",
            "request": {"context_grant": grant, "knowledge_id": "original-knowledge", "question": "question", "context_sha256": hashlib.sha256(b"Original accepted body").hexdigest()},
        }
        task = {
            "task_id": "answer",
            "scope": "runtime.answer",
            "outcome": "unmeasured",
            "knowledge_version": "original-knowledge@v1",
            "model_version": self.probe.ai_receipt_contract()[1][0]["model"],
            "retest_of": None,
            "conditions": json.dumps(original),
        }
        authored = {
            "actor": "ENGINEERING_AUTHORED_INTERVENTION_NOT_OWNER",
            "body": "Authored clarification",
            "note": "Not independent model-error evidence",
        }
        correction = {
            "answer_id": "answer",
            "failed_task_id": "evaluation_answer",
            "corrects_knowledge_id": "original-knowledge",
            "question": "question",
            "machine_answer": original["answer"]["answer"],
            "corrected_answer": authored["body"],
            "error_note": authored["note"],
            "reviewer": authored["actor"],
            "correction_candidate_id": "corrected-knowledge",
        }
        failed = {
            "task_id": "evaluation_answer",
            "scope": "runtime.evaluation.failed",
            "outcome": "failed",
            "conditions": json.dumps({**original, "correction": correction}),
        }
        candidate = {
            "knowledge_id": "corrected-knowledge",
            "body": authored["body"],
            "source_id": None,
            "anchor_id": None,
            "status": "candidate",
        }
        return grant, original, task, authored, failed, candidate

    def test_original_task_and_corrected_lineage_preserve_correct_answer(self):
        grant, original, task, authored, failed, candidate = self.ai_fixture()
        self.assertEqual(
            self.probe.assert_inference_task(task, "original-knowledge", "question", grant),
            original,
        )
        self.probe.assert_correction_lineage(original, failed, candidate, authored)
        self.assertIn("correct actual", original["answer"]["answer"])
        self.assertEqual(self.probe.inference_status(task), "EXECUTED_CANDIDATE_NOT_EVALUATED")
        for field in [
            "answer_id",
            "corrects_knowledge_id",
            "question",
            "machine_answer",
            "corrected_answer",
            "error_note",
            "reviewer",
            "correction_candidate_id",
        ]:
            changed = copy.deepcopy(failed)
            body = json.loads(changed["conditions"])
            body["correction"][field] = "another"
            changed["conditions"] = json.dumps(body)
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.probe.assert_correction_lineage(original, changed, candidate, authored)
        for field in ["source_id", "anchor_id"]:
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.probe.assert_correction_lineage(
                    original, failed, {**candidate, field: "invented-source"}, authored
                )

    def test_retest_requires_new_exact_grant_and_failed_ancestor(self):
        grant, original, task, _, failed, candidate = self.ai_fixture()
        new_grant = {**grant, "document_id": "independent-retest-grant", "purpose": "retest"}
        retest = {
            **original,
            "schema": "archeaxis.machine-retest/v1",
            "answer_id": "retest",
            "retest_task_id": "retest",
            "knowledge_id": "corrected-knowledge",
            "retest_of": "evaluation_answer",
            "request": {"knowledge_id": "corrected-knowledge", "question": "question", "retest_of": "evaluation_answer", "max_tokens": 2048, "context_grant": new_grant},
            "prior": {"conditions": json.loads(failed["conditions"])},
        }
        retest["execution_request"] = {"schema": "archeaxis.machine-retest-execution/v1",
            "request": copy.deepcopy(retest["request"]),
            "context_sha256": hashlib.sha256(candidate["body"].encode("utf-8")).hexdigest()}
        proof = {
            **task,
            "task_id": "retest",
            "scope": "runtime.retest",
            "knowledge_version": "corrected-knowledge@v1",
            "retest_of": "evaluation_answer",
            "conditions": json.dumps(retest),
        }
        self.probe.assert_inference_task(
            proof, "corrected-knowledge", "question", new_grant, "runtime.retest"
        )
        self.assertEqual(self.probe.inference_status(proof), "EXECUTED_CANDIDATE_NOT_EVALUATED")
        binding = self.probe.receipt_binding(proof, {**candidate, "status": "accepted"}, "question", new_grant, prior_failed_task=failed)
        self.assertEqual(binding["status"], "RECEIPT_BINDINGS_VALIDATED")
        with self.assertRaises(AssertionError):
            self.probe.assert_inference_task(
                proof, "corrected-knowledge", "question", grant, "runtime.retest"
            )
        with self.assertRaises(AssertionError):
            self.probe.assert_inference_task(
                {**proof, "retest_of": "other-failure"},
                "corrected-knowledge",
                "question",
                new_grant,
                "runtime.retest",
            )

    def test_authored_intervention_requires_explicit_actual_model(self):
        with self.assertRaisesRegex(AssertionError, "actual-model"):
            self.probe.run_ai_stage(None, None, None, None, {}, {}, False, True)
        source = (ROOT / "scripts/probes/aaos01_tauri_webdriver_loop.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("args.grouped_authored_intervention and not args.grouped_run_ai", source)
        self.assertIn("authored_intervention=args.grouped_authored_intervention", source)

    def test_restored_old_grant_refusal_observed_only_through_ui_without_new_task(self):
        grant, original, task, _, _, _ = self.ai_fixture()
        document = {
            **grant,
            "title": "original",
            "editor_json": {"attrs": {"archeaxis_context_grant": {"purpose": "original", "knowledge_id": "original-knowledge"}}},
        }
        stage = {
            "original_grant": document,
            "original_answer": original,
            "status": "EXECUTED_CANDIDATE_NOT_EVALUATED",
            "knowledge_before": {"knowledge_id": "original-knowledge", "status": "accepted", "body": "original body"},
        }
        actions, reads, waits = [], [], []

        normalized = {"operation": "answer", "request": {
            "knowledge_id": "original-knowledge", "question": "question", "max_tokens": 2048, "timeout_s": 120,
            "context_grant": self.probe.grant_snapshot(document), "asset_context_grant": None,
            "client_request_id": "machine_new_fixture", "retest_of": None,
        }}
        receipt = {"schema": "archeaxis.context-admission-refusal/v1", "reason_code": "RESTORED_GRANT_FENCED",
            "execution_state": "NOT_EXECUTED", "execution_scope": "CURRENT_INVOCATION", "prior_request_execution": "UNVERIFIED",
            "answer_published": False, "operation": "answer", "knowledge_id": "original-knowledge", "retest_of": None,
            "client_request_id": "machine_new_fixture", "grant": {k: document[k] for k in ("document_id", "version", "content_sha256")},
            "request_sha256": hashlib.sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()}

        class UI:
            def js(self, script):
                if "原知识授权详细信息 ·" in script:
                    return {"document": copy.deepcopy(document),
                            "grant": copy.deepcopy(document["editor_json"]["attrs"]["archeaxis_context_grant"]),
                            "snapshot": self_probe.grant_snapshot(document),
                            "knowledge": copy.deepcopy(stage["knowledge_before"]), "current": True}
                self_script = script
                assert "contextAdmissionRefusal" in self_script
                return copy.deepcopy(receipt)

            def page(self, page):
                actions.append(("page", page))

            def click(self, label):
                actions.append(("click", label))

            def click_revealed_selector(self, selector):
                actions.append(("click_selector", selector))

            def click_revealed(self, label, scope):
                actions.append(("click", label))

            def type(self, label, text, tag):
                actions.append(("type", label, text, tag))

        def read(op, payload=None):
            reads.append((op, payload))
            if op == "machine_tasks_list":
                return {"items": [{"task_id": "answer"}], "next_cursor": None}
            if op == "machine_task_get":
                return copy.deepcopy(task)
            if op == "document_get":
                return copy.deepcopy(document)
            if op == "knowledge_get":
                return copy.deepcopy(stage["knowledge_before"])
            if op == "capabilities_list":
                return {
                    "capabilities": [
                        {"capability": "machine.answer", "enabled": True, "registered": True}
                    ]
                }
            raise AssertionError("Unexpected write or read " + op)

        self_probe = self.probe
        observed = self.probe.restored_grant_refusal(
            UI(), read, lambda script, **_: waits.append(script), stage
        )
        self.assertEqual(observed["status"], "PASS")
        self.assertTrue(observed["tasks_unchanged"])
        self.assertEqual(observed["exact_core_reason"], "RESTORED_GRANT_FENCED")
        self.assertEqual(observed["execution_scope"], "CURRENT_INVOCATION")
        self.assertEqual(observed["prior_request_execution"], "UNVERIFIED")
        for field in ("reason_code", "execution_scope", "prior_request_execution", "knowledge_id", "request_sha256", "grant"):
            bad = {**receipt, field: "mismatch"}
            with self.assertRaises(AssertionError):
                self.probe.restored_admission_receipt(bad, document, "original-knowledge", "question")
        with self.assertRaises(AssertionError):
            self.probe.restored_admission_receipt(None, document, "original-knowledge", "question")
        self.assertIn(("type", "实际问题", "question", "textarea"), actions)
        self.assertIn(("click", "执行本地机器回答"), actions)
        self.assertTrue(any("本地知识库明确拒绝此回答请求" in script for script in waits))
        self.assertTrue(all(op in self.probe.READ_OPERATIONS for op, _ in reads))
        self.assertEqual(
            self.probe.restored_grant_refusal(None, None, None, {})["status"], "NOT_EXECUTED"
        )
        task_reads = [0]

        def changed_task_read(op, payload=None):
            value = read(op, payload)
            if op == "machine_task_get":
                task_reads[0] += 1
                if task_reads[0] > 1:
                    return {**value, "model_version": "changed-after-request"}
            return value

        with self.assertRaisesRegex(AssertionError, "created/changed"):
            self.probe.restored_grant_refusal(UI(), changed_task_read, lambda *_, **__: None, stage)

        with self.assertRaisesRegex(AssertionError, "partial page"):
            self.probe.machine_tasks(lambda *_: {"items": [], "next_cursor": "next-page"})

    def test_simulated_full_helper_actual_shaped_answer_adoption_new_grant_retest(self):
        self.exercise_simulated_ai(False)
        self.exercise_simulated_ai(True)

    def test_grouped_rejects_undeclared_stub_mock_and_wrong_frozen_request(self):
        for mutation in ("undeclared_model", "stub_model", "mock_model", "wrong_original_request"):
            with self.subTest(mutation=mutation):
                self.exercise_simulated_ai(True, mutation)

    def test_grouped_retest_without_exact_execution_body_is_unverified(self):
        for mutation in ("missing_retest_context", "wrong_retest_body"):
            with self.subTest(mutation=mutation):
                self.exercise_simulated_ai(True, mutation)

    def exercise_simulated_ai(self, intervention, mutation=None, selected_max_tokens=None, save_deep_binding=False):
        docs, tasks, actions, reads, fields = {}, {}, [], [], {}
        knowledge = {
            "knowledge_id": "original-knowledge",
            "body": "Preserved original bytes differ from document revisions",
            "status": "accepted",
        }
        candidate = {}
        bound = [knowledge["knowledge_id"]]
        probe = self.probe
        saved_configuration = {}
        def save_binding(ui, read, wait, stage, model, purposes, *, budget=1024):
            profile = {"model":model,"max_tokens":budget,"timeout_s":120}
            saved_configuration.update(resolved={p:{"purpose":p,"lane":"deep","profile":profile} for p in purposes})
            stage["saved_deep_binding"] = copy.deepcopy(saved_configuration)

        class UI:
            def page(self, page):
                actions.append(("page", page))

            def click_revealed(self, label, scope=""):
                actions.append(("revealed_click", label, scope))

            def js(self, script):
                assert '本地模型清单探测结果' in script
                return '清单已读取，共 1 项；声明模型已列出。加载状态未知，推理尚未验证。'

            def click_selector(self, selector):
                actions.append(("checkbox", selector))
                fields["operation"] = "retest" if "允许本地复测" in selector else "answer"

            def type(self, label, text, tag="input", scope=""):
                actions.append(("type", label, tag, scope))
                fields[label] = text

            def click(self, label, scope=""):
                actions.append(("click", label, scope))
                if label == "明确授权并保存":
                    ident = "grant-" + str(len(docs) + 1)
                    grant = {
                        "purpose": fields["用途"],
                        "consumer": "local-machine",
                        "operations": [fields["operation"]],
                        "state": "granted",
                        "knowledge_id": bound[0],
                    }
                    docs[ident] = {
                        "document_id": ident,
                        "title": fields["用途"],
                        "version": 1,
                        "content_sha256": "a" * 64,
                        "editor_json": {"attrs": {"archeaxis_context_grant": grant}},
                    }
                elif label == "执行本地机器回答":
                    body = {
                        "schema": "archeaxis.machine-answer/v1",
                        "answer_id": "actual-shaped-answer",
                        "question": fields["实际问题"],
                        "knowledge_id": knowledge["knowledge_id"],
                        "authority": "candidate",
                        "answer": {
                            **probe.ai_receipt_contract()[1][0],
                            "answer": "A correct explanation; no actual error claimed",
                            "usage": None, "usage_status":"UNKNOWN", "cost":None, "cost_status":"UNKNOWN",
                            "finish_reason": "stop",
                            "truncated": False,
                        },
                        "request": {
                            "knowledge_id": knowledge["knowledge_id"],
                            "question": fields["实际问题"],
                            "context_grant": probe.grant_snapshot(docs["grant-1"]),
                            "context_sha256": hashlib.sha256(
                                knowledge["body"].encode()
                            ).hexdigest(),
                        },
                    }
                    if selected_max_tokens is not None:
                        body["request"]["max_tokens"] = saved_configuration["resolved"]["answer"]["profile"]["max_tokens"] if save_deep_binding else selected_max_tokens
                    if save_deep_binding:
                        resolved = saved_configuration["resolved"]["answer"]
                        body["answer"].update(requested_model=resolved["profile"]["model"], observed_model=resolved["profile"]["model"], answer_source="content")
                        body["request"].update(model_configuration=copy.deepcopy(resolved),resolved_model=copy.deepcopy(resolved),model=resolved["profile"]["model"],timeout_s=120)
                    if mutation in ("undeclared_model", "stub_model", "mock_model"):
                        body["answer"]["model"] = {"undeclared_model": "configured-model", "stub_model": "local-stub", "mock_model": "mock-qwen"}[mutation]
                    if mutation == "wrong_original_request":
                        body["request"]["knowledge_id"] = "other-knowledge"
                    tasks[body["answer_id"]] = {
                        "task_id": body["answer_id"],
                        "scope": "runtime.answer",
                        "outcome": "unmeasured",
                        "knowledge_version": knowledge["knowledge_id"] + "@v1",
                        "model_version": body["answer"]["model"],
                        "retest_of": None,
                        "conditions": json.dumps(body),
                    }
                elif label == "记录使用者纠正候选":
                    original = json.loads(tasks["actual-shaped-answer"]["conditions"])
                    candidate.update(
                        knowledge_id="corrected-knowledge",
                        body=fields["正确答案"],
                        status="candidate",
                        source_id=None,
                        anchor_id=None,
                    )
                    correction = {
                        "answer_id": original["answer_id"],
                        "failed_task_id": "evaluation_" + original["answer_id"],
                        "corrects_knowledge_id": original["knowledge_id"],
                        "question": original["question"],
                        "machine_answer": original["answer"]["answer"],
                        "corrected_answer": fields["正确答案"],
                        "error_note": fields["具体错误依据"],
                        "reviewer": fields["纠正提交者"],
                        "correction_candidate_id": candidate["knowledge_id"],
                    }
                    tasks[correction["failed_task_id"]] = {
                        "task_id": correction["failed_task_id"],
                        "scope": "runtime.evaluation.failed",
                        "outcome": "failed",
                        "conditions": json.dumps({**original, "correction": correction}),
                    }
                elif label == "接受纠正知识":
                    candidate["status"] = "accepted"
                elif label == "为此纠正知识建立独立复测授权":
                    bound[0] = candidate["knowledge_id"]
                elif label == "以已接受纠正知识运行独立复测":
                    original = json.loads(tasks["actual-shaped-answer"]["conditions"])
                    failed_id = "evaluation_" + original["answer_id"]
                    body = {
                        **original,
                        "schema": "archeaxis.machine-retest/v1",
                        "answer_id": "actual-shaped-retest",
                        "retest_task_id": "actual-shaped-retest",
                        "knowledge_id": candidate["knowledge_id"],
                        "retest_of": failed_id,
                        "request": {"knowledge_id": candidate["knowledge_id"], "question": original["question"],
                                    "retest_of": failed_id, "max_tokens": 2048,
                                    "context_grant": probe.grant_snapshot(docs["grant-2"])},
                        "prior": {"conditions": json.loads(tasks[failed_id]["conditions"])},
                    }
                    body["execution_request"] = {"schema": "archeaxis.machine-retest-execution/v1",
                        "request": copy.deepcopy(body["request"]),
                        "context_sha256": hashlib.sha256(candidate["body"].encode("utf-8")).hexdigest()}
                    if mutation == "missing_retest_context":
                        del body["execution_request"]
                    if mutation == "wrong_retest_body":
                        body["execution_request"]["context_sha256"] = hashlib.sha256(knowledge["body"].encode("utf-8")).hexdigest()
                    tasks[body["answer_id"]] = {
                        "task_id": body["answer_id"],
                        "scope": "runtime.retest",
                        "outcome": "unmeasured",
                        "knowledge_version": candidate["knowledge_id"] + "@v1",
                        "model_version": body["answer"]["model"],
                        "retest_of": failed_id,
                        "conditions": json.dumps(body),
                    }

        def read(op, payload=None):
            self.assertIn(op, probe.READ_OPERATIONS)
            reads.append(op)
            payload = payload or {}
            if op == "machine_configuration":
                return {"schema":"archeaxis.machine-configuration/v1","availability":"CONFIGURED_UNVERIFIED","network_performed":False,"inference_status":"NOT_EXECUTED","loaded_status":"UNKNOWN","model_identity":None,"usage":None,"cost":None}
            if op == "capabilities_list":
                return {
                    "capabilities": [
                        {
                            "capability": "machine.answer",
                            "enabled": True,
                            "registered": True,
                            "health": "declared",
                            "provider": {
                                "worker_present": True,
                                "interpreter_present": True,
                            },
                        }
                    ]
                }
            if op == "knowledge_get":
                return copy.deepcopy(
                    knowledge if payload["id"] == knowledge["knowledge_id"] else candidate
                )
            if op == "machine_contexts_list":
                return {
                    "items": [
                        {k: d[k] for k in ["document_id", "title", "version", "content_sha256"]}
                        for d in docs.values()
                    ],
                    "next_cursor": None,
                }
            if op == "document_get":
                return copy.deepcopy(docs[payload["document_id"]])
            if op == "machine_tasks_list":
                return {"items": [{"task_id": key} for key in tasks], "next_cursor": None}
            if op == "machine_task_get":
                return copy.deepcopy(tasks[payload["task_id"]])
            raise AssertionError("Unexpected op " + op)

        result = {}
        with patch.object(probe, "save_deep_model_binding", save_binding), patch.object(probe, "select_saved_deep_lane", lambda *_:None):
            stage = probe.run_ai_stage(
                UI(), read, lambda _: "", lambda *_, **__: None,
                {"knowledge_id": knowledge["knowledge_id"]}, result, True, intervention,
                selected_model=probe.ai_receipt_contract()[1][0]["model"] if save_deep_binding else None,
                selected_max_tokens=selected_max_tokens, save_deep_binding=save_deep_binding,
            )
        if mutation in ("undeclared_model", "stub_model", "mock_model", "wrong_original_request"):
            self.assertEqual(stage["status"], "UNVERIFIED")
            self.assertEqual(stage["receipt_binding"]["status"], "UNVERIFIED")
            self.assertEqual(stage["correction"], "NOT_EXECUTED")
            self.assertFalse(any(action[1] == "记录使用者纠正候选" for action in actions))
            return
        self.assertEqual(stage["status"], "EXECUTED_CANDIDATE_NOT_EVALUATED")
        self.assertEqual(stage["receipt_binding"]["status"], "RECEIPT_BINDINGS_VALIDATED")
        self.assertEqual(stage["receipt_binding"]["actual_model_execution"], "NOT_PROVEN_BY_RECEIPT_HELPER")
        self.assertIn(("type", "实际问题", "textarea", ""), actions)
        self.assertEqual(
            json.loads(tasks["actual-shaped-answer"]["conditions"])["answer"]["answer"],
            "A correct explanation; no actual error claimed",
        )
        if intervention:
            self.assertEqual(
                stage["correction"], "EXECUTED_AUTHORED_INTERVENTION_NOT_INDEPENDENT_ERROR"
            )
            self.assertEqual(stage["retest"], "UNVERIFIED" if mutation in ("missing_retest_context", "wrong_retest_body") else "EXECUTED_CANDIDATE_NOT_EVALUATED")
            self.assertEqual(stage["retest_receipt_binding"]["status"], "UNVERIFIED" if mutation in ("missing_retest_context", "wrong_retest_body") else "RECEIPT_BINDINGS_VALIDATED")
            self.assertFalse(stage["authored_intervention"]["independent_error_adjudication"])
            self.assertIn("not independent model-failure evidence", stage["semantic_limitation"])
            self.assertNotEqual(
                stage["original_grant"]["document_id"], stage["retest_grant"]["document_id"]
            )
            self.assertEqual(len(result["actual_tasks"]), 3)
        else:
            self.assertEqual(stage["correction"], "NOT_EXECUTED")
            self.assertEqual(stage["retest"], "NOT_EXECUTED")
            self.assertEqual(len(tasks), 1)
            self.assertFalse(any(action[1] == "记录使用者纠正候选" for action in actions))

        return result

    def test_required_actual_ai_chain_revalidates_tasks_and_rejects_incomplete_execution(self):
        result = self.exercise_simulated_ai(True)
        result["restored_grant_refusal"] = {"status": "PASS"}
        result["capability_toggle"] = {"status": "PASS"}
        # Explicit SIMULATED observation for this strict-gate fixture only.
        for task in (result["ai_progress"]["task"], result["ai_progress"]["retest_task"]):
            conditions = json.loads(task["conditions"])
            answer = conditions["answer"]
            answer.update(requested_model=answer["model"], observed_model=answer["model"],
                          answer_source={"openai": "content", "ollama": "response"}[answer["protocol"]])
            task["conditions"] = json.dumps(conditions)
        self.probe.assert_actual_ai_chain(result)
        for task_key in ("task", "retest_task"):
            for key, changed in (("observed_model", None), ("observed_model", "different"), ("requested_model", None), ("answer_source", "reasoning_content")):
                bad = copy.deepcopy(result)
                task = bad["ai_progress"][task_key]
                conditions = json.loads(task["conditions"])
                conditions["answer"][key] = changed
                task["conditions"] = json.dumps(conditions)
                with self.subTest(task=task_key, field=key, value=changed), self.assertRaises(AssertionError):
                    self.probe.assert_actual_ai_chain(bad)
        for field in ("status", "retest"):
            bad = copy.deepcopy(result)
            bad["ai_progress"][field] = "NOT_EXECUTED"
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.probe.assert_actual_ai_chain(bad)
        for key, value in (("truncated", True), ("finish_reason", "length"), ("finish_reason", None), ("model", "mock")):
            bad = copy.deepcopy(result)
            task = bad["ai_progress"]["retest_task"]
            conditions = json.loads(task["conditions"])
            conditions["answer"][key] = value
            task["conditions"] = json.dumps(conditions)
            with self.subTest(key=key, value=value), self.assertRaises(AssertionError):
                self.probe.assert_actual_ai_chain(bad)
        for field in ("restored_grant_refusal", "capability_toggle"):
            bad = copy.deepcopy(result)
            bad[field]["status"] = "NOT_EXECUTED"
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.probe.assert_actual_ai_chain(bad)

    def capability_fixture(self):
        frozen = {
            "job_id": "read_exact",
            "request_id": "read_run_exact",
            "body": {"deadline_ms": 60000, "split": False, "words": False},
        }
        refused = {
            "job_id": "read_exact",
            "input_ref": "source-exact",
            "kind": "text",
            "state": "queued",
            "attempt": None,
            "request_id": None,
            "attempts": [],
            "attempts_capped": False,
        }
        succeeded = {
            **refused,
            "state": "succeeded",
            "attempt": 1,
            "request_id": "read_run_exact",
            "attempts": [
                {
                    "attempt": 1,
                    "request_id": "read_run_exact",
                    "state": "succeeded",
                    "budget": {**frozen["body"], "capability": "text.extract"},
                    "steps": {
                        "durable_claim": "RECORDED",
                        "worker_response_commit": "RECORDED",
                        "terminal_write": "RECORDED",
                    },
                    "checkpoint": {"status": "CORE_COMMITTED"},
                }
            ],
        }
        return frozen, refused, succeeded

    def test_refusal_empty_attempts_and_retry_full_identity_negative_guards(self):
        frozen, refused, succeeded = self.capability_fixture()
        self.probe.assert_unadmitted(refused, frozen["job_id"], "source-exact")
        self.probe.assert_single_attempt(succeeded, frozen, "source-exact")
        for field, changed in [
            ("attempt", 1),
            ("request_id", "consumed"),
            ("state", "running"),
            ("attempts", [succeeded["attempts"][0]]),
            ("input_ref", "another-source"),
            ("attempts_capped", True),
        ]:
            with self.subTest(refusal=field), self.assertRaises(AssertionError):
                self.probe.assert_unadmitted(
                    {**refused, field: changed}, frozen["job_id"], "source-exact"
                )
        for field, changed in [
            ("request_id", "another-request"),
            ("attempt", 2),
            ("state", "failed"),
            ("input_ref", "another-source"),
            ("attempts_capped", True),
            ("attempts", succeeded["attempts"] * 2),
        ]:
            with self.subTest(retry=field), self.assertRaises(AssertionError):
                self.probe.assert_single_attempt(
                    {**succeeded, field: changed}, frozen, "source-exact"
                )
        changed = copy.deepcopy(succeeded)
        changed["attempts"][0]["budget"]["split"] = True
        with self.assertRaises(AssertionError):
            self.probe.assert_single_attempt(changed, frozen, "source-exact")
        text = "Authored source text\n"
        output = {
            "content": text,
            "metadata": {
                "kind": "text",
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "byte_length": len(text.encode()),
            },
        }
        self.probe.assert_text_output(output, text)
        with self.assertRaises(AssertionError):
            self.probe.assert_text_output({**output, "content": "other"}, text)
        with self.assertRaises(AssertionError):
            self.probe.assert_text_output(
                {**output, "metadata": {**output["metadata"], "sha256": "bad"}}, text
            )

    def test_simulated_native_capability_controls_recover_exact_frozen_request(self):
        result, actions, restarts = self.exercise_capability_probe()
        self.assertEqual(
            [
                result[key]
                for key in [
                    "status",
                    "execution_refusal",
                    "frozen_intent_restart",
                    "enable_without_execution",
                    "same_request_retry",
                    "host_restart_result",
                ]
            ],
            ["PASS"] * 6,
        )
        self.assertEqual(restarts, [False, False, True])
        enable_index = actions.index(
            ("click", "启用 text.extract", "//section[@aria-label='冻结请求的能力恢复']")
        )
        retries = [i for i, action in enumerate(actions) if action ==
                   ("click", "重试上次处理", "//section[@aria-label='真实转换产物']")]
        self.assertEqual(len(retries), 2)
        self.assertLess(retries[0], enable_index, "disabled same-key proof refresh is a separate action")
        retry_index = retries[1]
        self.assertGreater(retry_index, enable_index)
        self.assertFalse(any(action[0] == "page" for action in actions[enable_index:retry_index]))

    def test_simulated_enable_must_not_autoexecute_and_retry_cannot_change_identity(self):
        with self.assertRaisesRegex(AssertionError, "automatically"):
            self.exercise_capability_probe(autoexecute=True)
        with self.assertRaises(AssertionError):
            self.exercise_capability_probe(wrong_retry=True)
        with self.assertRaises(AssertionError):
            self.exercise_capability_probe(wrong_budget=True)
        with self.assertRaisesRegex(AssertionError, "Restart silently executed"):
            self.exercise_capability_probe(restart_execute=True)
        with self.assertRaises(AssertionError):
            self.exercise_capability_probe(changed_journal=True)

    def exercise_capability_probe(self, autoexecute=False, wrong_retry=False, wrong_budget=False, restart_execute=False, changed_journal=False):
        frozen, refused, succeeded = self.capability_fixture()
        # Match the native UUID-shaped request text; pure tests never execute a host or model.
        frozen["request_id"] = "read_run_1234-abcd"
        succeeded["request_id"] = frozen["request_id"]
        succeeded["attempts"][0]["request_id"] = frozen["request_id"]
        state = {
            "enabled": True,
            "new_job": False,
            "status": copy.deepcopy(refused),
            "page": "#page=06",
            "finished": False,
            "hydrated": False,
            "journal": None,
            "request_details_open": False,
        }
        actions, restarts = [], []
        text = "Authored source text\n"
        output = {
            "content": text,
            "metadata": {
                "kind": "text",
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "byte_length": len(text.encode()),
            },
        }
        document = {
            "title": "source.txt",
            "document_id": "document-exact",
            "source_revision": "a" * 64,
            "source_id": "source-exact", "version": 1,
            "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "text_projection": text,
            "editor_json": {"type": "doc", "content": [
                {"type": "paragraph", "attrs": {"block_id": "block-exact"}, "content": [
                    {"type": "text", "text": text.removesuffix("\n")}, {"type": "hardBreak"},
                ]},
            ]},
        }
        transform = {
            "source_id": "source-exact",
            "job_id": frozen["job_id"],
            "raw_sha256": document["source_revision"],
            "content": text,
        }
        quality = {
            "job_id": frozen["job_id"],
            "state": "succeeded",
            "engine": "actual-shaped-test-engine",
        }

        class UI:
            def page(self, page):
                state["page"] = "#page=" + page
                actions.append(("page", page))

            def click_selector(self, selector):
                actions.append(("selector", selector))
                if "文档与来源详细信息：文档与来源详细信息" in selector:
                    state["diagnostic"] = True
                elif "禁用 text.extract" in selector:
                    state["enabled"] = False
                elif selector == "//*[@data-recovery-request=" + self_test.probe.xpath_literal(frozen["request_id"]) + "]//button[@data-recovery-action='restore']":
                    self_test.assertIsNotNone(state["journal"])
                    self_test.assertEqual(state["journal"]["request_id"], frozen["request_id"])
                    state["hydrated"] = True
                elif "打开文档" in selector:
                    assert state["page"] == "#page=02", "document selection requires library page"
                    state["page"] = "#page=03"
                elif selector == "//section[@aria-label='真实转换产物']//details[summary[normalize-space(.)='上次处理请求详情']]/summary":
                    self_test.assertIsNotNone(state["journal"])
                    state["request_details_open"] = True
                else:
                    raise AssertionError("unexpected selector")

            def click_revealed_selector(self, selector):
                self.click_selector(selector)

            def open_reader_source_tools(self):
                self.click("整理此来源为知识候选")

            def click_revealed(self, label, scope=""):
                self.click(label, scope)

            def click(self, label, scope=""):
                actions.append(("click", label, scope))
                if label == "执行真实内容转换":
                    state["new_job"] = True
                    state["journal"] = {**copy.deepcopy(frozen), "source_id": "source-exact",
                        "source_revision": document["source_revision"], "kind": "text",
                        "surface": "manual", "mode": "single", "relative": None,
                        "origin_restore_epoch": "initial"}
                elif label == "启用 text.extract":
                    state["enabled"] = True
                    if autoexecute:
                        state["status"] = copy.deepcopy(succeeded)
                elif label == "重试上次处理":
                    self_test.assertTrue(state["hydrated"], "retry needs explicit restored scene")
                    if not state["enabled"]:
                        self_test.assertEqual(state["status"], refused)
                        return  # Fresh bound NOT_ADMITTED, still no durable attempt.
                    state["status"] = copy.deepcopy(succeeded)
                    if wrong_budget:
                        state["status"]["attempts"][0]["budget"]["deadline_ms"] = 1
                    if wrong_retry:
                        state["status"]["request_id"] = "another-request"
                    state["finished"] = True
                elif label == "关闭运行诊断":
                    state["diagnostic"] = False
                elif label not in {"重新读取当前宿主能力", "整理此来源为知识候选"}:
                    raise AssertionError("unexpected click " + label)

        self_test = self
        def read(op, payload=None):
            self.assertIn(op, self.probe.READ_OPERATIONS)
            if op == "ui_state_read":
                self.assertIsNotNone(state["journal"])
                return {"schema": "archeaxis.ui-working-state/v1", "workspace_id": "b" * 32,
                    "restore_epoch": "initial", "state_revision": 1,
                    "state": {"drafts": {}, "opened_documents": [], "active_document": None,
                        "page_id": "03", "pending_jobs": {frozen["request_id"]: copy.deepcopy(state["journal"])}},
                    "draft_digests": {}, "pending_document_id": None,
                    "recovery_requires_confirmation": False, "recovery_candidates": None}
            if op == "capabilities_list":
                return {
                    "capabilities": [{"capability": "text.extract", "enabled": state["enabled"]}]
                }
            if op == "source_jobs":
                return {
                    "source_id": "source-exact",
                    "jobs_capped": False,
                    "jobs": [{"job_id": "folder-original"}]
                    + (
                        [{"job_id": frozen["job_id"], "state": state["status"]["state"]}]
                        if state["new_job"]
                        else []
                    ),
                }
            if op == "job_execution_status":
                return copy.deepcopy(state["status"])
            if op == "job_output":
                return copy.deepcopy(output)
            if op == "job_quality":
                return copy.deepcopy(quality)
            if op == "source_job_transform":
                return copy.deepcopy(transform)
            if op == "document_get":
                return copy.deepcopy(document)
            raise AssertionError("unexpected operation")

        def js(script):
            if script.startswith("const visible=n") or script.startswith("const rows="):
                return evaluate(script, reader_dom(document, diagnostic=state.get("diagnostic", False)))
            if "const root=" in script:
                self_test.assertTrue(state["request_details_open"], "Request identity must be revealed by its actual UI entry")
                return {
                    "page": state["page"],
                    "frozen": "执行请求已冻结："
                    + frozen["request_id"]
                    + "；单次预算 60s。未知结果不会产生新作业。",
                    "latest": "最新任务 " + frozen["job_id"],
                    "recovery": "Core 已证明原请求未受理",
                }
            return text

        def restart():
            restarts.append(state["enabled"])
            state["hydrated"] = False
            state["request_details_open"] = False
            state["page"] = ""
            if state["journal"] is not None and not state["finished"]:
                if restart_execute:
                    state["status"] = copy.deepcopy(succeeded)
                if changed_journal:
                    state["journal"]["body"]["deadline_ms"] = 1

        def wait(script, *args, **kwargs):
            if "data-current-page-id" in script or "诊断控制台" in script:
                assert evaluate(script, reader_dom(document, diagnostic=state.get("diagnostic", False))), "Rendered reader predicate failed; business page does not expose raw ID"
            if script == "return location.hash==='#page=03'":
                assert state["page"] == "#page=03", "hydrated scene needs real same-page URL navigation"

        with patch.object(self.probe.time, "sleep", lambda _: None):
            result = self.probe.capability_refusal_recovery(
                UI(),
                read,
                js,
                wait,
                restart,
                {"source_id": "source-exact"},
                document,
                text,
            )
        return result, actions, restarts

    def test_full_dom_range_including_lf_not_rendered_selection_serialization(self):
        text = "Line one.\nLine two.\n"
        proof = {
            "region_count": 1,
            "focused": True,
            "node_type": 3,
            "child_nodes": 1,
            "range_count": 1,
            "start_same": True,
            "end_same": True,
            "start_offset": 0,
            "end_offset": len(text),
            "node_length": len(text),
            "source_text": text,
            "node_text": text,
            "range_text": text,
            "cloned_text": text,
            "rendered_selection": text[:-1],
        }
        self.probe.assert_full_text_selection(proof, text)
        # A missing final LF in the DOM range is still a real failure, not trimmed away.
        for field, value in [
            ("focused", False),
            ("region_count", 2),
            ("range_count", 2),
            ("start_same", False),
            ("end_same", False),
            ("start_offset", 1),
            ("end_offset", len(text) - 1),
            ("node_length", len(text) - 1),
            ("source_text", text[:-1]),
            ("node_text", text[:-1]),
            ("range_text", text[:-1]),
            ("cloned_text", text[:-1]),
        ]:
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.probe.assert_full_text_selection({**proof, field: value}, text)
        script = self.probe.full_text_selection_wait_script(text)
        self.assertIn("document.activeElement===region", script)
        self.assertIn("range?.startContainer===node", script)
        self.assertIn("range?.endContainer===node", script)
        self.assertIn("proof.end_offset===proof.node_length", script)
        self.assertIn("proof.range_text===", script)
        self.assertIn("proof.cloned_text===", script)
        self.assertNotIn(".trim(", script)
        self.assertNotIn("proof.rendered_selection===", script)
        self.assertNotIn(".focus(", script)
        self.assertNotIn("addRange(", script)
        self.assertNotIn("removeAllRanges(", script)
        astral = "Astral \U0001f30c\n"
        self.probe.assert_full_text_selection(
            {
                **proof,
                "source_text": astral,
                "node_text": astral,
                "range_text": astral,
                "cloned_text": astral,
                "node_length": len(astral.encode("utf-16-le")) // 2,
                "end_offset": len(astral.encode("utf-16-le")) // 2,
            },
            astral,
        )
