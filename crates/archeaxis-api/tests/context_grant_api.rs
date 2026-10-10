//! INTEGRATED Core/SQLite with a SYNTHETIC isolated Python answer worker.
use archeaxis_application::executor::Executor;
use archeaxis_domain::knowledge;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::path::PathBuf;
use tower::ServiceExt;

async fn call(router: &Router, method: &str, path: &str, actor: &str, body: Value) -> (u16, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", actor)
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}
async fn fixture(dir: &std::path::Path) -> (Router, String) {
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let worker = dir.join("answer.py");
    std::fs::write(&worker,"import json\nfrom pathlib import Path\np=Path(__file__).with_suffix('.count')\np.write_text(str(int(p.read_text())+1) if p.exists() else '1')\nprint(json.dumps({'answer':'SYNTHETIC answer','model':'synthetic/local'}))\n").unwrap();
    let executor = Executor::open_routes(
        &dir.join("db.sqlite"),
        &dir.join("staging"),
        &python,
        &PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../services/python-workers/transport/text_ndjson.py"),
        &[("machine.answer", worker)],
    )
    .await
    .unwrap();
    let id = executor
        .store()
        .submit(|conn| {
            use rusqlite::OptionalExtension;
            let existing: Option<String> = conn
                .query_row(
                    "SELECT knowledge_id FROM knowledge WHERE body=?1",
                    ["SYNTHETIC authorized context"],
                    |r| r.get(0),
                )
                .optional()?;
            match existing {
                Some(id) => Ok(id),
                None => knowledge::create_knowledge(
                    conn,
                    "NOTE",
                    "SYNTHETIC authorized context",
                    "accepted",
                    None,
                    None,
                    "owner",
                ),
            }
        })
        .await
        .unwrap()
        .unwrap();
    (archeaxis_api::runtime::router(executor), id)
}
fn editor(id: &str, state: &str) -> Value {
    json!({"type":"doc","attrs":{"archeaxis_context_grant":{
    "schema":"archeaxis.context-grant/v1","purpose":"answer this project question","consumer":"local-machine",
    "operations":["answer"],"knowledge_id":id,"provenance":[],"authorization_basis":"explicit fixture owner grant",
    "expires_at":null,"state":state}},"content":[]})
}
fn consumption(doc: &Value) -> Value {
    json!({"document_id":doc["document_id"],"version":doc["version"],
    "content_sha256":doc["content_sha256"],"purpose":"answer this project question"})
}

#[tokio::test]
async fn restored_grant_receipt_binds_request_but_never_claims_prior_execution_did_not_happen() {
    use sha2::{Digest, Sha256};
    let dir = tempfile::tempdir().unwrap();
    let (router, id) = fixture(dir.path()).await;
    let (status, doc) = call(&router, "POST", "/api/v1/documents", "human",
        json!({"title":"restore test grant","editor_json":editor(&id,"granted")})).await;
    assert_eq!(status, 201);
    let request = json!({"client_request_id":"restore_receipt_original","knowledge_id":id,
        "question":"SYNTHETIC secret question","context_grant":consumption(&doc)});
    assert_eq!(call(&router,"POST","/api/v1/machine/answers","human",request.clone()).await.0,200);
    drop(router);
    let mut conn = archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap()).unwrap();
    let tx = conn.transaction().unwrap();
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
    tx.commit().unwrap();
    drop(conn);
    let (router, _) = fixture(dir.path()).await;
    let (status, receipt) = call(&router,"POST","/api/v1/machine/answers","human",request.clone()).await;
    assert_eq!(status,403);
    assert_eq!(receipt["reason_code"],"RESTORED_GRANT_FENCED");
    assert_eq!(receipt["execution_state"],"NOT_EXECUTED");
    assert_eq!(receipt["execution_scope"],"CURRENT_INVOCATION");
    assert_eq!(receipt["prior_request_execution"],"UNVERIFIED");
    assert_eq!(receipt["answer_published"],false);
    assert_eq!(receipt["grant"],json!({"document_id":doc["document_id"],"version":doc["version"],"content_sha256":doc["content_sha256"]}));
    let normalized = json!({"operation":"answer","request":{
        "knowledge_id":id,"question":request["question"],"max_tokens":2048,"timeout_s":120,
        "context_grant":request["context_grant"],"asset_context_grant":null,
        "client_request_id":request["client_request_id"],"retest_of":null}});
    assert_eq!(receipt["request_sha256"],format!("{:x}",Sha256::digest(normalized.to_string().as_bytes())));
    assert!(!receipt.to_string().contains("SYNTHETIC secret question"));
    assert!(!receipt.to_string().contains("answer this project question"));
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),"1");
    // An ordinary invalid snapshot on a new post-restore grant must remain generic.
    let (status, new_grant) = call(&router,"POST","/api/v1/documents","human",
        json!({"title":"new grant","editor_json":editor(&id,"granted")})).await;
    assert_eq!(status,201);
    let mut fresh = request.clone();
    fresh["client_request_id"] = json!("restore_receipt_fresh");
    fresh["context_grant"] = consumption(&new_grant);
    let mut invalid = fresh.clone();
    invalid["context_grant"]["content_sha256"] = json!("0".repeat(64));
    let (status, generic) = call(&router,"POST","/api/v1/machine/answers","human",invalid).await;
    assert_eq!(status,403);
    assert_ne!(generic["reason_code"],"RESTORED_GRANT_FENCED");
    assert_eq!(call(&router,"POST","/api/v1/machine/answers","human",fresh).await.0,200);
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),"2");
    // Corrupt fence is enforcement denial, not proof of membership in a valid restore fence.
    drop(router);
    let conn = archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap()).unwrap();
    conn.execute("UPDATE workspace_meta SET value='broken' WHERE key='authorization_restore_fence'",[]).unwrap();
    drop(conn);
    let (router, _) = fixture(dir.path()).await;
    let (status, generic) = call(&router,"POST","/api/v1/machine/answers","human",request).await;
    assert_eq!(status,403);
    assert_ne!(generic["reason_code"],"RESTORED_GRANT_FENCED");
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),"2");
}

