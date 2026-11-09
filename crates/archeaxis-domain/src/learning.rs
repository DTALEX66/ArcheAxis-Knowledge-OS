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

/// Assessment-bound reviews use only observations for that immutable assessment.
/// Unbound legacy reviews retain the existing item-wide behavior.
pub fn correct_streak_for_assessment(
    conn: &Connection,
    item_key: &str,
    assessment_id: Option<&str>,
) -> rusqlite::Result<u32> {
    let Some(assessment_id) = assessment_id else {
        return correct_streak(conn, item_key);
    };
    let mut stmt = conn.prepare(
        "SELECT COALESCE(json_extract(outcome, '$.outcome') = 'correct',
                         json_type(outcome, '$.correct') = 'true', 0)
         FROM learning_events WHERE item_key=?1 AND CASE WHEN json_valid(outcome)
         THEN json_extract(outcome, '$.assessment_id')=?2 ELSE 0 END ORDER BY event_id DESC",
    )?;
    let rows = stmt.query_map(rusqlite::params![item_key, assessment_id], |r| {
        r.get::<_, bool>(0)
    })?;
    let mut streak = 0u32;
    for row in rows {
        if row? {
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
    let next_review_days = if correct {
        suggest_next_interval(streak_after)
    } else {
        1
    };
    let outcome = format!(
        r#"{{"outcome": "{}"}}"#,
        if correct { "correct" } else { "incorrect" }
    );
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

/// Parse the two FSRS floating parameters through Rust's correctly rounded
/// f64 parser without changing other JSON or request-identity semantics.
pub fn parse_fsrs_card(raw: &str) -> Result<serde_json::Value, &'static str> {
    #[derive(serde::Deserialize)]
    struct NumericFields<'a> {
        #[serde(borrow)]
        stability: Option<&'a serde_json::value::RawValue>,
        #[serde(borrow)]
        difficulty: Option<&'a serde_json::value::RawValue>,
    }
    let fields: NumericFields = serde_json::from_str(raw).map_err(|_| "invalid FSRS card")?;
    let mut value: serde_json::Value =
        serde_json::from_str(raw).map_err(|_| "invalid FSRS card")?;
    if !value.is_object() {
        return Err("invalid FSRS card");
    }
    for (name, raw_number) in [
        ("stability", fields.stability),
        ("difficulty", fields.difficulty),
    ] {
        let Some(raw_number) = raw_number else {
            continue;
        };
        let current = &value[name];
        if !current.is_number() {
            return Err("invalid FSRS number");
        }
        if current.as_i64().is_some() || current.as_u64().is_some() {
            continue;
        }
        let exact: f64 = raw_number
            .get()
            .parse()
            .map_err(|_| "invalid FSRS number")?;
        value[name] = serde_json::Value::Number(
            serde_json::Number::from_f64(exact).ok_or("non-finite FSRS number")?,
        );
    }
    Ok(value)
}

pub fn precise_fsrs_state_from_schedule(raw: &str) -> Option<serde_json::Value> {
    #[derive(serde::Deserialize)]
    struct Schedule<'a> {
        #[serde(borrow)]
        state: Option<&'a serde_json::value::RawValue>,
    }
    let schedule: Schedule<'_> = serde_json::from_str(raw).ok()?;
    parse_fsrs_card(schedule.state?.get()).ok()
}

pub fn precise_fsrs_state_from_outcome(raw: &str) -> Option<serde_json::Value> {
    #[derive(serde::Deserialize)]
    struct Outcome<'a> {
        #[serde(borrow)]
        schedule: Option<&'a serde_json::value::RawValue>,
    }
    let outcome: Outcome<'_> = serde_json::from_str(raw).ok()?;
    precise_fsrs_state_from_schedule(outcome.schedule?.get())
}

pub fn precise_fsrs_projection_from_outcome(raw: &str) -> Option<serde_json::Value> {
    #[derive(serde::Deserialize)]
    struct Outcome<'a> {
        #[serde(borrow)]
        mastery_projection: Option<&'a serde_json::value::RawValue>,
    }
    let outcome: Outcome<'_> = serde_json::from_str(raw).ok()?;
    parse_fsrs_card(outcome.mastery_projection?.get()).ok()
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

/// A rebuildable learner-state projection. It is deliberately marked open:
/// review observations and FSRS scheduling do not establish Knowledge truth
/// or a closed mastery claim.
/// What the learner actually did, re-derived from the event log alone.
///
/// These are counts and timestamps, not judgements. Nothing here needs a competence ledger, and
/// reporting them is what lets the product show progress without closing a mastery claim.
fn learner_observation(
    conn: &Connection,
    item_key: &str,
    assessment_id: Option<&str>,
) -> rusqlite::Result<(u32, u32, Option<String>)> {
    conn.query_row(
        "SELECT
             count(*),
             count(DISTINCT CASE WHEN COALESCE(json_extract(outcome, '$.outcome') = 'correct',
                                               json_type(outcome, '$.correct') = 'true', 0)
                                 THEN date(created_at) END),
             max(CASE WHEN COALESCE(json_extract(outcome, '$.outcome') = 'correct',
                                    json_type(outcome, '$.correct') = 'true', 0)
                      THEN created_at END)
         FROM learning_events
         WHERE item_key = ?1 AND json_valid(outcome)
           AND (?2 IS NULL OR json_extract(outcome, '$.assessment_id') = ?2)",
        rusqlite::params![item_key, assessment_id],
        |r| {
            let attempts: i64 = r.get(0)?;
            let days: i64 = r.get(1)?;
            let last: Option<String> = r.get(2)?;
            Ok((attempts.max(0) as u32, days.max(0) as u32, last))
        },
    )
}

fn mastery_projection_json(
    schedule_json: &str,
    correct_streak: u32,
    attempts: u32,
    distinct_correct_days: u32,
    last_correct_at: Option<&str>,
    next_review_at: Option<&str>,
) -> String {
    let schedule: serde_json::Value =
        serde_json::from_str(schedule_json).unwrap_or_else(|_| serde_json::json!({}));
    let card = precise_fsrs_state_from_schedule(schedule_json)
        .unwrap_or_else(|| schedule["state"].clone());
    serde_json::json!({
        "status": "projection",
        "closed": false,
        "basis": "fsrs_review_state_and_learner_observation",
        "review_state": card["state"],
        "stability": card["stability"],
        "correct_streak": correct_streak,
        // Counts and times the learner can recognise, added so the product can show progress
        // without claiming mastery. They say what happened, never what it means.
        "attempts": attempts,
        "distinct_correct_days": distinct_correct_days,
        "last_correct_at": last_correct_at,
        "next_review_at": next_review_at,
    })
    .to_string()
}

