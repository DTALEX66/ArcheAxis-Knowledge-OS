//! Core-owned recoverable UI working state, separate from committed Document versions.
//! Existing workspace_meta participates in both archive and Online Backup; no new schema/DB.
use rusqlite::{Connection, OptionalExtension, TransactionBehavior};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashSet};

const ID_KEY: &str = "ui_workspace_identity_v1";
const STATE_KEY: &str = "ui_working_state_v1";
const MAX_BYTES: usize = 1_048_576;
const BASIS: &str = "archeaxis.ui-working-state/v1";

#[derive(Debug)]
pub enum Error {
    Invalid(&'static str),
    Conflict,
    Store(rusqlite::Error),
}
impl From<rusqlite::Error> for Error {
    fn from(e: rusqlite::Error) -> Self {
        Self::Store(e)
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Draft {
    pub base_version: i64,
    pub editor_json: Value,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct OriginalAttempt {
    pub create_request_id: String,
    pub title: String,
    pub editor_json: Value,
}
#[derive(Clone, Debug, Default, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct State {
    pub drafts: BTreeMap<String, Draft>,
    pub opened_documents: Vec<String>,
    pub active_document: Option<String>,
    pub page_id: Option<String>,
    #[serde(default)]
    pub pending_original: Option<OriginalAttempt>,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Write {
    pub workspace_id: String,
    pub restore_epoch: String,
    pub state_revision: i64,
    pub state: State,
}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ClearSaved {
    pub workspace_id: String,
    pub restore_epoch: String,
    pub state_revision: i64,
    pub document_id: String,
    pub base_version: i64,
    pub content_sha256: String,
    pub saved_version: i64,
}
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Stored {
    schema: String,
    workspace_id: String,
    restore_epoch: String,
    state_revision: i64,
    state: State,
}
fn identity(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 128
        && id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
}
fn hex32(s: &str) -> bool {
    s.len() == 32
        && s.bytes()
            .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
}
fn meta(conn: &Connection, key: &str) -> Result<Option<String>, Error> {
    Ok(conn
        .query_row(
            "SELECT value FROM workspace_meta WHERE key=?1",
            [key],
            |r| r.get(0),
        )
        .optional()?)
}
fn workspace_id(conn: &Connection) -> Result<String, Error> {
    if let Some(id) = meta(conn, ID_KEY)? {
        if !hex32(&id) {
            return Err(Error::Invalid("corrupt UI workspace identity"));
        }
        return Ok(id);
    }
    conn.execute(
        "INSERT INTO workspace_meta(key,value) VALUES(?1,lower(hex(randomblob(16))))",
        [ID_KEY],
    )?;
    meta(conn, ID_KEY)?.ok_or(Error::Invalid("workspace identity missing"))
}
fn epoch(conn: &Connection) -> Result<String, Error> {
    match meta(conn, archeaxis_store_sqlite::authorization_fence::KEY)? {
        None => Ok("initial".into()),
        Some(raw) => {
            let value: Value =
                serde_json::from_str(&raw).map_err(|_| Error::Invalid("corrupt restore fence"))?;
            let epoch = value["epoch"]
                .as_str()
                .ok_or(Error::Invalid("restore epoch missing"))?;
            if value["schema"] != archeaxis_store_sqlite::authorization_fence::SCHEMA
                || !hex32(epoch)
                || !value["blocked_grant_ids"].as_array().is_some_and(|items| {
                    items
                        .iter()
                        .all(|item| item.as_str().is_some_and(|s| !s.is_empty()))
                })
            {
                return Err(Error::Invalid("corrupt restore fence"));
            }
            Ok(epoch.into())
        }
    }
}
fn digest(content: &Value) -> String {
    hex::encode(Sha256::digest(
        serde_json::to_vec(content).expect("JSON Value serialization"),
    ))
}
fn validate(state: &State) -> Result<(), Error> {
    if let Some(attempt) = &state.pending_original {
        if !identity(&attempt.create_request_id)
            || attempt.title.len() > 1024
            || attempt.editor_json["type"] != "doc"
            || !attempt.editor_json["content"].is_array()
            || serde_json::to_vec(&attempt.editor_json)
                .map_err(|_| Error::Invalid("invalid original JSON"))?
                .len()
                > 262_144
        {
            return Err(Error::Invalid("invalid pending original request"));
        }
    }
    if state.drafts.len() > 32 || state.opened_documents.len() > 64 {
        return Err(Error::Invalid("UI object limit exceeded"));
    }
    let mut opened = HashSet::new();
    for id in &state.opened_documents {
        if !identity(id) || !opened.insert(id.as_str()) {
            return Err(Error::Invalid("invalid/duplicate opened document"));
        }
    }
    if let Some(id) = &state.active_document {
        if !identity(id) || !opened.contains(id.as_str()) {
            return Err(Error::Invalid("active document must be opened"));
        }
    }
    if let Some(page) = &state.page_id {
        if !matches!(
            page.as_str(),
            "01" | "02"
                | "03"
                | "04"
                | "05"
                | "06"
                | "07"
                | "08"
                | "09"
                | "10"
                | "11"
                | "12"
                | "13"
                | "14"
                | "15"
                | "16"
                | "17"
                | "18"
                | "19"
                | "20"
                | "21"
                | "22"
        ) {
            return Err(Error::Invalid("unknown UI page"));
        }
    }
    for (id, draft) in &state.drafts {
        if !identity(id)
            || draft.base_version <= 0
            || draft.editor_json["type"] != "doc"
            || !draft.editor_json["content"].is_array()
        {
            return Err(Error::Invalid("invalid draft"));
        }
        if serde_json::to_vec(&draft.editor_json)
            .map_err(|_| Error::Invalid("invalid JSON"))?
            .len()
            > 262_144
        {
            return Err(Error::Invalid("draft too large"));
        }
    }
    if serde_json::to_vec(state)
        .map_err(|_| Error::Invalid("invalid state JSON"))?
        .len()
        > MAX_BYTES
    {
        return Err(Error::Invalid("state too large"));
    }
    Ok(())
}
fn stored(conn: &Connection, id: &str, restore_epoch: &str) -> Result<Stored, Error> {
    match meta(conn, STATE_KEY)? {
        None => Ok(Stored {
            schema: BASIS.into(),
            workspace_id: id.into(),
            restore_epoch: restore_epoch.into(),
            state_revision: 0,
            state: State::default(),
        }),
        Some(raw) => {
            if raw.len() > MAX_BYTES + 1024 {
                return Err(Error::Invalid("stored UI state too large"));
            }
            let result: Stored =
                serde_json::from_str(&raw).map_err(|_| Error::Invalid("corrupt UI state"))?;
            if result.schema != BASIS
                || result.workspace_id != id
                || result.state_revision < 0
                || result.state_revision > 9_007_199_254_740_991
                || !(result.restore_epoch == "initial" || hex32(&result.restore_epoch))
            {
                return Err(Error::Invalid("corrupt UI state identity"));
            }
            validate(&result.state)?;
            Ok(result)
        }
    }
}
fn response(record: &Stored, current_epoch: &str) -> Value {
    let candidates = record.restore_epoch != current_epoch;
    let state = if candidates {
        State::default()
    } else {
        record.state.clone()
    };
    json!({"schema": BASIS, "workspace_id": record.workspace_id, "restore_epoch": current_epoch,
        "state_revision": record.state_revision, "state": state,
        "pending_document_id": if candidates { None } else { record.state.pending_original.as_ref().map(|a|format!("doc_req_{}",hex::encode(Sha256::digest(a.create_request_id.as_bytes())))) },
        "draft_digests": if candidates { BTreeMap::new() } else { record.state.drafts.iter().map(|(id,d)| (id.clone(),digest(&d.editor_json))).collect::<BTreeMap<_,_>>() },
        "recovery_candidates": if candidates { Some(&record.state) } else { None },
        "recovery_requires_confirmation": candidates})
}
fn next_revision(record: &Stored) -> Result<i64, Error> {
    if record.state_revision >= 9_007_199_254_740_991 {
        return Err(Error::Invalid("UI state revision exhausted"));
    }
    Ok(record.state_revision + 1)
}
fn publish(conn: &Connection, record: &Stored) -> Result<(), Error> {
    conn.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value", rusqlite::params![STATE_KEY,serde_json::to_string(record).map_err(|_|Error::Invalid("invalid state JSON"))?])?;
    Ok(())
}
fn compare(
    record: &Stored,
    id: &str,
    current_epoch: &str,
    request_id: &str,
    request_epoch: &str,
    revision: i64,
) -> Result<(), Error> {
    if request_id != id || request_epoch != current_epoch || revision != record.state_revision {
        return Err(Error::Conflict);
    }
    Ok(())
}
/// Called through Store even though named read: first-use identity initialization is a Core write.
pub fn read(conn: &mut Connection) -> Result<Value, Error> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let id = workspace_id(&tx)?;
    let current_epoch = epoch(&tx)?;
    let record = stored(&tx, &id, &current_epoch)?;
    let result = response(&record, &current_epoch);
    tx.commit()?;
    Ok(result)
}
pub fn write(conn: &mut Connection, request: Write) -> Result<Value, Error> {
    validate(&request.state)?;
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let id = workspace_id(&tx)?;
    let current_epoch = epoch(&tx)?;
    let old = stored(&tx, &id, &current_epoch)?;
    compare(
        &old,
        &id,
        &current_epoch,
        &request.workspace_id,
        &request.restore_epoch,
        request.state_revision,
    )?;
    // After restore, preserve candidate state until an explicit separate recovery decision exists.
    if old.restore_epoch != current_epoch {
        return Err(Error::Conflict);
    }
    if let (Some(old_attempt), Some(new_attempt)) =
        (&old.state.pending_original, &request.state.pending_original)
    {
        if old_attempt != new_attempt {
            return Err(Error::Invalid(
                "pending original request is frozen; resolve or explicitly cancel it first",
            ));
        }
    }
    for id in &request.state.opened_documents {
        if !tx.query_row(
            "SELECT EXISTS(SELECT 1 FROM documents WHERE document_id=?1)",
            [id],
            |r| r.get::<_, bool>(0),
        )? {
            return Err(Error::Invalid("opened document missing"));
        }
    }
    for (id, draft) in &request.state.drafts {
        if !tx.query_row(
            "SELECT EXISTS(SELECT 1 FROM document_versions WHERE document_id=?1 AND version=?2)",
            rusqlite::params![id, draft.base_version],
            |r| r.get::<_, bool>(0),
        )? {
            return Err(Error::Invalid("draft base version missing"));
        }
    }
    let record = Stored {
        schema: BASIS.into(),
        workspace_id: id,
        restore_epoch: current_epoch.clone(),
        state_revision: next_revision(&old)?,
        state: request.state,
    };
    publish(&tx, &record)?;
    let result = response(&record, &current_epoch);
    tx.commit()?;
    Ok(result)
}
pub fn clear_saved(conn: &mut Connection, request: ClearSaved) -> Result<Value, Error> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let id = workspace_id(&tx)?;
    let current_epoch = epoch(&tx)?;
    let mut record = stored(&tx, &id, &current_epoch)?;
    compare(
        &record,
        &id,
        &current_epoch,
        &request.workspace_id,
        &request.restore_epoch,
        request.state_revision,
    )?;
    if record.restore_epoch != current_epoch {
        return Err(Error::Conflict);
    }
    let draft = record
        .state
        .drafts
        .get(&request.document_id)
        .ok_or(Error::Conflict)?;
    if draft.base_version != request.base_version
        || digest(&draft.editor_json) != request.content_sha256
        || request.saved_version != request.base_version.checked_add(1).ok_or(Error::Conflict)?
    {
        return Err(Error::Conflict);
    }
    let raw: Option<String> = tx
        .query_row(
            "SELECT editor_json FROM document_versions WHERE document_id=?1 AND version=?2",
            rusqlite::params![request.document_id, request.saved_version],
            |r| r.get(0),
        )
        .optional()?;
    let saved: Value = serde_json::from_str(&raw.ok_or(Error::Conflict)?)
        .map_err(|_| Error::Invalid("corrupt document version"))?;
    if digest(&saved) != request.content_sha256 {
        return Err(Error::Conflict);
    }
    record.state.drafts.remove(&request.document_id);
    record.state_revision = next_revision(&record)?;
    publish(&tx, &record)?;
    let result = response(&record, &current_epoch);
    tx.commit()?;
    Ok(result)
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RecoveryAction {
    Preserve,
    Discard,
}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Recover {
    pub workspace_id: String,
    pub restore_epoch: String,
    pub state_revision: i64,
    pub action: RecoveryAction,
}
/// Explicit human recovery after preview; never called by read/write/Document ACK.
pub fn recover(conn: &mut Connection, request: Recover) -> Result<Value, Error> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let id = workspace_id(&tx)?;
    let current_epoch = epoch(&tx)?;
    let mut record = stored(&tx, &id, &current_epoch)?;
    compare(
        &record,
        &id,
        &current_epoch,
        &request.workspace_id,
        &request.restore_epoch,
        request.state_revision,
    )?;
    if record.restore_epoch == current_epoch {
        return Err(Error::Conflict);
    }
    match request.action {
        RecoveryAction::Discard => record.state = State::default(),
        RecoveryAction::Preserve => {
            for (id, draft) in &record.state.drafts {
                if !tx.query_row("SELECT EXISTS(SELECT 1 FROM document_versions WHERE document_id=?1 AND version=?2)",rusqlite::params![id,draft.base_version],|r|r.get::<_,bool>(0))? { return Err(Error::Invalid("recovery draft base version missing; candidate retained")); }
            }
            for id in &record.state.opened_documents {
                if !tx.query_row(
                    "SELECT EXISTS(SELECT 1 FROM documents WHERE document_id=?1)",
                    [id],
                    |r| r.get::<_, bool>(0),
                )? {
                    return Err(Error::Invalid(
                        "recovery opened document missing; candidate retained",
                    ));
                }
            }
        }
    }
    record.restore_epoch = current_epoch.clone();
    record.state_revision = next_revision(&record)?;
    publish(&tx, &record)?;
    let result = response(&record, &current_epoch);
    tx.commit()?;
    Ok(result)
}
