//! Synthetic persistence for the DeepTutor single-question candidate route.
//! These tests start no Python worker and call no model.
use archeaxis_domain::{
    document,
    provider_material_grant::Snapshot,
    provider_question_turn::{
        self as turn, QuestionTurnGeneration, QuestionTurnPreparation, QuestionTurnRequest,
    },
};
use rusqlite::Connection;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

fn digest(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn snap(value: &Value) -> Snapshot {
    Snapshot {
        document_id: value["document_id"].as_str().unwrap().into(),
        version: value["version"].as_i64().unwrap(),
        content_sha256: value["content_sha256"].as_str().unwrap().into(),
    }
}

fn material(conn: &mut Connection) -> Value {
    document::create_optional(
        conn,
        None,
        None,
        "SYNTHETIC material",
        json!({"type":"doc","content":[{"type":"paragraph",
            "content":[{"type":"text","text":"SYNTHETIC_MATERIAL_TEXT about arithmetic"}]}]}),
    )
    .unwrap()
}

fn grant(conn: &mut Connection, material: &Value, state: &str, consumer: &str) -> Value {
    document::create_optional(conn,None,None,"SYNTHETIC grant",json!({"type":"doc","content":[],"attrs":{
        "archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1",
            "purpose":"practice","consumer":consumer,"operations":["practice"],
            "material":snap(material),
            "authorization_basis":"SYNTHETIC human authorization","expires_at":null,"state":state}
    }})).unwrap()
}

fn request(material: &Value, create_request_id: &str) -> QuestionTurnRequest {
    QuestionTurnRequest {
        create_request_id: create_request_id.into(),
        material: snap(material),
        requirement: "Synthetic requirement about arithmetic".into(),
        model: None,
    }
}

fn pending(conn: &mut Connection, request: &QuestionTurnRequest) -> turn::QuestionTurnPending {
    match turn::prepare_question_turn(conn, request).unwrap() {
        QuestionTurnPreparation::Pending(value) => value,
        QuestionTurnPreparation::Existing(_) => panic!("expected a fresh request"),
    }
}

fn capture(pending: &turn::QuestionTurnPending) -> Value {
    let frame: Value =
        serde_json::from_slice(&pending.capture_frame()[..pending.capture_frame().len() - 1])
            .unwrap();
    let system = "SYNTHETIC_SYSTEM prompt";
    let user = "SYNTHETIC_USER prompt with SYNTHETIC_MATERIAL_TEXT";
    json!({"schema":"archeaxis.deeptutor-question-turn-replay/v1","status":"CAPTURED",
        "mode":"capture","request_id":frame["request_id"],
        "prompt_sha256":digest(user.as_bytes()),
        "origin":"CALLER_SUPPLIED_UNVERIFIED","model_call":"NOT_INVOKED",
        "upstream_agentic_loop":"NOT_INVOKED","upstream_method":"QuestionPipeline._quiz_one",
        "core_authorization":"NOT_ESTABLISHED","independent_mastery":"NOT_ESTABLISHED",
        "privacy_filter":"NOT_APPLIED","logging_safety":"NOT_ESTABLISHED",
        "original_input_preserved":false,"loss_receipt":"NOT_GENERATED",
        "messages":[{"role":"system","content":system},{"role":"user","content":user}]})
}

fn model_reply(content: &str) -> Value {
    json!({"schema":"archeaxis.openmaic-outline-model-reply/v1","status":"REPLY","reason":null,
        "content":content,"content_sha256":digest(content.as_bytes()),
        "content_bytes":content.as_bytes().len(),
        "model":"synthetic-local-model","requested_model":"synthetic-local-model",
        "observed_model":"synthetic-local-model","finish_reason":"stop",
        "usage":{"input_tokens":7,"output_tokens":3},
        "model_call":"INVOKED","network_performed":true,
        "network_scope":"LOOPBACK_LOCAL_MODEL_ONLY",
        "model_output_verification":"UNREVIEWED_LOCAL_MODEL_TEXT",
        "persisted":false,"core_task":"NOT_CONNECTED","human_review_required":true})
}

fn question_content() -> String {
    json!({"question_type":"choice","question":"What is 2+2?",
        "options":{"A":"3","B":"4","C":"5","D":"6"},
        "correct_answer":"B","explanation":"SYNTHETIC_EXPLANATION"})
    .to_string()
}

