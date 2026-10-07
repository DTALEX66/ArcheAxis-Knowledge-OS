//! Durable attempt identities and full text outputs, owned by the Core writer.
//! Process IO and file reading belong outside this transaction boundary.
use crate::jobs::{self, JobError, LossReceipt};
use archeaxis_sidecar_protocol::worker::{Request, Response, decode_response};
use archeaxis_store_sqlite::capability_settings;
use rusqlite::{Connection, OptionalExtension, TransactionBehavior};
use serde::Deserialize;
use serde_json::Value;
use sha2::{Digest, Sha256};

/// R08: engine identities a successful receipt may report, one per extraction
/// route. The worker must name the engine it actually used; the Core no longer
/// requires the text engine from every route.
pub const ENGINE_PROFILES: &[(&str, &str)] = &[
    ("python-worker-text", "0.1.0"),
    ("pymupdf-native-pdf", "pymupdf"),
    ("python-worker-ocr", "0.1.0"),
    ("python-worker-archive", "0.1.0"),
    ("python-worker-media", "0.1.0"),
    ("python-worker-office", "0.1.0"),
    ("python-worker-canvas", "0.1.0"),
    ("python-worker-subtitles", "0.1.0"),
    ("python-worker-html", "0.1.0"),
    ("python-worker-caption", "0.1.0"),
    // The ASR engine. It was real and verified - 3,362 characters from a real Chinese
    // recording - but no route named it, so no job could reach it. A receipt may not report
    // this engine until the route below exists.
    ("python-worker-transcribe", "0.1.0"),
    ("python-worker-video", "0.1.0"),
];

/// R08: the extraction routes the Core can dispatch, declared once. A job's kind
/// selects the route, which fixes both the capability the worker must advertise
/// and the media type of the input asset - so a PDF or image job is a first-class
/// job instead of being refused by a text-only allow-list.
pub const ROUTES: &[(&str, &str, &str)] = &[
    ("text", "text.extract", "text/plain"),
    ("text.extract", "text.extract", "text/plain"),
    ("pdf", "pdf.extract", "application/pdf"),
    ("image", "image.ocr", "image/png"),
    // R15/F15: a container is binary, so it gets its own route instead of being
    // decoded as text. The projection is an inventory listing, never the members.
    ("archive", "archive.inventory", "application/zip"),
    // R15/F10-F11: audio and video are binary too. The probe reads the container's own
    // header structure and never decodes a sample, so the projection is a fact listing.
    ("media", "media.probe", "video/mp4"),
    // R15/F07-F09: an Office document is a ZIP of XML parts. The structure route reads
    // the parts and reports what the package declares, without rendering anything.
    (
        "office",
        "office.structure",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
    // R15/F12: a canvas and a subtitle file each have their own worker that produces
    // real structure (node anchors with ids; cue anchors with timings). Their media
    // types are their own, so a .srt is no longer read as plain text by the text route.
    ("canvas", "canvas.structure", "application/json"),
    ("subtitles", "subtitles.structure", "application/x-subrip"),
    // R15/F02-F03: a saved HTML snapshot is read by its own worker, which reports the
    // title, the body blocks and the links. Fetching a URL is not part of this route:
    // the snapshot is the input, so no network client exists here.
    ("html", "html.structure", "text/html"),
    // R15/F04: a figure description is a model call, so it is its own route with its own
    // engine profile. What it produces is a candidate description, never extracted text,
    // and a missing model is a named failure rather than an empty success.
    ("caption", "image.caption", "image/png"),
    // The pack requires real audio before final closure. A recording is binary and its
    // projection is a transcript with time-coded cues, so it gets its own kind, capability
    // and worker rather than being probed as a container.
    ("transcribe", "media.transcribe", "audio/wav"),
    ("video", "media.video", "video/mp4"),
];

/// Resolve a job kind to its route: (capability, input media type).
pub fn route_for_kind(kind: &str) -> Option<(&'static str, &'static str)> {
    ROUTES
        .iter()
        .find(|(name, _, _)| *name == kind)
        .map(|(_, capability, media)| (*capability, *media))
}

/// R15/F04: the media types each route's worker actually accepts, mirroring the
/// transport's own route table (`services/python-workers/transport/text_ndjson.py`).
/// The Core used to pin one media type per job kind, which meant a JPEG was
/// announced to the OCR worker as `image/png`; a job's media type is now derived
/// from the source name and must be one of these.
pub const ROUTE_MEDIA_TYPES: &[(&str, &[&str])] = &[
    (
        "text.extract",
        &[
            "text/plain",
            "text/markdown",
            "text/x-python",
            "text/csv",
            "text/tab-separated-values",
            "application/json",
            "application/x-ndjson",
            "application/yaml",
            "text/x-yaml",
            "application/toml",
            "application/epub+zip",
            "message/rfc822",
            // R15/F13: the light-format reader handles these containers itself, so the route
            // that owns it accepts them rather than leaving them unnamed and refused.
            "application/vnd.oasis.opendocument.text",
            "application/vnd.oasis.opendocument.spreadsheet",
            "application/vnd.oasis.opendocument.presentation",
            "application/rtf",
            "application/xml",
            "text/xml",
        ],
    ),
    ("pdf.extract", &["application/pdf"]),
    (
        "image.ocr",
        &[
            "image/png",
            "image/jpeg",
            "image/tiff",
            "image/webp",
            "image/bmp",
        ],
    ),
    (
        "archive.inventory",
        &["application/zip", "application/x-tar"],
    ),
    (
        "media.probe",
        &["video/mp4", "video/quicktime", "audio/wav"],
    ),
    (
        "media.video",
        &[
            "video/mp4",
            "video/quicktime",
            "video/x-matroska",
            "video/webm",
        ],
    ),
    (
        "media.transcribe",
        &[
            "audio/mpeg",
            "audio/mp4",
            "audio/x-m4a",
            "audio/flac",
            "audio/ogg",
            "audio/opus",
            "audio/wav",
            "audio/x-wav",
        ],
    ),
    (
        "office.structure",
        &[
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "application/msword",
            "application/vnd.ms-powerpoint",
        ],
    ),
    ("canvas.structure", &["application/json"]),
    ("subtitles.structure", &["application/x-subrip", "text/vtt"]),
    ("html.structure", &["text/html", "application/xhtml+xml"]),
    (
        "image.caption",
        &[
            "image/png",
            "image/jpeg",
            "image/tiff",
            "image/webp",
            "image/bmp",
        ],
    ),
];

/// The media types a capability's worker accepts (empty when the capability is unknown).
pub fn accepted_media_types(capability: &str) -> &'static [&'static str] {
    ROUTE_MEDIA_TYPES
        .iter()
        .find(|(name, _)| *name == capability)
        .map(|(_, types)| *types)
        .unwrap_or(&[])
}

