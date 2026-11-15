//! New durable question-turn admission checks. Synthetic storage only: no workers or models.
use archeaxis_domain::{
    document,
    provider_material_grant::Snapshot,
    provider_question::{self, AcceptRequest},
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

fn snapshot(value: &Value) -> Snapshot {
    Snapshot {
        document_id: value["document_id"].as_str().unwrap().into(),
        version: value["version"].as_i64().unwrap(),
        content_sha256: value["content_sha256"].as_str().unwrap().into(),
    }
}

fn material(conn: &mut Connection) -> Value {
    document::create_optional(conn, None, None, "Synthetic claim material",
        json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"SYNTHETIC claim material"}]}]})).unwrap()
}

fn grant(conn: &mut Connection, material: &Value) -> Value {
    document::create_optional(conn, None, None, "Synthetic claim grant",
        json!({"type":"doc","content":[],"attrs":{"archeaxis_provider_material_grant":{
            "schema":"archeaxis.provider-material-grant/v1","purpose":"practice","consumer":"deeptutor",
            "operations":["practice"],"material":snapshot(material),"authorization_basis":"SYNTHETIC human choice",
            "expires_at":null,"state":"granted"}}})).unwrap()
}

fn request(material: &Value, id: &str) -> QuestionTurnRequest {
    QuestionTurnRequest {
        create_request_id: id.into(),
        material: snapshot(material),
        requirement: "SYNTHETIC requirement".into(),
        model: None,
    }
}

fn pending(conn: &mut Connection, request: &QuestionTurnRequest) -> turn::QuestionTurnPending {
    match turn::prepare_question_turn(conn, request).unwrap() {
        QuestionTurnPreparation::Pending(pending) => pending,
        QuestionTurnPreparation::Existing(_) => panic!("expected fresh admission"),
    }
}

fn generation(pending: &turn::QuestionTurnPending) -> QuestionTurnGeneration {
    let frame: Value = serde_json::from_slice(pending.capture_frame()).unwrap();
    let capture = json!({"schema":turn::WORKER_SCHEMA,"status":"CAPTURED","mode":"capture",
        "request_id":frame["request_id"],"prompt_sha256":digest(b"synthetic prompt"),
        "origin":"CALLER_SUPPLIED_UNVERIFIED","model_call":"NOT_INVOKED","upstream_agentic_loop":"NOT_INVOKED",
        "core_authorization":"NOT_ESTABLISHED","privacy_filter":"NOT_APPLIED","original_input_preserved":false,
        "loss_receipt":"NOT_GENERATED","messages":[{"role":"system","content":"synthetic system"},{"role":"user","content":"synthetic prompt"}]});
    let content = "synthetic model question";
    let model = json!({"schema":"archeaxis.openmaic-outline-model-reply/v1","status":"REPLY","reason":null,
        "content":content,"content_sha256":digest(content.as_bytes()),"content_bytes":content.len(),
        "model":"synthetic-model","requested_model":"synthetic-model","observed_model":"synthetic-model",
        "finish_reason":"stop","usage":null,"model_call":"INVOKED","network_performed":true,
        "network_scope":"LOOPBACK_LOCAL_MODEL_ONLY","model_output_verification":"UNREVIEWED_LOCAL_MODEL_TEXT",
        "persisted":false,"core_task":"NOT_CONNECTED","human_review_required":true});
    let replay = json!({"schema":turn::WORKER_SCHEMA,"status":"CANDIDATE","mode":"replay",
        "request_id":frame["request_id"],"prompt_sha256":capture["prompt_sha256"],"model_call":"NOT_INVOKED",
        "origin":"CALLER_SUPPLIED_UNVERIFIED","core_authorization":"NOT_ESTABLISHED","answer_correctness":"NOT_VERIFIED",
        "privacy_filter":"NOT_APPLIED","question":{"question_id":pending.question_id(),"question":"Synthetic question?",
            "question_type":"choice","options":{"A":"one","B":"two","C":"three","D":"four"}}});
    QuestionTurnGeneration {
        capture_document: capture,
        model_reply: model,
        replay_document: replay,
    }
}

