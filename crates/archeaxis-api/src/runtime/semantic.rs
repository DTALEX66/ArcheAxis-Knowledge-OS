//! Bounded query-time ranking of Core-owned knowledge; no vector index or caller-supplied corpus.
use super::*;
use std::{
    collections::HashSet,
    time::{Duration, Instant},
};
const SCHEMA: &str = "archeaxis.semantic-ranking/v1";
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Body {
    q: String,
}
fn error(status: StatusCode, reason: &str) -> Response {
    (status, Json(json!({"error":reason}))).into_response()
}

fn snapshot(conn: &rusqlite::Connection) -> rusqlite::Result<Vec<Value>> {
    conn.prepare("SELECT k.knowledge_id,k.body,k.receipt_hash,k.anchor_id,a.source_id,a.source_revision,s.sha256
        FROM knowledge k LEFT JOIN anchors a ON k.anchor_id=a.anchor_id LEFT JOIN sources s ON a.source_id=s.source_id
        WHERE k.status='accepted' AND NOT EXISTS(SELECT 1 FROM knowledge_supersedes x WHERE x.old_knowledge_id=k.knowledge_id)
        ORDER BY k.knowledge_id LIMIT 129")?.query_map([],|r| {
            let id:String=r.get(0)?;
            Ok(json!({"knowledge_id":id,"knowledge_version":id,"body":r.get::<_,String>(1)?,"status":"accepted",
                "receipt_hash":r.get::<_,String>(2)?,"anchor_id":r.get::<_,Option<String>>(3)?,
                "source_id":r.get::<_,Option<String>>(4)?,"source_revision":r.get::<_,Option<String>>(5)?,
                "current_source_revision":r.get::<_,Option<String>>(6)?}))
        })?.collect()
}
async fn current(runtime: &Runtime) -> Result<Vec<Value>, Response> {
    runtime
        .executor
        .store()
        .submit_wait(|conn| snapshot(conn))
        .await
        .map_err(|_| {
            error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "knowledge snapshot unavailable",
            )
        })?
        .map_err(|_| {
            error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "knowledge snapshot unavailable",
            )
        })
}