/// R15/F06+F15: the capabilities whose worker may write durable transfer files (the PDF
/// route renders text-less pages for the OCR route; the archive route extracts the
/// members the Core may import). The executor tells only these workers where the
/// artifact root is, so every other route keeps its launch shape and an unexpected flag
/// stays an error rather than being silently accepted.
///
/// R15/F13 adds `text.extract` for one reason: a mail carries attachments, and the route
/// table inside the transport decides that only `message/rfc822` may write into the area.
/// Every other text media type is handed no directory and declares no member.
pub const ARTIFACT_ROOT_CAPABILITIES: &[&str] = &[
    "pdf.extract",
    "archive.inventory",
    "media.video",
    "text.extract",
    "office.structure",
];

/// R15/F06: routes whose successful job is followed by Core-side work, done inside the
/// same commit as the completion so there is no window in which the job says it
/// succeeded while the pages it declared were never queued.
pub const CHAINED_AFTER_SUCCESS: &[&str] = &["pdf.extract"];

/// The media type a file name denotes, or `None` when the extension is not one we
/// are willing to name. Guessing here is what the old pinned value effectively did.
pub fn media_type_for_name(name: &str) -> Option<&'static str> {
    let file = name
        .rsplit(['/', '\\'])
        .next()
        .unwrap_or(name)
        .to_ascii_lowercase();
    let extension = file.rsplit_once('.')?.1;
    Some(match extension {
        "txt" | "log" | "text" | "rs" | "ts" | "tsx" | "js" | "jsx" | "c" | "h" | "cpp" | "hpp"
        | "go" | "java" | "cs" | "rb" | "sh" | "ps1" | "bat" | "ini" | "cfg" | "sql" => {
            "text/plain"
        }
        "md" | "markdown" => "text/markdown",
        // R15/F01: only a source language with a reader here gets its own type. `.py` is read
        // with the interpreter's own `ast`, so a symbol report is possible; the rest stay
        // text/plain rather than being named for a parser that does not exist.
        "py" => "text/x-python",
        "csv" => "text/csv",
        "tsv" => "text/tab-separated-values",
        "json" | "canvas" => "application/json",
        "jsonl" | "ndjson" => "application/x-ndjson",
        "yaml" | "yml" => "application/yaml",
        "toml" => "application/toml",
        "epub" => "application/epub+zip",
        // R15/F13: ODF carries its body in content.xml and RTF in its own control words, and a
        // reader for each exists here, so naming them lets the file reach that reader instead of
        // being refused as an unknown suffix. The legacy binary Microsoft containers stay
        // unnamed for the same reason they were left out of the Office group.
        "odt" => "application/vnd.oasis.opendocument.text",
        "ods" => "application/vnd.oasis.opendocument.spreadsheet",
        "odp" => "application/vnd.oasis.opendocument.presentation",
        "rtf" => "application/rtf",
        "xml" => "application/xml",
        // R15/F15: a container gets the archive route, not a text decode
        "zip" => "application/zip",
        "tar" => "application/x-tar",
        // Name the actual container type; each capability separately limits what it reads.
        // The video decoder accepts MKV/WebM; the limited header probe does not.
        //
        // The audio containers below WERE deliberately unnamed, on the grounds that no
        // reader here could read them. That stopped being true when the ASR route was
        // declared: `media.transcribe` has a reader for exactly these, so naming them lets
        // a real recording reach it instead of being custody-only. They stay out of
        // `media.probe`'s accepted types, so the probe still refuses a format it cannot
        // read rather than reporting a header it does not understand.
        "wav" => "audio/wav",
        "mp3" => "audio/mpeg",
        "m4a" => "audio/mp4",
        "flac" => "audio/flac",
        "ogg" | "oga" => "audio/ogg",
        "opus" => "audio/opus",
        "mp4" | "m4v" => "video/mp4",
        "mov" => "video/quicktime",
        "mkv" => "video/x-matroska",
        "webm" => "video/webm",
        // R15/F07-F09: the OOXML families this repository can read. `.xls` joins them because
        // a reader for it now exists (the declared xlrd engine); `.doc` and `.ppt` join it because
        // external sidecars are now probed for them - and a document whose sidecar is absent fails
        // with the engine's own named reason, which is a reported state, not a silent one.
        // `.ppt` is named now: a JVM and Apache Tika are declared external sidecars, so the
        // legacy binary presentation has a reader instead of staying custody-only by default.
        // The route is the declaration; the engine is still probed and never assumed.
        "docx" => "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx" => "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "xlsx" => "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls" => "application/vnd.ms-excel",
        "doc" => "application/msword",
        "ppt" => "application/vnd.ms-powerpoint",
        // subtitles have their own media types, so a .srt is no longer declared as
        // plain text and cannot reach the text route by accident
        "srt" => "application/x-subrip",
        "vtt" => "text/vtt",
        // R15/F02: a saved page is HTML; the route reads the snapshot, it never fetches
        "html" | "htm" => "text/html",
        "xhtml" => "application/xhtml+xml",
        // a saved mail message is text (RFC 822) with its own structure, which the
        // worker reports as facts. A binary .msg container is deliberately NOT named:
        // no route can read it, so it is refused instead of decoded into noise.
        "eml" => "message/rfc822",
        "pdf" => "application/pdf",
        "png" => "image/png",
        "jpg" | "jpeg" | "jpe" => "image/jpeg",
        "tif" | "tiff" => "image/tiff",
        "webp" => "image/webp",
        "bmp" => "image/bmp",
        _ => return None,
    })
}