fn workspace() -> (tempfile::TempDir, Connection, Value) {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = archeaxis_store_sqlite::init_workspace(
        dir.path().join("workspace.sqlite").to_str().unwrap(),
    )
    .unwrap();
    let selected = material(&mut conn);
    grant(&mut conn, &selected);
    (dir, conn, selected)
}

fn claim_key(request: &QuestionTurnRequest) -> String {
    format!(
        "deeptutor_question_turn_claim_{}",
        digest(request.create_request_id.as_bytes())
    )
}

fn read_claim(conn: &Connection, request: &QuestionTurnRequest) -> Value {
    let raw: String = conn
        .query_row(
            "SELECT value FROM workspace_meta WHERE key=?1",
            [claim_key(request)],
            |r| r.get(0),
        )
        .unwrap();
    assert!(raw.len() <= 4096);
    assert!(
        !raw.contains("SYNTHETIC"),
        "claims contain identities and digests, not material or prompts"
    );
    serde_json::from_str(&raw).unwrap()
}

#[test]
fn question_turn_claim_second_admission_never_receives_another_dispatch_ticket() {
    let (_dir, mut conn, selected) = workspace();
    let request = request(&selected, "claim_parallel");
    let _first = pending(&mut conn, &request);
    let before = conn.total_changes();
    assert!(
        turn::prepare_question_turn(&mut conn, &request).is_err(),
        "unresolved admission must not dispatch twice"
    );
    assert_eq!(conn.total_changes(), before);
}

#[test]
fn question_turn_claim_reopened_unfinished_request_is_not_replayed() {
    let (dir, mut conn, selected) = workspace();
    let request = request(&selected, "claim_restart");
    let _lost = pending(&mut conn, &request);
    drop(conn);
    let mut reopened = archeaxis_store_sqlite::init_workspace(
        dir.path().join("workspace.sqlite").to_str().unwrap(),
    )
    .unwrap();
    assert!(
        turn::prepare_question_turn(&mut reopened, &request).is_err(),
        "process disappearance is an unknown outcome"
    );
}

#[test]
fn question_turn_claim_changed_request_cannot_reuse_unfinished_identity() {
    let (_dir, mut conn, selected) = workspace();
    let mut request = request(&selected, "claim_changed");
    let _first = pending(&mut conn, &request);
    request.requirement = "changed requirement".into();
    assert!(turn::prepare_question_turn(&mut conn, &request).is_err());
}

#[test]
fn question_turn_claim_replacement_grant_cannot_authorize_an_old_result() {
    let (_dir, mut conn, selected) = workspace();
    let request = request(&selected, "claim_grant");
    let first = pending(&mut conn, &request);
    let id: String = conn.query_row("SELECT d.document_id FROM documents d JOIN document_versions v ON v.document_id=d.document_id AND v.version=d.current_version WHERE json_extract(v.editor_json,'$.attrs.archeaxis_provider_material_grant.state')='granted'", [], |r|r.get(0)).unwrap();
    let original = document::read(&conn, &id, None).unwrap();
    let mut editor = original["editor_json"].clone();
    editor["attrs"]["archeaxis_provider_material_grant"]["state"] = json!("revoked");
    document::save(
        &mut conn,
        &id,
        original["version"].as_i64().unwrap(),
        editor,
    )
    .unwrap();
    grant(&mut conn, &selected);
    assert!(
        turn::commit_question_turn(&mut conn, &request, &first, &generation(&first)).is_err(),
        "new authorization must not substitute for the admitted grant"
    );
}

