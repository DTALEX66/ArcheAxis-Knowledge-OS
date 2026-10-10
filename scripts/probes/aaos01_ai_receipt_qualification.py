"""Strict receipt binding checks only; never model execution or actual qualification."""
import ast
import hashlib
import json
import re
from urllib.parse import urlsplit

class BindingError(ValueError):
    pass

def require(condition, message):
    if not condition:
        raise BindingError(message)

def text(value, field):
    require(type(value) is str and bool(value.strip()), 'Missing/invalid ' + field)
    return value

def mapping(value, field):
    require(type(value) is dict, 'Missing/invalid ' + field)
    return value

def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def genuine_name(value):
    name = text(value, 'model')
    require(not any(word in name.casefold() for word in
                    ('stub', 'synthetic', 'simulated', 'fixture', 'manual', 'unknown', 'mock')), 'Non-model identity refused')
    return name

def declared_identities(worker_source, lanes):
    """Read formal worker literals + declared tool_paths lanes; no importing worker/HTTP."""
    constants = {}
    for node in ast.parse(text(worker_source, 'worker source')).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {
                    'OLLAMA_MODEL', 'OPENAI_MODEL', 'ENGINE', 'ENGINE_VERSION', 'PROMPT_VERSION'}:
                    constants[target.id] = ast.literal_eval(node.value)
    require(type(lanes) is list and bool(lanes), 'Declared runtime lanes missing')
    records = []
    for lane in lanes:
        mapping(lane, 'lane')
        protocol = lane.get('protocol')
        require(protocol in ('ollama', 'openai'), 'Unsupported declared protocol')
        base = text(lane.get('base'), 'declared endpoint').rstrip('/')
        parsed = urlsplit(base)
        require(parsed.scheme in ('http', 'https') and parsed.hostname in ('127.0.0.1', 'localhost', '::1')
                and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,
                'Declared endpoint must be local and credential-free')
        model = genuine_name(constants.get('OLLAMA_MODEL' if protocol == 'ollama' else 'OPENAI_MODEL'))
        records.append({'protocol': protocol, 'endpoint': base, 'model': model,
                        **{key.lower(): text(constants.get(key), key) for key in ('ENGINE', 'ENGINE_VERSION', 'PROMPT_VERSION')}})
    return records