/// The media type to announce for one claimed job: derived from the source name and
/// required to be accepted by the route's worker.
pub fn resolve_media_type(kind: &str, original_name: &str) -> Result<&'static str, JobError> {
    let (capability, _default) =
        route_for_kind(kind).ok_or(JobError::InvalidReceipt("undeclared job kind"))?;
    let accepted = accepted_media_types(capability);
    let derived = media_type_for_name(original_name);
    match derived {
        Some(media) if accepted.contains(&media) => Ok(media),
        _ => Err(JobError::MediaTypeNotAccepted {
            kind: kind.to_string(),
            name: original_name.to_string(),
            derived,
            accepted,
        }),
    }
}

/// A split transcription request: the Core-owned root under which windows are kept.
///
/// Splitting is the only extra input a job may carry, and only `media.transcribe` may carry it.
#[derive(Debug, Clone)]
pub struct Split {
    pub root: std::path::PathBuf,
}

impl Split {
    /// Where one recording's finished windows are kept.
    ///
    /// Keyed by the input's own digest rather than by the job, because a recording too long for one
    /// job is expected to take several: each of them is a separate job, and they must all see the
    /// windows the earlier ones finished. Keying by job would restart the work every round.
    pub fn windows_of(root: &std::path::Path, digest: &str) -> std::path::PathBuf {
        root.join("windows").join(digest)
    }
}

