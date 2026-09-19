//! Knowledge state machine: candidate -> accepted|rejected|deprecated
//! with immutable receipts. Candidates never auto-promote to verified.
use archeaxis_contracts::KNOWLEDGE_TYPES;
use rusqlite::{Connection, OptionalExtension};
use sha2::{Digest, Sha256};

/// Governance metadata owned by the canonical Rust writer.  The legacy
/// knowledge row remains the identity/status record; this sidecar stores the
/// V3 fields that cannot be inferred safely from that row.
#[derive(Clone, Debug)]
pub struct KnowledgeV3Metadata {
    pub source_type: String,
    pub owner: String,
    pub support_level: String,
    pub confidence: Option<f64>,
    pub risk_level: String,
    pub valid_from: Option<String>,
    pub valid_to: Option<String>,
    pub external_evidence: Vec<String>,
    pub requires_human_review: bool,
}

const V3_SOURCE_TYPES: &[&str] = &[
    "personal_experience", "personal_note", "personal_definition",
    "project_observation", "external_document", "authoritative_reference",
    "derived_inference", "machine_candidate", "imported_legacy", "research_result",
];
const V3_OWNERS: &[&str] = &["human", "machine", "system"];
const V3_SUPPORT_LEVELS: &[&str] = &["none", "weak", "moderate", "strong", "authoritative"];
const V3_RISK_LEVELS: &[&str] = &["low", "medium", "high", "critical"];

fn v3_error(message: impl Into<String>) -> rusqlite::Error {
    rusqlite::Error::InvalidParameterName(message.into())
}

fn validate_v3(status: &str, metadata: &KnowledgeV3Metadata) -> rusqlite::Result<()> {
    if !V3_SOURCE_TYPES.contains(&metadata.source_type.as_str()) {
        return Err(v3_error(format!("unknown V3 source_type: {}", metadata.source_type)));
    }
    if !V3_OWNERS.contains(&metadata.owner.as_str()) {
        return Err(v3_error(format!("unknown V3 owner: {}", metadata.owner)));
    }
    if !V3_SUPPORT_LEVELS.contains(&metadata.support_level.as_str()) {
        return Err(v3_error(format!("unknown V3 support_level: {}", metadata.support_level)));
    }
    if !V3_RISK_LEVELS.contains(&metadata.risk_level.as_str()) {
        return Err(v3_error(format!("unknown V3 risk_level: {}", metadata.risk_level)));
    }
    if let Some(confidence) = metadata.confidence {
        if !(0.0..=1.0).contains(&confidence) {
            return Err(v3_error("V3 confidence must be between 0 and 1"));
        }
    }
    if let (Some(valid_from), Some(valid_to)) = (&metadata.valid_from, &metadata.valid_to) {
        if valid_to < valid_from {
            return Err(v3_error("V3 valid_to must not precede valid_from"));
        }
    }
    if metadata.owner == "machine" && metadata.source_type != "machine_candidate" {
        return Err(v3_error("machine V3 owner must use source_type=machine_candidate"));
    }
    if metadata.source_type == "machine_candidate"
        && !matches!(status, "candidate" | "rejected" | "deprecated")
    {
        return Err(v3_error("machine_candidate cannot be accepted or verified automatically"));
    }
    if status == "verified"
        && (metadata.support_level == "none" || metadata.requires_human_review)
    {
        return Err(v3_error("verified V3 knowledge requires support and completed human review"));
    }
    Ok(())
}

fn receipt_hash(kind: &str, body: &str, status: &str, anchor_id: Option<&str>) -> String {
    let mut h = Sha256::new();
    let seed = format!("{kind}|{body}|{status}|{}", anchor_id.unwrap_or(""));
    h.update(seed.as_bytes());
    hex::encode(h.finalize())
}

/// Insert a knowledge row. `status` must be a valid transition start;
/// machine/AI content defaults to "candidate" (never verified automatically).
pub fn create_knowledge(
    conn: &mut Connection,
    knowledge_type: &str,
    body: &str,
    status: &str,
    evidence_status: Option<&str>,
    anchor_id: Option<&str>,
    created_by: &str,
) -> rusqlite::Result<String> {
    create_knowledge_v3(
        conn,
        knowledge_type,
        body,
        status,
        evidence_status,
        anchor_id,
        created_by,
        None,
    )
}

