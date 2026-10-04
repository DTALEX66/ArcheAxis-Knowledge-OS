use archeaxis_application::executor::Executor;
use archeaxis_domain::{
    anchor, knowledge,
    source::{self, ImportOutcome},
};
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::path::{Path, PathBuf};
use tower::ServiceExt;

async fn open(dir: &Path) -> Executor {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf();
    let python: PathBuf = std::env::var_os("ARCHEAXIS_PYTHON").unwrap().into();
    Executor::open_routes(
        &dir.join("db.sqlite"),
        &dir.join("staging"),
        &python,
        &root.join("services/python-workers/transport/text_ndjson.py"),
        &[(
            "course.general",
            root.join("services/python-workers/course/worker_general_course.py"),
        )],
    )
    .await
    .unwrap()
}
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
    (
        status,
        serde_json::from_slice(&bytes)
            .unwrap_or_else(|_| json!({"raw":String::from_utf8_lossy(&bytes)})),
    )
}
async fn fixture(executor: &Executor) -> Value {
    executor.store().submit_wait(|conn| {
        let sid=match source::import_source(conn,b"An anchor locates evidence.","course.md",None).unwrap(){ImportOutcome::Imported{source_id,..}=>source_id,_=>unreachable!()};
        let revision:String=conn.query_row("SELECT sha256 FROM sources WHERE source_id=?1",[&sid],|r|r.get(0)).unwrap();
        let aid=anchor::add_anchor(conn,&sid,&revision,r#"{"line":1}"#).unwrap();
        let kid=knowledge::create_knowledge(conn,"FACTUAL_CLAIM","An anchor locates evidence.","accepted",None,Some(&aid),"human").unwrap();
        json!({"manifest":{"manifest_id":"course-1","title":"Evidence","domain_pack_id":"general","status":"candidate",
            "knowledge_components":[{"component_id":"kc-1","kind":"fact","title":"Anchor","statement":"An anchor locates evidence.","source_ids":[sid]}],
            "learning_objectives":[{"objective_id":"obj-1","title":"Find evidence","statement":"Locate an anchor.","knowledge_component_ids":["kc-1"]}],
            "artifacts":[{"artifact_id":"lesson-1","artifact_type":"lesson","title":"Evidence lesson","domain_pack_id":"general","source_ids":[sid],"knowledge_ids":["kc-1"],"renderer":"native-lesson","renderer_version":"1.0.0","status":"candidate","interactive":false}]},
            "bindings":[{"component_id":"kc-1","knowledge_id":kid,"knowledge_version":kid,"source_id":sid,"source_revision":revision}]})
    }).await.unwrap()
}

#[tokio::test]
async fn real_course_worker_validates_persists_restarts_and_refuses_stale_rendering() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open(dir.path()).await;
    let payload = fixture(&executor).await;
    let app = archeaxis_api::runtime::router(executor.clone());
    let (status, health) = call(
        &app,
        "GET",
        "/api/v1/capabilities/course.general",
        json!({}),
        "human",
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(
        health["capability"]["health"], "handshake_ready",
        "{health}"
    );
    assert_eq!(
        health["capability"]["health_details"]["protocol"],
        "archeaxis.derived-worker-hello/v1"
    );
    assert_eq!(
        call(&app, "POST", "/api/v1/courses", payload.clone(), "machine")
            .await
            .0,
        403
    );
    let mut invalid = payload.clone();
    invalid["manifest"]["status"] = json!("ready");
    assert_eq!(
        call(&app, "POST", "/api/v1/courses", invalid, "human")
            .await
            .0,
        422
    );
    let mut invalid = payload.clone();
    invalid["bindings"][0]["source_revision"] = json!("wrong");
    assert_eq!(
        call(&app, "POST", "/api/v1/courses", invalid, "human")
            .await
            .0,
        409
    );
    let (status, saved) = call(&app, "POST", "/api/v1/courses", payload.clone(), "human").await;
    assert_eq!(status, 201, "{saved}");
    assert_eq!(saved["status"], "candidate");
    assert_eq!(saved["stale"], false);
    let mut collision = payload.clone();
    collision["manifest"]["manifest_id"] = json!("course-2");
    assert_eq!(
        call(&app, "POST", "/api/v1/courses", collision, "human")
            .await
            .0,
        409
    );
    assert_eq!(
        call(&app, "POST", "/api/v1/courses", payload, "human")
            .await
            .1,
        saved
    );
    let (status, rendered) = call(
        &app,
        "POST",
        "/api/v1/courses/course-1/render",
        json!({"artifact_id":"lesson-1"}),
        "human",
    )
    .await;
    assert_eq!(status, 200, "{rendered}");
    assert_eq!(rendered["render"]["lesson"]["write_policy"], "dry_run");
    assert!(
        rendered["render"]["lesson"]["content"]
            .as_str()
            .unwrap()
            .contains("An anchor locates evidence.")
    );
    drop(app);
    drop(executor);
    let executor = open(dir.path()).await;
    let app = archeaxis_api::runtime::router(executor.clone());
    assert_eq!(
        call(&app, "GET", "/api/v1/courses/course-1", json!({}), "human")
            .await
            .1,
        saved
    );
    executor
        .store()
        .submit_wait(|conn| {
            conn.execute("UPDATE knowledge SET status='deprecated'", [])
                .unwrap()
        })
        .await
        .unwrap();
    let (_, stale) = call(&app, "GET", "/api/v1/courses/course-1", json!({}), "human").await;
    assert_eq!(stale["stale"], true);
    assert_eq!(stale["manifest"], saved["manifest"]);
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/courses/course-1/render",
            json!({"artifact_id":"lesson-1"}),
            "human"
        )
        .await
        .0,
        409
    );
}

