//! Real workers and Core/CAS with controlled text/CSV/Markdown and the existing golden DOCX.
//! This qualifies the API contract; it is not a real-corpus or native layout claim.
use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use base64::Engine;
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::{path::PathBuf, time::Duration};
use tower::ServiceExt;

async fn call(app: &axum::Router, method: &str, path: &str, body: Value) -> (StatusCode, Value) {
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("content-type", "application/json")
                .header(
                    "idempotency-key",
                    format!("test-{}", path.replace('/', "-")),
                )
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

#[tokio::test]
async fn text_docx_failure_and_reopen_keep_operation_qualifications_separate() {
    let dir = tempfile::tempdir().unwrap();
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").expect("use dev.py"));
    let db = dir.path().join("db.sqlite");
    let executor = archeaxis_application::executor::Executor::open_routes(
        &db,
        &dir.path().join("staging"),
        &python,
        &repo.join("services/python-workers/transport/text_ndjson.py"),
        &[
            (
                "text.extract",
                repo.join("services/python-workers/document/worker_text.py"),
            ),
            (
                "office.structure",
                repo.join("services/python-workers/document/worker_office.py"),
            ),
        ],
    )
    .await
    .unwrap();
    let app = archeaxis_api::runtime::router(executor.clone());
    let docx = std::fs::read(repo.join("tests/fixtures/golden/golden-docx-anchor.docx")).unwrap();
    let cases = [
        (
            "plain.txt",
            "text",
            b"Known text\nChinese: \xe6\x98\x9f\xe7\x8e\xaf\n".to_vec(),
            true,
        ),
        ("sample.docx", "office", docx, true),
        ("broken.docx", "office", b"not a zip".to_vec(), false),
        (
            "table.csv",
            "text",
            "name,note\r\n星环,\"quoted, value\"\r\n"
                .as_bytes()
                .to_vec(),
            true,
        ),
        (
            "notes.md",
            "text",
            "# 星环\n\nA [local link](./source.txt).\n"
                .as_bytes()
                .to_vec(),
            true,
        ),
    ];
    let mut saved = Vec::new();
    for (index, (name, kind, bytes, success)) in cases.into_iter().enumerate() {
        let (status,import) = call(&app,"POST","/api/v1/imports",json!({"name":name,"content_base64":base64::engine::general_purpose::STANDARD.encode(&bytes)})).await;
        assert_eq!(status, StatusCode::ACCEPTED, "{import}");
        let source = import["source_id"].as_str().unwrap();
        let job = format!("format-{index}");
        let (status, _) = call(
            &app,
            "POST",
            "/api/v1/jobs",
            json!({"job_id":job,"kind":kind,"input_ref":source}),
        )
        .await;
        assert_eq!(status, StatusCode::ACCEPTED);
        let path = format!("/api/v1/sources/{source}/jobs/{job}/format-qualification");
        let (status, before) = call(&app, "GET", &path, Value::Null).await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(before["operations"]["extract"]["status"], "NOT_EXECUTED");
        assert!(before["attempt"].is_null());
        let (status, started) = call(
            &app,
            "POST",
            &format!("/api/v1/jobs/{job}/executions"),
            json!({"deadline_ms":60000}),
        )
        .await;
        assert_eq!(status, StatusCode::ACCEPTED, "{started}");
        tokio::time::timeout(Duration::from_secs(60), async {
            loop {
                let (_, state) =
                    call(&app, "GET", &format!("/api/v1/jobs/{job}"), Value::Null).await;
                if state["state"] == "succeeded" || state["state"] == "failed" {
                    break;
                }
                tokio::time::sleep(Duration::from_millis(20)).await;
            }
        })
        .await
        .unwrap();
        let (_, after) = call(&app, "GET", &path, Value::Null).await;
        assert_eq!(after["source_revision"], import["sha256"]);
        assert_eq!(after["source_id"], source);
        assert_eq!(after["job_id"], job);
        assert_eq!(after["job_kind"], kind);
        assert_eq!(after["qualification_version"], 1);
        assert_eq!(after["core_version"], env!("CARGO_PKG_VERSION"));
        assert_eq!(
            after["operations"]["extract"]["status"],
            if success { "QUALIFIED" } else { "FAILED" },
            "{after}"
        );
        assert_eq!(after["operations"]["store"]["status"], "RECORDED");
        assert_eq!(
            after["operations"]["export"]["scope"],
            "ORIGINAL_BYTES_ONLY; use source original endpoint"
        );
        for op in ["edit", "roundtrip"] {
            assert_eq!(after["operations"][op]["status"], "UNVERIFIED");
        }
        if success {
            assert_eq!(after["execution_succeeded"], true);
            assert_eq!(after["qualification_evidence"], "COMPLETE");
            assert!(after["engine_version"].as_str().is_some(), "{after}");
            assert!(after["loss"]["receipt_ref"].as_str().is_some());
            if matches!(name, "table.csv" | "notes.md") {
                // These are real worker projections over controlled samples, not
                // native editing, native layout or corpus-wide qualification.
                assert_eq!(after["engine"], "python-worker-text");
                assert_eq!(after["attempt"], 1);
                assert_eq!(after["attempt_state"], "succeeded");
                assert_eq!(after["operations"].as_object().unwrap().len(), 6);
                assert_eq!(after["operations"]["preview"]["status"], "QUALIFIED");
                assert_eq!(
                    after["operations"]["preview"]["scope"],
                    "DERIVED_TEXT_PROJECTION; native visual fidelity unqualified"
                );
                assert_eq!(after["operations"]["export"]["status"], "AVAILABLE");
                let (status, text) = call(
                    &app,
                    "GET",
                    &format!("/api/v1/jobs/{job}/outputs/text"),
                    Value::Null,
                )
                .await;
                assert_eq!(status, StatusCode::OK);
                assert_eq!(text["content"], std::str::from_utf8(&bytes).unwrap());
                let (status, loss) = call(
                    &app,
                    "GET",
                    &format!("/api/v1/jobs/{job}/outputs/loss_report"),
                    Value::Null,
                )
                .await;
                assert_eq!(status, StatusCode::OK);
                let receipt: Value =
                    serde_json::from_str(loss["content"].as_str().unwrap()).unwrap();
                assert_eq!(receipt["engine"], after["engine"]);
                assert_eq!(receipt["engine_version"], after["engine_version"]);
                let facts = &receipt["params"]["format"];
                assert_eq!(facts["parsed"], true);
                if name == "table.csv" {
                    assert_eq!(after["media_type"], "text/csv");
                    assert_eq!(facts["format"], "csv");
                    assert_eq!(facts["row_count"], 2);
                    assert_eq!(facts["column_count"], 2);
                    assert!(
                        facts["locations"]
                            .as_array()
                            .unwrap()
                            .iter()
                            .any(|cell| cell["coordinate"] == "B2"
                                && cell["value"] == "quoted, value")
                    );
                } else {
                    assert_eq!(after["media_type"], "text/markdown");
                    assert_eq!(facts["format"], "markdown");
                    assert_eq!(facts["heading_count"], 1);
                    assert_eq!(facts["headings"][0]["text"], "星环");
                    assert_eq!(facts["markdown_link_count"], 1);
                }
                for (output_kind, envelope) in [("text", &text), ("loss_report", &loss)] {
                    let output = after["outputs"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .find(|output| output["kind"] == output_kind)
                        .unwrap();
                    assert_eq!(output["sha256"], envelope["metadata"]["sha256"]);
                    assert_eq!(output["byte_length"], envelope["metadata"]["byte_length"]);
                    assert_eq!(output["schema"], envelope["metadata"]["schema"]);
                }
            }
        } else {
            assert_eq!(after["loss"]["status"], "unknown");
            assert!(!after.to_string().contains("QUALIFIED"));
        }
        let (_, original) = call(
            &app,
            "GET",
            &format!("/api/v1/sources/{source}/original"),
            Value::Null,
        )
        .await;
        assert_eq!(
            base64::engine::general_purpose::STANDARD
                .decode(original["content_base64"].as_str().unwrap())
                .unwrap(),
            bytes
        );
        let (mismatch, _) = call(
            &app,
            "GET",
            &format!("/api/v1/sources/missing/jobs/{job}/format-qualification"),
            Value::Null,
        )
        .await;
        assert_eq!(mismatch, StatusCode::NOT_FOUND);
        saved.push((path, after));
    }
    drop(app);
    drop(executor);
    let reopened = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    for (path, expected) in saved {
        let (status, value) = call(&reopened, "GET", &path, Value::Null).await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(value, expected, "qualification survives Core reopen");
        println!("FORMAT_QUALIFICATION_SAMPLE={value}");
    }
}

#[tokio::test]
async fn successful_execution_without_usable_receipt_is_not_qualified() {
    use sha2::{Digest, Sha256};
    // Seed controlled corrupt/incomplete persisted fixtures before starting the
    // API Store. There is never a second writer beside a running canonical Store.
    for case in [
        "missing",
        "oversize",
        "unreadable",
        "missing_engine",
        "missing_version",
        "pdf_placeholder_version",
        "bad_text_metadata",
        "bad_receipt_metadata",
        "bad_receipt_hash",
        "unknown_loss_count",
    ] {
        let dir = tempfile::tempdir().unwrap();
        let db = dir.path().join("fixture.sqlite");
        let mut conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
        let source = match archeaxis_domain::source::import_source(
            &mut conn,
            b"known text",
            "sample.txt",
            None,
        )
        .unwrap()
        {
            archeaxis_domain::source::ImportOutcome::Imported { source_id, .. }
            | archeaxis_domain::source::ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        archeaxis_application::jobs::enqueue(&mut conn, "job", "text", &source).unwrap();
        conn.execute("UPDATE jobs SET state='succeeded' WHERE job_id='job'", [])
            .unwrap();
        conn.execute("INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('job',1,'request','{}','succeeded')",[]).unwrap();
        let mut receipt = json!({"engine":"test-controlled","engine_version":"1","losses":[]});
        if case == "pdf_placeholder_version" {
            receipt["engine"] = json!("pymupdf-native-pdf");
            receipt["engine_version"] = json!("pymupdf");
        }
        if case == "missing_engine" {
            receipt.as_object_mut().unwrap().remove("engine");
        }
        if case == "missing_version" {
            receipt["engine_version"] = json!(" ");
        }
        if case == "unknown_loss_count" {
            receipt.as_object_mut().unwrap().remove("losses");
        }
        let wire = if case == "oversize" {
            " ".repeat(262145)
        } else if case == "unreadable" {
            "{not-json".to_string()
        } else {
            receipt.to_string()
        };
        for (kind, content, schema) in [
            ("text", "known text".to_string(), "archeaxis.text/v1"),
            ("loss_report", wire, "archeaxis.loss-receipt/v1"),
        ] {
            if case == "missing" && kind == "loss_report" {
                continue;
            }
            let mut metadata = json!({"kind":kind,"schema":schema,"byte_length":content.len(),
                "sha256":format!("{:x}",Sha256::digest(content.as_bytes()))});
            if (case == "bad_text_metadata" && kind == "text")
                || (case == "bad_receipt_metadata" && kind == "loss_report")
            {
                metadata.as_object_mut().unwrap().remove("byte_length");
            }
            if case == "bad_receipt_hash" && kind == "loss_report" {
                metadata["sha256"] = json!("0".repeat(64));
            }
            conn.execute("INSERT INTO job_outputs(job_id,attempt,kind,metadata_json,content) VALUES('job',1,?1,?2,?3)",
                rusqlite::params![kind,metadata.to_string(),content]).unwrap();
        }
        drop(conn);
        let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
        let (status, value) = call(
            &app,
            "GET",
            &format!("/api/v1/sources/{source}/jobs/job/format-qualification"),
            Value::Null,
        )
        .await;
        assert_eq!(status, StatusCode::OK, "{case}: {value}");
        assert_eq!(value["execution_succeeded"], true, "{case}");
        for op in ["preview", "extract"] {
            assert_eq!(
                value["operations"][op]["status"],
                if case == "unknown_loss_count" {
                    "QUALIFIED"
                } else {
                    "UNVERIFIED"
                },
                "{case}: {value}"
            );
        }
        if case != "bad_text_metadata" {
            assert_eq!(value["loss"]["status"], "unknown", "{case}");
        }
    }
}

#[tokio::test]
async fn static_unknown_pdf_can_execute_with_live_version_and_qualify_its_file() {
    let d = tempfile::tempdir().unwrap();
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").expect("declared Python"));
    let generated = std::process::Command::new(&python).args(["-B","-c",
        "import pymupdf,sys;d=pymupdf.open();d.new_page().insert_text((72,100),'PDF qualification 6371 km');sys.stdout.buffer.write(d.tobytes())"]).output().unwrap();
    assert!(
        generated.status.success(),
        "required project PDF dependency missing"
    );
    let e = archeaxis_application::executor::Executor::open_routes(
        &d.path().join("db"),
        &d.path().join("staging"),
        &python,
        &repo.join("services/python-workers/transport/text_ndjson.py"),
        &[(
            "pdf.extract",
            repo.join("services/python-workers/document/worker_pdf.py"),
        )],
    )
    .await
    .unwrap();
    let app = archeaxis_api::runtime::router(e.clone());
    let (_, static_read) = call(
        &app,
        "POST",
        "/api/v1/operation-readiness",
        json!({"scope":"pdf-before-run","operations":["pdf.extract"]}),
    )
    .await;
    assert_eq!(static_read["operations"][0]["dependencies"], "UNKNOWN");
    archeaxis_api::runtime::readiness::require_execution_dependencies(&e, "pdf.extract")
        .await
        .unwrap();
    let (status,import) = call(&app,"POST","/api/v1/imports",json!({"name":"controlled.pdf","content_base64":base64::engine::general_purpose::STANDARD.encode(generated.stdout)})).await;
    assert_eq!(status, StatusCode::ACCEPTED, "{import}");
    let source = import["source_id"].as_str().unwrap();
    let (status, _) = call(
        &app,
        "POST",
        "/api/v1/jobs",
        json!({"job_id":"pdf-current","kind":"pdf","input_ref":source}),
    )
    .await;
    assert_eq!(status, StatusCode::ACCEPTED);
    let (status, started) = call(
        &app,
        "POST",
        "/api/v1/jobs/pdf-current/executions",
        json!({"deadline_ms":30000}),
    )
    .await;
    assert_eq!(status, StatusCode::ACCEPTED, "{started}");
    tokio::time::timeout(Duration::from_secs(30), async {
        loop {
            let (_, job) = call(&app, "GET", "/api/v1/jobs/pdf-current", Value::Null).await;
            if job["state"] == "succeeded" || job["state"] == "failed" {
                assert_eq!(job["state"], "succeeded", "{job}");
                break;
            }
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
    })
    .await
    .unwrap();
    let (status, qualified) = call(
        &app,
        "GET",
        &format!("/api/v1/sources/{source}/jobs/pdf-current/format-qualification"),
        Value::Null,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(
        qualified["operations"]["extract"]["status"], "QUALIFIED",
        "{qualified}"
    );
    assert!(archeaxis_application::attempts::pdf_engine_version(
        qualified["engine_version"].as_str().unwrap()
    ));
    let saved: String = e
        .store()
        .submit_wait(|c| {
            c.query_row(
                "SELECT content FROM job_outputs WHERE job_id='pdf-current' AND kind='loss_report'",
                [],
                |r| r.get(0),
            )
        })
        .await
        .unwrap()
        .unwrap();
    let loss: Value = serde_json::from_str(&saved).unwrap();
    assert_eq!(loss["engine_version"], qualified["engine_version"]);
    assert_eq!(
        loss["params"]["runtime_dependency"]["version"],
        qualified["engine_version"]
    );
    assert_eq!(qualified["operations"]["roundtrip"]["status"], "UNVERIFIED");
}
