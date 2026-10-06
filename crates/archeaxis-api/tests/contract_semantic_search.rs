use archeaxis_application::executor::Executor;
use archeaxis_domain::{
    anchor, knowledge,
    source::{self, ImportOutcome},
};
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::path::PathBuf;
use tower::ServiceExt;

async fn setup(script: &str, count: usize) -> (tempfile::TempDir, Executor, Router) {
    let dir = tempfile::tempdir().unwrap();
    let worker = dir.path().join("semantic.py");
    std::fs::write(&worker, script).unwrap();
    let python: PathBuf = std::env::var_os("ARCHEAXIS_PYTHON").unwrap().into();
    let executor = Executor::open_routes(
        &dir.path().join("db"),
        &dir.path().join("staging"),
        &python,
        &worker,
        &[("search.semantic", worker.clone())],
    )
    .await
    .unwrap();
    executor
        .store()
        .submit_wait(move |conn| {
            let source = match source::import_source(
                conn,
                b"Synthetic semantic fixture",
                "fixture.txt",
                None,
            )
            .unwrap()
            {
                ImportOutcome::Imported { source_id, .. } => source_id,
                _ => unreachable!(),
            };
            let revision: String = conn
                .query_row(
                    "SELECT sha256 FROM sources WHERE source_id=?1",
                    [&source],
                    |r| r.get(0),
                )
                .unwrap();
            let anchor = anchor::add_anchor(conn, &source, &revision, r#"{"line":1}"#).unwrap();
            for i in 0..count {
                knowledge::create_knowledge(
                    conn,
                    if i == 0 {
                        "PERSONAL_DEFINITION"
                    } else {
                        "FACTUAL_CLAIM"
                    },
                    &format!("Accepted evidence {i}"),
                    "accepted",
                    None,
                    Some(&anchor),
                    "human",
                )
                .unwrap();
            }
            knowledge::create_knowledge(
                conn,
                "FACTUAL_CLAIM",
                "Do not send this candidate",
                "candidate",
                None,
                None,
                "human",
            )
            .unwrap();
        })
        .await
        .unwrap();
    let app = archeaxis_api::runtime::router(executor.clone());
    (dir, executor, app)
}
async fn call(app: Router, payload: Value) -> (u16, Value) {
    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/search/semantic")
                .header("content-type", "application/json")
                .body(Body::from(payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status().as_u16();
    let data = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&data)
            .unwrap_or_else(|_| json!({"raw":String::from_utf8_lossy(&data)})),
    )
}
/// The documented failure body, asserted rather than assumed.
///
/// These routes answered `{"error": ...}` until now: a client that reads `code` found nothing and
/// could not tell a refusal from a transient failure. `retryable` follows the contract, which ties
/// it to 503.
fn assert_error_envelope(code: &str, body: &serde_json::Value, retryable: bool) {
    assert_eq!(body["code"], code, "{body}");
    assert!(
        body["message"]
            .as_str()
            .is_some_and(|text| !text.trim().is_empty()),
        "an error must say what happened: {body}"
    );
    assert_eq!(body["retryable"], retryable, "{body}");
    assert!(
        body.get("error").is_none(),
        "the old body must be gone: {body}"
    );
}

fn stub(mode: &str) -> String {
    format!(
        r#"import json,sys
r=json.load(sys.stdin)
c=r['candidates']
assert len(c)<=16 and all(x['status']=='accepted' and x['body']!='Do not send this candidate' for x in c)
rows=[{{'knowledge_id':x['knowledge_id'],'knowledge_version':x['knowledge_version'],'score':0.5}} for x in c]
mode='{mode}'
if mode=='foreign': rows[0]['knowledge_id']='foreign'
if mode=='version': rows[0]['knowledge_version']='foreign'
if mode=='duplicate': rows.append(rows[0])
if mode=='score': rows[0]['score']=2.0
d={{'schema':'archeaxis.semantic-ranking/v1','status':'PARTIAL','engine_version':'stub',
 'embedding':{{'status':'AVAILABLE','model':'text-embedding-qwen3-embedding-0.6b','model_version':'UNVERIFIED','protocol':'openai-embeddings'}},'embedding_rank':rows,
 'reranker':{{'status':'UNAVAILABLE','model':'qwen3-reranker-0.6b','model_version':'UNVERIFIED','rank':[],'partial_scores':[],'reason':'missing exact yes/no','protocol':'qwen-yes-no-first-token-logprobs/v1'}}}}
if mode=='partial': d['reranker']['partial_scores']=[{{**rows[0],'yes_logprob':-1.0,'no_logprob':-1.0,'reasoning_tokens':0}}]
if mode in ('full','bad_logprob'):
 d['status']='AVAILABLE'; d['reranker']['status']='AVAILABLE'
 d['reranker']['rank']=[{{**x,'yes_logprob':-1.0,'no_logprob':-1.0,'reasoning_tokens':0}} for x in rows]
 if mode=='bad_logprob': d['reranker']['rank'][0]['score']=0.7
print(json.dumps(d))
sys.exit(0 if mode in ('full','bad_logprob') else 2)
"#
    )
}

#[tokio::test]
async fn core_candidates_are_batched_and_partial_is_not_a_complete_rerank() {
    let (_dir, _executor, app) = setup(&stub("partial"), 17).await;
    let (status, body) = call(app, json!({"q":"evidence"})).await;
    assert_eq!(status, 200, "{body}");
    assert_eq!(body["status"], "PARTIAL");
    assert_eq!(body["complete"], false);
    assert_eq!(body["candidate_count"], 17);
    assert!(
        body["candidates"]
            .as_array()
            .unwrap()
            .iter()
            .all(|c| c["source_id"].is_string() && c["source_revision"].is_string())
    );
    assert_eq!(body["embedding"]["complete"], true);
    assert_eq!(body["embedding"]["rank"].as_array().unwrap().len(), 17);
    assert_eq!(body["reranker"]["complete"], false);
    assert_eq!(body["reranker"]["rank"].as_array().unwrap().len(), 2);
}
#[tokio::test]
async fn empty_capacity_unknown_fields_and_untrusted_worker_rows_are_explicit() {
    let (_dir, _executor, app) = setup("raise RuntimeError('must not execute')", 0).await;
    let (status, body) = call(app.clone(), json!({"q":"x"})).await;
    assert_eq!(status, 200);
    assert_eq!(body["status"], "EMPTY");
    let (status, body) = call(app, json!({"q":"x","candidates":[]})).await;
    assert_eq!(status, 422);
    assert_error_envelope("AAK-VAL-001", &body, false);

    let (_dir, _executor, app) = setup("raise RuntimeError('must not execute')", 129).await;
    let (status, body) = call(app, json!({"q":"x"})).await;
    assert_eq!(status, 409);
    assert_error_envelope("AAK-CON-002", &body, false);

    for mode in ["foreign", "version", "duplicate", "score", "bad_logprob"] {
        let (_dir, _executor, app) = setup(&stub(mode), 2).await;
        let (status, body) = call(app, json!({"q":"x"})).await;
        assert_eq!(status, 502, "{mode}");
        assert_error_envelope("AAK-WORKER-001", &body, false);
    }
}

#[tokio::test]
async fn complete_ranks_are_merged_with_stable_ties() {
    let (_dir, _executor, app) = setup(&stub("full"), 17).await;
    let (status, body) = call(app, json!({"q":"evidence"})).await;
    assert_eq!(status, 200, "{body}");
    assert_eq!(body["complete"], true);
    assert_eq!(body["status"], "AVAILABLE");
    let rows = body["reranker"]["rank"].as_array().unwrap();
    assert_eq!(rows.len(), 17);
    assert!(
        rows.windows(2)
            .all(|pair| pair[0]["knowledge_id"].as_str() < pair[1]["knowledge_id"].as_str())
    );
}

#[tokio::test]
async fn changed_canonical_knowledge_is_not_returned_as_current() {
    let (dir, executor, app) = setup(&stub("partial"), 2).await;
    let entered = dir.path().join("entered");
    let release = dir.path().join("release");
    let gate = format!(
        "import pathlib,time\npathlib.Path({}).touch()\nwhile not pathlib.Path({}).exists(): time.sleep(.01)\n",
        serde_json::to_string(&entered).unwrap(),
        serde_json::to_string(&release).unwrap()
    );
    std::fs::write(dir.path().join("semantic.py"), gate + &stub("partial")).unwrap();
    let task = tokio::spawn(call(app, json!({"q":"evidence"})));
    let until = std::time::Instant::now() + std::time::Duration::from_secs(5);
    while !entered.exists() {
        assert!(std::time::Instant::now() < until);
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
    }
    executor
        .store()
        .submit_wait(|conn| {
            conn.execute(
                "UPDATE knowledge SET status='deprecated' WHERE status='accepted'",
                [],
            )
            .unwrap()
        })
        .await
        .unwrap();
    std::fs::write(&release, "").unwrap();
    assert_eq!(task.await.unwrap().0, 409);
}
