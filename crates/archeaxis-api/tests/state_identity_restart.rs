//! P5 / M0: one state written across every class this project owns, read back after restart.
//!
//! The neighbouring suites each pin their own class surviving a reopen. What none of them does is
//! hold a *whole* state - source bytes, a two-level container relation, a transform, three locator
//! kinds, a human-created candidate, a machine receipt - and assert that the identities that other
//! records point at are the same records after the store closes and opens twice. That matters most
//! for the anchor work: an anchor id and a knowledge receipt hash are derived from the stored
//! position, so a migration or a write that re-canonicalised the JSON would silently re-point
//! every citation in the workspace.
//!
//! Synthetic bytes and fixed strings only: no model call, no network, no release action.

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;

use archeaxis_api::app;
use archeaxis_domain::{
    anchor,
    knowledge::KnowledgeV3Metadata,
    machine::{self, MachineTask},
    source::{self, ImportOutcome, OriginInfo},
};
use archeaxis_store_sqlite::init_workspace;

const MEMBER_ORIGIN: &str = "notes/index.md";
const TRANSFORM_TEXT: &str = "# Index\nThe Earth radius is 6371 km.\n";
const MEMBER_BYTES: &[u8] = b"# Index\nThe Earth radius is 6371 km.\n";

/// The revision a source's bytes hash to, which is what an anchor's identity is partly made of.
fn sha(bytes: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    format!("{:x}", Sha256::digest(bytes))
}

fn imported(outcome: ImportOutcome) -> String {
    match outcome {
        ImportOutcome::Imported { source_id, .. } | ImportOutcome::Duplicate { source_id, .. } => {
            source_id
        }
    }
}

/// Everything the state consists of, as it was first written.
#[derive(Debug)]
struct Written {
    outer: String,
    member: String,
    inner: String,
    transform_id: i64,
    structure_anchor: String,
    location_anchor: String,
    text_anchor: String,
    knowledge_id: String,
    knowledge_anchor: String,
    raw_sha256: String,
}

async fn get(router: &axum::Router, uri: &str) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(Request::get(uri).body(Body::empty()).unwrap())
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

fn metadata() -> KnowledgeV3Metadata {
    KnowledgeV3Metadata {
        source_type: "derived_inference".to_string(),
        owner: "human".to_string(),
        support_level: "none".to_string(),
        confidence: None,
        risk_level: "low".to_string(),
        valid_from: None,
        valid_to: None,
        external_evidence: Vec::new(),
        requires_human_review: true,
    }
}

fn write_state(db: &str) -> Written {
    let mut conn = init_workspace(db).unwrap();
    let outer = imported(
        source::import_source(&mut conn, b"PK\x03\x04 outer container", "bundle.zip", None)
            .unwrap(),
    );
    let member = imported(
        source::import_source_with_origin(
            &mut conn,
            MEMBER_BYTES,
            MEMBER_ORIGIN,
            None,
            Some(OriginInfo {
                kind: "import",
                origin_ref: &format!("{outer}#{MEMBER_ORIGIN}"),
                original_name: Some(MEMBER_ORIGIN),
                received_at: None,
            }),
        )
        .unwrap(),
    );
    // the second level: a note that came out of a container that was itself a member
    let inner_ref = format!("{member}#inner/note.md");
    let inner = imported(
        source::import_source_with_origin(
            &mut conn,
            b"inner note 6371\n",
            "note.md",
            None,
            Some(OriginInfo {
                kind: "import",
                origin_ref: &inner_ref,
                original_name: Some("inner/note.md"),
                received_at: None,
            }),
        )
        .unwrap(),
    );
    let transform_id = source::record_transform(
        &mut conn,
        &member,
        "python-worker-text",
        TRANSFORM_TEXT,
        None,
    )
    .unwrap();
    conn.execute(
        "INSERT INTO jobs(job_id,kind,state,input_ref,engine,transform_id) VALUES('job-member','text','succeeded',?1,'fixture',?2)",
        rusqlite::params![member, transform_id],
    )
    .unwrap();

    // three locator kinds. Written through the domain, not the HTTP route: the route
    // augments the position with its own `location_status`/`checksum` fields, so a
    // route-written position string is a different one and therefore a different id.
    // What this pins is that *a* stored position keeps its id across reopens, not that
    // the route and the domain derive the same id.
    let member_sha = sha(MEMBER_BYTES);
    let structure_anchor = anchor::add_anchor(
        &mut conn,
        &member,
        &member_sha,
        &json!({"type": "worker_structure", "job_id": "job-member", "attempt": 1,
                "kind": "paragraph", "path": ["document-1", "paragraph-2"]})
        .to_string(),
    )
    .unwrap();
    let location_anchor = anchor::add_anchor(
        &mut conn,
        &member,
        &member_sha,
        &json!({"type": "format_location", "job_id": "job-member", "attempt": 1,
                "kind": "odf_heading", "path": "/text:h/1"})
        .to_string(),
    )
    .unwrap();
    let text_anchor = anchor::add_anchor(
        &mut conn,
        &member,
        &member_sha,
        &json!({"type": "text", "start": 21, "end": 28}).to_string(),
    )
    .unwrap();
    assert_eq!(
        anchor::add_anchor(
            &mut conn,
            &member,
            &member_sha,
            &json!({"type": "text", "start": 21, "end": 28}).to_string(),
        )
        .unwrap(),
        text_anchor,
        "the same position must dedupe to the same anchor rather than mint a second one"
    );

    let (knowledge_id, knowledge_anchor, raw_sha256) = knowledge_create(&mut conn, &member);

    let task = MachineTask {
        task_id: "task-restart-1",
        principal: "machine",
        conditions: "offline; fixed synthetic sample bound to a member source",
        knowledge_version: None,
        method_version: Some("container.expand_members/v1"),
        tool_version: Some("core"),
        model_version: "not-a-model: deterministic core chaining",
        scope: &member,
        outcome: "failed",
        failure: Some("the member beyond the nesting budget was not expanded"),
        retest_of: None,
    };
    machine::record_machine_task(&mut conn, &task).expect("record the machine receipt");

    Written {
        outer,
        member,
        inner,
        transform_id,
        structure_anchor,
        location_anchor,
        text_anchor,
        knowledge_id,
        knowledge_anchor,
        raw_sha256,
    }
}

