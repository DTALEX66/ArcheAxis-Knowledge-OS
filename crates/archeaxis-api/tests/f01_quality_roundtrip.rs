//! DP-F01 real text quality roundtrip through the Core API read-back.
//!
//! One hand-authored synthetic fixture is imported through `POST /api/v1/imports`,
//! bound to a job through `POST /api/v1/jobs`, executed by the real Rust `Executor`
//! (which drives the real Python `text_ndjson.py` transport, which drives the real
//! `worker_text.py`), and then read back from the public projection routes.
//!
//! The receipt this asserts is the whole one: original hash, transform hash,
//! source/job/transform binding, structure/anchors, quality/loss, engine/version,
//! decoder fallback, and explicit unsupported state.
//!
//! Boundary: this is a controlled synthetic fixture, NOT real-corpus qualification,
//! and it closes no P1 format.

use archeaxis_application::executor::Executor;
use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::Value;
use std::{path::PathBuf, time::Duration};
use tower::ServiceExt;

/// SHA-256, local to this test: `sha2` is not a dev-dependency of this crate, and
/// adding one is outside this card's write set. It is checked against the
/// independently measured fixture digests below, so a wrong implementation fails
/// loudly instead of silently agreeing with itself.
fn sha256(data: &[u8]) -> [u8; 32] {
    const K: [u32; 64] = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
    ];
    let mut state: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ];
    let bit_len = (data.len() as u64).wrapping_mul(8);
    let mut buffer = Vec::with_capacity(data.len() + 72);
    buffer.extend_from_slice(data);
    buffer.push(0x80);
    while buffer.len() % 64 != 56 {
        buffer.push(0);
    }
    buffer.extend_from_slice(&bit_len.to_be_bytes());

    for block in buffer.chunks(64) {
        let mut schedule = [0u32; 64];
        for (index, word) in schedule.iter_mut().take(16).enumerate() {
            let offset = index * 4;
            *word = u32::from_be_bytes([
                block[offset],
                block[offset + 1],
                block[offset + 2],
                block[offset + 3],
            ]);
        }
        for index in 16..64 {
            let s0 = schedule[index - 15].rotate_right(7)
                ^ schedule[index - 15].rotate_right(18)
                ^ (schedule[index - 15] >> 3);
            let s1 = schedule[index - 2].rotate_right(17)
                ^ schedule[index - 2].rotate_right(19)
                ^ (schedule[index - 2] >> 10);
            schedule[index] = schedule[index - 16]
                .wrapping_add(s0)
                .wrapping_add(schedule[index - 7])
                .wrapping_add(s1);
        }
        let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut h) = (
            state[0], state[1], state[2], state[3], state[4], state[5], state[6], state[7],
        );
        for index in 0..64 {
            let big_s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let choice = (e & f) ^ ((!e) & g);
            let temp1 = h
                .wrapping_add(big_s1)
                .wrapping_add(choice)
                .wrapping_add(K[index])
                .wrapping_add(schedule[index]);
            let big_s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let majority = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = big_s0.wrapping_add(majority);
            h = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
        }
        for (slot, value) in state.iter_mut().zip([a, b, c, d, e, f, g, h]) {
            *slot = slot.wrapping_add(value);
        }
    }
    let mut digest = [0u8; 32];
    for (index, word) in state.iter().enumerate() {
        digest[index * 4..index * 4 + 4].copy_from_slice(&word.to_be_bytes());
    }
    digest
}

/// Lowercase hex, local to this test so the crate needs no extra dependency.
fn hex(bytes: impl AsRef<[u8]>) -> String {
    bytes
        .as_ref()
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

fn sha256_hex(data: &[u8]) -> String {
    let digest = sha256(data);
    // Known-answer guard for the local implementation.
    assert_eq!(digest.len(), 32);
    hex(digest)
}

const CONTROLLED_SOURCE_SHA: &str = "70aff728005d7580260391e6754f30209ec5fbecd9803f30a31e48d72eb7b176";
const CONTROLLED_TRANSFORM_SHA: &str = "e5be0cbcaa4580bda39a481f49767ef8c3697f299adb2fa0806dc16592719ab6";
const CONTROLLED_TEXT_CHARS: usize = 535;
const CONTROLLED_LINES: u64 = 17;
const CAPPED_SOURCE_SHA: &str = "71c0029230e042d72e9ec8db74f9a28196b37fdfb29f7df7d68e3b425af38928";
const CAPPED_LINES: u64 = 5001;
const CAPPED_ANCHORS: u64 = 5000;
const GBK_SOURCE_SHA: &str = "8ba7ed5cd0f33c11b7bb447337b0ce852b0a4f52c5ee854b6107943408b2b215";
const GBK_TEXT_SHA: &str = "627f58abc97febb55b9eab82217283d523070ecd70575e02c5fd5fd0789a3b20";

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf()
}

