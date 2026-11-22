//! Read-only native SiYuan block projection over one completed batch manifest.
use crate::{AppState, format_qualification::usable_receipt, ingest_batches::response};
use archeaxis_domain::ingest_batches::{self as batches, Error};
use axum::{
    extract::{Path, State},
    response::Response,
};
use rusqlite::{Connection, OptionalExtension, params};
use serde_json::{Value, json};
use std::collections::BTreeMap;

pub(super) async fn read(
    State(state): State<AppState>,
    Path((batch, ordinal, block)): Path<(String, i64, String)>,
) -> Response {
    crate::with_store(state, move |conn| {
        response((|| {
            let tx = conn.transaction()?;
            let result = project(&tx, &batch, ordinal, &block)?;
            tx.commit()?;
            Ok(result)
        })())
    })
    .await
}

/// SiYuan stores URL paths while the batch stores filesystem names. Decode UTF-8
/// once per component, keeping encoded delimiters and traversal out of the lookup.
fn asset_path(href: &str) -> Option<String> {
    let tail = href.strip_prefix("assets/")?;
    let mut result = String::from("assets");
    for segment in tail.split('/') {
        let mut bytes = segment.bytes();
        let mut decoded = Vec::new();
        while let Some(byte) = bytes.next() {
            decoded.push(if byte == b'%' {
                let high = char::from(bytes.next()?).to_digit(16)?;
                let low = char::from(bytes.next()?).to_digit(16)?;
                (high * 16 + low) as u8
            } else {
                byte
            });
        }
        let name = std::str::from_utf8(&decoded).ok()?;
        if matches!(name, "" | "." | "..")
            || name.contains(['/', '\\', ':', '%', '?', '#'])
            || name.chars().any(char::is_control)
        {
            return None;
        }
        result.push('/');
        result.push_str(name);
    }
    Some(result)
}

