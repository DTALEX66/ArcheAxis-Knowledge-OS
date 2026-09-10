//! R08 option (A), second half: the Core compares anchors by kind and character
//! span and tolerates a page-qualified path, so a PDF/OCR receipt addresses the
//! same projected lines as the text route. It must not become lax: a wrong span
//! or a wrong final path segment is still refused.

use archeaxis_application::{attempts, bootstrap, jobs};
use archeaxis_domain::source::{self, ImportOutcome};
use archeaxis_sidecar_protocol::worker::{Output, Request, Response};
use serde_json::json;
use sha2::{Digest, Sha256};

const TEXT: &str = "alpha\n"; // one line, 6 Unicode scalars

fn setup() -> (tempfile::TempDir, rusqlite::Connection) {
    let dir = tempfile::tempdir().unwrap();
    let (mut conn, _) = bootstrap(dir.path().join("receipt.sqlite").to_str().unwrap()).unwrap();
    let sid = match source::import_source(&mut conn, TEXT.as_bytes(), "sample.pdf", None).unwrap() {
        ImportOutcome::Imported { source_id, .. } => source_id,
        ImportOutcome::Duplicate { source_id, .. } => source_id,
    };
    jobs::enqueue(&mut conn, "j", "pdf", &sid).unwrap();
    (dir, conn)
}

/// Build a succeeded response whose structure/loss report come from a PDF route.
fn pdf_style_output(req: &Request, path: serde_json::Value, engine: (&str, &str)) -> (Response, Vec<Vec<u8>>) {
    let payloads = vec![
        TEXT.as_bytes().to_vec(),
        serde_json::to_vec(&json!([{
            "kind": "line", "path": path, "char_start": 0, "char_end": 6
        }]))
        .unwrap(),
        serde_json::to_vec(&json!({
            "engine": engine.0, "engine_version": engine.1, "params": {},
            "loss_note": null, "losses": [], "covered": 1, "total": 1, "coverage": 1.0
        }))
        .unwrap(),
    ];
    let meta = [
        ("text", "archeaxis.text/v1", "text/plain; charset=utf-8"),
        ("document_structure", "archeaxis.document-structure/v1", "application/json"),
        ("loss_report", "archeaxis.loss-receipt/v1", "application/json"),
    ];
    let outputs = meta
        .into_iter()
        .zip(&payloads)
        .map(|((kind, schema, media), bytes)| {
            let sha = hex::encode(Sha256::digest(bytes));
            Output {
                kind: kind.into(),
                schema: schema.into(),
                media_type: media.into(),
                byte_length: bytes.len() as u64,
                uri: format!("job://output/{sha}"),
                sha256: sha,
                authority_effect: "candidate_or_measurement_only".into(),
            }
        })
        .collect();
    (
        Response {
            schema: "archeaxis.worker-response/v1".into(),
            message_type: "job_result".into(),
            request_id: req.request_id.clone(),
            job_id: req.job_id.clone(),
            attempt: req.attempt,
            protocol_minor: 0,
            status: "succeeded".into(),
            outputs,
            measurements: Default::default(),
            warnings: vec![],
            error: None,
        },
        payloads,
    )
}

#[test]
fn a_page_qualified_anchor_is_accepted_for_the_same_span() {
    let (_dir, mut conn) = setup();
    let req = attempts::claim(&mut conn, "j", "r", 5000).unwrap();
    assert_eq!(req.capability, "pdf.extract");
    let (response, bytes) =
        pdf_style_output(&req, json!(["page-1", "line-1"]), ("pymupdf-native-pdf", "pymupdf"));
    attempts::finish(&mut conn, &req, &response, &bytes).unwrap();
    assert_eq!(jobs::job_state(&conn, "j").unwrap().as_deref(), Some("succeeded"));
    let engine: String = conn
        .query_row("SELECT engine FROM jobs WHERE job_id='j'", [], |r| r.get(0))
        .unwrap();
    assert_eq!(engine, "pymupdf-native-pdf", "the route's real engine must be recorded");
    assert_eq!(conn.query_row("SELECT count(*) FROM job_outputs", [], |r| r.get::<_, i64>(0)).unwrap(), 3);
}

#[test]
fn a_wrong_final_path_segment_is_still_refused() {
    let (_dir, mut conn) = setup();
    let req = attempts::claim(&mut conn, "j", "r", 5000).unwrap();
    let (response, bytes) =
        pdf_style_output(&req, json!(["page-1", "line-9"]), ("pymupdf-native-pdf", "pymupdf"));
    assert!(
        attempts::finish(&mut conn, &req, &response, &bytes).is_err(),
        "tolerance must not accept an anchor that names a different line"
    );
}

#[test]
fn an_undeclared_engine_is_still_refused() {
    let (_dir, mut conn) = setup();
    let req = attempts::claim(&mut conn, "j", "r", 5000).unwrap();
    let (response, bytes) =
        pdf_style_output(&req, json!(["page-1", "line-1"]), ("totally-unknown-engine", "9.9"));
    assert!(
        attempts::finish(&mut conn, &req, &response, &bytes).is_err(),
        "only declared route engines may complete a job"
    );
}
