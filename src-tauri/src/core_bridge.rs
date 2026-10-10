//! Finite UI commands. Launch credentials and transport addresses stay in the host.
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::io::Read;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Request {
    pub operation: Operation,
    #[serde(default = "empty_payload", deserialize_with = "object_payload")]
    pub payload: Value,
}

fn empty_payload() -> Value {
    serde_json::json!({})
}

fn object_payload<'de, D>(deserializer: D) -> Result<Value, D::Error>
where
    D: serde::Deserializer<'de>,
{
    let value = Value::deserialize(deserializer)?;
    if value.is_object() {
        Ok(value)
    } else {
        Err(serde::de::Error::custom(
            "CORE_COMMAND_PAYLOAD_OBJECT_REQUIRED",
        ))
    }
}

#[derive(Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Operation {
    SystemVersion,
    SourceImport,
    SourcesList,
    SourceJobs,
    SourceMembers,
    SourcePages,
    SourceOriginal,
    DocumentsList,
    DocumentCreate,
    DocumentGet,
    DocumentGraph,
    CollectionQuery,
    DocumentDraft,
    DocumentVersion,
    DocumentRestore,
    DocumentChecks,
    DocumentCheckRecord,
    DocumentCheckExecute,
    JobsGet,
    JobQuality,
    AnchorsList,
    AnchorCreate,
    AnchorResolve,
    DocumentExport,
    DocumentExportSave,
    Search,
    KnowledgeGet,
    KnowledgeQualification,
    KnowledgeReview,
    CourseFromKnowledge,
    CourseGet,
    CourseList,
    TeachingList,
    TeachingGet,
    TeachingCreate,
    TeachingWithdraw,
    TeachingExport,
    TeachingImportPreview,
    TeachingImport,
    CourseRender,
    LearningItems,
    LearningState,
    LearningHistory,
    LearningReview,
    CapabilitiesList,
    CapabilitySetEnabled,
    JobEnqueue,
    JobExecute,
    JobExecutionStatus,
    JobExecutionCancel,
    JobOutput,
    AssessmentCreate,
    AssessmentGet,
    LearningReference,
    MachineAnswer,
    MachineCorrection,
    MachineRetest,
    MachineTaskGet,
    MachineTasksList,
    MachineContextsList,
    AiAssetsList,
    AiAssetPacket,
    MachineRubricsList,
    MachineRubricCreate,
    MachineEvaluationsList,
    MachineEvaluationCreate,
    MachineAnswerSnapshot,
    SourceJobTransform,
    KnowledgeFromTransform,
    WorkspaceBackup,
    WorkspaceBackups,
    UiStateRead,
    UiStateWrite,
    UiStateClearSaved,
    UiStateClearJob,
    UiStateRecover,
    // Constructed only by version 2 host commands; strict v1 JSON cannot select it.
    #[serde(skip)]
    WorkspaceRestorePreview,
}

#[derive(Serialize)]
pub struct Reply {
    pub status: u16,
    pub body: Value,
}

fn id(payload: &Value, key: &str) -> Result<String, String> {
    let value = payload
        .get(key)
        .and_then(Value::as_str)
        .ok_or("CORE_COMMAND_ID_REQUIRED")?;
    // Core-generated archive jobs contain a file suffix and may be longer than
    // source IDs. Match Core's bounded ASCII job vocabulary only for job_id.
    let job_id = key == "job_id";
    if value.is_empty()
        || value.len() > if job_id { 200 } else { 128 }
        || matches!(value, "." | "..")
        || !value
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || c == b'-' || c == b'_' || (job_id && c == b'.'))
    {
        return Err("CORE_COMMAND_ID_INVALID".into());
    }
    Ok(value.to_owned())
}

fn execution_request_id(payload: &Value) -> Result<String, String> {
    if payload.get("request_id").is_some() {
        id(payload, "request_id")
    } else {
        id(payload, "job_id")
    }
}

fn teaching_id(payload: &Value, key: &str) -> Result<String, String> {
    let value = payload
        .get(key)
        .and_then(Value::as_str)
        .ok_or("CORE_COMMAND_ID_REQUIRED")?;
    if value.is_empty()
        || value.len() > 128
        || matches!(value, "." | "..")
        || !value
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, b'-' | b'_' | b'.'))
    {
        return Err("CORE_COMMAND_ID_INVALID".into());
    }
    Ok(value.to_owned())
}

// Document references and graph cursors use the Core reference vocabulary.
// This does not relax unrelated legacy route identifiers.
fn reference_id(payload: &Value, key: &str) -> Result<String, String> {
    let value = payload
        .get(key)
        .and_then(Value::as_str)
        .ok_or("CORE_COMMAND_ID_REQUIRED")?;
    if value.is_empty()
        || value.len() > 256
        || matches!(value, "." | "..")
        || !value
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, b'-' | b'_' | b'.'))
    {
        return Err("CORE_COMMAND_ID_INVALID".into());
    }
    Ok(value.to_owned())
}

fn learning_item_key(payload: &Value) -> Result<String, String> {
    let value = payload
        .get("item_key")
        .and_then(Value::as_str)
        .ok_or("CORE_COMMAND_ID_REQUIRED")?;
    // Only Core's exact course/artifact vocabulary needs colons and 159 bytes.
    // Other identifiers keep the original bounded path-segment contract.
    if let Some(rest) = value.strip_prefix("course:course-") {
        if let Some((course, lesson)) = rest.split_once(":artifact:lesson-") {
            let digest = |part: &str| {
                part.len() == 64
                    && part
                        .bytes()
                        .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
            };
            if digest(course) && digest(lesson) {
                return Ok(value.to_owned());
            }
        }
        return Err("CORE_COMMAND_ID_INVALID".into());
    }
    id(payload, "item_key")
}

