//! SYNTHETIC inert asset material through actual HTTP/Store; no model or tool execution.
//! Production launch-token authority is separately tested in launch_auth.rs.
use archeaxis_store_sqlite::writer::Store;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
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
                .body(Body::from(if body.is_null() {
                    String::new()
                } else {
                    body.to_string()
                }))
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
fn snapshot(d: &Value) -> Value {
    json!({"document_id":d["document_id"],"version":d["version"],"content_sha256":d["content_sha256"]})
}
fn asset(kind: &str) -> Value {
    json!({"schema":"archeaxis.ai-asset/v1","kind":kind,
    "content":{"inert_text":"SYNTHETIC_SECRET_PACKET_CONTENT","unknown":{"command":"never execute"}},
    "purpose":"owned API purpose","scope":[],"provenance":[],"expires_at":null,"state":"candidate",
    "members":[],"conflicts":[],"revises":null,"review":null,"source_payload":{"unsupported_dialect":"byte-preserved inert data"}})
}
fn envelope(a: Value) -> Value {
    json!({"type":"doc","content":[],"attrs":{"archeaxis_ai_asset":a,"unknown_future":{"keep":"exact"}}})
}
async fn create(router: &Router, key: &str, editor: Value) -> Value {
    let body =
        json!({"create_request_id":key,"title":"owned synthetic asset","editor_json":editor});
    let (status, d) = call(router, "POST", "/api/v1/documents", "human", body.clone()).await;
    assert_eq!(status, 201, "{d}");
    assert_eq!(
        call(router, "POST", "/api/v1/documents", "human", body)
            .await
            .1,
        d
    );
    d
}
async fn save(router: &Router, d: &Value, editor: Value) -> (u16, Value) {
    call(
        router,
        "PUT",
        &format!(
            "/api/v1/documents/{}/draft",
            d["document_id"].as_str().unwrap()
        ),
        "human",
        json!({"expected_version":d["version"],"editor_json":editor}),
    )
    .await
}
async fn rubric(router: &Router) -> Value {
    let request = json!({"schema":"archeaxis.machine-rubric/v1","request_id":"fixed-asset-rubric-api",
        "title":"owned fixed rubric","purpose":"asset applicability","criteria":[{"criterion_id":"fit","label":"Fit","expectation":"human fixture observed fit"}],"sources":[]});
    let (code, d) = call(router, "POST", "/api/v1/machine/rubrics", "human", request).await;
    assert_eq!(code, 201, "{d}");
    d
}
async fn adopted(router: &Router, key: &str, a: Value, r: &Value) -> Value {
    let candidate = create(router, key, envelope(a)).await;
    let mut editor = candidate["editor_json"].clone();
    editor["attrs"]["archeaxis_ai_asset"]["state"] = json!("adopted");
    editor["attrs"]["archeaxis_ai_asset"]["review"] = json!({"asset":snapshot(&candidate),"rubric":snapshot(r),
        "reviewer":"SYNTHETIC human observer","basis":"fixture observation only","judgments":[{"criterion_id":"fit","outcome":"passed","basis":"fixture observed fit"}],"outcome":"passed"});
    let (code, d) = save(router, &candidate, editor).await;
    assert_eq!(code, 200, "{d}");
    d
}
async fn grant(router: &Router, key: &str, a: &Value, consumer: &str) -> Value {
    create(router,key,json!({"type":"doc","content":[],"attrs":{"archeaxis_asset_context_grant":{
        "schema":"archeaxis.asset-context-grant/v1","asset":snapshot(a),"purpose":"owned API purpose",
        "consumer":consumer,"operations":["read_packet"],"authorization_basis":"explicit SYNTHETIC human grant","expires_at":null,"state":"granted"}}})).await
}
fn request(key: &str, a: &Value, g: &Value, consumer: &str) -> Value {
    json!({"request_id":key,"asset":snapshot(a),"grant":snapshot(g),"purpose":"owned API purpose","consumer":consumer,"operation":"read_packet"})
}

