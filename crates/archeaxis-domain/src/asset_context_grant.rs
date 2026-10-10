//! Explicit finite asset packet authority; never imports executable tool/session authority.
use crate::{
    ai_asset::{self, Snapshot},
    document::{self, Error},
    machine,
};
use rusqlite::{Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
pub const NAMESPACE: &str = "archeaxis_asset_context_grant";
pub const SCHEMA: &str = "archeaxis.asset-context-grant/v1";
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Consumer {
    LocalMachine,
    ManualContextPacket,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Operation {
    ReadPacket,
    Answer,
    Retest,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum State {
    Candidate,
    Granted,
    Revoked,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AssetContextGrant {
    pub schema: String,
    pub asset: Snapshot,
    pub purpose: String,
    pub consumer: Consumer,
    pub operations: Vec<Operation>,
    pub authorization_basis: String,
    pub expires_at: Option<u64>,
    pub state: State,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PacketRequest {
    pub request_id: String,
    pub grant: Snapshot,
    pub asset: Snapshot,
    pub purpose: String,
    pub consumer: Consumer,
    pub operation: Operation,
}
fn invalid(s: &'static str) -> Error {
    Error::Invalid(s)
}
fn metadata(editor: &Value) -> Result<Option<AssetContextGrant>, Error> {
    editor
        .get("attrs")
        .and_then(|a| a.get(NAMESPACE))
        .map(|raw| {
            serde_json::from_value(raw.clone())
                .map_err(|_| invalid("unknown asset context grant shape; preserve original"))
        })
        .transpose()
}
pub fn validate_editor(conn: &Connection, id: &str, editor: &Value) -> Result<(), Error> {
    let Some(g) = metadata(editor)? else {
        return Ok(());
    };
    if g.schema != SCHEMA
        || g.purpose.len() > 1024
        || g.authorization_basis.len() > 16384
        || g.operations.len() > 3
        || g.expires_at.is_some_and(|e| e > 253402300799)
        || g.operations
            .iter()
            .enumerate()
            .any(|(i, op)| g.operations[..i].contains(op))
        || (g.consumer == Consumer::ManualContextPacket
            && g.operations.iter().any(|op| *op != Operation::ReadPacket))
    {
        return Err(invalid("asset grant scope or bounds unsupported"));
    }
    let revoked: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM document_versions WHERE document_id=?1
        AND json_extract(editor_json,'$.attrs.archeaxis_asset_context_grant.state')='revoked')",
        [id],
        |r| r.get(0),
    )?;
    if revoked && g.state != State::Revoked {
        return Err(invalid("revoked asset grant cannot be reactivated"));
    }
    if g.state == State::Revoked {
        return Ok(());
    } // Removing permission never needs unavailable source.
    let d = ai_asset::read_snapshot(conn, &g.asset, false)?;
    ai_asset::metadata(&d["editor_json"])?.ok_or(invalid("grant must bind a real AI asset"))?;
    if g.state == State::Granted {
        if g.purpose.trim().is_empty()
            || g.authorization_basis.trim().is_empty()
            || g.operations.is_empty()
        {
            return Err(invalid(
                "explicit grant requires purpose, human basis and finite operations",
            ));
        }
        ai_asset::read_snapshot(conn, &g.asset, true)?;
    }
    Ok(())
}
/// actual_consumer is selected by trusted host role/route, not request JSON.
/// Every caller repeats this same admission immediately before publication.
pub fn admit(
    conn: &Connection,
    request: &PacketRequest,
    actual_consumer: Consumer,
    now: u64,
) -> Result<Value, Error> {
    if request.request_id.is_empty()
        || request.request_id.len() > 128
        || !request.request_id.bytes().all(|b| b.is_ascii_graphic())
    {
        return Err(invalid(
            "packet request requires a frozen bounded ASCII identity",
        ));
    }
    archeaxis_store_sqlite::authorization_fence::assert_grant_not_fenced(
        conn,
        &request.grant.document_id,
    )
    .map_err(|e| match e {
        rusqlite::Error::InvalidParameterName(_) => {
            invalid("restored asset grant requires new explicit human authorization")
        }
        other => Error::Sql(other),
    })?;
    let d = ai_asset::read_snapshot(conn, &request.grant, true)?;
    let g = metadata(&d["editor_json"])?.ok_or(invalid("asset context grant absent"))?;
    validate_editor(conn, &request.grant.document_id, &d["editor_json"])?;
    if g.state != State::Granted
        || g.asset != request.asset
        || g.purpose != request.purpose
        || g.consumer != actual_consumer
        || request.consumer != actual_consumer
        || !g.operations.contains(&request.operation)
        || g.expires_at.is_some_and(|expiry| now >= expiry)
    {
        return Err(invalid(
            "asset packet exceeds current consumer/purpose/operation/version/expiry grant",
        ));
    }
    let items = ai_asset::packet_items(conn, &g.asset, now)?;
    let packet = json!({"schema":"archeaxis.ai-context-packet/v1","asset":g.asset,"consumer":actual_consumer,
        "purpose":g.purpose,"operation":request.operation,"items":items,
        "grant":request.grant,"reference_only_sources":true,"private_session_access":false,
        "tool_execution":"NOT_EXECUTED","machine_qualification":false,"human_mastery":false,"professional_truth":false});
    if packet.to_string().len() > 128000 {
        return Err(invalid("full context packet exceeds bounded output"));
    }
    Ok(packet)
}
/// Finite read-only packet endpoint, inside ONE Store closure including authorization,
/// packet projection, immutable redacted usage receipt and exact retry readback.
/// It never invokes a worker and does not prove an external client consumed the material.
pub fn prepare_packet(
    conn: &mut Connection,
    request: &PacketRequest,
    actual_consumer: Consumer,
    now: u64,
) -> Result<Value, Error> {
    if request.operation != Operation::ReadPacket {
        return Err(invalid(
            "packet endpoint supports read_packet only; model calls require owned runtime",
        ));
    }
    let packet = admit(conn, request, actual_consumer, now)?;
    let frozen = serde_json::to_value(request)
        .map_err(|_| invalid("packet request serialization failed"))?;
    let request_sha = ai_asset::hash(&frozen);
    let packet_sha = ai_asset::hash(&packet);
    let task_id = format!(
        "context_packet_{}",
        ai_asset::hash(&json!(request.request_id))
    );
    let proof = json!({"schema":"archeaxis.ai-context-packet-receipt/v1","request_id":request.request_id,
        "request_sha256":request_sha,"packet_sha256":packet_sha,"asset":request.asset,"grant":request.grant,
        "consumer":request.consumer,"purpose":request.purpose,"operation":"read_packet",
        "delivery_status":"PREPARED_NOT_SENT_TO_PEER","model_execution":"NOT_EXECUTED",
        "tool_execution":"NOT_EXECUTED","grants_machine_qualification":false,"grants_human_mastery":false});
    let exists: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='machine_tasks')",
        [],
        |r| r.get(0),
    )?;
    let previous: Option<String> = if exists {
        conn.query_row("SELECT conditions FROM machine_tasks WHERE task_id=?1 AND scope='runtime.context.packet'",[&task_id],|r|r.get(0)).optional()?
    } else {
        None
    };
    if let Some(old) = previous {
        let old: Value =
            serde_json::from_str(&old).map_err(|_| invalid("stored packet receipt unreadable"))?;
        if old != proof {
            return Err(invalid(
                "client request identity already has a different frozen packet",
            ));
        }
        return Ok(
            json!({"packet":packet,"packet_sha256":packet_sha,"receipt":proof,"audit_task_id":task_id,"duplicate":true}),
        );
    }
    machine::record_machine_task(
        conn,
        &machine::MachineTask {
            task_id: &task_id,
            principal: "machine",
            conditions: &proof.to_string(),
            knowledge_version: None,
            method_version: None,
            tool_version: None,
            model_version: "NOT_RUN_CONTEXT_PACKET",
            scope: "runtime.context.packet",
            outcome: "unmeasured",
            failure: None,
            retest_of: None,
        },
    )?;
    let stored:(String,String,String,String)=conn.query_row(
        "SELECT conditions,principal,model_version,outcome FROM machine_tasks WHERE task_id=?1 AND scope='runtime.context.packet'",
        [&task_id],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?)))?;
    let stored_proof: Value = serde_json::from_str(&stored.0)
        .map_err(|_| invalid("packet audit readback is unreadable"))?;
    if stored_proof != proof
        || stored.1 != "machine"
        || stored.2 != "NOT_RUN_CONTEXT_PACKET"
        || stored.3 != "unmeasured"
    {
        return Err(invalid(
            "packet audit write was not confirmed; no successful packet receipt",
        ));
    }
    Ok(
        json!({"packet":packet,"packet_sha256":packet_sha,"receipt":proof,"audit_task_id":task_id,"duplicate":false}),
    )
}
