//! Explicitly gated real-local-model check for the DeepTutor question turn.
//! Uses synthetic material and a synthetic human decision; records no
//! model-generated question text and makes no claim about its quality. An
//! explicitly labelled synthetic loopback lane can exercise the same test.
use archeaxis_application::executor::Executor;
use archeaxis_domain::{document, provider_material_grant::Snapshot};
use archeaxis_store_sqlite::init_workspace;
use axum::{Router, body::Body, http::Request, http::StatusCode};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::path::PathBuf;
use tower::ServiceExt;

const ROUTE: &str = "/api/v1/learning/deeptutor/question-turn";
const ACCEPT_ROUTE: &str = "/api/v1/learning/deeptutor/question-candidates/accept";
const GRADE_ROUTE: &str = "/api/v1/learning/deeptutor/practice-grade";
const ACTIVITIES: &str = "/api/v1/learning/provider-activities";
const IMPORT_CAPABILITY: &str = "deeptutor.practice.import";
const MODEL_CAPABILITY: &str = "course.openmaic.outline-model";

fn repository() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf()
}

fn snapshot(value: &Value) -> Snapshot {
    Snapshot {
        document_id: value["document_id"].as_str().unwrap().into(),
        version: value["version"].as_i64().unwrap(),
        content_sha256: value["content_sha256"].as_str().unwrap().into(),
    }
}

async fn call(router: &Router, actor: &str, body: &Value) -> (StatusCode, Value) {
    call_uri(router, ROUTE, actor, body).await
}

async fn call_uri(router: &Router, uri: &str, actor: &str, body: &Value) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(uri)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", actor)
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

async fn document_count(executor: &Executor) -> i64 {
    executor
        .store()
        .submit_wait(|conn| {
            conn.query_row("SELECT count(*) FROM documents", [], |row| {
                row.get::<_, i64>(0)
            })
        })
        .await
        .unwrap()
        .unwrap()
}

