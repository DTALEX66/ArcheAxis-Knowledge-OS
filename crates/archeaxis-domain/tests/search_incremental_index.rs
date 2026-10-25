//! FTS5 is maintained by triggers, not rebuilt before every query.
//!
//! The query path used to call `reindex` on every search, which made search O(N) in the
//! library size. These assertions pin the incremental behaviour: rows written after the
//! triggers exist are searchable without a rebuild, and updates/deletes stay in step.

use archeaxis_domain::{knowledge, search, source};
use archeaxis_store_sqlite::init_workspace;

fn workspace() -> (tempfile::TempDir, rusqlite::Connection) {
    let dir = tempfile::tempdir().unwrap();
    let conn = init_workspace(dir.path().join("s.sqlite").to_str().unwrap()).unwrap();
    (dir, conn)
}

#[test]
fn knowledge_writes_are_searchable_without_a_query_time_rebuild() {
    let (_dir, mut conn) = workspace();

    // Insert before the index/triggers exist: the first search has to backfill once.
    let early = knowledge::create_knowledge(
        &mut conn,
        "PERSONAL_DEFINITION",
        "spatial memory palace",
        "accepted",
        None,
        None,
        "human",
    )
    .unwrap();
    let first = search::search(&conn, "palace", 10).unwrap();
    assert_eq!(
        first.len(),
        1,
        "the one-time backfill must find existing rows"
    );
    assert_eq!(&first[0].0, &early);

    // Insert after the triggers exist: this row must be visible without `reindex`.
    let later = knowledge::create_knowledge(
        &mut conn,
        "FACTUAL_CLAIM",
        "incremental trigger row",
        "accepted",
        None,
        None,
        "human",
    )
    .unwrap();
    let second = search::search(&conn, "incremental", 10).unwrap();
    assert_eq!(second.len(), 1, "the insert trigger must index the new row");
    assert_eq!(&second[0].0, &later);

    // A status update is reflected in the indexed row, not only in the table.
    knowledge::review(&mut conn, &later, "rejected", "human", Some("test"), None).unwrap();
    let updated = search::search(&conn, "incremental", 10).unwrap();
    assert_eq!(updated.len(), 1);
    assert_eq!(
        updated[0].1, "rejected",
        "the update trigger must refresh status"
    );

    // Deletion removes the row from the index as well.
    conn.execute("DELETE FROM knowledge WHERE knowledge_id=?1", [&later])
        .unwrap();
    assert!(
        search::search(&conn, "incremental", 10).unwrap().is_empty(),
        "the delete trigger must remove the indexed row"
    );
}

#[test]
fn transform_writes_are_searchable_without_a_query_time_rebuild() {
    let (_dir, mut conn) = workspace();
    let source_id =
        match source::import_source(&mut conn, b"%PDF-1.4 payload", "report.pdf", None).unwrap() {
            source::ImportOutcome::Imported { source_id, .. }
            | source::ImportOutcome::Duplicate { source_id, .. } => source_id,
        };

    source::record_transform(
        &mut conn,
        &source_id,
        "pymupdf-native-pdf",
        "the extracted radius is 6371 km",
        None,
    )
    .unwrap();
    let hits = search::search_transforms(&conn, "6371", 10).unwrap();
    assert_eq!(
        hits.len(),
        1,
        "the transform insert trigger must index the row"
    );

    let transform_id = hits[0].0;
    conn.execute(
        "DELETE FROM transforms WHERE transform_id=?1",
        [transform_id],
    )
    .unwrap();
    assert!(
        search::search_transforms(&conn, "6371", 10)
            .unwrap()
            .is_empty(),
        "the transform delete trigger must remove the indexed row"
    );
}
