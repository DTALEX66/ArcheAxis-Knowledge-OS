//! Real reused parsers and document-backed template metadata through Core routes.
use archeaxis_application::executor::Executor;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::path::{Path, PathBuf};
use tower::ServiceExt;

async fn call(router: &Router, method: &str, path: &str, body: Value) -> (u16, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", "human")
                .header("idempotency-key", format!("oss-{}", path.replace('/', "-")))
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

fn repo() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

async fn executor(dir: &Path) -> Executor {
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").expect("use project runner"));
    Executor::open_routes(
        &dir.join("db.sqlite"),
        &dir.join("staging"),
        &python,
        &repo().join("services/python-workers/transport/text_ndjson.py"),
        &[
            (
                "html.structure",
                repo().join("services/python-workers/web/worker_html.py"),
            ),
            (
                "pdf.extract",
                repo().join("services/python-workers/document/worker_pdf.py"),
            ),
            (
                "office.structure",
                repo().join("services/python-workers/document/worker_office.py"),
            ),
            (
                "canvas.structure",
                repo().join("services/python-workers/document/worker_canvas.py"),
            ),
            (
                "image.ocr",
                repo().join("services/python-workers/vision/worker_ocr.py"),
            ),
        ],
    )
    .await
    .unwrap()
}

#[tokio::test]
async fn parsers_run_through_core_and_outputs_survive_reopen() {
    use base64::Engine;
    let dir = tempfile::tempdir().unwrap();
    let cases = [
        ("html", "article.html", format!("<html><body><nav>NOISE_NAV</nav><article><h1>Experiment</h1><p>{0}</p><p>{0}</p></article><footer>NOISE_FOOTER</footer></body></html>", "A measured result must remain bound to the original source and its revision. ".repeat(12)).into_bytes()),
        ("pdf", "evidence.pdf", std::fs::read(repo().join("tests/fixtures/golden/golden-journey-evidence.pdf")).unwrap()),
        ("office", "evidence.docx", std::fs::read(repo().join("tests/fixtures/golden/golden-docx-anchor.docx")).unwrap()),
        ("canvas", "evidence.canvas", std::fs::read(repo().join("tests/fixtures/golden/golden-canvas-anchor.canvas")).unwrap()),
        ("image", "evidence.png", std::fs::read(repo().join("tests/fixtures/golden/golden-screenshot-ocr.png")).unwrap()),
    ];
    let mut before = Vec::new();
    {
        let router = archeaxis_api::runtime::router(executor(dir.path()).await);
        for (kind, name, bytes) in cases {
            let (status, source) = call(&router, "POST", "/api/v1/imports", json!({"name":name,"content_base64":base64::engine::general_purpose::STANDARD.encode(bytes)})).await;
            assert_eq!(status, 202, "{source}");
            let job = format!("oss-{kind}");
            let (status, queued) = call(
                &router,
                "POST",
                "/api/v1/jobs",
                json!({"job_id":job,"kind":kind,"input_ref":source["source_id"]}),
            )
            .await;
            assert_eq!(status, 202, "{queued}");
            let (status, execution) = call(
                &router,
                "POST",
                &format!("/api/v1/jobs/{job}/executions"),
                json!({"deadline_ms":60000}),
            )
            .await;
            assert!(status == 200 || status == 202, "{execution}");
            for _ in 0..600 {
                let (_, state) =
                    call(&router, "GET", &format!("/api/v1/jobs/{job}"), Value::Null).await;
                if state["state"] == "succeeded" {
                    break;
                }
                assert!(
                    state["state"] != "failed" && state["state"] != "rejected",
                    "{state}"
                );
                tokio::time::sleep(std::time::Duration::from_millis(100)).await;
            }
            for output in ["text", "document_structure", "loss_report"] {
                let path = format!("/api/v1/jobs/{job}/outputs/{output}");
                let (status, value) = call(&router, "GET", &path, Value::Null).await;
                assert_eq!(status, 200, "{value}");
                assert_eq!(
                    value["metadata"]["authority_effect"],
                    "candidate_or_measurement_only"
                );
                if output == "text" {
                    let text = value["content"].as_str().unwrap();
                    assert!(!text.trim().is_empty());
                    match kind {
                        "html" => {
                            assert!(text.contains(
                                "A measured result must remain bound to the original source"
                            ));
                            assert!(!text.contains("NOISE_NAV") && !text.contains("NOISE_FOOTER"));
                        }
                        "pdf" => assert!(
                            text.contains("Golden Journey Evidence")
                                && text.contains("Page Anchor")
                        ),
                        "office" => assert!(
                            text.contains("Document evidence anchor")
                                && text.contains("no personal data")
                        ),
                        "image" => assert!(text.contains("OCR GOLDEN ANCHOR")),
                        _ => {}
                    }
                }
                if kind == "html" && output == "loss_report" {
                    let receipt: Value =
                        serde_json::from_str(value["content"].as_str().unwrap()).unwrap();
                    assert_eq!(
                        receipt["params"]["extraction"]["selected_engine"], "trafilatura",
                        "{receipt}"
                    );
                }
                before.push((path, value));
            }
        }
    }
    let reopened = archeaxis_api::runtime::router(executor(dir.path()).await);
    for (path, value) in before {
        assert_eq!(
            call(&reopened, "GET", &path, Value::Null).await,
            (200, value)
        );
    }
}

#[tokio::test]
async fn template_fields_links_and_canvas_are_one_versioned_document_after_restart() {
    let dir = tempfile::tempdir().unwrap();
    let database = dir.path().join("templates.sqlite");
    let editor = json!({"type":"doc","attrs":{"archeaxis_template":{"schema":"archeaxis.template/v1","template_id":"T1","discipline_id":"math","fields":{"question":"How is this related?","status":"unevaluated"},"references":[],"learning_item_key":null}},"content":[{"type":"paragraph","attrs":{"block_id":"sample-block"},"content":[{"type":"text","text":"A hypothesis can be saved before external evaluation."}]}]});
    let created;
    {
        let router = archeaxis_api::app(database.to_str().unwrap()).unwrap();
        let (status, result) = call(
            &router,
            "POST",
            "/api/v1/documents",
            json!({"title":"Math / knowledge network","editor_json":editor}),
        )
        .await;
        assert_eq!(status, 201, "{result}");
        let id = result["document_id"].as_str().unwrap();
        let mut changed = result["editor_json"].clone();
        changed["attrs"]["archeaxis_template"]["references"] = json!([{"document_id":id,"version":1,"block_id":"sample-block","relation":"related","x":20,"y":40}]);
        let (status, saved) = call(
            &router,
            "PUT",
            &format!("/api/v1/documents/{id}/draft"),
            json!({"expected_version":1,"editor_json":changed}),
        )
        .await;
        assert_eq!(status, 200, "{saved}");
        assert_eq!(
            call(
                &router,
                "PUT",
                &format!("/api/v1/documents/{id}/draft"),
                json!({"expected_version":1,"editor_json":editor})
            )
            .await
            .0,
            409
        );
        created = saved;
    }
    let reopened = archeaxis_api::app(database.to_str().unwrap()).unwrap();
    assert_eq!(
        call(
            &reopened,
            "GET",
            &format!(
                "/api/v1/documents/{}",
                created["document_id"].as_str().unwrap()
            ),
            Value::Null
        )
        .await,
        (200, created)
    );
}
