//! Supervisor<->Core sidecar protocol (v0.1 closed-loop step 1).
//!
//! The desktop Supervisor (future Avalonia shell) launches the Rust Core and
//! completes a handshake over this message envelope before any work starts.
//! Python workers never speak this protocol directly to the database — they
//! talk to the Core HTTP API and the Core relays receipts here.

use serde::{Deserialize, Serialize};

pub const PROTOCOL_VERSION: u32 = 1;

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq, Eq)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Message {
    Ping {
        nonce: String,
    },
    Handshake {
        runtime: String,
        contract: String,
        schema_version: i64,
        workspace_ready: bool,
    },
    Health {
        ok: bool,
        detail: Option<String>,
    },
    Shutdown {
        reason: Option<String>,
    },
    WorkerReceipt {
        job_id: String,
        state: String,
        engine: Option<String>,
        loss_receipt: Option<serde_json::Value>,
    },
}

/// Versioned envelope carrying one message.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct Envelope {
    pub version: u32,
    pub message: Message,
}

pub fn encode(message: Message) -> Result<String, serde_json::Error> {
    let env = Envelope {
        version: PROTOCOL_VERSION,
        message,
    };
    serde_json::to_string(&env)
}

/// Decode + version-check an envelope (mismatched version is a hard error).
pub fn decode(line: &str) -> Result<Envelope, ProtocolError> {
    let env: Envelope = serde_json::from_str(line).map_err(ProtocolError::Malformed)?;
    if env.version != PROTOCOL_VERSION {
        return Err(ProtocolError::VersionMismatch {
            expected: PROTOCOL_VERSION,
            got: env.version,
        });
    }
    Ok(env)
}

#[derive(Debug)]
pub enum ProtocolError {
    Malformed(serde_json::Error),
    VersionMismatch { expected: u32, got: u32 },
}

impl std::fmt::Display for ProtocolError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ProtocolError::Malformed(e) => write!(f, "malformed envelope: {e}"),
            ProtocolError::VersionMismatch { expected, got } => {
                write!(
                    f,
                    "protocol version mismatch: expected {expected}, got {got}"
                )
            }
        }
    }
}
