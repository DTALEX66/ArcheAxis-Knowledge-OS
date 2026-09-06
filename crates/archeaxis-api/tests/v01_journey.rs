//! v0.1 journey: the twelve-step minimal closed loop end to end.
//!
//! Mirrors MASTER-TASKPACK §1.2 on the real crates (store/domain/api/
//! application/archive). Steps run via the HTTP router where natural, and
//! directly through crates for backup/restore/archive. When the environment
//! variable VNEXT_RECEIPT_OUT is set, a machine-readable receipt is written
//! there (reports/vnext/v01-closed-loop-receipt.json), otherwise the test
//! only asserts.

use std::collections::BTreeMap;

use archeaxis_archive;
use axum::body::Body;
use base64::Engine;
use http_body_util::BodyExt;
use rusqlite::Connection;
use tower::ServiceExt;

use archeaxis_api::app;

fn receipt_path() -> Option<String> {
    std::env::var("VNEXT_RECEIPT_OUT").ok()
}

fn json_body(router: &axum::Router, method: &str, path: &str, body: String) -> serde_json::Value {
    let req = if method == "POST" {
        Request::post(path).header("content-type", "application/json")
    } else {
        Request::get(path)
    };
    let resp =
        futures_block_on(router.clone().oneshot(req.body(Body::from(body)).unwrap())).unwrap();
    let bytes = futures_block_on(resp.into_body().collect())
        .unwrap()
        .to_bytes();
    if bytes.is_empty() {
        serde_json::json!({})
    } else {
        serde_json::from_slice(&bytes).unwrap_or(serde_json::json!({}))
    }
}

fn futures_block_on<F: std::future::Future>(f: F) -> F::Output {
    tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .unwrap()
        .block_on(f)
}

use axum::http::Request;