#[tokio::test]
async fn frozen_answer_identity_serializes_concurrent_retries_survives_restart_and_refuses_conflict()
 {
    let dir = tempfile::tempdir().unwrap();
    let (router, id) = fixture(dir.path()).await;
    let (status, doc) = call(
        &router,
        "POST",
        "/api/v1/documents",
        "human",
        json!({"title":"retry grant","editor_json":editor(&id,"granted")}),
    )
    .await;
    assert_eq!(status, 201);
    let request = json!({"client_request_id":"answer_retry_fixture","knowledge_id":id,"question":"SYNTHETIC original question","context_grant":consumption(&doc)});
    let (first, second) = tokio::join!(
        call(
            &router,
            "POST",
            "/api/v1/machine/answers",
            "human",
            request.clone()
        ),
        call(
            &router,
            "POST",
            "/api/v1/machine/answers",
            "human",
            request.clone()
        )
    );
    assert_eq!(first.0, 200, "{}", first.1);
    assert_eq!(second.0, 200, "{}", second.1);
    assert_eq!(first.1, second.1);
    assert_eq!(
        std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),
        "1"
    );
    let mut conflict = request.clone();
    conflict["question"] = json!("different question with same identity");
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/machine/answers",
            "human",
            conflict
        )
        .await
        .0,
        409
    );
    drop(router);
    let (restarted, _) = fixture(dir.path()).await;
    let replay = call(
        &restarted,
        "POST",
        "/api/v1/machine/answers",
        "human",
        request.clone(),
    )
    .await;
    assert_eq!(replay.0, 200, "{}", replay.1);
    assert_eq!(replay.1, first.1);
    assert_eq!(
        std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),
        "1"
    );
    let draft = format!(
        "/api/v1/documents/{}/draft",
        doc["document_id"].as_str().unwrap()
    );
    assert_eq!(
        call(
            &restarted,
            "PUT",
            &draft,
            "human",
            json!({"expected_version":1,"editor_json":editor(&id,"revoked")})
        )
        .await
        .0,
        200
    );
    assert_eq!(
        call(
            &restarted,
            "POST",
            "/api/v1/machine/answers",
            "human",
            request
        )
        .await
        .0,
        403
    );
    assert_eq!(
        std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),
        "1"
    );
    let (_, receipt) = call(
        &restarted,
        "GET",
        &format!(
            "/api/v1/machine/tasks/{}",
            first.1["answer_id"].as_str().unwrap()
        ),
        "human",
        Value::Null,
    )
    .await;
    assert_eq!(
        serde_json::from_str::<Value>(receipt["conditions"].as_str().unwrap()).unwrap(),
        first.1
    );
}