/// Read a fixture and copy it into the test-owned directory.
///
/// The executor's staging directory lives under the test temporary directory, so
/// the fixture is materialised there instead of being read from the checkout while
/// a worker holds the staging area open. The bytes are unchanged.
fn fixture(dir: &std::path::Path, name: &str) -> PathBuf {
    let bytes = std::fs::read(repo_root().join("tests/fixtures/f01-quality").join(name)).unwrap();
    let path = dir.join(name);
    std::fs::write(&path, &bytes).unwrap();
    path
}

fn python() -> PathBuf {
    PathBuf::from(
        std::env::var_os("ARCHEAXIS_PYTHON")
            .expect("run cargo via scripts/runtime/dev.py to select the exact Python"),
    )
}

fn transport() -> PathBuf {
    repo_root().join("services/python-workers/transport/text_ndjson.py")
}

async fn call(
    router: &axum::Router,
    method: &str,
    path: &str,
    key: &str,
    body: &str,
) -> (StatusCode, Value) {
    let mut request = Request::builder().method(method).uri(path);
    if method == "POST" {
        request = request.header("content-type", "application/json");
    }
    if !key.is_empty() {
        request = request.header("idempotency-key", key);
    }
    let response = router
        .clone()
        .oneshot(request.body(Body::from(body.to_owned())).unwrap())
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or(Value::Null))
}

async fn terminal(router: &axum::Router, job_id: &str) -> Value {
    tokio::time::timeout(Duration::from_secs(30), async {
        loop {
            let (status, value) = call(router, "GET", &format!("/api/v1/jobs/{job_id}"), "", "").await;
            assert_eq!(status, StatusCode::OK, "{value}");
            if value["state"] != "running" && value["state"] != "queued" {
                return value;
            }
            tokio::time::sleep(Duration::from_millis(20)).await;
        }
    })
    .await
    .unwrap_or_else(|_| panic!("job {job_id} never reached a terminal state"))
}

/// Import the fixture and enqueue one text job against the exact source hash.
async fn import_and_enqueue(router: &axum::Router, path: &std::path::Path, name: &str, job_id: &str) -> String {
    let bytes = std::fs::read(path).unwrap();
    let sha = sha256_hex(&bytes);
    use base64::Engine;
    let encoded = base64::engine::general_purpose::STANDARD.encode(&bytes);
    let (status, imported) = call(
        router,
        "POST",
        "/api/v1/imports",
        "",
        &serde_json::json!({"name": name, "content_base64": encoded}).to_string(),
    )
    .await;
    assert_eq!(status, StatusCode::ACCEPTED, "{imported}");
    assert_eq!(imported["sha256"].as_str().unwrap(), sha, "Core must store the original bytes unchanged");
    assert_eq!(imported["duplicate"], false);
    let source_id = imported["source_id"].as_str().unwrap().to_string();
    let (status, queued) = call(
        router,
        "POST",
        "/api/v1/jobs",
        "",
        &serde_json::json!({"job_id": job_id, "kind": "text", "input_ref": source_id}).to_string(),
    )
    .await;
    assert_eq!(status, StatusCode::ACCEPTED, "{queued}");
    assert_eq!(queued["state"], "queued");
    source_id
}

async fn run_job(router: &axum::Router, job_id: &str) -> Value {
    let (status, started) = call(
        router,
        "POST",
        &format!("/api/v1/jobs/{job_id}/executions"),
        &format!("{job_id}-run-1"),
        r#"{"deadline_ms":60000}"#,
    )
    .await;
    assert_eq!(status, StatusCode::ACCEPTED, "{started}");
    terminal(router, job_id).await
}

fn body_of(value: &Value) -> String {
    value["content"].as_str().unwrap_or_default().to_string()
}

