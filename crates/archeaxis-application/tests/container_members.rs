//! R15/F15 second half: a container's members become sources, and the relation is
//! recorded.
//!
//! The end-to-end path is exercised with the real workers: an archive job inventories
//! the container and extracts its members; the Core verifies every member digest,
//! imports each one as its own source recording `archive-member` with the container in
//! the origin reference, and enqueues a job for each member whose name resolves to a
//! route. The negative cases are the point as much as the positive one: a member whose
//! bytes do not match its declaration is refused, and a member no route can read is
//! still kept as a source and reported as custody-only rather than dropped.

use archeaxis_application::{
    container,
    executor::{Cancellation, Executor},
    jobs,
};
use archeaxis_domain::source::{self, ImportOutcome};
use std::path::PathBuf;

fn python() -> PathBuf {
    std::env::var_os("ARCHEAXIS_PYTHON").expect("run cargo via the project wrapper").into()
}

fn repo() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize().unwrap()
}

/// A real ZIP with a readable text member, an image member and an unreadable one.
fn zip_bytes() -> Vec<u8> {
    let script = "import io,sys,zipfile\n\
                  from PIL import Image\n\
                  png=io.BytesIO()\n\
                  Image.new('RGB',(40,20),'white').save(png,'PNG')\n\
                  buf=io.BytesIO()\n\
                  with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as c:\n\
                  \x20   c.writestr('notes/index.md','# Index\\nThe value is 6371 km.\\n')\n\
                  \x20   c.writestr('assets/shot.png',png.getvalue())\n\
                  \x20   c.writestr('opaque/blob.bin','raw bytes no route reads\\n')\n\
                  sys.stdout.buffer.write(buf.getvalue())\n";
    match std::process::Command::new(python()).arg("-c").arg(script).output() {
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
        &[
            ("archive.inventory", repo().join("services/python-workers/document/worker_archive.py")),
            ("image.ocr", repo().join("services/python-workers/vision/worker_ocr.py")),
        ],
    )
    .await
    .unwrap()
}

async fn run_archive_job(executor: &Executor) -> Vec<u8> {
    let payload = zip_bytes();
    let copy = payload.clone();
    executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &copy, "bundle.zip", None).unwrap() {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-zip", "archive", &source_id).unwrap();
        })
        .await
        .unwrap();
    executor.execute("job-zip", "run-zip", 120_000, &Cancellation::new()).await.unwrap();
    payload
}