#[tokio::test]
async fn candidate_review_adoption_consumer_exact_retry_and_redacted_audit_survive_reopen() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("assets.sqlite");
    let store = Store::open(&db).unwrap();
    let router = archeaxis_api::router(store.clone());
    let candidate = create(&router, "inert-candidate", envelope(asset("memory"))).await;
    assert_eq!(
        candidate["editor_json"]["attrs"]["unknown_future"]["keep"],
        "exact"
    );
    let mut unreviewed = candidate["editor_json"].clone();
    unreviewed["attrs"]["archeaxis_ai_asset"]["state"] = json!("adopted");
    assert_eq!(save(&router, &candidate, unreviewed).await.0, 400);
    let r = rubric(&router).await;
    let a = adopted(&router, "adopted-memory", asset("memory"), &r).await;
    let mut future_rubric = r["editor_json"].clone();
    future_rubric["attrs"]["archeaxis_machine_rubric"]["criteria"].as_array_mut().unwrap().push(json!({"criterion_id":"future","label":"Future criterion","expectation":"not part of original review"}));
    let (code, rubric_v2) = save(&router, &r, future_rubric).await;
    assert_eq!(code, 200, "{rubric_v2}");
    assert_eq!(rubric_v2["version"], 2);
    assert_eq!(
        a["editor_json"]["attrs"]["archeaxis_ai_asset"]["review"]["rubric"],
        snapshot(&r)
    );
    let (_, old_rubric) = call(
        &router,
        "GET",
        &format!(
            "/api/v1/documents/{}/versions/1",
            r["document_id"].as_str().unwrap()
        ),
        "human",
        Value::Null,
    )
    .await;
    assert_eq!(old_rubric, r);
    let manual = grant(&router, "grant-manual", &a, "manual-context-packet").await;
    let local = grant(&router, "grant-local", &a, "local-machine").await;
    let req = request("packet-same-request", &a, &manual, "manual-context-packet");
    let (code, p) = call(
        &router,
        "POST",
        "/api/v1/ai/context-packets",
        "human",
        req.clone(),
    )
    .await;
    assert_eq!(code, 200, "{p}");
    assert_eq!(p["duplicate"], false);
    assert_eq!(
        p["packet_sha256"],
        archeaxis_domain::ai_asset::hash(&p["packet"])
    );
    assert_eq!(p["receipt"]["delivery_status"], "PREPARED_NOT_SENT_TO_PEER");
    assert_eq!(p["receipt"]["model_execution"], "NOT_EXECUTED");
    assert_eq!(p["receipt"]["tool_execution"], "NOT_EXECUTED");
    assert_eq!(p["packet"]["private_session_access"], false);
    let retry = call(
        &router,
        "POST",
        "/api/v1/ai/context-packets",
        "human",
        req.clone(),
    )
    .await;
    assert_eq!(retry.0, 200);
    assert_eq!(retry.1["duplicate"], true);
    assert_eq!(retry.1["receipt"], p["receipt"]);
    let second = grant(&router, "grant-manual-second", &a, "manual-context-packet").await;
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/ai/context-packets",
            "human",
            request("packet-same-request", &a, &second, "manual-context-packet")
        )
        .await
        .0,
        409
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/ai/context-packets",
            "machine",
            req.clone()
        )
        .await
        .0,
        403
    );
    let local_req = request("local-packet", &a, &local, "local-machine");
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/ai/context-packets",
            "human",
            local_req.clone()
        )
        .await
        .0,
        403
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/ai/context-packets",
            "machine",
            local_req
        )
        .await
        .0,
        200
    );
    let audit = p["audit_task_id"].as_str().unwrap();
    let (_, row) = call(
        &router,
        "GET",
        &format!("/api/v1/machine/tasks/{audit}"),
        "human",
        Value::Null,
    )
    .await;
    let proof: Value = serde_json::from_str(row["conditions"].as_str().unwrap()).unwrap();
    assert_eq!(proof, p["receipt"]);
    assert!(
        !proof
            .to_string()
            .contains("SYNTHETIC_SECRET_PACKET_CONTENT")
    );
    assert_eq!(row["scope"], "runtime.context.packet");
    assert_eq!(row["model_version"], "NOT_RUN_CONTEXT_PACKET");
    assert_eq!(row["outcome"], "unmeasured");
    let before = store
        .submit(|c| {
            assert_eq!(
                c.query_row(
                    "SELECT count(*) FROM machine_tasks WHERE scope='runtime.context.packet'",
                    [],
                    |r| r.get::<_, i64>(0)
                )
                .unwrap(),
                2
            );
            assert_eq!(
                c.query_row("SELECT count(*) FROM jobs", [], |r| r.get::<_, i64>(0))
                    .unwrap(),
                0
            );
            assert_eq!(
                c.query_row("SELECT count(*) FROM learning_events", [], |r| r
                    .get::<_, i64>(0))
                    .unwrap(),
                0
            );
            c.query_row("SELECT count(*) FROM document_versions", [], |r| {
                r.get::<_, i64>(0)
            })
            .unwrap()
        })
        .await
        .unwrap();
    let mut changed = a["editor_json"].clone();
    changed["attrs"]["archeaxis_ai_asset"]["content"] = json!("edited after pass");
    assert_eq!(save(&router, &a, changed).await.0, 400);
    let id = a["document_id"].as_str().unwrap();
    assert_eq!(
        call(
            &router,
            "GET",
            &format!("/api/v1/documents/{id}/versions/1"),
            "human",
            Value::Null
        )
        .await
        .1["editor_json"]["attrs"]["archeaxis_ai_asset"]["state"],
        "candidate"
    );
    drop(router);
    drop(store);
    tokio::task::yield_now().await;
    let reopened = Store::open(&db).unwrap();
    let router = archeaxis_api::router(reopened.clone());
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/ai/context-packets",
            "human",
            req.clone()
        )
        .await
        .1["receipt"],
        p["receipt"]
    );
    let (_, restored) = call(
        &router,
        "GET",
        &format!("/api/v1/machine/tasks/{audit}"),
        "human",
        Value::Null,
    )
    .await;
    assert_eq!(restored, row);
    assert_eq!(
        reopened
            .submit(|c| c
                .query_row("SELECT count(*) FROM document_versions", [], |r| r
                    .get::<_, i64>(0))
                .unwrap())
            .await
            .unwrap(),
        before
    );
    // Independent revocation: this asset still has no withdrawn member, so the grant alone causes refusal.
    let mut revoked = manual["editor_json"].clone();
    revoked["attrs"]["archeaxis_asset_context_grant"]["state"] = json!("revoked");
    assert_eq!(save(&router, &manual, revoked).await.0, 200);
    assert_eq!(
        call(&router, "POST", "/api/v1/ai/context-packets", "human", req)
            .await
            .0,
        403
    );
    assert_eq!(
        call(
            &router,
            "GET",
            &format!("/api/v1/machine/tasks/{audit}"),
            "human",
            Value::Null
        )
        .await
        .1,
        row
    );
}

