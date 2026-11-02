//! Staged DeepTutor grading transactions. The domain owns the durable
//! reservation, dispatch intent and final result; the Core-owned bridge owns
//! the fixed worker process. `complete_observed` accepts the worker's exact
//! receipt bytes and validates their identity against the reservation, but it
//! cannot itself prove which process produced them, so the bridge must be the
//! only caller. The synthetic `OwnedObservation` constructor remains test-only.
//!
//! The durable metadata stores identities and hashes, never answer or answer
//! key plaintext. Hashes of low-entropy answers are not secrecy mechanisms.
use crate::{
    provider_learning::{
        self as learning, Activity, Error, GradeEvidence, StoredResult, Submission,
    },
    provider_material_grant::{self as grant, Snapshot},
    provider_question,
};
use rusqlite::{Connection, OptionalExtension, TransactionBehavior, params};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

const SCHEMA: &str = "archeaxis.deeptutor-practice-grade/v1";
const UPSTREAM_SHA256: &str = "fdfbaee6cd0fa2c0f31de9a792e220e6989434fc1f44359db3e6afc62cd2472f";
const CLAIM_SCHEMA: &str = "archeaxis.provider-grade-claim/v1";
const INDEX_SCHEMA: &str = "archeaxis.provider-grade-event-index/v1";
/// The fixed worker prints one bounded JSON line. Anything else is not a receipt.
const MAX_RECEIPT_BYTES: usize = 16_384;
type Result<T> = std::result::Result<T, Error>;

#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GradeRequest {
    pub client_event_id: String,
    pub question_document: Snapshot,
    pub question_grant: Snapshot,
    pub answer: String,
}

#[derive(Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Claim {
    schema: String,
    activity_id: String,
    attempt_id: String,
    client_event_id: String,
    request_sha256: String,
    worker_input_sha256: String,
    question_document: Snapshot,
    question_grant: Snapshot,
    origin_restore_epoch: String,
    state: String,
    #[serde(deserialize_with = "Option::deserialize")]
    result_sha256: Option<String>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct EventIndex {
    schema: String,
    attempt_key: String,
    claim_sha256: String,
}

/// Never serializable or printable: it contains the worker stdin and answer.
/// It crosses the Core-owned bridge exactly once per reservation.
pub struct Prepared {
    request: GradeRequest,
    claim: Claim,
    stdin: Vec<u8>,
    finalization_started: AtomicBool,
}

pub enum Admission {
    Ready(Prepared),
    /// A prior owner may have started a worker. Never launch again automatically.
    Unknown,
    /// Previously committed result; this is a history read, not new execution.
    Completed(Value),
}

impl Prepared {
    /// The exact bytes a dispatched worker must receive.
    ///
    /// The caller owns their protection: they contain the learner answer and
    /// the question's answer key material. This is not a generic job frame.
    pub fn worker_input(&self) -> &[u8] {
        &self.stdin
    }

    #[cfg(test)]
    fn worker_stdin(&self) -> &[u8] {
        &self.stdin
    }
}

fn hash_bytes(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}
fn event_key(event: &str) -> String {
    format!("provider_grade_event_{}", hash_bytes(event.as_bytes()))
}
fn attempt_key(activity: &str, attempt: &str) -> String {
    format!(
        "provider_grade_attempt_{}",
        hash_bytes(format!("{activity}\0{attempt}").as_bytes())
    )
}

fn is_sha(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

fn valid_claim(key: &str, claim: &Claim) -> bool {
    claim.schema == CLAIM_SCHEMA
        && learning::token(&claim.activity_id, 128)
        && learning::token(&claim.attempt_id, 128)
        && learning::token(&claim.client_event_id, 128)
        && key == attempt_key(&claim.activity_id, &claim.attempt_id)
        && is_sha(&claim.request_sha256)
        && is_sha(&claim.worker_input_sha256)
        && grant::valid_snapshot_shape(&claim.question_document)
        && grant::valid_snapshot_shape(&claim.question_grant)
        && (claim.origin_restore_epoch == "initial"
            || (claim.origin_restore_epoch.len() == 32
                && claim
                    .origin_restore_epoch
                    .bytes()
                    .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))))
        && matches!(
            (claim.state.as_str(), claim.result_sha256.as_deref()),
            ("RESERVED" | "DISPATCHED" | "UNKNOWN", None) | ("COMPLETED", Some(_))
        )
        && !claim
            .result_sha256
            .as_deref()
            .is_some_and(|sha| !is_sha(sha))
}

fn valid_pair(
    event: &str,
    index: &EventIndex,
    attempt: &str,
    claim: &Claim,
    claim_raw: &str,
) -> bool {
    index.schema == INDEX_SCHEMA
        && is_sha(&index.claim_sha256)
        && valid_claim(attempt, claim)
        && index.attempt_key == attempt
        && event == event_key(&claim.client_event_id)
        && index.claim_sha256 == learning::digest(claim_raw)
}

fn bounded_value(conn: &Connection, key: &str) -> Result<Option<String>> {
    let raw: Option<Option<String>> = conn.query_row(
        "SELECT CASE WHEN length(CAST(value AS BLOB))<=8192 THEN value ELSE NULL END FROM workspace_meta WHERE key=?1",
        [key],|row|row.get(0)).optional()?;
    Ok(raw.flatten())
}

/// The ordinary provider submission path uses the same transaction as this
/// check. Orphaned or inconsistent pairs block new provider submissions
/// globally because a surviving identity might itself be damaged. Ordinary
/// Document operations do not call this function.
pub(crate) fn is_reserved(
    conn: &Connection,
    activity: &str,
    attempt: &str,
    event: &str,
) -> Result<bool> {
    let wanted_attempt = attempt_key(activity, attempt);
    let wanted_event = event_key(event);
    let mut statement = conn.prepare("SELECT key,CASE WHEN length(CAST(value AS BLOB))<=8192 THEN value ELSE NULL END FROM workspace_meta
        WHERE key GLOB 'provider_grade_event_*' OR key GLOB 'provider_grade_attempt_*'")?;
    let rows = statement.query_map([], |r| {
        Ok((r.get::<_, String>(0)?, r.get::<_, Option<String>>(1)?))
    })?;
    for row in rows {
        let (key, raw) = row?;
        if key == wanted_attempt || key == wanted_event {
            return Ok(true);
        }
        let Some(raw) = raw else {
            return Ok(true);
        };
        if key.starts_with("provider_grade_event_") {
            let Ok(index) = serde_json::from_str::<EventIndex>(&raw) else {
                return Ok(true);
            };
            let Some(attempt_suffix) = index.attempt_key.strip_prefix("provider_grade_attempt_")
            else {
                return Ok(true);
            };
            if index.schema != INDEX_SCHEMA
                || !is_sha(attempt_suffix)
                || !is_sha(&index.claim_sha256)
            {
                return Ok(true);
            }
            let Some(claim_raw) = bounded_value(conn, &index.attempt_key)? else {
                return Ok(true);
            };
            let Ok(claim) = serde_json::from_str::<Claim>(&claim_raw) else {
                return Ok(true);
            };
            if !valid_pair(&key, &index, &index.attempt_key, &claim, &claim_raw) {
                return Ok(true);
            }
            if index.attempt_key == wanted_attempt {
                return Ok(true);
            }
        } else {
            let Ok(claim) = serde_json::from_str::<Claim>(&raw) else {
                return Ok(true);
            };
            if !valid_claim(&key, &claim) {
                return Ok(true);
            }
            let paired_key = event_key(&claim.client_event_id);
            let Some(index_raw) = bounded_value(conn, &paired_key)? else {
                return Ok(true);
            };
            let Ok(index) = serde_json::from_str::<EventIndex>(&index_raw) else {
                return Ok(true);
            };
            if !valid_pair(&paired_key, &index, &key, &claim, &raw) {
                return Ok(true);
            }
            if claim.client_event_id == event || key == wanted_attempt {
                return Ok(true);
            }
        }
    }
    Ok(false)
}

fn read_claim(
    conn: &Connection,
    activity: &str,
    attempt: &str,
    event: &str,
) -> Result<Option<Claim>> {
    let attempt_key = attempt_key(activity, attempt);
    let event_key = event_key(event);
    let present: (bool,bool) = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM workspace_meta WHERE key=?1),EXISTS(SELECT 1 FROM workspace_meta WHERE key=?2)",
        params![attempt_key,event_key],|r|Ok((r.get(0)?,r.get(1)?)))?;
    match present {
        (false, false) => {
            if is_reserved(conn, activity, attempt, event)? {
                Err(Error::Conflict("grade event or attempt already reserved"))
            } else {
                Ok(None)
            }
        }
        (true, true) => {
            let raw = bounded_value(conn, &attempt_key)?
                .ok_or(Error::Conflict("grade claim unavailable"))?;
            let index = bounded_value(conn, &event_key)?
                .ok_or(Error::Conflict("grade index unavailable"))?;
            let claim: Claim = serde_json::from_str(&raw)
                .map_err(|_| Error::Conflict("grade claim unavailable"))?;
            let index: EventIndex = serde_json::from_str(&index)
                .map_err(|_| Error::Conflict("grade index unavailable"))?;
            if !valid_pair(&event_key, &index, &attempt_key, &claim, &raw)
                || claim.activity_id != activity
                || claim.attempt_id != attempt
                || claim.client_event_id != event
            {
                return Err(Error::Conflict("grade claim identity mismatch"));
            }
            Ok(Some(claim))
        }
        _ => Err(Error::Conflict("grade event or attempt already reserved")),
    }
}

fn store_claim(conn: &Connection, claim: &Claim, insert: bool) -> Result<()> {
    let raw = serde_json::to_string(claim).map_err(|_| Error::Invalid("invalid grade claim"))?;
    let key = attempt_key(&claim.activity_id, &claim.attempt_id);
    let index = serde_json::to_string(&EventIndex {
        schema: INDEX_SCHEMA.into(),
        attempt_key: key.clone(),
        claim_sha256: learning::digest(&raw),
    })
    .map_err(|_| Error::Invalid("invalid grade index"))?;
    if insert {
        conn.execute(
            "INSERT INTO workspace_meta(key,value) VALUES(?1,?2)",
            params![key, raw],
        )?;
        conn.execute(
            "INSERT INTO workspace_meta(key,value) VALUES(?1,?2)",
            params![event_key(&claim.client_event_id), index],
        )?;
    } else {
        let changed = conn.execute(
            "UPDATE workspace_meta SET value=?1 WHERE key=?2",
            params![raw, key],
        )?;
        let indexed = conn.execute(
            "UPDATE workspace_meta SET value=?1 WHERE key=?2",
            params![index, event_key(&claim.client_event_id)],
        )?;
        if changed != 1 || indexed != 1 {
            return Err(Error::Conflict("grade claim unavailable"));
        }
    }
    Ok(())
}

fn request_hash(activity: &Activity, attempt: &str, request: &GradeRequest) -> String {
    learning::digest(
        &json!({"activity":activity,"attempt_id":attempt,"request":request}).to_string(),
    )
}

/// Wall-clock second of the committed dispatch intent, keyed by the exact client
/// event rather than the attempt so a later event on the same attempt cannot
/// inherit an earlier dispatch time. This is not part of the claim identity: an
/// old claim without this key still reads, and its dispatch time is "not proven".
fn dispatch_time_key(event: &str) -> String {
    format!("provider_grade_dispatch_{}", learning::digest(event))
}

fn read_dispatch_time(conn: &Connection, event: &str) -> Result<Option<u64>> {
    let Some(raw) = bounded_value(conn, &dispatch_time_key(event))? else {
        return Ok(None);
    };
    raw.parse::<u64>()
        .ok()
        .filter(|seconds| *seconds > 0)
        .map(Some)
        .ok_or(Error::Conflict("grade dispatch time unavailable"))
}

fn store_dispatch_time(conn: &Connection, event: &str, seconds: u64) -> Result<()> {
    conn.execute(
        "INSERT OR REPLACE INTO workspace_meta(key,value) VALUES(?1,?2)",
        params![dispatch_time_key(event), seconds.to_string()],
    )?;
    Ok(())
}

