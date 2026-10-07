//! R15/F01/F13: a location reported in `params.format.locations` becomes an addressable anchor.
//!
//! Those families - JSON and XML paths, mail parts and headers, ODF headings, cells and pages, RTF
//! paragraphs, Python symbols - describe positions with a value rather than a span, so the check is
//! on the value: the receipt must name it once, and it must be text this attempt really projected.
//! Several entries legitimately share one path (every import in a source is `/symbols/import`), so
//! the locator may narrow the match with the fields the receipt already reported - and if it does
//! not, the ambiguity is refused instead of resolved by picking one.

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

const TEXT: &str =
    "结论\n半径 6371 千米\ndef load():\n    import os\n    import json\nname,radius,note\nEarth,6371,round\n";

fn digest(value: &str) -> String {
    format!("{:x}", Sha256::digest(value.as_bytes()))
}

fn locations() -> Vec<Value> {
    vec![
        json!({"kind": "odf_heading", "path": "/text:h/1", "level": 1, "value": "结论"}),
        json!({"kind": "odf_paragraph", "path": "/text:p/1", "value": "半径 6371 千米"}),
        json!({"kind": "python_symbol", "symbol_kind": "function", "name": "load", "line": 3,
               "path": "/symbols/load", "value": "def load():"}),
        json!({"kind": "python_symbol", "symbol_kind": "import", "name": "os", "line": 4,
               "path": "/symbols/import", "value": "import os"}),
        json!({"kind": "python_symbol", "symbol_kind": "import", "name": "json", "line": 5,
               "path": "/symbols/import", "value": "import json"}),
        // F01: one delimited row carries three cells, so a row-level anchor named more than the
        // evidence a single value supports. Each cell is reported by its own coordinate.
        json!({"kind": "table_cell", "path": "csv!B2", "value": "6371", "coordinate": "B2",
               "row": 2, "column": 2, "column_name": "radius", "in_projection": true}),
        json!({"kind": "table_cell", "path": "csv!C2", "value": "round", "coordinate": "C2",
               "row": 2, "column": 3, "column_name": "note", "in_projection": true}),
        // a location whose value is not in the projection at all: the receipt drifted
        json!({"kind": "xml_path", "path": "/root/radius", "value": "6371 km, unprojected"}),
    ]
}

fn seed(db: &str) -> (String, String) {
    let mut conn = init_workspace(db).unwrap();
    let bytes = b"PK\x03\x04 simulated odt package";
    let source_id = match source::import_source(&mut conn, bytes, "note.odt", None).unwrap() {
        ImportOutcome::Imported { source_id, .. } | ImportOutcome::Duplicate { source_id, .. } => {
            source_id
        }
    };
    let revision = format!("{:x}", Sha256::digest(bytes));
    archeaxis_application::jobs::enqueue(&mut conn, "text-job", "text", &source_id).unwrap();
    let loss = json!({
        "engine": "python-worker-text",
        "params": {"format": {"format": "odf", "parsed": true, "locations": locations()}},
        "losses": ["locations are capped by the worker"],
    })
    .to_string();
    let request = json!({
        "job_id": "text-job", "attempt": 1, "capability": "text.extract",
        "inputs": [{"sha256": revision, "media_type": "application/vnd.oasis.opendocument.text"}],
    })
    .to_string();
    conn.execute(
        "INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('text-job',1,'text-request',?1,'succeeded')",
        [&request],
    )
    .unwrap();
    conn.execute(
        "UPDATE jobs SET state='succeeded' WHERE job_id='text-job'",
        [],
    )
    .unwrap();
    for (kind, content) in [("loss_report", loss.clone()), ("text", TEXT.to_string())] {
        let metadata =
            json!({"kind": kind, "sha256": digest(&content), "byte_length": content.len()})
                .to_string();
        conn.execute(
            "INSERT INTO job_outputs(job_id,attempt,kind,metadata_json,content) VALUES('text-job',1,?1,?2,?3)",
            rusqlite::params![kind, metadata, content],
        )
        .unwrap();
    }
    (source_id, revision)
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

fn body(revision: &str, position: Value, checksum: &str) -> Value {
    json!({"revision": revision, "position": position.to_string(), "checksum": checksum})
}

#[tokio::test]
async fn a_heading_or_paragraph_named_by_the_receipt_is_addressable() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir
        .path()
        .join("locations.sqlite")
        .to_str()
        .unwrap()
        .to_string();
    let (source_id, revision) = seed(&db);

    for (kind, path, value) in [
        ("odf_heading", "/text:h/1", "结论"),
        ("odf_paragraph", "/text:p/1", "半径 6371 千米"),
        ("python_symbol", "/symbols/load", "def load():"),
        ("table_cell", "csv!B2", "6371"),
        ("table_cell", "csv!C2", "round"),
    ] {
        let (status, payload) = post(
            &db,
            &source_id,
            body(
                &revision,
                json!({"type": "format_location", "job_id": "text-job", "attempt": 1,
                       "kind": kind, "path": path}),
                &digest(value),
            ),
        )
        .await;
        assert_eq!(status, StatusCode::CREATED, "{kind} {path}: {payload}");
        assert_eq!(payload["location_status"], "located", "{payload}");
    }
}

