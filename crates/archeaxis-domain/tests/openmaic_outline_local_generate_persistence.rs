//! Synthetic persistence for the OpenMAIC local-model outline route.
//! These tests start no Node, call no model and qualify no installed app.
use archeaxis_domain::{
    document,
    openmaic_outline::{
        self, OpenMaicLocalGeneration, OpenMaicOutlineGenerationPending,
        OpenMaicOutlineGenerationPreparation,
    },
};
use archeaxis_store_sqlite::{capability_settings, init_workspace};
use rusqlite::Connection;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

const NAMESPACE: &str = "archeaxis_openmaic_outline_generate_candidate";

fn digest(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn request() -> Value {
    json!({"schema":"archeaxis.openmaic-outline-generate/v1","create_request_id":"client_1",
        "requirement":"Synthetic requirement","source_text":"SYNTHETIC source material",
        "model":null})
}

fn content() -> String {
    json!({"languageDirective":"Respond in Simplified Chinese.","courseTitle":"Synthetic course",
        "outlines":[
            {"id":"o1","type":"slide","title":"SYNTHETIC_OUTLINE_TITLE",
             "description":"SYNTHETIC_OUTLINE_DESCRIPTION","keyPoints":["SYNTHETIC_KEY_POINT"],
             "order":1},
            {"id":"o2","type":"quiz","title":"SYNTHETIC_QUIZ_TITLE","description":"",
             "keyPoints":[],"order":2}]})
    .to_string()
}

fn binding(request: &Value) -> Value {
    let system = "SYNTHETIC_SYSTEM prompt";
    let user = "SYNTHETIC_USER prompt with SYNTHETIC source material";
    let mut shas = serde_json::Map::new();
    for (name, seed) in [
        ("input_sha256", "unkeyed identity"),
        ("upstream_manifest_sha256", "manifest"),
        ("npm_members_sha256", "members"),
        ("worker_sha256", "worker"),
        ("guard_sha256", "guard"),
    ] {
        shas.insert(name.to_string(), json!(digest(seed.as_bytes())));
    }
    json!({"schema":"archeaxis.openmaic-outline-prompt-binding/v1",
        "request_id":request["create_request_id"],
        "input_sha256":shas["input_sha256"],
        "upstream_manifest_sha256":shas["upstream_manifest_sha256"],
        "npm_members_sha256":shas["npm_members_sha256"],
        "worker_sha256":shas["worker_sha256"],
        "guard_sha256":shas["guard_sha256"],
        "system":system,"user":user,
        "system_sha256":digest(system.as_bytes()),"user_sha256":digest(user.as_bytes())})
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

fn worker(request: &Value) -> Value {
    json!({"schema":"archeaxis.openmaic-outline-prompt-result/v1","status":"CANDIDATE","reason":null,
        "request_id":request["create_request_id"],"stage":"replay",
        "response_origin":"CALLER_SUPPLIED_UNVERIFIED","model_call":"NOT_INVOKED",
        "network_performed":false,"core_task":"NOT_CONNECTED","core_authorization":"NOT_ESTABLISHED",
        "canonical_bindings_verified":false,"identity_scope":"UNKEYED_COMPARISON_ONLY",
        "binding_authentication":"NOT_PROVIDED","source_snapshot_authority":"CALLER_DECLARED_ONLY",
        "persisted":false,"active_content_executed":false,"human_review_required":true,
        "response_origin_verification":null,
        "data":{"languageDirective":"Respond in Simplified Chinese.",
            "courseTitle":"Synthetic course",
            "outlines":[
                {"id":"o1","type":"slide","title":"SYNTHETIC_OUTLINE_TITLE",
                 "description":"SYNTHETIC_OUTLINE_DESCRIPTION","keyPoints":["SYNTHETIC_KEY_POINT"],
                 "order":1},
                {"id":"o2","type":"quiz","title":"SYNTHETIC_QUIZ_TITLE","description":"",
                 "keyPoints":[],"order":2}]}})
}

fn generation(request: &Value) -> OpenMaicLocalGeneration {
    let content = content();
    OpenMaicLocalGeneration {
        binding: binding(request),
        model_reply: model_reply(&content),
        replay_document: worker(request),
    }
}

fn pending(conn: &mut Connection, id: &str, request: &Value) -> OpenMaicOutlineGenerationPending {
    match openmaic_outline::prepare_openmaic_outline_generation(conn, id, request).unwrap() {
        OpenMaicOutlineGenerationPreparation::Pending(value) => value,
        OpenMaicOutlineGenerationPreparation::Existing(_) => panic!("expected a fresh request"),
    }
}

fn commit(conn: &mut Connection, id: &str, request: &Value) -> Value {
    let ticket = pending(conn, id, request);
    openmaic_outline::commit_openmaic_outline_generation(
        conn,
        id,
        request,
        &ticket,
        &generation(request),
    )
    .unwrap()
}

fn document_count(conn: &Connection) -> i64 {
    conn.query_row("SELECT count(*) FROM documents", [], |row| row.get(0))
        .unwrap()
}

#[test]
fn new_candidates_reject_nonstop_or_unconfirmed_model_completion() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let request = request();
    let ticket = pending(&mut conn, "client_1", &request);
    for finish in [json!("length"), Value::Null, json!("error")] {
        let mut generated = generation(&request);
        generated.model_reply["finish_reason"] = finish;
        assert!(
            openmaic_outline::commit_openmaic_outline_generation(
                &mut conn, "client_1", &request, &ticket, &generated,
            )
            .is_err(),
            "an unconfirmed model completion must not be persisted"
        );
        assert_eq!(document_count(&conn), 0);
    }
}

#[test]
fn a_preexisting_legacy_candidate_with_nonstop_metadata_remains_readable() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let request = request();
    let mut generated = generation(&request);
    generated.model_reply["finish_reason"] = json!("length");
    let saved = json!({
        "schema":openmaic_outline::OPENMAIC_OUTLINE_GENERATE_DOCUMENT_SCHEMA,
        "create_request_id":"client_1",
        "generation_request_sha256":openmaic_outline::openmaic_outline_generate_request_sha256(&request),
        "request_frame":request,
        "prompt_binding":generated.binding,
        "model_reply":generated.model_reply,
        "worker_document":generated.replay_document,
        "model_finish_reason":"length",
    });
    let editor = json!({"type":"doc","attrs":{(NAMESPACE):saved},"content":[]});
    let internal_id = openmaic_outline::openmaic_outline_generate_internal_request_id("client_1");
    document::create_optional_with_request(
        &mut conn,
        None,
        None,
        "Synthetic legacy",
        editor,
        Some(&internal_id),
    )
    .unwrap();
    let outcome =
        openmaic_outline::prepare_openmaic_outline_generation(&mut conn, "client_1", &request)
            .unwrap();
    let OpenMaicOutlineGenerationPreparation::Existing(receipt) = outcome else {
        panic!("the previous candidate must remain readable")
    };
    assert_eq!(receipt["model_finish_reason"], "length");
    assert_eq!(document_count(&conn), 1);
}

