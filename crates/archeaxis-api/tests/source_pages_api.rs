//! R15/F06: the page-to-PDF relation and each page's own recognised text are visible via the API.
//!
//! A scanned PDF chains its rendered pages into the OCR route; what makes the chain worth
//! having is that the PDF can afterwards be asked what its pages say. The pipeline that
//! produces the relation is exercised end to end in the application crate's `pdf_ocr_chain`
//! suite; this surface test pins what the endpoint reports, including a page nobody has read.

use archeaxis_api::app;
use archeaxis_domain::source::{self, ImportOutcome, OriginInfo};
use archeaxis_store_sqlite::init_workspace;
use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

async fn get(router: &axum::Router, path: &str) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(Request::builder().uri(path).body(Body::empty()).unwrap())
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

fn page_of(conn: &mut rusqlite::Connection, pdf: &str, page: u32, body: &[u8]) -> String {
    let name = format!("scan-page-{page}.png");
    let outcome = source::import_source_with_origin(
        conn,
        body,
        &name,
        None,
        Some(OriginInfo {
            kind: "import",
            origin_ref: &format!("{pdf}#page-{page}"),
            original_name: Some(&name),
            received_at: None,
        }),
    )
    .unwrap();
    match outcome {
        ImportOutcome::Imported { source_id, .. } => source_id,
        ImportOutcome::Duplicate { source_id, .. } => source_id,
    }
}

#[tokio::test]
async fn a_pdfs_pages_are_listed_with_the_text_read_from_each() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("api.sqlite");
    let pdf_id = {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        let imported =
            source::import_source(&mut conn, b"%PDF-1.4 scanned".as_slice(), "scan.pdf", None)
                .unwrap();
        let pdf_id = match imported {
            ImportOutcome::Imported { source_id, .. } => source_id,
            ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        page_of(&mut conn, &pdf_id, 1, b"page one bytes");
        let read = page_of(&mut conn, &pdf_id, 2, b"page two bytes");
        source::record_transform(
            &mut conn,
            &read,
            "python-worker-ocr",
            "scanned page 6371",
            Some("none"),
        )
        .unwrap();
        pdf_id
    };

    let router = app(db.to_str().unwrap()).unwrap();
    let (status, payload) = get(&router, &format!("/api/v1/sources/{pdf_id}/pages")).await;
    assert_eq!(status, StatusCode::OK, "{payload}");
    assert_eq!(payload["pdf_source_id"], pdf_id);
    assert_eq!(payload["page_count"], 2);
    assert_eq!(payload["recognised_count"], 1);

    let pages = payload["pages"].as_array().unwrap();
    let by_page: std::collections::BTreeMap<u64, &Value> = pages
        .iter()
        .map(|page| (page["page"].as_u64().unwrap(), page))
        .collect();
    assert_eq!(by_page[&1]["recognised"], false);
    assert_eq!(
        by_page[&1]["text"],
        Value::Null,
        "an unread page is reported without text rather than with an empty claim"
    );
    assert_eq!(by_page[&2]["recognised"], true);
    assert_eq!(by_page[&2]["text"], "scanned page 6371");
    assert_eq!(
        by_page[&2]["origin_ref"],
        format!("{pdf_id}#page-2"),
        "the page names the PDF it was rendered from"
    );
    assert_eq!(by_page[&1]["sha256"].as_str().unwrap().len(), 64);

    let note = payload["note"].as_str().unwrap();
    assert!(note.contains("chains nothing"), "{note}");
    assert!(note.contains("not that the reading is correct"), "{note}");
}

#[tokio::test]
async fn an_unknown_source_is_a_named_not_found_and_an_unrendered_pdf_has_no_pages() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("api.sqlite");
    let pdf_id = {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        match source::import_source(
            &mut conn,
            b"%PDF-1.4 has text".as_slice(),
            "typed.pdf",
            None,
        )
        .unwrap()
        {
            ImportOutcome::Imported { source_id, .. } => source_id,
            ImportOutcome::Duplicate { source_id, .. } => source_id,
        }
    };

    let router = app(db.to_str().unwrap()).unwrap();
    let (status, body) = get(&router, "/api/v1/sources/src_does_not_exist/pages").await;
    assert_eq!(status, StatusCode::NOT_FOUND, "{body}");

    let (status, payload) = get(&router, &format!("/api/v1/sources/{pdf_id}/pages")).await;
    assert_eq!(status, StatusCode::OK, "{payload}");
    assert_eq!(payload["page_count"], 0);
    assert_eq!(payload["recognised_count"], 0);
    assert!(payload["pages"].as_array().unwrap().is_empty());
}
