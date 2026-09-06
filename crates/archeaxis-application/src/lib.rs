//! ArcheAxis vNext application layer.
//!
//! - `bootstrap`: open/init a workspace, runtime identity (supervisor handshake
//!   target for the future Avalonia shell).
//! - `jobs`: worker job orchestration — enqueue, complete with a loss receipt,
//!   fail explicitly. `attempts` and `executor` run the new text NDJSON path;
//!   the Python child never opens the database. Old HTTP receipts are compatibility.

use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

pub mod jobs;
pub mod attempts;
pub mod executor;

pub const RUNTIME_NAME: &str = "archeaxis-application";
pub const CONTRACT_VERSION: &str = "0.1.0-outline";

/// Runtime identity returned to a Supervisor handshake.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct Handshake {
    pub runtime: String,
    pub contract: String,
    pub schema_version: i64,
    pub workspace_ready: bool,
}

/// Open (or create) the workspace and build the handshake identity.
pub fn bootstrap(db_path: &str) -> rusqlite::Result<(Connection, Handshake)> {
    let conn = archeaxis_store_sqlite::init_workspace(db_path)?;
    let handshake = Handshake {
        runtime: RUNTIME_NAME.to_string(),
        contract: CONTRACT_VERSION.to_string(),
        schema_version: archeaxis_store_sqlite::SCHEMA_VERSION,
        workspace_ready: true,
    };
    Ok((conn, handshake))
}

fn stable_id(prefix: &str, seed: &str) -> String {
    let mut h = Sha256::new();
    h.update(seed.as_bytes());
    format!("{prefix}_{}", &hex::encode(h.finalize())[..24])
}