/// Core-owned assessment snapshot bound to one learning item and one accepted
/// Knowledge revision. The content is a snapshot of what the learner saw;
/// answer/rating/correct observations never become Truth or Mastery here.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AssessmentRecord {
    pub assessment_id: String,
    pub item_key: String,
    pub knowledge_id: String,
    pub knowledge_version: String,
    pub question: String,
    pub content: String,
    pub source_id: Option<String>,
    pub anchor_id: Option<String>,
    pub created_at: String,
}

// SQLite also accepts time-only and Julian-day values; constrain the wire form
// to Python's ISO date-time representation before SQLite calendar validation.
fn schedule_timestamp_shape(value: &str) -> bool {
    if !value.is_ascii() || value.len() < 20 || &value[..4] == "0000" {
        return false;
    }
    for (index, byte) in value.as_bytes()[..19].iter().enumerate() {
        let separator = match index {
            4 | 7 => Some(b'-'),
            10 => Some(b'T'),
            13 | 16 => Some(b':'),
            _ => None,
        };
        if separator.map_or(!byte.is_ascii_digit(), |expected| *byte != expected) {
            return false;
        }
    }
    let mut zone = &value[19..];
    if let Some(fraction) = zone.strip_prefix('.') {
        let digits = fraction.bytes().take_while(u8::is_ascii_digit).count();
        if !(1..=6).contains(&digits) {
            return false;
        }
        zone = &fraction[digits..];
    }
    if zone == "Z" {
        return true;
    }
    let bytes = zone.as_bytes();
    bytes.len() == 6
        && matches!(bytes[0], b'+' | b'-')
        && bytes[3] == b':'
        && bytes[1..3]
            .iter()
            .chain(bytes[4..6].iter())
            .all(u8::is_ascii_digit)
        && zone[1..3].parse::<u8>().is_ok_and(|hour| hour < 24)
        && zone[4..6].parse::<u8>().is_ok_and(|minute| minute < 60)
}

pub fn valid_review_timestamp(conn: &Connection, value: &str) -> rusqlite::Result<bool> {
    if !schedule_timestamp_shape(value) {
        return Ok(false);
    }
    conn.query_row("SELECT COALESCE(strftime('%Y-%m-%dT%H:%M:%S',substr(?1,1,19),'+0 seconds')=substr(?1,1,19),0)",
        [value], |r| r.get(0))
}

/// Preserve microsecond ordering and timezone offsets without using SQLite's
/// millisecond-rounded Julian-day representation. The calendar is validated
/// by the same rule as the HTTP request before parsing the bounded suffix.
pub fn review_timestamp_micros(conn: &Connection, value: &str) -> rusqlite::Result<Option<i64>> {
    if !valid_review_timestamp(conn, value)? {
        return Ok(None);
    }
    let seconds: Option<i64> = conn.query_row(
        "SELECT CAST(strftime('%s',substr(?1,1,19)) AS INTEGER)",
        [value],
        |row| row.get(0),
    )?;
    let Some(seconds) = seconds else {
        return Ok(None);
    };
    let mut zone = &value[19..];
    let mut micros = 0_i64;
    if let Some(fraction) = zone.strip_prefix('.') {
        let digits = fraction.bytes().take_while(u8::is_ascii_digit).count();
        let Some(parsed) = fraction[..digits].parse::<i64>().ok() else {
            return Ok(None);
        };
        micros = parsed * 10_i64.pow((6 - digits) as u32);
        zone = &fraction[digits..];
    }
    let offset = if zone == "Z" {
        0
    } else {
        let (Some(hour), Some(minute)) = (
            zone[1..3].parse::<i64>().ok(),
            zone[4..6].parse::<i64>().ok(),
        ) else {
            return Ok(None);
        };
        (hour * 60 + minute) * 60 * if zone.as_bytes()[0] == b'+' { 1 } else { -1 }
    };
    Ok(seconds
        .checked_sub(offset)
        .and_then(|s| s.checked_mul(1_000_000))
        .and_then(|s| s.checked_add(micros)))
}

/// Last successful FSRS state. An unscheduled event never erases it. A row
/// claiming FSRS but lacking an object state stays present as invalid `null`,
/// rather than being mistaken for no history or causing a SQL type error.
pub fn latest_fsrs_state_json(
    conn: &Connection,
    item_key: &str,
) -> rusqlite::Result<Option<String>> {
    conn.query_row(
        "SELECT CASE WHEN json_type(outcome, '$.schedule.state')='object'
                THEN json_extract(outcome, '$.schedule.state') ELSE 'null' END FROM learning_events
         WHERE item_key=?1 AND CASE WHEN json_valid(outcome)
         THEN json_extract(outcome, '$.schedule.authority') = 'fsrs' ELSE 0 END
         ORDER BY event_id DESC LIMIT 1",
        [item_key],
        |r| r.get(0),
    )
    .optional()
}

/// Read only the FSRS state bound to this assessment. Unknown/legacy outcomes
/// cannot be inferred to belong to a later assessment of the same item.
pub fn latest_fsrs_state_for_assessment(
    conn: &Connection,
    item_key: &str,
    assessment_id: Option<&str>,
) -> rusqlite::Result<Option<String>> {
    let Some(assessment_id) = assessment_id else {
        return latest_fsrs_state_json(conn, item_key);
    };
    conn.query_row(
        "SELECT CASE WHEN json_type(outcome, '$.schedule.state')='object'
                THEN json_extract(outcome, '$.schedule.state') ELSE 'null' END FROM learning_events
         WHERE item_key=?1 AND CASE WHEN json_valid(outcome) THEN
           json_extract(outcome, '$.schedule.authority')='fsrs'
           AND json_extract(outcome, '$.assessment_id')=?2 ELSE 0 END
         ORDER BY event_id DESC LIMIT 1",
        rusqlite::params![item_key, assessment_id],
        |r| r.get(0),
    )
    .optional()
}

