//! Incremental explicit-cancel contracts. Synthetic SQLite only; no worker or model calls.
use archeaxis_domain::{
    document, provider_material_grant::Snapshot, provider_question_turn as turn,
};
use rusqlite::Connection;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

fn digest(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}
fn snapshot(value: &Value) -> Snapshot {
    serde_json::from_value(
        json!({"document_id":value["document_id"],"version":value["version"],
        "content_sha256":value["content_sha256"]}),
    )
    .unwrap()
}
fn fixture() -> (
    tempfile::TempDir,
    Connection,
    Value,
    Value,
    turn::QuestionTurnRequest,
) {
    let dir = tempfile::tempdir().unwrap();
    let mut conn =
        archeaxis_store_sqlite::init_workspace(dir.path().join("cancel.sqlite").to_str().unwrap())
            .unwrap();
    let material = document::create_optional(&mut conn, None, None, "Synthetic cancellation material",
        json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Synthetic arithmetic only"}]}]})).unwrap();
    let grant = grant(&mut conn, &material);
    let request = turn::QuestionTurnRequest {
        create_request_id: "explicit_cancel".into(),
        material: snapshot(&material),
        requirement: "Synthetic arithmetic question".into(),
        model: None,
    };
    (dir, conn, material, grant, request)
}
fn grant(conn: &mut Connection, material: &Value) -> Value {
    document::create_optional(conn, None, None, "Synthetic cancellation grant", json!({"type":"doc","content":[],"attrs":{
        "archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1","purpose":"practice","consumer":"deeptutor","operations":["practice"],"material":snapshot(material),"authorization_basis":"Synthetic explicit choice","expires_at":null,"state":"granted"}}})).unwrap()
}
fn admitted(
    conn: &mut Connection,
    request: &turn::QuestionTurnRequest,
) -> turn::QuestionTurnPending {
    match turn::prepare_question_turn(conn, request).unwrap() {
        turn::QuestionTurnPreparation::Pending(pending) => pending,
        _ => panic!("fresh request expected"),
    }
}
fn key(request: &turn::QuestionTurnRequest) -> String {
    format!(
        "deeptutor_question_turn_claim_{}",
        digest(request.create_request_id.as_bytes())
    )
}
fn claim(conn: &Connection, request: &turn::QuestionTurnRequest) -> Value {
    let raw: String = conn
        .query_row(
            "SELECT value FROM workspace_meta WHERE key=?1",
            [key(request)],
            |row| row.get(0),
        )
        .unwrap();
    serde_json::from_str(&raw).unwrap()
}
fn generation(pending: &turn::QuestionTurnPending) -> turn::QuestionTurnGeneration {
    let frame: Value = serde_json::from_slice(pending.capture_frame()).unwrap();
    let capture = json!({"schema":turn::WORKER_SCHEMA,"status":"CAPTURED","mode":"capture","request_id":frame["request_id"],"prompt_sha256":digest(b"synthetic prompt"),
        "origin":"CALLER_SUPPLIED_UNVERIFIED","model_call":"NOT_INVOKED","upstream_agentic_loop":"NOT_INVOKED","core_authorization":"NOT_ESTABLISHED","privacy_filter":"NOT_APPLIED","original_input_preserved":false,"loss_receipt":"NOT_GENERATED",
        "messages":[{"role":"system","content":"synthetic system"},{"role":"user","content":"synthetic prompt"}]});
    let content = "synthetic model question";
    let model = json!({"schema":"archeaxis.openmaic-outline-model-reply/v1","status":"REPLY","reason":null,"content":content,"content_sha256":digest(content.as_bytes()),"content_bytes":content.len(),
        "model":"synthetic-model","requested_model":"synthetic-model","observed_model":"synthetic-model","finish_reason":"stop","usage":null,"model_call":"INVOKED","network_performed":true,"network_scope":"LOOPBACK_LOCAL_MODEL_ONLY","model_output_verification":"UNREVIEWED_LOCAL_MODEL_TEXT","persisted":false,"core_task":"NOT_CONNECTED","human_review_required":true});
    let replay = json!({"schema":turn::WORKER_SCHEMA,"status":"CANDIDATE","mode":"replay","request_id":frame["request_id"],"prompt_sha256":capture["prompt_sha256"],"model_call":"NOT_INVOKED","origin":"CALLER_SUPPLIED_UNVERIFIED","core_authorization":"NOT_ESTABLISHED","answer_correctness":"NOT_VERIFIED","privacy_filter":"NOT_APPLIED",
        "question":{"question_id":pending.question_id(),"question":"Synthetic question?","question_type":"choice","options":{"A":"one","B":"two","C":"three","D":"four"}}});
    turn::QuestionTurnGeneration {
        capture_document: capture,
        model_reply: model,
        replay_document: replay,
    }
}
fn restore(conn: &mut Connection) {
    let tx = conn.transaction().unwrap();
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
    tx.commit().unwrap();
}

