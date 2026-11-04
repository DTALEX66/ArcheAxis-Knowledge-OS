//! Read-only OpenMAIC course-package projection.
//!
//! The projection answers scene count, type distribution and recorded playability
//! from reports Core already stored. These cases build the persisted candidate
//! Documents directly, so no Node provider, model or renderer runs; that is also
//! what the projection itself must never do.
use archeaxis_application::executor::Executor;
use archeaxis_domain::{course, document};
use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::path::Path;
use tower::ServiceExt;

const PROJECTION_ROUTE: &str = "/api/v1/courses/openmaic/package-projection";

fn snapshot() -> Value {
    json!({"document_id":"doc_material","version":1,
        "content_sha256":"a".repeat(64)})
}

fn slide_request(request_id: &str, lossless: bool) -> Value {
    let mut content = json!({"elements":[text_element("e1","first line")]});
    if !lossless {
        content["extra_note"] = json!("a field the donor projection does not carry");
    }
    json!({"schema":"archeaxis.openmaic-scene-build/v1","request_id":request_id,"attempt":1,
        "source":snapshot(),"stage_id":"stage_1","scene_id":"scene_1",
        "outline":{"id":"outline_1","type":"slide","title":"Slide one","order":0},
        "content":content,"actions":[]})
}

fn slide_scene(animations: bool) -> Value {
    json!({"type":"slide","content":{"canvas":{
        "elements":[text_element("e1","first line")],
        "background":null,
        "animations":if animations {json!([{"kind":"fade"}])} else {json!([])}}}})
}

fn text_element(id: &str, text: &str) -> Value {
    json!({"type":"text","id":id,"content":text,"left":0.0,"top":0.0,
        "width":100.0,"height":50.0,"rotate":0.0})
}

fn quiz_scene() -> Value {
    json!({"type":"quiz","content":{"questions":[{"id":"q1","type":"single",
        "question":"Which one?","options":[{"label":"A","value":"A"},{"label":"B","value":"B"}],
        "answer":["B"]}]}})
}

fn quiz_request(request_id: &str) -> Value {
    json!({"schema":"archeaxis.openmaic-scene-build/v1","request_id":request_id,"attempt":1,
        "source":snapshot(),"stage_id":"stage_1","scene_id":"scene_2",
        "outline":{"id":"outline_2","type":"quiz","title":"Quiz","order":1},
        "content":{"questions":[{"id":"q1","type":"single","question":"Which one?",
            "options":[{"label":"A","value":"A"},{"label":"B","value":"B"}],"answer":["B"]}]},
        "actions":[]})
}

/// The exact stored shape a v2 commit writes, derived by Core from the request.
fn v2_attrs(request: &Value, scene: &Value) -> Value {
    let frame = format!("{}\n", serde_json::to_string(request).unwrap());
    json!({"schema":"archeaxis.openmaic-scene-document/v2",
        "create_request_id":request["request_id"],
        "input_sha256":"b".repeat(64),
        "request_frame":frame,
        "worker_document":{"scene":scene},
        "contract":course::openmaic_projection(request),
        "render":course::openmaic_render_contract(scene)})
}

fn create(conn: &mut rusqlite::Connection, title: &str, attrs: Option<Value>) -> String {
    let editor = match attrs {
        Some(attrs) => json!({"type":"doc",
            "attrs":{"archeaxis_openmaic_scene_candidate":attrs},
            "content":[{"type":"paragraph","attrs":{"block_id":"b1"},
                "content":[{"type":"text","text":title}]}]}),
        None => json!({"type":"doc","content":[]}),
    };
    document::create_optional(conn, None, None, title, editor).unwrap()["document_id"]
        .as_str()
        .unwrap()
        .to_owned()
}