#[tokio::test]
async fn from_knowledge_uses_canonical_body_source_and_stable_candidate_only() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open(dir.path()).await;
    let fixture = fixture(&executor).await;
    let kid = fixture["bindings"][0]["knowledge_id"]
        .as_str()
        .unwrap()
        .to_owned();
    let payload = json!({"knowledge_id":kid});
    let app = archeaxis_api::runtime::router(executor.clone());
    let path = "/api/v1/courses/from-knowledge";
    assert_eq!(
        call(&app, "POST", path, payload.clone(), "machine").await.0,
        403
    );
    assert_eq!(
        call(
            &app,
            "POST",
            path,
            json!({"knowledge_id":kid,"body":"invented"}),
            "human"
        )
        .await
        .0,
        422
    );
    assert_eq!(
        call(
            &app,
            "POST",
            path,
            json!({"knowledge_id":"missing"}),
            "human"
        )
        .await
        .0,
        404
    );
    let (status, saved) = call(&app, "POST", path, payload.clone(), "human").await;
    assert_eq!(status, 201, "{saved}");
    let manifest = &saved["course"]["manifest"];
    assert_eq!(manifest["title"], "course.md");
    assert_eq!(
        manifest["knowledge_components"][0]["statement"],
        "An anchor locates evidence."
    );
    assert_eq!(
        manifest["knowledge_components"][0]["prerequisite_ids"],
        json!([])
    );
    assert_eq!(
        manifest["learning_objectives"][0]["statement"],
        "用自己的话解释已选知识并指出来源"
    );
    assert_eq!(
        saved["course"]["bindings"][0]["source_id"],
        fixture["bindings"][0]["source_id"]
    );
    assert_eq!(saved["suggested_learning_item"]["knowledge_id"], kid);
    assert_eq!(
        saved["suggested_learning_item"]["course_id"],
        manifest["manifest_id"]
    );
    assert_eq!(
        saved["suggested_learning_item"]["artifact_id"],
        manifest["artifacts"][0]["artifact_id"]
    );
    assert_eq!(saved["course"]["status"], "candidate");
    assert_eq!(
        call(&app, "POST", path, payload.clone(), "human").await.1,
        saved
    );
    let course_id = manifest["manifest_id"].as_str().unwrap().to_owned();
    let (status, rendered) = call(
        &app,
        "POST",
        &format!("/api/v1/courses/{course_id}/render"),
        json!({"artifact_id":manifest["artifacts"][0]["artifact_id"]}),
        "human",
    )
    .await;
    assert_eq!(status, 200, "{rendered}");
    assert!(
        rendered["render"]["lesson"]["content"]
            .as_str()
            .unwrap()
            .contains("An anchor locates evidence.")
    );
    let counts = executor
        .store()
        .submit_wait(|conn| {
            let refs: i64 = conn
                .query_row("SELECT COUNT(*) FROM card_references", [], |r| r.get(0))
                .unwrap();
            let assessments: i64 = conn
                .query_row("SELECT COUNT(*) FROM learning_assessments", [], |r| {
                    r.get(0)
                })
                .unwrap();
            (refs, assessments)
        })
        .await
        .unwrap();
    assert_eq!(counts, (0, 0));
    drop(app);
    drop(executor);
    let executor = open(dir.path()).await;
    let app = archeaxis_api::runtime::router(executor.clone());
    assert_eq!(
        call(&app, "POST", path, payload.clone(), "human").await.1,
        saved
    );
    executor
        .store()
        .submit_wait(|conn| {
            conn.execute("UPDATE sources SET sha256='changed'", [])
                .unwrap()
        })
        .await
        .unwrap();
    assert_eq!(
        call(&app, "POST", path, payload.clone(), "human").await.0,
        409
    );
    let (_, stale) = call(
        &app,
        "GET",
        &format!("/api/v1/courses/{course_id}"),
        json!({}),
        "human",
    )
    .await;
    assert_eq!(stale["stale"], true);
    assert_eq!(stale["manifest"], *manifest);
    executor
        .store()
        .submit_wait(|conn| {
            conn.execute("UPDATE knowledge SET status='candidate'", [])
                .unwrap()
        })
        .await
        .unwrap();
    assert_eq!(call(&app, "POST", path, payload, "human").await.0, 409);
}

