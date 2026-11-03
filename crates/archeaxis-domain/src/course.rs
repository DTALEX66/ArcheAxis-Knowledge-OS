//! Candidate General courses. Core validates canonical bindings; the existing
//! Python contract worker validates complete course shape before this write.
//! No mastery authority, promotion or renderer execution is introduced here.
use rusqlite::{Connection, OptionalExtension, params};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
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

/// Separated use state of a course binding's knowledge. A stale course says which
/// knowledge changed and what replaced it instead of only a boolean; the successor
/// is named, never substituted into the historical binding.
fn knowledge_state(conn: &Connection, knowledge_id: &str) -> rusqlite::Result<Value> {
    Ok(match crate::knowledge::currentness(conn, knowledge_id)? {
        Some(view) => json!({
            "status": view.status,
            "active": view.active,
            "currentness": view.currentness,
            "superseded_by": view.superseded_by,
            "successor_count": view.successor_count,
            "valid_to": view.valid_to,
        }),
        None => json!({
            "status": "missing",
            "active": false,
            "currentness": "unavailable",
        }),
    })
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
            "source_revision":b.source_revision,"stale":is_stale,
            "knowledge_state":knowledge_state(conn, &b.knowledge_id)?}),
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

// OpenMAIC's complete-scene builder is a projection, not a lossless copy of
// its input. Keep the exact worker frame and its returned candidate together in
// an ordinary Core Document rather than extending the General-v1 contract.
// Both may contain answer keys or material: ordinary document reads and
// exports include them, so the host must require a human actor and protect IO.
const OPENMAIC_NAMESPACE: &str = "archeaxis_openmaic_scene_candidate";
const OPENMAIC_REQUEST_SCHEMA: &str = "archeaxis.openmaic-scene-build/v1";
const OPENMAIC_RESULT_SCHEMA: &str = "archeaxis.openmaic-scene-build-result/v1";
/// Legacy candidate Documents, written before this slice recorded what the donor
/// projection dropped. They stay readable, but a readback must not describe them
/// as lossless or playable because nothing was recorded to support that claim.
const OPENMAIC_DOCUMENT_SCHEMA_V1: &str = "archeaxis.openmaic-scene-document/v1";
/// Current candidate Document. It carries the Core-derived projection loss report
/// and the render contract next to the exact request frame and worker reply.
const OPENMAIC_DOCUMENT_SCHEMA_V2: &str = "archeaxis.openmaic-scene-document/v2";
const OPENMAIC_CONTRACT_SCHEMA: &str = "archeaxis.openmaic-scene-projection/v2";
const OPENMAIC_RENDER_SCHEMA: &str = "archeaxis.openmaic-scene-render/v1";
const OPENMAIC_CAPABILITY: &str = "course.openmaic.scene-build";
const OPENMAIC_MAX_FRAME: usize = 256_000;
/// Scene kinds the offline slide/quiz slice can actually build and persist.
const OPENMAIC_SCENE_TYPES: [&str; 2] = ["slide", "quiz"];
const OPENMAIC_QUESTION_TYPES: [&str; 3] = ["single", "multiple", "short_answer"];
/// Content fields `buildCompleteScene` copies into each scene kind. Anything else
/// in the request is a projection loss, and the loss is reported instead of hidden.
fn openmaic_carried(outline_type: &str) -> (&'static [&'static str], &'static [&'static str]) {
    let outline_fields: &'static [&'static str] = &["id", "type", "title", "order"];
    let content_fields: &'static [&'static str] = match outline_type {
        "slide" => &["elements", "background"],
        "quiz" => &["questions"],
        "interactive" => &["html", "widgetType", "widgetConfig"],
        "pbl" => &["projectV2"],
        _ => &[],
    };
    (outline_fields, content_fields)
}

/// Captured by Core before dispatch and checked again when admitting the result.
/// Private fields prevent an HTTP caller from constructing an admission token.
#[derive(Clone)]
pub struct OpenMaicPending {
    restore_epoch: Option<String>,
    workspace_id: String,
    input_sha256: String,
    create_request_id: String,
}

/// Repeated requests return the first saved document without running a worker.
#[derive(Clone)]
pub enum OpenMaicPreparation {
    Existing(Value),
    Pending(OpenMaicPending),
}

fn openmaic_invalid(message: &'static str) -> crate::document::Error {
    crate::document::Error::Invalid(message)
}

