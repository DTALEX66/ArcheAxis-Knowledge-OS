use super::*;
use archeaxis_domain::readiness::{self, Snapshot};
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Query {
    pub scope: String,
    pub operations: Vec<String>,
}
fn valid(q: &Query) -> bool {
    !q.scope.is_empty()
        && q.scope.len() <= 128
        && !q.scope.chars().any(char::is_control)
        && !q.operations.is_empty()
        && q.operations.len() <= 32
        && q.operations.iter().enumerate().all(|(i, s)| {
            !s.is_empty()
                && s.len() <= 128
                && s.bytes()
                    .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'_' | b'-'))
                && !q.operations[..i].contains(s)
        })
}
/// No worker spawn, network, model inventory or engine load. Uses current registered routes.
pub async fn current(executor: &Executor, q: Query) -> Result<Snapshot, StatusCode> {
    if !valid(&q) {
        return Err(StatusCode::UNPROCESSABLE_ENTITY);
    }
    let (disabled, readable) = crate::capabilities::disabled_and_readable(executor).await;
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
        .as_millis() as u64;
    let expires = now.saturating_add(30_000);
    let routes = executor.registered_routes();
    let rows = q
        .operations
        .into_iter()
        .map(|name| {
            let providers: Vec<_> = routes.iter().filter(|r| r.0 == name).collect();
            let implemented = !providers.is_empty();
            let dependencies =
                executor.python_path().is_file() && providers.iter().any(|r| r.1.is_file());
            let permission = if readable {
                Some(!disabled.contains(&name))
            } else {
                None
            };
            readiness::observe(name, implemented, dependencies, permission, expires)
        })
        .collect();
    Ok(readiness::snapshot(q.scope, now, rows))
}
pub(super) async fn read(State(r): State<Runtime>, Json(q): Json<Query>) -> Response {
    match current(&r.executor, q).await {
        Ok(s) => Json(s).into_response(),
        Err(status) => (status, Json(json!({"error":"READINESS_SCOPE_INVALID"}))).into_response(),
    }
}
/// Fresh execution dependency check. Readiness never substitutes for grants/engine checks.
pub async fn require_execution_dependencies(
    executor: &Executor,
    operation: &str,
) -> Result<(), String> {
    let s = current(
        executor,
        Query {
            scope: "execution-admission".into(),
            operations: vec![operation.into()],
        },
    )
    .await
    .map_err(|_| "READINESS_UNAVAILABLE".to_string())?;
    let row = &s.operations[0];
    if row.implementation != "IMPLEMENTED"
        || row.dependencies != "AVAILABLE"
        || row.permission != "ENABLED"
    {
        return Err("OPERATION_DEPENDENCIES_OR_PERMISSION_UNAVAILABLE".into());
    }
    Ok(())
}
