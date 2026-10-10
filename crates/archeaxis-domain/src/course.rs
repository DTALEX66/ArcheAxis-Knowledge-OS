//! Candidate General courses. Core validates canonical bindings; the existing
//! Python contract worker validates complete course shape before this write.
//! No mastery authority, promotion or renderer execution is introduced here.
use rusqlite::{Connection, OptionalExtension, params};
use serde_json::{Value, json};
use std::collections::{BTreeSet, HashSet};

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct CourseBinding {
    pub component_id: String,
    pub knowledge_id: String,
    /// Existing canonical revision identity, matching Assessment: knowledge_id.
    pub knowledge_version: String,
    pub source_id: String,
    pub source_revision: String,
}

fn invalid(message: &str) -> rusqlite::Error {
    rusqlite::Error::InvalidParameterName(message.into())
}
fn text<'a>(value: &'a Value, key: &str) -> rusqlite::Result<&'a str> {
    value
        .get(key)
        .and_then(Value::as_str)
        .filter(|s| !s.trim().is_empty() && s.len() <= 16384)
        .ok_or_else(|| invalid("course requires bounded nonblank text"))
}
fn list<'a>(value: &'a Value, key: &str) -> rusqlite::Result<&'a Vec<Value>> {
    value
        .get(key)
        .and_then(Value::as_array)
        .filter(|v| !v.is_empty() && v.len() <= 64)
        .ok_or_else(|| invalid("course requires bounded nonempty lists"))
}
fn ids(value: &Value, key: &str) -> rusqlite::Result<BTreeSet<String>> {
    let values = list(value, key)?;
    let mut result = BTreeSet::new();
    for item in values {
        let id = item
            .as_str()
            .filter(|s| !s.trim().is_empty() && s.len() <= 256)
            .ok_or_else(|| invalid("invalid course reference"))?;
        if !result.insert(id.to_owned()) {
            return Err(invalid("duplicate course reference"));
        }
    }
    Ok(result)
}

