//! Synthetic Core Document persistence for inert OpenMAIC scene candidates.
//! These tests do not start Node, call a model, or qualify an installed app.
use archeaxis_domain::{
    course::{self, OpenMaicPending, OpenMaicPreparation},
    document,
};
use archeaxis_store_sqlite::{authorization_fence, capability_settings, init_workspace};
use rusqlite::Connection;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

const NAMESPACE: &str = "archeaxis_openmaic_scene_candidate";

fn editor(text: &str) -> Value {
    json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":text}]}]})
}

fn material(conn: &mut Connection) -> Value {
    document::create_optional(
        conn,
        None,
        None,
        "Synthetic material",
        editor("Synthetic source"),
    )
    .unwrap()
}

fn request(material: &Value, kind: &str) -> Value {
    let content = if kind == "slide" {
        json!({"elements":[{"id":"e1","type":"text","content":"SYNTHETIC slide"}],
            "background":{"type":"solid","color":"#ffffff"},
            "remark":"SYNTHETIC original lecture note","extra":"retained input"})
    } else {
        json!({"questions":[{"id":"q1","question":"SYNTHETIC question", "answer":"SYNTHETIC answer"}]})
    };
    json!({"schema":"archeaxis.openmaic-scene-build/v1", "request_id":"req_1", "attempt":1,
        "source":{"document_id":material["document_id"],"version":material["version"],"content_sha256":material["content_sha256"]},
        "stage_id":"stage_1","scene_id":"scene_1",
        "outline":{"id":"outline_1","type":kind,"title":"Synthetic course", "order":0,
            "description":"SYNTHETIC original description", "keyPoints":["SYNTHETIC original point"]},
        "content":content,"actions":[]})
}

fn result(request: &Value, random_canvas_id: &str) -> Value {
    let mut input = serde_json::to_vec(request).unwrap();
    input.push(b'\n');
    let content = if request["outline"]["type"] == "slide" {
        json!({"type":"slide","canvas":{"id":random_canvas_id,"elements":request["content"]["elements"],
            "background":request["content"]["background"]}})
    } else {
        json!({"type":"quiz","questions":request["content"]["questions"]})
    };
    json!({"schema":"archeaxis.openmaic-scene-build-result/v1", "status":"CANDIDATE",
        "request_id":request["request_id"],"attempt":request["attempt"],
        "input_sha256":hex::encode(Sha256::digest(&input)),"source":request["source"],
        "source_binding":"client_declared_unverified","provider":"openmaic","provider_version":"1.3.0",
        "generation_version":"0.3.28","authority_effect":"candidate_only","model_call":"NOT_INVOKED",
        "canonical_bindings_verified":false,"human_review_required":true,"active_content_executed":false,
        "rendering_authorized":false,"retry_bytes_stable":false,
        "scene":{"id":request["scene_id"],"stageId":request["stage_id"],"outlineId":request["outline"]["id"],
            "type":request["outline"]["type"],"title":request["outline"]["title"],"order":request["outline"]["order"],
            "content":content,"actions":request["actions"],"createdAt":10,"updatedAt":10}})
}

fn pending(conn: &mut Connection, id: &str, request: &Value) -> OpenMaicPending {
    match course::prepare_openmaic_scene(conn, id, request).unwrap() {
        OpenMaicPreparation::Pending(value) => value,
        OpenMaicPreparation::Existing(_) => panic!("expected a fresh request"),
    }
}

#[test]
fn slide_preserves_complete_input_and_first_scene_across_retry_and_restart() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let source = material(&mut conn);
    let request = request(&source, "slide");
    let ticket = pending(&mut conn, "client_1", &request);
    let first_worker = result(&request, "random_canvas_1");
    let first =
        course::commit_openmaic_scene(&mut conn, "client_1", &request, &ticket, &first_worker)
            .unwrap();
    let saved = &first["document"]["editor_json"]["attrs"][NAMESPACE];
    let stored_frame = saved["request_frame"].as_str().unwrap();
    assert_eq!(
        serde_json::from_str::<Value>(stored_frame).unwrap(),
        request
    );
    assert!(stored_frame.ends_with('\n'));
    assert_eq!(saved["worker_document"], first_worker);
    assert!(
        saved
            .to_string()
            .contains("SYNTHETIC original lecture note")
    );
    assert!(saved.to_string().contains("SYNTHETIC original description"));
    assert!(saved.to_string().contains("SYNTHETIC original point"));
    assert_eq!(first["document"]["source_id"], Value::Null);
    assert_eq!(first["candidate_document_status"], "current");
    assert_eq!(first["source_snapshot_status"], "current");
    assert_eq!(saved["source_derivation"], "client_declared_unverified");
    assert_eq!(saved["rendering_authorized"], false);
    match course::prepare_openmaic_scene(&mut conn, "client_1", &request).unwrap() {
        OpenMaicPreparation::Existing(value) => assert_eq!(value, first),
        _ => panic!("same request must be found before calling the worker"),
    }
    // A concurrent second worker may have made different random IDs. It must
    // return the first Document instead of appending or replacing it.
    let second = course::commit_openmaic_scene(
        &mut conn,
        "client_1",
        &request,
        &ticket,
        &result(&request, "random_canvas_2"),
    )
    .unwrap();
    assert_eq!(second, first);
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
        course::prepare_openmaic_scene(&mut conn, "client_1", &request).unwrap(),
        OpenMaicPreparation::Existing(_)
    ));
}

