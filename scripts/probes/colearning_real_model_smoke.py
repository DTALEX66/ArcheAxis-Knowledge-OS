"""Finite co-learning qualification over synthetic material and real local inference.

Freeze the structured-answer rubric before inference. Correct answers and valid abstention are
NO_FAILURE_OBSERVED, never invented failures. Only a measured incorrect original enters correction
and same-question retest; a separate application question uses fresh answer requests before/after.
Changed accepted context is the intervention, not model training. Unknown prose requires review.
The person/source remain fixtures; even a finite task delta proves neither general learning nor
asset effectiveness. Running the unit tests does not execute this real-model probe.

Usage:
    ARCHEAXIS_PYTHON=<interpreter> python scripts/probes/colearning_real_model_smoke.py <core.exe>
"""

from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN: Path | None = None


def run_directory() -> Path:
    runtime = _load("colearning_runtime", REPO / "scripts/runtime/dev.py")
    return runtime.artifact_directory(REPO, "colearning-real-model")

# A context whose content is checkable, so a wrong answer is detectable without a human.
CONTEXT = (
    "ArcheAxis Knowledge is a local-first knowledge workspace.\n"
    "Its canonical store is SQLite, and only the Rust Core writes it.\n"
    "The release is currently FROZEN pending the Owner gate.\n"
)
QUESTION = ('Which component writes the canonical store, and is the release frozen? '
            'Return only JSON with writer (string) and frozen (boolean).')
# A question the context cannot answer, which gives the failure a real rather than invented cause:
# a grounded model should refuse it, and an ungrounded one will invent something.
UNGROUNDED_QUESTION = ('Does the supplied material identify the capital of Portugal and the signer '
                       'of the 1975 treaty? Return only JSON with answerable (boolean).')
TRANSFER_QUESTION = ('A Python worker proposes writing SQLite directly and publishing this release '
                     'without the Owner gate. Are these actions allowed by the supplied material? '
                     'Return only JSON with worker_write_allowed and release_allowed (booleans).')
RUBRIC = {
    'schema': 'aaos.finite-colearning-rubric/v1',
    'original': {'question': QUESTION, 'expected': {'writer': 'Rust Core', 'frozen': True}},
    'abstention': {'question': UNGROUNDED_QUESTION, 'expected': {'answerable': False}},
    'transfer': {'question': TRANSFER_QUESTION,
                 'expected': {'worker_write_allowed': False, 'release_allowed': False}},
}
CORRECTED_CONTEXT = ('Only the Rust Core writes the SQLite canonical store. Python workers may not '
                     'write it directly. The release is FROZEN pending the Owner gate; publication '
                     'without that gate is not allowed.')


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def score(text: str, task: str) -> str:
    """A deliberately finite rubric, not a natural-language judge or accuracy estimate."""
    if not isinstance(text, str) or not text.strip():
        return 'INCORRECT'
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate answer key')
            result[key] = value
        return result
    try:
        answer = json.loads(text, object_pairs_hook=unique)
    except (ValueError, TypeError):
        return 'REVIEW_REQUIRED'
    expected = RUBRIC[task]['expected']
    if not isinstance(answer, dict) or answer.keys() != expected.keys():
        return 'REVIEW_REQUIRED'
    if any(type(answer[key]) is not type(value) for key, value in expected.items()):
        return 'REVIEW_REQUIRED'
    return 'CORRECT' if answer == expected else 'INCORRECT'


