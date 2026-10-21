//! SYNTHETIC data through actual Core HTTP/store, no network/worker task.
use archeaxis_application::executor::Executor;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::path::Path;
use tower::ServiceExt;

async fn router(dir: &Path) -> Router {
    let python = std::env::var_os("ARCHEAXIS_PYTHON").expect("canonical runner");
    let worker = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
    archeaxis_api::runtime::router(
        Executor::open(
            &dir.join("db.sqlite"),
            &dir.join("staging"),
            Path::new(&python),
            &worker,
        )
        .await
        .unwrap(),
    )
}
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
    let code = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (code, serde_json::from_slice(&bytes).unwrap_or(Value::Null))
}
async fn state(router: &Router) -> Value {
    let (code, value) = call(
        router,
        "GET",
        "/api/v1/capabilities/template.T3",
        "human",
        Value::Null,
    )
    .await;
    assert_eq!(
        code, 200,
        "first-party data-only template must be in the existing capability center: {value}"
    );
    value["capability"].clone()
}

fn editor(state: Option<&Value>) -> Value {
    let mut binding = json!({"schema":"archeaxis.template/v1","template_id":"T3","discipline_id":"math","fields":{"status":"unevaluated"},"references":[],"learning_item_key":null});
    if let Some(state) = state {
        let mut pin = state["definition"].clone();
        pin["application_epoch"] = state["state_epoch"].clone();
        binding["definition"] = pin;
    }
    json!({"type":"doc","attrs":{"archeaxis_template":binding},"content":[{"type":"paragraph","content":[{"type":"text","text":"SYNTHETIC owned learning practice"}]}]})
}
async fn create(router: &Router, key: &str, body: Value) -> (u16, Value) {
    call(
        router,
        "POST",
        "/api/v1/documents",
        "human",
        json!({"create_request_id":key,"title":"SYNTHETIC owned T3","editor_json":body}),
    )
    .await
}
async fn change(router: &Router, state: &Value, action: &str, version: i64) -> (u16, Value) {
    let target = state["available_definitions"]
        .as_array()
        .unwrap()
        .iter()
        .find(|d| d["version"] == version)
        .unwrap();
    call(router,"PUT","/api/v1/capabilities/template.T3/definition","human",json!({"expected_epoch":state["state_epoch"],"action":action,"version":version,"sha256":target["sha256"]})).await
}
async fn read(router: &Router, path: &str) -> Value {
    let (code, body) = call(router, "GET", path, "human", Value::Null).await;
    assert_eq!(code, 200, "{path}: {body}");
    body
}