fn route(request: &Request) -> Result<(&'static str, String, Option<Value>), String> {
    use Operation::*;
    let p = &request.payload;
    let body = || {
        p.get("body")
            .cloned()
            .ok_or_else(|| "CORE_COMMAND_BODY_REQUIRED".to_owned())
    };
    Ok(match request.operation {
        SystemVersion => ("GET", "/api/v1/system/version".into(), None),
        WorkspaceRestorePreview => (
            "POST",
            "/api/v2/workspace/restore/preview".into(),
            Some(body()?),
        ),
        SourceImport => ("POST", "/api/v1/imports".into(), Some(body()?)),
        SourcesList => ("GET", "/api/v1/sources".into(), None),
        SourceJobs => (
            "GET",
            format!("/api/v1/sources/{}/jobs", id(p, "source_id")?),
            None,
        ),
        SourceMembers => (
            "GET",
            format!("/api/v1/sources/{}/members", id(p, "source_id")?),
            None,
        ),
        SourcePages => (
            "GET",
            format!("/api/v1/sources/{}/pages", id(p, "source_id")?),
            None,
        ),
        SourceOriginal => (
            "GET",
            format!("/api/v1/sources/{}/original", id(p, "source_id")?),
            None,
        ),
        DocumentsList => {
            let path = if let Some(cursor) = p.get("cursor") {
                let cursor = cursor.as_str().ok_or("cursor must be a string")?;
                if cursor.is_empty()
                    || cursor.len() > 1024
                    || !cursor
                        .bytes()
                        .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
                {
                    return Err("invalid document cursor".into());
                }
                format!("/api/v1/documents?cursor={cursor}")
            } else {
                "/api/v1/documents".into()
            };
            ("GET", path, None)
        }
        DocumentCreate => ("POST", "/api/v1/documents".into(), Some(body()?)),
        DocumentChecks => {
            let base = format!("/api/v1/documents/{}/checks", id(p, "document_id")?);
            let mut query = Vec::new();
            if let Some(value) = p.get("version") {
                let version = value
                    .as_u64()
                    .filter(|v| *v > 0)
                    .ok_or("CORE_COMMAND_VERSION_INVALID")?;
                query.push(format!("version={version}"));
            }
            if let Some(value) = p.get("offset") {
                let offset = value
                    .as_u64()
                    .filter(|v| *v <= i64::MAX as u64)
                    .ok_or("CORE_COMMAND_OFFSET_INVALID")?;
                query.push(format!("offset={offset}"));
            }
            let path = if query.is_empty() {
                base
            } else {
                format!("{base}?{}", query.join("&"))
            };
            ("GET", path, None)
        }
        DocumentCheckRecord => (
            "POST",
            format!("/api/v1/documents/{}/checks", id(p, "document_id")?),
            Some(body()?),
        ),
        DocumentCheckExecute => (
            "POST",
            format!("/api/v1/documents/{}/checks/execute", id(p, "document_id")?),
            Some(body()?),
        ),
        DocumentGet => (
            "GET",
            format!("/api/v1/documents/{}", id(p, "document_id")?),
            None,
        ),
        DocumentGraph => {
            let mut query = Vec::new();
            if let Some(value) = p.get("version") {
                let version = value
                    .as_u64()
                    .filter(|v| *v > 0 && *v <= i64::MAX as u64)
                    .ok_or("CORE_COMMAND_VERSION_INVALID")?;
                query.push(format!("version={version}"));
            }
            if p.get("cursor").is_some() {
                query.push(format!("cursor={}", reference_id(p, "cursor")?));
            }
            (
                "GET",
                format!(
                    "/api/v1/documents/{}/relations{}",
                    reference_id(p, "document_id")?,
                    if query.is_empty() {
                        String::new()
                    } else {
                        format!("?{}", query.join("&"))
                    }
                ),
                None,
            )
        }
        CollectionQuery => {
            let mut query = vec![format!("view_id={}", teaching_id(p, "view_id")?)];
            if let Some(value) = p.get("version") {
                let version = value
                    .as_u64()
                    .filter(|v| *v > 0 && *v <= i64::MAX as u64)
                    .ok_or("CORE_COMMAND_VERSION_INVALID")?;
                query.push(format!("version={version}"));
            }
            for (key, min, max) in [("offset", 0, 500), ("limit", 1, 100)] {
                if let Some(value) = p.get(key) {
                    let value = value
                        .as_u64()
                        .filter(|v| *v >= min && *v <= max)
                        .ok_or("CORE_COLLECTION_PAGE_INVALID")?;
                    query.push(format!("{key}={value}"));
                }
            }
            (
                "GET",
                format!(
                    "/api/v1/documents/{}/collection?{}",
                    reference_id(p, "document_id")?,
                    query.join("&")
                ),
                None,
            )
        }
        DocumentDraft => (
            "PUT",
            format!("/api/v1/documents/{}/draft", id(p, "document_id")?),
            Some(body()?),
        ),
        DocumentRestore => (
            "POST",
            format!("/api/v1/documents/{}/restore", id(p, "document_id")?),
            Some(body()?),
        ),
        DocumentVersion => {
            let version = p
                .get("version")
                .and_then(Value::as_u64)
                .filter(|v| *v > 0)
                .ok_or("CORE_COMMAND_VERSION_INVALID")?;
            (
                "GET",
                format!(
                    "/api/v1/documents/{}/versions/{version}",
                    id(p, "document_id")?
                ),
                None,
            )
        }
        DocumentExport | DocumentExportSave => {
            let format = p
                .get("format")
                .and_then(Value::as_str)
                .filter(|v| matches!(*v, "markdown" | "obsidian"))
                .ok_or("CORE_EXPORT_FORMAT_INVALID")?;
            (
                "GET",
                format!(
                    "/api/v1/documents/{}/export?format={format}",
                    id(p, "document_id")?
                ),
                None,
            )
        }
        JobsGet => ("GET", format!("/api/v1/jobs/{}", id(p, "job_id")?), None),
        JobQuality => (
            "GET",
            format!("/api/v1/jobs/{}/quality", id(p, "job_id")?),
            None,
        ),
        AnchorsList => (
            "GET",
            format!("/api/v1/sources/{}/anchors", id(p, "source_id")?),
            None,
        ),
        AnchorCreate => (
            "POST",
            format!("/api/v1/sources/{}/anchors", id(p, "source_id")?),
            Some(body()?),
        ),
        AnchorResolve => (
            "GET",
            format!(
                "/api/v1/sources/{}/anchors/{}/resolve",
                id(p, "source_id")?,
                id(p, "anchor_id")?
            ),
            None,
        ),
        Search => {
            let q = p
                .get("q")
                .and_then(Value::as_str)
                .filter(|q| !q.trim().is_empty() && q.len() <= 1024)
                .ok_or("CORE_SEARCH_INVALID")?;
            let query = url::form_urlencoded::Serializer::new(String::new())
                .append_pair("q", q)
                .append_pair(
                    "active_only",
                    if p.get("active_only")
                        .and_then(Value::as_bool)
                        .unwrap_or(false)
                    {
                        "true"
                    } else {
                        "false"
                    },
                )
                .finish();
            ("GET", format!("/api/v1/search?{query}"), None)
        }
        KnowledgeGet => (
            "GET",
            format!("/api/v1/knowledge-items/{}/v3", id(p, "id")?),
            None,
        ),
        KnowledgeQualification => (
            "GET",
            format!("/api/v1/knowledge-items/{}/qualification", id(p, "id")?),
            None,
        ),
        KnowledgeReview => (
            "POST",
            format!("/api/v1/knowledge/{}/review/versioned", id(p, "id")?),
            Some(body()?),
        ),
        CourseFromKnowledge => (
            "POST",
            "/api/v1/courses/from-knowledge".into(),
            Some(body()?),
        ),
        CourseList => {
            let suffix = if p.get("cursor").is_some() {
                format!("?cursor={}", id(p, "cursor")?)
            } else {
                String::new()
            };
            ("GET", format!("/api/v1/courses{suffix}"), None)
        }
        TeachingList => {
            let suffix = if p.get("cursor").is_some() {
                format!("?cursor={}", teaching_id(p, "cursor")?)
            } else {
                String::new()
            };
            ("GET", format!("/api/v2/teaching/records{suffix}"), None)
        }
        TeachingGet => (
            "GET",
            format!("/api/v2/teaching/records/{}", teaching_id(p, "record_id")?),
            None,
        ),
        TeachingExport => (
            "GET",
            format!(
                "/api/v2/teaching/records/{}/export",
                teaching_id(p, "record_id")?
            ),
            None,
        ),
        TeachingCreate => ("POST", "/api/v2/teaching/records".into(), Some(body()?)),
        TeachingWithdraw => ("POST", "/api/v2/teaching/withdrawals".into(), Some(body()?)),
        TeachingImportPreview => (
            "POST",
            "/api/v2/teaching/imports/preview".into(),
            Some(body()?),
        ),
        TeachingImport => ("POST", "/api/v2/teaching/imports".into(), Some(body()?)),
        CourseGet => (
            "GET",
            format!("/api/v1/courses/{}", id(p, "course_id")?),
            None,
        ),
        CourseRender => (
            "POST",
            format!("/api/v1/courses/{}/render", id(p, "course_id")?),
            Some(body()?),
        ),
        LearningItems => ("GET", "/api/v1/learning/items".into(), None),
        LearningState => (
            "GET",
            format!("/api/v1/learning/items/{}/state", learning_item_key(p)?),
            None,
        ),
        LearningHistory => (
            "GET",
            format!("/api/v1/learning/events/{}", learning_item_key(p)?),
            None,
        ),
        LearningReview => ("POST", "/api/v1/learning/reviews".into(), Some(body()?)),
        MachineAnswer => ("POST", "/api/v1/machine/answers".into(), Some(body()?)),
        MachineRubricCreate => ("POST", "/api/v1/machine/rubrics".into(), Some(body()?)),
        MachineEvaluationCreate => ("POST", "/api/v1/machine/evaluations".into(), Some(body()?)),
        MachineAnswerSnapshot => (
            "GET",
            format!("/api/v1/machine/answers/{}/snapshot", id(p, "task_id")?),
            None,
        ),
        AiAssetsList => {
            let mut path = "/api/v1/ai/assets".to_owned();
            if p.get("cursor").is_some_and(|v| !v.is_null()) {
                path.push_str(&format!("?cursor={}", reference_id(p, "cursor")?));
            }
            ("GET", path, None)
        }
        AiAssetPacket => ("POST", "/api/v1/ai/context-packets".into(), Some(body()?)),
        MachineContextsList | MachineRubricsList | MachineEvaluationsList => {
            let path = match request.operation {
                MachineContextsList => "contexts",
                MachineRubricsList => "rubrics",
                _ => "evaluations",
            };
            let suffix = if p.get("cursor").is_some() {
                format!("?cursor={}", reference_id(p, "cursor")?)
            } else {
                String::new()
            };
            ("GET", format!("/api/v1/machine/{path}{suffix}"), None)
        }
        MachineCorrection => ("POST", "/api/v1/machine/corrections".into(), Some(body()?)),
        MachineRetest => ("POST", "/api/v1/machine/retests".into(), Some(body()?)),
        MachineTasksList => {
            let mut query = Vec::new();
            if p.get("cursor").is_some() {
                query.push(format!("cursor={}", reference_id(p, "cursor")?));
            }
            if let Some(value) = p.get("limit") {
                let limit = value
                    .as_u64()
                    .filter(|n| (1..=100).contains(n))
                    .ok_or("invalid receipt page limit")?;
                query.push(format!("limit={limit}"));
            }
            (
                "GET",
                format!(
                    "/api/v1/machine/tasks{}",
                    if query.is_empty() {
                        String::new()
                    } else {
                        format!("?{}", query.join("&"))
                    }
                ),
                None,
            )
        }
        MachineTaskGet => (
            "GET",
            format!("/api/v1/machine/tasks/{}", id(p, "task_id")?),
            None,
        ),
        SourceJobTransform => (
            "GET",
            format!(
                "/api/v1/sources/{}/jobs/{}/transform",
                id(p, "source_id")?,
                id(p, "job_id")?
            ),
            None,
        ),
        KnowledgeFromTransform => (
            "POST",
            "/api/v1/knowledge-items/from-transform".into(),
            Some(body()?),
        ),
        WorkspaceBackup => (
            "POST",
            "/api/v1/workspace/backups".into(),
            Some(serde_json::json!({})),
        ),
        WorkspaceBackups => ("GET", "/api/v1/workspace/backups".into(), None),
        UiStateRead => {
            if !p.as_object().is_some_and(|object| object.is_empty()) {
                return Err("CORE_UI_STATE_PAYLOAD_INVALID".into());
            }
            ("GET", "/api/v1/workspace/ui-state".into(), None)
        }
        UiStateWrite | UiStateClearSaved | UiStateClearJob | UiStateRecover => {
            if !p
                .as_object()
                .is_some_and(|object| object.len() == 1 && object.contains_key("body"))
            {
                return Err("CORE_UI_STATE_PAYLOAD_INVALID".into());
            }
            let value = body()?;
            if !value.is_object() {
                return Err("CORE_UI_STATE_PAYLOAD_INVALID".into());
            }
            let (method, path) = match request.operation {
                UiStateWrite => ("PUT", "/api/v1/workspace/ui-state"),
                UiStateClearJob => ("POST", "/api/v1/workspace/ui-state/clear-job"),
                UiStateClearSaved => ("POST", "/api/v1/workspace/ui-state/clear-saved"),
                UiStateRecover => ("POST", "/api/v1/workspace/ui-state/recover"),
                _ => unreachable!(),
            };
            (method, path.into(), Some(value))
        }
        AssessmentCreate => (
            "POST",
            format!(
                "/api/v1/learning/items/{}/assessment",
                learning_item_key(p)?
            ),
            Some(body()?),
        ),
        AssessmentGet => (
            "GET",
            format!(
                "/api/v1/learning/items/{}/assessment",
                learning_item_key(p)?
            ),
            None,
        ),
        LearningReference => (
            "POST",
            format!(
                "/api/v1/learning/items/{}/references",
                learning_item_key(p)?
            ),
            Some(body()?),
        ),
        CapabilitiesList => ("GET", "/api/v1/capabilities".into(), None),
        CapabilitySetEnabled => {
            let object = request
                .payload
                .as_object()
                .ok_or("CORE_COMMAND_PAYLOAD_OBJECT_REQUIRED")?;
            if object.len() != 2 {
                return Err("CORE_COMMAND_CAPABILITY_PAYLOAD_INVALID".into());
            }
            let capability = object
                .get("capability")
                .and_then(Value::as_str)
                .ok_or("CORE_COMMAND_CAPABILITY_REQUIRED")?;
            if capability.is_empty()
                || capability.len() > 128
                || capability.split('.').any(|part| part.is_empty())
                || !capability
                    .bytes()
                    .all(|c| c.is_ascii_alphanumeric() || c == b'-' || c == b'_' || c == b'.')
            {
                return Err("CORE_COMMAND_CAPABILITY_INVALID".into());
            }
            let enabled = object
                .get("enabled")
                .and_then(Value::as_bool)
                .ok_or("CORE_COMMAND_ENABLED_BOOLEAN_REQUIRED")?;
            (
                "PUT",
                format!("/api/v1/capabilities/{capability}/enabled"),
                Some(serde_json::json!({"enabled": enabled})),
            )
        }
        JobEnqueue => ("POST", "/api/v1/jobs".into(), Some(body()?)),
        JobExecutionStatus => (
            "GET",
            format!("/api/v1/jobs/{}/execution-status", id(p, "job_id")?),
            None,
        ),
        JobExecutionCancel => (
            "POST",
            format!(
                "/api/v1/jobs/{}/executions/{}/cancel",
                id(p, "job_id")?,
                id(p, "request_id")?
            ),
            None,
        ),
        JobExecute => (
            "POST",
            format!("/api/v1/jobs/{}/executions", id(p, "job_id")?),
            Some(body()?),
        ),
        JobOutput => {
            let kind = p
                .get("kind")
                .and_then(Value::as_str)
                .filter(|v| matches!(*v, "text" | "document_structure" | "loss_report"))
                .ok_or("CORE_OUTPUT_KIND_INVALID")?;
            (
                "GET",
                format!("/api/v1/jobs/{}/outputs/{kind}", id(p, "job_id")?),
                None,
            )
        }
    })
}

