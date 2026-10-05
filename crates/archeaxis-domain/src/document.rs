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
    let header: Option<(String,String,String,i64)> = conn.query_row(
        "SELECT source_id,source_revision,title,current_version FROM documents WHERE document_id=?1",[id],
        |r| Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?))).optional()?;
    let (source_id, source_revision, title, current) = header.ok_or(Error::NotFound)?;
    let version = requested.unwrap_or(current);
    let snapshot: Option<(String,String,String)> = conn.query_row(
        "SELECT editor_json,text_projection,content_sha256 FROM document_versions WHERE document_id=?1 AND version=?2",
        params![id,version],|r| Ok((r.get(0)?,r.get(1)?,r.get(2)?))).optional()?;
    let (editor, projection, digest) = snapshot.ok_or(Error::NotFound)?;
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
        "text_projection":projection,"content_sha256":digest,"blocks":blocks}),
    )
}

fn append(
    tx: &rusqlite::Transaction<'_>,
    id: &str,
    expected: i64,
    editor: Value,
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
    tx.execute("INSERT INTO document_versions(document_id,version,editor_json,text_projection,content_sha256) VALUES(?1,?2,?3,?4,?5)",params![id,version,encoded,projection,digest])?;
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
    if title.len() > 1024 {
        return Err(Error::Invalid("title exceeds limit"));
    }
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
    let id: String = conn.query_row("SELECT 'doc_' || lower(hex(randomblob(16)))", [], |r| {
        r.get(0)
    })?;
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    tx.execute("INSERT INTO documents(document_id,source_id,source_revision,title,current_version) VALUES(?1,?2,?3,?4,0)",params![id,source_id,revision,title])?;
    append(&tx, &id, 0, editor)?;
    tx.commit()?;
    read(conn, &id, None)
}

pub fn save(conn: &mut Connection, id: &str, expected: i64, editor: Value) -> Result<Value, Error> {
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    append(&tx, id, expected, editor)?;
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
        .query_map([], |r| Ok(json!({"document_id":r.get::<_,String>(0)?,"source_id":r.get::<_,String>(1)?,"source_revision":r.get::<_,String>(2)?,"title":r.get::<_,String>(3)?,"version":r.get::<_,i64>(4)?,"content_sha256":r.get::<_,String>(5)?})))?
        .collect::<Result<Vec<_>, _>>()?;
    Ok(summaries)
}
