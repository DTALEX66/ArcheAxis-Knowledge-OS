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


#[tokio::test]
async fn course_catalog_paginates_persists_and_retains_stale_history() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open(dir.path()).await;
    let payload = fixture(&executor).await;
    let app = archeaxis_api::runtime::router(executor.clone());
    let (status, empty) = call(&app, "GET", "/api/v1/courses", json!({}), "human").await;
    assert_eq!(status, 200);
    assert_eq!(empty["items"], json!([]));
    let (status, first) = call(&app, "POST", "/api/v1/courses", payload.clone(), "human").await;
    assert_eq!(status, 201, "{first}");
    let manifest = first["manifest"].clone();
    let binding = payload["bindings"][0].clone();
    executor.store().submit_wait(move |conn| {
        for index in 0..23 {
            let mut current = manifest.clone();
            current["manifest_id"] = json!(format!("course-page-{index:02}"));
            current["artifacts"][0]["artifact_id"] = json!(format!("lesson-page-{index:02}"));
            archeaxis_domain::course::create_candidate(conn, &current, &[archeaxis_domain::course::CourseBinding {
                component_id:binding["component_id"].as_str().unwrap().into(),
                knowledge_id:binding["knowledge_id"].as_str().unwrap().into(),
                knowledge_version:binding["knowledge_version"].as_str().unwrap().into(),
                source_id:binding["source_id"].as_str().unwrap().into(),
                source_revision:binding["source_revision"].as_str().unwrap().into(),
            }]).unwrap();
        }
    }).await.unwrap();
    let (_, page) = call(&app, "GET", "/api/v1/courses", json!({}), "human").await;
    assert_eq!(page["items"].as_array().unwrap().len(), 20);
    assert!(page["items"].as_array().unwrap().iter().all(|item| item["stale"]==false && item["human_review_required"]==true && item.get("manifest").is_none()));
    let cursor = page["next_cursor"].as_str().unwrap();
    let (_, next) = call(&app, "GET", &format!("/api/v1/courses?cursor={cursor}"), json!({}), "human").await;
    assert_eq!(next["items"].as_array().unwrap().len(), 4);
    assert!(next["next_cursor"].is_null());
    let first_ids: std::collections::BTreeSet<_> = page["items"].as_array().unwrap().iter().map(|item|item["manifest_id"].as_str().unwrap()).collect();
    assert!(next["items"].as_array().unwrap().iter().all(|item| !first_ids.contains(item["manifest_id"].as_str().unwrap())));
    assert_eq!(call(&app,"GET","/api/v1/courses?cursor=..%2Fprivate",json!({}),"human").await.0,422);
    assert_eq!(call(&app,"GET","/api/v1/courses?sql=delete",json!({}),"human").await.0,400);
    executor.store().submit_wait(|conn| {conn.execute("UPDATE knowledge SET status='deprecated'", []).unwrap();}).await.unwrap();
    let (_, stale) = call(&app,"GET","/api/v1/courses",json!({}),"human").await;
    assert_eq!(stale["items"].as_array().unwrap().len(),20);
    assert!(stale["items"].as_array().unwrap().iter().all(|item|item["stale"]==true));
    drop(app); drop(executor);
    let restarted = open(dir.path()).await;
    let app = archeaxis_api::runtime::router(restarted.clone());
    let (_, after) = call(&app,"GET","/api/v1/courses",json!({}),"human").await;
    assert_eq!(stale,after);
    let (_, old) = call(&app,"GET","/api/v1/courses/course-1",json!({}),"human").await;
    assert_eq!(old["manifest"],first["manifest"]);
    assert_eq!(old["stale"],true);
    drop(app); drop(restarted);
}