#[test]
fn question_turn_claim_completed_legacy_document_remains_a_read_only_history() {
    let (_dir, mut conn, selected) = workspace();
    let request = request(&selected, "claim_legacy");
    let first = pending(&mut conn, &request);
    let completed =
        turn::commit_question_turn(&mut conn, &request, &first, &generation(&first)).unwrap();
    conn.execute(
        "DELETE FROM workspace_meta WHERE key LIKE 'deeptutor_question_turn_claim_%'",
        [],
    )
    .unwrap();
    let before = conn.total_changes();
    match turn::prepare_question_turn(&mut conn, &request).unwrap() {
        QuestionTurnPreparation::Existing(receipt) => assert_eq!(receipt, completed),
        QuestionTurnPreparation::Pending(_) => panic!("history must not dispatch"),
    }
    assert_eq!(conn.total_changes(), before);
}

#[test]
fn question_turn_claim_restored_grant_does_not_hide_a_new_explicit_authorization() {
    let (_dir, mut conn, selected) = workspace();
    let editor: String = conn.query_row("SELECT v.editor_json FROM documents d JOIN document_versions v ON v.document_id=d.document_id AND v.version=d.current_version WHERE json_extract(v.editor_json,'$.attrs.archeaxis_provider_material_grant.state')='granted'", [], |r|r.get(0)).unwrap();
    let tx = conn.transaction().unwrap();
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
    tx.commit().unwrap();
    // Existing random IDs are doc_<hex>, so the explicit doc_req_ ID sorts after the fenced grant.
    document::create_optional_with_request(
        &mut conn,
        None,
        None,
        "Synthetic new authorization",
        serde_json::from_str(&editor).unwrap(),
        Some("new_grant_after_restore"),
    )
    .unwrap();
    let request = request(&selected, "claim_new_grant");
    assert!(
        matches!(
            turn::prepare_question_turn(&mut conn, &request),
            Ok(QuestionTurnPreparation::Pending(_))
        ),
        "a fenced lower ID must not shadow a current explicit grant"
    );
}

#[test]
fn question_turn_claim_malformed_persisted_barrier_fails_closed() {
    let (_dir, mut conn, selected) = workspace();
    let request = request(&selected, "claim_corrupt");
    let key = format!(
        "deeptutor_question_turn_claim_{}",
        digest(request.create_request_id.as_bytes())
    );
    conn.execute(
        "INSERT INTO workspace_meta(key,value) VALUES(?1,?2)",
        rusqlite::params![key, "not-json"],
    )
    .unwrap();
    assert!(turn::prepare_question_turn(&mut conn, &request).is_err());
}

#[test]
fn question_turn_claim_accept_identity_matches_utf8_frontend_vector() {
    let request = AcceptRequest {
        create_request_id: "request_1".into(),
        candidate: Snapshot {
            document_id: "doc_candidate".into(),
            version: 1,
            content_sha256: "b".repeat(64),
        },
        correct_answer: "A".into(),
        explanation: Some("人工说明\n第二行".into()),
        question_text: None,
    };
    assert_eq!(
        provider_question::accept_request_sha256(&request).unwrap(),
        "8ac653b4972266b5aad694a543709c7b51467de1c94d1d2100ca894860350e3c"
    );
}

#[test]
fn question_turn_claim_failure_is_terminal_and_repeated_finish_is_read_only() {
    for outcome in [
        turn::QuestionTurnFailure::Failed,
        turn::QuestionTurnFailure::Unknown,
    ] {
        let (_dir, mut conn, selected) = workspace();
        let request = request(&selected, "claim_terminal");
        let first = pending(&mut conn, &request);
        turn::finish_question_turn_failure(&mut conn, &first, outcome).unwrap();
        let terminal = read_claim(&conn, &request);
        let before = conn.total_changes();
        turn::finish_question_turn_failure(&mut conn, &first, turn::QuestionTurnFailure::Unknown)
            .unwrap();
        turn::finish_question_turn_failure(&mut conn, &first, turn::QuestionTurnFailure::Failed)
            .unwrap();
        assert_eq!(conn.total_changes(), before);
        assert_eq!(read_claim(&conn, &request), terminal);
        assert!(turn::prepare_question_turn(&mut conn, &request).is_err());
        assert!(
            turn::commit_question_turn(&mut conn, &request, &first, &generation(&first)).is_err()
        );
        let mut explicit_new = request.clone();
        explicit_new.create_request_id = "claim_explicit_new".into();
        let _new = pending(&mut conn, &explicit_new);
    }
}