#[test]
fn a_generated_candidate_is_persisted_once_with_its_model_and_prompt_identity() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let request = request();
    let first = commit(&mut conn, "client_1", &request);
    let saved = &first["document"]["editor_json"]["attrs"][NAMESPACE];
    let content = content();

    assert_eq!(
        saved["schema"],
        "archeaxis.openmaic-outline-generate-document/v1"
    );
    assert_eq!(saved["generation_route"], "local_model");
    assert_eq!(saved["model_call"], "INVOKED");
    assert_eq!(saved["model"], "synthetic-local-model");
    assert_eq!(saved["model_reply_sha256"], digest(content.as_bytes()));
    assert_eq!(saved["response_origin"], "LOCAL_MODEL_UNVERIFIED");
    assert_eq!(saved["human_review_required"], true);
    assert_eq!(saved["active_content_executed"], false);
    assert_eq!(saved["rendering_authorized"], false);
    assert_eq!(saved["provider"], "openmaic");
    assert_eq!(saved["provider_version"], "1.3.0");
    assert_eq!(saved["generation_version"], "0.3.28");
    // The prompt binding keeps the capture identity, not a re-derived one.
    assert_eq!(
        saved["prompt_binding"]["input_sha256"],
        binding(&request)["input_sha256"]
    );
    assert_eq!(
        saved["prompt_binding"]["system_sha256"],
        digest(b"SYNTHETIC_SYSTEM prompt")
    );
    assert_eq!(
        saved["prompt_binding"]["user_sha256"],
        digest(b"SYNTHETIC_USER prompt with SYNTHETIC source material")
    );
    // The exact frames Core sent are stored and parse back.
    let replay: Value = serde_json::from_str(saved["replay_frame"].as_str().unwrap()).unwrap();
    assert_eq!(replay["stage"], "replay");
    assert_eq!(replay["request_id"], "client_1");
    assert_eq!(replay["binding"], saved["prompt_binding"]);
    assert_eq!(replay["reply"]["kind"], "caller_supplied");
    assert_eq!(replay["reply"]["value"], content);
    let capture: Value = serde_json::from_str(saved["capture_frame"].as_str().unwrap()).unwrap();
    assert_eq!(capture["stage"], "capture");
    assert_eq!(
        capture,
        openmaic_outline::openmaic_outline_capture_request(&request)
    );
    assert_eq!(saved["request_frame"], request);
    assert_eq!(saved["worker_document"], worker(&request));
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
        openmaic_outline::openmaic_outline_generate_document_id("client_1")
    );
    // A retry reads the same candidate and never writes or re-runs a stage.
    let before = conn.total_changes();
    match openmaic_outline::prepare_openmaic_outline_generation(&mut conn, "client_1", &request)
        .unwrap()
    {
        OpenMaicOutlineGenerationPreparation::Existing(receipt) => {
            assert_eq!(receipt, first);
            assert_eq!(receipt["generation_route"], "local_model");
        }
        _ => panic!("the committed candidate must be found before a model call"),
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
        openmaic_outline::prepare_openmaic_outline_generation(&mut conn, "client_1", &request)
            .unwrap(),
        OpenMaicOutlineGenerationPreparation::Existing(_)
    ));
    assert_eq!(document_count(&conn), 1);
}