def answer_binding(body: dict, task: str, *, retest: bool = False) -> dict:
    """Bind the actual persisted request/context; absent assets never become asset evidence."""
    if not isinstance(body, dict):
        raise ValueError('missing answer body')
    request = body.get('execution_request') if retest else body.get('request')
    answer = body.get('answer')
    identity = body.get('retest_task_id' if retest else 'answer_id')
    if not identity or not isinstance(request, dict) or not isinstance(answer, dict):
        raise ValueError('missing answer/request identity')
    task_request = request.get('request') if retest else request
    if not isinstance(task_request, dict):
        raise ValueError('missing nested retest request')
    if task_request.get('max_tokens') != 2048 or request.get('timeout_s') != 120:
        raise ValueError('request differs from fixed generation budget')
    if (body.get('question') != RUBRIC[task]['question']
            or task_request.get('question') != RUBRIC[task]['question']
            or task_request.get('knowledge_id') != body.get('knowledge_id')
            or not body.get('knowledge_id')):
        raise ValueError('task or knowledge binding mismatch')
    context_hash = request.get('context_sha256')
    if (not isinstance(context_hash, str) or len(context_hash) != 64
            or any(c not in '0123456789abcdef' for c in context_hash)):
        raise ValueError('missing immutable context digest')
    if not retest and not body.get('client_request_id'):
        raise ValueError('missing frozen client request identity')
    if (not isinstance(answer.get('answer'), str) or not answer['answer'].strip()
            or not answer.get('model') or answer.get('finish_reason') != 'stop'
            or answer.get('truncated') is True):
        raise ValueError('incomplete answer or model conditions')
    authorization = body.get('context_authorization')
    if not isinstance(authorization, dict):
        raise ValueError('missing context authorization evidence')
    # Preserve the entire authorization, including any Core asset proof and member snapshots.
    # This probe exercises legacy knowledge only; it must not qualify an unexercised asset grant.
    if authorization.get('mode') != 'legacy_knowledge_eligibility_only':
        raise ValueError('asset/scoped context requires separately qualified fixture')
    if 'asset_context' in request or 'asset_context' in task_request:
        raise ValueError('asset proof cannot be silently treated as legacy knowledge')
    return {'answer_id': identity, 'client_request_id': body.get('client_request_id'),
            'request': request, 'request_sha256': digest(request),
            'context_sha256': context_hash, 'knowledge_id': body['knowledge_id'],
            'authorization_snapshot': authorization,
            'authorization_sha256': digest(authorization),
            'asset_qualification': 'NOT_PROVIDED_NOT_QUALIFIED',
            'model': answer['model'], 'answer_sha256': digest(answer['answer']),
            'max_tokens': task_request.get('max_tokens'),
            'timeout_s': request.get('timeout_s'),
            'rubric_sha256': digest(RUBRIC), 'score': score(answer['answer'], task)}