#[test]
fn question_turn_claim_completed_result_survives_late_unknown_callback() {
    let (_dir, mut conn, selected) = workspace();
    let request = request(&selected, "claim_completed");
    let first = pending(&mut conn, &request);
    let receipt =
        turn::commit_question_turn(&mut conn, &request, &first, &generation(&first)).unwrap();
    let completed = read_claim(&conn, &request);
    assert_eq!(completed["state"], "COMPLETED");
    assert_eq!(completed["result"], json!(snapshot(&receipt["document"])));
    let before = conn.total_changes();
    turn::finish_question_turn_failure(&mut conn, &first, turn::QuestionTurnFailure::Unknown)
        .unwrap();
    assert_eq!(conn.total_changes(), before);
    assert_eq!(read_claim(&conn, &request), completed);
}

#[test]
fn question_turn_claim_restore_fence_rejects_late_dispatch_commit_and_failure_write() {
    let (_dir, mut conn, selected) = workspace();
    let request = request(&selected, "claim_restore");
    let first = pending(&mut conn, &request);
    let original = read_claim(&conn, &request);
    let tx = conn.transaction().unwrap();
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
    tx.commit().unwrap();
    assert!(turn::assert_question_turn_dispatch(&mut conn, &first).is_err());
    assert!(turn::commit_question_turn(&mut conn, &request, &first, &generation(&first)).is_err());
    assert!(
        turn::finish_question_turn_failure(&mut conn, &first, turn::QuestionTurnFailure::Unknown)
            .is_err()
    );
    assert_eq!(read_claim(&conn, &request), original);
}

#[test]
fn question_turn_claim_wrong_owner_token_cannot_publish_or_finish() {
    let (_dir, mut conn, selected) = workspace();
    let request = request(&selected, "claim_owner");
    let first = pending(&mut conn, &request);
    let mut changed = read_claim(&conn, &request);
    let token = if changed["owner_token"] == "a".repeat(32) {
        "b"
    } else {
        "a"
    };
    changed["owner_token"] = json!(token.repeat(32));
    conn.execute(
        "UPDATE workspace_meta SET value=?1 WHERE key=?2",
        rusqlite::params![changed.to_string(), claim_key(&request)],
    )
    .unwrap();
    assert!(turn::assert_question_turn_dispatch(&mut conn, &first).is_err());
    assert!(turn::commit_question_turn(&mut conn, &request, &first, &generation(&first)).is_err());
    assert!(
        turn::finish_question_turn_failure(&mut conn, &first, turn::QuestionTurnFailure::Unknown)
            .is_err()
    );
    assert_eq!(read_claim(&conn, &request), changed);
}

#[test]
fn question_turn_claim_failed_terminal_update_rolls_back_candidate_publication() {
    let (_dir, mut conn, selected) = workspace();
    let request = request(&selected, "claim_atomic");
    let first = pending(&mut conn, &request);
    conn.execute_batch("CREATE TRIGGER refuse_question_claim_completion BEFORE UPDATE ON workspace_meta WHEN NEW.key LIKE 'deeptutor_question_turn_claim_%' AND json_extract(NEW.value,'$.state')='COMPLETED' BEGIN SELECT RAISE(ABORT,'synthetic terminal write failure'); END;").unwrap();
    let before: i64 = conn
        .query_row("SELECT count(*) FROM documents", [], |r| r.get(0))
        .unwrap();
    assert!(turn::commit_question_turn(&mut conn, &request, &first, &generation(&first)).is_err());
    let after: i64 = conn
        .query_row("SELECT count(*) FROM documents", [], |r| r.get(0))
        .unwrap();
    assert_eq!(before, after);
    assert_eq!(read_claim(&conn, &request)["state"], "DISPATCHED");
    assert!(turn::prepare_question_turn(&mut conn, &request).is_err());
}

