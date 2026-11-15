//! Private, bounded dispatch barriers. A dispatch intent is not proof of a live worker.
use super::{Error, Snapshot, digest, grant, question_turn_document_id, ui_state};
use archeaxis_store_sqlite::authorization_fence;
use rusqlite::{Connection, OptionalExtension, params};
use serde::{Deserialize, Serialize};

const SCHEMA: &str = "archeaxis.deeptutor-question-turn-claim/v1";
const MAX_BYTES: usize = 4096;

#[derive(Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
enum State {
    Dispatched,
    Failed,
    Unknown,
    Completed,
}

#[derive(Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Claim {
    schema: String,
    create_request_id: String,
    request_sha256: String,
    owner_token: String,
    material: Snapshot,
    material_grant: Snapshot,
    workspace_id: String,
    #[serde(deserialize_with = "Option::deserialize")]
    restore_epoch: Option<String>,
    capture_sha256: String,
    state: State,
    #[serde(deserialize_with = "Option::deserialize")]
    result: Option<Snapshot>,
}

fn unresolved() -> Error {
    Error::Invalid(super::QUESTION_TURN_EXECUTION_UNRESOLVED)
}

fn key(id: &str) -> String {
    format!("deeptutor_question_turn_claim_{}", digest(id.as_bytes()))
}

fn hex(value: &str, length: usize) -> bool {
    value.len() == length
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

fn valid(claim: &Claim) -> bool {
    claim.schema == SCHEMA
        && super::token(&claim.create_request_id)
        && hex(&claim.request_sha256, 64)
        && hex(&claim.owner_token, 32)
        && hex(&claim.capture_sha256, 64)
        && grant::valid_snapshot_shape(&claim.material)
        && grant::valid_snapshot_shape(&claim.material_grant)
        && !claim.workspace_id.is_empty()
        && claim.workspace_id.len() <= 128
        && !claim.workspace_id.chars().any(char::is_control)
        && claim
            .restore_epoch
            .as_ref()
            .is_none_or(|epoch| hex(epoch, 32))
        && match (&claim.state, &claim.result) {
            (State::Completed, Some(result)) => {
                grant::valid_snapshot_shape(result)
                    && result.version == 1
                    && result.document_id == question_turn_document_id(&claim.create_request_id)
            }
            (State::Completed, None) | (_, Some(_)) => false,
            (_, None) => true,
        }
}

fn read(conn: &Connection, id: &str) -> Result<Option<(Claim, String)>, Error> {
    let raw: Option<Option<String>> = conn.query_row(
        "SELECT CASE WHEN length(CAST(value AS BLOB))<=?2 THEN value ELSE NULL END FROM workspace_meta WHERE key=?1",
        params![key(id), MAX_BYTES as i64], |row| row.get(0)).optional()?;
    let Some(raw) = raw else { return Ok(None) };
    let raw = raw.ok_or_else(unresolved)?;
    let claim: Claim = serde_json::from_str(&raw).map_err(|_| unresolved())?;
    if !valid(&claim) || claim.create_request_id != id {
        return Err(unresolved());
    }
    Ok(Some((claim, raw)))
}

pub(super) fn refuse_existing(
    conn: &Connection,
    id: &str,
    request_sha256: &str,
) -> Result<(), Error> {
    if let Some((claim, _)) = read(conn, id)? {
        if claim.request_sha256 != request_sha256 {
            return Err(Error::Conflict(1));
        }
        // No state, elapsed time, restart or failure grants another dispatch.
        return Err(unresolved());
    }
    Ok(())
}

/// Read-only status after the caller has looked for the canonical candidate.
/// COMPLETED without its verified candidate is an unresolved integrity failure.
pub(super) fn disposition(
    conn: &Connection,
    id: &str,
    request_sha256: &str,
) -> Result<Option<&'static str>, Error> {
    let Some((claim, _)) = read(conn, id)? else {
        return Ok(None);
    };
    if claim.request_sha256 != request_sha256 {
        return Err(Error::Conflict(1));
    }
    Ok(Some(match claim.state {
        State::Dispatched => "DISPATCHED",
        State::Failed => "FAILED",
        State::Unknown => "UNKNOWN",
        State::Completed => return Err(unresolved()),
    }))
}