#[test]
fn explicit_cancel_missing_request_does_not_admit_or_write() {
    let (_dir, mut conn, _, _, request) = fixture();
    let before = conn.total_changes();
    let result = turn::cancel_question_turn(&mut conn, &request, None).unwrap();
    assert_eq!(result["state"], "NOT_FOUND");
    assert_eq!(result["cancel_requested"], false);
    assert_eq!(result["provider_stop_state"], "UNKNOWN");
    assert_eq!(
        result["request_sha256"],
        turn::request_sha256(&request).unwrap()
    );
    assert_eq!(
        result["current_invocation"],
        json!({"worker_invoked":false,"model_invoked":false})
    );
    assert_eq!(result.as_object().unwrap().len(), 9);
    assert_eq!(conn.total_changes(), before);
}

#[test]
fn explicit_cancel_wins_before_publication_and_unknown_is_repeatable() {
    let (_dir, mut conn, _, _, request) = fixture();
    let pending = admitted(&mut conn, &request);
    let mut expected = claim(&conn, &request);
    expected["state"] = json!("UNKNOWN");
    let result = turn::cancel_question_turn(&mut conn, &request, Some(&pending)).unwrap();
    assert_eq!(result["state"], "UNKNOWN");
    assert_eq!(result["cancel_requested"], true);
    assert_eq!(
        claim(&conn, &request),
        expected,
        "all frozen claim identities must remain unchanged"
    );
    let before = conn.total_changes();
    assert_eq!(
        turn::cancel_question_turn(&mut conn, &request, Some(&pending)).unwrap(),
        result
    );
    assert!(turn::assert_question_turn_dispatch(&mut conn, &pending).is_err());
    assert!(
        turn::commit_question_turn(&mut conn, &request, &pending, &generation(&pending)).is_err()
    );
    assert!(turn::prepare_question_turn(&mut conn, &request).is_err());
    turn::finish_question_turn_failure(&mut conn, &pending, turn::QuestionTurnFailure::Failed)
        .unwrap();
    assert_eq!(conn.total_changes(), before);
    assert!(
        document::read(
            &conn,
            &turn::question_turn_document_id(&request.create_request_id),
            None
        )
        .is_err()
    );
}

#[test]
fn explicit_cancel_uses_frozen_owner_after_grant_withdrawal_without_consuming_replacement() {
    let (_dir, mut conn, material, original, request) = fixture();
    let pending = admitted(&mut conn, &request);
    let frozen = claim(&conn, &request)["material_grant"].clone();
    let mut editor = original["editor_json"].clone();
    editor["attrs"]["archeaxis_provider_material_grant"]["state"] = json!("revoked");
    document::save(
        &mut conn,
        original["document_id"].as_str().unwrap(),
        1,
        editor,
    )
    .unwrap();
    let replacement = grant(&mut conn, &material);
    let before = conn.total_changes();
    assert_eq!(
        turn::cancel_question_turn(&mut conn, &request, Some(&pending)).unwrap()["cancel_requested"],
        true
    );
    assert_eq!(
        conn.total_changes(),
        before + 1,
        "only the existing claim state is changed"
    );
    assert_eq!(claim(&conn, &request)["material_grant"], frozen);
    assert_ne!(frozen["document_id"], replacement["document_id"]);
}

#[test]
fn explicit_cancel_conflicting_payload_or_owner_never_changes_claim() {
    let (_dir, mut conn, _, _, request) = fixture();
    let pending = admitted(&mut conn, &request);
    let original = claim(&conn, &request);
    let mut changed = request.clone();
    changed.requirement.push_str(" different");
    for expected in [None, Some(&pending)] {
        assert!(matches!(
            turn::cancel_question_turn(&mut conn, &changed, expected),
            Err(document::Error::Conflict(_))
        ));
    }
    assert_eq!(claim(&conn, &request), original);
    for field in ["owner_token", "material_grant", "material"] {
        let mut corrupted = original.clone();
        match field {
            "owner_token" => corrupted[field] = json!("f".repeat(32)),
            _ => corrupted[field]["content_sha256"] = json!("f".repeat(64)),
        }
        conn.execute(
            "UPDATE workspace_meta SET value=?1 WHERE key=?2",
            rusqlite::params![corrupted.to_string(), key(&request)],
        )
        .unwrap();
        let before = conn.total_changes();
        assert!(turn::cancel_question_turn(&mut conn, &request, Some(&pending)).is_err());
        assert_eq!(conn.total_changes(), before);
        assert_eq!(claim(&conn, &request), corrupted);
    }
}