pub fn save_export(root: &std::path::Path, reply: &Reply) -> Result<Value, String> {
    if reply.status != 200 {
        return Err("CORE_EXPORT_UNAVAILABLE".into());
    }
    let document = id(&reply.body, "document_id")?;
    let format = reply.body["format"]
        .as_str()
        .filter(|v| matches!(*v, "markdown" | "obsidian"))
        .ok_or("CORE_EXPORT_INVALID")?;
    let version = reply.body["version"]
        .as_u64()
        .filter(|v| *v > 0)
        .ok_or("CORE_EXPORT_INVALID")?;
    let files = reply.body["files"]
        .as_array()
        .filter(|v| v.len() == 2)
        .ok_or("CORE_EXPORT_INVALID")?;
    for name in ["document.md", "manifest.json"] {
        if files.iter().filter(|file| file["path"] == name).count() != 1 {
            return Err("CORE_EXPORT_INVALID".into());
        }
    }
    for file in files {
        if file["content"]
            .as_str()
            .is_none_or(|v| v.len() > 24 * 1024 * 1024)
        {
            return Err("CORE_EXPORT_INVALID".into());
        }
    }
    let mut random = [0u8; 8];
    getrandom::fill(&mut random).map_err(|_| "CORE_EXPORT_UNAVAILABLE")?;
    let suffix: String = random.iter().map(|value| format!("{value:02x}")).collect();
    let relative = format!("exports/{document}/{format}/v{version}-{suffix}");
    let mut directory = root.to_path_buf();
    reject_link(&directory)?;
    for part in relative.split('/') {
        directory.push(part);
        if !directory.exists() {
            std::fs::create_dir(&directory).map_err(|_| "CORE_EXPORT_DIRECTORY_FAILED")?;
        }
        reject_link(&directory)?;
    }
    for file in files {
        let name = file["path"].as_str().ok_or("CORE_EXPORT_INVALID")?;
        let mut target = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(directory.join(name))
            .map_err(|_| "CORE_EXPORT_WRITE_FAILED")?;
        use std::io::Write;
        target
            .write_all(file["content"].as_str().unwrap().as_bytes())
            .and_then(|_| target.sync_all())
            .map_err(|_| "CORE_EXPORT_WRITE_FAILED")?;
    }
    Ok(
        serde_json::json!({"directory":relative,"files":["document.md","manifest.json"],"document_id":document,"version":version,"format":format}),
    )
}

