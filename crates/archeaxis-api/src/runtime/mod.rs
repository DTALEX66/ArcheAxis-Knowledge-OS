//! Owned text execution HTTP projection; never accepts executable paths over HTTP.
use archeaxis_application::executor::{Cancellation, Executor};
use axum::{
    Json, Router,
    extract::{Path, State},
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
    routing::{get, post},
};
use rusqlite::OptionalExtension;
use serde::Deserialize;
use serde_json::{Value, json};
use std::{collections::HashMap, sync::Arc};
use tokio::sync::Mutex;

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
}
pub fn router(executor: Executor) -> Router {
    let projections = crate::projections(executor.store().clone(), false);
    Router::new()
        .route("/api/v1/jobs/:job_id", get(status))
        .route("/api/v1/jobs/:job_id/executions", post(execute))
        .route(
            "/api/v1/jobs/:job_id/executions/:request_id/cancel",
            post(cancel),
        )
        .route("/api/v1/jobs/:job_id/outputs/:kind", get(output))
        .with_state(Runtime {
            executor,
            active: Arc::new(Mutex::new(HashMap::new())),
            admission: Arc::new(Mutex::new(())),
        })
        .merge(projections)
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
    // The accepted HTTP operation outlives a disconnected waiter, including
    // the interval between durable claim, registration and worker completion.
    tokio::spawn(async move { start(runtime, job, id, body.deadline_ms).await })
        .await
        .unwrap_or_else(|_| unavailable())
}
async fn start(runtime: Runtime, job: String, id: String, deadline: u64) -> Response {
    let _admission = runtime.admission.lock().await;
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
            return if old_job == job && request["deadline_ms"] == deadline {
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
    let task = match runtime.executor.start(&job, &id, deadline, &cancel).await {
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
        "SELECT j.state,a.attempt,a.request_id,a.error FROM jobs j LEFT JOIN job_attempts a ON a.job_id=j.job_id AND a.attempt=(SELECT MAX(attempt) FROM job_attempts WHERE job_id=j.job_id) WHERE j.job_id=?1",
        [&job],|r|Ok(json!({"job_id":job,"state":r.get::<_,String>(0)?,"attempt":r.get::<_,Option<i64>>(1)?,"request_id":r.get::<_,Option<String>>(2)?,"error":r.get::<_,Option<String>>(3)?}))).optional()).await;
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
