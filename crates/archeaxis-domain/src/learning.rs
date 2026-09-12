//! Learning events: one learning event + next-review scheduling.
use rusqlite::{Connection, OptionalExtension};
use sha2::{Digest, Sha256};

/// Record a learning event (review/quiz/teach_back/mastery) with its outcome.
/// `next_review` is an ISO date hint produced by the scheduler (kept simple: +N days).
pub fn record_learning_event(
    conn: &mut Connection,
    item_key: &str,
    kind: &str,
    outcome_json: &str,
    next_review_days: i64,
) -> rusqlite::Result<i64> {
    let next_review = if next_review_days > 0 {
        Some(format!("+{} day", next_review_days))
    } else {
        None
    };
    conn.execute(
        "INSERT INTO learning_events(item_key, kind, outcome, next_review) VALUES(?1,?2,?3,?4)",
        rusqlite::params![item_key, kind, outcome_json, next_review],
    )?;
    Ok(conn.last_insert_rowid())
}

/// Simple spaced hint: review interval grows with correct answers.
pub fn suggest_next_interval(correct_in_a_row: u32) -> i64 {
    match correct_in_a_row {
        0 => 1,
        1 => 2,
        2 => 4,
        3 => 7,
        _ => 14,
    }
}

pub fn count_learning(conn: &Connection) -> rusqlite::Result<i64> {
    conn.query_row("SELECT count(*) FROM learning_events", [], |r| r.get(0))
}


/// Absolute next-review timestamp (UTC) computed by SQLite: 'now' + N days.
pub fn next_review_iso(conn: &Connection, days: i64) -> rusqlite::Result<Option<String>> {
    if days <= 0 {
        return Ok(None);
    }
    let modifier = format!("+{days} day");
    conn.query_row("SELECT datetime('now', ?1)", [&modifier], |r| r.get(0))
        .map(Some)
}
/// Count trailing correct outcomes for an item (most recent events first).
/// outcome JSON is expected to carry {"outcome": "correct" | "incorrect"}.
pub fn correct_streak(conn: &Connection, item_key: &str) -> rusqlite::Result<u32> {
    let mut stmt = conn.prepare(
        "SELECT outcome FROM learning_events WHERE item_key=?1 ORDER BY event_id DESC",
    )?;
    let rows = stmt.query_map([item_key], |r| r.get::<_, String>(0))?;
    let mut streak = 0u32;
    for row in rows {
        let outcome = row?;
        let is_correct = outcome.contains("\"outcome\": \"correct\"")
            || outcome.contains("\"correct\": true");
        if is_correct {
            streak += 1;
        } else {
            break;
        }
    }
    Ok(streak)
}

/// Record one human review outcome and persist the next-review hint.
/// correct -> interval grows with the streak; incorrect resets to 1 day.
pub fn record_review(
    conn: &mut Connection,
    item_key: &str,
    kind: &str,
    correct: bool,
) -> rusqlite::Result<(i64, u32, i64)> {
    let prior = correct_streak(conn, item_key)?;
    let streak_after = if correct { prior + 1 } else { 0 };
    let next_review_days = if correct { suggest_next_interval(streak_after) } else { 1 };
    let outcome = format!(r#"{{"outcome": "{}"}}"#, if correct { "correct" } else { "incorrect" });
    let next_review = next_review_iso(conn, next_review_days)?;
    conn.execute(
        "INSERT INTO learning_events(item_key, kind, outcome, next_review) VALUES(?1,?2,?3,?4)",
        rusqlite::params![item_key, kind, outcome, next_review],
    )?;
    Ok((conn.last_insert_rowid(), streak_after, next_review_days))
}

/// Record one human review outcome with a caller-supplied persistent event
/// key (EVENT-01). The key is bound to item_key and the canonical payload
/// hash, and the original receipt (event_id, streak, next-review days) is
/// stored with it, so:
/// - the same retry (same key + same payload) returns the ORIGINAL receipt
///   with `duplicate = true` and never accumulates a second event;
/// - the same key with a different item or payload is a conflict (error);
/// - a missing key is rejected: unkeyed submissions must not accumulate.
/// R05: interval sentinel - the reusable scheduler was unavailable, so the
/// review is recorded as explicitly *unscheduled* (no due date) instead of
/// falling back to the placeholder ladder.
pub const SCHEDULE_UNAVAILABLE: i64 = -2;
/// R2 EVENT-01: interval sentinel - the receipt replayed an earlier identical
/// submission.
pub const SCHEDULE_DUPLICATE: i64 = -1;

/// Where a keyed review's next interval comes from.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ScheduleSource {
    /// Temporary placeholder ladder (1/2/4/7/14). Kept only for callers that
    /// have no scheduler yet; it is no longer the intended product default.
    Ladder,
    /// Interval computed by the reusable FSRS scheduler. `None` means that
    /// scheduler was unavailable: the review is recorded as unscheduled and the
    /// reported interval is [`SCHEDULE_UNAVAILABLE`] - never a ladder value.
    Explicit(Option<i64>),
}