fn reject_link(path: &std::path::Path) -> Result<(), String> {
    let meta = std::fs::symlink_metadata(path).map_err(|_| "CORE_EXPORT_DIRECTORY_FAILED")?;
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        if meta.file_attributes() & 0x400 != 0 {
            return Err("CORE_EXPORT_LINK_REJECTED".into());
        }
    }
    if !meta.is_dir() || meta.file_type().is_symlink() {
        return Err("CORE_EXPORT_LINK_REJECTED".into());
    }
    Ok(())
}

/// How long the host waits for the Core before aborting the request.
///
/// A client timeout shorter than the operation's own bound aborts the transport while the Core is
/// still working, so the durable result arrives after the UI has already reported failure.
fn transport_timeout(operation: &Operation) -> std::time::Duration {
    std::time::Duration::from_secs(match operation {
        // The owned worker permits 120 seconds plus 20 seconds for bounded
        // transport cleanup; keep a finite margin for durable readback.
        Operation::DocumentCheckExecute => 160,
        Operation::MachineAnswer => 135,
        Operation::MachineRetest => 135,
        Operation::WorkspaceBackup => 120,
        // The Core caps a job deadline at 300 seconds and the reader polls for 310; real media
        // jobs run past both, so the transport must outlive them.
        Operation::JobExecute => 320,
        Operation::CourseFromKnowledge | Operation::CourseRender => 60,
        _ => 30,
    })
}

fn request_byte_limit(operation: &Operation) -> usize {
    if matches!(operation, Operation::SourceImport) {
        90 * 1024 * 1024
    } else if matches!(
        operation,
        Operation::UiStateWrite
            | Operation::UiStateClearSaved
            | Operation::UiStateClearJob
            | Operation::UiStateRecover
    ) {
        1_100_000
    } else {
        8 * 1024 * 1024
    }
}
fn response_byte_limit(operation: &Operation) -> usize {
    if matches!(operation, Operation::SourceOriginal) {
        90 * 1024 * 1024
    } else {
        24 * 1024 * 1024
    }
}