#[tokio::test]
async fn real_local_question_turn_is_durable_or_fails_without_a_partial_document() {
    if std::env::var("ARCHEAXIS_TEST_REAL_MODEL").as_deref() != Ok("1") {
        eprintln!("skipping: ARCHEAXIS_TEST_REAL_MODEL is not 1; this skip is not evidence");
        return;
    }
    let model = std::env::var("ARCHEAXIS_MACHINE_MODEL").expect("declared local model");
    let endpoint = std::env::var("ARCHEAXIS_MACHINE_ENDPOINT").expect("declared local endpoint");
    let lane = std::env::var("ARCHEAXIS_TEST_MODEL_LANE").unwrap_or_else(|_| "REAL_LOCAL".into());
    assert!(matches!(lane.as_str(), "REAL_LOCAL" | "SYNTHETIC_LOOPBACK"));
    if lane == "SYNTHETIC_LOOPBACK" {
        assert!(model.starts_with("synthetic-"));
    }
    let python: PathBuf = std::env::var_os("ARCHEAXIS_PYTHON")
        .expect("canonical isolated Python")
        .into();
    let repo = repository();
    let practice = repo
        .join("services/learning-providers/deeptutor/practice_host_worker.py")
        .canonicalize()
        .unwrap();
    let model_worker = repo
        .join("services/python-workers/course/worker_outline_local_model.py")
        .canonicalize()
        .unwrap();
    let text_worker = repo
        .join("services/python-workers/transport/text_ndjson.py")
        .canonicalize()
        .unwrap();
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    let (material, source_grant) = {
        let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
        let material = document::create_optional(
            &mut conn, None, None, "Synthetic material",
            json!({"type":"doc","content":[{"type":"paragraph","content":[
                {"type":"text","text":"SYNTHETIC: two groups of two objects contain four objects."}]}]}),
        ).unwrap();
        let source_grant = document::create_optional(&mut conn,None,None,"Synthetic grant",json!({"type":"doc","content":[],"attrs":{
            "archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1",
                "purpose":"practice","consumer":"deeptutor","operations":["practice"],
                "material":snapshot(&material),"authorization_basis":"SYNTHETIC explicit human authorization",
                "expires_at":null,"state":"granted"}
        }})).unwrap();
        (material, source_grant)
    };
    let executor = Executor::open_routes(
        &path,
        &dir.path().join("staging"),
        &python,
        &text_worker,
        &[
            (IMPORT_CAPABILITY, practice.clone()),
            (MODEL_CAPABILITY, model_worker.clone()),
        ],
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    let body = json!({"create_request_id":"real_question_turn", "material":snapshot(&material),
        "requirement":"根据材料出一道单项选择题。", "model":null});
    let (denied, _) = call(&router, "machine", &body).await;
    assert_eq!(denied, StatusCode::FORBIDDEN);
    assert_eq!(document_count(&executor).await, 2);

    let (status, result) = call(&router, "human", &body).await;
    if status != StatusCode::CREATED {
        assert!(
            [
                StatusCode::UNPROCESSABLE_ENTITY,
                StatusCode::SERVICE_UNAVAILABLE,
                StatusCode::GATEWAY_TIMEOUT,
                StatusCode::BAD_GATEWAY
            ]
            .contains(&status)
        );
        assert!(result["reason"].as_str().is_some());
        assert_eq!(document_count(&executor).await, 2);
        println!(
            "{}",
            json!({"schema":"archeaxis.deeptutor-real-model-receipt/v1",
            "outcome":"REFUSED", "model_lane":lane, "endpoint":endpoint, "model":model, "status":status.as_u16(),
            "stage":result["stage"], "reason":result["reason"],
            "worker_status":result["worker_outcome"]["status"],
            "worker_reason":result["worker_outcome"]["reason"],
            "response_format":result["worker_outcome"]["response_format"],
            "documents":2,"quality":"NOT_ASSESSED"})
        );
        return;
    }
    assert_eq!(
        result["generation_route"],
        "deeptutor_question_turn_local_model"
    );
    assert_eq!(result["response_origin"], "LOCAL_MODEL_UNVERIFIED");
    assert_eq!(result["rendering_authorized"], false);
    assert_eq!(result["active_content_executed"], false);
    assert_eq!(result["answer_secrecy"], "not_established");
    assert_eq!(result["candidate_document_status"], "current");
    assert_eq!(result["model"], model);
    assert_eq!(
        result["document"]["editor_json"]["attrs"]["archeaxis_deeptutor_question_turn_candidate"]["human_review_required"],
        true
    );
    let candidate_id = result["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    assert_eq!(document_count(&executor).await, 3);
    let (duplicate_status, duplicate) = call(&router, "human", &body).await;
    assert_eq!(duplicate_status, StatusCode::OK);
    assert_eq!(duplicate["worker_invoked"], false);
    assert_eq!(duplicate["document"]["document_id"], candidate_id);

    // A synthetic human fixture deliberately replaces the question text and
    // supplies its own answer and explanation. It makes no judgment about the
    // model's generated question or the model's own proposed answer.
    let accept_body = json!({"create_request_id":"real_model_fixture_accept",
        "candidate":snapshot(&result["document"]),"correct_answer":"A",
        "question_text":"SYNTHETIC fixture: select option A.",
        "explanation":"SYNTHETIC fixture explicitly specifies A."});
    let (status, accepted) = call_uri(&router, ACCEPT_ROUTE, "human", &accept_body).await;
    assert_eq!(status, StatusCode::CREATED, "synthetic acceptance failed");
    assert_eq!(
        accepted["question_view"]["question"]["question"],
        "SYNTHETIC fixture: select option A."
    );
    let acceptance =
        &accepted["document"]["editor_json"]["attrs"]["archeaxis_deeptutor_question_acceptance"];
    assert_eq!(acceptance["answer_key_source"], "human_declared");
    assert_eq!(acceptance["model_answer_used_as_key"], false);
    assert_eq!(acceptance["explanation_source"], "human_supplied");
    let question = snapshot(&accepted["question_document"]);
    let question_grant = executor
        .store()
        .submit_wait({
            let question = question.clone();
            move |conn| {
                document::create_optional(
                    conn,
                    None,
                    None,
                    "Synthetic question grant",
                    json!({"type":"doc","content":[],"attrs":{"archeaxis_provider_material_grant":{
                "schema":"archeaxis.provider-material-grant/v1","purpose":"practice",
                "consumer":"deeptutor","operations":["practice"],"material":question,
                "authorization_basis":"SYNTHETIC explicit human authorization",
                "expires_at":null,"state":"granted"}}}),
                )
            }
        })
        .await
        .unwrap()
        .unwrap();
    let activity = json!({"activity_id":"real_model_fixture_activity","material":snapshot(&material),
        "provider":{"id":"deeptutor","version":"1.7.1"},
        "question":{"question_id":accepted["question_view"]["question"]["question_id"],
            "question_version":accepted["question_view"]["question_version"]},
        "grant":snapshot(&source_grant)});
    let (status, _) = call_uri(&router, ACTIVITIES, "human", &activity).await;
    assert_eq!(status, StatusCode::CREATED, "synthetic activity failed");
    let (status, _) = call_uri(
        &router,
        &format!("{ACTIVITIES}/real_model_fixture_activity/attempts"),
        "human",
        &json!({"attempt_id":"real_model_fixture_attempt"}),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "synthetic attempt failed");
    let grade_body = json!({"activity_id":"real_model_fixture_activity",
        "attempt_id":"real_model_fixture_attempt","request":{
            "client_event_id":"real_model_fixture_grade","question_document":question,
            "question_grant":snapshot(&question_grant),"answer":"A"}});
    let (status, graded) = call_uri(&router, GRADE_ROUTE, "human", &grade_body).await;
    assert_eq!(status, StatusCode::CREATED, "synthetic grading failed");
    assert_eq!(graded["provider_correct"], true);
    assert_eq!(graded["independent_mastery"], "not_established");
    assert_eq!(document_count(&executor).await, 5);

    let (status, backup) =
        call_uri(&router, "/api/v1/workspace/backups", "human", &json!({})).await;
    assert_eq!(
        status,
        StatusCode::CREATED,
        "synthetic workspace backup failed"
    );
    assert_eq!(backup["verified"], true);
    let (status, preview) = call_uri(
        &router,
        "/api/v2/workspace/restore/preview",
        "human",
        &json!({"backup_id":backup["backup_id"],"expected_sha256":backup["sha256"]}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(preview["verified"], true);
    let backup_path = dir
        .path()
        .join("backups")
        .join(backup["filename"].as_str().unwrap());
    drop(router);
    drop(executor);

    let reopened = Executor::open_routes(
        &path,
        &dir.path().join("staging"),
        &python,
        &text_worker,
        &[],
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(reopened.clone());
    let (read_status, read_back) = call(&router, "human", &body).await;
    assert_eq!(read_status, StatusCode::OK);
    assert_eq!(read_back["worker_invoked"], false);
    assert_eq!(read_back["document"]["document_id"], candidate_id);
    let (status, acceptance_replay) = call_uri(&router, ACCEPT_ROUTE, "human", &accept_body).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(acceptance_replay["duplicate"], true);
    let (status, grade_replay) = call_uri(&router, GRADE_ROUTE, "human", &grade_body).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(grade_replay["duplicate"], true);
    assert_eq!(grade_replay["provider_correct"], true);
    assert_eq!(document_count(&reopened).await, 5);
    drop(router);
    drop(reopened);

    // The real maintenance entry restores only into this new synthetic DB.
    // History is readable; restored grants must not authorize new generation.
    let restored_path = dir.path().join("restored.sqlite");
    let restored = std::process::Command::new(env!("CARGO_BIN_EXE_archeaxis-api"))
        .arg("--maintenance-restore")
        .arg(&restored_path)
        .arg(&backup_path)
        .output()
        .unwrap();
    assert!(
        restored.status.success(),
        "synthetic maintenance restore failed"
    );
    let restore_receipt: Value = serde_json::from_slice(&restored.stdout).unwrap();
    assert_eq!(restore_receipt["authorization_requires_new_grants"], true);
    let restored_executor = Executor::open_routes(
        &restored_path,
        &dir.path().join("restored-staging"),
        &python,
        &text_worker,
        &[],
    )
    .await
    .unwrap();
    let restored_router = archeaxis_api::runtime::router(restored_executor.clone());
    let (status, history_turn) = call(&restored_router, "human", &body).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(history_turn["worker_invoked"], false);
    assert_eq!(history_turn["document"]["document_id"], candidate_id);
    let (status, history_accept) =
        call_uri(&restored_router, ACCEPT_ROUTE, "human", &accept_body).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(history_accept["duplicate"], true);
    let (status, history_grade) =
        call_uri(&restored_router, GRADE_ROUTE, "human", &grade_body).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(history_grade["duplicate"], true);
    assert_eq!(history_grade["provider_correct"], true);
    let mut new_turn = body.clone();
    new_turn["create_request_id"] = json!("restored_new_turn");
    let (status, _) = call(&restored_router, "human", &new_turn).await;
    assert_eq!(
        status,
        StatusCode::CONFLICT,
        "restored grant must stay fenced"
    );
    assert_eq!(document_count(&restored_executor).await, 5);

    // A new human fixture grant is independent of the fenced historical one.
    let fresh_grant = restored_executor
        .store()
        .submit_wait({
            let material = material.clone();
            move |conn| {
                document::create_optional_with_request(
                    conn,
                    None,
                    None,
                    "Synthetic renewed grant",
                    json!({"type":"doc","content":[],"attrs":{"archeaxis_provider_material_grant":{
                "schema":"archeaxis.provider-material-grant/v1","purpose":"practice",
                "consumer":"deeptutor","operations":["practice"],"material":snapshot(&material),
                "authorization_basis":"SYNTHETIC renewed human authorization",
                "expires_at":null,"state":"granted"}}}),
                    Some("synthetic_restored_new_grant"),
                )
            }
        })
        .await
        .unwrap()
        .unwrap();
    assert!(
        source_grant["document_id"].as_str().unwrap()
            < fresh_grant["document_id"].as_str().unwrap()
    );
    let (status, admitted) = call(&restored_router, "human", &new_turn).await;
    assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE);
    assert_eq!(admitted["reason"], "question_turn_worker_unavailable");
    assert_eq!(document_count(&restored_executor).await, 6);
    drop(restored_router);
    drop(restored_executor);

    // Reopen with the fixed workers. This is a new request under the renewed
    // grant, not a model retry. A strict model refusal remains a valid outcome
    // but must not create a partial document.
    let authorized_executor = Executor::open_routes(
        &restored_path,
        &dir.path().join("restored-staging"),
        &python,
        &text_worker,
        &[
            (IMPORT_CAPABILITY, practice),
            (MODEL_CAPABILITY, model_worker),
        ],
    )
    .await
    .unwrap();
    let authorized_router = archeaxis_api::runtime::router(authorized_executor.clone());
    let (status, regenerated) = call(&authorized_router, "human", &new_turn).await;
    let (regeneration, documents_after_generation) = if status == StatusCode::CREATED {
        assert_eq!(regenerated["worker_invoked"], true);
        assert_eq!(document_count(&authorized_executor).await, 7);
        let (status, duplicate) = call(&authorized_router, "human", &new_turn).await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(duplicate["worker_invoked"], false);
        (json!({"outcome":"GENERATED"}), 7)
    } else {
        assert!(
            [
                StatusCode::UNPROCESSABLE_ENTITY,
                StatusCode::SERVICE_UNAVAILABLE,
                StatusCode::GATEWAY_TIMEOUT,
                StatusCode::BAD_GATEWAY
            ]
            .contains(&status)
        );
        assert!(regenerated["reason"].as_str().is_some());
        assert_eq!(document_count(&authorized_executor).await, 6);
        (
            json!({"outcome":"REFUSED","status":status.as_u16(),"stage":regenerated["stage"],
            "reason":regenerated["reason"],"worker_reason":regenerated["worker_outcome"]["reason"]}),
            6,
        )
    };
    if lane == "SYNTHETIC_LOOPBACK" {
        assert_eq!(regeneration["outcome"], "GENERATED");
    }
    let fresh_id = fresh_grant["document_id"].as_str().unwrap().to_owned();
    let mut revoked = fresh_grant["editor_json"].clone();
    revoked["attrs"]["archeaxis_provider_material_grant"]["state"] = json!("revoked");
    authorized_executor
        .store()
        .submit_wait(move |conn| document::save(conn, &fresh_id, 1, revoked))
        .await
        .unwrap()
        .unwrap();
    new_turn["create_request_id"] = json!("restored_after_revoke");
    let (status, _) = call(&authorized_router, "human", &new_turn).await;
    assert_eq!(
        status,
        StatusCode::CONFLICT,
        "revoked new grant cannot authorize"
    );
    assert_eq!(
        document_count(&authorized_executor).await,
        documents_after_generation
    );
    println!(
        "{}",
        json!({"schema":"archeaxis.deeptutor-real-model-receipt/v1",
        "outcome":"GENERATED", "model_lane":lane, "endpoint":endpoint, "model":model,
        "candidate_document_id":candidate_id, "restart_worker_invoked":false,
        "documents_before_restore":5,"restored_documents_final":documents_after_generation,
        "restore_history_replayed":true,"restored_old_grant_fenced":true,
        "new_grant_reached_unregistered_worker":true,"restored_regeneration":regeneration,
        "new_grant_revoked":true,
        "quality":"NOT_ASSESSED","synthetic_fixture_accepted":true,
        "model_answer_used_as_key":false,"synthetic_fixture_graded":true,
        "owner_acceptance":false})
    );
}
