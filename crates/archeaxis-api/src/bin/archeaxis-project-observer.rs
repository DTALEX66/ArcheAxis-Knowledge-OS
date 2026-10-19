//! 明确授权的只读适配器消费者；连接资料仅 stdin，stdout 只输出有限 metadata DTO。
use archeaxis_api::project_handoff::{prepare, prepare_receipt};
use archeaxis_api::project_observer::client::{ClientAdmission, ObserverClient, ReadError};
use archeaxis_contracts::{
    project_handoff::{Handoff, Payload, PrepareError, ReceiptReason, ReceiptState},
    project_observer::ObjectReference,
};
use serde::Deserialize;
use std::io::Read;
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    admission: ClientAdmission,
    action: Action,
}
#[derive(Deserialize)]
#[serde(tag = "operation", rename_all = "snake_case", deny_unknown_fields)]
enum Action {
    Handshake,
    Objects,
    Status {
        reference: ObjectReference,
    },
    PrepareHandoff {
        key: String,
        payload: Payload,
    },
    PrepareReceipt {
        key: String,
        original: Handoff,
        state: ReceiptState,
        reason: ReceiptReason,
    },
}
// 不回显输入、token、引用正文或内部错误；新准备错误保持有限枚举。
enum CliError {
    Read(ReadError),
    Prepare(PrepareError),
}
impl From<ReadError> for CliError {
    fn from(value: ReadError) -> Self {
        Self::Read(value)
    }
}
impl From<PrepareError> for CliError {
    fn from(value: PrepareError) -> Self {
        Self::Prepare(value)
    }
}
impl CliError {
    fn code(&self) -> &'static str {
        match self {
            Self::Read(error) => error.code(),
            Self::Prepare(PrepareError::InvalidSnapshot) => "HANDOFF_INVALID_SNAPSHOT",
            Self::Prepare(PrepareError::InvalidProposal) => "HANDOFF_INVALID_PROPOSAL",
            Self::Prepare(PrepareError::ReferenceNotCurrent) => "HANDOFF_REFERENCE_NOT_CURRENT",
            Self::Prepare(PrepareError::OriginalRequired) => "HANDOFF_ORIGINAL_REQUIRED",
            Self::Prepare(PrepareError::IdentityMismatch) => "HANDOFF_IDENTITY_MISMATCH",
        }
    }
}
fn run() -> Result<(), CliError> {
    let (send, receive) = std::sync::mpsc::channel();
    std::thread::spawn(move || {
        let mut bytes = Vec::new();
        let result = std::io::stdin().take(65_537).read_to_end(&mut bytes);
        let _ = send.send(result.map(|_| bytes));
    });
    let bytes = receive
        .recv_timeout(std::time::Duration::from_secs(5))
        .map_err(|_| ReadError::InvalidAdmission)?
        .map_err(|_| ReadError::InvalidAdmission)?;
    if bytes.len() > 65_536 {
        return Err(ReadError::InvalidAdmission.into());
    }
    let input: Input = serde_json::from_slice(&bytes).map_err(|_| ReadError::InvalidAdmission)?;
    let client = ObserverClient::connect(input.admission)?;
    let response = match input.action {
        Action::Handshake => serde_json::to_value(client.handshake()?),
        Action::Objects => serde_json::to_value(client.objects()?),
        Action::Status { reference } => serde_json::to_value(client.status(&reference)?),
        Action::PrepareHandoff { key, payload } => {
            // 固定metadata端口；不接受调用者伪造的snapshot或任意URL。
            let snapshot = client.objects()?;
            let proposal = prepare(
                &snapshot,
                &key,
                payload,
                archeaxis_api::project_observer::now_ms(),
            )?;
            serde_json::to_value(proposal)
        }
        Action::PrepareReceipt {
            key,
            original,
            state,
            reason,
        } => {
            let snapshot = client.objects()?;
            let receipt = prepare_receipt(
                &snapshot,
                &original,
                &key,
                state,
                reason,
                archeaxis_api::project_observer::now_ms(),
            )?;
            serde_json::to_value(receipt)
        }
    }
    .map_err(|_| ReadError::InvalidResponse)?;
    println!(
        "{}",
        serde_json::to_string(&response).map_err(|_| ReadError::InvalidResponse)?
    );
    Ok(())
}
fn main() {
    if !std::env::args_os().skip(1).collect::<Vec<_>>().is_empty() {
        eprintln!("OBSERVER_STDIN_ONLY");
        std::process::exit(2);
    }
    if let Err(error) = run() {
        println!(
            "{}",
            serde_json::json!({"schema":"archeaxis.project-observer-error/v1","code":error.code()})
        );
        std::process::exit(1);
    }
}