#[tokio::test]
async fn lifecycle_guards_new_applications_and_preserves_old_public_objects_after_reopen() {
    let dir = tempfile::tempdir().unwrap();
    let core = router(dir.path()).await;
    // Knowledge and learning are created through their existing public APIs.
    let (code,k)=call(&core,"POST","/api/v1/knowledge-items","human",json!({"knowledge_type":"PERSONAL_DEFINITION","body":"SYNTHETIC owned definition","status":"accepted","created_by":"human"})).await;
    assert_eq!(code, 201, "{k}");
    let kid = k["knowledge_id"].as_str().unwrap();
    let (code, reference) = call(
        &core,
        "POST",
        "/api/v1/learning/items/t3-learning/references",
        "human",
        json!({"knowledge_id":kid}),
    )
    .await;
    assert_eq!(code, 201, "{reference}");
    let history = read(&core, "/api/v1/learning/events/t3-learning").await;
    let knowledge = read(&core, &format!("/api/v1/knowledge-items/{kid}/v3")).await;
    let initial = state(&core).await;
    let mut content = editor(Some(&initial));
    content["attrs"]["archeaxis_template"]["learning_item_key"] = json!("t3-learning");
    let (code, pinned) = create(&core, "pinned-v1", content.clone()).await;
    assert_eq!(code, 201, "{pinned}");
    let (code, legacy) = create(&core, "legacy-v1", editor(None)).await;
    assert_eq!(code, 201, "{legacy}");
    let (code, disabled) = change(&core, &initial, "disable", 1).await;
    assert_eq!(code, 200, "{disabled}");
    assert_eq!(
        create(&core, "disabled-pinned", editor(Some(&initial)))
            .await
            .0,
        400
    );
    assert_eq!(
        create(&core, "disabled-unpinned", editor(None)).await.0,
        400
    );
    // A body/field edit retains legacy and pinned identities without new approval.
    for doc in [&pinned, &legacy] {
        let mut edited = doc["editor_json"].clone();
        edited["attrs"]["archeaxis_template"]["fields"]["note"] = json!("still editable");
        let path = format!(
            "/api/v1/documents/{}/draft",
            doc["document_id"].as_str().unwrap()
        );
        assert_eq!(
            call(
                &core,
                "PUT",
                &path,
                "human",
                json!({"expected_version":1,"editor_json":edited})
            )
            .await
            .0,
            200
        );
    }
    let disabled = disabled["capability"].clone();
    let (code, enabled) = change(&core, &disabled, "enable", 1).await;
    assert_eq!(code, 200, "{enabled}");
    let enabled = enabled["capability"].clone();
    // ABA enable cannot revive an old application lease.
    assert_eq!(create(&core, "aba", editor(Some(&initial))).await.0, 400);
    let (code, updated) = change(&core, &enabled, "update", 2).await;
    assert_eq!(code, 200, "{updated}");
    let updated = updated["capability"].clone();
    assert_ne!(
        updated["definition"]["sha256"],
        initial["definition"]["sha256"]
    );
    assert_eq!(
        create(&core, "old-version", editor(Some(&enabled))).await.0,
        400
    );
    assert_eq!(
        create(&core, "legacy-after-update", editor(None)).await.0,
        400
    );
    let (code, newer) = create(&core, "pinned-v2", editor(Some(&updated))).await;
    assert_eq!(code, 201, "{newer}");
    let (code, rolled) = change(&core, &updated, "rollback", 1).await;
    assert_eq!(code, 200, "{rolled}");
    assert_eq!(rolled["capability"]["definition"], initial["definition"]);
    let (code, removed) = change(&core, &rolled["capability"], "uninstall", 1).await;
    assert_eq!(code, 200, "{removed}");
    assert_eq!(create(&core, "removed-unpinned", editor(None)).await.0, 400);
    assert_eq!(
        create(&core, "removed-pin", editor(Some(&rolled["capability"])))
            .await
            .0,
        400
    );
    // Ordinary T1/T2 and non-template creation remain available.
    for id in ["T1", "T2"] {
        let mut body = editor(None);
        body["attrs"]["archeaxis_template"]["template_id"] = json!(id);
        assert_eq!(create(&core, id, body).await.0, 201);
    }
    assert_eq!(
        create(&core, "ordinary", json!({"type":"doc","content":[]}))
            .await
            .0,
        201
    );
    for doc in [&pinned, &legacy, &newer] {
        let id = doc["document_id"].as_str().unwrap();
        assert_eq!(
            read(&core, &format!("/api/v1/documents/{id}/versions/1")).await,
            *doc
        );
        let current = read(&core, &format!("/api/v1/documents/{id}")).await;
        let result = call(
            &core,
            "PUT",
            &format!("/api/v1/documents/{id}/draft"),
            "human",
            json!({"expected_version":current["version"],"editor_json":current["editor_json"]}),
        )
        .await;
        assert_eq!(result.0, 200, "{result:?}");
    }
    assert_eq!(
        read(&core, "/api/v1/learning/events/t3-learning").await,
        history
    );
    assert_eq!(
        read(&core, &format!("/api/v1/knowledge-items/{kid}/v3")).await,
        knowledge
    );
    drop(core);
    let core = router(dir.path()).await;
    assert_eq!(state(&core).await, removed["capability"]);
    assert_eq!(
        read(&core, "/api/v1/learning/events/t3-learning").await,
        history
    );
    assert_eq!(
        read(&core, &format!("/api/v1/knowledge-items/{kid}/v3")).await,
        knowledge
    );
    for doc in [&pinned, &legacy, &newer] {
        assert_eq!(
            read(
                &core,
                &format!(
                    "/api/v1/documents/{}/versions/1",
                    doc["document_id"].as_str().unwrap()
                )
            )
            .await,
            *doc
        );
    }
    let (code, installed) = change(&core, &removed["capability"], "install", 2).await;
    assert_eq!(code, 200, "{installed}");
    assert_eq!(
        create(&core, "reinstalled", editor(Some(&installed["capability"])))
            .await
            .0,
        201
    );
}