/// Recoverable unscheduled observations following the last persisted FSRS card.
/// Existing events are never rewritten; missing evidence is not inferred.
pub struct PendingScheduleReview {
    pub event_id: i64,
    pub rating: u8,
    pub reviewed_at: String,
}

pub struct ReviewScheduleBasis {
    pub previous_state: Option<String>,
    pub latest_event_id: Option<i64>,
    pub latest_reviewed_at_micros: Option<i64>,
    pub baseline_reset_event_id: Option<i64>,
    pub pending: Vec<PendingScheduleReview>,
    pub recovery_issue: Option<&'static str>,
}

const MAX_PENDING_SCHEDULE_REVIEWS: usize = 4096;

/// The cursor also changes for unavailable reviews, which do not advance the
/// last successful card state but must still invalidate an in-flight snapshot.
pub fn latest_review_event_id(
    conn: &Connection,
    item_key: &str,
    assessment_id: Option<&str>,
) -> rusqlite::Result<Option<i64>> {
    conn.query_row(
        "SELECT MAX(event_id) FROM learning_events WHERE item_key=?1
         AND (?2 IS NULL OR CASE WHEN json_valid(outcome)
              THEN json_extract(outcome,'$.assessment_id')=?2 ELSE 0 END)",
        rusqlite::params![item_key, assessment_id],
        |r| r.get(0),
    )
}

pub fn review_schedule_basis(
    conn: &Connection,
    item_key: &str,
    assessment_id: Option<&str>,
) -> rusqlite::Result<ReviewScheduleBasis> {
    let previous_state = latest_fsrs_state_for_assessment(conn, item_key, assessment_id)?;
    let latest_event_id = latest_review_event_id(conn, item_key, assessment_id)?;
    let last_scheduled_id: Option<i64> = conn.query_row(
        "SELECT MAX(event_id) FROM learning_events WHERE item_key=?1 AND CASE WHEN json_valid(outcome)
         THEN json_extract(outcome,'$.schedule.authority')='fsrs'
          AND (?2 IS NULL OR json_extract(outcome,'$.assessment_id')=?2) ELSE 0 END",
        rusqlite::params![item_key, assessment_id],
        |r| r.get(0),
    )?;
    // A human-declared new baseline is append-only and only exists after a
    // successful FSRS result. Its metadata remains visible to later consumers.
    let baseline_reset_event_id: Option<i64> = conn.query_row(
        "SELECT MAX(event_id) FROM learning_events WHERE item_key=?1 AND event_id>0 AND CASE WHEN json_valid(outcome)
         THEN (?2 IS NULL OR json_extract(outcome,'$.assessment_id')=?2)
          AND json_extract(outcome,'$.review_evidence.schedule_reset.mode')='start_new'
          AND json_type(outcome,'$.review_evidence.schedule_reset.reason')='text'
          AND length(trim(json_extract(outcome,'$.review_evidence.schedule_reset.reason'))) BETWEEN 1 AND 512
          AND json_extract(outcome,'$.schedule.recovery.mode')='start_new'
          AND json_extract(outcome,'$.schedule.recovery.reason')=json_extract(outcome,'$.review_evidence.schedule_reset.reason')
          AND json_type(outcome,'$.review_evidence.schedule_reset.expected_latest_event_id')='integer'
          AND json_extract(outcome,'$.review_evidence.schedule_reset.expected_latest_event_id') BETWEEN 1 AND 9007199254740991
          AND json_extract(outcome,'$.review_evidence.schedule_reset.expected_latest_event_id') < event_id
          AND json_extract(outcome,'$.schedule.recovery.excluded_through_event_id')=json_extract(outcome,'$.review_evidence.schedule_reset.expected_latest_event_id')
          AND json_extract(outcome,'$.schedule.authority')='fsrs'
          AND json_extract(outcome,'$.schedule.recovery.state')='reset'
         ELSE 0 END",
        rusqlite::params![item_key, assessment_id],
        |r| r.get(0),
    )?;
    // Legacy review events can preserve the outcome while lacking the exact
    // time, rating and FSRS card needed to include them in a stateful history.
    // Look back to the last explicit baseline, not just the last FSRS card:
    // an older Core may already have produced that card while skipping a gap.
    let legacy_gap: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM learning_events WHERE item_key=?1 AND kind='review'
         AND event_id>COALESCE(?3,0) AND CASE WHEN json_valid(outcome) THEN
           (?2 IS NULL OR json_extract(outcome,'$.assessment_id')=?2)
           AND (json_type(outcome,'$.schedule') IS NOT 'object'
                OR json_type(outcome,'$.schedule.authority') IS NOT 'text'
                OR json_extract(outcome,'$.schedule.authority') NOT IN ('fsrs','unavailable'))
         ELSE ?2 IS NULL END)",
        rusqlite::params![item_key, assessment_id, baseline_reset_event_id],
        |r| r.get(0),
    )?;
    let mut stmt = conn.prepare(
        "SELECT event_id,outcome FROM learning_events WHERE item_key=?1 AND event_id>COALESCE(?3,0)
         AND CASE WHEN json_valid(outcome) THEN json_extract(outcome,'$.schedule.authority')='unavailable'
           AND (?2 IS NULL OR json_extract(outcome,'$.assessment_id')=?2) ELSE 0 END
         ORDER BY event_id LIMIT 4097",
    )?;
    let mut rows = stmt.query(rusqlite::params![
        item_key,
        assessment_id,
        last_scheduled_id
    ])?;
    let mut pending = Vec::new();
    let mut recovery_issue = legacy_gap.then_some("legacy_review_evidence_missing_or_invalid");
    let mut latest_reviewed_at_micros = None;
    if let Some(raw) = previous_state.as_deref() {
        let previous = parse_fsrs_card(raw).ok();
        let previous_time = previous
            .as_ref()
            .and_then(|value| value["last_review"].as_str());
        latest_reviewed_at_micros = match previous_time {
            Some(time) => review_timestamp_micros(conn, time)?,
            None => None,
        };
        if latest_reviewed_at_micros.is_none() && recovery_issue.is_none() {
            recovery_issue = Some("invalid_previous_card");
        }
    }
    while let Some(row) = rows.next()? {
        if recovery_issue.is_some() {
            break;
        }
        if pending.len() == MAX_PENDING_SCHEDULE_REVIEWS {
            recovery_issue = Some("too_many_unscheduled_reviews");
            break;
        }
        let event_id: i64 = row.get(0)?;
        let raw: String = row.get(1)?;
        let value: serde_json::Value = serde_json::from_str(&raw).unwrap_or_default();
        let rating = value["review_evidence"]["rating"].as_u64();
        let outcome = value["outcome"].as_str();
        let time = value["schedule"]["reviewed_at"]
            .as_str()
            .or_else(|| value["review_evidence"]["now"].as_str());
        let valid_rating = matches!(
            (rating, outcome),
            (Some(1), Some("incorrect")) | (Some(2..=4), Some("correct"))
        );
        let instant = match time {
            Some(time) => review_timestamp_micros(conn, time)?,
            None => None,
        };
        if event_id <= 0 || !valid_rating || instant.is_none() {
            recovery_issue = Some("unscheduled_review_evidence_missing_or_invalid");
            break;
        }
        if latest_reviewed_at_micros.is_some_and(|previous| instant.unwrap() < previous) {
            recovery_issue = Some("unscheduled_review_time_order_invalid");
            break;
        }
        latest_reviewed_at_micros = instant;
        pending.push(PendingScheduleReview {
            event_id,
            rating: rating.unwrap() as u8,
            reviewed_at: time.unwrap().to_owned(),
        });
    }
    Ok(ReviewScheduleBasis {
        previous_state,
        latest_event_id,
        latest_reviewed_at_micros,
        baseline_reset_event_id,
        pending,
        recovery_issue,
    })
}

