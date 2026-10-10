use archeaxis_store_sqlite::{init_workspace, raw_objects};
#[test]
fn cas_bounded_read_rejects_invalid_hash_overbudget_tamper_and_alias() {
    let dir = tempfile::tempdir().unwrap();
    let conn = init_workspace(dir.path().join("cas.sqlite").to_str().unwrap()).unwrap();
    let hash = raw_objects::persist(&conn, b"exact original").unwrap();
    assert_eq!(
        raw_objects::read_bounded(&conn, &hash, 14).unwrap(),
        b"exact original"
    );
    assert!(raw_objects::read_bounded(&conn, &hash, 13).is_err());
    assert!(raw_objects::read_bounded(&conn, "../outside", 100).is_err());
    let path = raw_objects::root(&conn).unwrap().join(&hash);
    std::fs::write(&path, b"different data").unwrap();
    assert!(raw_objects::read_bounded(&conn, &hash, 100).is_err());
    std::fs::write(&path, b"exact original").unwrap();
    std::fs::hard_link(&path, dir.path().join("alias")).unwrap();
    assert!(raw_objects::read_bounded(&conn, &hash, 100).is_err());
}
