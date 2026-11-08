//! Explicitly gated real-local-model check for the DeepTutor question turn.
//! Uses only synthetic material and records no model-generated question text.
use archeaxis_application::executor::Executor;
use archeaxis_domain::{document, provider_material_grant::Snapshot};
use archeaxis_store_sqlite::init_workspace;
use axum::{Router, body::Body, http::Request, http::StatusCode};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::path::PathBuf;
use tower::ServiceExt;

const ROUTE: &str = "/api/v1/learning/deeptutor/question-turn";
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
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(ROUTE)
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
    let material = {
        let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
        let material = document::create_optional(
            &mut conn, None, None, "Synthetic material",
            json!({"type":"doc","content":[{"type":"paragraph","content":[
                {"type":"text","text":"SYNTHETIC: two groups of two objects contain four objects."}]}]}),
        ).unwrap();
        document::create_optional(&mut conn,None,None,"Synthetic grant",json!({"type":"doc","content":[],"attrs":{
            "archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1",
                "purpose":"practice","consumer":"deeptutor","operations":["practice"],
                "material":snapshot(&material),"authorization_basis":"SYNTHETIC explicit human authorization",
                "expires_at":null,"state":"granted"}
        }})).unwrap();
        material
    };
    let executor = Executor::open_routes(
        &path,
        &dir.path().join("staging"),
        &python,
        &text_worker,
        &[
            (IMPORT_CAPABILITY, practice.clone()),
            (MODEL_CAPABILITY, model_worker),
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
            "outcome":"REFUSED", "endpoint":endpoint, "model":model, "status":status.as_u16(),
            "stage":result["stage"], "reason":result["reason"],
            "worker_status":result["worker_outcome"]["status"],
            "worker_reason":result["worker_outcome"]["reason"],
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
    drop(router);
    drop(executor);

    let reopened = Executor::open_routes(
        &path,
        &dir.path().join("staging"),
        &python,
        &text_worker,
        &[(IMPORT_CAPABILITY, practice)],
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(reopened.clone());
    let (read_status, read_back) = call(&router, "human", &body).await;
    assert_eq!(read_status, StatusCode::OK);
    assert_eq!(read_back["worker_invoked"], false);
    assert_eq!(read_back["document"]["document_id"], candidate_id);
    assert_eq!(document_count(&reopened).await, 3);
    println!(
        "{}",
        json!({"schema":"archeaxis.deeptutor-real-model-receipt/v1",
        "outcome":"GENERATED", "endpoint":endpoint, "model":model,
        "candidate_document_id":candidate_id, "restart_worker_invoked":false,
        "documents":3,"quality":"NOT_ASSESSED","answer_accepted":false})
    );
}