#[test]
fn changed_content_under_the_same_create_request_id_conflicts() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let request = request();
    commit(&mut conn, "client_1", &request);
    let mut other = request.clone();
    other["requirement"] = json!("DIFFERENT requirement");
    assert!(
        openmaic_outline::prepare_openmaic_outline_generation(&mut conn, "client_1", &other)
            .is_err(),
        "the same create ID cannot describe different content"
    );
    // A stage result assembled for another request is not admitted here.
    let mut separate = request.clone();
    separate["create_request_id"] = json!("client_3");
    separate["requirement"] = json!("DIFFERENT requirement");
    let ticket = pending(&mut conn, "client_3", &separate);
    assert!(
        openmaic_outline::commit_openmaic_outline_generation(
            &mut conn,
            "client_3",
            &separate,
            &ticket,
            &generation(&request)
        )
        .is_err(),
        "a generation built for another request must not be admitted"
    );
    assert_eq!(document_count(&conn), 1);
}

#[test]
fn every_named_failure_stage_is_refused_before_a_document_exists() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let request = request();
    let ticket = pending(&mut conn, "client_1", &request);

    // A model that did not reply has no content to replay.
    let mut unavailable = generation(&request);
    unavailable.model_reply = json!({"schema":"archeaxis.openmaic-outline-model-reply/v1",
        "status":"MODEL_UNAVAILABLE","reason":"MODEL_ENDPOINT_UNREACHABLE","content":null,
        "content_sha256":null,"model":null,"model_call":"INVOKED","network_performed":false,
        "network_scope":"LOOPBACK_LOCAL_MODEL_ONLY","persisted":false,
        "core_task":"NOT_CONNECTED","human_review_required":true});

    let mut changes: Vec<(&str, OpenMaicLocalGeneration)> = Vec::new();
    changes.push(("model unavailable", unavailable));
    let mut wrong_sha = generation(&request);
    wrong_sha.model_reply["content_sha256"] = json!("0".repeat(64));
    changes.push(("model reply digest", wrong_sha));
    let mut tampered_binding = generation(&request);
    tampered_binding.binding["system"] = json!(format!(
        "{} (tampered)",
        binding(&request)["system"].as_str().unwrap()
    ));
    changes.push(("prompt binding", tampered_binding));
    for change in [
        "status",
        "stage",
        "origin",
        "request_id",
        "outlines",
        "model_call",
    ] {
        let mut response = generation(&request);
        match change {
            "status" => response.replay_document["status"] = json!("UPSTREAM_FAILURE"),
            "stage" => response.replay_document["stage"] = json!("capture"),
            "origin" => response.replay_document["response_origin"] = json!("VERIFIED"),
            "request_id" => response.replay_document["request_id"] = json!("other_client"),
            "outlines" => response.replay_document["data"]["outlines"] = json!([]),
            _ => response.replay_document["model_call"] = json!("INVOKED"),
        }
        changes.push((change, response));
    }
    for (name, candidate) in changes {
        assert!(
            openmaic_outline::commit_openmaic_outline_generation(
                &mut conn, "client_1", &request, &ticket, &candidate
            )
            .is_err(),
            "{name}"
        );
    }
    assert!(
        openmaic_outline::commit_openmaic_outline_generation(
            &mut conn,
            "different_client",
            &request,
            &ticket,
            &generation(&request)
        )
        .is_err(),
        "admission must bind the create ID"
    );
    assert_eq!(document_count(&conn), 0);
}