fn knowledge_create(conn: &mut rusqlite::Connection, member: &str) -> (String, String, String) {
    let transform_id: i64 = conn
        .query_row(
            "SELECT transform_id FROM jobs WHERE job_id='job-member'",
            [],
            |row| row.get(0),
        )
        .unwrap();
    archeaxis_domain::knowledge::create_knowledge_v3_from_transform(
        conn,
        "FACTUAL_CLAIM",
        "The Earth radius is stated as 6371 km by a note inside the bundle.",
        "human",
        member,
        "job-member",
        transform_id,
        28,
        35,
        "6371 km",
        &metadata(),
    )
    .expect("the source-bound candidate is created")
}

/// Every identity read back through the surfaces that publish it.
async fn read_state(db: &str, written: &Written) {
    let router = app(db).unwrap();

    let (status, members) = get(
        &router,
        &format!("/api/v1/sources/{}/members", written.outer),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{members}");
    let row = members["members"]
        .as_array()
        .unwrap()
        .iter()
        .find(|item| item["member"] == MEMBER_ORIGIN)
        .unwrap_or_else(|| panic!("the member is still listed: {members}"));
    assert_eq!(row["source_id"], written.member, "{members}");
    assert_eq!(row["readable"], true, "a read member stays read: {members}");
    assert_eq!(
        row["origin_ref"],
        format!("{}#{}", written.outer, MEMBER_ORIGIN)
    );

    let (status, listed) = get(
        &router,
        &format!("/api/v1/sources/{}/anchors", written.member),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{listed}");
    let published: Vec<String> = listed["anchors"]
        .as_array()
        .unwrap()
        .iter()
        .map(|item| item["anchor_id"].as_str().unwrap().to_string())
        .collect();
    for anchor_id in [
        &written.structure_anchor,
        &written.location_anchor,
        &written.text_anchor,
    ] {
        assert!(
            published.contains(anchor_id),
            "{anchor_id} missing from {published:?}"
        );
    }

    let (status, knowledge) = get(
        &router,
        &format!("/api/v1/knowledge-items/{}/v3", written.knowledge_id),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{knowledge}");
    let serialized = knowledge.to_string();
    assert!(
        serialized.contains(&written.knowledge_anchor),
        "{knowledge}"
    );
    assert!(serialized.contains("candidate"), "{knowledge}");

    let (status, evidence) = get(
        &router,
        &format!("/api/v1/evidence/anchors?source_id={}", written.member),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{evidence}");

    // store-level identity that no route republishes
    let conn = init_workspace(db).unwrap();
    let raw: String = conn
        .query_row(
            "SELECT sha256 FROM sources WHERE source_id=?1",
            [&written.member],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(
        raw, written.raw_sha256,
        "the member's bytes are the same bytes"
    );
    let second_level: String = conn
        .query_row(
            "SELECT origin_ref FROM source_origins WHERE source_id=?1",
            [&written.inner],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(second_level, format!("{}#inner/note.md", written.member));
    let (outcome, failure): (String, Option<String>) = conn
        .query_row(
            "SELECT outcome, failure FROM machine_tasks WHERE task_id='task-restart-1'",
            [],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .unwrap();
    assert_eq!(outcome, "failed");
    assert!(failure.unwrap().contains("nesting budget"));
    let transform: String = conn
        .query_row(
            "SELECT text FROM transforms WHERE transform_id=?1",
            [written.transform_id],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(transform, TRANSFORM_TEXT);
}

#[tokio::test]
async fn a_whole_state_keeps_every_identity_through_two_reopens() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir
        .path()
        .join("state.sqlite")
        .to_str()
        .unwrap()
        .to_string();
    let written = write_state(&db);

    // first read, with the writing connection already released
    read_state(&db, &written).await;
    // second and third: the same process could reuse a handle, so re-open deliberately
    read_state(&db, &written).await;
    read_state(&db, &written).await;

    // and the position JSON is still stored verbatim, so an id derived from it cannot have moved
    let conn = init_workspace(&db).unwrap();
    let position: String = conn
        .query_row(
            "SELECT position FROM anchors WHERE anchor_id=?1",
            [&written.structure_anchor],
            |row| row.get(0),
        )
        .unwrap();
    assert!(position.contains("\"worker_structure\""), "{position}");
    assert!(position.contains("paragraph-2"), "{position}");
}