/// Known-answer check for the local SHA-256, so a broken implementation cannot
/// silently agree with a broken expectation elsewhere in this file.
#[test]
fn local_sha256_matches_published_test_vectors() {
    assert_eq!(
        sha256_hex(b""),
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    );
    assert_eq!(
        sha256_hex(b"abc"),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    );
    assert_eq!(
        sha256_hex(b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"),
        "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"
    );
}

#[tokio::test]
async fn f01_controlled_markdown_roundtrip_preserves_the_whole_receipt() {
    let dir = tempfile::tempdir().unwrap();
    let path = fixture(dir.path(), "controlled.md");
    assert_eq!(
        sha256_hex(&std::fs::read(&path).unwrap()),
        CONTROLLED_SOURCE_SHA,
        "fixture provenance changed"
    );

    let executor = Executor::open(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python(),
        &transport(),
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    let source_id = import_and_enqueue(&router, &path, "controlled.md", "f01-controlled").await;

    // Source/job binding is persisted before anything runs.
    let (status, jobs) = call(&router, "GET", &format!("/api/v1/sources/{source_id}/jobs"), "", "").await;
    assert_eq!(status, StatusCode::OK, "{jobs}");
    assert_eq!(jobs["source_id"], source_id);
    assert_eq!(jobs["jobs"][0]["job_id"], "f01-controlled");
    assert_eq!(jobs["jobs"][0]["input_ref"], source_id, "a job must project its persisted source binding");
    assert_eq!(jobs["jobs"][0]["kind"], "text");

    let job = run_job(&router, "f01-controlled").await;
    assert_eq!(job["state"], "succeeded", "{job}");
    assert_eq!(job["input_ref"], source_id);
    assert_eq!(job["attempt"], 1);

    // Read-back: text content is the projected text, and its transform hash is
    // recomputed here from the content the API really returned.
    let (status, text_output) = call(&router, "GET", "/api/v1/jobs/f01-controlled/outputs/text", "", "").await;
    assert_eq!(status, StatusCode::OK, "{text_output}");
    let text = body_of(&text_output);
    assert_eq!(text.chars().count(), CONTROLLED_TEXT_CHARS);
    assert_eq!(text.split_inclusive('\n').count() as u64, CONTROLLED_LINES);
    assert_eq!(sha256_hex(text.as_bytes()), CONTROLLED_TRANSFORM_SHA);
    assert_ne!(CONTROLLED_TRANSFORM_SHA, CONTROLLED_SOURCE_SHA, "a transform must not be the original");
    assert_eq!(text_output["metadata"]["kind"], "text");
    assert_eq!(text_output["metadata"]["schema"], "archeaxis.text/v1");
    assert_eq!(text_output["metadata"]["authority_effect"], "candidate_or_measurement_only");

    // Structure/anchors: the last anchor must end at the last character.
    let (status, structure_output) =
        call(&router, "GET", "/api/v1/jobs/f01-controlled/outputs/document_structure", "", "").await;
    assert_eq!(status, StatusCode::OK, "{structure_output}");
    let structure: Value = serde_json::from_str(&body_of(&structure_output)).unwrap();
    let anchors = structure.as_array().unwrap();
    assert_eq!(anchors.len() as u64, CONTROLLED_LINES);
    assert_eq!(anchors[0], serde_json::json!({"kind":"line","path":["line-1"],"char_start":0,"char_end":4}));
    let last = anchors.last().unwrap();
    assert_eq!(last["path"], serde_json::json!(["line-17"]));
    assert_eq!(last["kind"], "line");
    assert_eq!(last["char_end"].as_u64().unwrap() as usize, CONTROLLED_TEXT_CHARS);

    // Quality/loss read back from the public quality projection.
    let (status, quality) = call(&router, "GET", "/api/v1/jobs/f01-controlled/quality", "", "").await;
    assert_eq!(status, StatusCode::OK, "{quality}");
    assert_eq!(quality["state"], "succeeded");
    assert_eq!(quality["engine"], "python-worker-text");
    assert_eq!(quality["engine_version"], "0.1.0");
    assert_eq!(quality["covered"], CONTROLLED_LINES);
    assert_eq!(quality["total"], CONTROLLED_LINES);
    assert_eq!(quality["coverage"], 1.0);
    assert_eq!(quality["loss_count"], 1, "the BOM strip is exactly one documented loss");
    assert!(quality.get("accuracy").is_none(), "no accuracy figure may be reported");

    // Loss report: explicit, named loss; no invented fallback or unsupported state.
    let (status, loss_output) = call(&router, "GET", "/api/v1/jobs/f01-controlled/outputs/loss_report", "", "").await;
    assert_eq!(status, StatusCode::OK, "{loss_output}");
    let loss: Value = serde_json::from_str(&body_of(&loss_output)).unwrap();
    assert_eq!(loss["engine"], "python-worker-text");
    assert_eq!(loss["engine_version"], "0.1.0");
    assert_eq!(loss["params"]["decode"], "utf-8-sig");
    assert_eq!(loss["params"]["media_type"], "text/markdown");
    assert_eq!(loss["losses"], serde_json::json!(["UTF-8 BOM stripped"]));
    assert!(loss["loss_note"].as_str().unwrap().contains("UTF-8 BOM stripped"));
    let facts = &loss["params"]["format"];
    assert_eq!(facts["format"], "markdown");
    assert_eq!(facts["parsed"], true);
    assert_eq!(facts["frontmatter"], true);
    assert_eq!(facts["heading_count"], 2);
    assert_eq!(facts["wiki_link_count"], 1);
    assert_eq!(facts["embed_count"], 1);
    assert_eq!(facts["markdown_link_count"], 1);
    assert_eq!(facts["code_fence_count"], 2);
    assert_eq!(facts["list_item_count"], 2);
    // This fixture carries no fallback field at all: absent, not fabricated.
    assert!(loss["params"]["format"].get("fallback").is_none());
    assert!(loss["params"]["format"].get("unsupported").is_none());

    // Source/job/transform binding, read back from persisted Core state.
    let bound: (String, String, i64, String) = executor
        .store()
        .submit(move |conn| {
            conn.query_row(
                "SELECT s.sha256, j.input_ref, j.transform_id, t.source_id
                 FROM jobs j JOIN sources s ON s.source_id=j.input_ref
                 JOIN transforms t ON t.transform_id=j.transform_id WHERE j.job_id='f01-controlled'",
                [],
                |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)),
            )
        })
        .await
        .unwrap()
        .unwrap();
    assert_eq!(bound.0, CONTROLLED_SOURCE_SHA, "job source hash");
    assert_eq!(bound.1, source_id, "job input_ref");
    assert_eq!(bound.3, source_id, "the transform must belong to the same source");
    assert!(bound.2 > 0, "a successful job must bind a transform id");

    // Restart read-back: reopen the same workspace and re-read the same receipt.
    drop(router);
    drop(executor);
    let restored = Executor::open(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python(),
        &transport(),
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(restored);
    let (status, replay) = call(
        &router,
        "POST",
        "/api/v1/jobs/f01-controlled/executions",
        "f01-controlled-run-1",
        r#"{"deadline_ms":60000}"#,
    )
    .await;
    assert_eq!(status, StatusCode::ACCEPTED, "{replay}");
    assert_eq!(replay["replayed"], true, "the same idempotency key must replay, not re-transform");
    let (status, quality_after) = call(&router, "GET", "/api/v1/jobs/f01-controlled/quality", "", "").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(quality_after["engine"], quality["engine"]);
    assert_eq!(quality_after["engine_version"], quality["engine_version"]);
    assert_eq!(quality_after["covered"], quality["covered"]);
    let (status, text_after) = call(&router, "GET", "/api/v1/jobs/f01-controlled/outputs/text", "", "").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body_of(&text_after), text, "restart read-back must return the same transform");
}