pub fn claim(
    conn: &mut Connection,
    job_id: &str,
    request_id: &str,
    deadline_ms: u64,
) -> Result<Request, JobError> {
    claim_split(conn, job_id, request_id, deadline_ms, None, false)
}

/// `claim`, with the split choice the job carries persisted in the same transaction.
///
/// The choice travels inside the stored `request_json`, so replay and idempotency compare against
/// what the worker actually received rather than a shape the caller remembers.
pub fn claim_split(
    conn: &mut Connection,
    job_id: &str,
    request_id: &str,
    deadline_ms: u64,
    split: Option<Split>,
    words: bool,
) -> Result<Request, JobError> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let row:Option<(String,String,String,String)>=tx.query_row(
        "SELECT j.state,j.kind,s.sha256,COALESCE(s.original_name,'') FROM jobs j JOIN sources s ON s.source_id=j.input_ref WHERE j.job_id=?1",
        [job_id],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?))).optional()?;
    let (state, kind, sha, name) = row.ok_or(JobError::NotFound)?;
    if !matches!(state.as_str(), "queued" | "failed" | "cancelled") {
        return Err(JobError::InvalidState);
    }
    let capability = match route_for_kind(&kind) {
        Some((capability, _)) => capability,
        None => return Err(JobError::InvalidReceipt("undeclared job kind")),
    };
    // R7/G1: a capability this workspace turned off is refused here, inside the claim transaction,
    // so a disabled capability leaves no attempt row, no staging copy and no partial output behind.
    // Checking after the worker started would make "disabled" mean "ran and was then discarded".
    if !capability_settings::is_enabled(&tx, capability)? {
        return Err(JobError::CapabilityDisabled {
            capability: capability.to_string(),
            job: job_id.to_string(),
        });
    }
    // the media type comes from what the file is, not from a value pinned to the kind
    let media_type = resolve_media_type(&kind, &name)?;
    let next: i64 = tx.query_row(
        "SELECT COALESCE(MAX(attempt),0)+1 FROM job_attempts WHERE job_id=?1",
        [job_id],
        |r| r.get(0),
    )?;
    let request = Request::job(
        request_id,
        job_id,
        next as u64,
        capability,
        &sha,
        media_type,
        deadline_ms,
    )
    .map_err(JobError::InvalidReceipt)?;
    let request = match split {
        Some(split) => request
            .splitting(&Split::windows_of(&split.root, &sha).to_string_lossy())
            .map_err(JobError::InvalidReceipt)?,
        None => request,
    };
    let request = if words {
        request.word_timings().map_err(JobError::InvalidReceipt)?
    } else {
        request
    };
    tx.execute("INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES(?1,?2,?3,?4,'running')",
        rusqlite::params![job_id,next,request_id,serde_json::to_string(&request).map_err(|_|JobError::Conflict)?])?;
    tx.execute(
        "UPDATE jobs SET state='running',completed_at=NULL WHERE job_id=?1",
        [job_id],
    )?;
    tx.commit()?;
    Ok(request)
}

/// R08: compare anchors by kind and character span, tolerating extra leading path
/// components. A page-qualified anchor `["page-3","line-12"]` addresses the same
/// projected line as the canonical `["line-12"]`, so the Core checks that the
/// spans and the final path segment match - not that every route spells its path
/// exactly like the text route.
fn same_spans(found: &[Line], expected: &[Line]) -> bool {
    found.len() == expected.len()
        && found.iter().zip(expected).all(|(a, b)| {
            a.kind == b.kind
                && a.char_start == b.char_start
                && a.char_end == b.char_end
                && a.path.last() == b.path.last()
        })
}

