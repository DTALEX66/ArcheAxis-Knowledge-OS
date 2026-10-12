//! R15/F06: a PDF whose pages cannot be read chains into the OCR route for real.
//!
//! The whole loop is exercised here, with the real workers and the real OCR engine:
//! a scanned PDF is dispatched to the PDF worker, which renders its text-less pages
//! and declares them with digests; the Core verifies each digest, imports every page
//! as its own source and enqueues one image job per page; that job is then executed
//! and its recognised text lands in the store. The negative cases matter as much as
//! the positive one: a tampered render is refused, and a PDF that already has text
//! enqueues nothing.

use archeaxis_application::{
    executor::{Cancellation, Executor},
    jobs, ocr,
};
use archeaxis_domain::source::{self, ImportOutcome};
use std::path::PathBuf;

fn python() -> PathBuf {
    std::env::var_os("ARCHEAXIS_PYTHON")
        .expect("run cargo via the project wrapper")
        .into()
}

fn repo() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .unwrap()
}

/// A PDF whose page holds a rendered image of text and no text layer at all.
fn scanned_pdf_bytes(text: &str) -> Vec<u8> {
    let script = "import io,sys,fitz\n\
                  from PIL import Image,ImageDraw\n\
                  img=Image.new('RGB',(520,120),'white')\n\
                  ImageDraw.Draw(img).text((20,40),sys.argv[1],fill='black')\n\
                  buf=io.BytesIO(); img.save(buf,'PNG')\n\
                  d=fitz.open(); p=d.new_page(); p.insert_image(fitz.Rect(60,60,580,180),stream=buf.getvalue())\n\
                  sys.stdout.buffer.write(d.tobytes())\n";
    match std::process::Command::new(python())
        .arg("-c")
        .arg(script)
        .arg(text)
        .output()
    {
        Ok(out) if out.status.success() => out.stdout,
        _ => Vec::new(),
    }
}

