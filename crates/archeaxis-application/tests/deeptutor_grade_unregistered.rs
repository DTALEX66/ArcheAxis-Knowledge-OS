//! Integration tests compile the application as a production dependency, without cfg(test).
use archeaxis_application::executor::{
    Cancellation, Executor, PracticeGradeWorkerError, PracticeImportCancellation,
};
use std::time::Duration;

#[tokio::test]
async fn deeptutor_grade_declaration_is_not_registered_in_production() {
    let dir = tempfile::tempdir().unwrap();
    let worker = dir.path().join("grade_worker.py");
    std::fs::write(&worker, b"synthetic untrusted route").unwrap();
    let executor = Executor::open_routes(
        &dir.path().join("db"),
        &dir.path().join("staging"),
        &dir.path().join("unused-python"),
        &dir.path().join("unused-default"),
        &[("deeptutor.practice.grade", worker)],
    )
    .await
    .unwrap();
    let routes = executor.registered_routes();
    assert!(routes.iter().any(|(name, _, _)| *name == "text.extract"));
    assert!(
        !routes
            .iter()
            .any(|(name, _, _)| *name == "deeptutor.practice.grade")
    );
    assert_eq!(
        executor
            .store()
            .submit_wait(|conn| conn.query_row("SELECT 1", [], |row| row.get::<_, i64>(0)))
            .await
            .unwrap()
            .unwrap(),
        1
    );
}

#[tokio::test]
async fn private_grade_runner_refuses_before_any_process_without_its_fixed_worker() {
    let dir = tempfile::tempdir().unwrap();
    // No practice import worker was declared, so no adjacent fixed grader can be
    // selected; grading is unavailable before any process or database write.
    let executor = Executor::open(
        &dir.path().join("db"),
        &dir.path().join("staging"),
        &dir.path().join("unused-python"),
        &dir.path().join("unused-worker"),
    )
    .await
    .unwrap();
    assert_eq!(
        executor
            .run_deeptutor_practice_grade(
                b"{}\n".to_vec(),
                Duration::from_secs(1),
                Cancellation::new()
            )
            .await
            .unwrap_err(),
        PracticeGradeWorkerError::Unavailable
    );

    // Once a private practice worker is declared, the adjacent grader is the
    // only candidate and it is pinned by name, size and SHA.
    let workers = dir.path().join("workers");
    std::fs::create_dir(&workers).unwrap();
    let practice = workers.join("practice_host_worker.py");
    std::fs::write(&practice, b"synthetic untrusted route").unwrap();
    let executor = Executor::open_routes(
        &dir.path().join("db2"),
        &dir.path().join("staging2"),
        &dir.path().join("unused-python"),
        &dir.path().join("unused-default"),
        &[("deeptutor.practice.import", practice)],
    )
    .await
    .unwrap();
    assert!(
        executor
            .registered_routes()
            .iter()
            .all(|(name, _, _)| *name != "deeptutor.practice.import"),
        "the private answer-bearing protocols are not generic job routes"
    );
    assert_eq!(
        executor
            .run_deeptutor_practice_grade(
                b"{}\n".to_vec(),
                Duration::from_secs(1),
                Cancellation::new()
            )
            .await
            .unwrap_err(),
        PracticeGradeWorkerError::IdentityMismatch
    );
}

#[tokio::test]
async fn private_grade_runner_rejects_unbounded_or_multiline_input_before_a_process() {
    let dir = tempfile::tempdir().unwrap();
    let executor = Executor::open(
        &dir.path().join("db"),
        &dir.path().join("staging"),
        &dir.path().join("unused-python"),
        &dir.path().join("unused-worker"),
    )
    .await
    .unwrap();
    for bad in [
        Vec::new(),
        b"two\nlines\n".to_vec(),
        b"no trailing newline".to_vec(),
        vec![b'x'; 240_001],
    ] {
        assert_eq!(
            executor
                .run_deeptutor_practice_grade(bad, Duration::from_secs(1), Cancellation::new())
                .await
                .unwrap_err(),
            PracticeGradeWorkerError::InvalidInput
        );
    }
    let cancelled = Cancellation::new();
    cancelled.cancel();
    assert_eq!(
        executor
            .run_deeptutor_practice_grade(b"{}\n".to_vec(), Duration::from_secs(1), cancelled)
            .await
            .unwrap_err(),
        PracticeGradeWorkerError::Cancelled
    );
    // The private import protocol still requires its own explicit worker.
    assert_eq!(
        executor
            .run_deeptutor_practice_import(
                b"{}\n".to_vec(),
                Duration::from_secs(1),
                PracticeImportCancellation::new()
            )
            .await
            .unwrap_err(),
        archeaxis_application::executor::PracticeImportWorkerError::Unavailable
    );
}