fn identity(conn: &Connection, req: &Request) -> Result<(String, Option<String>), JobError> {
    let attempt = i64::try_from(req.attempt).map_err(|_| JobError::Conflict)?;
    let row:Option<(String,Option<String>,String,i64)>=conn.query_row(
        "SELECT state,result_digest,request_json,(SELECT MAX(attempt) FROM job_attempts WHERE job_id=?1) FROM job_attempts WHERE job_id=?1 AND attempt=?2",
        rusqlite::params![req.job_id,attempt],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?))).optional()?;
    let (state, digest, stored, latest) = row.ok_or(JobError::NotFound)?;
    if latest as u64 != req.attempt
        || stored != serde_json::to_string(req).map_err(|_| JobError::Conflict)?
    {
        return Err(JobError::Conflict);
    }
    Ok((state, digest))
}

#[derive(Deserialize, PartialEq, Debug)]
#[serde(deny_unknown_fields)]
struct Line {
    kind: String,
    path: Vec<String>,
    char_start: usize,
    char_end: usize,
}

fn expected_lines(text: &str) -> (Vec<Line>, usize) {
    // Python str.splitlines(keepends=True), in Unicode scalar offsets.
    let mut chars = text.chars().peekable();
    let mut lines = Vec::new();
    let mut start = 0;
    let mut i = 0;
    let mut total = 0;
    while let Some(ch) = chars.next() {
        let separator = matches!(
            ch,
            '\n' | '\r'
                | '\u{b}'
                | '\u{c}'
                | '\u{1c}'
                | '\u{1d}'
                | '\u{1e}'
                | '\u{85}'
                | '\u{2028}'
                | '\u{2029}'
        );
        if ch == '\r' && chars.peek() == Some(&'\n') {
            chars.next();
            i += 1;
        }
        i += 1;
        if separator || chars.peek().is_none() {
            total += 1;
            if lines.len() < 5000 {
                lines.push(Line {
                    kind: "line".into(),
                    path: vec![format!("line-{total}")],
                    char_start: start,
                    char_end: i,
                });
            }
            start = i;
        }
    }
    (lines, total)
}

/// Validate metadata AND bytes before any authoritative write. Contents remain
/// byte-faithful UTF-8 in this text profile; binary workers need a separate profile.
pub fn finish(
    conn: &mut Connection,
    req: &Request,
    response: &Response,
    payloads: &[Vec<u8>],
) -> Result<(), JobError> {
    finish_inner(conn, req, response, payloads, None)
}

pub fn finish_with_artifacts(
    conn: &mut Connection,
    req: &Request,
    response: &Response,
    payloads: &[Vec<u8>],
    artifact_root: &std::path::Path,
) -> Result<(), JobError> {
    finish_inner(conn, req, response, payloads, Some(artifact_root))
}

