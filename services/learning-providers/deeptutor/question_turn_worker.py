"""Offline single-question replay of DeepTutor 1.7.1's original quiz step.

No model, network, database, tool, or DeepTutor service is started. The caller
supplies a plan, context, and (in replay mode) a final JSON body; neither that
body nor an unkeyed prompt hash proves its origin. Prompts may contain private
material and the response may contain answers. This is not a privacy filter.
"""
from __future__ import annotations

import __future__
import ast
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from types import SimpleNamespace

try:
    import yaml
except ImportError:
    yaml = None

SCHEMA = "archeaxis.deeptutor-question-turn-replay/v1"
ROOT = Path(__file__).absolute().parent
UPSTREAM = ROOT / "upstream"
PINS = {
    "question_normalizer.py": (15_801, "dc60e865e27bb9316dce09bf94ec55a0420503acd2aa31c577557693a81a92a3"),
    "question_pipeline.py": (93_738, "b0e11748806225b286cff92a2dbf2f5722aa4538c8dc42138fa81def42cc392f"),
    "question_pipeline.en.yaml": (25_482, "148ccde0f60f2d96724e1cbaa3db1f4bc676e87ed086bda1dac1bcdc27f2ae89"),
    "question_pipeline.zh.yaml": (22_946, "ef14102e36f9c156528336b48112a3e8336269fdea5a3517119c651707a8ae58"),
    "question_language.py": (4_860, "7ef192bca1cc8d91c838a4601847a2b40d09becca704e5f74ed65af855f55ce3"),
}
MAX_INPUT_BYTES = 256 * 1024
MAX_PROMPT_BYTES = 384 * 1024
QUESTION_TYPES = frozenset({"choice", "concept", "fill_in_blank", "short_answer", "written", "coding"})


class InvalidRequest(ValueError):
    pass


class InvalidResponse(ValueError):
    pass


class BindingMismatch(ValueError):
    pass


class UpstreamUnavailable(RuntimeError):
    pass


class CaptureComplete(Exception):
    pass


def _read_pinned(path: Path, size: int, expected_sha: str) -> bytes:
    """Bound a fixed read; reject observed links, hardlinks and identity changes."""
    path = path.absolute()
    if path.parent not in {ROOT, UPSTREAM} or path.name not in PINS:
        raise UpstreamUnavailable("source path unavailable")
    components = [*reversed(path.parents), path]
    try:
        before = []
        for component in components:
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise UpstreamUnavailable("source link unavailable")
            if component != path and not stat.S_ISDIR(info.st_mode):
                raise UpstreamUnavailable("source ancestor unavailable")
            before.append(info)
        expected = before[-1]
        if not stat.S_ISREG(expected.st_mode) or expected.st_nlink != 1 or expected.st_size != size or not expected.st_ino:
            raise UpstreamUnavailable("source identity unavailable")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if ((opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino)
                    or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_size != size):
                raise UpstreamUnavailable("source identity changed")
            for component, original in zip(components, before):
                current = component.lstat()
                if (stat.S_ISLNK(current.st_mode) or getattr(current, "st_file_attributes", 0) & 0x400
                        or (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino)):
                    raise UpstreamUnavailable("source ancestor changed")
            chunks = []
            remaining = size + 1
            while remaining:
                chunk = os.read(fd, remaining)
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
            after = os.fstat(fd)
            if ((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_nlink)
                    != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, 1)):
                raise UpstreamUnavailable("source changed")
        finally:
            os.close(fd)
    except OSError as error:
        raise UpstreamUnavailable("source unavailable") from error
    if len(data) != size or hashlib.sha256(data).hexdigest() != expected_sha:
        raise UpstreamUnavailable("source digest mismatch")
    return data


def _source(name: str) -> bytes:
    if name not in PINS:
        raise UpstreamUnavailable("source is not selected")
    parent = ROOT if name == "question_normalizer.py" else UPSTREAM
    return _read_pinned(parent / name, *PINS[name])


def _one(nodes, predicate):
    matches = [node for node in nodes if predicate(node)]
    if len(matches) != 1:
        raise UpstreamUnavailable("upstream definition mismatch")
    return matches[0]


def _audited(nodes):
    for definition in nodes:
        for node in ast.walk(definition):
            if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)):
                raise UpstreamUnavailable("unexpected upstream operation")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {
                "eval", "exec", "open", "__import__", "compile"
            }:
                raise UpstreamUnavailable("unexpected upstream operation")