fn replay(pending: &turn::QuestionTurnPending, captured: &Value) -> Value {
    let frame: Value =
        serde_json::from_slice(&pending.capture_frame()[..pending.capture_frame().len() - 1])
            .unwrap();
    json!({"schema":"archeaxis.deeptutor-question-turn-replay/v1","status":"CANDIDATE",
        "mode":"replay","request_id":frame["request_id"],
        "prompt_sha256":captured["prompt_sha256"],
        "origin":"CALLER_SUPPLIED_UNVERIFIED","model_call":"NOT_INVOKED",
        "upstream_agentic_loop":"NOT_INVOKED","core_authorization":"NOT_ESTABLISHED",
        "independent_mastery":"NOT_ESTABLISHED","answer_correctness":"NOT_VERIFIED",
        "grounding":"NOT_VERIFIED","question_uniqueness":"NOT_VERIFIED",
        "privacy_filter":"NOT_APPLIED","logging_safety":"NOT_ESTABLISHED",
        "original_input_preserved":false,"loss_receipt":"NOT_GENERATED",
        "question":{"question_id":pending.question_id(),"question":"What is 2+2?",
            "question_type":"choice","options":{"A":"3","B":"4","C":"5","D":"6"}}})
}

fn generation(pending: &turn::QuestionTurnPending) -> QuestionTurnGeneration {
    let captured = capture(pending);
    let content = question_content();
    QuestionTurnGeneration {
        model_reply: model_reply(&content),
        replay_document: replay(pending, &captured),
        capture_document: captured,
    }
}

fn commit(conn: &mut Connection, request: &QuestionTurnRequest) -> Value {
    let ticket = pending(conn, request);
    turn::commit_question_turn(conn, request, &ticket, &generation(&ticket)).unwrap()
}

fn document_count(conn: &Connection) -> i64 {
    conn.query_row("SELECT count(*) FROM documents", [], |row| row.get(0))
        .unwrap()
}

#[test]
fn a_candidate_is_persisted_once_with_its_prompt_model_and_material_identity() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    let mut conn = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let selected = material(&mut conn);
    grant(&mut conn, &selected, "granted", "deeptutor");
    let request = request(&selected, "turn_1");
    let first = commit(&mut conn, &request);
    let saved = &first["document"]["editor_json"]["attrs"][turn::DOCUMENT_NAMESPACE];

    assert_eq!(saved["schema"], turn::DOCUMENT_SCHEMA);
    assert_eq!(
        saved["generation_route"],
        "deeptutor_question_turn_local_model"
    );
    assert_eq!(saved["model_call"], "INVOKED");
    assert_eq!(saved["model"], "synthetic-local-model");
    assert_eq!(
        saved["model_reply_sha256"],
        digest(question_content().as_bytes())
    );
    assert_eq!(saved["response_origin"], "LOCAL_MODEL_UNVERIFIED");
    assert_eq!(saved["human_review_required"], true);
    assert_eq!(saved["active_content_executed"], false);
    assert_eq!(saved["rendering_authorized"], false);
    assert_eq!(saved["answer_secrecy"], "not_established");
    assert_eq!(saved["material"], json!(snap(&selected)));
    assert_eq!(saved["capture_binding"]["request_id"], "turn_1");
    assert_eq!(
        saved["capture_binding"]["system_sha256"],
        digest(b"SYNTHETIC_SYSTEM prompt")
    );
    assert_eq!(first["candidate_document_status"], "current");
    assert_eq!(
        first["generation_route"],
        "deeptutor_question_turn_local_model"
    );
    assert_eq!(
        first["document"]["document_id"],
        turn::question_turn_document_id("turn_1")
    );
    // The exact frames Core sent are stored and parse back.
    let replay_frame: Value =
        serde_json::from_str(saved["replay_frame"].as_str().unwrap()).unwrap();
    assert_eq!(replay_frame["mode"], "replay");
    assert_eq!(
        replay_frame["expected_prompt_sha256"],
        saved["capture_binding"]["prompt_sha256"]
    );
    let capture_frame: Value =
        serde_json::from_str(saved["capture_frame"].as_str().unwrap()).unwrap();
    assert_eq!(capture_frame["mode"], "capture");
    assert_eq!(
        capture_frame["exploration_trace"],
        "SYNTHETIC_MATERIAL_TEXT about arithmetic"
    );

    // A retry reads the same candidate and never writes or re-runs a stage.
    let before = conn.total_changes();
    match turn::prepare_question_turn(&mut conn, &request).unwrap() {
        QuestionTurnPreparation::Existing(receipt) => {
            assert_eq!(receipt, first);
        }
        _ => panic!("the committed candidate must be found before a model call"),
    }
    assert_eq!(conn.total_changes(), before, "retry must not write");

    let document_id = first["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    drop(conn);
    let mut conn = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    assert_eq!(
        document::read(&conn, &document_id, Some(1)).unwrap(),
        first["document"]
    );
    assert!(matches!(
        turn::prepare_question_turn(&mut conn, &request).unwrap(),
        QuestionTurnPreparation::Existing(_)
    ));
    assert_eq!(document_count(&conn), 3, "material, grant and candidate");
}