def assess(stages: list[dict]) -> dict:
    """Recompute claims from bodies, never trust caller-supplied pass/link booleans."""
    result = {'status': 'INCOMPLETE', 'learning_improvement': 'NOT_ESTABLISHED',
              'asset_effect': 'NOT_QUALIFIED', 'rubric': RUBRIC, 'rubric_sha256': digest(RUBRIC)}
    result['negative_controls'] = {
        'wrong_writer': score('{"writer":"Python","frozen":false}', 'original'),
        'empty_answer': score('', 'original'),
        'negation': score('{"writer":"Not Rust Core","frozen":true}', 'original'),
    }
    try:
        names = [entry['stage'] for entry in stages]
        if len(names) != len(set(names)):
            raise ValueError('duplicate stage')
        by_name = {entry['stage']: entry for entry in stages}
        for entry in stages:
            expected = (403,) if entry['stage'] == 'machine_cannot_accept_correction' else (200, 201, 202)
            if entry.get('problem') or ('status' in entry and entry['status'] not in expected):
                raise ValueError('protocol stage failed')
        frozen = by_name['frozen_rubric']
        if frozen.get('rubric') != RUBRIC or frozen.get('rubric_sha256') != digest(RUBRIC):
            raise ValueError('rubric changed or missing')
        if names.index('frozen_rubric') > names.index('machine_answer'):
            raise ValueError('rubric not frozen before inference')
        bodies = {name: by_name[name]['body'] for name in
                  ('machine_answer', 'machine_answered_out_of_scope', 'transfer_before')}
        original = answer_binding(bodies['machine_answer'], 'original')
        refusal = answer_binding(bodies['machine_answered_out_of_scope'], 'abstention')
        before = answer_binding(bodies['transfer_before'], 'transfer')
        result['bindings'] = {'original': original, 'abstention': refusal, 'transfer_before': before}
        if original['context_sha256'] != hashlib.sha256(CONTEXT.encode()).hexdigest():
            raise ValueError('baseline context differs from frozen synthetic input')
        if len({b['client_request_id'] for b in (original, refusal, before)}) != 3:
            raise ValueError('independent requests reused')
        if any(b['knowledge_id'] != original['knowledge_id']
               or b['context_sha256'] != original['context_sha256']
               or b['model'] != original['model'] for b in (refusal, before)):
            raise ValueError('baseline conditions differ')
        if refusal['score'] != 'CORRECT':
            raise ValueError('abstention control requires review')
        if before['score'] == 'REVIEW_REQUIRED':
            result.update(status='TRANSFER_BASELINE_REVIEW_REQUIRED',
                          reason='independent baseline cannot be scored by the frozen rubric')
            return result
        if original['score'] == 'CORRECT':
            if any(name in by_name for name in ('human_correction', 'machine_retest', 'transfer_after')):
                raise ValueError('correct answer was labelled failed')
            if before['score'] != 'CORRECT':
                result.update(status='TRANSFER_FAILURE_REVIEW',
                              reason='original is correct but independent task failed; do not correct original')
                return result
            result['status'] = 'NO_FAILURE_OBSERVED'
            return result
        if original['score'] != 'INCORRECT':
            raise ValueError('original answer requires human review')
        correction = by_name['human_correction']['body']
        if any(correction.get(key) != value for key, value in {
            'answer_id': original['answer_id'], 'corrects_knowledge_id': original['knowledge_id'],
            'question': QUESTION, 'machine_answer': bodies['machine_answer']['answer']['answer'],
            'corrected_answer': CORRECTED_CONTEXT,
        }.items()):
            raise ValueError('correction does not bind the failed answer')
        failed = correction['failed_task_id']
        candidate = correction['correction_candidate_id']
        retest_body = by_name['machine_retest']['body']
        prior = retest_body['prior']['conditions']
        if (failed != 'evaluation_' + original['answer_id']
                or prior.get('answer_id') != original['answer_id']
                or prior.get('request') != original['request']
                or prior.get('answer') != bodies['machine_answer']['answer']
                or prior.get('correction') != correction):
            raise ValueError('failed answer/request not bound in persisted retest prior')
        retest = answer_binding(retest_body, 'original', retest=True)
        after = answer_binding(by_name['transfer_after']['body'], 'transfer')
        result['bindings'].update(retest=retest, transfer_after=after)
        readback = by_name['retest_readback']['body']
        conditions = readback.get('conditions')
        if isinstance(conditions, str):
            conditions = json.loads(conditions)
        if (retest_body.get('retest_of') != failed or readback.get('retest_of') != failed
                or readback.get('task_id') != retest['answer_id'] or conditions != retest_body):
            raise ValueError('persisted retest lineage mismatch')
        if (not failed or not candidate or candidate == original['knowledge_id']
                or retest['knowledge_id'] != candidate or after['knowledge_id'] != candidate
                or retest['context_sha256'] != after['context_sha256']
                or retest['context_sha256'] != hashlib.sha256(CORRECTED_CONTEXT.encode()).hexdigest()
                or after['client_request_id'] in {b['client_request_id'] for b in (original, refusal, before)}
                or after['answer_id'] in {original['answer_id'], before['answer_id'], retest['answer_id']}
                or any(b['model'] != original['model'] for b in (retest, after))):
            raise ValueError('intervention or independent task identity mismatch')
        if any(b['max_tokens'] != original['max_tokens'] or b['timeout_s'] != original['timeout_s']
               for b in (before, retest, after)):
            raise ValueError('generation budget changed')
        if retest['score'] != 'CORRECT' or after['score'] != 'CORRECT':
            raise ValueError('correction/transfer answer failed fixed rubric')
        result['status'] = 'FINITE_CORRECTION_VERIFIED'
        result['transfer_observation'] = ('FINITE_TASK_DELTA' if before['score'] == 'INCORRECT'
                                          else 'NO_MEASURED_DELTA')
        result['intervention'] = 'changed accepted knowledge context; not parameter learning'
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        result.update(status='REVIEW_REQUIRED', reason=str(exc))
    return result


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProbeTransportFailure(RuntimeError):
    """The request may have executed; stop without retry or guessed outcome."""