#[tokio::test]
async fn human_context_grant_is_pinned_consumed_and_revoked_without_rewriting_answers() {
    let dir = tempfile::tempdir().unwrap();
    let (router, id) = fixture(dir.path()).await;
    let create = json!({"title":"context","create_request_id":"context-api-fixture","editor_json":editor(&id,"granted")});
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/documents",
            "machine",
            create.clone()
        )
        .await
        .0,
        403
    );
    let (status, doc) = call(&router, "POST", "/api/v1/documents", "human", create).await;
    assert_eq!(status, 201, "{doc}");
    let request = json!({"knowledge_id":id,"question":"SYNTHETIC question","context_grant":consumption(&doc)});
    let (status, answer) = call(
        &router,
        "POST",
        "/api/v1/machine/answers",
        "human",
        request.clone(),
    )
    .await;
    assert_eq!(status, 200, "{answer}");
    assert_eq!(
        answer["context_authorization"]["current_permission_valid"],
        true
    );
    assert_eq!(
        answer["context_authorization"]["content_sha256"],
        doc["content_sha256"]
    );
    assert_eq!(
        std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),
        "1"
    );
    let draft = format!(
        "/api/v1/documents/{}/draft",
        doc["document_id"].as_str().unwrap()
    );
    let (status, revoked) = call(
        &router,
        "PUT",
        &draft,
        "human",
        json!({"expected_version":1,"editor_json":editor(&id,"revoked")}),
    )
    .await;
    assert_eq!(status, 200, "{revoked}");
    assert_eq!(
        call(&router, "POST", "/api/v1/machine/answers", "human", request)
            .await
            .0,
        403
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/machine/answers",
            "human",
            json!({"knowledge_id":id,"question":"omitted grant bypass attempt"})
        )
        .await
        .0,
        403
    );
    assert_eq!(call(&router,"POST","/api/v1/machine/answers","human",json!({"knowledge_id":id,"question":"new SYNTHETIC question","context_grant":consumption(&revoked)})).await.0,403);
    assert_eq!(
        std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),
        "1"
    );
    let (_, receipt) = call(
        &router,
        "GET",
        &format!(
            "/api/v1/machine/tasks/{}",
            answer["answer_id"].as_str().unwrap()
        ),
        "human",
        Value::Null,
    )
    .await;
    let stored: Value = serde_json::from_str(receipt["conditions"].as_str().unwrap()).unwrap();
    assert_eq!(stored, answer);
    assert_eq!(receipt["outcome"], "unmeasured");
}

#[tokio::test]
async fn wrong_purpose_or_hash_and_candidate_context_are_refused_before_worker() {
    let dir = tempfile::tempdir().unwrap();
    let (router, id) = fixture(dir.path()).await;
    let (_, doc) = call(
        &router,
        "POST",
        "/api/v1/documents",
        "human",
        json!({"title":"context draft","editor_json":editor(&id,"candidate")}),
    )
    .await;
    let mut grant = consumption(&doc);
    for variant in 0..3 {
        if variant == 1 {
            grant["purpose"] = json!("unapproved scope");
        }
        if variant == 2 {
            grant["content_sha256"] = json!("0".repeat(64));
        }
        assert_eq!(
            call(
                &router,
                "POST",
                "/api/v1/machine/answers",
                "human",
                json!({"knowledge_id":id,"question":"SYNTHETIC question","context_grant":grant})
            )
            .await
            .0,
            403
        );
    }
    assert!(!dir.path().join("answer.count").exists());
}