fn validate_attempt_with<F: FnMut() -> Result<u64>>(
    conn: &Connection,
    activity: &Activity,
    attempt: &str,
    request: &GradeRequest,
    mut now: F,
) -> Result<(String, Option<u64>)> {
    if activity.provider.id != "deeptutor" || activity.provider.version != "1.7.1" {
        return Err(Error::Invalid("DeepTutor activity required"));
    }
    let row: Option<(String,String)> = conn.query_row(
        "SELECT state,origin_restore_epoch FROM learning_provider_attempts WHERE activity_id=?1 AND attempt_id=?2",
        params![activity.activity_id,attempt],|r|Ok((r.get(0)?,r.get(1)?))).optional()?;
    let (state, origin) = row.ok_or(Error::NotFound)?;
    if state != "pending" {
        return Err(Error::Conflict("attempt already terminal"));
    }
    if origin != learning::epoch(conn)? {
        return Err(Error::Conflict("restored attempt requires a new attempt"));
    }
    grant::assert_material(conn, &activity.material)
        .map_err(|_| Error::Invalid("material snapshot unavailable or changed"))?;
    let source_grant = activity
        .grant
        .as_ref()
        .ok_or(Error::Invalid("provider grant required"))?;
    let source_expiry = grant::consume_with_expiry(conn, source_grant, &activity.material, now()?)
        .map_err(|_| Error::Invalid("provider grant unavailable or revoked"))?;
    let question_expiry = grant::consume_with_expiry(
        conn,
        &request.question_grant,
        &request.question_document,
        now()?,
    )
    .map_err(|_| Error::Invalid("question grant unavailable or revoked"))?;
    let expiry = match (source_expiry, question_expiry) {
        (Some(a), Some(b)) => Some(a.min(b)),
        (Some(a), None) | (None, Some(a)) => Some(a),
        (None, None) => None,
    };
    Ok((origin, expiry))
}

fn validate_attempt(
    conn: &Connection,
    activity: &Activity,
    attempt: &str,
    request: &GradeRequest,
) -> Result<String> {
    validate_attempt_with(conn, activity, attempt, request, learning::now).map(|(origin, _)| origin)
}

fn worker_stdin(conn: &Connection, activity: &Activity, request: &GradeRequest) -> Result<Vec<u8>> {
    let question = provider_question::grading_question(
        conn,
        &request.question_document,
        &activity.material,
        &activity.question.question_id,
        &activity.question.question_version,
    )
    .map_err(|_| Error::Invalid("question snapshot unavailable or changed"))?;
    let mut bytes = serde_json::to_vec(
        &json!({"schema":SCHEMA,"request_id":request.client_event_id,
        "question":question,"answer":request.answer}),
    )
    .map_err(|_| Error::Invalid("invalid worker input"))?;
    bytes.push(b'\n');
    // Leaves room for the upstream worker's own reserialization before its
    // 256-KiB limit, even with the maximum number of option keys.
    if bytes.len() > 240_000 {
        return Err(Error::Invalid("worker input exceeds bound"));
    }
    Ok(bytes)
}

fn terminal(
    conn: &Connection,
    activity: &Activity,
    attempt: &str,
    request: &GradeRequest,
    request_sha: &str,
) -> Result<Option<Value>> {
    let row: Option<(String,String,String,String,String)> = conn.query_row(
        "SELECT activity_id,attempt_id,result_json,result_sha256,origin_restore_epoch FROM learning_provider_attempts WHERE client_event_id=?1",
        [&request.client_event_id],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?,r.get(4)?))).optional()?;
    let Some((old_activity, old_attempt, raw, sha, origin)) = row else {
        return Ok(None);
    };
    let stored: StoredResult =
        serde_json::from_str(&raw).map_err(|_| Error::Invalid("stored submission invalid"))?;
    let grade = stored
        .grade
        .as_ref()
        .ok_or(Error::Conflict("event id conflict"))?;
    validate_stored(conn, activity, attempt, &stored, &origin, &raw)?;
    if learning::digest(&raw) != sha
        || old_activity != activity.activity_id
        || old_attempt != attempt
        || stored.request.client_event_id != request.client_event_id
        || stored.request.answer != request.answer
        || grade.request_sha256 != request_sha
        || grade.question_document != request.question_document
        || grade.question_grant != request.question_grant
        || stored.material_status_at_submission != "current"
    {
        return Err(Error::Conflict("event id conflict"));
    }
    Ok(Some(learning::result_receipt(
        &activity.activity_id,
        attempt,
        &stored.request,
        true,
        &stored.material_status_at_submission,
        learning::material_status(conn, &activity.material),
        Some(grade),
    )))
}

/// Reserve the exact event and attempt atomically. No worker may be started
/// until a Core-owned bridge calls `begin_dispatch` and then `complete_observed`.
pub fn prepare(
    conn: &mut Connection,
    activity_id: &str,
    attempt_id: &str,
    request: &GradeRequest,
) -> Result<Admission> {
    if !learning::token(activity_id, 128)
        || !learning::token(attempt_id, 128)
        || !learning::token(&request.client_event_id, 128)
        || request.answer.len() > 20_000
        || request.answer.contains('\0')
        || !grant::valid_snapshot_shape(&request.question_document)
        || !grant::valid_snapshot_shape(&request.question_grant)
    {
        return Err(Error::Invalid("invalid grade request"));
    }
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let activity = learning::activity(&tx, activity_id)?;
    let request_sha = request_hash(&activity, attempt_id, request);
    if let Some(receipt) = terminal(&tx, &activity, attempt_id, request, &request_sha)? {
        return Ok(Admission::Completed(receipt));
    }
    let origin = validate_attempt(&tx, &activity, attempt_id, request)?;
    let stdin = worker_stdin(&tx, &activity, request)?;
    let input_sha = hash_bytes(&stdin);
    if let Some(old) = read_claim(&tx, activity_id, attempt_id, &request.client_event_id)? {
        if !matches!(old.state.as_str(), "RESERVED" | "DISPATCHED" | "UNKNOWN")
            || old.request_sha256 != request_sha
            || old.worker_input_sha256 != input_sha
            || old.question_document != request.question_document
            || old.question_grant != request.question_grant
            || old.origin_restore_epoch != origin
        {
            return Err(Error::Conflict("grade request conflict"));
        }
        return Ok(Admission::Unknown);
    }
    let claim = Claim {
        schema: CLAIM_SCHEMA.into(),
        activity_id: activity_id.into(),
        attempt_id: attempt_id.into(),
        client_event_id: request.client_event_id.clone(),
        request_sha256: request_sha,
        worker_input_sha256: input_sha,
        question_document: request.question_document.clone(),
        question_grant: request.question_grant.clone(),
        origin_restore_epoch: origin,
        state: "RESERVED".into(),
        result_sha256: None,
    };
    store_claim(&tx, &claim, true)?;
    tx.commit()?;
    Ok(Admission::Ready(Prepared {
        request: request.clone(),
        claim,
        stdin,
        finalization_started: AtomicBool::new(false),
    }))
}

/// Recheck immediately before any future dispatch and again at completion.
/// It does not itself establish a linearization boundary with process I/O.
fn revalidate_with<F: FnMut() -> Result<u64>>(
    conn: &Connection,
    prepared: &Prepared,
    required_state: &str,
    now: F,
) -> Result<(Activity, Option<u64>)> {
    let claim = read_claim(
        conn,
        &prepared.claim.activity_id,
        &prepared.claim.attempt_id,
        &prepared.claim.client_event_id,
    )?
    .ok_or(Error::Conflict("grade claim unavailable"))?;
    let mut expected = prepared.claim.clone();
    expected.state = required_state.into();
    if claim != expected {
        return Err(Error::Conflict("grade claim changed"));
    }
    let activity = learning::activity(conn, &claim.activity_id)?;
    let (origin, expiry) =
        validate_attempt_with(conn, &activity, &claim.attempt_id, &prepared.request, now)?;
    if origin != claim.origin_restore_epoch
        || request_hash(&activity, &claim.attempt_id, &prepared.request) != claim.request_sha256
        || worker_stdin(conn, &activity, &prepared.request)? != prepared.stdin
        || hash_bytes(&prepared.stdin) != claim.worker_input_sha256
    {
        return Err(Error::Conflict("grade input changed"));
    }
    Ok((activity, expiry))
}

// This interface is deliberately private and has only synthetic test
// implementations. In particular, it is not a production process bridge.
// A future implementation must guarantee synchronous, deadline-bounded writes
// and that no background or pending write survives its return. Returning false
// when quiescence is uncertain does not prove that an OS pipe has stopped.
// No existing executor satisfies this contract yet.
trait BoundedDispatch {
    fn write_chunk(&mut self, bytes: &[u8], deadline: Instant) -> bool;
    fn writes_quiescent(&mut self, deadline: Instant) -> bool;
}

enum DispatchOutcome {
    Dispatched(Prepared),
    Unknown,
}

trait DispatchClock {
    fn monotonic(&self) -> Instant;
    fn wall(&mut self) -> Result<Duration>;
}
struct SystemDispatchClock;
impl DispatchClock for SystemDispatchClock {
    fn monotonic(&self) -> Instant {
        Instant::now()
    }
    fn wall(&mut self) -> Result<Duration> {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|_| Error::Invalid("clock unavailable"))
    }
}

fn sample_wall<C: DispatchClock>(
    clock: &mut C,
    last_wall: &mut Option<Duration>,
) -> Result<Duration> {
    let wall = clock.wall()?;
    if last_wall.as_ref().is_some_and(|last| wall < *last) {
        return Err(Error::Invalid("dispatch wall clock moved backwards"));
    }
    *last_wall = Some(wall);
    Ok(wall)
}

fn wall_unexpired<C: DispatchClock>(
    clock: &mut C,
    expiry: Option<u64>,
    last_wall: &mut Option<Duration>,
) -> bool {
    sample_wall(clock, last_wall)
        .ok()
        .is_some_and(|wall| expiry.map_or(true, |end| wall < Duration::from_secs(end)))
}

/// `prepare` must have committed RESERVED in a separate transaction. Consume
/// the in-memory token even on failure: a failed commit after a partial write
/// must not permit that token to be used for a second dispatch. Re-admission
/// of an extant RESERVED/DISPATCHED/UNKNOWN claim is always read-only UNKNOWN.
/// The transaction serializes the checks and synthetic write against other
/// SQLite writers. The deadline limits when synthetic writes may begin; it
/// does not bound time spent waiting for BEGIN IMMEDIATE. A monotonic deadline
/// is capped by the earlier validated grant expiry. Wall time is checked before
/// and after each chunk and any observed backwards jump fails closed. A clock
/// jump or expiry during a write can be detected only after that write returns.
/// Physical child-process I/O cancellation and quiescence remain unimplemented.
fn dispatch_bounded<S: BoundedDispatch>(
    conn: &mut Connection,
    prepared: Prepared,
    sink: &mut S,
    deadline: Instant,
) -> Result<DispatchOutcome> {
    dispatch_with_clock(conn, prepared, sink, deadline, &mut SystemDispatchClock)
}

fn dispatch_with_clock<S: BoundedDispatch, C: DispatchClock>(
    conn: &mut Connection,
    prepared: Prepared,
    sink: &mut S,
    deadline: Instant,
    clock: &mut C,
) -> Result<DispatchOutcome> {
    let now = clock.monotonic();
    if deadline <= now || deadline.duration_since(now) > Duration::from_secs(2) {
        return Err(Error::Invalid("invalid dispatch deadline"));
    }
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    // Every grant time read in this dispatch uses the same tracked clock;
    // otherwise a real clock sample hidden inside revalidation could be lost.
    let mut last_wall = None;
    sample_wall(clock, &mut last_wall)?;
    let (_, expiry) = revalidate_with(&tx, &prepared, "RESERVED", || {
        sample_wall(clock, &mut last_wall).map(|wall| wall.as_secs())
    })?;
    // Capture monotonic first so the derived bound is conservative relative to
    // the subsequently sampled wall time. Clock jumps remain detectable only
    // at the sampling boundaries; they cannot cancel an in-flight OS write.
    let sampled = clock.monotonic();
    let wall = sample_wall(clock, &mut last_wall)?;
    let mut write_deadline = deadline;
    if let Some(end) = expiry {
        let remaining = Duration::from_secs(end)
            .checked_sub(wall)
            .filter(|d| !d.is_zero())
            .ok_or(Error::Invalid("provider grant expired before dispatch"))?;
        if let Some(cap) = sampled.checked_add(remaining) {
            write_deadline = write_deadline.min(cap);
        }
    }
    let mut written = true;
    for chunk in prepared.stdin.chunks(4096) {
        // The SQLite write lock freezes both grants and restore epoch for this
        // transaction; time can still advance or jump while it is held.
        if clock.monotonic() >= write_deadline
            || !wall_unexpired(clock, expiry, &mut last_wall)
            || !sink.write_chunk(chunk, write_deadline)
            || clock.monotonic() >= write_deadline
            || !wall_unexpired(clock, expiry, &mut last_wall)
        {
            written = false;
            break;
        }
    }
    let quiescent = sink.writes_quiescent(write_deadline);
    let dispatched = written
        && quiescent
        && clock.monotonic() < write_deadline
        && wall_unexpired(clock, expiry, &mut last_wall);
    let mut claim = prepared.claim.clone();
    claim.state = if dispatched { "DISPATCHED" } else { "UNKNOWN" }.into();
    store_claim(&tx, &claim, false)?;
    tx.commit()?;
    Ok(if dispatched {
        DispatchOutcome::Dispatched(prepared)
    } else {
        DispatchOutcome::Unknown
    })
}

