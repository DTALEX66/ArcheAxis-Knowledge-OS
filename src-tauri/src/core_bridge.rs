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
    SourceOriginal,
    DocumentsList,
    DocumentCreate,
    DocumentGet,
    DocumentDraft,
    DocumentVersion,
    DocumentRestore,
    DocumentChecks,
    DocumentCheckRecord,
    JobsGet,
    JobQuality,
    AnchorsList,
    AnchorCreate,
    DocumentExport,
    DocumentExportSave,
    Search,
    KnowledgeGet,
    KnowledgeQualification,
    KnowledgeReview,
    LearningItems,
    LearningState,
    LearningHistory,
    LearningReview,
    CapabilitiesList,
    JobEnqueue,
    JobExecute,
    JobOutput,
    AssessmentCreate,
    AssessmentGet,
    LearningReference,
    MachineAnswer,
    MachineCorrection,
    MachineTaskGet,
    SourceJobTransform,
    KnowledgeFromTransform,
    WorkspaceBackup,
    WorkspaceBackups,
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
    if value.is_empty()
        || value.len() > 128
        || !value
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || c == b'-' || c == b'_')
    {
        return Err("CORE_COMMAND_ID_INVALID".into());
    }
    Ok(value.to_owned())
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
        SourceImport => ("POST", "/api/v1/imports".into(), Some(body()?)),
        SourcesList => ("GET", "/api/v1/sources".into(), None),
        SourceOriginal => (
            "GET",
            format!("/api/v1/sources/{}/original", id(p, "source_id")?),
            None,
        ),
        DocumentsList => ("GET", "/api/v1/documents".into(), None),
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
        DocumentGet => (
            "GET",
            format!("/api/v1/documents/{}", id(p, "document_id")?),
            None,
        ),
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
        LearningItems => ("GET", "/api/v1/learning/items".into(), None),
        LearningState => (
            "GET",
            format!("/api/v1/learning/items/{}/state", id(p, "item_key")?),
            None,
        ),
        LearningHistory => (
            "GET",
            format!("/api/v1/learning/events/{}", id(p, "item_key")?),
            None,
        ),
        LearningReview => ("POST", "/api/v1/learning/reviews".into(), Some(body()?)),
        MachineAnswer => ("POST", "/api/v1/machine/answers".into(), Some(body()?)),
        MachineCorrection => ("POST", "/api/v1/machine/corrections".into(), Some(body()?)),
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
        AssessmentCreate => (
            "POST",
            format!("/api/v1/learning/items/{}/assessment", id(p, "item_key")?),
            Some(body()?),
        ),
        AssessmentGet => (
            "GET",
            format!("/api/v1/learning/items/{}/assessment", id(p, "item_key")?),
            None,
        ),
        LearningReference => (
            "POST",
            format!("/api/v1/learning/items/{}/references", id(p, "item_key")?),
            Some(body()?),
        ),
        CapabilitiesList => ("GET", "/api/v1/capabilities".into(), None),
        JobEnqueue => ("POST", "/api/v1/jobs".into(), Some(body()?)),
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

pub fn execute(port: u16, token: &str, request: Request) -> Result<Reply, String> {
    let (method, path, body) = route(&request)?;
    if let Some(ref body) = body {
        if serde_json::to_vec(body)
            .map_err(|_| "CORE_COMMAND_BODY_INVALID")?
            .len()
            > 8 * 1024 * 1024
        {
            return Err("CORE_COMMAND_BODY_TOO_LARGE".into());
        }
    }
    let client = reqwest::blocking::Client::builder()
        .no_proxy()
        .redirect(reqwest::redirect::Policy::none())
        .timeout(std::time::Duration::from_secs(
            if matches!(request.operation, Operation::MachineAnswer) {
                135
            } else if matches!(request.operation, Operation::WorkspaceBackup) {
                120
            } else {
                30
            },
        ))
        .build()
        .map_err(|_| "CORE_TRANSPORT_UNAVAILABLE")?;
    let mut builder = client
        .request(
            method.parse().map_err(|_| "CORE_COMMAND_INVALID")?,
            format!("http://127.0.0.1:{port}{path}"),
        )
        .header("X-ArcheAxis-Launch-Token", token);
    if matches!(request.operation, Operation::JobExecute) {
        builder = builder.header("idempotency-key", id(&request.payload, "job_id")?);
    }
    if let Some(body) = body {
        builder = builder.json(&body);
    }
    let response = builder.send().map_err(|_| "CORE_TRANSPORT_FAILED")?;
    let status = response.status().as_u16();
    let mut bytes = Vec::new();
    response
        .take(24 * 1024 * 1024 + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| "CORE_RESPONSE_FAILED")?;
    if bytes.len() > 24 * 1024 * 1024 {
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
}