fn record_review_keyed_impl(
    conn: &mut Connection,
    item_key: &str,
    kind: &str,
    correct: bool,
    client_event_key: &str,
    schedule: ScheduleSource,
) -> rusqlite::Result<(i64, u32, i64, bool)> {
    if client_event_key.trim().is_empty() {
        return Err(rusqlite::Error::InvalidParameterName(
            "learning events require a persistent event_key; unkeyed submissions are rejected".into(),
        ));
    }
    // The marker is part of the keyed payload: an unscheduled review is not
    // interchangeable with a scheduled one for the same event key.
    let outcome = if schedule == ScheduleSource::Explicit(None) {
        format!(
            r#"{{"outcome": "{}", "schedule": "unavailable"}}"#,
            if correct { "correct" } else { "incorrect" }
        )
    } else {
        format!(r#"{{"outcome": "{}"}}"#, if correct { "correct" } else { "incorrect" })
    };
    let mut h = Sha256::new();
    h.update(format!("{kind}|{outcome}").as_bytes());
    let payload_hash = hex::encode(h.finalize());
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let existing: Option<(Option<i64>, Option<String>, Option<i64>, Option<i64>, String)> = tx
        .query_row(
            "SELECT event_id, payload_hash, streak_after, next_review_days, item_key
             FROM learning_event_keys WHERE event_key=?1",
            [client_event_key],
            |r| {
                Ok((
                    r.get(0)?,
                    r.get(1)?,
                    r.get(2)?,
                    r.get(3)?,
                    r.get(4)?,
                ))
            },
        )
        .optional()?;
    if let Some((event_id, stored_hash, stored_streak, stored_days, stored_item)) = existing {
        if stored_item == item_key && stored_hash.as_deref() == Some(payload_hash.as_str()) {
            // Same retry: replay the original receipt, write nothing.
            return Ok((
                event_id.unwrap_or(0),
                stored_streak.unwrap_or(0) as u32,
                stored_days.unwrap_or(-1),
                true,
            ));
        }
        return Err(rusqlite::Error::InvalidParameterName(
            "event_key conflict: key is already bound to a different item or payload".into(),
        ));
    }
    let prior = correct_streak(&tx, item_key)?;
    let streak_after = if correct { prior + 1 } else { 0 };
    let next_review_days = match schedule {
        ScheduleSource::Ladder => {
            if correct { suggest_next_interval(streak_after) } else { 1 }
        }
        ScheduleSource::Explicit(days) => days.unwrap_or(SCHEDULE_UNAVAILABLE),
    };
    let next_review = if next_review_days == SCHEDULE_UNAVAILABLE {
        None
    } else {
        next_review_iso(&tx, next_review_days)?
    };
    tx.execute(
        "INSERT INTO learning_events(item_key, kind, outcome, next_review) VALUES(?1,?2,?3,?4)",
        rusqlite::params![item_key, kind, outcome, next_review],
    )?;
    let event_id = tx.last_insert_rowid();
    tx.execute(
        "INSERT INTO learning_event_keys(event_key, item_key, payload_hash, event_id, streak_after, next_review_days)
         VALUES(?1,?2,?3,?4,?5,?6)",
        rusqlite::params![
            client_event_key,
            item_key,
            payload_hash,
            event_id,
            streak_after,
            if next_review_days == SCHEDULE_UNAVAILABLE {
                None
            } else {
                Some(next_review_days)
            }
        ],
    )?;
    tx.commit()?;
    Ok((event_id, streak_after, next_review_days, false))
}

/// Record a keyed review whose next interval comes from the reusable scheduler.
///
/// `next_review_days` is the value the Core's scheduler adapter obtained from the
/// reused FSRS worker. `None` means that scheduler was unavailable: the event is
/// still recorded with its persistent key (so a retry stays idempotent), but with
/// no due date, an explicit `schedule: unavailable` marker in the payload, and
/// the reported interval [`SCHEDULE_UNAVAILABLE`]. The review is never silently
/// scheduled by the placeholder ladder.
pub fn record_review_scheduled(
    conn: &mut Connection,
    item_key: &str,
    kind: &str,
    correct: bool,
    client_event_key: &str,
    next_review_days: Option<i64>,
) -> rusqlite::Result<(i64, u32, i64, bool)> {
    record_review_keyed_impl(
        conn,
        item_key,
        kind,
        correct,
        client_event_key,
        ScheduleSource::Explicit(next_review_days),
    )
}

/// Record a keyed review using the placeholder ladder.
///
/// Kept for callers that have no scheduler yet; behaviour is unchanged from
/// before R05. New callers use [`record_review_scheduled`].
pub fn record_review_keyed(
    conn: &mut Connection,
    item_key: &str,
    kind: &str,
    correct: bool,
    client_event_key: &str,
) -> rusqlite::Result<(i64, u32, i64, bool)> {
    record_review_keyed_impl(
        conn,
        item_key,
        kind,
        correct,
        client_event_key,
        ScheduleSource::Ladder,
    )
}

/// Read the persisted history for one learning item (oldest first).
pub fn events_for_item(
    conn: &Connection,
    item_key: &str,
) -> rusqlite::Result<Vec<(i64, String, String, Option<String>)>> {
    let mut stmt = conn.prepare(
        "SELECT event_id, kind, outcome, next_review FROM learning_events
         WHERE item_key=?1 ORDER BY event_id ASC",
    )?;
    let rows = stmt.query_map([item_key], |r| {
        Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?))
    })?;
    rows.collect()
}

