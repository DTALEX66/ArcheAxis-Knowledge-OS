//! Owned text execution HTTP projection; never accepts executable paths over HTTP.
use archeaxis_application::executor::{Cancellation, Executor};
use axum::{
    Json, Router,
    extract::{Path, State},
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
    routing::{get, post, put},
};
use rusqlite::OptionalExtension;
use serde::Deserialize;
use serde_json::{Value, json};
use std::{collections::HashMap, sync::Arc};
use tokio::sync::Mutex;

mod colearning;
mod courses;
mod semantic;
use colearning::{machine_answer, record_correction, run_retest};

struct Active {
    request_id: String,
    cancel: Cancellation,
    faulted: bool,
}
#[derive(Clone)]
struct Runtime {
    executor: Executor,
    active: Arc<Mutex<HashMap<String, Active>>>,
    admission: Arc<Mutex<()>>,
    colearning_admission: Arc<Mutex<()>>,
}
pub fn router(executor: Executor) -> Router {
    let projections = crate::projections_base(executor.store().clone(), false);
    Router::new()
        .route(
            "/api/v1/documents/:document_id/checks/execute",
            post(execute_document_check),
        )
        .route("/api/v1/jobs/:job_id", get(status))
        .route("/api/v1/jobs/:job_id/executions", post(execute))
        .route(
            "/api/v1/jobs/:job_id/executions/:request_id/cancel",
            post(cancel),
        )
        .route("/api/v1/jobs/:job_id/outputs/:kind", get(output))
        // R7/G1 capability surface. It lives here rather than with the projections because it reads
        // the executor's registered routes, and the executor is this router's state.
        .route("/api/v1/capabilities", get(capabilities))
        .route("/api/v1/capabilities/:capability", get(capability))
        .route(
            "/api/v1/capabilities/:capability/enabled",
            put(set_capability_enabled),
        )
        // G4: a machine answer over accepted material. It lives with the runtime router because it
        // needs the executor, and the executor is this router's state; the projection builder holds
        // only the store and cannot reach a worker.
        .route("/api/v1/machine/answers", post(machine_answer))
        // G2: Ask with citations. It needs the store and the domain search matcher, both reachable
        // from the executor, and it answers over the same material the search route answers over.
        .route("/api/v1/ask", post(ask))
        .route("/api/v1/search/semantic", post(semantic::search))
        // G4: the human half of the co-learning loop. A person marks a real error in a machine answer
        // and gives the correction; both are stored, and the correction is a candidate that only
        // human review can promote.
        .route("/api/v1/machine/corrections", post(record_correction))
        // G4: run the task again and record it against the one it retests, which is what closes the
        // loop rather than leaving the correction as an unreferenced note.
        .route("/api/v1/machine/retests", post(run_retest))
        .route("/api/v1/courses", post(courses::create))
        .route(
            "/api/v1/courses/from-knowledge",
            post(courses::from_knowledge),
        )
        .route("/api/v1/courses/:id", get(courses::read))
        .route("/api/v1/courses/:id/render", post(courses::render))
        // G2: the vault link graph of one note. It takes the note's text rather than a path, because
        // the Core does not walk a directory and this must not be the place that starts to.
        .route("/api/v1/vault/links", post(vault_links))
        // G2: store the link graph of one note. Separated from the parse so a caller can inspect what
        // a note declares before deciding to keep it.
        .route("/api/v1/vault/links/record", post(vault_links_record))
        // G2: what each member of a vault is, so a walker can tell the user's notes from the
        // application's own configuration before it reads anything.
        .route("/api/v1/vault/members", post(vault_members))
        .with_state(Runtime {
            executor,
            active: Arc::new(Mutex::new(HashMap::new())),
            admission: Arc::new(Mutex::new(())),
            colearning_admission: Arc::new(Mutex::new(())),
        })
        .merge(projections)
}

async fn capabilities(State(runtime): State<Runtime>) -> Response {
    crate::capabilities::list(&runtime.executor).await
}

async fn capability(State(runtime): State<Runtime>, Path(name): Path<String>) -> Response {
    crate::capabilities::read(&runtime.executor, &name).await
}