/// Validate worker output before recording an explicit unscheduled fallback.
pub fn review_schedule_is_valid(
    conn: &Connection,
    schedule: &ReviewSchedule,
) -> rusqlite::Result<bool> {
    let valid_json: bool =
        conn.query_row("SELECT json_valid(?1)", [&schedule.schedule_json], |r| {
            r.get(0)
        })?;
    if !valid_json {
        return Ok(false);
    }
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
    if !valid {
        return Ok(false);
    }
    if let Some(due) = schedule.next_review.as_deref() {
        let (last_review, stability, difficulty): (String, f64, f64) = conn.query_row(
            "SELECT json_extract(?1,'$.state.last_review'), json_extract(?1,'$.state.stability'),
                    json_extract(?1,'$.state.difficulty')",
            [&schedule.schedule_json],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
        )?;
        if !schedule_timestamp_shape(due)
            || !schedule_timestamp_shape(&last_review)
            || !stability.is_finite()
            || !difficulty.is_finite()
        {
            return Ok(false);
        }
        let (Some(due_instant), Some(review_instant)) = (
            review_timestamp_micros(conn, due)?,
            review_timestamp_micros(conn, &last_review)?,
        ) else {
            return Ok(false);
        };
        let Some(elapsed) = due_instant.checked_sub(review_instant) else {
            return Ok(false);
        };
        if elapsed < 0 || elapsed / 86_400_000_000 != schedule.next_review_days {
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
    record_review_with_state_and_answer(
        conn,
        item_key,
        kind,
        correct,
        client_event_key,
        canonical_request,
        None,
        None,
        None,
        resolve,
    )
}

fn stateful_review_hash(kind: &str, correct: bool, canonical_request: &str) -> String {
    let mut hash = Sha256::new();
    hash.update(b"archeaxis.learning-state/v1\0");
    for part in [
        kind,
        if correct { "correct" } else { "incorrect" },
        canonical_request,
    ] {
        hash.update((part.len() as u64).to_le_bytes());
        hash.update(part.as_bytes());
    }
    hex::encode(hash.finalize())
}

/// Read an already committed stateful receipt without invoking a scheduler.
/// This check is repeated under the write transaction when a new event is
/// committed, so concurrent requests still cannot create duplicate events.
pub fn existing_stateful_review(
    conn: &Connection,
    item_key: &str,
    kind: &str,
    correct: bool,
    client_event_key: &str,
    canonical_request: &str,
) -> rusqlite::Result<Option<ReviewReceipt>> {
    let payload_hash = stateful_review_hash(kind, correct, canonical_request);
    let existing: Option<(String, Option<String>, ReviewReceipt)> = conn
        .query_row(
            "SELECT k.item_key, k.payload_hash, e.event_id, k.streak_after,
                k.next_review_days, e.next_review, e.outcome
             FROM learning_event_keys k JOIN learning_events e ON e.event_id=k.event_id
             WHERE k.event_key=?1",
            [client_event_key],
            |r| {
                Ok((
                    r.get(0)?,
                    r.get(1)?,
                    ReviewReceipt {
                        event_id: r.get(2)?,
                        streak_after: r.get::<_, i64>(3)? as u32,
                        next_review_days: r
                            .get::<_, Option<i64>>(4)?
                            .unwrap_or(SCHEDULE_UNAVAILABLE),
                        next_review: r.get(5)?,
                        outcome_json: r.get(6)?,
                        duplicate: true,
                    },
                ))
            },
        )
        .optional()?;
    if let Some((stored_item, stored_hash, receipt)) = existing {
        if stored_item != item_key || stored_hash.as_deref() != Some(payload_hash.as_str()) {
            return Err(rusqlite::Error::InvalidParameterName(
                "event_key conflict: different item or payload".into(),
            ));
        }
        return Ok(Some(receipt));
    }
    let reserved: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM learning_event_keys WHERE event_key=?1)",
        [client_event_key],
        |r| r.get(0),
    )?;
    if reserved {
        return Err(rusqlite::Error::InvalidParameterName(
            "event_key conflict: incomplete legacy receipt".into(),
        ));
    }
    Ok(None)
}

