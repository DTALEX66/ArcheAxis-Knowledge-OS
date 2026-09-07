//! Knowledge state machine: candidate -> accepted|rejected|deprecated
//! with immutable receipts. Candidates never auto-promote to verified.
use archeaxis_contracts::KNOWLEDGE_TYPES;
use rusqlite::{Connection, OptionalExtension};
use sha2::{Digest, Sha256};

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
    if !KNOWLEDGE_TYPES.contains(&knowledge_type) {
        return Err(rusqlite::Error::InvalidParameterName(format!(
            "unknown knowledge_type: {knowledge_type}"
        )));
    }
    let mut h = Sha256::new();
    h.update(format!("{knowledge_type}|{body}|{created_by}").as_bytes());
    let knowledge_id = format!("k_{}", &hex::encode(h.finalize())[..24]);
    let r = receipt_hash(knowledge_type, body, status, anchor_id);
    conn.execute(
        "INSERT INTO knowledge(knowledge_id, knowledge_type, body, status, evidence_status, anchor_id, created_by, receipt_hash)
         VALUES(?1,?2,?3,?4,?5,?6,?7,?8)",
        rusqlite::params![knowledge_id, knowledge_type, body, status, evidence_status, anchor_id, created_by, r],
    )?;
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
    let row: Option<(String, String, String, Option<String>)> = tx
        .query_row(
            "SELECT knowledge_type, body, status, anchor_id FROM knowledge WHERE knowledge_id=?1",
            [knowledge_id],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)),
        )
        .optional()?;
    let (kind, old_body, _status, anchor_id) = match row {
        Some(x) => x,
        None => {
            return Err(rusqlite::Error::InvalidParameterName(
                "knowledge not found".into(),
            ));
        }
    };
    let final_body = new_body.unwrap_or(&old_body).to_string();
    if action == "modified" {
        // A modification creates a NEW candidate row inside the same
        // transaction and records the event on the old row; nothing is
        // committed unless both succeed.
        let mut h = Sha256::new();
        h.update(format!("{kind}|{final_body}|{reviewer}").as_bytes());
        let kid = format!("k_{}", &hex::encode(h.finalize())[..24]);
        tx.execute(
            "INSERT INTO knowledge(knowledge_id, knowledge_type, body, status, evidence_status, anchor_id, created_by, receipt_hash)
             VALUES(?1,?2,?3,'candidate',NULL,?4,?5,?6)",
            rusqlite::params![
                kid,
                kind,
                final_body,
                anchor_id,
                reviewer,
                receipt_hash(&kind, &final_body, "candidate", anchor_id.as_deref()),
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
    let r = receipt_hash(&kind, &final_body, new_status, anchor_id.as_deref());
    tx.execute(
        "UPDATE knowledge SET body=?1, status=?2, receipt_hash=?3 WHERE knowledge_id=?4",
        rusqlite::params![final_body, new_status, r, knowledge_id],
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
    let status: Option<String> = conn
        .query_row(
            "SELECT status FROM knowledge WHERE knowledge_id=?1",
            [knowledge_id],
            |r| r.get(0),
        )
        .optional()?;
    Ok(matches!(status.as_deref(), Some("candidate" | "accepted")))
}
