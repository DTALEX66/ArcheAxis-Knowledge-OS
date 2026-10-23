//! Product configuration only. No secret, agent routing, or network side effects.
use rusqlite::{Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
pub const MAX_REVISION: u64 = 9_007_199_254_740_991;
const MAX_BYTES: usize = 65_536;
const KEY: &str = "product_model_configuration_v1";
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Purpose {
    Answer,
    Retest,
    Material,
    Companion,
    DocumentCheck,
    Embedding,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Lane {
    Fast,
    Deep,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Profile {
    pub endpoint: String,
    pub protocol: String,
    pub model: String,
    pub credential_ref: Option<String>,
    pub max_tokens: u64,
    pub timeout_s: u64,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Binding {
    pub purpose: Purpose,
    pub lane: Lane,
    pub profile_id: String,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Configuration {
    pub workspace_id: String,
    pub restore_epoch: String,
    pub schema: String,
    pub revision: u64,
    pub profiles: BTreeMap<String, Profile>,
    pub bindings: Vec<Binding>,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Resolved {
    pub workspace_id: String,
    pub restore_epoch: String,
    pub schema: String,
    pub configuration_revision: u64,
    pub configuration_sha256: String,
    pub purpose: Purpose,
    pub lane: Lane,
    pub profile_id: String,
    pub profile: Profile,
}
fn invalid() -> rusqlite::Error {
    rusqlite::Error::InvalidParameterName("MODEL_CONFIGURATION_INVALID".into())
}
fn token(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 128
        && s.bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-'))
}
/// Configuration syntax only; the execution adapter must additionally reject non-public DNS results.
fn public_https_endpoint(endpoint: &str) -> bool {
    let Some(rest) = endpoint.strip_prefix("https://") else {
        return false;
    };
    if !rest.is_ascii()
        || rest.bytes().any(|b| {
            b.is_ascii_control()
                || b.is_ascii_whitespace()
                || matches!(b, b'@' | b'?' | b'#' | b'\\' | b'%')
        })
    {
        return false;
    }
    let (authority, path) = rest.split_once('/').unwrap_or((rest, ""));
    let (host, port) = authority
        .split_once(':')
        .map_or((authority, None), |(h, p)| (h, Some(p)));
    if port.is_some_and(|p| p != "443") {
        return false;
    }
    let host = host.to_ascii_lowercase();
    let labels: Vec<_> = host.split('.').collect();
    if labels.len() < 2
        || host.len() > 253
        || labels.iter().any(|s| {
            s.is_empty()
                || s.len() > 63
                || s.starts_with('-')
                || s.ends_with('-')
                || !s.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'-')
        })
    {
        return false;
    }
    let suffix = labels[labels.len() - 1];
    if suffix.len() < 2
        || !suffix.bytes().all(|b| b.is_ascii_alphabetic())
        || matches!(
            suffix,
            "localhost"
                | "local"
                | "internal"
                | "lan"
                | "home"
                | "arpa"
                | "test"
                | "invalid"
                | "example"
                | "onion"
        )
        || matches!(host.as_str(), "example.com" | "example.net" | "example.org")
    {
        return false;
    }
    path.is_empty()
        || path.split('/').all(|segment| {
            !segment.is_empty()
                && segment
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_'))
        })
}
pub fn validate(c: &Configuration) -> rusqlite::Result<()> {
    if c.schema != "archeaxis.model-configuration/v1"
        || c.workspace_id.len() != 32
        || !c
            .workspace_id
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        || !(c.restore_epoch == "initial"
            || (c.restore_epoch.len() == 32
                && c.restore_epoch
                    .bytes()
                    .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))))
        || c.revision > MAX_REVISION
        || c.profiles.len() > 32
        || c.bindings.len() > 12
    {
        return Err(invalid());
    }
    for (id, p) in &c.profiles {
        let cloud = p.protocol == "openai-buffered";
        let endpoint_valid = if cloud {
            public_https_endpoint(&p.endpoint) && p.credential_ref.is_some()
        } else {
            p.endpoint.strip_prefix("http://").is_some_and(|endpoint| {
                let (authority, path) = endpoint.split_once('/').unwrap_or((endpoint, ""));
                let port = authority
                    .strip_prefix("127.0.0.1:")
                    .or_else(|| authority.strip_prefix("[::1]:"));
                port.is_some_and(|p| p.parse::<u16>().ok().is_some_and(|v| v > 0))
                    && matches!(path, "" | "v1")
                    && matches!(p.protocol.as_str(), "ollama" | "openai")
            })
        };
        if !token(id)
            || p.endpoint.len() > 256
            || p.endpoint.ends_with('/')
            || !endpoint_valid
            || p.model.trim() != p.model
            || p.model.is_empty()
            || p.model.len() > 256
            || p.model.chars().any(char::is_control)
            || !(128..=4096).contains(&p.max_tokens)
            || !(1..=if cloud { 60 } else { 120 }).contains(&p.timeout_s)
            || p.credential_ref.as_ref().is_some_and(|r| {
                !r.strip_prefix("aak_cred_").is_some_and(|s| {
                    s.len() == 32
                        && s.bytes()
                            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
                })
            })
        {
            return Err(invalid());
        }
    }
    for (i, b) in c.bindings.iter().enumerate() {
        if c.profiles
            .get(&b.profile_id)
            .is_some_and(|p| p.protocol == "openai-buffered" && b.purpose != Purpose::Material)
            || !c.profiles.contains_key(&b.profile_id)
            || c.bindings[..i]
                .iter()
                .any(|v| v.purpose == b.purpose && v.lane == b.lane)
        {
            return Err(invalid());
        }
    }
    Ok(())
}
/// Read on the serialized Store connection without lazily creating workspace identity.
pub fn read_only(conn: &Connection) -> rusqlite::Result<Configuration> {
    crate::ui_state::existing_workspace_id(conn)
        .map_err(|_| invalid())?
        .ok_or_else(invalid)?;
    read(conn)
}
pub fn read(conn: &Connection) -> rusqlite::Result<Configuration> {
    let size: Option<i64> = conn
        .query_row(
            "SELECT length(CAST(value AS BLOB)) FROM workspace_meta WHERE key=?1",
            [KEY],
            |r| r.get(0),
        )
        .optional()?;
    if size.is_some_and(|n| n > MAX_BYTES as i64) {
        return Err(invalid());
    }
    let raw: Option<String> = conn
        .query_row(
            "SELECT value FROM workspace_meta WHERE key=?1",
            [KEY],
            |r| r.get(0),
        )
        .optional()?;
    let mut c = match raw {
        Some(raw) => {
            if raw.len() > MAX_BYTES {
                return Err(invalid());
            }
            serde_json::from_str(&raw).map_err(|_| invalid())?
        }
        None => Configuration {
            workspace_id: crate::ui_state::workspace_id(conn).map_err(|_| invalid())?,
            restore_epoch: crate::ui_state::machine_execution_epoch(conn).map_err(|_| invalid())?,
            schema: "archeaxis.model-configuration/v1".into(),
            revision: 0,
            profiles: BTreeMap::new(),
            bindings: vec![],
        },
    };
    validate(&c)?;
    c.workspace_id = crate::ui_state::workspace_id(conn).map_err(|_| invalid())?;
    c.restore_epoch = crate::ui_state::machine_execution_epoch(conn).map_err(|_| invalid())?;
    Ok(c)
}
pub fn put(
    conn: &mut Connection,
    expected: u64,
    mut next: Configuration,
) -> rusqlite::Result<Configuration> {
    validate(&next)?;
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let old = read(&tx)?;
    if old.revision != expected
        || next.revision != expected
        || next.workspace_id != old.workspace_id
        || next.restore_epoch != old.restore_epoch
    {
        return Err(rusqlite::Error::InvalidParameterName(
            "MODEL_CONFIGURATION_CONFLICT".into(),
        ));
    }
    // Embedding identities cannot change without a separately accepted index migration.
    for b in old
        .bindings
        .iter()
        .filter(|b| b.purpose == Purpose::Embedding)
    {
        if !next.bindings.contains(b)
            || old.profiles.get(&b.profile_id) != next.profiles.get(&b.profile_id)
        {
            return Err(rusqlite::Error::InvalidParameterName(
                "NEEDS_INDEX_REBUILD".into(),
            ));
        }
    }
    if expected >= MAX_REVISION {
        return Err(invalid());
    }
    next.revision = expected + 1;
    let raw = serde_json::to_string(&next).map_err(|_| invalid())?;
    if raw.len() > MAX_BYTES {
        return Err(invalid());
    }
    tx.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value",rusqlite::params![KEY,raw])?;
    tx.commit()?;
    Ok(next)
}
pub fn resolve(conn: &Connection, purpose: Purpose, lane: Lane) -> rusqlite::Result<Resolved> {
    let c = read(conn)?;
    let b = c
        .bindings
        .iter()
        .find(|b| b.purpose == purpose && b.lane == lane)
        .ok_or_else(|| rusqlite::Error::InvalidParameterName("MODEL_PURPOSE_UNBOUND".into()))?;
    Ok(Resolved {
        workspace_id: c.workspace_id.clone(),
        restore_epoch: c.restore_epoch.clone(),
        schema: "archeaxis.resolved-model/v1".into(),
        configuration_revision: c.revision,
        configuration_sha256: hex::encode(Sha256::digest(
            serde_json::to_vec(&c).map_err(|_| invalid())?,
        )),
        purpose,
        lane,
        profile_id: b.profile_id.clone(),
        profile: c.profiles[&b.profile_id].clone(),
    })
}
pub fn assert_current(conn: &Connection, r: &Resolved) -> rusqlite::Result<()> {
    if resolve(conn, r.purpose.clone(), r.lane.clone())? != *r {
        return Err(rusqlite::Error::InvalidParameterName(
            "MODEL_CONFIGURATION_CHANGED".into(),
        ));
    }
    Ok(())
}
