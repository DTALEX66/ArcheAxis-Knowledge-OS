//! X05: source provenance - identical bytes from distinct origins must keep
//! every reported origin, and unknown received times stay NULL (never
//! fabricated by the store).

use archeaxis_domain::source::{self, OriginInfo};
use archeaxis_store_sqlite::init_workspace;

#[test]
fn identical_bytes_from_two_origins_keep_both_origins_on_one_source() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("s.sqlite").to_str().unwrap()).unwrap();
    let bytes = b"same content bytes";
    let first = source::import_source_with_origin(
        &mut conn,
        bytes,
        "from-disk.bin",
        None,
        Some(OriginInfo {
            kind: "path",
            origin_ref: r"C:\notes\from-disk.bin",
            original_name: Some("from-disk.bin"),
            received_at: Some("2026-09-07T00:00:00Z"),
        }),
    )
    .unwrap();
    let (sid, sha) = match &first {
        source::ImportOutcome::Imported { source_id, sha256 } => {
            (source_id.clone(), sha256.clone())
        }
        source::ImportOutcome::Duplicate { .. } => panic!("first import must insert"),
    };

    let second = source::import_source_with_origin(
        &mut conn,
        bytes,
        "from-url.txt",
        None,
        Some(OriginInfo {
            kind: "url",
            origin_ref: "https://example.invalid/notes.txt",
            original_name: Some("from-url.txt"),
            received_at: None, // genuinely unknown: must stay NULL, never faked
        }),
    )
    .unwrap();
    assert!(matches!(
        second,
        source::ImportOutcome::Duplicate { .. }
    ));

    // Exactly one content row for the identical bytes.
    assert_eq!(source::count_sources(&conn).unwrap(), 1);
    assert_eq!(
        conn.query_row::<String, _, _>(
            "SELECT source_id FROM sources WHERE sha256=?1",
            [&sha],
            |r| r.get(0),
        )
        .unwrap(),
        sid
    );

    let origins = source::list_origins(&conn, &sid).unwrap();
    assert_eq!(origins.len(), 2);

    let url = origins
        .iter()
        .find(|(kind, _, _, _)| kind == "url")
        .expect("url origin retained");
    assert_eq!(url.1, "https://example.invalid/notes.txt");
    assert_eq!(url.2.as_deref(), Some("from-url.txt"));
    // received_at was None: stored cell must be NULL, not a fabricated clock.
    assert_eq!(url.3, None);

    let path = origins
        .iter()
        .find(|(kind, _, _, _)| kind == "path")
        .expect("path origin retained");
    assert_eq!(path.3.as_deref(), Some("2026-09-07T00:00:00Z"));
}

#[test]
fn repeated_same_origin_is_idempotent() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("s.sqlite").to_str().unwrap()).unwrap();
    let mut sid = String::new();
    for _ in 0..2 {
        let outcome = source::import_source_with_origin(
            &mut conn,
            b"dup",
            "dup.txt",
            None,
            Some(OriginInfo {
                kind: "manual",
                origin_ref: "user-typed",
                original_name: None,
                received_at: None,
            }),
        )
        .unwrap();
        match outcome {
            source::ImportOutcome::Imported { source_id, .. } => sid = source_id,
            source::ImportOutcome::Duplicate { source_id, .. } => sid = source_id,
        }
    }
    assert_eq!(source::list_origins(&conn, &sid).unwrap().len(), 1);
}