pub fn execute(port: u16, token: &str, request: Request) -> Result<Reply, String> {
    let (method, path, body) = route(&request)?;
    if let Some(ref body) = body {
        if serde_json::to_vec(body)
            .map_err(|_| "CORE_COMMAND_BODY_INVALID")?
            .len()
            > request_byte_limit(&request.operation)
        {
            return Err("CORE_COMMAND_BODY_TOO_LARGE".into());
        }
    }
    let client = reqwest::blocking::Client::builder()
        .no_proxy()
        .redirect(reqwest::redirect::Policy::none())
        .timeout(transport_timeout(&request.operation))
        .build()
        .map_err(|_| "CORE_TRANSPORT_UNAVAILABLE")?;
    let mut builder = client
        .request(
            method.parse().map_err(|_| "CORE_COMMAND_INVALID")?,
            format!("http://127.0.0.1:{port}{path}"),
        )
        .header("X-ArcheAxis-Launch-Token", token);
    if matches!(request.operation, Operation::JobExecute) {
        builder = builder.header("idempotency-key", execution_request_id(&request.payload)?);
    }
    if let Some(body) = body {
        builder = builder.json(&body);
    }
    let response = builder.send().map_err(|_| "CORE_TRANSPORT_FAILED")?;
    let status = response.status().as_u16();
    let response_limit = response_byte_limit(&request.operation);
    let mut bytes = Vec::new();
    response
        .take(response_limit as u64 + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| "CORE_RESPONSE_FAILED")?;
    if bytes.len() > response_limit {
        return Err("CORE_RESPONSE_TOO_LARGE".into());
    }
    let body = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes)
            .unwrap_or_else(|_| serde_json::json!({"message":String::from_utf8_lossy(&bytes)}))
    };
    Ok(Reply { status, body })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn course_commands_and_long_learning_keys_remain_finite() {
        let course = format!("course-{}", "a".repeat(64));
        let key = format!("course:{course}:artifact:lesson-{}", "b".repeat(64));
        for operation in [
            "learning_state",
            "learning_history",
            "assessment_create",
            "assessment_get",
            "learning_reference",
        ] {
            let request = serde_json::from_value::<Request>(
                serde_json::json!({"operation":operation,"payload":{"item_key":key,"body":{}}}),
            )
            .unwrap();
            assert!(route(&request).unwrap().1.contains(&key));
            for invalid in [
                format!("{key}/private"),
                key.replace("artifact:", "artifact%3A"),
                key.replace(&"a".repeat(64), &"g".repeat(64)),
                "a".repeat(159),
                "arbitrary:colon".into(),
            ] {
                let request = serde_json::from_value::<Request>(serde_json::json!({"operation":operation,"payload":{"item_key":invalid,"body":{}}})).unwrap();
                assert!(route(&request).is_err());
            }
        }
        for (operation, method, path) in [
            (
                "course_from_knowledge",
                "POST",
                "/api/v1/courses/from-knowledge".to_owned(),
            ),
            ("course_get", "GET", format!("/api/v1/courses/{course}")),
            (
                "course_render",
                "POST",
                format!("/api/v1/courses/{course}/render"),
            ),
        ] {
            let request = serde_json::from_value::<Request>(serde_json::json!({"operation":operation,"payload":{"course_id":course,"body":{"knowledge_id":"knowledge-safe"}}})).unwrap();
            let actual = route(&request).unwrap();
            assert_eq!(actual.0, method);
            assert_eq!(actual.1, path);
        }
        assert!(id(&serde_json::json!({"source_id":key}), "source_id").is_err());
        let request = serde_json::from_value::<Request>(
            serde_json::json!({"operation":"course_get","payload":{"course_id":"../private"}}),
        )
        .unwrap();
        assert!(route(&request).is_err());
    }
    #[test]
    fn job_execute_transport_outlives_the_core_job_deadline() {
        // The Core caps a job deadline at 300 seconds and the reader polls to 310; a shorter client
        // timeout aborts the request while the job is still going to succeed durably.
        assert!(transport_timeout(&Operation::JobExecute) >= std::time::Duration::from_secs(310));
        assert!(
            transport_timeout(&Operation::CourseFromKnowledge) > std::time::Duration::from_secs(30)
        );
        assert!(transport_timeout(&Operation::CourseRender) > std::time::Duration::from_secs(30));
        assert_eq!(
            transport_timeout(&Operation::SourceImport),
            std::time::Duration::from_secs(30)
        );
    }
    #[test]
    fn capability_enable_is_a_finite_boolean_write() {
        for enabled in [false, true] {
            let request: Request = serde_json::from_value(serde_json::json!({
                "operation": "capability_set_enabled",
                "payload": {"capability": "text.extract", "enabled": enabled}
            }))
            .unwrap();
            let actual = route(&request).unwrap();
            assert_eq!(actual.0, "PUT");
            assert_eq!(actual.1, "/api/v1/capabilities/text.extract/enabled");
            assert_eq!(actual.2, Some(serde_json::json!({"enabled": enabled})));
        }
        for payload in [
            serde_json::json!({"capability":"../text.extract","enabled":false}),
            serde_json::json!({"capability":"text.extract?x=1","enabled":false}),
            serde_json::json!({"capability":"text..extract","enabled":false}),
            serde_json::json!({"capability":"text.extract","enabled":"false"}),
            serde_json::json!({"capability":"text.extract"}),
            serde_json::json!({"capability":"text.extract","enabled":true,"url":"https://example.com"}),
        ] {
            let request: Request = serde_json::from_value(serde_json::json!({
                "operation":"capability_set_enabled", "payload":payload
            }))
            .unwrap();
            assert!(route(&request).is_err());
        }
    }
    #[test]
    fn finite_execution_status_cancel_and_explicit_retry_identity() {
        let status: Request = serde_json::from_value(
            serde_json::json!({"operation":"job_execution_status","payload":{"job_id":"job-safe"}}),
        )
        .unwrap();
        assert_eq!(
            route(&status).unwrap().1,
            "/api/v1/jobs/job-safe/execution-status"
        );
        let cancel: Request = serde_json::from_value(serde_json::json!({"operation":"job_execution_cancel","payload":{"job_id":"job-safe","request_id":"retry-safe"}})).unwrap();
        let actual = route(&cancel).unwrap();
        assert_eq!(actual.0, "POST");
        assert_eq!(
            actual.1,
            "/api/v1/jobs/job-safe/executions/retry-safe/cancel"
        );
        assert!(actual.2.is_none());
        assert_eq!(
            execution_request_id(&serde_json::json!({"job_id":"job-safe"})).unwrap(),
            "job-safe"
        );
        assert_eq!(
            execution_request_id(
                &serde_json::json!({"job_id":"job-safe","request_id":"retry-safe"})
            )
            .unwrap(),
            "retry-safe"
        );
        for invalid in ["", "../private", "a/b", "a%2fb"] {
            assert!(execution_request_id(
                &serde_json::json!({"job_id":"job-safe","request_id":invalid})
            )
            .is_err());
            let request: Request=serde_json::from_value(serde_json::json!({"operation":"job_execution_cancel","payload":{"job_id":"job-safe","request_id":invalid}})).unwrap();
            assert!(route(&request).is_err());
        }
    }
    #[test]
    fn asset_context_commands_are_finite_and_cursor_cannot_change_route() {
        let list: Request = serde_json::from_value(
            serde_json::json!({"operation":"ai_assets_list","payload":{"cursor":"doc-safe"}}),
        )
        .unwrap();
        let actual = route(&list).unwrap();
        assert_eq!(actual.0, "GET");
        assert_eq!(actual.1, "/api/v1/ai/assets?cursor=doc-safe");
        assert!(actual.2.is_none());
        for cursor in ["../private", "a&scope=all", "a%26scope", "a/b"] {
            let bad: Request = serde_json::from_value(
                serde_json::json!({"operation":"ai_assets_list","payload":{"cursor":cursor}}),
            )
            .unwrap();
            assert!(route(&bad).is_err());
        }
        let packet:Request=serde_json::from_value(serde_json::json!({"operation":"ai_asset_packet","payload":{"body":{"request_id":"packet-safe"}}})).unwrap();
        let actual = route(&packet).unwrap();
        assert_eq!(actual.0, "POST");
        assert_eq!(actual.1, "/api/v1/ai/context-packets");
        assert_eq!(actual.2.unwrap()["request_id"], "packet-safe");
    }
    #[test]
    fn exports_reject_traversal_before_creating_any_output() {
        let root = tempfile::tempdir().unwrap();
        let reply = Reply {
            status: 200,
            body: serde_json::json!({"document_id":"doc-safe","format":"markdown","version":1,"files":[{"path":"../private","content":"x"},{"path":"manifest.json","content":"{}"}]}),
        };
        assert!(save_export(root.path(), &reply).is_err());
        assert!(!root.path().join("exports").exists());
    }
    #[test]
    fn v1_client_cannot_select_internal_v2_recovery_transport() {
        assert!(serde_json::from_value::<Request>(serde_json::json!({"operation":"workspace_restore_preview","payload":{"body":{"backup_id":"a".repeat(32),"expected_sha256":"b".repeat(64)}}})).is_err());
    }
    #[test]
    fn every_schema_command_is_accepted_by_the_host_contract() {
        let schema: Value = serde_json::from_str(include_str!(
            "../../packages/contracts/v1/core-command.schema.json"
        ))
        .unwrap();
        for operation in schema["properties"]["operation"]["enum"]
            .as_array()
            .unwrap()
        {
            serde_json::from_value::<Request>(
                serde_json::json!({"operation":operation,"payload":{}}),
            )
            .expect("schema and host command contract must agree");
        }
    }
    #[test]
    fn bridge_rejects_arbitrary_transport_and_traversal() {
        assert!(serde_json::from_str::<Request>(
            r#"{"operation":"fetch","payload":{"url":"https://example.com"}}"#
        )
        .is_err());
        assert!(serde_json::from_str::<Request>(
            r#"{"operation":"sources_list","token":"secret"}"#
        )
        .is_err());
        let request = serde_json::from_str::<Request>(
            r#"{"operation":"source_original","payload":{"source_id":"../private"}}"#,
        )
        .unwrap();
        assert!(route(&request).is_err());
        let request = serde_json::from_value::<Request>(
            serde_json::json!({"operation":"source_jobs","payload":{"source_id":"src-safe"}}),
        )
        .unwrap();
        let (method, path, body) = route(&request).unwrap();
        assert_eq!(method, "GET");
        assert_eq!(path, "/api/v1/sources/src-safe/jobs");
        assert!(body.is_none());
        let request = serde_json::from_value::<Request>(
            serde_json::json!({"operation":"source_jobs","payload":{"source_id":"../private"}}),
        )
        .unwrap();
        assert!(route(&request).is_err());
    }

    #[test]
    fn source_members_is_a_finite_read_with_validated_source_id() {
        let request = serde_json::from_value::<Request>(
            serde_json::json!({"operation":"source_members","payload":{"source_id":"src-safe"}}),
        )
        .unwrap();
        let (method, path, body) = route(&request).unwrap();
        assert_eq!(method, "GET");
        assert_eq!(path, "/api/v1/sources/src-safe/members");
        assert!(body.is_none());
        for source_id in ["../private", "src-safe?token=x", "src-safe/members"] {
            let request = serde_json::from_value::<Request>(
                serde_json::json!({"operation":"source_members","payload":{"source_id":source_id}}),
            )
            .unwrap();
            assert!(route(&request).is_err());
        }
    }

    #[test]
    fn source_pages_is_a_finite_read_with_validated_source_id() {
        let request = serde_json::from_value::<Request>(
            serde_json::json!({"operation":"source_pages","payload":{"source_id":"src-safe"}}),
        )
        .unwrap();
        let (method, path, body) = route(&request).unwrap();
        assert_eq!(method, "GET");
        assert_eq!(path, "/api/v1/sources/src-safe/pages");
        assert!(body.is_none());
        for source_id in ["../private", "src-safe?token=x", "src-safe/pages"] {
            let request = serde_json::from_value::<Request>(
                serde_json::json!({"operation":"source_pages","payload":{"source_id":source_id}}),
            )
            .unwrap();
            assert!(route(&request).is_err());
        }
    }

    #[test]
    fn archive_job_ids_match_core_without_relaxing_other_path_ids() {
        for job_id in ["archive-member-0001-known.csv".to_owned(), "a".repeat(200)] {
            let request = serde_json::from_value::<Request>(serde_json::json!({
                "operation":"job_execute", "payload":{"job_id":job_id,"body":{"deadline_ms":30000}}
            }))
            .unwrap();
            assert_eq!(
                route(&request).unwrap().1,
                format!("/api/v1/jobs/{job_id}/executions")
            );
        }
        for job_id in [
            ".".to_owned(),
            "..".to_owned(),
            "../private".to_owned(),
            "id?x=1".to_owned(),
            "id%2fprivate".to_owned(),
            "a".repeat(201),
        ] {
            let request = serde_json::from_value::<Request>(serde_json::json!({
                "operation":"jobs_get", "payload":{"job_id":job_id}
            }))
            .unwrap();
            assert!(route(&request).is_err());
        }
        let request = serde_json::from_value::<Request>(serde_json::json!({
            "operation":"source_original", "payload":{"source_id":"source.with.dot"}
        }))
        .unwrap();
        assert!(route(&request).is_err());
    }

    #[test]
    fn envelope_payload_matches_the_schema_object_boundary() {
        for payload in [
            Value::Null,
            serde_json::json!([]),
            serde_json::json!(42),
            serde_json::json!("body"),
        ] {
            assert!(serde_json::from_value::<Request>(
                serde_json::json!({"operation":"system_version","payload":payload})
            )
            .is_err());
        }
        let default =
            serde_json::from_value::<Request>(serde_json::json!({"operation":"system_version"}))
                .unwrap();
        assert!(default.payload.is_object());
        assert!(route(&default).is_ok());
    }
    #[test]
    fn document_check_execute_is_finite_and_keeps_retry_body() {
        let body = serde_json::json!({"check_id":"check-safe","expected_content_sha256":"a".repeat(64),"retry_of_task_id":"doccheck_old"});
        let request=serde_json::from_value::<Request>(serde_json::json!({"operation":"document_check_execute","payload":{"document_id":"doc-safe","body":body}})).unwrap();
        let (method, path, value) = route(&request).unwrap();
        assert_eq!(method, "POST");
        assert_eq!(path, "/api/v1/documents/doc-safe/checks/execute");
        assert_eq!(value, Some(body));
        for unsafe_id in ["../secret", "doc/a", "https://example.test", "doc?url=bad"] {
            let request=serde_json::from_value::<Request>(serde_json::json!({"operation":"document_check_execute","payload":{"document_id":unsafe_id,"body":{}}})).unwrap();
            assert!(route(&request).is_err());
        }
    }
    #[test]
    fn check_history_queries_are_finite_and_numeric() {
        let request = serde_json::from_value::<Request>(serde_json::json!({
            "operation":"document_checks","payload":{"document_id":"doc-safe","version":2,"offset":1000}
        })).unwrap();
        let (method, path, body) = route(&request).unwrap();
        assert_eq!(method, "GET");
        assert_eq!(
            path,
            "/api/v1/documents/doc-safe/checks?version=2&offset=1000"
        );
        assert!(body.is_none());
        for payload in [
            serde_json::json!({"document_id":"doc-safe","version":0}),
            serde_json::json!({"document_id":"doc-safe","offset":-1}),
            serde_json::json!({"document_id":"doc-safe","offset":"0&actor=human"}),
            serde_json::json!({"document_id":"../private"}),
        ] {
            let request = serde_json::from_value::<Request>(
                serde_json::json!({"operation":"document_checks","payload":payload}),
            )
            .unwrap();
            assert!(route(&request).is_err());
        }
    }

    #[test]
    fn machine_retest_is_a_fixed_core_route_with_bounded_transport_time() {
        let body = serde_json::json!({
            "retest_of":"evaluation_answer123",
            "knowledge_id":"correction123",
            "question":"same question",
            "max_tokens":2048,
            "timeout_s":120
        });
        let request = serde_json::from_value::<Request>(serde_json::json!({
            "operation": "machine_retest",
            "payload": {"body": body}
        }))
        .unwrap();
        let (method, path, actual_body) = route(&request).unwrap();
        assert_eq!(method, "POST");
        assert_eq!(path, "/api/v1/machine/retests");
        assert_eq!(actual_body, Some(body));
        assert_eq!(
            transport_timeout(&request.operation),
            std::time::Duration::from_secs(135)
        );
    }
}

