"""Measure authored Chinese scan text through the qualified Core/worker candidate.

Truth is frozen before OCR. Raw and whitespace-compacted CER are both retained;
the local fixture gate is not an Owner/content-quality acceptance claim. Uses an
independent restore of the prior authored course workspace, never a user library.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import uuid

import aaos01_office_runtime_loop as office
import aaos01_common_light_ocr_runtime_loop as light
import aaos01_common_chinese_ocr_runtime_loop as chinese
import aaos_public_research_runtime_loop as helper
from aaos_research_learning_runtime import require, sha

ROOT = Path(__file__).resolve().parents[2]
LINES = [
    ["星环知识系统中文扫描测试", "本页是项目自造资料，仅用于识别测试。",
     "原始文件应当保留，转换正文单独保存。", "每次识别都需要记录来源、位置与损失。",
     "支持和反对的证据应分别列出。", "无法确认的内容保留为待核实。",
     "重复提交不得创建重复复习记录。", "日期：2026年10月22日。编号：6371。"],
    ["第二页：资料整理与学习", "先阅读资料，再用自己的话独立作答。",
     "查看核对内容之后，记录真实反馈。", "模型置信度不能当作识别准确率。",
     "来源版本发生变化时，应显示冲突。", "备份恢复后，原件和引用应保持一致。",
     "这是一段用于比较全文的中文说明。", "数量：42。页码：2。编号：8429。"],
]
GENERATOR = r'''
import sys,json
from pathlib import Path
import fitz
root=Path(sys.argv[1]);lines=json.loads(sys.argv[2]);root.mkdir(exist_ok=False)
scan=fitz.open()
for index,rows in enumerate(lines):
    native=fitz.open();page=native.new_page(width=720,height=500)
    for i,text in enumerate(rows):
        page.insert_text((36,55+i*51),text,fontname='china-s',fontsize=20 if index==0 else 16)
    pix=page.get_pixmap(dpi=150);png=pix.tobytes('png')
    (root/f'page-{index+1}.png').write_bytes(png)
    if index==1:(root/'page-2.jpeg').write_bytes(pix.tobytes('jpeg',jpg_quality=85))
    target=scan.new_page(width=720,height=500);target.insert_image(target.rect,stream=png)
    native.close()
(root/'scanned.pdf').write_bytes(scan.tobytes());scan.close()
check=fitz.open(root/'scanned.pdf');assert len(check)==2 and all(not p.get_text().strip() for p in check)
print(json.dumps({'pymupdf':fitz.VersionBind,'pages':2,'embedded_text_layer':False,'dpi':150,'font':'china-s','font_sizes':[20,16],'jpeg_quality':85}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--input-receipt", type=Path, required=True)
    args = parser.parse_args()
    dev = office.load("scan_quality_dev", ROOT / "scripts/runtime/dev.py")
    require(os.environ.get("ARCHEAXIS_RUN_ROOT"), "Use runtime/dev.py")
    run = dev.safe_path(Path(os.environ["ARCHEAXIS_RUN_ROOT"]))
    paths = dev.layout(ROOT, run.name)
    require(run == paths["run"], "Foreign run")

    def owned(path):
        path = dev.safe_path(path)
        path.relative_to(paths["dev"] / "runs")
        return path

    input_path = owned(args.input_receipt)
    prior = json.loads(input_path.read_text(encoding="utf-8"))
    require(prior["status"] == "PASS_DECLARED_INTEGRATED_SUBSET" and prior["independent_restore_equal"], "Unqualified prior")
    wrapper = json.loads((input_path.parent / "execution.json").read_text(encoding="utf-8"))
    require(wrapper["status"] == "LOCAL_PASS" and wrapper["source_consistent"], "Prior source changed")
    candidate = owned(args.candidate)
    original_workspace = owned(Path(prior["independent_workspace"]))
    manifest = json.loads((candidate / "candidate-manifest.json").read_text(encoding="utf-8"))
    previous = json.loads((owned(Path(prior["candidate"])) / "candidate-manifest.json").read_text(encoding="utf-8"))
    require(manifest["files"].keys() == previous["files"].keys(), "Different member set")
    require(all(v == previous["files"][n] for n, v in manifest["files"].items() if n != "ArcheAxis.exe"), "Backend changed")
    identity_names = ("ArcheAxis.exe", "core/archeaxis-api.exe", "worker-profile.json", "backend-runtime-manifest.json")
    before = {n: office.identity(candidate / n) for n in identity_names}
    require(all(v["sha256"] == manifest["files"][n]["sha256"] for n, v in before.items()), "Candidate identity mismatch")
    binary, tessdata = chinese.declared_ocr_resources()
    resources = chinese.validate_chinese_resources(binary, tessdata)
    environment = {"ARCHEAXIS_OCR_LANG": "chi_sim", "ARCHEAXIS_OCR_TESSDATA": str(tessdata),
                   "TESSDATA_PREFIX": str(tessdata), "TESSERACT_CMD": str(binary)}
    old_environment = {k: os.environ.get(k) for k in environment}
    launcher = office.load("scan_quality_launcher", ROOT / "scripts/release/backend_launcher.py")
    client = office.load("scan_quality_client", ROOT / "shared/core_client.py")
    quality = office.load("scan_quality_metrics", ROOT / "services/python-workers/evaluation/worker_quality.py")
    profile = launcher.load_profile(candidate)
    output = paths["artifacts"] / "chinese-scan-quality.json"
    require(not output.exists(), "Choose a new run ID")
    receipt = {"schema": "archeaxis.chinese-scan-quality/v1", "status": "RUNNING", "steps": [], "stopped": [],
               "candidate": str(candidate), "candidate_identity": before, "input": office.identity(input_path),
               "materials": "SYNTHETIC_AUTHORED", "execution": "ACTUAL_CORE_WORKERS",
               "gate": {"whitespace_compacted_CER_max": 0.05, "scope": "These authored fixtures only; engineering-selected threshold"},
               "limits": ["No natural scans, handwriting, table/column reading-order, native UI or installation qualification",
                          "No Owner acceptance or population accuracy claim; raw CER and observed failures remain visible",
                          "No model/public query/knowledge approval; prior objects remain unchanged"],
               "ocr_resources": resources, "cases": []}
    child = None
    base = token = None

    def checkpoint():
        output.write_bytes((json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))

    def call(method, path, body=None, expected=200, headers=None):
        status, value = client.call(base, method, path, token, body, extra_headers=headers, timeout=65)
        receipt["steps"].append({"method": method, "path": path, "status": status})
        checkpoint()
        require(status == expected, f"{method} {path}: expected {expected}, got {status}")
        return value

    def stop():
        nonlocal child
        helper.stop_owned(child, launcher, receipt["stopped"])
        child = None
        checkpoint()

    def restore(backup, workspace, target):
        backup_file = owned(workspace / "backups" / backup["filename"])
        require(sha(backup_file.read_bytes()) == backup["sha256"], "Backup hash changed")
        target.mkdir(exist_ok=False)
        operation = subprocess.run([str(candidate / "core/archeaxis-api.exe"), "--maintenance-restore",
                                    str(target / "workspace.sqlite"), str(backup_file)],
                                   capture_output=True, text=True, encoding="utf-8", timeout=90,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        require(operation.returncode == 0 and json.loads(operation.stdout).get("verified"), "Independent restore failed")
        return {"exit_code": operation.returncode, "stdout": operation.stdout, "stderr": operation.stderr}

    def metrics(name, prediction, truth):
        target = paths["artifacts"] / name
        target.mkdir(exist_ok=False)
        (target / "prediction.txt").write_bytes(prediction.encode("utf-8"))
        (target / "truth.txt").write_bytes(truth.encode("utf-8"))
        report = quality.evaluate(target / "prediction.txt", target / "truth.txt", sample_id=name, run_id=run.name, normalize="none")
        normalized_prediction, normalized_truth = "".join(prediction.split()), "".join(truth.split())
        (target / "prediction.compact.txt").write_bytes(normalized_prediction.encode("utf-8"))
        (target / "truth.compact.txt").write_bytes(normalized_truth.encode("utf-8"))
        compact = quality.evaluate(target / "prediction.compact.txt", target / "truth.compact.txt", sample_id=name + "-compact", run_id=run.name, normalize="none")
        measured = next(r["value"] for r in compact["rows"] if r["metric"] == "cer")
        return {"raw_report": report, "whitespace_compacted_report": compact,
                "normalization": "Remove Python Unicode whitespace only; no punctuation/case/content repair",
                "passed_declared_gate": measured <= receipt["gate"]["whitespace_compacted_CER_max"]}

    try:
        # Freeze the authored truth bytes before rendering or seeing an OCR result.
        truth = ["\n".join(rows) + "\n" for rows in LINES]
        receipt["truth_sha256"] = [sha(text.encode("utf-8")) for text in truth]
        checkpoint()
        material = run / "materials"
        generated = subprocess.run([str(profile["python"]), "-B", "-I", "-c", GENERATOR, str(material), json.dumps(LINES, ensure_ascii=False)],
                                   capture_output=True, text=True, encoding="utf-8", timeout=60,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        receipt["generator"] = {"exit_code": generated.returncode, "stdout": generated.stdout, "stderr": generated.stderr}
        require(generated.returncode == 0, "Candidate fixture generation failed")
        os.environ.update(environment)
        child, base, token, _ = helper.hidden_start(office, candidate, original_workspace, launcher)
        baseline_paths = [f"/api/v1/documents/{prior['document_id']}", f"/api/v1/courses/{prior['course_id']}",
                          f"/api/v1/learning/items/{prior['item_key']}/assessment", f"/api/v1/learning/events/{prior['item_key']}"]
        baseline = {path: call("GET", path) for path in baseline_paths}
        backup = call("POST", "/api/v1/workspace/backups", {}, 201)
        require(backup["verified"], "Input backup not verified")
        stop()
        workspace = paths["artifacts"] / "scan-quality-workspace"
        receipt["input_restore"] = restore(backup, original_workspace, workspace)
        receipt["workspace"] = str(workspace)
        child, base, token, _ = helper.hidden_start(office, candidate, workspace, launcher)
        for path, expected in baseline.items():
            require(call("GET", path) == expected, "Input restore changed prior object")
        snapshots = {}
        originals = {}

        def measure_image(source, job, snapshot, name, page_index):
            light.verify_artifacts(snapshot)
            predicted = snapshot["text"]["body"]["content"]
            loss = json.loads(snapshot["loss_report"]["body"]["content"])
            require(loss["params"]["lang"] == "chi_sim" and loss["params"]["regions"], "Wrong OCR lane or no boxes")
            record = {"name": name, "source": source, "job_id": job, "snapshot": snapshot,
                      "metrics": metrics(name, predicted, truth[page_index])}
            receipt["cases"].append(record)
            snapshots[job] = snapshot
            positions = json.loads(snapshot["document_structure"]["body"]["content"])
            selected = next(p for p in positions if predicted[p["char_start"]:p["char_end"]].strip())
            locator = {"type": "ocr_line", "job_id": job, "attempt": snapshot["job"]["body"]["attempt"],
                       "kind": selected["kind"], "path": selected["path"], "char_start": selected["char_start"], "char_end": selected["char_end"],
                       "result_sha256": snapshot["document_structure"]["body"]["metadata"]["sha256"],
                       "loss_sha256": snapshot["loss_report"]["body"]["metadata"]["sha256"]}
            body = {"revision": source["sha256"], "position": json.dumps(locator),
                    "checksum": sha(predicted[selected["char_start"]:selected["char_end"]].encode("utf-8"))}
            record["location"] = light.located(call, source, body)
            checkpoint()

        for filename, kind in (("page-1.png", "image"), ("page-2.jpeg", "image"), ("scanned.pdf", "pdf")):
            raw = (material / filename).read_bytes()
            source = call("POST", "/api/v1/imports", client.import_request(filename, raw), 202)
            require(source["sha256"] == sha(raw), "Input hash mismatch")
            original_path = f"/api/v1/sources/{source['source_id']}/original"
            originals[original_path] = call("GET", original_path)
            require(base64.b64decode(originals[original_path]["content_base64"]) == raw, "Original changed")
            job = "scan-quality-" + uuid.uuid4().hex
            call("POST", "/api/v1/jobs", {"job_id": job, "kind": kind, "input_ref": source["source_id"]}, 202)
            snapshot = light.execute(call, client, base, token, job)
            if kind == "image":
                measure_image(source, job, snapshot, filename, 0 if filename.endswith("png") else 1)
            else:
                light.verify_artifacts(snapshot)
                require(not snapshot["text"]["body"]["content"].strip(), "Scan gained fabricated PDF text layer")
                require(json.loads(snapshot["loss_report"]["body"]["content"])["params"]["pages_without_text"] == [1, 2], "Missing scan loss")
                snapshots[job] = snapshot
                pages = call("GET", f"/api/v1/sources/{source['source_id']}/pages")
                require(pages["page_count"] == 2, "Missing PDF pages")
                for page in pages["pages"]:
                    page_job = f"{job}-page-{page['page']}"
                    page_snapshot = light.execute(call, client, base, token, page_job)
                    page_source = {"source_id": page["source_id"], "sha256": page["sha256"]}
                    measure_image(page_source, page_job, page_snapshot, f"pdf-page-{page['page']}", page["page"] - 1)
                receipt["pdf_page_relation"] = call("GET", f"/api/v1/sources/{source['source_id']}/pages")
                require(receipt["pdf_page_relation"]["recognised_count"] == 2, "PDF OCR pages incomplete")
        expected_anchors = {case["source"]["source_id"]: call("GET", f"/api/v1/sources/{case['source']['source_id']}/anchors") for case in receipt["cases"]}
        stop()
        child, base, token, _ = helper.hidden_start(office, candidate, workspace, launcher)
        for job, expected in snapshots.items():
            require(office.capture(client, base, token, job) == expected, "Restart changed OCR output")
        for path, expected in {**baseline, **originals}.items():
            require(call("GET", path) == expected, "Restart changed original/prior object")
        receipt["restart_equal"] = True
        backup = call("POST", "/api/v1/workspace/backups", {}, 201)
        require(backup["verified"], "Output backup unverified")
        receipt["restore_preview"] = call("POST", "/api/v2/workspace/restore/preview", {"backup_id": backup["backup_id"], "expected_sha256": backup["sha256"]})
        require(receipt["restore_preview"]["verified"] and receipt["restore_preview"]["compatible"], "Restore preview failed")
        stop()
        restored = paths["artifacts"] / "independent-scan-restore"
        receipt["output_restore"] = restore(backup, workspace, restored)
        child, base, token, _ = helper.hidden_start(office, candidate, restored, launcher)
        for job, expected in snapshots.items():
            require(office.capture(client, base, token, job) == expected, "Restore changed OCR output")
        for path, expected in {**baseline, **originals}.items():
            require(call("GET", path) == expected, "Restore changed original/prior object")
        for source_id, expected in expected_anchors.items():
            require(call("GET", f"/api/v1/sources/{source_id}/anchors") == expected, "Restore changed OCR anchors")
        for case in receipt["cases"]:
            source_id, anchor = case["source"]["source_id"], case["location"]["anchor"]
            require(call("GET", f"/api/v1/sources/{source_id}/anchors/{anchor['anchor_id']}/resolve") == case["location"]["resolution"], "Restored location changed")
        receipt.update({"independent_restore_equal": True, "independent_workspace": str(restored),
                        "status": "PASS_AUTHORED_SCAN_FIXTURES" if all(c["metrics"]["passed_declared_gate"] for c in receipt["cases"]) else "PARTIAL_QUALITY_GATE_FAILED"})
    except Exception as error:
        receipt.update(status="FAIL", error=f"{type(error).__name__}: {error}")
    finally:
        if child is not None:
            try:
                stop()
            except Exception as error:
                receipt.update(status="FAIL", cleanup_error=str(error))
        for key, value in old_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        receipt["candidate_unchanged"] = before == {n: office.identity(candidate / n) for n in identity_names}
        receipt["ocr_resources_unchanged"] = resources == chinese.validate_chinese_resources(binary, tessdata)
        if not receipt["candidate_unchanged"] or not receipt["ocr_resources_unchanged"]:
            receipt["status"] = "FAIL"
        checkpoint()
    print(json.dumps({"status": receipt["status"], "cases": len(receipt["cases"]), "receipt": str(output)}, ensure_ascii=False))
    return 0 if receipt["status"] == "PASS_AUTHORED_SCAN_FIXTURES" else 1


if __name__ == "__main__":
    raise SystemExit(main())
