//! One autosaved document snapshot: editor JSON, stable blocks and projection.
use rusqlite::{Connection, OptionalExtension, params};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::HashSet;

#[derive(Debug)]
pub enum Error {
    Invalid(&'static str),
    NotFound,
    Conflict(i64),
    Sql(rusqlite::Error),
}
impl From<rusqlite::Error> for Error {
    fn from(value: rusqlite::Error) -> Self {
        Self::Sql(value)
    }
}

fn text(node: &Value, depth: usize) -> Result<String, Error> {
    if depth > 32 {
        return Err(Error::Invalid("editor tree exceeds depth limit"));
    }
    if !node.is_object() {
        return Err(Error::Invalid("editor nodes must be objects"));
    }
    if node["type"] == "text" {
        return node["text"]
            .as_str()
            .map(str::to_owned)
            .ok_or(Error::Invalid("text node lacks text"));
    }
    if node["type"] == "hardBreak" {
        return Ok("\n".into());
    }
    let mut result = String::new();
    if let Some(content) = node.get("content") {
        let nodes = content
            .as_array()
            .ok_or(Error::Invalid("node content must be an array"))?;
        for child in nodes {
            result.push_str(&text(child, depth + 1)?);
        }
    }
    Ok(result)
}

fn codec(
    document_id: &str,
    version: i64,
    mut editor: Value,
) -> Result<(Value, Vec<Value>, String), Error> {
    if editor["type"] != "doc" || editor.to_string().len() > 1024 * 1024 {
        return Err(Error::Invalid("bounded doc editor JSON is required"));
    }
    let nodes = editor
        .get_mut("content")
        .and_then(Value::as_array_mut)
        .ok_or(Error::Invalid("document content must be an array"))?;
    if nodes.len() > 5000 {
        return Err(Error::Invalid("document block limit exceeded"));
    }
    let mut ids = HashSet::new();
    let mut blocks = Vec::new();
    let mut projection = Vec::new();
    for (ordinal, node) in nodes.iter_mut().enumerate() {
        let kind = node["type"]
            .as_str()
            .filter(|s| !s.is_empty())
            .ok_or(Error::Invalid("block type is required"))?
            .to_owned();
        let generated = format!(
            "blk_{}",
            &hex::encode(Sha256::digest(
                format!("{document_id}|{version}|{ordinal}|{node}").as_bytes()
            ))[..24]
        );
        let attrs = node
            .as_object_mut()
            .ok_or(Error::Invalid("block must be an object"))?
            .entry("attrs")
            .or_insert_with(|| json!({}))
            .as_object_mut()
            .ok_or(Error::Invalid("block attrs must be an object"))?;
        let id = attrs
            .entry("block_id")
            .or_insert_with(|| json!(generated))
            .as_str()
            .filter(|s| !s.is_empty() && s.len() <= 128)
            .ok_or(Error::Invalid("block ID must be a bounded string"))?
            .to_owned();
        if !ids.insert(id.clone()) {
            return Err(Error::Invalid("duplicate block ID"));
        }
        let content = text(node, 0)?;
        let known = [
            "paragraph",
            "heading",
            "bulletList",
            "orderedList",
            "listItem",
            "blockquote",
            "codeBlock",
            "horizontalRule",
            "image",
            "table",
            "tableRow",
            "tableCell",
            "tableHeader",
            "taskList",
            "taskItem",
        ]
        .contains(&kind.as_str());
        blocks.push(json!({"block_id":id,"kind":kind,"ordinal":ordinal,"node_json":node,"text_projection":content,
            "codec_status":if known {"known"} else {"preserved_unknown"}}));
        if !content.is_empty() {
            projection.push(content);
        }
    }
    Ok((editor, blocks, projection.join("\n")))
}

pub fn read(conn: &Connection, id: &str, requested: Option<i64>) -> Result<Value, Error> {
    let header: Option<(Option<String>,Option<String>,String,i64)> = conn.query_row(
        "SELECT source_id,source_revision,title,current_version FROM documents WHERE document_id=?1",[id],
        |r| Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?))).optional()?;
    let (source_id, source_revision, title, current) = header.ok_or(Error::NotFound)?;
    let version = requested.unwrap_or(current);
    let snapshot: Option<(String,String,String,Option<String>)> = conn.query_row(
        "SELECT editor_json,text_projection,content_sha256,revision_basis FROM document_versions WHERE document_id=?1 AND version=?2",
        params![id,version],|r| Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?))).optional()?;
    let (editor, projection, digest, basis) = snapshot.ok_or(Error::NotFound)?;
    let mut stmt = conn.prepare("SELECT block_id,kind,ordinal,node_json,text_projection,codec_status FROM document_blocks WHERE document_id=?1 AND version=?2 ORDER BY ordinal")?;
    let blocks = stmt.query_map(params![id,version], |r| {
        let node: String = r.get(3)?;
        Ok(json!({"block_id":r.get::<_,String>(0)?,"kind":r.get::<_,String>(1)?,"ordinal":r.get::<_,i64>(2)?,
            "node_json":serde_json::from_str::<Value>(&node).map_err(|_|rusqlite::Error::InvalidQuery)?,
            "text_projection":r.get::<_,String>(4)?,"codec_status":r.get::<_,String>(5)?}))
    })?.collect::<Result<Vec<_>,_>>()?;
    Ok(
        json!({"document_id":id,"source_id":source_id,"source_revision":source_revision,"title":title,"version":version,
        "editor_json":serde_json::from_str::<Value>(&editor).map_err(|_|Error::Invalid("stored editor JSON is invalid"))?,
        "text_projection":projection,"content_sha256":digest,"blocks":blocks,"revision_basis":basis.map(|raw|serde_json::from_str::<Value>(&raw)).transpose().map_err(|_|Error::Invalid("stored revision basis is invalid"))?}),
    )
}

