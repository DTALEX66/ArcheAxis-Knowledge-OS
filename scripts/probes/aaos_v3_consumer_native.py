"""Incremental V3 consumer journey for the qualified native WebDriver harness.

No standalone launcher, SQLite writes, fake bridge responses, DOM input setters,
global model configuration or inherited full-journey execution. Seed mutations are
explicitly separated from trusted product UI actions. Synthetic answers and actor
declarations qualify engineering wiring only, never learning or Owner acceptance.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import stat
import subprocess
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from scripts.probes.workspace_path_report import checked_workspace_report


READS = frozenset({"system_version", "ui_state_read", "sources_list", "source_get",
    "source_original", "source_job_transform", "jobs_get", "documents_list",
    "document_get", "document_version", "knowledge_get", "knowledge_qualification",
    "search", "course_get", "teaching_list", "teaching_get", "anchors_list",
    "machine_task_get", "machine_answer_snapshot", "machine_tasks_list",
    "learning_deeptutor_question_turn_status", "learning_provider_activity_get"})
SEEDS = frozenset({"source_import", "job_enqueue", "job_execute", "knowledge_from_transform",
    "knowledge_review", "document_create", "course_from_knowledge", "course_openmaic_scene_create"})
VISIBLE = "[not(ancestor-or-self::*[@hidden or @aria-hidden='true' or @inert])]"
MODEL = "aaos-v3-consumer-synthetic-loopback"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def snapshot(document):
    return {key: document[key] for key in ("document_id", "version", "content_sha256")}


def literal(value):
    if "'" not in value:
        return "'" + value + "'"
    if '"' not in value:
        return '"' + value + '"'
    return "concat(" + ',"\'",'.join("'" + piece + "'" for piece in value.split("'")) + ")"


def owned_path(path, root, *, file=True):
    """Reject lexical escape and reparse traversal, not merely the final symlink."""
    path, root = Path(path), Path(root).resolve(strict=True)
    if not path.is_absolute():
        raise ValueError("An explicit absolute owned path is required")
    path = path.absolute()
    path.relative_to(root)
    for parent in [path, *path.parents]:
        if parent.exists():
            info = parent.lstat()
            if parent.is_symlink() or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ValueError("Seed/evidence reparse traversal is forbidden")
        if parent == root:
            break
    resolved = path.resolve(strict=file)
    resolved.relative_to(root)
    if file and not resolved.is_file():
        raise ValueError("Owned regular file required")
    return resolved


def canvas_export_file(receipt, saved, data_root):
    """The host reports a relative publication directory under its active data root."""
    document_id, version = saved["document_id"], saved["version"]
    directory = receipt.get("directory")
    if (not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", document_id)
            or type(version) is not int or version < 1
            or receipt.get("document_id") != document_id or receipt.get("version") != version
            or receipt.get("format") != "canvas" or not isinstance(directory, str)
            or not re.fullmatch(rf"exports/{re.escape(document_id)}/canvas/v{version}-[0-9a-f]{{16}}", directory)):
        raise ValueError("Canvas export receipt does not identify the selected saved version")
    return owned_path(data_root / directory / "document.canvas", data_root)


def load_seed(path, expected_sha256, repo, core_path, source):
    """Opt-in handoff only. Do not infer a seed from nearby runs or old receipts."""
    if not re.fullmatch(r"[a-f0-9]{64}", expected_sha256 or ""):
        raise ValueError("--v3-seed-receipt-sha256 must bind exact native-seed bytes")
    root = Path(repo) / ".project-local/runs"
    path = owned_path(path, root)
    raw = path.read_bytes()
    if len(raw) > 2_000_000 or digest(raw) != expected_sha256:
        raise ValueError("Native seed receipt hash/budget mismatch")
    seed = json.loads(raw)
    if seed.get("schema") != "archeaxis.v3-native-seed/v1" or seed.get("synthetic") is not True or seed.get("owner_acceptance") is not False:
        raise ValueError("Seed is not the explicitly synthetic V3 handoff")
    if Path(seed["source_worktree"]).resolve() != Path(repo).resolve() or seed["source_commit"] != source["commit"] or seed["source_patch_sha256"] != source["patch_sha256"]:
        raise ValueError("Seed and native candidate source identities differ")
    if seed["core_sha256"] != digest(Path(core_path).read_bytes()):
        raise ValueError("Seed Core differs from native candidate Core")
    runtime_root = Path(core_path).parent.parent
    manifest_path = owned_path(runtime_root / "backend-runtime-manifest.json", Path(repo) / ".project-local")
    manifest_raw = manifest_path.read_bytes()
    if not re.fullmatch(r"[a-f0-9]{64}", seed.get("runtime_manifest_sha256", "")) or digest(manifest_raw) != seed["runtime_manifest_sha256"]:
        raise ValueError("Seed runtime manifest differs from native candidate runtime")
    manifest = json.loads(manifest_raw)
    binding = seed.get("runtime_binding", {})
    if binding.get("schema") != "archeaxis.probe-runtime-binding/v1" or binding.get("mode") != "FORMAL_STAGED_RUNTIME" or binding.get("manifest", {}).get("sha256") != seed["runtime_manifest_sha256"]:
        raise ValueError("Seed lacks the formal staged runtime binding")
    profile_path = owned_path(runtime_root / "worker-profile.json", runtime_root)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    routes = [row for row in profile.get("routes", []) if row.get("capability") == "machine.answer"]
    if profile.get("python") not in {"runtime/python.exe", "runtime/python/python.exe"} or len(routes) != 1:
        raise ValueError("Native runtime launch profile differs from formal stage")
    for name, member in {"python": profile["python"], "profile": "worker-profile.json",
                         "worker": routes[0]["script"], "launcher": "start-backend.py"}.items():
        if not isinstance(member, str) or "\\" in member or ":" in member or any(part in {"", ".", ".."} for part in member.split("/")):
            raise ValueError("Unsafe native runtime member")
        member_path = owned_path(runtime_root / member, runtime_root)
        actual = {"bytes": member_path.stat().st_size, "sha256": digest(member_path.read_bytes())}
        expected = binding.get(name, {})
        if actual != {key: expected.get(key) for key in ("bytes", "sha256")} or actual != manifest.get("files", {}).get(member):
            raise ValueError("Seed runtime launch input differs from native candidate")
    backup = owned_path(seed["backup"]["path"], root)
    backup.relative_to(path.parent)
    if digest(backup.read_bytes()) != seed["backup"]["sha256"]:
        raise ValueError("Seed backup artifact hash mismatch")
    receipt = seed["backup"]["receipt"]
    if receipt.get("filename") != backup.name or receipt.get("verified") is not True or receipt.get("schema") != "archeaxis-core-backup-1" or receipt.get("sha256") != seed["backup"]["sha256"]:
        raise ValueError("Formal backup receipt filename differs")
    for name in ("material_v1", "material_v2", "asset_candidate_v1", "asset_adopted_v1", "asset_candidate_v2", "asset_adopted_v2"):
        ref = seed["snapshots"][name]
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", ref["document_id"]) or not isinstance(ref["version"], int) or ref["version"] < 1 or not re.fullmatch(r"[a-f0-9]{64}", ref["content_sha256"]):
            raise ValueError("Invalid handoff snapshot")
    return seed


def restore_seed(seed, *, read, close, launch, core, work, env, report):
    """Normal host shutdown, canonical maintenance restore, fresh supervisor launch."""
    before = read("system_version")
    expected = Path(work) / "data" / "archeaxis.sqlite"
    target = owned_path(checked_workspace_report(before["workspace_db"], expected), Path(work) / "data")
    close()
    result = subprocess.run([str(core), "--maintenance-restore", str(target), seed["backup"]["path"]],
        cwd=work, env=env, capture_output=True, text=True, encoding="utf-8", timeout=90,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    # Maintenance has no launch tokens or remote endpoint; keep its exact JSON receipt.
    saved = json.loads(result.stdout.strip())
    report["restore"] = {"exit_code": result.returncode, "receipt": saved,
                         "seed_workspace_id": seed["workspace_id"], "seed_restore_epoch": seed["restore_epoch"]}
    if result.returncode != 0 or any(saved.get(key) is not True for key in ("ok", "verified", "authorization_requires_new_grants")):
        raise AssertionError("Formal restore did not verify; no consumer actions started")
    if checked_workspace_report(saved["database"], expected).resolve(strict=True) != target:
        raise AssertionError("Maintenance restored a different target")
    launch()
    after = read("ui_state_read")
    assert after["workspace_id"] == seed["workspace_id"] and after["restore_epoch"] != seed["restore_epoch"]
    report["restore"]["restored_identity"] = {key: after[key] for key in ("workspace_id", "restore_epoch", "recovery_requires_confirmation")}


class ControlledModel:
    """A bounded owned loopback test service. Never modifies os.environ or config."""
    def __init__(self):
        self.calls = []
        self.lock = threading.Lock()
        self.hold_next = False
        self.question = {"question_type": "choice", "question": "合成练习：2 + 2 等于多少？",
                         "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
                         "correct_answer": "B", "explanation": "合成答案键：2 + 2 = 4。"}
        self.entered = threading.Event()
        self.release = threading.Event()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                if self.path != "/v1/chat/completions" or not 0 < length <= 2_000_000:
                    self.send_error(400)
                    return
                raw = self.rfile.read(length)
                request = json.loads(raw)
                if request.get("model") != MODEL:
                    self.send_error(400)
                    return
                with owner.lock:
                    delayed = owner.hold_next
                    owner.hold_next = False
                    record = {"ordinal": len(owner.calls) + 1, "request_sha256": digest(raw),
                              "model": request["model"], "delayed": delayed, "reply_written": False}
                    owner.calls.append(record)
                if delayed:
                    owner.entered.set()
                    owner.release.wait(60)
                question = owner.question
                reply = json.dumps({"id": "v3-synthetic", "object": "chat.completion", "model": MODEL,
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": json.dumps(question, ensure_ascii=False)}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}).encode()
                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(reply)))
                    self.end_headers()
                    self.wfile.write(reply)
                    record["reply_written"] = True
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    record["client_disconnected"] = True

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        # close() releases delayed handlers before server_close joins them.
        self.server.daemon_threads = False
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="aaos-v3-owned-model")

    def start(self):
        self.thread.start()
        return {"ARCHEAXIS_MACHINE_ENDPOINT": f"http://127.0.0.1:{self.server.server_port}/v1",
                "ARCHEAXIS_MACHINE_MODEL": MODEL, "ARCHEAXIS_MACHINE_PROTOCOL": "openai"}

    def arm_delay(self):
        self.entered.clear()
        self.release.clear()
        with self.lock:
            self.hold_next = True

    def close(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        assert not self.thread.is_alive(), "Owned synthetic model thread survived cleanup"


class Journey:
    def __init__(self, *, ui, bridge, js, wait, restart, screenshot, work, report, model):
        self.ui, self.bridge, self.js, self.wait = ui, bridge, js, wait
        self.restart, self.screenshot, self.work, self.report, self.model = restart, screenshot, Path(work), report, model
        self.tag = "V3N_" + uuid.uuid4().hex[:12]
        report.update(status="IN_PROGRESS", synthetic=True, owner_acceptance=False,
            seed_writes=[], readbacks=[], ui_operation_receipts=[], consumers={},
            limitations=["Controlled loopback replies do not establish actual model quality.",
                "Programmatic Chinese input, not physical IME or human usability acceptance.",
                "Synthetic review and self-report are not Owner approval, independent mastery or external practice execution.",
                "Canvas external application round-trip is not measured."])

    def read(self, operation, payload=None):
        if operation not in READS:
            raise ValueError("Incremental read bridge forbids mutation: " + operation)
        value = self.bridge(operation, payload or {})
        self.report["readbacks"].append({"operation": operation, "payload": payload or {}, "response_sha256": digest(canonical(value))})
        return value

    def seed(self, operation, payload):
        if operation not in SEEDS:
            raise ValueError("Undeclared fixture write: " + operation)
        value = self.bridge(operation, payload)
        self.report["seed_writes"].append({"operation": operation, "payload": payload, "response": value,
            "evidence_scope": "SYNTHETIC_INITIALIZATION_NOT_UI_OR_OWNER_ACCEPTANCE"})
        return value

    def until(self, callback, predicate, seconds=45):
        deadline, last = time.monotonic() + seconds, None
        while time.monotonic() < deadline:
            last = callback()
            if predicate(last):
                return last
            time.sleep(.15)
        raise AssertionError("Readback condition timed out: " + repr(last)[:1200])

    def scope(self, label):
        return "//*[@aria-label=" + literal(label) + "]" + VISIBLE

    def click(self, text, scope=""):
        selector = (scope or "") + "//button[normalize-space(.)=" + literal(text) + "]" + VISIBLE
        self.enabled(selector)
        self.ui.click_revealed_selector(selector)

    def enabled(self, selector):
        self.wait("const nodes=document.evaluate(" + json.dumps(selector) + ",document,null,7,null);const n=nodes.snapshotLength===1?nodes.snapshotItem(0):null;return !!n&&!n.matches(':disabled')")

    def summary(self, text):
        path = "//summary[normalize-space(.)=" + literal(text) + "]" + VISIBLE
        self.wait("return !!document.evaluate(" + json.dumps(path) + ",document,null,9,null).singleNodeValue")
        if not self.js("return document.evaluate(" + json.dumps(path) + ",document,null,9,null).singleNodeValue.parentElement.open"):
            self.ui.click_revealed_selector(path)

    def select(self, label, value, scope=""):
        path = (scope or "") + "//label[contains(.," + literal(label) + ")]//select" + VISIBLE
        self.enabled(path)
        # Record the real control before touching it: the option keys the product
        # renders are evidence, not an assumption of the probe.
        observed = self.js("const n=document.evaluate(" + json.dumps(path) +
            ",document,null,XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue;"
            "return n?{html:n.outerHTML,options:[...n.options].map(o=>({value:o.value,text:o.textContent,attr:o.getAttribute('value')})),"
            "parent:n.parentElement?n.parentElement.outerHTML.slice(0,1200):null}:null;")
        self.report.setdefault("select_observations", []).append({"label": label, "control": observed})
        available = [row["value"] for row in ((observed or {}).get("options") or [])]
        assert value in available, "Option key absent in the real control: " + json.dumps(observed, ensure_ascii=False)[:1500]
        # Compare the addressable forms of the same option node before choosing one.
        variants = {"value": path + "/option[@value=" + literal(value) + "]",
                    "text": path + "/option[normalize-space(.)=" + literal(value) + "]",
                    "descendant": path + "//option[@value=" + literal(value) + "]"}
        counts = {name: self.js("const n=document.evaluate(" + json.dumps(candidate) +
            ",document,null,7,null);return n.snapshotLength;") for name, candidate in variants.items()}
        self.report.setdefault("select_observations", [])[-1]["variants"] = counts
        self.report.setdefault("select_observations", [])[-1]["variant_paths"] = variants
        chosen = next((name for name, count in counts.items() if count == 1), None)
        assert chosen is not None, "Option node is not uniquely addressable: " + json.dumps(counts, ensure_ascii=False)
        self.ui.click_native_option(variants[chosen])

    def check(self, label, scope=""):
        path = (scope or "") + "//label[contains(.," + literal(label) + ")]//input[@type='checkbox']" + VISIBLE
        self.enabled(path)
        self.ui.click_revealed_selector(path)

    def type(self, label, value, tag="input", scope=""):
        self.enabled((scope or "") + "//label[contains(.," + literal(label) + ")]//" + tag + VISIBLE)
        self.ui.type(label, value, tag=tag, scope=scope)

    def text(self, label, expected):
        # CSS attribute values need literal Unicode. json.dumps' default ASCII
        # \uXXXX form is not a CSS escape and silently matches no element.
        selector = "[aria-label=" + json.dumps(label, ensure_ascii=False) + "]"
        self.wait("return [...document.querySelectorAll(" + json.dumps(selector) + ")].filter(n=>n.getClientRects().length&&!n.closest('[hidden],[aria-hidden=\"true\"],[inert]')).some(n=>n.textContent.includes(" + json.dumps(expected) + "))")

    def observe(self):
        # Transparent, bounded transport observation only. Product calls still go to
        # the real native bridge; no responses, fields, handlers or timers are replaced.
        self.js(r"""