#[tokio::test]
async fn f01_capped_fixture_reports_anchor_loss_and_never_claims_full_coverage() {
    let dir = tempfile::tempdir().unwrap();
    let path = fixture(dir.path(), "capped-lines.md");
    assert_eq!(
        sha256_hex(&std::fs::read(&path).unwrap()),
        CAPPED_SOURCE_SHA
    );
    let executor = Executor::open(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python(),
        &transport(),
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor);
    let _source_id = import_and_enqueue(&router, &path, "capped-lines.md", "f01-capped").await;
    let job = run_job(&router, "f01-capped").await;
    assert_eq!(job["state"], "succeeded", "{job}");

    let (status, quality) = call(&router, "GET", "/api/v1/jobs/f01-capped/quality", "", "").await;
    assert_eq!(status, StatusCode::OK, "{quality}");
    assert_eq!(quality["covered"], CAPPED_ANCHORS);
    assert_eq!(quality["total"], CAPPED_LINES);
    assert!(quality["coverage"].as_f64().unwrap() < 1.0);
    assert_eq!(quality["loss_count"], 2, "BOM strip and the anchor cap are two losses");

    let (status, structure_output) =
        call(&router, "GET", "/api/v1/jobs/f01-capped/outputs/document_structure", "", "").await;
    assert_eq!(status, StatusCode::OK);
    let structure: Value = serde_json::from_str(&body_of(&structure_output)).unwrap();
    assert_eq!(structure.as_array().unwrap().len() as u64, CAPPED_ANCHORS);
}

