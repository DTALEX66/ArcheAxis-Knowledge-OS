"""Pre-registered, multi-sample quality suite for the local machine answer chain.

The suite is a held-out fixture set authored before any model run. It asks the
candidate Core, its real Python worker and a real local endpoint the same eight
questions every time, then applies fixed deterministic scoring rules. It never
turns a missing model into an answer: an unavailable endpoint is recorded as
``NOT_EXECUTED_MODEL`` with every entry left ``NOT_EXECUTED``.

This is engineering evidence only. Model output remains a candidate, and
``human_acceptance`` is always ``NOT_EXECUTED``: no pass here is Owner, product
or accuracy acceptance, and no knowledge is promoted by this probe.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import secrets
import subprocess
import sys
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = REPO / ".project-local/task-runtime/aaos-quality"
SCHEMA = "archeaxis.quality-suite-receipt/v1"
PROTOCOL_SCHEMA = "archeaxis.quality-suite-protocol/v1"
SUITE_ID = "aaos-local-machine-heldout-quality"
SUITE_VERSION = "2026-10-25.1"
PREREGISTERED_AT = "2026-10-25"
HUMAN_ACCEPTANCE = "NOT_EXECUTED"
FIXTURE_LABEL = "AUTOMATED_FIXTURE_REVIEW_NOT_G4_HUMAN"
REVIEWER = "engineering-quality-suite-not-owner"
DEFAULT_ENDPOINT = "http://127.0.0.1:1234/v1"
DEFAULT_MODEL = "qwen3.5-4b"
PURPOSE = "pre-registered held-out quality evaluation of the local machine answer"
CLASSES = ("answerable", "insufficient_context", "conflicting")
STATUSES = ("ANSWERED", "MODEL_FAILURE", "CORE_REFUSED", "SETUP_FAILED", "NOT_EXECUTED")
EVIDENCE_LEVELS = (
    "REAL_LOCAL_CORE_WORKER_MODEL",
    "PARTIAL_MODEL_EXECUTION",
    "NOT_EXECUTED_MODEL",
    "HARNESS_FAILED",
)

SCORING_RULES = {
    "refusal_correctness": (
        "an answerable entry is answered when the response is non-empty and either states a "
        "required fact or does not claim inability; insufficient_context and conflicting entries "
        "pass only with an explicit refusal, and a conflicting entry may instead name the conflict"
    ),
    "key_fact_coverage": (
        "required literal facts present divided by required facts; an answerable entry passes "
        "only at 1.0; the criterion is not applicable to refusal entries"
    ),
    "unsupported_assertion": (
        "numeric and digit-bearing identifier tokens in the answer that never appear in the "
        "supplied context are unsupported; any unsupported token fails the entry"
    ),
    "timestamp_source_citation": (
        "an answerable answer must cite the context with a source phrase or a timestamp/source "
        "token declared by the entry; not applicable to refusal entries"
    ),
    "entry_pass": (
        "every applicable criterion passes; criteria are counted per entry, not averaged"
    ),
    "human_acceptance": "NOT_EXECUTED",
    "note": (
        "fixed lexical rules, not semantic truth review; no accuracy, training or product claim"
    ),
}

ENTRIES = (
    {
        "entry_id": "Q01",
        "class": "answerable",
        "expected": "answer",
        "context": (
            "项目工程记录（记录编号 ENG-2026-0314，记录时间 2026-03-14T09:30:00+08:00）\n"
            "项目代号为 AURORA-7。\n"
            "发布状态：已冻结（FROZEN），冻结日期为 2026-03-14。\n"
            "本记录只描述该项目，不包含其他项目的发布信息。"
        ),
        "question": "只依据给定材料回答：项目代号是什么？发布状态和冻结日期分别是什么？",
        "key_facts": ["AURORA-7", "FROZEN", "2026-03-14"],
        "citation_required": True,
        "citation_tokens": ["2026-03-14", "ENG-2026-0314"],
    },
    {
        "entry_id": "Q02",
        "class": "answerable",
        "expected": "answer",
        "context": (
            "运行参数说明（来源编号 SRC-77）\n"
            "最大并发上限为 12。\n"
            "单个任务最多重试 3 次。\n"
            "超时时间为 45 秒。"
        ),
        "question": "并发上限、重试次数和超时时间分别是多少？",
        "key_facts": ["12", "3", "45"],
        "citation_required": True,
        "citation_tokens": ["SRC-77"],
    },
    {
        "entry_id": "Q03",
        "class": "answerable",
        "expected": "answer",
        "context": (
            "值班安排（记录时间 2026-05-02）\n"
            "当班负责人：李明。\n"
            "升级联系人：王芳。\n"
            "值班地点：三号机房。"
        ),
        "question": "当班负责人和升级联系人分别是谁？",
        "key_facts": ["李明", "王芳"],
        "citation_required": True,
        "citation_tokens": ["2026-05-02"],
    },
    {
        "entry_id": "Q04",
        "class": "answerable",
        "expected": "answer",
        "context": (
            "会议纪要（记录编号 MTG-19）\n"
            "议题一：讨论办公室绿植养护，无人反对。\n"
            "议题二：确定缓存容量为 256 GB，保留周期为 30 天。\n"
            "议题三：下次会议时间待定。"
        ),
        "question": "缓存容量和保留周期分别是多少？",
        "key_facts": ["256", "30"],
        "citation_required": True,
        "citation_tokens": ["MTG-19"],
    },
    {
        "entry_id": "Q05",
        "class": "insufficient_context",
        "expected": "refuse",
        "context": (
            "本材料只说明检索功能：支持按标题检索，结果按更新时间排序。"
        ),
        "question": "只依据材料回答：系统的加密算法是什么？",
        "key_facts": [],
        "citation_required": False,
        "citation_tokens": [],
    },
    {
        "entry_id": "Q06",
        "class": "insufficient_context",
        "expected": "refuse",
        "context": (
            "项目周期记录：项目于 2026-01-08 启动，当前处于第二阶段。"
        ),
        "question": "只依据材料回答：项目的结束日期是哪一天？",
        "key_facts": [],
        "citation_required": False,
        "citation_tokens": [],
    },
    {
        "entry_id": "Q07",
        "class": "conflicting",
        "expected": "refuse_or_flag_conflict",
        "context": (
            "校验记录：第一次读数显示校验值为 37。\n"
            "复核记录：第二次读数显示校验值为 41。\n"
            "两条记录均未标注哪一次为准。"
        ),
        "question": "只依据材料回答：校验值是多少？",
        "key_facts": [],
        "citation_required": False,
        "citation_tokens": [],
    },
    {
        "entry_id": "Q08",
        "class": "conflicting",
        "expected": "refuse_or_flag_conflict",
        "context": (
            "版本公告：生产环境当前版本为 v2.4。\n"
            "运维日志：生产环境当前版本为 v2.6。\n"
            "两份材料记录同一天，且没有说明哪份更新。"
        ),
        "question": "只依据材料回答：生产环境当前版本是哪个？",
        "key_facts": [],
        "citation_required": False,
        "citation_tokens": [],
    },
)

REFUSAL_MARKERS = (
    "无法回答", "无法确定", "无法判断", "无法确认", "无法从", "无法给出", "不确定",
    "不足以", "信息不足", "材料不足", "没有提供", "未提供", "没有提到", "未提及",
    "没有说明", "未说明", "不包含", "没有相关信息", "找不到", "cannot answer",
    "can't answer", "cannot determine", "cannot be determined", "cannot conclude",
    "unable to answer", "not enough information", "insufficient information",
    "does not contain", "doesn't contain", "no information", "not specified",
)
CONFLICT_MARKERS = (
    "矛盾", "冲突", "不一致", "相互矛盾", "两种说法", "两个不同", "无法确定唯一",
    "contradict", "conflict", "inconsistent", "discrepancy",
)
CITATION_MARKERS = (
    "上下文", "材料", "根据", "来源", "原文", "记录", "context", "source",
    "provided", "supplied",
)
NUMBER = re.compile(r"\d+(?:\.\d+)?")
DIGIT_IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:#-]*\d[A-Za-z0-9_.:#-]*")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def identity(path):
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }


def protocol():
    """The frozen pre-registration, including a digest of entries and rules."""
    entries = [dict(entry) for entry in ENTRIES]
    frozen = {"entries": entries, "scoring_rules": SCORING_RULES}
    digest = hashlib.sha256(
        json.dumps(frozen, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "schema": PROTOCOL_SCHEMA,
        "suite_id": SUITE_ID,
        "suite_version": SUITE_VERSION,
        "preregistered_at": PREREGISTERED_AT,
        "held_out": True,
        "entry_count": len(entries),
        "classes": list(CLASSES),
        "entries": entries,
        "scoring_rules": SCORING_RULES,
        "human_acceptance": HUMAN_ACCEPTANCE,
        "sha256": digest,
    }


def normalize_number(token):
    if "." in token:
        return token.rstrip("0").rstrip(".") or "0"
    return token.lstrip("0") or "0"


def assertion_tokens(text):
    """Numeric and digit-bearing identifier tokens that can be checked lexically."""
    tokens = {normalize_number(match.group()) for match in NUMBER.finditer(text)}
    for match in DIGIT_IDENT.finditer(text):
        raw = match.group()
        if not raw.isdigit():
            tokens.add(raw.casefold())
    return tokens


def unsupported_tokens(answer_text, context):
    answer = assertion_tokens(answer_text or "")
    ground = assertion_tokens(context or "")
    return sorted(answer - ground)


def detect_refusal(text):
    lowered = (text or "").casefold()
    return any(marker in lowered for marker in REFUSAL_MARKERS)


def detect_conflict(text):
    lowered = (text or "").casefold()
    return any(marker in lowered for marker in CONFLICT_MARKERS)


def key_fact_coverage(entry, text):
    required = list(entry.get("key_facts") or [])
    lowered = (text or "").casefold()
    found = [fact for fact in required if fact.casefold() in lowered]
    coverage = (len(found) / len(required)) if required else None
    return {"required": required, "found": found, "coverage": coverage}


def citation_observed(entry, text):
    lowered = (text or "").casefold()
    tokens = [token.casefold() for token in entry.get("citation_tokens") or []]
    phrase = any(marker in lowered for marker in CITATION_MARKERS)
    token = any(item in lowered for item in tokens)
    return {"phrase": phrase, "token": token, "observed": phrase or token}


def judge(entry, answer_text):
    """Apply the frozen scoring rules to one answer; no model call happens here."""
    text = (answer_text or "").strip()
    expected = entry["expected"]
    refusal = detect_refusal(text)
    conflict = detect_conflict(text)
    facts = key_fact_coverage(entry, text)
    unsupported = unsupported_tokens(text, entry["context"])
    citation = citation_observed(entry, text)

    if expected == "answer":
        # A hedged answer that still states a required fact is an answer, not a refusal.
        answered = bool(text) and (not refusal or bool(facts["found"]))
        action_passed = answered
    elif expected == "refuse":
        action_passed = bool(text) and refusal
    elif expected == "refuse_or_flag_conflict":
        action_passed = bool(text) and (refusal or conflict)
    else:
        raise ValueError(f"unknown expected response {expected!r}")

    criteria = [
        {
            "criterion": "refusal_correctness",
            "status": "passed" if action_passed else "failed",
            "detail": {"expected": expected, "refusal": refusal, "conflict": conflict},
        },
        {
            "criterion": "key_fact_coverage",
            "status": (
                "not_applicable"
                if expected != "answer"
                else ("passed" if facts["coverage"] == 1.0 else "failed")
            ),
            "detail": facts,
        },
        {
            "criterion": "unsupported_assertion",
            "status": "failed" if unsupported else "passed",
            "detail": {"tokens": unsupported},
        },
        {
            "criterion": "timestamp_source_citation",
            "status": (
                "not_applicable"
                if not entry.get("citation_required")
                else ("passed" if citation["observed"] else "failed")
            ),
            "detail": citation,
        },
    ]
    applicable = [item for item in criteria if item["status"] != "not_applicable"]
    passed = sum(1 for item in applicable if item["status"] == "passed")
    return {
        "entry_id": entry["entry_id"],
        "entry_pass": all(item["status"] == "passed" for item in applicable),
        "criteria": criteria,
        "criteria_passed": passed,
        "criteria_total": len(applicable),
    }


def read_inventory(endpoint, timeout=10.0, fetch=None):
    """Read model inventory only. No inference and no invented answer."""
    def default_fetch(url, seconds):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url, timeout=seconds) as response:
            return json.load(response)

    fetch = fetch or default_fetch
    try:
        body = fetch(endpoint.rstrip("/") + "/models", timeout)
        models = sorted(
            row["id"]
            for row in body.get("data", [])
            if isinstance(row, dict) and isinstance(row.get("id"), str) and row["id"].strip()
        )
        return {"ok": True, "endpoint": endpoint, "models": models}
    except Exception as error:  # noqa: BLE001 - a missing endpoint is a named result
        return {
            "ok": False,
            "endpoint": endpoint,
            "error": f"{type(error).__name__}: {error}",
        }


def model_gate(inventory, requested_model):
    """Decide whether execution may start; never fabricate an answer."""
    if not inventory.get("ok"):
        return {
            "executable": False,
            "evidence_level": "NOT_EXECUTED_MODEL",
            "reason": "MODEL_ENDPOINT_UNAVAILABLE",
            "error": inventory.get("error"),
        }
    if requested_model not in inventory.get("models", []):
        return {
            "executable": False,
            "evidence_level": "NOT_EXECUTED_MODEL",
            "reason": "MODEL_NOT_LISTED",
            "error": None,
        }
    return {"executable": True, "evidence_level": None, "reason": None, "error": None}


def not_executed_result(entry, reason):
    return {
        "entry_id": entry["entry_id"],
        "class": entry["class"],
        "question": entry["question"],
        "context": entry["context"],
        "knowledge_id": None,
        "grant_document_id": None,
        "answer_id": None,
        "status": "NOT_EXECUTED",
        "reason": reason,
        "authority": None,
        "answer_text": None,
        "answer": None,
        "usage": None,
        "usage_status": None,
        "model": None,
        "judged": None,
    }


def not_executed_results(reason):
    return [not_executed_result(entry, reason) for entry in ENTRIES]


def summarize(results):
    statuses = {status: 0 for status in STATUSES}
    for row in results:
        statuses[row["status"]] = statuses.get(row["status"], 0) + 1
    answered = statuses.get("ANSWERED", 0)
    passed = sum(1 for row in results if row.get("judged") and row["judged"]["entry_pass"])
    complete = answered == len(results) and len(results) > 0
    by_class = {}
    for name in CLASSES:
        rows = [row for row in results if row["class"] == name]
        class_passed = sum(
            1 for row in rows if row.get("judged") and row["judged"]["entry_pass"]
        )
        by_class[name] = {
            "total": len(rows),
            "passed": class_passed,
            "pass_rate": (class_passed / len(rows)) if (rows and complete) else None,
        }
    return {
        "entry_count": len(results),
        "statuses": statuses,
        "answered": answered,
        "passed": passed,
        "failed": answered - passed,
        "pass_rate": (passed / len(results)) if complete else None,
        "complete_execution": complete,
        "by_class": by_class,
        "quality_pass": bool(complete and passed == len(results)),
        "human_acceptance": HUMAN_ACCEPTANCE,
        "note": (
            "pass covers response mode, declared fact coverage, grounding tokens and citation "
            "only; it is not accuracy, product or human acceptance"
        ),
    }


def receipt_template(*, run_id, candidate, work, endpoint, model):
    suite = protocol()
    return {
        "schema": SCHEMA,
        "suite": {
            "suite_id": SUITE_ID,
            "suite_version": SUITE_VERSION,
            "preregistered_at": PREREGISTERED_AT,
            "entry_count": len(ENTRIES),
            "classes": list(CLASSES),
            "protocol_sha256": suite["sha256"],
        },
        "protocol": suite,
        "run": {
            "run_id": run_id,
            "candidate": str(candidate),
            "data_root": str(work),
            "endpoint": endpoint,
            "requested_model": model,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
        },
        "evidence_level": "NOT_EXECUTED_MODEL",
        "model": {
            "endpoint": endpoint,
            "requested_model": model,
            "inventory": None,
            "gate": None,
            "observed_models": [],
        },
        "identity": {},
        "results": [],
        "summary": summarize([]),
        "human_acceptance": HUMAN_ACCEPTANCE,
        "limitations": [
            "No human acceptance: human_acceptance=NOT_EXECUTED",
            "Model output remains a candidate; no accuracy or training claim",
            "No installed Tauri/UI qualification",
            "Scoring is deterministic lexical/structural review, not semantic truth review",
            "One local model and endpoint; results do not generalize",
            "Fixture contexts are project-authored public material, not private Owner data",
        ],
        "ok": False,
    }


REQUIRED_RESULT_KEYS = {
    "entry_id", "class", "question", "context", "status", "reason", "answer_text",
    "answer", "usage", "model", "judged",
}


def validate_receipt(receipt):
    """Reject a receipt that would claim an answer or acceptance it cannot show."""
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be an object")
    for key in (
        "schema", "suite", "protocol", "run", "evidence_level", "model", "results",
        "summary", "human_acceptance", "limitations", "ok",
    ):
        if key not in receipt:
            raise ValueError(f"receipt is missing {key}")
    if receipt["schema"] != SCHEMA:
        raise ValueError("unexpected receipt schema")
    if receipt["human_acceptance"] != HUMAN_ACCEPTANCE:
        raise ValueError("receipt must keep human_acceptance=NOT_EXECUTED")
    if receipt["evidence_level"] not in EVIDENCE_LEVELS:
        raise ValueError(f"unknown evidence level {receipt['evidence_level']!r}")
    if receipt["summary"].get("human_acceptance") != HUMAN_ACCEPTANCE:
        raise ValueError("summary must keep human_acceptance=NOT_EXECUTED")
    if receipt["protocol"].get("human_acceptance") != HUMAN_ACCEPTANCE:
        raise ValueError("protocol must keep human_acceptance=NOT_EXECUTED")
    if receipt["suite"].get("protocol_sha256") != protocol()["sha256"]:
        raise ValueError("protocol digest mismatch")
    if receipt["suite"].get("entry_count") != len(ENTRIES):
        raise ValueError("suite entry count mismatch")
    results = receipt["results"]
    if not isinstance(results, list) or len(results) != len(ENTRIES):
        raise ValueError("receipt must carry one result per pre-registered entry")
    seen = set()
    for row in results:
        missing = REQUIRED_RESULT_KEYS - set(row)
        if missing:
            raise ValueError(f"result is missing {sorted(missing)}")
        entry_id = row["entry_id"]
        if entry_id in seen:
            raise ValueError(f"duplicate result entry {entry_id}")
        seen.add(entry_id)
        if row["class"] not in CLASSES:
            raise ValueError(f"unknown class {row['class']!r}")
        if row["status"] not in STATUSES:
            raise ValueError(f"unknown status {row['status']!r}")
        if row["status"] == "ANSWERED":
            if not isinstance(row["answer_text"], str) or not row["answer_text"].strip():
                raise ValueError("an answered entry needs answer text")
            if not isinstance(row["judged"], dict) or "entry_pass" not in row["judged"]:
                raise ValueError("an answered entry needs its judgment")
            if not isinstance(row["model"], dict):
                raise ValueError("an answered entry needs model identity")
        else:
            if row["answer_text"] is not None or row["judged"] is not None:
                raise ValueError("a non-answered entry must not carry an answer or judgment")
            if not str(row.get("reason") or "").strip():
                raise ValueError("a non-answered entry must name a reason")
    return True


def call(client, base, token, method, path, body=None, extra=None, timeout=30):
    return client.call(
        base, method, path, token, body, timeout=timeout, extra_headers=extra
    )


def require(status, body, expected, step):
    if status not in expected:
        raise RuntimeError(f"{step} returned {status}: {body}")
    return body


def start_candidate(candidate, work, launcher, endpoint, model):
    profile = launcher.load_profile(candidate)
    environment = launcher.build_environment(candidate)
    environment.update(
        {
            "ARCHEAXIS_MACHINE_ENDPOINT": endpoint,
            "ARCHEAXIS_MACHINE_MODEL": model,
            "ARCHEAXIS_MACHINE_PROTOCOL": "openai",
        }
    )
    for key in tuple(environment):
        if key.lower() in {"http_proxy", "https_proxy", "all_proxy"}:
            environment.pop(key)
    environment["NO_PROXY"] = "127.0.0.1,localhost"
    token = secrets.token_hex(32)
    worker = {
        "python": str(profile["python"]),
        "script": str(profile["script"]),
        "staging": str(work / "worker-staging"),
        "routes": [
            {"capability": row["capability"], "script": str(row["script"])}
            for row in profile["routes"]
        ],
    }
    (work / "worker-staging").mkdir(exist_ok=True)
    launch = {
        "launch_token": token,
        "machine_token": secrets.token_hex(32),
        "session_id": secrets.token_hex(16),
        "actor": "human",
        "protocol": launcher.LAUNCH_PROTOCOL,
        "text_worker": worker,
    }
    child = subprocess.Popen(
        [str(candidate / "core/archeaxis-api.exe"), str(work / "workspace.sqlite"), "0"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        cwd=candidate,
        env=environment,
    )
    try:
        child.stdin.write(json.dumps(launch) + "\n")
        child.stdin.close()
        base = launcher.wait_for_readiness(child, 0, 30)
        return child, base, token
    except BaseException:
        launcher.stop(child)
        raise


def grant_editor(knowledge_id):
    return {
        "type": "doc",
        "attrs": {
            "archeaxis_context_grant": {
                "schema": "archeaxis.context-grant/v1",
                "purpose": PURPOSE,
                "consumer": "local-machine",
                "operations": ["answer"],
                "knowledge_id": knowledge_id,
                "provenance": [],
                "authorization_basis": FIXTURE_LABEL,
                "expires_at": None,
                "state": "granted",
            }
        },
        "content": [],
    }


def prepare_entry(client, base, token, entry, run_id, timeout):
    """Create accepted knowledge plus an explicit current context grant."""
    status, created = call(
        client, base, token, "POST", "/api/v1/knowledge-items",
        {
            "knowledge_type": "NOTE",
            "body": entry["context"],
            "status": "candidate",
            "created_by": REVIEWER,
        },
    )
    created = require(status, created, {201}, f"{entry['entry_id']} knowledge create")
    knowledge_id = created["knowledge_id"]
    status, current = call(
        client, base, token, "GET", f"/api/v1/knowledge-items/{knowledge_id}/v3"
    )
    current = require(status, current, {200}, f"{entry['entry_id']} knowledge read")
    status, reviewed = call(
        client, base, token, "POST",
        f"/api/v1/knowledge/{knowledge_id}/review/versioned",
        {
            "action": "accepted",
            "reviewer": REVIEWER,
            "note": FIXTURE_LABEL,
            "expected_version": current["version"],
        },
    )
    require(status, reviewed, {200, 201}, f"{entry['entry_id']} knowledge review")
    status, document = call(
        client, base, token, "POST", "/api/v1/documents",
        {
            "title": f"quality grant {entry['entry_id']}",
            "create_request_id": f"quality-grant-{run_id}-{entry['entry_id'].lower()}",
            "editor_json": grant_editor(knowledge_id),
        },
    )
    document = require(status, document, {201}, f"{entry['entry_id']} grant create")
    consumption = {
        "document_id": document["document_id"],
        "version": document["version"],
        "content_sha256": document["content_sha256"],
        "purpose": PURPOSE,
    }
    request = {
        "knowledge_id": knowledge_id,
        "question": entry["question"],
        "context_grant": consumption,
        "max_tokens": 2048,
        "timeout_s": timeout,
        "client_request_id": f"quality-{run_id}-{entry['entry_id']}",
    }
    return knowledge_id, document["document_id"], request


def run_entry(client, base, token, entry, run_id, timeout):
    result = {
        "entry_id": entry["entry_id"],
        "class": entry["class"],
        "question": entry["question"],
        "context": entry["context"],
        "knowledge_id": None,
        "grant_document_id": None,
        "answer_id": None,
        "status": "SETUP_FAILED",
        "reason": None,
        "authority": None,
        "answer_text": None,
        "answer": None,
        "usage": None,
        "usage_status": None,
        "model": None,
        "judged": None,
    }
    try:
        knowledge_id, document_id, request = prepare_entry(
            client, base, token, entry, run_id, timeout
        )
        result["knowledge_id"] = knowledge_id
        result["grant_document_id"] = document_id
    except Exception as error:  # noqa: BLE001 - setup failure is a named result
        result["reason"] = f"{type(error).__name__}: {error}"
        return result
    status, response = call(
        client, base, token, "POST", "/api/v1/machine/answers", request,
        timeout=timeout + 15,
    )
    if status == 503:
        result["status"] = "MODEL_FAILURE"
        reason = response.get("reason_code") if isinstance(response, dict) else None
        result["reason"] = str(reason or "MODEL_CALL_FAILED")
        return result
    if status != 200:
        result["status"] = "CORE_REFUSED"
        result["reason"] = f"CORE_{status}: {response}"
        return result
    if not isinstance(response, dict):
        result["status"] = "CORE_REFUSED"
        result["reason"] = "machine answer response is not an object"
        return result
    payload = response.get("answer")
    if response.get("authority") != "candidate":
        result["status"] = "CORE_REFUSED"
        result["reason"] = "machine answer is not labelled candidate"
        return result
    if not isinstance(payload, dict):
        result["status"] = "MODEL_FAILURE"
        result["reason"] = "NO_FINAL_ANSWER"
        return result
    text = payload.get("answer")
    if not isinstance(text, str) or not text.strip():
        result["status"] = "MODEL_FAILURE"
        result["reason"] = "NO_FINAL_ANSWER"
        return result
    result.update(
        {
            "status": "ANSWERED",
            "reason": None,
            "answer_id": response.get("answer_id"),
            "authority": response.get("authority"),
            "answer_text": text,
            "answer": payload,
            "usage": payload.get("usage"),
            "usage_status": payload.get("usage_status"),
            "model": {
                "requested_model": payload.get("requested_model"),
                "reported_model": payload.get("model"),
                "observed_model": payload.get("observed_model"),
                "endpoint": payload.get("endpoint"),
                "protocol": payload.get("protocol"),
                "engine": payload.get("engine"),
                "engine_version": payload.get("engine_version"),
                "prompt_version": payload.get("prompt_version"),
                "answer_source": payload.get("answer_source"),
                "finish_reason": payload.get("finish_reason"),
                "truncated": payload.get("truncated"),
            },
            "judged": judge(entry, text),
        }
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--run-id", default=uuid.uuid4().hex)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout-s", type=int, default=120)
    arguments = parser.parse_args()
    candidate = Path(os.path.abspath(arguments.candidate))
    allowed = REPO / ".project-local"
    if (
        not candidate.is_relative_to(allowed)
        or not (candidate / "backend-runtime-manifest.json").is_file()
    ):
        parser.error("complete candidate must be in this worktree's .project-local")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", arguments.run_id):
        parser.error("unsafe run ID")
    if not 1 <= arguments.timeout_s <= 120:
        parser.error("timeout must be 1..120 seconds")
    if not arguments.model.strip():
        parser.error("model must not be empty")
    work = OUTPUT_ROOT / arguments.run_id
    work.mkdir(parents=True, exist_ok=False)
    receipt = receipt_template(
        run_id=arguments.run_id,
        candidate=candidate,
        work=work,
        endpoint=arguments.endpoint,
        model=arguments.model,
    )
    launcher = None
    client = None
    child = None
    try:
        launcher = load(
            "quality_suite_launcher", REPO / "scripts/release/backend_launcher.py"
        )
        client = load("quality_suite_client", REPO / "shared/core_client.py")
        inventory = read_inventory(arguments.endpoint)
        gate = model_gate(inventory, arguments.model)
        receipt["model"]["inventory"] = inventory
        receipt["model"]["gate"] = gate
        if not gate["executable"]:
            receipt["evidence_level"] = gate["evidence_level"]
            receipt["results"] = not_executed_results(gate["reason"])
            receipt["summary"] = summarize(receipt["results"])
            return 1
        profile = launcher.load_profile(candidate)
        worker_path = next(
            row["script"] for row in profile["routes"]
            if row["capability"] == "machine.answer"
        )
        receipt["identity"] = {
            "candidate_manifest": identity(candidate / "backend-runtime-manifest.json"),
            "worker_profile": identity(candidate / "worker-profile.json"),
            "core": identity(candidate / "core/archeaxis-api.exe"),
            "interpreter": identity(profile["python"]),
            "machine_worker": identity(worker_path),
            "lockfile": identity(REPO / "uv.lock"),
        }
        child, base, token = start_candidate(
            candidate, work, launcher, arguments.endpoint, arguments.model
        )
        receipt["run"]["pid"] = child.pid
        receipt["results"] = []
        for entry in ENTRIES:
            receipt["results"].append(
                run_entry(
                    client, base, token, entry, arguments.run_id, arguments.timeout_s
                )
            )
            receipt["evidence_level"] = "PARTIAL_MODEL_EXECUTION"
            receipt["summary"] = summarize(receipt["results"])
            (work / "receipt.partial.json").write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        answered = [row for row in receipt["results"] if row["status"] == "ANSWERED"]
        receipt["model"]["observed_models"] = sorted(
            {
                row["model"]["observed_model"]
                for row in answered
                if row["model"] and row["model"].get("observed_model")
            }
        )
        receipt["evidence_level"] = (
            "REAL_LOCAL_CORE_WORKER_MODEL"
            if len(answered) == len(receipt["results"])
            else ("PARTIAL_MODEL_EXECUTION" if answered else "HARNESS_FAILED")
        )
        receipt["summary"] = summarize(receipt["results"])
        receipt["ok"] = receipt["evidence_level"] == "REAL_LOCAL_CORE_WORKER_MODEL"
    except Exception as error:  # noqa: BLE001 - a harness failure is a named result
        receipt["error"] = f"{type(error).__name__}: {error}"
        receipt["evidence_level"] = "HARNESS_FAILED"
        done = {row["entry_id"] for row in receipt["results"]}
        for entry in ENTRIES:
            if entry["entry_id"] not in done:
                receipt["results"].append(
                    not_executed_result(entry, "HARNESS_FAILED")
                )
        receipt["results"].sort(key=lambda row: row["entry_id"])
        receipt["summary"] = summarize(receipt["results"])
        receipt["ok"] = False
    finally:
        if child is not None:
            launcher.stop(child)
        receipt["run"]["finished_at"] = datetime.now(timezone.utc).isoformat()
        try:
            validate_receipt(receipt)
        except ValueError as error:
            receipt["validation_error"] = str(error)
            receipt["ok"] = False
        output = work / "receipt.json"
        output.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "ok": receipt["ok"],
                    "evidence_level": receipt["evidence_level"],
                    "quality_pass": receipt["summary"]["quality_pass"],
                    "pass_rate": receipt["summary"]["pass_rate"],
                    "receipt": str(output),
                    "error": receipt.get("error"),
                },
                ensure_ascii=False,
            )
        )
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