fn openmaic_token(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
}

fn openmaic_digest(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

/// Internal create-request identity of the candidate Document. Exposed so a
/// reader or test can locate the exact Document a client request ID owns.
pub fn openmaic_internal_request_id(create_request_id: &str) -> String {
    format!(
        "openmaic_scene_{}",
        openmaic_digest(create_request_id.as_bytes())
    )
}

/// Deterministic candidate Document ID for a client create request ID.
pub fn openmaic_scene_document_id(create_request_id: &str) -> String {
    let internal_id = openmaic_internal_request_id(create_request_id);
    format!("doc_req_{}", openmaic_digest(internal_id.as_bytes()))
}

/// Recognise the contract version and scene kind a request declares, and name what
/// this offline slice cannot build. `None` means "no explicit version or kind
/// refusal"; the remaining shape checks still run in [`openmaic_frame`]. A caller
/// answers [`Some`] with a 422 instead of folding an unsupported version into a
/// generic parse failure, which is what made the earlier refusal indistinct.
pub fn openmaic_refusal(request: &Value) -> Option<Value> {
    if let Some(schema) = request.get("schema").and_then(Value::as_str)
        && schema != OPENMAIC_REQUEST_SCHEMA
    {
        return Some(json!({"reason":"UNSUPPORTED_REQUEST_VERSION",
            "declared":schema,"supported":[OPENMAIC_REQUEST_SCHEMA]}));
    }
    let outline = request.get("outline")?;
    let kind = outline.get("type").and_then(Value::as_str)?;
    if !OPENMAIC_SCENE_TYPES.contains(&kind) {
        return Some(json!({"reason":"UNSUPPORTED_SCENE","scene_type":kind,
            "supported_scene_types":OPENMAIC_SCENE_TYPES}));
    }
    let content = request.get("content")?.as_object()?;
    if let Some(declared) = content.get("schemaVersion")
        && declared.as_i64() != Some(1)
    {
        return Some(
            json!({"reason":"UNSUPPORTED_SCENE_VERSION","scene_type":kind,
            "declared":declared,"supported_scene_versions":[1]}),
        );
    }
    None
}

/// What the donor projection does not carry, derived by Core from the request it
/// actually sent. The renderer/consumer reads this instead of assuming the stored
/// candidate is a lossless copy: `lossless` is only true for an empty `omitted`.
pub fn openmaic_projection(request: &Value) -> Value {
    let kind = request["outline"]["type"].as_str().unwrap_or("");
    let (outline_carried, content_carried) = openmaic_carried(kind);
    let mut omitted: Vec<String> = Vec::new();
    if let Some(outline) = request["outline"].as_object() {
        for key in outline.keys() {
            if !outline_carried.contains(&key.as_str()) {
                omitted.push(format!("outline.{key}"));
            }
        }
    }
    if let Some(content) = request["content"].as_object() {
        for key in content.keys() {
            if !content_carried.contains(&key.as_str()) {
                omitted.push(format!("content.{key}"));
            }
        }
    }
    omitted.sort();
    json!({"contract":OPENMAIC_CONTRACT_SCHEMA,"lossless":omitted.is_empty(),
        "scene_type":kind,"omitted":omitted,
        "basis":"Core compared the stored request with the persisted scene projection; \
         every request field the projection does not carry is listed, never silently dropped"})
}

fn openmaic_bounded_text(value: &Value, max: usize) -> bool {
    value
        .as_str()
        .is_some_and(|text| !text.trim().is_empty() && text.len() <= max)
}

fn openmaic_number(value: &Value, min: f64, max: f64) -> bool {
    value
        .as_f64()
        .is_some_and(|number| number.is_finite() && (min..=max).contains(&number))
}

/// A slide element the text renderer can actually draw. Anything else is listed
/// as unsupported so a consumer can refuse the scene instead of drawing a blank.
fn openmaic_text_element_defect(element: &Value) -> Option<&'static str> {
    if !element.is_object() {
        return Some("element is not an object");
    }
    if element["type"].as_str() != Some("text") {
        return Some("only text elements are rendered");
    }
    if !openmaic_bounded_text(&element["id"], 128) {
        return Some("element needs a bounded ID");
    }
    let content = element["content"].as_str().unwrap_or("");
    if !openmaic_bounded_text(&element["content"], 16_000) {
        return Some("element needs bounded text content");
    }
    let active = [
        "img", "video", "audio", "iframe", "object", "embed", "svg", "canvas",
    ];
    for tag in active {
        if content.contains(&format!("<{tag}")) {
            return Some("active content is not executed");
        }
    }
    if !openmaic_number(&element["left"], -10_000.0, 10_000.0)
        || !openmaic_number(&element["top"], -10_000.0, 10_000.0)
        || !openmaic_number(&element["width"], 0.01, 10_000.0)
        || !openmaic_number(&element["height"], 0.01, 10_000.0)
        || !openmaic_number(&element["rotate"], -3_600.0, 3_600.0)
    {
        return Some("element needs bounded canvas geometry");
    }
    None
}

