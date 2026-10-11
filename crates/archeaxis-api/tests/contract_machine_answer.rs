//! G4: a machine answer over an accepted knowledge item, and the limits it must keep.
//!
//! This is the machine half of the co-learning loop. The checks below are about grounding and
//! labelling rather than about what the model says, because a model's wording is not a fact this
//! repository can fix: the answer must be grounded in the workspace's own accepted body, must be
//! labelled a candidate, and must never be promoted.

use archeaxis_application::executor::Executor;
use archeaxis_domain::knowledge;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use std::path::PathBuf;
use tower::ServiceExt;

/// An executor with the machine answer route declared, plus one accepted knowledge item to answer
/// from.
async fn fixture() -> (tempfile::TempDir, Router, String) {
    let dir = tempfile::tempdir().unwrap();
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    // Synthetic worker: deterministic contract evidence, never real-model evidence.
    let worker = dir.path().join("answer.py");
    std::fs::write(&worker, r#"import json
from pathlib import Path
p = Path(__file__).with_suffix('.count')
p.write_text(str(int(p.read_text()) + 1) if p.exists() else '1')
print(json.dumps({'answer': 'Synthetic answer', 'model': 'some-model', 'loss_receipt': {'params': {'authority': 'candidate'}}}))
"#).unwrap();
    let transport = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
    let executor = Executor::open_routes(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python,
        &transport,
        &[("machine.answer", worker)],
    )
    .await
    .unwrap();

    let knowledge_id = executor
        .store()
        .submit(|conn| {
            // `create_knowledge` rather than the v3 form: the v3 form requires governance metadata and
            // rejects its absence, which is a fact about governance rather than about this route.
            knowledge::create_knowledge(
                conn,
                "NOTE",
                "ArcheAxis Knowledge keeps its canonical store in SQLite, and only the Rust Core \
                 writes it. The release is currently FROZEN.",
                "accepted",
                None,
                None,
                "human",
            )
        })
        .await
        .unwrap()
        .unwrap();

    let router = archeaxis_api::runtime::router(executor);
    (dir, router, knowledge_id)
}

#[tokio::test]
async fn machine_journal_clear_is_human_only_and_does_not_invoke_worker() {
    let (dir,router,_)=fixture().await;
    let body=serde_json::json!({"workspace_id":"wrong","restore_epoch":"initial","state_revision":0,"journal_id":"missing","task_id":"missing"}).to_string();
    for (actor,expected) in [("ai",403),("human",409)] {
        let response=router.clone().oneshot(Request::builder().method("POST").uri("/api/v1/workspace/ui-state/clear-machine").header("content-type","application/json").header("x-archeaxis-actor",actor).body(Body::from(body.clone())).unwrap()).await.unwrap();
        assert_eq!(response.status().as_u16(),expected);
    }
    assert!(!dir.path().join("answer.count").exists());
}

#[tokio::test]
async fn actual_failure_status_and_clear_do_not_repeat_worker() {
    let (dir,router,id)=fixture().await;
    std::fs::write(dir.path().join("answer.py"),"import json,sys\nfrom pathlib import Path\np=Path(__file__).with_suffix('.count')\np.write_text('1')\nprint(json.dumps({'schema':'archeaxis.machine-worker-failure/v1','reason_code':'MODEL_CALL_FAILED'}))\nsys.exit(1)\n").unwrap();
    let response=router.clone().oneshot(Request::builder().uri("/api/v1/workspace/ui-state").body(Body::empty()).unwrap()).await.unwrap();
    assert_eq!(response.status(),200);
    let basis:serde_json::Value=serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes()).unwrap();
    let body=serde_json::json!({"knowledge_id":id,"question":"Synthetic failure recovery","max_tokens":2048,"timeout_s":120,"client_request_id":"failure_recovery"});
    let entry=serde_json::json!({"journal_id":"failure_recovery","owner_knowledge_id":id,"operation":"answer","origin_restore_epoch":"initial","body":body});
    let payload=serde_json::json!({"workspace_id":basis["workspace_id"],"restore_epoch":basis["restore_epoch"],"state_revision":basis["state_revision"],"state":{"drafts":{},"opened_documents":[],"active_document":null,"page_id":null,"pending_machine":{"failure_recovery":entry}}});
    let response=router.clone().oneshot(Request::builder().method("PUT").uri("/api/v1/workspace/ui-state").header("content-type","application/json").body(Body::from(payload.to_string())).unwrap()).await.unwrap();
    assert_eq!(response.status(),200);
    let written:serde_json::Value=serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes()).unwrap();
    let query=serde_json::json!({"workspace_id":written["workspace_id"],"restore_epoch":written["restore_epoch"],"state_revision":written["state_revision"],"journal_id":"failure_recovery"});
    let mut bypass=body.clone();bypass["client_request_id"]=serde_json::json!("new_identity");
    let (status,raw)=post(&router,"/api/v1/machine/answers",&bypass.to_string()).await;assert_eq!(status,409,"{raw}");assert!(!dir.path().join("answer.count").exists());
    let (status,raw)=post(&router,"/api/v1/workspace/ui-state/machine-status",&query.to_string()).await;assert_eq!(status,200,"{raw}");assert_eq!(serde_json::from_str::<serde_json::Value>(&raw).unwrap()["status"],"UNKNOWN");
    let (status,raw)=post(&router,"/api/v1/machine/answers",&body.to_string()).await;assert_eq!(status,503,"{raw}");
    for _ in 0..2 {
        let (status,raw)=post(&router,"/api/v1/workspace/ui-state/machine-status",&query.to_string()).await;assert_eq!(status,200,"{raw}");
        let read:serde_json::Value=serde_json::from_str(&raw).unwrap();assert_eq!(read["status"],"FAILED");assert_eq!(read["can_clear"],true);
    }
    let (status,raw)=post(&router,"/api/v1/workspace/ui-state/machine-status",&query.to_string()).await;assert_eq!(status,200);
    let read:serde_json::Value=serde_json::from_str(&raw).unwrap();let mut clear=query.clone();clear["task_id"]=read["task_id"].clone();
    let (status,raw)=post(&router,"/api/v1/workspace/ui-state/clear-machine",&clear.to_string()).await;assert_eq!(status,200,"{raw}");assert!(serde_json::from_str::<serde_json::Value>(&raw).unwrap()["state"].get("pending_machine").is_none());
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),"1");
    let response=router.clone().oneshot(Request::builder().method("POST").uri("/api/v1/workspace/ui-state/machine-status").header("content-type","application/json").header("x-archeaxis-actor","machine").body(Body::from(query.to_string())).unwrap()).await.unwrap();assert_eq!(response.status(),403);
}