#[tokio::test]
async fn stale_epoch_tamper_unknown_version_and_nonhuman_fail_without_state_or_document_writes() {
    let dir = tempfile::tempdir().unwrap();
    let core = router(dir.path()).await;
    let before = state(&core).await;
    let empty = read(&core, "/api/v1/documents").await;
    let base = json!({"expected_epoch":0,"action":"update","version":2,"sha256":before["available_definitions"][1]["sha256"]});
    for (key, value, code) in [
        ("expected_epoch", json!(1), 409),
        ("version", json!(99), 400),
        ("sha256", json!("0".repeat(64)), 400),
        ("action", json!("execute"), 400),
    ] {
        let mut body = base.clone();
        body[key] = value;
        assert_eq!(
            call(
                &core,
                "PUT",
                "/api/v1/capabilities/template.T3/definition",
                "human",
                body
            )
            .await
            .0,
            code
        );
        assert_eq!(state(&core).await, before);
    }
    assert_eq!(
        call(
            &core,
            "PUT",
            "/api/v1/capabilities/template.T3/definition",
            "machine",
            base
        )
        .await
        .0,
        403
    );
    for mutation in ["hash", "version", "epoch", "snapshot"] {
        let mut body = editor(Some(&before));
        let pin = &mut body["attrs"]["archeaxis_template"]["definition"];
        match mutation {
            "hash" => pin["sha256"] = json!("a".repeat(64)),
            "version" => pin["version"] = json!(2),
            "epoch" => pin["application_epoch"] = json!(1),
            _ => pin["snapshot"]["fields"]["injected"] = json!("not bundled"),
        }
        assert_eq!(create(&core, mutation, body).await.0, 400);
    }
    assert_eq!(read(&core, "/api/v1/documents").await, empty);
    let (code, changed) = change(&core, &before, "update", 2).await;
    assert_eq!(code, 200);
    assert_eq!(change(&core, &before, "disable", 1).await.0, 409);
    assert_eq!(state(&core).await, changed["capability"]);
    let (code, doc) = create(&core, "locked", editor(Some(&changed["capability"]))).await;
    assert_eq!(code, 201);
    let mut altered = doc["editor_json"].clone();
    altered["attrs"]["archeaxis_template"]["definition"] = before["definition"].clone();
    assert_eq!(
        call(
            &core,
            "PUT",
            &format!(
                "/api/v1/documents/{}/draft",
                doc["document_id"].as_str().unwrap()
            ),
            "human",
            json!({"expected_version":1,"editor_json":altered})
        )
        .await
        .0,
        400
    );
    assert_eq!(
        read(
            &core,
            &format!("/api/v1/documents/{}", doc["document_id"].as_str().unwrap())
        )
        .await,
        doc
    );
}

#[tokio::test]
async fn general_capability_switch_cannot_bypass_uninstall_or_reuse_a_stale_epoch() {
    let dir = tempfile::tempdir().unwrap();
    let core = router(dir.path()).await;
    let initial = state(&core).await;
    let route = "/api/v1/capabilities/template.T3/enabled";
    let (code, disabled) = call(&core, "PUT", route, "human", json!({"enabled":false})).await;
    assert_eq!(code, 200, "{disabled}");
    let disabled = state(&core).await;
    assert_eq!(disabled["state_epoch"], 1);
    assert_eq!(disabled["enabled"], false);
    assert_eq!(change(&core, &initial, "update", 2).await.0, 409);
    assert_eq!(create(&core, "disabled-legacy", editor(None)).await.0, 400);
    let (code, _) = call(&core, "PUT", route, "human", json!({"enabled":true})).await;
    assert_eq!(code, 200);
    let enabled = state(&core).await;
    assert_eq!(enabled["state_epoch"], 2);
    assert_eq!(
        create(&core, "stale-pin", editor(Some(&initial))).await.0,
        400
    );
    let (code, removed) = change(&core, &enabled, "uninstall", 1).await;
    assert_eq!(code, 200);
    assert_eq!(
        call(&core, "PUT", route, "human", json!({"enabled":true}))
            .await
            .0,
        400
    );
    assert_eq!(state(&core).await, removed["capability"]);
    assert_eq!(
        create(&core, "uninstalled-legacy", editor(None)).await.0,
        400
    );
}

#[tokio::test]
async fn first_party_template_has_versioned_definition_in_same_capability_center() {
    let dir = tempfile::tempdir().unwrap();
    let router = router(dir.path()).await;
    let record = state(&router).await;
    assert_eq!(record["provider"]["kind"], "first-party-data-only");
    assert_eq!(record["definition"]["snapshot"]["template_id"], "T3");
    assert_eq!(record["installed"], true);
    assert_eq!(record["enabled"], true);
    assert_eq!(record["definition"]["sha256"].as_str().unwrap().len(), 64);
}