fn openmaic_question_defect(question: &Value) -> Option<&'static str> {
    if !question.is_object() {
        return Some("question is not an object");
    }
    if !openmaic_bounded_text(&question["id"], 128) {
        return Some("question needs a bounded ID");
    }
    match question["type"].as_str() {
        Some(kind) if OPENMAIC_QUESTION_TYPES.contains(&kind) => {}
        _ => return Some("only single/multiple/short_answer questions are scored"),
    }
    if !openmaic_bounded_text(&question["question"], 16_000) {
        return Some("question needs bounded text");
    }
    if let Some(options) = question.get("options") {
        let Some(items) = options.as_array() else {
            return Some("options must be a list");
        };
        if items.len() > 32
            || items.iter().any(|option| {
                !option.is_object()
                    || !openmaic_bounded_text(&option["label"], 4_000)
                    || !openmaic_bounded_text(&option["value"], 512)
            })
        {
            return Some("options need bounded label/value pairs");
        }
    }
    if let Some(answer) = question.get("answer") {
        let Some(items) = answer.as_array() else {
            return Some("answer must be a list of option values");
        };
        if items.len() > 32
            || items
                .iter()
                .any(|item| !openmaic_bounded_text(item, 16_000))
        {
            return Some("answer references must be bounded text");
        }
    }
    None
}

/// The inert render contract for a persisted scene. `playable` describes whether
/// the stored content can be drawn or answered as-is; it never authorizes rendering
/// or claims mastery, and an unsupported item is listed rather than skipped.
pub fn openmaic_render_contract(scene: &Value) -> Value {
    let scene_type = scene["type"].as_str().unwrap_or("");
    let mut unsupported: Vec<Value> = Vec::new();
    let mut elements = 0usize;
    let mut questions = 0usize;
    let renderer = match scene_type {
        "slide" => {
            let canvas = &scene["content"]["canvas"];
            if !canvas.is_object() {
                unsupported.push(json!({"path":"content.canvas","reason":"canvas is missing"}));
            }
            let list = canvas["elements"]
                .as_array()
                .map(Vec::as_slice)
                .unwrap_or_default();
            elements = list.len();
            for (index, element) in list.iter().enumerate() {
                if let Some(reason) = openmaic_text_element_defect(element) {
                    unsupported.push(
                        json!({"path":format!("content.canvas.elements[{index}]"),"reason":reason}),
                    );
                }
            }
            if canvas["animations"]
                .as_array()
                .is_some_and(|items| !items.is_empty())
            {
                unsupported.push(
                    json!({"path":"content.canvas.animations","reason":"animation is not played"}),
                );
            }
            "openmaic-canvas-text"
        }
        "quiz" => {
            let list = scene["content"]["questions"]
                .as_array()
                .map(Vec::as_slice)
                .unwrap_or_default();
            questions = list.len();
            let mut seen = HashSet::new();
            for (index, question) in list.iter().enumerate() {
                if let Some(reason) = openmaic_question_defect(question) {
                    unsupported.push(
                        json!({"path":format!("content.questions[{index}]"),"reason":reason}),
                    );
                    continue;
                }
                let id = question["id"].as_str().unwrap_or("");
                if !seen.insert(id.to_owned()) {
                    unsupported.push(
                        json!({"path":format!("content.questions[{index}]"),"reason":"duplicate question ID"}),
                    );
                }
            }
            "openmaic-quiz-objective"
        }
        _ => {
            unsupported.push(json!({"path":"type","reason":"scene type is not playable here"}));
            ""
        }
    };
    json!({"schema":OPENMAIC_RENDER_SCHEMA,
        "playable": OPENMAIC_SCENE_TYPES.contains(&scene_type) && unsupported.is_empty(),
        "renderer":if renderer.is_empty() { Value::Null } else { Value::String(renderer.into()) },
        "scene_type":scene_type,
        "supported_scene_types":OPENMAIC_SCENE_TYPES,
        "counts":{"elements":elements,"questions":questions,"unsupported":unsupported.len()},
        "unsupported":unsupported,
        "basis":"Derived by Core from the persisted inert scene; playable means the stored \
         content has the shape a renderer needs, not that rendering is authorized or scored"})
}

