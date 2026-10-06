//! R15/F14: a legacy binary workbook's converted sheets become members the Core imports.
//!
//! The office worker writes one CSV per sheet into the attempt's transfer area and declares
//! each by digest; the Core verifies digest and size, imports each CSV as its own source
//! recording where it came from, and queues the text route the sheet's own name selects. The
//! refusal half matters equally: `.doc` and `.ppt` still have no reader, so they must stay
//! unnamed rather than reach a route that cannot open them.

use archeaxis_application::{
    attempts, container,
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

fn xls_bytes() -> Vec<u8> {
    let path = repo().join("tests/fixtures/golden/golden-xls-anchor.xls");
    std::fs::read(&path).unwrap_or_default()
}

async fn open_executor(dir: &std::path::Path) -> Executor {
    Executor::open_routes(
        &dir.join("db.sqlite"),
        &dir.join("staging"),
        &python(),
        &repo().join("services/python-workers/transport/text_ndjson.py"),
        &[(
            "office.structure",
            repo().join("services/python-workers/document/worker_office.py"),
        )],
    )
    .await
    .unwrap()
}

#[tokio::test]
async fn converted_sheets_become_sources_with_their_own_jobs() {
    let payload = xls_bytes();
    assert!(
        !payload.is_empty(),
        "the committed legacy workbook is the fixture for this chain"
    );
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let copy = payload.clone();
    let xls_source = executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &copy, "book.xls", None).unwrap() {
                ImportOutcome::Imported { source_id, .. }
                | ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-xls", "office", &source_id).unwrap();
            source_id
        })
        .await
        .unwrap();

    executor
        .execute("job-xls", "run-xls", 120_000, &Cancellation::new())
        .await
        .unwrap();

    let declared = executor
        .store()
        .submit(|conn| container::declared_members(conn, "job-xls").unwrap())
        .await
        .unwrap();
    assert_eq!(
        declared.len(),
        2,
        "one declared conversion per sheet: {declared:?}"
    );
    assert_eq!(declared[0].name, "Evidence.csv");
    assert_eq!(declared[1].name, "Numbers.csv");
    for member in &declared {
        assert!(
            !member.file.contains('/') && !member.file.contains(".."),
            "a written name is flat: {}",
            member.file
        );
    }

    let rows = executor
        .store()
        .submit({
            let source = xls_source.clone();
            move |conn| container::members_of(conn, &source).unwrap()
        })
        .await
        .unwrap();
    assert_eq!(rows.len(), 2, "{rows:?}");
    let evidence = rows
        .iter()
        .find(|row| row.member == "Evidence.csv")
        .expect("the converted sheet is a member");
    assert_eq!(
        evidence.origin_ref,
        format!("{xls_source}#Evidence.csv"),
        "the conversion names the workbook it came from"
    );
    assert!(
        evidence.job_id.is_some(),
        "a CSV sheet is readable, so it must have its own job"
    );
    let numbers = rows
        .iter()
        .find(|row| row.member == "Numbers.csv")
        .expect("the second sheet is a member");
    assert!(numbers.job_id.is_some());

    // running one member job proves the counterpart is real content, not a declared name
    let member_job = evidence.job_id.clone().unwrap();
    executor
        .execute(&member_job, "run-member", 120_000, &Cancellation::new())
        .await
        .unwrap();
    let (state, text) = executor
        .store()
        .submit({
            let source = evidence.source_id.clone();
            move |conn| {
                let state = jobs::job_state(conn, &member_job)
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
    assert_eq!(state, "succeeded", "the converted sheet was read");
    assert!(
        text.contains("星环 知识平台"),
        "the conversion carries the workbook's own text: {text:?}"
    );

    let after = executor
        .store()
        .submit({
            let source = xls_source.clone();
            move |conn| container::members_of(conn, &source).unwrap()
        })
        .await
        .unwrap();
    assert!(
        after
            .iter()
            .find(|row| row.member == "Evidence.csv")
            .expect("still a member")
            .readable,
        "readable means a transform now exists for the converted sheet"
    );
}

#[tokio::test]
async fn the_formats_with_no_reader_stay_unnamed_rather_than_reaching_a_route() {
    for name in ["old.doc", "old.ppt"] {
        let error = attempts::resolve_media_type("office", name)
            .unwrap_err()
            .to_string();
        assert!(
            error.contains("cannot name a media type"),
            "{name}: {error}"
        );
    }
    assert_eq!(
        attempts::resolve_media_type("office", "book.xls").unwrap(),
        "application/vnd.ms-excel",
        "the workbook is named because a reader exists for it here"
    );
}
