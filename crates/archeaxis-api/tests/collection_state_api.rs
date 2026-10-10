//! Real in-process HTTP + canonical SQLite integration; no browser/native/process proof.
use archeaxis_domain::collection::ENGINE_VERSION;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;
async fn call(app: &Router, method: &str, path: &str, body: Value, actor: &str) -> (u16, Value) {
    let response = app
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
    (status, serde_json::from_slice(&bytes).unwrap_or_default())
}
fn definition(target: &str) -> Value {
    json!({"schema":"archeaxis.collection/v1","properties":[
 {"property_id":"score","name":"Score","kind":"number"},
 {"property_id":"name","name":"Name","kind":"text"},
 {"property_id":"stage","name":"Stage","kind":"select","options":["todo","done"]},
 {"property_id":"day","name":"Date","kind":"date","timezone":"Asia/Shanghai"},
 {"property_id":"double","name":"Computed","kind":"formula","formula":{"dialect":ENGINE_VERSION,"engine_version":ENGINE_VERSION,"expression":{"op":"multiply","left":{"op":"property","key":"score"},"right":{"op":"literal","value":2}},"dependencies":["score"],"output_type":"number","original_expression":"score * 2","source_payload":{"source_dialect":"SYNTHETIC;not platform-qualified"}}}
 ],"records":[
 {"record_id":"r_zero","reference":{"kind":"document","document_id":target,"version":1},"values":{"score":0,"name":"Before filter","stage":"todo","day":"2026-10-10"}},
 {"record_id":"r_forty","reference":{"kind":"document","document_id":target,"version":1},"values":{"score":40,"name":"Forty","stage":"done","day":"2026-10-11"}},
 {"record_id":"r_twenty","reference":{"kind":"document","document_id":target,"version":1},"values":{"score":20,"name":"Twenty","stage":"todo","day":"2026-10-10"},"source_payload":{"foreign_field":{"keep":[1,2,3]}}},
 {"record_id":"r_thirty","reference":{"kind":"document","document_id":target,"version":1},"values":{"score":30,"name":"Thirty","stage":"done","day":"2026-10-11"}}
 ],"views":[
 {"view_id":"table","name":"Table","kind":"table","sort":[{"property_id":"score","descending":false}]},
 {"view_id":"list","name":"List","kind":"list","sort":[{"property_id":"score","descending":false}]},
 {"view_id":"board","name":"Board","kind":"board","group_by":"stage","sort":[{"property_id":"score","descending":false}]},
 {"view_id":"calendar","name":"Calendar","kind":"calendar","date_property":"day","sort":[{"property_id":"score","descending":false}]},
 {"view_id":"gallery","name":"Gallery","kind":"gallery","sort":[{"property_id":"score","descending":false}]},
 {"view_id":"filtered","name":"Filtered","kind":"list","filter":{"op":"greater_than","property_id":"score","value":15},"sort":[{"property_id":"score","descending":false}]}
 ],"source_payload":{"legacy_layout":{"preserved":true}}})
}
fn envelope(raw: Value) -> Value {
    json!({"type":"doc","attrs":{"archeaxis_collection":raw,"foreign_attrs":{"exact":[1,2]}},"content":[{"type":"paragraph","attrs":{"block_id":"stable_collection_body"},"content":[{"type":"text","text":"Collection original body"}]}]})
}
async fn target(app: &Router) -> Value {
    let (status,d)=call(app,"POST","/api/v1/documents",json!({"title":"Immutable member","create_request_id":"collection_api_member","editor_json":{"type":"doc","content":[]}}),"human").await;
    assert_eq!(status, 201, "{d}");
    d
}
async fn create(app: &Router, raw: Value, key: &str) -> Value {
    let (status, d) = call(
        app,
        "POST",
        "/api/v1/documents",
        json!({"title":"Collection","create_request_id":key,"editor_json":envelope(raw)}),
        "human",
    )
    .await;
    assert_eq!(status, 201, "{d}");
    d
}
fn doc_path(d: &Value) -> String {
    format!("/api/v1/documents/{}", d["document_id"].as_str().unwrap())
}
async fn query(app: &Router, path: &str, view: &str, extra: &str) -> Value {
    let (status, p) = call(
        app,
        "GET",
        &format!("{path}/collection?view_id={view}{extra}"),
        json!(null),
        "human",
    )
    .await;
    assert_eq!(status, 200, "{p}");
    p
}
fn counts(db: &std::path::Path) -> (i64, i64) {
    let c = rusqlite::Connection::open_with_flags(db, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
        .unwrap();
    (
        c.query_row("SELECT count(*) FROM documents", [], |r| r.get(0))
            .unwrap(),
        c.query_row("SELECT count(*) FROM document_versions", [], |r| r.get(0))
            .unwrap(),
    )
}
fn row_ids(p: &Value) -> Vec<String> {
    p["items"]
        .as_array()
        .unwrap()
        .iter()
        .map(|r| r["record_id"].as_str().unwrap().to_owned())
        .collect()
}
#[tokio::test]
async fn five_views_use_one_definition_filter_before_paging_and_never_write_computed_cells() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let member = target(&app).await;
    let raw = definition(member["document_id"].as_str().unwrap());
    let d = create(&app, raw.clone(), "five_views").await;
    let path = doc_path(&d);
    let before = counts(&db);
    let expected = vec!["r_zero", "r_twenty", "r_thirty", "r_forty"];
    for view in ["table", "list", "board", "calendar", "gallery"] {
        let p = query(&app, &path, view, "&limit=100").await;
        assert_eq!(p["view"]["kind"], view);
        assert_eq!(p["document_id"], d["document_id"]);
        assert_eq!(p["version"], 1);
        assert_eq!(p["content_sha256"], d["content_sha256"]);
        assert_eq!(p["definition"], raw);
        assert_eq!(p["canonical_writer"], "Document");
        assert_eq!(row_ids(&p), expected);
        assert_eq!(p["items"][1]["values"]["double"], 40.0);
    }
    let board = query(&app, &path, "board", "").await;
    assert_eq!(board["group_counts"]["\"todo\""], 2);
    assert_eq!(board["group_counts"]["\"done\""], 2);
    let calendar = query(&app, &path, "calendar", "").await;
    assert_eq!(calendar["group_counts"]["\"2026-10-10\""], 2);
    assert_eq!(calendar["group_counts"]["\"2026-10-11\""], 2);
    for (offset, id) in [(0, "r_twenty"), (1, "r_thirty"), (2, "r_forty")] {
        let p = query(
            &app,
            &path,
            "filtered",
            &format!("&offset={offset}&limit=1"),
        )
        .await;
        assert_eq!(p["total"], 3);
        assert_eq!(p["items"][0]["record_id"], id);
        if offset < 2 {
            assert_eq!(p["next_offset"], offset + 1);
        } else {
            assert!(p["next_offset"].is_null());
        }
    }
    assert_eq!(counts(&db), before);
    assert_eq!(call(&app, "GET", &path, json!(null), "human").await.1, d);
    assert_eq!(
        call(&app, "GET", &doc_path(&member), json!(null), "human")
            .await
            .1,
        member
    );
    for record in d["editor_json"]["attrs"]["archeaxis_collection"]["records"]
        .as_array()
        .unwrap()
    {
        assert!(record["values"].get("double").is_none());
    }
}
#[tokio::test]
async fn canonical_create_retry_draft_conflict_historical_views_and_sqlite_reopen_keep_members_pinned()
 {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let member = target(&app).await;
    let raw = definition(member["document_id"].as_str().unwrap());
    let body = json!({"title":"Collection","create_request_id":"collection_retry","editor_json":envelope(raw)});
    let (status, first) = call(&app, "POST", "/api/v1/documents", body.clone(), "human").await;
    assert_eq!(status, 201);
    let before = counts(&db);
    assert_eq!(
        call(&app, "POST", "/api/v1/documents", body, "human").await,
        (201, first.clone())
    );
    assert_eq!(counts(&db), before);
    let path = doc_path(&first);
    let mut editor = first["editor_json"].clone();
    editor["attrs"]["archeaxis_collection"]["records"]
        .as_array_mut()
        .unwrap()
        .remove(0);
    let save = json!({"expected_version":1,"editor_json":editor});
    let (status, saved) = call(&app, "PUT", &format!("{path}/draft"), save.clone(), "human").await;
    assert_eq!(status, 200, "{saved}");
    assert_eq!(saved["version"], 2);
    assert_eq!(
        saved["editor_json"]["attrs"]["foreign_attrs"],
        first["editor_json"]["attrs"]["foreign_attrs"]
    );
    assert_eq!(
        saved["editor_json"]["content"],
        first["editor_json"]["content"]
    );
    let post_save = counts(&db);
    assert_eq!(
        call(&app, "PUT", &format!("{path}/draft"), save, "human")
            .await
            .0,
        409
    );
    assert_eq!(counts(&db), post_save);
    assert_eq!(query(&app, &path, "table", "&version=1").await["total"], 4);
    assert_eq!(query(&app, &path, "table", "&version=2").await["total"], 3);
    let member_path = doc_path(&member);
    assert_eq!(
        call(
            &app,
            "PUT",
            &format!("{member_path}/draft"),
            json!({"expected_version":1,"editor_json":{"type":"doc","content":[]}}),
            "human"
        )
        .await
        .0,
        200
    );
    drop(app);
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    assert_eq!(
        call(&app, "GET", &path, json!(null), "human").await.1,
        saved
    );
    assert_eq!(
        call(
            &app,
            "GET",
            &format!("{path}/versions/1"),
            json!(null),
            "human"
        )
        .await
        .1,
        first
    );
    let old = query(&app, &path, "table", "&version=1").await;
    assert_eq!(old["total"], 4);
    assert_eq!(old["items"][0]["reference"]["version"], 1);
    assert_eq!(
        call(
            &app,
            "GET",
            &format!("{member_path}/versions/1"),
            json!(null),
            "human"
        )
        .await
        .1,
        member
    );
}
#[tokio::test]
async fn formula_errors_are_explicit_filter_errors_are_not_empty_success_and_export_preserves_definition()
 {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let member = target(&app).await;
    let mut raw = definition(member["document_id"].as_str().unwrap());
    raw["properties"][4]["formula"]["expression"]["op"] = json!("divide");
    raw["properties"][4]["formula"]["expression"]["right"]["value"] = json!(0);
    raw["views"].as_array_mut().unwrap().push(json!({"view_id":"broken_filter","name":"Failed formula filter","kind":"list","filter":{"op":"greater_than","property_id":"double","value":1}}));
    let d = create(&app, raw.clone(), "formula_errors").await;
    let path = doc_path(&d);
    let before = counts(&db);
    let p = query(&app, &path, "table", "").await;
    for r in p["items"].as_array().unwrap() {
        assert!(r["values"].get("double").is_none());
        assert_eq!(r["formulas"][0]["status"], "error");
        assert!(
            r["formula_errors"]["double"]
                .as_str()
                .unwrap()
                .contains("DivisionByZero")
        );
    }
    let (status, error) = call(
        &app,
        "GET",
        &format!("{path}/collection?view_id=broken_filter"),
        json!(null),
        "human",
    )
    .await;
    assert_eq!(status, 400);
    assert!(
        error["message"]
            .as_str()
            .unwrap()
            .contains("formula failed")
    );
    let (status, export) = call(
        &app,
        "GET",
        &format!("{path}/export?format=markdown"),
        json!(null),
        "human",
    )
    .await;
    assert_eq!(status, 200);
    let file = export["files"]
        .as_array()
        .unwrap()
        .iter()
        .find(|f| f["path"] == "manifest.json")
        .unwrap();
    let manifest: Value = serde_json::from_str(file["content"].as_str().unwrap()).unwrap();
    assert_eq!(manifest["document"], d);
    assert_eq!(manifest["collection_export"]["definition"], raw);
    assert_eq!(manifest["collection_export"]["full_media_package"], false);
    assert!(
        manifest["collection_export"]["computed_values"]
            .as_str()
            .unwrap()
            .contains("NOT_EMBEDDED")
    );
    assert!(
        manifest["collection_export"]["definition"]["records"][0]["values"]
            .get("double")
            .is_none()
    );
    assert_eq!(counts(&db), before);
    assert_eq!(call(&app, "GET", &path, json!(null), "human").await.1, d);
}
#[tokio::test]
async fn invalid_pages_missing_versions_bad_ast_and_machine_writes_fail_without_partial_versions() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let member = target(&app).await;
    let raw = definition(member["document_id"].as_str().unwrap());
    let d = create(&app, raw.clone(), "negative_parameters").await;
    let path = doc_path(&d);
    let before = counts(&db);
    for suffix in [
        "view_id=absent",
        "view_id=table&version=0",
        "view_id=table&limit=0",
        "view_id=table&limit=101",
        "view_id=table&offset=501",
        "view_id=table&offset=-1",
    ] {
        assert_eq!(
            call(
                &app,
                "GET",
                &format!("{path}/collection?{suffix}"),
                json!(null),
                "human"
            )
            .await
            .0,
            400,
            "{suffix}"
        );
    }
    assert_eq!(
        call(
            &app,
            "GET",
            &format!("{path}/collection?view_id=table&version=999"),
            json!(null),
            "human"
        )
        .await
        .0,
        404
    );
    let body = json!({"title":"Machine cannot author","create_request_id":"machine_attempt","editor_json":envelope(raw.clone())});
    assert_eq!(
        call(&app, "POST", "/api/v1/documents", body, "machine")
            .await
            .0,
        403
    );
    assert_eq!(
        call(
            &app,
            "PUT",
            &format!("{path}/draft"),
            json!({"expected_version":1,"editor_json":d["editor_json"]}),
            "machine"
        )
        .await
        .0,
        403
    );
    let mut invalid = raw;
    invalid["properties"][4]["formula"]["expression"] =
        json!({"op":"eval","code":"process.exit()"});
    let rejected_editor = envelope(invalid);
    assert_eq!(
        call(
            &app,
            "PUT",
            &format!("{path}/draft"),
            json!({"expected_version":1,"editor_json":rejected_editor.clone()}),
            "human"
        )
        .await
        .0,
        400
    );
    assert_eq!(call(&app,"POST","/api/v1/documents",json!({"title":"Rejected unsafe formula","create_request_id":"rejected_eval","editor_json":rejected_editor}),"human").await.0,400);
    assert_eq!(counts(&db), before);
    assert_eq!(call(&app, "GET", &path, json!(null), "human").await.1, d);
}