def _language_function():
    tree = ast.parse(_source("question_language.py"), filename="deeptutor-1.7.1/services/prompt/language.py")
    constants = []
    for name in ("_LANGUAGE_LABELS", "_OVERRIDE_ZH", "_OVERRIDE_EN"):
        node = _one(tree.body, lambda n: (
            isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == name
        ) or (
            isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
            and n.targets[0].id == name
        ))
        try:
            ast.literal_eval(node.value)
        except (TypeError, ValueError, SyntaxError) as error:
            raise UpstreamUnavailable("upstream language constant mismatch") from error
        constants.append(node)
    names = ("normalize_language", "language_label", "language_directive", "append_language_directive")
    functions = [_one(tree.body, lambda n: isinstance(n, ast.FunctionDef) and n.name == name) for name in names]
    if any(node.decorator_list for node in functions):
        raise UpstreamUnavailable("upstream language function mismatch")
    _audited([*constants, *functions])
    module = ast.Module(body=[*constants, *functions], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"__builtins__": {}}
    exec(compile(module, "deeptutor-1.7.1/services/prompt/language.py", "exec",
                 flags=__future__.annotations.compiler_flag, dont_inherit=True), namespace)  # noqa: S102
    return namespace["append_language_directive"]


def _question_class(loop):
    # Load the already-reviewed adapter exactly, then reuse its existing original
    # parser/normalizer/validator rather than creating a second implementation.
    adapter = {"__name__": "deeptutor_question_adapter", "__file__": str(ROOT / "question_normalizer.py")}
    exec(compile(_source("question_normalizer.py"), str(ROOT / "question_normalizer.py"), "exec"), adapter)  # noqa: S102
    base = adapter["_selected_functions"]()
    source = _source("question_pipeline.py")
    tree = ast.parse(source, filename="deeptutor-1.7.1/agents/question/pipeline.py")
    pipeline = _one(tree.body, lambda n: isinstance(n, ast.ClassDef) and n.name == "QuestionPipeline")
    methods = []
    names = ("_quiz_one", "_t", "_render_plan_summary", "_render_previous_questions",
             "_render_reference_block", "_payload_to_qa_pair", "_build_system_user_messages",
             "_kb_system_note", "_fallback_empty_tool_list")
    for name in names:
        wanted = ast.AsyncFunctionDef if name == "_quiz_one" else ast.FunctionDef
        method = _one(pipeline.body, lambda n: isinstance(n, wanted) and n.name == name)
        if method.decorator_list:
            raise UpstreamUnavailable("upstream method mismatch")
        methods.append(method)
    _audited(methods)
    selected = ast.ClassDef(name="SelectedQuizStep", bases=[ast.Name(id="Base", ctx=ast.Load())],
                            keywords=[], body=methods, decorator_list=[])
    module = ast.Module(body=[selected], type_ignores=[])
    ast.fix_missing_locations(module)
    builtins = {"__build_class__": __build_class__, "str": str, "dict": dict, "list": list,
                "isinstance": isinstance, "enumerate": enumerate, "KeyError": KeyError,
                "IndexError": IndexError, "ValueError": ValueError, "getattr": getattr}
    namespace = {"__name__": "deeptutor_quiz_step_subset", "__builtins__": builtins,
                 "Base": base, "QuizPair": SimpleNamespace, "run_agentic_loop": loop,
                 "_QuizLoopHost": lambda **_kwargs: None, "_PROTOCOL_QUIZ": None,
                 "SOURCE": "offline-replay", "STAGE_QUIZZING": "offline-replay",
                 "append_language_directive": _language_function()}
    exec(compile(module, "deeptutor-1.7.1/agents/question/pipeline.py", "exec",
                 flags=__future__.annotations.compiler_flag, dont_inherit=True), namespace)  # noqa: S102
    return namespace["SelectedQuizStep"], namespace["append_language_directive"]


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidRequest("duplicate JSON member")
        result[key] = value
    return result


def _nonfinite(_value):
    raise InvalidRequest("non-finite JSON number")


def _text(value, limit, *, required=False):
    if not isinstance(value, str) or "\x00" in value:
        raise InvalidRequest("invalid text")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError as error:
        raise InvalidRequest("invalid text encoding") from error
    if size > limit or (required and not value.strip()):
        raise InvalidRequest("text outside bounds")
    return value