#[cfg(test)]
mod media_bridge_budget_tests {
    #[test]
    fn document_cursor_cannot_change_the_route_or_query() {
        use super::*;
        let request: Request = serde_json::from_value(
            serde_json::json!({"operation":"documents_list","payload":{"cursor":"abc_DEF-123"}}),
        )
        .unwrap();
        assert_eq!(
            route(&request).unwrap().1,
            "/api/v1/documents?cursor=abc_DEF-123"
        );
        for cursor in [
            serde_json::json!("../private"),
            serde_json::json!("x&actor=human"),
            serde_json::json!(""),
            serde_json::json!(12),
            serde_json::json!("x".repeat(1025)),
        ] {
            let request: Request = serde_json::from_value(
                serde_json::json!({"operation":"documents_list","payload":{"cursor":cursor}}),
            )
            .unwrap();
            assert!(route(&request).is_err());
        }
    }
    #[test]
    fn enlarged_budgets_are_bound_to_original_transfer_operations() {
        use super::*;
        assert_eq!(
            request_byte_limit(&Operation::SourceImport),
            90 * 1024 * 1024
        );
        assert_eq!(
            response_byte_limit(&Operation::SourceOriginal),
            90 * 1024 * 1024
        );
        assert_eq!(
            request_byte_limit(&Operation::DocumentDraft),
            8 * 1024 * 1024
        );
        assert_eq!(response_byte_limit(&Operation::JobOutput), 24 * 1024 * 1024);
        assert_eq!(
            request_byte_limit(&Operation::SourceOriginal),
            8 * 1024 * 1024
        );
        assert_eq!(
            response_byte_limit(&Operation::SourceImport),
            24 * 1024 * 1024
        );
    }
    #[test]
    fn course_catalog_is_read_only_and_rejects_cursor_escape() {
        use super::*;
        let request: Request =
            serde_json::from_value(serde_json::json!({"operation":"course_list"})).unwrap();
        let (method, path, body) = route(&request).unwrap();
        assert_eq!(method, "GET");
        assert_eq!(path, "/api/v1/courses");
        assert!(body.is_none());
        let request: Request = serde_json::from_value(
            serde_json::json!({"operation":"course_list","payload":{"cursor":"../private"}}),
        )
        .unwrap();
        assert!(route(&request).is_err());
    }
}

