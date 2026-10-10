//! Append-only teaching records. Actor authorization belongs to the real Core principal.
//! Content is inert text. No provider, filesystem execution, knowledge mutation or FSRS write.
use rusqlite::{Connection, OptionalExtension, TransactionBehavior, params};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};

pub const RECORD_SCHEMA: &str = "archeaxis.teaching-record/v2";
pub const EXCHANGE_SCHEMA: &str = "archeaxis.teaching-exchange/v2";
pub const WITHDRAWAL_SCHEMA: &str = "archeaxis.teaching-withdrawal/v2";
pub const EXCHANGE_MAX_BYTES: usize = 4 * 1024 * 1024;
#[derive(Debug)]
pub enum TeachingError {
    Invalid(String),
    NotFound(String),
    Conflict(String),
    Withdrawn(String),
    Storage(rusqlite::Error),
}
impl From<rusqlite::Error> for TeachingError {
    fn from(value: rusqlite::Error) -> Self {
        Self::Storage(value)
    }
}
impl std::fmt::Display for TeachingError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Invalid(s) => write!(f, "invalid teaching record: {s}"),
            Self::NotFound(s) => write!(f, "teaching reference not found: {s}"),
            Self::Conflict(s) => write!(f, "teaching conflict: {s}"),
            Self::Withdrawn(s) => write!(f, "teaching record withdrawn: {s}"),
            Self::Storage(e) => write!(f, "teaching storage: {e}"),
        }
    }
}
impl std::error::Error for TeachingError {}
type Result<T> = std::result::Result<T, TeachingError>;
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum RecordKind {
    Observation,
    Requirement,
    Proposal,
    Delivery,
    TeachBack,
    Feedback,
    Revision,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum RecordScope {
    Personal,
    ManualExchange,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum RecordPrivacy {
    LocalOnly,
    AuthorizedExport,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum FeedbackClass {
    ProfessionalBasis,
    EvidenceFidelity,
    RecognitionQuality,
    ExpressionFit,
    OperationFault,
    Mastery,
    AiQualification,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ProducerKind {
    HumanAuthored,
    ExternalMaterial,
    MachineGenerated,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct TeachingRecord {
    pub schema: String,
    pub record_id: String,
    pub kind: RecordKind,
    pub knowledge_id: String,
    pub knowledge_version: String,
    pub course_id: Option<String>,
    pub parent_id: Option<String>,
    pub purpose: String,
    pub scope: RecordScope,
    pub privacy: RecordPrivacy,
    pub content: String,
    pub feedback_class: Option<FeedbackClass>,
    pub assessment_id: Option<String>,
    pub rubric_version: Option<String>,
    pub assisted: bool,
    pub producer_kind: ProducerKind,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct RecordView {
    pub record: TeachingRecord,
    pub content_sha256: String,
    pub withdrawn: bool,
    pub scoring_status: String,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct WriteReceipt {
    pub item: RecordView,
    pub duplicate: bool,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct RecordPage {
    pub items: Vec<RecordView>,
    pub next_cursor: Option<String>,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Withdrawal {
    pub schema: String,
    pub withdrawal_id: String,
    pub record_id: String,
    pub reason: String,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct WithdrawalReceipt {
    pub withdrawal_id: String,
    pub record_id: String,
    pub duplicate: bool,
    pub affected_record_ids: Vec<String>,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ExchangeBundle {
    pub schema: String,
    pub records: Vec<TeachingRecord>,
    pub package_sha256: String,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ImportReceipt {
    pub items: Vec<RecordView>,
    pub duplicate_count: usize,
    pub package_sha256: String,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ImportPreview {
    pub valid: bool,
    pub record_count: usize,
    pub duplicate_count: usize,
    pub package_sha256: String,
}
fn invalid(message: &str) -> TeachingError {
    TeachingError::Invalid(message.into())
}
fn token(value: &str, max: usize) -> Result<()> {
    if value.is_empty()
        || value.len() > max
        || !value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_' || b == b'.')
        || value == "."
        || value == ".."
    {
        return Err(invalid(
            "identifier must be bounded ASCII token without paths",
        ));
    }
    Ok(())
}
fn text(value: &str, max: usize) -> Result<()> {
    if value.trim().is_empty() || value.len() > max {
        return Err(invalid("text is blank or exceeds UTF-8 byte bound"));
    }
    Ok(())
}
fn sorted(value: Value) -> Value {
    match value {
        Value::Object(map) => {
            let mut fields: Vec<_> = map.into_iter().collect();
            fields.sort_by(|a, b| a.0.cmp(&b.0));
            Value::Object(fields.into_iter().map(|(k, v)| (k, sorted(v))).collect())
        }
        Value::Array(items) => Value::Array(items.into_iter().map(sorted).collect()),
        other => other,
    }
}
fn canonical<T: Serialize + ?Sized>(value: &T) -> Result<String> {
    serde_json::to_value(value)
        .and_then(|v| serde_json::to_string(&sorted(v)))
        .map_err(|_| invalid("canonical serialization failed"))
}
fn hash<T: Serialize + ?Sized>(value: &T) -> Result<String> {
    Ok(hex::encode(Sha256::digest(canonical(value)?.as_bytes())))
}
pub fn package_hash(records: &[TeachingRecord]) -> Result<String> {
    hash(records)
}
fn shape(record: &TeachingRecord) -> Result<()> {
    if record.schema != RECORD_SCHEMA {
        return Err(invalid("record schema"));
    }
    token(&record.record_id, 128)?;
    token(&record.knowledge_id, 256)?;
    token(&record.knowledge_version, 256)?;
    if record.knowledge_id != record.knowledge_version {
        return Err(invalid(
            "knowledge_version must be immutable knowledge ID, not review hash",
        ));
    }
    for id in [&record.course_id, &record.parent_id, &record.assessment_id] {
        if let Some(id) = id {
            token(id, 256)?;
        }
    }
    if let Some(id) = &record.parent_id {
        token(id, 128)?;
        if id == &record.record_id {
            return Err(invalid("self parent"));
        }
    }
    if let Some(version) = &record.rubric_version {
        token(version, 128)?;
    }
    text(&record.purpose, 512)?;
    text(&record.content, 65536)?;
    if record.feedback_class.is_some() && record.kind != RecordKind::Feedback {
        return Err(invalid("feedback_class belongs only to feedback"));
    }
    Ok(())
}
fn parent_shape(record: &TeachingRecord, parent: Option<&TeachingRecord>) -> Result<()> {
    use RecordKind::*;
    match (&record.kind, parent.map(|r| &r.kind)) {
        (Observation, None)
        | (Requirement, None)
        | (Requirement, Some(Observation))
        | (Proposal, Some(Requirement))
        | (Delivery, Some(Proposal))
        | (Delivery, Some(Revision))
        | (TeachBack, Some(Delivery))
        | (Feedback, Some(Delivery))
        | (Revision, Some(Feedback)) => {}
        _ => return Err(invalid("parent kind does not follow teaching lineage")),
    }
    if let Some(parent) = parent {
        if record.kind != Revision
            && ((parent.course_id.is_some() || matches!(record.kind, TeachBack | Feedback))
                && record.course_id != parent.course_id)
        {
            return Err(invalid("course context changes require explicit revision"));
        }
        if record.kind != Revision
            && (record.knowledge_id != parent.knowledge_id
                || record.knowledge_version != parent.knowledge_version)
        {
            return Err(invalid("knowledge changes require explicit revision"));
        }
    }
    Ok(())
}
fn stored_record(conn: &Connection, id: &str) -> Result<Option<(TeachingRecord, String)>> {
    let row: Option<(String, Option<String>, String, String, String)> = conn.query_row(
        "SELECT record_id,parent_id,kind,record_json,content_sha256 FROM teaching_records WHERE record_id=?1",
        [id], |r| Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?,r.get(4)?)),
    ).optional()?;
    let Some((stored_id, parent_id, kind, json, checksum)) = row else { return Ok(None); };
    let record: TeachingRecord = serde_json::from_str(&json).map_err(|_| invalid("stored record DTO"))?;
    shape(&record)?;
    let expected_kind = serde_json::to_value(&record.kind).map_err(|_| invalid("stored record kind"))?;
    if record.record_id != stored_id || record.record_id != id
        || record.parent_id != parent_id || expected_kind.as_str() != Some(kind.as_str()) {
        return Err(invalid("stored record metadata disagrees with DTO"));
    }
    if hash(&record)? != checksum { return Err(invalid("stored record checksum")); }
    Ok(Some((record, checksum)))
}
fn is_withdrawn(conn: &Connection, id: &str) -> Result<bool> {
    let mut current = Some(id.to_owned());
    let mut seen = BTreeSet::new();
    let mut withdrawn = false;
    while let Some(id) = current {
        if !seen.insert(id.clone()) || seen.len() > 128 {
            return Err(invalid("stored lineage cycle or depth"));
        }
        let (record, _) = stored_record(conn, &id)?.ok_or_else(|| invalid("stored ancestor missing"))?;
        let mut stmt = conn.prepare("SELECT withdrawal_id,record_id,request_json,content_sha256 FROM teaching_withdrawals WHERE record_id=?1")?;
        let rows = stmt.query_map([&id], |r| Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,String>(2)?,r.get::<_,String>(3)?)))?;
        for row in rows {
            let (withdrawal_id, target, json, checksum) = row?;
            let request: Withdrawal = serde_json::from_str(&json).map_err(|_| invalid("stored withdrawal DTO"))?;
            if request.schema != WITHDRAWAL_SCHEMA || request.withdrawal_id != withdrawal_id
                || request.record_id != target || hash(&request)? != checksum {
                return Err(invalid("stored withdrawal metadata/checksum"));
            }
            token(&request.withdrawal_id, 128)?;
            text(&request.reason, 512)?;
            withdrawn = true;
        }
        current = record.parent_id;
    }
    Ok(withdrawn)
}
pub fn get(conn: &Connection, id: &str) -> Result<Option<RecordView>> {
    token(id, 128)?;
    let Some((record, content_sha256)) = stored_record(conn, id)? else {
        return Ok(None);
    };
    Ok(Some(RecordView {
        record,
        content_sha256,
        withdrawn: is_withdrawn(conn, id)?,
        scoring_status: "not_scored".into(),
    }))
}
fn references(
    conn: &Connection,
    record: &TeachingRecord,
    parent: Option<&TeachingRecord>,
) -> Result<()> {
    let info: Option<(String, String, Option<String>)> = conn
        .query_row(
            "SELECT status,knowledge_type,anchor_id FROM knowledge WHERE knowledge_id=?1",
            [&record.knowledge_id],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
        )
        .optional()?;
    let Some((status, knowledge_type, anchor_id)) = info else {
        return Err(TeachingError::NotFound("knowledge".into()));
    };
    if record.kind == RecordKind::Delivery {
        if !crate::knowledge::is_knowledge_active(conn, &record.knowledge_id)?
            || (status != "accepted"
                && !matches!(
                    knowledge_type.as_str(),
                    "PERSONAL_DEFINITION" | "PERSONAL_EXPERIENCE"
                ))
        {
            return Err(TeachingError::Conflict(
                "new delivery requires current accepted or personal knowledge".into(),
            ));
        }
        if let Some(anchor) = anchor_id {
            let current:bool=conn.query_row("SELECT EXISTS(SELECT 1 FROM anchors a JOIN sources s ON s.source_id=a.source_id WHERE a.anchor_id=?1 AND a.source_revision=s.sha256)",[anchor],|r|r.get(0))?;
            if !current {
                return Err(TeachingError::Conflict("source binding stale".into()));
            }
        }
    }
    if let Some(id) = &record.course_id {
        let course = crate::course::read_candidate(conn, id)?
            .ok_or_else(|| TeachingError::NotFound("course".into()))?;
        let matched = course["bindings"].as_array().is_some_and(|bindings| {
            bindings.iter().any(|b| {
                b["knowledge_id"] == record.knowledge_id
                    && b["knowledge_version"] == record.knowledge_version
            })
        });
        if !matched {
            return Err(invalid("course is bound to different knowledge"));
        }
        if record.kind == RecordKind::Delivery && course["stale"] != false {
            return Err(TeachingError::Conflict(
                "new delivery course binding stale".into(),
            ));
        }
    }
    if let Some(id) = &record.assessment_id {
        let assessment = crate::learning::assessment_by_id(conn, id)?
            .ok_or_else(|| TeachingError::NotFound("assessment".into()))?;
        if assessment.knowledge_id != record.knowledge_id
            || assessment.knowledge_version != record.knowledge_version
        {
            return Err(invalid("assessment knowledge version mismatch"));
        }
        if let Some(course_id) = &record.course_id {
            let course = crate::course::read_candidate(conn, course_id)?
                .ok_or_else(|| TeachingError::NotFound("course".into()))?;
            let matched = course["manifest"]["artifacts"]
                .as_array()
                .is_some_and(|artifacts| {
                    artifacts.iter().any(|a| {
                        a["artifact_id"].as_str().is_some_and(|id| {
                            assessment.item_key == format!("course:{course_id}:artifact:{id}")
                        })
                    })
                });
            if !matched {
                return Err(invalid("assessment does not belong to course artifact"));
            }
        }
    }
    if let Some(parent) = parent {
        if record.kind == RecordKind::Revision && record.knowledge_id != parent.knowledge_id {
            let linked:bool=conn.query_row("WITH RECURSIVE lineage(id) AS (SELECT ?1 UNION SELECT k.new_knowledge_id FROM knowledge_supersedes k JOIN lineage l ON k.old_knowledge_id=l.id) SELECT EXISTS(SELECT 1 FROM lineage WHERE id=?2)",params![parent.knowledge_id,record.knowledge_id],|r|r.get(0))?;
            if !linked {
                return Err(invalid(
                    "new knowledge revision is not descended from parent knowledge",
                ));
            }
        }
    }
    Ok(())
}
fn insert(conn: &Connection, record: &TeachingRecord) -> Result<()> {
    let kind = canonical(&record.kind)?;
    conn.execute("INSERT INTO teaching_records(record_id,parent_id,kind,record_json,content_sha256) VALUES(?1,?2,?3,?4,?5)",params![record.record_id,record.parent_id,kind.trim_matches('"'),canonical(record)?,hash(record)?])?;
    Ok(())
}
pub fn put(conn: &mut Connection, record: &TeachingRecord) -> Result<WriteReceipt> {
    shape(record)?;
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    if let Some(existing) = get(&tx, &record.record_id)? {
        if existing.content_sha256 != hash(record)? || existing.record != *record {
            return Err(TeachingError::Conflict(
                "record_id already has different canonical content".into(),
            ));
        }
        tx.commit()?;
        return Ok(WriteReceipt {
            item: existing,
            duplicate: true,
        });
    }
    let parent = if let Some(id) = &record.parent_id {
        Some(get(&tx, id)?.ok_or_else(|| TeachingError::NotFound("parent".into()))?)
    } else {
        None
    };
    if parent.as_ref().is_some_and(|r| r.withdrawn) {
        return Err(TeachingError::Withdrawn("parent".into()));
    }
    parent_shape(record, parent.as_ref().map(|r| &r.record))?;
    references(&tx, record, parent.as_ref().map(|r| &r.record))?;
    insert(&tx, record)?;
    let item = get(&tx, &record.record_id)?.ok_or_else(|| invalid("insert readback"))?;
    tx.commit()?;
    Ok(WriteReceipt {
        item,
        duplicate: false,
    })
}
pub fn list(conn: &Connection, cursor: Option<&str>) -> Result<RecordPage> {
    if let Some(cursor) = cursor {
        token(cursor, 128)?;
    }
    let mut stmt = conn.prepare(
        "SELECT record_id FROM teaching_records WHERE record_id>?1 ORDER BY record_id LIMIT 21",
    )?;
    let mut ids = stmt
        .query_map([cursor.unwrap_or("")], |r| r.get::<_, String>(0))?
        .collect::<std::result::Result<Vec<_>, _>>()?;
    let more = ids.len() > 20;
    ids.truncate(20);
    let next_cursor = if more { ids.last().cloned() } else { None };
    let items = ids
        .iter()
        .map(|id| get(conn, id)?.ok_or_else(|| invalid("list readback")))
        .collect::<Result<Vec<_>>>()?;
    Ok(RecordPage { items, next_cursor })
}
fn descendants(conn: &Connection, id: &str) -> Result<Vec<String>> {
    let mut stmt=conn.prepare("WITH RECURSIVE children(id) AS (SELECT ?1 UNION SELECT t.record_id FROM teaching_records t JOIN children c ON t.parent_id=c.id) SELECT id FROM children ORDER BY id")?;
    let ids = stmt
        .query_map([id], |r| r.get(0))?
        .collect::<std::result::Result<Vec<String>, _>>()?;
    for id in &ids {
        get(conn, id)?.ok_or_else(|| invalid("withdraw descendant missing"))?;
    }
    Ok(ids)
}
pub fn withdraw(conn: &mut Connection, request: &Withdrawal) -> Result<WithdrawalReceipt> {
    if request.schema != WITHDRAWAL_SCHEMA {
        return Err(invalid("withdrawal schema"));
    }
    token(&request.withdrawal_id, 128)?;
    token(&request.record_id, 128)?;
    text(&request.reason, 512)?;
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let stored: Option<(String,String,String)> = tx
        .query_row(
            "SELECT content_sha256,record_id,request_json FROM teaching_withdrawals WHERE withdrawal_id=?1",
            [&request.withdrawal_id],
            |r| Ok((r.get(0)?,r.get(1)?,r.get(2)?)),
        )
        .optional()?;
    if let Some((checksum,target,json)) = &stored {
        let original: Withdrawal = serde_json::from_str(json).map_err(|_|invalid("stored withdrawal DTO"))?;
        if &original.record_id != target || original.withdrawal_id != request.withdrawal_id || hash(&original)? != *checksum {
            return Err(invalid("stored withdrawal metadata/checksum"));
        }
        if checksum != &hash(request)? || original != *request {
            return Err(TeachingError::Conflict(
                "withdrawal_id reused with different content".into(),
            ));
        }
    }
    get(&tx, &request.record_id)?
        .ok_or_else(|| TeachingError::NotFound("withdraw target".into()))?;
    let duplicate = stored.is_some();
    if !duplicate {
        tx.execute("INSERT INTO teaching_withdrawals(withdrawal_id,record_id,request_json,content_sha256) VALUES(?1,?2,?3,?4)",params![request.withdrawal_id,request.record_id,canonical(request)?,hash(request)?])?;
    }
    let affected_record_ids = descendants(&tx, &request.record_id)?;
    tx.commit()?;
    Ok(WithdrawalReceipt {
        withdrawal_id: request.withdrawal_id.clone(),
        record_id: request.record_id.clone(),
        duplicate,
        affected_record_ids,
    })
}
pub fn export_bundle(conn: &Connection, id: &str) -> Result<ExchangeBundle> {
    token(id, 128)?;
    let mut current = Some(id.to_owned());
    let mut seen = BTreeSet::new();
    let mut records = Vec::new();
    while let Some(id) = current {
        if !seen.insert(id.clone()) || seen.len() > 128 {
            return Err(invalid("lineage cycle or exchange depth"));
        }
        let item = get(conn, &id)?
            .ok_or_else(|| TeachingError::NotFound("export record/ancestor".into()))?;
        if item.withdrawn {
            return Err(TeachingError::Withdrawn("export record/ancestor".into()));
        }
        if item.record.scope != RecordScope::ManualExchange {
            return Err(TeachingError::Conflict("record/ancestor is personal; manual exchange not authorized".into()));
        }
        if item.record.privacy != RecordPrivacy::AuthorizedExport {
            return Err(TeachingError::Conflict(
                "record/ancestor is local_only, export not authorized".into(),
            ));
        }
        current = item.record.parent_id.clone();
        records.push(item.record);
    }
    records.reverse();
    if canonical(&records)?.len() > EXCHANGE_MAX_BYTES {
        return Err(invalid("exchange serialized byte budget"));
    }
    let package_sha256 = package_hash(&records)?;
    Ok(ExchangeBundle {
        schema: EXCHANGE_SCHEMA.into(),
        records,
        package_sha256,
    })
}
fn visit(
    id: &str,
    batch: &BTreeMap<String, TeachingRecord>,
    visiting: &mut BTreeSet<String>,
    done: &mut BTreeSet<String>,
    ordered: &mut Vec<String>,
) -> Result<()> {
    if done.contains(id) {
        return Ok(());
    }
    if !visiting.insert(id.to_owned()) {
        return Err(invalid("import lineage cycle"));
    }
    let r = &batch[id];
    if let Some(parent) = &r.parent_id {
        if batch.contains_key(parent) {
            visit(parent, batch, visiting, done, ordered)?;
        }
    }
    visiting.remove(id);
    done.insert(id.to_owned());
    ordered.push(id.to_owned());
    Ok(())
}
struct ImportPlan {
    batch: BTreeMap<String, TeachingRecord>,
    ordered: Vec<String>,
    existing_ids: BTreeSet<String>,
}
fn validate_import(conn: &Connection, bundle: &ExchangeBundle) -> Result<ImportPlan> {
    if bundle.schema != EXCHANGE_SCHEMA || bundle.records.is_empty() || bundle.records.len() > 128 {
        return Err(invalid("exchange schema or record count"));
    }
    if canonical(&bundle.records)?.len() > EXCHANGE_MAX_BYTES {
        return Err(invalid("exchange serialized byte budget"));
    }
    if bundle.package_sha256 != package_hash(&bundle.records)? {
        return Err(invalid("exchange package SHA256 mismatch"));
    }
    let mut batch = BTreeMap::new();
    for r in &bundle.records {
        shape(r)?;
        if batch.insert(r.record_id.clone(), r.clone()).is_some() {
            return Err(invalid("duplicate record ID in package"));
        }
    }
    let mut ordered = Vec::new();
    let mut visiting = BTreeSet::new();
    let mut done = BTreeSet::new();
    for id in batch.keys() {
        visit(id, &batch, &mut visiting, &mut done, &mut ordered)?;
    }
    let tx = conn;
    let mut existing_ids = BTreeSet::new();
    // Validate every object/reference before the first INSERT. Transaction rollback is a second barrier.
    for r in &bundle.records {
        if let Some(existing) = get(&tx, &r.record_id)? {
            if existing.content_sha256 != hash(r)? || existing.record != *r {
                return Err(TeachingError::Conflict(
                    "import record ID content conflict".into(),
                ));
            }
            existing_ids.insert(r.record_id.clone());
            continue;
        }
        let parent = if let Some(id) = &r.parent_id {
            if let Some(stored) = get(&tx, id)? {
                if stored.withdrawn {
                    return Err(TeachingError::Withdrawn("import parent".into()));
                }
                Some(stored.record)
            } else {
                Some(
                    batch
                        .get(id)
                        .cloned()
                        .ok_or_else(|| TeachingError::NotFound("import parent".into()))?,
                )
            }
        } else {
            None
        };
        parent_shape(r, parent.as_ref())?;
        references(&tx, r, parent.as_ref())?;
        // A batch ancestor which already exists must also respect transitive withdrawal.
        let mut ancestor = r.parent_id.clone();
        let mut seen = BTreeSet::new();
        while let Some(id) = ancestor {
            if !seen.insert(id.clone()) {
                return Err(invalid("import ancestor cycle"));
            }
            if let Some(stored) = get(&tx, &id)? {
                if stored.withdrawn {
                    return Err(TeachingError::Withdrawn("import ancestor".into()));
                }
                break;
            }
            ancestor = batch
                .get(&id)
                .ok_or_else(|| TeachingError::NotFound("import ancestor".into()))?
                .parent_id
                .clone();
        }
    }
    Ok(ImportPlan {
        batch,
        ordered,
        existing_ids,
    })
}
pub fn preview_import(conn: &Connection, bundle: &ExchangeBundle) -> Result<ImportPreview> {
    let plan = validate_import(conn, bundle)?;
    Ok(ImportPreview {
        valid: true,
        record_count: bundle.records.len(),
        duplicate_count: plan.existing_ids.len(),
        package_sha256: bundle.package_sha256.clone(),
    })
}
pub fn import_bundle(conn: &mut Connection, bundle: &ExchangeBundle) -> Result<ImportReceipt> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let plan = validate_import(&tx, bundle)?;
    for id in plan.ordered {
        if !plan.existing_ids.contains(&id) {
            insert(&tx, &plan.batch[&id])?;
        }
    }
    let mut items = Vec::new();
    for r in &bundle.records {
        items.push(get(&tx, &r.record_id)?.ok_or_else(|| invalid("import readback"))?);
    }
    let duplicate_count = plan.existing_ids.len();
    tx.commit()?;
    Ok(ImportReceipt {
        items,
        duplicate_count,
        package_sha256: bundle.package_sha256.clone(),
    })
}
