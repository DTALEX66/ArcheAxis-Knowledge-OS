//! R15/F07-F09/F12: a worker's semantic path becomes an addressable, verifiable anchor.
//!
//! Routes already reported their own structure - which paragraph, which heading, which sheet row -
//! but only as a fact inside the loss receipt, while the addressable level stayed the canonical
//! line anchor. That distinction is what several format rows called "a reported fact rather than an
//! addressing level". These tests pin the new state: a locator naming that path is accepted only
//! when the same attempt is the latest succeeded one for this source revision, the receipt names the
//! path exactly once, and the text at the recorded span hashes to the checksum being claimed. A
//! location the receipt cannot name unambiguously, an older attempt, a blank span and a mismatched
//! digest are all refused.

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use tower::ServiceExt;

use archeaxis_api::app;
use archeaxis_domain::source::{self, ImportOutcome};
use archeaxis_store_sqlite::init_workspace;

const TEXT: &str = "# Heading the first\n\nBody paragraph 6371\n\n星环 知识平台\n";
const HEADING: (usize, usize) = (0, 19);
const PARAGRAPH: (usize, usize) = (21, 40);
const BLANK: (usize, usize) = (19, 21);
// counted in characters, the way a Python worker counts them
const CJK: (usize, usize) = (42, 49);

/** A worker's span counted in characters, which is what `char_start`/`char_end` mean. */
fn span(text: &str, chars: (usize, usize)) -> String {
    text.chars().skip(chars.0).take(chars.1 - chars.0).collect()
}

fn digest(text: &str) -> String {
    format!("{:x}", Sha256::digest(text.as_bytes()))
}