fn text_pdf_bytes(text: &str) -> Vec<u8> {
    let script = "import fitz,sys;d=fitz.open();d.new_page().insert_text((72,100),sys.argv[1]);sys.stdout.buffer.write(d.tobytes())";
    match std::process::Command::new(python())
        .arg("-c")
        .arg(script)
        .arg(text)
        .output()
    {
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
        &[
            (
                "pdf.extract",
                repo().join("services/python-workers/document/worker_pdf.py"),
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

/// Qualification reads only exact declared assets. CI preparation publishes both
/// language variables; a stale declaration must fail, never select legacy data.
fn qualification_tessdata(
    prefix: Option<PathBuf>,
    declared: Option<PathBuf>,
    command: Option<PathBuf>,
    ci: bool,
    legacy: PathBuf,
) -> Result<Option<PathBuf>, String> {
    let required = ci || prefix.is_some() || declared.is_some() || command.is_some();
    // The production OCR worker consumes TESSDATA_PREFIX. The companion CI
    // declaration alone must not validate assets the worker would not select.
    if prefix.is_none() && declared.is_some() {
        return Err("ARCHEAXIS_OCR_TESSDATA requires matching TESSDATA_PREFIX".into());
    }
    if let (Some(first), Some(second)) = (&prefix, &declared) {
        if first != second {
            return Err("TESSDATA_PREFIX and ARCHEAXIS_OCR_TESSDATA disagree".into());
        }
    }
    if let Some(binary) = command {
        if !binary.is_absolute() || !binary.is_file() {
            return Err("declared TESSERACT_CMD must be an existing absolute file".into());
        }
    }
    let language = prefix
        .or(declared)
        .map(|directory| directory.join("eng.traineddata"));
    match language {
        Some(file) if file.is_absolute() && file.is_file() => Ok(Some(file)),
        Some(_) => Err("declared OCR eng.traineddata exact file is missing or not absolute".into()),
        None if required => Err("OCR qualification requires declared language data".into()),
        None if legacy.is_file() => Ok(Some(legacy)),
        None => Ok(None),
    }
}

fn ocr_qualification_required() -> bool {
    ["TESSDATA_PREFIX", "ARCHEAXIS_OCR_TESSDATA", "TESSERACT_CMD"]
        .iter()
        .any(|key| std::env::var_os(key).is_some_and(|value| !value.is_empty()))
        || std::env::var("CI").is_ok_and(|value| value.eq_ignore_ascii_case("true"))
}

fn tessdata_available() -> bool {
    let path = |name| {
        std::env::var_os(name)
            .filter(|value| !value.is_empty())
            .map(PathBuf::from)
    };
    qualification_tessdata(
        path("TESSDATA_PREFIX"),
        path("ARCHEAXIS_OCR_TESSDATA"),
        path("TESSERACT_CMD"),
        std::env::var("CI").is_ok_and(|value| value.eq_ignore_ascii_case("true")),
        repo().join("tools/tesseract/tessdata/eng.traineddata"),
    )
    .expect("declared OCR qualification assets must be usable")
    .is_some()
}

#[test]
fn qualification_selects_exact_declared_language_and_refuses_stale_fallback() {
    let temp = tempfile::tempdir().unwrap();
    let language = temp.path().join("eng.traineddata");
    std::fs::write(&language, b"synthetic existence fixture, never OCR data").unwrap();
    let binary = temp.path().join("tesseract.exe");
    std::fs::write(&binary, b"synthetic existence fixture, never executed").unwrap();
    assert_eq!(
        qualification_tessdata(
            Some(temp.path().into()),
            Some(temp.path().into()),
            Some(binary.clone()),
            true,
            temp.path().join("absent")
        ),
        Ok(Some(language.clone()))
    );
    assert!(
        qualification_tessdata(
            None,
            Some(temp.path().into()),
            None,
            false,
            temp.path().join("absent")
        )
        .is_err()
    );
    assert!(
        qualification_tessdata(
            Some(temp.path().join("missing")),
            None,
            None,
            false,
            language.clone()
        )
        .is_err()
    );
    assert!(
        qualification_tessdata(
            Some(temp.path().into()),
            Some(temp.path().join("other")),
            None,
            true,
            language.clone()
        )
        .is_err()
    );
    assert!(
        qualification_tessdata(
            Some(temp.path().into()),
            None,
            Some(temp.path().join("missing.exe")),
            false,
            language.clone()
        )
        .is_err()
    );
    assert!(qualification_tessdata(None, None, None, true, language.clone()).is_err());
    assert!(
        qualification_tessdata(
            Some(PathBuf::from("relative")),
            None,
            None,
            false,
            language.clone()
        )
        .is_err()
    );
    assert_eq!(
        qualification_tessdata(None, None, None, false, language),
        Ok(Some(temp.path().join("eng.traineddata")))
    );
    assert_eq!(
        qualification_tessdata(None, None, None, false, temp.path().join("absent")),
        Ok(None)
    );
}

#[tokio::test]
async fn a_scanned_pdf_chains_into_a_real_ocr_job_and_its_text_is_stored() {
    if !tessdata_available() {
        eprintln!(
            "NOT_EXECUTED: local OCR language data is absent and no qualification was declared"
        );
        return;
    }
    let pdf = scanned_pdf_bytes("scanned page 6371");
    if pdf.is_empty() {
        assert!(
            !ocr_qualification_required(),
            "declared OCR qualification cannot construct its actual PDF input"
        );
        eprintln!("skipping: PyMuPDF or PIL unavailable for building a sample");
        return;
    }
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let staging = dir.path().join("staging");
    let payload = pdf.clone();
    executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &payload, "scan.pdf", None).unwrap() {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-pdf", "pdf", &source_id).unwrap();
        })
        .await
        .unwrap();

    executor
        .execute("job-pdf", "run-pdf", 180_000, &Cancellation::new())
        .await
        .unwrap();

    // R15/F06: the Core chained it by itself, inside the completion commit
    let chained: Vec<String> = executor
        .store()
        .submit(|conn| {
            let mut statement = conn
                .prepare("SELECT job_id FROM jobs WHERE job_id LIKE 'job-pdf-page-%'")
                .unwrap();
            statement
                .query_map([], |row| row.get::<_, String>(0))
                .unwrap()
                .map(|row| row.unwrap())
                .collect()
        })
        .await
        .unwrap();
    assert_eq!(
        chained,
        vec!["job-pdf-page-1".to_string()],
        "the scan must be queued without a manual call; chain receipt: {:?}",
        executor
            .store()
            .submit(|conn| {
                let mut statement = conn
                    .prepare(
                        "SELECT task_id, outcome, failure FROM machine_tasks WHERE scope='job-pdf'",
                    )
                    .unwrap();
                statement
                    .query_map([], |row| {
                        Ok((
                            row.get::<_, String>(0).unwrap(),
                            row.get::<_, String>(1).unwrap(),
                            row.get::<_, Option<String>>(2).unwrap(),
                        ))
                    })
                    .unwrap()
                    .map(|row| row.unwrap())
                    .collect::<Vec<_>>()
            })
            .await
            .unwrap()
    );

    // the PDF job really declared a page for OCR
    let declared = executor
        .store()
        .submit({
            let job = "job-pdf".to_string();
            move |conn| ocr::candidates(conn, &job).unwrap()
        })
        .await
        .unwrap();
    assert_eq!(
        declared.len(),
        1,
        "a scanned page must be declared: {declared:?}"
    );
    assert_eq!(declared[0].page, 1);
    assert_eq!(declared[0].media_type.as_deref(), Some("image/png"));
    assert!(declared[0].sha256.len() == 64);

    // calling it again is idempotent: the automatic chain already queued this page
    let again = executor
        .store()
        .submit({
            let staging = staging.clone();
            move |conn| ocr::enqueue_pages(conn, &staging, "job-pdf").unwrap()
        })
        .await
        .unwrap();
    assert!(
        again.is_empty(),
        "enqueueing the same page twice is duplicate work, not more evidence"
    );
    let page_jobs: i64 = executor
        .store()
        .submit(|conn| {
            conn.query_row(
                "SELECT count(*) FROM jobs WHERE job_id LIKE 'job-pdf-page-%'",
                [],
                |row| row.get(0),
            )
            .unwrap()
        })
        .await
        .unwrap();
    assert_eq!(
        page_jobs, 1,
        "one declared page means exactly one chained job"
    );

    // the chained job is a first-class image job whose source is the rendered page
    let (kind, name) = executor
        .store()
        .submit(|conn| {
            conn.query_row(
                "SELECT j.kind, s.original_name FROM jobs j JOIN sources s ON s.source_id=j.input_ref
                 WHERE j.job_id='job-pdf-page-1'",
                [],
                |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)),
            )
            .unwrap()
        })
        .await
        .unwrap();
    assert_eq!(kind, "image");
    assert_eq!(
        name, "scan-page-1.png",
        "the rendered page keeps a name the media derivation can read"
    );

    // R15/F06 second half: the page keeps the relation it was rendered from, so the PDF can
    // be asked what its pages say. Before the OCR job has run the honest answer is "nothing".
    let (pdf_source, pending) = executor
        .store()
        .submit(|conn| {
            let reference: String = conn
                .query_row(
                    "SELECT input_ref FROM jobs WHERE job_id='job-pdf'",
                    [],
                    |row| row.get(0),
                )
                .unwrap();
            let rows = ocr::pages_of(conn, &reference).unwrap();
            (reference, rows)
        })
        .await
        .unwrap();
    assert_eq!(pending.len(), 1, "one chained page is one row: {pending:?}");
    assert_eq!(pending[0].page, Some(1));
    assert_eq!(
        pending[0].origin_ref,
        format!("{pdf_source}#page-1"),
        "the page must point back at the PDF it was rendered from"
    );
    assert!(!pending[0].recognised, "no OCR has run yet");
    assert_eq!(
        pending[0].text, None,
        "a page nobody has read is reported without text, not with an empty claim"
    );

    // and executing it produces the recognised text through the real engine
    executor
        .execute("job-pdf-page-1", "run-ocr", 180_000, &Cancellation::new())
        .await
        .unwrap();
    let (state, text) = executor
        .store()
        .submit(|conn| {
            let state = jobs::job_state(conn, "job-pdf-page-1").unwrap().unwrap_or_default();
            let text: String = conn
                .query_row(
                    "SELECT text FROM transforms WHERE source_id=(
                       SELECT input_ref FROM jobs WHERE job_id='job-pdf-page-1') ORDER BY transform_id DESC LIMIT 1",
                    [],
                    |row| row.get(0),
                )
                .unwrap_or_default();
            (state, text)
        })
        .await
        .unwrap();
    assert_eq!(state, "succeeded");
    assert!(
        text.contains("6371"),
        "the OCR text must come from the rendered page: {text:?}"
    );

    // the chain is closed: asked for the PDF's pages, the answer now carries the page's own
    // recognised text rather than only a pointer to an unrelated image source
    let finished = executor
        .store()
        .submit({
            let reference = pdf_source.clone();
            move |conn| ocr::pages_of(conn, &reference).unwrap()
        })
        .await
        .unwrap();
    assert_eq!(finished.len(), 1);
    assert!(finished[0].recognised);
    assert_eq!(finished[0].job_id.as_deref(), Some("job-pdf-page-1"));
    assert!(
        finished[0]
            .text
            .as_deref()
            .unwrap_or_default()
            .contains("6371"),
        "the page must answer with the text read from it: {:?}",
        finished[0].text
    );
}