#[test]
fn quiz_answers_are_stored_but_a_different_request_cannot_reuse_the_id() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let source = material(&mut conn);
    let request = request(&source, "quiz");
    let ticket = pending(&mut conn, "client_2", &request);
    let stored = course::commit_openmaic_scene(
        &mut conn,
        "client_2",
        &request,
        &ticket,
        &result(&request, "unused"),
    )
    .unwrap();
    assert!(stored.to_string().contains("SYNTHETIC answer"));
    let mut other = request.clone();
    other["content"]["questions"][0]["answer"] = json!("DIFFERENT");
    assert!(course::prepare_openmaic_scene(&mut conn, "client_2", &other).is_err());
    assert!(
        course::commit_openmaic_scene(
            &mut conn,
            "client_2",
            &other,
            &ticket,
            &result(&other, "unused")
        )
        .is_err()
    );
    let count: i64 = conn
        .query_row("SELECT count(*) FROM documents", [], |row| row.get(0))
        .unwrap();
    assert_eq!(count, 2); // source and exactly one candidate
}

#[test]
fn changed_material_restore_epoch_or_capability_prevents_new_commit() {
    for change in ["material", "restore", "capability"] {
        let dir = tempfile::tempdir().unwrap();
        let mut conn =
            init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
        let source = material(&mut conn);
        let request = request(&source, "slide");
        let ticket = pending(&mut conn, "client_3", &request);
        match change {
            "material" => {
                document::save(
                    &mut conn,
                    source["document_id"].as_str().unwrap(),
                    1,
                    editor("changed"),
                )
                .unwrap();
            }
            "restore" => {
                let tx = conn.transaction().unwrap();
                authorization_fence::install_after_restore(&tx).unwrap();
                tx.commit().unwrap();
            }
            _ => capability_settings::set_enabled(&conn, "course.openmaic.scene-build", false)
                .unwrap(),
        }
        assert!(
            course::commit_openmaic_scene(
                &mut conn,
                "client_3",
                &request,
                &ticket,
                &result(&request, "canvas")
            )
            .is_err(),
            "{change}"
        );
        let count: i64 = conn
            .query_row("SELECT count(*) FROM documents", [], |row| row.get(0))
            .unwrap();
        assert_eq!(count, 1);
    }
}

#[test]
fn invalid_worker_receipt_never_creates_a_candidate() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let source = material(&mut conn);
    let request = request(&source, "slide");
    let ticket = pending(&mut conn, "client_4", &request);
    assert!(
        course::commit_openmaic_scene(
            &mut conn,
            "different_client",
            &request,
            &ticket,
            &result(&request, "canvas")
        )
        .is_err(),
        "admission must bind the create ID"
    );
    for change in ["digest", "source", "candidate", "scene", "authority"] {
        let mut worker = result(&request, "canvas");
        match change {
            "digest" => worker["input_sha256"] = json!("0".repeat(64)),
            "source" => worker["source"]["version"] = json!(99),
            "candidate" => worker["status"] = json!("UPSTREAM_NULL"),
            "scene" => worker["scene"]["content"]["canvas"]["elements"] = json!([]),
            _ => worker["rendering_authorized"] = json!(true),
        }
        assert!(
            course::commit_openmaic_scene(&mut conn, "client_4", &request, &ticket, &worker)
                .is_err(),
            "{change}"
        );
    }
    let count: i64 = conn
        .query_row("SELECT count(*) FROM documents", [], |row| row.get(0))
        .unwrap();
    assert_eq!(count, 1);
}

#[test]
fn oversized_or_unsupported_request_is_rejected_before_worker() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let source = material(&mut conn);
    let mut oversized = request(&source, "slide");
    oversized["content"]["remark"] = json!("x".repeat(256_000));
    assert!(course::prepare_openmaic_scene(&mut conn, "client_5", &oversized).is_err());
    let mut unsupported = request(&source, "slide");
    unsupported["outline"]["type"] = json!("interactive");
    assert!(course::prepare_openmaic_scene(&mut conn, "client_5", &unsupported).is_err());
}