#[tokio::test]
async fn unfinished_durable_claim_refuses_before_worker_invocation() {
    use sha2::{Digest,Sha256};
    let (dir,router,knowledge_id)=fixture().await;
    let client="fixed_crash_request";
    let execution_id=format!("answer_req_{:x}",Sha256::digest(client.as_bytes()));
    let key=format!("machine_execution_claim_{:x}",Sha256::digest(execution_id.as_bytes()));
    let conn=rusqlite::Connection::open(dir.path().join("db.sqlite")).unwrap();
    let context:String=conn.query_row("SELECT body FROM knowledge WHERE knowledge_id=?1",[&knowledge_id],|r|r.get(0)).unwrap();
    let request=serde_json::json!({"schema":"archeaxis.machine-answer-request/v1","knowledge_id":knowledge_id,"question":"Synthetic crash recovery","max_tokens":2048,"timeout_s":120,"context_grant":null,"context_sha256":format!("{:x}",Sha256::digest(context.as_bytes()))});
    let value=serde_json::json!({"schema":"archeaxis.machine-execution-claim/v1","state":"IN_FLIGHT","request_sha256":format!("{:x}",Sha256::digest(request.to_string().as_bytes()))});
    conn.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,?2)",rusqlite::params![key,value.to_string()]).unwrap();drop(conn);
    let body=serde_json::json!({"knowledge_id":knowledge_id,"question":"Synthetic crash recovery","client_request_id":client}).to_string();
    let (status,message)=post(&router,"/api/v1/machine/answers",&body).await;
    assert_eq!(status,409);assert!(message.contains("UNVERIFIED"));
    assert!(!dir.path().join("answer.count").exists());
}