/// Explicit human cancellation never grants another execution. The current
/// grant may already be withdrawn: cancelling uses the frozen claim identity,
/// not a fresh authorization or a replacement grant.
pub(super) fn cancel(
    conn: &Connection,
    id: &str,
    request_sha256: &str,
    material: &Snapshot,
    expected: Option<&Claim>,
) -> Result<(&'static str, bool), Error> {
    let Some((mut current, raw)) = read(conn, id)? else {
        return if expected.is_some() {
            Err(unresolved())
        } else {
            Ok(("NOT_FOUND", false))
        };
    };
    if current.request_sha256 != request_sha256 {
        return Err(Error::Conflict(1));
    }
    if current.material != *material {
        return Err(unresolved());
    }
    if expected.is_some_and(|expected| !same_owner(&current, expected)) {
        return Err(unresolved());
    }
    context_matches(conn, &current)?;
    match current.state {
        State::Dispatched => {
            current.state = State::Unknown;
            replace(conn, &raw, &current)?;
            Ok(("UNKNOWN", true))
        }
        State::Unknown => Ok(("UNKNOWN", true)),
        State::Failed => Ok(("FAILED", false)),
        // The caller reads the immutable canonical result first. A completed
        // barrier without that result is an integrity error, not a cancellation.
        State::Completed => Err(unresolved()),
    }
}

pub(super) fn reserve(
    conn: &Connection,
    request: &super::QuestionTurnRequest,
    request_sha256: &str,
    material_grant: Snapshot,
    workspace_id: &str,
    restore_epoch: &Option<String>,
    capture_frame: &[u8],
) -> Result<Claim, Error> {
    if conn.is_autocommit() {
        return Err(unresolved());
    }
    let claim = Claim {
        schema: SCHEMA.into(),
        create_request_id: request.create_request_id.clone(),
        request_sha256: request_sha256.into(),
        owner_token: conn.query_row("SELECT lower(hex(randomblob(16)))", [], |r| r.get(0))?,
        material: request.material.clone(),
        material_grant,
        workspace_id: workspace_id.into(),
        restore_epoch: restore_epoch.clone(),
        capture_sha256: digest(capture_frame),
        state: State::Dispatched,
        result: None,
    };
    let raw = encode(&claim)?;
    conn.execute(
        "INSERT INTO workspace_meta(key,value) VALUES(?1,?2)",
        params![key(&claim.create_request_id), raw],
    )?;
    Ok(claim)
}

fn encode(claim: &Claim) -> Result<String, Error> {
    let raw = serde_json::to_string(claim).map_err(|_| unresolved())?;
    if !valid(claim) || raw.len() > MAX_BYTES {
        return Err(unresolved());
    }
    Ok(raw)
}

fn context_matches(conn: &Connection, claim: &Claim) -> Result<(), Error> {
    if authorization_fence::authorization_epoch(conn)? != claim.restore_epoch
        || ui_state::existing_workspace_id(conn)
            .map_err(|_| unresolved())?
            .as_deref()
            != Some(claim.workspace_id.as_str())
    {
        return Err(unresolved());
    }
    Ok(())
}

fn same_owner(current: &Claim, expected: &Claim) -> bool {
    let mut identity = current.clone();
    identity.state = expected.state;
    identity.result = expected.result.clone();
    identity == *expected
}

pub(super) fn assert_dispatched(conn: &Connection, expected: &Claim) -> Result<(), Error> {
    let (current, _) = read(conn, &expected.create_request_id)?.ok_or_else(unresolved)?;
    if current != *expected || current.state != State::Dispatched {
        return Err(unresolved());
    }
    context_matches(conn, expected)
}

fn replace(conn: &Connection, previous: &str, claim: &Claim) -> Result<(), Error> {
    if conn.is_autocommit() {
        return Err(unresolved());
    }
    let changed = conn.execute(
        "UPDATE workspace_meta SET value=?1 WHERE key=?2 AND value=?3",
        params![encode(claim)?, key(&claim.create_request_id), previous],
    )?;
    if changed != 1 {
        return Err(unresolved());
    }
    Ok(())
}

pub(super) fn complete(conn: &Connection, expected: &Claim, result: Snapshot) -> Result<(), Error> {
    assert_dispatched(conn, expected)?;
    let (_, raw) = read(conn, &expected.create_request_id)?.ok_or_else(unresolved)?;
    let mut completed = expected.clone();
    completed.state = State::Completed;
    completed.result = Some(result);
    replace(conn, &raw, &completed)
}

pub(super) fn finish_failure(
    conn: &Connection,
    expected: &Claim,
    outcome: super::QuestionTurnFailure,
) -> Result<(), Error> {
    let (mut current, raw) = read(conn, &expected.create_request_id)?.ok_or_else(unresolved)?;
    if !same_owner(&current, expected) {
        return Err(unresolved());
    }
    if current.state != State::Dispatched {
        // A late drop/failure callback cannot change a completed or otherwise terminal result.
        return Ok(());
    }
    context_matches(conn, expected)?;
    current.state = match outcome {
        super::QuestionTurnFailure::Failed => State::Failed,
        super::QuestionTurnFailure::Unknown => State::Unknown,
    };
    replace(conn, &raw, &current)
}
