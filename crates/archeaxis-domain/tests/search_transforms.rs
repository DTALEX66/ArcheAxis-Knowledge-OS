//! R08: text produced by the conversion routes is retrievable, attributed to its
//! original file and to the engine that produced it - without turning extracted
//! text into knowledge.

use archeaxis_domain::search;
use archeaxis_domain::source::{self, ImportOutcome};
use archeaxis_store_sqlite::init_workspace;

fn workspace() -> (tempfile::TempDir, rusqlite::Connection) {
    let dir = tempfile::tempdir().unwrap();
    let conn = init_workspace(dir.path().join("s.sqlite").to_str().unwrap()).unwrap();
    (dir, conn)
}

#[test]
fn extracted_text_is_retrievable_with_source_and_engine_attribution() {
    let (_dir, mut conn) = workspace();
    let source_id = match source::import_source(&mut conn, b"%PDF-1.4 payload", "report.pdf", None).unwrap() {
        ImportOutcome::Imported { source_id, .. } => source_id,
        ImportOutcome::Duplicate { source_id, .. } => source_id,
    };
    source::record_transform(
        &mut conn,
        &source_id,
        "pymupdf-native-pdf",
        "the extracted radius is 6371 km",
        Some("no transform applied"),
    )
    .unwrap();

    let hits = search::search_transforms(&conn, "6371", 10).unwrap();
    assert_eq!(hits.len(), 1, "extracted text must be findable: {hits:?}");
    let (transform_id, hit_source, engine, head) = &hits[0];
    assert!(*transform_id > 0);
    assert_eq!(hit_source, &source_id, "the hit must name its original file");
    assert_eq!(engine, "pymupdf-native-pdf", "the hit must name the engine that produced it");
    assert!(head.contains("6371"), "{head}");

    // A term that is not in any extracted text returns nothing, and searching the
    // knowledge index must not start reporting extracted text as knowledge.
    assert!(search::search_transforms(&conn, "absentterm", 10).unwrap().is_empty());
    assert!(search::search(&conn, "6371", 10).unwrap().is_empty());
}
