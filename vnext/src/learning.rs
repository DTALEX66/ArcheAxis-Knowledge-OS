//! Learning events: one learning event + next-review scheduling.
use rusqlite::Connection;

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