fn validate(manifest: &Value, bindings: &[CourseBinding]) -> rusqlite::Result<()> {
    let object = manifest
        .as_object()
        .ok_or_else(|| invalid("manifest must be an object"))?;
    let allowed = [
        "schema",
        "manifest_id",
        "title",
        "domain_pack_id",
        "status",
        "knowledge_components",
        "learning_objectives",
        "artifacts",
    ];
    if object.keys().any(|k| !allowed.contains(&k.as_str())) {
        return Err(invalid("unknown course fields"));
    }
    if manifest.get("schema").and_then(Value::as_str) != Some("archeaxis.course-manifest/v1")
        || text(manifest, "domain_pack_id")? != "general"
        || text(manifest, "status")? != "candidate"
    {
        return Err(invalid("only General candidate manifests are supported"));
    }
    text(manifest, "manifest_id")?;
    text(manifest, "title")?;
    if manifest.to_string().len() > 256000 || bindings.is_empty() || bindings.len() > 128 {
        return Err(invalid("course payload exceeds bounds"));
    }
    let components = list(manifest, "knowledge_components")?;
    let mut component_ids = BTreeSet::new();
    for c in components {
        let id = text(c, "component_id")?;
        if !component_ids.insert(id.to_owned()) {
            return Err(invalid("duplicate component"));
        }
        text(c, "title")?;
        text(c, "statement")?;
        if !["concept", "fact", "procedure", "method", "case"].contains(&text(c, "kind")?) {
            return Err(invalid("unknown component kind"));
        }
    }
    let mut binding_keys = HashSet::new();
    for b in bindings {
        if [
            &b.component_id,
            &b.knowledge_id,
            &b.knowledge_version,
            &b.source_id,
            &b.source_revision,
        ]
        .iter()
        .any(|s| s.trim().is_empty() || s.len() > 256)
            || !component_ids.contains(&b.component_id)
            || !binding_keys.insert((&b.component_id, &b.source_id))
        {
            return Err(invalid("invalid or duplicate canonical course binding"));
        }
    }
    for c in components {
        let id = text(c, "component_id")?;
        let bound_sources: BTreeSet<String> = bindings
            .iter()
            .filter(|b| b.component_id == id)
            .map(|b| b.source_id.clone())
            .collect();
        if bound_sources.is_empty() || !ids(c, "source_ids")?.is_subset(&bound_sources) {
            return Err(invalid(
                "component sources must belong to canonical bindings",
            ));
        }
        if let Some(prerequisites) = c.get("prerequisite_ids") {
            let values = prerequisites
                .as_array()
                .ok_or_else(|| invalid("invalid prerequisites"))?;
            for p in values {
                let p = p.as_str().ok_or_else(|| invalid("invalid prerequisite"))?;
                if p == id || !component_ids.contains(p) {
                    return Err(invalid("unclosed prerequisite"));
                }
            }
        }
    }
    let mut objective_ids = HashSet::new();
    let mut covered = BTreeSet::new();
    for objective in list(manifest, "learning_objectives")? {
        if !objective_ids.insert(text(objective, "objective_id")?) {
            return Err(invalid("duplicate objective"));
        }
        text(objective, "title")?;
        text(objective, "statement")?;
        let refs = ids(objective, "knowledge_component_ids")?;
        if !refs.is_subset(&component_ids) {
            return Err(invalid("unclosed objective"));
        }
        covered.extend(refs);
    }
    let mut artifacts = HashSet::new();
    let mut has_lesson = false;
    for artifact in list(manifest, "artifacts")? {
        if !artifacts.insert(text(artifact, "artifact_id")?) {
            return Err(invalid("duplicate artifact"));
        }
        for field in ["title", "renderer", "renderer_version"] {
            text(artifact, field)?;
        }
        if text(artifact, "domain_pack_id")? != "general"
            || text(artifact, "status")? != "candidate"
            || artifact.get("derived_only") != Some(&Value::Bool(true))
            || artifact.get("human_review_required") != Some(&Value::Bool(true))
        {
            return Err(invalid(
                "artifact must be a human-review-required derived candidate",
            ));
        }
        has_lesson |= text(artifact, "artifact_type")? == "lesson";
        let refs = ids(artifact, "knowledge_ids")?;
        let sources: BTreeSet<String> = bindings
            .iter()
            .filter(|b| refs.contains(&b.component_id))
            .map(|b| b.source_id.clone())
            .collect();
        if !refs.is_subset(&component_ids)
            || !refs.is_subset(&covered)
            || !ids(artifact, "source_ids")?.is_subset(&sources)
        {
            return Err(invalid(
                "artifact references must close over bound sources and objectives",
            ));
        }
    }
    if !has_lesson {
        return Err(invalid("General course requires a lesson"));
    }
    Ok(())
}

