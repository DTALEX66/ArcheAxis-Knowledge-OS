//! X05 slice C: archive export/restore round-trips source provenance rows.

use archeaxis_archive::{export_workspace, restore_workspace};
use archeaxis_domain::source::{self, OriginInfo};
use archeaxis_store_sqlite::init_workspace;

#[test]
fn origin_rows_survive_export_and_restore() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("src.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let bytes = b"archive provenance bytes";
    let outcome = source::import_source_with_origin(
        &mut conn,
        bytes,
        "note.txt",
        None,
        Some(OriginInfo {
            kind: "url",
            origin_ref: "https://example.invalid/note.txt",
            original_name: Some("note.txt"),
            received_at: None, // must stay NULL through the round trip
        }),
    )
    .unwrap();
    let sid = match outcome {
        source::ImportOutcome::Imported { source_id, .. } => source_id,
        _ => panic!("first import must insert"),
    };
    // second distinct origin (path) on the same digest
    source::import_source_with_origin(
        &mut conn,
        bytes,
        "note.txt",
        None,
        Some(OriginInfo {
            kind: "path",
            origin_ref: r"D:\notes\note.txt",
            original_name: None,
            received_at: Some("2026-09-07T00:00:00Z"),
        }),
    )
    .unwrap();
    let before = source::list_origins(&conn, &sid).unwrap();
    assert_eq!(before.len(), 2);
    drop(conn);

    let archive = dir.path().join("archive");
    export_workspace(db.to_str().unwrap(), archive.to_str().unwrap()).unwrap();

    let target = dir.path().join("restored.sqlite");
    restore_workspace(archive.to_str().unwrap(), target.to_str().unwrap()).unwrap();

    let restored = rusqlite::Connection::open_with_flags(
        target,
        rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
    )
    .unwrap();
    let after = source::list_origins(&restored, &sid).unwrap();
    assert_eq!(after.len(), 2);
    let url = after.iter().find(|o| o.0 == "url").unwrap();
    assert_eq!(url.1, "https://example.invalid/note.txt");
    assert_eq!(url.3, None, "NULL received_at must survive restore");
    let path = after.iter().find(|o| o.0 == "path").unwrap();
    assert_eq!(path.3.as_deref(), Some("2026-09-07T00:00:00Z"));
}