/// Seed one source with a succeeded office attempt whose receipt describes two paragraphs,
/// one of them named twice on purpose.
fn seed(db: &str) -> (String, String, String) {
    let mut conn = init_workspace(db).unwrap();
    let bytes = b"PK\x03\x04 simulated docx package";
    let source_id = match source::import_source(&mut conn, bytes, "report.docx", None).unwrap() {
        ImportOutcome::Imported { source_id, .. } | ImportOutcome::Duplicate { source_id, .. } => {
            source_id
        }
    };
    let revision = format!("{:x}", Sha256::digest(bytes));
    archeaxis_application::jobs::enqueue(&mut conn, "office-job", "office", &source_id).unwrap();

    let mut structure = Vec::new();
    for (kind, path, span) in [
        ("heading", json!(["document-1", "heading-1"]), HEADING),
        ("paragraph", json!(["document-1", "paragraph-1"]), PARAGRAPH),
        // one entry per format family whose worker already reports a semantic path, so the
        // mechanism is proven once for every family rather than once per format
        ("sheet_row", json!(["sheet-Finance", "row-3"]), PARAGRAPH),
        ("slide", json!(["slide-2"]), PARAGRAPH),
        ("text_node", json!(["n1"]), PARAGRAPH),
        ("cue", json!(["cue-4"]), PARAGRAPH),
        ("pdf_page", json!(["page-2"]), PARAGRAPH),
        ("paragraph", json!(["document-1", "cjk"]), CJK),
        ("paragraph", json!(["document-1", "ambiguous"]), PARAGRAPH),
        ("paragraph", json!(["document-1", "ambiguous"]), PARAGRAPH),
        ("paragraph", json!(["document-1", "blank"]), BLANK),
    ] {
        structure.push(json!({
            "kind": kind, "path": path,
            "char_start": span.0, "char_end": span.1,
        }));
    }
    let loss = json!({
        "engine": "python-worker-office",
        "params": {"worker_structure": structure},
        "losses": ["structure reported by the worker"],
    })
    .to_string();
    let lines = json!([
        {"kind": "line", "path": ["line-1"], "char_start": 0, "char_end": 20},
        {"kind": "line", "path": ["line-2"], "char_start": 20, "char_end": 21},
        {"kind": "line", "path": ["line-3"], "char_start": 21, "char_end": 41},
        {"kind": "line", "path": ["line-4"], "char_start": 41, "char_end": 42},
        {"kind": "line", "path": ["line-5"], "char_start": 42, "char_end": 50},
    ])
    .to_string();
    let request = json!({
        "job_id": "office-job", "attempt": 1, "capability": "office.structure",
        "inputs": [{"sha256": revision, "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}],
    })
    .to_string();
    conn.execute(
        "INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('office-job',1,'office-request',?1,'succeeded')",
        [&request],
    )
    .unwrap();
    conn.execute(
        "UPDATE jobs SET state='succeeded' WHERE job_id='office-job'",
        [],
    )
    .unwrap();
    for (kind, content) in [
        ("loss_report", loss.clone()),
        ("document_structure", lines.clone()),
        ("text", TEXT.to_string()),
    ] {
        let metadata =
            json!({"kind": kind, "sha256": digest(&content), "byte_length": content.len()})
                .to_string();
        conn.execute(
            "INSERT INTO job_outputs(job_id,attempt,kind,metadata_json,content) VALUES('office-job',1,?1,?2,?3)",
            rusqlite::params![kind, metadata, content],
        )
        .unwrap();
    }
    (source_id, revision, loss)
}

async fn post(db: &str, source_id: &str, body: Value) -> (StatusCode, Value) {
    let response = app(db)
        .unwrap()
        .oneshot(
            Request::post(format!("/api/v1/sources/{source_id}/anchors"))
                .header("x-archeaxis-actor", "human")
                .header("content-type", "application/json")
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

fn locator(path: &Value, kind: &str, attempt: u64, checksum: &str, revision: &str) -> Value {
    json!({
        "revision": revision,
        "checksum": checksum,
        "position": json!({
            "type": "worker_structure", "job_id": "office-job", "attempt": attempt,
            "kind": kind, "path": path,
        })
        .to_string(),
    })
}

#[tokio::test]
async fn a_paragraph_named_by_the_worker_becomes_an_addressable_anchor() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir
        .path()
        .join("anchors.sqlite")
        .to_str()
        .unwrap()
        .to_string();
    let (source_id, revision, _loss) = seed(&db);

    let excerpt = span(TEXT, PARAGRAPH);
    let (status, body) = post(
        &db,
        &source_id,
        locator(
            &json!(["document-1", "paragraph-1"]),
            "paragraph",
            1,
            &digest(&excerpt),
            &revision,
        ),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "{body}");
    assert_eq!(body["location_status"], "located", "{body}");
    let position: Value = serde_json::from_str(body["position"].as_str().unwrap()).unwrap();
    assert_eq!(position["path"], json!(["document-1", "paragraph-1"]));
    assert_eq!(position["kind"], "paragraph");
    assert_eq!(position["type"], "worker_structure");

    // and the heading is addressable as its own location, not as a line number
    let (status, body) = post(
        &db,
        &source_id,
        locator(
            &json!(["document-1", "heading-1"]),
            "heading",
            1,
            &digest(&span(TEXT, HEADING)),
            &revision,
        ),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "{body}");
    assert_eq!(
        serde_json::from_str::<Value>(body["position"].as_str().unwrap()).unwrap()["kind"],
        "heading"
    );
}

#[tokio::test]
async fn every_semantic_location_a_worker_names_is_addressable_the_same_way() {
    // The point of one mechanism rather than per-format navigation: a sheet row, a slide, a
    // canvas node, a subtitle cue and a PDF page are all located by the same verified shape.
    let dir = tempfile::tempdir().unwrap();
    let db = dir
        .path()
        .join("families.sqlite")
        .to_str()
        .unwrap()
        .to_string();
    let (source_id, revision, _loss) = seed(&db);
    let excerpt = span(TEXT, PARAGRAPH);
    for (kind, path) in [
        ("sheet_row", json!(["sheet-Finance", "row-3"])),
        ("slide", json!(["slide-2"])),
        ("text_node", json!(["n1"])),
        ("cue", json!(["cue-4"])),
        ("pdf_page", json!(["page-2"])),
    ] {
        let (status, body) = post(
            &db,
            &source_id,
            locator(&path, kind, 1, &digest(&excerpt), &revision),
        )
        .await;
        assert_eq!(status, StatusCode::CREATED, "{kind} {path}: {body}");
        assert_eq!(body["location_status"], "located", "{kind} {path}");
    }
}

#[tokio::test]
async fn a_location_in_a_non_latin_projection_is_addressable_too() {
    // The receipt's offsets count characters, the way the worker's own language does. Verifying
    // them as byte offsets would refuse a Chinese paragraph with "not a codepoint boundary" and
    // the refusal would look like a content problem rather than a unit-of-measure bug.
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("cjk.sqlite").to_str().unwrap().to_string();
    let (source_id, revision, _loss) = seed(&db);
    let excerpt = span(TEXT, CJK);
    assert_eq!(excerpt, "星环 知识平台");
    assert_ne!(
        excerpt.len(),
        CJK.1 - CJK.0,
        "the span is characters, not bytes"
    );

    let (status, body) = post(
        &db,
        &source_id,
        locator(
            &json!(["document-1", "cjk"]),
            "paragraph",
            1,
            &digest(&excerpt),
            &revision,
        ),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "{body}");
    assert_eq!(body["location_status"], "located", "{body}");

    // the same path with the digest of the byte slice is refused, so the unit is not negotiable
    let as_bytes = TEXT.as_bytes()[CJK.0..CJK.0 + (CJK.1 - CJK.0)]
        .to_vec()
        .iter()
        .map(|b| *b as char)
        .collect::<String>();
    let (status, _body) = post(
        &db,
        &source_id,
        locator(
            &json!(["document-1", "cjk"]),
            "paragraph",
            1,
            &digest(&as_bytes),
            &revision,
        ),
    )
    .await;
    assert_eq!(
        status,
        StatusCode::BAD_REQUEST,
        "a byte-offset digest must not pass"
    );
}

#[tokio::test]
async fn an_ambiguous_or_blank_location_is_refused_rather_than_guessed() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir
        .path()
        .join("refuse.sqlite")
        .to_str()
        .unwrap()
        .to_string();
    let (source_id, revision, _loss) = seed(&db);

    // the receipt names this path twice, so no single location can be taken from it
    let (status, body) = post(
        &db,
        &source_id,
        locator(
            &json!(["document-1", "ambiguous"]),
            "paragraph",
            1,
            &digest(&span(TEXT, PARAGRAPH)),
            &revision,
        ),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST, "{body}");

    // a span that addresses only line breaks is not a location worth claiming
    let (status, body) = post(
        &db,
        &source_id,
        locator(
            &json!(["document-1", "blank"]),
            "paragraph",
            1,
            &digest(&span(TEXT, BLANK)),
            &revision,
        ),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST, "{body}");

    // a path the receipt never named
    let (status, body) = post(
        &db,
        &source_id,
        locator(
            &json!(["document-1", "paragraph-99"]),
            "paragraph",
            1,
            &digest(&span(TEXT, PARAGRAPH)),
            &revision,
        ),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST, "{body}");

    // the right location with the wrong digest
    let (status, body) = post(
        &db,
        &source_id,
        locator(
            &json!(["document-1", "paragraph-1"]),
            "paragraph",
            1,
            &digest("a quote that was never in the projection"),
            &revision,
        ),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST, "{body}");
}

#[tokio::test]
async fn a_superseded_attempt_stops_addressing_the_document_it_described() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir
        .path()
        .join("stale.sqlite")
        .to_str()
        .unwrap()
        .to_string();
    let (source_id, revision, _loss) = seed(&db);
    let locator_body = locator(
        &json!(["document-1", "paragraph-1"]),
        "paragraph",
        1,
        &digest(&span(TEXT, PARAGRAPH)),
        &revision,
    );
    let (status, body) = post(&db, &source_id, locator_body.clone()).await;
    assert_eq!(status, StatusCode::CREATED, "{body}");

    // a newer succeeded attempt means the receipt no longer describes the latest reading
    let conn = rusqlite::Connection::open(&db).unwrap();
    conn.execute(
        "INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('office-job',2,'newer-request','{}','succeeded')",
        [],
    )
    .unwrap();
    let (status, body) = post(&db, &source_id, locator_body).await;
    assert_eq!(status, StatusCode::BAD_REQUEST, "{body}");
}

#[tokio::test]
async fn an_anchor_without_a_checksum_is_still_stored_and_says_it_is_unverified() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir
        .path()
        .join("unverified.sqlite")
        .to_str()
        .unwrap()
        .to_string();
    let (source_id, revision, _loss) = seed(&db);
    let (status, body) = post(
        &db,
        &source_id,
        json!({
            "revision": revision,
            "position": json!({
                "type": "worker_structure", "job_id": "office-job", "attempt": 1,
                "kind": "paragraph", "path": ["document-1", "paragraph-1"],
            })
            .to_string(),
        }),
    )
    .await;
    // the checksum is what makes a location verified; without it the anchor is kept and states so
    assert_eq!(status, StatusCode::CREATED, "{body}");
    assert_eq!(body["location_status"], "unverified", "{body}");
    assert!(body["checksum"].is_null(), "{body}");
}