#[tokio::test]
async fn a_delimited_cell_can_be_narrowed_by_the_column_the_header_named() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("columns.sqlite").to_str().unwrap().to_string();
    let (source_id, revision) = seed(&db);

    let (status, payload) = post(
        &db,
        &source_id,
        body(
            &revision,
            json!({"type": "format_location", "job_id": "text-job", "attempt": 1,
                   "kind": "table_cell", "path": "csv!B2",
                   "where": {"column_name": "radius"}}),
            &digest("6371"),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "{payload}");

    // the same coordinate under a column name the receipt does not carry is refused, even though
    // the digest itself would fit - narrowing must select, not invent
    let (status, _payload) = post(
        &db,
        &source_id,
        body(
            &revision,
            json!({"type": "format_location", "job_id": "text-job", "attempt": 1,
                   "kind": "table_cell", "path": "csv!B2",
                   "where": {"column_name": "note"}}),
            &digest("6371"),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn an_ambiguous_path_is_refused_until_the_reported_fields_narrow_it() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir
        .path()
        .join("ambiguous.sqlite")
        .to_str()
        .unwrap()
        .to_string();
    let (source_id, revision) = seed(&db);

    // both imports share one path, so the path alone names nothing
    let (status, payload) = post(
        &db,
        &source_id,
        body(
            &revision,
            json!({"type": "format_location", "job_id": "text-job", "attempt": 1,
                   "kind": "python_symbol", "path": "/symbols/import"}),
            &digest("import json"),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST, "{payload}");

    // narrowing with fields the receipt already reported resolves it, and to the right one
    let (status, payload) = post(
        &db,
        &source_id,
        body(
            &revision,
            json!({"type": "format_location", "job_id": "text-job", "attempt": 1,
                   "kind": "python_symbol", "path": "/symbols/import",
                   "where": {"name": "json"}}),
            &digest("import json"),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "{payload}");

    // a name the receipt does not carry stays refused, including when the digest would fit
    let (status, _payload) = post(
        &db,
        &source_id,
        body(
            &revision,
            json!({"type": "format_location", "job_id": "text-job", "attempt": 1,
                   "kind": "python_symbol", "path": "/symbols/import",
                   "where": {"name": "sys"}}),
            &digest("import os"),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn a_location_whose_value_the_projection_does_not_contain_is_refused() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir
        .path()
        .join("drift.sqlite")
        .to_str()
        .unwrap()
        .to_string();
    let (source_id, revision) = seed(&db);
    let value = "6371 km, unprojected";
    let (status, payload) = post(
        &db,
        &source_id,
        body(
            &revision,
            json!({"type": "format_location", "job_id": "text-job", "attempt": 1,
                   "kind": "xml_path", "path": "/root/radius"}),
            &digest(value),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST, "{payload}");
}

#[tokio::test]
async fn a_wrong_digest_or_a_superseded_attempt_stops_the_locator() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir
        .path()
        .join("staleloc.sqlite")
        .to_str()
        .unwrap()
        .to_string();
    let (source_id, revision) = seed(&db);
    let position = json!({"type": "format_location", "job_id": "text-job", "attempt": 1,
                          "kind": "odf_heading", "path": "/text:h/1"});

    let (status, _payload) = post(
        &db,
        &source_id,
        body(
            &revision,
            position.clone(),
            &digest("a heading from somewhere else"),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);

    let (status, payload) = post(
        &db,
        &source_id,
        body(&revision, position.clone(), &digest("结论")),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "{payload}");

    let conn = init_workspace(&db).unwrap();
    conn.execute(
        "INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('text-job',2,'newer','{}','succeeded')",
        [],
    )
    .unwrap();
    let (status, _payload) =
        post(&db, &source_id, body(&revision, position, &digest("结论"))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST, "a newer attempt wins");
}
