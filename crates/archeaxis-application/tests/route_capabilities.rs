//! R08 step (d) part 1: a job's kind selects an extraction route, which fixes the
//! capability the worker must advertise and the media type of the input asset, so
//! PDF and image jobs are first-class instead of being refused by a text-only
//! allow-list.

use archeaxis_application::{attempts, jobs};
use archeaxis_domain::source::{self, ImportOutcome};
use archeaxis_store_sqlite::init_workspace;

fn seed(kind: &str, payload: &[u8], name: &str) -> (tempfile::TempDir, rusqlite::Connection) {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("db.sqlite").to_str().unwrap()).unwrap();
    let source_id = match source::import_source(&mut conn, payload, name, None).unwrap() {
        ImportOutcome::Imported { source_id, .. } => source_id,
        ImportOutcome::Duplicate { source_id, .. } => source_id,
    };
    jobs::enqueue(&mut conn, "job", kind, &source_id).unwrap();
    (dir, conn)
}

#[test]
fn every_declared_route_selects_its_capability_and_media_type() {
    let cases = [
        ("text", "text.extract", "text/plain"),
        ("pdf", "pdf.extract", "application/pdf"),
        ("image", "image.ocr", "image/png"),
    ];
    for (kind, capability, media) in cases {
        let (_dir, mut conn) = seed(kind, b"%PDF-1.4 payload", "input.bin");
        let request = attempts::claim(&mut conn, "job", "req-1", 5000).unwrap();
        assert_eq!(request.capability, capability, "kind {kind}");
        assert_eq!(request.capability_version, "1");
        assert_eq!(request.inputs[0].media_type, media, "kind {kind}");
        assert_eq!(request.inputs[0].uri, format!("job://input/{}", request.inputs[0].sha256));
    }
    // The legacy alias keeps working: text.extract is still a text job.
    let aliased = attempts::route_for_kind("text.extract").unwrap();
    assert_eq!(aliased, ("text.extract", "text/plain"));
}

#[test]
fn an_unknown_job_kind_is_refused_at_claim_time() {
    let (_dir, mut conn) = seed("video", b"not a supported route", "clip.mp4");
    assert!(
        attempts::claim(&mut conn, "job", "req-2", 5000).is_err(),
        "an undeclared route must not be claimed as if it were text"
    );
    // The job stays queued: refusing a claim must not have moved it to running.
    let state: String = conn
        .query_row("SELECT state FROM jobs WHERE job_id='job'", [], |r| r.get(0))
        .unwrap();
    assert_eq!(state, "queued");
}

#[test]
fn route_lookup_is_explicit_about_unknown_kinds() {
    assert!(attempts::route_for_kind("text").is_some());
    assert!(attempts::route_for_kind("pdf").is_some());
    assert!(attempts::route_for_kind("image").is_some());
    assert!(attempts::route_for_kind("video").is_none());
    assert!(attempts::route_for_kind("").is_none());
}
