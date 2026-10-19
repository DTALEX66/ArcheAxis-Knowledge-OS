"""SYNTHETIC measured local transport; never contacts a server or model."""
import importlib.util
import io
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("measured_worker", ROOT / "services/python-workers/machine/worker_machine_answer.py")
machine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(machine)


@pytest.mark.parametrize("phase,wrapped", [("http_open", False), ("http_open", True), ("body_read", False), ("json_parse", False), ("response_validation", False)])
def test_real_call_failure_keeps_only_measured_phase_and_bytes(monkeypatch, phase, wrapped):
    clock = [100.0]
    observed = []
    payload = {"model": "m", "choices": [{"message": {"content": [] if phase == "response_validation" else ""}, "finish_reason": "stop"}]}
    raw = json.dumps(payload).encode()
    monkeypatch.setattr(machine.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(machine, "_endpoint", lambda: {"protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "m"})
    class Response(io.BytesIO):
        def read(self, size=-1):
            assert size == machine.MAX_MODEL_RESPONSE_BYTES + 1
            clock[0] += 2
            if phase == "body_read":
                raise TimeoutError("SYNTHETIC_PRIVATE response")
            return super().read(size)
    def open_(request, timeout):
        observed.append((request, timeout))
        clock[0] += 1
        if phase == "http_open":
            error = TimeoutError("SYNTHETIC_PRIVATE headers")
            raise machine.urllib.error.URLError(error) if wrapped else error
        return Response(raw)
    original_loads = machine.json.loads
    def parse(raw_text):
        clock[0] += .5
        if phase == "json_parse":
            raise json.JSONDecodeError("SYNTHETIC_PRIVATE body", raw_text, 0)
        return original_loads(raw_text)
    monkeypatch.setattr(machine, "local_urlopen", open_)
    monkeypatch.setattr(machine.json, "loads", parse)
    with pytest.raises(machine.ModelCallFailure) as error:
        machine.answer("合成材料", "合成问题", model="m", timeout_s=5, max_tokens=1024)
    failure = machine.failure_receipt(error.value)
    diag = failure["diagnostics"]
    assert failure["reason_code"] == ("MODEL_CALL_TIMEOUT" if phase in {"http_open", "body_read"} else "MODEL_CALL_FAILED")
    assert diag["request_stage"] == "model_request" and diag["request_phase"] == phase
    assert diag["http_open_elapsed_s"] == 1
    request, budget = observed[0]
    assert len(observed) == 1 and budget == 5
    assert diag["serialized_request_bytes"] == len(request.data)
    expected_prompt, _ = machine.answer_prompt("合成材料", "合成问题", "grounded")
    assert diag["prompt_utf8_bytes"] == len(expected_prompt.encode("utf-8"))
    outbound = original_loads(request.data)
    assert outbound == {"model":"m", "max_tokens":1024,"messages":[{"role":"user","content":expected_prompt}]}
    if phase != "http_open":
        assert diag["body_read_elapsed_s"] == 2
    else:
        assert "body_read_elapsed_s" not in diag
    if phase in {"json_parse", "response_validation"}:
        assert diag["response_bytes"] == len(raw) and diag["json_parse_elapsed_s"] == .5
    else:
        # Failed read has no complete response byte measurement, never fabricated zero.
        assert "response_bytes" not in diag and "json_parse_elapsed_s" not in diag
    assert "SYNTHETIC_PRIVATE" not in json.dumps(failure)
    assert not any(k in diag for k in ("prompt", "url", "headers", "response", "ttft_s", "provider_stop_state"))


def test_no_final_answer_preserves_complete_measurements_but_success_shape_is_unchanged(monkeypatch):
    monkeypatch.setattr(machine, "_endpoint", lambda: {"protocol":"openai","base":"http://127.0.0.1:1/v1","model":"m"})
    payload = {"model":"m","choices":[{"message":{"content":"","reasoning_content":"SYNTHETIC_PRIVATE thoughts"},"finish_reason":"length"}]}
    monkeypatch.setattr(machine,"local_urlopen",lambda *a,**k:io.BytesIO(json.dumps(payload).encode()))
    with pytest.raises(machine.FinalAnswerFailure) as error:
        machine.answer("context","question")
    diag = machine.failure_receipt(error.value)["diagnostics"]
    assert diag["request_phase"] == "response_validation" and diag["response_bytes"] > 0
    assert all(diag[k] >= 0 for k in ("http_open_elapsed_s","body_read_elapsed_s","json_parse_elapsed_s"))
    assert "SYNTHETIC_PRIVATE" not in json.dumps(machine.failure_receipt(error.value))
    payload["choices"][0]["message"]["content"] = "candidate"
    result = machine.answer("context","question")
    assert result["answer"] == "candidate" and result["finish_reason"] == "length"
    assert not any(k in result for k in ("diagnostics","request_phase","prompt_utf8_bytes","response_bytes"))


def test_oversized_response_reports_observed_bound_without_attempting_parse(monkeypatch):
    monkeypatch.setattr(machine, "MAX_MODEL_RESPONSE_BYTES", 16)
    monkeypatch.setattr(machine, "_endpoint", lambda: {"protocol":"openai","base":"http://127.0.0.1:1/v1","model":"m"})
    monkeypatch.setattr(machine,"local_urlopen",lambda *a,**k:io.BytesIO(b'x'*30))
    with pytest.raises(machine.ModelCallFailure) as error:
        machine.answer("context","question")
    diag=machine.failure_receipt(error.value)["diagnostics"]
    assert diag["request_phase"] == "body_read" and diag["response_bytes"] == 17
    assert "json_parse_elapsed_s" not in diag


@pytest.mark.parametrize("field", ["prompt_utf8_bytes","serialized_request_bytes","response_bytes"])
def test_byte_measurement_sanitizer_is_safe_integer_only(field):
    for value in (0,1,9007199254740991):
        assert machine.failure_diagnostics({field:value}) == {field:value}
    for value in (True,-1,1.5,9007199254740992,"SYNTHETIC_PRIVATE",None):
        assert machine.failure_diagnostics({field:value}) == {}


@pytest.mark.parametrize("field", ["http_open_elapsed_s","body_read_elapsed_s","json_parse_elapsed_s"])
def test_stage_duration_sanitizer_rejects_nonfinite_or_private(field):
    assert machine.failure_diagnostics({field:0.25}) == {field:0.25}
    for value in (True,-1,float("nan"),float("inf"),9007199254740992,"SYNTHETIC_PRIVATE"):
        assert machine.failure_diagnostics({field:value}) == {}
    assert machine.failure_diagnostics({"request_phase":"PRIVATE","headers":{"token":"SYNTHETIC_PRIVATE"}}) == {}
