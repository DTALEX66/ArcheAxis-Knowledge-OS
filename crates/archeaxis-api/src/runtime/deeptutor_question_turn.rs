//! DeepTutor's single-question step as a Core route: capture the donor prompt
//! from the pinned local worker, call the declared local text model, replay the
//! reply through the same worker and persist one inert candidate Document.
use super::*;
use archeaxis_application::executor::{Cancellation, QuestionTurnWorkerError};
use archeaxis_domain::{
    document as turn_error, openmaic_outline,
    provider_question_turn::{self as turn, QuestionTurnRequest},
};
use std::{
    sync::{Arc, Mutex as PublicationMutex},
    time::Duration,
};

const CAPTURE_TIMEOUT: Duration = Duration::from_secs(60);
const MODEL_TIMEOUT: Duration = Duration::from_secs(120);
const REPLAY_TIMEOUT: Duration = Duration::from_secs(60);
const MAX_ACTIVE_REQUESTS: usize = 64;

/// Only this question-turn lane owns these entries. Machine-answer retry and
/// capability-withdrawal registries must not reinterpret their claim identity.
#[derive(Clone, Default)]
pub(super) struct Registry(Arc<PublicationMutex<HashMap<String, Arc<ActiveQuestion>>>>);

struct ActiveQuestion {
    request_sha256: String,
    pending: Arc<turn::QuestionTurnPending>,
    cancel: Cancellation,
    publication: Arc<PublicationMutex<bool>>,
}

impl Registry {
    fn register(
        &self,
        request: &QuestionTurnRequest,
        pending: Arc<turn::QuestionTurnPending>,
        cancel: Cancellation,
        publication: Arc<PublicationMutex<bool>>,
    ) -> Result<(), &'static str> {
        let request_sha256 = turn::request_sha256(request)
            .map_err(|_| "question_turn_registry_identity_unavailable")?;
        let mut entries = self
            .0
            .lock()
            .map_err(|_| "question_turn_registry_unknown")?;
        if entries.contains_key(&request.create_request_id) {
            return Err("question_turn_registry_identity_conflict");
        }
        if entries.len() >= MAX_ACTIVE_REQUESTS {
            return Err("question_turn_registry_full");
        }
        entries.insert(
            request.create_request_id.clone(),
            Arc::new(ActiveQuestion {
                request_sha256,
                pending,
                cancel,
                publication,
            }),
        );
        Ok(())
    }

    fn find(&self, id: &str) -> Result<Option<Arc<ActiveQuestion>>, turn_error::Error> {
        self.0
            .lock()
            .map(|entries| entries.get(id).cloned())
            .map_err(|_| turn_error::Error::Invalid(turn::QUESTION_TURN_EXECUTION_UNRESOLVED))
    }

    fn remove(&self, id: &str, publication: &Arc<PublicationMutex<bool>>) {
        if let Ok(mut entries) = self.0.lock() {
            if entries
                .get(id)
                .is_some_and(|entry| Arc::ptr_eq(&entry.publication, publication))
            {
                entries.remove(id);
            }
        }
    }
}

/// Dropping the HTTP request closes publication and cancels the capture/replay
/// worker and its request-owned model transport. Provider-side stop is still UNKNOWN.
/// The durable claim blocks replay even when this best-effort terminal write is lost.
struct RequestLease {
    cancel: Cancellation,
    publication: Arc<PublicationMutex<bool>>,
    failure: Option<(
        archeaxis_store_sqlite::writer::Store,
        Arc<turn::QuestionTurnPending>,
    )>,
    registration: Option<(Registry, String)>,
}
impl Drop for RequestLease {
    fn drop(&mut self) {
        // Same critical section as the writer's final commit. A commit which
        // already owns this gate wins; a drop which owns it first prevents commit.
        if let Ok(mut open) = self.publication.lock() {
            *open = false;
        }
        self.cancel.cancel();
        if let Some((registry, id)) = self.registration.take() {
            registry.remove(&id, &self.publication);
        }
        if let Some((store, pending)) = self.failure.take() {
            if let Ok(handle) = tokio::runtime::Handle::try_current() {
                handle.spawn(async move {
                    let _ = store
                        .submit(move |conn| {
                            turn::finish_question_turn_failure(
                                conn,
                                &pending,
                                turn::QuestionTurnFailure::Unknown,
                            )
                        })
                        .await;
                });
            }
        }
    }
}