/// Insert a knowledge row and, when supplied, its V3 governance metadata in a
/// single transaction.  This keeps the legacy route compatible while giving
/// new callers one canonical write path for temporal/support/risk fields.
pub fn create_knowledge_v3(
    conn: &mut Connection,
    knowledge_type: &str,
    body: &str,
    status: &str,
    evidence_status: Option<&str>,
    anchor_id: Option<&str>,
    created_by: &str,
    metadata: Option<&KnowledgeV3Metadata>,
) -> rusqlite::Result<String> {
    if !KNOWLEDGE_TYPES.contains(&knowledge_type) {
        return Err(v3_error(format!("unknown knowledge_type: {knowledge_type}")));
    }
    if let Some(metadata) = metadata {
        validate_v3(status, metadata)?;
    }
    let mut h = Sha256::new();
    h.update(format!("{knowledge_type}|{body}|{created_by}").as_bytes());
    let knowledge_id = format!("k_{}", &hex::encode(h.finalize())[..24]);
    let r = receipt_hash(knowledge_type, body, status, anchor_id);
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    tx.execute(
        "INSERT INTO knowledge(knowledge_id, knowledge_type, body, status, evidence_status, anchor_id, created_by, receipt_hash)
         VALUES(?1,?2,?3,?4,?5,?6,?7,?8)",
        rusqlite::params![knowledge_id, knowledge_type, body, status, evidence_status, anchor_id, created_by, r],
    )?;
    if let Some(metadata) = metadata {
        let evidence = serde_json::to_string(&metadata.external_evidence)
            .map_err(|error| v3_error(format!("invalid V3 external_evidence: {error}")))?;
        tx.execute(
            "INSERT INTO knowledge_v3_metadata(
                knowledge_id, source_type, owner, support_level, confidence, risk_level,
                valid_from, valid_to, external_evidence, requires_human_review
             ) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10)",
            rusqlite::params![
                knowledge_id,
                &metadata.source_type,
                &metadata.owner,
                &metadata.support_level,
                metadata.confidence,
                &metadata.risk_level,
                metadata.valid_from.as_deref(),
                metadata.valid_to.as_deref(),
                &evidence,
                metadata.requires_human_review,
            ],
        )?;
    }
    tx.commit()?;
    Ok(knowledge_id)
}

/// Review action produces an immutable event and (for accept/reject/modify)
/// updates the knowledge status. `action` must be one of accepted|rejected|modified|deprecated.
/// C03: the status change and the review event are committed in ONE write
/// transaction - a failure rolls back both (no accepted-without-event).
pub fn review(
    conn: &mut Connection,
    knowledge_id: &str,
    action: &str,
    reviewer: &str,
    note: Option<&str>,
    new_body: Option<&str>,
) -> rusqlite::Result<String> {
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let row: Option<(String, String, String, Option<String>, String)> = tx
        .query_row(
            "SELECT knowledge_type, body, status, anchor_id, created_by FROM knowledge WHERE knowledge_id=?1",
            [knowledge_id],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?)),
        )
        .optional()?;
    let (kind, old_body, _status, anchor_id, old_created_by) = match row {
        Some(x) => x,
        None => {
            return Err(rusqlite::Error::InvalidParameterName(
                "knowledge not found".into(),
            ));
        }
    };
    // REVISION-01: accepting, rejecting or deprecating never rewrites the
    // reviewed body; a corrected body must go through "modified", which
    // creates a new revision and a supersede relation instead.
    if action != "modified" && new_body.is_some() {
        return Err(rusqlite::Error::InvalidParameterName(
            "new_body requires the modified action; accept/reject/deprecate never overwrite the reviewed body".into(),
        ));
    }
    if action == "modified" {
        // A modification creates a NEW candidate row carrying the corrected
        // body inside the same transaction and records the event on the old
        // row; nothing is committed unless both succeed.
        let revised_body = new_body.unwrap_or(&old_body).to_string();
        let mut h = Sha256::new();
        h.update(format!("{kind}|{revised_body}|{reviewer}").as_bytes());
        let kid = format!("k_{}", &hex::encode(h.finalize())[..24]);
        tx.execute(
            "INSERT INTO knowledge(knowledge_id, knowledge_type, body, status, evidence_status, anchor_id, created_by, receipt_hash)
             VALUES(?1,?2,?3,'candidate',NULL,?4,?5,?6)",
            rusqlite::params![
                kid,
                kind,
                revised_body,
                anchor_id,
                old_created_by,
                receipt_hash(&kind, &revised_body, "candidate", anchor_id.as_deref()),
            ],
        )?;
        tx.execute(
            "INSERT INTO review_events(knowledge_id, action, reviewer, note) VALUES(?1,?2,?3,?4)",
            rusqlite::params![
                knowledge_id,
                "modified",
                reviewer,
                note.map(|n| format!("{n} (new candidate {kid})"))
            ],
        )?;
        tx.execute(
            "INSERT INTO knowledge_supersedes(old_knowledge_id, new_knowledge_id) VALUES(?1,?2)",
            rusqlite::params![knowledge_id, kid],
        )?;
        // Carry V3 governance forward with a corrected candidate. The
        // supersession relation still records the revision boundary; callers
        // may replace metadata only through a future explicit review contract.
        tx.execute(
            "INSERT INTO knowledge_v3_metadata(
                knowledge_id, source_type, owner, support_level, confidence, risk_level,
                valid_from, valid_to, external_evidence, requires_human_review
             )
             SELECT ?1, source_type, owner, support_level, confidence, risk_level,
                    valid_from, valid_to, external_evidence, requires_human_review
             FROM knowledge_v3_metadata WHERE knowledge_id=?2",
            rusqlite::params![kid, knowledge_id],
        )?;
        tx.commit()?;
        return Ok(kid);
    }
    let new_status = match action {
        "accepted" => "accepted",
        "rejected" => "rejected",
        "deprecated" => "deprecated",
        _ => {
            return Err(rusqlite::Error::InvalidParameterName(
                "unknown action".into(),
            ));
        }
    };
    let r = receipt_hash(&kind, &old_body, new_status, anchor_id.as_deref());
    // REVISION-01: status changes touch only status and receipt; the reviewed
    // body bytes stay exactly as first stored.
    tx.execute(
        "UPDATE knowledge SET status=?1, receipt_hash=?2 WHERE knowledge_id=?3",
        rusqlite::params![new_status, r, knowledge_id],
    )?;
    tx.execute(
        "INSERT INTO review_events(knowledge_id, action, reviewer, note) VALUES(?1,?2,?3,?4)",
        rusqlite::params![knowledge_id, action, reviewer, note],
    )?;
    tx.commit()?;
    Ok(knowledge_id.to_string())
}

