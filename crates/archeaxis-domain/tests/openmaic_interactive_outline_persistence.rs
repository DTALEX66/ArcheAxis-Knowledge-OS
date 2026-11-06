//! Synthetic persistence for the local-model interactive-outline route.
//! These tests start no Node, call no model and qualify no installed app.
use archeaxis_domain::{
    document,
    openmaic_interactive_outline::{
        self, OpenMaicInteractiveOutlineGeneration, OpenMaicInteractiveOutlinePending,
        OpenMaicInteractiveOutlinePreparation,
    },
    openmaic_slide,
};
use archeaxis_store_sqlite::init_workspace;
use rusqlite::Connection;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

fn digest(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn request(create_request_id: &str) -> Value {
    json!({"schema":openmaic_interactive_outline::OPENMAIC_INTERACTIVE_OUTLINE_REQUEST_SCHEMA,
        "create_request_id":create_request_id,
        "requirement":"用本地材料准备交互课程","source_text":"SYNTHETIC source material",
        "model":null})
}

fn binding(create_request_id: &str) -> Value {
    let system = "SYNTHETIC_INTERACTIVE_SYSTEM prompt";
    let user = "SYNTHETIC_INTERACTIVE_USER prompt";
    json!({"schema":openmaic_interactive_outline::OPENMAIC_INTERACTIVE_OUTLINE_BINDING_SCHEMA,
        "request_id":create_request_id,
        "input_sha256":digest(b"unkeyed identity"),
        "templates_manifest_sha256":digest(b"templates"),
        "worker_sha256":digest(b"worker"),
        "system":system,"user":user,
        "system_sha256":digest(system.as_bytes()),"user_sha256":digest(user.as_bytes())})
}

fn data() -> Value {
    json!({"languageDirective":"使用简体中文","courseTitle":"交互课","outlines":[
        {"id":"o1","type":"interactive","title":"SYNTHETIC_INTERACTIVE_TITLE",
         "description":"SYNTHETIC_INTERACTIVE_DESCRIPTION","keyPoints":["SYNTHETIC_KEY_POINT"],
         "order":1,"widgetType":"diagram",
         "widgetOutline":{"diagramType":"flowchart","nodeCount":4}},
        {"id":"o2","type":"slide","title":"SYNTHETIC_SLIDE_TITLE","description":"",
         "keyPoints":[],"order":2}]})
}

fn reply(content: &str) -> Value {
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

fn worker(create_request_id: &str) -> Value {
    let content = data().to_string();
    json!({"schema":openmaic_interactive_outline::OPENMAIC_INTERACTIVE_OUTLINE_RESULT_SCHEMA,
        "status":"CANDIDATE","reason":null,"request_id":create_request_id,"stage":"replay",
        "response_origin":"CALLER_SUPPLIED_UNVERIFIED","model_call":"NOT_INVOKED",
        "network_performed":false,"core_task":"NOT_CONNECTED",
        "core_authorization":"NOT_ESTABLISHED","canonical_bindings_verified":false,
        "identity_scope":"UNKEYED_COMPARISON_ONLY","binding_authentication":"NOT_PROVIDED",
        "source_snapshot_authority":"CALLER_DECLARED_ONLY","persisted":false,
        "active_content_executed":false,"human_review_required":true,
        "prompt_template":"interactive-outlines","exact_json_output":true,
        "transformations":[],"input_sha256":digest(content.as_bytes()),"data":data()})
}

fn generation(create_request_id: &str) -> OpenMaicInteractiveOutlineGeneration {
    let content = data().to_string();
    OpenMaicInteractiveOutlineGeneration {
        binding: binding(create_request_id),
        model_reply: reply(&content),
        replay_document: worker(create_request_id),
    }
}

fn pending(conn: &mut Connection, id: &str) -> OpenMaicInteractiveOutlinePending {
    let request = request(id);
    assert_eq!(
        openmaic_interactive_outline::openmaic_interactive_outline_refusal(&request),
        None,
        "request must be admissible"
    );
    match openmaic_interactive_outline::prepare_openmaic_interactive_outline(conn, id, &request)
        .unwrap()
    {
        OpenMaicInteractiveOutlinePreparation::Pending(value) => value,
        OpenMaicInteractiveOutlinePreparation::Existing(_) => panic!("expected a fresh request"),
    }
}

fn document_count(conn: &Connection) -> i64 {
    conn.query_row("SELECT count(*) FROM documents", [], |row| row.get(0))
        .unwrap()
}

#[test]
fn a_generated_candidate_is_persisted_once_and_reads_back_with_its_widgets() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let pending = pending(&mut conn, "interactive_outline_1");
    let first = openmaic_interactive_outline::commit_openmaic_interactive_outline_generation(
        &mut conn,
        "interactive_outline_1",
        &request("interactive_outline_1"),
        &pending,
        &generation("interactive_outline_1"),
    )
    .unwrap();
    let stored = &first["document"]["editor_json"]["attrs"]
        [openmaic_interactive_outline::OPENMAIC_INTERACTIVE_OUTLINE_NAMESPACE];
    assert_eq!(
        stored["schema"],
        openmaic_interactive_outline::OPENMAIC_INTERACTIVE_OUTLINE_DOCUMENT_SCHEMA
    );
    assert_eq!(
        stored["generation_route"],
        "local_model_interactive_outline"
    );
    assert_eq!(stored["model_call"], "INVOKED");
    assert_eq!(stored["response_origin"], "LOCAL_MODEL_UNVERIFIED");
    assert_eq!(stored["human_review_required"], true);
    assert_eq!(stored["active_content_executed"], false);
    assert_eq!(stored["rendering_authorized"], false);
    // The capture frame keeps the prompt bytes; the binding keeps their digests.
    assert_eq!(
        stored["prompt_binding"]["system_sha256"],
        digest(b"SYNTHETIC_INTERACTIVE_SYSTEM prompt")
    );
    assert_eq!(
        stored["capture_frame"].as_str().map(str::len).is_some(),
        true
    );
    assert_eq!(stored["outlines"][0]["type"], "interactive");
    assert_eq!(first["outline_count"], 2);
    assert_eq!(first["candidate_document_status"], "current");
    // The interactive scene route reads the same document and keeps the widgets.
    let document_id = first["document"]["document_id"].as_str().unwrap();
    let selection = openmaic_slide::read_outline_candidate(&conn, document_id, 0).unwrap();
    assert_eq!(selection["outline"]["type"], "interactive");
    assert_eq!(selection["outline"]["widgetType"], "diagram");
    assert_eq!(selection["outline"]["widgetOutline"]["nodeCount"], 4);
    assert_eq!(selection["language_directive"], "使用简体中文");
    // A retry reads the same candidate and never writes.
    let before = conn.total_changes();
    assert!(matches!(
        openmaic_interactive_outline::prepare_openmaic_interactive_outline(
            &mut conn,
            "interactive_outline_1",
            &request("interactive_outline_1")
        )
        .unwrap(),
        OpenMaicInteractiveOutlinePreparation::Existing(_)
    ));
    assert_eq!(conn.total_changes(), before);
    assert_eq!(document_count(&conn), 1);
}

#[test]
fn a_receipt_that_does_not_match_the_frames_writes_nothing() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let pending = pending(&mut conn, "interactive_outline_2");
    let mut refused = generation("interactive_outline_2");
    refused.replay_document["transformations"] = json!(["UPSTREAM_RESULT_REWRITTEN"]);
    assert!(
        openmaic_interactive_outline::commit_openmaic_interactive_outline_generation(
            &mut conn,
            "interactive_outline_2",
            &request("interactive_outline_2"),
            &pending,
            &refused,
        )
        .is_err()
    );
    assert_eq!(document_count(&conn), 0);
    // An admitted shape with an unadmitted outline is refused too.
    let mut procedural = generation("interactive_outline_2");
    procedural.replay_document["data"]["outlines"][0]["widgetType"] = json!("procedural-skill");
    assert!(
        openmaic_interactive_outline::commit_openmaic_interactive_outline_generation(
            &mut conn,
            "interactive_outline_2",
            &request("interactive_outline_2"),
            &pending,
            &procedural,
        )
        .is_err()
    );
    assert_eq!(document_count(&conn), 0);
}