fn failure(status: StatusCode, reason: &'static str) -> Response {
    (
        status,
        Json(json!({"code":"DEEPTUTOR_QUESTION_TURN","reason":reason,
            "retryable":false})),
    )
        .into_response()
}

/// A stage failure named by the stage that produced it and by the worker's or
/// model's own status/reason, never rewritten into a generic message.
fn stage_failure(
    status: StatusCode,
    stage: &'static str,
    reason: &'static str,
    outcome: Value,
) -> Response {
    (
        status,
        Json(json!({"code":"DEEPTUTOR_QUESTION_TURN","reason":reason,
            "retryable":false,
            "stage":stage,"worker_outcome":outcome})),
    )
        .into_response()
}

fn worker_failure_reason(error: QuestionTurnWorkerError) -> &'static str {
    match error {
        QuestionTurnWorkerError::InvalidInput => "question_turn_worker_input_invalid",
        QuestionTurnWorkerError::Unavailable => "question_turn_worker_unavailable",
        QuestionTurnWorkerError::IdentityMismatch => "question_turn_worker_identity_mismatch",
        QuestionTurnWorkerError::Cancelled => "question_turn_request_cancelled",
        QuestionTurnWorkerError::TimedOut => "question_turn_worker_timed_out",
        QuestionTurnWorkerError::CleanupUnknown => "question_turn_worker_cleanup_unknown",
    }
}

fn worker_outcome(value: &Value) -> Value {
    json!({"status":value["document"]["status"],"reason":value["document"]["reason_code"],
        "exit_code":value["exit_code"]})
}

/// Map one worker result to the caller's status. Every named non-success keeps
/// the worker's own status; an exit code outside the declared 0/1/2 is an
/// unrecognized outcome rather than a candidate.
fn worker_status(value: &Value) -> Option<StatusCode> {
    if value["exit_code"] == 0 {
        return None;
    }
    Some(match value["document"]["status"].as_str() {
        Some("UNAVAILABLE") => StatusCode::SERVICE_UNAVAILABLE,
        Some("INVALID_REQUEST" | "REJECTED") => StatusCode::UNPROCESSABLE_ENTITY,
        _ => StatusCode::SERVICE_UNAVAILABLE,
    })
}

fn worker_reason(value: &Value) -> &'static str {
    match value["document"]["status"].as_str() {
        Some("UNAVAILABLE") => "question_turn_worker_upstream_unavailable",
        Some("INVALID_REQUEST") => "question_turn_worker_input_rejected",
        Some("REJECTED") => "question_turn_worker_response_rejected",
        _ => "question_turn_worker_outcome_unrecognized",
    }
}

fn result_response(status: StatusCode, receipt: Value, worker_invoked: bool) -> Response {
    let mut body = receipt;
    body["worker_invoked"] = json!(worker_invoked);
    (status, Json(body)).into_response()
}

fn claim_refusal(reason: &'static str) -> Response {
    (
        StatusCode::CONFLICT,
        Json(json!({
            "code":"DEEPTUTOR_QUESTION_TURN", "reason":reason, "retryable":false,
            "prior_execution":"UNVERIFIED",
            "current_invocation":{"worker_invoked":false,"model_invoked":false}
        })),
    )
        .into_response()
}

/// Exact-request reconciliation only. DISPATCHED reports durable intent, never process liveness.
pub(super) async fn status(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(request): Json<QuestionTurnRequest>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return failure(StatusCode::FORBIDDEN, "human_actor_required");
    }
    if turn::request_refusal(&request).is_some() {
        return failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "invalid_question_turn_request",
        );
    }
    match runtime
        .executor
        .store()
        .submit_wait(move |conn| turn::question_turn_status(conn, &request))
        .await
    {
        Ok(Ok(value)) => Json(value).into_response(),
        Ok(Err(archeaxis_domain::document::Error::Conflict(_))) => {
            claim_refusal("question_turn_request_id_conflict")
        }
        // Missing/invalid canonical bytes or a corrupt barrier cannot become NOT_FOUND.
        Ok(Err(_)) => claim_refusal("question_turn_execution_outcome_unresolved"),
        Err(_) => failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "question_turn_status_unavailable",
        ),
    }
}

