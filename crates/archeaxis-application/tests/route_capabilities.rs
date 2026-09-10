//! R08 step (d) part 1: a job's kind selects an extraction route, which fixes the
//! capability the worker must advertise and the media type of the input asset, so
//! PDF and image jobs are first-class instead of being refused by a text-only
//! allow-list.
//!
//! R15/F04 adds the second half: the media type is **derived from the source name**
//! and must be one the route's worker accepts, so a JPEG is no longer announced to
//! the OCR worker as a PNG, and a mismatch is refused rather than mislabelled.

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
        ("text", "text.extract", "text/plain", "notes.txt"),
        ("text", "text.extract", "text/markdown", "notes.md"),
        ("text", "text.extract", "text/csv", "table.csv"),
        ("text", "text.extract", "application/json", "payload.json"),
        ("pdf", "pdf.extract", "application/pdf", "sample.pdf"),
        ("image", "image.ocr", "image/png", "shot.png"),
        ("image", "image.ocr", "image/jpeg", "shot.jpg"),
        ("image", "image.ocr", "image/tiff", "shot.tif"),
        ("image", "image.ocr", "image/webp", "shot.webp"),
        ("image", "image.ocr", "image/bmp", "shot.bmp"),
    ];
    for (kind, capability, media, name) in cases {
        let (_dir, mut conn) = seed(kind, b"%PDF-1.4 payload", name);
        let request = attempts::claim(&mut conn, "job", "req-1", 5000).unwrap();
        assert_eq!(request.capability, capability, "kind {kind} name {name}");
        assert_eq!(request.capability_version, "1");
        assert_eq!(request.inputs[0].media_type, media, "kind {kind} name {name}");
        assert_eq!(request.inputs[0].uri, format!("job://input/{}", request.inputs[0].sha256));
    }
    // The legacy alias keeps working: text.extract is still a text job.
    let aliased = attempts::route_for_kind("text.extract").unwrap();
    assert_eq!(aliased, ("text.extract", "text/plain"));
}

#[test]
fn the_media_type_comes_from_the_file_name_not_from_the_kind() {
    // the same image kind announces five different media types by name
    for (name, expected) in [
        ("scan.png", "image/png"),
        ("scan.JPG", "image/jpeg"),
        ("scan.jpeg", "image/jpeg"),
        ("a/b/scan.tiff", "image/tiff"),
        ("scan.webp", "image/webp"),
        ("scan.bmp", "image/bmp"),
    ] {
        assert_eq!(
            attempts::resolve_media_type("image", name).unwrap(),
            expected,
            "name {name}"
        );
    }
    // and the derivation is not fooled by a directory that looks like an extension
    assert_eq!(attempts::media_type_for_name("a.pdf/notes.txt"), Some("text/plain"));
    assert_eq!(attempts::media_type_for_name("REPORT.MD"), Some("text/markdown"));
    assert_eq!(attempts::media_type_for_name("archive.bin"), None);
}

#[test]
fn a_name_the_route_cannot_accept_is_refused_with_a_reason() {
    // a PDF payload named like an image must not be dispatched as a PDF job
    let (_dir, mut conn) = seed("pdf", b"%PDF-1.4 payload", "shot.png");
    let error = attempts::claim(&mut conn, "job", "req-3", 5000).unwrap_err();
    let text = error.to_string();
    assert!(text.contains("cannot accept media type image/png"), "{text}");
    assert!(text.contains("application/pdf"), "the accepted set must be named: {text}");
    let state: String = conn
        .query_row("SELECT state FROM jobs WHERE job_id='job'", [], |r| r.get(0))
        .unwrap();
    assert_eq!(state, "queued", "a refused claim must leave the job queued");

    // a text job whose file is an image is refused too
    let (_dir2, _conn2) = seed("text", b"pretend text", "shot.jpg");
    let error = attempts::resolve_media_type("text", "shot.jpg").unwrap_err();
    assert!(error.to_string().contains("image/jpeg"), "{error}");
}

#[test]
fn canvas_and_subtitle_names_resolve_to_the_routes_that_can_read_them() {
    // a .canvas is a JSON document, and the canvas route reads its node structure
    assert_eq!(attempts::resolve_media_type("canvas", "vault.canvas").unwrap(), "application/json");
    assert_eq!(attempts::resolve_media_type("text", "vault.canvas").unwrap(), "application/json");
    // R15/F12: subtitles now have their own media types and their own route, so a .srt
    // is no longer declared as plain text (the dedicated worker is the one answer)
    assert_eq!(attempts::resolve_media_type("subtitles", "talk.srt").unwrap(), "application/x-subrip");
    assert_eq!(attempts::resolve_media_type("subtitles", "talk.vtt").unwrap(), "text/vtt");
    assert!(attempts::resolve_media_type("text", "talk.srt").is_err());
    assert!(attempts::resolve_media_type("text", "talk.vtt").is_err());
    // a saved mail message is text with its own structure
    assert_eq!(attempts::resolve_media_type("text", "message.eml").unwrap(), "text/plain");
    // and they are refused by a route that cannot read them
    assert!(attempts::resolve_media_type("image", "vault.canvas").is_err());
    assert!(attempts::resolve_media_type("pdf", "talk.srt").is_err());
    assert!(attempts::resolve_media_type("image", "message.eml").is_err());
}

#[test]
fn a_binary_container_name_is_refused_because_no_route_can_read_it() {
    // .msg is a binary OLE container with no reader here, and .epub/.ods are binary
    // archives no engine in this repository opens: decoding them as text would produce
    // noise, so the Core refuses the name instead
    for name in ["mail.msg", "book.epub", "sheet.ods"] {
        let error = attempts::resolve_media_type("text", name).unwrap_err().to_string();
        assert!(error.contains("cannot name a media type"), "{name}: {error}");
        assert!(error.contains("text/plain"), "the accepted set must be listed: {name}: {error}");
    }
    // a .zip is still refused by the text route, but it now has a route of its own, so
    // the refusal is "wrong route" rather than "nothing can read this"
    let error = attempts::resolve_media_type("text", "bundle.zip").unwrap_err().to_string();
    assert!(error.contains("cannot accept media type application/zip"), "{error}");
    assert_eq!(attempts::resolve_media_type("archive", "bundle.zip").unwrap(), "application/zip");
}

#[test]
fn an_unnamed_extension_is_refused_rather_than_guessed() {
    let error = attempts::resolve_media_type("image", "clipboard").unwrap_err();
    let text = error.to_string();
    assert!(text.contains("cannot name a media type for clipboard"), "{text}");
    assert!(text.contains("image/jpeg"), "the accepted set must be listed: {text}");
    assert!(attempts::resolve_media_type("image", "scan.dat").is_err());
    // the declared sets are the transport's own, and every route has one
    assert_eq!(attempts::accepted_media_types("image.ocr").len(), 5);
    assert_eq!(attempts::accepted_media_types("pdf.extract"), ["application/pdf"]);
    assert_eq!(attempts::accepted_media_types("text.extract").len(), 7);
    assert!(attempts::accepted_media_types("nothing.extract").is_empty());
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