#[test]
fn a_disabled_capability_refuses_the_commit() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let request = request();
    let ticket = pending(&mut conn, "client_1", &request);
    capability_settings::set_enabled(&conn, openmaic_outline::OPENMAIC_OUTLINE_CAPABILITY, false)
        .unwrap();
    assert!(
        openmaic_outline::commit_openmaic_outline_generation(
            &mut conn,
            "client_1",
            &request,
            &ticket,
            &generation(&request)
        )
        .is_err()
    );
    assert_eq!(document_count(&conn), 0);
}

#[test]
fn request_schema_and_shape_are_refused_before_any_stage() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let base = request();
    let mut cases: Vec<(&str, Value)> = Vec::new();
    let mut future = base.clone();
    future["schema"] = json!("archeaxis.openmaic-outline-generate/v2");
    cases.push(("version", future));
    let mut extra = base.clone();
    extra["reply"] = json!("caller supplied");
    cases.push(("extra", extra));
    let mut missing = base.clone();
    missing.as_object_mut().unwrap().remove("source_text");
    cases.push(("missing", missing));
    let mut identity = base.clone();
    identity["create_request_id"] = json!("not a token");
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
    let mut model = base.clone();
    model["model"] = json!("not\na model");
    cases.push(("model", model));
    for (name, request) in cases {
        assert!(
            openmaic_outline::openmaic_outline_generate_refusal(&request).is_some(),
            "{name}"
        );
        assert!(
            openmaic_outline::prepare_openmaic_outline_generation(&mut conn, "client_6", &request)
                .is_err(),
            "{name}"
        );
    }
    let refusal = openmaic_outline::openmaic_outline_generate_refusal(&json!({})).unwrap();
    assert_eq!(refusal["reason"], "UNSUPPORTED_REQUEST_VERSION");
    assert_eq!(
        refusal["supported"],
        json!(["archeaxis.openmaic-outline-generate/v1"])
    );
    assert_eq!(
        openmaic_outline::openmaic_outline_generate_refusal(&base),
        None
    );
    assert_eq!(document_count(&conn), 0);
}