async fn set_capability_enabled(
    State(runtime): State<Runtime>,
    Path(name): Path<String>,
    Json(body): Json<CapabilityEnabledBody>,
) -> Response {
    crate::capabilities::set_enabled(&runtime.executor, &name, body.enabled).await
}

/// G2: answer a question from accepted material, with the citations that make it checkable.
async fn ask(State(runtime): State<Runtime>, Json(body): Json<AskBody>) -> Response {
    if body.question.trim().is_empty() {
        return (
            StatusCode::UNPROCESSABLE_ENTITY,
            "a question is required; an answer to nothing is not an answer",
        )
            .into_response();
    }
    // Bounded so a projection cannot be turned into a full-table read by a caller, and floored at 1
    // so `limit: 0` asks for something rather than silently answering with nothing.
    let limit = body.limit.unwrap_or(20).clamp(1, 100);
    let question = body.question.clone();
    let asked = runtime
        .executor
        .store()
        .submit_wait(move |conn: &mut rusqlite::Connection| crate::ask::ask(conn, &question, limit))
        .await;
    match asked {
        Ok(Ok(document)) => Json(document).into_response(),
        Ok(Err(e)) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}

/// G2: classify a vault's members without reading any of them.
///
/// The gap this closes: nothing in the repository distinguished a person's notes from the vault's own
/// `.obsidian/` directory, so a directory walk had no way to tell that `workspace.json` - which
/// records a person's open panes, with **absolute paths on their disk** - is application state rather
/// than a claim about the world.
///
/// It is a pure function over names: it reads no file, touches no store, and cannot leak the contents
/// of what it classifies. An unsafe path is reported with the reason and is **not classified**, since
/// deciding what an out-of-tree path *is* would suggest it might be read.
async fn vault_members(Json(body): Json<VaultMembersBody>) -> Response {
    if body.members.is_empty() {
        return (
            StatusCode::UNPROCESSABLE_ENTITY,
            "members is required; classifying nothing answers nothing",
        )
            .into_response();
    }
    Json(archeaxis_domain::vault_members::classify_members(
        &body.members,
    ))
    .into_response()
}

/// G2: store one note's link graph.
///
/// This is the half `obsidian_vault_roundtrip.rs` said was missing: "no table stores a link or embed
/// relationship". The graph is now stored, **and the two things it still does not do are stated**:
/// the Core does not resolve a target by itself (the caller supplies the mapping) and it does not
/// walk a directory (it is handed one note's text at a time).
///
/// Dangling links are stored rather than dropped, because a link to a note that is not here is how a
/// reader learns the vault is incomplete.
async fn vault_links_record(
    State(runtime): State<Runtime>,
    Json(body): Json<VaultRecordBody>,
) -> Response {
    let knowledge_id = body.knowledge_id.clone();
    let markdown = body.markdown.clone();
    let resolutions = body.resolutions.clone();

    let written = runtime
        .executor
        .store()
        // One error layer, as `String`: a driver failure and "no such note" are both reasons to
        // hand back, and keeping them in one layer is what stops the call site having to unpack
        // three. The driver error is converted where it arises rather than by `?`.
        .submit_wait(
            move |conn: &mut rusqlite::Connection| -> Result<serde_json::Value, String> {
                // The declaring note has to exist, or its links would reference nothing.
                if !archeaxis_domain::vault::knowledge_exists(conn, &knowledge_id)
                    .map_err(|e| e.to_string())?
                {
                    // `Ok(Err(..))`: the outer error is the store driver's, so a missing note is a
                    // reason inside a successful transaction rather than a database failure.
                    return Err(format!("no knowledge item {knowledge_id}"));
                }
                let text = match &markdown {
                    Some(text) => text.clone(),
                    None => conn
                        .query_row(
                            "SELECT body FROM knowledge WHERE knowledge_id=?1",
                            [&knowledge_id],
                            |row| row.get::<_, String>(0),
                        )
                        .map_err(|e| e.to_string())?,
                };
                // A resolution the caller supplied is only honoured when the target really exists, so a
                // typo cannot manufacture a link to nothing.
                let mut checked: std::collections::HashMap<String, String> =
                    std::collections::HashMap::new();
                for (target, resolved) in &resolutions {
                    if archeaxis_domain::vault::knowledge_exists(conn, resolved).unwrap_or(false) {
                        checked.insert(target.clone(), resolved.clone());
                    }
                }
                let count =
                    archeaxis_domain::vault::record_links(conn, &knowledge_id, &text, |target| {
                        checked.get(target).cloned()
                    })
                    .map_err(|e| e.to_string())?;
                let stored = archeaxis_domain::vault::stored_links(conn, &knowledge_id)
                    .map_err(|e| e.to_string())?;
                let _ = count;
                Ok(stored)
            },
        )
        .await;

    // Three kinds of outcome, kept apart: the graph, a reason the note was not found, and a driver
    // failure. Flattening them was a mistake this route made twice while being written.
    let mut document: serde_json::Value = match written {
        Ok(Ok(document)) => document,
        Ok(Err(reason)) => return (StatusCode::NOT_FOUND, reason).into_response(),
        Err(e) => return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    };
    document["not_done_here"] = serde_json::json!([
        "resolving a target by itself: the caller supplies the name-to-item mapping, because only whoever walked the vault knows which note a link names",
        "walking a directory: the Core is handed one note's text at a time and reads no vault",
        "block reference definitions: a `^id` line is not recorded as a target",
    ]);
    Json(document).into_response()
}

/// G2: the Obsidian-style link graph of one note, as a projection.
///
/// `crates/archeaxis-archive/tests/obsidian_vault_roundtrip.rs` states that importing a vault writes
/// no anchors and that no table stores a link or embed relationship. This route reports what a note
/// declares; **persisting it is not done here**, and the response says so rather than leaving a
/// reader to assume the graph is now stored.
///
/// Text in, structure out: it reads no file, which is what keeps it inside the Core's stated
/// ingestion boundary.
async fn vault_links(State(runtime): State<Runtime>, Json(body): Json<VaultLinksBody>) -> Response {
    // Cloned because the id is used by the read closure and named again in the response.
    let requested = body.knowledge_id.clone();
    let markdown = match (body.markdown, requested.clone()) {
        (Some(text), _) => text,
        (None, Some(knowledge_id)) => {
            let wanted = knowledge_id.clone();
            let read = runtime
                .executor
                .store()
                .submit_wait(move |conn: &mut rusqlite::Connection| {
                    conn.query_row(
                        "SELECT body FROM knowledge WHERE knowledge_id=?1",
                        [&wanted],
                        |row| row.get::<_, String>(0),
                    )
                    .optional()
                })
                .await;
            match read {
                Ok(Ok(Some(text))) => text,
                Ok(Ok(None)) => {
                    return (
                        StatusCode::NOT_FOUND,
                        format!("no knowledge item {knowledge_id}"),
                    )
                        .into_response();
                }
                Ok(Err(e)) => {
                    return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response();
                }
                Err(e) => {
                    return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response();
                }
            }
        }
        (None, None) => {
            return (
                StatusCode::UNPROCESSABLE_ENTITY,
                "either markdown or knowledge_id is required; an empty graph answers nothing",
            )
                .into_response();
        }
    };
    let mut document = archeaxis_domain::vault::note_links(&markdown);
    document["knowledge_id"] = serde_json::json!(requested);
    Json(document).into_response()
}

fn error(status: u16, code: &str, message: &str) -> Response {
    (
        StatusCode::from_u16(status).unwrap(),
        Json(json!({"code":code,"message":message,"retryable":status==503})),
    )
        .into_response()
}
fn unavailable() -> Response {
    error(503, "AAK-WORKER-001", "execution is unavailable")
}
fn conflict() -> Response {
    error(409, "AAK-CON-002", "execution identity or payload conflict")
}
fn valid_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 200
        && id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"-_.".contains(&b))
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ExecuteBody {
    deadline_ms: u64,
    /// Ask for the recording to be split into bounded windows instead of decoded in one pass.
    ///
    /// `false` and an absent field mean the same thing — transcribe the input whole — so there is
    /// no third state to guess at. The window plan itself is not accepted from the caller: it is
    /// derived from the file's real duration inside the worker, so a request cannot describe a plan
    /// that drops audio while looking well-formed.
    #[serde(default)]
    split: bool,
}