/// Record a stateful review and retain the learner's submitted answer in the
/// append-only receipt. The answer is evidence of what the learner entered;
/// it does not assert that the answer is true or that mastery was achieved.
pub fn record_review_with_state_and_answer(
    conn: &mut Connection,
    item_key: &str,
    kind: &str,
    correct: bool,
    client_event_key: &str,
    canonical_request: &str,
    answer: Option<&str>,
    assessment_id: Option<&str>,
    expected_previous_fsrs_state: Option<Option<String>>,
    resolve: impl FnOnce(&Connection) -> rusqlite::Result<ReviewSchedule>,
) -> rusqlite::Result<ReviewReceipt> {
    let invalid = |message: &str| rusqlite::Error::InvalidParameterName(message.into());
    if item_key.trim().is_empty() || client_event_key.trim().is_empty() {
        return Err(invalid("review requires item and persistent event key"));
    }
    if answer.is_some_and(|value| value.trim().is_empty()) {
        return Err(invalid("submitted answer must not be empty"));
    }
    if assessment_id.is_some_and(|value| value.trim().is_empty()) {
        return Err(invalid("assessment_id must not be empty"));
    }
    let payload_hash = stateful_review_hash(kind, correct, canonical_request);
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    if let Some(receipt) = existing_stateful_review(
        &tx,
        item_key,
        kind,
        correct,
        client_event_key,
        canonical_request,
    )? {
        return Ok(receipt);
    }
    // A new schedule-only legacy review cannot name an assessment. Once an
    // assessment exists, accepting it would return a due date that the
    // assessment-scoped queue cannot use. Check inside the write transaction,
    // after duplicate replay, so a concurrently created assessment is seen
    // and an already committed legacy receipt stays replayable.
    if assessment_id.is_none() && assessment_for_item_key(&tx, item_key)?.is_some() {
        return Err(invalid(
            "assessment binding conflict: this item requires an assessment_id for a new review",
        ));
    }
    // When the caller scheduled outside the writer, its schedule was computed from a card snapshot.
    // Confirm that snapshot is still current before recording it, so a review that moved the card in
    // the interim cannot be silently overwritten by a stale schedule.
    if let Some(expected_basis) = expected_previous_fsrs_state {
        if latest_fsrs_state_for_assessment(&tx, item_key, assessment_id)? != expected_basis {
            return Err(invalid(
                "schedule basis conflict: review state moved during scheduling",
            ));
        }
    }
    let schedule = resolve(&tx)?;
    if !review_schedule_is_valid(&tx, &schedule)? {
        return Err(invalid("schedule state or exact due date is inconsistent"));
    }
    let streak_after = if correct {
        correct_streak_for_assessment(&tx, item_key, assessment_id)? + 1
    } else {
        0
    };
    // The projection describes the learner *after* this review, so it is derived once the event
    // is on record. Deriving it first would report the state before the review being recorded -
    // which is exactly the off-by-one the contract test caught.
    // Retain the request's version/exposure/assistance evidence, not just its dedup hash.
    // These are observations; they neither approve a rubric nor establish human mastery.
    // Old non-JSON domain callers and old stored events remain readable as unrecorded evidence.
    let request = serde_json::from_str::<serde_json::Value>(canonical_request).ok();
    let evidence = request
        .filter(|value| value.is_object())
        .map(|value| {
            let mut fields = serde_json::Map::new();
            fields.insert(
                "schema".into(),
                serde_json::json!("archeaxis.learning-review-evidence/v2"),
            );
            for key in [
                "question_version",
                "knowledge_version",
                "exposure_id",
                "assist_strategy",
                "rating_version",
                "correction_id",
                "rating",
                "correct",
                "now",
            ] {
                fields.insert(
                    key.into(),
                    value.get(key).cloned().unwrap_or(serde_json::Value::Null),
                );
            }
            if let Some(reset) = value.get("schedule_reset") {
                fields.insert("schedule_reset".into(), reset.clone());
            }
            serde_json::Value::Object(fields)
        })
        .unwrap_or(serde_json::Value::Null)
        .to_string();
    let outcome_json: String = tx.query_row(
        "SELECT json_object('outcome', ?1, 'schedule', json(?2), 'answer', ?3, 'assessment_id', ?4, 'review_evidence', json(?5))",
        rusqlite::params![if correct { "correct" } else { "incorrect" }, schedule.schedule_json, answer, assessment_id, evidence],
        |r| r.get(0),
    )?;
    tx.execute(
        "INSERT INTO learning_events(item_key,kind,outcome,next_review) VALUES(?1,?2,?3,?4)",
        rusqlite::params![item_key, kind, outcome_json, schedule.next_review],
    )?;
    let event_id = tx.last_insert_rowid();
    let (attempts, distinct_correct_days, last_correct_at) =
        learner_observation(&tx, item_key, assessment_id)?;
    let mastery_projection = mastery_projection_json(
        &schedule.schedule_json,
        streak_after,
        attempts,
        distinct_correct_days,
        last_correct_at.as_deref(),
        schedule.next_review.as_deref(),
    );
    tx.execute(
        "UPDATE learning_events SET outcome = json_set(outcome, '$.mastery_projection', json(?1)) WHERE event_id = ?2",
        rusqlite::params![mastery_projection, event_id],
    )?;
    tx.execute("INSERT INTO learning_event_keys(event_key,item_key,payload_hash,event_id,streak_after,next_review_days)
                VALUES(?1,?2,?3,?4,?5,?6)",
        rusqlite::params![client_event_key,item_key,payload_hash,event_id,streak_after,schedule.next_review_days])?;
    // The receipt carries the row as stored, so a caller reading the projection gets the same
    // value a later read of the event would.
    let stored_outcome: String = tx.query_row(
        "SELECT outcome FROM learning_events WHERE event_id = ?1",
        [event_id],
        |r| r.get(0),
    )?;
    tx.commit()?;
    Ok(ReviewReceipt {
        event_id,
        streak_after,
        next_review_days: schedule.next_review_days,
        next_review: schedule.next_review,
        outcome_json: stored_outcome,
        duplicate: false,
    })
}

/// Receipt for the legacy HTTP event route. New events bind the complete
/// accepted request and the original scheduling authority; older keys did
/// not record those inputs and are explicitly reported as limited evidence.
#[derive(Debug)]
pub struct HttpLearningEventReceipt {
    pub event_id: i64,
    pub streak_after: u32,
    pub next_review_days: i64,
    pub duplicate: bool,
    pub schedule_authority: &'static str,
    pub idempotency_scope: &'static str,
}

