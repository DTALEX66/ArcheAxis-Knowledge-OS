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
        "SELECT CASE WHEN json_valid(outcome) THEN
             COALESCE(json_extract(outcome, '$.outcome') = 'correct',
                      json_type(outcome, '$.correct') = 'true', 0)
         ELSE 0 END FROM learning_events WHERE item_key=?1 ORDER BY event_id DESC",
    )?;
    let rows = stmt.query_map([item_key], |r| r.get::<_, bool>(0))?;
    let mut streak = 0u32;
    for row in rows {
        let is_correct = row?;
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

/// Exact worker state is appended to the review event, not a second card store.
pub struct ReviewSchedule {
    pub schedule_json: String,
    pub next_review: Option<String>,
    pub next_review_days: i64,
}

#[derive(Debug, PartialEq, Eq)]
pub struct ReviewReceipt {
    pub event_id: i64,
    pub streak_after: u32,
    pub next_review_days: i64,
    pub next_review: Option<String>,
    pub outcome_json: String,
    pub duplicate: bool,
}

// SQLite also accepts time-only and Julian-day values; constrain the wire form
// to Python's ISO date-time representation before SQLite calendar validation.
fn schedule_timestamp_shape(value: &str) -> bool {
    if !value.is_ascii() || value.len() < 20 || &value[..4] == "0000" { return false; }
    for (index, byte) in value.as_bytes()[..19].iter().enumerate() {
        let separator = match index { 4 | 7 => Some(b'-'), 10 => Some(b'T'), 13 | 16 => Some(b':'), _ => None };
        if separator.map_or(!byte.is_ascii_digit(), |expected| *byte != expected) { return false; }
    }
    let mut zone = &value[19..];
    if let Some(fraction) = zone.strip_prefix('.') {
        let digits = fraction.bytes().take_while(u8::is_ascii_digit).count();
        if !(1..=6).contains(&digits) { return false; }
        zone = &fraction[digits..];
    }
    if zone == "Z" { return true; }
    let bytes = zone.as_bytes();
    bytes.len() == 6 && matches!(bytes[0], b'+' | b'-') && bytes[3] == b':'
        && bytes[1..3].iter().chain(bytes[4..6].iter()).all(u8::is_ascii_digit)
        && zone[1..3].parse::<u8>().is_ok_and(|hour| hour < 24)
        && zone[4..6].parse::<u8>().is_ok_and(|minute| minute < 60)
}

pub fn valid_review_timestamp(conn: &Connection, value: &str) -> rusqlite::Result<bool> {
    if !schedule_timestamp_shape(value) { return Ok(false); }
    conn.query_row("SELECT COALESCE(strftime('%Y-%m-%dT%H:%M:%S',substr(?1,1,19),'+0 seconds')=substr(?1,1,19),0)",
        [value], |r| r.get(0))
}

/// Last successful FSRS state. An unscheduled event never erases it.
pub fn latest_fsrs_state_json(conn: &Connection, item_key: &str) -> rusqlite::Result<Option<String>> {
    conn.query_row(
        "SELECT json_extract(outcome, '$.schedule.state') FROM learning_events
         WHERE item_key=?1 AND CASE WHEN json_valid(outcome)
         THEN json_extract(outcome, '$.schedule.authority') = 'fsrs' ELSE 0 END
         ORDER BY event_id DESC LIMIT 1", [item_key], |r| r.get(0),
    ).optional()
}

/// Validate worker output before recording an explicit unscheduled fallback.
pub fn review_schedule_is_valid(conn: &Connection, schedule: &ReviewSchedule) -> rusqlite::Result<bool> {
    let valid_json: bool = conn.query_row("SELECT json_valid(?1)", [&schedule.schedule_json], |r| r.get(0))?;
    if !valid_json { return Ok(false); }
    let valid: bool = conn.query_row(
        "SELECT COALESCE(json_type(?1)='object' AND (
          (json_extract(?1,'$.authority')='unavailable' AND ?2 IS NULL AND ?3=-2)
          OR (json_extract(?1,'$.authority')='fsrs' AND ?3>=0
              AND json_type(?1,'$.state')='object'
              AND json_extract(?1,'$.state.due')=?2
              AND strftime('%Y-%m-%dT%H:%M:%S',substr(?2,1,19),'+0 seconds')=substr(?2,1,19)
              AND strftime('%Y-%m-%dT%H:%M:%S',substr(json_extract(?1,'$.state.last_review'),1,19),'+0 seconds')
                  =substr(json_extract(?1,'$.state.last_review'),1,19)
              AND json_extract(?1,'$.state.state') IN ('learning','review','relearning')
              AND json_type(?1,'$.state.step') IN ('integer','null')
              AND (json_extract(?1,'$.state.step') IS NULL OR json_extract(?1,'$.state.step')>=0)
              AND json_type(?1,'$.state.stability') IN ('real','integer')
              AND json_type(?1,'$.state.difficulty') IN ('real','integer')
              AND json_extract(?1,'$.state.stability')>0
              AND json_extract(?1,'$.state.difficulty') BETWEEN 1 AND 10)), 0)",
        rusqlite::params![schedule.schedule_json, schedule.next_review, schedule.next_review_days], |r| r.get(0),
    )?;
    if !valid { return Ok(false); }
    if let Some(due) = schedule.next_review.as_deref() {
        let (last_review, stability, difficulty): (String, f64, f64) = conn.query_row(
            "SELECT json_extract(?1,'$.state.last_review'), json_extract(?1,'$.state.stability'),
                    json_extract(?1,'$.state.difficulty')", [&schedule.schedule_json],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
        )?;
        if !schedule_timestamp_shape(due) || !schedule_timestamp_shape(&last_review)
            || !stability.is_finite() || !difficulty.is_finite() {
            return Ok(false);
        }
    }
    Ok(true)
}