/// An independent command can cancel while the generation HTTP call is still
/// pending. Its durable write and final candidate publication use the same writer.
pub(super) async fn cancel(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(request): Json<QuestionTurnRequest>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return failure(StatusCode::FORBIDDEN, "human_actor_required");
    }
    if turn::request_refusal(&request).is_some() {
        return failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "invalid_question_turn_request",
        );
    }
    let registry = runtime.question_turn_active.clone();
    let result = runtime
        .executor
        .store()
        .submit_wait(move |conn| cancel_owned(conn, &registry, &request))
        .await;
    match result {
        Ok(Ok(value)) => Json(value).into_response(),
        Ok(Err(turn_error::Error::Conflict(_))) => {
            claim_refusal("question_turn_request_id_conflict")
        }
        Ok(Err(_)) => claim_refusal("question_turn_execution_outcome_unresolved"),
        Err(_) => failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "question_turn_cancel_unavailable",
        ),
    }
}

fn cancel_owned(
    conn: &mut rusqlite::Connection,
    registry: &Registry,
    request: &QuestionTurnRequest,
) -> Result<Value, turn_error::Error> {
    // Lookup inside the writer callback closes the prepare/registration
    // gap: a missing entry still receives a durable UNKNOWN barrier before
    // any later dispatch check can run. Never hold the map lock over I/O.
    let entry = registry.find(&request.create_request_id)?;
    if let Some(entry) = entry {
        if entry.request_sha256 != turn::request_sha256(&request)? {
            return Err(turn_error::Error::Conflict(1));
        }
        let mut open = entry
            .publication
            .lock()
            .map_err(|_| turn_error::Error::Invalid(turn::QUESTION_TURN_EXECUTION_UNRESOLVED))?;
        let receipt = turn::cancel_question_turn(conn, &request, Some(&entry.pending))?;
        if receipt["cancel_requested"] == true {
            *open = false;
            entry.cancel.cancel();
        }
        Ok(receipt)
    } else {
        // After restart no handle proves a worker stopped. The persisted
        // barrier still prevents later publication and never permits replay.
        turn::cancel_question_turn(conn, &request, None)
    }
}

/// Capture, model, replay, persist. Every failing stage leaves no Document.
pub(super) async fn question_turn(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(request): Json<QuestionTurnRequest>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return failure(StatusCode::FORBIDDEN, "human_actor_required");
    }
    if turn::request_refusal(&request).is_some() {
        return failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "invalid_question_turn_request",
        );
    }
    let mut lease = RequestLease {
        cancel: Cancellation::new(),
        publication: Arc::new(PublicationMutex::new(true)),
        failure: None,
        registration: None,
    };
    let prepared = runtime
        .executor
        .store()
        .submit_wait({
            let request = request.clone();
            move |conn| turn::prepare_question_turn(conn, &request)
        })
        .await;
    let pending = match prepared {
        Ok(Ok(turn::QuestionTurnPreparation::Existing(receipt))) => {
            // A repeated request reads the stored candidate; no prompt, model or
            // worker runs again.
            return result_response(StatusCode::OK, receipt, false);
        }
        Ok(Ok(turn::QuestionTurnPreparation::Pending(pending))) => pending,
        Ok(Err(archeaxis_domain::document::Error::Invalid(
            turn::QUESTION_TURN_EXECUTION_UNRESOLVED,
        ))) => {
            return claim_refusal("question_turn_execution_outcome_unresolved");
        }
        Ok(Err(archeaxis_domain::document::Error::Invalid(
            turn::QUESTION_TURN_GRANT_SCAN_EXHAUSTED,
        ))) => {
            return failure(StatusCode::CONFLICT, "question_turn_grant_scan_limit");
        }
        Ok(Err(archeaxis_domain::document::Error::Conflict(_))) => {
            return claim_refusal("question_turn_request_id_conflict");
        }
        Ok(Err(archeaxis_domain::document::Error::NotFound)) => {
            return failure(StatusCode::CONFLICT, "question_turn_material_unavailable");
        }
        Ok(Err(archeaxis_domain::document::Error::Invalid(_))) => {
            return failure(
                StatusCode::CONFLICT,
                "question_turn_material_not_authorized_or_changed",
            );
        }
        _ => {
            return failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "question_turn_preparation_failed",
            );
        }
    };
    let pending = Arc::new(pending);
    lease.failure = Some((runtime.executor.store().clone(), pending.clone()));
    if let Err(reason) = runtime.question_turn_active.register(
        &request,
        pending.clone(),
        lease.cancel.clone(),
        lease.publication.clone(),
    ) {
        // The dispatch intent remains non-replayable if registration fails.
        // No worker has been invoked; Drop attempts the conservative terminal write.
        return failure(StatusCode::SERVICE_UNAVAILABLE, reason);
    }
    lease.registration = Some((
        runtime.question_turn_active.clone(),
        request.create_request_id.clone(),
    ));
    let response = run_claimed(&runtime, request, pending.clone(), &lease).await;
    if response.status().is_success() {
        // The Document and COMPLETED claim were committed in one transaction.
        lease.failure = None;
    } else {
        let outcome = if response.status() == StatusCode::UNPROCESSABLE_ENTITY {
            turn::QuestionTurnFailure::Failed
        } else {
            // Transport, cancellation, timeout and cleanup cannot prove provider stop.
            turn::QuestionTurnFailure::Unknown
        };
        if matches!(
            runtime
                .executor
                .store()
                .submit_wait(move |conn| {
                    turn::finish_question_turn_failure(conn, &pending, outcome)
                })
                .await,
            Ok(Ok(()))
        ) {
            lease.failure = None;
        }
    }
    response
}

