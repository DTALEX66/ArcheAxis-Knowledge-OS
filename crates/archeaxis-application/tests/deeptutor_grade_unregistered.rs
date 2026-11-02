//! Integration tests compile the application as a production dependency, without cfg(test).
use archeaxis_application::executor::Executor;

#[tokio::test]
async fn deeptutor_grade_declaration_is_not_registered_in_production() {
    let dir = tempfile::tempdir().unwrap();
    let worker = dir.path().join("grade_worker.py");
    std::fs::write(&worker, b"synthetic untrusted route").unwrap();
    let executor = Executor::open_routes(&dir.path().join("db"), &dir.path().join("staging"),
        &dir.path().join("unused-python"), &dir.path().join("unused-default"),
        &[("deeptutor.practice.grade", worker)]).await.unwrap();
    let routes = executor.registered_routes();
    assert!(routes.iter().any(|(name, _, _)| *name == "text.extract"));
    assert!(!routes.iter().any(|(name, _, _)| *name == "deeptutor.practice.grade"));
    assert_eq!(executor.store().submit_wait(|conn| conn.query_row("SELECT 1", [], |row| row.get::<_, i64>(0)))
        .await.unwrap().unwrap(), 1);
}
