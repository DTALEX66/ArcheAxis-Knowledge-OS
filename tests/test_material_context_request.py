"""SYNTHETIC离线请求截获：证明文件正文进入序列化请求，不代表provider实际接收或质量通过。"""
import importlib.util
import io
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("material_context_request_worker", ROOT / "services/python-workers/machine/worker_machine_answer.py")
machine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(machine)


@pytest.mark.parametrize("text", [
    "Independent synthetic material 59a40506553e4814bb3de90b0e65e99f. ArcheAxis keeps a versioned local note for reading and review.",
    "原始材料编号甲：星环把阅读与复习保存在版本化本地笔记中。🌌",
])
@pytest.mark.parametrize("final", ["这是用于阅读和复习的版本化本地笔记。", ""])
def test_extract_preserves_selected_utf8_context_question_budget_and_final_only(monkeypatch, tmp_path, text, final):
    source = tmp_path / "owned-context.txt"
    source.write_bytes(text.encode("utf-8"))
    question = "请用一句中文概括当前已选文本的主题。"
    calls = []
    monkeypatch.setattr(machine, "_endpoint", lambda: {"protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "owned-model"})

    def capture(request, timeout):
        calls.append((request, timeout))
        return io.BytesIO(json.dumps({"model": "owned-model", "choices": [{"message": {"content": final, "reasoning_content": "SYNTHETIC reasoning must not be the answer"}, "finish_reason": "stop"}]}).encode("utf-8"))

    monkeypatch.setattr(machine, "local_urlopen", capture)
    if final:
        result = machine.extract(str(source), question, "owned-model", 1024, 120)
        assert result["answer"] == final and result["text"] == final
        assert result["answer_source"] == "content"
        assert result["answer_policy"] == "grounded" and result["max_tokens"] == 1024
    else:
        with pytest.raises(machine.FinalAnswerFailure) as error:
            machine.extract(str(source), question, "owned-model", 1024, 120)
        assert machine.failure_receipt(error.value)["reason_code"] == "NO_FINAL_ANSWER"
    assert len(calls) == 1
    request, timeout = calls[0]
    assert 0 < timeout <= 120
    body = json.loads(request.data)
    assert body["model"] == "owned-model" and body["max_tokens"] == 1024
    assert len(body["messages"]) == 1 and body["messages"][0]["role"] == "user"
    prompt = body["messages"][0]["content"]
    assert text in prompt and question in prompt
    assert prompt.index(text) < prompt.index(question)
    assert source.read_bytes() == text.encode("utf-8")
