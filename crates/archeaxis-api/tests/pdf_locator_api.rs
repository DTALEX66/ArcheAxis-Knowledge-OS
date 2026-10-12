//! Synthetic contract rows test native PDF locator validation, not parser fidelity.
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
    let raw = b"%PDF synthetic contract original";
    let source_id = match source::import_source(&mut conn, raw, "fixture.pdf", None).unwrap() {
        ImportOutcome::Imported { source_id, .. } | ImportOutcome::Duplicate { source_id, .. } => {
            source_id
        }
    };
    let revision = format!("{:x}", Sha256::digest(raw));
    archeaxis_application::jobs::enqueue(&mut conn, "pdf-job", "pdf", &source_id).unwrap();
    let structure = json!([
        {"kind":"line","path":["page-1","line-1"],"char_start":0,"char_end":6},
        {"kind":"line","path":["page-2","line-2"],"char_start":6,"char_end":12},
    ])
    .to_string();
    let wire = json!({"job_id":"pdf-job","attempt":1,"capability":"pdf.extract",
                      "inputs":[{"sha256":revision,"media_type":"application/pdf"}]})
    .to_string();
    conn.execute("INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('pdf-job',1,'pdf-request',?1,'succeeded')", [&wire]).unwrap();
    conn.execute(
        "UPDATE jobs SET state='succeeded' WHERE job_id='pdf-job'",
        [],
    )
    .unwrap();
    for (kind, content) in [("text", TEXT), ("document_structure", structure.as_str())] {
        let metadata =
            json!({"kind":kind,"sha256":digest(content),"byte_length":content.len()}).to_string();
        conn.execute("INSERT INTO job_outputs(job_id,attempt,kind,metadata_json,content) VALUES('pdf-job',1,?1,?2,?3)", rusqlite::params![kind,metadata,content]).unwrap();
    }
    let body = json!({"revision":revision,"checksum":digest("第二页中文\n"),
                      "position":json!({"type":"pdf_line","kind":"line","job_id":"pdf-job","attempt":1,
                                        "path":["page-2","line-2"],"char_start":6,"char_end":12,
                                        "result_sha256":digest(&structure)}).to_string()});
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
async fn native_pdf_page_line_revalidates_after_reopen_and_never_rewrites_history() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("pdf.sqlite").to_str().unwrap().to_owned();
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
    conn.execute("INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('pdf-job',2,'later','{}','running')",[]).unwrap();
    assert_eq!(
        call(&db, "GET", &resolve, Value::Null).await.1["status"],
        "STALE"
    );
    assert_eq!(call(&db, "GET", &route, Value::Null).await.1, before);
}

#[tokio::test]
async fn claimed_page_line_span_result_or_checksum_cannot_substitute_for_native_output() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("pdf.sqlite").to_str().unwrap().to_owned();
    let (source, body) = seed(&db);
    let route = format!("/api/v1/sources/{source}/anchors");
    for (field, value) in [
        ("path", json!(["page-1", "line-2"])),
        ("char_start", json!(7)),
        ("char_end", json!(11)),
        ("result_sha256", json!("0".repeat(64))),
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
    for tamper in ["text", "document_structure", "request"] {
        let dir = tempfile::tempdir().unwrap();
        let db = dir.path().join("pdf.sqlite").to_str().unwrap().to_owned();
        let (source, body) = seed(&db);
        let route = format!("/api/v1/sources/{source}/anchors");
        let (status, anchor) = call(&db, "POST", &route, body.clone()).await;
        assert_eq!(status, StatusCode::CREATED, "{anchor}");
        let historical = call(&db, "GET", &route, Value::Null).await.1;
        let conn = init_workspace(&db).unwrap();
        if tamper == "request" {
            let wire: String = conn
                .query_row(
                    "SELECT request_json FROM job_attempts WHERE job_id='pdf-job'",
                    [],
                    |r| r.get(0),
                )
                .unwrap();
            let mut request: Value = serde_json::from_str(&wire).unwrap();
            request["capability"] = json!("text.extract");
            conn.execute(
                "UPDATE job_attempts SET request_json=?1 WHERE job_id='pdf-job'",
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