#[tokio::test]
async fn withdrawn_member_and_revoked_grant_block_even_cached_packets_without_overwriting_audit() {
    let dir = tempfile::tempdir().unwrap();
    let store = Store::open(&dir.path().join("assets.sqlite")).unwrap();
    let router = archeaxis_api::router(store.clone());
    let r = rubric(&router).await;
    let member = adopted(&router, "member", asset("rule"), &r).await;
    let mut package = asset("knowledge_package");
    package["members"] = json!([snapshot(&member)]);
    let a = adopted(&router, "package", package, &r).await;
    let g = grant(&router, "package-grant", &a, "manual-context-packet").await;
    let req = request("package-packet", &a, &g, "manual-context-packet");
    let (code, p) = call(
        &router,
        "POST",
        "/api/v1/ai/context-packets",
        "human",
        req.clone(),
    )
    .await;
    assert_eq!(code, 200);
    assert_eq!(p["packet"]["items"].as_array().unwrap().len(), 2);
    let mut withdrawn = member["editor_json"].clone();
    withdrawn["attrs"]["archeaxis_ai_asset"]["state"] = json!("withdrawn");
    assert_eq!(save(&router, &member, withdrawn).await.0, 200);
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/ai/context-packets",
            "human",
            req.clone()
        )
        .await
        .0,
        403
    );
    let mut revoked = g["editor_json"].clone();
    revoked["attrs"]["archeaxis_asset_context_grant"]["state"] = json!("revoked");
    let (code, revoked) = save(&router, &g, revoked).await;
    assert_eq!(code, 200);
    assert_eq!(
        call(&router, "POST", "/api/v1/ai/context-packets", "human", req)
            .await
            .0,
        403
    );
    assert_eq!(
        save(&router, &revoked, g["editor_json"].clone()).await.0,
        400
    );
    let (_, audit) = call(
        &router,
        "GET",
        &format!(
            "/api/v1/machine/tasks/{}",
            p["audit_task_id"].as_str().unwrap()
        ),
        "human",
        Value::Null,
    )
    .await;
    assert_eq!(
        serde_json::from_str::<Value>(audit["conditions"].as_str().unwrap()).unwrap(),
        p["receipt"]
    );
    assert_eq!(
        store
            .submit(|c| c
                .query_row(
                    "SELECT count(*) FROM machine_tasks WHERE scope='runtime.context.packet'",
                    [],
                    |r| r.get::<_, i64>(0)
                )
                .unwrap())
            .await
            .unwrap(),
        1
    );
}