#[tokio::test]
async fn human_fixed_rubric_evaluation_never_rewrites_runtime_receipt_or_credits_mastery() {
    let dir = tempfile::tempdir().unwrap();
    let (router, id) = fixture(dir.path()).await;
    let (status, answer) = call(
        &router,
        "POST",
        "/api/v1/machine/answers",
        "human",
        json!({"knowledge_id":id,"question":"SYNTHETIC question"}),
    )
    .await;
    assert_eq!(status, 200);
    let rubric = json!({"schema":"archeaxis.machine-rubric/v1","request_id":"rubric_api_1","title":"SYNTHETIC standard","purpose":"fixture evaluation",
        "criteria":[{"criterion_id":"grounding","label":"Grounding","expectation":"Expected canonical context"}],"sources":[]});
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/machine/rubrics",
            "machine",
            rubric.clone()
        )
        .await
        .0,
        403
    );
    let (status, rubric_doc) = call(
        &router,
        "POST",
        "/api/v1/machine/rubrics",
        "human",
        rubric.clone(),
    )
    .await;
    assert_eq!(status, 201, "{rubric_doc}");
    assert_eq!(
        call(&router, "POST", "/api/v1/machine/rubrics", "human", rubric)
            .await
            .1,
        rubric_doc
    );
    let task = answer["answer_id"].as_str().unwrap();
    let (status, snapshot) = call(
        &router,
        "GET",
        &format!("/api/v1/machine/answers/{task}/snapshot"),
        "human",
        Value::Null,
    )
    .await;
    assert_eq!(status, 200, "{snapshot}");
    assert_eq!(snapshot["original_answer"], "SYNTHETIC answer");
    assert_eq!(snapshot["grants_human_mastery"], false);
    let request = json!({"request_id":"evaluation_api_1","task_id":task,"rubric":{
        "document_id":rubric_doc["document_id"],"version":1,"content_sha256":rubric_doc["content_sha256"]},
        "reviewer":"fixture-human","basis":"SYNTHETIC observation only","judgments":[{"criterion_id":"grounding","outcome":"failed","basis":"Expected context not shown"}],"outcome":"failed"});
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/machine/evaluations",
            "machine",
            request.clone()
        )
        .await
        .0,
        403
    );
    let (status, evaluation) = call(
        &router,
        "POST",
        "/api/v1/machine/evaluations",
        "human",
        request.clone(),
    )
    .await;
    assert_eq!(status, 201, "{evaluation}");
    assert_eq!(
        evaluation["editor_json"]["attrs"]["archeaxis_machine_evaluation"]["original_answer_sha256"],
        snapshot["original_answer_sha256"]
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/machine/evaluations",
            "human",
            request.clone()
        )
        .await
        .1,
        evaluation
    );
    let mut changed = request.clone();
    changed["basis"] = json!("rewrite");
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/machine/evaluations",
            "human",
            changed
        )
        .await
        .0,
        409
    );
    let mut forged = request;
    forged["request_id"] = json!("evaluation_forged");
    forged["outcome"] = json!("passed");
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/machine/evaluations",
            "human",
            forged
        )
        .await
        .0,
        400
    );
    let draft = format!(
        "/api/v1/documents/{}/draft",
        evaluation["document_id"].as_str().unwrap()
    );
    assert_eq!(
        call(
            &router,
            "PUT",
            &draft,
            "human",
            json!({"expected_version":1,"editor_json":{"type":"doc","content":[]}})
        )
        .await
        .0,
        400
    );
    let (_, listed) = call(
        &router,
        "GET",
        "/api/v1/machine/evaluations",
        "human",
        Value::Null,
    )
    .await;
    assert_eq!(listed["items"][0]["document_id"], evaluation["document_id"]);
    assert!(listed["next_cursor"].is_null());
    let (_, receipt) = call(
        &router,
        "GET",
        &format!("/api/v1/machine/tasks/{task}"),
        "human",
        Value::Null,
    )
    .await;
    assert_eq!(receipt["outcome"], "unmeasured");
    assert_eq!(
        serde_json::from_str::<Value>(receipt["conditions"].as_str().unwrap()).unwrap(),
        answer
    );
}

#[tokio::test]
async fn restored_workspace_without_historical_grants_cannot_bypass_permission_by_omission() {
    let dir = tempfile::tempdir().unwrap();
    let (router, id) = fixture(dir.path()).await;
    drop(router);
    let mut conn =
        archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
            .unwrap();
    let tx = conn.transaction().unwrap();
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
    tx.commit().unwrap();
    drop(conn);
    let (router, _) = fixture(dir.path()).await;
    let request = json!({"knowledge_id":id,"question":"SYNTHETIC restored context"});
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/machine/answers",
            "human",
            request.clone()
        )
        .await
        .0,
        403
    );
    assert!(
        !dir.path().join("answer.count").exists(),
        "no inference before explicit new authorization"
    );
    let (status, grant) = call(
        &router,
        "POST",
        "/api/v1/documents",
        "human",
        json!({"title":"new post-restore human authorization","editor_json":editor(&id,"granted")}),
    )
    .await;
    assert_eq!(status, 201);
    let mut authorized = request.clone();
    authorized["context_grant"] = consumption(&grant);
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/machine/answers",
            "human",
            authorized
        )
        .await
        .0,
        200
    );
    assert_eq!(
        std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),
        "1"
    );
    assert_eq!(
        call(&router, "POST", "/api/v1/machine/answers", "human", request)
            .await
            .0,
        403
    );
}
