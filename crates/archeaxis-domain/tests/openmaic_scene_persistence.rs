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

/// Frame bytes exactly as the domain function serializes them.
fn frame(request: &Value) -> String {
    let mut bytes = serde_json::to_vec(request).unwrap();
    bytes.push(b'\n');
    String::from_utf8(bytes).unwrap()
}

fn frame_sha(request: &Value) -> String {
    hex::encode(Sha256::digest(frame(request).as_bytes()))
}

fn commit(conn: &mut Connection, client: &str, request: &Value, canvas: &str) -> Value {
    let ticket = pending(conn, client, request);
    course::commit_openmaic_scene(conn, client, request, &ticket, &result(request, canvas)).unwrap()
}

#[test]
fn slide_candidate_reports_the_projection_loss_core_derived() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let source = material(&mut conn);
    let request = request(&source, "slide");
    let stored = commit(&mut conn, "client_loss", &request, "canvas_loss");
    let saved = &stored["document"]["editor_json"]["attrs"][NAMESPACE];
    assert_eq!(saved["schema"], "archeaxis.openmaic-scene-document/v2");
    let contract = &saved["contract"];
    assert_eq!(
        contract["contract"],
        "archeaxis.openmaic-scene-projection/v2"
    );
    // The outline description and key points are never carried into a scene, and a
    // text slide also drops its lecture note. They are listed, not silently removed.
    assert_eq!(contract["lossless"], false);
    assert_eq!(
        contract["omitted"],
        json!([
            "content.extra",
            "content.remark",
            "outline.description",
            "outline.keyPoints"
        ])
    );
    assert_eq!(stored["projection"]["status"], "RECORDED");
    assert_eq!(stored["projection"]["derived_by"], "core");
    assert_eq!(stored["projection"]["report"], *contract);
    assert_eq!(
        stored["contract_version"],
        "archeaxis.openmaic-scene-document/v2"
    );
    // The complete request is still stored byte-for-byte, so the loss is a
    // projection loss in the scene, not deletion from the candidate Document.
    let saved_frame = saved["request_frame"].as_str().unwrap();
    assert_eq!(saved_frame, frame(&request));
    assert!(saved_frame.contains("SYNTHETIC original lecture note"));
    assert!(saved_frame.contains("retained input"));
    // A retry reads the same report rather than recomputing a different one.
    match course::prepare_openmaic_scene(&mut conn, "client_loss", &request).unwrap() {
        OpenMaicPreparation::Existing(value) => assert_eq!(value, stored),
        _ => panic!("the committed candidate must be found"),
    }
}

#[test]
fn playable_slide_and_quiz_are_distinguished_from_unplayable_content() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let source = material(&mut conn);

    let mut playable = request(&source, "slide");
    playable["content"]["elements"] = json!([
        {"id":"t1","type":"text","content":"可播放文本","left":40,"top":40,
         "width":320,"height":80,"rotate":0}
    ]);
    let stored = commit(&mut conn, "client_playable", &playable, "canvas_playable");
    let render = &stored["document"]["editor_json"]["attrs"][NAMESPACE]["render"];
    assert_eq!(render["schema"], "archeaxis.openmaic-scene-render/v1");
    assert_eq!(render["playable"], true);
    assert_eq!(render["renderer"], "openmaic-canvas-text");
    assert_eq!(render["counts"]["elements"], 1);
    assert_eq!(render["unsupported"], json!([]));
    assert_eq!(stored["render"]["report"], *render);
    assert_eq!(
        stored["document"]["editor_json"]["attrs"][NAMESPACE]["rendering_authorized"],
        false
    );

    // A media element is not drawn by the text renderer. The scene is still stored,
    // but the candidate says which element cannot be played instead of dropping it.
    let mut media = request(&source, "slide");
    media["outline"]["id"] = json!("outline_media");
    media["scene_id"] = json!("scene_media");
    media["content"]["elements"] = json!([
        {"id":"t1","type":"text","content":"文本","left":0,"top":0,"width":100,"height":50,"rotate":0},
        {"id":"m1","type":"image","src":"https://example.invalid/a.png"}
    ]);
    let stored = commit(&mut conn, "client_media", &media, "canvas_media");
    let render = &stored["document"]["editor_json"]["attrs"][NAMESPACE]["render"];
    assert_eq!(render["playable"], false);
    assert_eq!(render["counts"]["elements"], 2);
    assert_eq!(render["counts"]["unsupported"], 1);
    assert_eq!(
        render["unsupported"][0]["path"],
        "content.canvas.elements[1]"
    );
    assert_eq!(
        render["unsupported"][0]["reason"],
        "only text elements are rendered"
    );

    // The slide element list is only the ids it can key: absent geometry cannot be
    // drawn, so it is reported rather than defaulted silently.
    let mut unpositioned = request(&source, "slide");
    unpositioned["outline"]["id"] = json!("outline_blank");
    unpositioned["scene_id"] = json!("scene_blank");
    let stored = commit(&mut conn, "client_blank", &unpositioned, "canvas_blank");
    let render = &stored["document"]["editor_json"]["attrs"][NAMESPACE]["render"];
    assert_eq!(render["playable"], false);
    assert_eq!(
        render["unsupported"][0]["reason"],
        "element needs bounded canvas geometry"
    );

    // A quiz without a question type or with a non-list answer cannot be scored.
    let mut quiz = request(&source, "quiz");
    quiz["outline"]["id"] = json!("outline_quiz");
    quiz["scene_id"] = json!("scene_quiz");
    let stored = commit(&mut conn, "client_quiz", &quiz, "unused");
    let render = &stored["document"]["editor_json"]["attrs"][NAMESPACE]["render"];
    assert_eq!(render["playable"], false);
    assert_eq!(render["counts"]["questions"], 1);
    assert_eq!(
        render["unsupported"][0]["reason"],
        "only single/multiple/short_answer questions are scored"
    );
}