/// Match the executor's serialization and frame limit before starting Node.
fn openmaic_frame(
    create_request_id: &str,
    request: &Value,
) -> Result<(String, String, crate::provider_material_grant::Snapshot), crate::document::Error> {
    use crate::provider_material_grant::{Snapshot, valid_snapshot_shape};
    if !openmaic_token(create_request_id) {
        return Err(openmaic_invalid("invalid OpenMAIC create request ID"));
    }
    let object = request
        .as_object()
        .ok_or(openmaic_invalid("invalid OpenMAIC request"))?;
    let keys = [
        "schema",
        "request_id",
        "attempt",
        "source",
        "stage_id",
        "scene_id",
        "outline",
        "content",
        "actions",
    ];
    if object.len() != keys.len()
        || keys.iter().any(|key| !object.contains_key(*key))
        || request["schema"] != OPENMAIC_REQUEST_SCHEMA
        || ["request_id", "stage_id", "scene_id"].iter().any(|key| {
            request[*key]
                .as_str()
                .is_none_or(|value| !openmaic_token(value))
        })
        || !request["attempt"]
            .as_i64()
            .is_some_and(|value| (1..=9_007_199_254_740_991).contains(&value))
    {
        return Err(openmaic_invalid("invalid OpenMAIC request identity"));
    }
    let material: Snapshot = serde_json::from_value(request["source"].clone())
        .map_err(|_| openmaic_invalid("invalid OpenMAIC material snapshot"))?;
    if !valid_snapshot_shape(&material) {
        return Err(openmaic_invalid("invalid OpenMAIC material snapshot"));
    }
    let outline = &request["outline"];
    let title = outline["title"]
        .as_str()
        .filter(|value| !value.trim().is_empty() && value.len() <= 960 && !value.contains('\0'));
    if !outline.is_object()
        || outline["id"]
            .as_str()
            .is_none_or(|value| !openmaic_token(value))
        || title.is_none()
        || !outline["description"].is_string()
        || !outline["keyPoints"].is_array()
        || !outline["order"]
            .as_i64()
            .is_some_and(|value| (0..=1_000_000).contains(&value))
        || !request["content"].is_object()
        || !request["actions"]
            .as_array()
            .is_some_and(|items| items.len() <= 100)
    {
        return Err(openmaic_invalid("invalid OpenMAIC outline or content"));
    }
    // Only the offline slide/quiz slice is stored. The request is retained in
    // full, including fields the upstream scene projection does not carry.
    let valid_content = match outline["type"].as_str() {
        Some("slide") => request["content"]["elements"]
            .as_array()
            .is_some_and(|items| items.len() <= 200),
        Some("quiz") => request["content"]["questions"]
            .as_array()
            .is_some_and(|items| !items.is_empty() && items.len() <= 200),
        _ => false,
    };
    if !valid_content {
        return Err(openmaic_invalid("unsupported OpenMAIC scene"));
    }
    // Defence in depth: [`openmaic_refusal`] names these for the caller, and the
    // write path still refuses them even when a caller skips that pre-check.
    if request["content"]
        .get("schemaVersion")
        .is_some_and(|declared| declared.as_i64() != Some(1))
    {
        return Err(openmaic_invalid(
            "unsupported OpenMAIC scene content version",
        ));
    }
    let mut bytes =
        serde_json::to_vec(request).map_err(|_| openmaic_invalid("invalid OpenMAIC JSON"))?;
    bytes.push(b'\n');
    if bytes.len() > OPENMAIC_MAX_FRAME {
        return Err(openmaic_invalid("OpenMAIC frame exceeds bound"));
    }
    let sha = openmaic_digest(&bytes);
    let frame = String::from_utf8(bytes).map_err(|_| openmaic_invalid("invalid OpenMAIC frame"))?;
    Ok((frame, sha, material))
}