/// R09: the table that links a learning item (card/question) to the knowledge
/// revision it was created from. Created on demand like the FTS indexes, so no
/// schema-version bump and no archive-layout change is needed.
///
/// Note (recorded limitation): because it is created on demand it is not part of
/// EXPORT_TABLES, so archives do not carry card references yet.
fn ensure_card_references(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS card_references(
             item_key TEXT NOT NULL,
             knowledge_id TEXT NOT NULL REFERENCES knowledge(knowledge_id),
             created_event_id INTEGER,
             referenced_at TEXT NOT NULL DEFAULT (datetime('now')),
             PRIMARY KEY(item_key, knowledge_id)
         );",
    )?;
    Ok(())
}

/// R09: record that a learning item was created from a knowledge revision.
///
/// Idempotent: recording the same (item, revision) twice keeps one row, so a
/// retry cannot fabricate a second reference.
pub fn record_card_reference(
    conn: &mut Connection,
    item_key: &str,
    knowledge_id: &str,
    created_event_id: Option<i64>,
) -> rusqlite::Result<()> {
    if item_key.trim().is_empty() || knowledge_id.trim().is_empty() {
        return Err(rusqlite::Error::InvalidParameterName(
            "card references need both an item_key and a knowledge_id".into(),
        ));
    }
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    ensure_card_references(&tx)?;
    let exists: Option<i64> = tx
        .query_row(
            "SELECT 1 FROM knowledge WHERE knowledge_id=?1",
            [knowledge_id],
            |r| r.get(0),
        )
        .optional()?;
    if exists.is_none() {
        return Err(rusqlite::Error::InvalidParameterName(
            "card reference must name an existing knowledge revision".into(),
        ));
    }
    tx.execute(
        "INSERT OR IGNORE INTO card_references(item_key, knowledge_id, created_event_id)
         VALUES(?1,?2,?3)",
        rusqlite::params![item_key, knowledge_id, created_event_id],
    )?;
    tx.commit()?;
    Ok(())
}

/// R09: the revisions a learning item was created from, each annotated with
/// whether it is still the current, active revision.
///
/// The reference itself is never rewritten: an item that was built on a later
/// superseded revision stays visibly linked to it, and the annotation tells a
/// consumer (question, cache, machine context, result write-back) that the
/// revision it used is no longer current.
pub fn references_for_card(
    conn: &Connection,
    item_key: &str,
) -> rusqlite::Result<Vec<(String, bool)>> {
    ensure_card_references(conn)?;
    let mut stmt = conn.prepare(
        "SELECT knowledge_id FROM card_references WHERE item_key=?1 ORDER BY knowledge_id",
    )?;
    let ids: Vec<String> = stmt
        .query_map([item_key], |r| r.get(0))?
        .collect::<Result<Vec<String>, _>>()?;
    let mut out = Vec::new();
    for id in ids {
        let active = crate::knowledge::is_knowledge_active(conn, &id).unwrap_or(false);
        out.push((id, active));
    }
    Ok(out)
}
