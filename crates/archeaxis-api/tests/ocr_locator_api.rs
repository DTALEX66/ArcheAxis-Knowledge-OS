//! Synthetic contract rows test native OCR locator validation, not parser fidelity.
use archeaxis_api::app;
use archeaxis_domain::source::{self, ImportOutcome};
use archeaxis_store_sqlite::init_workspace;
use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use tower::ServiceExt;

const TEXT: &str = "第一页中文\n第二页中文\n";

fn digest(raw: &str) -> String {
    format!("{:x}", Sha256::digest(raw.as_bytes()))
}

fn seed(db: &str) -> (String, Value) {
    let mut conn = init_workspace(db).unwrap();
    let raw = b"synthetic image contract bytes, not an OCR fixture";
    let source_id = match source::import_source(&mut conn, raw, "fixture.png", None).unwrap() {
        ImportOutcome::Imported { source_id, .. } | ImportOutcome::Duplicate { source_id, .. } => {
            source_id
        }
    };
    let revision = format!("{:x}", Sha256::digest(raw));
    archeaxis_application::jobs::enqueue(&mut conn, "ocr-job", "image", &source_id).unwrap();
    let structure = json!([
        {"kind":"line","path":["line-1"],"char_start":0,"char_end":6},
        {"kind":"line","path":["line-2"],"char_start":6,"char_end":12},
    ])
    .to_string();
    let loss = json!({"engine":"python-worker-ocr","params":{"input_transport":"stdin",
        "input_bytes":raw.len(),"input_sha256":revision,"regions":[
            {"region":0,"text":"第一页中文","char_start":0,"char_end":5,"bbox":{"x":2,"y":3,"w":20,"h":8}},
            {"region":1,"text":"第二页中文","char_start":6,"char_end":11,"bbox":{"x":2,"y":14,"w":20,"h":8}}
        ]}}).to_string();
    let wire = json!({"schema":"archeaxis.worker-request/v1","type":"job_request","request_id":"ocr-request","job_id":"ocr-job","attempt":1,"capability":"image.ocr",
                      "inputs":[{"sha256":revision,"media_type":"image/png"}]}).to_string();
    conn.execute("INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('ocr-job',1,'ocr-request',?1,'succeeded')", [&wire]).unwrap();
    conn.execute(
        "UPDATE jobs SET state='succeeded' WHERE job_id='ocr-job'",
        [],
    )
    .unwrap();
    for (kind, content) in [
        ("text", TEXT),
        ("document_structure", structure.as_str()),
        ("loss_report", loss.as_str()),
    ] {
        let metadata =
            json!({"kind":kind,"sha256":digest(content),"byte_length":content.len()}).to_string();
        conn.execute("INSERT INTO job_outputs(job_id,attempt,kind,metadata_json,content) VALUES('ocr-job',1,?1,?2,?3)", rusqlite::params![kind,metadata,content]).unwrap();
    }
    let body = json!({"revision":revision,"checksum":digest("第二页中文\n"),
                      "position":json!({"type":"ocr_line","kind":"line","job_id":"ocr-job","attempt":1,
                                        "path":["line-2"],"char_start":6,"char_end":12,
                                        "result_sha256":digest(&structure),"loss_sha256":digest(&loss)}).to_string()});
    (source_id, body)
}

async fn call(db: &str, method: &str, path: &str, payload: Value) -> (StatusCode, Value) {
    let response = app(db)
        .unwrap()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("x-archeaxis-actor", "human")
                .header("content-type", "application/json")
                .body(if method == "GET" {
                    Body::empty()
                } else {
                    Body::from(payload.to_string())
                })
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
async fn native_ocr_line_revalidates_after_reopen_and_never_rewrites_history() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("ocr.sqlite").to_str().unwrap().to_owned();
    let (source, body) = seed(&db);
    let route = format!("/api/v1/sources/{source}/anchors");
    let (status, anchor) = call(&db, "POST", &route, body).await;
    assert_eq!(status, StatusCode::CREATED, "{anchor}");
    let before = call(&db, "GET", &route, Value::Null).await.1;
    let resolve = format!("{route}/{}/resolve", anchor["anchor_id"].as_str().unwrap());
    for _ in 0..2 {
        let (status, result) = call(&db, "GET", &resolve, Value::Null).await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(result["status"], "CURRENT");
        assert_eq!(result["scope"], "locator_provenance_only");
        assert_eq!(call(&db, "GET", &route, Value::Null).await.1, before);
    }
    let conn = init_workspace(&db).unwrap();
    conn.execute("INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('ocr-job',2,'later','{}','running')",[]).unwrap();
    assert_eq!(
        call(&db, "GET", &resolve, Value::Null).await.1["status"],
        "STALE"
    );
    assert_eq!(call(&db, "GET", &route, Value::Null).await.1, before);
}