#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct WorkerResponse {
    schema: String,
    request_id: String,
    status: String,
    provider: String,
    adapter_version: String,
    upstream_member_sha256: String,
    input_sha256: String,
    #[serde(deserialize_with = "Option::deserialize")]
    provider_correct: Option<bool>,
    question_binding: String,
    independent_mastery: String,
}

// There is deliberately no test-independent constructor: only the Core-owned
// bridge passes the fixed worker's exact receipt bytes through
// `complete_observed`, which validates their identity against the reservation.
struct OwnedObservation {
    response: Value,
}

fn complete(
    conn: &mut Connection,
    prepared: &Prepared,
    observed: OwnedObservation,
) -> Result<Value> {
    complete_with_clock(conn, prepared, observed, &mut SystemDispatchClock)
}

/// Record the durable dispatch intent before the Core-owned bridge writes the
/// reservation's stdin to the fixed worker.
///
/// This rechecks both grants, the attempt, the restore epoch and the remaining
/// grant window inside one write transaction, then commits `DISPATCHED`. No
/// SQLite transaction is held across process I/O, so a withdrawal committed in
/// the short window between this commit and the first byte is detected only by
/// `complete_observed`, after the bytes may already have been sent. The bridge
/// must not retry a reservation whose dispatch is not certain.
pub fn begin_dispatch(conn: &mut Connection, prepared: &Prepared, budget: Duration) -> Result<()> {
    if budget.is_zero() || budget > Duration::from_secs(120) {
        return Err(Error::Invalid("invalid grading budget"));
    }
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let (_, expiry) = revalidate_with(&tx, prepared, "RESERVED", learning::now)?;
    if let Some(end) = expiry {
        // A grant that cannot cover the whole budget would authorize bytes that
        // the completion check must then reject; refuse before writing instead.
        let now = learning::now()?;
        if end <= now.saturating_add(budget.as_secs()) {
            return Err(Error::Invalid(
                "provider grant expires before the grading budget",
            ));
        }
    }
    let mut claim = prepared.claim.clone();
    claim.state = "DISPATCHED".into();
    store_claim(&tx, &claim, false)?;
    // Record the dispatch second inside the same write transaction so a reader can
    // later tell a live dispatch from one whose bounded window has already closed.
    store_dispatch_time(&tx, &claim.client_event_id, learning::now()?)?;
    tx.commit()?;
    Ok(())
}

/// Persist one observed result from the exact single-line receipt printed by the
/// fixed worker, or refuse.
///
/// A receipt with `provider_correct: null` is a legitimate observed outcome:
/// the upstream grader declined to decide, so the attempt is still submitted and
/// the result is stored as unscored, never as a failure to retry. The function
/// revalidates the claim, both grants, the attempt state and the restore epoch,
/// and binds the receipt to the reservation's input digest before writing.
pub fn complete_observed(
    conn: &mut Connection,
    prepared: &Prepared,
    receipt: &[u8],
) -> Result<Value> {
    if receipt.is_empty()
        || receipt.len() > MAX_RECEIPT_BYTES
        || receipt.last() != Some(&b'\n')
        || receipt[..receipt.len() - 1].contains(&b'\n')
    {
        return Err(Error::Invalid("invalid worker receipt"));
    }
    // Decode the struct directly so a duplicate member or an unknown field is
    // refused rather than collapsed by a generic Value round trip.
    let worker: WorkerResponse =
        serde_json::from_slice(receipt).map_err(|_| Error::Invalid("invalid worker receipt"))?;
    let response =
        serde_json::to_value(worker).map_err(|_| Error::Invalid("invalid worker receipt"))?;
    complete(conn, prepared, OwnedObservation { response })
}

/// Record that a reserved or dispatched worker's outcome cannot be established.
///
/// The attempt stays pending and no result is invented. Re-admission of the same
/// event is a read-only `Admission::Unknown`, so an unclear outcome can never be
/// turned into a second launch by retrying the same request.
pub fn abandon_unknown(conn: &mut Connection, prepared: &Prepared) -> Result<()> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let current = read_claim(
        &tx,
        &prepared.claim.activity_id,
        &prepared.claim.attempt_id,
        &prepared.claim.client_event_id,
    )?
    .ok_or(Error::Conflict("grade claim unavailable"))?;
    match current.state.as_str() {
        "RESERVED" | "DISPATCHED" => (),
        _ => return Err(Error::Conflict("grade claim already terminal")),
    }
    let mut expected = prepared.claim.clone();
    expected.state = current.state.clone();
    if current != expected {
        return Err(Error::Conflict("grade claim changed"));
    }
    let mut unknown = prepared.claim.clone();
    unknown.state = "UNKNOWN".into();
    store_claim(&tx, &unknown, false)?;
    tx.commit()?;
    Ok(())
}

/// Outcome of one bounded stale-dispatch reconciliation attempt.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Reconciled {
    /// No claim, or the claim is already past dispatch: nothing to reconcile.
    NotDispatched,
    /// A dispatch is recorded but its start second is not, so staleness is not proven.
    NoDispatchTime,
    /// The recorded window has not closed yet.
    NotStale,
    /// The dispatch window closed without a receipt; the claim is now terminal UNKNOWN.
    Abandoned,
}

impl Reconciled {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::NotDispatched => "NOT_DISPATCHED",
            Self::NoDispatchTime => "NO_DISPATCH_TIME",
            Self::NotStale => "NOT_STALE",
            Self::Abandoned => "ABANDONED",
        }
    }
}

/// Read-only grading disposition for one attempt: the durable claim state and the
/// dispatch second when one was recorded. It never launches, retries or writes.
pub fn disposition(conn: &Connection, activity: &str, attempt: &str) -> Result<Option<Value>> {
    if !learning::token(activity, 128) || !learning::token(attempt, 128) {
        return Err(Error::Invalid("invalid grade identity"));
    }
    let key = attempt_key(activity, attempt);
    let Some(raw) = bounded_value(conn, &key)? else {
        return Ok(None);
    };
    let claim: Claim =
        serde_json::from_str(&raw).map_err(|_| Error::Conflict("grade claim unavailable"))?;
    if !valid_claim(&key, &claim) || claim.activity_id != activity || claim.attempt_id != attempt {
        return Err(Error::Conflict("grade claim identity mismatch"));
    }
    let event_index = event_key(&claim.client_event_id);
    let index =
        bounded_value(conn, &event_index)?.ok_or(Error::Conflict("grade index unavailable"))?;
    let index: EventIndex =
        serde_json::from_str(&index).map_err(|_| Error::Conflict("grade index unavailable"))?;
    if !valid_pair(&event_index, &index, &key, &claim, &raw) {
        return Err(Error::Conflict("grade claim identity mismatch"));
    }
    let dispatched_at = read_dispatch_time(conn, &claim.client_event_id)?;
    Ok(Some(json!({
        "state": claim.state,
        "dispatched_at_unix": dispatched_at,
    })))
}

/// Finalize a dispatch whose bounded worker window closed without a receipt.
///
/// The caller supplies the window, so this function cannot widen or shorten the
/// grading budget on its own. It only marks a dispatched claim UNKNOWN; it never
/// starts, re-sends or retries a worker, and a claim without a recorded dispatch
/// second is left untouched because staleness is not proven. Repeating it is a
/// no-op once the claim is terminal.
pub fn reconcile_stale_dispatch(
    conn: &mut Connection,
    activity: &str,
    attempt: &str,
    event: &str,
    stale_after: Duration,
) -> Result<Reconciled> {
    if !learning::token(activity, 128)
        || !learning::token(attempt, 128)
        || !learning::token(event, 128)
    {
        return Err(Error::Invalid("invalid grade identity"));
    }
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let Some(mut claim) = read_claim(&tx, activity, attempt, event)? else {
        return Ok(Reconciled::NotDispatched);
    };
    if claim.state != "DISPATCHED" {
        return Ok(Reconciled::NotDispatched);
    }
    let Some(dispatched_at) = read_dispatch_time(&tx, event)? else {
        return Ok(Reconciled::NoDispatchTime);
    };
    let now = learning::now()?;
    if now < dispatched_at.saturating_add(stale_after.as_secs()) {
        return Ok(Reconciled::NotStale);
    }
    claim.state = "UNKNOWN".into();
    store_claim(&tx, &claim, false)?;
    tx.commit()?;
    Ok(Reconciled::Abandoned)
}

/// Result of the one-shot restart reconciliation.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct RestartFinalization {
    /// Dispatched claims older than the grace window that are now terminal UNKNOWN.
    pub abandoned: usize,
    /// Claim pairs too damaged to prove identity or age; left untouched.
    pub skipped: usize,
    /// Dispatched claims still inside the grace window; left untouched.
    pub recent: usize,
}

/// Finalize grading dispatches left over from a previous Core process.
///
/// A Core restart cannot complete a claim that the previous process dispatched:
/// the owned bridge is gone, so no receipt can arrive. The function marks
/// `DISPATCHED` claims terminal UNKNOWN only when their recorded dispatch second is
/// older than `grace`, which must cover the maximum grading budget plus transport
/// margin. A younger claim is left untouched so a second process that is still
/// grading cannot be cancelled, and a claim without a trusted dispatch second is
/// never guessed stale. It never launches, re-sends or retries a worker; repeating
/// it is a no-op once claims are terminal.
pub fn abandon_dispatched_after_restart(
    conn: &mut Connection,
    grace: Duration,
) -> Result<RestartFinalization> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let keys = {
        let mut statement =
            tx.prepare("SELECT key FROM workspace_meta WHERE key GLOB 'provider_grade_attempt_*'")?;
        let rows = statement.query_map([], |row| row.get::<_, String>(0))?;
        rows.collect::<rusqlite::Result<Vec<_>>>()?
    };
    let now = learning::now()?;
    let mut result = RestartFinalization::default();
    for key in keys {
        let Some(raw) = bounded_value(&tx, &key)? else {
            result.skipped += 1;
            continue;
        };
        let Ok(claim) = serde_json::from_str::<Claim>(&raw) else {
            result.skipped += 1;
            continue;
        };
        if !valid_claim(&key, &claim) {
            result.skipped += 1;
            continue;
        }
        if claim.state != "DISPATCHED" {
            continue;
        }
        let event_index = event_key(&claim.client_event_id);
        let Some(index_raw) = bounded_value(&tx, &event_index)? else {
            result.skipped += 1;
            continue;
        };
        let Ok(index) = serde_json::from_str::<EventIndex>(&index_raw) else {
            result.skipped += 1;
            continue;
        };
        if !valid_pair(&event_index, &index, &key, &claim, &raw) {
            result.skipped += 1;
            continue;
        }
        let Some(dispatched_at) = read_dispatch_time(&tx, &claim.client_event_id)? else {
            continue;
        };
        if now < dispatched_at.saturating_add(grace.as_secs()) {
            result.recent += 1;
            continue;
        }
        let mut unknown = claim;
        unknown.state = "UNKNOWN".into();
        store_claim(&tx, &unknown, false)?;
        result.abandoned += 1;
    }
    tx.commit()?;
    Ok(result)
}

