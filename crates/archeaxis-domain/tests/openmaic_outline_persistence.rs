//! Synthetic Core Document persistence for inert OpenMAIC outline candidates.
//! These tests do not start Node, call a model, or qualify an installed app.
use archeaxis_domain::{
    document,
    openmaic_outline::{self, OpenMaicOutlinePending, OpenMaicOutlinePreparation},
};
use archeaxis_store_sqlite::{capability_settings, init_workspace};
use rusqlite::Connection;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

const NAMESPACE: &str = "archeaxis_openmaic_outline_candidate";

fn request() -> Value {
    json!({"schema":"archeaxis.openmaic-outline-replay/v1","request_id":"req_1",
        "requirement":"Synthetic requirement",
        "source_text":"SYNTHETIC source material",
        "reply":{"kind":"synthetic_response",
            "value":"{\"languageDirective\":\"Respond in Simplified Chinese.\",\"outlines\":[{\"id\":\"o1\",\"type\":\"slide\",\"title\":\"Synthetic outline\"}]}"}})
}

fn worker(request: &Value) -> Value {
    let mut frame = serde_json::to_vec(request).unwrap();
    frame.push(b'\n');
    json!({"schema":"archeaxis.openmaic-outline-replay-result/v1","status":"CANDIDATE","reason":null,
    "input":request,"input_sha256":hex::encode(Sha256::digest(&frame)),
    "upstream_generation":"0.3.28","upstream_entry":"generateSceneOutlinesFromRequirements",
    "response_origin":"SYNTHETIC_REPLAY","response_origin_verification":"CALLER_DECLARED_UNVERIFIED",
    "model_call":"NOT_INVOKED","network_performed":false,"core_task":"NOT_CONNECTED",
    "canonical_bindings_verified":false,"human_review_required":true,"active_content_executed":false,
    "data":{"languageDirective":"Respond in Simplified Chinese.","courseTitle":"Synthetic course",
        "outlines":[
            {"id":"o1","type":"slide","title":"SYNTHETIC_OUTLINE_TITLE",
             "description":"SYNTHETIC_OUTLINE_DESCRIPTION","keyPoints":["SYNTHETIC_KEY_POINT"],"order":1},
            {"id":"o2","type":"quiz","title":"SYNTHETIC_QUIZ_TITLE",
             "description":"","keyPoints":[],"order":2}
        ]}})
}

fn pending(conn: &mut Connection, id: &str, request: &Value) -> OpenMaicOutlinePending {
    match openmaic_outline::prepare_openmaic_outline(conn, id, request).unwrap() {
        OpenMaicOutlinePreparation::Pending(value) => value,
        OpenMaicOutlinePreparation::Existing(_) => panic!("expected a fresh request"),
    }
}

fn commit(conn: &mut Connection, id: &str, request: &Value) -> Value {
    let ticket = pending(conn, id, request);
    openmaic_outline::commit_openmaic_outline(conn, id, request, &ticket, &worker(request)).unwrap()
}

fn document_count(conn: &Connection) -> i64 {
    conn.query_row("SELECT count(*) FROM documents", [], |row| row.get(0))
        .unwrap()
}

#[test]
fn a_candidate_is_persisted_once_and_read_back_after_restart_without_a_rerun() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let request = request();
    let first = commit(&mut conn, "client_1", &request);
    let saved = &first["document"]["editor_json"]["attrs"][NAMESPACE];
    let stored_frame = saved["request_frame"].as_str().unwrap();
    assert_eq!(
        serde_json::from_str::<Value>(stored_frame).unwrap(),
        request
    );
    assert!(stored_frame.ends_with('\n'));
    assert_eq!(
        saved["input_sha256"],
        hex::encode(Sha256::digest(stored_frame.as_bytes()))
    );
    assert_eq!(saved["worker_document"], worker(&request));
    assert!(saved.to_string().contains("SYNTHETIC_OUTLINE_DESCRIPTION"));
    assert!(saved.to_string().contains("SYNTHETIC_KEY_POINT"));
    assert_eq!(saved["response_origin"], "CALLER_DECLARED_UNVERIFIED");
    assert_eq!(saved["model_call"], "NOT_INVOKED");
    assert_eq!(saved["human_review_required"], true);
    assert_eq!(saved["active_content_executed"], false);
    assert_eq!(saved["rendering_authorized"], false);
    assert_eq!(saved["provider"], "openmaic");
    assert_eq!(saved["provider_version"], "1.3.0");
    assert_eq!(saved["generation_version"], "0.3.28");
    assert_eq!(
        saved["outlines"],
        json!([
            {"id":"o1","type":"slide","title":"SYNTHETIC_OUTLINE_TITLE","order":1,"key_points_count":1},
            {"id":"o2","type":"quiz","title":"SYNTHETIC_QUIZ_TITLE","order":2,"key_points_count":0}
        ])
    );
    assert_eq!(first["outline_count"], 2);
    assert_eq!(first["candidate_document_status"], "current");
    assert_eq!(
        first["document"]["document_id"],
        openmaic_outline::openmaic_outline_document_id("client_1")
    );
    // A retry reads the same candidate and never runs another worker.
    let before = conn.total_changes();
    let existing =
        openmaic_outline::prepare_openmaic_outline(&mut conn, "client_1", &request).unwrap();
    match existing {
        OpenMaicOutlinePreparation::Existing(receipt) => assert_eq!(receipt, first),
        _ => panic!("the committed candidate must be found before a worker"),
    }
    assert_eq!(conn.total_changes(), before, "retry must not write");

    let document_id = first["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    drop(conn);
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    assert_eq!(
        document::read(&conn, &document_id, Some(1)).unwrap(),
        first["document"]
    );
    assert!(matches!(
        openmaic_outline::prepare_openmaic_outline(&mut conn, "client_1", &request).unwrap(),
        OpenMaicOutlinePreparation::Existing(_)
    ));
    assert_eq!(document_count(&conn), 1);
}