#[test]
fn explicit_cancel_restore_and_workspace_fences_refuse_old_execution() {
    let (_dir, mut conn, _, _, request) = fixture();
    let pending = admitted(&mut conn, &request);
    restore(&mut conn);
    let before = conn.total_changes();
    assert!(turn::cancel_question_turn(&mut conn, &request, Some(&pending)).is_err());
    assert!(turn::cancel_question_turn(&mut conn, &request, None).is_err());
    assert_eq!(conn.total_changes(), before);
    let (_dir2, mut other, _, _, second) = fixture();
    let _pending2 = admitted(&mut other, &second);
    let mut corrupted = claim(&other, &second);
    corrupted["workspace_id"] = json!("different_workspace");
    other
        .execute(
            "UPDATE workspace_meta SET value=?1 WHERE key=?2",
            rusqlite::params![corrupted.to_string(), key(&second)],
        )
        .unwrap();
    let before = other.total_changes();
    assert!(turn::cancel_question_turn(&mut other, &second, None).is_err());
    assert_eq!(other.total_changes(), before);
}

#[test]
fn explicit_cancel_terminal_and_legacy_completed_results_are_read_only() {
    let (_dir, mut conn, _, _, request) = fixture();
    let pending = admitted(&mut conn, &request);
    let receipt =
        turn::commit_question_turn(&mut conn, &request, &pending, &generation(&pending)).unwrap();
    for legacy in [false, true] {
        if legacy {
            conn.execute("DELETE FROM workspace_meta WHERE key=?1", [key(&request)])
                .unwrap();
            restore(&mut conn);
        }
        let before = conn.total_changes();
        let result = turn::cancel_question_turn(&mut conn, &request, None).unwrap();
        assert_eq!(result["state"], "COMPLETED");
        assert_eq!(result["cancel_requested"], false);
        assert_eq!(
            result["result_document_id"],
            receipt["document"]["document_id"]
        );
        assert_eq!(result["result_version"], 1);
        assert_eq!(
            result["result_content_sha256"],
            receipt["document"]["content_sha256"]
        );
        assert_eq!(conn.total_changes(), before);
    }
    let (_dir2, mut failed, _, _, request2) = fixture();
    let pending2 = admitted(&mut failed, &request2);
    turn::finish_question_turn_failure(&mut failed, &pending2, turn::QuestionTurnFailure::Failed)
        .unwrap();
    let before = failed.total_changes();
    let result = turn::cancel_question_turn(&mut failed, &request2, Some(&pending2)).unwrap();
    assert_eq!(result["state"], "FAILED");
    assert_eq!(result["cancel_requested"], false);
    assert_eq!(failed.total_changes(), before);
}

#[test]
fn explicit_cancel_without_a_live_handle_still_persists_nonreplayable_unknown() {
    let (dir, mut conn, _, _, request) = fixture();
    let _lost = admitted(&mut conn, &request);
    drop(conn);
    let mut reopened =
        archeaxis_store_sqlite::init_workspace(dir.path().join("cancel.sqlite").to_str().unwrap())
            .unwrap();
    let result = turn::cancel_question_turn(&mut reopened, &request, None).unwrap();
    assert_eq!(result["state"], "UNKNOWN");
    assert_eq!(result["cancel_requested"], true);
    assert_eq!(result["provider_stop_state"], "UNKNOWN");
    assert!(turn::prepare_question_turn(&mut reopened, &request).is_err());
}

#[test]
fn explicit_cancel_corrupt_barrier_never_reports_acceptance_or_not_found() {
    for raw in ["bad-json".to_owned(), "x".repeat(4097)] {
        let (_dir, mut conn, _, _, request) = fixture();
        conn.execute(
            "INSERT INTO workspace_meta(key,value) VALUES(?1,?2)",
            rusqlite::params![key(&request), raw],
        )
        .unwrap();
        let before = conn.total_changes();
        assert!(turn::cancel_question_turn(&mut conn, &request, None).is_err());
        assert_eq!(conn.total_changes(), before);
    }
}