#[tokio::test]
async fn container_members_become_sources_recording_where_they_came_from() {
    if zip_bytes().is_empty() {
        eprintln!("skipping: zipfile or PIL unavailable for building a sample");
        return;
    }
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let staging = dir.path().join("staging");
    run_archive_job(&executor).await;

    let expansion = executor
        .store()
        .submit({
            let staging = staging.clone();
            move |conn| container::expand_members(conn, &staging, "job-zip").unwrap()
        })
        .await
        .unwrap();

    assert_eq!(expansion.sources.len(), 3, "every extracted member becomes a source: {expansion:?}");
    assert_eq!(expansion.jobs.len(), 2, "the markdown and the image resolve to routes: {expansion:?}");
    assert_eq!(expansion.custody_only, vec!["opaque/blob.bin".to_string()]);

    // the relation is recorded, with the container in the origin reference
    let (records, container_source) = executor
        .store()
        .submit(|conn| {
            let container_source: String = conn
                .query_row(
                    "SELECT input_ref FROM jobs WHERE job_id='job-zip'",
                    [],
                    |row| row.get(0),
                )
                .unwrap();
            let mut statement = conn
                .prepare("SELECT origin_kind, origin_ref, original_name FROM source_origins ORDER BY origin_ref")
                .unwrap();
            let rows = statement
                .query_map([], |row| {
                    Ok((
                        row.get::<_, String>(0).unwrap(),
                        row.get::<_, String>(1).unwrap(),
                        row.get::<_, Option<String>>(2).unwrap(),
                    ))
                })
                .unwrap()
                .map(|row| row.unwrap())
                .collect::<Vec<_>>();
            (rows, container_source)
        })
        .await
        .unwrap();

    assert_eq!(records.len(), 3, "each member records exactly one origin: {records:?}");
    for (kind, reference, name) in &records {
        assert_eq!(kind, container::ORIGIN_KIND);
        assert_eq!(kind, "import", "the store's origin vocabulary is fixed; the relation rides in the reference");
        assert!(
            reference.starts_with(&format!("{container_source}#")),
            "the origin must name the container: {reference}"
        );
        assert!(name.as_deref().unwrap_or_default().contains('/'), "member names keep their path: {name:?}");
    }
    // the vocabulary is enforced by the store, so an invented kind would be dropped in
    // silence: this test exists to keep the kind inside it
    assert!(
        ["path", "url", "import", "manual"].contains(&container::ORIGIN_KIND),
        "the recorded kind must be one the store accepts"
    );

    // the queued member jobs are real jobs with the right kinds
    let kinds: Vec<(String, String)> = executor
        .store()
        .submit(|conn| {
            let mut statement = conn
                .prepare("SELECT job_id, kind FROM jobs WHERE job_id LIKE 'job-zip-member-%' ORDER BY job_id")
                .unwrap();
            statement
                .query_map([], |row| Ok((row.get::<_, String>(0).unwrap(), row.get::<_, String>(1).unwrap())))
                .unwrap()
                .map(|row| row.unwrap())
                .collect()
        })
        .await
        .unwrap();
    let kind_set: std::collections::BTreeSet<String> = kinds.iter().map(|(_, kind)| kind.clone()).collect();
    assert_eq!(kind_set, ["image".to_string(), "text".to_string()].into_iter().collect());

    // expanding twice is idempotent: same sources, no new jobs
    let again = executor
        .store()
        .submit({
            let staging = staging.clone();
            move |conn| container::expand_members(conn, &staging, "job-zip").unwrap()
        })
        .await
        .unwrap();
    assert!(again.jobs.is_empty(), "a second expansion must not enqueue more work: {again:?}");
    assert_eq!(again.sources.len(), 3);

    // and a member job really reads its member: the markdown text reaches the store
    let text_job = kinds
        .iter()
        .find(|(_, kind)| kind == "text")
        .map(|(job, _)| job.clone())
        .unwrap();
    executor.execute(&text_job, "run-member", 120_000, &Cancellation::new()).await.unwrap();
    let text: String = executor
        .store()
        .submit(move |conn| {
            conn.query_row(
                "SELECT text FROM transforms WHERE source_id=(
                   SELECT input_ref FROM jobs WHERE job_id=?1) ORDER BY transform_id DESC LIMIT 1",
                [&text_job],
                |row| row.get(0),
            )
            .unwrap_or_default()
        })
        .await
        .unwrap();
    assert!(text.contains("6371"), "the member's own content must be extracted: {text:?}");
}

#[tokio::test]
async fn a_member_that_does_not_match_its_declaration_is_refused() {
    if zip_bytes().is_empty() {
        eprintln!("skipping: zipfile or PIL unavailable for building a sample");
        return;
    }
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let staging = dir.path().join("staging");
    run_archive_job(&executor).await;

    let declared = executor
        .store()
        .submit(|conn| container::declared_members(conn, "job-zip").unwrap())
        .await
        .unwrap();
    assert_eq!(declared.len(), 3);
    let target = staging.join("members").join(&declared[0].file);
    assert!(target.is_file(), "the member must be there before we tamper with it");
    std::fs::write(&target, b"not the member that was declared").unwrap();

    let refused = executor
        .store()
        .submit({
            let staging = staging.clone();
            move |conn| container::expand_members(conn, &staging, "job-zip")
        })
        .await
        .unwrap();
    let error = refused.unwrap_err().to_string();
    assert!(error.contains("cannot enqueue work"), "{error}");
    let jobs_after: i64 = executor
        .store()
        .submit(|conn| {
            conn.query_row("SELECT count(*) FROM jobs WHERE job_id LIKE 'job-zip-member-%'", [], |row| row.get(0))
                .unwrap()
        })
        .await
        .unwrap();
    assert_eq!(jobs_after, 0, "an unverifiable member must leave no queued job behind");
}