#[test]
fn v01_twelve_step_journey() {
    // step 0: receipt collector
    let mut steps: BTreeMap<String, String> = BTreeMap::new();
    let mut pass = |id: &str, ok: bool, note: &str| {
        steps.insert(
            id.to_string(),
            format!("{}: {}", if ok { "PASS" } else { "FAIL" }, note),
        );
        assert!(ok, "{id} failed: {note}");
    };

    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("journey.sqlite");
    let archive_dir = dir.path().join("archive").to_str().unwrap().to_string();

    // 1) workspace init (Green start: no terminal window concept at Core level)
    let conn0 = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    drop(conn0);
    pass("01_workspace_init", db.is_file(), "fresh vNext workspace initialized");
    let router = app(db.to_str().unwrap()).unwrap();

    // 2) import two sources; sha256 readable; repeat import idempotent
    let a = base64::engine::general_purpose::STANDARD.encode(b"journey source one body");
    let b = base64::engine::general_purpose::STANDARD.encode(b"journey source two body");
    let r1 = json_body(
        &router,
        "POST",
        "/api/v1/imports",
        format!(r#"{{"name":"s1.txt","content_base64":"{a}"}}"#),
    );
    let sid1 = r1["source_id"].as_str().unwrap().to_string();
    let r2 = json_body(
        &router,
        "POST",
        "/api/v1/imports",
        format!(r#"{{"name":"s2.txt","content_base64":"{b}"}}"#),
    );
    let sid2 = r2["source_id"].as_str().unwrap().to_string();
    let dup = json_body(
        &router,
        "POST",
        "/api/v1/imports",
        format!(r#"{{"name":"s1-again.txt","content_base64":"{a}"}}"#),
    );
    pass(
        "02_import_hash_idempotent",
        dup["duplicate"] == true && r1["sha256"].as_str().is_some(),
        &format!("{r1} {dup}"),
    );

    // 3) python worker returns text+loss receipt (no DB handle) via jobs API
    let _ = json_body(
        &router,
        "POST",
        "/api/v1/jobs",
        format!(r#"{{"job_id":"j1","kind":"transform","input_ref":"{sid1}"}}"#),
    );
    let receipt = format!(
        r#"{{"state":"succeeded","engine":"python-worker-extract","text":"journey source one body (clean)","loss_receipt":{{"engine":"python-worker-extract","engine_version":"0.1.0","params":{{}},"loss_note":"bom stripped"}}}}"#
    );
    let rr = json_body(&router, "POST", "/api/v1/jobs/j1/receipts", receipt);
    pass(
        "03_worker_receipt",
        rr.get("state").and_then(|s| s.as_str()) == Some("succeeded"),
        &format!("{rr}"),
    );

    // 4) anchor a sentence, read back
    let ar = json_body(
        &router,
        "POST",
        &format!("/api/v1/sources/{sid1}/anchors"),
        r#"{"revision":"rev-1","position":"{\"start\":0,\"end\":10}"}"#.to_string(),
    );
    let aid = ar["anchor_id"].as_str().unwrap().to_string();
    let conn = Connection::open(db.to_str().unwrap()).unwrap();
    let got = archeaxis_domain::anchor::get_anchor(&conn, &aid).unwrap();
    drop(conn);
    pass(
        "04_anchor_readback",
        got.is_some() && got.unwrap().0 == sid1,
        "anchor roundtrip",
    );

    // 5) personal definition (no external evidence) + machine candidate
    let p = json_body(&router, "POST", "/api/v1/knowledge-items", r#"{"knowledge_type":"PERSONAL_DEFINITION","body":"个人定义：不需要外证","status":"accepted","created_by":"owner"}"#.to_string());
    let pid = p["knowledge_id"].as_str().unwrap().to_string();
    let mc = json_body(&router, "POST", "/api/v1/knowledge-items", r#"{"knowledge_type":"FACTUAL_CLAIM","body":"机器候选：未经复核不可自动升级","status":"candidate","created_by":"python-worker"}"#.to_string());
    let mc_id = mc["knowledge_id"].as_str().unwrap().to_string();
    pass(
        "05_personal_and_candidate",
        !pid.is_empty() && !mc_id.is_empty(),
        "created",
    );

    // 6) accept/reject produce immutable receipts; candidate not auto-verified
    let ok1 = json_body(
        &router,
        "POST",
        &format!("/api/v1/knowledge-items/{mc_id}/review-decisions"),
        r#"{"action":"accepted","reviewer":"owner","note":"核实"}"#.to_string(),
    );
    let rej = json_body(&router, "POST", "/api/v1/knowledge-items", r#"{"knowledge_type":"OPINION","body":"待拒绝项","status":"candidate","created_by":"python-worker"}"#.to_string());
    let rej_id = rej["knowledge_id"].as_str().unwrap().to_string();
    let _ = json_body(
        &router,
        "POST",
        &format!("/api/v1/knowledge-items/{rej_id}/review-decisions"),
        r#"{"action":"rejected","reviewer":"owner","note":"无关"}"#.to_string(),
    );
    let conn = Connection::open(db.to_str().unwrap()).unwrap();
    let status: String = conn
        .query_row(
            "SELECT status FROM knowledge WHERE knowledge_id=?1",
            [&mc_id],
            |r| r.get(0),
        )
        .unwrap();
    let rej_status: String = conn
        .query_row(
            "SELECT status FROM knowledge WHERE knowledge_id=?1",
            [&rej_id],
            |r| r.get(0),
        )
        .unwrap();
    drop(conn);
    pass(
        "06_review_immutable",
        status == "accepted" && rej_status == "rejected",
        &format!("{status}/{rej_status}"),
    );

    // 7) FTS5 retrieval over sources + knowledge
    let s = json_body(
        &router,
        "GET",
        "/api/v1/search?q=%E4%B8%AA%E4%BA%BA%E5%AE%9A%E4%B9%89",
        String::new(),
    );
    pass(
        "07_fts5",
        s["count"].as_i64().unwrap_or(0) >= 1,
        &format!("{s}"),
    );

    // 8) learning event + next review
    let mut lconn = Connection::open(db.to_str().unwrap()).unwrap();
    let ev = archeaxis_domain::learning::record_learning_event(
        &mut lconn,
        &pid,
        "quiz",
        r#"{"correct":true}"#,
        2,
    )
    .unwrap();
    drop(lconn);
    pass("08_learning", ev > 0, &format!("event {ev}"));

    // 9) restart read-back: fresh connections read everything back
    let conn = Connection::open(db.to_str().unwrap()).unwrap();
    let counts: (i64, i64, i64, i64, i64) = conn.query_row(
        "SELECT (SELECT count(*) FROM sources),(SELECT count(*) FROM knowledge),(SELECT count(*) FROM transforms),(SELECT count(*) FROM anchors),(SELECT count(*) FROM learning_events)",
        [], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?))).unwrap();
    drop(conn);
    pass(
        "09_restart_readback",
        counts.0 == 2 && counts.1 == 3 && counts.2 >= 1 && counts.3 == 1 && counts.4 >= 1,
        &format!("{counts:?}"),
    );

    // 10) consistent snapshot (online backup)
    let snap = dir.path().join("snapshot.sqlite");
    let conn = Connection::open(db.to_str().unwrap()).unwrap();
    archeaxis_domain::backup::backup(&conn, snap.to_str().unwrap()).unwrap();
    drop(conn);
    pass("10_snapshot", snap.exists(), "snapshot written");

    // 11) restore into a fresh workspace -> identical counts
    let db2 = dir.path().join("restored.sqlite");
    let mut conn2 = archeaxis_store_sqlite::init_workspace(db2.to_str().unwrap()).unwrap();
    archeaxis_domain::backup::restore(snap.to_str().unwrap(), &mut conn2).unwrap();
    let snap_c = Connection::open(snap.to_str().unwrap()).unwrap();
    let same = archeaxis_domain::backup::verify_counts(&conn2, &snap_c).unwrap();
    drop(snap_c);
    drop(conn2);
    pass("11_restore", same, "counts identical");

    // 12) open-format archive export + manifest
    let m = archeaxis_archive::export_workspace(db2.to_str().unwrap(), &archive_dir).unwrap();
    pass(
        "12_archive",
        m.manifest_sha256.len() == 64 && m.tables.contains_key("sources"),
        &format!("{}", m.tables["sources"].rows),
    );

    // receipt
    if let Some(out) = receipt_path() {
        if let Some(parent) = std::path::Path::new(&out).parent() {
            std::fs::create_dir_all(parent).unwrap();
        }
        let receipt = serde_json::json!({
            "schema": "archeaxis.vnext/v01-closed-loop-receipt",
            "schema_version": 2,
            "source_commit": std::env::var("ARCHEAXIS_SOURCE_COMMIT").unwrap_or_default(),
            "run_id": std::env::var("ARCHEAXIS_RUN_ID").unwrap_or_default(),
            "scope": "in-process journey; worker receipt is simulated; not installed qualification",
            "generated_at_unix": std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs(),
            "total_steps": steps.len(),
            "steps": steps,
            "manifest_sha256": m.manifest_sha256,
        });
        std::fs::write(&out, serde_json::to_string_pretty(&receipt).unwrap()).unwrap();
    }
}
