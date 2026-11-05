//! Synthetic persistence for the outline-to-slide candidate route.
//! These tests start no Node, call no model and qualify no installed app.
use archeaxis_domain::{
    course, document,
    openmaic_outline::{
        self, OpenMaicLocalGeneration, OpenMaicOutlineGenerationPending,
        OpenMaicOutlineGenerationPreparation,
    },
    openmaic_slide::{self, OpenMaicSlideGeneration, OpenMaicSlidePreparation},
};
use archeaxis_store_sqlite::init_workspace;
use rusqlite::Connection;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

fn digest(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn outline_generate_request() -> Value {
    json!({"schema":"archeaxis.openmaic-outline-generate/v1","create_request_id":"outline_1",
        "requirement":"Synthetic requirement","source_text":"SYNTHETIC source material",
        "model":null})
}

fn outline_content() -> String {
    json!({"languageDirective":"Use Simplified Chinese.","courseTitle":"Synthetic course",
        "outlines":[
            {"id":"o1","type":"slide","title":"SYNTHETIC_SLIDE_TITLE",
             "description":"SYNTHETIC_SLIDE_DESCRIPTION","keyPoints":["SYNTHETIC_KEY_POINT"],
             "order":0},
            {"id":"o2","type":"quiz","title":"SYNTHETIC_QUIZ_TITLE","description":"",
             "keyPoints":[],"order":1}]})
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
                {"id":"o1","type":"slide","title":"SYNTHETIC_SLIDE_TITLE",
                 "description":"SYNTHETIC_SLIDE_DESCRIPTION","keyPoints":["SYNTHETIC_KEY_POINT"],
                 "order":0},
                {"id":"o2","type":"quiz","title":"SYNTHETIC_QUIZ_TITLE","description":"",
                 "keyPoints":[],"order":1}]}})
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

fn slide_request(outline_document_id: &str, index: i64, source: &Value) -> Value {
    json!({"schema":openmaic_slide::OPENMAIC_SLIDE_REQUEST_SCHEMA,
        "create_request_id":"slide_1","outline_document_id":outline_document_id,
        "outline_index":index,
        "source":{"document_id":source["document_id"],"version":source["version"],
            "content_sha256":source["content_sha256"]},
        "model":null})
}

fn prompt_binding_record() -> Value {
    json!({"schema":openmaic_slide::OPENMAIC_SLIDE_PROMPT_BINDING_SCHEMA,
        "system_sha256":digest(b"SYNTHETIC_SYSTEM"),"user_sha256":digest(b"SYNTHETIC_USER"),
        "system_bytes":16,"user_bytes":15})
}

fn model_reply() -> Value {
    json!({"schema":"archeaxis.openmaic-outline-model-reply/v1","status":"REPLY",
        "content":null,"content_sha256":digest(b"REPLY"),"content_bytes":5,
        "model":"synthetic-local-model","observed_model":"synthetic-local-model",
        "finish_reason":"stop","usage":{"input_tokens":1,"output_tokens":1},
        "model_call":"INVOKED","network_performed":true})
}

fn reply_document() -> Value {
    json!({"schema":openmaic_slide::OPENMAIC_SLIDE_REPLY_RESULT_SCHEMA,"status":"CANDIDATE",
        "reason":"EXACT_TEXT_ELEMENTS_ONLY",
        "private":{"reply":{"bytes":10,"sha256":digest(b"REPLY")},
            "normalized":{"bytes":20,"sha256":digest(b"NORMALIZED")},
            "semantic_changes":[]}})
}

fn normalize_document(request_id: &str) -> Value {
    json!({"schema":openmaic_slide::OPENMAIC_SLIDE_NORMALIZE_RESULT_SCHEMA,
        "status":"CANDIDATE","request_id":request_id,
        "input_sha256":digest(b"INPUT"),"input_bytes":5,
        "output_sha256":digest(b"OUTPUT"),"output_bytes":6,"semantic_changes":[]})
}

fn normalized_scene() -> Value {
    json!({"id":"scene_x","stageId":"stage_x","type":"slide","title":"SYNTHETIC_SLIDE_TITLE",
        "order":0,"content":{"type":"slide","canvas":{
            "id":"canvas_x","viewportSize":1000,"viewportRatio":0.5625,
            "theme":{"backgroundColor":"#ffffff","themeColors":["#5b9bd5"],
                "fontColor":"#333333","fontName":"Microsoft YaHei"},
            "elements":[{"id":"el_1","type":"text","left":60.0,"top":50.0,"width":880.0,
                "height":76.0,"rotate":0.0,"content":"SYNTHETIC_SLIDE_TEXT",
                "defaultFontName":"Microsoft YaHei","defaultColor":"#333333"}],
            "background":{"type":"solid","color":"#ffffff"}}},
        "actions":[]})
}