/// `enabled` is a required boolean and unknown fields are refused.
///
/// `Option<bool>` would let `{}` mean "disable it", silently turning an empty body into the most
/// destructive of the two actions. Requiring the field means a caller has to say which it wants, and
/// `deny_unknown_fields` means a misspelled key is a `422` rather than a silent no-op.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct CapabilityEnabledBody {
    enabled: bool,
}

/// The body of a machine answer request.
///
/// `knowledge_id` is required and there is no free-text context field: an answer grounded in a string
/// the caller supplied would be unverifiable, and grounding is the whole point of this route.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct MachineAnswerBody {
    knowledge_id: String,
    question: String,
    #[serde(default)]
    max_tokens: Option<u64>,
    #[serde(default)]
    timeout_s: Option<u64>,
}

/// The body of an Ask request. `limit` is optional; the query is not.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct AskBody {
    question: String,
    #[serde(default)]
    limit: Option<i64>,
}

/// The body of a correction candidate.
///
/// Every field is required, including the answer the model gave and the specific error the human
/// found. A correction that omits what was wrong is not reviewable: a reviewer reading it later
/// would have to guess which part of the answer was the problem, and guessing is what review exists
/// to avoid.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct CorrectionBody {
    /// Optional for legacy clients; their tuple must still match a persisted answer.
    #[serde(default)]
    answer_id: Option<String>,
    /// The knowledge item the machine was answering from.
    knowledge_id: String,
    question: String,
    /// What the model answered, carried so the pair is reviewable as a pair.
    machine_answer: String,
    /// What the human says is correct instead.
    corrected_answer: String,
    /// What specifically was wrong. Required, because "it was wrong" is not a reviewable finding.
    error_note: String,
    /// Who found it. Review is a human act, so the default is the human principal.
    #[serde(default)]
    reviewer: Option<String>,
}

