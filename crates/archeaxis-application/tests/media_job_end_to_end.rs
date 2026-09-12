//! R15/F10-F11: a media file reaches the store through its own route.
//!
//! Audio and video are binary, so the Core derives `audio/wav` or `video/mp4` from the
//! name, dispatches the media capability to its own worker, and the header fact listing
//! lands in the store with line anchors. The negative cases matter as much: a media
//! file offered to the text route is refused, a container the probe cannot read is
//! refused by name, and the projection must not contain decoded content.

use archeaxis_application::{
    attempts,
    executor::{Cancellation, Executor},
    jobs,
};
use archeaxis_domain::source::{self, ImportOutcome};
use std::path::PathBuf;

fn python() -> PathBuf {
    std::env::var_os("ARCHEAXIS_PYTHON").expect("run cargo via the project wrapper").into()
}

fn repo() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize().unwrap()
}

/// A real WAV header through the same interpreter the worker uses; the samples are
/// silent, because the probe never reads them.
fn wav_bytes() -> Vec<u8> {
    let script = "import io,sys,wave\n\
                  buf=io.BytesIO()\n\
                  with wave.open(buf,'wb') as h:\n\
                  \x20   h.setnchannels(2); h.setsampwidth(2); h.setframerate(8000)\n\
                  \x20   h.writeframes(b'\\x00\\x01'*2*4000)\n\
                  sys.stdout.buffer.write(buf.getvalue())\n";
    match std::process::Command::new(python()).arg("-c").arg(script).output() {
        Ok(out) if out.status.success() => out.stdout,
        _ => Vec::new(),
    }
}

async fn open_executor(dir: &std::path::Path) -> Executor {
    Executor::open_routes(
        &dir.join("db.sqlite"),
        &dir.join("staging"),
        &python(),
        &repo().join("services/python-workers/transport/text_ndjson.py"),
        &[("media.probe", repo().join("services/python-workers/document/worker_media.py"))],
    )
    .await
    .unwrap()
}

#[test]
fn media_names_select_the_media_route_and_never_the_text_route() {
    assert_eq!(attempts::resolve_media_type("media", "tone.wav").unwrap(), "audio/wav");
    assert_eq!(attempts::resolve_media_type("media", "clip.mp4").unwrap(), "video/mp4");
    assert_eq!(attempts::resolve_media_type("media", "movie.mov").unwrap(), "video/mp4");
    // a media file cannot travel as text: no route may decode a binary container
    for name in ["tone.wav", "clip.mp4"] {
        let error = attempts::resolve_media_type("text", name).unwrap_err().to_string();
        assert!(error.contains("cannot accept media type"), "{name}: {error}");
    }
    // formats no reader here can read are refused by name rather than probed with a guess
    for name in ["song.mp3", "audio.m4a", "lossless.flac", "movie.mkv", "clip.webm"] {
        let error = attempts::resolve_media_type("media", name).unwrap_err().to_string();
        assert!(error.contains("cannot name a media type"), "{name}: {error}");
    }
}

#[tokio::test]
async fn a_wav_job_is_dispatched_to_the_media_worker_and_its_facts_are_stored() {
    let wav = wav_bytes();
    if wav.is_empty() {
        eprintln!("skipping: the wave module is unavailable for building a sample");
        return;
    }
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let payload = wav.clone();
    executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &payload, "tone.wav", None).unwrap() {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-wav", "media", &source_id).unwrap();
        })
        .await
        .unwrap();

    executor.execute("job-wav", "run-wav", 120_000, &Cancellation::new()).await.unwrap();

    let (state, text, receipt) = executor
        .store()
        .submit(|conn| {
            let state = jobs::job_state(conn, "job-wav").unwrap().unwrap_or_default();
            let text: String = conn
                .query_row(
                    "SELECT text FROM transforms WHERE source_id=(
                       SELECT input_ref FROM jobs WHERE job_id='job-wav') ORDER BY transform_id DESC LIMIT 1",
                    [],
                    |row| row.get(0),
                )
                .unwrap_or_default();
            let receipt: String = conn
                .query_row(
                    "SELECT content FROM job_outputs WHERE job_id='job-wav' AND kind='loss_report'",
                    [],
                    |row| row.get(0),
                )
                .unwrap_or_default();
            (state, text, receipt)
        })
        .await
        .unwrap();

    assert_eq!(state, "succeeded");
    assert!(text.contains("container\twav"), "{text:?}");
    assert!(text.contains("sample_rate_hz\t8000"), "{text:?}");
    assert!(text.contains("channels\t2"), "{text:?}");
    // the projection is a header probe: no decoded content can be in it
    assert!(!text.contains("transcript"), "a probe must not claim a transcript: {text:?}");
    assert!(receipt.contains("python-worker-media"), "{receipt}");
    assert!(receipt.contains("not measurements of the media"), "{receipt}");
}

#[tokio::test]
async fn a_container_the_probe_cannot_read_fails_the_job_instead_of_succeeding_empty() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    executor
        .store()
        .submit(|conn| {
            let source_id =
                match source::import_source(conn, b"ID3\x04\x00\x00 not a wav and not an mp4", "song.wav", None).unwrap()
                {
                    ImportOutcome::Imported { source_id, .. } => source_id,
                    ImportOutcome::Duplicate { source_id, .. } => source_id,
                };
            jobs::enqueue(conn, "job-bad-wav", "media", &source_id).unwrap();
        })
        .await
        .unwrap();

    let outcome = executor.execute("job-bad-wav", "run-bad-wav", 60_000, &Cancellation::new()).await;
    let state = executor
        .store()
        .submit(|conn| jobs::job_state(conn, "job-bad-wav").unwrap().unwrap_or_default())
        .await
        .unwrap();
    assert!(outcome.is_err(), "an unreadable media container must not report success");
    assert_eq!(state, "failed");
    let text_outputs: i64 = executor
        .store()
        .submit(|conn| {
            conn.query_row(
                "SELECT count(*) FROM job_outputs WHERE job_id='job-bad-wav' AND kind='text'",
                [],
                |row| row.get(0),
            )
            .unwrap()
        })
        .await
        .unwrap();
    assert_eq!(text_outputs, 0, "no text artifact may exist for a media job that failed");
}