/// What `scene-build-worker.mjs` returns for the request Core builds.
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
            "outlineId":request["outline"]["id"],"type":"slide",
            "title":request["outline"]["title"],"order":request["outline"]["order"],
            "content":{"type":"slide","canvas":{"id":"canvas_built","viewportSize":1000,
                "viewportRatio":0.5625,
                "theme":{"backgroundColor":"#ffffff","themeColors":["#5b9bd5"],
                    "fontColor":"#333333","fontName":"Microsoft YaHei"},
                "elements":request["content"]["elements"],
                "background":request["content"]["background"]}},
            "actions":[]}})
}

fn slide_generation(
    create_request_id: &str,
    request: &Value,
    selection: &Value,
    scene_request: Value,
) -> OpenMaicSlideGeneration {
    let record = openmaic_slide::openmaic_slide_record(
        create_request_id,
        &openmaic_slide::openmaic_slide_request_sha256(request, selection),
        selection,
        &prompt_binding_record(),
        &model_reply(),
        &reply_document(),
        &normalize_document(create_request_id),
    );
    OpenMaicSlideGeneration {
        scene_request,
        record,
    }
}

fn prepare_and_commit(
    conn: &mut Connection,
    create_request_id: &str,
    request: &Value,
    selection: &Value,
    scene_request: Value,
) -> Value {
    let pending = match openmaic_slide::prepare_openmaic_slide_candidate(
        conn,
        create_request_id,
        request,
        selection,
    )
    .unwrap()
    {
        OpenMaicSlidePreparation::Pending(value) => value,
        OpenMaicSlidePreparation::Existing(_) => panic!("expected a fresh request"),
    };
    let scene_pending =
        match course::prepare_openmaic_scene(conn, create_request_id, &scene_request).unwrap() {
            course::OpenMaicPreparation::Pending(value) => value,
            course::OpenMaicPreparation::Existing(_) => panic!("expected a fresh scene"),
        };
    let worker = scene_build_document(&scene_request);
    let generation = slide_generation(create_request_id, request, selection, scene_request);
    openmaic_slide::commit_openmaic_slide_candidate(
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
fn one_slide_outline_becomes_a_scene_candidate_with_its_chain_identity() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let outline_document_id = seed_outline(&mut conn);
    let source = source(&mut conn);
    let request = slide_request(&outline_document_id, 0, &source);
    let selection = openmaic_slide::read_outline_candidate(&conn, &outline_document_id, 0).unwrap();
    assert_eq!(selection["outline"]["type"], "slide");
    assert_eq!(selection["outline"]["title"], "SYNTHETIC_SLIDE_TITLE");
    assert_eq!(selection["language_directive"], "Use Simplified Chinese.");
    let normalized = normalized_scene();
    let scene_request = openmaic_slide::openmaic_slide_scene_build_request(
        "slide_1",
        &selection,
        &normalized,
        &request["source"],
    )
    .unwrap();
    let first = prepare_and_commit(&mut conn, "slide_1", &request, &selection, scene_request);
    let stored = &first["document"]["editor_json"]["attrs"][course::OPENMAIC_SCENE_NAMESPACE]["derived_metadata"];
    assert_eq!(
        stored["schema"],
        openmaic_slide::OPENMAIC_SLIDE_RECORD_SCHEMA
    );
    assert_eq!(stored["generation_route"], "outline_slide_local_model");
    assert_eq!(stored["model_call"], "INVOKED");
    assert_eq!(stored["response_origin"], "LOCAL_MODEL_UNVERIFIED");
    assert_eq!(stored["outline_document_id"], outline_document_id.as_str());
    assert_eq!(stored["outline_index"], 0);
    assert_eq!(
        stored["prompt_binding"]["system_sha256"],
        digest(b"SYNTHETIC_SYSTEM")
    );
    assert!(stored["prompt_binding"].get("system").is_none());
    assert_eq!(stored["model_reply_sha256"], digest(b"REPLY"));
    assert_eq!(stored["human_review_required"], true);
    assert_eq!(stored["active_content_executed"], false);
    assert_eq!(stored["rendering_authorized"], false);
    // The existing scene contract is unchanged and still reports its own verdicts.
    assert_eq!(
        first["contract_version"],
        "archeaxis.openmaic-scene-document/v2"
    );
    assert_eq!(first["projection"]["status"], "RECORDED");
    assert_eq!(first["render"]["status"], "RECORDED");
    // The stored frame is the exact scene-build request Core sent.
    assert_eq!(
        first["document"]["editor_json"]["attrs"][course::OPENMAIC_SCENE_NAMESPACE]
            ["request_frame"]
            .as_str(),
        Some(scene_build_frame(&first).as_str())
    );
    let candidate_id = first["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    // A repeated request reads the same candidate and writes nothing.
    let before = conn.total_changes();
    assert!(matches!(
        openmaic_slide::prepare_openmaic_slide_candidate(
            &mut conn, "slide_1", &request, &selection
        )
        .unwrap(),
        OpenMaicSlidePreparation::Existing(_)
    ));
    let read_back =
        openmaic_slide::read_openmaic_slide_candidate(&conn, "slide_1", &request, &selection)
            .unwrap()
            .unwrap();
    assert_eq!(read_back["document"]["document_id"], candidate_id.as_str());
    assert_eq!(read_back["generation_route"], "outline_slide_local_model");
    assert_eq!(conn.total_changes(), before, "a retry must not write");
    let count = document_count(&conn);
    drop(conn);
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    assert_eq!(document_count(&conn), count);
    assert!(matches!(
        openmaic_slide::prepare_openmaic_slide_candidate(
            &mut conn, "slide_1", &request, &selection
        )
        .unwrap(),
        OpenMaicSlidePreparation::Existing(_)
    ));
}

fn scene_build_frame(receipt: &Value) -> String {
    receipt["document"]["editor_json"]["attrs"][course::OPENMAIC_SCENE_NAMESPACE]["request_frame"]
        .as_str()
        .unwrap()
        .to_owned()
}

#[test]
fn only_a_slide_outline_at_a_valid_index_is_selected() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let outline_document_id = seed_outline(&mut conn);
    let source = source(&mut conn);
    let request = slide_request(&outline_document_id, 1, &source);
    let quiz = openmaic_slide::read_outline_candidate(&conn, &outline_document_id, 1).unwrap();
    assert_eq!(quiz["outline"]["type"], "quiz");
    assert!(matches!(
        openmaic_slide::prepare_openmaic_slide_candidate(&mut conn, "slide_1", &request, &quiz),
        Err(archeaxis_domain::document::Error::Invalid(
            "UNSUPPORTED_OUTLINE_TYPE"
        ))
    ));
    assert!(matches!(
        openmaic_slide::read_outline_candidate(&conn, &outline_document_id, 9),
        Err(archeaxis_domain::document::Error::Invalid(
            "OUTLINE_INDEX_OUT_OF_RANGE"
        ))
    ));
    assert!(
        openmaic_slide::read_outline_candidate(&conn, "doc_missing", 0).is_err(),
        "a missing outline document is not a selection"
    );
    assert!(matches!(
        openmaic_slide::read_outline_candidate(&conn, outline_document_id.as_str(), -1),
        Err(archeaxis_domain::document::Error::Invalid(
            "OUTLINE_INDEX_OUT_OF_RANGE"
        ))
    ));
    // Nothing was written while the selection was refused.
    assert_eq!(document_count(&conn), 2, "outline plus source only");
}

#[test]
fn a_changed_outline_or_content_conflicts_before_a_write() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let outline_document_id = seed_outline(&mut conn);
    let source = source(&mut conn);
    let request = slide_request(&outline_document_id, 0, &source);
    let selection = openmaic_slide::read_outline_candidate(&conn, &outline_document_id, 0).unwrap();
    let normalized = normalized_scene();
    let scene_request = openmaic_slide::openmaic_slide_scene_build_request(
        "slide_1",
        &selection,
        &normalized,
        &request["source"],
    )
    .unwrap();
    prepare_and_commit(&mut conn, "slide_1", &request, &selection, scene_request);
    // The same outline index with different source material is different content.
    let other_source = self::source(&mut conn);
    let mut other = request.clone();
    other["source"] = json!({"document_id":other_source["document_id"],
        "version":other_source["version"],
        "content_sha256":other_source["content_sha256"]});
    assert!(matches!(
        openmaic_slide::prepare_openmaic_slide_candidate(&mut conn, "slide_1", &other, &selection),
        Err(archeaxis_domain::document::Error::Invalid(
            "SLIDE_REQUEST_CONFLICT"
        ))
    ));
    // A quiz outline at the same create ID is refused by type before identity.
    let other_selection =
        openmaic_slide::read_outline_candidate(&conn, &outline_document_id, 1).unwrap();
    let mut quiz = request.clone();
    quiz["outline_index"] = json!(1);
    assert!(matches!(
        openmaic_slide::prepare_openmaic_slide_candidate(
            &mut conn,
            "slide_1",
            &quiz,
            &other_selection
        ),
        Err(archeaxis_domain::document::Error::Invalid(
            "UNSUPPORTED_OUTLINE_TYPE"
        ))
    ));
    // The same request with a different model is also different content.
    let mut model = request.clone();
    model["model"] = json!("another-model");
    assert!(matches!(
        openmaic_slide::prepare_openmaic_slide_candidate(&mut conn, "slide_1", &model, &selection),
        Err(archeaxis_domain::document::Error::Invalid(
            "SLIDE_REQUEST_CONFLICT"
        ))
    ));
    let count = document_count(&conn);
    assert_eq!(count, 4, "two sources, one outline and one scene candidate");
}