/// Resolve scheduling under the writer transaction, after checking idempotency.
/// The caller supplies canonical request JSON, including any state/time/rating.
/// Old receipt hashes remain intact; this explicit stateful path has its own
/// hash domain and does not reinterpret or rewrite legacy events.
pub fn record_review_with_state(
    conn: &mut Connection,
    item_key: &str,
    kind: &str,
    correct: bool,
    client_event_key: &str,
    canonical_request: &str,
    resolve: impl FnOnce(&Connection) -> rusqlite::Result<ReviewSchedule>,
) -> rusqlite::Result<ReviewReceipt> {
    let invalid = |message: &str| rusqlite::Error::InvalidParameterName(message.into());
    if item_key.trim().is_empty() || client_event_key.trim().is_empty() {
        return Err(invalid("review requires item and persistent event key"));
    }
    let mut hash = Sha256::new();
    hash.update(b"archeaxis.learning-state/v1\0");
    for part in [kind, if correct { "correct" } else { "incorrect" }, canonical_request] {
        hash.update((part.len() as u64).to_le_bytes());
        hash.update(part.as_bytes());
    }
    let payload_hash = hex::encode(hash.finalize());
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let existing: Option<(String, Option<String>, ReviewReceipt)> = tx.query_row(
        "SELECT k.item_key, k.payload_hash, e.event_id, k.streak_after,
                k.next_review_days, e.next_review, e.outcome
         FROM learning_event_keys k JOIN learning_events e ON e.event_id=k.event_id
         WHERE k.event_key=?1", [client_event_key], |r| Ok((r.get(0)?, r.get(1)?, ReviewReceipt {
             event_id: r.get(2)?, streak_after: r.get::<_, i64>(3)? as u32,
             next_review_days: r.get::<_, Option<i64>>(4)?.unwrap_or(SCHEDULE_UNAVAILABLE),
             next_review: r.get(5)?, outcome_json: r.get(6)?, duplicate: true,
         })),
    ).optional()?;
    if let Some((stored_item, stored_hash, receipt)) = existing {
        if stored_item != item_key || stored_hash.as_deref() != Some(payload_hash.as_str()) {
            return Err(invalid("event_key conflict: different item or payload"));
        }
        return Ok(receipt);
    }
    // A legacy key without a complete receipt is not permission to resubmit it.
    let reserved: bool = tx.query_row("SELECT EXISTS(SELECT 1 FROM learning_event_keys WHERE event_key=?1)",
        [client_event_key], |r| r.get(0))?;
    if reserved { return Err(invalid("event_key conflict: incomplete legacy receipt")); }
    let schedule = resolve(&tx)?;
    if !review_schedule_is_valid(&tx, &schedule)? {
        return Err(invalid("schedule state or exact due date is inconsistent"));
    }
    let outcome_json: String = tx.query_row(
        "SELECT json_object('outcome', ?1, 'schedule', json(?2))",
        rusqlite::params![if correct { "correct" } else { "incorrect" }, schedule.schedule_json], |r| r.get(0),
    )?;
    let streak_after = if correct { correct_streak(&tx, item_key)? + 1 } else { 0 };
    tx.execute("INSERT INTO learning_events(item_key,kind,outcome,next_review) VALUES(?1,?2,?3,?4)",
        rusqlite::params![item_key, kind, outcome_json, schedule.next_review])?;
    let event_id = tx.last_insert_rowid();
    tx.execute("INSERT INTO learning_event_keys(event_key,item_key,payload_hash,event_id,streak_after,next_review_days)
                VALUES(?1,?2,?3,?4,?5,?6)",
        rusqlite::params![client_event_key,item_key,payload_hash,event_id,streak_after,schedule.next_review_days])?;
    tx.commit()?;
    Ok(ReviewReceipt { event_id, streak_after, next_review_days: schedule.next_review_days,
        next_review: schedule.next_review, outcome_json, duplicate: false })
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