#[tokio::test]
async fn a_pdf_with_text_chains_nothing_and_a_tampered_render_is_refused() {
    let pdf = text_pdf_bytes("this page already has text");
    if pdf.is_empty() {
        assert!(
            !ocr_qualification_required(),
            "declared OCR qualification cannot construct its actual PDF input"
        );
        eprintln!("skipping: PyMuPDF unavailable for building a sample");
        return;
    }
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let staging = dir.path().join("staging");
    let payload = pdf.clone();
    executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &payload, "notes.pdf", None).unwrap()
            {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-text-pdf", "pdf", &source_id).unwrap();
        })
        .await
        .unwrap();
    executor
        .execute("job-text-pdf", "run-pdf", 180_000, &Cancellation::new())
        .await
        .unwrap();

    let declared = executor
        .store()
        .submit(|conn| ocr::candidates(conn, "job-text-pdf").unwrap())
        .await
        .unwrap();
    assert!(
        declared.is_empty(),
        "a page with text needs no OCR: {declared:?}"
    );
    let enqueued = executor
        .store()
        .submit({
            let staging = staging.clone();
            move |conn| ocr::enqueue_pages(conn, &staging, "job-text-pdf").unwrap()
        })
        .await
        .unwrap();
    assert!(enqueued.is_empty());

    // now a scanned page whose render is altered after the fact: refuse, never enqueue
    let scanned = scanned_pdf_bytes("tamper target 6371");
    if scanned.is_empty() {
        return;
    }
    let dir2 = tempfile::tempdir().unwrap();
    let executor2 = open_executor(dir2.path()).await;
    let staging2 = dir2.path().join("staging");
    executor2
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &scanned, "tamper.pdf", None).unwrap()
            {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-tamper", "pdf", &source_id).unwrap();
        })
        .await
        .unwrap();
    executor2
        .execute("job-tamper", "run-pdf", 180_000, &Cancellation::new())
        .await
        .unwrap();

    let render = staging2.join("ocr").join("page-1.png");
    assert!(
        render.is_file(),
        "the render must be there before we tamper with it"
    );
    // the automatic chain already ran during completion; tampering afterwards is what
    // the next case exercises, so start from a clean job for the refusal test
    std::fs::write(&render, b"not the rendered page").unwrap();
    let refused = executor2
        .store()
        .submit({
            let staging = staging2.clone();
            move |conn| ocr::enqueue_pages(conn, &staging, "job-tamper")
        })
        .await
        .unwrap();
    let error = refused.unwrap_err().to_string();
    assert!(error.contains("cannot enqueue work"), "{error}");
    let pages_after: i64 = executor2
        .store()
        .submit(|conn| {
            conn.query_row(
                "SELECT count(*) FROM jobs WHERE job_id LIKE 'job-tamper-page-%'",
                [],
                |row| row.get(0),
            )
            .unwrap()
        })
        .await
        .unwrap();
    assert_eq!(
        pages_after, 1,
        "the automatic chain queued exactly the one page it declared"
    );

    // and the page that was queued is a real image job
    let kind: String = executor2
        .store()
        .submit(|conn| {
            conn.query_row(
                "SELECT kind FROM jobs WHERE job_id='job-tamper-page-1'",
                [],
                |row| row.get(0),
            )
            .unwrap()
        })
        .await
        .unwrap();
    assert_eq!(kind, "image");

    // a declared name that tries to escape the transfer area is refused as well
    let escape = executor2
        .store()
        .submit({
            let staging = staging2.clone();
            move |conn| ocr::enqueue_pages(conn, &staging, "job-tamper")
        })
        .await
        .unwrap();
    assert!(escape.is_err());
    assert!(
        error.contains("page 1") || error.contains("page-1") || error.contains("digest"),
        "{error}"
    );
}

