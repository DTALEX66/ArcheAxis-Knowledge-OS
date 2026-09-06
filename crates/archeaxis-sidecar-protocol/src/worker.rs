//! Bounded text-worker transport adapter for worker-protocol.schema.json.
//! This validates wire metadata, not output file contents, process exit or DB authority.
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

pub const MAX_FRAME_BYTES: usize = 1024 * 1024;
pub const TEXT_SCHEMAS: [&str; 3] = ["archeaxis.text/v1", "archeaxis.document-structure/v1", "archeaxis.loss-receipt/v1"];
type Result<T> = std::result::Result<T, &'static str>;

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Protocol {
    #[serde(deserialize_with="integer")] pub major: u64,
    #[serde(deserialize_with="integer")] pub min_minor: u64,
    #[serde(deserialize_with="integer")] pub max_minor: u64,
}
#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Worker { pub name: String, pub version: String }
#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Hello {
    pub schema: String, #[serde(rename="type")] pub message_type: String,
    pub protocol: Protocol, pub worker: Worker, pub capabilities: Vec<String>, pub schemas: Vec<String>,
}
#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Asset { pub uri: String, pub sha256: String, pub media_type: String }
#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Request {
    pub schema: String, #[serde(rename="type")] pub message_type: String,
    pub request_id: String, pub job_id: String, pub attempt: u64, pub protocol_minor: u32,
    pub capability: String, pub capability_version: String, pub deadline_ms: u64,
    pub inputs: Vec<Asset>, pub parameters: Map<String, Value>,
}
#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Output {
    pub kind: String, pub uri: String, pub sha256: String, pub media_type: String,
    #[serde(deserialize_with="integer")] pub byte_length: u64,
    pub schema: String, pub authority_effect: String,
}
#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WorkerError { pub code: String, pub message: String, pub retryable: bool }
#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Response {
    pub schema: String, #[serde(rename="type")] pub message_type: String,
    pub request_id: String, pub job_id: String,
    #[serde(deserialize_with="integer")] pub attempt: u64,
    #[serde(deserialize_with="integer")] pub protocol_minor: u64,
    pub status: String, pub outputs: Vec<Output>, pub measurements: Map<String, Value>,
    pub warnings: Vec<String>,
    #[serde(deserialize_with="required_error")] pub error: Option<WorkerError>,
}
fn required_error<'de, D: serde::Deserializer<'de>>(d: D) -> std::result::Result<Option<WorkerError>, D::Error> {
    Option::<WorkerError>::deserialize(d)
}
fn integer<'de, D: serde::Deserializer<'de>>(d: D) -> std::result::Result<u64, D::Error> {
    let n = Value::deserialize(d)?.as_f64().filter(|n| n.is_finite() && n.fract()==0.0
        && (0.0..=9_007_199_254_740_991.0).contains(n))
        .ok_or_else(|| serde::de::Error::custom("expected exact nonnegative JSON integer"))?;
    Ok(n as u64)
}
fn hash(value: &str) -> bool {
    value.len()==64 && value.bytes().all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
}
fn unique(values: &[String]) -> bool {
    values.iter().enumerate().all(|(i, value)| !values[..i].contains(value))
}
fn parse<T: serde::de::DeserializeOwned>(line: &str) -> Result<T> {
    if line.len()>MAX_FRAME_BYTES { return Err("worker frame exceeds byte limit"); }
    // Struct deserialization rejects duplicate/unknown protocol fields.
    serde_json::from_str(line).map_err(|_| "malformed worker frame")
}
impl Request {
    pub fn text(request_id: &str, job_id: &str, attempt: u64, sha256: &str, media_type: &str, deadline_ms: u64) -> Result<Self> {
        if request_id.trim().is_empty() || job_id.trim().is_empty() || attempt==0
            || attempt>9_007_199_254_740_991 || deadline_ms==0 || deadline_ms>9_007_199_254_740_991 || !hash(sha256) {
            return Err("invalid text task identity or budget");
        }
        Ok(Self {schema:"archeaxis.worker-request/v1".into(), message_type:"job_request".into(),
            request_id:request_id.into(), job_id:job_id.into(), attempt, protocol_minor:0,
            capability:"text.extract".into(), capability_version:"1".into(), deadline_ms,
            inputs:vec![Asset {uri:format!("job://input/{sha256}"),sha256:sha256.into(),media_type:media_type.into()}],
            parameters:Map::new()})
    }
}
pub fn decode_hello(line: &str) -> Result<Hello> {
    let hello: Hello = parse(line)?;
    if hello.schema!="archeaxis.worker-hello/v1" || hello.message_type!="hello"
        || hello.protocol.major!=1 || hello.protocol.min_minor!=0
        || hello.protocol.max_minor<hello.protocol.min_minor
        || hello.worker.name.trim().is_empty() || hello.worker.version.trim().is_empty()
        || !hello.capabilities.iter().any(|c| c=="text.extract")
        || !TEXT_SCHEMAS.iter().all(|schema| hello.schemas.iter().any(|s| s==schema))
        || !unique(&hello.capabilities) || !unique(&hello.schemas) {
        return Err("incompatible worker hello");
    }
    Ok(hello)
}
pub fn decode_response(line: &str, request: &Request) -> Result<Response> {
    let result: Response = parse(line)?;
    if result.schema!="archeaxis.worker-response/v1" || result.message_type!="job_result"
        || result.request_id!=request.request_id || result.job_id!=request.job_id
        || result.attempt!=request.attempt || result.attempt==0
        || result.protocol_minor!=u64::from(request.protocol_minor) {
        return Err("worker result identity mismatch");
    }
    match result.status.as_str() {
        "succeeded" => {
            if result.error.is_some() || result.outputs.len()!=3 { return Err("incomplete successful worker result"); }
            let kinds: Vec<String> = result.outputs.iter().map(|o|o.kind.clone()).collect();
            if !unique(&kinds) { return Err("duplicate worker output kind"); }
            for output in &result.outputs {
                let (schema, media) = match output.kind.as_str() {
                    "text" => (TEXT_SCHEMAS[0], "text/plain; charset=utf-8"),
                    "document_structure" => (TEXT_SCHEMAS[1], "application/json"),
                    "loss_report" => (TEXT_SCHEMAS[2], "application/json"),
                    _ => return Err("unsupported text worker output kind"),
                };
                if output.schema!=schema || output.media_type!=media || !hash(&output.sha256)
                    || output.uri!=format!("job://output/{}",output.sha256)
                    || output.authority_effect!="candidate_or_measurement_only" {
                    return Err("invalid worker output metadata");
                }
            }
        }
        "failed" | "rejected" => {
            let error = result.error.as_ref().ok_or("missing worker error")?;
            if !result.outputs.is_empty() || error.code.trim().is_empty() || error.message.trim().is_empty()
                || (result.status=="rejected" && error.retryable) { return Err("invalid failed worker result"); }
        }
        _ => return Err("unsupported worker status"),
    }
    Ok(result)
}
