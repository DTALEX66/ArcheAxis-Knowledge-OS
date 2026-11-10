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
    ProjectHandoffPreview,
    ProjectHandoffSnapshot,
    SourceImport,
    IngestBatchRegister,
    IngestBatchesList,
    IngestBatchGet,
    IngestMemberImport,
    IngestMemberEnqueue,
    IngestMemberRelationsApply,
    SourcesList,
    SourceGet,
    SourceJobs,
    SourceJobFormatQualification,
    SourceMembers,
    SourcePages,
    SourceOriginal,
    DocumentsList,
    DocumentCreate,
    DocumentGet,
    DocumentGraph,
    DocumentResearchReferences,
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
    DocumentPackageExport,
    DocumentPackageImport,
    DocumentExportSave,
    Search,
    SemanticSearch,
    KnowledgeGet,
    KnowledgeQualification,
    KnowledgeReview,
    CourseFromKnowledge,
    CourseGet,
    CourseList,
    CourseOpenmaicSceneCreate,
    CourseOpenmaicOutlineCreate,
    CourseOpenmaicOutlineGenerate,
    CourseOpenmaicInteractiveOutlineGenerate,
    CourseOpenmaicSceneGenerate,
    CourseOpenmaicPackageProjection,
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
    LearningDeeptutorQuestionTurn,
    LearningDeeptutorQuestionAccept,
    LearningDeeptutorTeachingFeedback,
    LearningDeeptutorPracticeImport,
    LearningDeeptutorPracticeGrade,
    LearningDeeptutorQuestionView,
    LearningProviderActivityCreate,
    LearningProviderActivityGet,
    LearningProviderAttemptStart,
    LearningProviderAttemptSubmit,
    LearningProviderAttemptCancel,
    CapabilitiesList,
    CapabilitySetEnabled,
    CapabilityTemplateChange,
    CapabilityTemplateRead,
    JobEnqueue,
    JobExecute,
    JobExecutionStatus,
    JobExecutionCancel,
    JobOutput,
    AssessmentCreate,
    AssessmentGet,
    LearningReference,
    MachineAnswer,
    MaterialQuestion,
    MaterialQuestionSubmit,
    MaterialContextPrepare,
    MaterialQuestionCancel,
    MaterialQuestionStatus,
    PublicResearchSearch,
    PublicResearchRead,
    PublicResearchList,
    PublicResearchCancel,
    PublicResearchMaterialize,
    OperationReadiness,
    CharacterMemoryGet,
    CharacterMemoryApply,
    CharacterMemoryContext,
    CharacterMemoryExport,
    ConfigurationPlansRead,
    ModelConfigurationGet,
    ModelConfigurationPut,
    ModelConfigurationResolve,
    ConversationSessionCreate,
    ConversationHistory,
    ConversationRequest,
    ConversationCancel,
    ConversationStatus,
    MachineConfiguration,
    MachineInventory,
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
    LayoutRead,
    LayoutWrite,
    LayoutRecover,
    UiStateRead,
    OperationFailureLogRead,
    OperationFailureLogAppend,
    OperationFailureLogClear,
    UiStateWrite,
    UiStateClearSaved,
    UiStateClearJob,
    UiStateClearMachine,
    UiStateMachineStatus,
    UiStateCancelMachine,
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
        SemanticSearch => {
            let fields = p
                .as_object()
                .ok_or("CORE_COMMAND_SEMANTIC_PAYLOAD_INVALID")?;
            let body = fields
                .get("body")
                .and_then(Value::as_object)
                .ok_or("CORE_COMMAND_SEMANTIC_PAYLOAD_INVALID")?;
            let q = body
                .get("q")
                .and_then(Value::as_str)
                .ok_or("CORE_COMMAND_SEMANTIC_PAYLOAD_INVALID")?;
            if fields.len() != 1
                || body.len() != 1
                || q.trim().is_empty()
                || q.chars().count() > 2048
            {
                return Err("CORE_COMMAND_SEMANTIC_PAYLOAD_INVALID".into());
            }
            (
                "POST",
                "/api/v1/search/semantic".into(),
                Some(serde_json::json!({"q":q})),
            )
        }
        ProjectHandoffPreview | ProjectHandoffSnapshot => {
            // 仅已有human会话的本地metadata预览；无URL、凭据或任意命令入口。
            if p.as_object().is_none_or(|fields| fields.len() != 1)
                || !p.get("body").is_some_and(Value::is_object)
            {
                return Err("CORE_COMMAND_PREVIEW_PAYLOAD_INVALID".into());
            }
            (
                "POST",
                if matches!(request.operation, ProjectHandoffSnapshot) {
                    "/api/v1/project-handoff/snapshot".into()
                } else {
                    "/api/v1/project-handoff/preview".into()
                },
                Some(body()?),
            )
        }
        WorkspaceRestorePreview => (
            "POST",
            "/api/v2/workspace/restore/preview".into(),
            Some(body()?),
        ),
        SourceImport => ("POST", "/api/v1/imports".into(), Some(body()?)),
        IngestMemberRelationsApply => {
            if p.as_object().is_none_or(|fields| {
                fields
                    .keys()
                    .any(|key| !["batch_id", "ordinal", "body"].contains(&key.as_str()))
            }) || !p.get("body").is_some_and(Value::is_object)
            {
                return Err("CORE_COMMAND_RELATION_PAYLOAD_INVALID".into());
            }
            let ordinal = p
                .get("ordinal")
                .and_then(Value::as_u64)
                .filter(|v| *v < 10000)
                .ok_or("CORE_COMMAND_MEMBER_ORDINAL_INVALID")?;
            (
                "POST",
                format!(
                    "/api/v1/ingest-batches/{}/members/{ordinal}/relations",
                    id(p, "batch_id")?
                ),
                Some(body()?),
            )
        }
        IngestBatchRegister | IngestMemberImport | IngestMemberEnqueue => {
            let register = matches!(request.operation, IngestBatchRegister);
            let keys = if register {
                vec!["body"]
            } else {
                vec!["batch_id", "body"]
            };
            if p.as_object()
                .is_none_or(|fields| fields.keys().any(|key| !keys.contains(&key.as_str())))
                || !p.get("body").is_some_and(Value::is_object)
            {
                return Err("CORE_COMMAND_BATCH_PAYLOAD_INVALID".into());
            }
            let path = if register {
                "/api/v1/ingest-batches".into()
            } else {
                format!(
                    "/api/v1/ingest-batches/{}/{}",
                    id(p, "batch_id")?,
                    if matches!(request.operation, IngestMemberImport) {
                        "imports"
                    } else {
                        "jobs"
                    }
                )
            };
            ("POST", path, Some(body()?))
        }
        IngestBatchesList | IngestBatchGet => {
            let listing = matches!(request.operation, IngestBatchesList);
            let keys = if listing {
                vec!["cursor", "limit"]
            } else {
                vec!["batch_id", "after_ordinal", "limit"]
            };
            if p.as_object()
                .is_none_or(|fields| fields.keys().any(|key| !keys.contains(&key.as_str())))
            {
                return Err("CORE_COMMAND_BATCH_PAYLOAD_INVALID".into());
            }
            let limit = p
                .get("limit")
                .map(|v| {
                    v.as_u64()
                        .filter(|n| (1..=200).contains(n))
                        .ok_or_else(|| "CORE_COMMAND_BATCH_LIMIT_INVALID".to_owned())
                })
                .transpose()?
                .unwrap_or(200);
            let mut path = if listing {
                "/api/v1/ingest-batches".into()
            } else {
                format!("/api/v1/ingest-batches/{}", id(p, "batch_id")?)
            };
            path.push_str(&format!("?limit={limit}"));
            if listing && p.get("cursor").is_some() {
                path.push_str(&format!("&cursor={}", id(p, "cursor")?));
            }
            if !listing {
                if let Some(value) = p.get("after_ordinal") {
                    let after = value
                        .as_u64()
                        .filter(|n| *n < 10000)
                        .ok_or("CORE_COMMAND_BATCH_CURSOR_INVALID")?;
                    path.push_str(&format!("&after_ordinal={after}"));
                }
            }
            ("GET", path, None)
        }
        SourcesList => ("GET", "/api/v1/sources".into(), None),
        SourceGet => (
            "GET",
            format!("/api/v1/sources/{}", id(p, "source_id")?),
            None,
        ),
        SourceJobs => (
            "GET",
            format!("/api/v1/sources/{}/jobs", id(p, "source_id")?),
            None,
        ),
        SourceJobFormatQualification => (
            "GET",
            format!(
                "/api/v1/sources/{}/jobs/{}/format-qualification",
                id(p, "source_id")?,
                id(p, "job_id")?
            ),
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
        DocumentResearchReferences => {
            let query = if let Some(value) = p.get("version") {
                let version = value
                    .as_u64()
                    .filter(|v| *v > 0 && *v <= i64::MAX as u64)
                    .ok_or("CORE_COMMAND_VERSION_INVALID")?;
                format!("?version={version}")
            } else {
                String::new()
            };
            (
                "GET",
                format!(
                    "/api/v1/documents/{}/research-references{query}",
                    reference_id(p, "document_id")?
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
        DocumentPackageExport => (
            "GET",
            format!("/api/v1/documents/{}/package", id(p, "document_id")?),
            None,
        ),
        DocumentPackageImport => (
            "POST",
            "/api/v1/document-packages/import".into(),
            Some(p.clone()),
        ),
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
        CourseOpenmaicSceneCreate
        | CourseOpenmaicOutlineCreate
        | CourseOpenmaicOutlineGenerate
        | CourseOpenmaicInteractiveOutlineGenerate
        | CourseOpenmaicSceneGenerate
        | CourseOpenmaicPackageProjection
        | LearningDeeptutorQuestionTurn
        | LearningDeeptutorQuestionAccept
        | LearningDeeptutorTeachingFeedback
        | LearningDeeptutorPracticeImport
        | LearningDeeptutorPracticeGrade
        | LearningDeeptutorQuestionView => {
            // Only fixed, human-session Core routes are exposed. The selected
            // body contains provider data and must not become a generic URL,
            // job payload, or transport log.
            if p.as_object().is_none_or(|fields| fields.len() != 1)
                || !p.get("body").is_some_and(Value::is_object)
            {
                return Err("CORE_COMMAND_PROVIDER_PAYLOAD_INVALID".into());
            }
            let path = match request.operation {
                CourseOpenmaicSceneCreate => "/api/v1/courses/openmaic/scenes",
                CourseOpenmaicOutlineCreate => "/api/v1/courses/openmaic/outlines",
                CourseOpenmaicOutlineGenerate => "/api/v1/courses/openmaic/outlines/generate",
                CourseOpenmaicInteractiveOutlineGenerate => {
                    "/api/v1/courses/openmaic/outlines/generate-interactive"
                }
                CourseOpenmaicSceneGenerate => "/api/v1/courses/openmaic/scenes/generate",
                CourseOpenmaicPackageProjection => "/api/v1/courses/openmaic/package-projection",
                LearningDeeptutorQuestionTurn => "/api/v1/learning/deeptutor/question-turn",
                LearningDeeptutorQuestionAccept => {
                    "/api/v1/learning/deeptutor/question-candidates/accept"
                }
                LearningDeeptutorTeachingFeedback => "/api/v1/learning/deeptutor/teaching-feedback",
                LearningDeeptutorPracticeImport => "/api/v1/learning/deeptutor/practice-import",
                LearningDeeptutorPracticeGrade => "/api/v1/learning/deeptutor/practice-grade",
                LearningDeeptutorQuestionView => "/api/v1/learning/deeptutor/question-view",
                _ => unreachable!(),
            };
            ("POST", path.into(), Some(body()?))
        }
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
        LearningProviderActivityCreate => (
            "POST",
            "/api/v1/learning/provider-activities".into(),
            Some(body()?),
        ),
        LearningProviderActivityGet => {
            let mut path = format!(
                "/api/v1/learning/provider-activities/{}",
                id(p, "activity_id")?
            );
            if p.get("after_attempt_id").is_some() {
                path.push_str(&format!("?after_attempt_id={}", id(p, "after_attempt_id")?));
            }
            ("GET", path, None)
        }
        LearningProviderAttemptStart => (
            "POST",
            format!(
                "/api/v1/learning/provider-activities/{}/attempts",
                id(p, "activity_id")?
            ),
            Some(body()?),
        ),
        LearningProviderAttemptSubmit | LearningProviderAttemptCancel => (
            "POST",
            format!(
                "/api/v1/learning/provider-activities/{}/attempts/{}/{}",
                id(p, "activity_id")?,
                id(p, "attempt_id")?,
                if matches!(request.operation, LearningProviderAttemptSubmit) {
                    "submit"
                } else {
                    "cancel"
                }
            ),
            Some(body()?),
        ),
        ConversationSessionCreate => (
            "POST",
            "/api/v1/conversation/sessions".into(),
            Some(body()?),
        ),
        ConversationHistory => ("POST", "/api/v1/conversation/history".into(), Some(body()?)),
        ConversationRequest => (
            "POST",
            "/api/v1/conversation/requests".into(),
            Some(body()?),
        ),
        ConversationCancel => ("POST", "/api/v1/conversation/cancel".into(), Some(body()?)),
        ConversationStatus => ("POST", "/api/v1/conversation/status".into(), Some(body()?)),
        MachineAnswer => ("POST", "/api/v1/machine/answers".into(), Some(body()?)),
        MaterialQuestion => ("POST", "/api/v1/material/questions".into(), Some(body()?)),
        MaterialQuestionSubmit => (
            "POST",
            "/api/v1/material/questions/submissions".into(),
            Some(body()?),
        ),
        PublicResearchSearch => (
            "POST",
            "/api/v1/research/public/search".into(),
            Some(body()?),
        ),
        PublicResearchRead => ("POST", "/api/v1/research/public/read".into(), Some(body()?)),
        PublicResearchList => ("POST", "/api/v1/research/public/list".into(), Some(body()?)),
        PublicResearchCancel => (
            "POST",
            "/api/v1/research/public/cancel".into(),
            Some(body()?),
        ),
        PublicResearchMaterialize => (
            "POST",
            "/api/v1/research/public/materialize".into(),
            Some(body()?),
        ),
        MaterialContextPrepare => ("POST", "/api/v1/material/context".into(), Some(body()?)),
        MaterialQuestionCancel => (
            "POST",
            "/api/v1/material/questions/cancel".into(),
            Some(body()?),
        ),
        MaterialQuestionStatus => (
            "POST",
            "/api/v1/material/questions/status".into(),
            Some(body()?),
        ),
        OperationReadiness => ("POST", "/api/v1/operation-readiness".into(), Some(body()?)),
        CharacterMemoryGet | CharacterMemoryContext | CharacterMemoryExport => {
            if !p.as_object().is_some_and(|v| v.is_empty()) {
                return Err("CORE_COMMAND_FIELDS_INVALID".into());
            }
            (
                "GET",
                match request.operation {
                    CharacterMemoryContext => "/api/v1/character-memory/context",
                    CharacterMemoryExport => "/api/v1/character-memory/export",
                    _ => "/api/v1/character-memory",
                }
                .into(),
                None,
            )
        }
        CharacterMemoryApply => ("POST", "/api/v1/character-memory".into(), Some(body()?)),
        ConfigurationPlansRead => {
            if !p.as_object().is_some_and(|v| v.is_empty()) {
                return Err("CORE_COMMAND_PAYLOAD_EMPTY_REQUIRED".into());
            }
            ("GET", "/api/v1/configuration-plans".into(), None)
        }
        ModelConfigurationGet => {
            if !p.as_object().is_some_and(|v| v.is_empty()) {
                return Err("CORE_COMMAND_PAYLOAD_EMPTY_REQUIRED".into());
            }
            ("GET", "/api/v1/model-configuration".into(), None)
        }
        ModelConfigurationPut => ("PUT", "/api/v1/model-configuration".into(), Some(body()?)),
        ModelConfigurationResolve => (
            "POST",
            "/api/v1/model-configuration/resolve".into(),
            Some(body()?),
        ),
        MachineConfiguration => {
            if !request
                .payload
                .as_object()
                .is_some_and(|value| value.is_empty())
            {
                return Err("CORE_COMMAND_PAYLOAD_EMPTY_REQUIRED".into());
            }
            ("GET", "/api/v1/machine/configuration".into(), None)
        }
        MachineInventory => {
            if !request
                .payload
                .as_object()
                .is_some_and(|value| value.is_empty())
            {
                return Err("CORE_COMMAND_PAYLOAD_EMPTY_REQUIRED".into());
            }
            (
                "POST",
                "/api/v1/machine/inventory".into(),
                Some(serde_json::json!({})),
            )
        }
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
        LayoutRead => {
            if !p
                .as_object()
                .is_some_and(|object| object.len() == 1 && object.contains_key("device_id"))
            {
                return Err("CORE_LAYOUT_PAYLOAD_INVALID".into());
            }
            let device = p["device_id"]
                .as_str()
                .ok_or("CORE_LAYOUT_DEVICE_INVALID")?;
            if device.is_empty()
                || device.len() > 64
                || !device
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
            {
                return Err("CORE_LAYOUT_DEVICE_INVALID".into());
            }
            (
                "GET",
                format!("/api/v1/workspace/layout?device_id={device}"),
                None,
            )
        }
        LayoutWrite | LayoutRecover => {
            if !p
                .as_object()
                .is_some_and(|object| object.len() == 1 && object.contains_key("body"))
            {
                return Err("CORE_LAYOUT_PAYLOAD_INVALID".into());
            }
            let value = body()?;
            if !value.is_object() {
                return Err("CORE_LAYOUT_PAYLOAD_INVALID".into());
            }
            if matches!(request.operation, LayoutWrite) {
                ("PUT", "/api/v1/workspace/layout".into(), Some(value))
            } else {
                (
                    "POST",
                    "/api/v1/workspace/layout/recover".into(),
                    Some(value),
                )
            }
        }
        OperationFailureLogRead | OperationFailureLogAppend | OperationFailureLogClear => {
            if !p
                .as_object()
                .is_some_and(|object| object.len() == 1 && object.contains_key("body"))
            {
                return Err("CORE_FAILURE_LOG_PAYLOAD_INVALID".into());
            }
            let value = body()?;
            if !value.is_object() {
                return Err("CORE_FAILURE_LOG_PAYLOAD_INVALID".into());
            }
            let action = match request.operation {
                OperationFailureLogRead => "read",
                OperationFailureLogAppend => "append",
                _ => "clear",
            };
            (
                "POST",
                format!("/api/v1/workspace/operation-failures/{action}"),
                Some(value),
            )
        }
        UiStateRead => {
            if !p.as_object().is_some_and(|object| object.is_empty()) {
                return Err("CORE_UI_STATE_PAYLOAD_INVALID".into());
            }
            ("GET", "/api/v1/workspace/ui-state".into(), None)
        }
        UiStateWrite | UiStateClearSaved | UiStateClearJob | UiStateClearMachine
        | UiStateMachineStatus | UiStateCancelMachine | UiStateRecover => {
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
                UiStateClearMachine => ("POST", "/api/v1/workspace/ui-state/clear-machine"),
                UiStateMachineStatus => ("POST", "/api/v1/workspace/ui-state/machine-status"),
                UiStateCancelMachine => ("POST", "/api/v1/workspace/ui-state/cancel-machine"),
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
        CapabilityTemplateRead => {
            if request
                .payload
                .as_object()
                .is_none_or(|object| !object.is_empty())
            {
                return Err("CORE_COMMAND_TEMPLATE_READ_EMPTY_PAYLOAD_REQUIRED".into());
            }
            ("GET", "/api/v1/capabilities/template.T3".into(), None)
        }
        CapabilityTemplateChange => {
            let object = request
                .payload
                .as_object()
                .ok_or("CORE_COMMAND_PAYLOAD_OBJECT_REQUIRED")?;
            if object.len() != 4
                || !["expected_epoch", "action", "version", "sha256"]
                    .iter()
                    .all(|key| object.contains_key(*key))
                || !object["expected_epoch"].as_i64().is_some_and(|v| v >= 0)
                || !object["version"].as_i64().is_some_and(|v| v > 0)
                || !object["action"].as_str().is_some_and(|v| {
                    matches!(
                        v,
                        "enable" | "disable" | "update" | "rollback" | "install" | "uninstall"
                    )
                })
                || !object["sha256"].as_str().is_some_and(|v| {
                    v.len() == 64
                        && v.bytes()
                            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
                })
            {
                return Err("CORE_COMMAND_TEMPLATE_CHANGE_INVALID".into());
            }
            (
                "PUT",
                "/api/v1/capabilities/template.T3/definition".into(),
                Some(request.payload.clone()),
            )
        }
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

#[cfg(test)]
mod provider_host_transport_tests {
    use super::*;
    use std::io::{Read, Write};
    use std::net::TcpListener;
    use std::time::{Duration, Instant};

    // An owned synthetic loopback fixture. It is not an actual Core or worker.
    fn serve_once(
        expected_path: &'static str,
        status: u16,
        response: &'static str,
    ) -> (u16, std::thread::JoinHandle<()>) {
        let listener = TcpListener::bind(("127.0.0.1", 0)).unwrap();
        listener.set_nonblocking(true).unwrap();
        let port = listener.local_addr().unwrap().port();
        let server = std::thread::spawn(move || {
            let deadline = Instant::now() + Duration::from_secs(5);
            let mut socket = loop {
                match listener.accept() {
                    Ok((socket, _)) => break socket,
                    Err(error)
                        if error.kind() == std::io::ErrorKind::WouldBlock
                            && Instant::now() < deadline =>
                    {
                        std::thread::sleep(Duration::from_millis(5))
                    }
                    Err(error) => panic!("synthetic provider fixture accept: {error}"),
                }
            };
            socket.set_nonblocking(false).unwrap();
            socket
                .set_read_timeout(Some(Duration::from_secs(5)))
                .unwrap();
            let mut wire = Vec::new();
            let mut chunk = [0_u8; 1024];
            loop {
                let count = socket.read(&mut chunk).unwrap();
                assert!(count > 0);
                wire.extend_from_slice(&chunk[..count]);
                assert!(wire.len() < 16_384);
                if let Some(end) = wire.windows(4).position(|bytes| bytes == b"\r\n\r\n") {
                    let headers = String::from_utf8(wire[..end].to_vec()).unwrap();
                    let lower = headers.to_ascii_lowercase();
                    let length = lower
                        .lines()
                        .find_map(|line| {
                            line.strip_prefix("content-length:")
                                .map(|value| value.trim().parse::<usize>().unwrap())
                        })
                        .unwrap();
                    if wire.len() < end + 4 + length {
                        continue;
                    }
                    assert!(headers.starts_with(&format!("POST {expected_path} HTTP/1.1")));
                    assert!(lower
                        .lines()
                        .any(|line| line == "x-archeaxis-launch-token: synthetic-host-token"));
                    let body: Value =
                        serde_json::from_slice(&wire[end + 4..end + 4 + length]).unwrap();
                    assert_eq!(body, serde_json::json!({"request_id":"synthetic"}));
                    break;
                }
            }
            write!(socket, "HTTP/1.1 {status} Synthetic\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                response.len(), response).unwrap();
        });
        (port, server)
    }

    #[test]
    fn provider_commands_use_the_owned_loopback_and_return_json() {
        for (operation, path) in [
            (
                "course_openmaic_outline_create",
                "/api/v1/courses/openmaic/outlines",
            ),
            (
                "course_openmaic_outline_generate",
                "/api/v1/courses/openmaic/outlines/generate",
            ),
            (
                "course_openmaic_interactive_outline_generate",
                "/api/v1/courses/openmaic/outlines/generate-interactive",
            ),
            (
                "course_openmaic_scene_generate",
                "/api/v1/courses/openmaic/scenes/generate",
            ),
            (
                "course_openmaic_package_projection",
                "/api/v1/courses/openmaic/package-projection",
            ),
            (
                "learning_deeptutor_question_turn",
                "/api/v1/learning/deeptutor/question-turn",
            ),
            (
                "learning_deeptutor_question_accept",
                "/api/v1/learning/deeptutor/question-candidates/accept",
            ),
            (
                "learning_deeptutor_teaching_feedback",
                "/api/v1/learning/deeptutor/teaching-feedback",
            ),
            (
                "learning_deeptutor_practice_import",
                "/api/v1/learning/deeptutor/practice-import",
            ),
            (
                "learning_deeptutor_practice_grade",
                "/api/v1/learning/deeptutor/practice-grade",
            ),
            (
                "learning_deeptutor_question_view",
                "/api/v1/learning/deeptutor/question-view",
            ),
            (
                "course_openmaic_scene_create",
                "/api/v1/courses/openmaic/scenes",
            ),
        ] {
            let (port, server) = serve_once(path, 200, r#"{"state":"synthetic"}"#);
            let request: Request = serde_json::from_value(serde_json::json!({
                "operation":operation, "payload":{"body":{"request_id":"synthetic"}}
            }))
            .unwrap();
            let reply = execute(port, "synthetic-host-token", request).unwrap();
            assert_eq!(reply.status, 200);
            assert_eq!(reply.body["state"], "synthetic");
            server.join().unwrap();
        }
    }

    #[test]
    fn provider_transport_does_not_echo_a_malformed_private_response() {
        for (operation, path) in [
            (
                "course_openmaic_outline_create",
                "/api/v1/courses/openmaic/outlines",
            ),
            (
                "course_openmaic_outline_generate",
                "/api/v1/courses/openmaic/outlines/generate",
            ),
            (
                "course_openmaic_interactive_outline_generate",
                "/api/v1/courses/openmaic/outlines/generate-interactive",
            ),
            (
                "course_openmaic_scene_generate",
                "/api/v1/courses/openmaic/scenes/generate",
            ),
            (
                "course_openmaic_package_projection",
                "/api/v1/courses/openmaic/package-projection",
            ),
            (
                "learning_deeptutor_question_turn",
                "/api/v1/learning/deeptutor/question-turn",
            ),
            (
                "learning_deeptutor_question_accept",
                "/api/v1/learning/deeptutor/question-candidates/accept",
            ),
            (
                "learning_deeptutor_teaching_feedback",
                "/api/v1/learning/deeptutor/teaching-feedback",
            ),
            (
                "learning_deeptutor_practice_import",
                "/api/v1/learning/deeptutor/practice-import",
            ),
            (
                "learning_deeptutor_practice_grade",
                "/api/v1/learning/deeptutor/practice-grade",
            ),
        ] {
            for response in [
                "SYNTHETIC_PRIVATE_INVALID",
                r#""SYNTHETIC_PRIVATE_INVALID""#,
                "null",
            ] {
                let (port, server) = serve_once(path, 200, response);
                let request: Request = serde_json::from_value(serde_json::json!({
                    "operation":operation,
                    "payload":{"body":{"request_id":"synthetic"}}
                }))
                .unwrap();
                let error = execute(port, "synthetic-host-token", request)
                    .err()
                    .unwrap();
                assert_eq!(error, "CORE_PROVIDER_RESPONSE_INVALID");
                assert!(!error.contains("SYNTHETIC_PRIVATE_INVALID"));
                server.join().unwrap();
            }
        }
    }

    #[test]
    fn provider_transport_keeps_http_error_status_without_echoing_the_body() {
        for (operation, path) in [
            (
                "learning_deeptutor_question_view",
                "/api/v1/learning/deeptutor/question-view",
            ),
            (
                "learning_deeptutor_question_turn",
                "/api/v1/learning/deeptutor/question-turn",
            ),
            (
                "learning_deeptutor_question_accept",
                "/api/v1/learning/deeptutor/question-candidates/accept",
            ),
            (
                "learning_deeptutor_teaching_feedback",
                "/api/v1/learning/deeptutor/teaching-feedback",
            ),
            (
                "course_openmaic_outline_create",
                "/api/v1/courses/openmaic/outlines",
            ),
            (
                "course_openmaic_outline_generate",
                "/api/v1/courses/openmaic/outlines/generate",
            ),
            (
                "course_openmaic_interactive_outline_generate",
                "/api/v1/courses/openmaic/outlines/generate-interactive",
            ),
            (
                "course_openmaic_scene_generate",
                "/api/v1/courses/openmaic/scenes/generate",
            ),
            (
                "course_openmaic_package_projection",
                "/api/v1/courses/openmaic/package-projection",
            ),
        ] {
            let (port, server) = serve_once(path, 422, "SYNTHETIC_PRIVATE_INVALID");
            let request: Request = serde_json::from_value(serde_json::json!({
                "operation":operation,
                "payload":{"body":{"request_id":"synthetic"}}
            }))
            .unwrap();
            let reply = execute(port, "synthetic-host-token", request).unwrap();
            assert_eq!(reply.status, 422);
            assert_eq!(
                reply.body,
                serde_json::json!({"code":"CORE_PROVIDER_RESPONSE_INVALID"})
            );
            assert!(!reply.body.to_string().contains("SYNTHETIC_PRIVATE_INVALID"));
            server.join().unwrap();
        }
    }
}

#[cfg(test)]
mod ingest_batch_routes {
    use super::*;
    use serde_json::json;
    fn request(operation: &str, payload: Value) -> Request {
        serde_json::from_value(json!({"operation":operation,"payload":payload})).unwrap()
    }
    #[test]
    fn original_relation_route_is_fixed_and_member_bounded() {
        let good = json!({"batch_id":"selected-batch","ordinal":1,"body":{"expected_version":2}});
        let routed = route(&request("ingest_member_relations_apply", good)).unwrap();
        assert_eq!(routed.0, "POST");
        assert_eq!(
            routed.1,
            "/api/v1/ingest-batches/selected-batch/members/1/relations"
        );
        for bad in [
            json!({"batch_id":"../other","ordinal":1,"body":{}}),
            json!({"batch_id":"ok","ordinal":10000,"body":{}}),
            json!({"batch_id":"ok","ordinal":-1,"body":{}}),
            json!({"batch_id":"ok","ordinal":1,"body":{},"url":"http://invalid"}),
        ] {
            assert!(route(&request("ingest_member_relations_apply", bad)).is_err());
        }
    }
    #[test]
    fn batch_routes_bind_members_and_reject_extra_or_unbounded_transport_inputs() {
        assert_eq!(
            route(&request(
                "ingest_batch_get",
                json!({"batch_id":"batch","after_ordinal":199,"limit":200})
            ))
            .unwrap(),
            (
                "GET",
                "/api/v1/ingest-batches/batch?limit=200&after_ordinal=199".into(),
                None
            )
        );
        for operation in ["ingest_member_import", "ingest_member_enqueue"] {
            let (_, path, body) = route(&request(
                operation,
                json!({"batch_id":"batch","body":{"ordinal":1}}),
            ))
            .unwrap();
            assert!(path.starts_with("/api/v1/ingest-batches/batch/"));
            assert_eq!(body.unwrap()["ordinal"], 1);
            for payload in [
                json!({"batch_id":"../other","body":{}}),
                json!({"batch_id":"batch","body":{},"url":"https://invalid"}),
            ] {
                assert!(route(&request(operation, payload)).is_err());
            }
        }
        for payload in [
            json!({"limit":201}),
            json!({"cursor":"a&limit=2"}),
            json!({"url":"http://invalid"}),
        ] {
            assert!(route(&request("ingest_batches_list", payload)).is_err());
        }
        assert_eq!(
            request_byte_limit(&Operation::IngestMemberImport),
            90 * 1024 * 1024
        );
    }
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
        Operation::MachineAnswer
        | Operation::MaterialQuestion
        | Operation::ConversationRequest
        | Operation::PublicResearchSearch => 135,
        Operation::MachineRetest => 135,
        // Core semantic ranking has a 90 second overall bound; retain transport margin.
        Operation::SemanticSearch => 135,
        Operation::WorkspaceBackup => 120,
        Operation::ProjectHandoffPreview | Operation::ProjectHandoffSnapshot => 3,
        // The Core caps a job deadline at 300 seconds and the reader polls for 310; real media
        // jobs run past both, so the transport must outlive them.
        Operation::JobExecute => 320,
        Operation::LearningDeeptutorPracticeImport => 95,
        Operation::LearningDeeptutorPracticeGrade => 95,
        // Capture (60 s), model (120 s), replay (60 s), and a transport margin.
        Operation::LearningDeeptutorQuestionTurn => 270,
        Operation::LearningDeeptutorTeachingFeedback => 95,
        // Outline generation uses capture, model, and replay. Scene generation
        // can additionally run a second model and several bounded worker stages.
        Operation::CourseOpenmaicOutlineGenerate
        | Operation::CourseOpenmaicInteractiveOutlineGenerate => 210,
        Operation::CourseOpenmaicSceneGenerate => 480,
        Operation::CourseOpenmaicOutlineCreate => 60,
        Operation::CourseFromKnowledge
        | Operation::CourseRender
        | Operation::CourseOpenmaicSceneCreate => 60,
        _ => 30,
    })
}

fn request_byte_limit(operation: &Operation) -> usize {
    if matches!(
        operation,
        Operation::CourseOpenmaicSceneCreate
            | Operation::CourseOpenmaicOutlineCreate
            | Operation::CourseOpenmaicOutlineGenerate
            | Operation::CourseOpenmaicInteractiveOutlineGenerate
            | Operation::CourseOpenmaicSceneGenerate
    ) {
        262_144
    } else if matches!(operation, Operation::LearningDeeptutorTeachingFeedback) {
        131_072
    } else if matches!(operation, Operation::LearningDeeptutorPracticeGrade) {
        // The Core grading route accepts one bounded answer submission; this is the
        // route's own 32,768-byte body limit, not the larger import envelope.
        32_768
    } else if matches!(
        operation,
        Operation::LearningDeeptutorPracticeImport
            | Operation::LearningDeeptutorQuestionView
            | Operation::LearningDeeptutorQuestionTurn
            | Operation::LearningDeeptutorQuestionAccept
            | Operation::CourseOpenmaicPackageProjection
    ) {
        65_536
    } else if matches!(
        operation,
        Operation::ProjectHandoffPreview | Operation::ProjectHandoffSnapshot
    ) {
        65_536
    } else if matches!(operation, Operation::DocumentPackageImport) {
        // 8 MiB originals can occupy 32 MiB as JSON byte arrays, plus bounded
        // package metadata and the import request envelope.
        40 * 1024 * 1024 + 65_536
    } else if matches!(
        operation,
        Operation::SourceImport | Operation::IngestMemberImport
    ) {
        90 * 1024 * 1024
    } else if matches!(
        operation,
        Operation::LayoutWrite
            | Operation::LayoutRecover
            | Operation::UiStateWrite
            | Operation::UiStateClearSaved
            | Operation::UiStateClearMachine
            | Operation::UiStateMachineStatus
            | Operation::UiStateCancelMachine
            | Operation::UiStateClearJob
            | Operation::UiStateRecover
    ) {
        1_100_000
    } else {
        8 * 1024 * 1024
    }
}
fn response_byte_limit(operation: &Operation) -> usize {
    if matches!(operation, Operation::ProjectHandoffPreview) {
        65_536
    } else if matches!(operation, Operation::SourceOriginal) {
        90 * 1024 * 1024
    } else if matches!(operation, Operation::DocumentPackageExport) {
        40 * 1024 * 1024
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
    let private_provider_response = matches!(
        request.operation,
        Operation::CourseOpenmaicSceneCreate
            | Operation::CourseOpenmaicOutlineCreate
            | Operation::CourseOpenmaicOutlineGenerate
            | Operation::CourseOpenmaicInteractiveOutlineGenerate
            | Operation::CourseOpenmaicSceneGenerate
            | Operation::CourseOpenmaicPackageProjection
            | Operation::LearningDeeptutorQuestionTurn
            | Operation::LearningDeeptutorQuestionAccept
            | Operation::LearningDeeptutorTeachingFeedback
            | Operation::LearningDeeptutorPracticeImport
            | Operation::LearningDeeptutorPracticeGrade
            | Operation::LearningDeeptutorQuestionView
    );
    let body = if bytes.is_empty() && !private_provider_response {
        Value::Null
    } else if private_provider_response {
        // Worker/source text may be sensitive. Never echo a malformed Core
        // response as a fallback message for these provider operations. Keep
        // the HTTP status for an error so callers can distinguish a 4xx/5xx.
        match serde_json::from_slice::<Value>(&bytes) {
            Ok(value) if value.is_object() => value,
            _ if status >= 400 => serde_json::json!({"code":"CORE_PROVIDER_RESPONSE_INVALID"}),
            _ => return Err("CORE_PROVIDER_RESPONSE_INVALID".into()),
        }
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
    fn provider_host_routes_are_fixed_and_require_one_object_body() {
        for (operation, expected) in [
            (
                "course_openmaic_outline_create",
                "/api/v1/courses/openmaic/outlines",
            ),
            (
                "course_openmaic_outline_generate",
                "/api/v1/courses/openmaic/outlines/generate",
            ),
            (
                "course_openmaic_interactive_outline_generate",
                "/api/v1/courses/openmaic/outlines/generate-interactive",
            ),
            (
                "course_openmaic_scene_generate",
                "/api/v1/courses/openmaic/scenes/generate",
            ),
            (
                "course_openmaic_package_projection",
                "/api/v1/courses/openmaic/package-projection",
            ),
            (
                "learning_deeptutor_question_turn",
                "/api/v1/learning/deeptutor/question-turn",
            ),
            (
                "learning_deeptutor_question_accept",
                "/api/v1/learning/deeptutor/question-candidates/accept",
            ),
            (
                "learning_deeptutor_teaching_feedback",
                "/api/v1/learning/deeptutor/teaching-feedback",
            ),
            (
                "learning_deeptutor_practice_import",
                "/api/v1/learning/deeptutor/practice-import",
            ),
            (
                "learning_deeptutor_practice_grade",
                "/api/v1/learning/deeptutor/practice-grade",
            ),
            (
                "learning_deeptutor_question_view",
                "/api/v1/learning/deeptutor/question-view",
            ),
            (
                "course_openmaic_scene_create",
                "/api/v1/courses/openmaic/scenes",
            ),
        ] {
            let request: Request = serde_json::from_value(serde_json::json!({
                "operation":operation, "payload":{"body":{"request_id":"synthetic"}}
            }))
            .unwrap();
            let (method, path, body) = route(&request).unwrap();
            assert_eq!((method, path.as_str()), ("POST", expected));
            assert_eq!(body.unwrap()["request_id"], "synthetic");
            for payload in [
                serde_json::json!({}),
                serde_json::json!({"body":null}),
                serde_json::json!({"body":[]}),
                serde_json::json!({"body":{}, "url":"http://127.0.0.1/private"}),
            ] {
                let request: Request = serde_json::from_value(serde_json::json!({
                    "operation":operation, "payload":payload
                }))
                .unwrap();
                assert_eq!(
                    route(&request).unwrap_err(),
                    "CORE_COMMAND_PROVIDER_PAYLOAD_INVALID"
                );
            }
        }
        assert_eq!(
            request_byte_limit(&Operation::LearningDeeptutorPracticeImport),
            65_536
        );
        assert_eq!(
            request_byte_limit(&Operation::LearningDeeptutorPracticeGrade),
            32_768
        );
        assert_eq!(
            request_byte_limit(&Operation::LearningDeeptutorQuestionView),
            65_536
        );
        assert_eq!(
            request_byte_limit(&Operation::CourseOpenmaicSceneCreate),
            262_144
        );
        for operation in [
            Operation::LearningDeeptutorQuestionTurn,
            Operation::LearningDeeptutorQuestionAccept,
            Operation::CourseOpenmaicPackageProjection,
        ] {
            assert_eq!(request_byte_limit(&operation), 65_536);
        }
        assert_eq!(
            request_byte_limit(&Operation::LearningDeeptutorTeachingFeedback),
            131_072
        );
        for operation in [
            Operation::CourseOpenmaicOutlineCreate,
            Operation::CourseOpenmaicOutlineGenerate,
            Operation::CourseOpenmaicInteractiveOutlineGenerate,
            Operation::CourseOpenmaicSceneGenerate,
        ] {
            assert_eq!(request_byte_limit(&operation), 262_144);
        }
        assert_eq!(
            transport_timeout(&Operation::LearningDeeptutorQuestionTurn).as_secs(),
            270
        );
        assert_eq!(
            transport_timeout(&Operation::LearningDeeptutorTeachingFeedback).as_secs(),
            95
        );
        assert_eq!(
            transport_timeout(&Operation::CourseOpenmaicOutlineCreate).as_secs(),
            60
        );
        assert_eq!(
            transport_timeout(&Operation::CourseOpenmaicOutlineGenerate).as_secs(),
            210
        );
        assert_eq!(
            transport_timeout(&Operation::CourseOpenmaicInteractiveOutlineGenerate).as_secs(),
            210
        );
        assert_eq!(
            transport_timeout(&Operation::CourseOpenmaicSceneGenerate).as_secs(),
            480
        );
        assert!(
            transport_timeout(&Operation::LearningDeeptutorPracticeImport)
                > std::time::Duration::from_secs(60)
        );
        assert!(
            transport_timeout(&Operation::LearningDeeptutorPracticeGrade)
                > std::time::Duration::from_secs(60)
        );
        assert!(
            transport_timeout(&Operation::CourseOpenmaicSceneCreate)
                > std::time::Duration::from_secs(30)
        );
    }
    #[test]
    fn provider_new_routes_reject_oversized_bodies_before_transport() {
        for (operation, limit) in [
            ("learning_deeptutor_question_turn", 65_536),
            ("learning_deeptutor_question_accept", 65_536),
            ("learning_deeptutor_teaching_feedback", 131_072),
            ("course_openmaic_outline_create", 262_144),
            ("course_openmaic_outline_generate", 262_144),
            ("course_openmaic_interactive_outline_generate", 262_144),
            ("course_openmaic_scene_generate", 262_144),
            ("course_openmaic_package_projection", 65_536),
        ] {
            let request: Request = serde_json::from_value(serde_json::json!({
                "operation": operation, "payload": {"body": {"input": "x".repeat(limit)}}
            }))
            .unwrap();
            assert_eq!(
                execute(0, "synthetic-host-token", request).err().as_deref(),
                Some("CORE_COMMAND_BODY_TOO_LARGE")
            );
        }
    }
    #[test]
    #[ignore = "requires an explicitly launched synthetic Core and private launch token"]
    fn provider_real_core_projection_and_route_admission() {
        let port: u16 = std::env::var("AAOS_SYNTHETIC_CORE_PORT")
            .expect("synthetic Core port required")
            .parse()
            .expect("valid synthetic Core port required");
        let token =
            std::env::var("AAOS_SYNTHETIC_CORE_TOKEN").expect("synthetic Core token required");
        let request: Request = serde_json::from_value(serde_json::json!({
            "operation":"course_openmaic_package_projection",
            "payload":{"body":{"document_ids":["synthetic_missing_scene"]}}
        }))
        .unwrap();
        let reply = execute(port, &token, request).expect("projection transport must succeed");
        assert_eq!(reply.status, 200);
        assert_eq!(
            reply.body["schema"],
            "archeaxis.openmaic-course-package-projection/v1"
        );
        assert_eq!(reply.body["scenes"][0]["status"], "missing");
        assert_eq!(reply.body["renderer_executed"], false);
        assert_eq!(reply.body["rendering_authorized"], false);

        for operation in [
            "learning_deeptutor_question_turn",
            "learning_deeptutor_question_accept",
            "learning_deeptutor_teaching_feedback",
            "course_openmaic_outline_create",
            "course_openmaic_outline_generate",
            "course_openmaic_interactive_outline_generate",
            "course_openmaic_scene_generate",
        ] {
            let request: Request = serde_json::from_value(serde_json::json!({
                "operation": operation, "payload": {"body": {}}
            }))
            .unwrap();
            let reply = execute(port, &token, request).expect("Core transport must succeed");
            assert!(
                matches!(reply.status, 400 | 422),
                "{operation}: unexpected status {}",
                reply.status
            );
        }
    }

    #[test]
    #[ignore = "requires a synthetic Core, explicit create/reopen phase, and private token"]
    fn learning_schedule_reset_real_core_transport() {
        use serde_json::json;
        let port: u16 = std::env::var("AAOS_SYNTHETIC_CORE_PORT")
            .unwrap()
            .parse()
            .unwrap();
        let token = std::env::var("AAOS_SYNTHETIC_CORE_TOKEN").unwrap();
        let phase = std::env::var("AAOS_SYNTHETIC_CORE_PHASE").unwrap();
        let identity_file = std::env::var_os("AAOS_SYNTHETIC_LEARNING_STATE").unwrap();
        let invoke = |operation: &str, payload: Value| {
            let request: Request = serde_json::from_value(json!({
                "operation": operation, "payload": payload
            }))
            .unwrap();
            execute(port, &token, request).expect("synthetic Core transport")
        };
        let item = "synthetic-host-reset";
        let assessed = std::env::var("AAOS_SYNTHETIC_ASSESSED").as_deref() == Ok("1");
        if phase == "create" {
            let create_binding = |knowledge: String| {
                let reference = invoke(
                    "learning_reference",
                    json!({
                        "item_key":item,"body":{"knowledge_id":knowledge}
                    }),
                );
                assert_eq!(reference.status, 201);
                let assessment = invoke(
                    "assessment_create",
                    json!({
                        "item_key":item,"body":{"knowledge_id":knowledge}
                    }),
                );
                assert_eq!(assessment.status, 201);
                (
                    assessment.body["assessment_id"].clone(),
                    assessment.body["knowledge_version"].clone(),
                )
            };
            let (binding, historical_binding) = if assessed {
                let previous =
                    create_binding(std::env::var("AAOS_SYNTHETIC_PREVIOUS_KNOWLEDGE_ID").unwrap());
                let prior = invoke(
                    "learning_review",
                    json!({"body":{
                        "item_key":item,"client_event_id":"host-previous-assessment","correct":true,"rating":3,
                        "now":"2026-08-31T00:00:00Z","assessment_id":previous.0,"knowledge_version":previous.1
                    }}),
                );
                assert_eq!(prior.status, 201);
                let current = create_binding(std::env::var("AAOS_SYNTHETIC_KNOWLEDGE_ID").unwrap());
                (Some(current), Some(previous))
            } else {
                (None, None)
            };
            let mut old_body = json!({"item_key":item,"client_event_id":"host-old","correct":true,
                "rating":3,"now":"2030-09-03T00:00:00Z"});
            if let Some((assessment_id, version)) = &binding {
                old_body["assessment_id"] = assessment_id.clone();
                old_body["knowledge_version"] = version.clone();
            }
            let old = invoke("learning_review", json!({"body":old_body}));
            assert_eq!(old.status, 201);
            assert_eq!(old.body["schedule_authority"], "fsrs");
            if let Some((assessment_id, version)) = &historical_binding {
                let historical = invoke(
                    "learning_review",
                    json!({"body":{
                        "item_key":item,"client_event_id":"host-late-previous-assessment","correct":true,"rating":3,
                        "now":"2026-09-01T00:00:00Z","assessment_id":assessment_id,"knowledge_version":version
                    }}),
                );
                assert_eq!(historical.status, 201);
            }
            let state = invoke("learning_state", json!({"item_key":item}));
            assert_eq!(state.status, 200);
            let latest = if assessed {
                &state.body["learner"]["assessment_progress"]["latest_review"]
            } else {
                &state.body["learner"]["latest_review"]
            };
            let old_id = latest["event_id"].as_i64().unwrap();
            assert_eq!(old.body["event_id"], old_id);
            let item_latest = state.body["learner"]["latest_review"]["event_id"]
                .as_i64()
                .unwrap();
            if assessed {
                assert!(item_latest > old_id);
            }
            let body = |expected| {
                let mut value = json!({
                    "item_key":item,"client_event_id":"host-reset","correct":true,"rating":3,
                    "now":"2026-09-03T00:00:00Z","schedule_reset":{
                        "mode":"start_new","reason":"Synthetic old time was mistyped",
                        "expected_latest_event_id":expected
                    }
                });
                if let Some((assessment_id, version)) = &binding {
                    value["assessment_id"] = assessment_id.clone();
                    value["knowledge_version"] = version.clone();
                }
                value
            };
            assert_eq!(
                invoke(
                    "learning_review",
                    json!({"body":body(if assessed {item_latest} else {old_id + 1})})
                )
                .status,
                409
            );
            let reset_body = body(old_id);
            let reset = invoke("learning_review", json!({"body":reset_body}));
            assert_eq!(reset.status, 201);
            assert_eq!(reset.body["schedule_authority"], "fsrs");
            assert_eq!(
                reset.body["schedule_recovery"]["excluded_through_event_id"],
                old_id
            );
            std::fs::write(
                identity_file,
                json!({"old_id":old_id,"reset_id":reset.body["event_id"],"reset_body":reset_body})
                    .to_string(),
            )
            .unwrap();
        } else if phase == "reopen" || phase == "restore" {
            let mut saved: Value =
                serde_json::from_slice(&std::fs::read(&identity_file).unwrap()).unwrap();
            let state = invoke("learning_state", json!({"item_key":item}));
            assert_eq!(state.status, 200);
            let latest = if assessed {
                &state.body["learner"]["assessment_progress"]["latest_review"]
            } else {
                &state.body["learner"]["latest_review"]
            };
            assert_eq!(latest["event_id"], saved["reset_id"]);
            assert_eq!(latest["schedule_recovery"]["state"], "reset");
            let replay = invoke("learning_review", json!({"body":saved["reset_body"]}));
            assert_eq!(replay.status, 200);
            assert_eq!(replay.body["duplicate"], true);
            assert_eq!(replay.body["event_id"], saved["reset_id"]);
            let history = invoke("learning_history", json!({"item_key":item}));
            assert_eq!(history.status, 200);
            assert_eq!(history.body["count"], if assessed { 4 } else { 2 });
            assert!(history.body["events"]
                .as_array()
                .unwrap()
                .iter()
                .any(|event| event["event_id"] == saved["old_id"]));
            if phase == "reopen" {
                let backup = invoke("workspace_backup", json!({}));
                assert_eq!(backup.status, 201);
                assert_eq!(backup.body["verified"], true);
                saved["backup_filename"] = backup.body["filename"].clone();
                saved["backup_sha256"] = backup.body["sha256"].clone();
                std::fs::write(identity_file, saved.to_string()).unwrap();
            }
        } else {
            panic!("unknown synthetic phase");
        }
    }

    #[test]
    #[ignore = "requires an explicitly launched synthetic Core and private launch token"]
    fn research_reference_real_core_transport() {
        let port: u16 = std::env::var("AAOS_SYNTHETIC_CORE_PORT")
            .unwrap()
            .parse()
            .unwrap();
        let token = std::env::var("AAOS_SYNTHETIC_CORE_TOKEN").unwrap();
        let invoke = |operation: &str, payload: Value| {
            let request: Request = serde_json::from_value(serde_json::json!({
                "operation": operation, "payload": payload
            }))
            .unwrap();
            execute(port, &token, request).expect("synthetic Core transport")
        };
        let material = invoke(
            "document_create",
            serde_json::json!({"body":{
                "title":"synthetic host material","editor_json":{"type":"doc","content":[]}
            }}),
        );
        assert_eq!(material.status, 201);
        let material_id = material.body["document_id"].as_str().unwrap();
        let reference = serde_json::json!({"kind":"document","document_id":material_id,"version":1,"block_id":null});
        let research = invoke(
            "document_create",
            serde_json::json!({"body":{
                "title":"synthetic host research","editor_json":{"type":"doc","content":[],"attrs":{
                    "archeaxis_research":{"schema":"archeaxis.research/v1","question":"synthetic",
                        "materials":[{"id":"source","note":"synthetic","reference":reference}],
                        "hypotheses":[],"methods":[],"experiments":[],"counterevidence":[],
                        "conclusions":[],"unresolved":[]}}}
            }}),
        );
        assert_eq!(research.status, 201);
        let research_id = research.body["document_id"].as_str().unwrap();
        let query = || {
            invoke(
                "document_research_references",
                serde_json::json!({
                    "document_id":research_id,"version":1
                }),
            )
        };
        let before = query();
        assert_eq!(before.status, 200);
        assert_eq!(
            before.body["references"][0]["object"]["version_relation"],
            "current"
        );
        assert_eq!(before.body["references"][0]["version_relation"], "current");
        let changed = invoke(
            "document_draft",
            serde_json::json!({"document_id":material_id,"body":{
                "expected_version":1,"editor_json":{"type":"doc","content":[
                    {"type":"paragraph","content":[{"type":"text","text":"synthetic revision"}]}]}
            }}),
        );
        assert_eq!(changed.status, 200);
        let after = query();
        assert_eq!(after.status, 200);
        assert_eq!(after.body["references"][0]["reference"], reference);
        assert_eq!(
            after.body["references"][0]["object"]["version_relation"],
            "historical"
        );
        assert_eq!(
            after.body["references"][0]["version_relation"],
            "historical"
        );
        assert_eq!(after.body["references"][0]["current_version"], 2);
        assert_eq!(after.body["document"], before.body["document"]);
    }
    #[test]
    #[ignore = "requires a synthetic Core, explicit create/reopen phase, and private token"]
    fn provider_real_core_teaching_feedback_roundtrip() {
        let port: u16 = std::env::var("AAOS_SYNTHETIC_CORE_PORT")
            .expect("synthetic Core port required")
            .parse()
            .expect("valid synthetic Core port required");
        let token =
            std::env::var("AAOS_SYNTHETIC_CORE_TOKEN").expect("synthetic Core token required");
        let phase = std::env::var("AAOS_SYNTHETIC_CORE_PHASE").expect("phase required");
        let identity_file = std::env::var_os("AAOS_SYNTHETIC_FEEDBACK_ID_FILE")
            .expect("synthetic identity file required");
        let body = serde_json::json!({
            "create_request_id":"synthetic_host_feedback_1",
            "session_id":"synthetic_session", "turn_id":"synthetic_turn",
            "profile":null,
            "current_message":"Please keep the examples short and concrete.",
            "objective_ids":["objective_basics"],
            "focus_objective_id":"objective_basics",
            "updates":[{"kind":"preference","op":"upsert","key":"examples",
                "text":"Keep examples short","basis":"learner_report",
                "evidence":"examples short"}],
            "include_history":false
        });
        let invoke = || {
            let request: Request = serde_json::from_value(serde_json::json!({
                "operation":"learning_deeptutor_teaching_feedback", "payload":{"body":body}
            }))
            .unwrap();
            execute(port, &token, request).expect("feedback transport must succeed")
        };
        match phase.as_str() {
            "create" => {
                let first = invoke();
                assert_eq!(first.status, 201);
                assert_eq!(first.body["worker_invoked"], true);
                assert_eq!(first.body["model_call"], "NOT_INVOKED");
                assert_eq!(first.body["human_review_required"], true);
                assert_eq!(first.body["rendering_authorized"], false);
                let document_id = first.body["document"]["document_id"]
                    .as_str()
                    .expect("candidate identity required");
                std::fs::write(&identity_file, document_id).expect("save synthetic identity");
                let duplicate = invoke();
                assert_eq!(duplicate.status, 200);
                assert_eq!(duplicate.body["worker_invoked"], false);
                assert_eq!(duplicate.body["document"]["document_id"], document_id);
            }
            "reopen" => {
                let document_id =
                    std::fs::read_to_string(&identity_file).expect("read synthetic identity");
                let duplicate = invoke();
                assert_eq!(duplicate.status, 200);
                assert_eq!(duplicate.body["worker_invoked"], false);
                assert_eq!(duplicate.body["document"]["document_id"], document_id);
                assert_eq!(duplicate.body["candidate_document_status"], "current");
            }
            _ => panic!("unknown synthetic Core phase"),
        }
    }
    #[test]
    #[ignore = "requires a synthetic Core, pinned Node for creation, and private token"]
    fn provider_real_core_openmaic_outline_roundtrip() {
        let port: u16 = std::env::var("AAOS_SYNTHETIC_CORE_PORT")
            .expect("synthetic Core port required")
            .parse()
            .expect("valid synthetic Core port required");
        let token =
            std::env::var("AAOS_SYNTHETIC_CORE_TOKEN").expect("synthetic Core token required");
        let phase = std::env::var("AAOS_SYNTHETIC_CORE_PHASE").expect("phase required");
        let identity_file = std::env::var_os("AAOS_SYNTHETIC_OUTLINE_ID_FILE")
            .expect("synthetic identity file required");
        let reply = serde_json::json!({
            "languageDirective":"Respond in Simplified Chinese.",
            "courseTitle":"Synthetic course",
            "outlines":[{"id":"outline_1","type":"slide","title":"Synthetic title",
                "description":"Synthetic description","keyPoints":["Synthetic key point"]}]
        });
        let body = serde_json::json!({
            "create_request_id":"synthetic_host_outline_1",
            "request":{"schema":"archeaxis.openmaic-outline-replay/v1",
                "request_id":"synthetic_outline_request",
                "requirement":"Synthetic requirement", "source_text":"Synthetic source",
                "reply":{"kind":"synthetic_response","value":reply.to_string()}}
        });
        let invoke = || {
            let request: Request = serde_json::from_value(serde_json::json!({
                "operation":"course_openmaic_outline_create", "payload":{"body":body}
            }))
            .unwrap();
            execute(port, &token, request).expect("outline transport must succeed")
        };
        match phase.as_str() {
            "create" => {
                let first = invoke();
                assert_eq!(first.status, 200);
                assert_eq!(first.body["worker_invoked"], true);
                assert_eq!(first.body["outline_count"], 1);
                assert_eq!(first.body["rendering_authorized"], false);
                assert_eq!(first.body["active_content_executed"], false);
                let document_id = first.body["document"]["document_id"]
                    .as_str()
                    .expect("candidate identity required");
                std::fs::write(&identity_file, document_id).expect("save synthetic identity");
                let duplicate = invoke();
                assert_eq!(duplicate.status, 200);
                assert_eq!(duplicate.body["worker_invoked"], false);
                assert_eq!(duplicate.body["document"]["document_id"], document_id);
            }
            "reopen" => {
                let document_id =
                    std::fs::read_to_string(&identity_file).expect("read synthetic identity");
                let duplicate = invoke();
                assert_eq!(duplicate.status, 200);
                assert_eq!(duplicate.body["worker_invoked"], false);
                assert_eq!(duplicate.body["document"]["document_id"], document_id);
                assert_eq!(duplicate.body["candidate_document_status"], "current");
            }
            _ => panic!("unknown synthetic Core phase"),
        }
    }
    #[test]
    #[ignore = "requires a synthetic Core, workers, loopback model, and explicit phase"]
    fn provider_real_core_deeptutor_synthetic_journey() {
        use serde_json::{json, Value};
        let port: u16 = std::env::var("AAOS_SYNTHETIC_CORE_PORT")
            .expect("synthetic Core port required")
            .parse()
            .expect("valid Core port");
        let token = std::env::var("AAOS_SYNTHETIC_CORE_TOKEN").expect("Core token required");
        let phase = std::env::var("AAOS_SYNTHETIC_CORE_PHASE").expect("phase required");
        let state_path = std::env::var_os("AAOS_SYNTHETIC_JOURNEY_STATE")
            .expect("synthetic state path required");
        let invoke = |operation: &str, payload: Value| {
            let request: Request = serde_json::from_value(json!({
                "operation":operation, "payload":payload
            }))
            .expect("valid host request");
            execute(port, &token, request).expect("host/Core transport must succeed")
        };
        let snapshot = |document: &Value| {
            json!({
                "document_id": document["document_id"], "version": document["version"],
                "content_sha256": document["content_sha256"]
            })
        };
        match phase.as_str() {
            "create" => {
                let material = invoke(
                    "document_create",
                    json!({"body":{
                        "title":"Synthetic host journey material",
                        "editor_json":{"type":"doc","content":[{"type":"paragraph",
                            "content":[{"type":"text","text":"SYNTHETIC: two plus two equals four."}]}]}
                    }}),
                );
                assert_eq!(material.status, 201, "material create");
                let grant = |title: &str, target: Value| {
                    let reply = invoke(
                        "document_create",
                        json!({"body":{
                            "title":title,"editor_json":{"type":"doc","content":[],"attrs":{
                                "archeaxis_provider_material_grant":{
                                    "schema":"archeaxis.provider-material-grant/v1", "purpose":"practice",
                                    "consumer":"deeptutor", "operations":["practice"], "material":target,
                                    "authorization_basis":"SYNTHETIC explicit human authorization",
                                    "expires_at":null,"state":"granted"}}}
                        }}),
                    );
                    assert_eq!(reply.status, 201, "synthetic grant create");
                    reply.body
                };
                let material_snapshot = snapshot(&material.body);
                let source_grant =
                    grant("Synthetic host material grant", material_snapshot.clone());
                let turn = json!({"create_request_id":"synthetic_host_turn",
                    "material":material_snapshot,"requirement":"One synthetic arithmetic question",
                    "model":null,"output_mode":"choice_json_schema"});
                let candidate = invoke("learning_deeptutor_question_turn", json!({"body":turn}));
                assert_eq!(candidate.status, 201, "question turn");
                assert_eq!(candidate.body["worker_invoked"], true);
                assert_eq!(
                    candidate.body["model_response_format"]["sha256"],
                    "753c5addda0233a21cb4aa40af0c9b6ff6dc52956d10178b8b465d1fcdb0b437"
                );
                let accept = json!({"create_request_id":"synthetic_host_accept",
                    "candidate":snapshot(&candidate.body["document"]),"correct_answer":"B",
                    "question_text":"SYNTHETIC fixture: select B.",
                    "explanation":"SYNTHETIC human fixture declares B."});
                let accepted = invoke("learning_deeptutor_question_accept", json!({"body":accept}));
                assert_eq!(accepted.status, 201, "synthetic human acceptance");
                let attrs = &accepted.body["document"]["editor_json"]["attrs"]
                    ["archeaxis_deeptutor_question_acceptance"];
                assert_eq!(attrs["answer_key_source"], "human_declared");
                assert_eq!(attrs["model_answer_used_as_key"], false);
                assert_eq!(attrs["explanation_source"], "human_supplied");
                let question = snapshot(&accepted.body["question_document"]);
                let question_grant = grant("Synthetic host question grant", question.clone());
                let activity = invoke(
                    "learning_provider_activity_create",
                    json!({"body":{
                        "activity_id":"synthetic_host_activity", "material":material_snapshot,
                        "provider":{"id":"deeptutor","version":"1.7.1"},
                        "question":{"question_id":accepted.body["question_view"]["question"]["question_id"],
                            "question_version":accepted.body["question_view"]["question_version"]},
                        "grant":snapshot(&source_grant)
                    }}),
                );
                assert_eq!(activity.status, 201, "activity create");
                let attempt = invoke(
                    "learning_provider_attempt_start",
                    json!({
                        "activity_id":"synthetic_host_activity","body":{"attempt_id":"synthetic_host_attempt"}
                    }),
                );
                assert_eq!(attempt.status, 201, "attempt start");
                let grade = json!({"activity_id":"synthetic_host_activity",
                    "attempt_id":"synthetic_host_attempt","request":{
                        "client_event_id":"synthetic_host_grade", "question_document":question,
                        "question_grant":snapshot(&question_grant),"answer":"B"}});
                let graded = invoke("learning_deeptutor_practice_grade", json!({"body":grade}));
                assert_eq!(graded.status, 201, "synthetic grade");
                assert_eq!(graded.body["provider_correct"], true);
                assert_eq!(graded.body["independent_mastery"], "not_established");
                let backup = invoke("workspace_backup", json!({}));
                assert_eq!(backup.status, 201, "synthetic workspace backup");
                assert_eq!(backup.body["verified"], true);
                let state = json!({"turn":turn,"accept":accept,"grade":grade,
                    "candidate_id":candidate.body["document"]["document_id"],
                    "accepted_id":accepted.body["document"]["document_id"],
                    "backup_filename":backup.body["filename"],"backup_sha256":backup.body["sha256"]});
                std::fs::write(&state_path, state.to_string()).expect("save synthetic state");
            }
            "reopen" | "restore" => {
                let state: Value = serde_json::from_slice(
                    &std::fs::read(&state_path).expect("read synthetic state"),
                )
                .expect("valid synthetic state");
                let candidate = invoke(
                    "learning_deeptutor_question_turn",
                    json!({"body":state["turn"]}),
                );
                assert_eq!(candidate.status, 200, "candidate replay");
                assert_eq!(candidate.body["worker_invoked"], false);
                assert_eq!(
                    candidate.body["document"]["document_id"],
                    state["candidate_id"]
                );
                let accepted = invoke(
                    "learning_deeptutor_question_accept",
                    json!({"body":state["accept"]}),
                );
                assert_eq!(accepted.status, 201, "acceptance replay");
                assert_eq!(accepted.body["duplicate"], true);
                assert_eq!(
                    accepted.body["document"]["document_id"],
                    state["accepted_id"]
                );
                let graded = invoke(
                    "learning_deeptutor_practice_grade",
                    json!({"body":state["grade"]}),
                );
                assert_eq!(graded.status, 200, "grade replay");
                assert_eq!(graded.body["duplicate"], true);
                assert_eq!(graded.body["provider_correct"], true);
                let history = invoke(
                    "learning_provider_activity_get",
                    json!({"activity_id":"synthetic_host_activity"}),
                );
                assert_eq!(history.status, 200, "activity readback");
                assert_eq!(
                    history.body["attempts"][0]["grade_disposition"]["state"],
                    "COMPLETED"
                );
                if phase == "restore" {
                    let mut new_turn = state["turn"].clone();
                    new_turn["create_request_id"] = json!("synthetic_host_restored_new_turn");
                    let refused =
                        invoke("learning_deeptutor_question_turn", json!({"body":new_turn}));
                    assert_eq!(refused.status, 409, "restored grants remain fenced");
                }
            }
            _ => panic!("unknown synthetic Core phase"),
        }
    }
    #[test]
    #[ignore = "requires synthetic Core, pinned Node, loopback model, and explicit phase"]
    fn provider_real_core_openmaic_synthetic_generation_journey() {
        use serde_json::{json, Value};
        let port: u16 = std::env::var("AAOS_SYNTHETIC_CORE_PORT")
            .expect("synthetic Core port required")
            .parse()
            .expect("valid Core port");
        let token = std::env::var("AAOS_SYNTHETIC_CORE_TOKEN").expect("Core token required");
        let phase = std::env::var("AAOS_SYNTHETIC_CORE_PHASE").expect("phase required");
        let state_path = std::env::var_os("AAOS_SYNTHETIC_JOURNEY_STATE")
            .expect("synthetic state path required");
        let invoke = |operation: &str, payload: Value| {
            let request: Request = serde_json::from_value(json!({
                "operation":operation,"payload":payload
            }))
            .expect("valid host request");
            execute(port, &token, request).expect("host/Core transport must succeed")
        };
        match phase.as_str() {
            "create" => {
                let source = invoke(
                    "document_create",
                    json!({"body":{
                        "title":"Synthetic interactive material",
                        "editor_json":{"type":"doc","content":[{"type":"paragraph",
                            "content":[{"type":"text","text":"SYNTHETIC diagram material"}]}]}
                    }}),
                );
                assert_eq!(source.status, 201, "source create");
                let outline_body = json!({"create_request_id":"synthetic_host_interactive_outline",
                    "requirement":"Create an interactive diagram for the synthetic material.",
                    "source_text":"SYNTHETIC diagram material","model":null});
                let outline = invoke(
                    "course_openmaic_interactive_outline_generate",
                    json!({"body":outline_body}),
                );
                assert_eq!(outline.status, 200, "interactive outline generate");
                assert_eq!(outline.body["worker_invoked"], true);
                let outlines = outline.body["outlines"]
                    .as_array()
                    .expect("outlines required");
                let selected = outlines
                    .iter()
                    .position(|entry| entry["type"] == "interactive")
                    .expect("an interactive outline is required for this journey");
                let widget_type = outlines[selected]["widgetType"]
                    .as_str()
                    .expect("widget required");
                assert_eq!(outline.body["rendering_authorized"], false);
                let scene_body = json!({"create_request_id":"synthetic_host_interactive_scene",
                    "outline_document_id":outline.body["document"]["document_id"],"outline_index":selected,
                    "source":{"document_id":source.body["document_id"],"version":source.body["version"],
                        "content_sha256":source.body["content_sha256"]},"model":null});
                let scene = invoke("course_openmaic_scene_generate", json!({"body":scene_body}));
                assert_eq!(scene.status, 200, "interactive scene generate");
                assert_eq!(scene.body["scene_route"], "interactive");
                assert_eq!(scene.body["widget_type"], widget_type);
                assert_eq!(scene.body["html_execution"], "NOT_PERFORMED");
                assert_eq!(scene.body["rendering_authorized"], false);
                assert_eq!(scene.body["render"]["report"]["playable"], false);
                let scene_id = scene.body["document"]["document_id"].clone();
                let projection = invoke(
                    "course_openmaic_package_projection",
                    json!({"body":{
                    "document_ids":[scene_id]}}),
                );
                assert_eq!(projection.status, 200, "package projection");
                assert_eq!(projection.body["scene_count"], 1);
                assert_eq!(projection.body["renderer_executed"], false);
                assert_eq!(projection.body["all_playable"], false);
                let state = json!({"outline_body":outline_body,"scene_body":scene_body,
                    "outline_id":outline.body["document"]["document_id"],"scene_id":scene_id});
                std::fs::write(&state_path, state.to_string()).expect("save synthetic state");
            }
            "reopen" => {
                let state: Value = serde_json::from_slice(
                    &std::fs::read(&state_path).expect("read synthetic state"),
                )
                .expect("valid synthetic state");
                let outline = invoke(
                    "course_openmaic_interactive_outline_generate",
                    json!({"body":state["outline_body"]}),
                );
                assert_eq!(outline.status, 200, "outline replay");
                assert_eq!(outline.body["worker_invoked"], false);
                assert_eq!(outline.body["document"]["document_id"], state["outline_id"]);
                let scene = invoke(
                    "course_openmaic_scene_generate",
                    json!({"body":state["scene_body"]}),
                );
                assert_eq!(scene.status, 200, "scene replay");
                assert_eq!(scene.body["worker_invoked"], false);
                assert_eq!(scene.body["document"]["document_id"], state["scene_id"]);
                let projection = invoke(
                    "course_openmaic_package_projection",
                    json!({"body":{
                    "document_ids":[state["scene_id"]]}}),
                );
                assert_eq!(projection.status, 200, "package readback");
                assert_eq!(projection.body["renderer_executed"], false);
                assert_eq!(projection.body["all_playable"], false);
            }
            _ => panic!("unknown synthetic Core phase"),
        }
    }
    #[test]
    fn provider_learning_routes_are_finite_and_history_cursor_is_bounded() {
        for (operation, path) in [
            (
                "learning_provider_activity_create",
                "/api/v1/learning/provider-activities",
            ),
            (
                "learning_provider_attempt_start",
                "/api/v1/learning/provider-activities/a/attempts",
            ),
            (
                "learning_provider_attempt_submit",
                "/api/v1/learning/provider-activities/a/attempts/b/submit",
            ),
            (
                "learning_provider_attempt_cancel",
                "/api/v1/learning/provider-activities/a/attempts/b/cancel",
            ),
        ] {
            let request: Request=serde_json::from_value(serde_json::json!({"operation":operation,"payload":{"activity_id":"a","attempt_id":"b","body":{}}})).unwrap();
            let (method, actual, body) = route(&request).unwrap();
            assert_eq!((method, actual.as_str()), ("POST", path));
            assert!(body.is_some());
        }
        let request: Request=serde_json::from_value(serde_json::json!({"operation":"learning_provider_activity_get","payload":{"activity_id":"a","after_attempt_id":"b"}})).unwrap();
        let (method, path, body) = route(&request).unwrap();
        assert_eq!(
            (method, path.as_str()),
            (
                "GET",
                "/api/v1/learning/provider-activities/a?after_attempt_id=b"
            )
        );
        assert!(body.is_none());
        for invalid in ["../private", "bad?x=1", "bad/other"] {
            let request: Request=serde_json::from_value(serde_json::json!({"operation":"learning_provider_activity_get","payload":{"activity_id":"a","after_attempt_id":invalid}})).unwrap();
            assert!(route(&request).is_err());
        }
    }
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
    fn template_lifecycle_is_fixed_data_only_route_with_state_guard() {
        let body = serde_json::json!({"expected_epoch":3,"action":"rollback","version":1,"sha256":"a".repeat(64)});
        let request: Request = serde_json::from_value(
            serde_json::json!({"operation":"capability_template_change","payload":body}),
        )
        .unwrap();
        let mapped = route(&request).unwrap();
        assert_eq!(
            mapped,
            (
                "PUT",
                "/api/v1/capabilities/template.T3/definition".into(),
                Some(body.clone())
            )
        );
        for (key, value) in [
            ("expected_epoch", serde_json::json!(-1)),
            ("version", serde_json::json!(1.5)),
            ("action", serde_json::json!("execute")),
            ("sha256", serde_json::json!("unknown")),
            ("url", serde_json::json!("https://example.invalid")),
        ] {
            let mut altered = body.clone();
            altered[key] = value;
            let request: Request = serde_json::from_value(
                serde_json::json!({"operation":"capability_template_change","payload":altered}),
            )
            .unwrap();
            assert!(route(&request).is_err());
        }
        let request: Request =
            serde_json::from_value(serde_json::json!({"operation":"capability_template_read"}))
                .unwrap();
        assert_eq!(
            route(&request).unwrap(),
            ("GET", "/api/v1/capabilities/template.T3".into(), None)
        );
        let request: Request = serde_json::from_value(
            serde_json::json!({"operation":"capability_template_read","payload":{"url":"x"}}),
        )
        .unwrap();
        assert!(route(&request).is_err());
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
    fn semantic_search_is_exact_query_only_post_with_finite_budget() {
        let request: Request = serde_json::from_value(serde_json::json!({
            "operation":"semantic_search","payload":{"body":{"q":"SYNTHETIC query"}}
        }))
        .unwrap();
        assert_eq!(
            route(&request).unwrap(),
            (
                "POST",
                "/api/v1/search/semantic".into(),
                Some(serde_json::json!({"q":"SYNTHETIC query"}))
            )
        );
        assert_eq!(
            transport_timeout(&request.operation),
            std::time::Duration::from_secs(135)
        );
        let unicode: Request = serde_json::from_value(serde_json::json!({"operation":"semantic_search","payload":{"body":{"q":"🛰".repeat(2048)}}})).unwrap();
        assert!(route(&unicode).is_ok());
    }

    #[test]
    fn semantic_search_refuses_extra_authority_and_invalid_queries() {
        for payload in [
            serde_json::json!({}),
            serde_json::json!({"body":null}),
            serde_json::json!({"body":[]}),
            serde_json::json!({"body":{"q":true}}),
            serde_json::json!({"body":{"q":" "}}),
            serde_json::json!({"body":{"q":"x".repeat(2049)}}),
            serde_json::json!({"body":{"q":"q","model":"other"}}),
            serde_json::json!({"body":{"q":"q","candidates":[]}}),
            serde_json::json!({"body":{"q":"q"},"endpoint":"https://example.invalid"}),
            serde_json::json!({"body":{"q":"q"},"token":"SYNTHETIC"}),
            serde_json::json!({"body":{"q":"q"},"method":"DELETE"}),
        ] {
            let request: Request = serde_json::from_value(
                serde_json::json!({"operation":"semantic_search","payload":payload}),
            )
            .unwrap();
            assert!(route(&request).is_err());
        }
        for operation in ["vault_links", "vault_members", "vault_links_record"] {
            assert!(
                serde_json::from_value::<Request>(serde_json::json!({"operation":operation}))
                    .is_err()
            );
        }
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
    fn format_qualification_is_a_bounded_read_with_both_validated_ids() {
        let request = serde_json::from_value::<Request>(serde_json::json!({
            "operation":"source_job_format_qualification", "payload":{"source_id":"src-safe","job_id":"job-safe.txt"}
        })).unwrap();
        let (method, path, body) = route(&request).unwrap();
        assert_eq!(method, "GET");
        assert_eq!(
            path,
            "/api/v1/sources/src-safe/jobs/job-safe.txt/format-qualification"
        );
        assert!(body.is_none());
        for payload in [
            serde_json::json!({"source_id":"src-safe"}),
            serde_json::json!({"source_id":"../other","job_id":"job-safe"}),
            serde_json::json!({"source_id":"src-safe","job_id":"../other"}),
        ] {
            let request = serde_json::from_value::<Request>(serde_json::json!({"operation":"source_job_format_qualification","payload":payload})).unwrap();
            assert!(route(&request).is_err());
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
        let inventory = serde_json::from_value::<Request>(
            serde_json::json!({"operation":"machine_inventory","payload":{}}),
        )
        .unwrap();
        assert_eq!(
            route(&inventory).unwrap(),
            (
                "POST",
                "/api/v1/machine/inventory".into(),
                Some(serde_json::json!({}))
            )
        );
        for payload in [
            serde_json::json!({"endpoint":"http://example.invalid"}),
            serde_json::json!({"context":"SYNTHETIC_PRIVATE"}),
        ] {
            let inventory = serde_json::from_value::<Request>(
                serde_json::json!({"operation":"machine_inventory","payload":payload}),
            )
            .unwrap();
            assert!(route(&inventory).is_err());
        }
        let config = serde_json::from_value::<Request>(
            serde_json::json!({"operation":"machine_configuration","payload":{}}),
        )
        .unwrap();
        assert_eq!(
            route(&config).unwrap(),
            ("GET", "/api/v1/machine/configuration".into(), None)
        );
        let config = serde_json::from_value::<Request>(serde_json::json!({"operation":"machine_configuration","payload":{"endpoint":"http://example.invalid"}})).unwrap();
        assert!(route(&config).is_err());
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
            request_byte_limit(&Operation::DocumentPackageImport),
            40 * 1024 * 1024 + 65_536
        );
        assert_eq!(
            response_byte_limit(&Operation::DocumentPackageExport),
            40 * 1024 * 1024
        );
        assert_eq!(
            request_byte_limit(&Operation::DocumentPackageExport),
            8 * 1024 * 1024
        );
        assert_eq!(
            response_byte_limit(&Operation::DocumentPackageImport),
            24 * 1024 * 1024
        );
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
        let research = route(&Request {
            operation: Operation::DocumentResearchReferences,
            payload: serde_json::json!({"document_id":"doc.real","version":3}),
        })
        .unwrap();
        assert_eq!(research.0, "GET");
        assert_eq!(
            research.1,
            "/api/v1/documents/doc.real/research-references?version=3"
        );
        assert!(research.2.is_none());
        for payload in [
            serde_json::json!({"document_id":"../escape"}),
            serde_json::json!({"document_id":"doc","version":0}),
            serde_json::json!({"document_id":"doc","version":18446744073709551615_u64}),
        ] {
            assert!(route(&Request {
                operation: Operation::DocumentResearchReferences,
                payload
            })
            .is_err());
        }
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
                let response = format!(
                    "HTTP/1.1 202 Accepted\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                    body.len(),
                    body
                );
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
                "ui_state_clear_machine",
                "POST",
                "/api/v1/workspace/ui-state/clear-machine",
            ),
            (
                "ui_state_machine_status",
                "POST",
                "/api/v1/workspace/ui-state/machine-status",
            ),
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
    #[test]
    fn layout_routes_are_finite_and_device_query_cannot_inject_transport() {
        let request: Request = serde_json::from_value(
            serde_json::json!({"operation":"layout_read","payload":{"device_id":"desktop_01"}}),
        )
        .unwrap();
        let (method, path, body) = route(&request).unwrap();
        assert_eq!(method, "GET");
        assert_eq!(path, "/api/v1/workspace/layout?device_id=desktop_01");
        assert!(body.is_none());
        for payload in [
            serde_json::json!({"device_id":"../other"}),
            serde_json::json!({"device_id":"a&actor=machine"}),
            serde_json::json!({"device_id":"desktop","url":"http://example.invalid"}),
        ] {
            let request: Request = serde_json::from_value(
                serde_json::json!({"operation":"layout_read","payload":payload}),
            )
            .unwrap();
            assert!(route(&request).is_err());
        }
        for (operation, method, path) in [
            ("layout_write", "PUT", "/api/v1/workspace/layout"),
            ("layout_recover", "POST", "/api/v1/workspace/layout/recover"),
        ] {
            let request: Request = serde_json::from_value(
                serde_json::json!({"operation":operation,"payload":{"body":{}}}),
            )
            .unwrap();
            let (actual, url, _) = route(&request).unwrap();
            assert_eq!(actual, method);
            assert_eq!(url, path);
            let request: Request=serde_json::from_value(serde_json::json!({"operation":operation,"payload":{"body":{},"token":"synthetic"}})).unwrap();
            assert!(route(&request).is_err());
        }
    }
    #[test]
    fn configuration_plans_are_input_free_gets_with_no_install_route() {
        let request: Request = serde_json::from_value(
            serde_json::json!({"operation":"configuration_plans_read","payload":{}}),
        )
        .unwrap();
        let actual = route(&request).unwrap();
        assert_eq!(actual, ("GET", "/api/v1/configuration-plans".into(), None));
        for payload in [
            serde_json::json!({"url":"https://external.invalid"}),
            serde_json::json!({"grant":"synthetic"}),
            serde_json::json!({"install":true}),
        ] {
            let invalid: Request = serde_json::from_value(
                serde_json::json!({"operation":"configuration_plans_read","payload":payload}),
            )
            .unwrap();
            assert!(route(&invalid).is_err());
        }
    }
}

#[cfg(test)]
mod material_async_bridge_tests {
    use super::*;
    #[test]
    fn material_async_submission_uses_a_fixed_route_without_extending_sync_budget() {
        let body = serde_json::json!({"execution_mode":"async","timeout_s":120});
        let request: Request = serde_json::from_value(
            serde_json::json!({"operation":"material_question_submit","payload":{"body":body}}),
        )
        .unwrap();
        let (method, path, actual) = route(&request).unwrap();
        assert_eq!(method, "POST");
        assert_eq!(path, "/api/v1/material/questions/submissions");
        assert_eq!(actual, Some(body));
        assert_eq!(
            transport_timeout(&Operation::MaterialQuestion),
            std::time::Duration::from_secs(135)
        );
        assert_eq!(
            transport_timeout(&Operation::MaterialQuestionSubmit),
            std::time::Duration::from_secs(30)
        );
    }
}

#[cfg(test)]
mod single_source_identity_route {
    use super::*;
    #[test]
    fn source_identity_route_is_fixed_and_rejects_traversal() {
        let request: Request = serde_json::from_value(
            serde_json::json!({"operation":"source_get","payload":{"source_id":"src_exact"}}),
        )
        .unwrap();
        let (method, path, body) = route(&request).unwrap();
        assert_eq!(method, "GET");
        assert_eq!(path, "/api/v1/sources/src_exact");
        assert_eq!(body, None);
        for value in ["../secret", "src/other", "https://example.invalid", ""] {
            let request: Request = serde_json::from_value(
                serde_json::json!({"operation":"source_get","payload":{"source_id":value}}),
            )
            .unwrap();
            assert!(route(&request).is_err());
        }
    }
}
