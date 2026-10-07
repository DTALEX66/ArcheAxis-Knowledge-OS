//! R15/F15: a container's member, read by its own job, promoted to a knowledge candidate.
//!
//! The chain this closes is the last clause of F15: a member that has been read was never taken
//! through the product's own promotion route, so the container-to-file-to-knowledge relation was
//! proven only as far as "readable". Here a real ZIP is expanded by a real worker, one member is
//! read by the job its own name selected, and a human promotes a quoted selection of that reading
//! into a candidate. The container relation must survive it, and the two refusals that make the
//! promotion honest - a machine actor and a quote that is not what the transform holds - must hold.

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;

use archeaxis_api::app;
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

/// A real ZIP whose one member is a markdown note a text route can read.
fn zip_bytes() -> Vec<u8> {
    let script = "import io,sys,zipfile\n\
                  buf=io.BytesIO()\n\
                  with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as c:\n\
                  \x20   c.writestr('notes/index.md','# Index\\nThe Earth radius is 6371 km.\\n')\n\
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

/// UTF-16 offsets, which is what the promotion route counts in.
fn utf16_prefix(text: &str, byte_index: usize) -> usize {
    text[..byte_index]
        .chars()
        .map(char::len_utf16)
        .sum::<usize>()
}

async fn post(
    router: &axum::Router,
    uri: &str,
    payload: Value,
    actor: &str,
) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::post(uri)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", actor)
                .body(Body::from(payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes)
            .unwrap_or_else(|_| json!({"raw": String::from_utf8_lossy(&bytes).to_string()})),
    )
}

#[tokio::test]
async fn a_read_member_is_promotable_and_keeps_naming_its_container() {
    let sample = zip_bytes();
    assert!(
        !sample.is_empty(),
        "zipfile must build the sample, never skip"
    );
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("db.sqlite");
    let executor = Executor::open_routes(
        &db,
        &dir.path().join("staging"),
        &python(),
        &repo().join("services/python-workers/transport/text_ndjson.py"),
        &[(
            "archive.inventory",
            repo().join("services/python-workers/document/worker_archive.py"),
        )],
    )
    .await
    .unwrap();

    // level 1: the container is inventoried and its member becomes a source with its own job
    let outer = {
        let copy = sample.clone();
        executor
            .store()
            .submit(move |conn| {
                let source_id = match source::import_source(conn, &copy, "bundle.zip", None)
                    .expect("import the container")
                {
                    ImportOutcome::Imported { source_id, .. }
                    | ImportOutcome::Duplicate { source_id, .. } => source_id,
                };
                jobs::enqueue(conn, "job-outer", "archive", &source_id).expect("enqueue");
                source_id
            })
            .await
            .unwrap()
    };
    executor
        .execute("job-outer", "run-outer", 120_000, &Cancellation::new())
        .await
        .unwrap();
    let members = {
        let outer = outer.clone();
        executor
            .store()
            .submit(move |conn| container::members_of(conn, &outer).unwrap())
            .await
            .unwrap()
    };
    let member = members
        .iter()
        .find(|row| row.member == "notes/index.md")
        .unwrap_or_else(|| panic!("the note became a member: {members:?}"));
    let member_job = member
        .job_id
        .clone()
        .expect("a readable member name selects its own job");

    // level 2: the member is read by that job, which is what "readable" was ever supposed to mean
    executor
        .execute(&member_job, "run-member", 120_000, &Cancellation::new())
        .await
        .unwrap();
    let (transform_id, transform_text) = {
        let source_id = member.source_id.clone();
        let member_job = member_job.clone();
        executor
            .store()
            .submit(move |conn| {
                let (transform_id, text): (i64, String) = conn
                    .query_row(
                        "SELECT j.transform_id, t.text FROM jobs j JOIN transforms t ON t.transform_id=j.transform_id
                         WHERE j.job_id=?1 AND j.input_ref=?2 AND j.state='succeeded'",
                        rusqlite::params![member_job, source_id],
                        |row| Ok((row.get(0)?, row.get(1)?)),
                    )
                    .unwrap();
                (transform_id, text)
            })
            .await
            .unwrap()
    };
    assert!(
        transform_text.contains("6371"),
        "the member's own reading: {transform_text:?}"
    );
    drop(executor);

    let router = app(db.to_str().unwrap()).unwrap();
    let start = transform_text
        .find("6371 km")
        .expect("the reading holds the fact");
    let quote = &transform_text[start..start + "6371 km".len()];
    let promotion = json!({
        "knowledge_type": "FACTUAL_CLAIM",
        "body": "The Earth radius is stated as 6371 km by a note inside the bundle.",
        "source_id": member.source_id,
        "job_id": member_job,
        "transform_id": transform_id,
        "selection_start_utf16": utf16_prefix(&transform_text, start),
        "selection_end_utf16": utf16_prefix(&transform_text, start) + quote.len(),
        "quote": quote,
    });

    let (status, payload) = post(
        &router,
        &format!("/api/v1/knowledge-items/from-transform"),
        promotion.clone(),
        "human",
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "{payload}");
    assert_eq!(payload["status"], "candidate", "{payload}");
    assert_eq!(payload["requires_human_review"], true, "{payload}");
    assert!(
        payload["anchor_id"]
            .as_str()
            .is_some_and(|id| id.starts_with("anc_")),
        "{payload}"
    );
    assert_eq!(payload["source_id"], member.source_id, "{payload}");

    // promotion must not disturb where the member came from
    let check = rusqlite::Connection::open(&db).unwrap();
    let (origin_ref, readable): (String, i64) = check
        .query_row(
            "SELECT o.origin_ref, EXISTS(SELECT 1 FROM transforms t WHERE t.source_id=o.source_id)
             FROM source_origins o WHERE o.source_id=?1 AND o.origin_kind='import'",
            [&member.source_id],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .expect("the member's origin is still recorded");
    assert_eq!(origin_ref, format!("{outer}#notes/index.md"));
    assert_eq!(readable, 1, "and it is still readable after promotion");

    // a machine cannot promote: the candidate stays a human act
    let (status, payload) = post(
        &router,
        "/api/v1/knowledge-items/from-transform",
        promotion.clone(),
        "machine",
    )
    .await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{payload}");

    // and a quote that is not what the transform holds at those offsets is refused
    let forged = json!({
        "knowledge_type": "FACTUAL_CLAIM",
        "body": "A claim the source does not make.",
        "source_id": member.source_id,
        "job_id": member_job,
        "transform_id": transform_id,
        "selection_start_utf16": utf16_prefix(&transform_text, start),
        "selection_end_utf16": utf16_prefix(&transform_text, start) + quote.len(),
        "quote": "9312 km",
    });
    let (status, payload) = post(
        &router,
        "/api/v1/knowledge-items/from-transform",
        forged,
        "human",
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST, "{payload}");
    assert!(
        format!("{payload}").contains("quote"),
        "the refusal names why: {payload}"
    );
}