fn openmaic_material_current(
    conn: &Connection,
    material: &crate::provider_material_grant::Snapshot,
) -> Result<(), crate::document::Error> {
    let current = crate::document::read_verified(conn, &material.document_id, None)?;
    if current["version"].as_i64() != Some(material.version)
        || current["content_sha256"] != material.content_sha256
    {
        return Err(openmaic_invalid(
            "OpenMAIC material snapshot is no longer current",
        ));
    }
    Ok(())
}

fn openmaic_check_result(
    request: &Value,
    input_sha256: &str,
    worker: &Value,
) -> Result<(), crate::document::Error> {
    let scene = &worker["scene"];
    if worker["schema"] != OPENMAIC_RESULT_SCHEMA
        || worker["status"] != "CANDIDATE"
        || worker["request_id"] != request["request_id"]
        || worker["attempt"] != request["attempt"]
        || worker["input_sha256"] != input_sha256
        || worker["source"] != request["source"]
        || worker["source_binding"] != "client_declared_unverified"
        || worker["provider"] != "openmaic"
        || worker["provider_version"] != "1.3.0"
        || worker["generation_version"] != "0.3.28"
        || worker["authority_effect"] != "candidate_only"
        || worker["model_call"] != "NOT_INVOKED"
        || worker["canonical_bindings_verified"] != false
        || worker["human_review_required"] != true
        || worker["active_content_executed"] != false
        || worker["rendering_authorized"] != false
        || worker["retry_bytes_stable"] != false
        || scene["id"] != request["scene_id"]
        || scene["stageId"] != request["stage_id"]
        || scene["outlineId"] != request["outline"]["id"]
        || scene["type"] != request["outline"]["type"]
        || scene["title"] != request["outline"]["title"]
        || scene["order"] != request["outline"]["order"]
        || scene["actions"] != request["actions"]
        || scene["content"]["type"] != scene["type"]
    {
        return Err(openmaic_invalid(
            "OpenMAIC worker receipt does not match input",
        ));
    }
    let content_matches = match scene["type"].as_str() {
        Some("slide") => {
            scene["content"]["canvas"]["elements"] == request["content"]["elements"]
                && scene["content"]["canvas"]["background"] == request["content"]["background"]
        }
        Some("quiz") => scene["content"]["questions"] == request["content"]["questions"],
        _ => false,
    };
    if !content_matches {
        return Err(openmaic_invalid(
            "OpenMAIC scene content does not match input",
        ));
    }
    Ok(())
}

fn openmaic_material_status(
    conn: &Connection,
    material: &crate::provider_material_grant::Snapshot,
) -> &'static str {
    let selected =
        match crate::document::read_verified(conn, &material.document_id, Some(material.version)) {
            Ok(value) if value["content_sha256"] == material.content_sha256 => value,
            _ => return "unavailable",
        };
    match crate::document::read_verified(conn, &material.document_id, None) {
        Ok(current)
            if current["version"] == selected["version"]
                && current["content_sha256"] == selected["content_sha256"] =>
        {
            "current"
        }
        Ok(current)
            if current["version"]
                .as_i64()
                .is_some_and(|version| version > material.version) =>
        {
            "historical"
        }
        _ => "unavailable",
    }
}

fn openmaic_receipt(
    conn: &Connection,
    document: Value,
    material: &crate::provider_material_grant::Snapshot,
) -> Value {
    let candidate_status = match document["document_id"].as_str() {
        Some(id) => match crate::document::read_verified(conn, id, None) {
            Ok(current)
                if current["version"] == document["version"]
                    && current["content_sha256"] == document["content_sha256"] =>
            {
                "current"
            }
            Ok(current)
                if current["version"]
                    .as_i64()
                    .is_some_and(|version| version > 1) =>
            {
                "historical"
            }
            _ => "unavailable",
        },
        None => "unavailable",
    };
    // Version dispatch for readers: a v1 candidate reports that no projection or
    // render report was ever recorded, so a consumer cannot read silence as
    // "lossless". A v2 candidate reports exactly what Core derived and stored.
    let stored = &document["editor_json"]["attrs"][OPENMAIC_NAMESPACE];
    let (contract_version, projection, render) =
        if stored["schema"].as_str() == Some(OPENMAIC_DOCUMENT_SCHEMA_V2) {
            (
                OPENMAIC_DOCUMENT_SCHEMA_V2,
                json!({"status":"RECORDED","derived_by":"core",
                "report":stored["contract"]}),
                json!({"status":"RECORDED","derived_by":"core","report":stored["render"]}),
            )
        } else {
            (
                OPENMAIC_DOCUMENT_SCHEMA_V1,
                json!({"status":"NOT_RECORDED",
                "reason":"legacy v1 candidate predates the projection report; \
                 the readback must not be read as lossless"}),
                json!({"status":"NOT_RECORDED",
                "reason":"legacy v1 candidate predates the render contract; \
                 playability is not established"}),
            )
        };
    json!({"document":document,"candidate_document_status":candidate_status,
        "source_snapshot_status":openmaic_material_status(conn, material),
        "source_derivation":"client_declared_unverified",
        "contract_version":contract_version,"projection":projection,"render":render})
}

