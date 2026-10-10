//! R15/F15: a container reaches the store through its own route.
//!
//! A ZIP is binary, so this test also pins the honesty of the routing: the Core
//! derives `application/zip` from the name, dispatches the archive capability to its
//! own worker, and the inventory listing lands in the store with line anchors. The
//! negative cases matter as much: a `.zip` offered to the text route is refused, and a
//! corrupt container fails the job instead of succeeding with an empty inventory.

use archeaxis_application::{
    attempts,
    executor::{Cancellation, Executor},
    jobs,
};
use archeaxis_domain::source::{self, ImportOutcome};
use std::path::PathBuf;

fn python() -> PathBuf {
    std::env::var_os("ARCHEAXIS_PYTHON")
        .expect("run cargo via the project wrapper")
        .into()
}

fn repo() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .unwrap()
}

/// Build a real ZIP through the same interpreter the worker uses.
fn zip_bytes() -> Vec<u8> {
    let script = "import io,sys,zipfile\n\
                  buf=io.BytesIO()\n\
                  with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as c:\n\
                  \x20   c.writestr('notes/index.md','# Index\\nThe value is 6371 km.\\n')\n\
                  \x20   c.writestr('assets/',b'')\n\
                  \x20   c.writestr('data.csv','name,qty\\nbolt,4\\n')\n\
                  sys.stdout.buffer.write(buf.getvalue())\n";
    match std::process::Command::new(python())
        .arg("-c")
        .arg(script)
        .output()
    {
        Ok(out) if out.status.success() => out.stdout,
        _ => Vec::new(),
    }
}

async fn open_executor(dir: &std::path::Path) -> Executor {
    Executor::open_routes(
        &dir.join("db.sqlite"),
        &dir.join("staging"),
        &python(),
        &repo().join("services/python-workers/transport/text_ndjson.py"),
        &[(
            "archive.inventory",
            repo().join("services/python-workers/document/worker_archive.py"),
        )],
    )
    .await
    .unwrap()
}

#[test]
fn a_zip_name_selects_the_archive_route_and_never_the_text_route() {
    assert_eq!(
        attempts::resolve_media_type("archive", "bundle.zip").unwrap(),
        "application/zip"
    );
    assert!(attempts::route_for_kind("archive").is_some());
    // a .zip cannot travel as text: no route may decode a container into text
    let error = attempts::resolve_media_type("text", "bundle.zip")
        .unwrap_err()
        .to_string();
    assert!(
        error.contains("cannot accept media type application/zip"),
        "{error}"
    );
    // and the archive route will not take something that is not a container
    let error = attempts::resolve_media_type("archive", "notes.md")
        .unwrap_err()
        .to_string();
    assert!(error.contains("application/zip"), "{error}");
}

#[tokio::test]
async fn a_zip_job_is_dispatched_to_the_archive_worker_and_its_inventory_is_stored() {
    let container = zip_bytes();
    if container.is_empty() {
        eprintln!("skipping: zipfile unavailable for building a sample");
        return;
    }
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let payload = container.clone();
    executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &payload, "bundle.zip", None).unwrap()
            {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-zip", "archive", &source_id).unwrap();
        })
        .await
        .unwrap();

    executor
        .execute("job-zip", "run-zip", 120_000, &Cancellation::new())
        .await
        .unwrap();

    let (state, text, receipt) = executor
        .store()
        .submit(|conn| {
            let state = jobs::job_state(conn, "job-zip").unwrap().unwrap_or_default();
            let text: String = conn
                .query_row(
                    "SELECT text FROM transforms WHERE source_id=(
                       SELECT input_ref FROM jobs WHERE job_id='job-zip') ORDER BY transform_id DESC LIMIT 1",
                    [],
                    |row| row.get(0),
                )
                .unwrap_or_default();
            let receipt: String = conn
                .query_row(
                    "SELECT content FROM job_outputs WHERE job_id='job-zip' AND kind='loss_report'",
                    [],
                    |row| row.get(0),
                )
                .unwrap_or_default();
            (state, text, receipt)
        })
        .await
        .unwrap();

    assert_eq!(state, "succeeded");
    assert!(
        text.contains("notes/index.md"),
        "the inventory must name the members: {text:?}"
    );
    assert!(text.contains("data.csv"), "{text:?}");
    // the projection is the inventory, so the members' contents are NOT in the store text
    assert!(
        !text.contains("6371"),
        "a container projection must not contain member contents: {text:?}"
    );
    assert!(receipt.contains("container inventory"), "{receipt}");
    assert!(receipt.contains("NOT the members' contents"), "{receipt}");
    // and the receipt carries the engine the route is allowed to report
    assert!(receipt.contains("python-worker-archive"), "{receipt}");
}