fn checked_rows(rows: &Value, batch: &[Value], rerank: bool) -> Result<Vec<Value>, &'static str> {
    let rows = rows.as_array().ok_or("worker rank must be an array")?;
    if rows.len() > batch.len() {
        return Err("worker rank exceeds submitted batch");
    }
    let mut seen = HashSet::new();
    let mut result = Vec::new();
    for row in rows {
        let id = row["knowledge_id"]
            .as_str()
            .ok_or("worker rank identity missing")?;
        let candidate = batch
            .iter()
            .find(|c| c["knowledge_id"] == id)
            .ok_or("worker returned an unsubmitted knowledge ID")?;
        if !seen.insert(id) || row["knowledge_version"] != candidate["knowledge_version"] {
            return Err("worker duplicate identity or revision mismatch");
        }
        let score = row["score"]
            .as_f64()
            .filter(|s| s.is_finite())
            .ok_or("worker score is not finite")?;
        if !(if rerank { 0.0..=1.0 } else { -1.0..=1.0 }).contains(&score) {
            return Err("worker score is outside protocol range");
        }
        let mut checked = json!({"knowledge_id":id,"knowledge_version":candidate["knowledge_version"],"score":score,
            "anchor_id":candidate["anchor_id"],"source_id":candidate["source_id"],"source_revision":candidate["source_revision"]});
        if rerank {
            let yes = row["yes_logprob"]
                .as_f64()
                .filter(|v| v.is_finite() && *v <= 0.0)
                .ok_or("yes logprob unavailable")?;
            let no = row["no_logprob"]
                .as_f64()
                .filter(|v| v.is_finite() && *v <= 0.0)
                .ok_or("no logprob unavailable")?;
            if row["reasoning_tokens"] != 0 {
                return Err("rerank position consumed by reasoning");
            }
            let difference = yes - no;
            let computed = if difference >= 0.0 {
                1.0 / (1.0 + (-difference).exp())
            } else {
                difference.exp() / (1.0 + difference.exp())
            };
            if (computed - score).abs() > 1e-10 {
                return Err("rerank score does not match yes/no logprobs");
            }
            checked["yes_logprob"] = yes.into();
            checked["no_logprob"] = no.into();
            checked["reasoning_tokens"] = 0.into();
        }
        result.push(checked);
    }
    Ok(result)
}
fn sort(rows: &mut [Value]) {
    rows.sort_by(|a, b| {
        b["score"]
            .as_f64()
            .unwrap()
            .total_cmp(&a["score"].as_f64().unwrap())
            .then_with(|| {
                a["knowledge_id"]
                    .as_str()
                    .unwrap()
                    .cmp(b["knowledge_id"].as_str().unwrap())
            })
    });
}
fn validate_batch(
    value: &Value,
    batch: &[Value],
) -> Result<(Vec<Value>, Vec<Value>, bool, bool), &'static str> {
    let doc = &value["document"];
    if doc["schema"] != SCHEMA
        || !matches!(
            doc["status"].as_str(),
            Some("AVAILABLE" | "PARTIAL" | "UNAVAILABLE")
        )
    {
        return Err("invalid semantic worker schema or outcome");
    }
    if doc["embedding"]["model"] != "text-embedding-qwen3-embedding-0.6b"
        || doc["reranker"]["model"] != "qwen3-reranker-0.6b"
    {
        return Err("semantic worker model identity mismatch");
    }
    let mut available = Vec::new();
    for leg in ["embedding", "reranker"] {
        match doc[leg]["status"].as_str() {
            Some("AVAILABLE") => available.push(true),
            Some("UNAVAILABLE") => available.push(false),
            _ => return Err("invalid semantic leg status"),
        }
    }
    let expected = if available[0] && available[1] {
        "AVAILABLE"
    } else if available[0] || available[1] {
        "PARTIAL"
    } else {
        "UNAVAILABLE"
    };
    if doc["status"] != expected
        || value["exit_code"] != if expected == "AVAILABLE" { 0 } else { 2 }
    {
        return Err("worker exit and completeness disagree");
    }
    let embedding = checked_rows(&doc["embedding_rank"], batch, false)?;
    if (available[0]
        && (embedding.len() != batch.len() || doc["embedding"]["protocol"] != "openai-embeddings"))
        || (!available[0] && !embedding.is_empty())
    {
        return Err("embedding completeness mismatch");
    }
    let rerank = checked_rows(&doc["reranker"]["rank"], batch, true)?;
    let partial = if doc["reranker"].get("partial_scores").is_some() {
        checked_rows(&doc["reranker"]["partial_scores"], batch, true)?
    } else {
        Vec::new()
    };
    if !partial.is_empty() && doc["reranker"]["protocol"] != "qwen-yes-no-first-token-logprobs/v1" {
        return Err("partial rerank protocol mismatch");
    }
    if available[1] {
        if rerank.len() != batch.len()
            || !partial.is_empty()
            || doc["reranker"]["protocol"] != "qwen-yes-no-first-token-logprobs/v1"
        {
            return Err("rerank completeness mismatch");
        }
    } else if !rerank.is_empty() {
        return Err("unavailable reranker supplied a complete rank");
    }
    Ok((
        embedding,
        if available[1] { rerank } else { partial },
        available[0],
        available[1],
    ))
}