fn openmaic_existing(
    conn: &Connection,
    create_request_id: &str,
    request: &Value,
    frame: &str,
    input_sha256: &str,
    material: &crate::provider_material_grant::Snapshot,
) -> Result<Option<Value>, crate::document::Error> {
    let id = openmaic_scene_document_id(create_request_id);
    let exists: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM documents WHERE document_id=?1)",
        [&id],
        |row| row.get(0),
    )?;
    if !exists {
        return Ok(None);
    }
    let document = crate::document::read_verified(conn, &id, Some(1))?;
    let saved = &document["editor_json"]["attrs"][OPENMAIC_NAMESPACE];
    let stored_schema = saved["schema"].as_str();
    // Version dispatch: a legacy v1 candidate is read, never upgraded in place;
    // a v2 candidate additionally has to still match the report Core derived.
    if !(stored_schema == Some(OPENMAIC_DOCUMENT_SCHEMA_V1)
        || stored_schema == Some(OPENMAIC_DOCUMENT_SCHEMA_V2))
        || saved["create_request_id"] != create_request_id
        || saved["request_frame"] != frame
        || saved["input_sha256"] != input_sha256
    {
        return Err(openmaic_invalid(
            "OpenMAIC create request ID conflicts with another document",
        ));
    }
    openmaic_check_result(request, input_sha256, &saved["worker_document"])?;
    if stored_schema == Some(OPENMAIC_DOCUMENT_SCHEMA_V2)
        && (saved["contract"] != openmaic_projection(request)
            || saved["render"] != openmaic_render_contract(&saved["worker_document"]["scene"]))
    {
        return Err(openmaic_invalid(
            "OpenMAIC stored projection or render report changed",
        ));
    }
    // The reader consumes the current version, so a later edit that rewrites the
    // recorded contract or render verdict has to be refused there as well; otherwise
    // an edited document could claim lossless or playable while Core derived otherwise.
    // A current version that fails its own integrity recheck is left to the receipt,
    // which reports it as unavailable rather than as a valid scene.
    if let Ok(current) = crate::document::read_verified(conn, &id, None) {
        let current_saved = &current["editor_json"]["attrs"][OPENMAIC_NAMESPACE];
        if current_saved["schema"].as_str() == Some(OPENMAIC_DOCUMENT_SCHEMA_V2)
            && current_saved["create_request_id"] == saved["create_request_id"]
            && (current_saved["contract"] != openmaic_projection(request)
                || current_saved["render"]
                    != openmaic_render_contract(&current_saved["worker_document"]["scene"]))
        {
            return Err(openmaic_invalid(
                "OpenMAIC stored projection or render report changed",
            ));
        }
    }
    Ok(Some(openmaic_receipt(conn, document, material)))
}