#[tokio::test]
async fn twenty_one_real_namespace_objects_paginate_without_qualifying_unknown_metadata() {
    let dir = tempfile::tempdir().unwrap();
    let store = Store::open(&dir.path().join("assets.sqlite")).unwrap();
    let router = archeaxis_api::router(store.clone());
    let mut ids = std::collections::BTreeSet::new();
    for i in 0..21 {
        let d = create(&router, &format!("page-{i}"), envelope(asset("experience"))).await;
        ids.insert(d["document_id"].as_str().unwrap().to_owned());
    }
    let (code, first) = call(&router, "GET", "/api/v1/ai/assets", "human", Value::Null).await;
    assert_eq!(code, 200);
    assert_eq!(first["items"].as_array().unwrap().len(), 20);
    let cursor = first["next_cursor"].as_str().unwrap();
    let (code, last) = call(
        &router,
        "GET",
        &format!("/api/v1/ai/assets?cursor={cursor}"),
        "human",
        Value::Null,
    )
    .await;
    assert_eq!(code, 200);
    assert_eq!(last["items"].as_array().unwrap().len(), 1);
    assert!(last["next_cursor"].is_null());
    let listed: std::collections::BTreeSet<String> = first["items"]
        .as_array()
        .unwrap()
        .iter()
        .chain(last["items"].as_array().unwrap())
        .map(|d| d["document_id"].as_str().unwrap().to_owned())
        .collect();
    assert_eq!(listed, ids);
    assert_eq!(
        call(
            &router,
            "GET",
            "/api/v1/ai/assets?cursor=..%2Foutside",
            "human",
            Value::Null
        )
        .await
        .0,
        400
    );
    // Seed a historical import-only unsupported asset namespace via the test's sole Store writer.
    // New writes reject the shape; raw historical GET must not manufacture adoption or destroy it.
    let historical = json!({"type":"doc","content":[],"attrs":{"archeaxis_ai_asset":{"schema":"vendor.unknown/v99","opaque":"preserve-exact"}}});
    let original = historical.clone();
    store.submit(move|c|{
        c.execute("INSERT INTO documents(document_id,title,current_version) VALUES('unknown_asset','legacy unknown',1)",[]).unwrap();
        c.execute("INSERT INTO document_versions(document_id,version,editor_json,text_projection,content_sha256) VALUES('unknown_asset',1,?1,'',?2)",rusqlite::params![historical.to_string(),archeaxis_domain::ai_asset::hash(&historical)]).unwrap();
    }).await.unwrap();
    let (_, read) = call(
        &router,
        "GET",
        "/api/v1/documents/unknown_asset/versions/1",
        "human",
        Value::Null,
    )
    .await;
    assert_eq!(read["editor_json"], original);
    assert_eq!(save(&router, &read, original.clone()).await.0, 400);
    let (_, after) = call(
        &router,
        "GET",
        "/api/v1/documents/unknown_asset",
        "human",
        Value::Null,
    )
    .await;
    assert_eq!(after["editor_json"], original);
    assert_eq!(after["version"], 1);
    let (_, last_with_unknown) = call(
        &router,
        "GET",
        &format!("/api/v1/ai/assets?cursor={cursor}"),
        "human",
        Value::Null,
    )
    .await;
    let listed_unknown = last_with_unknown["items"]
        .as_array()
        .unwrap()
        .iter()
        .find(|d| d["document_id"] == "unknown_asset")
        .unwrap();
    assert!(
        listed_unknown.get("state").is_none(),
        "namespace discovery must not assert adoption of an unknown schema"
    );
    assert_eq!(listed_unknown["version"], 1);
}
