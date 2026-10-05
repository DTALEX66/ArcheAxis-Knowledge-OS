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