#[test]
fn legacy_v1_candidate_reads_with_an_explicit_not_recorded_report() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let source = material(&mut conn);
    let request = request(&source, "slide");
    let worker = result(&request, "legacy_canvas");
    let attrs = json!({
        "schema":"archeaxis.openmaic-scene-document/v1",
        "create_request_id":"client_legacy",
        "input_sha256":frame_sha(&request),
        "request_frame":frame(&request),
        "worker_document":worker,
        "source_snapshot_status_at_commit":"current",
        "source_derivation":"client_declared_unverified",
        "rendering_authorized":false,
        "human_review_required":true,
    });
    let editor = json!({"type":"doc","attrs":{NAMESPACE:attrs},
        "content":[{"type":"paragraph","attrs":{"block_id":"openmaic_scene_candidate"},
            "content":[{"type":"text","text":"legacy candidate"}]}]});
    let internal = course::openmaic_internal_request_id("client_legacy");
    let seeded = document::create_optional_with_request(
        &mut conn,
        None,
        None,
        "legacy candidate",
        editor,
        Some(&internal),
    )
    .unwrap();
    assert_eq!(
        seeded["document_id"],
        course::openmaic_scene_document_id("client_legacy")
    );
    let read = match course::prepare_openmaic_scene(&mut conn, "client_legacy", &request).unwrap() {
        OpenMaicPreparation::Existing(value) => value,
        _ => panic!("a seeded v1 candidate must be readable"),
    };
    assert_eq!(
        read["contract_version"],
        "archeaxis.openmaic-scene-document/v1"
    );
    assert_eq!(read["projection"]["status"], "NOT_RECORDED");
    assert_eq!(read["render"]["status"], "NOT_RECORDED");
    assert!(read["projection"].get("report").is_none());
    assert_eq!(read["document"]["document_id"], seeded["document_id"]);
    // A v1 candidate is never rewritten in place, and a request that differs from
    // its stored frame still conflicts rather than silently upgrading the version.
    let mut changed = request.clone();
    changed["outline"]["title"] = json!("different title");
    assert!(course::prepare_openmaic_scene(&mut conn, "client_legacy", &changed).is_err());
    assert_eq!(
        document::read(&conn, seeded["document_id"].as_str().unwrap(), Some(1)).unwrap()["editor_json"],
        seeded["editor_json"]
    );
}

#[test]
fn tampered_projection_or_render_report_is_refused_on_readback() {
    for change in ["contract", "render"] {
        let dir = tempfile::tempdir().unwrap();
        let mut conn =
            init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
        let source = material(&mut conn);
        let request = request(&source, "slide");
        let stored = commit(&mut conn, "client_tamper", &request, "canvas_tamper");
        let id = stored["document"]["document_id"]
            .as_str()
            .unwrap()
            .to_owned();
        let editor = document::read(&conn, &id, Some(1)).unwrap()["editor_json"].clone();
        let mut tampered = editor.clone();
        let saved = &mut tampered["attrs"][NAMESPACE];
        if change == "contract" {
            saved["contract"]["omitted"] = json!([]);
            saved["contract"]["lossless"] = json!(true);
        } else {
            // Flip the stored verdict instead of writing a fixed `true`: a text slide is
            // already playable, so a fixed value would not actually tamper with the report.
            let playable = saved["render"]["playable"].as_bool().unwrap();
            saved["render"]["playable"] = json!(!playable);
        }
        document::save(&mut conn, &id, 1, tampered).unwrap();
        assert!(
            course::prepare_openmaic_scene(&mut conn, "client_tamper", &request).is_err(),
            "{change}"
        );
    }
}

#[test]
fn unsupported_scene_version_or_kind_is_named_before_any_worker() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let source = material(&mut conn);
    let slide = request(&source, "slide");
    assert_eq!(course::openmaic_refusal(&slide), None);
    assert_eq!(course::openmaic_refusal(&request(&source, "quiz")), None);

    let mut interactive = slide.clone();
    interactive["outline"]["type"] = json!("interactive");
    let refusal = course::openmaic_refusal(&interactive).unwrap();
    assert_eq!(refusal["reason"], "UNSUPPORTED_SCENE");
    assert_eq!(refusal["scene_type"], "interactive");
    assert_eq!(refusal["supported_scene_types"], json!(["slide", "quiz"]));

    let mut future = slide.clone();
    future["schema"] = json!("archeaxis.openmaic-scene-build/v2");
    let refusal = course::openmaic_refusal(&future).unwrap();
    assert_eq!(refusal["reason"], "UNSUPPORTED_REQUEST_VERSION");
    assert_eq!(refusal["declared"], "archeaxis.openmaic-scene-build/v2");

    let mut versioned = slide.clone();
    versioned["content"]["schemaVersion"] = json!(2);
    let refusal = course::openmaic_refusal(&versioned).unwrap();
    assert_eq!(refusal["reason"], "UNSUPPORTED_SCENE_VERSION");
    assert_eq!(refusal["declared"], 2);
    assert_eq!(refusal["supported_scene_versions"], json!([1]));

    // The same declarations are refused at the write boundary even when a caller
    // skips the naming pre-check, and none of them creates a worker ticket.
    for request in [interactive, future, versioned] {
        assert!(course::prepare_openmaic_scene(&mut conn, "client_refuse", &request).is_err());
    }
    let count: i64 = conn
        .query_row("SELECT count(*) FROM documents", [], |row| row.get(0))
        .unwrap();
    assert_eq!(count, 1);
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