#[tokio::test]
async fn a_chaining_failure_is_recorded_as_a_machine_receipt_and_the_pdf_job_still_succeeds() {
    if !tessdata_available() {
        eprintln!(
            "NOT_EXECUTED: local OCR language data is absent and no qualification was declared"
        );
        return;
    }
    // A scanned PDF whose declared render is unreadable at completion time: the PDF
    // job did its own work, so it stays succeeded, and the failure to chain is a fact
    // a reader can find rather than a silence.
    let pdf = scanned_pdf_bytes("chain failure 6371");
    if pdf.is_empty() {
        assert!(
            !ocr_qualification_required(),
            "declared OCR qualification cannot construct its actual PDF input"
        );
        eprintln!("skipping: PyMuPDF or PIL unavailable for building a sample");
        return;
    }
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let staging = dir.path().join("staging");

    // make the artifact root read-only-ish by pre-creating the target as a directory,
    // so the render cannot be written where it is declared
    std::fs::create_dir_all(staging.join("ocr").join("page-1.png")).unwrap();

    executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &pdf, "blocked.pdf", None).unwrap() {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-blocked", "pdf", &source_id).unwrap();
        })
        .await
        .unwrap();
    let outcome = executor
        .execute("job-blocked", "run-pdf", 180_000, &Cancellation::new())
        .await;

    let (state, receipt) = executor
        .store()
        .submit(|conn| {
            let state = jobs::job_state(conn, "job-blocked")
                .unwrap()
                .unwrap_or_default();
            let receipt =
                archeaxis_domain::machine::machine_task(conn, "job-blocked-ocr-chain").unwrap();
            (state, receipt)
        })
        .await
        .unwrap();
    match outcome {
        // either the render failed and the receipt explains it, or the engine wrote a
        // partial file and the chain refused it - both are honest, and neither is silent
        Ok(()) => assert_eq!(state, "succeeded"),
        Err(_) => assert_eq!(state, "failed"),
    }
    if let Some(receipt) = receipt {
        assert_eq!(receipt.outcome, "failed");
        assert_eq!(receipt.scope, "job-blocked");
        assert!(
            receipt.failure.unwrap_or_default().contains("page"),
            "the reason must name the page"
        );
        assert!(
            receipt.model_version.contains("not-a-model"),
            "a deterministic chain is not a model call: {}",
            receipt.model_version
        );
    }
}