fn finish_inner(
    conn: &mut Connection,
    req: &Request,
    response: &Response,
    payloads: &[Vec<u8>],
    artifact_root: Option<&std::path::Path>,
) -> Result<(), JobError> {
    let wire = serde_json::to_string(response).map_err(|_| JobError::Conflict)?;
    let response = decode_response(&wire, req).map_err(JobError::InvalidReceipt)?;
    if response.status != "succeeded" || payloads.len() != 3 {
        return Err(JobError::InvalidState);
    }
    let mut text = None;
    let mut structure = None;
    let mut loss = None;
    let mut strings = Vec::new();
    for (output, bytes) in response.outputs.iter().zip(payloads) {
        if bytes.len() > 16 * 1024 * 1024
            || output.byte_length != bytes.len() as u64
            || hex::encode(Sha256::digest(bytes)) != output.sha256
        {
            return Err(JobError::InvalidReceipt("output hash or size mismatch"));
        }
        let content = std::str::from_utf8(bytes)
            .map_err(|_| JobError::InvalidReceipt("text profile output is not UTF-8"))?;
        match output.kind.as_str() {
            "text" => text = Some(content),
            "document_structure" => {
                structure = Some(
                    serde_json::from_str::<Vec<Line>>(content)
                        .map_err(|_| JobError::InvalidReceipt("invalid line structure"))?,
                )
            }
            "loss_report" => {
                loss = Some(
                    serde_json::from_str::<LossReceipt>(content)
                        .map_err(|_| JobError::InvalidReceipt("invalid loss receipt"))?,
                )
            }
            _ => return Err(JobError::InvalidReceipt("unsupported output")),
        }
        strings.push(content);
    }
    let text = text.ok_or(JobError::InvalidReceipt("missing text"))?;
    let (expected, total) = expected_lines(text);
    let structure = structure.ok_or(JobError::InvalidReceipt("missing structure"))?;
    let loss = loss.ok_or(JobError::InvalidReceipt("missing loss receipt"))?;
    loss.validate().map_err(JobError::InvalidReceipt)?;
    if !ENGINE_PROFILES
        .iter()
        .any(|(name, version)| loss.engine == *name && loss.engine_version == *version)
        || !same_spans(&structure, &expected)
        || loss.covered != Some(structure.len() as u64)
        || loss.total != Some(total as u64)
    {
        return Err(JobError::InvalidReceipt(
            "structure or coverage does not match projected text",
        ));
    }
    let digest = hex::encode(Sha256::digest(wire.as_bytes()));
    if req.capability == "media.video" {
        let (state, old) = identity(conn, req)?;
        if state == "succeeded" {
            return if old.as_deref() == Some(&digest) {
                Ok(())
            } else {
                Err(JobError::Conflict)
            };
        }
        if state != "running" {
            return Err(JobError::InvalidState);
        }
    }
    let artifacts = if req.capability == "media.video" {
        Some(crate::media_artifacts::prepare(
            artifact_root.ok_or(JobError::InvalidReceipt("video artifact root missing"))?,
            req,
            &loss,
        )?)
    } else {
        None
    };
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let (state, old) = identity(&tx, req)?;
    if state == "succeeded" {
        return if old.as_deref() == Some(&digest) {
            Ok(())
        } else {
            Err(JobError::Conflict)
        };
    }
    if state != "running" {
        return Err(JobError::InvalidState);
    }
    let mut core_loss = loss.clone();
    if let Some(artifacts) = artifacts {
        let adoption = crate::media_artifacts::adopt_tx(&tx, req, &artifacts)?;
        core_loss
            .params
            .as_object_mut()
            .ok_or(JobError::InvalidReceipt("loss params must be object"))?
            .insert("core_artifact_adoption".into(), adoption);
    }
    jobs::complete_tx(&tx, &req.job_id, &loss.engine, text, Some(&core_loss))?;
    if req.capability == "canvas.structure" {
        persist_canvas_projection(&tx, &req.job_id, &loss.params)?;
    }
    for (output, content) in response.outputs.iter().zip(strings) {
        tx.execute("INSERT INTO job_outputs(job_id,attempt,kind,metadata_json,content) VALUES(?1,?2,?3,?4,?5)",
            rusqlite::params![req.job_id,i64::try_from(req.attempt).map_err(|_|JobError::Conflict)?,output.kind,serde_json::to_string(output).map_err(|_|JobError::Conflict)?,content])?;
    }
    tx.execute("UPDATE job_attempts SET state='succeeded',response_json=?1,result_digest=?2,completed_at=datetime('now') WHERE job_id=?3 AND attempt=?4",
        rusqlite::params![wire,digest,req.job_id,i64::try_from(req.attempt).map_err(|_|JobError::Conflict)?])?;
    tx.commit()?;
    Ok(())
}