fn append(
    tx: &rusqlite::Transaction<'_>,
    id: &str,
    expected: i64,
    editor: Value,
    basis: Option<Value>,
) -> Result<(), Error> {
    let current: Option<i64> = tx
        .query_row(
            "SELECT current_version FROM documents WHERE document_id=?1",
            [id],
            |r| r.get(0),
        )
        .optional()?;
    let current = current.ok_or(Error::NotFound)?;
    if current != expected {
        return Err(Error::Conflict(current));
    }
    let version = current
        .checked_add(1)
        .ok_or(Error::Invalid("version exhausted"))?;
    let (editor, blocks, projection) = codec(id, version, editor)?;
    let encoded = editor.to_string();
    let digest = hex::encode(Sha256::digest(encoded.as_bytes()));
    tx.execute("INSERT INTO document_versions(document_id,version,editor_json,text_projection,content_sha256,revision_basis) VALUES(?1,?2,?3,?4,?5,?6)",params![id,version,encoded,projection,digest,basis.map(|v|v.to_string())])?;
    for block in blocks {
        tx.execute("INSERT INTO document_blocks(document_id,version,block_id,ordinal,kind,node_json,text_projection,codec_status) VALUES(?1,?2,?3,?4,?5,?6,?7,?8)",
            params![id,version,block["block_id"].as_str(),block["ordinal"].as_i64(),block["kind"].as_str(),block["node_json"].to_string(),block["text_projection"].as_str(),block["codec_status"].as_str()])?;
    }
    tx.execute(
        "UPDATE documents SET current_version=?1 WHERE document_id=?2",
        params![version, id],
    )?;
    Ok(())
}

pub fn create(
    conn: &mut Connection,
    source_id: &str,
    revision: &str,
    title: &str,
    editor: Value,
) -> Result<Value, Error> {
    create_optional(conn, Some(source_id), Some(revision), title, editor)
}

pub fn create_optional(
    conn: &mut Connection,
    source_id: Option<&str>,
    revision: Option<&str>,
    title: &str,
    editor: Value,
) -> Result<Value, Error> {
    if title.len() > 1024 {
        return Err(Error::Invalid("title exceeds limit"));
    }
    match (source_id, revision) {
        (None, None) => {}
        (Some(source_id), Some(revision)) => {
            let digest: Option<String> = conn
                .query_row(
                    "SELECT sha256 FROM sources WHERE source_id=?1",
                    [source_id],
                    |r| r.get(0),
                )
                .optional()?;
            if digest.as_deref() != Some(revision) {
                return Err(Error::Invalid(
                    "source revision must match its immutable CAS hash",
                ));
            }
            archeaxis_store_sqlite::raw_objects::read(conn, revision)?;
        }
        _ => {
            return Err(Error::Invalid(
                "source ID and revision must be provided together",
            ));
        }
    }
    let id: String = conn.query_row("SELECT 'doc_' || lower(hex(randomblob(16)))", [], |r| {
        r.get(0)
    })?;
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    tx.execute("INSERT INTO documents(document_id,source_id,source_revision,title,current_version) VALUES(?1,?2,?3,?4,0)",params![id,source_id,revision,title])?;
    append(&tx, &id, 0, editor, None)?;
    tx.commit()?;
    read(conn, &id, None)
}

pub fn save(conn: &mut Connection, id: &str, expected: i64, editor: Value) -> Result<Value, Error> {
    save_with_basis(conn, id, expected, editor, None)
}

pub fn save_with_basis(
    conn: &mut Connection,
    id: &str,
    expected: i64,
    editor: Value,
    basis: Option<Value>,
) -> Result<Value, Error> {
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    if let Some(ref value) = basis {
        validate_basis(&tx, id, expected, value)?;
    }
    append(&tx, id, expected, editor, basis)?;
    tx.commit()?;
    read(conn, id, None)
}

pub fn restore(
    conn: &mut Connection,
    id: &str,
    expected: i64,
    version: i64,
) -> Result<Value, Error> {
    let snapshot = read(conn, id, Some(version))?;
    save(conn, id, expected, snapshot["editor_json"].clone())
}

pub fn list(conn: &Connection) -> Result<Vec<Value>, Error> {
    let mut stmt = conn.prepare(
        "SELECT d.document_id,d.source_id,d.source_revision,d.title,d.current_version,v.content_sha256 FROM documents d JOIN document_versions v ON v.document_id=d.document_id AND v.version=d.current_version ORDER BY d.created_at DESC,d.document_id LIMIT 500",
    )?;
    let summaries = stmt
        .query_map([], |r| Ok(json!({"document_id":r.get::<_,String>(0)?,"source_id":r.get::<_,Option<String>>(1)?,"source_revision":r.get::<_,Option<String>>(2)?,"title":r.get::<_,String>(3)?,"version":r.get::<_,i64>(4)?,"content_sha256":r.get::<_,String>(5)?})))?
        .collect::<Result<Vec<_>, _>>()?;
    Ok(summaries)
}

fn validate_basis(conn: &Connection, id: &str, expected: i64, basis: &Value) -> Result<(), Error> {
    let object = basis
        .as_object()
        .ok_or(Error::Invalid("revision basis must be an object"))?;
    if basis.to_string().len() > 16 * 1024
        || object.keys().any(|key| {
            !["reference_version", "check_id", "position", "rationale"].contains(&key.as_str())
        })
    {
        return Err(Error::Invalid(
            "revision basis has unknown fields or exceeds limit",
        ));
    }
    if basis["rationale"]
        .as_str()
        .is_none_or(|v| v.trim().is_empty() || v.len() > 4096)
    {
        return Err(Error::Invalid("revision rationale required"));
    }
    let reference = match basis.get("reference_version") {
        Some(v) => v
            .as_i64()
            .ok_or(Error::Invalid("reference version must be an integer"))?,
        None => expected,
    };
    if reference < 1 || reference > expected {
        return Err(Error::Invalid(
            "reference version must be historical or current",
        ));
    }
    read(conn, id, Some(reference))?;
    if let Some(check) = basis.get("check_id") {
        let check = check
            .as_str()
            .ok_or(Error::Invalid("check ID must be a string"))?;
        let found:bool=conn.query_row("SELECT EXISTS(SELECT 1 FROM document_checks WHERE check_id=?1 AND document_id=?2 AND version=?3)",params![check,id,reference],|r|r.get(0))?;
        if !found {
            return Err(Error::Invalid(
                "revision check must match reference document version",
            ));
        }
    }
    if let Some(position) = basis.get("position") {
        if !position.is_object() {
            return Err(Error::Invalid("revision position must be an object"));
        }
        if let Some(block) = position.get("block_id") {
            let block = block
                .as_str()
                .ok_or(Error::Invalid("revision block ID must be a string"))?;
            let exists:bool=conn.query_row("SELECT EXISTS(SELECT 1 FROM document_blocks WHERE document_id=?1 AND version=?2 AND block_id=?3)",params![id,reference,block],|r|r.get(0))?;
            if !exists {
                return Err(Error::Invalid(
                    "revision position must match referenced version block",
                ));
            }
        }
        if let Some(check) = basis.get("check_id").and_then(Value::as_str) {
            let raw: String = conn.query_row(
                "SELECT receipt_json FROM document_checks WHERE check_id=?1",
                [check],
                |r| r.get(0),
            )?;
            let receipt: Value = serde_json::from_str(&raw)
                .map_err(|_| Error::Invalid("stored check receipt invalid"))?;
            if receipt["position"] != *position {
                return Err(Error::Invalid(
                    "revision position must match referenced check position",
                ));
            }
        }
    }
    Ok(())
}