#[tokio::test]
async fn claimed_ocr_line_span_result_or_checksum_cannot_substitute_for_native_output() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("ocr.sqlite").to_str().unwrap().to_owned();
    let (source, body) = seed(&db);
    let route = format!("/api/v1/sources/{source}/anchors");
    for (field, value) in [
        ("path", json!(["line-99"])),
        ("char_start", json!(7)),
        ("char_end", json!(11)),
        ("result_sha256", json!("0".repeat(64))),
        ("loss_sha256", json!("0".repeat(64))),
        ("bbox", json!({"x":1,"y":1,"w":2,"h":2})),
        ("kind", json!("bbox")),
        ("attempt", json!(2)),
    ] {
        let mut candidate = body.clone();
        let mut position: Value =
            serde_json::from_str(candidate["position"].as_str().unwrap()).unwrap();
        position[field] = value;
        candidate["position"] = json!(position.to_string());
        assert_eq!(
            call(&db, "POST", &route, candidate).await.0,
            StatusCode::BAD_REQUEST,
            "{field}"
        );
    }
    let mut wrong = body;
    wrong["checksum"] = json!("0".repeat(64));
    assert_eq!(
        call(&db, "POST", &route, wrong).await.0,
        StatusCode::BAD_REQUEST
    );
    assert_eq!(
        call(&db, "GET", &route, Value::Null).await.1["anchors"],
        json!([])
    );
}

#[tokio::test]
async fn tampered_output_metadata_or_foreign_capability_is_refused() {
    for tamper in ["text", "document_structure", "loss_report", "request"] {
        let dir = tempfile::tempdir().unwrap();
        let db = dir.path().join("ocr.sqlite").to_str().unwrap().to_owned();
        let (source, body) = seed(&db);
        let route = format!("/api/v1/sources/{source}/anchors");
        let (status, anchor) = call(&db, "POST", &route, body.clone()).await;
        assert_eq!(status, StatusCode::CREATED, "{anchor}");
        let historical = call(&db, "GET", &route, Value::Null).await.1;
        let conn = init_workspace(&db).unwrap();
        if tamper == "request" {
            let wire: String = conn
                .query_row(
                    "SELECT request_json FROM job_attempts WHERE job_id='ocr-job'",
                    [],
                    |r| r.get(0),
                )
                .unwrap();
            let mut request: Value = serde_json::from_str(&wire).unwrap();
            request["capability"] = json!("text.extract");
            conn.execute(
                "UPDATE job_attempts SET request_json=?1 WHERE job_id='ocr-job'",
                [request.to_string()],
            )
            .unwrap();
        } else {
            conn.execute(
                "UPDATE job_outputs SET metadata_json='{}' WHERE kind=?1",
                [tamper],
            )
            .unwrap();
        }
        assert_eq!(
            call(&db, "POST", &route, body).await.0,
            StatusCode::BAD_REQUEST,
            "{tamper}"
        );
        let resolve = format!("{route}/{}/resolve", anchor["anchor_id"].as_str().unwrap());
        assert_eq!(
            call(&db, "GET", &resolve, Value::Null).await.1["status"],
            "STALE"
        );
        assert_eq!(call(&db, "GET", &route, Value::Null).await.1, historical);
    }
}

#[tokio::test]
async fn honest_receipt_identity_and_actual_region_spans_are_required() {
    for tamper in [
        "input_sha",
        "input_bytes",
        "engine",
        "empty_regions",
        "word",
        "box",
        "span",
    ] {
        let dir = tempfile::tempdir().unwrap();
        let db = dir.path().join("ocr.sqlite").to_str().unwrap().to_owned();
        let (source, mut body) = seed(&db);
        let conn = init_workspace(&db).unwrap();
        let old: String = conn
            .query_row(
                "SELECT content FROM job_outputs WHERE kind='loss_report'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        let mut loss: Value = serde_json::from_str(&old).unwrap();
        match tamper {
            "input_sha" => loss["params"]["input_sha256"] = json!("0".repeat(64)),
            "input_bytes" => loss["params"]["input_bytes"] = json!(1),
            "engine" => loss["engine"] = json!("caption-candidate"),
            "empty_regions" => loss["params"]["regions"] = json!([]),
            "word" => loss["params"]["regions"][1]["text"] = json!("invented word"),
            "box" => loss["params"]["regions"][1]["bbox"]["w"] = json!(0),
            "span" => loss["params"]["regions"][1]["char_end"] = json!(999),
            _ => unreachable!(),
        }
        let content = loss.to_string();
        let meta =
            json!({"kind":"loss_report","sha256":digest(&content),"byte_length":content.len()})
                .to_string();
        conn.execute(
            "UPDATE job_outputs SET content=?1,metadata_json=?2 WHERE kind='loss_report'",
            rusqlite::params![content, meta],
        )
        .unwrap();
        let mut position: Value = serde_json::from_str(body["position"].as_str().unwrap()).unwrap();
        position["loss_sha256"] = json!(digest(&content));
        body["position"] = json!(position.to_string());
        let route = format!("/api/v1/sources/{source}/anchors");
        assert_eq!(
            call(&db, "POST", &route, body).await.0,
            StatusCode::BAD_REQUEST,
            "{tamper}"
        );
        assert_eq!(
            call(&db, "GET", &route, Value::Null).await.1["anchors"],
            json!([])
        );
    }
}