fn persist_canvas_projection(
    tx: &rusqlite::Transaction<'_>,
    canvas_id: &str,
    params: &Value,
) -> Result<(), JobError> {
    let output = params.get("worker_output").unwrap_or(params);
    let nodes = output
        .get("node_geometry")
        .and_then(Value::as_array)
        .ok_or(JobError::InvalidReceipt(
            "canvas worker output missing node_geometry",
        ))?;
    let edges = output
        .get("edges")
        .and_then(Value::as_array)
        .ok_or(JobError::InvalidReceipt(
            "canvas worker output missing edges",
        ))?;
    tx.execute(
        "DELETE FROM canvas_projection_edges WHERE canvas_id=?1",
        [canvas_id],
    )?;
    tx.execute(
        "DELETE FROM canvas_projection_nodes WHERE canvas_id=?1",
        [canvas_id],
    )?;
    tx.execute(
        "DELETE FROM canvas_projections WHERE canvas_id=?1",
        [canvas_id],
    )?;
    tx.execute(
        "INSERT INTO canvas_projections(canvas_id,source_job_id) VALUES(?1,?1)",
        [canvas_id],
    )?;
    for node in nodes {
        let node_id = node
            .get("node_id")
            .and_then(Value::as_str)
            .ok_or(JobError::InvalidReceipt("canvas node missing node_id"))?;
        let node_type = node.get("type").and_then(Value::as_str).unwrap_or("text");
        let geometry = node.get("geometry").and_then(Value::as_object);
        let number = |key: &str, default: f64| {
            geometry
                .and_then(|g| g.get(key))
                .and_then(Value::as_f64)
                .unwrap_or(default)
        };
        tx.execute(
            "INSERT INTO canvas_projection_nodes(canvas_id,node_id,node_type,x,y,width,height) VALUES(?1,?2,?3,?4,?5,?6,?7)",
            rusqlite::params![canvas_id,node_id,node_type,number("x",0.0),number("y",0.0),number("width",300.0),number("height",200.0)],
        )?;
    }
    for edge in edges {
        let edge_id = edge
            .get("id")
            .and_then(Value::as_str)
            .ok_or(JobError::InvalidReceipt("canvas edge missing id"))?;
        tx.execute(
            "INSERT INTO canvas_projection_edges(canvas_id,edge_id,from_node,to_node,label,color) VALUES(?1,?2,?3,?4,?5,?6)",
            rusqlite::params![canvas_id,edge_id,
                edge.get("fromNode").and_then(Value::as_str).unwrap_or(""),
                edge.get("toNode").and_then(Value::as_str).unwrap_or(""),
                edge.get("label").and_then(Value::as_str).unwrap_or(""),
                edge.get("color").and_then(Value::as_str).unwrap_or("#888")],
        )?;
    }
    Ok(())
}

pub fn terminate(
    conn: &mut Connection,
    req: &Request,
    status: &str,
    error: &str,
) -> Result<(), JobError> {
    if !matches!(status, "failed" | "rejected" | "cancelled") || error.trim().is_empty() {
        return Err(JobError::InvalidState);
    }
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let (state, _) = identity(&tx, req)?;
    if state == status {
        let old: Option<String> = tx.query_row(
            "SELECT error FROM job_attempts WHERE job_id=?1 AND attempt=?2",
            rusqlite::params![
                req.job_id,
                i64::try_from(req.attempt).map_err(|_| JobError::Conflict)?
            ],
            |r| r.get(0),
        )?;
        return if old.as_deref() == Some(error) {
            Ok(())
        } else {
            Err(JobError::Conflict)
        };
    }
    if state != "running" {
        return Err(JobError::InvalidState);
    }
    tx.execute("UPDATE job_attempts SET state=?1,error=?2,completed_at=datetime('now') WHERE job_id=?3 AND attempt=?4",
        rusqlite::params![status,error,req.job_id,i64::try_from(req.attempt).map_err(|_|JobError::Conflict)?])?;
    tx.execute(
        "UPDATE jobs SET state=?1,loss_receipt=?2,completed_at=datetime('now') WHERE job_id=?3",
        rusqlite::params![
            status,
            serde_json::json!({"error":error}).to_string(),
            req.job_id
        ],
    )?;
    tx.commit()?;
    Ok(())
}

/// Invoke only during exclusive Core startup, before accepting work. Never run
/// as periodic maintenance while an executor can still be using these attempts.
pub fn recover_interrupted(conn: &mut Connection) -> Result<usize, JobError> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    tx.execute("UPDATE jobs SET state='failed',loss_receipt='{\"error\":\"interrupted Core attempt\"}',completed_at=datetime('now') WHERE state='running' AND job_id IN (SELECT job_id FROM job_attempts WHERE state='running')",[])?;
    let count=tx.execute("UPDATE job_attempts SET state='failed',error='interrupted Core attempt',completed_at=datetime('now') WHERE state='running'",[])?;
    tx.commit()?;
    Ok(count)
}