def _request(value):
    common = {"schema", "request_id", "mode", "language", "plan", "question_number",
              "exploration_trace", "previous_questions"}
    if (not isinstance(value, dict) or value.get("schema") != SCHEMA
            or not isinstance(value.get("mode"), str) or value["mode"] not in {"capture", "replay"}):
        raise InvalidRequest("invalid envelope")
    expected = common if value["mode"] == "capture" else common | {"expected_prompt_sha256", "response_body"}
    if set(value) != expected:
        raise InvalidRequest("invalid envelope fields")
    request_id = _text(value["request_id"], 128, required=True)
    if (not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id)
            or not isinstance(value["language"], str) or value["language"] not in {"en", "zh"}):
        raise InvalidRequest("invalid identity or language")
    plan = value["plan"]
    if not isinstance(plan, dict) or set(plan) != {"analysis", "templates"}:
        raise InvalidRequest("invalid plan")
    analysis = _text(plan["analysis"], 24_000)
    templates = plan["templates"]
    if not isinstance(templates, list) or not 1 <= len(templates) <= 10:
        raise InvalidRequest("invalid templates")
    parsed = []
    ids = set()
    fields = {"question_id", "topic", "question_type", "difficulty", "source", "reference_question", "reference_answer"}
    for item in templates:
        if not isinstance(item, dict) or set(item) != fields:
            raise InvalidRequest("invalid template")
        identity = _text(item["question_id"], 64, required=True)
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identity) or identity in ids:
            raise InvalidRequest("invalid template identity")
        ids.add(identity)
        topic = _text(item["topic"], 12_000, required=True)
        if (not isinstance(item["question_type"], str) or item["question_type"] not in QUESTION_TYPES
                or not isinstance(item["difficulty"], str) or item["difficulty"] not in {"easy", "medium", "hard"}):
            raise InvalidRequest("invalid template type or difficulty")
        if not isinstance(item["source"], str) or item["source"] not in {"custom", "mimic"}:
            raise InvalidRequest("invalid template source")
        reference_question = _text(item["reference_question"], 24_000)
        reference_answer = _text(item["reference_answer"], 24_000)
        if item["source"] == "custom" and (reference_question or reference_answer):
            raise InvalidRequest("custom template cannot carry a mimic reference")
        parsed.append(SimpleNamespace(question_id=identity, topic=topic, question_type=item["question_type"],
                                      difficulty=item["difficulty"], source=item["source"],
                                      reference_question=reference_question, reference_answer=reference_answer))
    number = value["question_number"]
    if type(number) is not int or not 1 <= number <= len(parsed):
        raise InvalidRequest("invalid question number")
    previous = value["previous_questions"]
    if not isinstance(previous, list) or len(previous) > number - 1:
        raise InvalidRequest("invalid previous questions")
    previous = [SimpleNamespace(question=_text(item, 16_000, required=True)) for item in previous]
    exploration = _text(value["exploration_trace"], 80_000)
    if value["mode"] == "replay":
        if not isinstance(value["expected_prompt_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", value["expected_prompt_sha256"]):
            raise InvalidRequest("invalid prompt identity")
        _text(value["response_body"], 180_000, required=True)
    return request_id, SimpleNamespace(analysis=analysis, templates=parsed), number, exploration, previous


def _strict_response(raw, template):
    try:
        payload = json.loads(raw, object_pairs_hook=_unique, parse_constant=_nonfinite)
    except (ValueError, TypeError, RecursionError) as error:
        raise InvalidResponse("invalid final JSON") from error
    allowed = {"question_type", "question", "correct_answer", "explanation", "options"}
    required = allowed - {"options"}
    if not isinstance(payload, dict) or not required <= set(payload) or not set(payload) <= allowed:
        raise InvalidResponse("invalid final fields")
    if payload["question_type"] != template.question_type:
        raise InvalidResponse("question type mismatch")
    try:
        question = _text(payload["question"], 80_000, required=True)
        answer = _text(payload["correct_answer"], 20_000, required=True)
        _text(payload["explanation"], 80_000, required=True)
        options = payload.get("options")
        if template.question_type == "choice":
            if not isinstance(options, dict) or set(options) != {"A", "B", "C", "D"}:
                raise InvalidResponse("invalid choices")
            aliases = {}
            for key, option in options.items():
                _text(option, 20_000, required=True)
                # Match the original grader's whitespace/case folding and the
                # four forms it accepts. An alias must identify only one key.
                for candidate in (key, option, f"{key}. {option}", f"{key}) {option}"):
                    folded = " ".join(candidate.strip().upper().split())
                    if folded in aliases and aliases[folded] != key:
                        raise InvalidResponse("ambiguous choice aliases")
                    aliases[folded] = key
            if answer not in {"A", "B", "C", "D"}:
                raise InvalidResponse("invalid choice answer")
        elif options is not None:
            raise InvalidResponse("unexpected options")
        if template.question_type == "concept" and answer not in {"true", "false"}:
            raise InvalidResponse("invalid concept answer")
        if template.question_type == "fill_in_blank" and len(re.findall(r"(?=____)", question)) != 1:
            raise InvalidResponse("invalid blank count")
        if (question.strip().startswith("[Generation failed]") or answer.strip() == "N/A"
                or payload["explanation"].strip() == "N/A"):
            raise InvalidResponse("placeholder response")
    except InvalidRequest as error:
        raise InvalidResponse("invalid final text") from error
    return payload


def _wire(messages):
    data = json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(data) > MAX_PROMPT_BYTES:
        raise InvalidRequest("prompt exceeds bounds")
    return hashlib.sha256(data).hexdigest()


def process(value):
    try:
        if len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")) > MAX_INPUT_BYTES:
            raise InvalidRequest("input exceeds bounds")
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise InvalidRequest("invalid input encoding") from error
    request_id, plan, number, exploration, previous = _request(value)
    language = value["language"]
    if yaml is None:
        raise UpstreamUnavailable("YAML reader unavailable")
    try:
        prompts = yaml.safe_load(_source(f"question_pipeline.{language}.yaml"))
        if not isinstance(prompts, dict):
            raise UpstreamUnavailable("prompt source unavailable")
        if not isinstance(prompts.get("quiz_step"), dict) or not isinstance(prompts.get("empty"), dict):
            raise UpstreamUnavailable("prompt fields unavailable")
        for key in ("system", "user_template"):
            if not isinstance(prompts["quiz_step"].get(key), str):
                raise UpstreamUnavailable("prompt fields unavailable")
        for key in ("no_exploration_trace", "no_previous_questions", "no_reference"):
            if not isinstance(prompts["empty"].get(key), str):
                raise UpstreamUnavailable("prompt fields unavailable")
    except (yaml.YAMLError, UnicodeError) as error:
        raise UpstreamUnavailable("prompt source unavailable") from error
    observed = {}

    async def loop(**kwargs):
        if observed.get("calls") or kwargs.get("tool_schemas") is not None:
            raise UpstreamUnavailable("unexpected loop call")
        observed["calls"] = 1
        messages = kwargs.get("initial_messages")
        if messages != observed["expected_messages"]:
            raise UpstreamUnavailable("upstream prompt assembly changed")
        observed["messages"] = messages
        observed["prompt_sha256"] = _wire(messages)
        if value["mode"] == "capture":
            raise CaptureComplete()
        if observed["prompt_sha256"] != value["expected_prompt_sha256"]:
            raise BindingMismatch("prompt mismatch")
        _strict_response(value["response_body"], plan.templates[number - 1])
        return SimpleNamespace(final_text=value["response_body"])

    selected, append_language = _question_class(loop)
    step = selected()
    step._prompts = prompts
    step.language = language
    step.kb_name = None
    step.model = None
    step.binding = None
    step.usage = None
    step._budgets = {"quiz_finish": {"max_tokens": 0}}
    step.max_quiz_iterations_per_question = 1
    step._tool_list_text = lambda _context: step._fallback_empty_tool_list()
    step._use_native_tools = lambda _context: False
    step._completion_kwargs = lambda _tokens: {}

    async def no_repair(**_kwargs):
        observed["repair_skipped"] = True
        return None

    class NoStream:
        async def progress(self, *_args, **_kwargs):
            return None

    step._repair_quiz_payload = no_repair
    template = plan.templates[number - 1]
    try:
        system = prompts["quiz_step"]["system"].format(
            question_number=number, total_questions=len(plan.templates), kb_note=step._kb_system_note(),
            tool_list=step._tool_list_text(None))
        user = prompts["quiz_step"]["user_template"].format(
            question_id=template.question_id, topic=template.topic, question_type=template.question_type,
            difficulty=template.difficulty, exploration_trace=exploration or step._t("empty.no_exploration_trace"),
            plan_summary=step._render_plan_summary(plan), previous_questions=step._render_previous_questions(previous),
            reference_block=step._render_reference_block(template))
    except (KeyError, IndexError, ValueError) as error:
        raise UpstreamUnavailable("prompt template cannot be formatted") from error
    observed["expected_messages"] = [{"role": "system", "content": append_language(system, language)},
                                     {"role": "user", "content": user}]
    try:
        result = asyncio.run(step._quiz_one(template=template, question_number=number,
            total_questions=len(plan.templates), exploration_trace=exploration, plan=plan,
            previous_pairs=previous, image_attachments=[], context=None, stream=NoStream(), client=None))
    except CaptureComplete:
        result = None
    if observed.get("calls") != 1 or "prompt_sha256" not in observed:
        raise UpstreamUnavailable("upstream loop did not run exactly once")
    common = {"schema": SCHEMA, "request_id": request_id, "mode": value["mode"],
              "prompt_sha256": observed["prompt_sha256"], "origin": "CALLER_SUPPLIED_UNVERIFIED",
              "prompt_binding": "UNKEYED_TEXT_ONLY_NOT_SOURCE_OR_AUTHENTICATION",
              "model_call": "NOT_INVOKED", "upstream_agentic_loop": "NOT_INVOKED",
              "upstream_method": "QuestionPipeline._quiz_one",
              "plan_and_exploration": "CALLER_SUPPLIED_UNVERIFIED",
              "tool_execution": "NOT_INVOKED", "repair": "NOT_INVOKED",
              "grounding": "NOT_VERIFIED", "question_uniqueness": "NOT_VERIFIED",
              "answer_correctness": "NOT_VERIFIED",
              "core_authorization": "NOT_ESTABLISHED", "independent_mastery": "NOT_ESTABLISHED",
              "privacy_filter": "NOT_APPLIED", "logging_safety": "NOT_ESTABLISHED",
              "original_input_preserved": False, "loss_receipt": "NOT_GENERATED",
              "upstream_pipeline_sha256": PINS["question_pipeline.py"][1],
              "upstream_prompt_sha256": PINS[f"question_pipeline.{language}.yaml"][1],
              "upstream_language_sha256": PINS["question_language.py"][1]}
    if value["mode"] == "capture":
        return {**common, "status": "CAPTURED", "messages": observed["messages"]}
    if result is None or getattr(result, "metadata", {}).get("issues") or observed.get("repair_skipped"):
        raise InvalidResponse("upstream validation reported issues")
    return {**common, "status": "CANDIDATE", "question": {
        "question_id": result.question_id, "question": result.question,
        "question_type": result.question_type, "options": result.options}}


def main():
    try:
        raw = sys.stdin.buffer.readline(MAX_INPUT_BYTES + 1)
        if not raw or len(raw) > MAX_INPUT_BYTES:
            raise InvalidRequest("empty or oversized input")
        # A single-shot caller must close stdin; do not silently ignore another frame.
        if sys.stdin.buffer.read(1):
            raise InvalidRequest("unexpected trailing input")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_nonfinite)
        result = process(value)
        code = 0
    except BindingMismatch:
        result = {"schema": SCHEMA, "status": "REJECTED", "reason_code": "PROMPT_MISMATCH"}
        code = 2
    except InvalidResponse:
        result = {"schema": SCHEMA, "status": "REJECTED", "reason_code": "INVALID_RESPONSE"}
        code = 2
    except (InvalidRequest, ValueError, UnicodeError, RecursionError):
        result = {"schema": SCHEMA, "status": "INVALID_REQUEST", "reason_code": "INVALID_INPUT"}
        code = 2
    except Exception:  # noqa: BLE001 - no source or caller content is emitted on failure.
        result = {"schema": SCHEMA, "status": "UNAVAILABLE", "reason_code": "UPSTREAM_UNAVAILABLE"}
        code = 1
    # The worker protocol is UTF-8 regardless of the host's text console code page.
    wire = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(wire + b"\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