#[cfg(test)]
mod teaching_bridge_tests {
    use super::*;
    use serde_json::json;
    #[test]
    fn teaching_routes_remain_finite_and_reject_path_escape() {
        for (operation, path) in [
            (Operation::TeachingGet, "/api/v2/teaching/records/record.v2"),
            (
                Operation::TeachingExport,
                "/api/v2/teaching/records/record.v2/export",
            ),
        ] {
            let routed = route(&Request {
                operation,
                payload: json!({"record_id":"record.v2"}),
            })
            .unwrap();
            assert_eq!(routed.0, "GET");
            assert_eq!(routed.1, path);
            assert!(routed.2.is_none());
        }
        for id in ["../other", "E:\\private", "x?actor=human", "x/y", ".."] {
            assert!(route(&Request {
                operation: Operation::TeachingGet,
                payload: json!({"record_id":id})
            })
            .is_err());
        }
        let preview = route(&Request {
            operation: Operation::TeachingImportPreview,
            payload: json!({"body":{"schema":"archeaxis.teaching-exchange/v2"}}),
        })
        .unwrap();
        assert_eq!(preview.0, "POST");
        assert_eq!(preview.1, "/api/v2/teaching/imports/preview");
        assert_eq!(
            request_byte_limit(&Operation::TeachingImport),
            8 * 1024 * 1024
        );
    }
    #[test]
    fn research_queries_pin_versions_and_bound_scan_arguments() {
        let graph=route(&Request{operation:Operation::DocumentGraph,payload:serde_json::json!({"document_id":"doc.real","version":3,"cursor":"doc.cursor"})}).unwrap();
        assert_eq!(graph.0, "GET");
        assert_eq!(
            graph.1,
            "/api/v1/documents/doc.real/relations?version=3&cursor=doc.cursor"
        );
        assert!(graph.2.is_none());
        let collection=route(&Request{operation:Operation::CollectionQuery,payload:serde_json::json!({"document_id":"doc.real","version":2,"view_id":"view.real","offset":20,"limit":10})}).unwrap();
        assert_eq!(collection.0, "GET");
        assert_eq!(
            collection.1,
            "/api/v1/documents/doc.real/collection?view_id=view.real&version=2&offset=20&limit=10"
        );
        assert!(collection.2.is_none());
        for payload in [
            serde_json::json!({"document_id":"../escape"}),
            serde_json::json!({"document_id":"doc","version":0}),
            serde_json::json!({"document_id":"doc","version":18446744073709551615_u64}),
            serde_json::json!({"document_id":"doc","cursor":"x?actor=human"}),
        ] {
            assert!(route(&Request {
                operation: Operation::DocumentGraph,
                payload
            })
            .is_err());
        }
        for payload in [
            serde_json::json!({"document_id":"doc","view_id":"view","limit":0}),
            serde_json::json!({"document_id":"doc","view_id":"view","limit":101}),
            serde_json::json!({"document_id":"doc","view_id":"view","offset":501}),
            serde_json::json!({"document_id":"doc","view_id":"view/escape"}),
        ] {
            assert!(route(&Request {
                operation: Operation::CollectionQuery,
                payload
            })
            .is_err());
        }
    }
}

#[cfg(test)]
mod folder_native_contract_regression {
    use super::*;
    use std::io::{Read, Write};
    use std::net::TcpListener;
    use std::time::{Duration, Instant};