#[tokio::test]
async fn a_corrupt_container_fails_the_job_instead_of_succeeding_empty() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    executor
        .store()
        .submit(|conn| {
            let source_id = match source::import_source(
                conn,
                b"PK\x03\x04 not a container",
                "broken.zip",
                None,
            )
            .unwrap()
            {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-broken", "archive", &source_id).unwrap();
        })
        .await
        .unwrap();

    let outcome = executor
        .execute("job-broken", "run-broken", 60_000, &Cancellation::new())
        .await;
    let state = executor
        .store()
        .submit(|conn| {
            jobs::job_state(conn, "job-broken")
                .unwrap()
                .unwrap_or_default()
        })
        .await
        .unwrap();
    assert!(
        outcome.is_err(),
        "a corrupt container must not report success"
    );
    assert_eq!(state, "failed");
    let text_outputs: i64 = executor
        .store()
        .submit(|conn| {
            conn.query_row(
                "SELECT count(*) FROM job_outputs WHERE job_id='job-broken' AND kind='text'",
                [],
                |row| row.get(0),
            )
            .unwrap()
        })
        .await
        .unwrap();
    assert_eq!(
        text_outputs, 0,
        "no text artifact may exist for a container that failed"
    );
}

#[test]
fn uncompressed_tar_uses_the_same_bounded_archive_contract() {
    assert_eq!(
        attempts::resolve_media_type("archive", "bundle.tar").unwrap(),
        "application/x-tar"
    );
    assert!(attempts::resolve_media_type("text", "bundle.tar").is_err());
    assert!(attempts::resolve_media_type("archive", "bundle.tar.gz").is_err());
}

fn tar_bytes() -> Vec<u8> {
    let script = "import io,sys,tarfile\nb=io.BytesIO()\nwith tarfile.open(fileobj=b,mode='w') as t:\n p=b'TAR known member value 37\\n'; i=tarfile.TarInfo('notes/a.txt'); i.size=len(p); t.addfile(i,io.BytesIO(p))\nsys.stdout.buffer.write(b.getvalue())";
    let out = std::process::Command::new(python())
        .args(["-c", script])
        .output()
        .unwrap();
    assert!(
        out.status.success(),
        "TAR fixture creation must not silently skip"
    );
    assert!(!out.stdout.is_empty());
    out.stdout
}

#[tokio::test]
async fn tar_production_member_content_origin_anchor_loss_and_reopen_are_preserved() {
    use archeaxis_application::container;
    use archeaxis_domain::anchor;
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let payload = tar_bytes();
    let parent = executor
        .store()
        .submit(move |conn| {
            let parent = match source::import_source(conn, &payload, "bundle.tar", None).unwrap() {
                ImportOutcome::Imported { source_id, .. }
                | ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-tar", "archive", &parent).unwrap();
            parent
        })
        .await
        .unwrap();
    executor
        .execute("job-tar", "run-tar", 60_000, &Cancellation::new())
        .await
        .unwrap();
    let parent_query = parent.clone();
    let rows = executor
        .store()
        .submit(move |conn| container::members_of(conn, &parent_query).unwrap())
        .await
        .unwrap();
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0].member, "notes/a.txt");
    assert_eq!(rows[0].origin_ref, format!("{parent}#notes/a.txt"));
    let member_job = rows[0]
        .job_id
        .clone()
        .expect("production expansion queues text without manual expand");
    executor
        .execute(&member_job, "run-tar-member", 60_000, &Cancellation::new())
        .await
        .unwrap();
    let member_source = rows[0].source_id.clone();
    let snapshot = executor.store().submit(move |conn| {
        let text: String = conn.query_row("SELECT text FROM transforms WHERE source_id=?1", [&member_source], |r| r.get(0)).unwrap();
        assert_eq!(text, "TAR known member value 37\n");
        let revision: String = conn.query_row("SELECT sha256 FROM sources WHERE source_id=?1", [&member_source], |r| r.get(0)).unwrap();
        let reference: String = conn.query_row("SELECT origin_ref FROM source_origins WHERE source_id=?1 AND origin_kind='import'", [&member_source], |r| r.get(0)).unwrap();
        assert_eq!(reference, format!("{parent}#notes/a.txt"));
        let position = r#"{"type":"text","start":0,"end":24}"#;
        let anchor_id = anchor::add_anchor(conn, &member_source, &revision, position).unwrap();
        let locator = anchor::get_anchor(conn, &anchor_id).unwrap().unwrap();
        let loss: String = conn.query_row("SELECT content FROM job_outputs WHERE job_id='job-tar' AND kind='loss_report'", [], |r| r.get(0)).unwrap();
        let receipt: serde_json::Value = serde_json::from_str(&loss).unwrap();
        assert_eq!(receipt["params"]["structure"]["extractable_member_count"], 1);
        assert!(loss.contains("NOT the members' contents"));
        (text, reference, locator, loss, anchor_id, member_source)
    }).await.unwrap();
    drop(executor);
    let reopened = open_executor(dir.path()).await;
    let expected = snapshot.clone();
    reopened
        .store()
        .submit(move |conn| {
            let text: String = conn
                .query_row(
                    "SELECT text FROM transforms WHERE source_id=?1",
                    [&expected.5],
                    |r| r.get(0),
                )
                .unwrap();
            let reference: String = conn
                .query_row(
                    "SELECT origin_ref FROM source_origins WHERE source_id=?1",
                    [&expected.5],
                    |r| r.get(0),
                )
                .unwrap();
            let locator = anchor::get_anchor(conn, &expected.4).unwrap().unwrap();
            let loss: String = conn
                .query_row(
                    "SELECT content FROM job_outputs WHERE job_id='job-tar' AND kind='loss_report'",
                    [],
                    |r| r.get(0),
                )
                .unwrap();
            assert_eq!(
                (text, reference, locator, loss),
                (expected.0, expected.1, expected.2, expected.3)
            );
            assert_eq!(
                jobs::job_state(conn, "job-tar").unwrap().unwrap(),
                "succeeded"
            );
        })
        .await
        .unwrap();
}