#[test]
fn a_missing_or_revoked_grant_is_refused_before_any_worker() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = archeaxis_store_sqlite::init_workspace(
        dir.path().join("workspace.sqlite").to_str().unwrap(),
    )
    .unwrap();
    let selected = material(&mut conn);
    let request = request(&selected, "turn_no_grant");
    assert!(turn::prepare_question_turn(&mut conn, &request).is_err());
    assert_eq!(document_count(&conn), 1);

    grant(&mut conn, &selected, "revoked", "deeptutor");
    assert!(turn::prepare_question_turn(&mut conn, &request).is_err());

    let other = material(&mut conn);
    grant(&mut conn, &other, "granted", "deeptutor");
    assert!(
        turn::prepare_question_turn(&mut conn, &request).is_err(),
        "a grant for another material cannot authorize this one"
    );
    assert_eq!(document_count(&conn), 4);
}

#[test]
fn changed_content_under_the_same_create_request_id_conflicts() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = archeaxis_store_sqlite::init_workspace(
        dir.path().join("workspace.sqlite").to_str().unwrap(),
    )
    .unwrap();
    let selected = material(&mut conn);
    grant(&mut conn, &selected, "granted", "deeptutor");
    let base = request(&selected, "turn_conflict");
    commit(&mut conn, &base);
    let mut other = base.clone();
    other.requirement = "DIFFERENT requirement".into();
    assert!(
        turn::prepare_question_turn(&mut conn, &other).is_err(),
        "the same create ID cannot describe different content"
    );
    // A stage result assembled for another request is not admitted here.
    let separate = request(&selected, "turn_conflict_other");
    let ticket = pending(&mut conn, &separate);
    let mut wrong = generation(&ticket);
    wrong.replay_document["request_id"] = json!("turn_conflict");
    assert!(
        turn::commit_question_turn(&mut conn, &separate, &ticket, &wrong).is_err(),
        "a generation built for another request must not be admitted"
    );
    assert_eq!(document_count(&conn), 3);
}

#[test]
fn every_named_failure_stage_is_refused_before_a_document_exists() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = archeaxis_store_sqlite::init_workspace(
        dir.path().join("workspace.sqlite").to_str().unwrap(),
    )
    .unwrap();
    let selected = material(&mut conn);
    grant(&mut conn, &selected, "granted", "deeptutor");
    let request = request(&selected, "turn_failures");
    let ticket = pending(&mut conn, &request);
    let baseline = document_count(&conn);

    let mut unavailable = generation(&ticket);
    unavailable.model_reply = json!({"schema":"archeaxis.openmaic-outline-model-reply/v1",
        "status":"MODEL_UNAVAILABLE","reason":"MODEL_ENDPOINT_UNREACHABLE","content":null,
        "content_sha256":null,"model":null,"model_call":"INVOKED","network_performed":false,
        "network_scope":"LOOPBACK_LOCAL_MODEL_ONLY","persisted":false,
        "core_task":"NOT_CONNECTED","human_review_required":true});
    assert!(turn::commit_question_turn(&mut conn, &request, &ticket, &unavailable).is_err());

    let mut wrong_sha = generation(&ticket);
    wrong_sha.model_reply["content_sha256"] = json!("0".repeat(64));
    assert!(turn::commit_question_turn(&mut conn, &request, &ticket, &wrong_sha).is_err());

    for change in [
        "capture_status",
        "replay_status",
        "origin",
        "question_id",
        "options",
        "prompt",
    ] {
        let mut bad = generation(&ticket);
        match change {
            "capture_status" => bad.capture_document["status"] = json!("REJECTED"),
            "replay_status" => bad.replay_document["status"] = json!("REJECTED"),
            "origin" => bad.replay_document["origin"] = json!("VERIFIED"),
            "question_id" => bad.replay_document["question"]["question_id"] = json!("other"),
            "options" => bad.replay_document["question"]["options"] = json!({"A":"1","B":"2"}),
            _ => bad.capture_document["messages"][0]["content"] = json!(""),
        }
        assert!(
            turn::commit_question_turn(&mut conn, &request, &ticket, &bad).is_err(),
            "{change}"
        );
    }
    assert_eq!(document_count(&conn), baseline, "no partial candidate");
}

#[test]
fn a_material_that_changes_after_preparation_refuses_the_commit() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = archeaxis_store_sqlite::init_workspace(
        dir.path().join("workspace.sqlite").to_str().unwrap(),
    )
    .unwrap();
    let selected = material(&mut conn);
    grant(&mut conn, &selected, "granted", "deeptutor");
    let request = request(&selected, "turn_changed");
    let ticket = pending(&mut conn, &request);
    let mut changed = selected["editor_json"].clone();
    changed["content"][0]["content"][0]["text"] = json!("new material revision");
    document::save(
        &mut conn,
        selected["document_id"].as_str().unwrap(),
        1,
        changed,
    )
    .unwrap();
    assert!(
        turn::commit_question_turn(&mut conn, &request, &ticket, &generation(&ticket)).is_err(),
        "the granted material version must still be the current one"
    );
}
