use archeaxis_domain::source::{self, ImportOutcome};
use archeaxis_store_sqlite::{init_workspace, raw_objects};

#[test]
fn original_bytes_survive_source_removal_restart_and_archive_restore() {
    let dir = tempfile::tempdir().unwrap();
    let external = dir.path().join("original.bin");
    let bytes = b"\x00\xffPDF image audio original\r\n";
    std::fs::write(&external, bytes).unwrap();
    let db = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let digest = match source::import_source(&mut conn, &std::fs::read(&external).unwrap(), "original.bin", None).unwrap() {
        ImportOutcome::Imported { sha256, .. } => sha256,
        _ => unreachable!(),
    };
    std::fs::remove_file(external).unwrap();
    drop(conn);
    let conn = init_workspace(db.to_str().unwrap()).unwrap();
    assert_eq!(raw_objects::read(&conn, &digest).unwrap(), bytes);
    drop(conn);
    let archive = dir.path().join("archive");
    archeaxis_archive::export_workspace(db.to_str().unwrap(), archive.to_str().unwrap()).unwrap();
    let target = dir.path().join("restored.sqlite");
    archeaxis_archive::restore_workspace(archive.to_str().unwrap(), target.to_str().unwrap()).unwrap();
    let mut restored = init_workspace(target.to_str().unwrap()).unwrap();
    assert_eq!(raw_objects::read(&restored, &digest).unwrap(), bytes);
    assert!(matches!(source::import_source(&mut restored, bytes, "again.bin", None).unwrap(), ImportOutcome::Duplicate { .. }));
    std::fs::write(archive.join("objects").join(&digest), b"corrupt").unwrap();
    let refused = dir.path().join("refused.sqlite");
    assert!(archeaxis_archive::restore_workspace(archive.to_str().unwrap(), refused.to_str().unwrap()).is_err());
    assert!(!refused.exists());
}