/// Commit checks the earlier grant expiry immediately before SQLite COMMIT.
/// COMMIT itself can block or cross a wall-clock boundary; this function cannot
/// prove that durable publication finished before an expiry or clock jump.
fn complete_with_clock<C: DispatchClock>(
    conn: &mut Connection,
    prepared: &Prepared,
    observed: OwnedObservation,
    clock: &mut C,
) -> Result<Value> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let activity = learning::activity(&tx, &prepared.claim.activity_id)?;
    if let Some(receipt) = terminal(
        &tx,
        &activity,
        &prepared.claim.attempt_id,
        &prepared.request,
        &prepared.claim.request_sha256,
    )? {
        return Ok(receipt);
    }
    // A failed finalization must never retry an old observation after clock
    // rollback. Historical duplicate receipts above remain read-only.
    if prepared.finalization_started.swap(true, Ordering::SeqCst) {
        return Err(Error::Conflict("grade finalization already attempted"));
    }
    let mut last_wall = None;
    sample_wall(clock, &mut last_wall)?;
    let (activity, expiry) = revalidate_with(&tx, prepared, "DISPATCHED", || {
        sample_wall(clock, &mut last_wall).map(|wall| wall.as_secs())
    })?;
    if !wall_unexpired(clock, expiry, &mut last_wall) {
        return Err(Error::Conflict(
            "grade authorization expired or clock changed",
        ));
    }
    let worker: WorkerResponse = serde_json::from_value(observed.response)
        .map_err(|_| Error::Invalid("invalid worker observation"))?;
    if worker.schema != SCHEMA
        || worker.request_id != prepared.claim.client_event_id
        || worker.status != "OBSERVED"
        || worker.provider != "deeptutor"
        || worker.adapter_version != "1.7.1"
        || worker.upstream_member_sha256 != UPSTREAM_SHA256
        || worker.input_sha256 != prepared.claim.worker_input_sha256
        || worker.question_binding != "caller_declared_unverified"
        || worker.independent_mastery != "not_established"
    {
        return Err(Error::Invalid("worker observation identity mismatch"));
    }
    let submission = Submission {
        client_event_id: prepared.request.client_event_id.clone(),
        answer: prepared.request.answer.clone(),
        provider_correct: worker.provider_correct,
        self_report: false,
        rating: None,
    };
    learning::submission_shape(&submission)?;
    let evidence = GradeEvidence {
        question_document: prepared.request.question_document.clone(),
        question_grant: prepared.request.question_grant.clone(),
        request_sha256: prepared.claim.request_sha256.clone(),
        worker_input_sha256: prepared.claim.worker_input_sha256.clone(),
        upstream_member_sha256: worker.upstream_member_sha256,
        origin_restore_epoch: prepared.claim.origin_restore_epoch.clone(),
    };
    let raw = serde_json::to_string(&StoredResult {
        request: submission.clone(),
        material_status_at_submission: "current".into(),
        grade: Some(evidence.clone()),
    })
    .map_err(|_| Error::Invalid("invalid grade result"))?;
    let result_sha = learning::digest(&raw);
    if !wall_unexpired(clock, expiry, &mut last_wall) {
        return Err(Error::Conflict(
            "grade authorization expired or clock changed",
        ));
    }
    let changed = tx.execute("UPDATE learning_provider_attempts SET state='submitted',client_event_id=?1,result_json=?2,result_sha256=?3,completed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE activity_id=?4 AND attempt_id=?5 AND state='pending'",
        params![submission.client_event_id,raw,result_sha,activity.activity_id,prepared.claim.attempt_id])?;
    if changed != 1 {
        return Err(Error::Conflict("attempt already terminal"));
    }
    let mut completed = prepared.claim.clone();
    completed.state = "COMPLETED".into();
    completed.result_sha256 = Some(result_sha);
    store_claim(&tx, &completed, false)?;
    if !wall_unexpired(clock, expiry, &mut last_wall) {
        return Err(Error::Conflict(
            "grade authorization expired or clock changed",
        ));
    }
    tx.commit()?;
    Ok(learning::result_receipt(
        &activity.activity_id,
        &prepared.claim.attempt_id,
        &submission,
        false,
        "current",
        "current",
        Some(&evidence),
    ))
}