/// Check a retry and capture the material, workspace and restore epoch in one
/// Core transaction before launching the worker. On a fresh workspace this may
/// initialize the existing Core-owned workspace identity. The caller must
/// independently enforce human access, process lifecycle, cancellation, and
/// capability admission.
pub fn prepare_openmaic_scene(
    conn: &mut Connection,
    create_request_id: &str,
    request: &Value,
) -> Result<OpenMaicPreparation, crate::document::Error> {
    let (frame, input_sha256, material) = openmaic_frame(create_request_id, request)?;
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    if let Some(receipt) = openmaic_existing(
        &tx,
        create_request_id,
        request,
        &frame,
        &input_sha256,
        &material,
    )? {
        tx.commit()?;
        return Ok(OpenMaicPreparation::Existing(receipt));
    }
    openmaic_material_current(&tx, &material)?;
    let restore_epoch = archeaxis_store_sqlite::authorization_fence::authorization_epoch(&tx)?;
    // Existing Core UI-state identity is also the workspace identity used by
    // other long-lived operations. Initialize it once for a fresh workspace.
    let workspace_id = crate::ui_state::workspace_id(&tx)
        .map_err(|_| openmaic_invalid("OpenMAIC workspace identity unavailable"))?;
    tx.commit()?;
    Ok(OpenMaicPreparation::Pending(OpenMaicPending {
        restore_epoch,
        workspace_id,
        input_sha256,
        create_request_id: create_request_id.to_owned(),
    }))
}

/// Persist one inert scene candidate through the existing Document writer.
/// Worker stdout and the stored Document contain the complete request and can
/// include answers; this API is not an answer-secrecy or execution boundary.
pub fn commit_openmaic_scene(
    conn: &mut Connection,
    create_request_id: &str,
    request: &Value,
    pending: &OpenMaicPending,
    worker_document: &Value,
) -> Result<Value, crate::document::Error> {
    let (frame, input_sha256, material) = openmaic_frame(create_request_id, request)?;
    if input_sha256 != pending.input_sha256
        || create_request_id != pending.create_request_id.as_str()
    {
        return Err(openmaic_invalid("OpenMAIC request changed after admission"));
    }
    openmaic_check_result(request, &input_sha256, worker_document)?;
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let epoch = archeaxis_store_sqlite::authorization_fence::authorization_epoch(&tx)?;
    let workspace_id = crate::ui_state::existing_workspace_id(&tx)
        .map_err(|_| openmaic_invalid("OpenMAIC workspace identity unavailable"))?;
    if epoch != pending.restore_epoch
        || workspace_id.as_deref() != Some(pending.workspace_id.as_str())
    {
        return Err(openmaic_invalid(
            "OpenMAIC workspace or restore epoch changed",
        ));
    }
    openmaic_material_current(&tx, &material)?;
    if !archeaxis_store_sqlite::capability_settings::is_enabled(&tx, OPENMAIC_CAPABILITY)? {
        return Err(openmaic_invalid("OpenMAIC capability is disabled"));
    }
    // Two requests may have passed preparation concurrently. Never replace the
    // first scene with a later canvas ID or timestamps from a second run.
    if let Some(existing) = openmaic_existing(
        &tx,
        create_request_id,
        request,
        &frame,
        &input_sha256,
        &material,
    )? {
        tx.commit()?;
        return Ok(existing);
    }
    let outline_title = request["outline"]["title"]
        .as_str()
        .ok_or(openmaic_invalid("OpenMAIC title missing"))?;
    let title = format!("OpenMAIC candidate · {outline_title}");
    // Core derives both reports from what it actually sent and received; a caller
    // or worker cannot declare a lossless or playable candidate by itself.
    let projection = openmaic_projection(request);
    let render = openmaic_render_contract(&worker_document["scene"]);
    let saved = json!({
        "schema": OPENMAIC_DOCUMENT_SCHEMA_V2,
        "create_request_id": create_request_id,
        "input_sha256": input_sha256,
        "request_frame": frame,
        "worker_document": worker_document,
        "contract": projection,
        "render": render,
        "source_snapshot_status_at_commit": "current",
        "source_derivation": "client_declared_unverified",
        "rendering_authorized": false,
        "human_review_required": true,
    });
    let editor = json!({"type":"doc","attrs":{"archeaxis_openmaic_scene_candidate":saved},
        "content":[{"type":"paragraph","attrs":{"block_id":"openmaic_scene_candidate"},
            "content":[{"type":"text","text":title.clone()}]}]});
    let internal_id = openmaic_internal_request_id(create_request_id);
    let document =
        crate::document::create_optional_tx(&tx, None, None, &title, editor, Some(&internal_id))?;
    let document_id = document["document_id"]
        .as_str()
        .ok_or(openmaic_invalid("OpenMAIC document ID missing"))?;
    let verified = crate::document::read_verified(&tx, document_id, Some(1))?;
    let receipt = openmaic_receipt(&tx, verified, &material);
    tx.commit()?;
    Ok(receipt)
}