def call_core(client, receipt, base, method, path, token, body=None, headers=None):
    timeout = 30
    if path in {'/api/v1/machine/answers', '/api/v1/machine/retests'}:
        budget = body.get('timeout_s', 120) if isinstance(body, dict) else 120
        if type(budget) is not int or not 1 <= budget <= 120:
            raise ValueError('model request timeout outside Core contract')
        # colearning.rs answer/retest admission is bounded at 10s. The additional
        # 5s is client transport tolerance, not a claim of a total Core bound.
        timeout = budget + 15

    def unknown(error_type):
        receipt.stage('transport_failure', problem='request outcome UNKNOWN; no retry',
                      method=method, path=path, transport_timeout_s=timeout,
                      request_sha256=digest(body), error_type=error_type)
        receipt.block('transport', 'request outcome UNKNOWN; no automatic retry')
        raise ProbeTransportFailure('request outcome UNKNOWN') from None

    try:
        status, response = client.call(base, method, path, token, body,
                                       timeout=timeout, extra_headers=headers)
    except (TimeoutError, OSError, urllib.error.URLError) as error:
        unknown(type(error).__name__)
    # The shared client normalizes URLError/OSError to status zero. Its error text
    # is deliberately neither retained nor printed: it can contain URL details.
    if status == 0:
        unknown('CLIENT_TRANSPORT_STATUS_ZERO')
    return status, response


class Receipt:
    def __init__(self, *, live_execution: bool = False) -> None:
        self.stages: list[dict] = []
        self.blocked: dict[str, str] = {}
        self.live_execution = live_execution

    def stage(self, name: str, **fields) -> None:
        self.stages.append({"stage": name, "at": datetime.now(timezone.utc).isoformat(), **fields})

    def block(self, name: str, reason: str) -> None:
        self.blocked[name] = reason

    @property
    def failed_stage(self) -> str | None:
        for entry in self.stages:
            if entry.get("problem"):
                return entry["stage"]
            status = entry.get("status")
            expected = (403,) if entry["stage"] == "machine_cannot_accept_correction" else (200, 201, 202)
            if status is not None and status not in expected:
                return entry["stage"]
            if entry.get("links_to_failure") is False:
                return entry["stage"]
        return None

    def document(self, **extra) -> dict:
        # Tests/constructed receipts never inherit a claim of real inference. Even main's
        # explicit live attempt is not evidence of inference before a model response arrives.
        observed = []
        if self.live_execution:
            for entry in self.stages:
                body = entry.get('body')
                answer = body.get('answer') if isinstance(body, dict) else None
                if (entry['stage'] in {'machine_answer', 'machine_answered_out_of_scope',
                                       'transfer_before', 'machine_retest', 'transfer_after'}
                        and entry.get('status') == 200 and isinstance(answer, dict)
                        and answer.get('engine') == 'python-worker-machine-answer'
                        and isinstance(answer.get('answer'), str) and answer['answer'].strip()
                        and answer.get('model') and answer.get('finish_reason') == 'stop'):
                    observed.append(entry['stage'])
        evidence_class = ('LIVE_CORE_MODEL_RESPONSE_OBSERVED' if observed else
                          'LIVE_ATTEMPT_NO_MODEL_EVIDENCE' if self.live_execution else
                          'SYNTHETIC_OR_UNEXECUTED')
        return {
            "schema": "aaos.colearning-real-model-receipt/v3",
            "evidence_class": evidence_class,
            "execution_mode": 'LIVE_LOCAL_ATTEMPT' if self.live_execution else 'SYNTHETIC_OR_UNEXECUTED',
            "observed_model_response_stages": observed,
            "what_is_real": (["live Core responses carrying local model inference metadata for "
                              "the listed observed stages only; not full-loop completion"]
                             if observed else []),
            "what_is_still_a_fixture": [
                "the person: this script picks the question, judges the answer wrong and writes the "
                "correction, so a run is not evidence that a human reviewed anything",
                "the source file, which this script writes",
            ],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "failed_stage": self.failed_stage,
            "quality_assessment": assess(self.stages),
            "stages": self.stages,
            "blocked": self.blocked,
            **extra,
        }