/// Count knowledge rows by status.
pub fn status_counts(conn: &Connection) -> rusqlite::Result<String> {
    let (c, a, r, d): (i64, i64, i64, i64) = conn.query_row(
        "SELECT
           (SELECT count(*) FROM knowledge WHERE status='candidate'),
           (SELECT count(*) FROM knowledge WHERE status='accepted'),
           (SELECT count(*) FROM knowledge WHERE status='rejected'),
           (SELECT count(*) FROM knowledge WHERE status='deprecated')",
        [],
        |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)),
    )?;
    let mut s = String::from("{");
    let mut add = |key: &str, val: i64, last: bool| {
        s.push('"');
        s.push_str(key);
        s.push('"');
        s.push(':');
        s.push_str(&val.to_string());
        if !last {
            s.push(',');
        }
    };
    add("candidate", c, false);
    add("accepted", a, false);
    add("rejected", r, false);
    add("deprecated", d, true);
    s.push('}');
    Ok(s)
}

/// Qualification check used before a machine (or any consumer) reuses a
/// knowledge unit as current context (X09). A knowledge row is active only
/// while its latest status is candidate or accepted; deprecated/rejected rows
/// must not be served as current valid facts. Unknown ids report false.
pub fn is_knowledge_active(conn: &Connection, knowledge_id: &str) -> rusqlite::Result<bool> {
    let row: Option<(String, bool)> = conn
        .query_row(
            "SELECT status,
                    EXISTS(SELECT 1 FROM knowledge_supersedes WHERE old_knowledge_id=?1)
             FROM knowledge WHERE knowledge_id=?1",
            [knowledge_id],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .optional()?;
    match row {
        Some((status, superseded)) => {
            // A row that has a newer successor is no longer "current" even if
            // its own status is candidate/accepted (version strategy).
            Ok(!superseded && matches!(status.as_str(), "candidate" | "accepted"))
        }
        None => Ok(false),
    }
}

/// Reverse lookup: knowledge rows bound to a source anchor (bidirectional
/// navigation from an original-source position back to derived content).
pub fn knowledge_ids_for_anchor(
    conn: &Connection,
    anchor_id: &str,
) -> rusqlite::Result<Vec<String>> {
    let mut stmt = conn.prepare(
        "SELECT knowledge_id FROM knowledge WHERE anchor_id=?1 ORDER BY knowledge_id",
    )?;
    let rows = stmt.query_map([anchor_id], |r| r.get(0))?;
    rows.collect()
}

/// Read the persisted status of a knowledge row (None when missing) so a
/// consumer can check qualification before reuse.
pub fn knowledge_status(conn: &Connection, knowledge_id: &str) -> rusqlite::Result<Option<String>> {
    conn.query_row(
        "SELECT status FROM knowledge WHERE knowledge_id=?1",
        [knowledge_id],
        |r| r.get(0),
    )
    .optional()
}

/// Successor ids produced by modified reviews (revision chain forward).
pub fn knowledge_successors(conn: &Connection, knowledge_id: &str) -> rusqlite::Result<Vec<String>> {
    let mut stmt = conn.prepare(
        "SELECT new_knowledge_id FROM knowledge_supersedes
         WHERE old_knowledge_id=?1 ORDER BY created_at, rowid",
    )?;
    let rows = stmt.query_map([knowledge_id], |r| r.get(0))?;
    rows.collect()
}