#[test]
fn retry_reports_both_current_historical_and_unavailable_without_replacing_v1() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    assert!(
        archeaxis_domain::ui_state::existing_workspace_id(&conn)
            .unwrap()
            .is_none()
    );
    let source = material(&mut conn);
    let request = request(&source, "slide");
    let ticket = pending(&mut conn, "client_status", &request);
    let workspace = archeaxis_domain::ui_state::existing_workspace_id(&conn)
        .unwrap()
        .unwrap();
    let first = course::commit_openmaic_scene(
        &mut conn,
        "client_status",
        &request,
        &ticket,
        &result(&request, "canvas_status"),
    )
    .unwrap();
    let candidate_id = first["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    let source_id = source["document_id"].as_str().unwrap().to_owned();
    let before = conn.total_changes();
    match course::prepare_openmaic_scene(&mut conn, "client_status", &request).unwrap() {
        OpenMaicPreparation::Existing(receipt) => assert_eq!(receipt, first),
        _ => panic!("retry must read existing candidate"),
    }
    assert_eq!(
        conn.total_changes(),
        before,
        "existing retry must not write another identity"
    );
    assert_eq!(
        archeaxis_domain::ui_state::existing_workspace_id(&conn)
            .unwrap()
            .unwrap(),
        workspace
    );

    document::save(&mut conn, &candidate_id, 1, editor("later candidate edit")).unwrap();
    document::save(&mut conn, &source_id, 1, editor("later material edit")).unwrap();
    let historical =
        match course::prepare_openmaic_scene(&mut conn, "client_status", &request).unwrap() {
            OpenMaicPreparation::Existing(receipt) => receipt,
            _ => panic!("v1 remains the idempotent candidate"),
        };
    assert_eq!(historical["candidate_document_status"], "historical");
    assert_eq!(historical["source_snapshot_status"], "historical");
    assert_eq!(historical["document"], first["document"]);
    assert_eq!(historical["document"]["version"], 1);

    // A failed integrity recheck is unavailable, not evidence of a valid
    // current or historical snapshot. Only synthetic fixture rows are changed.
    conn.execute(
        "UPDATE document_versions SET content_sha256='corrupt' WHERE document_id=?1 AND version=2",
        [&candidate_id],
    )
    .unwrap();
    conn.execute(
        "UPDATE document_versions SET content_sha256='corrupt' WHERE document_id=?1 AND version=2",
        [&source_id],
    )
    .unwrap();
    let unavailable =
        match course::prepare_openmaic_scene(&mut conn, "client_status", &request).unwrap() {
            OpenMaicPreparation::Existing(receipt) => receipt,
            _ => panic!("v1 remains the idempotent candidate"),
        };
    assert_eq!(unavailable["candidate_document_status"], "unavailable");
    assert_eq!(unavailable["source_snapshot_status"], "unavailable");
    assert_eq!(unavailable["document"], first["document"]);
}

#[test]
fn pending_ticket_cannot_cross_workspaces_with_identical_material_and_epoch() {
    let dir = tempfile::tempdir().unwrap();
    let mut left = init_workspace(dir.path().join("left.sqlite").to_str().unwrap()).unwrap();
    let mut right = init_workspace(dir.path().join("right.sqlite").to_str().unwrap()).unwrap();
    let left_source = document::create_optional_with_request(
        &mut left,
        None,
        None,
        "Same",
        editor("identical synthetic source"),
        Some("same_material"),
    )
    .unwrap();
    let right_source = document::create_optional_with_request(
        &mut right,
        None,
        None,
        "Same",
        editor("identical synthetic source"),
        Some("same_material"),
    )
    .unwrap();
    assert_eq!(left_source["document_id"], right_source["document_id"]);
    assert_eq!(
        left_source["content_sha256"],
        right_source["content_sha256"]
    );
    assert_eq!(
        authorization_fence::authorization_epoch(&left).unwrap(),
        None
    );
    assert_eq!(
        authorization_fence::authorization_epoch(&right).unwrap(),
        None
    );
    let request = request(&left_source, "slide");
    let left_pending = pending(&mut left, "client_cross", &request);
    let right_pending = pending(&mut right, "client_cross", &request);
    let left_id = archeaxis_domain::ui_state::existing_workspace_id(&left)
        .unwrap()
        .unwrap();
    let right_id = archeaxis_domain::ui_state::existing_workspace_id(&right)
        .unwrap()
        .unwrap();
    assert_ne!(left_id, right_id);
    assert!(
        course::commit_openmaic_scene(
            &mut right,
            "client_cross",
            &request,
            &left_pending,
            &result(&request, "crossed")
        )
        .is_err()
    );
    let count: i64 = right
        .query_row("SELECT count(*) FROM documents", [], |row| row.get(0))
        .unwrap();
    assert_eq!(count, 1);
    assert!(
        course::commit_openmaic_scene(
            &mut right,
            "client_cross",
            &request,
            &right_pending,
            &result(&request, "owned")
        )
        .is_ok()
    );
}
