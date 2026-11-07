//! Synthetic persistence for the outline-to-interactive candidate route.
//! These tests start no Node, call no model and qualify no installed app.
use archeaxis_domain::{
    course, document,
    openmaic_interactive::{self, OpenMaicInteractiveGeneration, OpenMaicInteractivePreparation},
    openmaic_outline::{
        self, OpenMaicLocalGeneration, OpenMaicOutlineGenerationPending,
        OpenMaicOutlineGenerationPreparation,
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

const HTML: &str = "<!DOCTYPE html><html><body><p>SYNTHETIC_INTERACTIVE_HTML</p></body></html>";

fn outline_generate_request() -> Value {
    json!({"schema":"archeaxis.openmaic-outline-generate/v1","create_request_id":"outline_1",
        "requirement":"Synthetic requirement","source_text":"SYNTHETIC source material",
        "model":null})
}

fn outline_content() -> String {
    json!({"languageDirective":"Use Simplified Chinese.","courseTitle":"Synthetic course",
        "outlines":[
            {"id":"o1","type":"interactive","title":"SYNTHETIC_INTERACTIVE_TITLE",
             "description":"SYNTHETIC_INTERACTIVE_DESCRIPTION","keyPoints":["SYNTHETIC_KEY_POINT"],
             "order":0,"widgetType":"diagram",
             "widgetOutline":{"diagramType":"flowchart","nodeCount":4}},
            {"id":"o2","type":"slide","title":"SYNTHETIC_SLIDE_TITLE",
             "description":"SYNTHETIC_SLIDE_DESCRIPTION","keyPoints":[],
             "order":1}]})
    .to_string()
}

fn outline_binding() -> Value {
    let system = "SYNTHETIC_SYSTEM prompt";
    let user = "SYNTHETIC_USER prompt with SYNTHETIC source material";
    json!({"schema":"archeaxis.openmaic-outline-prompt-binding/v1","request_id":"outline_1",
        "input_sha256":digest(b"unkeyed identity"),
        "upstream_manifest_sha256":digest(b"manifest"),
        "npm_members_sha256":digest(b"members"),
        "worker_sha256":digest(b"worker"),
        "guard_sha256":digest(b"guard"),
        "system":system,"user":user,
        "system_sha256":digest(system.as_bytes()),"user_sha256":digest(user.as_bytes())})
}

fn outline_model_reply(content: &str) -> Value {
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

fn outline_worker() -> Value {
    json!({"schema":"archeaxis.openmaic-outline-prompt-result/v1","status":"CANDIDATE",
        "reason":null,"request_id":"outline_1","stage":"replay",
        "response_origin":"CALLER_SUPPLIED_UNVERIFIED","model_call":"NOT_INVOKED",
        "network_performed":false,"core_task":"NOT_CONNECTED",
        "core_authorization":"NOT_ESTABLISHED","canonical_bindings_verified":false,
        "identity_scope":"UNKEYED_COMPARISON_ONLY","binding_authentication":"NOT_PROVIDED",
        "source_snapshot_authority":"CALLER_DECLARED_ONLY","persisted":false,
        "active_content_executed":false,"human_review_required":true,
        "response_origin_verification":null,
        "data":{"languageDirective":"Use Simplified Chinese.","courseTitle":"Synthetic course",
            "outlines":[
                {"id":"o1","type":"interactive","title":"SYNTHETIC_INTERACTIVE_TITLE",
                 "description":"SYNTHETIC_INTERACTIVE_DESCRIPTION","keyPoints":["SYNTHETIC_KEY_POINT"],
                 "order":0,"widgetType":"diagram",
                 "widgetOutline":{"diagramType":"flowchart","nodeCount":4}},
                {"id":"o2","type":"slide","title":"SYNTHETIC_SLIDE_TITLE",
                 "description":"SYNTHETIC_SLIDE_DESCRIPTION","keyPoints":[],"order":1}]}})
}

/// Seed a committed outline candidate with the existing local-model writer.
fn seed_outline(conn: &mut Connection) -> String {
    let request = outline_generate_request();
    let content = outline_content();
    let pending: OpenMaicOutlineGenerationPending =
        match openmaic_outline::prepare_openmaic_outline_generation(conn, "outline_1", &request)
            .unwrap()
        {
            OpenMaicOutlineGenerationPreparation::Pending(value) => value,
            OpenMaicOutlineGenerationPreparation::Existing(_) => panic!("expected a fresh outline"),
        };
    let generation = OpenMaicLocalGeneration {
        binding: outline_binding(),
        model_reply: outline_model_reply(&content),
        replay_document: outline_worker(),
    };
    openmaic_outline::commit_openmaic_outline_generation(
        conn,
        "outline_1",
        &request,
        &pending,
        &generation,
    )
    .unwrap()["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned()
}

fn source(conn: &mut Connection) -> Value {
    document::create_optional(
        conn,
        None,
        None,
        "synthetic material",
        json!({"type":"doc","content":[]}),
    )
    .unwrap()
}

fn interactive_request(outline_document_id: &str, index: i64, source: &Value) -> Value {
    json!({"schema":openmaic_interactive::OPENMAIC_INTERACTIVE_REQUEST_SCHEMA,
        "create_request_id":"interactive_1","outline_document_id":outline_document_id,
        "outline_index":index,
        "source":{"document_id":source["document_id"],"version":source["version"],
            "content_sha256":source["content_sha256"]},
        "model":null})
}

fn prompt_document(widget: &str) -> Value {
    let system = "SYNTHETIC_INTERACTIVE_SYSTEM";
    let user = "SYNTHETIC_INTERACTIVE_USER";
    json!({"schema":openmaic_interactive::OPENMAIC_INTERACTIVE_PROMPT_RESULT_SCHEMA,
        "status":"BUILT","scope":"CALLER_SUPPLIED_UNVERIFIED",
        "operation":"UPSTREAM_INTERACTIVE_PROMPT_ONLY","widget_type":widget,
        "model_call":"NOT_INVOKED","html_output":"NOT_PRODUCED",
        "full_generation":"NOT_PERFORMED","core_authorization":"NOT_ESTABLISHED",
        "resource_availability":"NOT_VERIFIED","network_isolation":"NOT_ESTABLISHED",
        "private":{"system":system,"user":user,
            "system_sha256":digest(system.as_bytes()),"user_sha256":digest(user.as_bytes())}})
}

fn model_reply() -> Value {
    json!({"schema":"archeaxis.openmaic-outline-model-reply/v1","status":"REPLY",
        "content":HTML,"content_sha256":digest(HTML.as_bytes()),
        "content_bytes":HTML.len(),
        "model":"synthetic-local-model","observed_model":"synthetic-local-model",
        "finish_reason":"stop","usage":{"input_tokens":1,"output_tokens":1},
        "model_call":"INVOKED","network_performed":true})
}

fn normalize_document(create_request_id: &str, widget: &str) -> Value {
    use base64::Engine;
    let request_id =
        openmaic_interactive::openmaic_interactive_normalize_request_id(create_request_id);
    let output = HTML.as_bytes();
    let encoded = base64::engine::general_purpose::STANDARD.encode(output);
    json!({"schema":openmaic_interactive::OPENMAIC_INTERACTIVE_NORMALIZE_SCHEMA,
        "status":"OBSERVED_CANDIDATE","scope":"CALLER_SUPPLIED_UNVERIFIED",
        "node_version":"24.21.0","model_call":"NOT_INVOKED","rendering_authorized":false,
        "security_sanitizer":false,"resource_availability":"NOT_VERIFIED",
        "network_isolation":"NOT_ESTABLISHED","core_authorization":"NOT_ESTABLISHED",
        "external_references":"NOT_ENUMERATED",
        "script_validation":"CLASSIC_INLINE_COMPILED_NOT_EXECUTED",
        "original_preservation":"CALLER_RESPONSIBILITY",
        "request_id":request_id,"widget_type":widget,
        "extraction_strategy":"COMPLETE_DOCUMENT",
        "input_sha256":digest(HTML.as_bytes()),"input_bytes":HTML.len(),
        "extracted_sha256":digest(HTML.as_bytes()),"extracted_bytes":HTML.len(),
        "output_sha256":digest(output),"output_bytes":output.len(),
        "output_utf8_base64":encoded,
        "katex_injected":false})
}

/// What `scene-build-worker.mjs` returns for the interactive request Core builds.
fn scene_build_document(request: &Value) -> Value {
    let mut frame = serde_json::to_vec(request).unwrap();
    frame.push(b'\n');
    json!({"schema":"archeaxis.openmaic-scene-build-result/v1","status":"CANDIDATE",
        "request_id":request["request_id"],"attempt":request["attempt"],
        "input_sha256":digest(&frame),
        "source":request["source"],"source_binding":"client_declared_unverified",
        "provider":"openmaic","provider_version":"1.3.0","generation_version":"0.3.28",
        "authority_effect":"candidate_only","model_call":"NOT_INVOKED",
        "canonical_bindings_verified":false,"human_review_required":true,
        "active_content_executed":false,"rendering_authorized":false,
        "retry_bytes_stable":false,
        "scene":{"id":request["scene_id"],"stageId":request["stage_id"],
            "outlineId":request["outline"]["id"],"type":"interactive",
            "title":request["outline"]["title"],"order":request["outline"]["order"],
            "content":{"type":"interactive","url":"","html":request["content"]["html"],
                "widgetType":request["content"]["widgetType"]},
            "actions":[]}})
}

fn interactive_generation(
    create_request_id: &str,
    request: &Value,
    selection: &Value,
    widget: &str,
    scene_request: Value,
) -> OpenMaicInteractiveGeneration {
    let record = openmaic_interactive::openmaic_interactive_record(
        create_request_id,
        &openmaic_interactive::openmaic_interactive_request_sha256(request, selection),
        selection,
        &openmaic_interactive::openmaic_interactive_prompt_binding(
            &prompt_document(widget),
            widget,
        )
        .unwrap(),
        &model_reply(),
        &normalize_document(create_request_id, widget),
    );
    OpenMaicInteractiveGeneration {
        scene_request,
        record,
    }
}

fn prepare_and_commit(
    conn: &mut Connection,
    create_request_id: &str,
    request: &Value,
    selection: &Value,
    widget: &str,
    scene_request: Value,
) -> Value {
    let pending = match openmaic_interactive::prepare_openmaic_interactive_candidate(
        conn,
        create_request_id,
        request,
        selection,
    )
    .unwrap()
    {
        OpenMaicInteractivePreparation::Pending(value) => value,
        OpenMaicInteractivePreparation::Existing(_) => panic!("expected a fresh request"),
    };
    let scene_pending =
        match course::prepare_openmaic_scene(conn, create_request_id, &scene_request).unwrap() {
            course::OpenMaicPreparation::Pending(value) => value,
            course::OpenMaicPreparation::Existing(_) => panic!("expected a fresh scene"),
        };
    let worker = scene_build_document(&scene_request);
    let generation =
        interactive_generation(create_request_id, request, selection, widget, scene_request);
    openmaic_interactive::commit_openmaic_interactive_candidate(
        conn,
        create_request_id,
        request,
        &pending,
        &scene_pending,
        &worker,
        &generation,
    )
    .unwrap()
}

fn document_count(conn: &Connection) -> i64 {
    conn.query_row("SELECT count(*) FROM documents", [], |row| row.get(0))
        .unwrap()
}

#[test]
fn a_widget_outline_is_carried_and_the_prompt_uses_the_adapter_field_names() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let outline_document_id = seed_outline(&mut conn);
    let selection = openmaic_slide::read_outline_candidate(&conn, &outline_document_id, 0).unwrap();
    assert_eq!(selection["outline"]["type"], "interactive");
    assert_eq!(selection["outline"]["widgetType"], "diagram");
    assert_eq!(selection["outline"]["widgetOutline"]["nodeCount"], 4);
    let (widget, widget_outline) =
        openmaic_interactive::openmaic_interactive_widget(&selection).unwrap();
    assert_eq!(widget, "diagram");
    assert_eq!(widget_outline["diagram_type"], "flowchart");
    assert_eq!(widget_outline["node_count"], 4);
    let request = openmaic_interactive::openmaic_interactive_prompt_request(&selection).unwrap();
    assert_eq!(
        request["schema"],
        openmaic_interactive::OPENMAIC_INTERACTIVE_PROMPT_SCHEMA
    );
    assert_eq!(request["include_private"], true);
    use base64::Engine;
    let frame = base64::engine::general_purpose::STANDARD
        .decode(request["request_utf8_base64"].as_str().unwrap())
        .unwrap();
    let decoded: Value = serde_json::from_slice(&frame).unwrap();
    assert_eq!(decoded["outline"]["widget_type"], "diagram");
    assert_eq!(decoded["outline"]["widget_outline"]["node_count"], 4);
    assert_eq!(decoded["language_directive"], "Use Simplified Chinese.");
    // The slide chain refuses an interactive outline before any worker runs.
    let source = source(&mut conn);
    let slide_request = interactive_request(&outline_document_id, 0, &source);
    assert!(
        openmaic_slide::prepare_openmaic_slide_candidate(
            &mut conn,
            "interactive_1",
            &slide_request,
            &selection
        )
        .is_err()
    );
}

#[test]
fn one_interactive_outline_becomes_a_scene_candidate_with_its_chain_identity() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let outline_document_id = seed_outline(&mut conn);
    let source = source(&mut conn);
    let request = interactive_request(&outline_document_id, 0, &source);
    let selection = openmaic_slide::read_outline_candidate(&conn, &outline_document_id, 0).unwrap();
    let normalized = json!({"widgetType":"diagram","html":HTML,
        "extraction_strategy":"COMPLETE_DOCUMENT","katex_injected":false});
    let scene_request = openmaic_interactive::openmaic_interactive_scene_build_request(
        "interactive_1",
        &selection,
        &normalized,
        &request["source"],
    )
    .unwrap();
    assert_eq!(scene_request["content"]["widgetType"], "diagram");
    assert_eq!(scene_request["content"]["html"], HTML);
    let first = prepare_and_commit(
        &mut conn,
        "interactive_1",
        &request,
        &selection,
        "diagram",
        scene_request,
    );
    let stored = &first["document"]["editor_json"]["attrs"][course::OPENMAIC_SCENE_NAMESPACE]["derived_metadata"];
    assert_eq!(
        stored["schema"],
        openmaic_interactive::OPENMAIC_INTERACTIVE_RECORD_SCHEMA
    );
    assert_eq!(
        stored["generation_route"],
        "outline_interactive_local_model"
    );
    assert_eq!(stored["model_call"], "INVOKED");
    assert_eq!(stored["widget_type"], "diagram");
    assert_eq!(stored["html_execution"], "NOT_PERFORMED");
    assert_eq!(stored["response_origin"], "LOCAL_MODEL_UNVERIFIED");
    assert_eq!(stored["outline_document_id"], outline_document_id.as_str());
    assert_eq!(stored["outline_index"], 0);
    assert_eq!(stored["human_review_required"], true);
    assert_eq!(stored["active_content_executed"], false);
    assert_eq!(stored["rendering_authorized"], false);
    // The prompt text is never stored; only its declared identity is.
    assert!(stored["prompt_binding"].get("system").is_none());
    assert!(stored["prompt_binding"].get("user").is_none());
    assert_eq!(
        first["render"]["report"]["playable"],
        json!(false),
        "the stored HTML is not executed, served or authorized for rendering"
    );
    assert!(
        first["render"]["report"]["unsupported"]
            .as_array()
            .unwrap()
            .iter()
            .any(|entry| entry["path"] == "content.html")
    );
    // A repeated request reads the same candidate and writes nothing.
    let before = conn.total_changes();
    assert!(matches!(
        openmaic_interactive::prepare_openmaic_interactive_candidate(
            &mut conn,
            "interactive_1",
            &request,
            &selection
        )
        .unwrap(),
        OpenMaicInteractivePreparation::Existing(_)
    ));
    assert_eq!(conn.total_changes(), before);
}

#[test]
fn a_receipt_that_does_not_describe_the_sent_reply_is_refused_before_a_write() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let outline_document_id = seed_outline(&mut conn);
    let source = source(&mut conn);
    let request = interactive_request(&outline_document_id, 0, &source);
    let selection = openmaic_slide::read_outline_candidate(&conn, &outline_document_id, 0).unwrap();
    let pending = match openmaic_interactive::prepare_openmaic_interactive_candidate(
        &mut conn,
        "interactive_1",
        &request,
        &selection,
    )
    .unwrap()
    {
        OpenMaicInteractivePreparation::Pending(value) => value,
        OpenMaicInteractivePreparation::Existing(_) => panic!("expected a fresh request"),
    };
    let normalized = json!({"widgetType":"diagram","html":HTML,
        "extraction_strategy":"COMPLETE_DOCUMENT","katex_injected":false});
    let scene_request = openmaic_interactive::openmaic_interactive_scene_build_request(
        "interactive_1",
        &selection,
        &normalized,
        &request["source"],
    )
    .unwrap();
    let scene_pending =
        match course::prepare_openmaic_scene(&mut conn, "interactive_1", &scene_request).unwrap() {
            course::OpenMaicPreparation::Pending(value) => value,
            course::OpenMaicPreparation::Existing(_) => panic!("expected a fresh scene"),
        };
    let mut worker = scene_build_document(&scene_request);
    worker["scene"]["content"]["html"] = json!("<html>OTHER</html>");
    let generation = interactive_generation(
        "interactive_1",
        &request,
        &selection,
        "diagram",
        scene_request,
    );
    assert!(
        openmaic_interactive::commit_openmaic_interactive_candidate(
            &mut conn,
            "interactive_1",
            &request,
            &pending,
            &scene_pending,
            &worker,
            &generation,
        )
        .is_err()
    );
    assert_eq!(document_count(&conn), 2, "outline and source only");
}

#[test]
fn a_normalize_receipt_for_another_widget_or_other_bytes_is_not_admitted() {
    let request_id =
        openmaic_interactive::openmaic_interactive_normalize_request_id("interactive_1");
    let mut receipt = normalize_document("interactive_1", "diagram");
    assert!(
        openmaic_interactive::openmaic_interactive_normalized(
            &receipt,
            &request_id,
            "diagram",
            HTML
        )
        .unwrap()
        .is_some()
    );
    receipt["widget_type"] = json!("simulation");
    assert!(
        openmaic_interactive::openmaic_interactive_normalized(
            &receipt,
            &request_id,
            "diagram",
            HTML
        )
        .is_err()
    );
    let mut other = normalize_document("interactive_1", "diagram");
    other["input_sha256"] = json!(digest(b"OTHER REPLY"));
    assert!(
        openmaic_interactive::openmaic_interactive_normalized(&other, &request_id, "diagram", HTML)
            .is_err()
    );
}

#[test]
fn a_procedural_skill_outline_is_not_an_admitted_widget() {
    let selection = json!({"outline":{"id":"o1","type":"interactive",
        "title":"SYNTHETIC_INTERACTIVE_TITLE","description":"d","keyPoints":[],
        "order":0,"widgetType":"procedural-skill","widgetOutline":{"task":"x"}}});
    assert!(openmaic_interactive::openmaic_interactive_widget(&selection).is_err());
}

#[test]
fn the_widget_fields_the_donor_prompt_documents_reach_the_frame() {
    // The vendored interactive-outlines template asks the model for `challenge`
    // and `playerControls` on a game and `challengeType` on code; the scene
    // chain must carry them instead of refusing or renaming them.
    let game = openmaic_interactive::openmaic_interactive_widget(&json!({
        "outline":{"id":"o1","type":"interactive","title":"SYNTHETIC_GAME_TITLE",
            "description":"d","keyPoints":[],"order":0,"widgetType":"game",
            "widgetOutline":{"gameType":"action","challenge":"控制推力使飞船低速着陆",
                "playerControls":["thrust_slider","angle"]}}}))
    .expect("a template-conformant game outline is admitted");
    assert_eq!(game.0, "game");
    assert_eq!(game.1["game_type"], "action");
    assert_eq!(game.1["challenge"], "控制推力使飞船低速着陆");
    assert_eq!(game.1["player_controls"], json!(["thrust_slider", "angle"]));
    assert!(game.1.get("interactions").is_none());

    let code = openmaic_interactive::openmaic_interactive_widget(&json!({
        "outline":{"id":"o2","type":"interactive","title":"SYNTHETIC_CODE_TITLE",
            "description":"d","keyPoints":[],"order":0,"widgetType":"code",
            "widgetOutline":{"language":"python","challengeType":"function"}}}))
    .expect("a template-conformant code outline is admitted");
    assert_eq!(code.1["language"], "python");
    assert_eq!(code.1["challenge_type"], "function");
    assert!(code.1.get("interactions").is_none());
}
