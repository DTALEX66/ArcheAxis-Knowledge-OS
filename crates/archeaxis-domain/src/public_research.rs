//! Frozen public-query receipts. Only the Core writer may persist retrievals.
//! No document fallback, model verdict or knowledge admission belongs here.
use base64::{Engine as _, engine::general_purpose::STANDARD};
use rusqlite::{Connection, OptionalExtension, params};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::Digest;

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Request {
    pub request_id: String,
    pub workspace_id: String,
    pub restore_epoch: String,
    pub query: String,
    pub families: Vec<String>,
    pub limit: u64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub community_site: Option<String>,
}
#[derive(Debug)]
pub enum Begin {
    Started,
    Cached(Value),
}
fn failure(reason: &str) -> String {
    reason.to_owned()
}
fn finite_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 128
        && id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"_-".contains(&b))
}
impl Request {
    pub fn validate(&self) -> Result<(), String> {
        if !finite_id(&self.request_id)
            || self.query.trim().is_empty()
            || self.query.len() > 4000
            || self.query.chars().count() > 1000
            || self.query.chars().any(char::is_control)
            || !(1..=3).contains(&self.limit)
            || !["academia", "stats"].contains(&self.community_site())
            || self.families.is_empty()
            || self.families.len() > 3
            || self.families.iter().enumerate().any(|(i, family)| {
                !["encyclopedia", "community", "research"].contains(&family.as_str())
                    || self.families[..i].contains(family)
            })
        {
            return Err(failure("public_query_bounds"));
        }
        Ok(())
    }
    pub fn worker_request(&self) -> Value {
        let mut value = json!({"schema":"public-research-worker/v1","query":self.query,"families":self.families,"limit":self.limit});
        if let Some(site) = &self.community_site {
            value["community_site"] = json!(site);
        }
        value
    }
    fn community_site(&self) -> &str {
        self.community_site.as_deref().unwrap_or("academia")
    }
}
pub fn assert_current(conn: &mut Connection, request: &Request) -> Result<(), String> {
    assert_workspace(conn, &request.workspace_id, &request.restore_epoch)
}
pub fn assert_workspace(
    conn: &mut Connection,
    workspace_id: &str,
    restore_epoch: &str,
) -> Result<(), String> {
    let state = crate::ui_state::read(conn).map_err(|_| failure("workspace_read_unavailable"))?;
    if state["workspace_id"].as_str() != Some(workspace_id)
        || state["restore_epoch"].as_str() != Some(restore_epoch)
        || state["recovery_requires_confirmation"] == true
    {
        return Err(failure("workspace_identity_or_restore_changed"));
    }
    Ok(())
}
fn envelope(request: &Request, state: &str) -> Value {
    let mut value = json!({"schema":"archeaxis.public-research-receipt/v1","request_id":request.request_id,
        "workspace_id":request.workspace_id,"restore_epoch":request.restore_epoch,
        "query":request.query,"families":request.families,"limit":request.limit,"state":state,
        "channels":null,"reason_code":null,"provider_stop_state":"unknown",
        "knowledge_admission":"not_executed"});
    if let Some(site) = &request.community_site {
        value["community_site"] = json!(site);
    }
    value
}
pub fn begin(conn: &mut Connection, request: &Request) -> Result<Begin, String> {
    request.validate()?;
    assert_current(conn, request)?;
    let frozen = serde_json::to_string(request).map_err(|_| failure("request_encoding_failed"))?;
    let tx = conn
        .transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)
        .map_err(|_| failure("public_query_write_unavailable"))?;
    let prior: Option<(String, String, Option<String>)> = tx
        .query_row(
            "SELECT request_json,state,receipt_json FROM public_research_runs WHERE request_id=?1",
            [&request.request_id],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
        )
        .optional()
        .map_err(|_| failure("public_query_read_unavailable"))?;
    if let Some((old, state, receipt)) = prior {
        if old != frozen {
            return Err(failure("public_query_identity_conflict"));
        }
        if state == "pending" {
            return Err(failure("public_query_prior_execution_unknown"));
        }
        let receipt = receipt.ok_or_else(|| failure("public_query_receipt_unconfirmed"))?;
        return serde_json::from_str(&receipt)
            .map(Begin::Cached)
            .map_err(|_| failure("public_query_receipt_invalid"));
    }
    tx.execute("INSERT INTO public_research_runs(request_id,workspace_id,restore_epoch,request_json,state) VALUES(?1,?2,?3,?4,'pending')",
        params![request.request_id,request.workspace_id,request.restore_epoch,frozen])
        .map_err(|_| failure("public_query_write_unavailable"))?;
    tx.commit()
        .map_err(|_| failure("public_query_write_unconfirmed"))?;
    Ok(Begin::Started)
}
pub fn read(conn: &Connection, request_id: &str) -> Result<Option<Value>, String> {
    if !finite_id(request_id) {
        return Err(failure("public_query_bounds"));
    }
    let row: Option<(String, Option<String>)> = conn
        .query_row(
            "SELECT request_json,receipt_json FROM public_research_runs WHERE request_id=?1",
            [request_id],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .optional()
        .map_err(|_| failure("public_query_read_unavailable"))?;
    row.map(|(frozen, receipt)| {
        if let Some(receipt) = receipt {
            return serde_json::from_str(&receipt)
                .map_err(|_| failure("public_query_receipt_invalid"));
        }
        let request: Request =
            serde_json::from_str(&frozen).map_err(|_| failure("public_query_request_invalid"))?;
        Ok(envelope(&request, "unknown"))
    })
    .transpose()
}
pub fn list(conn: &Connection) -> Result<Value, String> {
    let mut statement = conn
        .prepare("SELECT request_id FROM public_research_runs ORDER BY rowid DESC LIMIT 16")
        .map_err(|_| failure("public_query_read_unavailable"))?;
    let ids = statement
        .query_map([], |row| row.get::<_, String>(0))
        .map_err(|_| failure("public_query_read_unavailable"))?
        .collect::<rusqlite::Result<Vec<_>>>()
        .map_err(|_| failure("public_query_read_unavailable"))?;
    let receipts = ids
        .into_iter()
        .map(|id| read(conn, &id)?.ok_or_else(|| failure("public_query_not_found")))
        .collect::<Result<Vec<_>, _>>()?;
    Ok(
        json!({"schema":"archeaxis.public-research-journal/v1","receipts":receipts,"limit":16,"scope":"latest_requests_only"}),
    )
}
pub fn fail(
    conn: &mut Connection,
    request: &Request,
    reason: &str,
    cancelled: bool,
) -> Result<Value, String> {
    assert_current(conn, request)?;
    if !finite_id(reason) {
        return Err(failure("public_query_failure_invalid"));
    }
    let state = if cancelled { "cancelled" } else { "failed" };
    let mut receipt = envelope(request, state);
    receipt["reason_code"] = json!(reason);
    let frozen = serde_json::to_string(request).map_err(|_| failure("request_encoding_failed"))?;
    let changed=conn.execute("UPDATE public_research_runs SET state=?1,receipt_json=?2 WHERE request_id=?3 AND request_json=?4 AND state='pending'",
        params![state,receipt.to_string(),request.request_id,frozen]).map_err(|_|failure("public_query_write_unavailable"))?;
    if changed != 1 {
        return Err(failure("public_query_terminal_or_identity_changed"));
    }
    Ok(receipt)
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct WorkerResponse {
    schema: String,
    query: String,
    families: Vec<String>,
    channels: Vec<Channel>,
}
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Channel {
    family: String,
    provider: String,
    status: String,
    retrieved_at: String,
    request_url: String,
    #[serde(deserialize_with = "required_nullable")]
    retry_after_seconds: Option<u64>,
    #[serde(deserialize_with = "required_nullable")]
    error_code: Option<String>,
    #[serde(deserialize_with = "required_nullable")]
    raw_response_base64: Option<String>,
    hits: Vec<Hit>,
}
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Hit {
    id: String,
    family: String,
    provider: String,
    title: String,
    url: String,
    retrieved_at: String,
    content: String,
    excerpt: String,
    #[serde(deserialize_with = "required_nullable")]
    locator: Option<String>,
    #[serde(deserialize_with = "required_nullable")]
    license: Option<String>,
    free_access: String,
    #[serde(deserialize_with = "required_nullable")]
    upstream_revision: Option<String>,
    representation: String,
    truncated: bool,
}
// Option by itself treats a missing field as None. The worker wire contract
// requires every nullable key, and distinguishes an explicit null from omission.
fn required_nullable<'de, D, T>(deserializer: D) -> Result<Option<T>, D::Error>
where
    D: serde::Deserializer<'de>,
    T: Deserialize<'de>,
{
    Option::<T>::deserialize(deserializer)
}
fn provider(family: &str, name: &str) -> Option<&'static str> {
    match (family, name) {
        ("encyclopedia", "wikipedia") => Some("https://en.wikipedia.org/w/api.php?"),
        ("community", "stackexchange") => {
            Some("https://api.stackexchange.com/2.3/search/advanced?")
        }
        ("research", "openalex") => Some("https://api.openalex.org/works?"),
        ("research", "crossref") => Some("https://api.crossref.org/works?"),
        _ => None,
    }
}
fn bounded(text: &str, max: usize, multiline: bool) -> bool {
    text.len() <= max
        && !text
            .chars()
            .any(|c| c.is_control() && !(multiline && matches!(c, '\r' | '\n' | '\t')))
}

fn decimal(value: &str, zero: bool) -> bool {
    !value.is_empty()
        && value.bytes().all(|c| c.is_ascii_digit())
        && (value.len() == 1 || !value.starts_with('0'))
        && value.parse::<u64>().is_ok_and(|number| zero || number > 0)
}

/// Strict form decoding for the fixed API query strings. Malformed escapes,
/// non-UTF8, duplicate keys and undeclared parameters never acquire provenance.
fn form_decode(value: &str) -> Option<String> {
    fn digit(byte: u8) -> Option<u8> {
        match byte {
            b'0'..=b'9' => Some(byte - b'0'),
            b'a'..=b'f' => Some(byte - b'a' + 10),
            b'A'..=b'F' => Some(byte - b'A' + 10),
            _ => None,
        }
    }
    let mut decoded = Vec::with_capacity(value.len());
    let mut input = value.bytes();
    while let Some(byte) = input.next() {
        decoded.push(match byte {
            b'+' => b' ',
            b'%' => digit(input.next()?)?
                .checked_mul(16)?
                .checked_add(digit(input.next()?)?)?,
            other => other,
        });
    }
    String::from_utf8(decoded).ok()
}

fn request_url_matches(channel: &Channel, request: &Request, prefix: &str) -> bool {
    let Some(query) = channel.request_url.strip_prefix(prefix) else {
        return false;
    };
    if channel.request_url.contains('#') || !bounded(&channel.request_url, 12288, false) {
        return false;
    }
    let mut actual = std::collections::BTreeMap::new();
    for pair in query.split('&') {
        let Some((key, value)) = pair.split_once('=') else {
            return false;
        };
        let (Some(key), Some(value)) = (form_decode(key), form_decode(value)) else {
            return false;
        };
        if key.is_empty() || actual.insert(key, value).is_some() {
            return false;
        }
    }
    let limit = request.limit.to_string();
    let expected = match channel.family.as_str() {
        "encyclopedia" => vec![
            ("action", "query"),
            ("generator", "search"),
            ("gsrsearch", &request.query),
            ("gsrlimit", &limit),
            ("gsrnamespace", "0"),
            ("prop", "revisions"),
            ("rvprop", "ids|timestamp|content"),
            ("rvslots", "main"),
            ("rvsection", "0"),
            ("format", "json"),
            ("formatversion", "2"),
        ],
        "community" => vec![
            ("site", request.community_site()),
            ("q", &request.query),
            ("pagesize", &limit),
            ("sort", "relevance"),
            ("filter", "withbody"),
        ],
        "research" if channel.provider == "crossref" => vec![
            ("query.bibliographic", request.query.as_str()),
            ("rows", limit.as_str()),
            ("select", "DOI,title,URL,published"),
        ],
        "research" => vec![
            ("search", request.query.as_str()),
            ("per_page", limit.as_str()),
        ],
        _ => return false,
    }
    .into_iter()
    .map(|(key, value)| (key.to_owned(), value.to_owned()))
    .collect::<std::collections::BTreeMap<_, _>>();
    actual == expected
}

/// UTC datetime emitted by the worker, including real calendar/day validation.
/// Upstream timestamps have their own representation and are not rewritten.
fn utc_time(value: &str) -> bool {
    if !value.is_ascii() || value.len() < 20 || value.len() > 30 || !value.ends_with('Z') {
        return false;
    }
    let bytes = value.as_bytes();
    if bytes[4] != b'-'
        || bytes[7] != b'-'
        || bytes[10] != b'T'
        || bytes[13] != b':'
        || bytes[16] != b':'
    {
        return false;
    }
    let parse = |start: usize, end: usize| {
        value[start..end]
            .bytes()
            .all(|c| c.is_ascii_digit())
            .then(|| value[start..end].parse::<u32>().ok())
            .flatten()
    };
    let (Some(year), Some(month), Some(day), Some(hour), Some(minute), Some(second)) = (
        parse(0, 4),
        parse(5, 7),
        parse(8, 10),
        parse(11, 13),
        parse(14, 16),
        parse(17, 19),
    ) else {
        return false;
    };
    let leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
    let days = match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 => {
            if leap {
                29
            } else {
                28
            }
        }
        _ => return false,
    };
    if year == 0 || day == 0 || day > days || hour > 23 || minute > 59 || second > 59 {
        return false;
    }
    value.len() == 20
        || (bytes[19] == b'.'
            && value.len() > 21
            && bytes[20..value.len() - 1]
                .iter()
                .all(|c| c.is_ascii_digit()))
}