#[tokio::test]
async fn malformed_tar_is_failed_with_no_publish_and_reopen_keeps_error_state() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    executor
        .store()
        .submit(|conn| {
            let source_id =
                match source::import_source(conn, b"not a TAR", "broken.tar", None).unwrap() {
                    ImportOutcome::Imported { source_id, .. }
                    | ImportOutcome::Duplicate { source_id, .. } => source_id,
                };
            jobs::enqueue(conn, "bad-tar", "archive", &source_id).unwrap();
        })
        .await
        .unwrap();
    assert!(
        executor
            .execute("bad-tar", "bad-tar-run", 60_000, &Cancellation::new())
            .await
            .is_err()
    );
    drop(executor);
    let reopened = open_executor(dir.path()).await;
    reopened
        .store()
        .submit(|conn| {
            assert_eq!(jobs::job_state(conn, "bad-tar").unwrap().unwrap(), "failed");
            let outputs: i64 = conn
                .query_row(
                    "SELECT count(*) FROM job_outputs WHERE job_id='bad-tar'",
                    [],
                    |r| r.get(0),
                )
                .unwrap();
            assert_eq!(outputs, 0);
        })
        .await
        .unwrap();
}

#[tokio::test]
async fn unicode_and_long_parent_members_execute_and_reopen_with_stable_ascii_jobs() {
    use archeaxis_application::container;
    use archeaxis_domain::anchor;
    assert_eq!(
        container::member_job_id("job-safe", "0001-known.csv"),
        "job-safe-member-0001-known.csv"
    );
    let cases = [
        (
            "job-unicode".to_string(),
            "资料/章节.txt",
            "member-d37ffbd7568f4df14b8871ebb463d284f724e278f8bc440f55627b1c7277803e",
        ),
        (
            "p".repeat(190),
            "notes/long-parent.txt",
            "member-0f70bfa2ac7cdead3cb290192bf1bbffdb98e358521ffa74bcbd165a5a1dfcf6",
        ),
    ];
    for (parent_job, member_name, expected_identifier) in cases {
        let script = "import io,sys,tarfile\nb=io.BytesIO()\nwith tarfile.open(fileobj=b,mode='w') as t:\n p=b'Archive fallback known value 82\\n'; i=tarfile.TarInfo(sys.argv[1]); i.size=len(p); t.addfile(i,io.BytesIO(p))\nsys.stdout.buffer.write(b.getvalue())";
        let generated = std::process::Command::new(python())
            .env("PYTHONUTF8", "1")
            .args(["-c", script, member_name])
            .output()
            .unwrap();
        assert!(generated.status.success(), "fixture creation must not skip");
        assert!(!generated.stdout.is_empty());
        let dir = tempfile::tempdir().unwrap();
        let executor = open_executor(dir.path()).await;
        let import_job = parent_job.clone();
        let payload = generated.stdout;
        let parent = executor
            .store()
            .submit(move |conn| {
                let source =
                    match source::import_source(conn, &payload, "id-fallback.tar", None).unwrap() {
                        ImportOutcome::Imported { source_id, .. }
                        | ImportOutcome::Duplicate { source_id, .. } => source_id,
                    };
                jobs::enqueue(conn, &import_job, "archive", &source).unwrap();
                source
            })
            .await
            .unwrap();
        executor
            .execute(
                &parent_job,
                "fallback-parent-run",
                60_000,
                &Cancellation::new(),
            )
            .await
            .unwrap();
        let query_parent = parent.clone();
        let query_job = parent_job.clone();
        let rows = executor
            .store()
            .submit(move |conn| {
                assert_eq!(
                    jobs::job_state(conn, &query_job).unwrap().unwrap(),
                    "succeeded"
                );
                container::members_of(conn, &query_parent).unwrap()
            })
            .await
            .unwrap();
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0].member, member_name);
        assert_eq!(rows[0].original_name.as_deref(), Some(member_name));
        assert_eq!(rows[0].origin_ref, format!("{parent}#{member_name}"));
        let child_job = rows[0]
            .job_id
            .clone()
            .expect("automatic child job must exist");
        assert!(child_job.starts_with("member-") && child_job.len() == 71);
        assert_eq!(
            child_job, expected_identifier,
            "Rust fallback must match the probe SHA framing"
        );
        assert!(
            child_job
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || b"-_.".contains(&byte))
        );
        let expected_job = parent_job.clone();
        let expected_child = child_job.clone();
        executor
            .store()
            .submit(move |conn| {
                let declared = container::declared_members(conn, &expected_job).unwrap();
                assert_eq!(declared.len(), 1);
                assert_eq!(
                    container::member_job_id(&expected_job, &declared[0].file),
                    expected_child
                );
            })
            .await
            .unwrap();
        executor
            .execute(
                &child_job,
                "fallback-child-run",
                60_000,
                &Cancellation::new(),
            )
            .await
            .unwrap();
        let child_source = rows[0].source_id.clone();
        let source_query = child_source.clone();
        let job_query = child_job.clone();
        let snapshot = executor
            .store()
            .submit(move |conn| {
                assert_eq!(
                    jobs::job_state(conn, &job_query).unwrap().unwrap(),
                    "succeeded"
                );
                let text: String = conn
                    .query_row(
                        "SELECT text FROM transforms WHERE source_id=?1",
                        [&source_query],
                        |r| r.get(0),
                    )
                    .unwrap();
                assert_eq!(text, "Archive fallback known value 82\n");
                let revision: String = conn
                    .query_row(
                        "SELECT sha256 FROM sources WHERE source_id=?1",
                        [&source_query],
                        |r| r.get(0),
                    )
                    .unwrap();
                let anchor_id = anchor::add_anchor(
                    conn,
                    &source_query,
                    &revision,
                    r#"{"type":"text","start":0,"end":30}"#,
                )
                .unwrap();
                let position = anchor::get_anchor(conn, &anchor_id).unwrap().unwrap();
                let loss: String = conn
                    .query_row(
                        "SELECT content FROM job_outputs WHERE job_id=?1 AND kind='loss_report'",
                        [&job_query],
                        |r| r.get(0),
                    )
                    .unwrap();
                assert!(
                    serde_json::from_str::<serde_json::Value>(&loss).unwrap()["loss_note"]
                        .as_str()
                        .unwrap()
                        .len()
                        > 0
                );
                (text, loss, anchor_id, position)
            })
            .await
            .unwrap();
        drop(executor);
        let reopened = open_executor(dir.path()).await;
        let expected = snapshot.clone();
        let origin_parent = parent.clone();
        reopened
            .store()
            .submit(move |conn| {
                assert_eq!(
                    jobs::job_state(conn, &parent_job).unwrap().unwrap(),
                    "succeeded"
                );
                assert_eq!(
                    jobs::job_state(conn, &child_job).unwrap().unwrap(),
                    "succeeded"
                );
                let members = container::members_of(conn, &origin_parent).unwrap();
                assert_eq!(members[0].member, member_name);
                assert_eq!(
                    members[0].origin_ref,
                    format!("{origin_parent}#{member_name}")
                );
                assert_eq!(members[0].job_id.as_deref(), Some(child_job.as_str()));
                assert!(members[0].readable);
                let text: String = conn
                    .query_row(
                        "SELECT text FROM transforms WHERE source_id=?1",
                        [&child_source],
                        |r| r.get(0),
                    )
                    .unwrap();
                let loss: String = conn
                    .query_row(
                        "SELECT content FROM job_outputs WHERE job_id=?1 AND kind='loss_report'",
                        [&child_job],
                        |r| r.get(0),
                    )
                    .unwrap();
                assert_eq!(
                    (
                        text,
                        loss,
                        anchor::get_anchor(conn, &expected.2).unwrap().unwrap()
                    ),
                    (expected.0, expected.1, expected.3)
                );
            })
            .await
            .unwrap();
    }
}