pub struct CheckInput {
    pub version: i64,
    pub dimension: String,
    pub provider_mode: String,
    pub status: Option<String>,
    pub source_id: Option<String>,
    pub source_revision: Option<String>,
    pub position: Option<Value>,
    pub recognition_job_id: Option<String>,
    pub recognition_result_sha256: Option<String>,
    pub basis: Option<String>,
    pub reason: Option<String>,
}

pub fn checks(conn: &Connection, id: &str, version: Option<i64>) -> Result<Value, Error> {
    checks_page(conn, id, version, 0)
}
pub fn checks_page(
    conn: &Connection,
    id: &str,
    version: Option<i64>,
    offset: i64,
) -> Result<Value, Error> {
    if offset < 0 {
        return Err(Error::Invalid("check offset must be nonnegative"));
    }
    let current = read(conn, id, None)?;
    let snapshot = read(conn, id, version)?;
    let version = snapshot["version"].as_i64().unwrap();
    let mut stmt=conn.prepare("SELECT receipt_json FROM document_checks WHERE document_id=?1 AND version=?2 ORDER BY rowid LIMIT 1000 OFFSET ?3")?;
    let rows = stmt
        .query_map(params![id, version, offset], |r| r.get::<_, String>(0))?
        .collect::<Result<Vec<_>, _>>()?;
    let records = rows
        .into_iter()
        .map(|raw| {
            serde_json::from_str::<Value>(&raw)
                .map_err(|_| Error::Invalid("stored check receipt is invalid"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    let count: i64 = conn.query_row(
        "SELECT count(*) FROM document_checks WHERE document_id=?1 AND version=?2",
        params![id, version],
        |r| r.get(0),
    )?;
    Ok(
        json!({"document_id":id,"version":version,"content_sha256":snapshot["content_sha256"],"historical":version!=current["version"].as_i64().unwrap(),"default_status":"unverified","checks":records,"checks_capped":count.saturating_sub(offset)>1000,"next_offset":if count.saturating_sub(offset)>1000 {Some(offset.saturating_add(1000))}else{None}}),
    )
}

pub fn record_check(
    conn: &mut Connection,
    id: &str,
    actor: &str,
    input: CheckInput,
) -> Result<Value, Error> {
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let snapshot = read(&tx, id, Some(input.version))?;
    if !["recognition_fidelity", "professional_basis"].contains(&input.dimension.as_str()) {
        return Err(Error::Invalid("unsupported check dimension"));
    }
    if !["manual", "cloud"].contains(&input.provider_mode.as_str()) {
        return Err(Error::Invalid("unsupported provider mode"));
    }
    let common = [
        "pending",
        "unverified",
        "uncertain",
        "original_unclear",
        "conflicting",
        "failed",
    ];
    let status = input
        .status
        .as_deref()
        .unwrap_or(if input.provider_mode == "cloud" {
            "pending"
        } else {
            "unverified"
        });
    let specialized = if input.dimension == "recognition_fidelity" {
        ["faithful", "mismatch", "passed"]
    } else {
        ["supported", "refuted", "passed"]
    };
    if !common.contains(&status) && !specialized.contains(&status) {
        return Err(Error::Invalid("status does not match check dimension"));
    }
    if input.provider_mode == "manual" && actor != "human" {
        return Err(Error::Invalid("manual check records require human actor"));
    }
    if input.provider_mode == "cloud" && status != "pending" {
        return Err(Error::Invalid(
            "cloud worker is not configured; only a pending request can be recorded",
        ));
    }
    if input.basis.as_ref().is_some_and(|v| v.len() > 8192)
        || input.reason.as_ref().is_some_and(|v| v.len() > 4096)
    {
        return Err(Error::Invalid("check explanation exceeds limit"));
    }
    if input
        .position
        .as_ref()
        .is_some_and(|v| !v.is_object() || v.to_string().len() > 8192)
    {
        return Err(Error::Invalid("check position must be a bounded object"));
    }
    if input.source_id.is_some() || input.source_revision.is_some() {
        if input.source_id.as_deref() != snapshot["source_id"].as_str()
            || input.source_revision.as_deref() != snapshot["source_revision"].as_str()
        {
            return Err(Error::Invalid(
                "check source must match document source identity",
            ));
        }
    }
    if let Some(position) = input.position.as_ref() {
        if let Some(block) = position.get("block_id") {
            let block = block
                .as_str()
                .ok_or(Error::Invalid("check block must be a string"))?;
            let found:bool=tx.query_row("SELECT EXISTS(SELECT 1 FROM document_blocks WHERE document_id=?1 AND version=?2 AND block_id=?3)",params![id,input.version,block],|r|r.get(0))?;
            if !found {
                return Err(Error::Invalid(
                    "check position must match document version block",
                ));
            }
        }
        if position["type"] == "text" {
            let revision = snapshot["source_revision"].as_str().ok_or(Error::Invalid(
                "original text position requires source identity",
            ))?;
            let bytes = archeaxis_store_sqlite::raw_objects::read(&tx, revision)?;
            let original = std::str::from_utf8(&bytes)
                .map_err(|_| Error::Invalid("text position requires UTF8 original"))?;
            let start = position["start"]
                .as_u64()
                .and_then(|v| usize::try_from(v).ok())
                .ok_or(Error::Invalid("text position start required"))?;
            let end = position["end"]
                .as_u64()
                .and_then(|v| usize::try_from(v).ok())
                .ok_or(Error::Invalid("text position end required"))?;
            if start >= end
                || end > bytes.len()
                || !original.is_char_boundary(start)
                || !original.is_char_boundary(end)
            {
                return Err(Error::Invalid(
                    "text position must locate actual original UTF8 bytes",
                ));
            }
        }
    }
    match (&input.recognition_job_id, &input.recognition_result_sha256) {
        (None, None) => {}
        (Some(job), Some(digest)) => {
            let mut outputs=tx.prepare("SELECT o.content FROM jobs j JOIN job_outputs o ON o.job_id=j.job_id JOIN job_attempts a ON a.job_id=o.job_id AND a.attempt=o.attempt WHERE j.job_id=?1 AND j.state='succeeded' AND a.state='succeeded' AND j.input_ref=?2 AND json_extract(o.metadata_json,'$.sha256')=?3")?;
            let values = outputs
                .query_map(params![job, snapshot["source_id"].as_str(), digest], |r| {
                    r.get::<_, String>(0)
                })?
                .collect::<Result<Vec<_>, _>>()?;
            let valid = values
                .iter()
                .any(|content| hex::encode(Sha256::digest(content.as_bytes())) == *digest);
            if !valid {
                return Err(Error::Invalid(
                    "recognition result must match completed source job output",
                ));
            }
        }
        _ => {
            return Err(Error::Invalid(
                "recognition job and result SHA must be paired",
            ));
        }
    }
    if input.provider_mode == "manual" && specialized.contains(&status) {
        if input.basis.as_deref().is_none_or(|v| v.trim().is_empty()) {
            return Err(Error::Invalid("manual conclusion requires actual basis"));
        }
        if input.dimension == "recognition_fidelity"
            && (input.recognition_job_id.is_none() || input.position.is_none())
        {
            return Err(Error::Invalid(
                "recognition conclusion requires job result and original position",
            ));
        }
    }
    let check_id: String = tx.query_row("SELECT 'chk_'||lower(hex(randomblob(16)))", [], |r| {
        r.get(0)
    })?;
    let at: String = tx.query_row("SELECT datetime('now')", [], |r| r.get(0))?;
    let record = json!({"check_id":check_id,"document_id":id,"version":input.version,"content_sha256":snapshot["content_sha256"],
        "dimension":input.dimension,"status":status,"actor":actor,"provider_mode":input.provider_mode,
        "execution_verified":false,"execution_state":if input.provider_mode=="cloud"{"not_executed"}else{"reported_manual"},
        "source_id":snapshot["source_id"],"source_revision":snapshot["source_revision"],"position":input.position,
        "recognition_job_id":input.recognition_job_id,"recognition_result_sha256":input.recognition_result_sha256,
        "basis":input.basis,"reason":if input.provider_mode=="cloud"{Some("worker_not_configured".to_owned())}else{input.reason},"recorded_at":at});
    tx.execute("INSERT INTO document_checks(check_id,document_id,version,dimension,receipt_json) VALUES(?1,?2,?3,?4,?5)",params![check_id,id,input.version,record["dimension"].as_str(),record.to_string()])?;
    tx.commit()?;
    Ok(record)
}

/// Latest saved note versions are discoverable without source/review/check gates.
pub fn search(conn: &Connection, query: &str) -> Result<Vec<Value>, Error> {
    if query.len() > 512 {
        return Err(Error::Invalid("document search query exceeds limit"));
    }
    if query.trim().is_empty() {
        return Ok(Vec::new());
    }
    let pattern = format!(
        "%{}%",
        query
            .replace('\\', "\\\\")
            .replace('%', "\\%")
            .replace('_', "\\_")
    );
    let mut stmt=conn.prepare("SELECT d.document_id,d.source_id,d.source_revision,d.title,d.current_version,v.content_sha256,substr(v.text_projection,1,320) FROM documents d JOIN document_versions v ON v.document_id=d.document_id AND v.version=d.current_version WHERE v.text_projection LIKE ?1 ESCAPE '\\' OR d.title LIKE ?1 ESCAPE '\\' ORDER BY d.created_at DESC,d.document_id LIMIT 20")?;
    let rows=stmt.query_map([pattern],|r|Ok(json!({"document_id":r.get::<_,String>(0)?,"source_id":r.get::<_,Option<String>>(1)?,"source_revision":r.get::<_,Option<String>>(2)?,"title":r.get::<_,String>(3)?,"version":r.get::<_,i64>(4)?,"content_sha256":r.get::<_,String>(5)?,"head":r.get::<_,String>(6)?})))?.collect::<Result<Vec<_>,_>>()?;
    Ok(rows)
}

/// Explicit execution preflight. No provider is configured by this product path yet.
/// Preserve each failed attempt and permit only an explicit retry of that attempt.
pub fn execute_check_unconfigured(
    conn: &mut Connection,
    id: &str,
    check_id: &str,
    expected_sha: &str,
    retry_of: Option<&str>,
) -> Result<Value, Error> {
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let raw: Option<String> = tx
        .query_row(
            "SELECT receipt_json FROM document_checks WHERE check_id=?1 AND document_id=?2",
            params![check_id, id],
            |r| r.get(0),
        )
        .optional()?;
    let request: Value = serde_json::from_str(&raw.ok_or(Error::NotFound)?)
        .map_err(|_| Error::Invalid("invalid stored check"))?;
    if request["provider_mode"] != "cloud" || request["status"] != "pending" {
        return Err(Error::Invalid(
            "execution requires original cloud pending request",
        ));
    }
    let version = request["version"]
        .as_i64()
        .ok_or(Error::Invalid("invalid check version"))?;
    let snapshot = read(&tx, id, Some(version))?;
    if snapshot["content_sha256"] != expected_sha || request["content_sha256"] != expected_sha {
        return Err(Error::Invalid("check snapshot digest mismatch"));
    }
    let previous: Option<String> = tx.query_row(
        "SELECT receipt_json FROM document_checks WHERE document_id=?1 AND version=?2 AND json_extract(receipt_json,'$.request_check_id')=?3 ORDER BY rowid DESC LIMIT 1",
        params![id,version,check_id],|r|r.get(0)).optional()?;
    match (previous, retry_of) {
        (None, None) => {}
        (Some(raw), Some(task)) => {
            let previous: Value = serde_json::from_str(&raw)
                .map_err(|_| Error::Invalid("invalid previous attempt"))?;
            if previous["status"] != "failed" || previous["attempt_id"] != task {
                return Err(Error::Invalid("retry must reference latest failed attempt"));
            }
        }
        _ => return Err(Error::Invalid("explicit retry required")),
    }
    let task: String = tx.query_row("SELECT 'doccheck_'||lower(hex(randomblob(16)))", [], |r| {
        r.get(0)
    })?;
    let terminal_id: String =
        tx.query_row("SELECT 'chk_'||lower(hex(randomblob(16)))", [], |r| {
            r.get(0)
        })?;
    let at: String = tx.query_row("SELECT datetime('now')", [], |r| r.get(0))?;
    let mut result = request.clone();
    result["check_id"] = json!(terminal_id);
    result["request_check_id"] = json!(check_id);
    result["attempt_id"] = json!(task);
    result["retry_of_task_id"] = json!(retry_of);
    result["status"] = json!("failed");
    result["reason"] = json!("not_configured");
    result["actor"] = json!("machine");
    result["execution_verified"] = json!(false);
    result["execution_state"] = json!("not_executed");
    result["recorded_at"] = json!(at);
    result["engine_receipt"] = Value::Null;
    result["retrieval_receipts"] = json!([]);
    let conditions = result.to_string();
    crate::machine::record_machine_task_in_transaction(
        &tx,
        &crate::machine::MachineTask {
            task_id: &task,
            principal: "machine",
            conditions: &conditions,
            knowledge_version: None,
            method_version: Some("document-check/v1"),
            tool_version: None,
            model_version: "not_configured",
            scope: "runtime.document_check",
            outcome: "failed",
            failure: Some("not_configured"),
            retest_of: retry_of,
        },
    )?;
    tx.execute("INSERT INTO document_checks(check_id,document_id,version,dimension,receipt_json) VALUES(?1,?2,?3,?4,?5)",
        params![terminal_id,id,version,request["dimension"].as_str(),conditions])?;
    tx.commit()?;
    Ok(result)
}

#[cfg(test)]
mod execution_preflight_tests {
    use super::*;
    fn setup() -> Connection {
        let c = Connection::open_in_memory().unwrap();
        c.execute_batch("CREATE TABLE documents(document_id TEXT PRIMARY KEY,source_id TEXT,source_revision TEXT,title TEXT,current_version INTEGER);
          CREATE TABLE document_versions(document_id TEXT,version INTEGER,editor_json TEXT,text_projection TEXT,content_sha256 TEXT,revision_basis TEXT);
          CREATE TABLE document_blocks(document_id TEXT,version INTEGER,block_id TEXT,kind TEXT,ordinal INTEGER,node_json TEXT,text_projection TEXT,codec_status TEXT);
          CREATE TABLE document_checks(check_id TEXT PRIMARY KEY,document_id TEXT,version INTEGER,dimension TEXT,receipt_json TEXT);
          INSERT INTO documents VALUES('d',NULL,NULL,'ordinary',2);
          INSERT INTO document_versions VALUES('d',1,'{}','old','old-sha',NULL);
          INSERT INTO document_versions VALUES('d',2,'{}','new','new-sha',NULL);").unwrap();
        let request = json!({"check_id":"pending","document_id":"d","version":1,"content_sha256":"old-sha","dimension":"professional_basis","provider_mode":"cloud","status":"pending"});
        c.execute(
            "INSERT INTO document_checks VALUES('pending','d',1,'professional_basis',?1)",
            [request.to_string()],
        )
        .unwrap();
        c
    }
    #[test]
    fn absent_provider_persists_failure_and_explicit_retry_without_changing_document() {
        let mut c = setup();
        let a = execute_check_unconfigured(&mut c, "d", "pending", "old-sha", None).unwrap();
        assert_eq!(a["reason"], "not_configured");
        assert_eq!(a["execution_verified"], false);
        assert!(execute_check_unconfigured(&mut c, "d", "pending", "old-sha", None).is_err());
        let b =
            execute_check_unconfigured(&mut c, "d", "pending", "old-sha", a["attempt_id"].as_str())
                .unwrap();
        assert_ne!(a["attempt_id"], b["attempt_id"]);
        assert_eq!(read(&c, "d", None).unwrap()["content_sha256"], "new-sha");
        assert_eq!(
            checks(&c, "d", Some(1)).unwrap()["checks"]
                .as_array()
                .unwrap()
                .len(),
            3
        );
        let n:i64=c.query_row("SELECT count(*) FROM machine_tasks WHERE outcome='failed' AND knowledge_version IS NULL",[],|r|r.get(0)).unwrap();
        assert_eq!(n, 2);
    }
    #[test]
    fn rejects_wrong_sha_cross_document_and_foreign_retry_without_partial_receipt() {
        let mut c = setup();
        assert!(execute_check_unconfigured(&mut c, "d", "pending", "new-sha", None).is_err());
        assert!(execute_check_unconfigured(&mut c, "other", "pending", "old-sha", None).is_err());
        assert!(
            execute_check_unconfigured(&mut c, "d", "pending", "old-sha", Some("foreign")).is_err()
        );
        let n: i64 = c
            .query_row("SELECT count(*) FROM document_checks", [], |r| r.get(0))
            .unwrap();
        assert_eq!(n, 1);
    }
}

/// Snapshot-bound claim for one explicit cloud attempt. No network occurs here.
pub struct CheckExecution {
    pub preparation_error: Option<&'static str>,
    pub running: Value,
    pub text: String,
    pub original: Option<(String, String, Vec<u8>)>,
    pub recognition: Option<Value>,
}

pub fn begin_check(
    conn: &mut Connection,
    id: &str,
    check_id: &str,
    expected_sha: &str,
    retry_of: Option<&str>,
) -> Result<CheckExecution, Error> {
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let raw: Option<String> = tx
        .query_row(
            "SELECT receipt_json FROM document_checks WHERE document_id=?1 AND check_id=?2",
            params![id, check_id],
            |r| r.get(0),
        )
        .optional()?;
    let request: Value = serde_json::from_str(&raw.ok_or(Error::NotFound)?)
        .map_err(|_| Error::Invalid("invalid stored check"))?;
    if request["provider_mode"] != "cloud"
        || request["status"] != "pending"
        || !request["request_check_id"].is_null()
    {
        return Err(Error::Invalid("execution requires original cloud request"));
    }
    let version = request["version"]
        .as_i64()
        .ok_or(Error::Invalid("invalid version"))?;
    let snapshot = read(&tx, id, Some(version))?;
    if snapshot["content_sha256"] != expected_sha || request["content_sha256"] != expected_sha {
        return Err(Error::Invalid("check snapshot digest mismatch"));
    }
    let previous:Option<String>=tx.query_row(
        "SELECT receipt_json FROM document_checks WHERE document_id=?1 AND version=?2 AND json_extract(receipt_json,'$.request_check_id')=?3 ORDER BY rowid DESC LIMIT 1",
        params![id,version,check_id],|r|r.get(0)).optional()?;
    match (previous, retry_of) {
        (None, None) => {}
        (Some(raw), Some(previous_id)) => {
            let previous: Value = serde_json::from_str(&raw)
                .map_err(|_| Error::Invalid("invalid previous attempt"))?;
            if previous["status"] != "failed" || previous["attempt_id"] != previous_id {
                return Err(Error::Invalid("explicit latest failed retry required"));
            }
        }
        _ => return Err(Error::Invalid("explicit latest failed retry required")),
    }
    // Identity/version/retry checks above reject before any attempt is claimed.
    // Material failures below become a terminal attempt without invoking a worker.
    let material = (|| -> Result<CheckExecution, Error> {
        let text = snapshot["text_projection"]
            .as_str()
            .ok_or(Error::Invalid("missing document text"))?
            .to_owned();
        if text.len() > 64000 {
            return Err(Error::Invalid("cloud snapshot exceeds bound"));
        }
        let original = if request["dimension"] == "recognition_fidelity" {
            match (
                snapshot["source_id"].as_str(),
                snapshot["source_revision"].as_str(),
            ) {
                (Some(source_id), Some(revision)) => {
                    let name: String = tx.query_row(
                        "SELECT original_name FROM sources WHERE source_id=?1 AND sha256=?2",
                        params![source_id, revision],
                        |r| r.get(0),
                    )?;
                    let bytes = archeaxis_store_sqlite::raw_objects::read(&tx, revision)?;
                    if bytes.len() > 64000 || hex::encode(Sha256::digest(&bytes)) != revision {
                        return Err(Error::Invalid("original exceeds bound or digest mismatch"));
                    }
                    Some((name, revision.to_owned(), bytes))
                }
                _ => None,
            }
        } else {
            None
        };
        let recognition = if let (Some(job), Some(digest)) = (
            request["recognition_job_id"].as_str(),
            request["recognition_result_sha256"].as_str(),
        ) {
            let output:Option<String>=tx.query_row("SELECT o.content FROM jobs j JOIN job_outputs o ON j.job_id=o.job_id JOIN job_attempts a ON a.job_id=o.job_id AND a.attempt=o.attempt WHERE j.job_id=?1 AND j.input_ref=?2 AND j.state='succeeded' AND a.state='succeeded' AND o.kind='text' AND json_extract(o.metadata_json,'$.sha256')=?3 ORDER BY o.attempt DESC LIMIT 1",params![job,snapshot["source_id"].as_str(),digest],|r|r.get(0)).optional()?;
            let output = output.ok_or(Error::Invalid("recognition output unavailable"))?;
            if output.len() > 64000 || hex::encode(Sha256::digest(output.as_bytes())) != digest {
                return Err(Error::Invalid(
                    "recognition digest mismatch or exceeds bound",
                ));
            }
            Some(json!({"job_id":job,"result_sha256":digest,"text":output}))
        } else {
            None
        };
        Ok(CheckExecution {
            running: Value::Null,
            text,
            original,
            recognition,
            preparation_error: None,
        })
    })();
    let attempt: String =
        tx.query_row("SELECT 'doccheck_'||lower(hex(randomblob(16)))", [], |r| {
            r.get(0)
        })?;
    let running_id: String =
        tx.query_row("SELECT 'chk_'||lower(hex(randomblob(16)))", [], |r| {
            r.get(0)
        })?;
    let at: String = tx.query_row("SELECT datetime('now')", [], |r| r.get(0))?;
    let mut running = request;
    running["check_id"] = json!(running_id);
    running["request_check_id"] = json!(check_id);
    running["attempt_id"] = json!(attempt);
    running["retry_of_task_id"] = json!(retry_of);
    running["actor"] = json!("machine");
    running["execution_verified"] = json!(false);
    running["execution_state"] = json!("running");
    running["recorded_at"] = json!(at);
    tx.execute("INSERT INTO document_checks(check_id,document_id,version,dimension,receipt_json) VALUES(?1,?2,?3,?4,?5)",params![running_id,id,version,running["dimension"].as_str(),running.to_string()])?;
    tx.commit()?;
    match material {
        Ok(mut execution) => {
            execution.running = running;
            Ok(execution)
        }
        Err(error) => {
            let reason = match error {
                Error::Invalid("cloud snapshot exceeds bound") => "cloud_snapshot_exceeds_bound",
                Error::Invalid("original exceeds bound or digest mismatch") => {
                    "original_bound_or_digest_mismatch"
                }
                Error::Invalid("recognition output unavailable") => {
                    "recognition_output_unavailable"
                }
                Error::Invalid("recognition digest mismatch or exceeds bound") => {
                    "recognition_bound_or_digest_mismatch"
                }
                _ => "material_preflight_failed",
            };
            Ok(CheckExecution {
                running,
                text: String::new(),
                original: None,
                recognition: None,
                preparation_error: Some(reason),
            })
        }
    }
}

/// Terminal append and machine receipt commit together. No document or prior receipt is edited.
pub fn finish_check(
    conn: &mut Connection,
    running: &Value,
    response: &Value,
    provider: &str,
    model: &str,
) -> Result<Value, Error> {
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let raw: Option<String> = tx
        .query_row(
            "SELECT receipt_json FROM document_checks WHERE check_id=?1 AND document_id=?2",
            params![
                running["check_id"].as_str(),
                running["document_id"].as_str()
            ],
            |r| r.get(0),
        )
        .optional()?;
    let persisted: Value = serde_json::from_str(&raw.ok_or(Error::NotFound)?)
        .map_err(|_| Error::Invalid("invalid running check"))?;
    if persisted != *running || running["execution_state"] != "running" {
        return Err(Error::Invalid("running check identity mismatch"));
    }
    let exists:bool=tx.query_row("SELECT EXISTS(SELECT 1 FROM document_checks WHERE json_extract(receipt_json,'$.attempt_id')=?1 AND json_extract(receipt_json,'$.execution_state')!='running')",[running["attempt_id"].as_str()],|r|r.get(0))?;
    if exists {
        return Err(Error::Invalid("attempt already terminal"));
    }
    if response["schema"] != "archeaxis.document-check.response/v1" {
        return Err(Error::Invalid("worker response schema mismatch"));
    }
    for key in [
        "attempt_id",
        "request_check_id",
        "document_id",
        "version",
        "content_sha256",
        "dimension",
    ] {
        if response[key] != running[key] {
            return Err(Error::Invalid("worker snapshot identity mismatch"));
        }
    }
    let success = response["outcome"] == "succeeded";
    if !success && response["outcome"] != "failed" {
        return Err(Error::Invalid("invalid execution outcome"));
    }
    let basis = response["basis"]
        .as_str()
        .ok_or(Error::Invalid("missing basis"))?;
    let raw_response = response["raw_response"]
        .as_str()
        .ok_or(Error::Invalid("missing raw response"))?;
    let retrieval = response["retrieval_receipts"]
        .as_array()
        .ok_or(Error::Invalid("missing retrieval receipts"))?;
    if basis.len() > 8192
        || raw_response.len() > 32000
        || retrieval.len() > 10
        || response.to_string().len() > 128000
    {
        return Err(Error::Invalid("worker response exceeds bound"));
    }
    let reason = response["reason"].as_str();
    if !success
        && reason.is_none_or(|v| {
            v.is_empty()
                || v.len() > 128
                || !v.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'_')
        })
    {
        return Err(Error::Invalid(
            "failed execution requires bounded reason code",
        ));
    }
    if success {
        let status = response["status"]
            .as_str()
            .ok_or(Error::Invalid("missing conclusion"))?;
        let allowed: &[&str] = if running["dimension"] == "recognition_fidelity" {
            &[
                "faithful",
                "mismatch",
                "uncertain",
                "original_unclear",
                "conflicting",
            ]
        } else {
            &["supported", "refuted", "uncertain", "conflicting"]
        };
        if !allowed.contains(&status) {
            return Err(Error::Invalid("conclusion does not match dimension"));
        }
        let verdict: Value = serde_json::from_str(raw_response)
            .map_err(|_| Error::Invalid("invalid provider verdict JSON"))?;
        if verdict["status"] != response["status"]
            || verdict["basis"] != response["basis"]
            || verdict.as_object().is_none_or(|v| v.len() != 2)
        {
            return Err(Error::Invalid(
                "provider verdict differs from recorded conclusion",
            ));
        }
        if running["dimension"] == "professional_basis" {
            if !retrieval.iter().any(|r| r["kind"] == "search")
                || !retrieval.iter().any(|r| r["kind"] == "article")
            {
                return Err(Error::Invalid(
                    "professional check requires retrieval receipts",
                ));
            }
            for receipt in retrieval {
                if receipt["body_sha256"]
                    .as_str()
                    .is_none_or(|v| v.len() != 64 || !v.bytes().all(|b| b.is_ascii_hexdigit()))
                    || receipt["http_status"]
                        .as_u64()
                        .is_none_or(|v| !(200..300).contains(&v))
                    || receipt["bytes"]
                        .as_u64()
                        .is_none_or(|v| v == 0 || v > 500000)
                    || receipt["retrieved_at"].as_f64().is_none_or(|v| v <= 0.0)
                {
                    return Err(Error::Invalid("invalid retrieval receipt"));
                }
            }
        }
        let engine = &response["engine_receipt"];
        if basis.trim().is_empty()
            || engine["tokens_used"].as_u64().is_none()
            || engine["provider"] != provider
            || engine["requested_model"] != model
            || engine["model"]
                .as_str()
                .is_none_or(|v| v.is_empty() || v == "unknown" || v.len() > 256)
            || raw_response.trim().is_empty()
            || engine["response_sha256"] != hex::encode(Sha256::digest(raw_response.as_bytes()))
            || engine["finish_reason"].as_str().is_none_or(|v| v != "stop")
            || engine["prompt_sha256"]
                .as_str()
                .is_none_or(|v| v.len() != 64 || !v.bytes().all(|b| b.is_ascii_hexdigit()))
        {
            return Err(Error::Invalid("successful execution evidence mismatch"));
        }
    }
    let mut result = running.clone();
    result["check_id"] = tx
        .query_row("SELECT 'chk_'||lower(hex(randomblob(16)))", [], |r| {
            r.get::<_, String>(0)
        })
        .map(Value::String)?;
    result["status"] = if success {
        response["status"].clone()
    } else {
        json!("failed")
    };
    result["reported_status"] = response["status"].clone();
    result["basis"] = json!(basis);
    result["reason"] = response["reason"].clone();
    result["raw_response"] = json!(raw_response);
    result["engine_receipt"] = response["engine_receipt"].clone();
    result["retrieval_receipts"] = response["retrieval_receipts"].clone();
    result["execution_verified"] = json!(success);
    result["execution_state"] = json!(if success { "executed" } else { "failed" });
    result["recorded_at"] = tx
        .query_row("SELECT datetime('now')", [], |r| r.get::<_, String>(0))
        .map(Value::String)?;
    let conditions = result.to_string();
    crate::machine::record_machine_task_in_transaction(
        &tx,
        &crate::machine::MachineTask {
            task_id: running["attempt_id"]
                .as_str()
                .ok_or(Error::Invalid("missing attempt"))?,
            principal: "machine",
            conditions: &conditions,
            knowledge_version: None,
            method_version: Some("document-check/v1"),
            tool_version: Some("python-worker-machine-answer"),
            model_version: if success {
                response["engine_receipt"]["model"]
                    .as_str()
                    .unwrap_or("unknown")
            } else {
                model
            },
            scope: "runtime.document_check",
            outcome: if success { "succeeded" } else { "failed" },
            failure: if success { None } else { reason },
            retest_of: running["retry_of_task_id"].as_str(),
        },
    )?;
    tx.execute("INSERT INTO document_checks(check_id,document_id,version,dimension,receipt_json) VALUES(?1,?2,?3,?4,?5)",params![result["check_id"].as_str(),running["document_id"].as_str(),running["version"].as_i64(),running["dimension"].as_str(),conditions])?;
    tx.commit()?;
    Ok(result)
}

pub fn failed_check_response(running: &Value, reason: &str) -> Value {
    let mut result = running.clone();
    result["schema"] = json!("archeaxis.document-check.response/v1");
    result["outcome"] = json!("failed");
    result["status"] = json!("failed");
    result["reason"] = json!(reason);
    result["basis"] = json!("");
    result["raw_response"] = json!("");
    result["engine_receipt"] = Value::Null;
    result["retrieval_receipts"] = json!([]);
    result
}

/// A restart records interrupted attempts as failures; it never repeats a paid call.
pub fn recover_interrupted_checks(conn: &mut Connection) -> Result<(), Error> {
    let running: Vec<Value> = {
        let mut stmt=conn.prepare("SELECT c.receipt_json FROM document_checks c WHERE json_extract(c.receipt_json,'$.execution_state')='running' AND NOT EXISTS(SELECT 1 FROM document_checks t WHERE json_extract(t.receipt_json,'$.attempt_id')=json_extract(c.receipt_json,'$.attempt_id') AND json_extract(t.receipt_json,'$.execution_state')!='running')")?;
        stmt.query_map([], |r| r.get::<_, String>(0))?
            .collect::<Result<Vec<_>, _>>()?
            .into_iter()
            .map(|v| {
                serde_json::from_str(&v).map_err(|_| Error::Invalid("invalid interrupted check"))
            })
            .collect::<Result<Vec<_>, _>>()?
    };
    for attempt in running {
        let response = failed_check_response(&attempt, "process_interrupted");
        finish_check(
            conn,
            &attempt,
            &response,
            "not_configured",
            "not_configured",
        )?;
    }
    Ok(())
}

#[cfg(test)]
mod cloud_execution_tests {
    use super::*;
    fn setup() -> Connection {
        let c = Connection::open_in_memory().unwrap();
        c.execute_batch("CREATE TABLE documents(document_id TEXT PRIMARY KEY,source_id TEXT,source_revision TEXT,title TEXT,current_version INTEGER);
            CREATE TABLE document_versions(document_id TEXT,version INTEGER,editor_json TEXT,text_projection TEXT,content_sha256 TEXT,revision_basis TEXT);
            CREATE TABLE document_blocks(document_id TEXT,version INTEGER,block_id TEXT,kind TEXT,ordinal INTEGER,node_json TEXT,text_projection TEXT,codec_status TEXT);
            CREATE TABLE document_checks(check_id TEXT PRIMARY KEY,document_id TEXT,version INTEGER,dimension TEXT,receipt_json TEXT);
            INSERT INTO documents VALUES('d',NULL,NULL,'ordinary',2);
            INSERT INTO document_versions VALUES('d',1,'{}','old','old-sha',NULL);
            INSERT INTO document_versions VALUES('d',2,'{}','new','new-sha',NULL);").unwrap();
        let value = json!({"check_id":"request","document_id":"d","version":1,"content_sha256":"old-sha","dimension":"professional_basis","provider_mode":"cloud","status":"pending"});
        c.execute(
            "INSERT INTO document_checks VALUES('request','d',1,'professional_basis',?1)",
            [value.to_string()],
        )
        .unwrap();
        c
    }
    #[test]
    fn append_only_attempt_binds_version_and_explicit_retry() {
        let mut c = setup();
        let a = begin_check(&mut c, "d", "request", "old-sha", None).unwrap();
        assert!(begin_check(&mut c, "d", "request", "old-sha", None).is_err());
        let response = failed_check_response(&a.running, "provider_call_failed");
        let terminal =
            finish_check(&mut c, &a.running, &response, "explicit", "explicit/model").unwrap();
        assert_eq!(terminal["status"], "failed");
        assert_eq!(terminal["execution_verified"], false);
        assert!(finish_check(&mut c, &a.running, &response, "explicit", "explicit/model").is_err());
        let persisted: String = c
            .query_row(
                "SELECT receipt_json FROM document_checks WHERE check_id=?1",
                [a.running["check_id"].as_str()],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(
            serde_json::from_str::<Value>(&persisted).unwrap(),
            a.running
        );
        assert!(begin_check(&mut c, "d", "request", "old-sha", Some("foreign")).is_err());
        let retry = begin_check(
            &mut c,
            "d",
            "request",
            "old-sha",
            terminal["attempt_id"].as_str(),
        )
        .unwrap();
        assert_ne!(retry.running["attempt_id"], terminal["attempt_id"]);
        assert_eq!(read(&c, "d", None).unwrap()["content_sha256"], "new-sha");
    }
    #[test]
    fn identity_or_engine_mismatch_has_no_partial_terminal() {
        let mut c = setup();
        let a = begin_check(&mut c, "d", "request", "old-sha", None).unwrap();
        let mut response = failed_check_response(&a.running, "provider_call_failed");
        response["document_id"] = json!("foreign");
        assert!(finish_check(&mut c, &a.running, &response, "explicit", "explicit/model").is_err());
        let count: i64 = c
            .query_row("SELECT count(*) FROM document_checks", [], |r| r.get(0))
            .unwrap();
        assert_eq!(count, 2);
        response["document_id"] = json!("d");
        response["outcome"] = json!("succeeded");
        response["status"] = json!("supported");
        assert!(finish_check(&mut c, &a.running, &response, "explicit", "explicit/model").is_err());
        let count: i64 = c
            .query_row("SELECT count(*) FROM document_checks", [], |r| r.get(0))
            .unwrap();
        assert_eq!(count, 2);
    }
    #[test]
    fn terminal_and_machine_receipt_roll_back_together() {
        let mut c = setup();
        let a = begin_check(&mut c, "d", "request", "old-sha", None).unwrap();
        c.execute_batch("CREATE TRIGGER fail_terminal BEFORE INSERT ON document_checks WHEN json_extract(NEW.receipt_json,'$.execution_state')='failed' BEGIN SELECT RAISE(ABORT,'injected terminal failure'); END;").unwrap();
        let response = failed_check_response(&a.running, "provider_call_failed");
        assert!(finish_check(&mut c, &a.running, &response, "explicit", "explicit/model").is_err());
        let exists: bool = c
            .query_row(
                "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE name='machine_tasks')",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert!(!exists);
        let count: i64 = c
            .query_row("SELECT count(*) FROM document_checks", [], |r| r.get(0))
            .unwrap();
        assert_eq!(count, 2);
    }
    #[test]
    fn restart_recovers_as_failure_and_never_reexecutes() {
        let mut c = setup();
        let a = begin_check(&mut c, "d", "request", "old-sha", None).unwrap();
        recover_interrupted_checks(&mut c).unwrap();
        recover_interrupted_checks(&mut c).unwrap();
        let raw:String=c.query_row("SELECT receipt_json FROM document_checks WHERE json_extract(receipt_json,'$.execution_state')='failed'",[],|r|r.get(0)).unwrap();
        let terminal: Value = serde_json::from_str(&raw).unwrap();
        assert_eq!(terminal["reason"], "process_interrupted");
        assert_eq!(terminal["attempt_id"], a.running["attempt_id"]);
        assert_eq!(terminal["execution_verified"], false);
        assert_eq!(read(&c, "d", None).unwrap()["text_projection"], "new");
    }
    #[test]
    fn professional_terminal_rejects_legacy_and_wrong_dimension_statuses() {
        let mut c = setup();
        let a = begin_check(&mut c, "d", "request", "old-sha", None).unwrap();
        for status in ["passed", "unverified", "original_unclear", "faithful"] {
            let mut response = failed_check_response(&a.running, "fixture");
            response["outcome"] = json!("succeeded");
            response["status"] = json!(status);
            assert!(matches!(
                finish_check(&mut c, &a.running, &response, "explicit", "explicit/model"),
                Err(Error::Invalid("conclusion does not match dimension"))
            ));
        }
        assert_eq!(
            c.query_row("SELECT count(*) FROM document_checks", [], |r| r
                .get::<_, i64>(0))
                .unwrap(),
            2
        );
    }
}
