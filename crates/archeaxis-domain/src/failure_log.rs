//! Bounded metadata-only problem history. Independent of draft CAS and payloads.
use crate::ui_state;
use archeaxis_store_sqlite::authorization_fence;
use rusqlite::{Connection, OptionalExtension, TransactionBehavior};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

pub const KEY: &str = "operation_failure_log_v1";
const SCHEMA: &str = "archeaxis.operation-failure-log/v1";
const MAX_BYTES: usize = 65_536;
const LIMIT: usize = 50;

#[derive(Debug)]
pub enum Error {
    Invalid,
    ScopeChanged,
    GenerationChanged,
    Corrupt,
    Store(rusqlite::Error),
}
impl From<rusqlite::Error> for Error {
    fn from(e: rusqlite::Error) -> Self {
        Self::Store(e)
    }
}

macro_rules! finite {
    ($name:ident { $($value:ident),+ $(,)? }) => {
        #[derive(Clone, Debug, PartialEq, Eq, Deserialize, Serialize)]
        #[serde(rename_all="snake_case")]
        pub enum $name { $($value),+ }
    };
}
finite!(Operation {
    SourcesList,
    SourceGet,
    SourceOriginal,
    DocumentsList,
    DocumentGet,
    DocumentCreate,
    DocumentDraft,
    DocumentRestore,
    Search,
    LearningItems,
    LearningState,
    LearningReview,
    MachineAnswer,
    MachineRetest,
    MachineTasksList,
    JobExecute,
    JobExecutionStatus,
    JobExecutionCancel,
    ModelConfigurationGet,
    ModelConfigurationPut,
    WorkspaceBackups,
    UiStateRead,
    UiStateWrite,
    LocalRequest,
    LocalWrite,
    UnknownOperation
});
finite!(Code {
    Offline,
    BackendStarting,
    Migrating,
    Incompatible,
    Unauthorized,
    Unavailable,
    Unknown
});
finite!(Reason {
    UnknownResult,
    Offline,
    Starting,
    Migrating,
    Conflict,
    Permission,
    Missing,
    Busy,
    Incompatible,
    NotAdmitted,
    RestoredAuthorization,
    Withheld,
    ModelUnconfirmed
});

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Scope {
    pub workspace_id: String,
    pub restore_epoch: String,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Append {
    pub workspace_id: String,
    pub restore_epoch: String,
    pub log_generation: String,
    pub operation: Operation,
    pub status: Option<u16>,
    pub code: Code,
    pub reason: Reason,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Clear {
    pub workspace_id: String,
    pub restore_epoch: String,
    pub log_generation: Option<String>,
}
#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Entry {
    entry_id: String,
    operation: Operation,
    status: Option<u16>,
    code: Code,
    reason: Reason,
    restore_epoch: String,
    first_at: String,
    at: String,
    count: u32,
}
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Stored {
    schema: String,
    workspace_id: String,
    log_generation: String,
    entries: Vec<Entry>,
}

fn hex32(value: &str) -> bool {
    value.len() == 32
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
fn valid_epoch(value: &str) -> bool {
    value == "initial" || hex32(value)
}
fn timestamp(value: &str) -> bool {
    value.len() == 24
        && value.bytes().enumerate().all(|(i, b)| match i {
            4 | 7 => b == b'-',
            10 => b == b'T',
            13 | 16 => b == b':',
            19 => b == b'.',
            23 => b == b'Z',
            _ => b.is_ascii_digit(),
        })
}
fn nonce(conn: &Connection) -> Result<String, Error> {
    Ok(conn.query_row("SELECT lower(hex(randomblob(16)))", [], |r| r.get(0))?)
}
fn scope(conn: &Connection, id: &str, epoch: &str) -> Result<(), Error> {
    if !hex32(id) || !valid_epoch(epoch) {
        return Err(Error::Invalid);
    }
    let actual = ui_state::existing_workspace_id(conn).map_err(|_| Error::ScopeChanged)?;
    let actual_epoch =
        authorization_fence::authorization_epoch(conn)?.unwrap_or_else(|| "initial".into());
    if actual.as_deref() != Some(id) || actual_epoch != epoch {
        return Err(Error::ScopeChanged);
    }
    Ok(())
}
fn load(conn: &Connection, id: &str) -> Result<Option<Stored>, Error> {
    // Bound bytes transferred into Rust before allocating/deserializing a value.
    // This does not claim a bound on SQLite's internal C allocations or RSS.
    let raw: Option<Vec<u8>> = conn
        .query_row(
            "SELECT substr(CAST(value AS BLOB),1,?2) FROM workspace_meta WHERE key=?1",
            rusqlite::params![KEY, (MAX_BYTES + 1) as i64],
            |r| r.get(0),
        )
        .optional()?;
    let Some(raw) = raw else { return Ok(None) };
    if raw.len() > MAX_BYTES {
        return Err(Error::Corrupt);
    }
    let value: Stored = serde_json::from_slice(&raw).map_err(|_| Error::Corrupt)?;
    if value.schema != SCHEMA
        || value.workspace_id != id
        || !hex32(&value.log_generation)
        || value.entries.len() > LIMIT
        || value.entries.iter().any(|e| {
            !hex32(&e.entry_id)
                || !valid_epoch(&e.restore_epoch)
                || !timestamp(&e.first_at)
                || !timestamp(&e.at)
                || e.count == 0
                || e.count > 1_000_000
                || e.status.is_some_and(|s| s > 599)
        })
    {
        return Err(Error::Corrupt);
    }
    Ok(Some(value))
}
fn fresh(conn: &Connection, id: &str) -> Result<Stored, Error> {
    Ok(Stored {
        schema: SCHEMA.into(),
        workspace_id: id.into(),
        log_generation: nonce(conn)?,
        entries: vec![],
    })
}
fn save(conn: &Connection, value: &Stored) -> Result<(), Error> {
    let raw = serde_json::to_string(value).map_err(|_| Error::Invalid)?;
    if raw.len() > MAX_BYTES {
        return Err(Error::Invalid);
    }
    conn.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value", rusqlite::params![KEY,raw])?;
    Ok(())
}
fn snapshot(value: &Stored, epoch: &str) -> Value {
    json!({"schema":SCHEMA,"workspace_id":value.workspace_id,"restore_epoch":epoch,
        "log_generation":value.log_generation,"entries":value.entries,"corrupt":false,"limit":50})
}
pub fn read(conn: &mut Connection, input: Scope) -> Result<Value, Error> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    scope(&tx, &input.workspace_id, &input.restore_epoch)?;
    let value = match load(&tx, &input.workspace_id) {
        Ok(Some(value)) => snapshot(&value, &input.restore_epoch),
        Ok(None) => {
            let value = fresh(&tx, &input.workspace_id)?;
            save(&tx, &value)?;
            snapshot(&value, &input.restore_epoch)
        }
        Err(Error::Corrupt) => {
            json!({"schema":SCHEMA,"workspace_id":input.workspace_id,"restore_epoch":input.restore_epoch,"log_generation":null,"entries":[],"corrupt":true,"limit":50})
        }
        Err(error) => return Err(error),
    };
    tx.commit()?;
    Ok(value)
}
pub fn append(conn: &mut Connection, input: Append) -> Result<Value, Error> {
    if input.status.is_some_and(|s| s > 599) || !hex32(&input.log_generation) {
        return Err(Error::Invalid);
    }
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    scope(&tx, &input.workspace_id, &input.restore_epoch)?;
    let mut value = load(&tx, &input.workspace_id)?.ok_or(Error::GenerationChanged)?;
    if value.log_generation != input.log_generation {
        return Err(Error::GenerationChanged);
    }
    let now: String = tx.query_row("SELECT strftime('%Y-%m-%dT%H:%M:%fZ','now')", [], |r| {
        r.get(0)
    })?;
    let mut previous = None;
    for (i, e) in value.entries.iter().enumerate() {
        if e.operation == input.operation
            && e.status == input.status
            && e.code == input.code
            && e.reason == input.reason
            && e.restore_epoch == input.restore_epoch
        {
            let age: f64 = tx.query_row(
                "SELECT (julianday(?1)-julianday(?2))*86400.0",
                rusqlite::params![now, e.at],
                |r| r.get(0),
            )?;
            if (0.0..30.0).contains(&age) {
                previous = Some(i);
                break;
            }
        }
    }
    let entry = if let Some(i) = previous {
        let mut old = value.entries.remove(i);
        old.at = now;
        old.count = (old.count + 1).min(1_000_000);
        old
    } else {
        Entry {
            entry_id: nonce(&tx)?,
            operation: input.operation,
            status: input.status,
            code: input.code,
            reason: input.reason,
            restore_epoch: input.restore_epoch.clone(),
            first_at: now.clone(),
            at: now,
            count: 1,
        }
    };
    value.entries.insert(0, entry);
    value.entries.truncate(LIMIT);
    save(&tx, &value)?;
    let result = snapshot(&value, &input.restore_epoch);
    tx.commit()?;
    Ok(result)
}
pub fn clear(conn: &mut Connection, input: Clear) -> Result<Value, Error> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    scope(&tx, &input.workspace_id, &input.restore_epoch)?;
    match load(&tx, &input.workspace_id) {
        Ok(Some(value)) if Some(&value.log_generation) == input.log_generation.as_ref() => (),
        Err(Error::Corrupt) if input.log_generation.is_none() => (),
        Ok(None) if input.log_generation.is_none() => (),
        Err(Error::Store(error)) => return Err(Error::Store(error)),
        _ => return Err(Error::GenerationChanged),
    }
    let value = fresh(&tx, &input.workspace_id)?;
    save(&tx, &value)?;
    let result = snapshot(&value, &input.restore_epoch);
    tx.commit()?;
    Ok(result)
}