async fn run_claimed(
    runtime: &Runtime,
    request: QuestionTurnRequest,
    pending: Arc<turn::QuestionTurnPending>,
    lease: &RequestLease,
) -> Response {
    if !dispatch_authorized(runtime, &pending, lease).await {
        return failure(
            StatusCode::CONFLICT,
            "question_turn_dispatch_not_authorized_or_changed",
        );
    }
    // Stage 1: capture the donor prompt. The capture carries no reply.
    let capture = runtime
        .executor
        .run_deeptutor_question_turn(
            pending.capture_frame().to_vec(),
            CAPTURE_TIMEOUT,
            lease.cancel.clone(),
        )
        .await;
    let capture = match capture {
        Ok(value) => value,
        Err(error) => {
            return failure(
                StatusCode::SERVICE_UNAVAILABLE,
                worker_failure_reason(error),
            );
        }
    };
    if let Some(status) = worker_status(&capture) {
        return stage_failure(
            status,
            "capture",
            worker_reason(&capture),
            worker_outcome(&capture),
        );
    }
    if capture["document"]["status"] != "CAPTURED" {
        return stage_failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "capture",
            "question_turn_capture_outcome_unrecognized",
            worker_outcome(&capture),
        );
    }
    let binding = match turn::capture_binding(&request.create_request_id, &capture["document"]) {
        Ok(value) => value,
        Err(_) => {
            return stage_failure(
                StatusCode::BAD_GATEWAY,
                "capture",
                "question_turn_capture_binding_invalid",
                worker_outcome(&capture),
            );
        }
    };
    // Stage 2: the one declared local text model, through the same worker and
    // hardened loopback-only transport as the outline route.
    if !dispatch_authorized(runtime, &pending, lease).await {
        return failure(
            StatusCode::CONFLICT,
            "question_turn_dispatch_not_authorized_or_changed",
        );
    }
    let model = runtime
        .executor
        .local_model_json_cancellable(
            turn::model_request(&binding, &request.model),
            MODEL_TIMEOUT,
            lease.cancel.clone(),
        )
        .await;
    let model = match model {
        Ok(value) => value,
        Err(reason) => {
            let (status, code) = match reason.as_str() {
                "local model request cancelled" => {
                    (StatusCode::CONFLICT, "question_turn_local_model_cancelled")
                }
                "local model request timed out" => (
                    StatusCode::GATEWAY_TIMEOUT,
                    "question_turn_local_model_timed_out",
                ),
                "local model worker cleanup unknown" => (
                    StatusCode::SERVICE_UNAVAILABLE,
                    "question_turn_local_model_cleanup_unknown",
                ),
                _ => (
                    StatusCode::SERVICE_UNAVAILABLE,
                    "question_turn_local_model_capability_unavailable",
                ),
            };
            return stage_failure(
                status,
                "local_model",
                code,
                json!({"reason":reason,"provider_stop_state":"UNKNOWN"}),
            );
        }
    };
    let model_outcome = worker_outcome(&model);
    if model["exit_code"] != 0 || model["document"]["status"] != "REPLY" {
        let status = match model["document"]["status"].as_str() {
            Some("MODEL_REJECTED" | "INVALID_MODEL_OUTPUT") => StatusCode::UNPROCESSABLE_ENTITY,
            Some("MODEL_TIMEOUT" | "NO_FINAL_ANSWER") => StatusCode::GATEWAY_TIMEOUT,
            _ => StatusCode::SERVICE_UNAVAILABLE,
        };
        return stage_failure(
            status,
            "local_model",
            "question_turn_local_model_failed",
            model_outcome,
        );
    }
    let Some(content) =
        openmaic_outline::openmaic_outline_model_content(&model["document"]).map(str::to_owned)
    else {
        return stage_failure(
            StatusCode::BAD_GATEWAY,
            "local_model",
            "question_turn_local_model_receipt_inconsistent",
            model_outcome,
        );
    };
    let prompt_sha256 = binding["prompt_sha256"]
        .as_str()
        .unwrap_or_default()
        .to_owned();
    // Stage 3: replay the model text through the real donor worker.
    let replay_frame = match pending.replay_frame(&prompt_sha256, &content) {
        Ok(value) => value,
        Err(_) => {
            return stage_failure(
                StatusCode::UNPROCESSABLE_ENTITY,
                "replay",
                "question_turn_replay_frame_unusable",
                model_outcome,
            );
        }
    };
    if !dispatch_authorized(runtime, &pending, lease).await {
        return failure(
            StatusCode::CONFLICT,
            "question_turn_dispatch_not_authorized_or_changed",
        );
    }
    let replay = runtime
        .executor
        .run_deeptutor_question_turn(replay_frame, REPLAY_TIMEOUT, lease.cancel.clone())
        .await;
    let replay = match replay {
        Ok(value) => value,
        Err(error) => {
            return failure(
                StatusCode::SERVICE_UNAVAILABLE,
                worker_failure_reason(error),
            );
        }
    };
    if let Some(status) = worker_status(&replay) {
        return stage_failure(
            status,
            "replay",
            worker_reason(&replay),
            worker_outcome(&replay),
        );
    }
    if replay["document"]["status"] != "CANDIDATE" {
        // Every named replay outcome keeps its own status and reason.
        return stage_failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "replay",
            "question_turn_replay_not_a_candidate",
            worker_outcome(&replay),
        );
    }
    let generation = turn::QuestionTurnGeneration {
        capture_document: capture["document"].clone(),
        model_reply: model["document"].clone(),
        replay_document: replay["document"].clone(),
    };
    if lease.cancel.is_cancelled() {
        return failure(StatusCode::CONFLICT, "question_turn_request_cancelled");
    }
    let cancelled = lease.cancel.clone();
    let publication = lease.publication.clone();
    let persisted = runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            let open = publication.lock().map_err(|_| {
                archeaxis_domain::document::Error::Invalid(
                    "question turn publication state unknown",
                )
            })?;
            if !*open || cancelled.is_cancelled() {
                return Err(archeaxis_domain::document::Error::Invalid(
                    "question turn request cancelled",
                ));
            }
            turn::commit_question_turn(conn, &request, &pending, &generation)
        })
        .await;
    match persisted {
        Ok(Ok(receipt)) => result_response(StatusCode::CREATED, receipt, true),
        Ok(Err(
            archeaxis_domain::document::Error::NotFound
            | archeaxis_domain::document::Error::Invalid(_)
            | archeaxis_domain::document::Error::Conflict(_),
        )) => failure(
            StatusCode::CONFLICT,
            "question_turn_material_or_request_changed",
        ),
        _ => failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "question_turn_persistence_failed",
        ),
    }
}