fn hit_identity(hit: &Hit, request: &Request) -> bool {
    match hit.family.as_str() {
        "encyclopedia" => {
            let Some((page, revision)) = hit
                .id
                .strip_prefix("wikipedia:en:")
                .and_then(|value| value.split_once(':'))
            else {
                return false;
            };
            decimal(page, false)
                && decimal(revision, false)
                && hit.upstream_revision.as_deref() == Some(revision)
                && hit.url == format!("https://en.wikipedia.org/w/index.php?oldid={revision}")
                && (hit.excerpt.is_empty()
                    || hit.locator.as_deref()
                        == Some(format!("pageid={page};revid={revision};section=0").as_str()))
        }
        "community" => {
            let site = request.community_site();
            let Some(id) = hit
                .id
                .strip_prefix(&format!("stackexchange:{site}:question:"))
            else {
                return false;
            };
            let prefix = format!("https://{site}.stackexchange.com/questions/{id}");
            let Some(suffix) = hit.url.strip_prefix(&prefix) else {
                return false;
            };
            let slug_ok = suffix.is_empty()
                || suffix
                    .strip_prefix('/')
                    .and_then(form_decode)
                    .is_some_and(|slug| {
                        slug.chars()
                            .all(|c| c.is_alphanumeric() || matches!(c, '-' | '_'))
                    });
            decimal(id, false)
                && slug_ok
                && hit.upstream_revision.as_ref().is_none_or(|revision| {
                    revision
                        .strip_prefix("last_edit_date:")
                        .is_some_and(|value| decimal(value, true))
                })
                && (hit.excerpt.is_empty()
                    || hit.locator.as_deref() == Some(format!("question_id={id};body").as_str()))
        }
        "research" if hit.provider == "crossref" => {
            let Some(doi) = hit
                .id
                .strip_prefix("https://doi.org/")
                .and_then(form_decode)
            else {
                return false;
            };
            let Some((registrant, suffix)) =
                doi.strip_prefix("10.").and_then(|v| v.split_once('/'))
            else {
                return false;
            };
            (4..=9).contains(&registrant.len())
                && registrant.bytes().all(|v| v.is_ascii_digit())
                && !suffix.is_empty()
                && !hit.id.contains(['?', '#'])
                && !doi.chars().any(|c| c.is_whitespace() || c.is_control())
                && hit.id == hit.url
                && hit.upstream_revision.is_none()
                && hit.license.is_none()
                && hit.content == "metadata"
        }
        "research" => {
            hit.id
                .strip_prefix("https://openalex.org/W")
                .is_some_and(|id| decimal(id, false))
                && hit.url == hit.id
                && (hit.excerpt.is_empty()
                    || hit.locator.as_deref()
                        == Some(format!("{}#/abstract_inverted_index", hit.id).as_str()))
        }
        _ => false,
    }
}