#[tokio::test]
async fn unfinished_retest_claim_cannot_be_bypassed_by_changing_knowledge_body() {
    use sha2::{Digest,Sha256};
    let hash=|s:&str|format!("{:x}",Sha256::digest(s.as_bytes()));
    let (dir,router,id)=fixture().await;
    let question="Synthetic immutable retest input";
    let (status,raw)=post(&router,"/api/v1/machine/answers",&serde_json::json!({"knowledge_id":id,"question":question}).to_string()).await;
    assert_eq!(status,200,"{raw}");let answer:serde_json::Value=serde_json::from_str(&raw).unwrap();
    let (status,raw)=post(&router,"/api/v1/machine/corrections",&serde_json::json!({"answer_id":answer["answer_id"],"knowledge_id":id,"question":question,"machine_answer":answer["answer"]["answer"],"corrected_answer":"Synthetic corrected content","error_note":"Synthetic correction basis"}).to_string()).await;
    assert_eq!(status,200,"{raw}");let correction:serde_json::Value=serde_json::from_str(&raw).unwrap();
    let candidate=correction["correction_candidate_id"].as_str().unwrap();
    assert_eq!(post(&router,&format!("/api/v1/knowledge-items/{candidate}/review-decisions"),r#"{"action":"accepted","reviewer":"synthetic-human"}"#).await.0,200);
    let body=serde_json::json!({"retest_of":correction["failed_task_id"],"knowledge_id":candidate,"question":question});
    let normalized=serde_json::json!({"operation":"retest","request":{"knowledge_id":candidate,"question":question,"max_tokens":2048,"timeout_s":120,"context_grant":null,"asset_context_grant":null,"client_request_id":null,"retest_of":correction["failed_task_id"]}});
    let claim_id=format!("retest_input_{}",hash(&normalized.to_string()));
    let conn=rusqlite::Connection::open(dir.path().join("db.sqlite")).unwrap();
    let old_body:String=conn.query_row("SELECT body FROM knowledge WHERE knowledge_id=?1",[candidate],|r|r.get(0)).unwrap();
    let cache_request=serde_json::json!({"retest_of":correction["failed_task_id"],"knowledge_id":candidate,"question":question,"max_tokens":2048});
    let old_execution=serde_json::json!({"schema":"archeaxis.machine-retest-execution/v1","request":cache_request,"timeout_s":120,"context_sha256":hash(&old_body)});
    let claim=serde_json::json!({"schema":"archeaxis.machine-execution-claim/v1","state":"IN_FLIGHT","request_sha256":hash(&old_execution.to_string())});
    conn.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,?2)",rusqlite::params![format!("machine_execution_claim_{}",hash(&claim_id)),claim.to_string()]).unwrap();
    // Isolated test fixture mutation models material changing after a lost process.
    conn.execute("UPDATE knowledge SET body='Synthetic material changed after interrupted retest' WHERE knowledge_id=?1",[candidate]).unwrap();drop(conn);
    let before=std::fs::read(dir.path().join("answer.count")).unwrap();
    let (status,message)=post(&router,"/api/v1/machine/retests",&body.to_string()).await;
    assert_eq!(status,409,"{message}");assert!(message.contains("UNVERIFIED"));
    assert_eq!(std::fs::read(dir.path().join("answer.count")).unwrap(),before);
}

#[tokio::test]
async fn configuration_read_never_executes_worker_or_creates_machine_tasks() {
    let (dir, router, _) = fixture().await;
    for _ in 0..2 {
        let response = router.clone().oneshot(Request::builder()
            .uri("/api/v1/machine/configuration").body(Body::empty()).unwrap()).await.unwrap();
        assert_eq!(response.status(), 200);
        let value: serde_json::Value = serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes()).unwrap();
        assert_eq!(value["schema"], "archeaxis.machine-configuration/v1");
        assert_eq!(value["availability"], "CONFIGURED_UNVERIFIED");
        assert_eq!(value["worker_registered"], true);
        assert_eq!(value["network_performed"], false);
        assert_eq!(value["inference_status"], "NOT_EXECUTED");
        assert_eq!(value["loaded_status"], "UNKNOWN");
        for key in ["model_identity", "usage", "cost"] { assert!(value[key].is_null()); }
        assert_eq!(value.as_object().unwrap().len(), 13);
    }
    assert!(!dir.path().join("answer.count").exists());
    let response = router.oneshot(Request::builder().uri("/api/v1/machine/tasks").body(Body::empty()).unwrap()).await.unwrap();
    assert_eq!(response.status(), 200);
    let value: serde_json::Value = serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes()).unwrap();
    assert!(value["items"].as_array().unwrap().is_empty());
}