/// The body of a vault member classification.
///
/// The members are relative paths the caller enumerated. The Core does not walk the directory, which
/// is why this takes a list of names rather than a root.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct VaultMembersBody {
    members: Vec<String>,
}

/// The body of a vault link record.
///
/// `resolutions` is supplied by the caller because only whoever walked the vault knows which note a
/// link name refers to. The Core does not guess it and does not read a directory: handing over a
/// mapping is what keeps the walk outside the Core while still letting it store the graph. A name
/// absent from the map is stored as an unresolved link, which is a fact about the vault.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct VaultRecordBody {
    /// The knowledge item whose body declares the links.
    knowledge_id: String,
    /// Optional parser input; the item's own body is used when this is absent.
    #[serde(default)]
    markdown: Option<String>,
    /// target-as-written -> knowledge item, for the targets the caller could resolve.
    #[serde(default)]
    resolutions: std::collections::HashMap<String, String>,
}

/// The body of a vault link parse.
///
/// Either `markdown` or `knowledge_id` is required, and giving neither is refused rather than
/// answered with an empty graph. The Core does not read a directory: a vault is walked outside it and
/// each note's text is handed over, which is why this takes text rather than a path.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct VaultLinksBody {
    #[serde(default)]
    markdown: Option<String>,
    #[serde(default)]
    knowledge_id: Option<String>,
}

/// The body of a retest: run the machine task again and record it against the one it retests.
///
/// `retest_of` is required. A retest that does not name what it retests is just another task, and
/// "did the correction help" would have no answer.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RetestBody {
    /// The machine task being retested.
    retest_of: String,
    /// The knowledge the retest answers from - usually the corrected item, which is why it is named
    /// separately from whatever the original task ran against.
    knowledge_id: String,
    /// The question to put again.
    question: String,
    #[serde(default)]
    max_tokens: Option<u64>,
    #[serde(default)]
    timeout_s: Option<u64>,
}

