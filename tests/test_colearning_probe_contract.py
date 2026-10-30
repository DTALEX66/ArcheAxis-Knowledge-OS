"""The real-model co-learning probe: it exists, it declares what is real, and it fails closed.

The probe itself is run by hand because it needs a live Core and a local model, so what is asserted
here is the part that can be checked without either: that the script is present, that it is honest
about which parts of its evidence are real, and that its verdict logic cannot report a pass for a run
that stopped short.

The honesty labels matter more than usual. `m0_full_loop_smoke.py` covers the same chain and says of
itself that the model failure is a fixture. If this probe ever loses that distinction, a run of it
would look like evidence of human judgement that nobody exercised.
"""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "scripts" / "probes" / "colearning_real_model_smoke.py"


def _module():
    spec = importlib.util.spec_from_file_location("colearning_probe_under_test", PROBE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_probe_exists_and_drives_the_routes_that_run_a_model():
    source = PROBE.read_text(encoding="utf-8")
    # The three routes that make this different from the synthetic probe.
    for route in ("/api/v1/machine/answers", "/api/v1/machine/corrections",
                  "/api/v1/machine/retests"):
        assert route in source, f"the probe does not drive {route}"


def test_the_probe_declares_what_is_real_and_what_is_still_a_fixture():
    probe = _module()
    receipt = probe.Receipt().document()
    assert receipt['schema'] == 'aaos.colearning-real-model-receipt/v3'
    assert receipt["evidence_class"] == "SYNTHETIC_OR_UNEXECUTED"
    assert receipt['what_is_real'] == []
    assert receipt['observed_model_response_stages'] == []
    fixture = " ".join(receipt["what_is_still_a_fixture"]).lower()
    # The person is still explicitly a fixture, even in the real invocation path.
    assert "the person" in fixture, receipt["what_is_still_a_fixture"]
    assert "not evidence that a human reviewed" in fixture


def test_the_probe_needs_the_interpreter_before_it_can_claim_to_have_observed_the_loop(monkeypatch):
    probe = _module()
    monkeypatch.delenv("ARCHEAXIS_PYTHON", raising=False)
    missing = probe.unmet_prerequisites()
    assert "ARCHEAXIS_PYTHON" in missing
    # the reason says why the loop could not be observed, not merely that a variable is unset
    assert "scheduler" in missing["ARCHEAXIS_PYTHON"]
    monkeypatch.setenv("ARCHEAXIS_PYTHON", "python")
    assert probe.unmet_prerequisites() == {}


def test_a_run_that_stopped_short_is_never_a_pass():
    """The verdict logic, exercised directly rather than only through a live run."""
    probe = _module()

    complete = probe.Receipt()
    complete.stage("import_source", status=202)
    complete.stage("machine_cannot_accept_correction", status=403)
    # a prerequisite noted along the way does not demote a run that reached the end
    assert not complete.failed_stage
    assert any(entry["stage"] == "machine_cannot_accept_correction" for entry in complete.stages)

    stopped = probe.Receipt()
    stopped.stage("import_source", status=202)
    stopped.stage("machine_answer", status=503, problem="no worker is registered")
    assert stopped.failed_stage == "machine_answer"

    blocked = probe.Receipt()
    blocked.stage("import_source", status=202)
    blocked.block("machine_principal", "no machine credential in this launch")
    assert blocked.blocked


def test_the_probe_fails_closed_on_a_problem_stage():
    """A stage carrying `problem` has to decide the verdict, or a partial run reads as a pass."""
    probe = _module()
    receipt = probe.Receipt()
    receipt.stage("ok", status=200)
    assert receipt.failed_stage is None
    receipt.stage("bad", status=500, problem="something went wrong")
    assert receipt.failed_stage == "bad"


def test_the_probe_does_not_import_anything_outside_the_standard_library():
    """A probe runs on whatever interpreter is at hand, so its imports have to be stdlib plus the
    repository's own modules."""
    tree = ast.parse(PROBE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    third_party = imported - {
        "__future__", "importlib", "json", "os", "shutil", "sys", "time", "uuid",
        "datetime", "pathlib", "hashlib",
    }
    assert not third_party, f"the probe imports third-party modules: {sorted(third_party)}"


def test_report_rejects_incomplete_or_wrong_final_status():
    probe = _module()
    incomplete = probe.Receipt()
    incomplete.stage("import_source", status=202)
    assert probe.report(incomplete) == 1
    incorrect = probe.Receipt()
    incorrect.stage("machine_cannot_accept_correction", status=200)
    assert probe.report(incorrect) == 1


def test_retest_readback_must_match_the_failure():
    probe = _module()
    receipt = probe.Receipt()
    receipt.stage("retest_readback", status=200, links_to_failure=False)
    receipt.stage("machine_cannot_accept_correction", status=403)
    assert probe.report(receipt) == 1


def _finite_receipt(probe, *, correction=False):
    """Actual Core response shapes, deterministic synthetic outputs, no Core/model call."""
    receipt = probe.Receipt()
    receipt.stage('frozen_rubric', rubric=copy.deepcopy(probe.RUBRIC),
                  rubric_sha256=probe.digest(probe.RUBRIC))
    for name in ('import_source', 'text_transform', 'read_transform', 'create_knowledge',
                 'accept_knowledge'):
        receipt.stage(name, status=200)

    def answer(task, identity, knowledge='original', wrong=False, retest=False):
        context = probe.CORRECTED_CONTEXT if knowledge == 'candidate' else probe.CONTEXT
        value = copy.deepcopy(probe.RUBRIC[task]['expected'])
        if wrong:
            if task == 'original':
                value['writer'] = 'Python'
            else:
                value['worker_write_allowed'] = True
        request = {'knowledge_id': knowledge, 'question': probe.RUBRIC[task]['question'],
                   'max_tokens': 2048}
        result = {'answer_id': identity, 'client_request_id': identity + '-request',
                  'knowledge_id': knowledge, 'question': request['question'],
                  'answer': {'answer': json.dumps(value), 'model': 'synthetic-test-model',
                             'finish_reason': 'stop', 'truncated': False},
                  'request': request,
                  'context_authorization': {'mode': 'legacy_knowledge_eligibility_only',
                                            'context_grant': 'NOT_PROVIDED'}}
        effective = {'timeout_s': 120, 'context_sha256': probe.hashlib.sha256(context.encode()).hexdigest()}
        if retest:
            result.update(retest_task_id=identity, retest_of='evaluation_original-answer',
                          execution_request={'request': copy.deepcopy(request), **effective})
        else:
            request.update(effective)
        return result

    original = answer('original', 'original-answer', wrong=correction)
    receipt.stage('machine_answer', status=200, body=original)
    receipt.stage('machine_answered_out_of_scope', status=200, body=answer('abstention', 'refusal'))
    receipt.stage('transfer_before', status=200, body=answer('transfer', 'before', wrong=correction))
    if correction:
        receipt.stage('human_correction', status=200, body={
            'answer_id': 'original-answer', 'corrects_knowledge_id': 'original',
            'question': probe.QUESTION, 'machine_answer': original['answer']['answer'],
            'corrected_answer': probe.CORRECTED_CONTEXT,
            'failed_task_id': 'evaluation_original-answer', 'correction_candidate_id': 'candidate'})
        receipt.stage('accept_correction_fixture', status=200)
        retest = answer('original', 'retest', 'candidate', retest=True)
        prior = copy.deepcopy(original)
        prior['correction'] = copy.deepcopy(receipt.stages[-2]['body'])
        retest['prior'] = {'conditions': prior, 'outcome': 'failed'}
        receipt.stage('machine_retest', status=200, body=retest)
        receipt.stage('retest_readback', status=200, links_to_failure=True, body={
            'task_id': 'retest', 'retest_of': 'evaluation_original-answer',
            'conditions': json.dumps(retest)})
        receipt.stage('transfer_after', status=200, body=answer('transfer', 'after', 'candidate'))
        receipt.stage('machine_cannot_accept_correction', status=403)
    return receipt


def test_correct_original_and_valid_abstention_are_not_failed_learning():
    probe = _module()
    receipt = _finite_receipt(probe)
    assert probe.report(receipt) == 0
    quality = receipt.document()['quality_assessment']
    assert quality['status'] == 'NO_FAILURE_OBSERVED'
    assert quality['learning_improvement'] == 'NOT_ESTABLISHED'
    assert quality['asset_effect'] == 'NOT_QUALIFIED'


def test_finite_correction_and_independent_task_delta_are_not_general_learning():
    probe = _module()
    receipt = _finite_receipt(probe, correction=True)
    assert probe.report(receipt) == 0
    quality = receipt.document()['quality_assessment']
    assert quality['status'] == 'FINITE_CORRECTION_VERIFIED'
    assert quality['transfer_observation'] == 'FINITE_TASK_DELTA'
    assert quality['learning_improvement'] == 'NOT_ESTABLISHED'
    binding = quality['bindings']['original']
    assert binding['request_sha256'] == probe.digest(binding['request'])
    assert binding['authorization_sha256'] == probe.digest(binding['authorization_snapshot'])
    assert binding['asset_qualification'] == 'NOT_PROVIDED_NOT_QUALIFIED'


@pytest.mark.parametrize(('text', 'status'), [
    ('{"worker_write_allowed":true,"release_allowed":true}', 'TRANSFER_FAILURE_REVIEW'),
    ('The worker may not write and the release is frozen.', 'TRANSFER_BASELINE_REVIEW_REQUIRED'),
])
def test_correct_original_does_not_hide_independent_task_failure_or_unknown(text, status):
    probe = _module()
    receipt = _finite_receipt(probe)
    next(s for s in receipt.stages if s['stage'] == 'transfer_before')['body']['answer']['answer'] = text
    assert probe.report(receipt) == 1
    quality = receipt.document()['quality_assessment']
    assert quality['status'] == status
    assert quality['bindings']['original']['score'] == 'CORRECT'
    assert not any(s['stage'] == 'human_correction' for s in receipt.stages)
    assert quality['learning_improvement'] == 'NOT_ESTABLISHED'


def test_unknown_independent_baseline_cannot_claim_comparable_correction():
    probe = _module()
    receipt = _finite_receipt(probe, correction=True)
    next(s for s in receipt.stages if s['stage'] == 'transfer_before')['body']['answer']['answer'] = 'uncertain'
    assert probe.report(receipt) == 1
    quality = receipt.document()['quality_assessment']
    assert quality['status'] == 'TRANSFER_BASELINE_REVIEW_REQUIRED'
    assert 'transfer_observation' not in quality


def test_correct_independent_baseline_is_comparable_but_not_improvement():
    probe = _module()
    receipt = _finite_receipt(probe, correction=True)
    before = next(s for s in receipt.stages if s['stage'] == 'transfer_before')
    before['body']['answer']['answer'] = json.dumps(probe.RUBRIC['transfer']['expected'])
    assert probe.report(receipt) == 0
    quality = receipt.document()['quality_assessment']
    assert quality['transfer_observation'] == 'NO_MEASURED_DELTA'
    assert quality['learning_improvement'] == 'NOT_ESTABLISHED'


def test_constructed_positive_receipt_is_still_synthetic_evidence():
    probe = _module()
    receipt = _finite_receipt(probe, correction=True)
    for stage in receipt.stages:
        body = stage.get('body', {})
        if isinstance(body.get('answer'), dict):
            body['answer']['engine'] = 'python-worker-machine-answer'
    document = receipt.document()
    assert document['evidence_class'] == 'SYNTHETIC_OR_UNEXECUTED'
    assert document['what_is_real'] == []
    assert document['observed_model_response_stages'] == []


@pytest.mark.parametrize('blocked', [False, True])
def test_live_attempt_without_model_response_does_not_claim_inference(blocked):
    probe = _module()
    receipt = probe.Receipt(live_execution=True)
    if blocked:
        receipt.stage('machine_answer', status=503, body={'error': 'model unavailable'})
        receipt.block('local_model', 'model unavailable')
    document = receipt.document()
    assert document['evidence_class'] == 'LIVE_ATTEMPT_NO_MODEL_EVIDENCE'
    assert document['what_is_real'] == []
    assert document['observed_model_response_stages'] == []


def test_live_metadata_classifier_records_only_observed_stages_not_completion():
    # Synthetic test of the classifier; no actual inference is performed by this test.
    probe = _module()
    receipt = probe.Receipt(live_execution=True)
    receipt.stage('machine_answer', status=200, body={'answer': {
        'engine': 'python-worker-machine-answer', 'model': 'synthetic-test-model',
        'answer': '{"writer":"Rust Core","frozen":true}', 'finish_reason': 'stop'}})
    receipt.stage('machine_retest', status=503, body={})
    document = receipt.document()
    assert document['evidence_class'] == 'LIVE_CORE_MODEL_RESPONSE_OBSERVED'
    assert document['observed_model_response_stages'] == ['machine_answer']
    assert document['quality_assessment']['status'] == 'REVIEW_REQUIRED'
    assert 'not full-loop completion' in document['what_is_real'][0]
    assert probe.report(receipt) == 1


@pytest.mark.parametrize(('text', 'expected'), [
    ('{"writer":"Rust Core","frozen":true}', 'CORRECT'),
    ('{"writer":"Not Rust Core","frozen":true}', 'INCORRECT'),
    ('{"writer":"Rust Core","frozen":false}', 'INCORRECT'),
    ('{"writer":"Python","frozen":true}', 'INCORRECT'),
    ('', 'INCORRECT'),
    ('Rust Core is the writer; release is UNFROZEN', 'REVIEW_REQUIRED'),
    ('{"writer":"Rust Core","frozen":1}', 'REVIEW_REQUIRED'),
    ('{"writer":"Rust Core","frozen":false,"frozen":true}', 'REVIEW_REQUIRED'),
    ('{"writer":"Rust Core","frozen":true,"but":"Python may write"}', 'REVIEW_REQUIRED'),
    ('Correct prose describing only Rust Core and a frozen release.', 'REVIEW_REQUIRED'),
])
def test_fixed_rubric_negative_controls_and_uninterpreted_prose(text, expected):
    assert _module().score(text, 'original') == expected


@pytest.mark.parametrize('case', [
    'wrong_retest', 'empty_answer', 'wrong_link_true_flag', 'missing_body', 'duplicate_stage',
    'wrong_answer_id', 'wrong_question', 'wrong_machine_answer', 'missing_request_id',
    'missing_context_hash', 'changed_asset_snapshot', 'changed_rubric', 'same_request_id',
    'same_task_only', 'changed_model', 'changed_budget', 'changed_context',
    'false_refusal', 'correct_baseline_falsely_corrected', 'mismatched_readback',
    'wrong_transfer', 'late_rubric', 'wrong_prior_request', 'wrong_prior_answer',
])
def test_f05_semantic_lineage_and_condition_counterexamples_fail_closed(case):
    probe = _module()
    receipt = _finite_receipt(probe, correction=True)
    stages = {s['stage']: s for s in receipt.stages}
    original = stages['machine_answer']['body']
    retest = stages['machine_retest']['body']
    after = stages['transfer_after']['body']
    correction = stages['human_correction']['body']
    if case == 'wrong_retest':
        retest['answer']['answer'] = '{"writer":"Python","frozen":false}'
    elif case == 'empty_answer':
        after['answer']['answer'] = ''
    elif case == 'wrong_link_true_flag':
        stages['retest_readback']['body']['retest_of'] = 'another-failure'
    elif case == 'missing_body':
        stages['machine_answer']['body'] = {}
    elif case == 'duplicate_stage':
        receipt.stage('machine_retest', status=200, body={})
    elif case == 'wrong_answer_id':
        correction['answer_id'] = 'another-answer'
    elif case == 'wrong_question':
        correction['question'] = probe.UNGROUNDED_QUESTION
    elif case == 'wrong_machine_answer':
        correction['machine_answer'] = 'different persisted text'
    elif case == 'missing_request_id':
        original.pop('client_request_id')
    elif case == 'missing_context_hash':
        original['request'].pop('context_sha256')
    elif case == 'changed_asset_snapshot':
        original['context_authorization'] = {'mode': 'asset', 'member_snapshots': [{'version': 2}]}
    elif case == 'changed_rubric':
        stages['frozen_rubric']['rubric']['original']['expected']['writer'] = 'Python'
    elif case == 'same_request_id':
        after['client_request_id'] = original['client_request_id']
    elif case == 'same_task_only':
        receipt.stages.remove(stages['transfer_after'])
    elif case == 'changed_model':
        after['answer']['model'] = 'another-model'
    elif case == 'changed_budget':
        after['request']['max_tokens'] = 4000
    elif case == 'changed_context':
        after['request']['context_sha256'] = 'a' * 64
    elif case == 'false_refusal':
        stages['machine_answered_out_of_scope']['body']['answer']['answer'] = '{"answerable":true}'
    elif case == 'correct_baseline_falsely_corrected':
        original['answer']['answer'] = json.dumps(probe.RUBRIC['original']['expected'])
    elif case == 'mismatched_readback':
        stages['retest_readback']['body']['conditions'] = '{}'
    elif case == 'wrong_transfer':
        after['answer']['answer'] = '{"worker_write_allowed":true,"release_allowed":true}'
    elif case == 'late_rubric':
        receipt.stages.remove(stages['frozen_rubric'])
        receipt.stages.append(stages['frozen_rubric'])
    elif case == 'wrong_prior_request':
        retest['prior']['conditions']['request']['context_sha256'] = 'f' * 64
    elif case == 'wrong_prior_answer':
        retest['prior']['conditions']['answer']['answer'] = 'another answer'
    # Semantic failures must remain failures even when persisted readback is otherwise consistent.
    if case not in {'mismatched_readback', 'wrong_link_true_flag'}:
        stages['retest_readback']['body']['conditions'] = json.dumps(retest)
    assert probe.report(receipt) == 1
    assert receipt.document()['quality_assessment']['learning_improvement'] == 'NOT_ESTABLISHED'