fn binding_current(conn: &Connection, b: &CourseBinding) -> rusqlite::Result<bool> {
    if b.knowledge_version != b.knowledge_id
        || !crate::knowledge::is_knowledge_active(conn, &b.knowledge_id)?
    {
        return Ok(false);
    }
    conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM knowledge k JOIN anchors a ON a.anchor_id=k.anchor_id
         JOIN sources s ON s.source_id=a.source_id WHERE k.knowledge_id=?1
         AND (k.status='accepted' OR k.knowledge_type IN ('PERSONAL_DEFINITION','PERSONAL_EXPERIENCE'))
         AND a.source_id=?2 AND a.source_revision=?3 AND s.sha256=?3)",
        params![b.knowledge_id,b.source_id,b.source_revision], |r| r.get(0))
}
fn stored_bindings(conn: &Connection, id: &str) -> rusqlite::Result<Vec<CourseBinding>> {
    conn.prepare("SELECT component_id,knowledge_id,knowledge_version,source_id,source_revision
                  FROM general_course_bindings WHERE manifest_id=?1 ORDER BY component_id,source_id")?
        .query_map([id], |r| Ok(CourseBinding { component_id:r.get(0)?,knowledge_id:r.get(1)?,
            knowledge_version:r.get(2)?,source_id:r.get(3)?,source_revision:r.get(4)? }))?
        .collect()
}

/// Read historical candidate and immutable bindings; stale is computed, not persisted.
pub fn read_candidate(conn: &Connection, id: &str) -> rusqlite::Result<Option<Value>> {
    let raw: Option<String> = conn
        .query_row(
            "SELECT manifest_json FROM general_courses WHERE manifest_id=?1",
            [id],
            |r| r.get(0),
        )
        .optional()?;
    let Some(raw) = raw else {
        return Ok(None);
    };
    let manifest: Value =
        serde_json::from_str(&raw).map_err(|_| invalid("invalid stored manifest"))?;
    let mut bindings = Vec::new();
    let mut stale = false;
    for b in stored_bindings(conn, id)? {
        let is_stale = !binding_current(conn, &b)?;
        stale |= is_stale;
        bindings.push(
            json!({"component_id":b.component_id,"knowledge_id":b.knowledge_id,
            "knowledge_version":b.knowledge_version,"source_id":b.source_id,
            "source_revision":b.source_revision,"stale":is_stale}),
        );
    }
    Ok(Some(
        json!({"manifest":manifest,"bindings":bindings,"stale":stale,
        "status":"candidate","human_review_required":true}),
    ))
}

/// Canonical writer entry after the Python worker has validated full contract shape.
/// No caller-supplied verified flag is accepted. Unanchored personal knowledge is
/// explicitly unsupported here because it has no canonical source binding.
pub fn create_candidate(
    conn: &mut Connection,
    manifest: &Value,
    bindings: &[CourseBinding],
) -> rusqlite::Result<Value> {
    validate(manifest, bindings)?;
    let id = text(manifest, "manifest_id")?;
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let previous: Option<String> = tx
        .query_row(
            "SELECT manifest_json FROM general_courses WHERE manifest_id=?1",
            [id],
            |r| r.get(0),
        )
        .optional()?;
    if let Some(previous) = previous {
        let prior: Value =
            serde_json::from_str(&previous).map_err(|_| invalid("invalid stored manifest"))?;
        let mut incoming = bindings.to_vec();
        incoming.sort();
        let mut stored = stored_bindings(&tx, id)?;
        stored.sort();
        if prior != *manifest || stored != incoming {
            return Err(invalid("course ID payload conflict"));
        }
    } else {
        for b in bindings {
            if !binding_current(&tx, b)? {
                return Err(invalid(
                    "course requires current anchored accepted/personal revision",
                ));
            }
        }
        tx.execute("INSERT INTO general_courses(manifest_id,title,manifest_json,status,human_review_required)
                    VALUES(?1,?2,?3,'candidate',1)", params![id,text(manifest,"title")?,manifest.to_string()])?;
        for artifact in list(manifest, "artifacts")? {
            tx.execute("INSERT INTO general_course_artifacts(artifact_id,manifest_id,artifact_json,status,derived_only,human_review_required)
                        VALUES(?1,?2,?3,'candidate',1,1)",params![text(artifact,"artifact_id")?,id,artifact.to_string()])?;
        }
        for b in bindings {
            tx.execute("INSERT INTO general_course_bindings(manifest_id,component_id,knowledge_id,knowledge_version,source_id,source_revision)
                        VALUES(?1,?2,?3,?4,?5,?6)",params![id,b.component_id,b.knowledge_id,b.knowledge_version,b.source_id,b.source_revision])?;
        }
    }
    let readback = read_candidate(&tx, id)?.ok_or_else(|| invalid("course readback missing"))?;
    tx.commit()?;
    Ok(readback)
}

/// Bounded read-only projection, including stale courses for historical reading.
pub fn list_candidates(conn: &Connection, cursor: Option<&str>) -> rusqlite::Result<Value> {
    let ids: Vec<String> = conn.prepare(
        "SELECT manifest_id FROM general_courses WHERE (?1 IS NULL OR manifest_id > ?1) ORDER BY manifest_id LIMIT 21"
    )?.query_map([cursor], |row| row.get(0))?.collect::<rusqlite::Result<_>>()?;
    let more = ids.len() > 20;
    let mut items = Vec::new();
    for id in ids.iter().take(20) {
        let course =
            read_candidate(conn, id)?.ok_or_else(|| invalid("listed course disappeared"))?;
        items.push(json!({"manifest_id":id,"title":course["manifest"]["title"],
            "stale":course["stale"],"status":course["status"],"human_review_required":true}));
    }
    let next_cursor = if more { ids.get(19).cloned() } else { None };
    Ok(json!({"items":items,"next_cursor":next_cursor}))
}
