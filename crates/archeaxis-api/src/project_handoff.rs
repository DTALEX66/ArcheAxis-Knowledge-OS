//! BE10 纯metadata投影：无HTTP入口、DB、正文或执行；复用现有sha2依赖。
use archeaxis_contracts::project_handoff::*;
use archeaxis_contracts::project_observer::{
    self as observer, Payload as ReadPayload, ReadResponse,
};
use sha2::{Digest, Sha256};

/// v1明确的规范JSON：对象key按字典序，数组保序，无空白，整数十进制。
/// 值只来自strict DTO，不接受任意JSON；UTF-8字节带版本域分隔后SHA-256。
pub fn proposal_fingerprint(proposal: &Handoff) -> Result<String, PrepareError> {
    if !proposal.valid(proposal.created_at_ms) || proposal.payload.proposal_kind().is_none() {
        return Err(PrepareError::InvalidProposal);
    }
    fn canonical(value: &serde_json::Value, bytes: &mut Vec<u8>) {
        match value {
            serde_json::Value::Object(map) => {
                bytes.push(b'{');
                let mut keys: Vec<_> = map.keys().collect();
                keys.sort_unstable();
                for (index, key) in keys.into_iter().enumerate() {
                    if index > 0 {
                        bytes.push(b',');
                    }
                    serde_json::to_writer(&mut *bytes, key).expect("validated DTO key");
                    bytes.push(b':');
                    canonical(&map[key], bytes);
                }
                bytes.push(b'}');
            }
            serde_json::Value::Array(values) => {
                bytes.push(b'[');
                for (index, value) in values.iter().enumerate() {
                    if index > 0 {
                        bytes.push(b',');
                    }
                    canonical(value, bytes);
                }
                bytes.push(b']');
            }
            _ => serde_json::to_writer(bytes, value).expect("validated finite DTO scalar"),
        }
    }
    let mut bytes = b"archeaxis.project-handoff/v1\0".to_vec();
    canonical(
        &serde_json::to_value(proposal).map_err(|_| PrepareError::InvalidProposal)?,
        &mut bytes,
    );
    Ok(format!("{:x}", Sha256::digest(bytes)))
}
/// 上游必须来自已认证 ObserverClient；此函数不负责认证、不做任何 I/O。
pub fn prepare(
    snapshot: &ReadResponse,
    key: &str,
    payload: Payload,
    now_ms: u64,
) -> Result<Handoff, PrepareError> {
    if !snapshot.valid(now_ms) {
        return Err(PrepareError::InvalidSnapshot);
    }
    if matches!(payload, Payload::Receipt { .. }) {
        return Err(PrepareError::OriginalRequired);
    }
    let allowed = match &snapshot.payload {
        ReadPayload::Objects { objects, .. } => objects.iter().collect::<Vec<_>>(),
        ReadPayload::ObjectStatus {
            reference,
            state: observer::ObjectState::Current,
            ..
        } => vec![reference],
        _ => return Err(PrepareError::ReferenceNotCurrent),
    };
    if payload
        .references()
        .iter()
        .any(|reference| !allowed.contains(reference))
    {
        return Err(PrepareError::ReferenceNotCurrent);
    }
    finish(snapshot, key, payload, now_ms)
}
fn finish(
    snapshot: &ReadResponse,
    key: &str,
    payload: Payload,
    now_ms: u64,
) -> Result<Handoff, PrepareError> {
    let value = Handoff {
        schema: SCHEMA.into(),
        protocol: observer::PROTOCOL.into(),
        idempotency_key: key.into(),
        producer: snapshot.producer.clone(),
        consumer: snapshot.consumer.clone(),
        created_at_ms: now_ms,
        expires_at_ms: snapshot.expires_at_ms,
        authority: Authority::PreparationOnly,
        payload,
    };
    if value.valid(now_ms) {
        Ok(value)
    } else {
        Err(PrepareError::InvalidProposal)
    }
}
pub fn prepare_receipt(
    snapshot: &ReadResponse,
    original: &Handoff,
    key: &str,
    state: ReceiptState,
    reason: ReceiptReason,
    now_ms: u64,
) -> Result<Handoff, PrepareError> {
    if !snapshot.valid(now_ms) {
        return Err(PrepareError::InvalidSnapshot);
    }
    if !original.valid(original.created_at_ms) || original.created_at_ms > now_ms {
        return Err(PrepareError::InvalidProposal);
    }
    if snapshot.producer != original.producer || snapshot.consumer != original.consumer {
        return Err(PrepareError::IdentityMismatch);
    }
    let kind = original
        .payload
        .proposal_kind()
        .ok_or(PrepareError::OriginalRequired)?;
    if state == ReceiptState::Prepared {
        if !original.valid(now_ms) {
            return Err(PrepareError::InvalidProposal);
        }
        prepare(
            snapshot,
            &original.idempotency_key,
            original.payload.clone(),
            now_ms,
        )?;
    }
    let prepared = state == ReceiptState::Prepared;
    let mut result = finish(
        snapshot,
        key,
        Payload::Receipt {
            proposal: ProposalReference {
                idempotency_key: original.idempotency_key.clone(),
                proposal_sha256: proposal_fingerprint(original)?,
                kind,
            },
            state,
            reason,
        },
        now_ms,
    )?;
    if prepared {
        result.expires_at_ms = result.expires_at_ms.min(original.expires_at_ms);
    }
    Ok(result)
}
/// 回执必须与原提案的身份、restore epoch、key和kind全匹配；UNKNOWN不折算为成功。
pub fn receipt_matches(receipt: &Handoff, original: &Handoff, now_ms: u64) -> bool {
    let Ok(fingerprint) = proposal_fingerprint(original) else {
        return false;
    };
    receipt.valid(now_ms)
        && original.valid(original.created_at_ms)
        && original.created_at_ms <= receipt.created_at_ms
        && receipt.producer == original.producer
        && receipt.consumer == original.consumer
        && match &receipt.payload {
            Payload::Receipt {
                state: ReceiptState::Prepared,
                ..
            } => {
                receipt.expires_at_ms <= original.expires_at_ms
                    && original.valid(receipt.created_at_ms)
            }
            _ => true,
        }
        && matches!(&receipt.payload,Payload::Receipt { proposal, .. } if proposal.idempotency_key == original.idempotency_key && proposal.proposal_sha256 == fingerprint && Some(proposal.kind.clone()) == original.payload.proposal_kind())
}
/// 仅合同内的幂等比较；不持久化、不投递，不承诺 exactly-once。
pub fn classify_retry(original: &Handoff, retry: &Handoff) -> Result<RetryClass, PrepareError> {
    if !original.valid(original.created_at_ms) || !retry.valid(retry.created_at_ms) {
        return Err(PrepareError::InvalidProposal);
    }
    if original.producer != retry.producer
        || original.consumer != retry.consumer
        || original.idempotency_key != retry.idempotency_key
    {
        return Ok(RetryClass::Unrelated);
    }
    Ok(if original == retry {
        RetryClass::Equivalent
    } else {
        RetryClass::Conflict
    })
}