#[tokio::test]
async fn from_knowledge_rechecks_source_after_worker_and_refuses_unanchored() {
    let dir = tempfile::tempdir().unwrap();
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_owned();
    let entered = dir.path().join("entered");
    let release = dir.path().join("release");
    let wrapper = dir.path().join("course.py");
    std::fs::write(&wrapper,format!("import pathlib,time,runpy\npathlib.Path({}).touch()\nwhile not pathlib.Path({}).exists(): time.sleep(.01)\nrunpy.run_path({},run_name='__main__')\n",serde_json::to_string(&entered).unwrap(),serde_json::to_string(&release).unwrap(),serde_json::to_string(&root.join("services/python-workers/course/worker_general_course.py")).unwrap())).unwrap();
    let python: PathBuf = std::env::var_os("ARCHEAXIS_PYTHON").unwrap().into();
    let executor = Executor::open_routes(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python,
        &wrapper,
        &[("course.general", wrapper.clone())],
    )
    .await
    .unwrap();
    let fixture = fixture(&executor).await;
    let app = archeaxis_api::runtime::router(executor.clone());
    let spawned = app.clone();
    let kid = fixture["bindings"][0]["knowledge_id"].clone();
    let task = tokio::spawn(async move {
        call(
            &spawned,
            "POST",
            "/api/v1/courses/from-knowledge",
            json!({"knowledge_id":kid}),
            "human",
        )
        .await
    });
    let until = std::time::Instant::now() + std::time::Duration::from_secs(5);
    while !entered.exists() {
        assert!(std::time::Instant::now() < until);
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
    }
    executor
        .store()
        .submit_wait(|conn| {
            conn.execute("UPDATE sources SET original_name='renamed.md'", [])
                .unwrap()
        })
        .await
        .unwrap();
    std::fs::write(release, "").unwrap();
    assert_eq!(task.await.unwrap().0, 409);
    let count: i64 = executor
        .store()
        .submit_wait(|conn| {
            conn.query_row("SELECT COUNT(*) FROM general_courses", [], |r| r.get(0))
                .unwrap()
        })
        .await
        .unwrap();
    assert_eq!(count, 0);
    executor
        .store()
        .submit_wait(|conn| {
            conn.execute("UPDATE knowledge SET anchor_id=NULL", [])
                .unwrap()
        })
        .await
        .unwrap();
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/courses/from-knowledge",
            json!({"knowledge_id":fixture["bindings"][0]["knowledge_id"]}),
            "human"
        )
        .await
        .0,
        409
    );
}

#[tokio::test]
async fn from_knowledge_rejects_validated_worker_content_and_identity_changes() {
    for mutation in [
        "m['knowledge_components'][0]['statement']='invented worker claim'",
        "m['manifest_id']='worker-course';m['artifacts'][0]['artifact_id']='worker-lesson'",
        "m['title']='invented title'",
    ] {
        let dir = tempfile::tempdir().unwrap();
        let worker = dir.path().join("course.py");
        // Plausible VALIDATED output with all existing contract defaults and a legal closed shape.
        std::fs::write(&worker,format!(r#"import json,sys
r=json.load(sys.stdin)
m=r['manifest']
m.setdefault('schema','archeaxis.course-manifest/v1')
for c in m['knowledge_components']: c.setdefault('schema','archeaxis.knowledge-component/v1')
for o in m['learning_objectives']: o.setdefault('schema','archeaxis.learning-objective/v1')
for a in m['artifacts']:
 a.setdefault('schema','archeaxis.courseware-artifact/v1')
 a.setdefault('derived_only',True)
 a.setdefault('human_review_required',True)
{mutation}
print(json.dumps({{'schema':'archeaxis.general-course-worker/v1','status':'VALIDATED','derived_only':True,'human_review_required':True,'canonical_bindings_verified':False,'manifest':m}}))
"#)).unwrap();
        let python: PathBuf = std::env::var_os("ARCHEAXIS_PYTHON").unwrap().into();
        let executor = Executor::open_routes(
            &dir.path().join("db.sqlite"),
            &dir.path().join("staging"),
            &python,
            &worker,
            &[("course.general", worker.clone())],
        )
        .await
        .unwrap();
        let fixture = fixture(&executor).await;
        let app = archeaxis_api::runtime::router(executor.clone());
        let (status, response) = call(
            &app,
            "POST",
            "/api/v1/courses/from-knowledge",
            json!({"knowledge_id":fixture["bindings"][0]["knowledge_id"]}),
            "human",
        )
        .await;
        assert_eq!(status, 502, "{mutation}: {response}");
        let count: i64 = executor
            .store()
            .submit_wait(|conn| {
                conn.query_row("SELECT COUNT(*) FROM general_courses", [], |r| r.get(0))
                    .unwrap()
            })
            .await
            .unwrap();
        assert_eq!(count, 0, "{mutation}");
    }
}