#[tokio::test]
async fn inventory_is_input_free_and_projects_no_private_worker_fields() {
    let (dir, router, _) = fixture().await;
    let (status, _) = post(&router, "/api/v1/machine/inventory", r#"{"endpoint":"http://example.invalid","context":"SYNTHETIC_PRIVATE"}"#).await;
    assert_eq!(status, 400);
    assert!(!dir.path().join("answer.count").exists());
    std::fs::write(dir.path().join("answer.py"), r#"import json,sys
assert sys.argv[1:] == ['--probe']
assert sys.stdin.read() == ''
print(json.dumps({'inventory_status':'READ_VERIFIED','loaded_status':'UNKNOWN','inference_status':'NOT_EXECUTED','evidence_scope':'MODEL_INVENTORY_ONLY','available':['m'],'model':'m','capability':True,'availability':'MODEL_LISTED_INFERENCE_UNVERIFIED','endpoint':'SYNTHETIC_PRIVATE'}))
"#).unwrap();
    let (status, body) = post(&router, "/api/v1/machine/inventory", "{}").await;
    assert_eq!(status, 200);
    let value: serde_json::Value = serde_json::from_str(&body).unwrap();
    assert_eq!(value["status"], "READ_VERIFIED");
    assert_eq!(value["selected_model_listed"], true);
    assert_eq!(value["listed_model_count"], 1);
    assert_eq!(value["loaded_status"], "UNKNOWN");
    assert_eq!(value["inference_status"], "NOT_EXECUTED");
    assert!(value["cost"].is_null());
    assert!(!body.contains("SYNTHETIC_PRIVATE"));
    assert!(value.get("available").is_none());
    let response = router.oneshot(Request::builder().uri("/api/v1/machine/tasks").body(Body::empty()).unwrap()).await.unwrap();
    let value: serde_json::Value = serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes()).unwrap();
    assert!(value["items"].as_array().unwrap().is_empty());
}

async fn post(router: &Router, path: &str, body: &str) -> (u16, String) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(path)
                .header("content-type", "application/json")
                .body(Body::from(body.to_owned()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, String::from_utf8_lossy(&bytes).to_string())
}

#[tokio::test]
async fn a_question_is_required_rather_than_answering_nothing() {
    let (_dir, router, knowledge_id) = fixture().await;
    let (status, body) = post(
        &router,
        "/api/v1/machine/answers",
        &format!(r#"{{"knowledge_id":"{knowledge_id}","question":"   "}}"#),
    )
    .await;

    assert_eq!(status, 422, "{body}");
    assert!(body.contains("question is required"), "{body}");
}

#[tokio::test]
async fn an_unknown_knowledge_item_is_a_not_found_rather_than_a_free_answer() {
    // Without this, a typo in the id would silently answer from nothing and look like a capability.
    let (_dir, router, _) = fixture().await;
    let (status, body) = post(
        &router,
        "/api/v1/machine/answers",
        r#"{"knowledge_id":"k_does_not_exist","question":"what?"}"#,
    )
    .await;

    assert_eq!(status, 404, "{body}");
    assert!(body.contains("no knowledge item"), "{body}");
}

#[tokio::test]
async fn candidate_and_deprecated_knowledge_are_refused_before_inference() {
    for status in ["candidate", "deprecated", "rejected"] {
        let (dir, router, knowledge_id) = fixture().await;
        let conn = rusqlite::Connection::open(dir.path().join("db.sqlite")).unwrap();
        conn.execute(
            "UPDATE knowledge SET status=?1 WHERE knowledge_id=?2",
            [status, &knowledge_id],
        )
        .unwrap();
        let (status, body) = post(
            &router,
            "/api/v1/machine/answers",
            &serde_json::json!({"knowledge_id": knowledge_id, "question": "what?", "timeout_s": 1})
                .to_string(),
        )
        .await;
        assert_eq!(status, 404, "{body}");
    }
}

#[tokio::test]
async fn active_personal_knowledge_is_allowed_but_superseded_knowledge_is_not() {
    let (dir, router, id) = fixture().await;
    let mut conn = rusqlite::Connection::open(dir.path().join("db.sqlite")).unwrap();
    let personal = knowledge::create_knowledge(
        &mut conn,
        "PERSONAL_DEFINITION",
        "my experience",
        "candidate",
        None,
        None,
        "human",
    )
    .unwrap();
    let request = serde_json::json!({"knowledge_id":personal,"question":"what?"});
    assert_eq!(
        post(&router, "/api/v1/machine/answers", &request.to_string())
            .await
            .0,
        200
    );
    conn.execute(
        "INSERT INTO knowledge_supersedes(old_knowledge_id,new_knowledge_id) VALUES(?1,?2)",
        [&id, &personal],
    )
    .unwrap();
    let request = serde_json::json!({"knowledge_id":id,"question":"what?"});
    assert_eq!(
        post(&router, "/api/v1/machine/answers", &request.to_string())
            .await
            .0,
        404
    );
    assert_eq!(
        std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),
        "1"
    );
}

#[tokio::test]
async fn a_free_text_context_is_refused_because_grounding_is_the_point() {
    let (_dir, router, _) = fixture().await;
    // `context` is not a field of this route; a caller must name accepted material instead.
    let (status, _) = post(
        &router,
        "/api/v1/machine/answers",
        r#"{"knowledge_id":"k_x","question":"what?","context":"whatever I like"}"#,
    )
    .await;

    assert_eq!(
        status, 422,
        "an unknown field must be refused rather than ignored"
    );
}

#[tokio::test]
async fn a_disabled_capability_refuses_before_the_model_runs() {
    let (dir, router, knowledge_id) = fixture().await;
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri("/api/v1/capabilities/machine.answer/enabled")
                .header("content-type", "application/json")
                .body(Body::from(r#"{"enabled":false}"#))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status().as_u16(), 200);
    let probe_baseline = std::fs::read(dir.path().join("answer.count")).ok();
    let (probe_status, probe_body) = post(&router, "/api/v1/machine/inventory", "{}").await;
    assert_eq!(probe_status, 200);
    let probe: serde_json::Value = serde_json::from_str(&probe_body).unwrap();
    assert_eq!(probe["status"], "DISABLED");
    assert!(probe["listed_model_count"].is_null());
    assert!(probe["selected_model_listed"].is_null());
    assert_eq!(std::fs::read(dir.path().join("answer.count")).ok(), probe_baseline);

    let (status, body) = post(
        &router,
        "/api/v1/machine/answers",
        &format!(r#"{{"knowledge_id":"{knowledge_id}","question":"what writes the store?"}}"#),
    )
    .await;

    assert_eq!(status, 409, "{body}");
    assert!(body.contains("machine.answer"), "{body}");
}

#[tokio::test]
async fn an_answer_is_either_a_labelled_candidate_or_a_named_failure() {
    // The assertion is deliberately about which of the two honest outcomes happens, not about the
    // model's wording. A machine with no model must fail by name; a machine with one must answer and
    // label the answer a candidate. Either way nothing is invented and nothing is promoted.
    let (_dir, router, knowledge_id) = fixture().await;
    // One line, so no backslash-newline can end up inside the JSON string: that is an invalid escape
    // and a defect in the test rather than in the route.
    let question = "What writes the canonical store, and is the release frozen?";
    let body =
        format!(r#"{{"knowledge_id":"{knowledge_id}","question":"{question}","timeout_s":120}}"#);
    let (status, body) = post(&router, "/api/v1/machine/answers", &body).await;

    match status {
        200 => {
            let value: serde_json::Value = serde_json::from_str(&body).unwrap();
            assert_eq!(value["schema"], "archeaxis.machine-answer/v1");
            assert_eq!(value["authority"], "candidate", "{body}");
            assert!(
                value["note"]
                    .as_str()
                    .unwrap()
                    .contains("not accepted knowledge"),
                "{body}"
            );
            let answer = value["answer"]["answer"].as_str().unwrap();
            assert!(
                !answer.trim().is_empty(),
                "an empty answer must never be a success"
            );
            // the receipt that travels with it must also say candidate
            assert_eq!(
                value["answer"]["loss_receipt"]["params"]["authority"],
                "candidate"
            );
            // and nothing may claim knowledge changed or a model was trained
            let lowered = body.to_lowercase();
            for forbidden in ["\"promoted\":true", "trained", "accuracy"] {
                assert!(
                    !lowered.contains(forbidden),
                    "{forbidden} appears in {body}"
                );
            }
        }
        503 => {
            // No model on this host is a real state, and the reason must be the worker's own.
            assert!(!body.trim().is_empty(), "a failure must name a reason");
        }
        other => panic!("unexpected status {other}: {body}"),
    }
}

#[tokio::test]
async fn persisted_answer_correction_review_and_retest_form_one_chain() {
    let (dir, router, id) = fixture().await;
    let request = serde_json::json!({"knowledge_id":id,"question":"what writes the store?"});
    let (status, answer) = post(&router, "/api/v1/machine/answers", &request.to_string()).await;
    assert_eq!(status, 200, "{answer}");
    let answer: serde_json::Value = serde_json::from_str(&answer).unwrap();
    let correction = serde_json::json!({"answer_id":answer["answer_id"],
        "knowledge_id":id,"question":request["question"],"machine_answer":answer["answer"]["answer"],
        "corrected_answer":"The Rust Core writes the SQLite store.", "error_note":"synthetic worker did not identify the writer"});
    let (status, correction) = post(
        &router,
        "/api/v1/machine/corrections",
        &correction.to_string(),
    )
    .await;
    assert_eq!(status, 200, "{correction}");
    let correction: serde_json::Value = serde_json::from_str(&correction).unwrap();
    let candidate = correction["correction_candidate_id"].as_str().unwrap();
    let retest = serde_json::json!({"retest_of":correction["failed_task_id"],
        "knowledge_id":candidate,"question":request["question"]});
    assert_eq!(
        post(&router, "/api/v1/machine/retests", &retest.to_string())
            .await
            .0,
        404
    );
    assert_eq!(
        post(
            &router,
            &format!("/api/v1/knowledge-items/{candidate}/review-decisions"),
            r#"{"action":"accepted","reviewer":"synthetic-human"}"#
        )
        .await
        .0,
        200
    );
    let (status, result) = post(&router, "/api/v1/machine/retests", &retest.to_string()).await;
    assert_eq!(status, 200, "{result}");
    let result: serde_json::Value = serde_json::from_str(&result).unwrap();
    assert_eq!(
        result["prior"]["conditions"]["answer_id"],
        answer["answer_id"]
    );
    assert_eq!(
        std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),
        "2"
    );
    // Default-model cache still binds the effective timeout; a different budget
    // is a distinct execution, while replaying either exact budget does no work.
    let mut short=retest.clone();short["timeout_s"]=serde_json::json!(1);
    let (status,raw)=post(&router,"/api/v1/machine/retests",&short.to_string()).await;assert_eq!(status,200,"{raw}");
    let short_result:serde_json::Value=serde_json::from_str(&raw).unwrap();assert_eq!(short_result["execution_request"]["timeout_s"],1);assert_ne!(short_result["retest_task_id"],result["retest_task_id"]);
    let (status,raw)=post(&router,"/api/v1/machine/retests",&retest.to_string()).await;assert_eq!(status,200,"{raw}");assert_eq!(serde_json::from_str::<serde_json::Value>(&raw).unwrap()["retest_task_id"],result["retest_task_id"]);
    let (status,raw)=post(&router,"/api/v1/machine/retests",&short.to_string()).await;assert_eq!(status,200,"{raw}");assert_eq!(serde_json::from_str::<serde_json::Value>(&raw).unwrap()["retest_task_id"],short_result["retest_task_id"]);
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),"3");
    // A wrong retest is another persisted answer; the same correction text must work again.
    let second = serde_json::json!({
        "answer_id": result["retest_task_id"], "knowledge_id": candidate,
        "question": request["question"], "machine_answer": result["answer"]["answer"],
        "corrected_answer": "The Rust Core writes the SQLite store.",
        "error_note": "synthetic retest still omitted the writer"
    });
    let (status, second) = post(&router, "/api/v1/machine/corrections", &second.to_string()).await;
    assert_eq!(status, 200, "{second}");
    let second: serde_json::Value = serde_json::from_str(&second).unwrap();
    assert_eq!(second["answer_id"], result["retest_task_id"]);
    assert_ne!(
        second["correction_candidate_id"],
        correction["correction_candidate_id"]
    );
    let second_id = second["correction_candidate_id"].as_str().unwrap();
    assert_eq!(
        post(
            &router,
            &format!("/api/v1/knowledge-items/{second_id}/review-decisions"),
            r#"{"action":"accepted","reviewer":"synthetic-human"}"#
        )
        .await
        .0,
        200
    );
    let second_retest = serde_json::json!({
        "retest_of": second["failed_task_id"], "knowledge_id": second_id,
        "question": request["question"]
    });
    let (status, response) = post(
        &router,
        "/api/v1/machine/retests",
        &second_retest.to_string(),
    )
    .await;
    assert_eq!(status, 200, "{response}");
}

#[tokio::test]
async fn explicit_model_is_verified_frozen_and_retest_cache_is_model_bound() {
    let (dir, router, id) = fixture().await;
    std::fs::write(dir.path().join("answer.py"), r#"import json,sys
from pathlib import Path
if sys.argv[1:] == ['--probe']:
 print(json.dumps({'inventory_status':'READ_VERIFIED','loaded_status':'UNKNOWN','inference_status':'NOT_EXECUTED','evidence_scope':'MODEL_INVENTORY_ONLY','available':['m1','m2'],'model':'m1','capability':True,'availability':'MODEL_LISTED_INFERENCE_UNVERIFIED'}))
else:
 model=sys.argv[sys.argv.index('--model')+1]
 p=Path(__file__).with_suffix('.calls')
 p.write_text(str(int(p.read_text())+1) if p.exists() else '1')
 print(json.dumps({'answer':'Synthetic answer','model':model,'requested_model':model,'loss_receipt':{'params':{'authority':'candidate'}}}))
"#).unwrap();
    let mut request=serde_json::json!({"knowledge_id":id,"question":"what writes?","model":"m1"});
    assert_eq!(post(&router,"/api/v1/machine/answers",&request.to_string()).await.0,422);
    request["client_request_id"]=serde_json::json!("selected-model-request");
    let (status,raw)=post(&router,"/api/v1/machine/answers",&request.to_string()).await;
    assert_eq!(status,200,"{raw}");
    let answer:serde_json::Value=serde_json::from_str(&raw).unwrap();
    assert_eq!(answer["request"]["model"],"m1");
    assert_eq!(answer["answer"]["requested_model"],"m1");
    let (status,replayed)=post(&router,"/api/v1/machine/answers",&request.to_string()).await;
    assert_eq!(status,200); assert_eq!(serde_json::from_str::<serde_json::Value>(&replayed).unwrap(),answer);
    request["model"]=serde_json::json!("m2");
    assert_eq!(post(&router,"/api/v1/machine/answers",&request.to_string()).await.0,409);
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.calls")).unwrap(),"1");
    let correction=serde_json::json!({"answer_id":answer["answer_id"],"knowledge_id":id,"question":"what writes?","machine_answer":"Synthetic answer","corrected_answer":"Rust Core writes.","error_note":"synthetic omission"});
    let (status,raw)=post(&router,"/api/v1/machine/corrections",&correction.to_string()).await;
    assert_eq!(status,200,"{raw}");
    let correction:serde_json::Value=serde_json::from_str(&raw).unwrap();
    let candidate=correction["correction_candidate_id"].as_str().unwrap();
    let omitted=serde_json::json!({"retest_of":correction["failed_task_id"],"knowledge_id":candidate,"question":"what writes?"});
    assert_eq!(post(&router,"/api/v1/machine/retests",&omitted.to_string()).await.0,422);
    let mut retest=serde_json::json!({"retest_of":correction["failed_task_id"],"knowledge_id":candidate,"question":"what writes?","model":"m1"});
    assert_eq!(post(&router,"/api/v1/machine/retests",&retest.to_string()).await.0,404);
    assert_eq!(post(&router,&format!("/api/v1/knowledge-items/{candidate}/review-decisions"),r#"{"action":"accepted","reviewer":"synthetic-human"}"#).await.0,200);
    let (status,raw)=post(&router,"/api/v1/machine/retests",&retest.to_string()).await;
    assert_eq!(status,200,"{raw}");
    let first:serde_json::Value=serde_json::from_str(&raw).unwrap();
    assert_eq!(first["request"]["model"],"m1");
    assert_eq!(first["request"]["timeout_s"],120);
    assert_eq!(post(&router,"/api/v1/machine/retests",&retest.to_string()).await.0,200);
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.calls")).unwrap(),"2");
    retest["model"]=serde_json::json!("m2");
    let (status,raw)=post(&router,"/api/v1/machine/retests",&retest.to_string()).await;
    assert_eq!(status,200,"{raw}");
    let second:serde_json::Value=serde_json::from_str(&raw).unwrap();
    assert_ne!(first["retest_task_id"],second["retest_task_id"]);
    assert_eq!(second["answer"]["model"],"m2");
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.calls")).unwrap(),"3");
    retest["model"]=serde_json::json!("missing-model");
    assert_eq!(post(&router,"/api/v1/machine/retests",&retest.to_string()).await.0,503);
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.calls")).unwrap(),"3");
}

#[tokio::test]
async fn failed_worker_diagnostic_is_safe_and_never_creates_success_task() {
    for (code, expected) in [("NO_FINAL_ANSWER", "NO_FINAL_ANSWER"), ("SYNTHETIC_PRIVATE", "WORKER_FAILED")] {
        let (dir,router,id)=fixture().await;
        std::fs::write(dir.path().join("answer.py"),format!("import json,sys\nprint(json.dumps({{\"schema\":\"archeaxis.machine-worker-failure/v1\",\"reason_code\":\"{code}\",\"error\":\"SYNTHETIC_PRIVATE\"}}))\nsys.exit(1)\n")).unwrap();
        let (status,body)=post(&router,"/api/v1/machine/answers",&serde_json::json!({"knowledge_id":id,"question":"synthetic question"}).to_string()).await;
        assert_eq!(status,503,"{body}");
        let value:serde_json::Value=serde_json::from_str(&body).unwrap();
        assert_eq!(value,serde_json::json!({"schema":"archeaxis.machine-call-failure/v1","operation":"answer","reason_code":expected,"execution_state":"UNVERIFIED","answer_published":false}));
        assert!(!body.contains("SYNTHETIC_PRIVATE"));
        let conn=rusqlite::Connection::open(dir.path().join("db.sqlite")).unwrap();
        let count:i64=conn.query_row("SELECT count(*) FROM machine_tasks WHERE scope IN ('runtime.answer','runtime.retest')",[],|row|row.get(0)).unwrap();
        assert_eq!(count,0);
    }
}

#[tokio::test]
async fn failed_answer_retry_budget_stops_before_fourth_worker_invocation() {
    let (dir,router,id)=fixture().await;
    std::fs::write(dir.path().join("answer.py"),r#"import json,sys
from pathlib import Path
p=Path(__file__).with_suffix('.count')
p.write_text(str(int(p.read_text())+1) if p.exists() else '1')
print(json.dumps({'schema':'archeaxis.machine-worker-failure/v1','reason_code':'MODEL_CALL_FAILED'}))
sys.exit(1)
"#).unwrap();
    let body=serde_json::json!({"knowledge_id":id,"question":"Synthetic bounded failure","client_request_id":"bounded_failure"}).to_string();
    for attempt in 1..=3 {
        let (status,raw)=post(&router,"/api/v1/machine/answers",&body).await;
        assert_eq!(status,503,"{raw}");
        assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),attempt.to_string());
    }
    let (status,raw)=post(&router,"/api/v1/machine/answers",&body).await;
    assert_eq!(status,409,"{raw}");
    assert!(raw.contains("UNVERIFIED"));
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),"3");
    let conn=rusqlite::Connection::open(dir.path().join("db.sqlite")).unwrap();
    let count:i64=conn.query_row("SELECT count(*) FROM machine_tasks WHERE scope IN ('runtime.answer','runtime.retest')",[],|row|row.get(0)).unwrap();
    assert_eq!(count,0);
    let failures:i64=conn.query_row("SELECT count(*) FROM machine_tasks WHERE scope='runtime.execution.failed' AND outcome='failed'",[],|row|row.get(0)).unwrap();
    assert_eq!(failures,3);
    let conditions:String=conn.query_row("SELECT conditions FROM machine_tasks WHERE scope='runtime.execution.failed' AND json_extract(conditions,'$.attempt')=3",[],|row|row.get(0)).unwrap();
    let terminal:serde_json::Value=serde_json::from_str(&conditions).unwrap();
    assert_eq!(terminal["answer_published"],false);
    assert_eq!(terminal["provider_stop_state"],"UNKNOWN");
    assert!(terminal["usage"].is_null());
    assert!(!conditions.contains("Synthetic bounded failure"));
}