def unmet_prerequisites() -> dict[str, str]:
    missing: dict[str, str] = {}
    if not os.environ.get("ARCHEAXIS_PYTHON"):
        missing["ARCHEAXIS_PYTHON"] = (
            "the interpreter the Core uses for its scheduler worker; without it a review is recorded "
            "as unscheduled and the run could not observe the whole loop")
    return missing


def main() -> int:
    global RUN
    if len(sys.argv) < 2:
        print("usage: colearning_real_model_smoke.py <core-executable>")
        return 2
    core = Path(sys.argv[1])
    if not core.is_file():
        print(f"core executable not found: {core}")
        return 2

    receipt = Receipt(live_execution=True)
    receipt.stage('frozen_rubric', rubric=json.loads(json.dumps(RUBRIC)),
                  rubric_sha256=digest(RUBRIC),
                  negative_controls={'wrong_writer': score('{"writer":"Python","frozen":false}', 'original'),
                                     'empty_answer': score('', 'original')},
                  scope='finite synthetic questions; no human learning or asset-effect qualification')
    for name, reason in unmet_prerequisites().items():
        receipt.block(name, reason)

    launcher = _load("launcher_colearning", REPO / "scripts/release/backend_launcher.py")
    client = _load("client_colearning", REPO / "shared/core_client.py")

    RUN = run_directory()
    (RUN / "core").mkdir(parents=True)
    shutil.copy2(core, RUN / "core" / "archeaxis-api.exe")
    (RUN / "data").mkdir(parents=True)
    (RUN / "worker-profile.json").write_text(json.dumps({
        "schema": "archeaxis.worker-profile/v1",
        "python": os.environ.get("ARCHEAXIS_PYTHON", sys.executable),
        "script": str(REPO / "services/python-workers/transport/text_ndjson.py"),
        "staging": "data/worker-staging",
        # The machine answer route is declared here because it is what this probe drives; a launch
        # that does not declare it has no capability to answer with, which the probe reports as
        # blocked rather than as a failure of the loop.
        "routes": [
            {"capability": "machine.answer",
             "script": str(REPO
                           / "services/python-workers/machine/worker_machine_answer.py")},
        ],
    }, indent=2), encoding="utf-8")

    launcher.ROOT = RUN
    child, base, _doc, tokens = launcher.start(RUN / "data", 0)
    human = launcher.credential(tokens, "human")["x-archeaxis-launch-token"]
    machine_token = None
    for principal in ("machine",):
        try:
            machine_token = launcher.credential(tokens, principal)["x-archeaxis-launch-token"]
        except Exception:  # noqa: BLE001 - a missing machine principal is reported below
            machine_token = None

    def call(method: str, path: str, token: str, body=None, headers=None):
        return call_core(client, receipt, base, method, path, token, body, headers)

    try:
        # 1. A real file becomes an accepted knowledge item through the product's own text route.
        status, imported = call("POST", "/api/v1/imports", human,
                                client.import_request("loop.txt", CONTEXT.encode()))
        receipt.stage("import_source", status=status, body=imported)
        if status != 202:
            receipt.stage("import_source", problem="import refused")
            return report(receipt)
        source_id = imported["source_id"]

        status, _ = call("POST", "/api/v1/jobs", human,
                         {"job_id": "loop-text", "kind": "text", "input_ref": source_id})
        status, _ = call("POST", "/api/v1/jobs/loop-text/executions", human,
                         {"deadline_ms": 120000},
                         headers={"idempotency-key": "loop-text"})
        state = None
        for _ in range(120):
            _, job = call("GET", "/api/v1/jobs/loop-text", human)
            state = job.get("state") if isinstance(job, dict) else None
            if state in ("succeeded", "failed", "cancelled"):
                break
            time.sleep(1)
        receipt.stage("text_transform", status=status, state=state)
        if state != "succeeded":
            receipt.stage("text_transform", problem=f"transform state {state}")
            return report(receipt)

        # 2. Knowledge from that transform, then accepted by a human review. The projection is read
        #    back first because the request names the transform and the exact quoted span, which is
        #    what binds the knowledge to a position in the source rather than to a copy of the text.
        status, transform = call("GET", f"/api/v1/sources/{source_id}/jobs/loop-text/transform", human)
        receipt.stage("read_transform", status=status,
                      transform_id=(transform or {}).get("transform_id"),
                      content_chars=len((transform or {}).get("content", "")))
        if status != 200:
            receipt.stage("read_transform", problem="the transform could not be read back")
            return report(receipt)
        content = transform["content"]
        status, created = call("POST", "/api/v1/knowledge-items/from-transform", human, {
            "knowledge_type": "FACTUAL_CLAIM",
            "body": content,
            "source_id": source_id,
            "job_id": "loop-text",
            "transform_id": transform["transform_id"],
            # The whole projection is the quoted span, and the offsets are in UTF-16 code units
            # because that is what the store records.
            "selection_start_utf16": 0,
            "selection_end_utf16": len(content.encode("utf-16-le")) // 2,
            "quote": content,
        })
        receipt.stage("create_knowledge", status=status, body=created)
        if status not in (200, 201):
            receipt.stage("create_knowledge", problem="knowledge creation refused")
            return report(receipt)
        knowledge_id = created.get("knowledge_id") or created.get("id")

        status, _ = call("POST", f"/api/v1/knowledge-items/{knowledge_id}/review-decisions", human,
                         {"action": "accepted", "reviewer": "owner"})
        receipt.stage("accept_knowledge", status=status)

        # 3. The real model answers the answerable question.
        status, answered = call("POST", "/api/v1/machine/answers", human,
                                {"knowledge_id": knowledge_id, "question": QUESTION,
                                 "client_request_id": "colearning-original-v2",
                                 "timeout_s": 120})
        receipt.stage("machine_answer", status=status, body=answered)
        if status != 200:
            # A host without a model is a real state, and the reason is the worker's own words.
            receipt.block("local_model", str(answered)[:400])
            return report(receipt)
        answer_text = answered["answer"]["answer"]

        # 4. A valid refusal is a passing grounding control, never a model failure.
        status, ungrounded = call("POST", "/api/v1/machine/answers", human,
                                  {"knowledge_id": knowledge_id, "question": UNGROUNDED_QUESTION,
                                   "client_request_id": "colearning-abstention-v2",
                                   "timeout_s": 120})
        receipt.stage("machine_answered_out_of_scope", status=status, body=ungrounded)
        if status != 200:
            return report(receipt)
        status, transfer_before = call('POST', '/api/v1/machine/answers', human, {
            'knowledge_id': knowledge_id, 'question': TRANSFER_QUESTION,
            'client_request_id': 'colearning-transfer-before-v2', 'timeout_s': 120})
        receipt.stage('transfer_before', status=status, body=transfer_before)
        if status != 200:
            return report(receipt)
        try:
            answer_binding(answered, 'original')
            answer_binding(ungrounded, 'abstention')
            answer_binding(transfer_before, 'transfer')
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            receipt.stage('answer_binding', problem=str(exc))
            return report(receipt)
        # Only a failed bounded answer may enter the correction path. Unparsed prose remains
        # REVIEW_REQUIRED; a correct answer is NO_FAILURE_OBSERVED, not an invented failure.
        if (score(answer_text, 'original') != 'INCORRECT'
                or score(ungrounded.get('answer', {}).get('answer', ''), 'abstention') != 'CORRECT'
                or score(transfer_before.get('answer', {}).get('answer', ''), 'transfer') == 'REVIEW_REQUIRED'):
            return report(receipt)

        # 5. The human correction, through the product's own route.
        status, corrected = call("POST", "/api/v1/machine/corrections", human, {
            "answer_id": answered["answer_id"],
            "knowledge_id": knowledge_id,
            "question": QUESTION,
            "machine_answer": answer_text,
            "corrected_answer": CORRECTED_CONTEXT,
            "reviewer": "scripted-human-fixture",
            "error_note": "fixed synthetic rubric original/v2: structured answer differs from expected",
        })
        receipt.stage("human_correction", status=status, body=corrected)
        if status != 200:
            receipt.stage("human_correction", problem="the correction was refused")
            return report(receipt)
        candidate = corrected["correction_candidate_id"]
        failed_task = corrected["failed_task_id"]
        status, accepted_correction = call(
            "POST", f"/api/v1/knowledge-items/{candidate}/review-decisions", human,
            {"action": "accepted", "reviewer": "scripted-human-fixture"})
        receipt.stage("accept_correction_fixture", status=status, body=accepted_correction)
        if status != 200:
            return report(receipt)

        # 6. The retest: the same question again, linked to the failure.
        status, retest = call("POST", "/api/v1/machine/retests", human, {
            "retest_of": failed_task,
            "knowledge_id": candidate,
            "question": QUESTION,
            "timeout_s": 120,
        })
        receipt.stage("machine_retest", status=status, body=retest)
        if status != 200:
            receipt.stage("machine_retest", problem=f"retest refused: {retest}")
            return report(receipt)
        retest_id = retest["retest_task_id"]

        # 7. Read it back from the store, so the link is a fact about the database and not only about
        #    the response that created it.
        status, readback = call("GET", f"/api/v1/machine/tasks/{retest_id}", machine_token)
        receipt.stage("retest_readback", status=status, body=readback,
                      links_to_failure=(readback.get("retest_of") == failed_task
                                        if isinstance(readback, dict) else False))

        # Independent application task uses a NEW answer request. Core retests intentionally
        # keep the original question; changing that contract would erase the comparison.
        status, transfer_after = call('POST', '/api/v1/machine/answers', human, {
            'knowledge_id': candidate, 'question': TRANSFER_QUESTION,
            'client_request_id': 'colearning-transfer-after-v2', 'timeout_s': 120})
        receipt.stage('transfer_after', status=status, body=transfer_after)

        # 8. Review remains forbidden to machines after the scripted human review.
        status, _ = call("POST", f"/api/v1/knowledge-items/{candidate}/review-decisions",
                         machine_token, {"action": "accepted", "reviewer": "machine"})
        receipt.stage("machine_cannot_accept_correction", status=status,
                      note="403 is the required answer")

        return report(receipt, correction_candidate=candidate, failed_task=failed_task,
                      retest_task=retest_id, knowledge_id=knowledge_id)
    except ProbeTransportFailure:
        return report(receipt)
    finally:
        launcher.stop(child)