pub(super) async fn search(State(runtime): State<Runtime>, Json(body): Json<Body>) -> Response {
    if body.q.trim().is_empty() || body.q.chars().count() > 2048 {
        return error(
            StatusCode::UNPROCESSABLE_ENTITY,
            "query must contain 1..2048 characters",
        );
    }
    match tokio::time::timeout(Duration::from_secs(90), run(runtime, body.q)).await {
        Ok(response) => response,
        Err(_) => error(
            StatusCode::GATEWAY_TIMEOUT,
            "semantic search exceeded overall 90 second deadline",
        ),
    }
}
async fn run(runtime: Runtime, q: String) -> Response {
    let deadline = Instant::now() + Duration::from_secs(90);
    let candidates = match current(&runtime).await {
        Ok(v) => v,
        Err(r) => return r,
    };
    if candidates.len() > 128 {
        return error(
            StatusCode::CONFLICT,
            "semantic search capacity exceeded: more than 128 eligible knowledge items; no partial corpus was ranked",
        );
    }
    if candidates.is_empty() {
        return Json(json!({"schema":"archeaxis.semantic-search/v1","q":q,"status":"EMPTY","complete":false,"candidate_count":0,
        "candidates":[],"embedding":{"complete":false,"rank":[]},"reranker":{"complete":false,"rank":[]},"index_persisted":false})).into_response();
    }
    if candidates.iter().any(|c| {
        c["body"]
            .as_str()
            .is_none_or(|b| b.trim().is_empty() || b.chars().count() > 8192)
    }) {
        return error(
            StatusCode::UNPROCESSABLE_ENTITY,
            "eligible knowledge body exceeds worker capacity; no text was truncated",
        );
    }
    if candidates.iter().any(|c| {
        !c["anchor_id"].is_null()
            && (c["source_revision"].is_null()
                || c["source_revision"] != c["current_source_revision"])
    }) {
        return error(
            StatusCode::CONFLICT,
            "eligible knowledge has a stale source binding",
        );
    }
    let mut embedding = Vec::new();
    let mut rerank = Vec::new();
    let mut batches = Vec::new();
    let mut embedding_complete = true;
    let mut rerank_complete = true;
    let mut provenance = None;
    let mut cursor = 0;
    while cursor < candidates.len() {
        let mut end = (cursor + 16).min(candidates.len());
        let request = loop {
            let request = json!({"schema":SCHEMA,"query":q,"candidates":candidates[cursor..end].iter().map(|c|json!({
                "knowledge_id":c["knowledge_id"],"knowledge_version":c["knowledge_version"],"body":c["body"],"status":"accepted"})).collect::<Vec<_>>()});
            // Python's validation serializes ensure_ascii=True; reserve separators too.
            let upper_bound = request
                .to_string()
                .chars()
                .map(|c| {
                    if c.is_ascii() {
                        1
                    } else if u32::from(c) > 0xffff {
                        12
                    } else {
                        6
                    }
                })
                .sum::<usize>()
                + 2048;
            if upper_bound <= 256000 {
                break request;
            }
            if end == cursor + 1 {
                return error(
                    StatusCode::UNPROCESSABLE_ENTITY,
                    "knowledge exceeds worker byte capacity; no text was truncated",
                );
            }
            end -= 1;
        };
        let batch = &candidates[cursor..end];
        let remaining = deadline.saturating_duration_since(Instant::now());
        if remaining.is_zero() {
            return error(
                StatusCode::GATEWAY_TIMEOUT,
                "semantic search deadline exceeded",
            );
        }
        let result = match runtime
            .executor
            .derived_json("search.semantic", request, remaining)
            .await
        {
            Ok(v) => v,
            Err(reason) => return error(StatusCode::SERVICE_UNAVAILABLE, &reason),
        };
        let (e, r, ec, rc) = match validate_batch(&result, batch) {
            Ok(v) => v,
            Err(reason) => return error(StatusCode::BAD_GATEWAY, reason),
        };
        let doc = &result["document"];
        let identity = json!([
            doc["engine_version"],
            doc["embedding"]["model"],
            doc["embedding"]["model_version"],
            doc["reranker"]["model"],
            doc["reranker"]["model_version"]
        ]);
        if provenance.as_ref().is_some_and(|p| p != &identity) {
            return error(
                StatusCode::BAD_GATEWAY,
                "semantic provider identity changed across batches",
            );
        }
        provenance = Some(identity);
        embedding.extend(e);
        rerank.extend(r);
        embedding_complete &= ec;
        rerank_complete &= rc;
        batches.push(json!({"candidate_ids":batch.iter().map(|c|c["knowledge_id"].clone()).collect::<Vec<_>>(),"worker_outcome":result}));
        cursor = end;
    }
    let latest = match current(&runtime).await {
        Ok(v) => v,
        Err(r) => return r,
    };
    if latest != candidates {
        return error(
            StatusCode::CONFLICT,
            "knowledge or source revisions changed during semantic ranking",
        );
    }
    sort(&mut embedding);
    sort(&mut rerank);
    let complete = embedding_complete && rerank_complete;
    let status = if complete {
        "AVAILABLE"
    } else if !embedding.is_empty() || !rerank.is_empty() {
        "PARTIAL"
    } else {
        "UNAVAILABLE"
    };
    Json(json!({"schema":"archeaxis.semantic-search/v1","q":q,"status":status,"complete":complete,"candidate_count":candidates.len(),
        "candidates":candidates,"embedding":{"complete":embedding_complete,"rank":embedding},"reranker":{"complete":rerank_complete,"rank":rerank},
        "batches":batches,"index_persisted":false,"ranking_basis":"query-time worker responses over Core-owned current accepted knowledge; no persistent vector index"})).into_response()
}