/// One integrated fixture journey, not a claim of real learner mastery or knowledge qualification.
#[tokio::test]
async fn generated_course_assessment_and_review_keep_original_versions_after_reopen() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open(dir.path()).await;
    let fixture = fixture(&executor).await;
    let knowledge_id = fixture["bindings"][0]["knowledge_id"].as_str().unwrap().to_owned();
    let app = archeaxis_api::runtime::router(executor.clone());
    let (status, generated) = call(&app, "POST", "/api/v1/courses/from-knowledge",
        json!({"knowledge_id":knowledge_id}), "human").await;
    assert_eq!(status, 201, "{generated}");
    assert_eq!(generated["human_review_required"], true);
    let original_course = generated["course"].clone();
    let manifest = original_course["manifest"].clone();
    let course_id = manifest["manifest_id"].as_str().unwrap().to_owned();
    let artifact_id = manifest["artifacts"][0]["artifact_id"].as_str().unwrap().to_owned();
    let suggested = &generated["suggested_learning_item"];
    let item_key = suggested["item_key"].as_str().unwrap().to_owned();
    assert_eq!(item_key, format!("course:{course_id}:artifact:{artifact_id}"));
    assert_eq!(suggested["knowledge_id"], knowledge_id);
    assert_eq!(suggested["knowledge_version"], knowledge_id);
    let course_path = format!("/api/v1/courses/{course_id}");
    let (status, read) = call(&app, "GET", &course_path, json!({}), "human").await;
    assert_eq!(status, 200);
    assert_eq!(read, original_course);
    let (status, rendered) = call(&app, "POST", &format!("{course_path}/render"),
        json!({"artifact_id":artifact_id}), "human").await;
    assert_eq!(status, 200, "{rendered}");
    assert_eq!(rendered["course"], original_course);
    assert_eq!(rendered["canonical_bindings_verified"], true);
    assert_eq!(rendered["derived_only"], true);
    let item_path = format!("/api/v1/learning/items/{item_key}");
    let assessment_path = format!("{item_path}/assessment");
    let state_path = format!("{item_path}/state");
    let history_path = format!("/api/v1/learning/events/{item_key}");
    let (status, reference) = call(&app, "POST", &format!("{item_path}/references"),
        json!({"knowledge_id":knowledge_id}), "human").await;
    assert_eq!(status, 201, "{reference}");
    let (status, assessment) = call(&app, "POST", &assessment_path,
        json!({"knowledge_id":knowledge_id}), "human").await;
    assert_eq!(status, 201, "{assessment}");
    assert_eq!(assessment["item_key"], item_key);
    assert_eq!(assessment["knowledge_id"], knowledge_id);
    assert_eq!(assessment["knowledge_version"], knowledge_id);
    assert_eq!(assessment["content"], "An anchor locates evidence.");
    assert!(!assessment["question"].as_str().unwrap().is_empty());
    let (status, before) = call(&app, "GET", &state_path, json!({}), "human").await;
    assert_eq!(status, 200);
    assert_eq!(before["learner"]["assessment"], assessment);
    assert_eq!(before["learner"]["event_count"], 0);
    // Synthetic attempt deliberately records an incorrect answer; it establishes no mastery.
    let review = json!({"item_key":item_key,"client_event_id":"course-fixture-review-01",
        "correct":false,"rating":1,"now":"2026-10-09T10:00:00+00:00",
        "answer":"Synthetic fixture answer, not a human qualification.",
        "assessment_id":assessment["assessment_id"],"knowledge_version":assessment["knowledge_version"]});
    assert_eq!(call(&app, "POST", "/api/v1/learning/reviews", review.clone(), "machine").await.0, 403);
    let (status, receipt) = call(&app, "POST", "/api/v1/learning/reviews", review.clone(), "human").await;
    assert_eq!(status, 201, "{receipt}");
    // A missing real scheduler is a failure, never a skipped or fabricated scheduling PASS.
    assert_eq!(receipt["schedule_authority"], "fsrs", "{receipt}");
    assert!(receipt["next_review"].is_string());
    let (status, history) = call(&app, "GET", &history_path, json!({}), "human").await;
    assert_eq!(status, 200);
    assert_eq!(history["count"], 1);
    let events = history["events"].as_array().unwrap();
    assert_eq!(events.len(), 1);
    assert_eq!(events[0]["event_id"], receipt["event_id"]);
    let outcome: Value = serde_json::from_str(events[0]["outcome"].as_str().unwrap()).unwrap();
    assert_eq!(outcome["assessment_id"], assessment["assessment_id"]);
    assert_eq!(outcome["answer"], review["answer"]);
    assert_eq!(outcome["outcome"], "incorrect");
    let (status, state) = call(&app, "GET", &state_path, json!({}), "human").await;
    assert_eq!(status, 200);
    assert_eq!(state["learner"]["event_count"], events.len());
    assert_eq!(state["learner"]["assessment"], assessment);
    assert_eq!(state["machine"]["status"], "not_recorded");
    drop(app);
    drop(executor);

    let executor = open(dir.path()).await;
    let app = archeaxis_api::runtime::router(executor.clone());
    assert_eq!(call(&app, "GET", &course_path, json!({}), "human").await, (200, original_course.clone()));
    assert_eq!(call(&app, "GET", &assessment_path, json!({}), "human").await, (200, assessment.clone()));
    assert_eq!(call(&app, "GET", &history_path, json!({}), "human").await, (200, history.clone()));
    assert_eq!(call(&app, "GET", &state_path, json!({}), "human").await, (200, state));
    let (status, replay) = call(&app, "POST", "/api/v1/learning/reviews", review.clone(), "human").await;
    assert_eq!(status, 200, "{replay}");
    assert_eq!(replay["duplicate"], true);
    assert_eq!(replay["event_id"], receipt["event_id"]);
    assert_eq!(replay["schedule_state"], receipt["schedule_state"]);
    assert_eq!(call(&app, "GET", &history_path, json!({}), "human").await, (200, history.clone()));
    let mut conflict = review.clone();
    conflict["answer"] = json!("Changed answer with the same event key");
    assert_eq!(call(&app, "POST", "/api/v1/learning/reviews", conflict, "human").await.0, 409);

    let old_id = knowledge_id.clone();
    let new_id = executor.store().submit_wait(move |conn| {
        knowledge::review_checked(conn, &old_id, "modified", "fixture-owner", Some("synthetic revision"),
            Some("A revised anchor explanation belongs to a new knowledge version."), None).unwrap()
    }).await.unwrap();
    assert_ne!(new_id, knowledge_id);
    let (status, stale) = call(&app, "GET", &course_path, json!({}), "human").await;
    assert_eq!(status, 200);
    assert_eq!(stale["stale"], true);
    assert_eq!(stale["manifest"], manifest);
    assert_eq!(stale["bindings"][0]["knowledge_id"], knowledge_id);
    assert_eq!(stale["bindings"][0]["knowledge_version"], knowledge_id);
    assert_eq!(stale["bindings"][0]["source_revision"], original_course["bindings"][0]["source_revision"]);
    assert_eq!(call(&app, "POST", &format!("{course_path}/render"), json!({"artifact_id":artifact_id}), "human").await.0, 409);
    assert_eq!(call(&app, "GET", &assessment_path, json!({}), "human").await, (200, assessment.clone()));
    let (status, revised_history) = call(&app, "GET", &history_path, json!({}), "human").await;
    assert_eq!(status, 200);
    assert_eq!(revised_history["events"], history["events"]);
    assert_eq!(revised_history["count"], history["count"]);
    assert_eq!(revised_history["references"][0]["knowledge_id"], knowledge_id);
    assert_eq!(revised_history["references"][0]["active"], false);
    drop(app);
    drop(executor);

    let executor = open(dir.path()).await;
    let app = archeaxis_api::runtime::router(executor.clone());
    assert_eq!(call(&app, "GET", &course_path, json!({}), "human").await, (200, stale));
    assert_eq!(call(&app, "GET", &assessment_path, json!({}), "human").await, (200, assessment));
    assert_eq!(call(&app, "GET", &history_path, json!({}), "human").await, (200, revised_history));
    let actual_counts = executor.store().submit_wait(|conn| {
        (conn.query_row("SELECT COUNT(*) FROM learning_events", [], |r|r.get::<_,i64>(0)).unwrap(),
         conn.query_row("SELECT COUNT(*) FROM learning_event_keys", [], |r|r.get::<_,i64>(0)).unwrap())
    }).await.unwrap();
    assert_eq!(actual_counts, (1, 1));
    drop(app);
    drop(executor);
}
