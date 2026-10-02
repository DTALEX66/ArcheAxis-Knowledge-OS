//! R7/G1: the capability surface the UI reads to tell a capability apart from a promise.
//!
//! Section 42 of the master taskpack asks the first version for a registry, enable/disable, health,
//! default and fallback, and section 33 names `AAOS_CAPABILITY_REGISTRY_V1`. This module is that
//! surface, and it is deliberately narrow about what it claims.
//!
//! The honesty rules it follows, because a capability surface is exactly where a project starts
//! lying to itself:
//!
//! * It reports the routes the Core actually registered, not the routes a checkout happens to
//!   contain. The launch declares routes, so the launch is the source of truth.
//! * `health` describes what is checkable from here - whether the worker script exists and whether
//!   the interpreter does. It does **not** claim a capability is working, because that requires
//!   running a job, and a registry cannot substitute for a job.
//! * `enabled` comes from the workspace's own capability record, not from a guess. When that record
//!   cannot be read the field falls back to the launch's registration state and the response says
//!   so, rather than reporting a decision nobody made.
//! * A disabled capability is refused by the execute path, so the field is not decoration: turning a
//!   capability off actually stops it running.

use std::collections::HashSet;
use std::path::Path;

use axum::Json;
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use serde_json::json;

use archeaxis_application::executor::Executor;
use archeaxis_store_sqlite::capability_settings;

/// Whether a path exists as a regular file. Health is a fact about the filesystem, so it is checked
/// rather than assumed from configuration.
fn file_exists(path: &Path) -> bool {
    std::fs::metadata(path)
        .map(|meta| meta.is_file())
        .unwrap_or(false)
}

/// The capabilities this workspace has explicitly disabled, and whether that record could be read.
///
/// A store failure yields an empty set plus `false`, and every record then says its `enabled` value
/// is the launch's registration rather than a decision. The alternative - defaulting silently to
/// "enabled" - would turn a database problem into a claim that nothing was ever turned off.
pub async fn disabled_and_readable(executor: &Executor) -> (HashSet<String>, bool) {
    let read = executor
        .store()
        .submit_wait(|conn: &mut rusqlite::Connection| {
            capability_settings::disabled_capabilities(conn)
        })
        .await;
    match read {
        Ok(Ok(list)) => (list.into_iter().collect(), true),
        _ => (HashSet::new(), false),
    }
}

pub fn capability_record(
    capability: &str,
    worker: &Path,
    site_packages: bool,
    python: &Path,
    disabled: &HashSet<String>,
    record_readable: bool,
) -> serde_json::Value {
    let worker_present = file_exists(worker);
    let python_present = file_exists(python);
    let health = if !worker_present {
        // A declared capability whose worker is absent is not "unhealthy"; it is unusable, and the
        // difference matters to whoever has to fix it.
        "worker_missing"
    } else if !python_present {
        "interpreter_missing"
    } else {
        "declared"
    };
    json!({
        "capability": capability,
        "provider": {
            // The provider is the worker script. Naming it is what lets a UI say which process
            // would answer, instead of implying a capability is built into the Core.
            "kind": "python-worker",
            "worker": worker.to_string_lossy(),
            "worker_present": worker_present,
            "interpreter": python.to_string_lossy(),
            "interpreter_present": python_present,
            "uses_site_packages": site_packages,
        },
        "enabled": !disabled.contains(capability),
        "enabled_basis": if record_readable {
            "the workspace's capability record; an absent record means enabled"
        } else {
            "the capability record could not be read, so this is the launch's registration rather \
             than a decision"
        },
        "registered": true,
        "health": health,
        "health_basis": "file existence only - a job has to run before anything may be called \
                         working",
        "is_default": true,
        "fallback": serde_json::Value::Null,
        "fallback_note": "no second provider exists for any capability yet",
    })
}

/// The whole registry.
pub async fn list(executor: &Executor) -> Response {
    let (disabled, readable) = disabled_and_readable(executor).await;
    let routes = executor.registered_routes();
    let python = executor.python_path();
    let capabilities: Vec<serde_json::Value> = routes
        .iter()
        .map(|(capability, worker, site_packages)| {
            capability_record(
                capability,
                worker,
                *site_packages,
                python,
                &disabled,
                readable,
            )
        })
        .collect();
    let unhealthy = capabilities
        .iter()
        .filter(|record| record["health"] != "declared")
        .count();
    let disabled_count = capabilities
        .iter()
        .filter(|record| record["enabled"] == false)
        .count();
    Json(json!({
        "schema": "archeaxis.capabilities/v1",
        "source": "capability routes declared at launch and registered by the Core",
        "count": capabilities.len(),
        "disabled": disabled_count,
        "unhealthy": unhealthy,
        "declared_only": true,
        "declared_only_note": "this surface reports registration and file health; it is not proof \
                               a capability works, and a passing entry here must not be read as one",
        "capabilities": capabilities,
    }))
    .into_response()
}

/// One capability by its exact dot-separated name. A near miss is a 404 rather than the nearest
/// match, because a registry that guesses is worse than one that says it does not know.
pub async fn read(executor: &Executor, capability: &str) -> Response {
    // Registration is checked first: a capability that does not exist cannot be enabled, disabled or
    // reported, and saying "not found" is more useful than answering about its settings.
    let registered = executor
        .registered_routes()
        .iter()
        .map(|(name, worker, site_packages)| {
            (name.to_string(), worker.to_path_buf(), *site_packages)
        })
        .find(|(name, _, _)| name == capability);
    let Some((name, worker, site_packages)) = registered else {
        return (
            StatusCode::NOT_FOUND,
            format!("no capability is registered as {capability}"),
        )
            .into_response();
    };
    let (disabled, readable) = disabled_and_readable(executor).await;
    let python = executor.python_path();
    Json(json!({
        "schema": "archeaxis.capability/v1",
        "capability": capability_record(&name, &worker, site_packages, python, &disabled, readable),
    }))
    .into_response()
}

/// Turn a capability on or off, and answer with the record as it now stands.
///
/// The write goes through the Core's own store, like every other canonical change, and the response
/// is re-read from the record rather than echoed from the request: a reply that repeated the request
/// would not prove the write landed.
pub async fn set_enabled(executor: &Executor, capability: &str, enabled: bool) -> Response {
    let registered = executor
        .registered_routes()
        .iter()
        .any(|(name, _, _)| *name == capability);
    if !registered {
        // Refusing an unknown capability keeps this table from accumulating rows for capabilities
        // that do not exist, which would later read as decisions about nothing.
        return (
            StatusCode::NOT_FOUND,
            format!("no capability is registered as {capability}"),
        )
            .into_response();
    }
    let owned = capability.to_string();
    let written = executor
        .store()
        .submit_wait(move |conn| capability_settings::set_enabled(conn, &owned, enabled))
        .await;
    match written {
        Ok(Ok(())) => read(executor, capability).await,
        _ => (
            StatusCode::SERVICE_UNAVAILABLE,
            "the capability record could not be written",
        )
            .into_response(),
    }
}

/// Whether the execute path should refuse this capability.
///
/// A store that cannot be read does **not** block execution: refusing to run because a settings read
/// failed would turn a diagnosable problem into an outage, and the capability is enabled by default.
pub async fn refusal(executor: &Executor, capability: &str) -> Option<Response> {
    let (disabled, readable) = disabled_and_readable(executor).await;
    if readable && disabled.contains(capability) {
        return Some(
            (
                StatusCode::CONFLICT,
                format!("capability {capability} is disabled in this workspace"),
            )
                .into_response(),
        );
    }
    None
}