fn hit_representation(hit: &Hit) -> bool {
    if hit.content == "metadata" {
        return hit.representation == "metadata"
            && hit.excerpt.is_empty()
            && hit.locator.is_none()
            && !hit.truncated;
    }
    if hit.excerpt.is_empty() || hit.locator.is_none() {
        return false;
    }
    match hit.family.as_str() {
        "encyclopedia" => hit.representation == "wikitext" && hit.content == "excerpt",
        "community" => {
            hit.representation == "html_text"
                && ((hit.content == "full_text" && !hit.truncated)
                    || (hit.content == "excerpt" && hit.truncated))
        }
        "research" => hit.representation == "abstract" && hit.content == "excerpt",
        _ => false,
    }
}

fn validate_channel(channel: &Channel, request: &Request) -> Result<Option<Vec<u8>>, String> {
    let request_prefix =
        provider(&channel.family, &channel.provider).ok_or("public_provider_invalid")?;
    if !request_url_matches(channel, request, request_prefix)
        || !utc_time(&channel.retrieved_at)
        || !["complete", "limited", "failed", "offline", "unknown"]
            .contains(&channel.status.as_str())
        || channel.hits.len() > request.limit as usize
        || channel.retry_after_seconds.is_some_and(|v| v > 86400)
        || channel.error_code.as_ref().is_some_and(|v| !finite_id(v))
        || (!["complete", "limited"].contains(&channel.status.as_str()) && !channel.hits.is_empty())
        || (channel.status == "complete"
            && (channel.error_code.is_some() || channel.retry_after_seconds.is_some()))
        || (["limited", "failed", "offline"].contains(&channel.status.as_str())
            && channel.error_code.is_none())
    {
        return Err(failure("public_channel_invalid"));
    }
    let mut identities = std::collections::BTreeSet::new();
    for hit in &channel.hits {
        if hit.id.is_empty()
            || !bounded(&hit.id, 256, false)
            || !identities.insert(&hit.id)
            || hit.family != channel.family
            || hit.provider != channel.provider
            || !hit_identity(hit, request)
            || !bounded(&hit.url, 8192, false)
            || hit.title.trim().is_empty()
            || !bounded(&hit.title, 4096, true)
            || !bounded(&hit.excerpt, 16384, true)
            || hit.retrieved_at != channel.retrieved_at
            || !["metadata", "excerpt", "full_text"].contains(&hit.content.as_str())
            || !["wikitext", "html_text", "abstract", "metadata"]
                .contains(&hit.representation.as_str())
            || !["free", "unknown"].contains(&hit.free_access.as_str())
            || (hit.truncated && hit.content == "full_text")
            || !hit_representation(hit)
            || hit
                .license
                .as_ref()
                .is_some_and(|license| match hit.family.as_str() {
                    "encyclopedia" => license != "CC BY-SA 4.0",
                    "community" => !["CC BY-SA 2.5", "CC BY-SA 3.0", "CC BY-SA 4.0"]
                        .contains(&license.as_str()),
                    "research" => license != "CC0",
                    _ => true,
                })
            || hit
                .locator
                .as_ref()
                .is_some_and(|v| !bounded(v, 4096, false))
            || hit
                .license
                .as_ref()
                .is_some_and(|v| !bounded(v, 1024, false))
            || hit
                .upstream_revision
                .as_ref()
                .is_some_and(|v| !bounded(v, 1024, false))
        {
            return Err(failure("public_hit_invalid"));
        }
    }
    match &channel.raw_response_base64 {
        Some(encoded) => {
            if encoded.len() > 174764 {
                return Err(failure("public_raw_response_exceeds_bound"));
            }
            let raw = STANDARD
                .decode(encoded)
                .map_err(|_| failure("public_raw_response_invalid"))?;
            if raw.len() > 131072 {
                return Err(failure("public_raw_response_exceeds_bound"));
            }
            if raw.is_empty() && channel.status == "complete" {
                return Err(failure("public_raw_response_missing"));
            }
            Ok(Some(raw))
        }
        None if channel.status == "complete" || !channel.hits.is_empty() => {
            Err(failure("public_raw_response_missing"))
        }
        None => Ok(None),
    }
}
fn source_reference(outcome: crate::source::ImportOutcome) -> Value {
    let (source_id, sha256) = match outcome {
        crate::source::ImportOutcome::Imported { source_id, sha256 }
        | crate::source::ImportOutcome::Duplicate { source_id, sha256 } => (source_id, sha256),
    };
    json!({"kind":"source","source_id":source_id,"sha256":sha256})
}
fn fallback_allowed(channel: &Channel) -> bool {
    let code = channel.error_code.as_deref().unwrap_or("");
    (channel.status == "offline" && ["network_unavailable", "proxy_timeout"].contains(&code))
        || (channel.status == "limited" && code == "http_429")
        || (channel.status == "failed"
            && code.strip_prefix("http_").is_some_and(|v| {
                v.len() == 3
                    && v.parse::<u16>()
                        .is_ok_and(|status| (500..=599).contains(&status))
            }))
}
/// Validate a bounded worker response before a single writer transaction. Raw
/// HTTP entity bytes remain separate from every normalized content snapshot.
pub fn publish(conn: &mut Connection, request: &Request, value: Value) -> Result<Value, String> {
    request.validate()?;
    let response: WorkerResponse =
        serde_json::from_value(value).map_err(|_| failure("public_response_shape_invalid"))?;
    if response.schema != "public-research-worker/v1"
        || response.query != request.query
        || response.families != request.families
        || response.channels.len() < request.families.len()
        || response.channels.len()
            > request.families.len() + usize::from(request.families.iter().any(|f| f == "research"))
    {
        return Err(failure("public_response_identity_mismatch"));
    }
    let mut seen = std::collections::BTreeSet::new();
    let mut raw = Vec::new();
    for channel in &response.channels {
        if !request.families.contains(&channel.family)
            || !seen.insert((&channel.family, &channel.provider))
        {
            return Err(failure("public_channel_identity_mismatch"));
        }
        raw.push(validate_channel(channel, request)?);
    }
    for family in &request.families {
        let expected = match family.as_str() {
            "encyclopedia" => "wikipedia",
            "community" => "stackexchange",
            "research" => "openalex",
            _ => unreachable!(),
        };
        if !response
            .channels
            .iter()
            .any(|c| &c.family == family && c.provider == expected)
        {
            return Err(failure("public_channel_identity_mismatch"));
        }
    }
    if let Some(fallback) = response
        .channels
        .iter()
        .position(|c| c.provider == "crossref")
    {
        let Some(primary) = response
            .channels
            .iter()
            .position(|c| c.provider == "openalex")
        else {
            return Err(failure("public_fallback_identity_invalid"));
        };
        if fallback <= primary || !fallback_allowed(&response.channels[primary]) {
            return Err(failure("public_fallback_identity_invalid"));
        }
    }
    assert_current(conn, request)?;
    let frozen = serde_json::to_string(request).map_err(|_| failure("request_encoding_failed"))?;
    let tx = conn
        .transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)
        .map_err(|_| failure("public_query_write_unavailable"))?;
    let pending:bool=tx.query_row("SELECT EXISTS(SELECT 1 FROM public_research_runs WHERE request_id=?1 AND request_json=?2 AND state='pending')",
        params![request.request_id,frozen],|row|row.get(0)).map_err(|_|failure("public_query_read_unavailable"))?;
    if !pending {
        return Err(failure("public_query_terminal_or_identity_changed"));
    }
    let complete = response.channels.iter().all(|c| c.status == "complete");
    let any = response
        .channels
        .iter()
        .any(|c| matches!(c.status.as_str(), "complete" | "limited"));
    let state = if complete {
        "complete"
    } else if any {
        "partial"
    } else {
        "failed"
    };
    let mut receipt = envelope(request, state);
    let mut channels = Vec::new();
    for (channel, raw) in response.channels.into_iter().zip(raw) {
        let reference = if let Some(raw) = raw {
            let suffix = if raw.starts_with(&[0x1f, 0x8b]) {
                "json.gz"
            } else {
                "json"
            };
            let name = format!(
                "public-research-{}-{}-{}.{}",
                request.request_id, channel.family, channel.provider, suffix
            );
            source_reference(
                crate::source::import_source_tx(
                    &tx,
                    &raw,
                    &name,
                    Some(crate::source::OriginInfo {
                        kind: "url",
                        origin_ref: &channel.request_url,
                        original_name: Some(&name),
                        received_at: Some(&channel.retrieved_at),
                    }),
                )
                .map_err(|_| failure("public_raw_source_write_failed"))?,
            )
        } else {
            Value::Null
        };
        let mut row =
            serde_json::to_value(channel).map_err(|_| failure("public_channel_encoding_failed"))?;
        row.as_object_mut()
            .ok_or("public_channel_encoding_failed")?
            .remove("raw_response_base64");
        row["raw_source"] = reference;
        row["raw_representation"] = json!("http_entity_body_bytes");
        channels.push(row);
    }
    receipt["channels"] = json!(channels);
    let changed=tx.execute("UPDATE public_research_runs SET state=?1,receipt_json=?2 WHERE request_id=?3 AND request_json=?4 AND state='pending'",
        params![state,receipt.to_string(),request.request_id,frozen]).map_err(|_|failure("public_query_write_unavailable"))?;
    if changed != 1 {
        return Err(failure("public_query_terminal_or_identity_changed"));
    }
    tx.commit()
        .map_err(|_| failure("public_query_write_unconfirmed"))?;
    Ok(receipt)
}
/// Explicit local selection creates a labeled derived UTF-8 Source. It never
/// claims that normalized offsets point into the original API JSON/gzip bytes.
pub fn materialize(
    conn: &mut Connection,
    request_id: &str,
    family: &str,
    hit_id: &str,
) -> Result<Value, String> {
    let receipt = read(conn, request_id)?.ok_or("public_query_not_found")?;
    if !["complete", "partial"].contains(&receipt["state"].as_str().unwrap_or("")) {
        return Err(failure("public_query_not_selectable"));
    }
    let channel = receipt["channels"]
        .as_array()
        .and_then(|rows| {
            rows.iter().find(|c| {
                c["family"] == family
                    && c["hits"]
                        .as_array()
                        .is_some_and(|hits| hits.iter().any(|hit| hit["id"] == hit_id))
            })
        })
        .ok_or("public_channel_not_found")?;
    let hit = channel["hits"]
        .as_array()
        .and_then(|hits| hits.iter().find(|hit| hit["id"] == hit_id))
        .ok_or("public_hit_not_found")?;
    let hit: Hit =
        serde_json::from_value(hit.clone()).map_err(|_| failure("public_hit_invalid"))?;
    let raw = &channel["raw_source"];
    let raw_id = raw["source_id"]
        .as_str()
        .ok_or("public_raw_source_missing")?;
    let raw_sha = raw["sha256"].as_str().ok_or("public_raw_source_missing")?;
    let actual: Option<String> = conn
        .query_row(
            "SELECT sha256 FROM sources WHERE source_id=?1",
            [raw_id],
            |row| row.get(0),
        )
        .optional()
        .map_err(|_| failure("public_raw_source_read_failed"))?;
    if actual.as_deref() != Some(raw_sha) {
        return Err(failure("public_raw_source_identity_changed"));
    }
    archeaxis_store_sqlite::raw_objects::read_bounded(conn, raw_sha, 131072)
        .map_err(|_| failure("public_raw_source_bytes_unavailable"))?;
    let text = format!(
        "AAOS 派生内容快照（不是上游原始字节；未作专业核验）\n来源：{} / {}\n标题：{}\n地址：{}\n取得时间：{}\n原API来源：{}\n原API内容指纹：{}\n表示：{}\n内容范围：{}\n许可：{}\n截断：{}\n定位说明：{}\n\n内容：\n{}",
        hit.family,
        hit.provider,
        hit.title,
        hit.url,
        hit.retrieved_at,
        raw_id,
        raw_sha,
        hit.representation,
        hit.content,
        hit.license.as_deref().unwrap_or("未知"),
        hit.truncated,
        hit.locator.as_deref().unwrap_or("未提供"),
        hit.excerpt
    );
    let name = format!(
        "public-research-{}-{}.txt",
        request_id,
        hex::encode(sha2::Sha256::digest(
            format!("{family}:{hit_id}").as_bytes()
        ))
    );
    let origin = format!(
        "public-research:{raw_id}:{raw_sha}:{}:{}",
        hit.family, hit.id
    );
    let reference = source_reference(
        crate::source::import_source_with_origin(
            conn,
            text.as_bytes(),
            &name,
            None,
            Some(crate::source::OriginInfo {
                kind: "import",
                origin_ref: &origin,
                original_name: Some(&hit.title),
                received_at: Some(&hit.retrieved_at),
            }),
        )
        .map_err(|_| failure("public_derived_source_write_failed"))?,
    );
    Ok(
        json!({"schema":"archeaxis.public-research-selection/v1","request_id":request_id,"family":family,"hit_id":hit_id,
        "reference":reference,"raw_reference":raw,"title":hit.title,"representation":hit.representation,"truncated":hit.truncated,
        "note":format!("公开资料的派生内容快照：{}；原API来源/指纹及取得时间在快照中保留；未核验、未采用为知识。",hit.title),
        "knowledge_admission":"not_executed"}),
    )
}