async fn dispatch_authorized(
    runtime: &Runtime,
    pending: &Arc<turn::QuestionTurnPending>,
    lease: &RequestLease,
) -> bool {
    if lease.cancel.is_cancelled() {
        return false;
    }
    let pending = pending.clone();
    let allowed = runtime
        .executor
        .store()
        .submit_wait(move |conn| turn::assert_question_turn_dispatch(conn, &pending))
        .await;
    matches!(allowed, Ok(Ok(()))) && !lease.cancel.is_cancelled()
}

#[cfg(test)]
mod explicit_cancel_registry_tests {
    use super::*;

    fn fixture() -> (tempfile::TempDir, rusqlite::Connection, QuestionTurnRequest) {
        let dir = tempfile::tempdir().unwrap();
        let mut conn = archeaxis_store_sqlite::init_workspace(
            dir.path().join("registry.sqlite").to_str().unwrap(),
        )
        .unwrap();
        let material = turn_error::create_optional(&mut conn, None, None, "Synthetic registry material",
            json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Synthetic registry arithmetic"}]}]})).unwrap();
        let snapshot = json!({"document_id":material["document_id"],"version":material["version"],"content_sha256":material["content_sha256"]});
        turn_error::create_optional(&mut conn,None,None,"Synthetic registry grant",json!({"type":"doc","content":[],"attrs":{
            "archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1","purpose":"practice","consumer":"deeptutor","operations":["practice"],"material":snapshot,"authorization_basis":"Synthetic explicit choice","expires_at":null,"state":"granted"}}})).unwrap();
        let request = serde_json::from_value(json!({"create_request_id":"registry_0","material":snapshot,"requirement":"Synthetic registry question","model":null})).unwrap();
        (dir, conn, request)
    }