#[test]
fn changed_content_under_the_same_create_request_id_conflicts() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let request = request();
    let ticket = pending(&mut conn, "client_2", &request);
    openmaic_outline::commit_openmaic_outline(
        &mut conn,
        "client_2",
        &request,
        &ticket,
        &worker(&request),
    )
    .unwrap();
    let mut other = request.clone();
    other["requirement"] = json!("DIFFERENT requirement");
    assert!(openmaic_outline::prepare_openmaic_outline(&mut conn, "client_2", &other).is_err());
    assert!(
        openmaic_outline::commit_openmaic_outline(
            &mut conn,
            "client_2",
            &other,
            &ticket,
            &worker(&other)
        )
        .is_err()
    );
    assert_eq!(document_count(&conn), 1);
}

#[test]
fn request_schema_and_shape_are_refused_before_a_worker() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let base = request();
    let mut cases: Vec<(&str, Value)> = Vec::new();
    let mut future = base.clone();
    future["schema"] = json!("archeaxis.openmaic-outline-replay/v2");
    cases.push(("version", future));
    let mut extra = base.clone();
    extra["attempt"] = json!(1);
    cases.push(("extra", extra));
    let mut missing = base.clone();
    missing.as_object_mut().unwrap().remove("source_text");
    cases.push(("missing", missing));
    let mut identity = base.clone();
    identity["request_id"] = json!("not a token");
    cases.push(("id", identity));
    let mut empty = base.clone();
    empty["requirement"] = json!("   ");
    cases.push(("empty requirement", empty));
    let mut long = base.clone();
    long["requirement"] = json!("x".repeat(8_001));
    cases.push(("long requirement", long));
    let mut source = base.clone();
    source["source_text"] = json!("x".repeat(50_001));
    cases.push(("long source", source));
    let mut reply = base.clone();
    reply["reply"] = json!({"kind":"synthetic_response","value":"x","extra":true});
    cases.push(("reply", reply));
    for (name, request) in cases {
        assert!(
            openmaic_outline::openmaic_outline_refusal(&request).is_some(),
            "{name}"
        );
        assert!(
            openmaic_outline::prepare_openmaic_outline(&mut conn, "client_3", &request).is_err(),
            "{name}"
        );
    }
    let refusal = openmaic_outline::openmaic_outline_refusal(&json!({})).unwrap();
    assert_eq!(refusal["reason"], "UNSUPPORTED_REQUEST_VERSION");
    assert_eq!(
        refusal["supported"],
        json!(["archeaxis.openmaic-outline-replay/v1"])
    );
    let refusal = openmaic_outline::openmaic_outline_refusal(&base);
    assert_eq!(refusal, None);
    assert_eq!(document_count(&conn), 0);
}

#[test]
fn invalid_worker_replies_never_create_a_candidate() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let request = request();
    let ticket = pending(&mut conn, "client_4", &request);
    assert!(
        openmaic_outline::commit_openmaic_outline(
            &mut conn,
            "different_client",
            &request,
            &ticket,
            &worker(&request)
        )
        .is_err(),
        "admission must bind the create ID"
    );
    for change in [
        "schema",
        "status",
        "digest",
        "input",
        "model",
        "network",
        "origin",
        "outlines",
        "type",
        "title",
        "key_points",
    ] {
        let mut response = worker(&request);
        match change {
            "schema" => response["schema"] = json!("archeaxis.openmaic-outline-replay-result/v2"),
            "status" => response["status"] = json!("UPSTREAM_FAILURE"),
            "digest" => response["input_sha256"] = json!("0".repeat(64)),
            "input" => response["input"]["requirement"] = json!("changed"),
            "model" => response["model_call"] = json!("INVOKED"),
            "network" => response["network_performed"] = json!(true),
            "origin" => response["response_origin_verification"] = json!("VERIFIED"),
            "outlines" => response["data"]["outlines"] = json!([]),
            "type" => response["data"]["outlines"][0]["type"] = json!("interactive"),
            "title" => response["data"]["outlines"][0]["title"] = json!("x".repeat(241)),
            _ => response["data"]["outlines"][0]["keyPoints"] = json!(["x".repeat(2_001)]),
        }
        assert!(
            openmaic_outline::commit_openmaic_outline(
                &mut conn, "client_4", &request, &ticket, &response
            )
            .is_err(),
            "{change}"
        );
    }
    assert_eq!(document_count(&conn), 0);
}

#[test]
fn a_disabled_capability_refuses_the_commit() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let request = request();
    let ticket = pending(&mut conn, "client_5", &request);
    capability_settings::set_enabled(&conn, openmaic_outline::OPENMAIC_OUTLINE_CAPABILITY, false)
        .unwrap();
    assert!(
        openmaic_outline::commit_openmaic_outline(
            &mut conn,
            "client_5",
            &request,
            &ticket,
            &worker(&request)
        )
        .is_err()
    );
    assert_eq!(document_count(&conn), 0);
}