/// Verify persisted grade evidence without requiring a live grant or replaying
/// the process. Historical results remain readable after revoke or restore.
pub(crate) fn validate_stored(
    conn: &Connection,
    activity: &Activity,
    attempt: &str,
    stored: &StoredResult,
    origin: &str,
    raw: &str,
) -> Result<()> {
    let grade = stored
        .grade
        .as_ref()
        .ok_or(Error::Invalid("grade evidence absent"))?;
    if activity.provider.id != "deeptutor"
        || activity.provider.version != "1.7.1"
        || stored.request.self_report
        || stored.request.rating.is_some()
        || stored.material_status_at_submission != "current"
        || grade.upstream_member_sha256 != UPSTREAM_SHA256
        || grade.origin_restore_epoch != origin
        || !grant::valid_snapshot_shape(&grade.question_document)
        || !grant::valid_snapshot_shape(&grade.question_grant)
    {
        return Err(Error::Invalid("stored grade evidence invalid"));
    }
    let request = GradeRequest {
        client_event_id: stored.request.client_event_id.clone(),
        answer: stored.request.answer.clone(),
        question_document: grade.question_document.clone(),
        question_grant: grade.question_grant.clone(),
    };
    let claim = read_claim(
        conn,
        &activity.activity_id,
        attempt,
        &request.client_event_id,
    )?
    .ok_or(Error::Invalid("stored grade claim unavailable"))?;
    if claim.state != "COMPLETED"
        || claim.request_sha256 != request_hash(activity, attempt, &request)
        || claim.request_sha256 != grade.request_sha256
        || claim.worker_input_sha256 != grade.worker_input_sha256
        || claim.question_document != grade.question_document
        || claim.question_grant != grade.question_grant
        || claim.origin_restore_epoch != grade.origin_restore_epoch
        || claim.result_sha256.as_deref() != Some(learning::digest(raw).as_str())
    {
        return Err(Error::Invalid("stored grade claim mismatch"));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        backup, document,
        provider_learning::{self, Cancel, Provider, Question, Start},
        provider_question,
    };

    fn snap(value: &Value) -> Snapshot {
        Snapshot {
            document_id: value["document_id"].as_str().unwrap().into(),
            version: value["version"].as_i64().unwrap(),
            content_sha256: value["content_sha256"].as_str().unwrap().into(),
        }
    }
    fn permission(conn: &mut Connection, value: &Value, expiry: Option<u64>) -> Value {
        document::create_optional(conn,None,None,"synthetic grant",json!({"type":"doc","content":[],"attrs":{
            "archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1",
                "purpose":"practice","consumer":"deeptutor","operations":["practice"],"material":snap(value),
                "authorization_basis":"SYNTHETIC human grant","expires_at":expiry,"state":"granted"}
        }})).unwrap()
    }
    struct Fixture {
        _dir: tempfile::TempDir,
        conn: Connection,
        activity: Activity,
        source: Value,
        question: Value,
        source_grant: Value,
        question_grant: Value,
        request: GradeRequest,
    }
    fn fixture() -> Fixture {
        fixture_with_expiry(None, None)
    }
    fn fixture_with_expiry(source_expiry: Option<u64>, question_expiry: Option<u64>) -> Fixture {
        let dir = tempfile::tempdir().unwrap();
        let mut conn =
            archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
                .unwrap();
        let source = document::create_optional(
            &mut conn,
            None,
            None,
            "source",
            json!({"type":"doc","content":[]}),
        )
        .unwrap();
        let question=document::create_optional(&mut conn,None,None,"question",json!({"type":"doc","content":[],"attrs":{
            "archeaxis_deeptutor_question":{"schema":"archeaxis.deeptutor-question/v1","source_material":snap(&source),
                "origin":"user_import_unverified","question":{"question_id":"question_1","question":"synthetic?",
                "question_type":"choice","options":{"A":"first","B":"second"},"correct_answer":"SYNTHETIC_KEY","explanation":"hidden"}}
        }})).unwrap();
        let source_grant = permission(&mut conn, &source, source_expiry);
        let question_grant = permission(&mut conn, &question, question_expiry);
        let view = provider_question::read_view(&conn, &snap(&question)).unwrap();
        let activity = Activity {
            activity_id: "activity".into(),
            material: snap(&source),
            provider: Provider {
                id: "deeptutor".into(),
                version: "1.7.1".into(),
            },
            question: Question {
                question_id: "question_1".into(),
                question_version: view["question_version"].as_str().unwrap().into(),
            },
            grant: Some(snap(&source_grant)),
        };
        provider_learning::create(&mut conn, &activity).unwrap();
        provider_learning::start(
            &mut conn,
            "activity",
            &Start {
                attempt_id: "attempt".into(),
            },
        )
        .unwrap();
        let request = GradeRequest {
            client_event_id: "event".into(),
            question_document: snap(&question),
            question_grant: snap(&question_grant),
            answer: "SYNTHETIC_ANSWER".into(),
        };
        Fixture {
            _dir: dir,
            conn,
            activity,
            source,
            question,
            source_grant,
            question_grant,
            request,
        }
    }
    fn ready(f: &mut Fixture) -> Prepared {
        match prepare(&mut f.conn, "activity", "attempt", &f.request).unwrap() {
            Admission::Ready(prepared) => prepared,
            _ => panic!("expected new reservation"),
        }
    }
    struct SyntheticSink {
        bytes: Vec<u8>,
        fail_after: Option<usize>,
        writes: usize,
        quiescent: bool,
    }
    impl BoundedDispatch for SyntheticSink {
        fn write_chunk(&mut self, bytes: &[u8], _: Instant) -> bool {
            if self.fail_after == Some(self.writes) {
                return false;
            }
            self.writes += 1;
            self.bytes.extend_from_slice(bytes);
            true
        }
        fn writes_quiescent(&mut self, _: Instant) -> bool {
            self.quiescent
        }
    }
    fn sink() -> SyntheticSink {
        SyntheticSink {
            bytes: Vec::new(),
            fail_after: None,
            writes: 0,
            quiescent: true,
        }
    }
    struct FakeClock {
        mono: std::rc::Rc<std::cell::Cell<Instant>>,
        wall_now: std::rc::Rc<std::cell::Cell<Duration>>,
        wall_samples: std::collections::VecDeque<Duration>,
    }
    impl DispatchClock for FakeClock {
        fn monotonic(&self) -> Instant {
            self.mono.get()
        }
        fn wall(&mut self) -> Result<Duration> {
            Ok(self.wall_samples.pop_front().unwrap_or(self.wall_now.get()))
        }
    }
    fn fake_clock(wall: Duration) -> FakeClock {
        FakeClock {
            mono: std::rc::Rc::new(std::cell::Cell::new(Instant::now())),
            wall_now: std::rc::Rc::new(std::cell::Cell::new(wall)),
            wall_samples: Default::default(),
        }
    }
    fn dispatched(f: &mut Fixture) -> Prepared {
        let prepared = ready(f);
        let mut output = sink();
        match dispatch_bounded(
            &mut f.conn,
            prepared,
            &mut output,
            Instant::now() + Duration::from_secs(1),
        )
        .unwrap()
        {
            DispatchOutcome::Dispatched(prepared) => {
                assert_eq!(output.bytes, prepared.stdin);
                prepared
            }
            DispatchOutcome::Unknown => panic!("expected synthetic dispatch"),
        }
    }
    // Only tests can create a simulated proof. This is not an actual process or
    // a claim that DeepTutor, a model, or a human has run.
    fn synthetic(prepared: &Prepared, correct: Option<bool>) -> OwnedObservation {
        OwnedObservation {
            response: json!({"schema":SCHEMA,"request_id":prepared.claim.client_event_id,
            "status":"OBSERVED","provider":"deeptutor","adapter_version":"1.7.1",
            "upstream_member_sha256":UPSTREAM_SHA256,"input_sha256":prepared.claim.worker_input_sha256,
            "provider_correct":correct,"question_binding":"caller_declared_unverified","independent_mastery":"not_established"}),
        }
    }
    // Test-only copies model a separately forged late observation. Production
    // Prepared is intentionally not Clone and never exposes its fields.
    fn synthetic_duplicate(prepared: &Prepared) -> Prepared {
        Prepared {
            request: prepared.request.clone(),
            claim: prepared.claim.clone(),
            stdin: prepared.stdin.clone(),
            finalization_started: AtomicBool::new(false),
        }
    }
    fn manual(event: &str) -> Submission {
        Submission {
            client_event_id: event.into(),
            answer: "manual".into(),
            provider_correct: None,
            self_report: true,
            rating: None,
        }
    }
    fn assert_no_plaintext(conn: &Connection) {
        let mut stmt = conn
            .prepare("SELECT value FROM workspace_meta WHERE key LIKE 'provider_grade_%'")
            .unwrap();
        let rows = stmt
            .query_map([], |r| r.get::<_, String>(0))
            .unwrap()
            .collect::<rusqlite::Result<Vec<_>>>()
            .unwrap();
        // The claim and its event index always exist; a dispatch-time note with the
        // wall-clock second is added once a dispatch intent is committed. None of
        // these three keys may carry answer or key plaintext.
        assert!(
            rows.len() == 2 || rows.len() == 3,
            "unexpected provider_grade metadata count: {}",
            rows.len()
        );
        for value in rows {
            assert!(!value.contains("SYNTHETIC_ANSWER") && !value.contains("SYNTHETIC_KEY"));
        }
    }

    #[test]
    fn dispatch_rechecks_both_grants_attempt_and_document_versions_before_writing() {
        for case in [
            "cancel",
            "source_grant",
            "question_grant",
            "source",
            "question",
        ] {
            let mut f = fixture();
            let prepared = ready(&mut f);
            match case {
                "cancel" => {
                    provider_learning::cancel(
                        &mut f.conn,
                        "activity",
                        "attempt",
                        &Cancel {
                            client_cancel_id: "cancel_before_dispatch".into(),
                        },
                    )
                    .unwrap();
                }
                "source_grant" | "question_grant" => {
                    let g = if case == "source_grant" {
                        &f.source_grant
                    } else {
                        &f.question_grant
                    };
                    let mut edit = g["editor_json"].clone();
                    edit["attrs"]["archeaxis_provider_material_grant"]["state"] = json!("revoked");
                    document::save(&mut f.conn, g["document_id"].as_str().unwrap(), 1, edit)
                        .unwrap();
                }
                _ => {
                    let d = if case == "source" {
                        &f.source
                    } else {
                        &f.question
                    };
                    let mut edit = d["editor_json"].clone();
                    edit["attrs"]["revision"] = json!("changed");
                    document::save(&mut f.conn, d["document_id"].as_str().unwrap(), 1, edit)
                        .unwrap();
                }
            }
            let mut output = sink();
            assert!(
                dispatch_bounded(
                    &mut f.conn,
                    prepared,
                    &mut output,
                    Instant::now() + Duration::from_secs(1)
                )
                .is_err(),
                "{case}"
            );
            assert!(output.bytes.is_empty(), "{case}");
            assert!(
                prepare(&mut f.conn, "activity", "attempt", &f.request).is_err(),
                "{case}"
            );
        }
    }

    #[test]
    fn unconfirmed_or_failed_dispatch_cannot_complete_or_be_replayed() {
        for case in ["failed_write", "partial_write", "unknown_cleanup"] {
            let mut f = fixture();
            if case == "partial_write" {
                f.request.answer = "synthetic".repeat(1000);
            }
            let prepared = ready(&mut f);
            // This duplicate exists only in the synthetic test so that a
            // forged late observation can be rejected after token consumption.
            let shadow = synthetic_duplicate(&prepared);
            let late = synthetic_duplicate(&prepared);
            assert!(complete(&mut f.conn, &shadow, synthetic(&shadow, Some(true))).is_err());
            let mut output = sink();
            output.fail_after = match case {
                "failed_write" => Some(0),
                "partial_write" => Some(1),
                _ => None,
            };
            output.quiescent = case != "unknown_cleanup";
            assert!(
                matches!(
                    dispatch_bounded(
                        &mut f.conn,
                        prepared,
                        &mut output,
                        Instant::now() + Duration::from_secs(1)
                    ),
                    Ok(DispatchOutcome::Unknown)
                ),
                "{case}"
            );
            if case == "partial_write" {
                assert_eq!(output.bytes.len(), 4096);
            }
            let claim = read_claim(&f.conn, "activity", "attempt", "event")
                .unwrap()
                .unwrap();
            assert_eq!(claim.state, "UNKNOWN", "{case}");
            assert!(
                complete(&mut f.conn, &late, synthetic(&late, Some(true))).is_err(),
                "{case}"
            );
            assert!(
                matches!(
                    prepare(&mut f.conn, "activity", "attempt", &f.request),
                    Ok(Admission::Unknown)
                ),
                "{case}"
            );
            assert_no_plaintext(&f.conn);
        }
    }

    #[test]
    fn dispatch_update_failure_after_write_keeps_reservation_and_prevents_replay() {
        let mut f = fixture();
        let prepared = ready(&mut f);
        let mut output = sink();
        f.conn.execute_batch("CREATE TEMP TRIGGER synthetic_grade_failure BEFORE UPDATE OF value ON workspace_meta WHEN NEW.key GLOB 'provider_grade_attempt_*' BEGIN SELECT RAISE(ABORT,'synthetic failure'); END;").unwrap();
        assert!(
            dispatch_bounded(
                &mut f.conn,
                prepared,
                &mut output,
                Instant::now() + Duration::from_secs(1)
            )
            .is_err()
        );
        assert!(!output.bytes.is_empty());
        assert_eq!(
            read_claim(&f.conn, "activity", "attempt", "event")
                .unwrap()
                .unwrap()
                .state,
            "RESERVED"
        );
        assert!(matches!(
            prepare(&mut f.conn, "activity", "attempt", &f.request),
            Ok(Admission::Unknown)
        ));
        assert_no_plaintext(&f.conn);
    }

    #[test]
    fn restored_reservation_cannot_dispatch_with_old_epoch() {
        let mut f = fixture();
        let prepared = ready(&mut f);
        let path = f._dir.path().join("before-dispatch-backup.sqlite");
        backup::backup(&f.conn, path.to_str().unwrap()).unwrap();
        let mut restored = archeaxis_store_sqlite::init_workspace(
            f._dir
                .path()
                .join("before-dispatch-restored.sqlite")
                .to_str()
                .unwrap(),
        )
        .unwrap();
        assert!(backup::restore_authorized(path.to_str().unwrap(), &mut restored).unwrap());
        let mut output = sink();
        assert!(
            dispatch_bounded(
                &mut restored,
                prepared,
                &mut output,
                Instant::now() + Duration::from_secs(1)
            )
            .is_err()
        );
        assert!(output.bytes.is_empty());
    }

    #[test]
    fn source_expiring_while_question_grant_is_checked_prevents_first_write() {
        let expiry = learning::now().unwrap() + 120;
        let mut f = fixture_with_expiry(Some(expiry), Some(expiry + 20));
        let prepared = ready(&mut f);
        let mut clock = fake_clock(Duration::from_secs(expiry));
        clock.wall_samples = [
            Duration::from_secs(expiry - 1),
            Duration::from_secs(expiry - 1),
            Duration::from_secs(expiry),
            Duration::from_secs(expiry),
        ]
        .into();
        let deadline = clock.monotonic() + Duration::from_secs(1);
        let mut output = sink();
        assert!(
            dispatch_with_clock(&mut f.conn, prepared, &mut output, deadline, &mut clock).is_err()
        );
        assert!(output.bytes.is_empty());
    }

    #[test]
    fn wall_clock_backwards_between_grant_checks_prevents_first_write() {
        let expiry = learning::now().unwrap() + 120;
        let mut f = fixture_with_expiry(Some(expiry), Some(expiry + 20));
        let prepared = ready(&mut f);
        let mut clock = fake_clock(Duration::from_secs(expiry - 2));
        clock.wall_samples = [
            Duration::from_secs(expiry - 1),
            Duration::from_secs(expiry - 1),
            Duration::from_secs(expiry - 2),
        ]
        .into();
        let deadline = clock.monotonic() + Duration::from_secs(1);
        let mut output = sink();
        assert!(
            dispatch_with_clock(&mut f.conn, prepared, &mut output, deadline, &mut clock).is_err()
        );
        assert!(output.bytes.is_empty());
    }

    #[test]
    fn wall_clock_backwards_between_initial_sample_and_revalidation_fails_closed() {
        let expiry = learning::now().unwrap() + 120;
        let mut f = fixture_with_expiry(Some(expiry), Some(expiry + 20));
        let prepared = ready(&mut f);
        let mut clock = fake_clock(Duration::from_secs(expiry - 10));
        clock.wall_samples = [
            Duration::from_secs(expiry - 1),
            Duration::from_secs(expiry - 10),
        ]
        .into();
        let deadline = clock.monotonic() + Duration::from_secs(1);
        let mut output = sink();
        assert!(
            dispatch_with_clock(&mut f.conn, prepared, &mut output, deadline, &mut clock).is_err()
        );
        assert!(output.bytes.is_empty());
    }

    #[test]
    fn either_grant_expiring_between_chunks_blocks_remaining_chunks() {
        for earlier in ["source", "question"] {
            let expiry = learning::now().unwrap() + 120;
            let (source, question) = if earlier == "source" {
                (expiry, expiry + 20)
            } else {
                (expiry + 20, expiry)
            };
            let mut f = fixture_with_expiry(Some(source), Some(question));
            f.request.answer = "synthetic".repeat(1000);
            let prepared = ready(&mut f);
            let before = Duration::from_secs(expiry - 1);
            let after = Duration::from_secs(expiry);
            let mut clock = fake_clock(after);
            // Baseline, source grant, question grant, initial cap, first
            // chunk pre/post, and second chunk's wall-time check.
            clock.wall_samples = [before, before, before, before, before, before, after].into();
            let deadline = clock.monotonic() + Duration::from_millis(1500);
            let mut output = sink();
            assert!(
                matches!(
                    dispatch_with_clock(&mut f.conn, prepared, &mut output, deadline, &mut clock),
                    Ok(DispatchOutcome::Unknown)
                ),
                "{earlier}"
            );
            assert_eq!(output.bytes.len(), 4096, "{earlier}");
            assert_eq!(
                read_claim(&f.conn, "activity", "attempt", "event")
                    .unwrap()
                    .unwrap()
                    .state,
                "UNKNOWN"
            );
        }
    }

    #[test]
    fn expiry_during_write_or_backward_wall_jump_is_unknown() {
        struct JumpSink {
            bytes: Vec<u8>,
            wall: std::rc::Rc<std::cell::Cell<Duration>>,
            mono: std::rc::Rc<std::cell::Cell<Instant>>,
            next_wall: Duration,
            next_mono: Instant,
        }
        impl BoundedDispatch for JumpSink {
            fn write_chunk(&mut self, bytes: &[u8], _: Instant) -> bool {
                self.bytes.extend_from_slice(bytes);
                self.wall.set(self.next_wall);
                self.mono.set(self.next_mono);
                true
            }
            fn writes_quiescent(&mut self, _: Instant) -> bool {
                true
            }
        }
        for case in ["forward_during_write", "backward_wall", "monotonic_cap"] {
            let expiry = learning::now().unwrap() + 120;
            let mut f = fixture_with_expiry(Some(expiry), Some(expiry + 20));
            let prepared = ready(&mut f);
            let mut clock = fake_clock(Duration::from_secs(expiry - 1));
            let start = clock.monotonic();
            let next_wall = Duration::from_secs(match case {
                "forward_during_write" => expiry,
                "backward_wall" => expiry - 2,
                _ => expiry - 1,
            });
            // Backward-wall detection is exercised while the monotonic limit
            // is still valid; the separate case verifies the initial cap.
            let next_mono = if case == "monotonic_cap" {
                start + Duration::from_millis(1001)
            } else {
                start + Duration::from_millis(100)
            };
            let mut output = JumpSink {
                bytes: Vec::new(),
                wall: clock.wall_now.clone(),
                mono: clock.mono.clone(),
                next_wall,
                next_mono,
            };
            let deadline = start + Duration::from_millis(1500);
            assert!(
                matches!(
                    dispatch_with_clock(&mut f.conn, prepared, &mut output, deadline, &mut clock),
                    Ok(DispatchOutcome::Unknown)
                ),
                "{case}"
            );
            // The synthetic write happened; post-write detection cannot prove
            // that an actual OS pipe stopped before the clock changed.
            assert!(!output.bytes.is_empty(), "{case}");
        }
    }

    #[test]
    fn result_transaction_rolls_back_on_expiry_or_clock_rollback() {
        for case in [
            "between_grants",
            "before_update",
            "before_commit",
            "backward_before_commit",
        ] {
            let expiry = learning::now().unwrap() + 120;
            let mut f = fixture_with_expiry(Some(expiry), Some(expiry + 20));
            let prepared = dispatched(&mut f);
            let before = Duration::from_secs(expiry - 1);
            let after = Duration::from_secs(expiry);
            let mut clock = fake_clock(after);
            clock.wall_samples = match case {
                // baseline, source grant, question grant, post-validation
                "between_grants" => vec![before, before, after, after],
                // post-validation, before UPDATE, before COMMIT
                "before_update" => vec![before, before, before, before, after],
                "before_commit" => vec![before, before, before, before, before, after],
                _ => vec![
                    before,
                    before,
                    before,
                    before,
                    before,
                    Duration::from_secs(expiry - 2),
                ],
            }
            .into();
            assert!(
                complete_with_clock(
                    &mut f.conn,
                    &prepared,
                    synthetic(&prepared, Some(true)),
                    &mut clock
                )
                .is_err(),
                "{case}"
            );
            let (state,result):(String,Option<String>)=f.conn.query_row(
                "SELECT state,result_json FROM learning_provider_attempts WHERE activity_id='activity' AND attempt_id='attempt'",
                [],|r|Ok((r.get(0)?,r.get(1)?))).unwrap();
            assert_eq!(state, "pending", "{case}");
            assert!(result.is_none(), "{case}");
            assert_eq!(
                read_claim(&f.conn, "activity", "attempt", "event")
                    .unwrap()
                    .unwrap()
                    .state,
                "DISPATCHED",
                "{case}"
            );
            // The same in-memory observation cannot be retried after a clock
            // rewind. A restart cannot reconstruct Prepared from a claim.
            let mut rewound = fake_clock(before);
            assert!(
                complete_with_clock(
                    &mut f.conn,
                    &prepared,
                    synthetic(&prepared, Some(true)),
                    &mut rewound
                )
                .is_err(),
                "{case}"
            );
            assert!(
                matches!(
                    prepare(&mut f.conn, "activity", "attempt", &f.request),
                    Ok(Admission::Unknown)
                ),
                "{case}"
            );
        }
    }

    #[test]
    fn synthetic_dispatch_and_cancellation_serialize_on_the_database() {
        use std::sync::mpsc;
        struct PausedSink {
            entered: mpsc::Sender<()>,
            release: mpsc::Receiver<()>,
        }
        impl BoundedDispatch for PausedSink {
            fn write_chunk(&mut self, _: &[u8], deadline: Instant) -> bool {
                self.entered.send(()).is_ok()
                    && self
                        .release
                        .recv_timeout(deadline.saturating_duration_since(Instant::now()))
                        .is_ok()
            }
            fn writes_quiescent(&mut self, _: Instant) -> bool {
                true
            }
        }
        let mut f = fixture();
        let prepared = ready(&mut f);
        let path = f._dir.path().join("db.sqlite");
        let mut first = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
        let mut second = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
        let (entered_tx, entered_rx) = mpsc::channel();
        let (release_tx, release_rx) = mpsc::channel();
        let dispatch = std::thread::spawn(move || {
            let mut output = PausedSink {
                entered: entered_tx,
                release: release_rx,
            };
            match dispatch_bounded(
                &mut first,
                prepared,
                &mut output,
                Instant::now() + Duration::from_millis(1900),
            ) {
                Ok(DispatchOutcome::Dispatched(prepared)) => Some(prepared),
                _ => None,
            }
        });
        entered_rx.recv_timeout(Duration::from_secs(1)).unwrap();
        let (started_tx, started_rx) = mpsc::channel();
        let (done_tx, done_rx) = mpsc::channel();
        let cancel = std::thread::spawn(move || {
            started_tx.send(()).unwrap();
            let ok = provider_learning::cancel(
                &mut second,
                "activity",
                "attempt",
                &Cancel {
                    client_cancel_id: "during_dispatch".into(),
                },
            )
            .is_ok();
            done_tx.send(ok).unwrap();
        });
        started_rx.recv_timeout(Duration::from_secs(1)).unwrap();
        assert!(done_rx.recv_timeout(Duration::from_millis(100)).is_err());
        release_tx.send(()).unwrap();
        let prepared = dispatch
            .join()
            .unwrap()
            .expect("synthetic dispatch must commit");
        assert!(done_rx.recv_timeout(Duration::from_secs(2)).unwrap());
        cancel.join().unwrap();
        assert!(complete(&mut f.conn, &prepared, synthetic(&prepared, Some(true))).is_err());
    }

    #[test]
    fn sqlite_lock_wait_can_exceed_write_deadline_but_starts_no_late_write() {
        use std::sync::mpsc;
        let mut f = fixture();
        let prepared = ready(&mut f);
        let path = f._dir.path().join("db.sqlite");
        let mut locker = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
        let mut worker = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
        let lock = locker
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .unwrap();
        let (started_tx, started_rx) = mpsc::channel();
        let (done_tx, done_rx) = mpsc::channel();
        let thread = std::thread::spawn(move || {
            let deadline = Instant::now() + Duration::from_millis(200);
            let mut output = sink();
            started_tx.send(()).unwrap();
            let result = dispatch_bounded(&mut worker, prepared, &mut output, deadline);
            done_tx
                .send((
                    matches!(result, Ok(DispatchOutcome::Unknown)),
                    output.bytes.len(),
                ))
                .unwrap();
        });
        started_rx.recv_timeout(Duration::from_secs(1)).unwrap();
        // BEGIN waits under the Store's busy timeout; this is not an overall
        // two-second call guarantee. Release only after the write deadline.
        assert!(done_rx.recv_timeout(Duration::from_millis(300)).is_err());
        lock.commit().unwrap();
        let (unknown, bytes) = done_rx.recv_timeout(Duration::from_secs(2)).unwrap();
        thread.join().unwrap();
        assert!(unknown);
        assert_eq!(bytes, 0);
    }

    #[test]
    fn reservation_requires_two_grants_and_never_stores_plaintext_or_replays() {
        let mut f = fixture();
        let mut wrong = f.request.clone();
        wrong.question_grant = snap(&f.source_grant);
        assert!(prepare(&mut f.conn, "activity", "attempt", &wrong).is_err());
        let input = json!({"client_event_id":"event","question_document":f.request.question_document,
            "question_grant":f.request.question_grant,"answer":"x","correct_answer":"injected"});
        assert!(serde_json::from_value::<GradeRequest>(input).is_err());
        let forged = json!({"client_event_id":"event","question_document":f.request.question_document,
            "question_grant":f.request.question_grant,"answer":"x","provider_correct":true,
            "input_sha256":"0".repeat(64)});
        assert!(serde_json::from_value::<GradeRequest>(forged).is_err());
        let prepared = ready(&mut f);
        let payload: Value = serde_json::from_slice(prepared.worker_stdin()).unwrap();
        assert_eq!(payload["question"]["correct_answer"], "SYNTHETIC_KEY");
        assert!(prepared.worker_stdin().ends_with(b"\n"));
        assert_eq!(
            hash_bytes(prepared.worker_stdin()),
            prepared.claim.worker_input_sha256
        );
        assert_no_plaintext(&f.conn);
        assert!(matches!(
            prepare(&mut f.conn, "activity", "attempt", &f.request),
            Ok(Admission::Unknown)
        ));
        let mut changed = f.request.clone();
        changed.answer = "changed".into();
        assert!(prepare(&mut f.conn, "activity", "attempt", &changed).is_err());
        let mut other_event = f.request.clone();
        other_event.client_event_id = "different".into();
        assert!(prepare(&mut f.conn, "activity", "attempt", &other_event).is_err());
        assert!(
            provider_learning::submit(&mut f.conn, "activity", "attempt", &manual("different"))
                .is_err()
        );
        provider_learning::start(
            &mut f.conn,
            "activity",
            &Start {
                attempt_id: "other".into(),
            },
        )
        .unwrap();
        assert!(
            provider_learning::submit(&mut f.conn, "activity", "other", &manual("event")).is_err()
        );
        let mut another = f.activity.clone();
        another.activity_id = "other_activity".into();
        provider_learning::create(&mut f.conn, &another).unwrap();
        provider_learning::start(
            &mut f.conn,
            "other_activity",
            &Start {
                attempt_id: "attempt".into(),
            },
        )
        .unwrap();
        assert!(prepare(&mut f.conn, "other_activity", "attempt", &f.request).is_err());
        assert!(
            provider_learning::submit(&mut f.conn, "other_activity", "attempt", &manual("event"))
                .is_err()
        );
        assert_eq!(
            f.conn
                .query_row("SELECT count(*) FROM learning_events", [], |r| r
                    .get::<_, i64>(0))
                .unwrap(),
            0
        );
    }

    #[test]
    fn synthetic_result_is_atomic_idempotent_and_digest_bound() {
        let mut f = fixture();
        let prepared = dispatched(&mut f);
        let first = complete(&mut f.conn, &prepared, synthetic(&prepared, None)).unwrap();
        assert!(first["provider_correct"].is_null());
        assert_eq!(first["independent_mastery"], "not_established");
        assert_eq!(
            first["provider_result_verification"],
            "local_upstream_worker_observation"
        );
        assert_eq!(
            complete(&mut f.conn, &prepared, synthetic(&prepared, None)).unwrap()["duplicate"],
            true
        );
        assert!(
            provider_learning::cancel(
                &mut f.conn,
                "activity",
                "attempt",
                &Cancel {
                    client_cancel_id: "after_commit".into()
                }
            )
            .is_err()
        );
        match prepare(&mut f.conn, "activity", "attempt", &f.request).unwrap() {
            Admission::Completed(receipt) => assert_eq!(receipt["duplicate"], true),
            _ => panic!("expected history"),
        }
        let history = provider_learning::read(&f.conn, "activity", None).unwrap();
        assert_eq!(
            history["attempts"][0]["provider_result_verification"],
            "local_upstream_worker_observation"
        );
        assert_no_plaintext(&f.conn);
        assert_eq!(
            f.conn
                .query_row("SELECT count(*) FROM learning_events", [], |r| r
                    .get::<_, i64>(0))
                .unwrap(),
            0
        );
        let (raw,):(String,)=f.conn.query_row("SELECT result_json FROM learning_provider_attempts WHERE activity_id='activity' AND attempt_id='attempt'",[],|r|Ok((r.get(0)?,))).unwrap();
        let mut altered: Value = serde_json::from_str(&raw).unwrap();
        altered["request"]["provider_correct"] = json!(true);
        let changed = altered.to_string();
        f.conn.execute("UPDATE learning_provider_attempts SET result_json=?1,result_sha256=?2 WHERE activity_id='activity' AND attempt_id='attempt'",params![changed,learning::digest(&changed)]).unwrap();
        assert!(provider_learning::read(&f.conn, "activity", None).is_err());
        assert!(prepare(&mut f.conn, "activity", "attempt", &f.request).is_err());
    }

    #[test]
    fn cancel_or_withdrawal_prevents_late_result_and_old_claim_reuse() {
        for case in [
            "cancel",
            "source_grant",
            "question_grant",
            "source",
            "question",
        ] {
            let mut f = fixture();
            let prepared = dispatched(&mut f);
            match case {
                "cancel" => {
                    provider_learning::cancel(
                        &mut f.conn,
                        "activity",
                        "attempt",
                        &Cancel {
                            client_cancel_id: "cancel".into(),
                        },
                    )
                    .unwrap();
                }
                "source_grant" | "question_grant" => {
                    let g = if case == "source_grant" {
                        &f.source_grant
                    } else {
                        &f.question_grant
                    };
                    let mut edit = g["editor_json"].clone();
                    edit["attrs"]["archeaxis_provider_material_grant"]["state"] = json!("revoked");
                    document::save(&mut f.conn, g["document_id"].as_str().unwrap(), 1, edit)
                        .unwrap();
                }
                "source" | "question" => {
                    let d = if case == "source" {
                        &f.source
                    } else {
                        &f.question
                    };
                    let mut edit = d["editor_json"].clone();
                    edit["attrs"]["unrelated_revision"] = json!("changed");
                    document::save(&mut f.conn, d["document_id"].as_str().unwrap(), 1, edit)
                        .unwrap();
                }
                _ => unreachable!(),
            }
            assert!(
                complete(&mut f.conn, &prepared, synthetic(&prepared, Some(true))).is_err(),
                "{case}"
            );
            assert!(
                prepare(&mut f.conn, "activity", "attempt", &f.request).is_err(),
                "{case}"
            );
            assert_eq!(
                f.conn
                    .query_row(
                        "SELECT count(*) FROM learning_provider_attempts WHERE state='submitted'",
                        [],
                        |r| r.get::<_, i64>(0)
                    )
                    .unwrap(),
                0,
                "{case}"
            );
        }
    }

    #[test]
    fn malformed_observation_and_expired_grants_fail_closed() {
        let mut f = fixture();
        let expired = permission(&mut f.conn, &f.question, Some(0));
        let mut request = f.request.clone();
        request.question_grant = snap(&expired);
        assert!(prepare(&mut f.conn, "activity", "attempt", &request).is_err());
        let prepared = dispatched(&mut f);
        for field in [
            "input_sha256",
            "upstream_member_sha256",
            "provider_correct",
            "unknown",
        ] {
            let mut proof = synthetic(&prepared, Some(true));
            match field {
                "input_sha256" | "upstream_member_sha256" => {
                    proof.response[field] = json!("0".repeat(64))
                }
                "provider_correct" => proof.response[field] = json!("true"),
                _ => proof.response[field] = json!(true),
            }
            assert!(
                complete(&mut f.conn, &synthetic_duplicate(&prepared), proof).is_err(),
                "{field}"
            );
        }
        assert!(matches!(
            prepare(&mut f.conn, "activity", "attempt", &f.request),
            Ok(Admission::Unknown)
        ));
    }

    #[test]
    fn restore_never_reuses_a_prepared_claim_or_old_grants() {
        let mut f = fixture();
        let prepared = dispatched(&mut f);
        let path = f._dir.path().join("backup.sqlite");
        backup::backup(&f.conn, path.to_str().unwrap()).unwrap();
        let mut restored = archeaxis_store_sqlite::init_workspace(
            f._dir.path().join("restored.sqlite").to_str().unwrap(),
        )
        .unwrap();
        assert!(backup::restore_authorized(path.to_str().unwrap(), &mut restored).unwrap());
        assert!(prepare(&mut restored, "activity", "attempt", &f.request).is_err());
        assert!(complete(&mut restored, &prepared, synthetic(&prepared, Some(true))).is_err());
        assert_eq!(
            restored
                .query_row(
                    "SELECT count(*) FROM learning_provider_attempts WHERE state='submitted'",
                    [],
                    |r| r.get::<_, i64>(0)
                )
                .unwrap(),
            0
        );
    }

    #[test]
    fn restored_completed_grade_is_only_a_historical_read() {
        let mut f = fixture();
        let prepared = dispatched(&mut f);
        complete(&mut f.conn, &prepared, synthetic(&prepared, Some(true))).unwrap();
        let path = f._dir.path().join("complete-backup.sqlite");
        backup::backup(&f.conn, path.to_str().unwrap()).unwrap();
        let mut restored = archeaxis_store_sqlite::init_workspace(
            f._dir
                .path()
                .join("complete-restored.sqlite")
                .to_str()
                .unwrap(),
        )
        .unwrap();
        assert!(backup::restore_authorized(path.to_str().unwrap(), &mut restored).unwrap());
        match prepare(&mut restored, "activity", "attempt", &f.request).unwrap() {
            Admission::Completed(receipt) => assert_eq!(receipt["duplicate"], true),
            _ => panic!("expected historical read"),
        }
        assert!(
            provider_learning::start(
                &mut restored,
                "activity",
                &Start {
                    attempt_id: "new".into()
                }
            )
            .is_err()
        );
        assert_eq!(
            restored
                .query_row("SELECT count(*) FROM learning_provider_attempts", [], |r| r
                    .get::<_, i64>(0))
                .unwrap(),
            1
        );
    }

    #[test]
    fn cancellation_and_completion_have_exactly_one_transactional_winner() {
        use std::sync::{Arc, Barrier};
        let mut f = fixture();
        let prepared = dispatched(&mut f);
        let proof = synthetic(&prepared, Some(true));
        let path = f._dir.path().join("db.sqlite");
        let mut first = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
        let mut second = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
        let barrier = Arc::new(Barrier::new(2));
        let other = barrier.clone();
        let submit = std::thread::spawn(move || {
            barrier.wait();
            complete(&mut first, &prepared, proof).is_ok()
        });
        let cancel = std::thread::spawn(move || {
            other.wait();
            provider_learning::cancel(
                &mut second,
                "activity",
                "attempt",
                &Cancel {
                    client_cancel_id: "race_cancel".into(),
                },
            )
            .is_ok()
        });
        assert_eq!(
            u8::from(submit.join().unwrap()) + u8::from(cancel.join().unwrap()),
            1
        );
        let state:String=f.conn.query_row("SELECT state FROM learning_provider_attempts WHERE activity_id='activity' AND attempt_id='attempt'",[],|r|r.get(0)).unwrap();
        assert!(matches!(state.as_str(), "submitted" | "cancelled"));
        assert_eq!(
            f.conn
                .query_row("SELECT count(*) FROM learning_events", [], |r| r
                    .get::<_, i64>(0))
                .unwrap(),
            0
        );
    }

    #[test]
    fn reservation_and_manual_submit_compete_in_one_transaction() {
        use std::sync::{Arc, Barrier};
        let f = fixture();
        let path = f._dir.path().join("db.sqlite");
        let mut first = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
        let mut second = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
        let request = f.request.clone();
        let barrier = Arc::new(Barrier::new(2));
        let other = barrier.clone();
        let reserve = std::thread::spawn(move || {
            barrier.wait();
            matches!(
                prepare(&mut first, "activity", "attempt", &request),
                Ok(Admission::Ready(_))
            )
        });
        let submit = std::thread::spawn(move || {
            other.wait();
            provider_learning::submit(&mut second, "activity", "attempt", &manual("event")).is_ok()
        });
        assert_eq!(
            u8::from(reserve.join().unwrap()) + u8::from(submit.join().unwrap()),
            1
        );
        assert_eq!(
            f.conn
                .query_row(
                    "SELECT count(*) FROM learning_provider_attempts WHERE state='submitted'",
                    [],
                    |r| r.get::<_, i64>(0)
                )
                .unwrap()
                <= 1,
            true
        );
        assert_eq!(
            f.conn
                .query_row("SELECT count(*) FROM learning_events", [], |r| r
                    .get::<_, i64>(0))
                .unwrap(),
            0
        );
    }

    #[test]
    fn two_attempts_cannot_reserve_the_same_event_concurrently() {
        use std::sync::{Arc, Barrier};
        let mut f = fixture();
        provider_learning::start(
            &mut f.conn,
            "activity",
            &Start {
                attempt_id: "other".into(),
            },
        )
        .unwrap();
        let path = f._dir.path().join("db.sqlite");
        let mut first = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
        let mut second = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
        let first_request = f.request.clone();
        let second_request = f.request.clone();
        let barrier = Arc::new(Barrier::new(2));
        let other = barrier.clone();
        let one = std::thread::spawn(move || {
            barrier.wait();
            matches!(
                prepare(&mut first, "activity", "attempt", &first_request),
                Ok(Admission::Ready(_))
            )
        });
        let two = std::thread::spawn(move || {
            other.wait();
            matches!(
                prepare(&mut second, "activity", "other", &second_request),
                Ok(Admission::Ready(_))
            )
        });
        assert_eq!(
            u8::from(one.join().unwrap()) + u8::from(two.join().unwrap()),
            1
        );
        assert_no_plaintext(&f.conn);
    }

    #[test]
    fn either_half_of_a_damaged_index_still_prevents_identity_reuse() {
        use std::sync::{Arc, Barrier};
        for missing in ["attempt", "event"] {
            let mut f = fixture();
            let prepared = dispatched(&mut f);
            provider_learning::start(
                &mut f.conn,
                "activity",
                &Start {
                    attempt_id: "other".into(),
                },
            )
            .unwrap();
            provider_learning::start(
                &mut f.conn,
                "activity",
                &Start {
                    attempt_id: "unrelated".into(),
                },
            )
            .unwrap();
            let key = if missing == "attempt" {
                attempt_key("activity", "attempt")
            } else {
                event_key("event")
            };
            f.conn
                .execute("DELETE FROM workspace_meta WHERE key=?1", [key])
                .unwrap();
            let path = f._dir.path().join("db.sqlite");
            let mut first = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
            let mut second =
                archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
            let mut different = f.request.clone();
            different.client_event_id = "other_event".into();
            let barrier = Arc::new(Barrier::new(2));
            let other = barrier.clone();
            let reserve = std::thread::spawn(move || {
                barrier.wait();
                prepare(&mut first, "activity", "attempt", &different).is_ok()
            });
            let submit = std::thread::spawn(move || {
                other.wait();
                provider_learning::submit(&mut second, "activity", "other", &manual("event"))
                    .is_ok()
            });
            assert!(
                !reserve.join().unwrap() && !submit.join().unwrap(),
                "missing {missing}"
            );
            assert!(
                complete(&mut f.conn, &prepared, synthetic(&prepared, Some(true))).is_err(),
                "missing {missing}"
            );
            assert!(
                provider_learning::submit(
                    &mut f.conn,
                    "activity",
                    "unrelated",
                    &manual("unrelated_event")
                )
                .is_err(),
                "missing {missing}"
            );
            let ordinary = document::create_optional(
                &mut f.conn,
                None,
                None,
                "ordinary",
                json!({"type":"doc","content":[]}),
            )
            .unwrap();
            assert!(
                document::save(
                    &mut f.conn,
                    ordinary["document_id"].as_str().unwrap(),
                    1,
                    ordinary["editor_json"].clone()
                )
                .is_ok()
            );
        }
    }

    #[test]
    fn unattributable_double_damage_blocks_provider_submissions_but_not_document_saves() {
        use std::sync::{Arc, Barrier};
        for missing in ["attempt", "event"] {
            let mut f = fixture();
            let prepared = dispatched(&mut f);
            provider_learning::start(
                &mut f.conn,
                "activity",
                &Start {
                    attempt_id: "other".into(),
                },
            )
            .unwrap();
            let (deleted, broken) = if missing == "attempt" {
                (attempt_key("activity", "attempt"), event_key("event"))
            } else {
                (event_key("event"), attempt_key("activity", "attempt"))
            };
            f.conn
                .execute("DELETE FROM workspace_meta WHERE key=?1", [deleted])
                .unwrap();
            f.conn
                .execute("UPDATE workspace_meta SET value='{' WHERE key=?1", [broken])
                .unwrap();
            let path = f._dir.path().join("db.sqlite");
            let mut first = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
            let mut second =
                archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
            let mut changed = f.request.clone();
            changed.client_event_id = "new_event".into();
            let barrier = Arc::new(Barrier::new(2));
            let other = barrier.clone();
            let reserve = std::thread::spawn(move || {
                barrier.wait();
                prepare(&mut first, "activity", "attempt", &changed).is_ok()
            });
            let submit = std::thread::spawn(move || {
                other.wait();
                provider_learning::submit(&mut second, "activity", "other", &manual("new_manual"))
                    .is_ok()
            });
            assert!(
                !reserve.join().unwrap() && !submit.join().unwrap(),
                "missing {missing}"
            );
            assert!(
                complete(&mut f.conn, &prepared, synthetic(&prepared, Some(true))).is_err(),
                "missing {missing}"
            );
            let ordinary = document::create_optional(
                &mut f.conn,
                None,
                None,
                "ordinary",
                json!({"type":"doc","content":[]}),
            )
            .unwrap();
            let saved = document::save(
                &mut f.conn,
                ordinary["document_id"].as_str().unwrap(),
                1,
                ordinary["editor_json"].clone(),
            )
            .unwrap();
            assert_eq!(saved["version"], 2, "missing {missing}");
        }
    }

    #[test]
    fn plausible_retargeted_or_mismatched_indexes_cannot_free_an_identity() {
        use std::sync::{Arc, Barrier};
        for case in ["event_retarget", "claim_retarget", "claim_sha_mismatch"] {
            let mut f = fixture();
            let prepared = dispatched(&mut f);
            provider_learning::start(
                &mut f.conn,
                "activity",
                &Start {
                    attempt_id: "other".into(),
                },
            )
            .unwrap();
            let event = event_key("event");
            let attempt = attempt_key("activity", "attempt");
            match case {
                "event_retarget" => {
                    f.conn
                        .execute("DELETE FROM workspace_meta WHERE key=?1", [&attempt])
                        .unwrap();
                    let raw: String = f
                        .conn
                        .query_row(
                            "SELECT value FROM workspace_meta WHERE key=?1",
                            [&event],
                            |r| r.get(0),
                        )
                        .unwrap();
                    let mut index: Value = serde_json::from_str(&raw).unwrap();
                    index["attempt_key"] = json!(attempt_key("activity", "other"));
                    f.conn
                        .execute(
                            "UPDATE workspace_meta SET value=?1 WHERE key=?2",
                            params![index.to_string(), event],
                        )
                        .unwrap();
                }
                "claim_retarget" => {
                    f.conn
                        .execute("DELETE FROM workspace_meta WHERE key=?1", [&event])
                        .unwrap();
                    let raw: String = f
                        .conn
                        .query_row(
                            "SELECT value FROM workspace_meta WHERE key=?1",
                            [&attempt],
                            |r| r.get(0),
                        )
                        .unwrap();
                    let mut claim: Value = serde_json::from_str(&raw).unwrap();
                    claim["client_event_id"] = json!("retargeted_event");
                    f.conn
                        .execute(
                            "UPDATE workspace_meta SET value=?1 WHERE key=?2",
                            params![claim.to_string(), attempt],
                        )
                        .unwrap();
                }
                "claim_sha_mismatch" => {
                    let raw: String = f
                        .conn
                        .query_row(
                            "SELECT value FROM workspace_meta WHERE key=?1",
                            [&attempt],
                            |r| r.get(0),
                        )
                        .unwrap();
                    let mut claim: Value = serde_json::from_str(&raw).unwrap();
                    claim["request_sha256"] = json!("0".repeat(64));
                    f.conn
                        .execute(
                            "UPDATE workspace_meta SET value=?1 WHERE key=?2",
                            params![claim.to_string(), attempt],
                        )
                        .unwrap();
                }
                _ => unreachable!(),
            }
            let path = f._dir.path().join("db.sqlite");
            let mut first = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
            let mut second =
                archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
            let mut changed = f.request.clone();
            changed.client_event_id = "new_event".into();
            let barrier = Arc::new(Barrier::new(2));
            let other = barrier.clone();
            let reserve = std::thread::spawn(move || {
                barrier.wait();
                prepare(&mut first, "activity", "attempt", &changed).is_ok()
            });
            let submit = std::thread::spawn(move || {
                other.wait();
                provider_learning::submit(
                    &mut second,
                    "activity",
                    "other",
                    &manual("unrelated_event"),
                )
                .is_ok()
            });
            assert!(
                !reserve.join().unwrap() && !submit.join().unwrap(),
                "{case}"
            );
            assert!(
                complete(&mut f.conn, &prepared, synthetic(&prepared, Some(true))).is_err(),
                "{case}"
            );
            let ordinary = document::create_optional(
                &mut f.conn,
                None,
                None,
                "ordinary",
                json!({"type":"doc","content":[]}),
            )
            .unwrap();
            assert!(
                document::save(
                    &mut f.conn,
                    ordinary["document_id"].as_str().unwrap(),
                    1,
                    ordinary["editor_json"].clone()
                )
                .is_ok()
            );
        }
    }

    #[test]
    fn oversized_claim_or_index_cannot_bypass_bounded_revalidation() {
        for enlarged in ["claim", "index"] {
            let mut f = fixture();
            let prepared = dispatched(&mut f);
            let claim_key = attempt_key("activity", "attempt");
            let index_key = event_key("event");
            let raw: String = f
                .conn
                .query_row(
                    "SELECT value FROM workspace_meta WHERE key=?1",
                    [&claim_key],
                    |r| r.get(0),
                )
                .unwrap();
            let index_raw: String = f
                .conn
                .query_row(
                    "SELECT value FROM workspace_meta WHERE key=?1",
                    [&index_key],
                    |r| r.get(0),
                )
                .unwrap();
            if enlarged == "claim" {
                // Still valid JSON and matching index digest: structural equality
                // alone must not let an arbitrarily large row through.
                let padded = format!("{raw}{}", " ".repeat(8193));
                let mut index: Value = serde_json::from_str(&index_raw).unwrap();
                index["claim_sha256"] = json!(learning::digest(&padded));
                f.conn
                    .execute(
                        "UPDATE workspace_meta SET value=?1 WHERE key=?2",
                        params![padded, claim_key],
                    )
                    .unwrap();
                f.conn
                    .execute(
                        "UPDATE workspace_meta SET value=?1 WHERE key=?2",
                        params![index.to_string(), index_key],
                    )
                    .unwrap();
            } else {
                f.conn
                    .execute(
                        "UPDATE workspace_meta SET value=?1 WHERE key=?2",
                        params![format!("{index_raw}{}", " ".repeat(8193)), index_key],
                    )
                    .unwrap();
            }
            assert!(
                prepare(&mut f.conn, "activity", "attempt", &f.request).is_err(),
                "{enlarged}"
            );
            assert!(
                complete(&mut f.conn, &prepared, synthetic(&prepared, Some(true))).is_err(),
                "{enlarged}"
            );
            assert!(
                provider_learning::submit(
                    &mut f.conn,
                    "activity",
                    "attempt",
                    &manual("other_event")
                )
                .is_err(),
                "{enlarged}"
            );
        }
    }

    #[test]
    fn self_reported_correctness_never_claims_a_worker_observation() {
        let mut f = fixture();
        let mut submitted = manual("self_event");
        submitted.self_report = false;
        submitted.provider_correct = Some(true);
        let receipt =
            provider_learning::submit(&mut f.conn, "activity", "attempt", &submitted).unwrap();
        assert_eq!(
            receipt["provider_result_verification"],
            "unverified_client_report"
        );
        assert_eq!(receipt["question_binding"], "client_declared_unverified");
        assert!(receipt.get("grade_evidence").is_none());
        assert_eq!(receipt["independent_mastery"], "not_established");
    }

    // The fixed worker prints exactly one JSON line. These bytes model its shape
    // for the transaction tests below; only the ignored integration-worker test
    // runs the retained upstream grader.
    fn receipt_bytes(prepared: &Prepared, correct: Option<bool>) -> Vec<u8> {
        let mut bytes = serde_json::to_vec(&json!({
            "schema":SCHEMA,"request_id":prepared.claim.client_event_id,"status":"OBSERVED",
            "provider":"deeptutor","adapter_version":"1.7.1",
            "upstream_member_sha256":UPSTREAM_SHA256,
            "input_sha256":hash_bytes(prepared.worker_input()),
            "provider_correct":correct,
            "question_binding":"caller_declared_unverified",
            "independent_mastery":"not_established"
        }))
        .unwrap();
        bytes.push(b'\n');
        bytes
    }

    #[test]
    fn completion_requires_a_dispatch_intent_and_rejects_malformed_receipts() {
        let mut f = fixture();
        let early = ready(&mut f);
        assert!(matches!(
            complete_observed(&mut f.conn, &early, &receipt_bytes(&early, Some(true))),
            Err(Error::Conflict(_))
        ));
        // A burned token can never finalize the same reservation afterwards.
        assert!(matches!(
            complete_observed(&mut f.conn, &early, &receipt_bytes(&early, Some(true))),
            Err(Error::Conflict(_))
        ));

        let mut f = fixture();
        let prepared = ready(&mut f);
        assert!(matches!(
            begin_dispatch(&mut f.conn, &prepared, Duration::ZERO),
            Err(Error::Invalid(_))
        ));
        assert!(matches!(
            begin_dispatch(&mut f.conn, &prepared, Duration::from_secs(121)),
            Err(Error::Invalid(_))
        ));
        begin_dispatch(&mut f.conn, &prepared, Duration::from_secs(30)).unwrap();
        // A second dispatch of the same reservation is refused.
        assert!(begin_dispatch(&mut f.conn, &prepared, Duration::from_secs(30)).is_err());

        let good = receipt_bytes(&prepared, Some(true));
        let body = String::from_utf8(good.clone()).unwrap();
        let body = body.trim_end();
        // Framing and shape failures are refused before any finalization attempt,
        // so the reservation can still accept the one exact receipt afterwards.
        for bad in [
            String::new(),
            body.to_owned(),
            format!("{body}\n{body}\n"),
            format!("{}\n", "x".repeat(MAX_RECEIPT_BYTES)),
        ] {
            assert!(
                complete_observed(&mut f.conn, &prepared, bad.as_bytes()).is_err(),
                "accepted malformed framing: {} bytes",
                bad.len()
            );
        }
        let duplicated = body.replacen(
            "\"status\":\"OBSERVED\"",
            "\"status\":\"OBSERVED\",\"status\":\"OBSERVED\"",
            1,
        );
        let mut extra: Value = serde_json::from_str(body).unwrap();
        extra["answer"] = json!("private");
        let mut wrong_shape: Value = serde_json::from_str(body).unwrap();
        wrong_shape["provider_correct"] = json!("true");
        for bad in [duplicated, extra.to_string(), wrong_shape.to_string()] {
            assert!(
                complete_observed(&mut f.conn, &prepared, format!("{bad}\n").as_bytes()).is_err(),
                "accepted an unbound receipt"
            );
        }
        let receipt = complete_observed(&mut f.conn, &prepared, &good).unwrap();
        assert_eq!(receipt["provider_correct"], json!(true));
        assert_eq!(
            receipt["question_binding"],
            "question_document_content_bound_origin_unverified"
        );
        assert_eq!(
            receipt["provider_result_verification"],
            "local_upstream_worker_observation"
        );
        assert_eq!(receipt["independent_mastery"], "not_established");
        assert_eq!(receipt["duplicate"], false);
        assert_eq!(
            complete_observed(&mut f.conn, &prepared, &good).unwrap()["duplicate"],
            true
        );
        assert_no_plaintext(&f.conn);

        // A structurally valid receipt that is not bound to this reservation is
        // refused inside the finalization, and that attempt burns the token:
        // a mismatched observation is never retried after a clock or grant change.
        for mutate in ["input_sha256", "upstream_member_sha256", "request_id"] {
            let mut f = fixture();
            let prepared = ready(&mut f);
            begin_dispatch(&mut f.conn, &prepared, Duration::from_secs(30)).unwrap();
            let mut wrong: Value = serde_json::from_str(body).unwrap();
            wrong[mutate] = json!("0".repeat(64));
            assert!(
                complete_observed(&mut f.conn, &prepared, format!("{}\n", wrong).as_bytes())
                    .is_err(),
                "{mutate}"
            );
            assert!(
                matches!(
                    complete_observed(&mut f.conn, &prepared, &good),
                    Err(Error::Conflict(_))
                ),
                "{mutate}: a rejected observation must not free the reservation"
            );
        }
    }

    #[test]
    fn unscored_receipt_is_persisted_as_an_observed_null_not_a_failure() {
        let mut f = fixture();
        let prepared = ready(&mut f);
        begin_dispatch(&mut f.conn, &prepared, Duration::from_secs(30)).unwrap();
        let receipt =
            complete_observed(&mut f.conn, &prepared, &receipt_bytes(&prepared, None)).unwrap();
        assert!(receipt["provider_correct"].is_null());
        assert_eq!(receipt["self_report"], false);
        let history = provider_learning::read(&f.conn, "activity", None).unwrap();
        assert_eq!(history["attempts"][0]["state"], "submitted");
        assert!(history["attempts"][0]["result"]["provider_correct"].is_null());
        assert_eq!(history["provider_result_verification"], "per_attempt");
        let stored = provider_learning::submit(
            &mut f.conn,
            "activity",
            "attempt",
            &Submission {
                client_event_id: "event".into(),
                answer: "SYNTHETIC_ANSWER".into(),
                provider_correct: None,
                self_report: false,
                rating: None,
            },
        )
        .unwrap();
        assert_eq!(stored["duplicate"], true);
        assert!(stored.get("grade_evidence").is_some());
        assert!(stored["provider_correct"].is_null());
    }

    #[test]
    fn unclear_dispatch_is_unknown_and_never_automatically_relaunched() {
        let mut f = fixture();
        let prepared = ready(&mut f);
        abandon_unknown(&mut f.conn, &prepared).unwrap();
        match prepare(&mut f.conn, "activity", "attempt", &f.request).unwrap() {
            Admission::Unknown => (),
            _ => panic!("an unclear reservation was offered for a second launch"),
        }
        assert!(
            complete_observed(
                &mut f.conn,
                &prepared,
                &receipt_bytes(&prepared, Some(true))
            )
            .is_err()
        );
        assert!(abandon_unknown(&mut f.conn, &prepared).is_err());
        provider_learning::cancel(
            &mut f.conn,
            "activity",
            "attempt",
            &Cancel {
                client_cancel_id: "cancel".into(),
            },
        )
        .unwrap();
        assert!(matches!(
            prepare(&mut f.conn, "activity", "attempt", &f.request),
            Err(Error::Conflict(_))
        ));
        assert!(
            provider_learning::read(&f.conn, "activity", None).unwrap()["attempts"][0]["result"]
                .is_null()
        );
    }

    #[test]
    fn dispatch_requires_the_authorization_window_to_cover_the_whole_budget() {
        let now = learning::now().unwrap();
        let mut f = fixture_with_expiry(Some(now + 5), None);
        let prepared = ready(&mut f);
        assert!(matches!(
            begin_dispatch(&mut f.conn, &prepared, Duration::from_secs(30)),
            Err(Error::Invalid(_))
        ));
        begin_dispatch(&mut f.conn, &prepared, Duration::from_secs(2)).unwrap();
        let receipt = complete_observed(
            &mut f.conn,
            &prepared,
            &receipt_bytes(&prepared, Some(false)),
        )
        .unwrap();
        assert_eq!(receipt["provider_correct"], json!(false));
    }

    #[test]
    fn withdrawal_after_dispatch_prevents_publication_of_the_observed_result() {
        let mut f = fixture();
        let prepared = ready(&mut f);
        begin_dispatch(&mut f.conn, &prepared, Duration::from_secs(30)).unwrap();
        let mut revoked = f.source_grant["editor_json"].clone();
        revoked["attrs"]["archeaxis_provider_material_grant"]["state"] = json!("revoked");
        document::save(
            &mut f.conn,
            f.source_grant["document_id"].as_str().unwrap(),
            1,
            revoked,
        )
        .unwrap();
        assert!(
            complete_observed(
                &mut f.conn,
                &prepared,
                &receipt_bytes(&prepared, Some(true))
            )
            .is_err()
        );
        assert_eq!(
            provider_learning::read(&f.conn, "activity", None).unwrap()["attempts"][0]["state"],
            "pending"
        );
        assert!(matches!(
            prepare(&mut f.conn, "activity", "attempt", &f.request),
            Err(Error::Invalid(_))
        ));
    }
}