async fn execute(
    State(runtime): State<Runtime>,
    Path(job): Path<String>,
    headers: HeaderMap,
    body: Result<Json<ExecuteBody>, axum::extract::rejection::JsonRejection>,
) -> Response {
    let body = match body {
        Ok(Json(body)) => body,
        Err(rejection) => {
            return match rejection.status().as_u16() {
                413 => error(413, "AAK-VAL-003", "request exceeds limit"),
                415 => error(415, "AAK-VAL-002", "JSON content type required"),
                _ => error(422, "AAK-VAL-001", "invalid execution request"),
            };
        }
    };
    let mut values = headers.get_all("idempotency-key").iter();
    let id = values
        .next()
        .and_then(|h| h.to_str().ok())
        .unwrap_or_default()
        .to_owned();
    if values.next().is_some()
        || !valid_id(&id)
        || !valid_id(&job)
        || body.deadline_ms == 0
        || body.deadline_ms > 300_000
    {
        return error(
            422,
            "AAK-VAL-001",
            "bounded execution identity and deadline required",
        );
    }
    let split = body.split;
    // The accepted HTTP operation outlives a disconnected waiter, including
    // the interval between durable claim, registration and worker completion.
    tokio::spawn(async move { start(runtime, job, id, body.deadline_ms, split).await })
        .await
        .unwrap_or_else(|_| unavailable())
}
async fn start(runtime: Runtime, job: String, id: String, deadline: u64, split: bool) -> Response {
    let _admission = runtime.admission.lock().await;
    // R7/G1: name a disabled capability instead of letting it fall into the generic "cannot start in
    // its current state". The authoritative refusal is inside the claim transaction, which is what
    // guarantees no attempt row is created; this is here because `Executor::start` reports failures
    // as strings, so without it the caller is told the job cannot start and not why.
    if let Some(capability) = runtime.executor.disabled_capability_for(&job).await {
        return error(
            409,
            "AAK-CAP-001",
            &format!("capability {capability} is disabled in this workspace"),
        );
    }
    if runtime
        .active
        .lock()
        .await
        .get(&job)
        .is_some_and(|entry| entry.faulted)
    {
        return unavailable();
    }
    let query_id = id.clone();
    let previous = runtime
        .executor
        .store()
        .submit(move |conn| {
            conn.query_row(
                "SELECT job_id,request_json,state FROM job_attempts WHERE request_id=?1",
                [query_id],
                |r| {
                    Ok((
                        r.get::<_, String>(0)?,
                        r.get::<_, String>(1)?,
                        r.get::<_, String>(2)?,
                    ))
                },
            )
            .optional()
        })
        .await;
    match previous {
        Ok(Ok(Some((old_job, request, state)))) => {
            let request: Value = match serde_json::from_str(&request) {
                Ok(r) => r,
                Err(_) => return unavailable(),
            };
            // Whether the job was split is part of the request identity: the same key must not
            // replay a whole-file receipt for a split request, or the reverse.
            let same_split = request
                .pointer("/parameters/split")
                .and_then(Value::as_bool)
                .unwrap_or(false)
                == split;
            return if old_job == job && request["deadline_ms"] == deadline && same_split {
                (
                    StatusCode::ACCEPTED,
                    Json(json!({"job_id":job,"request_id":id,"state":state,"replayed":true})),
                )
                    .into_response()
            } else {
                conflict()
            };
        }
        Ok(Ok(None)) => (),
        _ => return unavailable(),
    }
    {
        let active = runtime.active.lock().await;
        if active.contains_key(&job) {
            return conflict();
        }
        if active.len() >= 2 {
            return unavailable();
        }
    }
    let cancel = Cancellation::new();
    let task = match runtime
        .executor
        .start_splitting(&job, &id, deadline, &cancel, split)
        .await
    {
        Ok(task) => task,
        Err(_) => return error(409, "AAK-CON-003", "job cannot start in its current state"),
    };
    runtime.active.lock().await.insert(
        job.clone(),
        Active {
            request_id: id.clone(),
            cancel,
            faulted: false,
        },
    );
    let registry = runtime.active.clone();
    let key = job.clone();
    let request = id.clone();
    let store = runtime.executor.store().clone();
    tokio::spawn(async move {
        let _outcome = task.await; // Database terminal evidence, not a returned string, owns status.
        let query = request.clone();
        let terminal = store
            .submit_wait(move |conn| -> Result<(), String> {
                let (state, wire): (String, String) = conn
                    .query_row(
                        "SELECT state,request_json FROM job_attempts WHERE request_id=?1",
                        [query],
                        |r| Ok((r.get(0)?, r.get(1)?)),
                    )
                    .map_err(|e| e.to_string())?;
                if state == "running" {
                    let request = serde_json::from_str(&wire).map_err(|e| e.to_string())?;
                    archeaxis_application::attempts::terminate(
                        conn,
                        &request,
                        "failed",
                        "Core execution ended without a terminal receipt",
                    )
                    .map_err(|e| e.to_string())?;
                }
                Ok(())
            })
            .await;
        let mut active = registry.lock().await;
        if active
            .get(&key)
            .is_some_and(|entry| entry.request_id == request)
        {
            if matches!(terminal, Ok(Ok(()))) {
                active.remove(&key);
            } else if let Some(entry) = active.get_mut(&key) {
                entry.faulted = true;
            }
        }
    });
    (
        StatusCode::ACCEPTED,
        Json(json!({"job_id":job,"request_id":id,"state":"running","replayed":false})),
    )
        .into_response()
}
async fn status(State(runtime): State<Runtime>, Path(job): Path<String>) -> Response {
    if runtime
        .active
        .lock()
        .await
        .get(&job)
        .is_some_and(|entry| entry.faulted)
    {
        return unavailable();
    }
    let value=runtime.executor.store().submit(move|conn|conn.query_row(
        "SELECT j.state,a.attempt,a.request_id,a.error,j.input_ref FROM jobs j LEFT JOIN job_attempts a ON a.job_id=j.job_id AND a.attempt=(SELECT MAX(attempt) FROM job_attempts WHERE job_id=j.job_id) WHERE j.job_id=?1",
        [&job],|r|Ok(json!({"job_id":job,"state":r.get::<_,String>(0)? ,"attempt":r.get::<_,Option<i64>>(1)? ,"request_id":r.get::<_,Option<String>>(2)? ,"error":r.get::<_,Option<String>>(3)? ,"input_ref":r.get::<_,String>(4)?}))).optional()).await;
    match value {
        Ok(Ok(Some(value))) => Json(value).into_response(),
        Ok(Ok(None)) => error(404, "AAK-VAL-004", "job not found"),
        _ => unavailable(),
    }
}
async fn cancel(
    State(runtime): State<Runtime>,
    Path((job, id)): Path<(String, String)>,
) -> Response {
    {
        let active = runtime.active.lock().await;
        if let Some(entry) = active.get(&job) {
            if entry.faulted {
                return unavailable();
            }
            if entry.request_id != id {
                return conflict();
            }
            entry.cancel.cancel();
            return (
                StatusCode::ACCEPTED,
                Json(json!({"job_id":job,"request_id":id,"cancel_requested":true})),
            )
                .into_response();
        }
    }
    let query_job = job.clone();
    let query_id = id.clone();
    let previous = runtime
        .executor
        .store()
        .submit(move |conn| {
            conn.query_row(
                "SELECT state FROM job_attempts WHERE job_id=?1 AND request_id=?2",
                [query_job, query_id],
                |r| r.get::<_, String>(0),
            )
            .optional()
        })
        .await;
    match previous {
        Ok(Ok(Some(state))) if state != "running" => {
            Json(json!({"job_id":job,"request_id":id,"state":state,"cancel_requested":false}))
                .into_response()
        }
        Ok(Ok(None)) => error(404, "AAK-VAL-004", "execution not found"),
        _ => unavailable(),
    }
}
async fn output(
    State(runtime): State<Runtime>,
    Path((job, kind)): Path<(String, String)>,
) -> Response {
    let value=runtime.executor.store().submit(move|conn|conn.query_row(
        "SELECT metadata_json,content FROM job_outputs WHERE job_id=?1 AND kind=?2 AND attempt=(SELECT MAX(attempt) FROM job_attempts WHERE job_id=?1)",
        [job,kind],|r|Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?))).optional()).await;
    match value {
        Ok(Ok(Some((metadata, content)))) => match serde_json::from_str::<Value>(&metadata) {
            Ok(metadata) => Json(json!({"metadata":metadata,"content":content})).into_response(),
            Err(_) => unavailable(),
        },
        Ok(Ok(None)) => error(404, "AAK-VAL-004", "output not found"),
        _ => unavailable(),
    }
}

async fn execute_document_check(
    State(runtime): State<Runtime>,
    Path(id): Path<String>,
    headers: HeaderMap,
    Json(body): Json<crate::documents::CheckExecuteBody>,
) -> Response {
    crate::documents::execute_runtime_check(runtime.executor, id, headers, body).await
}