    fn admitted(
        conn: &mut rusqlite::Connection,
        request: &QuestionTurnRequest,
    ) -> Arc<turn::QuestionTurnPending> {
        match turn::prepare_question_turn(conn, request).unwrap() {
            turn::QuestionTurnPreparation::Pending(pending) => Arc::new(pending),
            _ => panic!("fresh registry claim expected"),
        }
    }

    #[test]
    fn explicit_cancel_registry_capacity_and_removal_require_exact_owner() {
        let (_dir, mut conn, template) = fixture();
        let registry = Registry::default();
        let mut first_publication = None;
        for index in 0..MAX_ACTIVE_REQUESTS {
            let mut request = template.clone();
            request.create_request_id = format!("registry_{index}");
            let pending = admitted(&mut conn, &request);
            let publication = Arc::new(PublicationMutex::new(true));
            registry
                .register(&request, pending, Cancellation::new(), publication.clone())
                .unwrap();
            if index == 0 {
                first_publication = Some(publication);
            }
        }
        let mut extra = template.clone();
        extra.create_request_id = "registry_overflow".into();
        let pending = admitted(&mut conn, &extra);
        assert_eq!(
            registry.register(
                &extra,
                pending.clone(),
                Cancellation::new(),
                Arc::new(PublicationMutex::new(true))
            ),
            Err("question_turn_registry_full")
        );
        registry.remove(
            &template.create_request_id,
            &Arc::new(PublicationMutex::new(true)),
        );
        assert_eq!(registry.0.lock().unwrap().len(), MAX_ACTIVE_REQUESTS);
        registry.remove(&template.create_request_id, &first_publication.unwrap());
        registry
            .register(
                &extra,
                pending,
                Cancellation::new(),
                Arc::new(PublicationMutex::new(true)),
            )
            .unwrap();
        assert_eq!(registry.0.lock().unwrap().len(), MAX_ACTIVE_REQUESTS);
    }

    #[test]
    fn explicit_cancel_registry_closes_only_the_matching_request_publication() {
        let (_dir, mut conn, first) = fixture();
        let mut second = first.clone();
        second.create_request_id = "registry_second".into();
        let registry = Registry::default();
        let one = admitted(&mut conn, &first);
        let two = admitted(&mut conn, &second);
        let cancel_one = Cancellation::new();
        let cancel_two = Cancellation::new();
        let publication_one = Arc::new(PublicationMutex::new(true));
        let publication_two = Arc::new(PublicationMutex::new(true));
        registry
            .register(
                &first,
                one.clone(),
                cancel_one.clone(),
                publication_one.clone(),
            )
            .unwrap();
        registry
            .register(
                &second,
                two.clone(),
                cancel_two.clone(),
                publication_two.clone(),
            )
            .unwrap();
        let mut wrong = first.clone();
        wrong.requirement.push_str(" changed");
        assert!(matches!(
            cancel_owned(&mut conn, &registry, &wrong),
            Err(turn_error::Error::Conflict(_))
        ));
        assert!(!cancel_one.is_cancelled() && !cancel_two.is_cancelled());
        let result = cancel_owned(&mut conn, &registry, &first).unwrap();
        assert_eq!(result["cancel_requested"], true);
        assert!(cancel_one.is_cancelled());
        assert!(!*publication_one.lock().unwrap());
        assert!(!cancel_two.is_cancelled());
        assert!(*publication_two.lock().unwrap());
        assert!(turn::assert_question_turn_dispatch(&mut conn, &one).is_err());
        turn::assert_question_turn_dispatch(&mut conn, &two).unwrap();
        let repeated = cancel_owned(&mut conn, &registry, &first).unwrap();
        assert_eq!(repeated, result);
        registry.remove(&first.create_request_id, &publication_one);
        assert!(registry.find(&first.create_request_id).unwrap().is_none());
        assert!(registry.find(&second.create_request_id).unwrap().is_some());
    }
}
