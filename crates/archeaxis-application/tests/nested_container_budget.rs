//! R15/F15 and F13: a container inside a container is reached, and the bound on that is stated.
//!
//! Nesting used to be refused by name, so an archive inside an archive (or inside a mail) kept
//! its files out of reach at any depth. Now the member relation is followed and each level is
//! expanded like any container, with one bounded decision recorded in the Core: past
//! `CONTAINER_DEPTH_LIMIT` a member container is imported and kept, but its own expansion does
//! not run, and it is reported as nesting-limited rather than as unread.

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

/// The bytes of an outer archive holding `level-2.zip` holding `level-3.zip`, where `level-3.zip`
/// holds both `level-4.zip` and a plain note. Built from the inside out, so every layer is a
/// real ZIP rather than a declared one, and the over-budget level contains a readable file as
/// well as a container - which is what tells the two decisions apart.
fn nested_zip_bytes() -> Vec<u8> {
    let script = "import io,sys,zipfile\n\
                  def pack(items):\n\
                  \x20   buf=io.BytesIO()\n\
                  \x20   with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as c:\n\
                  \x20   \x20   for name,data in items:\n\
                  \x20   \x20   \x20   c.writestr(name,data)\n\
                  \x20   return buf.getvalue()\n\
                  note=b'# Deep\\nThe value is 6371 km.\\n'\n\
                  four=pack([('deep/note.md',note)])\n\
                  three=pack([('level-4.zip',four),('deep/note.md',note)])\n\
                  two=pack([('level-3.zip',three)])\n\
                  sys.stdout.buffer.write(pack([('level-2.zip',two)]))\n";
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

/// Submit one source, queue one job of `kind`, run it, and return the ids of both.
async fn submit_and_run(
    executor: &Executor,
    job: &str,
    name: &str,
    kind: &str,
    payload: Vec<u8>,
) -> String {
    let copy = payload.clone();
    let owned_job = job.to_string();
    let owned_name = name.to_string();
    let owned_kind = kind.to_string();
    let source_id = executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &copy, &owned_name, None).unwrap() {
                ImportOutcome::Imported { source_id, .. }
                | ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, &owned_job, &owned_kind, &source_id).unwrap();
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

async fn members(executor: &Executor, source_id: &str) -> Vec<container::MemberRow> {
    let owned = source_id.to_string();
    executor
        .store()
        .submit(move |conn| container::members_of(conn, &owned).unwrap())
        .await
        .unwrap()
}

#[tokio::test]
async fn an_archive_inside_an_archive_is_expanded_and_the_depth_bound_is_named() {
    let sample = nested_zip_bytes();
    if sample.is_empty() {
        eprintln!("skipping: zipfile is unavailable for building nested samples");
        return;
    }
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;

    // level 1: the outer archive holds level-2.zip, which holds level-3.zip
    let outer = submit_and_run(&executor, "job-nest-1", "outer.zip", "archive", sample).await;
    let second = members(&executor, &outer).await;
    let second = second
        .iter()
        .find(|row| row.member == "level-2.zip")
        .unwrap_or_else(|| panic!("the nested archive became a member: {second:?}"));
    let level_two_job = second
        .job_id
        .clone()
        .expect("a nested container gets its own archive job now, not a name refusal");

    // level 2: expanding it reaches level-3.zip, which is still inside the budget
    executor
        .execute(&level_two_job, "run-nest-2", 120_000, &Cancellation::new())
        .await
        .unwrap();
    let third = members(&executor, &second.source_id).await;
    let third = third
        .iter()
        .find(|row| row.member == "level-3.zip")
        .unwrap_or_else(|| panic!("the second level expanded: {third:?}"));
    assert!(
        third.job_id.is_some(),
        "the second nesting level is still inside the budget: {third:?}"
    );

    // level 3: its own container is kept but stops at the recorded bound
    let level_three_job = third.job_id.clone().unwrap();
    executor
        .execute(
            &level_three_job,
            "run-nest-3",
            120_000,
            &Cancellation::new(),
        )
        .await
        .unwrap();
    let fourth = members(&executor, &third.source_id).await;
    let stopped = fourth
        .iter()
        .find(|row| row.member == "level-4.zip")
        .unwrap_or_else(|| panic!("the third level expanded: {fourth:?}"));
    assert_eq!(
        stopped.job_id, None,
        "past the budget no work is created: {stopped:?}"
    );
    let stopped_source = stopped.source_id.clone();
    let lane = executor
        .store()
        .submit(move |conn| container::member_lane(conn, &stopped_source, "level-4.zip").unwrap())
        .await
        .unwrap();
    assert_eq!(
        lane,
        container::MemberLane::NestingLimited,
        "and the reason is the nesting budget, not an unreadable name"
    );

    // a file inside the same over-budget container is still read - the bound stops containers
    let note = fourth
        .iter()
        .find(|row| row.member == "deep/note.md")
        .unwrap_or_else(|| panic!("a plain member is unaffected: {fourth:?}"));
    assert!(
        note.job_id.is_some(),
        "the depth bound applies to containers only: {note:?}"
    );
}
