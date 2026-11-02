//! Version-bound human practice observations, separate from FSRS reviews.
//! The caller supplies observations, not authoritative scores or mastery.
use crate::{
    document,
    provider_material_grant::{self as grant, Snapshot},
    ui_state,
};
use rusqlite::{Connection, OptionalExtension, TransactionBehavior, params};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug)]
pub enum Error {
    Invalid(&'static str),
    NotFound,
    Conflict(&'static str),
    Storage(rusqlite::Error),
}
impl From<rusqlite::Error> for Error {
    fn from(value: rusqlite::Error) -> Self {
        Self::Storage(value)
    }
}
type Result<T> = std::result::Result<T, Error>;

/// The Core-owned grading transaction façade for the provider bridge.
///
/// The implementation stays in the crate-private `provider_grade` module; these
/// are the only entry points a host may reach. `prepare` reserves the exact
/// client event and attempt together, `begin_dispatch` records the durable
/// dispatch intent after rechecking both grants, the attempt and the restore
/// epoch, `complete_observed` persists the fixed worker's exact receipt, and
/// `abandon_unknown` records an unclear outcome without inventing a result.
pub mod grade {
    pub use crate::provider_grade::{
        Admission, GradeRequest, Prepared, Reconciled, abandon_unknown, begin_dispatch,
        complete_observed, disposition, prepare, reconcile_stale_dispatch,
    };
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Provider {
    pub id: String,
    pub version: String,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Question {
    pub question_id: String,
    pub question_version: String,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Activity {
    pub activity_id: String,
    pub material: Snapshot,
    pub provider: Provider,
    pub question: Question,
    #[serde(deserialize_with = "Option::deserialize")]
    pub grant: Option<Snapshot>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Start {
    pub attempt_id: String,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Submission {
    pub client_event_id: String,
    pub answer: String,
    #[serde(deserialize_with = "Option::deserialize")]
    pub provider_correct: Option<bool>,
    pub self_report: bool,
    #[serde(deserialize_with = "Option::deserialize")]
    pub rating: Option<String>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Cancel {
    pub client_cancel_id: String,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct StoredResult {
    pub(crate) request: Submission,
    pub(crate) material_status_at_submission: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub(crate) grade: Option<GradeEvidence>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct GradeEvidence {
    pub(crate) question_document: Snapshot,
    pub(crate) question_grant: Snapshot,
    pub(crate) request_sha256: String,
    pub(crate) worker_input_sha256: String,
    pub(crate) upstream_member_sha256: String,
    pub(crate) origin_restore_epoch: String,
}

pub(crate) fn token(value: &str, max: usize) -> bool {
    !value.is_empty()
        && value.len() <= max
        && value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"_-".contains(&b))
}
fn version(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 256
        && value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"_-.:".contains(&b))
}
pub(crate) fn digest(value: &str) -> String {
    hex::encode(Sha256::digest(value.as_bytes()))
}
pub(crate) fn now() -> Result<u64> {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .map_err(|_| Error::Invalid("clock unavailable"))
}
pub(crate) fn epoch(conn: &Connection) -> Result<String> {
    ui_state::machine_execution_epoch(conn).map_err(|_| Error::Invalid("restore epoch unavailable"))
}
fn activity_shape(a: &Activity) -> Result<()> {
    if !token(&a.activity_id, 128)
        || !token(&a.question.question_id, 256)
        || !version(&a.question.question_version)
        || !grant::valid_snapshot_shape(&a.material)
    {
        return Err(Error::Invalid("invalid activity identity"));
    }
    match (
        a.provider.id.as_str(),
        a.provider.version.as_str(),
        &a.grant,
    ) {
        ("openmaic", "1.3.0", None) => Ok(()),
        ("deeptutor", "1.7.1", Some(g)) if grant::valid_snapshot_shape(g) => Ok(()),
        _ => Err(Error::Invalid(
            "unsupported provider, version or authorization",
        )),
    }
}
pub(crate) fn authorize(conn: &Connection, a: &Activity) -> Result<()> {
    grant::assert_material(conn, &a.material)
        .map_err(|_| Error::Invalid("material snapshot unavailable or changed"))?;
    if a.provider.id == "deeptutor" {
        let g = a
            .grant
            .as_ref()
            .ok_or(Error::Invalid("provider grant required"))?;
        grant::consume(conn, g, &a.material, now()?)
            .map_err(|_| Error::Invalid("provider grant unavailable or revoked"))?;
    }
    Ok(())
}
pub(crate) fn activity(conn: &Connection, id: &str) -> Result<Activity> {
    let row: Option<(String,String)> = conn.query_row("SELECT request_json,request_sha256 FROM learning_provider_activities WHERE activity_id=?1", [id], |r| Ok((r.get(0)?,r.get(1)?))).optional()?;
    let (raw, sha) = row.ok_or(Error::NotFound)?;
    if digest(&raw) != sha {
        return Err(Error::Invalid("stored activity digest mismatch"));
    }
    let value: Activity =
        serde_json::from_str(&raw).map_err(|_| Error::Invalid("stored activity invalid"))?;
    if value.activity_id != id {
        return Err(Error::Invalid("stored activity identity mismatch"));
    }
    activity_shape(&value)?;
    Ok(value)
}
pub(crate) fn material_status(conn: &Connection, material: &Snapshot) -> &'static str {
    if grant::assert_material(conn, material).is_err() {
        return "unavailable";
    }
    match document::read_verified(conn, &material.document_id, None) {
        Ok(current)
            if current["version"].as_i64() == Some(material.version)
                && current["content_sha256"] == material.content_sha256 =>
        {
            "current"
        }
        Ok(_) => "historical",
        Err(_) => "unavailable",
    }
}
fn activity_receipt(a: &Activity, duplicate: bool, material_status: &str) -> Value {
    json!({"schema":"archeaxis.provider-learning-activity/v1","activity":a,"duplicate":duplicate,
        "material_status":material_status,"question_binding":"client_declared_unverified","provider_identity":"adapter_declared_unverified","independent_mastery":"not_established"})
}

pub fn create(conn: &mut Connection, request: &Activity) -> Result<Value> {
    activity_shape(request)?;
    let raw = serde_json::to_string(request).map_err(|_| Error::Invalid("invalid activity"))?;
    let sha = digest(&raw);
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let prior: Option<(String,String)> = tx.query_row("SELECT request_json,request_sha256 FROM learning_provider_activities WHERE activity_id=?1", [&request.activity_id], |r| Ok((r.get(0)?,r.get(1)?))).optional()?;
    if let Some((old, old_sha)) = prior {
        if old != raw || old_sha != sha {
            return Err(Error::Conflict("activity id conflict"));
        }
        return Ok(activity_receipt(
            request,
            true,
            material_status(&tx, &request.material),
        ));
    }
    authorize(&tx, request)?;
    tx.execute("INSERT INTO learning_provider_activities(activity_id,request_json,request_sha256) VALUES(?1,?2,?3)",params![request.activity_id,raw,sha])?;
    let current = material_status(&tx, &request.material);
    // The write lock serializes grant changes, but wall-clock expiry can still
    // pass while the transaction is open. COMMIT itself may also cross it.
    authorize(&tx, request)?;
    tx.commit()?;
    Ok(activity_receipt(request, false, current))
}

pub fn start(conn: &mut Connection, activity_id: &str, request: &Start) -> Result<Value> {
    if !token(activity_id, 128) || !token(&request.attempt_id, 128) {
        return Err(Error::Invalid("invalid attempt identity"));
    }
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let a = activity(&tx, activity_id)?;
    activity_shape(&a)?;
    let old: Option<(String,String)> = tx.query_row("SELECT state,origin_restore_epoch FROM learning_provider_attempts WHERE activity_id=?1 AND attempt_id=?2",params![activity_id,request.attempt_id],|r|Ok((r.get(0)?,r.get(1)?))).optional()?;
    if let Some((state, origin)) = old {
        // A pending retry is an admission to continue, not merely a read of
        // history: restore, expiry or withdrawal must prevent its reuse.
        if state == "pending" {
            if origin != epoch(&tx)? {
                return Err(Error::Conflict("restored attempt requires a new attempt"));
            }
            authorize(&tx, &a)?;
        }
        let current = material_status(&tx, &a.material);
        if state == "pending" {
            authorize(&tx, &a)?;
        }
        return Ok(
            json!({"schema":"archeaxis.provider-learning-attempt/v1","activity_id":activity_id,"attempt_id":request.attempt_id,"state":state,"origin_restore_epoch":origin,"duplicate":true,"material_status":current}),
        );
    }
    authorize(&tx, &a)?;
    let origin = epoch(&tx)?;
    tx.execute("INSERT INTO learning_provider_attempts(activity_id,attempt_id,origin_restore_epoch,state) VALUES(?1,?2,?3,'pending')",params![activity_id,request.attempt_id,origin])?;
    let current = material_status(&tx, &a.material);
    authorize(&tx, &a)?;
    tx.commit()?;
    Ok(
        json!({"schema":"archeaxis.provider-learning-attempt/v1","activity_id":activity_id,"attempt_id":request.attempt_id,"state":"pending","origin_restore_epoch":origin,"duplicate":false,"material_status":current}),
    )
}

pub(crate) fn submission_shape(s: &Submission) -> Result<()> {
    if !token(&s.client_event_id, 128)
        || s.answer.len() > 20_000
        || s.answer.contains('\0')
        || s.rating
            .as_deref()
            .is_some_and(|r| !matches!(r, "again" | "hard" | "good" | "easy"))
    {
        return Err(Error::Invalid("invalid practice observation"));
    }
    Ok(())
}
pub(crate) fn result_receipt(
    activity_id: &str,
    attempt_id: &str,
    s: &Submission,
    duplicate: bool,
    material_status: &str,
    material_status_now: &str,
    grade: Option<&GradeEvidence>,
) -> Value {
    let mut receipt = json!({"schema":"archeaxis.provider-learning-result/v1","activity_id":activity_id,"attempt_id":attempt_id,
        "client_event_id":s.client_event_id,"answer":s.answer,"provider_correct":s.provider_correct,
        "self_report":s.self_report,"rating":s.rating,"duplicate":duplicate,"material_status":material_status,"material_status_now":material_status_now,
        "question_binding":if grade.is_some(){"question_document_content_bound_origin_unverified"}else{"client_declared_unverified"},
        "provider_result_verification":if grade.is_some(){"local_upstream_worker_observation"}else{"unverified_client_report"},
        "independent_mastery":"not_established"});
    if let Some(evidence) = grade {
        receipt["grade_evidence"] = json!(evidence);
    }
    receipt
}
pub fn submit(
    conn: &mut Connection,
    activity_id: &str,
    attempt_id: &str,
    request: &Submission,
) -> Result<Value> {
    if !token(activity_id, 128) || !token(attempt_id, 128) {
        return Err(Error::Invalid("invalid attempt identity"));
    }
    submission_shape(request)?;
    let raw = serde_json::to_string(request).map_err(|_| Error::Invalid("invalid submission"))?;
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let prior: Option<(String,String,String,String)> = tx.query_row("SELECT activity_id,attempt_id,result_json,result_sha256 FROM learning_provider_attempts WHERE client_event_id=?1",[&request.client_event_id],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?))).optional()?;
    if let Some((old_activity, old_attempt, old, old_sha)) = prior {
        let stored: StoredResult =
            serde_json::from_str(&old).map_err(|_| Error::Invalid("stored submission invalid"))?;
        let stored_request = serde_json::to_string(&stored.request)
            .map_err(|_| Error::Invalid("stored submission invalid"))?;
        if digest(&old) != old_sha {
            return Err(Error::Invalid("stored submission digest mismatch"));
        }
        if old_activity != activity_id || old_attempt != attempt_id || stored_request != raw {
            return Err(Error::Conflict("event id conflict"));
        }
        if !matches!(
            stored.material_status_at_submission.as_str(),
            "current" | "historical"
        ) {
            return Err(Error::Invalid("stored material status invalid"));
        }
        let a = activity(&tx, activity_id)?;
        if stored.grade.is_some() {
            let origin: String = tx.query_row("SELECT origin_restore_epoch FROM learning_provider_attempts WHERE activity_id=?1 AND attempt_id=?2",params![activity_id,attempt_id],|r|r.get(0))?;
            crate::provider_grade::validate_stored(&tx, &a, attempt_id, &stored, &origin, &old)?;
        }
        return Ok(result_receipt(
            activity_id,
            attempt_id,
            request,
            true,
            &stored.material_status_at_submission,
            material_status(&tx, &a.material),
            stored.grade.as_ref(),
        ));
    }
    if crate::provider_grade::is_reserved(&tx, activity_id, attempt_id, &request.client_event_id)? {
        return Err(Error::Conflict(
            "practice event or attempt already reserved",
        ));
    }
    let a = activity(&tx, activity_id)?;
    activity_shape(&a)?;
    let stored: Option<(String,String)> = tx.query_row("SELECT state,origin_restore_epoch FROM learning_provider_attempts WHERE activity_id=?1 AND attempt_id=?2",params![activity_id,attempt_id],|r|Ok((r.get(0)?,r.get(1)?))).optional()?;
    let (state, origin) = stored.ok_or(Error::NotFound)?;
    if state != "pending" {
        return Err(Error::Conflict("attempt already terminal"));
    }
    if origin != epoch(&tx)? {
        return Err(Error::Conflict("restored attempt requires a new attempt"));
    }
    if a.provider.id == "deeptutor" && request.self_report && request.provider_correct.is_some() {
        return Err(Error::Invalid("self-report cannot be a provider grade"));
    }
    if a.provider.id == "deeptutor"
        && request.provider_correct == Some(false)
        && request.rating.as_deref().is_some_and(|r| r != "again")
    {
        return Err(Error::Invalid(
            "incorrect provider observation requires again",
        ));
    }
    if a.provider.id == "openmaic" && request.provider_correct.is_some() {
        return Err(Error::Invalid(
            "local course comparison is not a provider grade",
        ));
    }
    authorize(&tx, &a)?;
    let current = material_status(&tx, &a.material);
    if current == "unavailable" {
        return Err(Error::Invalid("current material state unavailable"));
    }
    let stored = serde_json::to_string(&StoredResult {
        request: request.clone(),
        material_status_at_submission: current.into(),
        grade: None,
    })
    .map_err(|_| Error::Invalid("invalid submission"))?;
    let stored_sha = digest(&stored);
    tx.execute("UPDATE learning_provider_attempts SET state='submitted',client_event_id=?1,result_json=?2,result_sha256=?3,completed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE activity_id=?4 AND attempt_id=?5 AND state='pending'",params![request.client_event_id,stored,stored_sha,activity_id,attempt_id])?;
    authorize(&tx, &a)?;
    tx.commit()?;
    Ok(result_receipt(
        activity_id,
        attempt_id,
        request,
        false,
        current,
        current,
        None,
    ))
}

pub fn cancel(
    conn: &mut Connection,
    activity_id: &str,
    attempt_id: &str,
    request: &Cancel,
) -> Result<Value> {
    if !token(activity_id, 128) || !token(attempt_id, 128) || !token(&request.client_cancel_id, 128)
    {
        return Err(Error::Invalid("invalid cancellation identity"));
    }
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let prior: Option<(String,String)> = tx.query_row("SELECT activity_id,attempt_id FROM learning_provider_attempts WHERE client_cancel_id=?1",[&request.client_cancel_id],|r|Ok((r.get(0)?,r.get(1)?))).optional()?;
    if let Some((old_activity, old_attempt)) = prior {
        if old_activity != activity_id || old_attempt != attempt_id {
            return Err(Error::Conflict("cancellation id conflict"));
        }
        return Ok(
            json!({"schema":"archeaxis.provider-learning-cancel/v1","activity_id":activity_id,"attempt_id":attempt_id,"client_cancel_id":request.client_cancel_id,"state":"cancelled","duplicate":true,"provider_stop_state":"unknown"}),
        );
    }
    let state: Option<String> = tx
        .query_row(
            "SELECT state FROM learning_provider_attempts WHERE activity_id=?1 AND attempt_id=?2",
            params![activity_id, attempt_id],
            |r| r.get(0),
        )
        .optional()?;
    if state.ok_or(Error::NotFound)? != "pending" {
        return Err(Error::Conflict("attempt already terminal"));
    }
    tx.execute("UPDATE learning_provider_attempts SET state='cancelled',client_cancel_id=?1,completed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE activity_id=?2 AND attempt_id=?3 AND state='pending'",params![request.client_cancel_id,activity_id,attempt_id])?;
    tx.commit()?;
    Ok(
        json!({"schema":"archeaxis.provider-learning-cancel/v1","activity_id":activity_id,"attempt_id":attempt_id,"client_cancel_id":request.client_cancel_id,"state":"cancelled","duplicate":false,"provider_stop_state":"unknown"}),
    )
}

pub fn read(conn: &Connection, activity_id: &str, after_attempt_id: Option<&str>) -> Result<Value> {
    if !token(activity_id, 128) || after_attempt_id.is_some_and(|after| !token(after, 128)) {
        return Err(Error::Invalid("invalid history cursor"));
    }
    let a = activity(conn, activity_id)?;
    let mut statement = conn.prepare("SELECT attempt_id,state,origin_restore_epoch,client_event_id,result_json,result_sha256,client_cancel_id,created_at,completed_at FROM learning_provider_attempts WHERE activity_id=?1 AND (?2 IS NULL OR attempt_id>?2) ORDER BY attempt_id LIMIT 101")?;
    let rows = statement
        .query_map(params![activity_id, after_attempt_id], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, String>(1)?,
                r.get::<_, String>(2)?,
                r.get::<_, Option<String>>(3)?,
                r.get::<_, Option<String>>(4)?,
                r.get::<_, Option<String>>(5)?,
                r.get::<_, Option<String>>(6)?,
                r.get::<_, String>(7)?,
                r.get::<_, Option<String>>(8)?,
            ))
        })?
        .collect::<rusqlite::Result<Vec<_>>>()?;
    let next_cursor = if rows.len() > 100 {
        Some(rows[99].0.clone())
    } else {
        None
    };
    let mut items = Vec::new();
    let mut has_grade = false;
    for (id, state, origin, event, raw, sha, cancelled, created, completed) in
        rows.into_iter().take(100)
    {
        let result = match (raw, sha) {
            (Some(raw), Some(sha)) => {
                let stored: StoredResult = serde_json::from_str(&raw)
                    .map_err(|_| Error::Invalid("stored submission invalid"))?;
                if digest(&raw) != sha
                    || event.as_deref() != Some(stored.request.client_event_id.as_str())
                    || !matches!(
                        stored.material_status_at_submission.as_str(),
                        "current" | "historical"
                    )
                {
                    return Err(Error::Invalid("stored event identity mismatch"));
                }
                if stored.grade.is_some() {
                    crate::provider_grade::validate_stored(conn, &a, &id, &stored, &origin, &raw)?;
                }
                Some(stored)
            }
            (None, None) => None,
            _ => return Err(Error::Invalid("stored submission digest mismatch")),
        };
        let mut item = json!({"attempt_id":id,"state":state,"origin_restore_epoch":origin,"client_event_id":event,"result":result.as_ref().map(|r|&r.request),"material_status_at_submission":result.as_ref().map(|r|&r.material_status_at_submission),"client_cancel_id":cancelled,"created_at":created,"completed_at":completed});
        if let Some(grade) = result.as_ref().and_then(|r| r.grade.as_ref()) {
            has_grade = true;
            item["grade_evidence"] = json!(grade);
            item["question_binding"] = json!("question_document_content_bound_origin_unverified");
            item["provider_result_verification"] = json!("local_upstream_worker_observation");
        }
        items.push(item);
    }
    let current = material_status(conn, &a.material);
    Ok(
        json!({"schema":"archeaxis.provider-learning-history/v1","activity":a,"attempts":items,"next_cursor":next_cursor,
        "material_status":current,"question_binding":if has_grade{"per_attempt"}else{"client_declared_unverified"},"provider_identity":"adapter_declared_unverified","provider_result_verification":if has_grade{"per_attempt"}else{"unverified_client_report"},"independent_mastery":"not_established"}),
    )
}
