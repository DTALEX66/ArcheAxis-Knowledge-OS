//! Native OCR line locators bind actual image.ocr structure and region receipt.
//! Canonical text line spans are not bounding boxes; pixel claims are refused.
use rusqlite::Connection;
use serde_json::Value;
use sha2::{Digest, Sha256};

fn verified_output(metadata: &str, content: &str, kind: &str) -> Option<bool> {
    let metadata: Value = serde_json::from_str(metadata).ok()?;
    Some(metadata["kind"] == kind
        && metadata["sha256"] == format!("{:x}", Sha256::digest(content.as_bytes()))
        && metadata["byte_length"].as_u64()? == content.len() as u64)
}

pub(super) fn verify(
    conn: &Connection,
    source: &str,
    revision: &str,
    position: &Value,
    checksum: &str,
) -> Option<bool> {
    let job = position["job_id"].as_str()?;
    let attempt = i64::try_from(position["attempt"].as_u64()?).ok()?;
    let expected = position["result_sha256"].as_str()?;
    let path = position["path"].as_array()?;
    if path.len() != 1 || position["kind"] != "line"
        || position.get("bbox").is_some() || position.get("region").is_some() {
        return Some(false);
    }
    for (segment, prefix) in path.iter().zip(["line-"]) {
        let number = segment.as_str()?.strip_prefix(prefix)?.parse::<u64>().ok()?;
        if number == 0 {
            return Some(false);
        }
    }
    let start = usize::try_from(position["char_start"].as_u64()?).ok()?;
    let end = usize::try_from(position["char_end"].as_u64()?).ok()?;
    if end <= start {
        return Some(false);
    }
    let (input, source_sha, kind, state, attempt_state, wire, latest, text_meta, text, structure_meta, structure, loss_meta, loss, request_id):
        (String, String, String, String, String, String, i64, String, String, String, String, String, String, String) = conn.query_row(
        "SELECT j.input_ref,s.sha256,j.kind,j.state,a.state,a.request_json,
                (SELECT MAX(attempt) FROM job_attempts WHERE job_id=j.job_id),
                t.metadata_json,t.content,d.metadata_json,d.content,l.metadata_json,l.content,a.request_id
         FROM jobs j JOIN sources s ON s.source_id=j.input_ref
         JOIN job_attempts a ON a.job_id=j.job_id
         JOIN job_outputs t ON t.job_id=a.job_id AND t.attempt=a.attempt AND t.kind='text'
         JOIN job_outputs d ON d.job_id=a.job_id AND d.attempt=a.attempt AND d.kind='document_structure'
         JOIN job_outputs l ON l.job_id=a.job_id AND l.attempt=a.attempt AND l.kind='loss_report'
         WHERE j.job_id=?1 AND a.attempt=?2",
        rusqlite::params![job, attempt],
        |r| Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?,r.get(4)?,r.get(5)?,
                r.get(6)?,r.get(7)?,r.get(8)?,r.get(9)?,r.get(10)?,r.get(11)?,r.get(12)?,r.get(13)?)),
    ).ok()?;
    if input != source || source_sha != revision || kind != "image"
        || state != "succeeded" || attempt_state != "succeeded" || latest != attempt {
        return Some(false);
    }
    let request: Value = serde_json::from_str(&wire).ok()?;
    let inputs = request["inputs"].as_array()?;
    if request["schema"] != "archeaxis.worker-request/v1" || request["type"] != "job_request"
        || request["request_id"] != request_id || request["job_id"] != job || request["attempt"] != attempt
        || request["capability"] != "image.ocr" || inputs.len() != 1
        || inputs[0]["sha256"] != revision || !matches!(inputs[0]["media_type"].as_str(), Some("image/png" | "image/jpeg" | "image/tiff" | "image/webp" | "image/bmp"))
        || verified_output(&text_meta, &text, "text") != Some(true)
        || verified_output(&structure_meta, &structure, "document_structure") != Some(true)
        || verified_output(&loss_meta, &loss, "loss_report") != Some(true)
        || position["loss_sha256"] != format!("{:x}", Sha256::digest(loss.as_bytes()))
        || expected != format!("{:x}", Sha256::digest(structure.as_bytes())) {
        return Some(false);
    }
    let receipt: Value = serde_json::from_str(&loss).ok()?;
    let params = &receipt["params"];
    let raw = archeaxis_store_sqlite::raw_objects::read(conn, revision).ok()?;
    if receipt["engine"] != "python-worker-ocr" || params["input_sha256"] != revision
        || params["input_bytes"].as_u64()? != raw.len() as u64
        || params["input_transport"] != "stdin" {
        return Some(false);
    }
    let regions = params["regions"].as_array()?;
    let chars: Vec<char> = text.chars().collect();
    let mut line_has_region = false;
    for region in regions {
        let first = usize::try_from(region["char_start"].as_u64()?).ok()?;
        let last = usize::try_from(region["char_end"].as_u64()?).ok()?;
        let word: String = chars.get(first..last)?.iter().collect();
        if first >= last || word != region["text"].as_str()?
            || region["bbox"]["w"].as_f64()? <= 0.0 || region["bbox"]["h"].as_f64()? <= 0.0
            || region["bbox"]["x"].as_f64()? < 0.0 || region["bbox"]["y"].as_f64()? < 0.0 {
            return Some(false);
        }
        line_has_region |= first >= start && last <= end;
    }
    if !line_has_region { return Some(false); }
    let entries: Value = serde_json::from_str(&structure).ok()?;
    let matches: Vec<&Value> = entries.as_array()?.iter().filter(|entry| {
        entry["kind"] == "line" && entry["path"] == position["path"]
    }).collect();
    if matches.len() != 1 || matches[0]["char_start"] != position["char_start"]
        || matches[0]["char_end"] != position["char_end"] {
        return Some(false);
    }
    let excerpt: String = text.chars().skip(start).take(end - start).collect();
    Some(excerpt.chars().count() == end - start && !excerpt.trim().is_empty()
        && format!("{:x}", Sha256::digest(excerpt.as_bytes())) == checksum)
}
