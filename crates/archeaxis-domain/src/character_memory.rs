//! Explicitly human-approved product memory. Never imports chat or admits knowledge.
use rusqlite::{Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
const KEY: &str = "character_memory_v1";
const MAX_BYTES: usize = 131_072;
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Memory {
    pub id: String,
    pub text: String,
    pub provenance: String,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Profile {
    pub schema: String,
    pub workspace_id: String,
    pub restore_epoch: String,
    pub revision: u64,
    pub enabled: bool,
    pub preferences: String,
    pub learning_goals: String,
    pub memories: Vec<Memory>,
}
#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "operation", rename_all = "snake_case", deny_unknown_fields)]
pub enum Operation {
    Profile {
        preferences: String,
        learning_goals: String,
    },
    Remember {
        memory: Memory,
    },
    Correct {
        memory: Memory,
    },
    Forget {
        id: String,
    },
    Disable,
    Enable,
    ForgetAll,
}
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Write {
    pub workspace_id: String,
    pub restore_epoch: String,
    pub expected_revision: u64,
    pub command: Operation,
}
fn error(code: &str) -> rusqlite::Error {
    rusqlite::Error::InvalidParameterName(code.into())
}
fn text(s: &str, max: usize) -> bool {
    s.len() <= max && !s.contains('\0')
}
fn identity(conn: &Connection) -> rusqlite::Result<(String, String)> {
    Ok((
        crate::ui_state::workspace_id(conn).map_err(|_| error("MEMORY_IDENTITY_INVALID"))?,
        crate::ui_state::machine_execution_epoch(conn)
            .map_err(|_| error("MEMORY_IDENTITY_INVALID"))?,
    ))
}
fn validate(p: &Profile) -> rusqlite::Result<()> {
    if p.schema != "archeaxis.character-memory/v1"
        || p.revision > crate::model_configuration::MAX_REVISION
        || !text(&p.preferences, 8192)
        || !text(&p.learning_goals, 8192)
        || p.memories.len() > 128
    {
        return Err(error("MEMORY_INVALID"));
    }
    for (i, m) in p.memories.iter().enumerate() {
        if m.id.is_empty()
            || m.id.len() > 128
            || !m
                .id
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-'))
            || m.text.trim().is_empty()
            || !text(&m.text, 4096)
            || m.provenance.trim().is_empty()
            || !text(&m.provenance, 1024)
            || p.memories[..i].iter().any(|v| v.id == m.id)
        {
            return Err(error("MEMORY_INVALID"));
        }
    }
    Ok(())
}
pub fn read(conn: &Connection) -> rusqlite::Result<Profile> {
    let size: Option<i64> = conn
        .query_row(
            "SELECT length(CAST(value AS BLOB)) FROM workspace_meta WHERE key=?1",
            [KEY],
            |r| r.get(0),
        )
        .optional()?;
    if size.is_some_and(|s| s > MAX_BYTES as i64) {
        return Err(error("MEMORY_INVALID"));
    }
    let raw: Option<String> = conn
        .query_row(
            "SELECT value FROM workspace_meta WHERE key=?1",
            [KEY],
            |r| r.get(0),
        )
        .optional()?;
    let (workspace_id, restore_epoch) = identity(conn)?;
    let mut p = match raw {
        Some(raw) => serde_json::from_str(&raw).map_err(|_| error("MEMORY_INVALID"))?,
        None => Profile {
            schema: "archeaxis.character-memory/v1".into(),
            workspace_id: workspace_id.clone(),
            restore_epoch: restore_epoch.clone(),
            revision: 0,
            enabled: false,
            preferences: String::new(),
            learning_goals: String::new(),
            memories: vec![],
        },
    };
    validate(&p)?;
    if p.restore_epoch != restore_epoch {
        p.enabled = false;
    }
    p.workspace_id = workspace_id;
    p.restore_epoch = restore_epoch;
    Ok(p)
}
pub fn apply(conn: &mut Connection, w: Write) -> rusqlite::Result<Value> {
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let mut p = read(&tx)?;
    if p.workspace_id != w.workspace_id
        || p.restore_epoch != w.restore_epoch
        || p.revision != w.expected_revision
    {
        return Err(error("MEMORY_CONFLICT"));
    }
    if p.revision >= crate::model_configuration::MAX_REVISION {
        return Err(error("MEMORY_INVALID"));
    }
    let mut forgotten = vec![];
    match w.command {
        Operation::Profile {
            preferences,
            learning_goals,
        } => {
            p.preferences = preferences;
            p.learning_goals = learning_goals;
        }
        Operation::Remember { memory } => {
            if p.memories.iter().any(|v| v.id == memory.id) {
                return Err(error("MEMORY_ALREADY_EXISTS"));
            }
            p.memories.push(memory);
        }
        Operation::Correct { memory } => {
            let existing = p
                .memories
                .iter_mut()
                .find(|v| v.id == memory.id)
                .ok_or_else(|| error("MEMORY_NOT_FOUND"))?;
            *existing = memory;
        }
        Operation::Forget { id } => {
            if !p.memories.iter().any(|v| v.id == id) {
                return Err(error("MEMORY_NOT_FOUND"));
            }
            p.memories.retain(|v| v.id != id);
            forgotten.push(id);
        }
        Operation::ForgetAll => {
            forgotten = p.memories.iter().map(|v| v.id.clone()).collect();
            p.memories.clear();
        }
        Operation::Disable => p.enabled = false,
        Operation::Enable => p.enabled = true,
    }
    p.revision += 1;
    validate(&p)?;
    let raw = serde_json::to_string(&p).map_err(|_| error("MEMORY_INVALID"))?;
    if raw.len() > MAX_BYTES {
        return Err(error("MEMORY_INVALID"));
    }
    tx.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value",rusqlite::params![KEY,raw])?;
    tx.commit()?;
    Ok(
        json!({"schema":"archeaxis.memory-write/v1","profile":p,"live_store_deleted":!forgotten.is_empty(),"forgotten_ids":forgotten,"historical_chat_modified":false,"backups_modified":false,"secure_erasure":false}),
    )
}
/// Separate style/memory channel. No facts, grants, automatic indexing or secret read.
pub fn context(conn: &Connection) -> rusqlite::Result<Value> {
    let p = read(conn)?;
    Ok(
        json!({"schema":"archeaxis.character-context/v1","workspace_id":p.workspace_id,"restore_epoch":p.restore_epoch,"revision":p.revision,"enabled":p.enabled,"preferences":if p.enabled{p.preferences}else{String::new()},"learning_goals":if p.enabled{p.learning_goals}else{String::new()},"approved_memories":if p.enabled{p.memories}else{vec![]},"authority":"human_preferences_only","grants":[],"knowledge_admitted":false}),
    )
}
/// Execution consumer checks its frozen snapshot, never silently refreshes consent.
pub fn assert_context_current(conn: &Connection, frozen: &Value) -> rusqlite::Result<()> {
    if context(conn)? != *frozen {
        return Err(error("MEMORY_CONTEXT_CHANGED"));
    }
    Ok(())
}