if(!window.__v3NativeObserver){
 const original=window.__TAURI__,invoke=original.core.invoke;window.__v3NativeObserver=[];
 const observed=function(command,args){
   const req=command==='core_command'?args?.request:null;
   const allowed=new Set(['document_create','document_draft','document_export','document_export_save',
    'source_import','learning_deeptutor_question_turn','learning_deeptutor_question_turn_cancel',
    'learning_deeptutor_question_turn_status','learning_deeptutor_question_accept',
    'learning_deeptutor_practice_grade','learning_deeptutor_teaching_feedback',
    'learning_provider_activity_create','learning_provider_attempt_start','learning_provider_attempt_submit',
    'teaching_create','course_openmaic_package_projection','machine_task_get','machine_tasks_list']);
   const row=req&&allowed.has(req.operation)?{operation:req.operation,payload:structuredClone(req.payload),state:'pending'}:null;
   if(row){if(window.__v3NativeObserver.length>=512)throw new Error('V3 observation budget exceeded');window.__v3NativeObserver.push(row);}
   return invoke(command,args).then(value=>{if(row){row.state='returned';row.response=structuredClone(value);}return value;},error=>{if(row){row.state='rejected';row.error=String(error);}throw error;});
 };
 window.__TAURI__={...original,core:{...original.core,invoke:observed}};
 if(window.__TAURI__.core.invoke!==observed)throw new Error('V3 transparent observer installation refused');
} return true;
""")

    def observations(self):
        return self.js("return window.__v3NativeObserver??[]")

    def returned(self, operation, predicate=lambda _row: True):
        return self.until(self.observations, lambda rows: any(r["operation"] == operation and r["state"] == "returned" and 200 <= r["response"]["status"] < 300 and predicate(r) for r in rows))

    def cold(self):
        self.report["ui_operation_receipts"].extend(self.observations())
        self.report.setdefault("cold_restarts", []).append(self.restart())
        self.observe()

    def documents(self):
        result, cursor, seen = [], None, set()
        for _ in range(20):
            page = self.read("documents_list", {"cursor": cursor} if cursor else {})
            result.extend(page["documents"])
            cursor = page.get("next_cursor")
            if not cursor:
                return result
            assert cursor not in seen, "Document pagination repeated"
            seen.add(cursor)
        raise AssertionError("Synthetic workspace exceeded document read budget")

    def namespace(self, namespace, predicate=lambda _v: True):
        result = []
        for row in self.documents():
            doc = self.read("document_get", {"document_id": row["document_id"]})
            value = doc.get("editor_json", {}).get("attrs", {}).get(namespace)
            if value is not None and predicate(value):
                result.append((doc, value))
        return result

    def new_document(self, title, *, text="", attrs=None):
        return self.seed("document_create", {"body": {"create_request_id": self.tag + "_" + uuid.uuid4().hex,
            "title": title, "editor_json": {"type": "doc", "attrs": attrs or {},
            "content": [{"type": "paragraph", "attrs": {"block_id": uuid.uuid4().hex}, "content": [{"type": "text", "text": text}]}] if text else []}}})

    def list_button(self, text, more, scope=""):
        for _ in range(20):
            path = (scope or "") + "//button[normalize-space(.)=" + literal(text) + "]" + VISIBLE
            next_path = "//button[normalize-space(.)=" + literal(more) + "]" + VISIBLE
            self.wait("return !!document.evaluate(" + json.dumps(path + " | " + next_path) + ",document,null,9,null).singleNodeValue")
            if self.js("return !!document.evaluate(" + json.dumps(path) + ",document,null,9,null).singleNodeValue"):
                self.enabled(path)
                self.ui.click_revealed_selector(path)
                return
            self.click(more)
        raise AssertionError("Requested exact UI list identity not found")

    def open_document(self, doc):
        self.ui.page("02", confirm_navigation=True)
        self.click("刷新资料列表")
        path = "//button[@aria-label=" + literal("打开文档 " + doc["title"]) + "]" + VISIBLE
        # All newly seeded items have unique titles. The UI does not get an ID injected.
        for _ in range(20):
            next_path = "//button[normalize-space(.)='加载更多文档']" + VISIBLE
            self.wait("return !!document.evaluate(" + json.dumps(path + " | " + next_path) + ",document,null,9,null).singleNodeValue")
            if self.js("return !!document.evaluate(" + json.dumps(path) + ",document,null,9,null).singleNodeValue"):
                self.enabled(path)
                self.ui.click_revealed_selector(path)
                return
            self.click("加载更多文档")
        raise AssertionError("Material not reachable from saved document list")

    def material_panel(self, material):
        self.open_document(material)
        self.summary("围绕此材料学习与练习")
        self.text("围绕材料学习与练习", material["title"])
        return self.scope("围绕材料学习与练习")

    def journey(self, material, key):
        return self.until(lambda: self.namespace("archeaxis_deeptutor_journey", lambda v: v["material"] == snapshot(material)),
            lambda rows: len(rows) == 1 and key in rows[0][1] and "pending" not in rows[0][1])[0]


def initialize(j, seed):
    if seed:
        refs = seed["snapshots"]
        for name in ("material_v1", "material_v2", "asset_candidate_v1", "asset_adopted_v1", "asset_candidate_v2", "asset_adopted_v2"):
            ref = refs[name]
            assert snapshot(j.read("document_version", {"document_id": ref["document_id"], "version": ref["version"]})) == ref
        material = j.read("document_get", {"document_id": refs["material_v2"]["document_id"]})
        assert snapshot(material) == refs["material_v2"], "Seed material head changed"
        knowledge = j.read("knowledge_get", {"id": refs["knowledge_v2"]["knowledge_id"]})
        assert knowledge["version"] == refs["knowledge_v2"]["review_version"] and digest(knowledge["body"].encode()) == refs["knowledge_v2"]["body_sha256"]
        j.report["seed_handoff"] = {"schema": seed["schema"], "snapshots": refs,
            "authorization": {"maintenance_authorization_requires_new_grants": True,
                "old_grant_consumption_refusal": "NOT_MEASURED_NO_REPLAY", "new_material_and_question_grants": "PENDING_TRUSTED_UI"}}
        j.report["seed_handoff"]["restored_fixed_history"] = seed_history(j, seed)
        j.model.question = {"question_type": "choice", "question": "合成 Lumen v2 政策：初始借阅期限是多少天？",
            "options": {"A": "7", "B": "10", "C": "5", "D": "14"}, "correct_answer": "B",
            "explanation": "此合成固定 v2 材料明确规定初始期限10天。"}
    else:
        text = j.tag + " 合成来源：2 + 2 = 4。固定原件用于工程接线，不代表实际学习。"
        source = j.seed("source_import", {"body": {"name": j.tag + ".txt", "content_base64": base64.b64encode(text.encode()).decode()}})
        job = j.tag + "_text"
        j.seed("job_enqueue", {"body": {"job_id": job, "kind": "text", "input_ref": source["source_id"]}})
        j.seed("job_execute", {"job_id": job, "body": {"deadline_ms": 30000}})
        outcome = j.until(lambda: j.read("jobs_get", {"job_id": job}), lambda r: r["state"] not in {"queued", "running"})
        assert outcome["state"] == "succeeded"
        transform = j.read("source_job_transform", {"source_id": source["source_id"], "job_id": job})
        body = transform["content"]
        created = j.seed("knowledge_from_transform", {"body": {"knowledge_type": "NOTE", "body": body,
            "source_id": source["source_id"], "job_id": job, "transform_id": transform["transform_id"],
            "selection_start_utf16": 0, "selection_end_utf16": len(body.encode("utf-16-le")) // 2, "quote": body}})
        knowledge = j.read("knowledge_get", {"id": created["knowledge_id"]})
        j.seed("knowledge_review", {"id": knowledge["knowledge_id"], "body": {"action": "accepted",
            "expected_version": knowledge["version"], "reviewer": "SYNTHETIC_NATIVE_ACTOR_NOT_OWNER", "note": "工程夹具，不是本人验收"}})
        knowledge = j.read("knowledge_get", {"id": knowledge["knowledge_id"]})
        material = j.new_document(j.tag + " 学习材料", text=text)
    assert knowledge.get("anchor_id"), "Same-object course fixture requires the inherited real source/transform anchor"
    course = j.seed("course_from_knowledge", {"body": {"knowledge_id": knowledge["knowledge_id"]}})["course"]
    cancel_material = j.new_document(j.tag + " 延迟取消材料", text="合成取消请求单独固定材料；2 + 2 = 4。")
    reference = {"kind": "knowledge", "knowledge_id": knowledge["knowledge_id"]}
    research = j.new_document(j.tag + " 修订对照研究", attrs={"archeaxis_research": {
        "schema": "archeaxis.research/v1", "question": "固定旧知识在后继修订后如何显示？",
        "materials": [{"id": "material1", "note": "合成固定引用", "reference": reference}],
        "hypotheses": [], "methods": [], "experiments": [], "counterevidence": [], "conclusions": [], "unresolved": []}})
    asset = j.read("document_get", {"document_id": seed["snapshots"]["asset_adopted_v2"]["document_id"]}) if seed else j.new_document(j.tag + " 引用当前性资产", attrs={"archeaxis_ai_asset": {
        "schema": "archeaxis.ai-asset/v1", "kind": "experience", "content": "合成经验，仅核对固定引用当前性",
        "purpose": "原生消费者工程观察", "scope": [], "provenance": [reference], "expires_at": None,
        "state": "candidate", "members": [], "conflicts": [], "revises": None, "review": None, "source_payload": None}})
    if seed:
        assert snapshot(asset) == seed["snapshots"]["asset_adopted_v2"]
        asset_value = asset["editor_json"]["attrs"]["archeaxis_ai_asset"]
        assert reference in asset_value["scope"] + asset_value["provenance"], "Same-knowledge asset provenance/scope is missing"
    scenes = []
    for kind in ("slide", "quiz"):
        title = j.tag + " " + kind
        content = {"elements": [{"type": "text", "id": "text1", "left": 60, "top": 60, "width": 800,
            "height": 100, "rotate": 0, "content": "<p>" + title + " 固定版本文本</p>",
            "defaultFontName": "Microsoft YaHei", "defaultColor": "#222222"}], "background": {"type": "solid", "color": "#ffffff"}} if kind == "slide" else {
            "questions": [{"id": "q1", "type": "single", "question": "合成课件：2 + 2？",
                "options": [{"label": "3", "value": "A"}, {"label": "4", "value": "B"}], "answer": ["B"], "analysis": "合成答案键", "points": 1}]}
        request = {"schema": "archeaxis.openmaic-scene-build/v1", "request_id": j.tag + "_" + kind, "attempt": 1,
            "source": snapshot(material), "stage_id": j.tag + "_stage", "scene_id": j.tag + "_scene_" + kind,
            "outline": {"id": j.tag + "_outline_" + kind, "type": kind, "title": title, "description": "合成离线场景",
                        "keyPoints": ["固定版本"], "order": len(scenes)}, "content": content,
            "actions": [{"id": "speech1", "type": "speech", "text": "第一步合成讲解"},
                        {"id": "focus1", "type": "spotlight", "elementId": "text1"}] if kind == "slide" else []}
        saved = j.seed("course_openmaic_scene_create", {"body": {"create_request_id": j.tag + "_save_" + kind, "request": request}})
        assert saved["worker_invoked"] is True and saved["human_review_required"] is True
        scenes.append(saved["document"])
    return {"material": material, "cancel_material": cancel_material, "knowledge": knowledge,
            "course": course, "research": research, "asset": asset, "scenes": scenes}


def seed_history(j, seed):
    """Read original fixed identities; restoration flags alone do not prove history."""
    refs = seed["snapshots"]
    source_ref = refs["source"]
    source = j.read("source_get", {"source_id": source_ref["source_id"]})
    original = j.read("source_original", {"source_id": source_ref["source_id"]})
    assert source["source_revision"] == source_ref["source_revision"] == source_ref["sha256"] == original["sha256"]
    assert digest(base64.b64decode(original["content_base64"], validate=True)) == original["sha256"]
    transform = j.read("source_job_transform", {"source_id": source_ref["source_id"], "job_id": source_ref["job_id"]})
    assert transform["transform_id"] == source_ref["transform_id"]
    anchors = j.read("anchors_list", {"source_id": source_ref["source_id"]})["anchors"]
    fixed_anchor = next(row for row in anchors if row["anchor_id"] == source_ref["anchor_id"])
    assert fixed_anchor["source_id"] == source_ref["source_id"] and fixed_anchor["source_revision"] == source_ref["source_revision"]
    for name in ("knowledge_v1", "knowledge_v2"):
        ref = refs[name]
        doc = j.read("knowledge_get", {"id": ref["knowledge_id"]})
        assert doc["knowledge_id"] == ref["knowledge_id"] and doc["version"] == ref["review_version"] and digest(doc["body"].encode()) == ref["body_sha256"]
        assert doc["source_id"] == ref["source_id"] == source_ref["source_id"] and doc["anchor_id"] == ref["anchor_id"] == source_ref["anchor_id"]
        assert ref["source_revision"] == source_ref["source_revision"]
    answers = []
    for ref in refs["answers"]:
        task = j.read("machine_task_get", {"task_id": ref["task_id"]})
        fixed = j.read("machine_answer_snapshot", {"task_id": ref["task_id"]})
        # Core stores `knowledge_version` as `<knowledge_id>@<version>`; the
        # knowledge identity itself lives in the task conditions and the answer
        # snapshot. Comparing those two different fields directly made the
        # first real native run fail against a qualified restored workspace.
        conditions = json.loads(task["conditions"]) if isinstance(task["conditions"], str) else task["conditions"]
        assert task["task_id"] == fixed["task_id"] == ref["task_id"]
        assert conditions["knowledge_id"] == fixed["knowledge_id"] == ref["knowledge_id"]
        assert isinstance(task["knowledge_version"], str) and task["knowledge_version"].startswith(ref["knowledge_id"] + "@")
        assert fixed["original_answer_sha256"] == ref["answer_sha256"] == digest(fixed["original_answer"].encode())
        assert fixed["task_receipt_sha256"] == ref["task_receipt_sha256"]
        assert conditions["answer"]["answer"] == fixed["original_answer"]
        answers.append({"binding": ref, "answer": fixed, "task": task})
    evaluations = []
    for ref in refs["evaluations"]:
        doc = j.read("document_version", {"document_id": ref["document_id"], "version": ref["version"]})
        assert snapshot(doc) == ref
        value = doc["editor_json"]["attrs"]["archeaxis_machine_evaluation"]
        answer = next(row for row in refs["answers"] if row["task_id"] == value["task_id"])
        assert value["knowledge_id"] == answer["knowledge_id"] and value["original_answer_sha256"] == answer["answer_sha256"] and value["task_receipt_sha256"] == answer["task_receipt_sha256"]
        evaluations.append(snapshot(doc))
    grants = []
    for ref in refs["knowledge_grants"] + refs["asset_grants"]:
        saved = snapshot(j.read("document_version", {"document_id": ref["document_id"], "version": ref["version"]}))
        assert saved == ref
        grants.append(saved)
    return {"source": source_ref, "answers": answers, "evaluations": evaluations, "old_grant_readback": grants}


def show_seed_answers(j, seed):
    """Open the real historical task list; do not inject selected IDs into React."""
    before_calls = len(j.model.calls)
    j.ui.page("22", confirm_navigation=True)
    scope = j.scope("资料处理与 AI 任务记录")
    j.click("AI 任务记录", scope)
    j.click("刷新任务记录", scope)
    page = j.read("machine_tasks_list")
    rows, cursor = page["items"], page["next_cursor"]
    wanted = {row["task_id"] for row in seed["snapshots"]["answers"]}
    for _ in range(20):
        if wanted.issubset({row["task_id"] for row in rows}):
            break
        assert cursor, "Restored answer absent from current task catalog"
        j.click("查看更多任务记录", scope)
        page = j.read("machine_tasks_list", {"cursor": cursor})
        rows.extend(page["items"]); cursor = page["next_cursor"]
    assert wanted.issubset({row["task_id"] for row in rows})
    for ref in seed["snapshots"]["answers"]:
        index = next(i for i, row in enumerate(rows) if row["task_id"] == ref["task_id"])
        selector = "(" + scope + "//ul[contains(@class,'action-list')]/li/button)[" + str(index + 1) + "]"
        j.enabled(selector); j.ui.click_revealed_selector(selector)
        returned = j.returned("machine_task_get", lambda row: row["payload"]["task_id"] == ref["task_id"])
        task = next(row["response"]["body"] for row in reversed(returned) if row["operation"] == "machine_task_get" and row["payload"]["task_id"] == ref["task_id"])
        answer = json.loads(task["conditions"])["answer"]["answer"]
        j.text("历史机器回答", answer)
        j.summary("来源与版本详情")
        j.text("任务记录详情", ref["task_id"])
        assert digest(answer.encode()) == ref["answer_sha256"]
        j.screenshot("v3-restored-answer-" + str(index + 1) + ".png")
        j.click("关闭任务详情", scope)
    assert len(j.model.calls) == before_calls
    j.report["seed_handoff"]["historical_answer_ui"] = {"status": "PASS", "task_ids": sorted(wanted), "new_inference": False}


def deeptutor(j, fixtures):
    material = fixtures["material"]
    scope = j.material_panel(material)
    j.type("本次学习目标", "合成接线验收：根据此固定材料出一道可人工核对的选择题", "textarea", scope)
    j.check("允许使用此材料固定版本进行本地出题与练习", scope)
    j.click("保存材料授权", scope)
    j.journey(material, "material_grant")
    before = len(j.model.calls)
    j.click("生成一道题目候选", scope)
    j.journey(material, "candidate")
    assert len(j.model.calls) > before, "No actual loopback model request crossed the worker boundary"
    j.text("题目内容", j.model.question["question"])
    j.select("你确认的正确选项", "B", scope)
    j.type("你核对后的解释", j.model.question["explanation"] + "这不是Owner人工验收。", "textarea", scope)
    j.check("我已核对题目和答案，作为人工声明的答案键保存", scope)
    j.click("接纳为练习题", scope)
    j.journey(material, "question")
    j.check("允许使用此接纳题目固定版本进行本地评分", scope)
    j.click("保存题目授权", scope)
    j.journey(material, "question_grant")
    j.click("建立本次材料练习", scope)
    j.journey(material, "activity")
    j.click("开始本次作答", scope)
    j.journey(material, "attempt_id")
    j.select("作答选项", "B", scope)
    j.click("保存作答并评分", scope)
    j.text("围绕材料学习与练习", "本地供体评分")
    j.type("本人的反馈与学习需要", "合成自报：已看答案，仍需独立练习；不能据此认定掌握。", "textarea", scope)
    j.click("保存反馈与教学策略", scope)
    document, journey = j.journey(material, "feedback")
    history = j.read("learning_provider_activity_get", {"activity_id": journey["activity"]["activity_id"]})
    attempted = next(row for row in history["attempts"] if row["attempt_id"] == journey["attempt_id"])
    assert history["independent_mastery"] == "not_established" and attempted["state"] == "submitted"
    assert attempted["result"]["answer"] == "B" and attempted["result"]["provider_correct"] is True and attempted["grade_disposition"]["state"] == "COMPLETED"
    for key, ref in (("material_grant", snapshot(material)), ("question_grant", journey["question"])):
        grant = j.read("document_version", {"document_id": journey[key]["document_id"], "version": journey[key]["version"]})
        value = grant["editor_json"]["attrs"]["archeaxis_provider_material_grant"]
        assert snapshot(grant) == journey[key] and value["state"] == "granted" and value["material"] == ref and value["operations"] == ["practice"]
    j.text("已保存的本人反馈", "合成自报")
    j.screenshot("v3-deeptutor-feedback.png")
    j.report["consumers"]["deeptutor"] = {"status": "PASS", "journal": snapshot(document), "value": journey,
        "attempt_history": history, "grant_count": 2, "independent_mastery": "NOT_ESTABLISHED", "model_calls": len(j.model.calls) - before}
    j.cold()
    j.material_panel(material)
    j.text("已保存的本人反馈", "合成自报")
    assert snapshot(j.read("document_get", {"document_id": document["document_id"]})) == snapshot(document)
    if "seed_handoff" in j.report:
        j.report["seed_handoff"]["authorization"]["new_material_and_question_grants"] = "CREATED_BY_TRUSTED_UI_AND_FIXED_VERSION_READBACK"


def cancellation(j, fixtures):
    material = fixtures["cancel_material"]
    scope = j.material_panel(material)
    j.type("本次学习目标", "合成延迟请求：核对明确取消和原请求恢复", "textarea", scope)
    j.check("允许使用此材料固定版本进行本地出题与练习", scope)
    j.click("保存材料授权", scope)
    j.journey(material, "material_grant")
    j.model.arm_delay()
    before = len(j.model.calls)
    j.click("生成一道题目候选", scope)
    assert j.model.entered.wait(45), "Delayed actual model request was never admitted"
    pending = j.namespace("archeaxis_deeptutor_journey", lambda v: v["material"] == snapshot(material))[0][1]["pending"]
    j.click("取消本次生成", scope)
    rows = j.returned("learning_deeptutor_question_turn_cancel")
    cancel = [r for r in rows if r["operation"] == "learning_deeptutor_question_turn_cancel"][-1]
    assert cancel["payload"] == pending["payload"], "Cancel did not use the exact frozen request"
    assert cancel["response"]["body"]["provider_stop_state"] == "UNKNOWN"
    j.model.release.set()
    # UI completion is driven by the real cancelled generation response, not a fake timeout.
    j.text("围绕材料学习与练习", "模型服务是否停止仍未知")
    j.click("查询原请求与已保存记录", scope)
    j.text("原请求恢复状态", "未知")
    j.screenshot("v3-deeptutor-cancel-unknown.png")
    call_count = len(j.model.calls)
    assert call_count == before + 1
    j.cold()
    scope = j.material_panel(material)
    j.click("查询原请求与已保存记录", scope)
    j.text("原请求恢复状态", "未知")
    saved = j.namespace("archeaxis_deeptutor_journey", lambda v: v["material"] == snapshot(material))[0]
    assert saved[1]["pending"] == pending and not saved[1].get("candidate")
    assert len(j.model.calls) == call_count, "Read-only cancellation recovery invoked the model again"
    j.report["consumers"]["cancellation"] = {"status": "PASS", "journal": snapshot(saved[0]), "request": pending,
        "cancel_receipt": cancel["response"]["body"], "model_call_count_unchanged_on_reopen": True,
        "provider_stop_state": "UNKNOWN"}


def scene_panel(j, doc):
    j.ui.page("07", confirm_navigation=True)
    j.click("外部课程", j.scope("学习内容导航"))
    j.summary("已生成课件与外部课程")
    scope = j.scope("已生成课件")
    j.click("浏览生成场景文档", scope)
    j.list_button("打开场景 " + doc["title"], "读取更多场景文档", scope)
    title = doc["editor_json"]["attrs"]["archeaxis_openmaic_scene_candidate"]["worker_document"]["scene"]["title"]
    j.text("固定版本课件", title)
    return scope


def scenes(j, fixtures):
    slide, quiz = fixtures["scenes"]
    scope = scene_panel(j, slide)
    j.text("文本幻灯片", "固定版本文本")
    j.text("逐步讲解", "第一步合成讲解")
    j.click("下一步讲解", scope)
    j.wait("return !!document.querySelector('[aria-label=\"文本幻灯片\"] [data-focused=\"true\"]')")
    j.click("保存阅读位置", scope)
    j.text("已生成课件", "阅读位置已保存并读回")
    position = j.namespace("archeaxis_scene_position", lambda v: v["scene"] == snapshot(slide))
    assert len(position) == 1 and position[0][1]["step"] == 1 and position[0][1]["learning_evidence"] == "NONE"
    j.screenshot("v3-openmaic-slide-focus.png")
    j.cold()
    scene_panel(j, slide)
    j.text("讲解步骤", "第 2 / 2 步")
    j.wait("return !!document.querySelector('[aria-label=\"文本幻灯片\"] [data-focused=\"true\"]')")
    scope = scene_panel(j, quiz)
    j.click("开始记录本次作答", scope)
    option = scope + "//label[normalize-space(.)='4']//input[@type='radio']"
    j.enabled(option); j.ui.click_revealed_selector(option)
    j.click("保存作答", scope)
    j.returned("learning_provider_attempt_submit")
    j.text("固定版本课件", "未建立独立掌握")
    j.click("读取已保存作答", scope)
    j.text("固定版本课件", "课件参考对照不是供体评分或独立掌握")
    j.screenshot("v3-openmaic-stored-quiz.png")
    j.cold()
    scope = scene_panel(j, quiz)
    j.click("读取已保存作答", scope)
    j.text("固定版本课件", "课件参考对照不是供体评分或独立掌握")
    j.text("固定版本课件", "已提交：4")
    j.report["consumers"]["openmaic"] = {"status": "PASS", "entry": "OpenMaicScenePanel",
        "scenes": [snapshot(slide), snapshot(quiz)], "position": snapshot(position[0][0]),
        "source": snapshot(fixtures["material"]), "scene_seed": "REAL_OFFLINE_NODE_WORKER_SYNTHETIC_CONTENT",
        "model_generation": "NOT_CLAIMED", "manifest_import_used": False}


def canvas(j):
    raw = {"nodes": [{"id": "text1", "type": "text", "x": 0, "y": 0, "width": 360, "height": 180, "text": "原画布中文🙂"},
        {"id": "link1", "type": "link", "x": 420, "y": 0, "width": 200, "height": 100, "url": "https://example.invalid/never-open"}],
        "edges": [{"id": "edge1", "fromNode": "text1", "toNode": "link1", "label": "原连线"}], "extension": {"preserve": True}}
    path = j.work / (j.tag + ".canvas")
    path.write_bytes(json.dumps(raw, ensure_ascii=False).encode())
    j.ui.page("16", confirm_navigation=True)
    # A document read earlier in the journey leaves the exchange page on 文档导出.
    # Choosing 原件与转换 is the same visible action a person takes; it does not
    # bypass the hidden guard, and the import input must still be visible afterwards.
    j.ui.click_revealed_selector("//nav[@aria-label='导入导出区域']//button[normalize-space(.)="
        + literal("原件与转换") + "]" + VISIBLE)
    selector = "//*[@aria-label='原件与转换']//input[@type='file' and @aria-label='导入原件']" + VISIBLE
    element = j.ui.find(selector)
    j.ui.command(element, "value", {"text": str(path), "value": list(str(path))})
    j.report.setdefault("ui_file_inputs", []).append({"path": str(path), "sha256": digest(path.read_bytes())})
    j.click("打开刚导入的原件", j.scope("导入一份原件"))
    j.click("阅读此原件与整理知识候选")
    j.text("只读画布", "原画布中文🙂")
    j.click("创建可编辑草稿")
    mapped = j.until(lambda: [d for d in j.documents() if d["title"] == path.name], lambda d: len(d) == 1)
    original = j.read("document_get", {"document_id": mapped[0]["document_id"]})
    edited = "修改后画布中文🙂；原位置连线与链接保持。"
    j.ui.keys("//*[@contenteditable='true' and @aria-label='文档草稿']" + VISIBLE, "\ue009a\ue000" + edited)
    j.click("保存草稿")
    saved = j.until(lambda: j.read("document_get", {"document_id": original["document_id"]}), lambda d: d["version"] > original["version"] and d["text_projection"] == edited)
    j.report.setdefault("canvas_identity", {})["original"] = {"source_id": original["source_id"],
        "source_revision": original["source_revision"], "block_ids": [block["block_id"] for block in original["blocks"]],
        "editor_content": original.get("editor_json", {}).get("content")}
    j.report["canvas_identity"]["saved"] = {"source_id": saved["source_id"],
        "source_revision": saved["source_revision"], "block_ids": [block["block_id"] for block in saved["blocks"]],
        "editor_content": saved.get("editor_json", {}).get("content")}
    j.report["ui_operation_receipts"].extend(j.observations())
    assert saved["source_revision"] == original["source_revision"], "Canvas draft lost the original source revision"
    assert saved["blocks"][0]["block_id"] == original["blocks"][0]["block_id"], "Canvas draft lost the first block identity"
    j.text("只读画布", edited)
    j.click("属性与引用")
    j.summary("导出已保存文档")
    j.click("Canvas 已保存版导出到产品资料目录")
    rows = j.returned("document_export_save", lambda r: r["payload"]["document_id"] == saved["document_id"])
    proof = [r["response"]["body"] for r in rows if r["operation"] == "document_export" and r["payload"]["document_id"] == saved["document_id"]][-1]
    export = [r["response"]["body"] for r in rows if r["operation"] == "document_export_save" and r["payload"]["document_id"] == saved["document_id"]][-1]
    exported = canvas_export_file(export, saved, j.work / "data")
    parsed = json.loads(exported.read_bytes())
    expected = json.loads(json.dumps(raw)); expected["nodes"][0]["text"] = edited
    assert parsed == expected and proof["version"] == saved["version"]
    assert digest(exported.read_bytes()) == digest(next(f["content"].encode() for f in proof["files"] if f["path"] == "document.canvas"))
    j.screenshot("v3-canvas-saved-export.png")
    j.cold()
    j.open_document(saved)
    j.text("只读画布", edited)
    source = j.read("source_original", {"source_id": saved["source_id"]})
    assert source["sha256"] == digest(path.read_bytes())
    assert snapshot(j.read("document_get", {"document_id": saved["document_id"]})) == snapshot(saved)
    j.report["consumers"]["canvas"] = {"status": "PASS", "original_sha256": source["sha256"],
        "mapped": snapshot(original), "saved": snapshot(saved), "export": export,
        "export_sha256": digest(exported.read_bytes()), "external_roundtrip": "NOT_MEASURED"}


def external_practice(j, fixtures):
    j.ui.page("08", confirm_navigation=True)
    knowledge = fixtures["knowledge"]
    search = j.read("search", {"q": knowledge["body"][:40], "active_only": True})
    row = next(row for row in search["items"] if row["knowledge_id"] == knowledge["knowledge_id"])
    j.type("查找来源知识", knowledge["body"][:40], scope=j.scope("真实教学来源"))
    j.click("搜索来源知识", j.scope("真实教学来源"))
    j.click(row["head"], j.scope("真实教学来源"))
    records, parent = [], None
    for action in ("requirement", "plan", "revise", "skip", "replace", "start", "note", "complete", "feedback"):
        scope = j.scope("外部实践计划与文字记录")
        j.select("实践操作", action, scope)
        if parent:
            j.select("实践依据记录", parent, scope)
        j.click("准备实践文字草稿", scope)
        text = j.tag + " " + action + "：仅合成文字记录，无工具连接、无成果文件；不证明实际实践或掌握。"
        j.type("内容", text, "textarea", j.scope("创建教学记录"))
        j.click("保存教学记录", j.scope("创建教学记录"))
        rows = j.returned("teaching_create", lambda r: r["payload"]["body"].get("content") == text)
        operation = next(r for r in reversed(rows) if r["operation"] == "teaching_create" and r["payload"]["body"].get("content") == text)
        record = operation["payload"]["body"]
        read = j.read("teaching_get", {"record_id": record["record_id"]})
        assert read["record"] == record and read["scoring_status"] == "not_scored"
        assert record["knowledge_id"] == knowledge["knowledge_id"] and record["knowledge_version"] == knowledge["knowledge_id"] and record["course_id"] is None
        assert record["parent_id"] == parent
        records.append({"action": action, "record": read})
        # Process and self-report are sibling observations of the same fixed plan.
        if action not in {"start", "note"}:
            parent = record["record_id"]
    j.screenshot("v3-l0-text-practice-feedback.png")
    j.cold()
    j.ui.page("12", confirm_navigation=True)
    j.click("刷新教学记录")
    j.click("反馈 · " + records[-1]["record"]["record"]["purpose"])
    j.text("已保存教学记录", records[-1]["record"]["record"]["content"])
    for row in records:
        assert j.read("teaching_get", {"record_id": row["record"]["record"]["record_id"]}) == row["record"]
    j.report["consumers"]["external_practice"] = {"status": "PASS", "records": records,
        "external_connection": False, "artifact_file_required": False, "mastery": "NOT_ESTABLISHED"}


def x8(j, fixtures):
    knowledge = fixtures["knowledge"]
    kid = knowledge["knowledge_id"]
    revised = j.seed("knowledge_review", {"id": kid, "body": {"action": "modified", "new_body": knowledge["body"] + "\n" + j.tag + " 后继修订，旧引用不自动迁移。",
        "expected_version": knowledge["version"], "reviewer": "SYNTHETIC_NATIVE_ACTOR_NOT_OWNER", "note": "本批同对象当前性工程观察"}})
    qualification = j.read("knowledge_qualification", {"id": kid})
    assert qualification["active"] is False and qualification["currentness"] == "superseded"
    first = x8_read(j, fixtures, "before-cold")
    j.cold()
    reopened = x8_read(j, fixtures, "after-cold")
    assert first == reopened
    j.report["consumers"]["x8"] = {"status": "PASS", "original_knowledge_id": kid, "revision_receipt": revised,
        "qualification": qualification, **first, "cold_reopen_all_four": True,
        "consumers": ["research", "pinned_reference", "course", "ai_asset"], "seed_revision_is_UI_action": False}


def x8_read(j, fixtures, stage):
    knowledge, research, asset, course = (fixtures[key] for key in ("knowledge", "research", "asset", "course"))
    kid = knowledge["knowledge_id"]
    def notice(scope):
        css = '[aria-label="知识引用当前性"][data-knowledge-id=' + json.dumps(kid) + ']'
        j.wait("const roots=[...document.querySelectorAll(" + json.dumps('[aria-label=' + json.dumps(scope, ensure_ascii=False) + ']') + ")];return roots.some(root=>root.getClientRects().length&&!root.closest('[hidden],[aria-hidden=\"true\"],[inert]')&&[...root.querySelectorAll(" + json.dumps(css) + ")].some(n=>n.getClientRects().length&&!n.closest('[hidden]')&&n.textContent.includes('历史知识版本')&&n.textContent.includes('原引用保持不变')))")
    j.ui.page("05", confirm_navigation=True)
    j.summary("研究文档与版本")
    j.click("刷新文档列表")
    j.list_button(research["title"] + " · 版本 1", "更多文档", j.scope("研究文档列表"))
    j.click("证据对比 (1)")
    # Opening a research document may already select its first material.
    choice = j.scope("材料与原文") + "//button[normalize-space(.)='材料 1 · 选择对照']"
    if j.js("return !!document.evaluate(" + json.dumps(choice) + ",document,null,9,null).singleNodeValue"):
        j.ui.click_revealed_selector(choice)
    notice("材料与原文")
    j.screenshot("v3-x8-research-history-" + stage + ".png")
    j.click("查看出处原文", j.scope("材料与原文"))
    notice("固定版本引用阅读")
    j.text("固定版本引用阅读", knowledge["body"])
    j.screenshot("v3-x8-pinned-history-" + stage + ".png")
    j.click("关闭引用")
    j.ui.page("07", confirm_navigation=True)
    j.click("课程与课时", j.scope("学习内容导航"))
    j.click("刷新课程", j.scope("已保存课程"))
    j.list_button(course["manifest"]["title"], "读取更多课程", j.scope("已保存课程"))
    notice("课程候选课时")
    j.text("课程候选课时", "历史课程")
    j.screenshot("v3-x8-course-history-" + stage + ".png")
    j.ui.page("13", confirm_navigation=True)
    j.click("AI 资产候选", j.scope("上下文对象类型"))
    j.click("刷新资产", j.scope("AI 基础资产"))
    j.list_button(asset["title"] + " · v" + str(asset["version"]), "更多资产", j.scope("AI 基础资产"))
    notice("AI 基础资产")
    j.screenshot("v3-x8-asset-history-" + stage + ".png")
    for doc in (research, asset):
        assert snapshot(j.read("document_get", {"document_id": doc["document_id"]})) == snapshot(doc)
    old_course = j.read("course_get", {"course_id": course["manifest"]["manifest_id"]})
    assert old_course["stale"] is True and old_course["manifest"] == course["manifest"]
    assert j.read("knowledge_get", {"id": kid})["body"] == knowledge["body"]
    return {"fixed_research": snapshot(research), "fixed_asset": snapshot(asset),
            "fixed_course_id": course["manifest"]["manifest_id"], "original_knowledge_body_sha256": digest(knowledge["body"].encode())}


def run(*, ui, bridge, js, wait, restart, screenshot, work, report, model, seed=None):
    j = Journey(ui=ui, bridge=bridge, js=js, wait=wait, restart=restart, screenshot=screenshot,
                work=work, report=report, model=model)
    state = j.read("ui_state_read")
    if seed:
        assert all(report.get("restore", {}).get("receipt", {}).get(key) is True for key in ("ok", "verified", "authorization_requires_new_grants")), "Seed consumers require the formal restore receipt"
    if state["recovery_requires_confirmation"]:
        j.click("保留恢复候选")
        j.until(lambda: j.read("ui_state_read"), lambda value: value["recovery_requires_confirmation"] is False)
    fixtures = initialize(j, seed)
    report["fixtures"] = fixtures
    j.observe()
    if seed:
        show_seed_answers(j, seed)
    deeptutor(j, fixtures)
    scenes(j, fixtures)
    canvas(j)
    external_practice(j, fixtures)
    x8(j, fixtures)
    cancellation(j, fixtures)
    report["ui_operation_receipts"].extend(j.observations())
    report["model_calls"] = model.calls
    report["status"] = "PASS"
    report["same_object_scope"] = "RESTORED_CL07_SEED_PLUS_EXPLICIT_CONSUMER_FIXTURES" if seed else "NEW_SYNTHETIC_CONSUMER_FIXTURES_ONLY"
    report["v3_complete"] = False  # Parent combines separate model/installed/Owner evidence.
    return report
