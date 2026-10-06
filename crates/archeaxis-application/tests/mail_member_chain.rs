//! R15/F13: a mail's attachments leave the mail and become members the Core can import.
//!
//! The container channel is reused rather than duplicated: the worker writes the attachment
//! bytes into the attempt's transfer area and declares each one by digest, and the Core verifies
//! digest and size, imports each attachment as its own source recording where it came from, and
//! queues the route the attachment's own name selects. The negative half matters as much - an
//! attachment no route can read is kept as a source and reported as custody-only, and an
//! ordinary text job declares nothing at all.

use archeaxis_application::{
    container,
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

/// A two-attachment mail built from stdlib-free bytes: one name a route reads, one it does not.
fn eml_bytes() -> Vec<u8> {
    let lines: &[&str] = &[
        r#"From: sender@example.invalid"#,
        r#"To: reader@example.invalid"#,
        r#"Subject: Two files"#,
        r#"Date: Mon, 06 Oct 2026 12:00:00 +0800"#,
        r#"Message-ID: <chain-1@example.invalid>"#,
        r#"MIME-Version: 1.0"#,
        r#"Content-Type: multipart/mixed; boundary="CHAIN""#,
        "",
        "--CHAIN",
        r#"Content-Type: text/plain; charset="utf-8""#,
        "",
        "Please find the two files. 6371",
        "",
        "--CHAIN",
        r#"Content-Type: application/octet-stream"#,
        r#"Content-Disposition: attachment; filename="notes/index.md""#,
        "",
        "# Index",
        "The value is 6371 km.",
        "",
        "--CHAIN",
        r#"Content-Type: application/octet-stream"#,
        r#"Content-Disposition: attachment; filename="opaque/blob.bin""#,
        "",
        "raw bytes no route reads",
        "",
        "--CHAIN--",
    ];
    let mut out = String::new();
    for line in lines {
        out.push_str(line);
        out.push_str("\r\n");
    }
    out.into_bytes()
}

async fn open_executor(dir: &std::path::Path) -> Executor {
    // No route override for text.extract: the transport is the text route's worker, and it is
    // the layer that decides which media type may write into the transfer area.
    Executor::open_routes(
        &dir.join("db.sqlite"),
        &dir.join("staging"),
        &python(),
        &repo().join("services/python-workers/transport/text_ndjson.py"),
        &[],
    )
    .await
    .unwrap()
}

async fn run_text_job(executor: &Executor, job: &str, name: &str, payload: Vec<u8>) -> String {
    let copy = payload.clone();
    let owned_job = job.to_string();
    let owned_name = name.to_string();
    let source_id = executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &copy, &owned_name, None).unwrap() {
                ImportOutcome::Imported { source_id, .. }
                | ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, &owned_job, "text", &source_id).unwrap();
            source_id
        })
        .await
        .unwrap();
    executor
        .execute(job, &format!("run-{job}"), 120_000, &Cancellation::new())
        .await
        .unwrap();
    source_id
}

#[tokio::test]
async fn mail_attachments_become_sources_with_their_own_jobs() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let mail_source = run_text_job(&executor, "job-mail", "letter.eml", eml_bytes()).await;

    let declared = executor
        .store()
        .submit(|conn| container::declared_members(conn, "job-mail").unwrap())
        .await
        .unwrap();
    assert_eq!(
        declared.len(),
        2,
        "the mail declared both attachments: {declared:?}"
    );
    assert_eq!(declared[0].name, "notes/index.md");
    assert_eq!(declared[1].name, "opaque/blob.bin");
    for member in &declared {
        assert!(
            !member.file.contains('/'),
            "a written name is flat: {}",
            member.file
        );
    }

    // production completion already queued the routable attachment - no manual expansion call
    let rows = executor
        .store()
        .submit({
            let source = mail_source.clone();
            move |conn| container::members_of(conn, &source).unwrap()
        })
        .await
        .unwrap();
    assert_eq!(rows.len(), 2, "{rows:?}");
    let markdown = rows
        .iter()
        .find(|row| row.member == "notes/index.md")
        .expect("the markdown attachment is a member");
    let blob = rows
        .iter()
        .find(|row| row.member == "opaque/blob.bin")
        .expect("the unreadable attachment is still a member");
    assert_eq!(
        markdown.origin_ref,
        format!("{mail_source}#notes/index.md"),
        "the attachment names the mail it came in"
    );
    assert_eq!(
        markdown.job_id.as_deref(),
        Some("job-mail-member-0001-index.md")
    );
    assert!(
        !markdown.readable,
        "the attachment is queued for its own route, not yet read"
    );
    assert_eq!(
        blob.job_id, None,
        "an attachment no route can read stays custody-only"
    );

    // and running that job makes the attachment readable on its own, with its own text
    executor
        .execute(
            "job-mail-member-0001-index.md",
            "run-member",
            120_000,
            &Cancellation::new(),
        )
        .await
        .unwrap();
    let (state, text) = executor
        .store()
        .submit({
            let source = markdown.source_id.clone();
            move |conn| {
                let state = jobs::job_state(conn, "job-mail-member-0001-index.md")
                    .unwrap()
                    .unwrap_or_default();
                let text: String = conn
                    .query_row(
                        "SELECT text FROM transforms WHERE source_id=?1 ORDER BY transform_id DESC LIMIT 1",
                        [&source],
                        |row| row.get(0),
                    )
                    .unwrap_or_default();
                (state, text)
            }
        })
        .await
        .unwrap();
    assert_eq!(state, "succeeded");
    assert!(text.contains("6371"), "the member's own text: {text:?}");
    let after = executor
        .store()
        .submit({
            let source = mail_source.clone();
            move |conn| container::members_of(conn, &source).unwrap()
        })
        .await
        .unwrap();
    let markdown = after
        .iter()
        .find(|row| row.member == "notes/index.md")
        .expect("the member is still listed");
    assert!(
        markdown.readable,
        "readable means a transform now exists for it"
    );
    let kept = after
        .iter()
        .find(|row| row.member == "opaque/blob.bin")
        .expect("the custody member is still listed");
    assert!(!kept.readable, "custody is not silently promoted to read");
}

#[tokio::test]
async fn an_ordinary_text_job_declares_no_members_and_creates_no_chain() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let source = run_text_job(
        &executor,
        "job-note",
        "note.txt",
        b"just a note 6371\n".to_vec(),
    )
    .await;
    let declared = executor
        .store()
        .submit(|conn| container::declared_members(conn, "job-note").unwrap())
        .await
        .unwrap();
    assert!(
        declared.is_empty(),
        "a plain text job declares no members: {declared:?}"
    );
    let rows = executor
        .store()
        .submit({
            let source = source.clone();
            move |conn| container::members_of(conn, &source).unwrap()
        })
        .await
        .unwrap();
    assert!(
        rows.is_empty(),
        "and nothing was imported from it: {rows:?}"
    );
    let members: i64 = executor
        .store()
        .submit(|conn| {
            conn.query_row(
                "SELECT count(*) FROM jobs WHERE job_id LIKE 'job-note-member-%'",
                [],
                |row| row.get(0),
            )
            .unwrap()
        })
        .await
        .unwrap();
    assert_eq!(
        members, 0,
        "the shared channel must not invent work for a text file"
    );
}
