"""Real local machine answer on isolated authored engineering material.

AUTOMATED_FIXTURE_REVIEW_NOT_G4_HUMAN: engineering acceptance is never Owner
acceptance. Model output remains a candidate with unmeasured outcome. No provider
or agent/global configuration is changed; only the child uses the local endpoint.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.request
import uuid
from pathlib import Path

from aaos01_office_runtime_loop import REPO, identity, load

LOCAL_ENDPOINT = "http://127.0.0.1:1234/v1"
MODEL = "qwen3.5-4b"
REVIEWER = "engineering-probe-not-owner"
FIXTURE_LABEL = "AUTOMATED_FIXTURE_REVIEW_NOT_G4_HUMAN"
MATERIAL = (
    "这是公开工程验证夹具，不代表产品或真人验收。项目代号为 AAOS-01。\n"
    "夹具定义：一致备份复制已提交的 SQLite 数据；恢复需重启读回验证。\n"
    "本夹具的校验值是 37。\n"
)
QUESTION = "只依据材料回答：夹具里的校验值是多少？用一句话回答，不输出推理过程。"


def start(candidate, work, launcher):
    from types import SimpleNamespace

    from aaos01_office_runtime_loop import start as start_office

    environment = launcher.build_environment(candidate)
    environment.update(
        {
            "ARCHEAXIS_MACHINE_ENDPOINT": LOCAL_ENDPOINT,
            "ARCHEAXIS_MACHINE_MODEL": MODEL,
            "ARCHEAXIS_MACHINE_PROTOCOL": "openai",
        }
    )
    for key in tuple(environment):
        if key.lower() in {"http_proxy", "https_proxy", "all_proxy"}:
            environment.pop(key)
    environment["NO_PROXY"] = "127.0.0.1,localhost"
    scoped_launcher = SimpleNamespace(
        load_profile=launcher.load_profile,
        LAUNCH_PROTOCOL=launcher.LAUNCH_PROTOCOL,
        build_environment=lambda _: environment,
        wait_for_readiness=launcher.wait_for_readiness,
        stop=launcher.stop,
    )
    child, base, token, _ = start_office(candidate, work, scoped_launcher)
    return child, base, token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--run-id", default=uuid.uuid4().hex)
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
    work = allowed / "task-runtime/aaos01-machine" / arguments.run_id
    work.mkdir(parents=True, exist_ok=False)
    receipt = {
        "ok": False,
        "candidate": str(candidate),
        "work": str(work),
        "review_class": FIXTURE_LABEL,
        "reviewer": REVIEWER,
        "effectiveness": "unmeasured",
        "evidence_level": "NOT_EXECUTED_MODEL",
        "limitations": [
            "No Owner or G4 human review",
            "No accuracy or model-training claim",
            "No desktop/installed UI qualification",
            "No fabricated error or correction",
        ],
    }
    launcher = load("machine_probe_launcher", REPO / "scripts/release/backend_launcher.py")
    client = load("machine_probe_client", REPO / "shared/core_client.py")
    child = None
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(LOCAL_ENDPOINT + "/models", timeout=10) as response:
            models = json.load(response)
        receipt["model_inventory"] = {"endpoint": LOCAL_ENDPOINT, "body": models}
        if MODEL not in {row.get("id") for row in models.get("data", [])}:
            raise RuntimeError("required local model is not advertised")
        profile = launcher.load_profile(candidate)
        worker_path = next(
            row["script"] for row in profile["routes"] if row["capability"] == "machine.answer"
        )
        worker = load("machine_candidate_worker", worker_path)
        receipt["candidate_manifest"] = identity(candidate / "backend-runtime-manifest.json")
        receipt["worker"] = identity(worker_path)
        receipt["interpreter"] = identity(profile["python"])
        receipt["core"] = identity(candidate / "core/archeaxis-api.exe")
        receipt["lockfile"] = identity(REPO / "uv.lock")
        child, base, token = start(candidate, work, launcher)
        receipt["pid"] = child.pid

        def call(method, path, body=None, extra=None, timeout=30):
            status, result = client.call(
                base, method, path, token, body, timeout=timeout, extra_headers=extra
            )
            if not 200 <= status < 300:
                raise RuntimeError(f"Core {method} {path} returned {status}: {result}")
            return result

        receipt["system"] = call("GET", "/api/v1/system/version")
        imported = call(
            "POST",
            "/api/v1/imports",
            client.import_request("public-engineering-fixture.txt", MATERIAL.encode()),
        )
        receipt["source"] = imported
        job_id = "machine-source-" + uuid.uuid4().hex
        call(
            "POST",
            "/api/v1/jobs",
            {"job_id": job_id, "kind": "text", "input_ref": imported["source_id"]},
        )
        call(
            "POST",
            f"/api/v1/jobs/{job_id}/executions",
            {"deadline_ms": 30000},
            {"Idempotency-Key": job_id},
        )
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            job = call("GET", f"/api/v1/jobs/{job_id}")
            if job["state"] in {"succeeded", "failed", "cancelled", "rejected"}:
                break
            time.sleep(0.2)
        if job["state"] != "succeeded":
            raise RuntimeError(f"public fixture job failed: {job}")
        transformed = call(
            "GET", f"/api/v1/sources/{imported['source_id']}/jobs/{job_id}/transform"
        )
        context = transformed["content"]
        quote_end = len(context.encode("utf-16-le")) // 2
        created = call(
            "POST",
            "/api/v1/knowledge-items/from-transform",
            {
                "knowledge_type": "OBSERVATION",
                "body": context,
                "source_id": imported["source_id"],
                "job_id": job_id,
                "transform_id": transformed["transform_id"],
                "selection_start_utf16": 0,
                "selection_end_utf16": quote_end,
                "quote": context,
            },
        )
        knowledge_id = created["knowledge_id"]
        knowledge = call("GET", f"/api/v1/knowledge-items/{knowledge_id}/v3")
        fixture_review = call(
            "POST",
            f"/api/v1/knowledge/{knowledge_id}/review/versioned",
            {
                "action": "accepted",
                "reviewer": REVIEWER,
                "note": FIXTURE_LABEL,
                "expected_version": knowledge["version"],
            },
        )
        knowledge = call("GET", f"/api/v1/knowledge-items/{knowledge_id}/v3")
        receipt["fixture_review"] = {"label": FIXTURE_LABEL, "receipt": fixture_review}
        receipt["knowledge"] = knowledge
        receipt["job"] = job
        receipt["prompt"] = {
            "context": context,
            "question": QUESTION,
            "version": worker.PROMPT_VERSION,
            "text": worker.PROMPT_TEMPLATE.format(context=context, question=QUESTION),
        }
        answer = call(
            "POST",
            "/api/v1/machine/answers",
            {
                "knowledge_id": knowledge_id,
                "question": QUESTION,
                "max_tokens": 2048,
                "timeout_s": 120,
            },
            timeout=135,
        )
        receipt["answer"] = answer
        receipt["evidence_level"] = "REAL_LOCAL_CORE_WORKER_MODEL"
        actual = answer["answer"]
        if (
            not actual["answer"].strip()
            or actual["endpoint"] != LOCAL_ENDPOINT
            or actual["model"] != MODEL
            or answer["authority"] != "candidate"
        ):
            raise RuntimeError("machine output identity or candidate boundary mismatch")
        task_id = answer["answer_id"]
        task = call("GET", f"/api/v1/machine/tasks/{task_id}")
        if json.loads(task["conditions"]) != answer or task["outcome"] != "unmeasured":
            raise RuntimeError("machine task persistent readback differs")
        receipt["task"] = task
        receipt["expected_marker_observation"] = {
            "marker": "37",
            "present": "37" in actual["answer"],
            "not_accuracy_measurement": True,
        }
        launcher.stop(child)
        child = None
        child, base, token = start(candidate, work, launcher)
        receipt["restart_pid"] = child.pid
        after = call("GET", f"/api/v1/machine/tasks/{task_id}")
        after_knowledge = call("GET", f"/api/v1/knowledge-items/{knowledge_id}/v3")
        receipt["restart_task"] = after
        receipt["restart_knowledge"] = after_knowledge
        if after != task or after_knowledge != knowledge:
            raise RuntimeError("restart persistent readback differs")
        receipt["restart_equal"] = True
        receipt["ok"] = True
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
    finally:
        if child is not None:
            launcher.stop(child)
        path = work / "receipt.json"
        path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "ok": receipt["ok"],
                    "receipt": str(path),
                    "review_class": FIXTURE_LABEL,
                    "error": receipt.get("error"),
                },
                ensure_ascii=False,
            )
        )
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