#[test]
fn a_failed_or_mismatched_chain_writes_nothing() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let outline_document_id = seed_outline(&mut conn);
    let source = source(&mut conn);
    let request = slide_request(&outline_document_id, 0, &source);
    let selection = openmaic_slide::read_outline_candidate(&conn, &outline_document_id, 0).unwrap();
    let pending = match openmaic_slide::prepare_openmaic_slide_candidate(
        &mut conn, "slide_1", &request, &selection,
    )
    .unwrap()
    {
        OpenMaicSlidePreparation::Pending(value) => value,
        OpenMaicSlidePreparation::Existing(_) => panic!("expected a fresh request"),
    };
    let normalized = normalized_scene();
    let scene_request = openmaic_slide::openmaic_slide_scene_build_request(
        "slide_1",
        &selection,
        &normalized,
        &request["source"],
    )
    .unwrap();
    let scene_pending =
        match course::prepare_openmaic_scene(&mut conn, "slide_1", &scene_request).unwrap() {
            course::OpenMaicPreparation::Pending(value) => value,
            course::OpenMaicPreparation::Existing(_) => panic!("expected a fresh scene"),
        };
    // A record assembled for another request is not admitted.
    let mut stale = slide_generation("slide_1", &request, &selection, scene_request.clone());
    stale.record["request_sha256"] = json!(digest(b"other request"));
    let worker = scene_build_document(&scene_request);
    assert!(
        openmaic_slide::commit_openmaic_slide_candidate(
            &mut conn,
            "slide_1",
            &request,
            &pending,
            &scene_pending,
            &worker,
            &stale,
        )
        .is_err()
    );
    assert_eq!(document_count(&conn), 2, "no partial candidate");
}