fn project(conn: &Connection, batch: &str, ordinal: i64, block: &str) -> Result<Value, Error> {
    if !batches::valid_id(block) {
        return Err(Error::Invalid("invalid native block id"));
    }
    let member = batches::executable_member(conn, batch, ordinal)?;
    if !member.path.to_ascii_lowercase().ends_with(".sy") {
        return Err(Error::Invalid("SiYuan source member required"));
    }
    let (Some(source), Some(revision), Some(job)) =
        (member.source_id, member.revision, member.job_id)
    else {
        return Err(Error::Invalid(
            "native block requires an imported and converted SiYuan member",
        ));
    };
    let row: Option<(i64, String, String, String, String)> = conn
        .query_row(
            "SELECT a.attempt,a.request_id,a.request_json,o.metadata_json,o.content
         FROM jobs j JOIN sources s ON j.input_ref=s.source_id
         JOIN job_attempts a ON a.job_id=j.job_id
         JOIN job_outputs o ON o.job_id=a.job_id AND o.attempt=a.attempt AND o.kind='loss_report'
         WHERE j.job_id=?1 AND j.input_ref=?2 AND s.sha256=?3 AND j.kind='text'
         AND j.state='succeeded' AND a.state='succeeded'
         AND a.attempt=(SELECT MAX(attempt) FROM job_attempts WHERE job_id=j.job_id)
         AND length(CAST(o.content AS BLOB))<=262144",
            params![job, source, revision],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?)),
        )
        .optional()?;
    let (attempt, request_id, wire, metadata, content) =
        row.ok_or(Error::Invalid("verified SiYuan conversion unavailable"))?;
    let parse = |raw: &str| {
        serde_json::from_str::<Value>(raw)
            .map_err(|_| Error::Invalid("invalid conversion metadata"))
    };
    let request = parse(&wire)?;
    let metadata = parse(&metadata)?;
    let loss = usable_receipt(&metadata, &content)
        .ok_or(Error::Invalid("invalid SiYuan conversion receipt"))?;
    let format = &loss["params"]["format"];
    if request["schema"] != "archeaxis.worker-request/v1"
        || request["type"] != "job_request"
        || request["request_id"] != request_id
        || request["job_id"] != job
        || request["attempt"] != attempt
        || request["capability"] != "text.extract"
        || request["inputs"]
            .as_array()
            .is_none_or(|inputs| inputs.len() != 1)
        || request["inputs"][0]["sha256"] != revision
        || request["inputs"][0]["media_type"] != "application/x-siyuan"
        || loss["params"]["media_type"] != "application/x-siyuan"
        || format["format"] != "siyuan"
        || format["parsed"] != true
    {
        return Err(Error::Invalid(
            "conversion identity differs from SiYuan member",
        ));
    }
    let blocks = format["blocks"]
        .as_array()
        .ok_or(Error::Invalid("native block inventory unavailable"))?;
    match blocks.iter().filter(|b| b["id"] == block).count() {
        0 => return Err(Error::NotFound),
        1 => (),
        _ => return Err(Error::Invalid("native block identity is ambiguous")),
    }
    let paths = format["attachment_paths"]
        .as_array()
        .ok_or(Error::Invalid("native attachment inventory unavailable"))?;
    let mut entries = BTreeMap::<String, Vec<(String, i64)>>::new();
    let mut stmt =
        conn.prepare("SELECT relative_path,ordinal FROM ingest_batch_members WHERE batch_id=?1")?;
    for row in stmt.query_map([batch], |r| {
        Ok((r.get::<_, String>(0)?, r.get::<_, i64>(1)?))
    })? {
        let (path, index) = row?;
        entries
            .entry(path.to_lowercase())
            .or_default()
            .push((path, index));
    }
    let mut assets = Vec::new();
    for link in paths.iter().filter(|v| v["source_block_id"] == block) {
        let path = link["relative_path"]
            .as_str()
            .ok_or(Error::Invalid("native attachment path unavailable"))?;
        let mut asset = json!({"relative_path":path,"status":"unbound","target":null});
        if let Some(path) = asset_path(path).filter(|_| link["resolution"] == "unbound") {
            let folded = path.to_lowercase();
            // Qualify batch-root assets only. A scoped assets directory on the note's
            // ancestor chain (including its own SiYuan ID directory) can shadow the root.
            let mut prefix = String::new();
            let shadowed = member.path[..member.path.len() - 3].split('/').any(|part| {
                prefix.push_str(&part.to_lowercase());
                prefix.push('/');
                entries.contains_key(&format!("{prefix}{folded}"))
            });
            match entries.get(&folded).map(Vec::as_slice).unwrap_or(&[]) {
                _ if shadowed => asset["reason"] = json!("scoped_asset_path_unverified"),
                [] => asset["reason"] = json!("path_not_in_batch"),
                [(exact, index)] if exact == &path => {
                    let target: Option<(String,String)> = conn.query_row(
                        "SELECT s.source_id,s.sha256 FROM ingest_batch_members m JOIN sources s
                         ON s.source_id=m.source_id AND s.sha256=m.source_revision WHERE m.batch_id=?1
                         AND m.ordinal=?2 AND m.disposition='pending'", params![batch,index],
                        |r| Ok((r.get(0)?,r.get(1)?))).optional()?;
                    if let Some((id, sha)) = target {
                        asset["status"] = json!("resolved_reference");
                        asset["target"] = json!({"kind":"source","source_id":id,"sha256":sha});
                        asset["target_ordinal"] = json!(index);
                        asset["original_url"] = json!(format!("/api/v1/sources/{id}/original"));
                    } else {
                        asset["reason"] = json!("target_not_imported_or_identity_changed");
                    }
                }
                _ => asset["reason"] = json!("ambiguous_or_case_mismatched_path"),
            }
        } else {
            asset["reason"] = json!("unsupported_path");
        }
        assets.push(asset);
    }
    Ok(
        json!({"schema":"archeaxis.siyuan-block-assets/v1","batch_id":batch,"ordinal":ordinal,
        "native_source_block":{"source_id":source,"sha256":revision,"block_id":block},
        "conversion":{"job_id":job,"attempt":attempt,"loss_sha256":metadata["sha256"]},"assets":assets}),
    )
}
