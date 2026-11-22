//! New MHTML-only Core/worker fixtures. This does not qualify an installed browser archive.
use archeaxis_application::{
    attempts,
    executor::{Cancellation, Executor},
    jobs,
};
use archeaxis_domain::source::{self, ImportOutcome};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};

const MHTML: &[u8] = b"MIME-Version: 1.0\r\nContent-Type: multipart/related; boundary=BOUND; type=\"text/html\"; start=\"<root>\"\r\n\r\n\
--BOUND\r\nContent-Type: image/png\r\nContent-ID: <image>\r\nContent-Transfer-Encoding: base64\r\nContent-Location: ../../private.png\r\n\r\naW1hZ2U=\r\n\
--BOUND\r\nContent-Type: text/html; charset=utf-8\r\nContent-ID: <root>\r\nContent-Location: https://example.invalid/saved\r\n\r\n\
<html><body><p>Selected root 6371</p><script>DO_NOT_EXECUTE</script><img src=\"cid:image\"><p>Second paragraph</p></body></html>\r\n\
--BOUND--\r\n";

async fn open_executor(root: &Path) -> Executor {
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .unwrap();
    let python =
        PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").expect("run via the project wrapper"));
    Executor::open_routes(
        &root.join("db.sqlite"),
        &root.join("staging"),
        &python,
        &repo.join("services/python-workers/transport/text_ndjson.py"),
        &[(
            "html.structure",
            repo.join("services/python-workers/web/worker_html.py"),
        )],
    )
    .await
    .unwrap()
}

#[test]
fn mhtml_selects_html_route_without_reclassifying_ordinary_mail() {
    for name in ["saved.mht", "saved.MHTML"] {
        assert_eq!(
            attempts::resolve_media_type("html", name).unwrap(),
            "multipart/related"
        );
        assert!(attempts::resolve_media_type("text", name).is_err());
    }
    assert_eq!(
        attempts::resolve_media_type("text", "mail.eml").unwrap(),
        "message/rfc822"
    );
    assert!(attempts::resolve_media_type("html", "mail.eml").is_err());
}

#[tokio::test]
async fn mhtml_job_preserves_original_and_binds_decoded_root_locations_and_losses() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let source_id = executor
        .store()
        .submit(|conn| {
            let id = match source::import_source(conn, MHTML, "saved.mhtml", None).unwrap() {
                ImportOutcome::Imported { source_id, .. }
                | ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "mhtml-fixture", "html", &id).unwrap();
            id
        })
        .await
        .unwrap();
    executor
        .execute(
            "mhtml-fixture",
            "mhtml-request",
            120_000,
            &Cancellation::new(),
        )
        .await
        .unwrap();
    let digest = hex::encode(Sha256::digest(MHTML));
    let (state, text, loss, original) = executor.store().submit(move |conn| {
        let text: String = conn.query_row("SELECT text FROM transforms WHERE source_id=?1 ORDER BY transform_id DESC LIMIT 1", [&source_id], |row| row.get(0)).unwrap();
        let loss: String = conn.query_row("SELECT content FROM job_outputs WHERE job_id='mhtml-fixture' AND kind='loss_report'", [], |row| row.get(0)).unwrap();
        (jobs::job_state(conn, "mhtml-fixture").unwrap().unwrap(), text, loss,
         archeaxis_store_sqlite::raw_objects::read(conn, &digest).unwrap())
    }).await.unwrap();
    assert_eq!(state, "succeeded");
    assert_eq!(original, MHTML);
    assert!(text.contains("Selected root 6371") && text.contains("Second paragraph"));
    assert!(!text.contains("DO_NOT_EXECUTE") && !text.contains("private.png"));
    let receipt: Value = serde_json::from_str(&loss).unwrap();
    assert_eq!(receipt["engine_version"], "0.1.1");
    assert_eq!(
        receipt["params"]["source_sha256"],
        hex::encode(Sha256::digest(MHTML))
    );
    assert_eq!(
        receipt["params"]["mhtml"]["root"]["path"],
        serde_json::json!(["mime-part-2"])
    );
    assert_eq!(receipt["params"]["mhtml"]["resource_count"], 1);
    assert_eq!(
        receipt["params"]["worker_output"]["format_execution_receipt"]["original"]["format"],
        "mhtml"
    );
    assert!(
        receipt["loss_note"]
            .as_str()
            .unwrap()
            .contains("never archive byte offsets")
    );
    for anchor in receipt["params"]["worker_structure"].as_array().unwrap() {
        assert_eq!(anchor["kind"], "mhtml_block");
        assert_eq!(anchor["path"][0], "mime-part-2");
        let start = anchor["char_start"].as_u64().unwrap() as usize;
        let end = anchor["char_end"].as_u64().unwrap() as usize;
        assert!(end > start && end <= text.chars().count());
        assert!(
            !text
                .chars()
                .skip(start)
                .take(end - start)
                .collect::<String>()
                .trim()
                .is_empty()
        );
    }
}

#[tokio::test]
async fn mhtml_missing_selected_root_fails_without_publishing_an_alternate_body() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let malformed = String::from_utf8(MHTML.to_vec())
        .unwrap()
        .replace("start=\"<root>\"", "start=\"<absent>\"")
        .into_bytes();
    let original = malformed.clone();
    let digest = hex::encode(Sha256::digest(&original));
    executor
        .store()
        .submit(move |conn| {
            let id =
                match source::import_source(conn, &malformed, "missing-root.mht", None).unwrap() {
                    ImportOutcome::Imported { source_id, .. }
                    | ImportOutcome::Duplicate { source_id, .. } => source_id,
                };
            jobs::enqueue(conn, "mhtml-refused", "html", &id).unwrap();
        })
        .await
        .unwrap();
    assert!(
        executor
            .execute(
                "mhtml-refused",
                "mhtml-bad-request",
                60_000,
                &Cancellation::new()
            )
            .await
            .is_err()
    );
    let (state, count, retained) = executor.store().submit(move |conn| {
        let count: i64 = conn.query_row("SELECT count(*) FROM job_outputs WHERE job_id='mhtml-refused' AND kind IN ('text','document_structure')", [], |row| row.get(0)).unwrap();
        (jobs::job_state(conn, "mhtml-refused").unwrap().unwrap(), count,
         archeaxis_store_sqlite::raw_objects::read(conn, &digest).unwrap())
    }).await.unwrap();
    assert_eq!(state, "failed");
    assert_eq!(count, 0);
    assert_eq!(retained, original);
}