fn legacy_event_outcome(correct: bool, unavailable: bool) -> String {
    let outcome = if correct { "correct" } else { "incorrect" };
    if unavailable {
        format!(r#"{{"outcome": "{outcome}", "schedule": "unavailable"}}"#)
    } else {
        format!(r#"{{"outcome": "{outcome}"}}"#)
    }
}

fn legacy_event_hash(kind: &str, outcome: &str) -> String {
    let mut hash = Sha256::new();
    hash.update(format!("{kind}|{outcome}").as_bytes());
    hex::encode(hash.finalize())
}

fn http_learning_event_hash(canonical_request: &str) -> String {
    let mut hash = Sha256::new();
    hash.update(b"archeaxis.learning-event-http/v2\0");
    hash.update(canonical_request.as_bytes());
    hex::encode(hash.finalize())
}

/// Read an HTTP legacy event receipt before invoking the scheduler. For old
/// keys only item, kind and outcome can be verified; schedule inputs were not
/// stored and must not be claimed as verified after an upgrade.
pub fn existing_http_learning_event(
    conn: &Connection,
    item_key: &str,
    kind: &str,
    correct: bool,
    client_event_key: &str,
    canonical_request: &str,
) -> rusqlite::Result<Option<HttpLearningEventReceipt>> {
    let row: Option<(
        String,
        Option<String>,
        Option<i64>,
        Option<i64>,
        Option<i64>,
    )> = conn
        .query_row(
            "SELECT k.item_key,k.payload_hash,k.event_id,k.streak_after,k.next_review_days
             FROM learning_event_keys k JOIN learning_events e ON e.event_id=k.event_id
             WHERE k.event_key=?1",
            [client_event_key],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?)),
        )
        .optional()?;
    let Some((stored_item, stored_hash, event_id, streak, stored_days)) = row else {
        let reserved: bool = conn.query_row(
            "SELECT EXISTS(SELECT 1 FROM learning_event_keys WHERE event_key=?1)",
            [client_event_key],
            |r| r.get(0),
        )?;
        if reserved {
            return Err(rusqlite::Error::InvalidParameterName(
                "event_key conflict: incomplete legacy receipt".into(),
            ));
        }
        return Ok(None);
    };
    let conflict = || {
        rusqlite::Error::InvalidParameterName(
            "event_key conflict: key is already bound to a different item or payload".into(),
        )
    };
    if stored_item != item_key {
        return Err(conflict());
    }
    let stored_hash = stored_hash.ok_or_else(conflict)?;
    let (authority, scope) = if let Some(binding) = stored_hash.strip_prefix("http-event-v2:") {
        let (authority, hash) = binding.split_once(':').ok_or_else(conflict)?;
        if hash != http_learning_event_hash(canonical_request) {
            return Err(conflict());
        }
        let authority = match authority {
            "fsrs" => "fsrs",
            "unavailable" => "unavailable",
            "placeholder_ladder" => "placeholder_ladder",
            _ => return Err(conflict()),
        };
        (authority, "full_request")
    } else if stored_hash == legacy_event_hash(kind, &legacy_event_outcome(correct, true)) {
        ("unavailable", "legacy_item_kind_outcome")
    } else if stored_hash == legacy_event_hash(kind, &legacy_event_outcome(correct, false)) {
        ("legacy_unverified", "legacy_item_kind_outcome")
    } else {
        return Err(conflict());
    };
    let next_review_days = match (authority, stored_days) {
        ("unavailable", None) => SCHEDULE_UNAVAILABLE,
        (_, Some(days)) => days,
        _ => return Err(conflict()),
    };
    Ok(Some(HttpLearningEventReceipt {
        event_id: event_id.ok_or_else(conflict)?,
        streak_after: u32::try_from(streak.ok_or_else(conflict)?).map_err(|_| conflict())?,
        next_review_days,
        duplicate: true,
        schedule_authority: authority,
        idempotency_scope: scope,
    }))
}

fn record_review_keyed_impl(
    conn: &mut Connection,
    item_key: &str,
    kind: &str,
    correct: bool,
    client_event_key: &str,
    schedule: ScheduleSource,
    canonical_request: Option<&str>,
) -> rusqlite::Result<HttpLearningEventReceipt> {
    if client_event_key.trim().is_empty() {
        return Err(rusqlite::Error::InvalidParameterName(
            "learning events require a persistent event_key; unkeyed submissions are rejected"
                .into(),
        ));
    }
    let authority = match schedule {
        ScheduleSource::Ladder => "placeholder_ladder",
        ScheduleSource::Explicit(Some(_)) => "fsrs",
        ScheduleSource::Explicit(None) => "unavailable",
    };
    let outcome = legacy_event_outcome(correct, schedule == ScheduleSource::Explicit(None));
    let payload_hash = match canonical_request {
        Some(request) => format!(
            "http-event-v2:{authority}:{}",
            http_learning_event_hash(request)
        ),
        None => legacy_event_hash(kind, &outcome),
    };
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    if let Some(request) = canonical_request {
        if let Some(receipt) =
            existing_http_learning_event(&tx, item_key, kind, correct, client_event_key, request)?
        {
            return Ok(receipt);
        }
    } else {
        let existing: Option<(
            Option<i64>,
            Option<String>,
            Option<i64>,
            Option<i64>,
            String,
        )> = tx
            .query_row(
                "SELECT event_id, payload_hash, streak_after, next_review_days, item_key
             FROM learning_event_keys WHERE event_key=?1",
                [client_event_key],
                |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?)),
            )
            .optional()?;
        if let Some((event_id, stored_hash, stored_streak, stored_days, stored_item)) = existing {
            if stored_item == item_key && stored_hash.as_deref() == Some(payload_hash.as_str()) {
                // Same retry: replay the original receipt, write nothing.
                return Ok(HttpLearningEventReceipt {
                    event_id: event_id.unwrap_or(0),
                    streak_after: stored_streak.unwrap_or(0) as u32,
                    next_review_days: stored_days.unwrap_or(-1),
                    duplicate: true,
                    schedule_authority: authority,
                    idempotency_scope: "legacy_internal",
                });
            }
            return Err(rusqlite::Error::InvalidParameterName(
                "event_key conflict: key is already bound to a different item or payload".into(),
            ));
        }
    }
    if canonical_request.is_some()
        && matches!(schedule, ScheduleSource::Explicit(Some(days)) if days < 0)
    {
        return Err(rusqlite::Error::InvalidParameterName(
            "scheduler interval must not be negative".into(),
        ));
    }
    // The legacy events endpoint cannot bind a review to an assessment. Keep
    // historical retries replayable, but refuse a new review once an
    // assessment exists instead of reporting a deadline the queue ignores.
    // Other event kinds continue to be stored as item history.
    if kind == "review" && assessment_for_item_key(&tx, item_key)?.is_some() {
        return Err(rusqlite::Error::InvalidParameterName(
            "assessment binding conflict: use the assessment-bound reviews endpoint".into(),
        ));
    }
    let prior = correct_streak(&tx, item_key)?;
    let streak_after = if correct { prior + 1 } else { 0 };
    let next_review_days = match schedule {
        ScheduleSource::Ladder => {
            if correct {
                suggest_next_interval(streak_after)
            } else {
                1
            }
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
    Ok(HttpLearningEventReceipt {
        event_id,
        streak_after,
        next_review_days,
        duplicate: false,
        schedule_authority: authority,
        idempotency_scope: if canonical_request.is_some() {
            "full_request"
        } else {
            "legacy_internal"
        },
    })
}

/// Commit a legacy HTTP event, binding its normalized request and original
/// scheduler outcome atomically with the event key. A lookup is repeated inside
/// the transaction because another request can finish while scheduling runs.
pub fn record_http_learning_event(
    conn: &mut Connection,
    item_key: &str,
    kind: &str,
    correct: bool,
    client_event_key: &str,
    canonical_request: &str,
    schedule: ScheduleSource,
) -> rusqlite::Result<HttpLearningEventReceipt> {
    record_review_keyed_impl(
        conn,
        item_key,
        kind,
        correct,
        client_event_key,
        schedule,
        Some(canonical_request),
    )
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
        None,
    )
    .map(|r| (r.event_id, r.streak_after, r.next_review_days, r.duplicate))
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
        None,
    )
    .map(|r| (r.event_id, r.streak_after, r.next_review_days, r.duplicate))
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