#[test]
fn request_schema_and_fields_are_refused_before_any_stage() {
    let base = request("interactive_outline_4");
    assert_eq!(
        openmaic_interactive_outline::openmaic_interactive_outline_refusal(&base),
        None
    );
    let mut future = base.clone();
    future["schema"] = json!("archeaxis.openmaic-interactive-outline-generate/v2");
    assert_eq!(
        openmaic_interactive_outline::openmaic_interactive_outline_refusal(&future).unwrap()["reason"],
        "UNSUPPORTED_REQUEST_VERSION"
    );
    let mut extra = base.clone();
    extra["remark"] = json!("extra");
    assert_eq!(
        openmaic_interactive_outline::openmaic_interactive_outline_refusal(&extra).unwrap()["reason"],
        "UNEXPECTED_REQUEST_FIELDS"
    );
    let mut empty = base.clone();
    empty["requirement"] = json!("  ");
    assert_eq!(
        openmaic_interactive_outline::openmaic_interactive_outline_refusal(&empty).unwrap()["reason"],
        "REQUIREMENT_OUT_OF_BOUNDS"
    );
}

#[test]
fn the_scene_route_refuses_a_quiz_outline_from_this_document() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let pending = pending(&mut conn, "interactive_outline_3");
    openmaic_interactive_outline::commit_openmaic_interactive_outline_generation(
        &mut conn,
        "interactive_outline_3",
        &request("interactive_outline_3"),
        &pending,
        &generation("interactive_outline_3"),
    )
    .unwrap();
    let source = document::create_optional(
        &mut conn,
        None,
        None,
        "synthetic material",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    let document_id = openmaic_interactive_outline::openmaic_interactive_outline_document_id(
        "interactive_outline_3",
    );
    let selection = openmaic_slide::read_outline_candidate(&conn, &document_id, 1).unwrap();
    assert_eq!(selection["outline"]["type"], "slide");
    let request = json!({"schema":openmaic_slide::OPENMAIC_SLIDE_REQUEST_SCHEMA,
        "create_request_id":"scene_1","outline_document_id":document_id,"outline_index":1,
        "source":{"document_id":source["document_id"],"version":source["version"],
            "content_sha256":source["content_sha256"]},"model":null});
    assert!(
        openmaic_slide::prepare_openmaic_slide_candidate(
            &mut conn, "scene_1", &request, &selection
        )
        .is_ok()
    );
    // Index 0 is the interactive outline, which the slide chain refuses.
    let interactive = openmaic_slide::read_outline_candidate(&conn, &document_id, 0).unwrap();
    assert!(
        openmaic_slide::prepare_openmaic_slide_candidate(
            &mut conn,
            "scene_2",
            &request,
            &interactive
        )
        .is_err()
    );
}