#[test]
fn question_turn_claim_oversized_barrier_cannot_be_treated_as_missing() {
    let (_dir, mut conn, selected) = workspace();
    let request = request(&selected, "claim_large");
    let first = pending(&mut conn, &request);
    let mut enlarged = read_claim(&conn, &request);
    enlarged["padding"] = json!("x".repeat(4096));
    conn.execute(
        "UPDATE workspace_meta SET value=?1 WHERE key=?2",
        rusqlite::params![enlarged.to_string(), claim_key(&request)],
    )
    .unwrap();
    assert!(turn::prepare_question_turn(&mut conn, &request).is_err());
    assert!(turn::assert_question_turn_dispatch(&mut conn, &first).is_err());
    assert!(
        turn::finish_question_turn_failure(&mut conn, &first, turn::QuestionTurnFailure::Unknown)
            .is_err()
    );
}

#[test]
fn question_turn_claim_scan_exhaustion_does_not_claim_no_authorization_or_write_a_barrier() {
    let (_dir, mut conn, selected) = workspace();
    for _ in 1..64 {
        grant(&mut conn, &selected);
    }
    let editor: String = conn.query_row("SELECT v.editor_json FROM documents d JOIN document_versions v ON v.document_id=d.document_id AND v.version=d.current_version WHERE json_extract(v.editor_json,'$.attrs.archeaxis_provider_material_grant.state')='granted' LIMIT 1", [], |r|r.get(0)).unwrap();
    let tx = conn.transaction().unwrap();
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
    tx.commit().unwrap();
    document::create_optional_with_request(
        &mut conn,
        None,
        None,
        "Synthetic grant beyond scan window",
        serde_json::from_str(&editor).unwrap(),
        Some("grant_beyond_window"),
    )
    .unwrap();
    let request = request(&selected, "claim_scan_limit");
    assert!(matches!(
        turn::prepare_question_turn(&mut conn, &request),
        Err(document::Error::Invalid(
            turn::QUESTION_TURN_GRANT_SCAN_EXHAUSTED
        ))
    ));
    let exists: bool = conn
        .query_row(
            "SELECT EXISTS(SELECT 1 FROM workspace_meta WHERE key=?1)",
            [claim_key(&request)],
            |r| r.get(0),
        )
        .unwrap();
    assert!(!exists);
}

#[test]
fn question_turn_claim_unencodable_worker_frame_leaves_no_durable_barrier() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = archeaxis_store_sqlite::init_workspace(
        dir.path().join("workspace.sqlite").to_str().unwrap(),
    )
    .unwrap();
    // JSON escaping expands this supported-size text beyond the worker's 256 KiB frame limit.
    let selected = document::create_optional(&mut conn, None, None, "Synthetic expanded frame",
        json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"\u{1}".repeat(80_000)}]}]})).unwrap();
    grant(&mut conn, &selected);
    let request = request(&selected, "claim_frame_limit");
    assert!(matches!(
        turn::prepare_question_turn(&mut conn, &request),
        Err(document::Error::Invalid("worker frame exceeds limit"))
    ));
    let exists: bool = conn
        .query_row(
            "SELECT EXISTS(SELECT 1 FROM workspace_meta WHERE key=?1)",
            [claim_key(&request)],
            |r| r.get(0),
        )
        .unwrap();
    assert!(!exists);
}