/// Read only review events explicitly bound to one immutable assessment.
pub fn events_for_assessment(
    conn: &Connection,
    item_key: &str,
    assessment_id: &str,
) -> rusqlite::Result<Vec<(i64, String, String, Option<String>)>> {
    let mut stmt = conn.prepare(
        "SELECT event_id, kind, outcome, next_review FROM learning_events
         WHERE item_key=?1 AND CASE WHEN json_valid(outcome)
         THEN json_extract(outcome, '$.assessment_id')=?2 ELSE 0 END ORDER BY event_id ASC",
    )?;
    let rows = stmt.query_map(rusqlite::params![item_key, assessment_id], |row| {
        Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?))
    })?;
    rows.collect()
}

/// Return each referenced item once. With an assessment, its deadline comes
/// only from a review explicitly bound to the latest assessment. Unbound legacy
/// items retain their item-wide deadline. No review or mastery is inferred.
pub fn item_keys_with_latest_review(
    conn: &Connection,
) -> rusqlite::Result<Vec<(String, Option<String>)>> {
    ensure_card_references(conn)?;
    let mut stmt = conn.prepare(
        "SELECT items.item_key, latest.next_review
         FROM (
             SELECT item_key FROM card_references
             UNION
             SELECT item_key FROM learning_assessments
             UNION
             SELECT item_key FROM learning_events
         ) items
         LEFT JOIN learning_events latest
           ON latest.event_id = (
               SELECT MAX(event_id) FROM learning_events e
               WHERE e.item_key=items.item_key AND (
                   NOT EXISTS (SELECT 1 FROM learning_assessments a WHERE a.item_key=items.item_key)
                   OR CASE WHEN json_valid(e.outcome) THEN
                       json_extract(e.outcome, '$.assessment_id') = (
                           SELECT a.assessment_id FROM learning_assessments a
                           WHERE a.item_key=items.item_key ORDER BY a.rowid DESC LIMIT 1
                       ) ELSE 0 END
               )
           )
         ORDER BY items.item_key ASC",
    )?;
    let rows = stmt.query_map([], |row| Ok((row.get(0)?, row.get(1)?)))?;
    rows.collect()
}

/// A display-only summary of the first nonempty line, capped in Unicode scalars.
/// This never changes an item's identity or its persisted assessment snapshot.
fn learning_title_excerpt(value: &str) -> Option<String> {
    value.lines().find_map(|line| {
        let clean: String = line
            .chars()
            .filter(|ch| !ch.is_control() || ch.is_whitespace())
            .collect();
        let normalized = clean.split_whitespace().collect::<Vec<_>>().join(" ");
        (!normalized.is_empty()).then(|| normalized.chars().take(80).collect())
    })
}

fn course_learning_identity(item_key: &str) -> Option<(&str, &str)> {
    fn valid_id(value: &str) -> bool {
        !value.is_empty()
            && value.len() <= 256
            && value.as_bytes()[0].is_ascii_alphanumeric()
            && value
                .bytes()
                .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, b'_' | b'.' | b'-'))
    }
    let (course_id, artifact_id) = item_key.strip_prefix("course:")?.split_once(":artifact:")?;
    (valid_id(course_id) && valid_id(artifact_id)).then_some((course_id, artifact_id))
}

/// Read a human-readable label without writing, following latest knowledge, or
/// inferring mastery. A course prefix alone never establishes artifact ownership.
pub fn item_display_title(conn: &Connection, item_key: &str) -> rusqlite::Result<String> {
    let assessment = assessment_for_item_key(conn, item_key)?;
    if let (Some((course_id, artifact_id)), Some(assessment)) =
        (course_learning_identity(item_key), assessment.as_ref())
    {
        let title: Option<String> = conn
            .query_row(
                "SELECT c.title FROM general_courses c
                 JOIN general_course_artifacts a ON a.manifest_id=c.manifest_id
                 JOIN general_course_bindings b ON b.manifest_id=c.manifest_id
                 JOIN json_each(a.artifact_json,'$.knowledge_ids') component
                   ON component.type='text' AND component.value=b.component_id
                 JOIN anchors h ON h.anchor_id=?6 AND h.source_id=b.source_id
                   AND h.source_revision=b.source_revision
                 WHERE c.manifest_id=?1 AND a.artifact_id=?2
                   AND b.knowledge_id=?3 AND b.knowledge_version=?4 AND b.source_id=?5
                 LIMIT 1",
                rusqlite::params![
                    course_id,
                    artifact_id,
                    assessment.knowledge_id,
                    assessment.knowledge_version,
                    assessment.source_id,
                    assessment.anchor_id
                ],
                |row| row.get(0),
            )
            .optional()?;
        if let Some(title) = title.as_deref().and_then(learning_title_excerpt) {
            return Ok(title);
        }
    }
    if let Some(assessment) = assessment {
        if let Some(title) = learning_title_excerpt(&assessment.content) {
            return Ok(title);
        }
    }
    Ok("学习项目".to_owned())
}