#[tokio::test]
async fn f01_decoder_fallback_is_persisted_and_read_back() {
    let dir = tempfile::tempdir().unwrap();
    let path = fixture(dir.path(), "fallback-gbk.txt");
    let raw = std::fs::read(&path).unwrap();
    assert_eq!(sha256_hex(&raw), GBK_SOURCE_SHA);
    // The fixture must really be invalid UTF-8, or the fallback proves nothing.
    assert!(std::str::from_utf8(&raw).is_err());

    let executor = Executor::open(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python(),
        &transport(),
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor);
    let _source_id = import_and_enqueue(&router, &path, "fallback-gbk.txt", "f01-gbk").await;
    let job = run_job(&router, "f01-gbk").await;
    assert_eq!(job["state"], "succeeded", "{job}");

    let (status, text_output) = call(&router, "GET", "/api/v1/jobs/f01-gbk/outputs/text", "", "").await;
    assert_eq!(status, StatusCode::OK, "{text_output}");
    let text = body_of(&text_output);
    assert_eq!(sha256_hex(text.as_bytes()), GBK_TEXT_SHA);
    assert_eq!(text, "简体中文回退编码\nGBK 回退第二行\n");

    let (status, loss_output) = call(&router, "GET", "/api/v1/jobs/f01-gbk/outputs/loss_report", "", "").await;
    assert_eq!(status, StatusCode::OK);
    let loss: Value = serde_json::from_str(&body_of(&loss_output)).unwrap();
    assert_eq!(loss["params"]["decode"], "gbk", "the fallback decoder must be named, not hidden");
    assert!(loss["loss_note"].as_str().unwrap().contains("gbk"));
    // The fallback must also be stated as a loss entry, not only as a parameter.
    assert_eq!(loss["losses"].as_array().unwrap().len(), 1, "{loss}");
    assert!(loss["losses"][0].as_str().unwrap().contains("gbk"), "{loss}");
    assert_eq!(loss["covered"], 2, "two decoded lines are anchored");
    assert_eq!(loss["total"], 2);
}

#[tokio::test]
async fn f01_unsupported_extension_is_refused_explicitly_and_never_guessed() {
    let dir = tempfile::tempdir().unwrap();
    let path = fixture(dir.path(), "unsupported.unknown-ext");
    let executor = Executor::open(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python(),
        &transport(),
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    // Enqueue succeeds: the source really is bound to a job; it is the *media type*
    // that cannot be named, and that is only discovered when the job is claimed.
    let source_id = import_and_enqueue(&router, &path, "unsupported.unknown-ext", "f01-unsupported").await;

    // The direct executor call is the authoritative refusal: it fails by name and
    // never dispatches a worker under a guessed media type.
    let direct = executor
        .execute(
            "f01-unsupported",
            "f01-unsupported-run-1",
            30_000,
            &archeaxis_application::executor::Cancellation::new(),
        )
        .await
        .unwrap_err();
    assert!(
        direct.contains("cannot name a media type"),
        "the refusal must name the actual reason: {direct}"
    );

    // The HTTP entry must project the same refusal as an explicit conflict, not as
    // a pretense that the job is running.
    let (status, refused) = call(
        &router,
        "POST",
        "/api/v1/jobs/f01-unsupported/executions",
        "f01-unsupported-run-2",
        r#"{"deadline_ms":30000}"#,
    )
    .await;
    assert_eq!(status, StatusCode::CONFLICT, "{refused}");
    assert_eq!(refused["code"], "AAK-CON-003");
    assert_eq!(refused["retryable"], false);

    // Nothing was written and no transform exists: the refusal is not a partial run.
    let (status, job) = call(&router, "GET", "/api/v1/jobs/f01-unsupported", "", "").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(job["state"], "queued", "a refused claim must leave the job claimable: {job}");
    assert_eq!(job["input_ref"], source_id);
    assert!(job["attempt"].is_null(), "{job}");
    let (status, _) = call(&router, "GET", "/api/v1/jobs/f01-unsupported/outputs/text", "", "").await;
    assert_eq!(status, StatusCode::NOT_FOUND, "a refused job must expose no transform");
    let transforms: i64 = executor
        .store()
        .submit(|conn| conn.query_row("SELECT count(*) FROM transforms", [], |r| r.get(0)))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(transforms, 0, "no transform may be written for a refused input");

    // Control: the same executor and the same text route DO process a name whose
    // media type can be resolved, so the refusal above is about the name, not about
    // a broken executor.
    let readable = dir.path().join("f01-readable.txt");
    std::fs::write(&readable, "readable control line\n").unwrap();
    let _control = import_and_enqueue(&router, &readable, "f01-readable.txt", "f01-control").await;
    let control = run_job(&router, "f01-control").await;
    assert_eq!(control["state"], "succeeded", "{control}");
}
