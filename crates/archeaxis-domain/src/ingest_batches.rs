//! Durable folder membership; job execution/results remain owned by jobs.
use rusqlite::{Connection, OptionalExtension, TransactionBehavior, params};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

const EXCLUDED_DIRS: &[&str] = &[
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".project-local",
    ".hermes",
    ".cache",
    "dist",
    "build",
    "target",
];

#[derive(Debug)]
pub enum Error {
    Invalid(&'static str),
    Conflict,
    NotFound,
    Sql(rusqlite::Error),
}
impl From<rusqlite::Error> for Error {
    fn from(value: rusqlite::Error) -> Self {
        Self::Sql(value)
    }
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Member {
    pub ordinal: i64,
    pub relative_path: String,
    pub byte_length: i64,
    pub disposition: String,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Register {
    pub workspace_id: String,
    pub restore_epoch: String,
    pub batch_id: String,
    pub folder_label: String,
    pub expected_members: i64,
    pub members: Vec<Member>,
}
pub fn valid_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, b'-' | b'_'))
}
fn member_disposition(path: &str, bytes: i64) -> Result<&'static str, Error> {
    if path.is_empty()
        || path.len() > 4096
        || bytes < 0
        || path.contains(['\\', ':', '\0'])
        || path.chars().any(char::is_control)
    {
        return Err(Error::Invalid("invalid relative path or byte length"));
    }
    let parts: Vec<_> = path.split('/').collect();
    if parts
        .iter()
        .any(|s| s.is_empty() || matches!(*s, "." | ".."))
    {
        return Err(Error::Invalid("relative path escapes member"));
    }
    let lower: Vec<_> = parts.iter().map(|s| s.to_lowercase()).collect();
    if lower
        .iter()
        .any(|s| [".zcode", ".codex", ".hermes", ".openhuman", ".git"].contains(&s.as_str()))
    {
        return Err(Error::Invalid("private state is not ingest material"));
    }
    if parts.iter().any(|s| s.starts_with('.')) {
        return Ok("excluded_hidden");
    }
    if lower.iter().any(|s| EXCLUDED_DIRS.contains(&s.as_str())) {
        return Ok("excluded_directory");
    }
    Ok(if bytes > 64 * 1024 * 1024 {
        "too_large"
    } else {
        "pending"
    })
}
pub fn identity(conn: &Connection) -> Result<(String, String), Error> {
    Ok((
        crate::ui_state::workspace_id(conn)
            .map_err(|_| Error::Invalid("workspace identity unavailable"))?,
        crate::ui_state::machine_execution_epoch(conn)
            .map_err(|_| Error::Invalid("restore epoch unavailable"))?,
    ))
}
pub fn guard(conn: &Connection, workspace: &str, epoch: &str) -> Result<(), Error> {
    let current = identity(conn)?;
    if current.0 != workspace || current.1 != epoch {
        return Err(Error::Conflict);
    }
    Ok(())
}
pub struct StoredMember {
    pub path: String,
    pub byte_length: i64,
    pub source_id: Option<String>,
    pub revision: Option<String>,
    pub job_id: Option<String>,
}
/// Reject unfinished manifests before publishing any bytes or scheduling work.
pub fn executable_member(
    conn: &Connection,
    batch: &str,
    ordinal: i64,
) -> Result<StoredMember, Error> {
    if !valid_id(batch) || ordinal < 0 {
        return Err(Error::Invalid("invalid member identity"));
    }
    let header: Option<(String, bool)> = conn
        .query_row(
            "SELECT folder_label,expected_members=(SELECT count(*) FROM ingest_batch_members WHERE batch_id=?1)
         FROM ingest_batches WHERE batch_id=?1",
            [batch],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .optional()?;
    let (folder_label, complete) = header.ok_or(Error::NotFound)?;
    if folder_label.starts_with('.')
        || EXCLUDED_DIRS.contains(&folder_label.to_lowercase().as_str())
    {
        return Err(Error::Invalid(
            "excluded folder root cannot execute members",
        ));
    }
    if !complete {
        return Err(Error::Conflict);
    }
    let member: Option<(StoredMember, String)> = conn
        .query_row(
            "SELECT relative_path,byte_length,source_id,source_revision,job_id,disposition
         FROM ingest_batch_members WHERE batch_id=?1 AND ordinal=?2",
            params![batch, ordinal],
            |r| {
                Ok((
                    StoredMember {
                        path: r.get(0)?,
                        byte_length: r.get(1)?,
                        source_id: r.get(2)?,
                        revision: r.get(3)?,
                        job_id: r.get(4)?,
                    },
                    r.get(5)?,
                ))
            },
        )
        .optional()?;
    let (member, disposition) = member.ok_or(Error::NotFound)?;
    if disposition != "pending" {
        return Err(Error::Invalid("excluded member cannot execute"));
    }
    Ok(member)
}
pub fn register(conn: &mut Connection, request: Register) -> Result<Value, Error> {
    if !valid_id(&request.batch_id)
        || !(1..=10000).contains(&request.expected_members)
        || request.members.is_empty()
        || request.members.len() > 200
        || request.folder_label.trim().is_empty()
        || request.folder_label.len() > 1024
        || request.folder_label.contains(['/', '\\', ':', '\0'])
        || request.folder_label.chars().any(char::is_control)
    {
        return Err(Error::Invalid("invalid batch manifest"));
    }
    if [".zcode", ".codex", ".hermes", ".openhuman", ".git"]
        .contains(&request.folder_label.to_lowercase().as_str())
    {
        return Err(Error::Invalid("private folder is not ingest material"));
    }
    if request.folder_label.starts_with('.')
        || EXCLUDED_DIRS.contains(&request.folder_label.to_lowercase().as_str())
    {
        return Err(Error::Invalid(
            "excluded folder root is not ingest material",
        ));
    }
    let mut ordinals = std::collections::HashSet::new();
    let mut paths = std::collections::HashSet::new();
    for member in &request.members {
        if !(0..request.expected_members).contains(&member.ordinal)
            || !ordinals.insert(member.ordinal)
            || !paths.insert(&member.relative_path)
            || member_disposition(&member.relative_path, member.byte_length)? != member.disposition
        {
            return Err(Error::Invalid("invalid or duplicate manifest member"));
        }
    }
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    guard(&tx, &request.workspace_id, &request.restore_epoch)?;
    let old: Option<(String, i64)> = tx
        .query_row(
            "SELECT folder_label,expected_members FROM ingest_batches WHERE batch_id=?1",
            [&request.batch_id],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .optional()?;
    if let Some(old) = old {
        if old != (request.folder_label.clone(), request.expected_members) {
            return Err(Error::Conflict);
        }
    } else {
        tx.execute(
            "INSERT INTO ingest_batches(batch_id,folder_label,expected_members) VALUES(?1,?2,?3)",
            params![
                request.batch_id,
                request.folder_label,
                request.expected_members
            ],
        )?;
    }
    for member in request.members {
        let old: Option<(String,i64,String)> = tx.query_row(
            "SELECT relative_path,byte_length,disposition FROM ingest_batch_members WHERE batch_id=?1 AND ordinal=?2",
            params![request.batch_id,member.ordinal],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?))).optional()?;
        if let Some(old) = old {
            if old != (member.relative_path, member.byte_length, member.disposition) {
                return Err(Error::Conflict);
            }
        } else {
            let exists: bool = tx.query_row("SELECT EXISTS(SELECT 1 FROM ingest_batch_members WHERE batch_id=?1 AND relative_path=?2)",
                params![request.batch_id,member.relative_path],|r|r.get(0))?;
            if exists {
                return Err(Error::Conflict);
            }
            tx.execute("INSERT INTO ingest_batch_members(batch_id,ordinal,relative_path,byte_length,disposition) VALUES(?1,?2,?3,?4,?5)",
                params![request.batch_id,member.ordinal,member.relative_path,member.byte_length,member.disposition])?;
        }
    }
    let result = read(&tx, &request.batch_id, None, 200)?;
    tx.commit()?;
    Ok(result)
}
pub fn read(
    conn: &Connection,
    batch: &str,
    after: Option<i64>,
    limit: i64,
) -> Result<Value, Error> {
    if !valid_id(batch) || !(1..=200).contains(&limit) || after.is_some_and(|v| v < 0) {
        return Err(Error::Invalid("invalid batch pagination"));
    }
    let (workspace, epoch) = identity(conn)?;
    let header: Option<(String, i64, String)> = conn
        .query_row(
            "SELECT folder_label,expected_members,created_at FROM ingest_batches WHERE batch_id=?1",
            [batch],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
        )
        .optional()?;
    let (label, expected, created) = header.ok_or(Error::NotFound)?;
    let registered: i64 = conn.query_row(
        "SELECT count(*) FROM ingest_batch_members WHERE batch_id=?1",
        [batch],
        |r| r.get(0),
    )?;
    let mut stmt=conn.prepare("SELECT m.ordinal,m.relative_path,m.byte_length,m.disposition,m.source_id,m.source_revision,m.job_id,j.kind,j.state
        FROM ingest_batch_members m LEFT JOIN jobs j ON j.job_id=m.job_id
        WHERE m.batch_id=?1 AND m.ordinal>?2 ORDER BY m.ordinal LIMIT ?3")?;
    let mut members=stmt.query_map(params![batch,after.unwrap_or(-1),limit+1],|r|Ok(json!({
        "ordinal":r.get::<_,i64>(0)?,"relative_path":r.get::<_,String>(1)?,"byte_length":r.get::<_,i64>(2)?,
        "disposition":r.get::<_,String>(3)?,"source_id":r.get::<_,Option<String>>(4)?,
        "source_revision":r.get::<_,Option<String>>(5)?,"job_id":r.get::<_,Option<String>>(6)?,
        "kind":r.get::<_,Option<String>>(7)?,"job_state":r.get::<_,Option<String>>(8)?
    })))?.collect::<Result<Vec<_>,_>>()?;
    let next = if members.len() > limit as usize {
        members.pop();
        members.last().map(|v| v["ordinal"].clone())
    } else {
        None
    };
    Ok(
        json!({"schema":"archeaxis.ingest-batch/v1","workspace_id":workspace,"restore_epoch":epoch,
        "batch_id":batch,"folder_label":label,"expected_members":expected,"registered_members":registered,
        "complete":registered==expected,"created_at":created,"members":members,"next_ordinal":next}),
    )
}
pub fn list(conn: &Connection, cursor: Option<&str>, limit: i64) -> Result<Value, Error> {
    if !(1..=200).contains(&limit) || cursor.is_some_and(|v| !valid_id(v)) {
        return Err(Error::Invalid("invalid batch cursor"));
    }
    let (workspace, epoch) = identity(conn)?;
    let mut stmt = conn.prepare(
        "SELECT b.batch_id,b.folder_label,b.expected_members,b.created_at,count(m.ordinal)
        FROM ingest_batches b LEFT JOIN ingest_batch_members m ON m.batch_id=b.batch_id
        WHERE b.batch_id>?1 GROUP BY b.batch_id ORDER BY b.batch_id LIMIT ?2",
    )?;
    let mut batches=stmt.query_map(params![cursor.unwrap_or(""),limit+1],|r|{
        let expected:i64=r.get(2)?;let registered:i64=r.get(4)?;
        Ok(json!({"batch_id":r.get::<_,String>(0)?,"folder_label":r.get::<_,String>(1)?,
            "expected_members":expected,"registered_members":registered,"complete":expected==registered,"created_at":r.get::<_,String>(3)?}))
    })?.collect::<Result<Vec<_>,_>>()?;
    let next = if batches.len() > limit as usize {
        batches.pop();
        batches.last().map(|v| v["batch_id"].clone())
    } else {
        None
    };
    Ok(
        json!({"schema":"archeaxis.ingest-batches/v1","workspace_id":workspace,"restore_epoch":epoch,"batches":batches,"next_cursor":next}),
    )
}