async fn call(router: &axum::Router, body: &Value, actor: Option<&str>) -> (StatusCode, Value) {
    let mut builder = Request::builder()
        .method("POST")
        .uri(PROJECTION_ROUTE)
        .header("content-type", "application/json");
    if let Some(actor) = actor {
        builder = builder.header("x-archeaxis-actor", actor);
    }
    let response = router
        .clone()
        .oneshot(builder.body(Body::from(body.to_string())).unwrap())
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

async fn router(conn: rusqlite::Connection, dir: &tempfile::TempDir) -> axum::Router {
    // The Core must open the database alone, so the fixture connection is closed.
    drop(conn);
    let executor = Executor::open_routes(
        &dir.path().join("workspace.sqlite"),
        &dir.path().join("staging"),
        Path::new("unused-python"),
        &dir.path().join("staging").join("unused-worker"),
        &[],
    )
    .await
    .unwrap();
    archeaxis_api::runtime::router(executor)
}

fn workspace() -> (tempfile::TempDir, rusqlite::Connection) {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    (dir, conn)
}

#[tokio::test]
async fn a_fully_recorded_package_reports_its_scenes_and_types() {
    let (dir, mut conn) = workspace();
    let slide = create(
        &mut conn,
        "Slide scene",
        Some(v2_attrs(
            &slide_request("scene_a", true),
            &slide_scene(false),
        )),
    );
    let quiz = create(
        &mut conn,
        "Quiz scene",
        Some(v2_attrs(&quiz_request("scene_b"), &quiz_scene())),
    );
    let router = router(conn, &dir).await;

    let (status, body) = call(
        &router,
        &json!({"document_ids":[slide, quiz]}),
        Some("human"),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{body}");
    assert_eq!(
        body["schema"],
        "archeaxis.openmaic-course-package-projection/v1"
    );
    assert_eq!(body["document_count"], 2);
    assert_eq!(body["scene_count"], 2);
    assert_eq!(body["reported_scene_count"], 2);
    assert_eq!(body["non_scene_document_count"], 0);
    assert_eq!(body["by_scene_type"]["slide"], 1);
    assert_eq!(body["by_scene_type"]["quiz"], 1);
    assert_eq!(body["playable_scene_count"], 2);
    assert_eq!(body["not_playable_scene_count"], 0);
    assert_eq!(body["unknown_scene_count"], 0);
    assert_eq!(body["all_playable"], true);
    // The projection itself never renders, validates a course or authorizes output.
    assert_eq!(body["renderer_executed"], false);
    assert_eq!(body["rendering_authorized"], false);
    assert_eq!(body["server_validation"], "NONE");
    assert_eq!(body["scenes"][0]["playability"], "playable");
    assert_eq!(body["scenes"][0]["lossless"], true);
    assert_eq!(body["scenes"][1]["scene_type"], "quiz");
}

#[tokio::test]
async fn unsupported_legacy_and_missing_entries_are_reported_not_assumed() {
    let (dir, mut conn) = workspace();
    // An animated slide cannot be played by the inert text renderer.
    let animated = create(
        &mut conn,
        "Animated scene",
        Some(v2_attrs(
            &slide_request("scene_c", true),
            &slide_scene(true),
        )),
    );
    // A legacy v1 candidate never recorded a render report.
    let legacy = create(
        &mut conn,
        "Legacy scene",
        Some(json!({"schema":"archeaxis.openmaic-scene-document/v1",
            "create_request_id":"legacy_request"})),
    );
    // A plain document is not a scene candidate at all.
    let plain = create(&mut conn, "Ordinary note", None);
    let router = router(conn, &dir).await;

    let (status, body) = call(
        &router,
        &json!({"document_ids":[animated, legacy, plain, "doc_absent"]}),
        Some("human"),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{body}");
    assert_eq!(body["document_count"], 4);
    assert_eq!(body["scene_count"], 2);
    assert_eq!(body["reported_scene_count"], 1);
    assert_eq!(body["non_scene_document_count"], 2);
    assert_eq!(body["playable_scene_count"], 0);
    assert_eq!(body["not_playable_scene_count"], 1);
    assert_eq!(body["unknown_scene_count"], 1);
    assert_eq!(body["all_playable"], false);
    let statuses: Vec<&str> = body["scenes"]
        .as_array()
        .unwrap()
        .iter()
        .map(|scene| scene["status"].as_str().unwrap())
        .collect();
    assert_eq!(
        statuses,
        vec![
            "recorded",
            "report_not_recorded",
            "not_a_scene_candidate",
            "missing"
        ]
    );
    assert_eq!(body["scenes"][0]["unsupported_count"], 1);
    assert_eq!(body["scenes"][0]["playability"], "not_playable");
    assert_eq!(body["scenes"][1]["playability"], "unknown");
}

#[tokio::test]
async fn an_edited_report_is_not_quoted_as_playable() {
    let (dir, mut conn) = workspace();
    let request = slide_request("scene_d", true);
    let scene = slide_scene(false);
    let mut attrs = v2_attrs(&request, &scene);
    // A later edit rewrites the recorded verdict; the projection must not trust it.
    attrs["render"] = json!({"schema":"archeaxis.openmaic-scene-render/v1",
        "playable":true,"scene_type":"slide","unsupported":[]});
    let edited = create(&mut conn, "Edited scene", Some(attrs));
    let router = router(conn, &dir).await;

    let (status, body) = call(&router, &json!({"document_ids":[edited]}), Some("human")).await;
    assert_eq!(status, StatusCode::OK, "{body}");
    assert_eq!(body["scene_count"], 1);
    assert_eq!(body["reported_scene_count"], 0);
    assert_eq!(body["unknown_scene_count"], 1);
    assert_eq!(body["all_playable"], false);
    assert_eq!(body["scenes"][0]["status"], "report_mismatch");
    assert_eq!(body["scenes"][0]["playability"], "unknown");
}

#[tokio::test]
async fn the_projection_is_human_only_and_bounds_its_request() {
    let (dir, mut conn) = workspace();
    let scene = create(
        &mut conn,
        "Slide scene",
        Some(v2_attrs(
            &slide_request("scene_e", true),
            &slide_scene(false),
        )),
    );
    let router = router(conn, &dir).await;

    let body = json!({"document_ids":[scene]});
    assert_eq!(
        call(&router, &body, Some("machine")).await.0,
        StatusCode::FORBIDDEN
    );
    assert_eq!(
        call(&router, &json!({"document_ids":[]}), Some("human"))
            .await
            .0,
        StatusCode::UNPROCESSABLE_ENTITY
    );
    assert_eq!(
        call(
            &router,
            &json!({"document_ids":[scene, scene]}),
            Some("human")
        )
        .await
        .0,
        StatusCode::UNPROCESSABLE_ENTITY
    );
    let too_many: Vec<String> = (0..65).map(|index| format!("doc_{index}")).collect();
    assert_eq!(
        call(&router, &json!({"document_ids":too_many}), Some("human"))
            .await
            .0,
        StatusCode::UNPROCESSABLE_ENTITY
    );
    // Undeclared fields are refused rather than silently ignored.
    assert_eq!(
        call(
            &router,
            &json!({"document_ids":[scene],"unexpected":true}),
            Some("human")
        )
        .await
        .0,
        StatusCode::UNPROCESSABLE_ENTITY
    );
}