def report(receipt: Receipt, **extra) -> int:
    document = receipt.document(**extra)
    out = RUN / "receipt.json" if RUN is not None else None
    if out is not None and RUN.exists():
        out.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(document, ensure_ascii=False, indent=2)[:4000])
    # A run that reached every stage is a pass even when a prerequisite was noted on the way: the
    # note belongs in the receipt, and letting it decide the verdict would mark a complete run as
    # incomplete. A prerequisite only decides the verdict when it actually stopped the run.
    required = {
        "import_source", "text_transform", "read_transform", "create_knowledge",
        "accept_knowledge", "machine_answer", "machine_answered_out_of_scope",
        "frozen_rubric", "transfer_before",
    }
    quality = document['quality_assessment']
    if quality['status'] == 'FINITE_CORRECTION_VERIFIED':
        required.update({'human_correction', 'accept_correction_fixture', 'machine_retest',
                         'retest_readback', 'machine_cannot_accept_correction', 'transfer_after'})
    reached_the_end = not receipt.failed_stage and required.issubset(
        entry["stage"] for entry in receipt.stages)
    if receipt.blocked and not reached_the_end:
        print("\nBLOCKED:", json.dumps(receipt.blocked, ensure_ascii=False))
        return 3
    if receipt.failed_stage:
        print(f"\nFAILED at {receipt.failed_stage}")
        return 1
    if not reached_the_end:
        print("\nINCOMPLETE: the probe did not reach all required stages")
        return 1
    if quality['status'] not in {'NO_FAILURE_OBSERVED', 'FINITE_CORRECTION_VERIFIED'}:
        print('\nQUALITY NOT QUALIFIED:', quality['status'])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