/// R09: the table that links a learning item (card/question) to the knowledge
/// revision it was created from. Current workspaces initialize and archive it;
/// the idempotent creation also supports older compatible databases.
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

fn assessment_id(item_key: &str, knowledge_id: &str) -> String {
    let mut hash = Sha256::new();
    hash.update(b"archeaxis.learning-assessment/v1\0");
    hash.update((item_key.len() as u64).to_le_bytes());
    hash.update(item_key.as_bytes());
    hash.update((knowledge_id.len() as u64).to_le_bytes());
    hash.update(knowledge_id.as_bytes());
    format!("assessment_{}", &hex::encode(hash.finalize())[..24])
}

fn assessment_from_row(row: &rusqlite::Row<'_>) -> rusqlite::Result<AssessmentRecord> {
    Ok(AssessmentRecord {
        assessment_id: row.get(0)?,
        item_key: row.get(1)?,
        knowledge_id: row.get(2)?,
        knowledge_version: row.get(3)?,
        question: row.get(4)?,
        content: row.get(5)?,
        source_id: row.get(6)?,
        anchor_id: row.get(7)?,
        created_at: row.get(8)?,
    })
}

/// Create or return the stable Core assessment for a referenced accepted
/// Knowledge revision. The snapshot is append-only and never follows a later
/// superseding revision silently.
pub fn create_assessment(
    conn: &mut Connection,
    item_key: &str,
    knowledge_id: &str,
) -> rusqlite::Result<AssessmentRecord> {
    if item_key.trim().is_empty() || knowledge_id.trim().is_empty() {
        return Err(rusqlite::Error::InvalidParameterName(
            "assessment needs both an item_key and a knowledge_id".into(),
        ));
    }
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    ensure_card_references(&tx)?;
    let linked: bool = tx.query_row(
        "SELECT EXISTS(SELECT 1 FROM card_references WHERE item_key=?1 AND knowledge_id=?2)",
        rusqlite::params![item_key, knowledge_id],
        |row| row.get(0),
    )?;
    if !linked {
        return Err(rusqlite::Error::InvalidParameterName(
            "assessment knowledge must be referenced by the learning item".into(),
        ));
    }
    let (status, knowledge_type, body, anchor_id): (String, String, String, Option<String>) = tx
        .query_row(
            "SELECT status, knowledge_type, body, anchor_id FROM knowledge WHERE knowledge_id=?1",
            [knowledge_id],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)),
        )
        .optional()?
        .ok_or_else(|| {
            rusqlite::Error::InvalidParameterName("assessment knowledge revision not found".into())
        })?;
    if !crate::knowledge::is_knowledge_active(&tx, knowledge_id)?
        || (status != "accepted"
            && !matches!(
                knowledge_type.as_str(),
                "PERSONAL_DEFINITION" | "PERSONAL_EXPERIENCE"
            ))
    {
        return Err(rusqlite::Error::InvalidParameterName(
            "assessment requires active accepted or personal knowledge".into(),
        ));
    }
    let source_id = match anchor_id.as_deref() {
        Some(anchor) => tx
            .query_row(
                "SELECT source_id FROM anchors WHERE anchor_id=?1",
                [anchor],
                |row| row.get::<_, String>(0),
            )
            .optional()?,
        None => None,
    };
    let id = assessment_id(item_key, knowledge_id);
    let question = "请用自己的话复述本条知识，并解释其依据或适用条件；作答后再查看核对内容。";
    tx.execute(
        "INSERT OR IGNORE INTO learning_assessments(
            assessment_id, item_key, knowledge_id, knowledge_version,
            question, content, source_id, anchor_id
         ) VALUES(?1,?2,?3,?4,?5,?6,?7,?8)",
        rusqlite::params![
            id,
            item_key,
            knowledge_id,
            knowledge_id,
            question,
            body,
            source_id,
            anchor_id
        ],
    )?;
    tx.commit()?;
    assessment_by_id(conn, &id)?.ok_or_else(|| rusqlite::Error::InvalidQuery)
}

/// Read one persisted assessment without changing its source binding.
pub fn assessment_by_id(
    conn: &Connection,
    assessment_id: &str,
) -> rusqlite::Result<Option<AssessmentRecord>> {
    conn.query_row(
        "SELECT assessment_id, item_key, knowledge_id, knowledge_version,
                question, content, source_id, anchor_id, created_at
         FROM learning_assessments WHERE assessment_id=?1",
        [assessment_id],
        assessment_from_row,
    )
    .optional()
}

/// Validate that a review uses an assessment belonging to the same item.
pub fn assessment_for_item(
    conn: &Connection,
    assessment_id: &str,
    item_key: &str,
) -> rusqlite::Result<Option<AssessmentRecord>> {
    let assessment = assessment_by_id(conn, assessment_id)?;
    Ok(assessment.filter(|value| value.item_key == item_key))
}

/// Return the most recently created assessment, rather than ordering equal
/// second-resolution timestamps by an unrelated content-derived identifier.
/// The Core appends these rows; its archive export/import also preserves row order.
pub fn assessment_for_item_key(
    conn: &Connection,
    item_key: &str,
) -> rusqlite::Result<Option<AssessmentRecord>> {
    conn.query_row(
        "SELECT assessment_id, item_key, knowledge_id, knowledge_version,
                question, content, source_id, anchor_id, created_at
         FROM learning_assessments WHERE item_key=?1
         ORDER BY rowid DESC LIMIT 1",
        [item_key],
        assessment_from_row,
    )
    .optional()
}