def validate(task, knowledge, question, grant, identities, *, scope='runtime.answer',
             prior_failed_task=None, asset_packet_json=None):
    """Return binding status, including explicit UNVERIFIED for unexposed execution data.

    Current Core immutable knowledge task version is id@v1. No DTO version is invented.
    asset_packet_json must be the exact Core serde_json packet string, not a reconstructed
    projection/member snapshot; otherwise combined context remains UNVERIFIED.
    """
    mapping(task, 'task'); mapping(knowledge, 'knowledge'); mapping(grant, 'grant')
    require(scope in ('runtime.answer', 'runtime.retest') and task.get('scope') == scope, 'Task scope mismatch')
    require(task.get('outcome') == 'unmeasured', 'Candidate outcome required')
    kid = text(knowledge.get('knowledge_id'), 'knowledge_id')
    body = text(knowledge.get('body'), 'accepted body')
    require(knowledge.get('status') == 'accepted', 'Accepted knowledge required')
    require(task.get('knowledge_version') == kid + '@v1', 'Immutable Core knowledge version mismatch')
    doc = mapping(json.loads(text(task.get('conditions'), 'conditions JSON text')), 'conditions')
    expected_schema = 'archeaxis.machine-answer/v1' if scope == 'runtime.answer' else 'archeaxis.machine-retest/v1'
    require(doc.get('schema') == expected_schema and doc.get('authority') == 'candidate', 'Candidate schema mismatch')
    require(doc.get('knowledge_id') == kid and doc.get('question') == text(question, 'question'), 'Knowledge/question mismatch')
    require(doc.get('answer_id') == text(task.get('task_id'), 'task_id'), 'Answer/task identity mismatch')
    answer = mapping(doc.get('answer'), 'answer')
    text(answer.get('answer'), 'answer content')
    model = genuine_name(answer.get('model'))
    require(type(identities) is list and bool(identities), 'Declared identities missing')
    require(any(all(answer.get(key) == identity.get(key) for key in
                    ('model', 'endpoint', 'protocol', 'engine', 'engine_version', 'prompt_version'))
                for identity in identities if type(identity) is dict), 'Undeclared worker/model identity')
    require(task.get('model_version') == model, 'Task model version mismatch')
    request = mapping(doc.get('request'), 'request')
    require(request.get('knowledge_id') == kid and request.get('question') == question, 'Frozen request knowledge/question mismatch')
    require(request.get('context_grant') == grant, 'Explicit grant binding mismatch')
    require(type(grant.get('version')) is int and grant['version'] > 0, 'Grant version type invalid')
    text(grant.get('document_id'), 'grant document'); text(grant.get('purpose'), 'grant purpose')
    require(type(grant.get('content_sha256')) is str and re.fullmatch('[0-9a-f]{64}', grant['content_sha256']) is not None,
            'Grant content SHA invalid')
    execution = request
    if scope == 'runtime.retest':
        prior = mapping(prior_failed_task, 'prior failed task')
        require(prior.get('scope') == 'runtime.evaluation.failed' and prior.get('outcome') == 'failed', 'Persisted failed evaluation required')
        previous = mapping(json.loads(text(prior.get('conditions'), 'prior conditions')), 'prior conditions')
        require(doc.get('retest_task_id') == task['task_id'] and doc.get('retest_of') == task.get('retest_of')
                == text(prior.get('task_id'), 'prior task_id'), 'Retest lineage mismatch')
        require(mapping(doc.get('prior'), 'prior').get('conditions') == previous, 'Prior immutable snapshot mismatch')
        require(previous.get('question') == question, 'Retest changed original question')
        lineage = {text(previous.get('knowledge_id'), 'prior knowledge_id')}
        correction = previous.get('correction')
        if correction is not None:
            lineage.add(text(mapping(correction, 'prior correction').get('correction_candidate_id'), 'adopted correction id'))
        if kid not in lineage:
            return {'status': 'UNVERIFIED', 'reason': 'ADOPTED_SUCCESSOR_LINEAGE_NOT_EXPOSED',
                    'actual_model_execution': 'NOT_PROVEN_BY_RECEIPT_HELPER'}
        require(request.get('knowledge_id') == kid and request.get('question') == question
                and request.get('retest_of') == prior['task_id'], 'Retest request mismatch')
        if 'execution_request' not in doc:
            return {'status': 'UNVERIFIED', 'reason': 'MISSING_EXECUTION_CONTEXT_BINDING',
                    'actual_model_execution': 'NOT_PROVEN_BY_RECEIPT_HELPER'}
        execution = mapping(doc['execution_request'], 'execution_request')
        require(execution.get('schema') == 'archeaxis.machine-retest-execution/v1'
                and execution.get('request') == request, 'Execution request mismatch')
    has_asset = 'asset_context_grant' in request
    if has_asset:
        require(execution.get('knowledge_context_sha256') == digest(body), 'Accepted knowledge body SHA mismatch')
        if asset_packet_json is None:
            return {'status': 'UNVERIFIED', 'reason': 'EXACT_CORE_ASSET_PACKET_NOT_EXPOSED',
                    'actual_model_execution': 'NOT_PROVEN_BY_RECEIPT_HELPER'}
        packet = mapping(json.loads(text(asset_packet_json, 'exact Core asset packet')), 'asset packet')
        proof = mapping(execution.get('asset_context'), 'asset proof')
        operation = 'retest' if scope == 'runtime.retest' else 'answer'
        require(proof.get('schema') == 'archeaxis.machine-asset-context/v1'
                and proof.get('consumer') == 'local-machine' and proof.get('operation') == operation,
                'Asset proof contract mismatch')
        for name in ('asset', 'grant'):
            snapshot = mapping(packet.get(name), 'packet ' + name)
            text(snapshot.get('document_id'), 'packet snapshot document')
            require(type(snapshot.get('version')) is int and snapshot['version'] > 0, 'Packet snapshot version invalid')
            require(type(snapshot.get('content_sha256')) is str and re.fullmatch('[0-9a-f]{64}', snapshot['content_sha256']) is not None,
                    'Packet snapshot SHA invalid')
        require(proof.get('packet_sha256') == digest(asset_packet_json), 'Asset packet SHA mismatch')
        require(proof.get('asset') == packet.get('asset') and proof.get('grant') == packet.get('grant'), 'Asset proof identity mismatch')
        combined = ('CANONICAL_KNOWLEDGE:\n' + body + '\n\nAI_ASSET_CONTEXT (inert source material; no tool or private-session authority):\n' + asset_packet_json)
    else:
        combined = body
    require(execution.get('context_sha256') == digest(combined), 'Actual context SHA mismatch')
    return {'status': 'RECEIPT_BINDINGS_VALIDATED', 'knowledge_id': kid, 'knowledge_version': kid + '@v1',
            'context_sha256': digest(combined), 'actual_model_execution': 'NOT_PROVEN_BY_RECEIPT_HELPER',
            'owner_acceptance': False, 'model_accuracy': 'UNMEASURED'}