#[test]
fn a_scene_request_without_the_slide_record_is_not_read_as_a_slide_candidate() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let outline_document_id = seed_outline(&mut conn);
    let source = source(&mut conn);
    let request = slide_request(&outline_document_id, 0, &source);
    let selection = openmaic_slide::read_outline_candidate(&conn, &outline_document_id, 0).unwrap();
    let normalized = normalized_scene();
    let scene_request = openmaic_slide::openmaic_slide_scene_build_request(
        "slide_1",
        &selection,
        &normalized,
        &request["source"],
    )
    .unwrap();
    // An ordinary scene candidate at the same create ID has no chain record.
    let scene_pending =
        match course::prepare_openmaic_scene(&mut conn, "slide_1", &scene_request).unwrap() {
            course::OpenMaicPreparation::Pending(value) => value,
            course::OpenMaicPreparation::Existing(_) => panic!("expected a fresh scene"),
        };
    let worker = scene_build_document(&scene_request);
    course::commit_openmaic_scene(
        &mut conn,
        "slide_1",
        &scene_request,
        &scene_pending,
        &worker,
    )
    .unwrap();
    assert!(matches!(
        openmaic_slide::prepare_openmaic_slide_candidate(
            &mut conn, "slide_1", &request, &selection
        ),
        Err(archeaxis_domain::document::Error::Invalid(
            "SLIDE_REQUEST_CONFLICT"
        ))
    ));
}