#[test]
fn question_turn_status_reports_no_execution_and_never_mutates_any_state() {
    let (_dir, mut conn, selected) = workspace();
    for (id, outcome, expected) in [
        ("status_dispatched", None, "DISPATCHED"),
        (
            "status_failed",
            Some(turn::QuestionTurnFailure::Failed),
            "FAILED",
        ),
        (
            "status_unknown",
            Some(turn::QuestionTurnFailure::Unknown),
            "UNKNOWN",
        ),
    ] {
        let request = request(&selected, id);
        let before = conn.total_changes();
        assert_eq!(
            turn::question_turn_status(&conn, &request).unwrap()["state"],
            "NOT_FOUND"
        );
        assert_eq!(conn.total_changes(), before);
        let ticket = pending(&mut conn, &request);
        if let Some(outcome) = outcome {
            turn::finish_question_turn_failure(&mut conn, &ticket, outcome).unwrap();
        }
        let before = conn.total_changes();
        let status = turn::question_turn_status(&conn, &request).unwrap();
        assert_eq!(status["state"], expected);
        assert_eq!(
            status["request_sha256"],
            turn::request_sha256(&request).unwrap()
        );
        assert_eq!(
            status["current_invocation"],
            json!({"worker_invoked":false,"model_invoked":false})
        );
        assert!(status["result_document_id"].is_null());
        assert!(status["result_version"].is_null());
        assert!(status["result_content_sha256"].is_null());
        assert_eq!(status.as_object().unwrap().len(), 7);
        assert_eq!(conn.total_changes(), before);
    }
}

#[test]
fn question_turn_status_recovers_legacy_completed_snapshot_after_restore() {
    let (_dir, mut conn, selected) = workspace();
    let request = request(&selected, "status_legacy");
    let ticket = pending(&mut conn, &request);
    let completed =
        turn::commit_question_turn(&mut conn, &request, &ticket, &generation(&ticket)).unwrap();
    conn.execute(
        "DELETE FROM workspace_meta WHERE key=?1",
        [claim_key(&request)],
    )
    .unwrap();
    let tx = conn.transaction().unwrap();
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
    tx.commit().unwrap();
    let before = conn.total_changes();
    let status = turn::question_turn_status(&conn, &request).unwrap();
    assert_eq!(status["state"], "COMPLETED");
    assert_eq!(
        status["result_document_id"],
        completed["document"]["document_id"]
    );
    assert_eq!(status["result_version"], 1);
    assert_eq!(
        status["result_content_sha256"],
        completed["document"]["content_sha256"]
    );
    assert_eq!(conn.total_changes(), before);
}

#[test]
fn question_turn_status_conflicting_request_is_refused_without_mutation() {
    let (_dir, mut conn, selected) = workspace();
    let mut request = request(&selected, "status_conflict");
    let _ticket = pending(&mut conn, &request);
    request.requirement.push_str(" different");
    let before = conn.total_changes();
    assert!(matches!(
        turn::question_turn_status(&conn, &request),
        Err(document::Error::Conflict(_))
    ));
    assert_eq!(conn.total_changes(), before);
}

#[test]
fn question_turn_status_corrupt_or_inconsistent_barrier_is_never_not_found() {
    for value in ["not-json".to_owned(), "x".repeat(4097)] {
        let (_dir, conn, selected) = workspace();
        let request = request(&selected, "status_bad");
        conn.execute(
            "INSERT INTO workspace_meta(key,value) VALUES(?1,?2)",
            rusqlite::params![claim_key(&request), value],
        )
        .unwrap();
        assert!(turn::question_turn_status(&conn, &request).is_err());
    }
    let (_dir, mut conn, selected) = workspace();
    let request = request(&selected, "status_missing_result");
    let _ticket = pending(&mut conn, &request);
    let mut claim = read_claim(&conn, &request);
    claim["state"] = json!("COMPLETED");
    claim["result"] = json!({"document_id":turn::question_turn_document_id(&request.create_request_id),"version":1,"content_sha256":"0".repeat(64)});
    conn.execute(
        "UPDATE workspace_meta SET value=?1 WHERE key=?2",
        rusqlite::params![claim.to_string(), claim_key(&request)],
    )
    .unwrap();
    assert!(turn::question_turn_status(&conn, &request).is_err());
}
