use archeaxis_application::{attempts, bootstrap, jobs};
use archeaxis_domain::{
    backup,
    source::{self, ImportOutcome},
};
use archeaxis_sidecar_protocol::worker::{Output, Request, Response};
use archeaxis_store_sqlite::raw_objects;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

fn digest(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}
fn receipt(req: &Request, path: &std::path::Path, sha: &str) -> (Response, Vec<Vec<u8>>) {
    let body = json!({"engine":"python-worker-video","engine_version":"0.1.0","params":{"worker_output":{"source_sha256":req.inputs[0].sha256,"duration_ms":1000,"frames":[{"path":path.to_str().unwrap(),"sha256":sha,"sampling_seek_requested_ms":0}],"audio_wav":null,"visual_results":[]}},"loss_note":"sampled only, actual PTS unavailable","losses":[],"covered":1,"total":1,"coverage":1.0});
    let bytes = vec![
        b"known".to_vec(),
        serde_json::to_vec(&json!([{"kind":"line","path":["line-1"],"char_start":0,"char_end":5}]))
            .unwrap(),
        serde_json::to_vec(&body).unwrap(),
    ];
    let outputs = [
        ("text", "archeaxis.text/v1", "text/plain; charset=utf-8"),
        (
            "document_structure",
            "archeaxis.document-structure/v1",
            "application/json",
        ),
        (
            "loss_report",
            "archeaxis.loss-receipt/v1",
            "application/json",
        ),
    ]
    .into_iter()
    .zip(&bytes)
    .map(|((kind, schema, media), data)| {
        let sha = digest(data);
        Output {
            kind: kind.into(),
            schema: schema.into(),
            media_type: media.into(),
            byte_length: data.len() as u64,
            uri: format!("job://output/{sha}"),
            sha256: sha,
            authority_effect: "candidate_or_measurement_only".into(),
        }
    })
    .collect();
    (
        Response {
            schema: "archeaxis.worker-response/v1".into(),
            message_type: "job_result".into(),
            request_id: req.request_id.clone(),
            job_id: req.job_id.clone(),
            attempt: req.attempt,
            protocol_minor: 0,
            status: "succeeded".into(),
            outputs,
            measurements: Default::default(),
            warnings: vec![],
            error: None,
        },
        bytes,
    )
}
fn setup() -> (
    tempfile::TempDir,
    rusqlite::Connection,
    Request,
    std::path::PathBuf,
    std::path::PathBuf,
) {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let (mut conn, _) = bootstrap(db.to_str().unwrap()).unwrap();
    let id = match source::import_source(&mut conn, b"immutable original video", "lesson.mp4", None)
        .unwrap()
    {
        ImportOutcome::Imported { source_id, .. } => source_id,
        _ => unreachable!(),
    };
    jobs::enqueue(&mut conn, "video-job", "video", &id).unwrap();
    let req = attempts::claim(&mut conn, "video-job", "video-request", 300000).unwrap();
    let root = dir.path().join("staging");
    std::fs::create_dir(&root).unwrap();
    let image = root.join("frame.jpg");
    std::fs::write(&image, b"actual controlled decoded bytes").unwrap();
    (dir, conn, req, root, image)
}
#[test]
fn decoded_custody_survives_reopen_staging_loss_and_backup_restore() {
    let (dir, mut conn, req, root, image) = setup();
    let frame = b"actual controlled decoded bytes";
    let sha = digest(frame);
    let (response, payloads) = receipt(&req, &image, &sha);
    attempts::finish_with_artifacts(&mut conn, &req, &response, &payloads, &root).unwrap();
    let original: String = conn
        .query_row(
            "SELECT content FROM job_outputs WHERE kind='loss_report'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(original.as_bytes(), payloads[2]);
    let loss: String = conn
        .query_row(
            "SELECT loss_receipt FROM jobs WHERE job_id='video-job'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let loss: Value = serde_json::from_str(&loss).unwrap();
    let adoption = &loss["params"]["core_artifact_adoption"];
    assert_eq!(adoption["job_id"], "video-job");
    assert_eq!(adoption["attempt"], 1);
    assert_eq!(adoption["source_sha256"], req.inputs[0].sha256);
    assert_eq!(raw_objects::read(&conn, &sha).unwrap(), frame);
    assert_eq!(adoption["artifacts"][0]["sha256"], sha);
    let db = dir.path().join("workspace.sqlite");
    drop(conn);
    std::fs::remove_dir_all(&root).unwrap();
    let (mut conn, _) = bootstrap(db.to_str().unwrap()).unwrap();
    attempts::finish_with_artifacts(&mut conn, &req, &response, &payloads, &root).unwrap();
    let snapshot = dir.path().join("snapshot.sqlite");
    backup::backup(&conn, snapshot.to_str().unwrap()).unwrap();
    let (mut restored, _) =
        bootstrap(dir.path().join("restored.sqlite").to_str().unwrap()).unwrap();
    backup::restore(snapshot.to_str().unwrap(), &mut restored).unwrap();
    assert_eq!(raw_objects::read(&restored, &sha).unwrap(), frame);
    let restored_loss: String = restored
        .query_row(
            "SELECT loss_receipt FROM jobs WHERE job_id='video-job'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(serde_json::from_str::<Value>(&restored_loss).unwrap(), loss);
}
#[test]
fn false_hash_and_outside_path_add_zero_sources() {
    for outside in [false, true] {
        let (dir, mut conn, req, root, image) = setup();
        let path = if outside {
            let p = dir.path().join("outside.jpg");
            std::fs::write(&p, b"outside").unwrap();
            p
        } else {
            image
        };
        let sha = if outside {
            digest(b"outside")
        } else {
            "0".repeat(64)
        };
        let (response, bytes) = receipt(&req, &path, &sha);
        assert!(
            attempts::finish_with_artifacts(&mut conn, &req, &response, &bytes, &root).is_err()
        );
        let count: i64 = conn
            .query_row("SELECT count(*) FROM sources", [], |r| r.get(0))
            .unwrap();
        assert_eq!(count, 1);
        let outputs: i64 = conn
            .query_row("SELECT count(*) FROM job_outputs", [], |r| r.get(0))
            .unwrap();
        assert_eq!(outputs, 0);
    }
}
#[test]
fn failed_completion_rolls_back_custody_source_refs() {
    let (_dir, mut conn, req, root, image) = setup();
    conn.execute_batch("CREATE TRIGGER fail_output BEFORE INSERT ON job_outputs BEGIN SELECT RAISE(ABORT,'controlled output failure'); END;").unwrap();
    let (response, bytes) = receipt(&req, &image, &digest(b"actual controlled decoded bytes"));
    assert!(attempts::finish_with_artifacts(&mut conn, &req, &response, &bytes, &root).is_err());
    let count: i64 = conn
        .query_row("SELECT count(*) FROM sources", [], |r| r.get(0))
        .unwrap();
    assert_eq!(count, 1);
    let state: String = conn
        .query_row("SELECT state FROM jobs", [], |r| r.get(0))
        .unwrap();
    assert_eq!(state, "running");
}

#[test]
fn linked_artifact_is_refused_without_source_registration() {
    let (_dir, mut conn, req, root, image) = setup();
    std::fs::hard_link(&image, root.join("alias.jpg")).unwrap();
    let (response, bytes) = receipt(&req, &image, &digest(b"actual controlled decoded bytes"));
    assert!(attempts::finish_with_artifacts(&mut conn, &req, &response, &bytes, &root).is_err());
    let count: i64 = conn
        .query_row("SELECT count(*) FROM sources", [], |r| r.get(0))
        .unwrap();
    assert_eq!(count, 1);
}