    #[test]
    fn folder_explicit_execute_body_and_request_identity_survive_native_http_transport() {
        // SYNTHETIC owned loopback fixture; no Core/worker or credentials.
        let listener = TcpListener::bind(("127.0.0.1", 0)).unwrap();
        listener.set_nonblocking(true).unwrap();
        let port = listener.local_addr().unwrap().port();
        let server = std::thread::spawn(move || {
            for replayed in [false, true] {
                let until = Instant::now() + Duration::from_secs(5);
                let mut socket = loop {
                    match listener.accept() {
                        Ok((socket, _)) => break socket,
                        Err(error)
                            if error.kind() == std::io::ErrorKind::WouldBlock
                                && Instant::now() < until =>
                        {
                            std::thread::sleep(Duration::from_millis(5))
                        }
                        Err(error) => panic!("owned native fixture accept: {error}"),
                    }
                };
                // Windows accepted sockets can inherit the nonblocking listener mode.
                // The owned fixture uses bounded blocking reads below, like the client.
                socket.set_nonblocking(false).unwrap();
                socket
                    .set_read_timeout(Some(Duration::from_secs(5)))
                    .unwrap();
                let mut bytes = Vec::new();
                let mut buffer = [0; 1024];
                loop {
                    let count = socket.read(&mut buffer).unwrap();
                    assert!(count > 0);
                    bytes.extend_from_slice(&buffer[..count]);
                    assert!(bytes.len() < 16384);
                    if let Some(header_end) = bytes.windows(4).position(|part| part == b"\r\n\r\n")
                    {
                        let headers = String::from_utf8(bytes[..header_end].to_vec()).unwrap();
                        let lower = headers.to_ascii_lowercase();
                        let length = lower
                            .lines()
                            .find_map(|line| {
                                line.strip_prefix("content-length:")
                                    .map(|value| value.trim().parse::<usize>().unwrap())
                            })
                            .unwrap();
                        if bytes.len() < header_end + 4 + length {
                            continue;
                        }
                        assert!(headers
                            .starts_with("POST /api/v1/jobs/folder-text-safe/executions HTTP/1.1"));
                        assert!(lower
                            .lines()
                            .any(|line| line == "idempotency-key: folder-explicit-request"));
                        assert!(lower.lines().any(|line| line
                            == "x-archeaxis-launch-token: synthetic-owned-native-contract"));
                        let body: Value =
                            serde_json::from_slice(&bytes[header_end + 4..header_end + 4 + length])
                                .unwrap();
                        assert_eq!(
                            body,
                            serde_json::json!({"deadline_ms":5000,"split":false,"words":false})
                        );
                        assert!(body.get("job_id").is_none());
                        assert!(body.get("request_id").is_none());
                        break;
                    }
                }
                let body=serde_json::json!({"job_id":"folder-text-safe","request_id":"folder-explicit-request","state":"running","replayed":replayed}).to_string();
                let response=format!("HTTP/1.1 202 Accepted\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",body.len(),body);
                socket.write_all(response.as_bytes()).unwrap();
            }
        });
        for expected in [false, true] {
            let request:Request=serde_json::from_value(serde_json::json!({"operation":"job_execute","payload":{"job_id":"folder-text-safe","request_id":"folder-explicit-request","body":{"deadline_ms":5000,"split":false,"words":false}}})).unwrap();
            let reply = execute(port, "synthetic-owned-native-contract", request).unwrap();
            assert_eq!(reply.status, 202);
            assert_eq!(
                reply.body,
                serde_json::json!({"job_id":"folder-text-safe","request_id":"folder-explicit-request","state":"running","replayed":expected})
            );
        }
        server.join().unwrap();
    }

    #[test]
    fn folder_bodyless_execute_is_refused_and_cancel_binds_exact_attempt() {
        let missing:Request=serde_json::from_value(serde_json::json!({"operation":"job_execute","payload":{"job_id":"folder-text-safe","request_id":"folder-explicit-request"}})).unwrap();
        assert_eq!(route(&missing).unwrap_err(), "CORE_COMMAND_BODY_REQUIRED");
        let cancel:Request=serde_json::from_value(serde_json::json!({"operation":"job_execution_cancel","payload":{"job_id":"folder-text-safe","request_id":"folder-explicit-request"}})).unwrap();
        let (method, path, body) = route(&cancel).unwrap();
        assert_eq!(method, "POST");
        assert_eq!(
            path,
            "/api/v1/jobs/folder-text-safe/executions/folder-explicit-request/cancel"
        );
        assert!(body.is_none());
    }

    #[test]
    fn anchor_resolution_is_a_finite_read_with_two_bound_ids() {
        let request:Request=serde_json::from_value(serde_json::json!({"operation":"anchor_resolve","payload":{"source_id":"src-1","anchor_id":"anchor-1"}})).unwrap();
        let (method, path, body) = route(&request).unwrap();
        assert_eq!(method, "GET");
        assert_eq!(path, "/api/v1/sources/src-1/anchors/anchor-1/resolve");
        assert!(body.is_none());
        for key in ["source_id", "anchor_id"] {
            for invalid in ["../other", "x/y", "x?role=human", ""] {
                let mut payload = serde_json::json!({"source_id":"src-1","anchor_id":"anchor-1"});
                payload[key] = serde_json::json!(invalid);
                assert!(route(&Request {
                    operation: Operation::AnchorResolve,
                    payload
                })
                .is_err());
            }
        }
    }

    #[test]
    fn ui_working_state_uses_only_fixed_routes_and_bounded_bodies() {
        let read: Request =
            serde_json::from_value(serde_json::json!({"operation":"ui_state_read","payload":{}}))
                .unwrap();
        let (method, path, body) = route(&read).unwrap();
        assert_eq!(method, "GET");
        assert_eq!(path, "/api/v1/workspace/ui-state");
        assert!(body.is_none());
        for (operation, method, path) in [
            ("ui_state_write", "PUT", "/api/v1/workspace/ui-state"),
            (
                "ui_state_clear_job",
                "POST",
                "/api/v1/workspace/ui-state/clear-job",
            ),
            (
                "ui_state_clear_saved",
                "POST",
                "/api/v1/workspace/ui-state/clear-saved",
            ),
            (
                "ui_state_recover",
                "POST",
                "/api/v1/workspace/ui-state/recover",
            ),
        ] {
            let request: Request = serde_json::from_value(
                serde_json::json!({"operation":operation,"payload":{"body":{"state_revision":7}}}),
            )
            .unwrap();
            let routed = route(&request).unwrap();
            assert_eq!((routed.0, routed.1.as_str()), (method, path));
            assert_eq!(routed.2, Some(serde_json::json!({"state_revision":7})));
            assert_eq!(request_byte_limit(&request.operation), 1_100_000);
            for payload in [
                serde_json::json!({}),
                serde_json::json!({"body":[]}),
                serde_json::json!({"body":{},"url":"https://example.com"}),
            ] {
                let invalid: Request = serde_json::from_value(
                    serde_json::json!({"operation":operation,"payload":payload}),
                )
                .unwrap();
                assert!(route(&invalid).is_err());
            }
        }
        assert!(route(&Request {
            operation: Operation::UiStateRead,
            payload: serde_json::json!({"body":{}})
        })
        .is_err());
    }
}
